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


def test_next_step_after_find_spots_defaults_to_index_with_beam_position_as_optional(tmp_path):
    """
    dials.index is the default next step (matching the TL;DR workflow), with
    dials.search_beam_position and dials.reciprocal_lattice_viewer offered as
    optional branches per the SLAC-2026 workflow tutorial -- run right after
    find_spots, before indexing, to check for a beam-centre/geometry problem
    (reciprocal_lattice_viewer works on unindexed strong.refl directly, since
    reflection positions come from geometry, not Miller index assignment).
    """
    (tmp_path / "imported.expt").touch()
    (tmp_path / "strong.refl").touch()
    workflow = create_workflow_manager(str(tmp_path))

    suggestion = workflow.get_next_step_suggestion()

    assert suggestion["next_command"] == "dials.index imported.expt strong.refl"
    assert "dials.search_beam_position imported.expt strong.refl" in suggestion["optional_commands"]
    assert "dials.reciprocal_lattice_viewer imported.expt strong.refl" in suggestion["optional_commands"]
