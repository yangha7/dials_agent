"""
Centring vs. pseudo-centring check -- numeric, no rendering.

Run with DIALS's own Python (e.g. `dials.python`), which has dxtbx/dials/cctbx
on sys.path:

    dials.python centring_vs_pseudocentring_check.py indexed.expt indexed.refl

Prints a single JSON object to stdout. Grounded in the DIALS "Centring vs.
Pseudo-centring" tutorial (dials.github.io/documentation/tutorials/
centring_vs_pseudocentring.html): a hidden translational pseudo-symmetry
shows up as reflections along one systematic-row direction alternating
between strong and weak (weak but *not exactly absent* -- unlike true
centring, where the equivalent reflections are absent altogether). In the
reciprocal lattice viewer this looks like "alternating long and short
lines" along one axis; in the image viewer, "spots with even l are
systematically weaker than spots with odd l" with the two sets also
differing in spot profile.

Method
------
For each systematic row (fix two Miller indices, vary the third -- same
grouping as `reciprocal_lattice_linearity.py`, factored out into
`_systematic_rows.py`), compare two kinds of intensity difference:

  - lag-1: I(v+1) - I(v), between *adjacent* integer values of the varying
    index (opposite parity of each other).
  - lag-2: I(v+2) - I(v), between values two apart (*same* parity).

A period-2 alternation (strong/weak/strong/weak...) makes lag-1
differences huge (strong vs. weak) while lag-2 differences stay small
(same phase each time) -- so its variance ratio var(lag-1)/var(lag-2) is
large. A smooth resolution-dependent fall-off does the opposite (points
twice as far apart differ about twice as much), giving a ratio well below
1. Pure noise with no structure at all gives a ratio near 1.

An earlier version of this script instead detrended each row with a
low-order polynomial fit and looked at the lag-1 autocorrelation of the
residuals. That turned out to have a real bug: fitting a polynomial to as
few as ~10-20 noisy points and then examining its own residuals is
overfitting, which *artificially induces negative autocorrelation between
neighbouring residuals even for pure random noise with no real structure
at all* -- a false positive, confirmed with a synthetic pure-noise test.
The lag-1-vs-lag-2 variance-ratio approach above needs no curve fitting at
all, so it doesn't have that failure mode (also confirmed with the same
synthetic tests -- see the version history / commit message for numbers).

We pool the lag-1 and lag-2 difference samples across every row in a
family (typically thousands of pairs, not the ~10-20 in any single row)
and use an F-test on the pooled variance ratio, since a single row's own
estimate is too noisy to trust in isolation. Once a family's ratio is
significant, we also pool intensities by parity across that whole family
to find the systematically weaker set and report its mean I/sigma(I): low
(roughly <3) looks like TRUE centring (systematic absence), clearly above
that looks like PSEUDO-centring (weak but real) -- the actual distinction
the tutorial is teaching.

This does not attempt to determine or suggest a specific space group by
itself -- that still needs dials.refine_bravais_settings and the user's
judgment (as in the tutorial). It only reports whether the alternation
signature is present, along which axis, and which of the two categories
the intensity pattern is more consistent with.
"""
import json
import sys

import numpy as np

from _systematic_rows import iter_systematic_rows

MIN_POINTS_PER_ROW = 6  # need a reasonable number of both parities
# One-sided F-test p-value threshold for a family's pooled lag1/lag2
# variance ratio. Deliberately stringent, since this feeds into a real
# space-group decision and pooled sample sizes are typically large enough
# that even a very strict threshold still catches a real effect easily.
P_VALUE_THRESHOLD = 1e-6


def build_value_map(varying_values: np.ndarray, intensities: np.ndarray) -> dict:
    """Average intensity per unique integer value of the varying index
    (collapses any duplicate observations of the same Miller index)."""
    uniq_v, inverse = np.unique(varying_values, return_inverse=True)
    sums = np.bincount(inverse, weights=intensities)
    counts = np.bincount(inverse)
    means = sums / counts
    return dict(zip(uniq_v.astype(int).tolist(), means.tolist()))


