"""
Tests for WorkflowManager.get_next_step_suggestion()'s WORKFLOW_SUGGESTIONS data.

Regression test for a real bug found live: the "import" entry's next_command
was `dials.image_viewer imported.expt` -- a GUI viewer, not an actual workflow
step, listed as if it were the required next action while the real next step
(dials.find_spots) was buried in optional_commands. This produced a confusing
"Next Step" panel suggesting a non-advancing visualization tool as if it were
the primary next action, immediately followed by the LLM's own (correct)
suggestion of dials.find_spots in a separate panel below it -- two different
"next step" panels disagreeing with each other.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dials_agent.dials.workflow import create_workflow_manager


def test_next_step_after_import_is_find_spots_not_image_viewer(tmp_path):
    (tmp_path / "imported.expt").touch()
    workflow = create_workflow_manager(str(tmp_path))

    suggestion = workflow.get_next_step_suggestion()

    assert suggestion["next_command"] == "dials.find_spots imported.expt"
    assert "dials.image_viewer imported.expt" in suggestion["optional_commands"]
