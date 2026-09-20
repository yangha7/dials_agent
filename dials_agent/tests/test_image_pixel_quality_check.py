"""
Tests for the pure-numpy parts of dials/scripts/image_pixel_quality_check.py.

`main()` needs a real DIALS environment (dxtbx image reading, check_format=True)
and could not be validated against real image data locally -- this Mac's local
DIALS build has a known, unrelated dxtbx/nxmx bug blocking real-image reads
(see the other numeric checks' test files / memory notes for the same
limitation). Everything below main() needs only numpy, so it's covered here
directly with synthetic pixel arrays.
"""
import sys
from pathlib import Path

import numpy as np

scripts_dir = Path(__file__).parent.parent / "dials" / "scripts"
sys.path.insert(0, str(scripts_dir))

import image_pixel_quality_check as pq  # noqa: E402


class TestPickSampleIndices:
    def test_fewer_images_than_max_returns_all(self):
        assert pq.pick_sample_indices(5, max_samples=12) == [0, 1, 2, 3, 4]

    def test_max_samples_none_means_full_scan(self):
        # The explicit "all" / full-scan mode: escalation for a later-stage
        # problem a quick sample couldn't explain, or a user request for a
        # thorough check -- not the default.
        assert pq.pick_sample_indices(1000, max_samples=None) == list(range(1000))

    def test_more_images_than_max_samples_evenly_including_ends(self):
        indices = pq.pick_sample_indices(1000, max_samples=10)
        assert len(indices) <= 10
        assert indices[0] == 0
        assert indices[-1] == 999
        assert indices == sorted(indices)

    def test_zero_images_returns_empty(self):
        assert pq.pick_sample_indices(0) == []


class TestAnalyzePanelImage:
    def test_all_trusted_pixels_reports_no_untrusted_fraction(self):
        raw = np.full((10, 10), 100.0)
        trusted_mask = np.ones((10, 10), dtype=bool)
        stats = pq.analyze_panel_image(raw, trusted_mask)
        assert stats["fraction_untrusted"] == 0.0
        assert stats["mean_trusted"] == 100.0
        assert stats["max_value"] == 100.0

    def test_some_saturated_pixels_reflected_in_fraction_and_excluded_from_mean(self):
        raw = np.full((10, 10), 50.0)
        raw[0, 0] = 1e9  # a saturated outlier
        trusted_mask = np.ones((10, 10), dtype=bool)
        trusted_mask[0, 0] = False  # the saturated pixel is untrusted
        stats = pq.analyze_panel_image(raw, trusted_mask)
        assert stats["fraction_untrusted"] == 1 / 100
        # The outlier must not pollute the trusted-only mean.
        assert stats["mean_trusted"] == 50.0
        # But it should still show up as the panel's raw max.
        assert stats["max_value"] == 1e9

    def test_no_trusted_pixels_gives_none_means_not_a_crash(self):
        raw = np.full((5, 5), 1e9)
        trusted_mask = np.zeros((5, 5), dtype=bool)
        stats = pq.analyze_panel_image(raw, trusted_mask)
        assert stats["mean_trusted"] is None
        assert stats["median_trusted"] is None
        assert stats["fraction_untrusted"] == 1.0


class TestFindHotPixels:
    def test_too_few_images_sampled_skips_the_check(self):
        masks = [np.zeros((5, 5), dtype=bool)] * 2  # fewer than HOT_PIXEL_MIN_IMAGES
        result = pq.find_hot_pixels(masks, min_images=3)
        assert result["checked"] is False

    def test_pixel_untrusted_in_every_image_is_flagged(self):
        n = 5
        masks = []
        for _ in range(n):
            m = np.zeros((4, 4), dtype=bool)
            m[2, 2] = True  # this pixel is "untrusted" (e.g. saturated) on every image
            masks.append(m)
        result = pq.find_hot_pixels(masks, min_images=3)
        assert result["checked"] is True
        assert result["n_candidate_hot_or_dead_pixels"] == 1
        assert result["fraction_of_panel"] == 1 / 16

    def test_pixel_untrusted_on_only_some_images_is_not_flagged(self):
        # Simulates a real diffraction spot: "untrusted" (e.g. saturated core)
        # on some images but not others, as it moves across the detector --
        # must NOT be confused with a genuine, stationary hot pixel.
        n = 5
        masks = []
        for i in range(n):
            m = np.zeros((4, 4), dtype=bool)
            if i < 3:
                m[1, 1] = True
            masks.append(m)
        result = pq.find_hot_pixels(masks, min_images=3)
        assert result["checked"] is True
        assert result["n_candidate_hot_or_dead_pixels"] == 0

    def test_no_untrusted_pixels_anywhere(self):
        masks = [np.zeros((3, 3), dtype=bool) for _ in range(4)]
        result = pq.find_hot_pixels(masks, min_images=3)
        assert result["n_candidate_hot_or_dead_pixels"] == 0


class TestSummarizePanel:
    def test_clean_summary_mentions_low_fraction_and_no_hot_pixels(self):
        per_image = [{"fraction_untrusted": 0.0001} for _ in range(5)]
        hot = {"checked": True, "n_candidate_hot_or_dead_pixels": 0, "fraction_of_panel": 0.0}
        text = pq.summarize_panel(0, per_image, hot)
        assert "low" in text.lower()
        assert "No candidate hot/dead pixels" in text

    def test_flagged_summary_mentions_high_fraction_and_hot_pixel_count(self):
        per_image = [{"fraction_untrusted": 0.05} for _ in range(5)]
        hot = {"checked": True, "n_candidate_hot_or_dead_pixels": 3, "fraction_of_panel": 0.001}
        text = pq.summarize_panel(0, per_image, hot)
        assert "5.0%" in text or "5.00%" in text or "5%" in text
        assert "3 pixel(s)" in text

    def test_skipped_hot_pixel_check_is_noted(self):
        per_image = [{"fraction_untrusted": 0.0}]
        hot = {"checked": False, "reason": "only 1 image(s) sampled, need at least 3"}
        text = pq.summarize_panel(0, per_image, hot)
        assert "skipped" in text.lower()
