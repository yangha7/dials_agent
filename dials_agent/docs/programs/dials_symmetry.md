# dials.symmetry

## Introduction
This program implements the methods of
POINTLESS (
Evans, P. (2006). Acta Cryst. D62, 72-82. and
Evans, P. R. (2011). Acta Cryst. D67, 282-292.)
for scoring and determination of Laue group symmetry.
The program takes as input a set of one or more integrated experiments and
reflections.
Examples:
```
dials.symmetry models.expt observations.refl

```

## Basic parameters
```
d_min = Auto
min_i_mean_over_sigma_mean = 4
min_cc_half = 0.6
normalisation = kernel quasi ml_iso *ml_aniso
lattice_group = None
seed = 230
lattice_symmetry_max_delta = 2.0
relative_length_tolerance = 0.05
absolute_angle_tolerance = 2
exclude_inconsistent_unit_cells = False
partiality_threshold = 0.4
laue_group = auto
change_of_basis_op = None
best_monoclinic_beta = True
systematic_absences {
  check = True
  method = *direct fourier
  significance_level = 0.95
}
output {
  log = dials.symmetry.log
  experiments = "symmetrized.expt"
  reflections = "symmetrized.refl"
  excluded = False
  excluded_prefix = "excluded"
  json = dials.symmetry.json
  html = "dials.symmetry.html"
}

```

## Full parameter definitions
```
exclude_images = None
  .help = "Input in the format exp:start:end Exclude a range of images (start,"
          "stop) from the dataset with experiment identifier exp  (inclusive"
          "of frames start, stop). Multiple ranges can be given in one go,"
          "e.g. exclude_images=0:150:200,1:200:250 exclude_images='0:150:200"
          "1:200:250'"
  .short_caption = "Exclude images"
  .type = strings
  .multiple = True
  .expert_level = 1
exclude_images_multiple = None
  .help = "Exclude this single image and each multiple of this image number in"
          "each experiment. This is provided as a convenient shorthand to"
          "specify image exclusions for cRED data, where the scan of"
          "diffraction images is interrupted at regular intervals by a crystal"
          "positioning image (typically every 20th image)."
  .type = int(value_min=2, allow_none=True)
  .expert_level = 2
d_min = Auto
  .type = float(value_min=0, allow_none=True)
min_i_mean_over_sigma_mean = 4
  .type = float(value_min=0, allow_none=True)
min_cc_half = 0.6
  .type = float(value_min=0, value_max=1, allow_none=True)
normalisation = kernel quasi ml_iso *ml_aniso
  .type = choice
lattice_group = None
  .type = space_group
seed = 230
  .type = int(value_min=0, allow_none=True)
lattice_symmetry_max_delta = 2.0
  .type = float(value_min=0, allow_none=True)
relative_length_tolerance = 0.05
  .type = float(value_min=0, allow_none=True)
absolute_angle_tolerance = 2
  .type = float(value_min=0, allow_none=True)
exclude_inconsistent_unit_cells = False
  .help = "Exclude datasets with unit cells that cannot be mapped to a common"
          "minimum cell, as controlled by the absolute_angle_tolerance and"
          "relative_length_tolerance parameters. If False, an error will be"
          "raised instead."
  .type = bool
partiality_threshold = 0.4
  .help = "Use only reflections with a partiality above this threshold."
  .type = float(allow_none=True)
laue_group = auto
  .help = "Optionally specify the Laue group. If set to auto, then test all"
          "possible  Laue groups. If set to None, then take the Laue group"
          "from the input file."
  .type = space_group
change_of_basis_op = None
  .type = str
best_monoclinic_beta = True
  .help = "If True, then for monoclinic centered cells, I2 will be preferred"
          "over C2 if it gives a less oblique cell (i.e. smaller beta angle)."
  .type = bool
systematic_absences {
  check = True
    .help = "Check systematic absences for the current laue group."
    .type = bool
  method = *direct fourier
    .help = "Use fourier analysis or direct analysis of I/sigma to determine"
            "likelihood of systematic absences"
    .type = choice
  significance_level = 0.95
    .help = "Significance to use when testing whether axial reflections are "
            "different to zero (absences and reflections in reflecting"
            "condition)."
    .type = float(value_min=0, value_max=1, allow_none=True)
}
output {
  log = dials.symmetry.log
    .type = str
  experiments = "symmetrized.expt"
    .type = path
  reflections = "symmetrized.refl"
    .type = path
  excluded = False
    .type = bool
  excluded_prefix = "excluded"
    .type = path
  json = dials.symmetry.json
    .type = path
  html = "dials.symmetry.html"
    .help = "Filename for html report."
    .type = path
}

```