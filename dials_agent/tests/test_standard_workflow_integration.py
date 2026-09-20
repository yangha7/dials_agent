"""
End-to-end integration test for a standard, successful DIALS workflow --
import through merge -- driving the REAL display/execution/workflow-tracking
code (not just isolated unit tests of individual functions).

No real DIALS install or LLM API calls are involved: `CommandExecutor.execute`
is mocked to return realistic CommandResult objects and create the expected
output files (so WorkflowManager's real, file-based stage detection runs for
real), while everything downstream of that -- execute_command, display_result,
display_command_suggestion, display_timing_summary, display_workflow_status,
the pending_command approval flow, and the geometry/centring numeric checks'
dials.python invocations -- runs exactly as it would in a live session.

This exists to catch exactly the class of bug found live-testing recently:
things that only show up when you look at the actual rendered text across a
full run (silent truncation, confusing duplicate state) rather than testing
each function in isolation.
"""
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dials_agent.cli import DIALSAgent
from dials_agent.config import Settings
from dials_agent.core.claude_client import ToolCall
from dials_agent.dials.executor import CommandResult


def make_agent(working_directory: Path, data_directory: str = "/shared/data/example") -> DIALSAgent:
    settings = Settings(
        llm_provider="anthropic",
        anthropic_api_key="sk-dummy-test-key",
        cborg_api_key="", openai_api_key="", gemini_api_key="",
        data_directory=data_directory,
    )
    return DIALSAgent(working_directory=str(working_directory), settings=settings)


# A standard, successful pipeline: (command, files_to_create, stdout, output_files).
# Mirrors a real run's shape, including all three numeric checks invoked exactly the
# way the base prompt tells the LLM to invoke them (via dials.python with an absolute
# script path) at the points they're meant to run (after import, after index, after
# refine, after integrate) -- this is the main thing worth exercising end-to-end, since
# that's precisely the display path the truncation bug hid in.
SCRIPT_DIR = "/shared/home/yangha/workshop_dials_agent/dials_agent/dials/scripts"

STANDARD_WORKFLOW = [
    (
        "dials.import /shared/data/example/insulin_*.cbf",
        ["imported.expt"],
        "Importing data...\nAutomatically determined image format.\n",
        ["imported.expt"],
    ),
    (
        f"dials.python {SCRIPT_DIR}/import_geometry_check.py imported.expt",
        [],
        '{"n_experiments": 1, "experiments": {"0": {"summary": "Geometry looks sane: beam centre on-detector, wavelength/distance/oscillation all within normal ranges."}}}\n',
        [],
    ),
    (
        "dials.find_spots imported.expt nproc=Auto",
        ["strong.refl"],
        "Setting spotfinding threshold...\n108393 spots found on 400 images\nSaved 108393 reflections to strong.refl\n",
        ["strong.refl"],
    ),
    (
        "dials.index imported.expt strong.refl",
        ["indexed.expt", "indexed.refl"],
        "Indexing...\n95.2% of spots indexed\nRMSDs: 0.31, 0.30 px\nModel 1 (0.312 mm sd, 0.301 mm sd)\n",
        ["indexed.expt", "indexed.refl"],
    ),
    (
        f"dials.python {SCRIPT_DIR}/reciprocal_lattice_linearity.py indexed.expt indexed.refl",
        [],
        '{"n_crystals": 1, "crystals": {"0": {"summary": {"n_rows": 203, "fraction_rows_flagged_nonlinear": 0.01}, "verdict": "Reciprocal lattice rows are straight and consistent -- no evidence of a geometry-modelling problem."}}}\n',
        [],
    ),
    (
        "dials.refine indexed.expt indexed.refl",
        ["refined.expt", "refined.refl"],
        "Refining...\nRMSDs decreased: 0.31 -> 0.18 px\n",
        ["refined.expt", "refined.refl"],
    ),
    (
        f"dials.python {SCRIPT_DIR}/reciprocal_lattice_linearity.py refined.expt refined.refl",
        [],
        '{"n_crystals": 1, "crystals": {"0": {"summary": {"n_rows": 203, "fraction_rows_flagged_nonlinear": 0.0}, "verdict": "Reciprocal lattice rows are straight and consistent -- no evidence of a geometry-modelling problem."}}}\n',
        [],
    ),
    (
        "dials.integrate refined.expt refined.refl nproc=Auto",
        ["integrated.expt", "integrated.refl"],
        "Integrating...\nIntegrated 62006 reflections\n",
        ["integrated.expt", "integrated.refl"],
    ),
    (
        f"dials.python {SCRIPT_DIR}/centring_vs_pseudocentring_check.py integrated.expt integrated.refl",
        [],
        '{"n_crystals": 1, "crystals": {"0": {"verdict": "No systematic strong/weak intensity alternation detected along any axis -- no evidence of hidden translational pseudo-symmetry."}}}\n',
        [],
    ),
    (
        "dials.symmetry integrated.expt integrated.refl",
        ["symmetrized.expt", "symmetrized.refl"],
        "Best solution: P 21 21 21\n",
        ["symmetrized.expt", "symmetrized.refl"],
    ),
    (
        "dials.scale symmetrized.expt symmetrized.refl",
        ["scaled.expt", "scaled.refl"],
        "Scaling successful.\nCompleteness: 99.8%; Multiplicity: 6.4\n",
        ["scaled.expt", "scaled.refl", "dials.scale.html"],
    ),
    (
        "dials.merge scaled.expt scaled.refl d_min=1.8",
        ["merged.mtz"],
        "Merging successful.\nOverall CC1/2: 0.998\n",
        ["merged.mtz"],
    ),
]


