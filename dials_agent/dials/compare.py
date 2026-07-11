"""
DIALS run comparison tool.

This module compares results from multiple DIALS processing runs
(e.g., human vs agent, different parameters) to assess consistency.

It parses log files, timing data, and output files from each run directory
and presents a side-by-side comparison with consistency metrics.
"""

import json
import logging
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Ordered from most to least advanced stage; dials.report is most informative
# on scaled or integrated data.
_REPORT_STAGE_FILES: list[tuple[str, list[str]]] = [
    ("scaled",     ["scaled.expt",     "scaled.refl"]),
    ("integrated", ["integrated.expt", "integrated.refl"]),
    ("refined",    ["refined.expt",    "refined.refl"]),
    ("indexed",    ["indexed.expt",    "indexed.refl"]),
    ("imported",   ["imported.expt"]),
]


def generate_dials_report(
    directory: str,
    label: str = "",
    timeout: int = 300,
) -> dict[str, Optional[str]]:
    """
    Run ``dials.report`` on the most advanced output files found in *directory*.

    Returns a dict with keys:
      ``html``  – absolute path to the generated HTML file, or None on failure
      ``json``  – absolute path to the generated JSON file, or None on failure
      ``stage`` – which stage's files were used (e.g. "scaled")
      ``error`` – error message string if the run failed, else None
    """
    dir_path = Path(directory).resolve()
    result: dict[str, Optional[str]] = {"html": None, "json": None, "stage": None, "error": None}

    if not dir_path.exists():
        result["error"] = f"Directory not found: {directory}"
        return result

    # Find the most advanced pair of expt/refl files
    input_files: list[str] = []
    for stage, files in _REPORT_STAGE_FILES:
        if all((dir_path / f).exists() for f in files):
            input_files = [str(dir_path / f) for f in files]
            result["stage"] = stage
            break

    if not input_files:
        result["error"] = "No DIALS output files found for dials.report"
        return result

    # Name outputs after the label (or directory name) so multiple runs
    # in the same parent directory do not overwrite each other.
    stem = label or dir_path.name
    html_name = f"dials.report.{stem}.html" if label else "dials.report.html"
    json_name = f"dials.report.{stem}.json" if label else "dials.report.json"
    html_path = dir_path / html_name
    json_path = dir_path / json_name

    cmd = [
        "dials.report",
        *input_files,
        f"output.html={html_path}",
        f"output.json={json_path}",
    ]

    logger.info("Running: %s", " ".join(cmd))
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(dir_path),
        )
        if proc.returncode != 0:
            result["error"] = f"dials.report exited {proc.returncode}: {proc.stderr[-500:]}"
        else:
            if html_path.exists():
                result["html"] = str(html_path)
            if json_path.exists():
                result["json"] = str(json_path)
    except FileNotFoundError:
        result["error"] = "dials.report not found — is DIALS on the PATH?"
    except subprocess.TimeoutExpired:
        result["error"] = f"dials.report timed out after {timeout}s"
    except Exception as exc:
        result["error"] = str(exc)

    return result


# ── Metric extraction from log files ────────────────────────────────────────

# Each extractor returns a dict of metric_name -> value
LOG_PARSERS: dict[str, list[tuple[str, str, type]]] = {
    # (regex_pattern, metric_name, value_type)
    "dials.find_spots.log": [
        (r"Saved (\d+) reflections to", "spots_found", int),
        (r"Found (\d+) strong pixels", "strong_pixels", int),
    ],
    "dials.index.log": [
        (r"model \d+ \((\d+) reflections\)", "indexed_reflections", int),
        (r"RMSDs by experiment:.*?(\d+\.\d+)\s+(\d+\.\d+)\s+(\d+\.\d+)", "rmsd_xyz", str),
        (r"Unit cell: \(([\d., ]+)\)", "unit_cell", str),
        (r"Space group: (\S+)", "space_group", str),
    ],
    "dials.refine.log": [
        (r"RMSDs by experiment:.*?(\d+\.\d+)\s+(\d+\.\d+)\s+(\d+\.\d+)", "rmsd_xyz", str),
        (r"Final RMS.*?(\d+\.\d+)", "final_rms", float),
    ],
    "dials.integrate.log": [
        (r"Integrated (\d+) reflections", "integrated_reflections", int),
        (r"(\d+) reflections integrated", "integrated_reflections", int),
    ],
    "dials.scale.log": [
        (r"Space group being used.*?(\S+)\s*$", "space_group", str),
        (r"Resolution limit.*?(\d+\.\d+)", "resolution_limit", float),
    ],
    "dials.merge.log": [
        (r"Resolution.*?(\d+\.\d+)\s*-\s*(\d+\.\d+)", "resolution_range", str),
    ],
}


