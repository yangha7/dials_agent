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
from dials_agent.core.claude_client import ToolCall, AgentResponse


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
    assert len(agent.claude.tools) == 20
    tool_names = {t["name"] for t in agent.claude.tools}
    assert "suggest_dials_command" in tool_names  # base tool
    assert "calculate" in tool_names  # skill tool
    assert "load_skill" in tool_names  # progressive-disclosure tool
    assert len(agent.claude.registry.skill_names) == 12


def test_agent_forwards_its_settings_to_the_claude_client(tmp_path):
    """Regression test: DIALSAgent(settings=...) must reach ClaudeClient.

    Previously create_client() silently ignored the settings passed into
    DIALSAgent, so the LLM client always fell back to the global env-based
    settings regardless of what was explicitly configured.
    """
    settings = Settings(
        llm_provider="anthropic",
        anthropic_api_key="sk-dummy-test-key",
        cborg_api_key="", openai_api_key="", gemini_api_key="",
        token_budget=42,
    )
    agent = DIALSAgent(working_directory=str(tmp_path), settings=settings)

    assert agent.claude.settings is agent.settings
    assert agent.claude.provider == "anthropic"
    assert agent.claude.api_type == "anthropic"
    assert agent.claude.settings.token_budget == 42


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


def test_second_suggest_dials_command_while_one_pending_is_rejected_not_silently_overwritten(agent):
    # Regression test for a real bug found live-testing: the LLM sometimes calls
    # suggest_dials_command twice in one turn. pending_command is a single field, not a
    # queue, so the second call used to silently clobber the first -- the CLI would only
    # ever confirm/run the second command, while the LLM (having gotten a
    # "pending_approval" ack for the first call too) kept believing both were still
    # awaiting approval on later turns, producing a repeating "still pending on my end"
    # loop. The second call must now be rejected with a clear error instead.
    first = agent._handle_tool_call(ToolCall(
        id="1", name="suggest_dials_command",
        input={"command": "dials.index imported.expt strong.refl", "explanation": "index", "expected_output": "indexed.expt"},
    ))
    assert first["status"] == "pending_approval"

    second = agent._handle_tool_call(ToolCall(
        id="2", name="suggest_dials_command",
        input={"command": "dials.refine indexed.expt indexed.refl", "explanation": "refine", "expected_output": "refined.expt"},
    ))
    assert second["status"] == "error"
    assert "already pending" in second["message"]
    assert "dials.index imported.expt strong.refl" in second["message"]

    # The first command must survive untouched -- not silently overwritten by the second.
    assert agent.pending_command["command"] == "dials.index imported.expt strong.refl"


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


def test_get_token_usage_through_full_wrapper_reflects_live_session_usage(agent):
    # Starts at zero.
    result = agent._handle_tool_call(ToolCall(id="1", name="get_token_usage", input={}))
    assert result["session_total_tokens"] == 0
    assert result["token_budget"] == 0

    # Simulate usage having accumulated from real turns, and confirm the
    # tool reflects it live (it reads agent.claude.session_usage fresh on
    # every call, not a snapshot taken at agent-construction time).
    agent.claude.session_usage.input_tokens = 1200
    agent.claude.session_usage.output_tokens = 300

    result = agent._handle_tool_call(ToolCall(id="1", name="get_token_usage", input={}))
    assert result["session_total_tokens"] == 1500


def test_check_workflow_status_through_full_wrapper(agent):
    result = agent._handle_tool_call(ToolCall(id="1", name="check_workflow_status", input={}))
    assert result["stage_name"] == "none" or "stage_name" in result


def test_load_skill_through_full_wrapper(agent):
    result = agent._handle_tool_call(ToolCall(
        id="1", name="load_skill", input={"skill_name": "troubleshooting"}
    ))
    assert result["skill"] == "troubleshooting"
    assert result["guidance"] == agent.claude.registry.get_skill("troubleshooting").get_prompt_fragment()


# ---------------------------------------------------------------------------
# display_workflow_status shows both directories and the CLI reports its
# own version -- regression tests for a real gap a user noticed: the
# startup "welcome" table only had Working Directory, no Data Directory,
# and the agent's own version was never displayed anywhere.
# ---------------------------------------------------------------------------

