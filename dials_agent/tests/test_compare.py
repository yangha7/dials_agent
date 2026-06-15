"""
Tests for the DIALS run comparison module.

Creates mock DIALS output directories and verifies that the comparison
tool correctly extracts metrics and assesses consistency.
"""

import json
import os
import tempfile
from pathlib import Path

import pytest

# Add parent to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dials_agent.dials.compare import (
    ComparisonResult,
    RunMetrics,
    compare_runs,
    display_comparison_markdown,
    extract_metrics,
    _assess_consistency,
    _parse_timing_log,
    _parse_unit_cell,
    _determine_stage,
)


# ── Fixtures ────────────────────────────────────────────────────────────────

def _create_mock_run(tmpdir: Path, name: str, data: dict) -> Path:
    """Create a mock DIALS run directory with log files."""
    run_dir = tmpdir / name
    run_dir.mkdir(parents=True, exist_ok=True)
    
    # Create dummy DIALS output files based on stage
    stage = data.get("stage", "scaled")
    stage_files = {
        "imported": ["imported.expt"],
        "spots_found": ["imported.expt", "strong.refl"],
        "indexed": ["imported.expt", "strong.refl", "indexed.expt", "indexed.refl"],
        "refined": ["imported.expt", "strong.refl", "indexed.expt", "indexed.refl",
                     "refined.expt", "refined.refl"],
        "integrated": ["imported.expt", "strong.refl", "indexed.expt", "indexed.refl",
                        "refined.expt", "refined.refl", "integrated.expt", "integrated.refl"],
        "scaled": ["imported.expt", "strong.refl", "indexed.expt", "indexed.refl",
                    "refined.expt", "refined.refl", "integrated.expt", "integrated.refl",
                    "symmetrized.expt", "symmetrized.refl", "scaled.expt", "scaled.refl"],
        "exported": ["imported.expt", "strong.refl", "indexed.expt", "indexed.refl",
                      "refined.expt", "refined.refl", "integrated.expt", "integrated.refl",
                      "symmetrized.expt", "symmetrized.refl", "scaled.expt", "scaled.refl",
                      "scaled.mtz"],
    }
    
    for f in stage_files.get(stage, []):
        (run_dir / f).write_text("mock")
    
    # Create dials.find_spots.log
    if "spots" in data:
        (run_dir / "dials.find_spots.log").write_text(
            f"Saved {data['spots']} reflections to strong.refl\n"
        )
    
    # Create dials.index.log
    if "unit_cell" in data or "space_group" in data:
        index_log = []
        if "indexed_refl" in data:
            index_log.append(f"model 1 ({data['indexed_refl']} reflections)")
        if "unit_cell" in data:
            index_log.append(f"Unit cell: ({data['unit_cell']})")
        if "space_group" in data:
            index_log.append(f"Space group: {data['space_group']}")
        (run_dir / "dials.index.log").write_text("\n".join(index_log) + "\n")
    
    # Create dials.integrate.log
    if "integrated" in data:
        (run_dir / "dials.integrate.log").write_text(
            f"Integrated {data['integrated']} reflections on all images\n"
        )
    
    # Create dials.scale.log
    if "rmerge" in data or "cc_half" in data:
        scale_lines = []
        if "rmerge" in data:
            scale_lines.append(f"Rmerge(I): {data['rmerge']}")
        if "cc_half" in data:
            scale_lines.append(f"CC half: {data['cc_half']}")
        if "completeness" in data:
            scale_lines.append(f"Completeness: {data['completeness']}%")
        if "multiplicity" in data:
            scale_lines.append(f"Multiplicity: {data['multiplicity']}")
        if "i_sigma" in data:
            scale_lines.append(f"<I/sigma>: {data['i_sigma']}")
        (run_dir / "dials.scale.log").write_text("\n".join(scale_lines) + "\n")
    
    # Create timing log
    if "timings" in data:
        timing_lines = []
        for cmd, duration in data["timings"].items():
            timing_lines.append(
                f"2024-01-01 12:00:00  →  2024-01-01 12:01:00  "
                f"[{duration:.1f}s]  OK      {cmd}"
            )
        (run_dir / "dials_agent_timing.log").write_text("\n".join(timing_lines) + "\n")
    
    return run_dir


