# dials.check_indexing_symmetry

## Introduction
This program can be used to analyse the correlation coefficients between
reflections related by the symmetry operators belonging to the space group of
the input experiment.expt file. It can also check for misindexing of
the diffraction pattern, possibly as a result of an incorrect beam centre.
Examples:
```
dials.check_indexing_symmetry indexed.expt indexed.refl \
  grid=1 symop_threshold=0.7

dials.check_indexing_symmetry indexed.expt indexed.refl \
  grid_l=3 symop_threshold=0.7

```

## Basic parameters
```
d_min = 0
d_max = 0
symop_threshold = 0
grid = 0
grid_h = 0
grid_k = 0
grid_l = 0
asu = False
normalise = False
normalise_bins = 0
reference = None
output {
  log = dials.check_indexing_symmetry.log
}

```

## Full parameter definitions
```
d_min = 0
  .help = "High resolution limit to use for analysis"
  .type = float(allow_none=True)
d_max = 0
  .help = "Low resolution limit to use for analysis"
  .type = float(allow_none=True)
symop_threshold = 0
  .help = "Threshold above which we consider a symmetry operator true at"
          "approximately 95% confidence."
  .type = float(allow_none=True)
grid = 0
  .help = "Search scope for testing misindexing on h, k, l."
  .type = int(allow_none=True)
grid_h = 0
  .help = "Search scope for testing misindexing on h."
  .type = int(allow_none=True)
grid_k = 0
  .help = "Search scope for testing misindexing on k."
  .type = int(allow_none=True)
grid_l = 0
  .help = "Search scope for testing misindexing on l."
  .type = int(allow_none=True)
asu = False
  .help = "Perform search comparing within ASU (assumes input symm)"
  .type = bool
normalise = False
  .help = "Normalise intensities before calculating correlation coefficients."
  .type = bool
normalise_bins = 0
  .help = "Number of resolution bins for normalisation"
  .type = int(allow_none=True)
reference = None
  .help = "Correctly indexed reference set for comparison"
  .type = path
output {
  log = dials.check_indexing_symmetry.log
    .type = str
}

```