def test_workflow_status_table_shows_data_directory(tmp_path, capsys):
    settings = Settings(
        llm_provider="anthropic",
        anthropic_api_key="sk-dummy-test-key",
        cborg_api_key="", openai_api_key="", gemini_api_key="",
        data_directory="/some/shared/data/",
    )
    agent = DIALSAgent(working_directory=str(tmp_path), settings=settings)
    agent.display_workflow_status()
    out = capsys.readouterr().out
    assert "Data Directory" in out
    assert "/some/shared/data/" in out


def test_workflow_status_table_handles_unset_data_directory(tmp_path, capsys):
    settings = Settings(
        llm_provider="anthropic",
        anthropic_api_key="sk-dummy-test-key",
        cborg_api_key="", openai_api_key="", gemini_api_key="",
        data_directory="",
    )
    agent = DIALSAgent(working_directory=str(tmp_path), settings=settings)
    agent.display_workflow_status()
    out = capsys.readouterr().out
    assert "Data Directory" in out
    assert "(not configured)" in out


# ---------------------------------------------------------------------------
# Truncated (MAX_TOKENS-cut-off) responses get surfaced, not silently dropped.
# Regression tests for a real bug found live: a long, context-heavy turn hit
# the output token limit with no visible text and no tool call in the final
# round -- response.stop_reason was captured on every response but never
# actually checked anywhere, so the turn silently produced nothing (no
# "Agent" header, no text) despite a full-price, maximum-length API call
# having just run (visible only as output_tokens == the configured MAX_TOKENS
# in the token-usage line).
# ---------------------------------------------------------------------------

def test_truncated_empty_response_shows_loud_warning(agent, capsys):
    response = AgentResponse(message="", tool_calls=[], stop_reason="length")
    agent._warn_if_response_truncated(response)
    out = capsys.readouterr().out
    assert "cut off" in out
    assert "no output" in out.lower()
    assert "MAX_TOKENS" in out


def test_truncated_but_nonempty_response_shows_soft_note(agent, capsys):
    response = AgentResponse(message="Partial analysis before it got cut off...", tool_calls=[], stop_reason="length")
    agent._warn_if_response_truncated(response)
    out = capsys.readouterr().out
    assert "cut off" in out
    assert "may be incomplete" in out


def test_truncated_with_tool_call_but_no_text_shows_soft_note_not_loud_error(agent, capsys):
    # A truncated round that still produced a tool call isn't the "silent
    # nothing" failure mode -- something did happen -- so it gets the lighter note.
    response = AgentResponse(
        message="",
        tool_calls=[ToolCall(id="1", name="suggest_dials_command", input={"command": "dials.refine ..."})],
        stop_reason="length",
    )
    agent._warn_if_response_truncated(response)
    out = capsys.readouterr().out
    assert "cut off" in out
    assert "no output" not in out.lower()


def test_anthropic_native_max_tokens_stop_reason_also_detected(agent, capsys):
    # Native Anthropic API uses "max_tokens" where OpenAI-compatible providers use "length".
    response = AgentResponse(message="", tool_calls=[], stop_reason="max_tokens")
    agent._warn_if_response_truncated(response)
    out = capsys.readouterr().out
    assert "cut off" in out


def test_normal_completed_response_shows_no_warning(agent, capsys):
    response = AgentResponse(message="Here's my analysis...", tool_calls=[], stop_reason="end_turn")
    agent._warn_if_response_truncated(response)
    out = capsys.readouterr().out
    assert out == ""


def test_cli_module_version_matches_package_version():
    import dials_agent
    from dials_agent import cli
    assert cli.__version__ == dials_agent.__version__
    assert cli.__version__  # non-empty


# ---------------------------------------------------------------------------
# Command display in the timing summary / history tables -- regression
# tests for a real bug a user noticed: a blind `command[:60]` slice with no
# ellipsis silently dropped everything past character 60, so e.g. every
# `dials.python /long/path/to/<script>.py ...` invocation looked identical
# and unreadable, hiding which numeric check ran on which files.
# ---------------------------------------------------------------------------

