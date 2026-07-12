"""
Tests for the DIALSAgent tool-dispatch wrapper in cli.py.

test_skills.py exercises the SkillRegistry and skill handlers directly.
This file covers the layer on top of that: DIALSAgent._handle_tool_call,
which handles the three base tools itself, and otherwise dispatches to
the registry while applying host-side effects (updating the live working
directory/workflow/executor, printing `_cli_print` messages, running the
destructive-shell-command confirmation round-trip, and stripping
host-only keys before a result is sent to the LLM).

No real LLM API calls are made — ClaudeClient's __init__ only constructs
the SDK client objects, it doesn't hit the network, so a dummy API key
is enough to build a DIALSAgent for these tests.
"""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dials_agent.cli import DIALSAgent
from dials_agent.config import Settings
from dials_agent.core.claude_client import ToolCall


def make_agent(working_directory: Path) -> DIALSAgent:
    # Force the provider/key explicitly so this doesn't depend on (or read)
    # whatever is in the real .env file — deterministic and no real secrets.
    settings = Settings(
        llm_provider="anthropic",
        anthropic_api_key="sk-dummy-test-key",
        cborg_api_key="",
        openai_api_key="",
        gemini_api_key="",
    )
    return DIALSAgent(working_directory=str(working_directory), settings=settings)


@pytest.fixture
def agent(tmp_path) -> DIALSAgent:
    return make_agent(tmp_path)


# ---------------------------------------------------------------------------
# Agent construction wires the registry correctly
# ---------------------------------------------------------------------------

def test_agent_wires_all_skills_and_tools(agent):
    assert len(agent.claude.tools) == 17
    tool_names = {t["name"] for t in agent.claude.tools}
    assert "suggest_dials_command" in tool_names  # base tool
    assert "calculate" in tool_names  # skill tool
    assert len(agent.claude.registry.skill_names) == 12


# ---------------------------------------------------------------------------
# Base tools (handled directly by DIALSAgent, not the registry)
# ---------------------------------------------------------------------------

def test_suggest_dials_command_sets_pending_command(agent):
    result = agent._handle_tool_call(ToolCall(
        id="1", name="suggest_dials_command",
        input={"command": "dials.import foo.nxs", "explanation": "import", "expected_output": "imported.expt"},
    ))
    assert result["status"] == "pending_approval"
    assert agent.pending_command["command"] == "dials.import foo.nxs"


def test_explain_dials_concept(agent):
    result = agent._handle_tool_call(ToolCall(
        id="1", name="explain_dials_concept", input={"concept": "unit cell"}
    ))
    assert result == {"status": "explanation_requested", "concept": "unit cell"}


def test_analyze_dials_output(agent):
    result = agent._handle_tool_call(ToolCall(
        id="1", name="analyze_dials_output",
        input={"command": "dials.index", "output": "some log text", "return_code": 0},
    ))
    assert set(result.keys()) == {"summary", "metrics", "warnings", "suggestions"}


def test_unknown_tool_returns_error(agent):
    result = agent._handle_tool_call(ToolCall(id="1", name="not_a_real_tool", input={}))
    assert "error" in result


# ---------------------------------------------------------------------------
# _cli_print / host-key stripping
# ---------------------------------------------------------------------------

def test_cli_print_is_printed_and_stripped_from_llm_result(agent, capsys):
    result = agent._handle_tool_call(ToolCall(
        id="1", name="create_markdown_file",
        input={"filename": "notes", "content": "# hi"},
    ))
    captured = capsys.readouterr()
    assert "Created notes.md" in captured.out
    assert "_cli_print" not in result
    assert result["status"] == "success"


def test_no_host_only_keys_leak_to_llm_for_run_shell_command(agent):
    result = agent._handle_tool_call(ToolCall(
        id="1", name="run_shell_command",
        input={"command": "ls", "explanation": "list files"},
    ))
    assert not any(k.startswith("_") for k in result)
    assert result["status"] == "success"


# ---------------------------------------------------------------------------
# Destructive shell command confirmation round-trip
# ---------------------------------------------------------------------------

