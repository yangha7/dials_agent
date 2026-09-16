"""
Tests for the pure-Python parts of dials/scripts/centring_vs_pseudocentring_check.py
and dials/scripts/_systematic_rows.py.

`main()` needs a real DIALS environment (dxtbx/dials imports) and is only
exercised manually via dials.python/cctbx.python -- see the module docstring
and version history for how it was validated against synthetic reflection
data at realistic scale. Everything below it (row grouping, the lag-1/lag-2
variance-ratio statistic, the weak-group I/sigma(I) classification, and the
verdict text) needs only numpy/scipy, so it's covered here directly.
"""
import sys
from pathlib import Path

import numpy as np
import pytest

scripts_dir = Path(__file__).parent.parent / "dials" / "scripts"
sys.path.insert(0, str(scripts_dir))

pytest.importorskip("scipy")

import centring_vs_pseudocentring_check as cpc  # noqa: E402
from _systematic_rows import iter_systematic_rows  # noqa: E402


def make_lattice(n_side=15, res_cutoff2=200):
    hkls = []
    for h in range(-n_side, n_side + 1):
        for k in range(-n_side, n_side + 1):
            for l in range(-n_side, n_side + 1):
                if h == k == l == 0:
                    continue
                if h * h + k * k + l * l < res_cutoff2:
                    hkls.append((h, k, l))
    return np.array(hkls)


def build_dataset(mode: str, seed: int = 42):
    rng = np.random.default_rng(seed)
    hkls = make_lattice()
    res = np.sqrt((hkls ** 2).sum(axis=1))

    if mode == "pure_noise":
        intensities = rng.normal(1000, 100, size=len(hkls))
    else:
        intensities = 5000 * np.exp(-res / 8.0) + 50
        is_even_l = (hkls[:, 2] % 2 == 0)
        if mode == "true_centring":
            intensities[is_even_l] = rng.normal(0, 15, size=is_even_l.sum())
        elif mode == "pseudo_centring":
            intensities[is_even_l] *= 0.15
        elif mode != "smooth_falloff":
            raise ValueError(mode)

    variances = np.clip(np.abs(intensities) * 3 + 400, 100, None)
    noisy = intensities + rng.normal(0, np.sqrt(variances))
    return hkls, noisy, variances


def analyze(hkls, intensities, variances):
    rows_by_family = {}
    for family_name, _fixed, varying_values, mask in iter_systematic_rows(
        hkls, min_points=cpc.MIN_POINTS_PER_ROW
    ):
        rows_by_family.setdefault(family_name, []).append(
            (varying_values, intensities[mask], variances[mask])
        )
    return {name: cpc.analyze_family(rows) for name, rows in rows_by_family.items()}


PSEUDO_TRANSLATION_FAMILY = "h,k fixed (rows along c*)"  # varies l, matching the synthetic parity effect


class TestBuildValueMapAndLaggedDiffs:
    def test_averages_duplicate_indices(self):
        vmap = cpc.build_value_map(np.array([1, 1, 2]), np.array([10.0, 20.0, 100.0]))
        assert vmap == {1: 15.0, 2: 100.0}

    def test_lag1_and_lag2_pairs(self):
        vmap = {0: 10.0, 1: 20.0, 2: 12.0, 4: 40.0}
        # lag-1: only (0,1) and (1,2) are adjacent; (2,4) has a gap of 2, not 1.
        assert sorted(cpc.lagged_diffs(vmap, 1)) == sorted([20.0 - 10.0, 12.0 - 20.0])
        # lag-2: (0,2) and (2,4) are two apart; (1,3) isn't present (no v=3).
        assert sorted(cpc.lagged_diffs(vmap, 2)) == sorted([12.0 - 10.0, 40.0 - 12.0])


