"""
Raw image pixel-content quality check -- Option 2 of the raw-image-checking
discussion (Option 1, header/geometry only, already shipped as
import_geometry_check.py). This one actually reads image pixel data, so
unlike Option 1 its cost genuinely scales with how many images are read.

Deliberately NOT wired into the automatic post-import checks, and
deliberately NOT part of the main suggested workflow -- this is an opt-in,
user-requested check only. Offered two ways: (1) as an option right after
import, with an explicit runtime warning (see data_import SKILL.md); (2)
as an escalation when a LATER step (indexing, refinement, ...) shows a
problem that a quick numeric check can't fully explain -- going back to
look at the raw images directly, which is exactly what a human would do
for a small dataset but becomes impractical to do by eye across thousands
of images (see troubleshooting skill). Sampled by default (not a full
scan) to keep typical runtime bounded, but for a large dataset or slow/
networked storage this can still take real time even sampled -- there is
no way to know that in advance without actually reading some images. Pass
'all' instead of a sample count for an explicit full scan (every image,
not a sample) if a quick sample wasn't conclusive -- this is the slow
case the sampling exists to avoid by default, so only do this if asked.

Run with DIALS's own Python:

    dials.python image_pixel_quality_check.py imported.expt [max_images | all]

Prints a single JSON object to stdout.

Method
------
Sample up to `max_images` evenly-spaced images (including the first and
last) from each experiment's imageset -- NOT every image, since reading
every image of a large dataset is exactly the unbounded-runtime case this
tool is meant to avoid by default. For each sampled image, per panel:

  - fraction of pixels outside the panel's trusted range (saturated, or
    below the valid minimum -- e.g. masked/gap regions)
  - mean/median intensity among the trusted pixels (a background proxy)
  - max pixel value (a crude signal-presence indicator)

Across the sampled images, per panel: pixels that are outside the trusted
range on EVERY sampled image are flagged as candidate hot/dead pixels --
real diffraction spots move across images as the crystal rotates, so a
pixel that is *always* extreme regardless of which image was sampled is
more likely a detector defect than repeated genuine signal. This needs at
least a handful of sampled images to be meaningful (see
HOT_PIXEL_MIN_IMAGES) -- it is not attempted on datasets too small to
sample enough images from.

This does not attempt to determine spot count or diffraction quality in
the way dials.find_spots does -- it is a cheap(er) pixel-level sanity
check one step earlier, not a replacement for spot finding.
"""
import json
import sys

import numpy as np

DEFAULT_MAX_IMAGES_SAMPLED = 12
HOT_PIXEL_MIN_IMAGES = 3  # need at least this many sampled images for "always extreme" to mean anything
SATURATION_FRACTION_WARN = 0.01  # 1% of a panel's pixels saturated on a single image is already a lot


def pick_sample_indices(n_images: int, max_samples: "int | None" = DEFAULT_MAX_IMAGES_SAMPLED) -> list:
    """
    Evenly-spaced sample of 0-based image indices, including the first and
    last. max_samples=None means no cap -- every image, for an explicit full
    scan (e.g. re-checking raw data after a later-stage problem showed up
    and a quick sample wasn't conclusive). This is deliberately opt-in, not
    the default, since it's the one case where runtime genuinely scales with
    the full dataset size.
    """
    if n_images <= 0:
        return []
    if max_samples is None or n_images <= max_samples:
        return list(range(n_images))
    return sorted(set(np.linspace(0, n_images - 1, max_samples).round().astype(int).tolist()))


def analyze_panel_image(raw: np.ndarray, trusted_mask: np.ndarray) -> dict:
    """Pure-numpy stats for one panel's pixel array on one image."""
    n_total = int(raw.size)
    n_trusted = int(trusted_mask.sum())
    trusted_values = raw[trusted_mask]
    return {
        "n_pixels": n_total,
        "fraction_untrusted": (n_total - n_trusted) / n_total if n_total else 0.0,
        "mean_trusted": float(trusted_values.mean()) if n_trusted else None,
        "median_trusted": float(np.median(trusted_values)) if n_trusted else None,
        "max_value": float(raw.max()) if n_total else None,
    }


def find_hot_pixels(untrusted_masks: list, min_images: int = HOT_PIXEL_MIN_IMAGES) -> dict:
    """
    untrusted_masks: list of same-shape boolean arrays (one per sampled
    image), True where that pixel was OUTSIDE the trusted range on that
    specific image. Flags pixels untrusted on EVERY sampled image.
    """
    if len(untrusted_masks) < min_images:
        return {
            "checked": False,
            "reason": f"only {len(untrusted_masks)} image(s) sampled, need at least {min_images}",
        }
    stacked = np.stack(untrusted_masks, axis=0)
    always_untrusted = stacked.all(axis=0)
    n_hot = int(always_untrusted.sum())
    total = int(always_untrusted.size)
    return {
        "checked": True,
        "n_candidate_hot_or_dead_pixels": n_hot,
        "fraction_of_panel": (n_hot / total) if total else 0.0,
    }


