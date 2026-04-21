# dials.plot_scan_varying_model

## Introduction
Generate plots of scan-varying models, including crystal orientation, unit cell
and beam centre, from the input refined.expt
Examples:
```
dials.plot_scan_varying_model refined.expt

```

## Basic parameters
```
output {
  directory = .
  format = *png pdf
}
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
  directory = .
    .help = "The directory to store the results"
    .type = str
  format = *png pdf
    .type = choice
  debug = False
    .help = "print tables of values that will be plotted"
    .type = bool
    .expert_level = 1
}
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