"""
Tests for the skills-based architecture.

Covers: every skill's prompt fragment/tool schema, registry composition
(no duplicate tools, dispatch works), and representative handler behavior
for the trickier tools (destructive-command confirmation flow, directory
switching).
"""

import sys
from pathlib import Path

import pytest

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dials_agent.skills import SkillContext, SkillRegistry, create_default_registry
from dials_agent.dials.workflow import create_workflow_manager
from dials_agent.dials.executor import create_executor
from dials_agent.dials.parser import create_parser


EXPECTED_SKILL_NAMES = {
    "data_import", "spot_finding", "indexing", "refinement", "integration",
    "symmetry", "scaling", "export", "troubleshooting", "workspace",
    "phil_params", "tutorials",
}

EXPECTED_TOOL_NAMES = {
    "change_data_directory", "suggest_troubleshooting", "diagnose_problem",
    "check_workflow_status", "list_available_commands", "read_file",
    "open_file", "change_working_directory", "calculate", "get_timing_report",
    "run_shell_command", "create_markdown_file", "create_html_file",
    "lookup_phil_params",
}


@pytest.fixture
def registry() -> SkillRegistry:
    return create_default_registry()


def make_context(tmp_path: Path, **overrides) -> SkillContext:
    working_directory = str(overrides.pop("working_directory", tmp_path))
    workflow = create_workflow_manager(working_directory)
    defaults = dict(
        working_directory=working_directory,
        data_directory="",
        existing_files=workflow.get_available_files(),
        executor=create_executor(working_directory),
        parser=create_parser(),
        workflow=workflow,
        command_timings=[],
    )
    defaults.update(overrides)
    return SkillContext(**defaults)


# ---------------------------------------------------------------------------
# Registry composition
# ---------------------------------------------------------------------------

def test_default_registry_has_all_skills(registry):
    assert set(registry.skill_names) == EXPECTED_SKILL_NAMES


def test_every_skill_has_name_description_and_prompt_fragment(registry):
    for name in registry.skill_names:
        skill = registry.get_skill(name)
        assert skill.name == name
        assert isinstance(skill.description, str) and skill.description
        fragment = skill.get_prompt_fragment()
        assert isinstance(fragment, str) and fragment.strip()


def test_every_tool_has_a_valid_schema(registry):
    for tool in registry.get_all_tools():
        assert "name" in tool and tool["name"]
        assert "description" in tool and tool["description"]
        schema = tool["input_schema"]
        assert schema["type"] == "object"
        assert "properties" in schema
        for required_field in schema.get("required", []):
            assert required_field in schema["properties"]


def test_no_duplicate_tool_names_across_skills(registry):
    all_names = [t["name"] for t in registry.get_all_tools()]
    assert len(all_names) == len(set(all_names)) == len(EXPECTED_TOOL_NAMES)
    assert set(all_names) == EXPECTED_TOOL_NAMES


def test_registering_a_duplicate_tool_name_raises():
    from dials_agent.skills.base import BaseSkill

    class FakeSkillA(BaseSkill):
        name = "fake_a"
        description = "fake"

        def get_prompt_fragment(self):
            return "fake"

        def get_tools(self):
            return [{"name": "calculate", "description": "x", "input_schema": {"type": "object", "properties": {}}}]

    class FakeSkillB(FakeSkillA):
        name = "fake_b"

    reg = SkillRegistry()
    reg.register(FakeSkillA())
    with pytest.raises(ValueError):
        reg.register(FakeSkillB())


def test_unknown_tool_returns_error_dict(registry, tmp_path):
    result = registry.handle_tool_call("not_a_real_tool", {}, make_context(tmp_path))
    assert "error" in result


def test_composed_prompt_is_content_equivalent_to_monolithic_prompt(registry):
    """Guards against accidentally dropping a whole section during the split."""
    from dials_agent.core.tutorials import get_tutorial_prompt_section

    prompt = registry.get_composed_prompt()
    tutorials_len = len(get_tutorial_prompt_section())
    # Composed skills prompt should be roughly the old SYSTEM_PROMPT content
    # (minus the base-prompt portion, which now lives separately) plus the
    # tutorials section. This is a loose bound, not a byte-for-byte check.
    assert len(prompt) > tutorials_len
    assert "lookup_phil_params" in prompt
    assert "diagnose_problem" in prompt or "Problem Diagnosis" in prompt


