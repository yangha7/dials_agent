"""
Reciprocal-lattice linearity/spiral check -- numeric, no rendering.

Run with DIALS's own Python (e.g. `dials.python`), which has dxtbx/dials/cctbx
on sys.path:

    dials.python reciprocal_lattice_linearity.py indexed.expt indexed.refl

Prints a single JSON object to stdout summarizing, per crystal, whether the
observed reciprocal-lattice points fall on straight lines (good geometry),
show static (phi-independent) curvature (a likely model/geometry error, e.g.
wrong unit cell or detector distance), or show curvature that is locked to
rotation angle -- a "spiral" (classic signature of the crystal or beam
actually moving/drifting during the rotation, or a wrong beam centre).

Method
------
A true reciprocal lattice is rlp(h,k,l) = h*a* + k*b* + l*c*: an exactly
linear function of the integer Miller indices. So for a "systematic row"
(fix two of the three indices, vary the third), the *observed* rlp
positions of the matching reflections should fall on a perfectly straight
line if the experimental geometry is correctly modelled -- regardless of
what the crystal's true unit cell actually is. This makes the check
model-free: it never needs to know the "correct" a*/b*/c*, only whether the
data are self-consistent with *some* straight lattice.

For each systematic row we fit a straight line via total least squares
(SVD) and compute:
  - normalized_straightness: RMS perpendicular residual / row span.
    ~0 for a well-modelled dataset; grows with any curvature.
  - phi_correlation_r2: how well the residual's perpendicular *direction*
    is predicted by (cos(phi), sin(phi)) of each reflection's rotation
    angle. ~0 means noise or a static (phi-independent) bend; close to 1
    means the bend rotates coherently with phi -- a spiral.

Results are aggregated per crystal (reflections['id']) and per row family
(rows along each of the three index directions).
"""
import json
import sys

import numpy as np

from _systematic_rows import MIN_POINTS_PER_ROW, iter_systematic_rows


def fit_line_residuals(points: np.ndarray):
    centroid = points.mean(axis=0)
    centered = points - centroid
    _, _, vt = np.linalg.svd(centered, full_matrices=False)
    direction = vt[0]
    proj_lengths = centered @ direction
    proj = np.outer(proj_lengths, direction)
    residual_vectors = centered - proj
    rms_residual = float(np.sqrt((residual_vectors ** 2).sum(axis=1).mean()))
    span = float(proj_lengths.max() - proj_lengths.min())
    return rms_residual, span, residual_vectors, direction


def phi_correlation(residual_vectors: np.ndarray, phis: np.ndarray, direction: np.ndarray) -> float:
    if np.ptp(phis) < 1e-6:
        return 0.0
    tmp = np.array([1.0, 0.0, 0.0]) if abs(direction[0]) < 0.9 else np.array([0.0, 1.0, 0.0])
    perp1 = np.cross(direction, tmp)
    perp1 /= np.linalg.norm(perp1)
    perp2 = np.cross(direction, perp1)

    a = residual_vectors @ perp1
    b = residual_vectors @ perp2
    cosphi, sinphi = np.cos(phis), np.sin(phis)

    def r2(y, x1, x2):
        X = np.column_stack([x1, x2, np.ones_like(x1)])
        coef, *_ = np.linalg.lstsq(X, y, rcond=None)
        pred = X @ coef
        ss_res = ((y - pred) ** 2).sum()
        ss_tot = ((y - y.mean()) ** 2).sum()
        return 0.0 if ss_tot < 1e-30 else float(1 - ss_res / ss_tot)

    return 0.5 * (r2(a, cosphi, sinphi) + r2(b, cosphi, sinphi))


def analyze_row(points: np.ndarray, phis: np.ndarray) -> dict:
    rms, span, resid, direction = fit_line_residuals(points)
    return {
        "n_points": int(len(points)),
        "rms_residual": rms,
        "span": span,
        "normalized_straightness": (rms / span) if span > 0 else 0.0,
        "phi_correlation_r2": phi_correlation(resid, phis, direction),
    }


def systematic_rows(miller_indices: np.ndarray, rlp: np.ndarray, phis: np.ndarray):
    """Yield (family_name, fixed_indices, row_stats) for all three families
    of systematic rows (fix two Miller indices, vary the third)."""
    for family_name, fixed_idx, _varying_values, mask in iter_systematic_rows(miller_indices):
        stats = analyze_row(rlp[mask], phis[mask])
        yield family_name, fixed_idx, stats