def lagged_diffs(value_map: dict, lag: int) -> list:
    return [value_map[v + lag] - i_v for v, i_v in value_map.items() if (v + lag) in value_map]


def pooled_variance_ratio(lag1_all: np.ndarray, lag2_all: np.ndarray) -> dict:
    from scipy import stats

    n1, n2 = len(lag1_all), len(lag2_all)
    if n1 < 20 or n2 < 20:
        return {"n_lag1": n1, "n_lag2": n2, "variance_ratio": 1.0, "p_value": 1.0}

    var1 = float(np.var(lag1_all, ddof=1))
    var2 = float(np.var(lag2_all, ddof=1))
    if var2 < 1e-12:
        ratio = float("inf") if var1 > 1e-12 else 1.0
    else:
        ratio = var1 / var2

    # One-sided F-test: H0 is var1 <= var2 (no alternation); large ratio is evidence against H0.
    p_value = float(stats.f.sf(ratio, n1 - 1, n2 - 1)) if np.isfinite(ratio) else 0.0
    return {"n_lag1": n1, "n_lag2": n2, "variance_ratio": float(ratio) if np.isfinite(ratio) else None, "p_value": p_value}


def family_weak_group_snr(varying_values_list: list, intensities_list: list, variances_list: list) -> "dict | None":
    """
    Pool intensities (and variances) by parity of the varying index across
    an entire row family, identify the systematically weaker parity, and
    return its pooled mean I/sigma(I).
    """
    if not varying_values_list:
        return None
    v_all = np.concatenate(varying_values_list)
    i_all = np.concatenate(intensities_list)
    var_all = np.concatenate(variances_list)
    even_mask = (v_all % 2 == 0)
    if not even_mask.any() or not (~even_mask).any():
        return None
    even_mean = i_all[even_mask].mean()
    odd_mean = i_all[~even_mask].mean()
    weak_mask = even_mask if even_mean < odd_mean else ~even_mask
    sig = np.sqrt(np.clip(var_all[weak_mask], 1e-12, None))
    return {
        "weak_parity": "even" if even_mean < odd_mean else "odd",
        "weak_mean_i_over_sigma": float(np.mean(i_all[weak_mask] / sig)),
        "strong_mean_intensity": float(max(even_mean, odd_mean)),
        "weak_mean_intensity": float(min(even_mean, odd_mean)),
    }


def analyze_family(rows: list) -> dict:
    """rows: list of (varying_values, intensities, variances) for every row in one family."""
    lag1_all, lag2_all = [], []
    for varying_values, intensities, _variances in rows:
        vmap = build_value_map(varying_values, intensities)
        lag1_all.extend(lagged_diffs(vmap, 1))
        lag2_all.extend(lagged_diffs(vmap, 2))

    ratio_result = pooled_variance_ratio(np.array(lag1_all), np.array(lag2_all))
    result = {"n_rows": len(rows), **ratio_result}

    is_significant_alternation = (
        ratio_result["variance_ratio"] is not None
        and ratio_result["variance_ratio"] > 1.0
        and ratio_result["p_value"] < P_VALUE_THRESHOLD
    )
    result["flagged"] = bool(is_significant_alternation)

    if is_significant_alternation:
        snr_info = family_weak_group_snr(
            [r[0] for r in rows], [r[1] for r in rows], [r[2] for r in rows]
        )
        if snr_info:
            result.update(snr_info)
    return result