def test_destructive_command_confirmed_executes_and_deletes(agent, tmp_path):
    target = tmp_path / "delete_me.txt"
    target.write_text("bye")

    with patch("dials_agent.cli.Confirm.ask", return_value=True) as mock_confirm:
        result = agent._handle_tool_call(ToolCall(
            id="1", name="run_shell_command",
            input={"command": f"rm {target}", "explanation": "cleanup"},
        ))

    assert mock_confirm.called
    assert result["status"] == "success"
    assert not target.exists()


def test_destructive_command_declined_leaves_file_untouched(agent, tmp_path):
    target = tmp_path / "keep_me.txt"
    target.write_text("still here")

    with patch("dials_agent.cli.Confirm.ask", return_value=False) as mock_confirm:
        result = agent._handle_tool_call(ToolCall(
            id="1", name="run_shell_command",
            input={"command": f"rm {target}", "explanation": "cleanup"},
        ))

    assert mock_confirm.called
    assert result["status"] == "cancelled"
    assert target.exists()


def test_safe_command_does_not_prompt_for_confirmation(agent):
    with patch("dials_agent.cli.Confirm.ask") as mock_confirm:
        result = agent._handle_tool_call(ToolCall(
            id="1", name="run_shell_command",
            input={"command": "ls", "explanation": "list files"},
        ))

    assert not mock_confirm.called
    assert result["status"] == "success"


# ---------------------------------------------------------------------------
# Host-state mutation: change_working_directory / change_data_directory
# ---------------------------------------------------------------------------

def test_change_working_directory_updates_live_agent_state(agent, tmp_path):
    subdir = tmp_path / "round2"
    subdir.mkdir()

    result = agent._handle_tool_call(ToolCall(
        id="1", name="change_working_directory", input={"path": "round2"}
    ))

    assert result["status"] == "success"
    assert agent.working_directory == subdir.resolve()
    assert agent.workflow.working_directory == subdir.resolve()
    assert agent.executor is not None
    assert agent.claude.working_directory == str(subdir.resolve())
    assert subdir.resolve() in agent.used_directories


def test_change_working_directory_create_flag_makes_new_dir(agent, tmp_path):
    result = agent._handle_tool_call(ToolCall(
        id="1", name="change_working_directory", input={"path": "brand_new", "create": True}
    ))
    assert result["status"] == "success"
    assert (tmp_path / "brand_new").is_dir()
    assert agent.working_directory == (tmp_path / "brand_new").resolve()


def test_change_working_directory_missing_dir_no_create_leaves_agent_unchanged(agent, tmp_path):
    original = agent.working_directory
    result = agent._handle_tool_call(ToolCall(
        id="1", name="change_working_directory", input={"path": "nope"}
    ))
    assert "error" in result
    assert agent.working_directory == original


def test_change_data_directory_updates_settings(agent, tmp_path):
    data_dir = tmp_path / "raw_data"
    data_dir.mkdir()

    result = agent._handle_tool_call(ToolCall(
        id="1", name="change_data_directory", input={"path": str(data_dir)}
    ))

    assert result["status"] == "success"
    assert agent.settings.data_directory == str(data_dir)


def test_change_data_directory_missing_path_does_not_update_settings(agent, tmp_path):
    original = agent.settings.data_directory
    result = agent._handle_tool_call(ToolCall(
        id="1", name="change_data_directory", input={"path": str(tmp_path / "missing")}
    ))
    assert "error" in result
    assert agent.settings.data_directory == original


# ---------------------------------------------------------------------------
# Representative skill tools through the full wrapper
# ---------------------------------------------------------------------------

def test_diagnose_problem_through_full_wrapper(agent):
    result = agent._handle_tool_call(ToolCall(
        id="1", name="diagnose_problem", input={"problem": "high rmerge"}
    ))
    assert "absorption" in result["diagnosis"].lower()


def test_get_timing_report_through_full_wrapper(agent):
    result = agent._handle_tool_call(ToolCall(id="1", name="get_timing_report", input={}))
    assert "No commands have been executed yet." in result["timing_report"]


def test_check_workflow_status_through_full_wrapper(agent):
    result = agent._handle_tool_call(ToolCall(id="1", name="check_workflow_status", input={}))
    assert result["stage_name"] == "none" or "stage_name" in result