@dataclass
class MergingStatistics:
    """Merging statistics extracted from dials.scale or dials.merge output."""
    resolution_range: str = ""
    completeness: float = 0.0
    multiplicity: float = 0.0
    r_merge: float = 0.0
    r_meas: float = 0.0
    r_pim: float = 0.0
    cc_half: float = 0.0
    cc_anom: float = 0.0
    i_over_sigma: float = 0.0
    n_obs: int = 0
    n_unique: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary, excluding zero/empty values."""
        d = {}
        for k, v in self.__dict__.items():
            if v and v != 0 and v != 0.0:
                d[k] = v
        return d


@dataclass
class RunMetrics:
    """All metrics extracted from a single DIALS processing run."""
    directory: str
    label: str  # Short label for display (e.g., "run1", "agent", "human")

    # Per-step metrics
    spots_found: Optional[int] = None
    indexed_reflections: Optional[int] = None
    unit_cell: Optional[str] = None
    space_group: Optional[str] = None
    rmsd_index: Optional[str] = None
    rmsd_refine: Optional[str] = None
    integrated_reflections: Optional[int] = None
    resolution_limit: Optional[float] = None

    # Merging statistics (overall)
    merging_stats: Optional[MergingStatistics] = None
    # Merging statistics (highest resolution shell)
    merging_stats_high: Optional[MergingStatistics] = None

    # Timing
    total_time: Optional[float] = None  # seconds
    step_timings: dict[str, float] = field(default_factory=dict)

    # Commands executed
    commands: list[str] = field(default_factory=list)

    # Workflow completion
    workflow_complete: bool = False
    final_stage: str = ""

    # Files produced
    output_files: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to a flat dictionary for comparison."""
        d = {
            "directory": self.directory,
            "label": self.label,
            "spots_found": self.spots_found,
            "indexed_reflections": self.indexed_reflections,
            "unit_cell": self.unit_cell,
            "space_group": self.space_group,
            "rmsd_index": self.rmsd_index,
            "rmsd_refine": self.rmsd_refine,
            "integrated_reflections": self.integrated_reflections,
            "resolution_limit": self.resolution_limit,
            "total_time": self.total_time,
            "workflow_complete": self.workflow_complete,
            "final_stage": self.final_stage,
        }
        if self.merging_stats:
            for k, v in self.merging_stats.to_dict().items():
                d[f"overall_{k}"] = v
        if self.merging_stats_high:
            for k, v in self.merging_stats_high.to_dict().items():
                d[f"high_shell_{k}"] = v
        return d


# ── Parsing functions ───────────────────────────────────────────────────────

def _parse_unit_cell(text: str) -> Optional[dict[str, float]]:
    """Parse a unit cell string like '67.20, 67.20, 67.20, 90.00, 90.00, 90.00'."""
    parts = [p.strip() for p in text.split(",")]
    if len(parts) == 6:
        try:
            return {
                "a": float(parts[0]), "b": float(parts[1]), "c": float(parts[2]),
                "alpha": float(parts[3]), "beta": float(parts[4]), "gamma": float(parts[5]),
            }
        except ValueError:
            pass
    return None