@pytest.fixture
def consistent_runs(tmp_path):
    """Create two runs with consistent results."""
    run1 = _create_mock_run(tmp_path, "run_agent", {
        "stage": "exported",
        "spots": 25000,
        "indexed_refl": 22000,
        "unit_cell": "67.20, 67.20, 67.20, 90.00, 90.00, 90.00",
        "space_group": "P213",
        "integrated": 45000,
        "rmerge": "0.054",
        "cc_half": "0.998",
        "completeness": "99.5",
        "multiplicity": "6.2",
        "i_sigma": "15.3",
        "timings": {
            "dials.import": 2.5,
            "dials.find_spots": 15.0,
            "dials.index": 8.3,
            "dials.refine": 5.1,
            "dials.integrate": 120.0,
            "dials.symmetry": 3.2,
            "dials.scale": 25.0,
            "dials.export": 1.5,
        },
    })
    
    run2 = _create_mock_run(tmp_path, "run_human", {
        "stage": "exported",
        "spots": 24800,
        "indexed_refl": 21900,
        "unit_cell": "67.18, 67.18, 67.18, 90.00, 90.00, 90.00",
        "space_group": "P213",
        "integrated": 44500,
        "rmerge": "0.056",
        "cc_half": "0.997",
        "completeness": "99.4",
        "multiplicity": "6.1",
        "i_sigma": "14.9",
        "timings": {
            "dials.import": 2.3,
            "dials.find_spots": 14.5,
            "dials.index": 9.1,
            "dials.refine": 4.8,
            "dials.integrate": 115.0,
            "dials.symmetry": 3.5,
            "dials.scale": 22.0,
            "dials.export": 1.3,
        },
    })
    
    return [str(run1), str(run2)]


@pytest.fixture
def divergent_runs(tmp_path):
    """Create two runs with significantly different results."""
    run1 = _create_mock_run(tmp_path, "run_good", {
        "stage": "exported",
        "spots": 25000,
        "indexed_refl": 22000,
        "unit_cell": "67.20, 67.20, 67.20, 90.00, 90.00, 90.00",
        "space_group": "P213",
        "integrated": 45000,
        "rmerge": "0.054",
        "cc_half": "0.998",
        "completeness": "99.5",
    })
    
    run2 = _create_mock_run(tmp_path, "run_bad", {
        "stage": "integrated",  # Didn't complete
        "spots": 15000,
        "indexed_refl": 10000,
        "unit_cell": "67.50, 67.50, 67.50, 90.00, 90.00, 90.00",
        "space_group": "P23",  # Different space group
        "integrated": 20000,
    })
    
    return [str(run1), str(run2)]


@pytest.fixture
def three_runs(tmp_path):
    """Create three runs for multi-way comparison."""
    runs = []
    for i, name in enumerate(["agent_v1", "agent_v2", "human"]):
        run = _create_mock_run(tmp_path, name, {
            "stage": "exported",
            "spots": 25000 + i * 100,
            "space_group": "P213",
            "unit_cell": "67.20, 67.20, 67.20, 90.00, 90.00, 90.00",
            "rmerge": f"{0.054 + i * 0.001}",
            "cc_half": f"{0.998 - i * 0.001}",
        })
        runs.append(str(run))
    return runs


# ── Unit tests ──────────────────────────────────────────────────────────────

class TestUnitCellParsing:
    def test_valid_unit_cell(self):
        result = _parse_unit_cell("67.20, 67.20, 67.20, 90.00, 90.00, 90.00")
        assert result is not None
        assert result["a"] == 67.20
        assert result["alpha"] == 90.00
    
    def test_invalid_unit_cell(self):
        assert _parse_unit_cell("invalid") is None
        assert _parse_unit_cell("1, 2, 3") is None