def summarize_panel(panel_id: int, per_image_stats: list, hot_pixel_result: dict) -> str:
    max_untrusted_fraction = max((s["fraction_untrusted"] for s in per_image_stats), default=0.0)
    parts = [f"Panel {panel_id}: sampled {len(per_image_stats)} image(s)."]
    if max_untrusted_fraction > SATURATION_FRACTION_WARN:
        parts.append(
            f"Up to {max_untrusted_fraction:.1%} of pixels were outside the trusted range on at "
            "least one sampled image (saturated and/or masked/gap regions) -- worth a visual check "
            "if this seems high for this detector."
        )
    else:
        parts.append(f"Untrusted-pixel fraction stayed low (<= {max_untrusted_fraction:.2%}) across sampled images.")
    if hot_pixel_result.get("checked"):
        n_hot = hot_pixel_result["n_candidate_hot_or_dead_pixels"]
        if n_hot > 0:
            parts.append(
                f"{n_hot} pixel(s) were outside the trusted range on EVERY sampled image "
                f"({hot_pixel_result['fraction_of_panel']:.4%} of the panel) -- candidate "
                "hot/dead pixels (a real diffraction spot moves across images; these didn't)."
            )
        else:
            parts.append("No candidate hot/dead pixels found among sampled images.")
    else:
        parts.append(f"Hot/dead-pixel check skipped ({hot_pixel_result.get('reason', 'not enough samples')}).")
    return " ".join(parts)


def main(expt_path: str, max_images: "int | None" = DEFAULT_MAX_IMAGES_SAMPLED) -> dict:
    from dxtbx.model.experiment_list import ExperimentListFactory

    # check_format=True (unlike the header-only checks in this file's
    # family) -- this one genuinely needs to open and read image data.
    experiments = ExperimentListFactory.from_json_file(expt_path, check_format=True)

    results_by_experiment = {}
    for exp_idx, experiment in enumerate(experiments):
        imageset = experiment.imageset
        detector = experiment.detector
        n_images = len(imageset)
        sample_indices = pick_sample_indices(n_images, max_images)

        stats_by_panel: dict = {i: [] for i in range(len(detector))}
        untrusted_masks_by_panel: dict = {i: [] for i in range(len(detector))}

        for image_index in sample_indices:
            raw_data = imageset.get_raw_data(image_index)
            for panel_id, raw_flex in enumerate(raw_data):
                panel = detector[panel_id]
                raw_np = raw_flex.as_numpy_array()
                trusted_mask = np.asarray(panel.get_trusted_range_mask(raw_flex))
                stats = analyze_panel_image(raw_np, trusted_mask)
                stats["image_index"] = image_index
                stats_by_panel[panel_id].append(stats)
                untrusted_masks_by_panel[panel_id].append(~trusted_mask)

        panels_result = {}
        for panel_id in range(len(detector)):
            hot_pixel_result = find_hot_pixels(untrusted_masks_by_panel[panel_id])
            panels_result[str(panel_id)] = {
                "per_image": stats_by_panel[panel_id],
                "hot_pixels": hot_pixel_result,
                "summary": summarize_panel(panel_id, stats_by_panel[panel_id], hot_pixel_result),
            }

        results_by_experiment[str(exp_idx)] = {
            "n_images_total": n_images,
            "n_images_sampled": len(sample_indices),
            "full_scan": len(sample_indices) == n_images,
            "sampled_image_indices": sample_indices,
            "panels": panels_result,
        }

    return {"n_experiments": len(results_by_experiment), "experiments": results_by_experiment}


if __name__ == "__main__":
    if len(sys.argv) not in (2, 3):
        print(json.dumps({
            "error": (
                "usage: image_pixel_quality_check.py <imported.expt> "
                "[max_images_to_sample | 'all' for a full scan]"
            )
        }))
        sys.exit(1)
    if len(sys.argv) == 3 and sys.argv[2].lower() == "all":
        max_images = None
    elif len(sys.argv) == 3:
        max_images = int(sys.argv[2])
    else:
        max_images = DEFAULT_MAX_IMAGES_SAMPLED
    print(json.dumps(main(sys.argv[1], max_images), indent=2))