class TestDisplayCommandLabel:
    def test_shortens_dials_python_script_path_to_basename(self):
        label = DIALSAgent._display_command_label(
            "dials.python /shared/home/yangha/workshop_dials_agent/dials_agent/"
            "dials/scripts/reciprocal_lattice_linearity.py indexed.expt indexed.refl"
        )
        assert label == "dials.python reciprocal_lattice_linearity.py indexed.expt indexed.refl"

    def test_shortens_cctbx_python_and_libtbx_python_too(self):
        for interpreter in ("cctbx.python", "libtbx.python"):
            label = DIALSAgent._display_command_label(f"{interpreter} /abs/path/to/script.py a.expt b.refl")
            assert label == f"{interpreter} script.py a.expt b.refl"

    def test_script_with_no_arguments(self):
        label = DIALSAgent._display_command_label("dials.python /abs/path/to/script.py")
        assert label == "dials.python script.py"

    def test_ordinary_dials_command_is_unchanged(self):
        cmd = "dials.import /shared/data/projects/yangha/DPF3/x247398/t1.*.img.bz2"
        assert DIALSAgent._display_command_label(cmd) == cmd

    def test_non_python_script_argument_is_unchanged(self):
        # Only shorten when it actually looks like <interpreter> <script>.py
        cmd = "dials.find_spots imported.expt nproc=Auto"
        assert DIALSAgent._display_command_label(cmd) == cmd


def test_timing_summary_never_truncates_long_commands(agent, capsys):
    long_command = (
        "dials.python /shared/home/yangha/workshop_dials_agent/dials_agent/"
        "dials/scripts/centring_vs_pseudocentring_check.py integrated.expt integrated.refl"
    )
    agent.command_timings.append({"command": long_command, "success": True, "duration": 14.8})
    agent.display_timing_summary()
    # Rich wraps across lines and strips the newline, so check the actual
    # words survive somewhere in the output rather than as one substring.
    out = capsys.readouterr().out
    assert "centring_vs_pseudocentring_check.py" in out
    assert "integrated.expt" in out
    assert "integrated.refl" in out
    # And the old bug's symptom is gone: the un-shortened absolute path
    # should NOT appear (it's been reduced to the basename).
    assert "workshop_dials_agent" not in out


# ---------------------------------------------------------------------------
# run_interactive: a chained pending_command must survive the current one's
# result-analysis step, not get silently wiped.
#
# Real bug found live: run_interactive's "if self.pending_command:" block ran
# the newly-approved command, then fed its output back to the LLM via a
# NESTED self.chat() call for analysis. If that analysis itself proactively
# called suggest_dials_command for the next step (exactly what the agent is
# generally encouraged to do), self.pending_command got set to the new
# suggestion -- and then unconditionally overwritten back to None right
# after the block, regardless of what the nested call had just set. The
# user saw the agent's text ("ready to run when you are") with no actual
# command queued to approve, and typing "y" just went to the LLM as an
# ordinary chat message instead of a confirmation, since nothing was
# actually pending. Fixed by consuming (clearing) the command immediately
# before acting on it, so a freshly re-set one survives to the next
# `while self.pending_command:` check instead of being wiped afterward.
# ---------------------------------------------------------------------------

def test_run_interactive_picks_up_command_chained_during_result_analysis(tmp_path, capsys):
    from dials_agent.dials.executor import CommandResult

    agent = make_agent(tmp_path)

    find_spots_result = CommandResult(
        command="dials.find_spots imported.expt nproc=Auto",
        return_code=0, stdout="56403 spots found\n", stderr="",
        duration=12.3, success=True,
        working_directory=str(agent.working_directory),
        output_files=["strong.refl"],
    )
    index_result = CommandResult(
        command="dials.index imported.expt strong.refl",
        return_code=0, stdout="Indexing...\n95% indexed\n", stderr="",
        duration=8.0, success=True,
        working_directory=str(agent.working_directory),
        output_files=["indexed.expt", "indexed.refl"],
    )

    def fake_execute(command_str, **kwargs):
        (agent.working_directory / "strong.refl").touch()
        (agent.working_directory / "indexed.expt").touch()
        (agent.working_directory / "indexed.refl").touch()
        return find_spots_result if "find_spots" in command_str else index_result

    chat_calls = {"n": 0}

    def fake_chat(message):
        chat_calls["n"] += 1
        if chat_calls["n"] == 1:
            # Initial user message -> LLM suggests find_spots.
            agent.pending_command = {
                "command": "dials.find_spots imported.expt nproc=Auto",
                "explanation": "find spots", "expected_output": "strong.refl",
            }
            return "Suggesting spot finding."
        elif chat_calls["n"] == 2:
            # Analysis of find_spots' result -> LLM chains straight into
            # suggesting dials.index, exactly the scenario that got dropped.
            agent.pending_command = {
                "command": "dials.index imported.expt strong.refl",
                "explanation": "index", "expected_output": "indexed.expt",
            }
            return "Found 56403 spots. Suggesting indexing next."
        else:
            # Analysis of dials.index's result -> nothing further to chain.
            return "Indexing looks good."

    with patch.object(agent.executor, "execute", side_effect=fake_execute), \
         patch.object(agent, "chat", side_effect=fake_chat), \
         patch("dials_agent.cli.Confirm.ask", return_value=True), \
         patch("builtins.input", side_effect=["please process my data", "quit"]):
        agent.run_interactive()

    out = capsys.readouterr().out
    # Both commands must have actually been suggested/displayed and executed --
    # not just the first one, with the second silently dropped.
    assert "dials.find_spots imported.expt nproc=Auto" in out
    assert "dials.index imported.expt strong.refl" in out
    assert chat_calls["n"] == 3
    assert agent.pending_command is None


