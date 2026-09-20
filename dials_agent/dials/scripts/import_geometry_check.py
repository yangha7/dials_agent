"""
Import geometry sanity check -- numeric, no rendering, no pixel data read.

Run with DIALS's own Python (e.g. `dials.python`), which has dxtbx/dials/cctbx
on sys.path:

    dials.python import_geometry_check.py imported.expt

Prints a single JSON object to stdout. This is the "raw images" equivalent of
`reciprocal_lattice_linearity.py`/`centring_vs_pseudocentring_check.py`: the
agent cannot see `dials.image_viewer`'s rendered output, so this checks the
same things a human's first glance at the image viewer would catch --
implausible beam centre, detector distance, wavelength, or oscillation --
directly from the beam/detector/goniometer/scan *models* already read into
`imported.expt` by `dials.import`. No image pixel data is read at all
(`check_format=False`), so this costs a couple of seconds regardless of
dataset size, dominated entirely by interpreter/dxtbx import startup -- same
cost profile as the other checks in this file's family.

Deliberately scoped to header/geometry only. A pixel-content check (actual
image data: saturation, hot pixels, background level, rough presence of real
diffraction) is a known, separate follow-up -- NOT built here. That one would
need to actually read image data, so unlike this script its cost genuinely
scales with dataset size unless deliberately sampled (a handful of
representative images, not a full scan) -- flagged for later, not started.

Method
------
For each experiment (usually one per imported sweep):
  - Beam centre: does the direct beam actually land on some panel of the
    detector, in pixel coordinates? (dxtbx's own `Panel.is_coord_valid` does
    NOT reliably answer this -- confirmed empirically it returns True well
    outside a panel's physical extent -- so this compares
    `get_beam_centre_px()` against `get_image_size()` directly instead.)
  - Wavelength: within a broad, physically-plausible X-ray range.
  - Detector distance: positive and within a broad plausible range.
  - Oscillation width: flagged only if exactly zero on a genuine rotation
    scan (a `None` scan, i.e. stills data, is not flagged at all -- zero
    width there is correct, not a problem).
  - Achievable resolution: the finest resolution reachable at any panel's
    farthest-from-beam-centre corner; advisory-only (many legitimate
    experiments target low resolution on purpose), not treated as an error.

All thresholds here are broad sanity bounds, not physics -- they exist to
catch header/unit mistakes and gross beam-centre errors (exactly the
"Correcting Poor Initial Geometry" tutorial's failure mode), not to judge
data quality.
"""
import json
import sys


WAVELENGTH_RANGE_ANGSTROM = (0.05, 5.0)
DISTANCE_RANGE_MM = (10.0, 2000.0)
ADVISORY_WORST_RESOLUTION_ANGSTROM = 10.0


def check_beam_centre(beam, detector) -> dict:
    s0 = beam.get_s0()
    panels = []
    on_any_panel = False
    for i, panel in enumerate(detector):
        px, py = panel.get_beam_centre_px(s0)
        width, height = panel.get_image_size()
        in_bounds = 0 <= px < width and 0 <= py < height
        on_any_panel = on_any_panel or in_bounds
        panels.append({
            "panel": i,
            "beam_centre_px": [float(px), float(py)],
            "image_size_px": [int(width), int(height)],
            "in_bounds": in_bounds,
        })
    return {
        "on_any_panel": on_any_panel,
        "flagged": not on_any_panel,
        "panels": panels,
    }


def check_wavelength(beam) -> dict:
    wavelength = beam.get_wavelength()
    lo, hi = WAVELENGTH_RANGE_ANGSTROM
    flagged = not (lo <= wavelength <= hi)
    return {"wavelength_angstrom": float(wavelength), "flagged": flagged}


def check_distance(detector) -> dict:
    panels = []
    flagged = False
    lo, hi = DISTANCE_RANGE_MM
    for i, panel in enumerate(detector):
        distance = panel.get_distance()
        panel_flagged = not (lo <= distance <= hi)
        flagged = flagged or panel_flagged
        panels.append({"panel": i, "distance_mm": float(distance), "flagged": panel_flagged})
    return {"flagged": flagged, "panels": panels}


def check_oscillation(scan) -> "dict | None":
    if scan is None:
        return None
    _, width = scan.get_oscillation()
    return {"oscillation_width_deg": float(width), "flagged": width == 0.0}


def check_achievable_resolution(beam, detector) -> dict:
    s0 = beam.get_s0()
    panels = []
    best_d_min = None
    for i, panel in enumerate(detector):
        width, height = panel.get_image_size()
        corners = [(0, 0), (width, 0), (0, height), (width, height)]
        d_values = [panel.get_resolution_at_pixel(s0, corner) for corner in corners]
        panel_best = min(d_values)
        panels.append({"panel": i, "best_d_min_at_corner_angstrom": float(panel_best)})
        best_d_min = panel_best if best_d_min is None else min(best_d_min, panel_best)
    return {
        "best_d_min_angstrom": float(best_d_min) if best_d_min is not None else None,
        "flagged": best_d_min is not None and best_d_min > ADVISORY_WORST_RESOLUTION_ANGSTROM,
        "panels": panels,
    }


def summarize(checks: dict) -> str:
    problems = []
    if checks["beam_centre"]["flagged"]:
        problems.append(
            "the direct beam does not land on any detector panel -- indexing will very "
            "likely fail or silently mis-index until this is fixed (see "
            "dials.search_beam_position / dials.check_indexing_symmetry after indexing)"
        )
    if checks["wavelength"]["flagged"]:
        problems.append(
            f"wavelength {checks['wavelength']['wavelength_angstrom']:.4g} Angstrom is "
            "outside the typical X-ray range -- check for a units/header parsing mistake"
        )
    if checks["distance"]["flagged"]:
        problems.append(
            "detector distance is outside a plausible range -- check for a units/header "
            "parsing mistake"
        )
    if checks["oscillation"] is not None and checks["oscillation"]["flagged"]:
        problems.append(
            "oscillation width is exactly zero on what looks like a rotation scan -- "
            "downstream indexing/integration assumes a real sweep"
        )
    if checks["achievable_resolution"]["flagged"]:
        problems.append(
            f"even at the panel edges the best achievable resolution is only "
            f"{checks['achievable_resolution']['best_d_min_angstrom']:.1f} Angstrom -- worth "
            "confirming this geometry is intentional (advisory only, not necessarily wrong)"
        )
    if not problems:
        return "Geometry looks sane: beam centre on-detector, wavelength/distance/oscillation all within normal ranges."
    return "Potential geometry problem(s): " + "; ".join(problems) + "."


def main(expt_path: str) -> dict:
    from dxtbx.model.experiment_list import ExperimentListFactory

    experiments = ExperimentListFactory.from_json_file(expt_path, check_format=False)

    results_by_experiment = {}
    for i, experiment in enumerate(experiments):
        beam = experiment.beam
        detector = experiment.detector
        scan = experiment.scan

        checks = {
            "beam_centre": check_beam_centre(beam, detector),
            "wavelength": check_wavelength(beam),
            "distance": check_distance(detector),
            "oscillation": check_oscillation(scan),
            "achievable_resolution": check_achievable_resolution(beam, detector),
        }
        checks["summary"] = summarize(checks)
        results_by_experiment[str(i)] = checks

    return {"n_experiments": len(results_by_experiment), "experiments": results_by_experiment}


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(json.dumps({"error": "usage: import_geometry_check.py <imported.expt>"}))
        sys.exit(1)
    print(json.dumps(main(sys.argv[1]), indent=2))
