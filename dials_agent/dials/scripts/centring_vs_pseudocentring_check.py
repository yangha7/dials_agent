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
    decisive_test = (
        "This I/sigma(I) reading is a rough first-pass signal, NOT decisive on its own -- real "
        "systematic absences are rarely perfectly zero in practice (dynamical scattering, "
        "detector background, and imperfect crystal symmetry all leave some residual signal), "
        "so even a clearly-nonzero I/sigma(I) does not rule out true centring. The actual "
        "decisive test: dials.refine_bravais_settings only ever finds SUBGROUPS of the cell "
        "it's given -- it will show no centred candidates here regardless of which case this "
        "is, because the current cell was never reindexed toward that hypothesis. Explicitly "
        f"test it: dials.reindex with the centred space group matching this axis ('{family_name}'), "
        "THEN re-run dials.refine_bravais_settings on that reindexed result (centred candidates "
        "can only appear once the input cell's own metric symmetry admits them), THEN compare "
        "real refinement R-factors between the primitive and centred settings -- as the tutorial "
        "does (C222₁ there won on R-cryst/R-free, not on an intensity threshold). Do not treat "
        "an absence of centred candidates from the ORIGINAL, untransformed cell as evidence "
        "either way."
    )
    if weak_snr is None:
        return base + " Could not assess the weak set's I/sigma(I). " + decisive_test
    if weak_snr < 3.0:
        return (
            base + f" The weak reflections have mean I/sigma(I) ~= {weak_snr:.1f} -- weak enough "
            "to be consistent with genuine systematic absences (tentatively leaning TRUE "
            "centring), though this reading alone is not conclusive. " + decisive_test
        )
    return (
        base + f" The weak reflections have mean I/sigma(I) ~= {weak_snr:.1f} -- clearly above "
        "background/noise (tentatively leaning PSEUDO-centring, a real but approximate extra "
        "translation), though this reading alone is not conclusive. " + decisive_test
    )


# Column indices (h, k, l) that sum to test each named lattice centering's
# systematic-absence condition: "allowed" when the sum is even.
NAMED_CENTERING_CONDITIONS = {
    "A": (1, 2),   # k+l even
    "B": (0, 2),   # h+l even
    "C": (0, 1),   # h+k even
    "I": (0, 1, 2),  # h+k+l even
}


def test_named_centering_condition(
    miller_indices: np.ndarray, intensities: np.ndarray, variances: np.ndarray, condition: str
) -> dict:
    """
    Directly test one specific named centering's systematic-absence condition
    against real intensities: split reflections into "allowed" (sum of the
    relevant indices even) and "forbidden" (odd) groups and compare their
    mean intensity and I/sigma(I).

    This is deliberately a separate, explicit function with its own test
    coverage -- exactly the kind of small ad hoc calculation that's easy to
    get subtly wrong under time pressure (a real instance found live-testing:
    building the even/odd mask correctly but then computing both group means
    from the *unmasked* array, silently turning the whole test into a
    no-op comparison of the data against itself).
    """
    if condition not in NAMED_CENTERING_CONDITIONS:
        raise ValueError(f"Unknown centering condition '{condition}', expected one of {sorted(NAMED_CENTERING_CONDITIONS)}")
    cols = NAMED_CENTERING_CONDITIONS[condition]
    combo = miller_indices[:, cols].sum(axis=1)
    parity = combo % 2
    allowed = parity == 0
    forbidden = parity == 1

    result = {
        "condition": condition,
        "n_allowed": int(allowed.sum()),
        "n_forbidden": int(forbidden.sum()),
    }
    if not allowed.any() or not forbidden.any():
        result["error"] = "one of the two groups is empty -- cannot compare"
        return result

    sig = np.sqrt(np.clip(variances, 1e-12, None))
    allowed_mean_i = float(intensities[allowed].mean())
    forbidden_mean_i = float(intensities[forbidden].mean())
    result.update({
        "allowed_mean_intensity": allowed_mean_i,
        "forbidden_mean_intensity": forbidden_mean_i,
        "forbidden_mean_i_over_sigma": float(np.mean(intensities[forbidden] / sig[forbidden])),
        "allowed_mean_i_over_sigma": float(np.mean(intensities[allowed] / sig[allowed])),
        "forbidden_to_allowed_ratio": (forbidden_mean_i / allowed_mean_i) if allowed_mean_i != 0 else None,
    })
    return result