class TestConsistencyAssessment:
    def test_consistent_strings(self):
        assert _assess_consistency(["P213", "P213", "P213"], "space_group") == "consistent"
    
    def test_differing_strings(self):
        assert _assess_consistency(["P213", "P23"], "space_group") == "differs"
    
    def test_consistent_numbers(self):
        assert _assess_consistency([25000, 25100, 24900], "spots_found") == "consistent"
    
    def test_differing_numbers(self):
        assert _assess_consistency([25000, 15000], "spots_found") == "differs"
    
    def test_single_value(self):
        assert _assess_consistency([25000], "spots_found") == "n/a"
    
    def test_all_none(self):
        assert _assess_consistency([None, None], "spots_found") == "n/a"
    
    def test_partial_none(self):
        assert _assess_consistency([25000, None], "spots_found") == "n/a"
    
    def test_consistent_booleans(self):
        assert _assess_consistency([True, True], "workflow_complete") == "consistent"
    
    def test_differing_booleans(self):
        assert _assess_consistency([True, False], "workflow_complete") == "differs"
    
    def test_cc_half_consistent(self):
        assert _assess_consistency([0.998, 0.997], "cc_half") == "consistent"
    
    def test_cc_half_differs(self):
        assert _assess_consistency([0.998, 0.950], "cc_half") == "differs"


class TestDetermineStage:
    def test_not_started(self, tmp_path):
        stage, complete = _determine_stage(tmp_path)
        assert stage == "not_started"
        assert not complete
    
    def test_imported(self, tmp_path):
        (tmp_path / "imported.expt").write_text("mock")
        stage, complete = _determine_stage(tmp_path)
        assert stage == "imported"
        assert not complete
    
    def test_exported(self, tmp_path):
        for f in ["scaled.expt", "scaled.refl", "scaled.mtz"]:
            (tmp_path / f).write_text("mock")
        stage, complete = _determine_stage(tmp_path)
        assert stage == "exported"
        assert complete


class TestTimingParsing:
    def test_parse_timing_log(self, tmp_path):
        timing_file = tmp_path / "dials_agent_timing.log"
        timing_file.write_text(
            "2024-01-01 12:00:00  →  2024-01-01 12:00:15  [  15.0s]  OK      dials.find_spots imported.expt\n"
            "2024-01-01 12:00:15  →  2024-01-01 12:00:23  [   8.3s]  OK      dials.index imported.expt strong.refl\n"
        )
        total, steps, commands = _parse_timing_log(timing_file)
        assert total == pytest.approx(23.3)
        assert "dials.find_spots" in steps
        assert steps["dials.find_spots"] == pytest.approx(15.0)
        assert len(commands) == 2
    
    def test_parse_missing_file(self, tmp_path):
        total, steps, commands = _parse_timing_log(tmp_path / "nonexistent.log")
        assert total is None
        assert steps == {}
        assert commands == []
    
    def test_parse_minutes_format(self, tmp_path):
        timing_file = tmp_path / "dials_agent_timing.log"
        timing_file.write_text(
            "2024-01-01 12:00:00  →  2024-01-01 12:02:00  [2m 0.5s]  OK      dials.integrate refined.expt refined.refl\n"
        )
        total, steps, commands = _parse_timing_log(timing_file)
        assert total == pytest.approx(120.5)


# ── Integration tests ───────────────────────────────────────────────────────