# ---------------------------------------------------------------------------
# _confirm_command_to_run: structural safeguard for "quick subset vs full
# dataset" on the first dials.import of a fresh dataset.
#
# Real failure this exists to fix: pure prompt wording (base prompt +
# data_import/SKILL.md, both saying to ask and wait before suggesting a
# command) was skipped by the LLM three separate times live, each producing
# a straight-to-full-dataset suggestion with no choice offered at all.
# Enforcing the choice at the actual approval gate doesn't depend on the
# LLM's text having asked anything.
# ---------------------------------------------------------------------------

class TestConfirmCommandToRun:
    def test_fresh_import_choice_1_runs_full_dataset_unchanged(self, tmp_path):
        agent = make_agent(tmp_path)
        with patch("dials_agent.cli.Prompt.ask", return_value="1") as mock_prompt:
            proceed, command = agent._confirm_command_to_run("dials.import data/*.h5")
        assert mock_prompt.called
        assert proceed is True
        assert command == "dials.import data/*.h5"

    def test_fresh_import_choice_2_appends_image_range(self, tmp_path):
        agent = make_agent(tmp_path)
        with patch("dials_agent.cli.Prompt.ask", return_value="2"):
            proceed, command = agent._confirm_command_to_run("dials.import data/*.h5")
        assert proceed is True
        assert command == "dials.import data/*.h5 image_range=1,1200"

    def test_fresh_import_choice_n_declines(self, tmp_path):
        agent = make_agent(tmp_path)
        with patch("dials_agent.cli.Prompt.ask", return_value="n"):
            proceed, command = agent._confirm_command_to_run("dials.import data/*.h5")
        assert proceed is False
        assert command == "dials.import data/*.h5"

    def test_import_with_image_range_already_set_uses_plain_confirm(self, tmp_path):
        # The LLM already chose a subset itself (e.g. user asked for one
        # explicitly) -- nothing to structurally enforce, plain y/n is fine.
        agent = make_agent(tmp_path)
        with patch("dials_agent.cli.Confirm.ask", return_value=True) as mock_confirm, \
             patch("dials_agent.cli.Prompt.ask") as mock_prompt:
            proceed, command = agent._confirm_command_to_run("dials.import data/*.h5 image_range=1,50")
        assert mock_confirm.called
        assert not mock_prompt.called
        assert proceed is True
        assert command == "dials.import data/*.h5 image_range=1,50"

    def test_reimport_after_imported_expt_exists_uses_plain_confirm(self, tmp_path):
        # Not a "fresh" import (e.g. re-importing/switching datasets after
        # already having one) -- don't force the choice a second time.
        agent = make_agent(tmp_path)
        (agent.working_directory / "imported.expt").touch()
        with patch("dials_agent.cli.Confirm.ask", return_value=True) as mock_confirm, \
             patch("dials_agent.cli.Prompt.ask") as mock_prompt:
            proceed, command = agent._confirm_command_to_run("dials.import data/*.h5")
        assert mock_confirm.called
        assert not mock_prompt.called
        assert proceed is True

    def test_unrelated_command_uses_plain_confirm(self, tmp_path):
        agent = make_agent(tmp_path)
        with patch("dials_agent.cli.Confirm.ask", return_value=True) as mock_confirm, \
             patch("dials_agent.cli.Prompt.ask") as mock_prompt:
            proceed, command = agent._confirm_command_to_run("dials.find_spots imported.expt nproc=Auto")
        assert mock_confirm.called
        assert not mock_prompt.called
        assert proceed is True