def make_mock_executor(agent):
    """A fake CommandExecutor.execute that creates the right output files
    (so WorkflowManager's real file-based stage detection runs for real) and
    returns a matching, realistic CommandResult -- no subprocess, no real DIALS."""
    by_command = {cmd: (files, stdout, outputs) for cmd, files, stdout, outputs in STANDARD_WORKFLOW}

    def _execute(command_str, timeout=None, capture_output=True, progress_callback=None):
        files, stdout, output_files = by_command[command_str]
        for fname in files:
            (agent.working_directory / fname).touch()
        return CommandResult(
            command=command_str,
            return_code=0,
            stdout=stdout,
            stderr="",
            duration=12.3,
            success=True,
            working_directory=str(agent.working_directory),
            output_files=output_files,
        )
    return _execute


class TestStandardWorkflowIntegration:
    def test_full_pipeline_runs_and_reaches_completion(self, tmp_path, capsys):
        agent = make_agent(tmp_path)
        with patch.object(agent.executor, "execute", side_effect=make_mock_executor(agent)):
            for command, _files, _stdout, _outputs in STANDARD_WORKFLOW:
                agent.execute_command(command)

        agent.workflow.refresh()
        assert agent.workflow.is_complete()
        assert agent.workflow.get_stage_name() == "Data exported"
        assert agent.workflow.get_progress_percentage() == 100.0

        # Sanity: capturing output didn't raise, and something was printed for every step.
        out = capsys.readouterr().out
        assert out.count("Executing:") == len(STANDARD_WORKFLOW)

    def test_workflow_stage_progresses_correctly_after_each_step(self, tmp_path):
        agent = make_agent(tmp_path)
        expected_stage_after = [
            "Images imported", "Images imported",  # check doesn't advance stage
            "Spots found", "Data indexed", "Data indexed",  # check doesn't advance stage
            "Models refined", "Models refined", "Data integrated", "Data integrated",
            "Symmetry determined", "Data scaled", "Data exported",
        ]
        with patch.object(agent.executor, "execute", side_effect=make_mock_executor(agent)):
            for (command, *_), expected in zip(STANDARD_WORKFLOW, expected_stage_after):
                agent.execute_command(command)
                assert agent.workflow.get_stage_name() == expected, f"after {command}"

    def test_timing_summary_shows_every_step_fully_and_shortens_python_scripts(self, tmp_path, capsys):
        agent = make_agent(tmp_path)
        with patch.object(agent.executor, "execute", side_effect=make_mock_executor(agent)):
            for command, *_ in STANDARD_WORKFLOW:
                agent.execute_command(command)

        capsys.readouterr()  # discard per-step output
        agent.display_timing_summary()
        out = capsys.readouterr().out

        # Every ordinary command's full text should survive somewhere in the table.
        assert "dials.import" in out
        assert "insulin_*.cbf" in out  # not truncated off, unlike the pre-fix behavior
        assert "dials.merge scaled.expt scaled.refl d_min=1.8" in out

        # Both dials.python invocations must be distinguishable from each other --
        # this is the exact thing the old command[:60] truncation destroyed. Rich wraps
        # long cells across lines (overflow="fold"), so check the pieces survive rather
        # than one contiguous string spanning a line break.
        out_no_newlines = out.replace("\n", " ")
        assert "reciprocal_lattice_linearity.py" in out
        assert "indexed.expt indexed.refl" in out_no_newlines
        assert "refined.expt refined.refl" in out_no_newlines
        assert "centring_vs_pseudocentring_check.py" in out
        assert "integrated.expt integrated.refl" in out_no_newlines
        # And the absolute installation path should NOT appear -- it's shortened to the basename.
        assert SCRIPT_DIR not in out

        # Total row present and the 12-step total looks sane.
        assert "Total" in out

    def test_workflow_status_table_shows_version_data_dir_and_progress(self, tmp_path, capsys):
        agent = make_agent(tmp_path, data_directory="/shared/data/example")
        with patch.object(agent.executor, "execute", side_effect=make_mock_executor(agent)):
            for command, *_ in STANDARD_WORKFLOW[:4]:  # partway through: import, geometry check, find_spots, index
                agent.execute_command(command)

        capsys.readouterr()
        agent.display_workflow_status()
        out = capsys.readouterr().out
        assert "Data Directory" in out
        assert "/shared/data/example" in out
        assert "Working Directory" in out
        assert "Data indexed" in out
        # 3 completed stages (imported, spots_found, indexed) out of 8 steps in
        # STAGE_ORDER -> 3/8 = 37.5%, rounds to 38%. The geometry check in between
        # creates no files, so it doesn't add a stage of its own.
        assert "38%" in out

    def test_normal_single_suggestion_per_turn_flow_still_works_after_pending_command_fix(self, tmp_path):
        # Regression guard: the v2.7.0 fix that rejects a SECOND suggest_dials_command
        # while one is pending must not break the ordinary case -- suggest, approve/
        # execute, clear, suggest again for the next step.
        agent = make_agent(tmp_path)
        with patch.object(agent.executor, "execute", side_effect=make_mock_executor(agent)):
            for command, *_ in STANDARD_WORKFLOW[:4]:
                result = agent._handle_tool_call(ToolCall(
                    id="x", name="suggest_dials_command",
                    input={"command": command, "explanation": "e", "expected_output": "o"},
                ))
                assert result["status"] == "pending_approval"
                assert agent.pending_command["command"] == command

                agent.execute_command(agent.pending_command["command"])
                agent.pending_command = None  # what the real approval flow does once executed

        assert agent.workflow.get_stage_name() == "Data indexed"

    def test_executing_line_and_suggestion_panel_also_shorten_python_scripts(self, tmp_path, capsys):
        # Found by actually looking at the rendered output of a full run: the
        # per-command "Executing:" line and the pre-approval "Suggested Command"
        # panel were still printing the raw absolute script path (unlike the
        # summary tables, fixed in v2.5.3), and Rich's default text wrapping
        # breaks a long path with no spaces mid-word. Both should use the same
        # shortened label -- display-only, doesn't change what actually runs.
        agent = make_agent(tmp_path)
        long_command = f"dials.python {SCRIPT_DIR}/reciprocal_lattice_linearity.py indexed.expt indexed.refl"

        def normalize(text: str) -> str:
            # Collapse box-drawing borders/padding and line breaks so wrapped
            # text can be checked as one contiguous string regardless of
            # exactly where Rich chose to wrap it.
            for ch in "\n│╭╮╰╯─┏┓┗┛┃━┡┩":
                text = text.replace(ch, " ")
            return " ".join(text.split())

        capsys.readouterr()
        agent.display_command_suggestion({"command": long_command, "explanation": "e", "expected_output": "o"})
        panel_out = capsys.readouterr().out
        assert "reciprocal_lattice_linearity.py indexed.expt indexed.refl" in normalize(panel_out)
        assert SCRIPT_DIR not in panel_out

        with patch.object(agent.executor, "execute", side_effect=make_mock_executor(agent)):
            capsys.readouterr()
            agent.execute_command(long_command)
        exec_out = capsys.readouterr().out
        assert "reciprocal_lattice_linearity.py indexed.expt indexed.refl" in normalize(exec_out)
        assert SCRIPT_DIR not in exec_out
        # The real, full command must still be what's passed to the executor --
        # this is display-only shortening, not a change to what actually runs.
        assert agent.command_timings[-1]["command"] == long_command

    def test_workflow_complete_banner_shown_on_real_transition(self, tmp_path, capsys):
        # A command that genuinely finishes the workflow (creates the first .mtz)
        # should show the completion banner -- this is the case that matters.
        agent = make_agent(tmp_path)
        with patch.object(agent.executor, "execute", side_effect=make_mock_executor(agent)):
            for command, *_ in STANDARD_WORKFLOW[:-1]:
                agent.execute_command(command)
            capsys.readouterr()
            result = agent.execute_command(STANDARD_WORKFLOW[-1][0])  # dials.merge -> merged.mtz
            agent.display_result(result)
        assert "Workflow Complete" in capsys.readouterr().out

    def test_workflow_complete_banner_suppressed_when_already_complete_before_resuming(self, tmp_path, capsys):
        # Regression test for a real bug found live-testing: resuming in a directory
        # copied from a prior finished run (scaled.mtz etc. already present from the
        # start, as in the v2/v3 centring-investigation directories) made the
        # "Workflow Complete!" banner fire after every single subsequent command --
        # including read-only diagnostic scripts with nothing to do with finishing
        # anything -- which is confusing noise, not a useful signal.
        # WorkflowManager scans the directory at construction time, so the file must
        # exist *before* the agent is created -- matching the real scenario (a
        # directory copied from a prior finished run, complete before the agent
        # process even starts), not a file appearing mid-session.
        (tmp_path / "merged.mtz").touch()
        agent = make_agent(tmp_path)

        centring_check_command = STANDARD_WORKFLOW[8][0]  # a dials.python check, creates no files
        with patch.object(agent.executor, "execute", side_effect=make_mock_executor(agent)):
            capsys.readouterr()
            result = agent.execute_command(centring_check_command)
            agent.display_result(result)
        out = capsys.readouterr().out
        assert "Workflow Complete" not in out
        assert "Command Successful" in out  # the actual result should still show

    def test_explicit_next_command_still_shows_completion_regardless(self, tmp_path, capsys):
        # The suppression above must NOT affect the explicit `next` command -- that's
        # a deliberate query, not unsolicited noise after an unrelated command.
        (tmp_path / "merged.mtz").touch()
        agent = make_agent(tmp_path)
        capsys.readouterr()
        agent.display_next_step_suggestion()
        assert "Workflow Complete" in capsys.readouterr().out

    def test_version_shown_in_startup_banner_text(self):
        import dials_agent
        from dials_agent import cli
        # The banner f-string embeds __version__ directly -- confirm it's a real,
        # non-empty value that would actually render (covered structurally here;
        # test_cli_dispatch.py's test_cli_module_version_matches_package_version
        # covers the import wiring itself).
        assert dials_agent.__version__ == cli.__version__
        assert len(cli.__version__.split(".")) == 3  # looks like semver, e.g. "2.7.0"