def _parse_merging_table(log_content: str) -> tuple[Optional[MergingStatistics], Optional[MergingStatistics]]:
    """
    Parse the merging statistics table from dials.scale.log or dials.merge.log.

    Returns (overall_stats, highest_shell_stats).
    """
    overall = MergingStatistics()
    high_shell = MergingStatistics()

    # Look for the merging statistics table
    # The table typically has columns: d_max, d_min, #obs, #uniq, mult, %comp, ...
    # and rows for resolution shells, with the last row being "overall"

    # Try to find the summary table that dials.scale prints
    # Pattern: look for lines with "Overall" or the table header

    lines = log_content.split("\n")

    # Strategy 1: Look for the tabulated merging statistics
    # dials.scale prints a table like:
    #            ----------Overall----------
    # d_max  d_min   #obs  #uniq   mult  %comp       <I>  <I/sI>    r_mrg   r_meas    r_pim   r_anom   cc1/2   cc_ano
    table_start = None
    overall_line = None
    high_shell_line = None

    for i, line in enumerate(lines):
        if "----------Overall----------" in line or "Merging statistics" in line:
            table_start = i
        # Look for the header line
        if table_start and ("r_mrg" in line.lower() or "r_merge" in line.lower() or "cc1/2" in line.lower()):
            # The next lines should be data rows
            # Find the overall row (usually last data row or marked "overall")
            for j in range(i + 1, min(i + 50, len(lines))):
                stripped = lines[j].strip()
                if not stripped or stripped.startswith("-"):
                    continue
                # Check if this looks like a data row (starts with a number)
                parts = stripped.split()
                if len(parts) >= 8:
                    try:
                        float(parts[0])
                        high_shell_line = stripped  # Keep updating; last valid = highest shell
                    except ValueError:
                        pass
            break

    # Strategy 2: Look for individual metric lines
    # dials.scale also prints summary lines like:
    #   Rmerge(I):  0.0543
    #   CC half:    0.9987
    for line in lines:
        stripped = line.strip()

        # Resolution
        m = re.search(r"Resolution range:\s*([\d.]+)\s*-?\s*([\d.]+)", stripped, re.IGNORECASE)
        if not m:
            m = re.search(r"Resolution:\s*([\d.]+)\s*-\s*([\d.]+)", stripped, re.IGNORECASE)
        if m:
            overall.resolution_range = f"{m.group(1)} - {m.group(2)}"

        # Completeness
        m = re.search(r"Completeness\s*[:=]\s*([\d.]+)\s*%?", stripped, re.IGNORECASE)
        if m:
            val = float(m.group(1))
            overall.completeness = val if val <= 1.0 else val / 100.0

        # Multiplicity / Redundancy
        m = re.search(r"(?:Multiplicity|Redundancy)\s*[:=]\s*([\d.]+)", stripped, re.IGNORECASE)
        if m:
            overall.multiplicity = float(m.group(1))

        # Rmerge
        m = re.search(r"R\s*merge\s*(?:\(I\))?\s*[:=]\s*([\d.]+)", stripped, re.IGNORECASE)
        if m:
            overall.r_merge = float(m.group(1))

        # Rmeas
        m = re.search(r"R\s*meas\s*(?:\(I\))?\s*[:=]\s*([\d.]+)", stripped, re.IGNORECASE)
        if m:
            overall.r_meas = float(m.group(1))

        # Rpim
        m = re.search(r"R\s*pim\s*(?:\(I\))?\s*[:=]\s*([\d.]+)", stripped, re.IGNORECASE)
        if m:
            overall.r_pim = float(m.group(1))

        # CC1/2
        m = re.search(r"CC\s*(?:1/2|half)\s*[:=]\s*([\d.]+)", stripped, re.IGNORECASE)
        if m:
            overall.cc_half = float(m.group(1))

        # I/sigma
        m = re.search(r"<I/sigma>\s*[:=]\s*([\d.]+)", stripped, re.IGNORECASE)
        if not m:
            m = re.search(r"I/sigma\s*[:=]\s*([\d.]+)", stripped, re.IGNORECASE)
        if not m:
            m = re.search(r"Mean I/sigma\s*[:=]\s*([\d.]+)", stripped, re.IGNORECASE)
        if m:
            overall.i_over_sigma = float(m.group(1))

        # Number of observations
        m = re.search(r"(?:Total )?observations?\s*[:=]\s*(\d+)", stripped, re.IGNORECASE)
        if m:
            overall.n_obs = int(m.group(1))

        # Number of unique reflections
        m = re.search(r"(?:Unique )?reflections?\s*[:=]\s*(\d+)", stripped, re.IGNORECASE)
        if m:
            overall.n_unique = int(m.group(1))

    # Check if we got any meaningful data
    has_overall = any(v for v in overall.to_dict().values())
    has_high = False  # TODO: parse high-resolution shell from table rows

    return (overall if has_overall else None, high_shell if has_high else None)


def _parse_timing_log(timing_path: Path) -> tuple[Optional[float], dict[str, float], list[str]]:
    """
    Parse dials_agent_timing.log to extract timing information.

    Returns (total_time, step_timings, commands_list).
    """
    if not timing_path.exists():
        return None, {}, []

    step_timings: dict[str, float] = {}
    commands: list[str] = []
    total_time = 0.0

    content = timing_path.read_text()
    for line in content.strip().split("\n"):
        if not line.strip():
            continue

        # Format: "2024-01-01 12:00:00  →  2024-01-01 12:01:00  [   60.0s]  OK      dials.import ..."
        # Extract duration and command
        m = re.search(r"\[\s*([\d.]+)s\s*\]", line)
        if not m:
            m = re.search(r"\[\s*(\d+)m\s+([\d.]+)s\s*\]", line)
            if m:
                duration = int(m.group(1)) * 60 + float(m.group(2))
            else:
                continue
        else:
            duration = float(m.group(1))

        # Extract command (after OK/FAILED and whitespace)
        cmd_match = re.search(r"(?:OK|FAILED)\s+(.+)$", line)
        if cmd_match:
            cmd = cmd_match.group(1).strip()
            cmd_name = cmd.split()[0] if cmd else ""
            commands.append(cmd)
            step_timings[cmd_name] = step_timings.get(cmd_name, 0) + duration
            total_time += duration

    return total_time, step_timings, commands


def _determine_stage(directory: Path) -> tuple[str, bool]:
    """Determine the workflow stage from files in a directory."""
    stage_checks = [
        ("exported", ["scaled.mtz"], True),
        ("scaled", ["scaled.expt", "scaled.refl"], False),
        ("symmetry_determined", ["symmetrized.expt", "symmetrized.refl"], False),
        ("integrated", ["integrated.expt", "integrated.refl"], False),
        ("refined", ["refined.expt", "refined.refl"], False),
        ("indexed", ["indexed.expt", "indexed.refl"], False),
        ("spots_found", ["strong.refl"], False),
        ("imported", ["imported.expt"], False),
    ]

    files = set(f.name for f in directory.iterdir() if f.is_file()) if directory.exists() else set()

    # Check for any .mtz file
    has_mtz = any(f.endswith(".mtz") for f in files)

    for stage_name, required, is_complete in stage_checks:
        if all(f in files for f in required):
            return stage_name, is_complete or has_mtz

    return "not_started", False