class TestPooledVarianceRatio:
    def test_pure_noise_ratio_near_one_not_significant(self):
        rng = np.random.default_rng(0)
        lag1 = rng.normal(0, 10, 5000)
        lag2 = rng.normal(0, 10, 5000)
        result = cpc.pooled_variance_ratio(lag1, lag2)
        assert 0.85 < result["variance_ratio"] < 1.18
        assert result["p_value"] > 0.01

    def test_large_lag1_variance_is_significant(self):
        rng = np.random.default_rng(0)
        lag1 = rng.normal(0, 100, 5000)  # much more variable
        lag2 = rng.normal(0, 10, 5000)
        result = cpc.pooled_variance_ratio(lag1, lag2)
        assert result["variance_ratio"] > 50
        assert result["p_value"] < 1e-6

    def test_too_few_points_returns_null_result(self):
        result = cpc.pooled_variance_ratio(np.array([1.0, 2.0]), np.array([1.0, 2.0, 3.0]))
        assert result["variance_ratio"] == 1.0
        assert result["p_value"] == 1.0


class TestAnalyzeFamilyEndToEnd:
    """
    Full realistic-scale validation (the same synthetic scenarios used
    during development): pure noise and a smooth resolution fall-off must
    NOT be flagged on any axis; true- and pseudo-centring-shaped data must
    be flagged specifically on the axis carrying the parity effect (and
    only that axis), with the weak set correctly classified.
    """

    def test_pure_noise_not_flagged_on_any_axis(self):
        hkls, intensities, variances = build_dataset("pure_noise")
        by_family = analyze(hkls, intensities, variances)
        assert not any(r["flagged"] for r in by_family.values())

    def test_smooth_falloff_not_flagged_on_any_axis(self):
        hkls, intensities, variances = build_dataset("smooth_falloff")
        by_family = analyze(hkls, intensities, variances)
        assert not any(r["flagged"] for r in by_family.values())

    def test_true_centring_flagged_only_on_pseudo_translation_axis(self):
        hkls, intensities, variances = build_dataset("true_centring")
        by_family = analyze(hkls, intensities, variances)
        assert by_family[PSEUDO_TRANSLATION_FAMILY]["flagged"] is True
        for name, result in by_family.items():
            if name != PSEUDO_TRANSLATION_FAMILY:
                assert result["flagged"] is False
        # weak set should look like a genuine systematic absence
        assert by_family[PSEUDO_TRANSLATION_FAMILY]["weak_mean_i_over_sigma"] < 3.0

    def test_pseudo_centring_flagged_only_on_pseudo_translation_axis(self):
        hkls, intensities, variances = build_dataset("pseudo_centring")
        by_family = analyze(hkls, intensities, variances)
        assert by_family[PSEUDO_TRANSLATION_FAMILY]["flagged"] is True
        for name, result in by_family.items():
            if name != PSEUDO_TRANSLATION_FAMILY:
                assert result["flagged"] is False
        # weak set should look clearly non-zero/significant, not an absence
        assert by_family[PSEUDO_TRANSLATION_FAMILY]["weak_mean_i_over_sigma"] > 3.0


class TestVerdictText:
    def test_no_verdict_when_not_flagged(self):
        assert cpc.verdict_for_family("some axis", {"flagged": False}) is None

    def test_true_centring_verdict_mentions_true_centring(self):
        result = {
            "flagged": True, "variance_ratio": 50.0, "p_value": 1e-20,
            "n_lag1": 800, "n_lag2": 800, "weak_mean_i_over_sigma": 0.5,
        }
        text = cpc.verdict_for_family("h,k fixed (rows along c*)", result)
        assert "TRUE centring" in text
        assert "PSEUDO" not in text.split("TRUE centring")[0]  # TRUE mentioned first/primarily

    def test_pseudo_centring_verdict_mentions_pseudo_centring(self):
        result = {
            "flagged": True, "variance_ratio": 50.0, "p_value": 1e-20,
            "n_lag1": 800, "n_lag2": 800, "weak_mean_i_over_sigma": 7.0,
        }
        text = cpc.verdict_for_family("h,k fixed (rows along c*)", result)
        assert "PSEUDO-centring" in text

    def test_missing_snr_gives_hedged_verdict(self):
        result = {"flagged": True, "variance_ratio": 50.0, "p_value": 1e-20, "n_lag1": 800, "n_lag2": 800}
        text = cpc.verdict_for_family("axis", result)
        assert "Could not assess" in text