def verify_all_centerings(miller_indices: np.ndarray, intensities: np.ndarray, variances: np.ndarray) -> dict:
    """Run `test_named_centering_condition` for all four centering types (A/B/C/I)."""
    return {
        cond: test_named_centering_condition(miller_indices, intensities, variances, cond)
        for cond in NAMED_CENTERING_CONDITIONS
    }


def main(expt_path: str, refl_path: str, verify_centering: bool = False) -> dict:
    from dials.array_family import flex
    from dxtbx.model.experiment_list import ExperimentListFactory

    experiments = ExperimentListFactory.from_json_file(expt_path, check_format=False)
    reflections = flex.reflection_table.from_file(refl_path)

    # Select on the flag matching whichever intensity column we're about to use, NOT
    # `indexed`. A real bug found live: `indexed` marks the original strong-spot list
    # used for orientation during dials.index -- a subset that is itself biased toward
    # STRONG reflections, since that's how spot-finding/indexing selects candidates in
    # the first place. Systematic absences are, by definition, weak -- so filtering an
    # intensity-based absence test to the indexed subset systematically under-samples
    # exactly the reflections the test is trying to characterize. Confirmed
    # empirically: on a real dataset, this made a genuine systematic absence (full
    # population: I/sigma(I) ~ 0.15, 46% negative, cleanly split 50/50 by parity) look
    # like a much weaker, ambiguous signal (indexed-only subset: I/sigma(I) ~ 8.4, only
    # 12% of the expected population present at all) -- enough to flag the wrong
    # category (pseudo- vs. true centring). `integrated`/`integrated_prf`/
    # `integrated_sum` reflect the full predicted-and-measured population regardless of
    # strength, which is what an intensity-based test needs.
    if "intensity.prf.value" in reflections and "intensity.prf.variance" in reflections:
        intensity_col, variance_col, source = "intensity.prf.value", "intensity.prf.variance", "profile-fitted"
        integration_flag = reflections.flags.integrated_prf
    elif "intensity.sum.value" in reflections and "intensity.sum.variance" in reflections:
        intensity_col, variance_col, source = "intensity.sum.value", "intensity.sum.variance", "summed"
        integration_flag = reflections.flags.integrated_sum
    else:
        return {
            "error": "No intensity.prf.* or intensity.sum.* columns found -- run after "
                     "dials.integrate (or at least dials.find_spots/dials.index)."
        }

    sel = reflections.get_flags(integration_flag)
    if sel.count(True) == 0:
        # Not yet integrated (e.g. called on indexed.refl/strong.refl before
        # dials.integrate has run) -- integrated_prf/integrated_sum will never be set
        # in that case. Fall back to `indexed` so the documented pre-integration mode
        # (cruder spot-finding intensities) still works, rather than silently
        # returning zero reflections.
        sel = reflections.get_flags(reflections.flags.indexed)
    reflections = reflections.select(sel)

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

        crystal_result = {
            "n_analyzed_reflections": int(len(sub)),
            "intensity_source": source,
            "by_family": by_family,
            "verdict": overall_verdict,
        }
        if verify_centering:
            crystal_result["named_centering_tests"] = verify_all_centerings(miller_indices, intensities, variances)
        results_by_crystal[str(crystal_id)] = crystal_result

    return {"n_crystals": len(results_by_crystal), "crystals": results_by_crystal}


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--verify-centering"]
    verify = "--verify-centering" in sys.argv[1:]
    if len(args) != 2:
        print(json.dumps({
            "error": "usage: centring_vs_pseudocentring_check.py <indexed.expt> <indexed.refl> [--verify-centering]"
        }))
        sys.exit(1)
    result = main(args[0], args[1], verify_centering=verify)
    print(json.dumps(result, indent=2))