def summarize(rows: list[dict]) -> dict:
    if not rows:
        return {"n_rows": 0}
    straightness = np.array([r["normalized_straightness"] for r in rows])
    phi_corr = np.array([r["phi_correlation_r2"] for r in rows])
    # Robust, dataset-relative flagging threshold rather than a hardcoded
    # absolute cutoff -- straightness scale depends on unit cell/resolution.
    median = float(np.median(straightness))
    mad = float(np.median(np.abs(straightness - median))) or 1e-9
    threshold = median + 6 * mad
    flagged = straightness > threshold
    return {
        "n_rows": len(rows),
        "median_normalized_straightness": median,
        "mean_normalized_straightness": float(straightness.mean()),
        "fraction_rows_flagged_nonlinear": float(flagged.mean()),
        "mean_phi_correlation_r2_of_flagged": (
            float(phi_corr[flagged].mean()) if flagged.any() else 0.0
        ),
        "mean_phi_correlation_r2_overall": float(phi_corr.mean()),
    }


def verdict(summary: dict) -> str:
    if summary.get("n_rows", 0) == 0:
        return "Not enough systematic rows with sufficient points to assess linearity."
    frac_flagged = summary["fraction_rows_flagged_nonlinear"]
    phi_r2 = summary["mean_phi_correlation_r2_of_flagged"]
    if frac_flagged < 0.05:
        return "Reciprocal lattice rows are straight and consistent -- no evidence of a geometry-modelling problem."
    if phi_r2 > 0.5:
        return (
            "Reciprocal lattice rows show curvature that correlates strongly with rotation "
            "angle (a 'spiral'). This is a classic signature of the crystal or beam actually "
            "moving/drifting during the rotation, or an incorrect beam centre. Try "
            "dials.search_beam_position imported.expt strong.refl and re-index/re-refine."
        )
    return (
        "Reciprocal lattice rows show curvature that does NOT correlate with rotation angle "
        "(a static bend, not a spiral). This points to a fixed geometry/model error -- e.g. an "
        "incorrect unit cell, detector distance, or detector tilt -- rather than motion during "
        "the scan. Consider dials.search_beam_position as a first check, and inspect the "
        "detector/crystal model parameters."
    )


def main(expt_path: str, refl_path: str) -> dict:
    from dials.array_family import flex
    from dxtbx.model.experiment_list import ExperimentListFactory

    experiments = ExperimentListFactory.from_json_file(expt_path, check_format=False)
    reflections = flex.reflection_table.from_file(refl_path)

    sel = reflections.get_flags(reflections.flags.indexed)
    reflections = reflections.select(sel)

    if "rlp" not in reflections:
        if "xyzobs.mm.value" not in reflections:
            reflections.centroid_px_to_mm(experiments)
        reflections.map_centroids_to_reciprocal_space(experiments)

    results_by_crystal = {}
    ids = reflections["id"]
    for crystal_id in sorted(set(ids)):
        crystal_sel = ids == crystal_id
        sub = reflections.select(crystal_sel)
        if len(sub) < MIN_POINTS_PER_ROW:
            continue

        miller_indices = np.array(sub["miller_index"], dtype=np.int64)
        rlp = np.array(sub["rlp"], dtype=np.float64)
        phis = np.array(sub["xyzobs.mm.value"], dtype=np.float64)[:, 2]

        all_rows = []
        by_family = {}
        for family_name, fixed_idx, stats in systematic_rows(miller_indices, rlp, phis):
            all_rows.append(stats)
            by_family.setdefault(family_name, []).append(stats)

        summary = summarize(all_rows)
        results_by_crystal[str(crystal_id)] = {
            "n_indexed_reflections": int(len(sub)),
            "summary": summary,
            "by_family": {name: summarize(rows) for name, rows in by_family.items()},
            "verdict": verdict(summary),
        }

    return {"n_crystals": len(results_by_crystal), "crystals": results_by_crystal}


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(json.dumps({"error": "usage: reciprocal_lattice_linearity.py <indexed.expt> <indexed.refl>"}))
        sys.exit(1)
    result = main(sys.argv[1], sys.argv[2])
    print(json.dumps(result, indent=2))