def extract_metrics(directory: str, label: Optional[str] = None) -> RunMetrics:
    """
    Extract all metrics from a DIALS processing run directory.

    Args:
        directory: Path to the run directory
        label: Short label for this run (defaults to directory name)

    Returns:
        RunMetrics with all extracted data
    """
    dir_path = Path(directory).resolve()
    if label is None:
        label = dir_path.name

    metrics = RunMetrics(directory=str(dir_path), label=label)

    # Determine workflow stage
    metrics.final_stage, metrics.workflow_complete = _determine_stage(dir_path)

    # List output files
    dials_extensions = {".expt", ".refl", ".mtz", ".html", ".log"}
    if dir_path.exists():
        metrics.output_files = sorted(
            f.name for f in dir_path.iterdir()
            if f.is_file() and f.suffix in dials_extensions
        )

    # Parse timing log
    timing_path = dir_path / "dials_agent_timing.log"
    total_time, step_timings, commands = _parse_timing_log(timing_path)
    metrics.total_time = total_time
    metrics.step_timings = step_timings
    metrics.commands = commands

    # Parse individual log files
    for log_name, patterns in LOG_PARSERS.items():
        log_path = dir_path / log_name
        if not log_path.exists():
            continue

        try:
            content = log_path.read_text(errors="replace")
        except Exception as e:
            logger.warning(f"Could not read {log_path}: {e}")
            continue

        for pattern, metric_name, value_type in patterns:
            m = re.search(pattern, content, re.MULTILINE)
            if m:
                try:
                    if value_type == int:
                        value = int(m.group(1))
                    elif value_type == float:
                        value = float(m.group(1))
                    else:
                        value = m.group(1)

                    # Map to RunMetrics fields
                    if metric_name == "spots_found" and metrics.spots_found is None:
                        metrics.spots_found = value
                    elif metric_name == "indexed_reflections" and metrics.indexed_reflections is None:
                        metrics.indexed_reflections = value
                    elif metric_name == "unit_cell" and metrics.unit_cell is None:
                        metrics.unit_cell = value
                    elif metric_name == "space_group" and metrics.space_group is None:
                        metrics.space_group = value
                    elif metric_name == "integrated_reflections" and metrics.integrated_reflections is None:
                        metrics.integrated_reflections = value
                    elif metric_name == "resolution_limit" and metrics.resolution_limit is None:
                        metrics.resolution_limit = value
                    elif metric_name == "rmsd_xyz":
                        if "index" in log_name:
                            metrics.rmsd_index = value
                        elif "refine" in log_name:
                            metrics.rmsd_refine = value
                except (ValueError, IndexError):
                    pass

    # Parse merging statistics from dials.scale.log or dials.merge.log
    for scale_log in ["dials.scale.log", "dials.merge.log"]:
        log_path = dir_path / scale_log
        if log_path.exists():
            try:
                content = log_path.read_text(errors="replace")
                overall, high_shell = _parse_merging_table(content)
                if overall:
                    metrics.merging_stats = overall
                if high_shell:
                    metrics.merging_stats_high = high_shell
            except Exception as e:
                logger.warning(f"Could not parse merging stats from {log_path}: {e}")
            break  # Use the first one found

    return metrics


# ── Comparison logic ────────────────────────────────────────────────────────

