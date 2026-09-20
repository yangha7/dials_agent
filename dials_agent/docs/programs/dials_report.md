# dials.report

## Introduction
Generates a html report given the output of various DIALS programs
(observations.refl and/or models.expt).
Examples:
```
dials.report strong.refl

dials.report indexed.refl

dials.report refined.refl

dials.report integrated.refl

dials.report refined.expt

dials.report integrated.refl integrated.expt

```

## Basic parameters
```
output {
  html = dials.report.html
  json = None
  external_dependencies = *remote local embed
}
grid_size = Auto
pixels_per_bin = 40
orientation_decomposition {
  e1 = 1. 0. 0.
  e2 = 0. 1. 0.
  e3 = 0. 0. 1.
  relative_to_static_orientation = True
}

```

## Full parameter definitions
```
output {
  html = dials.report.html
    .help = "The name of the output html file"
    .type = path
  json = None
    .help = "The name of the optional json file containing the plot data"
    .type = path
  external_dependencies = *remote local embed
    .help = "Whether to use remote external dependencies (files relocatable"
            "but requires an internet connection), local (does not require"
            "internet connection but files may not be relocatable) or embed"
            "all external dependencies (inflates the html file size)."
    .type = choice
}
grid_size = Auto
  .type = ints(size=2)
pixels_per_bin = 40
  .type = int(value_min=1, allow_none=True)
centroid_diff_max = None
  .help = "Magnitude in pixels of shifts mapped to the extreme colours in the"
          "heatmap plots centroid_diff_x and centroid_diff_y"
  .type = float(allow_none=True)
  .expert_level = 1
orientation_decomposition
  .help = "Options determining how the orientation matrix decomposition is"
          "done. The axes about which to decompose the matrix into three"
          "rotations are chosen here, as well as whether the rotations are"
          "relative to the reference orientation, taken from the static"
          "crystal model"
{
  e1 = 1. 0. 0.
    .type = floats(size=3)
  e2 = 0. 1. 0.
    .type = floats(size=3)
  e3 = 0. 0. 1.
    .type = floats(size=3)
  relative_to_static_orientation = True
    .type = bool
}

```