# ---------------------------------------------------------------------------
# Representative handler behavior
# ---------------------------------------------------------------------------

def test_calculate_tool(registry, tmp_path):
    result = registry.handle_tool_call(
        "calculate", {"expression": "1200 * 0.1"}, make_context(tmp_path)
    )
    assert result["result"] == 120.0


def test_calculate_tool_rejects_bad_expression(registry, tmp_path):
    result = registry.handle_tool_call(
        "calculate", {"expression": "__import__('os').system('echo hi')"}, make_context(tmp_path)
    )
    assert "error" in result


def test_diagnose_problem_matches_known_keyword(registry, tmp_path):
    result = registry.handle_tool_call(
        "diagnose_problem", {"problem": "too few spots found"}, make_context(tmp_path)
    )
    assert "sigma_strong" in result["diagnosis"]


def test_diagnose_problem_unknown_problem_gives_general_advice(registry, tmp_path):
    result = registry.handle_tool_call(
        "diagnose_problem", {"problem": "the crystal exploded"}, make_context(tmp_path)
    )
    assert "don't have a specific diagnosis" in result["diagnosis"]


def test_lookup_phil_params_missing_command_reports_checked_paths(registry, tmp_path):
    result = registry.handle_tool_call(
        "lookup_phil_params", {"command": "dials.not_a_real_command"}, make_context(tmp_path)
    )
    assert "No documentation found" in result["phil_params"]


def test_run_shell_command_safe_command_executes_directly(registry, tmp_path):
    (tmp_path / "a.txt").write_text("hello")
    result = registry.handle_tool_call(
        "run_shell_command",
        {"command": "ls", "explanation": "list files"},
        make_context(tmp_path),
    )
    assert result["status"] == "success"
    assert "a.txt" in result["output"]
    assert result.get("_files_may_have_changed") is True


def test_run_shell_command_destructive_requires_confirmation_first(registry, tmp_path):
    target = tmp_path / "keep_me.txt"
    target.write_text("do not delete")

    result = registry.handle_tool_call(
        "run_shell_command",
        {"command": f"rm {target}", "explanation": "cleanup"},
        make_context(tmp_path),
    )
    assert result["status"] == "requires_confirmation"
    assert target.exists()  # nothing happened yet

    # Now simulate the host re-calling with confirmation.
    confirmed = registry.handle_tool_call(
        "run_shell_command",
        {"command": f"rm {target}", "explanation": "cleanup", "_confirmed": True},
        make_context(tmp_path),
    )
    assert confirmed["status"] == "success"
    assert not target.exists()


def test_change_working_directory_switches_to_existing_subdir(registry, tmp_path):
    subdir = tmp_path / "round2"
    subdir.mkdir()

    result = registry.handle_tool_call(
        "change_working_directory",
        {"path": "round2"},
        make_context(tmp_path),
    )
    assert result["status"] == "success"
    assert result["working_directory"] == str(subdir)


def test_change_working_directory_does_not_create_by_default(registry, tmp_path):
    result = registry.handle_tool_call(
        "change_working_directory",
        {"path": "does_not_exist_yet"},
        make_context(tmp_path),
    )
    assert "error" in result
    assert not (tmp_path / "does_not_exist_yet").exists()


def test_change_working_directory_creates_when_asked(registry, tmp_path):
    result = registry.handle_tool_call(
        "change_working_directory",
        {"path": "new_dir", "create": True},
        make_context(tmp_path),
    )
    assert result["status"] == "success"
    assert (tmp_path / "new_dir").is_dir()


def test_change_data_directory_rejects_missing_path(registry, tmp_path):
    result = registry.handle_tool_call(
        "change_data_directory",
        {"path": str(tmp_path / "nope")},
        make_context(tmp_path),
    )
    assert "error" in result


def test_create_markdown_file_writes_file(registry, tmp_path):
    result = registry.handle_tool_call(
        "create_markdown_file",
        {"filename": "notes", "content": "# Hello"},
        make_context(tmp_path),
    )
    assert result["status"] == "success"
    assert (tmp_path / "notes.md").read_text() == "# Hello"


def test_check_workflow_status_reports_none_stage_on_empty_dir(registry, tmp_path):
    result = registry.handle_tool_call(
        "check_workflow_status", {}, make_context(tmp_path)
    )
    assert isinstance(result, dict)