def verdict_for_family(family_name: str, result: dict) -> "str | None":
    if not result.get("flagged"):
        return None
    weak_snr = result.get("weak_mean_i_over_sigma")
    ratio = result["variance_ratio"]
    base = (
        f"Rows along '{family_name}' show a statistically significant intensity alternation "
        f"(lag-1/lag-2 variance ratio {ratio:.1f}, p={result['p_value']:.1e}, pooled from "
        f"{result['n_lag1']} lag-1 and {result['n_lag2']} lag-2 observations) -- consistent "
        "with the 'alternating long and short lines' pattern in the reciprocal lattice viewer "
        "and 'spots with even/odd index systematically weaker' in the image viewer (see "
        "DIALS's 'Centring vs. Pseudo-centring' tutorial)."
    )
    if weak_snr is None:
        return base + " Could not assess whether the weak set is absent or just weak."
    if weak_snr < 3.0:
        return (
            base + f" The weak reflections have mean I/sigma(I) ~= {weak_snr:.1f} -- consistent "
            "with genuine systematic absences: this looks like TRUE centring. Consider "
            "dials.refine_bravais_settings to find the correct centred setting, then "
            "dials.reindex to that space group."
        )
    return (
        base + f" The weak reflections have mean I/sigma(I) ~= {weak_snr:.1f} -- clearly above "
        "background/noise, not consistent with true absences: this looks like PSEUDO-centring "
        "(a real but approximate extra translation, not exact symmetry). Reindexing to the "
        "higher-symmetry centred setting and discarding these as absent would be wrong -- verify "
        "carefully with dials.refine_bravais_settings and compare refinement statistics (as in "
        "the tutorial) before deciding."
    )


def main(expt_path: str, refl_path: str) -> dict:
    from dials.array_family import flex
    from dxtbx.model.experiment_list import ExperimentListFactory

    experiments = ExperimentListFactory.from_json_file(expt_path, check_format=False)
    reflections = flex.reflection_table.from_file(refl_path)

    sel = reflections.get_flags(reflections.flags.indexed)
    reflections = reflections.select(sel)

    if "intensity.prf.value" in reflections and "intensity.prf.variance" in reflections:
        intensity_col, variance_col, source = "intensity.prf.value", "intensity.prf.variance", "profile-fitted"
    elif "intensity.sum.value" in reflections and "intensity.sum.variance" in reflections:
        intensity_col, variance_col, source = "intensity.sum.value", "intensity.sum.variance", "summed"
    else:
        return {
            "error": "No intensity.prf.* or intensity.sum.* columns found -- run after "
                     "dials.integrate (or at least dials.find_spots/dials.index)."
        }

    results_by_crystal = {}
    ids = reflections["id"]
    for crystal_id in sorted(set(ids)):
        crystal_sel = ids == crystal_id
        sub = reflections.select(crystal_sel)
        if len(sub) < MIN_POINTS_PER_ROW:
            continue

        miller_indices = np.array(sub["miller_index"], dtype=np.int64)
        intensities = np.array(sub[intensity_col], dtype=np.float64)
        variances = np.array(sub[variance_col], dtype=np.float64)

        rows_by_family = {}
        for family_name, fixed_idx, varying_values, mask in iter_systematic_rows(
            miller_indices, min_points=MIN_POINTS_PER_ROW
        ):
            rows_by_family.setdefault(family_name, []).append(
                (varying_values, intensities[mask], variances[mask])
            )

        by_family = {name: analyze_family(rows) for name, rows in rows_by_family.items()}
        family_verdicts = [
            v for name, result in by_family.items() if (v := verdict_for_family(name, result))
        ]
        overall_verdict = (
            " ".join(family_verdicts) if family_verdicts else
            "No systematic strong/weak intensity alternation detected along any axis -- no "
            "evidence of hidden translational pseudo-symmetry."
        )

        results_by_crystal[str(crystal_id)] = {
            "n_indexed_reflections": int(len(sub)),
            "intensity_source": source,
            "by_family": by_family,
            "verdict": overall_verdict,
        }

    return {"n_crystals": len(results_by_crystal), "crystals": results_by_crystal}


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(json.dumps({"error": "usage: centring_vs_pseudocentring_check.py <indexed.expt> <indexed.refl>"}))
        sys.exit(1)
    result = main(sys.argv[1], sys.argv[2])
    print(json.dumps(result, indent=2))