class TestExtractMetrics:
    def test_extract_from_complete_run(self, consistent_runs):
        metrics = extract_metrics(consistent_runs[0], "agent")
        assert metrics.label == "agent"
        assert metrics.spots_found == 25000
        assert metrics.space_group == "P213"
        assert metrics.workflow_complete is True
        assert metrics.final_stage == "exported"
        assert metrics.total_time is not None
        assert metrics.total_time > 0
        assert len(metrics.commands) > 0
    
    def test_extract_from_incomplete_run(self, divergent_runs):
        metrics = extract_metrics(divergent_runs[1], "bad")
        assert metrics.label == "bad"
        assert metrics.workflow_complete is False
        assert metrics.final_stage == "integrated"
    
    def test_extract_from_empty_dir(self, tmp_path):
        empty = tmp_path / "empty"
        empty.mkdir()
        metrics = extract_metrics(str(empty), "empty")
        assert metrics.spots_found is None
        assert metrics.final_stage == "not_started"
        assert metrics.workflow_complete is False
    
    def test_merging_stats_extracted(self, consistent_runs):
        metrics = extract_metrics(consistent_runs[0])
        assert metrics.merging_stats is not None
        assert metrics.merging_stats.r_merge == pytest.approx(0.054)
        assert metrics.merging_stats.cc_half == pytest.approx(0.998)
        assert metrics.merging_stats.completeness == pytest.approx(0.995)


class TestCompareRuns:
    def test_consistent_comparison(self, consistent_runs):
        result = compare_runs(consistent_runs, ["agent", "human"])
        
        assert len(result.runs) == 2
        assert result.runs[0].label == "agent"
        assert result.runs[1].label == "human"
        
        # Space group should be consistent
        assert result.consistency["Space Group"] == "consistent"
        
        # Both should be complete
        assert result.consistency["Workflow Complete"] == "consistent"
        
        # Summary should mention consistency
        assert "consistent" in result.summary.lower() or "same" in result.summary.lower() or "Compared" in result.summary
    
    def test_divergent_comparison(self, divergent_runs):
        result = compare_runs(divergent_runs, ["good", "bad"])
        
        # Space group should differ
        assert result.consistency["Space Group"] == "differs"
        
        # Workflow completion should differ
        assert result.consistency["Workflow Complete"] == "differs"
        
        # Summary should mention differences
        assert "differ" in result.summary.lower()
    
    def test_three_way_comparison(self, three_runs):
        result = compare_runs(three_runs)
        
        assert len(result.runs) == 3
        # Space group should be consistent across all three
        assert result.consistency["Space Group"] == "consistent"
    
    def test_auto_labels(self, consistent_runs):
        result = compare_runs(consistent_runs)
        # Should use directory names as labels
        assert result.runs[0].label == "run_agent"
        assert result.runs[1].label == "run_human"
    
    def test_duplicate_labels(self, tmp_path):
        # Create two dirs with same name under different parents
        d1 = tmp_path / "a" / "run"
        d2 = tmp_path / "b" / "run"
        d1.mkdir(parents=True)
        d2.mkdir(parents=True)
        
        result = compare_runs([str(d1), str(d2)])
        # Labels should be made unique
        assert result.runs[0].label != result.runs[1].label
    
    def test_save_json(self, consistent_runs, tmp_path):
        result = compare_runs(consistent_runs, ["agent", "human"])
        
        output_file = str(tmp_path / "report.json")
        result.save_json(output_file)
        
        assert Path(output_file).exists()
        
        with open(output_file) as f:
            data = json.load(f)
        
        assert data["num_runs"] == 2
        assert "agent" in data["labels"]
        assert "human" in data["labels"]
        assert "metrics" in data
        assert "consistency" in data


class TestMarkdownOutput:
    def test_markdown_generation(self, consistent_runs):
        result = compare_runs(consistent_runs, ["agent", "human"])
        md = display_comparison_markdown(result)
        
        assert "# DIALS Run Comparison" in md
        assert "agent" in md
        assert "human" in md
        assert "| Metric |" in md
        assert "## Summary" in md


class TestRichDisplay:
    def test_display_does_not_crash(self, consistent_runs):
        """Verify that display_comparison runs without errors."""
        from dials_agent.dials.compare import display_comparison
        from rich.console import Console
        
        result = compare_runs(consistent_runs, ["agent", "human"])
        
        # Use a string buffer console to avoid terminal output during tests
        console = Console(file=open(os.devnull, "w"))
        display_comparison(result, console)  # Should not raise


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