@dataclass
class ComparisonResult:
    """Result of comparing multiple DIALS runs."""
    runs: list[RunMetrics]
    metrics_table: dict[str, list[Any]]  # metric_name -> [value_per_run]
    consistency: dict[str, str]  # metric_name -> "consistent" / "differs" / "partial"
    summary: str
    # dials.report outputs: one entry per run (may be None if generation failed)
    report_html: list[Optional[str]] = field(default_factory=list)
    report_json: list[Optional[str]] = field(default_factory=list)
    report_errors: list[Optional[str]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to serializable dictionary."""
        return {
            "num_runs": len(self.runs),
            "labels": [r.label for r in self.runs],
            "directories": [r.directory for r in self.runs],
            "metrics": self.metrics_table,
            "consistency": self.consistency,
            "summary": self.summary,
            "reports": {
                "html": self.report_html,
                "json": self.report_json,
            },
        }

    def save_json(self, filepath: str):
        """Save comparison results to a JSON file."""
        with open(filepath, "w") as f:
            json.dump(self.to_dict(), f, indent=2, default=str)


def _format_value(value: Any) -> str:
    """Format a value for display."""
    if value is None:
        return "—"
    if isinstance(value, float):
        if value >= 100:
            return f"{value:.1f}"
        elif value >= 1:
            return f"{value:.2f}"
        else:
            return f"{value:.4f}"
    if isinstance(value, bool):
        return "✓" if value else "✗"
    return str(value)


def _assess_consistency(values: list[Any], metric_name: str) -> str:
    """
    Assess whether values across runs are consistent.

    Returns: "consistent", "differs", "partial", or "n/a"
    """
    # Filter out None values
    valid = [v for v in values if v is not None]

    if len(valid) <= 1:
        return "n/a"

    # String comparison (space group, etc.)
    if all(isinstance(v, str) for v in valid):
        return "consistent" if len(set(valid)) == 1 else "differs"

    # Boolean comparison
    if all(isinstance(v, bool) for v in valid):
        return "consistent" if len(set(valid)) == 1 else "differs"

    # Numeric comparison with tolerance
    if all(isinstance(v, (int, float)) for v in valid):
        numeric = [float(v) for v in valid]
        mean = sum(numeric) / len(numeric)

        if mean == 0:
            return "consistent" if all(v == 0 for v in numeric) else "differs"

        # Use coefficient of variation (CV) for consistency check
        variance = sum((v - mean) ** 2 for v in numeric) / len(numeric)
        std_dev = variance ** 0.5
        cv = std_dev / abs(mean) if mean != 0 else 0

        # Thresholds depend on the metric
        if metric_name in ("space_group", "workflow_complete"):
            return "consistent" if cv == 0 else "differs"
        elif metric_name in ("spots_found", "indexed_reflections", "integrated_reflections"):
            # Allow 5% variation for counts
            return "consistent" if cv < 0.05 else ("partial" if cv < 0.15 else "differs")
        elif metric_name in ("resolution_limit",):
            # Allow 0.1 Å variation
            max_diff = max(numeric) - min(numeric)
            return "consistent" if max_diff < 0.1 else ("partial" if max_diff < 0.3 else "differs")
        elif metric_name in ("r_merge", "r_meas", "r_pim"):
            # Allow 10% relative variation for R-values
            return "consistent" if cv < 0.10 else ("partial" if cv < 0.25 else "differs")
        elif metric_name in ("cc_half",):
            # CC1/2 should be very consistent
            max_diff = max(numeric) - min(numeric)
            return "consistent" if max_diff < 0.005 else ("partial" if max_diff < 0.02 else "differs")
        elif metric_name in ("completeness",):
            max_diff = max(numeric) - min(numeric)
            return "consistent" if max_diff < 0.01 else ("partial" if max_diff < 0.05 else "differs")
        elif metric_name in ("total_time",):
            # Timing can vary a lot
            return "consistent" if cv < 0.20 else ("partial" if cv < 0.50 else "differs")
        else:
            # Default: 10% CV threshold
            return "consistent" if cv < 0.10 else ("partial" if cv < 0.25 else "differs")

    return "n/a"


def compare_runs(
    directories: list[str],
    labels: Optional[list[str]] = None,
    generate_reports: bool = True,
) -> ComparisonResult:
    """
    Compare multiple DIALS processing runs.

    Args:
        directories: List of paths to run directories
        labels: Optional labels for each run (defaults to directory names)
        generate_reports: If True, run ``dials.report`` on each directory to
            produce HTML/JSON reports for visual comparison.

    Returns:
        ComparisonResult with detailed comparison data
    """
    if labels is None:
        labels = [Path(d).name for d in directories]

    # Ensure labels are unique
    seen = {}
    unique_labels = []
    for label in labels:
        if label in seen:
            seen[label] += 1
            unique_labels.append(f"{label}_{seen[label]}")
        else:
            seen[label] = 0
            unique_labels.append(label)
    labels = unique_labels

    # Extract metrics from each run
    runs = []
    for directory, label in zip(directories, labels):
        try:
            metrics = extract_metrics(directory, label)
            runs.append(metrics)
        except Exception as e:
            logger.error(f"Failed to extract metrics from {directory}: {e}")
            # Create a minimal entry
            runs.append(RunMetrics(directory=directory, label=label))

    # Build comparison table
    # Define the metrics to compare, in display order
    metric_keys = [
        ("Workflow Stage", "final_stage"),
        ("Workflow Complete", "workflow_complete"),
        ("Spots Found", "spots_found"),
        ("Indexed Reflections", "indexed_reflections"),
        ("Space Group", "space_group"),
        ("Unit Cell", "unit_cell"),
        ("RMSD (Index)", "rmsd_index"),
        ("RMSD (Refine)", "rmsd_refine"),
        ("Integrated Reflections", "integrated_reflections"),
        ("Resolution Limit (Å)", "resolution_limit"),
        ("Completeness", "overall_completeness"),
        ("Multiplicity", "overall_multiplicity"),
        ("Rmerge", "overall_r_merge"),
        ("Rmeas", "overall_r_meas"),
        ("Rpim", "overall_r_pim"),
        ("CC1/2", "overall_cc_half"),
        ("I/σ(I)", "overall_i_over_sigma"),
        ("Total Time (s)", "total_time"),
    ]

    # Convert runs to flat dicts for easy access
    run_dicts = [r.to_dict() for r in runs]

    metrics_table: dict[str, list[Any]] = {}
    consistency: dict[str, str] = {}

    for display_name, key in metric_keys:
        values = [d.get(key) for d in run_dicts]
        metrics_table[display_name] = values
        consistency[display_name] = _assess_consistency(values, key)

    # Add step timings if available
    all_steps = set()
    for r in runs:
        all_steps.update(r.step_timings.keys())

    for step in sorted(all_steps):
        display_name = f"Time: {step}"
        values = [r.step_timings.get(step) for r in runs]
        metrics_table[display_name] = values
        consistency[display_name] = _assess_consistency(values, "total_time")

    # Generate summary
    summary = _generate_summary(runs, metrics_table, consistency)

    # Run dials.report on each directory to produce HTML/JSON reports
    report_html: list[Optional[str]] = []
    report_json: list[Optional[str]] = []
    report_errors: list[Optional[str]] = []
    if generate_reports:
        for run in runs:
            rpt = generate_dials_report(run.directory, label=run.label)
            report_html.append(rpt["html"])
            report_json.append(rpt["json"])
            report_errors.append(rpt["error"])
            if rpt["error"]:
                logger.warning("dials.report failed for %s: %s", run.label, rpt["error"])
            elif rpt["html"]:
                logger.info("dials.report → %s", rpt["html"])

    return ComparisonResult(
        runs=runs,
        metrics_table=metrics_table,
        consistency=consistency,
        summary=summary,
        report_html=report_html,
        report_json=report_json,
        report_errors=report_errors,
    )


def _generate_summary(
    runs: list[RunMetrics],
    metrics_table: dict[str, list[Any]],
    consistency: dict[str, str],
) -> str:
    """Generate a human-readable summary of the comparison."""
    n_runs = len(runs)
    n_consistent = sum(1 for v in consistency.values() if v == "consistent")
    n_differs = sum(1 for v in consistency.values() if v == "differs")
    n_partial = sum(1 for v in consistency.values() if v == "partial")
    n_applicable = sum(1 for v in consistency.values() if v != "n/a")

    lines = [
        f"Compared {n_runs} DIALS processing runs:",
        "",
    ]

    # List runs
    for r in runs:
        status = "✓ complete" if r.workflow_complete else f"→ {r.final_stage}"
        time_str = ""
        if r.total_time is not None:
            if r.total_time >= 60:
                mins = int(r.total_time // 60)
                secs = r.total_time % 60
                time_str = f" ({mins}m {secs:.0f}s)"
            else:
                time_str = f" ({r.total_time:.1f}s)"
        lines.append(f"  • {r.label}: {status}{time_str}")

    lines.append("")

    # Consistency summary
    if n_applicable > 0:
        pct = n_consistent / n_applicable * 100
        lines.append(f"Consistency: {n_consistent}/{n_applicable} metrics consistent ({pct:.0f}%)")

        if n_differs > 0:
            lines.append(f"  ⚠ {n_differs} metric(s) differ significantly:")
            for name, status in consistency.items():
                if status == "differs":
                    values = metrics_table[name]
                    formatted = [_format_value(v) for v in values]
                    lines.append(f"    • {name}: {' vs '.join(formatted)}")

        if n_partial > 0:
            lines.append(f"  ~ {n_partial} metric(s) show minor differences:")
            for name, status in consistency.items():
                if status == "partial":
                    values = metrics_table[name]
                    formatted = [_format_value(v) for v in values]
                    lines.append(f"    • {name}: {' vs '.join(formatted)}")

        if n_consistent == n_applicable:
            lines.append("  ✓ All metrics are consistent across runs!")
    else:
        lines.append("  No comparable metrics found.")

    return "\n".join(lines)


# ── Rich display ────────────────────────────────────────────────────────────

def display_comparison(result: ComparisonResult, console=None):
    """
    Display comparison results using Rich tables.

    Args:
        result: ComparisonResult to display
        console: Rich Console instance (creates one if not provided)
    """
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text

    if console is None:
        console = Console()

    # Header
    console.print(Panel.fit(
        f"[bold blue]DIALS Run Comparison[/bold blue]\n"
        f"Comparing {len(result.runs)} processing runs",
        border_style="blue"
    ))

    # Main comparison table
    table = Table(
        title="📊 Metrics Comparison",
        border_style="cyan",
        show_lines=True,
    )

    # Add columns
    table.add_column("Metric", style="bold", min_width=20)
    for run in result.runs:
        table.add_column(run.label, min_width=12, justify="right")
    table.add_column("Status", justify="center", min_width=10)

    # Add rows
    for metric_name, values in result.metrics_table.items():
        status = result.consistency.get(metric_name, "n/a")

        # Skip metrics where all values are None
        if all(v is None for v in values):
            continue

        # Format values
        formatted = [_format_value(v) for v in values]

        # Color-code status
        if status == "consistent":
            status_str = "[green]✓ same[/green]"
        elif status == "partial":
            status_str = "[yellow]~ close[/yellow]"
        elif status == "differs":
            status_str = "[red]✗ differs[/red]"
        else:
            status_str = "[dim]—[/dim]"

        # Highlight differing values
        if status == "differs":
            formatted = [f"[red]{v}[/red]" for v in formatted]
        elif status == "partial":
            formatted = [f"[yellow]{v}[/yellow]" for v in formatted]

        table.add_row(metric_name, *formatted, status_str)

    console.print(table)

    # Commands comparison
    if any(r.commands for r in result.runs):
        cmd_table = Table(
            title="🔧 Commands Executed",
            border_style="dim",
        )
        cmd_table.add_column("Run", style="cyan")
        cmd_table.add_column("# Commands", justify="right")
        cmd_table.add_column("Commands", style="dim")

        for run in result.runs:
            cmd_names = [c.split()[0] for c in run.commands] if run.commands else []
            cmd_table.add_row(
                run.label,
                str(len(run.commands)),
                " → ".join(cmd_names) if cmd_names else "—"
            )

        console.print(cmd_table)

    # dials.report links
    if result.report_html:
        rpt_table = Table(title="📄 DIALS Reports", border_style="dim")
        rpt_table.add_column("Run", style="cyan")
        rpt_table.add_column("HTML Report")
        rpt_table.add_column("Note", style="dim")

        for run, html, err in zip(result.runs, result.report_html, result.report_errors):
            if html:
                rpt_table.add_row(run.label, html, "")
            else:
                rpt_table.add_row(run.label, "[dim]—[/dim]", err or "not generated")

        console.print(rpt_table)

    # Summary
    console.print(Panel(
        result.summary,
        title="[bold]Summary[/bold]",
        border_style="green" if all(
            v in ("consistent", "n/a") for v in result.consistency.values()
        ) else "yellow"
    ))


def display_comparison_markdown(result: ComparisonResult) -> str:
    """
    Generate a Markdown representation of the comparison.

    Args:
        result: ComparisonResult to format

    Returns:
        Markdown string
    """
    lines = [
        "# DIALS Run Comparison",
        "",
        f"Comparing {len(result.runs)} processing runs.",
        "",
    ]

    # Runs overview
    lines.append("## Runs")
    lines.append("")
    for r in result.runs:
        status = "✓ complete" if r.workflow_complete else f"→ {r.final_stage}"
        lines.append(f"- **{r.label}**: `{r.directory}` ({status})")
    lines.append("")

    # Metrics table
    lines.append("## Metrics")
    lines.append("")

    # Table header
    header = "| Metric |"
    separator = "|--------|"
    for run in result.runs:
        header += f" {run.label} |"
        separator += "--------|"
    header += " Status |"
    separator += "--------|"
    lines.append(header)
    lines.append(separator)

    # Table rows
    for metric_name, values in result.metrics_table.items():
        if all(v is None for v in values):
            continue

        formatted = [_format_value(v) for v in values]
        status = result.consistency.get(metric_name, "n/a")

        status_emoji = {"consistent": "✓", "partial": "~", "differs": "✗", "n/a": "—"}.get(status, "?")

        row = f"| {metric_name} |"
        for v in formatted:
            row += f" {v} |"
        row += f" {status_emoji} |"
        lines.append(row)

    lines.append("")

    # dials.report links
    if result.report_html:
        lines.append("## DIALS Reports")
        lines.append("")
        for run, html, err in zip(result.runs, result.report_html, result.report_errors):
            if html:
                lines.append(f"- **{run.label}**: [{Path(html).name}]({html})")
            else:
                lines.append(f"- **{run.label}**: not generated ({err or 'unknown error'})")
        lines.append("")

    # Summary
    lines.append("## Summary")
    lines.append("")
    lines.append(result.summary)

    return "\n".join(lines)


def save_comparison_markdown(result: ComparisonResult, filepath: str) -> None:
    """Write the comparison as a Markdown file."""
    Path(filepath).write_text(display_comparison_markdown(result), encoding="utf-8")


def display_comparison_html(result: ComparisonResult) -> str:
    """
    Generate a self-contained HTML report for the comparison.

    Returns an HTML string with inline CSS — no external dependencies.
    """
    status_color = {"consistent": "#2e7d32", "partial": "#e65100", "differs": "#c62828", "n/a": "#757575"}
    status_label = {"consistent": "✓ same", "partial": "~ close", "differs": "✗ differs", "n/a": "—"}

    def esc(s: str) -> str:
        return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))

    # ── header ──────────────────────────────────────────────────────────────
    html = ["""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>DIALS Run Comparison</title>
<style>
  body { font-family: system-ui, sans-serif; max-width: 1100px; margin: 2rem auto; padding: 0 1rem; color: #212121; }
  h1   { color: #1565c0; }
  h2   { color: #37474f; border-bottom: 1px solid #cfd8dc; padding-bottom: .3rem; margin-top: 2rem; }
  table { border-collapse: collapse; width: 100%; margin-top: 1rem; }
  th, td { padding: .5rem .75rem; border: 1px solid #cfd8dc; text-align: left; }
  th { background: #eceff1; font-weight: 600; }
  tr:nth-child(even) { background: #f9fafb; }
  .consistent { color: #2e7d32; font-weight: 600; }
  .partial    { color: #e65100; font-weight: 600; }
  .differs    { color: #c62828; font-weight: 600; }
  .na         { color: #757575; }
  .badge-ok   { background: #e8f5e9; border-radius: 4px; padding: 2px 6px; }
  .badge-warn { background: #fff3e0; border-radius: 4px; padding: 2px 6px; }
  .badge-err  { background: #ffebee; border-radius: 4px; padding: 2px 6px; }
  pre  { background: #f5f5f5; padding: 1rem; border-radius: 4px; overflow-x: auto; }
  ul   { margin-top: .5rem; }
  .summary { background: #f1f8e9; border-left: 4px solid #7cb342; padding: 1rem; border-radius: 4px; }
</style>
</head>
<body>
"""]

    html.append(f"<h1>DIALS Run Comparison</h1>\n<p>Comparing <strong>{len(result.runs)}</strong> processing runs.</p>\n")

    # ── runs overview ────────────────────────────────────────────────────────
    html.append("<h2>Runs</h2><ul>")
    for r in result.runs:
        status = "✓ complete" if r.workflow_complete else f"→ {r.final_stage}"
        html.append(f"  <li><strong>{esc(r.label)}</strong>: <code>{esc(r.directory)}</code> ({esc(status)})</li>")
    html.append("</ul>")

    # ── metrics table ────────────────────────────────────────────────────────
    html.append("<h2>Metrics</h2>")
    html.append("<table><thead><tr><th>Metric</th>")
    for run in result.runs:
        html.append(f"<th>{esc(run.label)}</th>")
    html.append("<th>Status</th></tr></thead><tbody>")

    for metric_name, values in result.metrics_table.items():
        if all(v is None for v in values):
            continue
        status = result.consistency.get(metric_name, "n/a")
        css = {"consistent": "consistent", "partial": "partial", "differs": "differs"}.get(status, "na")
        badge = {"consistent": "badge-ok", "partial": "badge-warn", "differs": "badge-err"}.get(status, "")
        label = status_label.get(status, status)

        html.append("<tr>")
        html.append(f"  <td>{esc(metric_name)}</td>")
        for v in values:
            cell = esc(_format_value(v))
            if status == "differs":
                cell = f'<span class="differs">{cell}</span>'
            elif status == "partial":
                cell = f'<span class="partial">{cell}</span>'
            html.append(f"  <td>{cell}</td>")
        html.append(f'  <td><span class="{css} {badge}">{esc(label)}</span></td>')
        html.append("</tr>")

    html.append("</tbody></table>")

    # ── commands ─────────────────────────────────────────────────────────────
    if any(r.commands for r in result.runs):
        html.append("<h2>Commands Executed</h2><table><thead><tr><th>Run</th><th>#</th><th>Sequence</th></tr></thead><tbody>")
        for run in result.runs:
            cmd_names = [c.split()[0] for c in run.commands] if run.commands else []
            seq = " → ".join(esc(c) for c in cmd_names) if cmd_names else "—"
            html.append(f"<tr><td><strong>{esc(run.label)}</strong></td><td>{len(run.commands)}</td><td><code>{seq}</code></td></tr>")
        html.append("</tbody></table>")

    # ── dials.report links ───────────────────────────────────────────────────
    if result.report_html:
        html.append("<h2>DIALS Reports</h2><ul>")
        for run, rpt_html, err in zip(result.runs, result.report_html, result.report_errors):
            if rpt_html:
                name = esc(Path(rpt_html).name)
                html.append(f'  <li><strong>{esc(run.label)}</strong>: <a href="{esc(rpt_html)}">{name}</a></li>')
            else:
                html.append(f'  <li><strong>{esc(run.label)}</strong>: not generated ({esc(err or "unknown error")})</li>')
        html.append("</ul>")

    # ── summary ──────────────────────────────────────────────────────────────
    html.append(f'<h2>Summary</h2><div class="summary"><pre>{esc(result.summary)}</pre></div>')

    html.append("</body></html>")
    return "\n".join(html)


def save_comparison_html(result: ComparisonResult, filepath: str) -> None:
    """Write the comparison as a self-contained HTML file."""
    Path(filepath).write_text(display_comparison_html(result), encoding="utf-8")
