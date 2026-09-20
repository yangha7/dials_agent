# dials.show

## Introduction
Examples:
```
dials.show models.expt

dials.show image_*.cbf

dials.show observations.refl

```

## Basic parameters
```
show_scan_varying = False
show_shared_models = False
show_all_reflection_data = False
show_intensities = False
show_centroids = False
show_profile_fit = False
show_flags = False
show_identifiers = False
image_statistics {
  show_corrected = False
  show_raw = False
}
max_reflections = None

```

## Full parameter definitions
```
show_scan_varying = False
  .help = "Whether or not to show the crystal at each scan point."
  .type = bool
show_shared_models = False
  .help = "Show which models are linked to which experiments"
  .type = bool
show_all_reflection_data = False
  .help = "Whether or not to print individual reflections"
  .type = bool
show_intensities = False
  .type = bool
show_centroids = False
  .type = bool
show_profile_fit = False
  .type = bool
show_flags = False
  .help = "Show a summary table of reflection flags"
  .type = bool
show_identifiers = False
  .help = "Show experiment identifiers map if set"
  .type = bool
image_statistics {
  show_corrected = False
    .help = "Show statistics on the distribution of values in each corrected"
            "image"
    .type = bool
  show_raw = False
    .help = "Show statistics on the distribution of values in each raw image"
    .type = bool
}
max_reflections = None
  .help = "Limit the number of reflections in the output."
  .type = int(allow_none=True)

```