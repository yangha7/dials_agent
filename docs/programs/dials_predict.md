# dials.predict

## Introduction
This program takes a set of experiments and predicts the reflections. The
reflections are then saved to file.
Examples:
```
dials.predict models.expt

dials.predict models.expt force_static=True

dials.predict models.expt d_min=2.0

```

## Basic parameters
```
output = predicted.refl
force_static = False
ignore_shadows = True
buffer_size = 0
d_min = None
profile {
  algorithm = ellipsoid *gaussian_rs
  ellipsoid {
    rlp_mosaicity {
      model = simple1 *simple6 simple1angular1 simple1angular3 \
              simple6angular1
    }
    wavelength_spread {
      model = *delta
    }
    unit_cell {
      fixed = False
    }
    orientation {
      fixed = False
    }
    indexing {
      fail_on_bad_index = False
    }
    refinement {
      max_separation = 2
      outlier_probability = 0.975
      n_macro_cycles = 3
      n_cycles = 3
      min_n_reflections = 10
      max_iter = 100
      LL_tolerance = 1e-3
      mosaicity_max_limit = 0.004
      max_cell_volume_change_fraction = 0.2
    }
  }
  gaussian_rs {
    scan_varying = False
    min_spots {
      overall = 50
      per_degree = 20
    }
    sigma_m_algorithm = basic *extended
    centroid_definition = com *s1
    parameters {
      n_sigma = 3.0
      sigma_b = None
      sigma_m = None
    }
    filter {
      min_zeta = 0.05
    }
    fitting {
      scan_step = 5
      grid_size = 5
      threshold = 0.02
      grid_method = single *regular_grid circular_grid spherical_grid
      fit_method = *reciprocal_space detector_space
      detector_space {
        deconvolution = False
      }
    }
  }
}

```

## Full parameter definitions
```
output = predicted.refl
  .help = "The filename for the predicted reflections"
  .type = str
force_static = False
  .help = "For a scan varying model, force static prediction"
  .type = bool
ignore_shadows = True
  .help = "Ignore dynamic shadowing"
  .type = bool
buffer_size = 0
  .help = "Calculate predictions within a buffer zone of n images either  side"
          "of the scan"
  .type = int(allow_none=True)
d_min = None
  .help = "Minimum d-spacing of predicted reflections"
  .type = float(allow_none=True)
profile
  .help = "The interface definition for a profile model."
{
  algorithm = ellipsoid *gaussian_rs
    .help = "The choice of algorithm"
    .type = choice
  ellipsoid
    .help = "An extension class implementing a reciprocal space multivariate"
            "normal profile model."
  {
    rlp_mosaicity {
      model = simple1 *simple6 simple1angular1 simple1angular3 \
              simple6angular1
        .type = choice
    }
    wavelength_spread {
      model = *delta
        .type = choice
    }
    unit_cell {
      fixed = False
        .type = bool
    }
    orientation {
      fixed = False
        .type = bool
    }
    indexing {
      fail_on_bad_index = False
        .type = bool
    }
    refinement {
      max_separation = 2
        .type = float(allow_none=True)
      outlier_probability = 0.975
        .type = float(allow_none=True)
      n_macro_cycles = 3
        .type = int(allow_none=True)
      n_cycles = 3
        .type = int(allow_none=True)
      min_n_reflections = 10
        .type = int(allow_none=True)
      max_iter = 100
        .help = "Max number of iterations per refinement cycle"
        .type = int(allow_none=True)
      LL_tolerance = 1e-3
        .help = "Convergence tolerance for log likelihood during refinement"
        .type = float(allow_none=True)
      mosaicity_max_limit = 0.004
        .help = "Mosaicity values above this limit are considered unphysical"
                "and processing will stop for the given image. Units are"
                "inverse angstroms"
        .type = float(allow_none=True)
      max_cell_volume_change_fraction = 0.2
        .help = "Processing will be stopped for a given image if the"
                "fractional volume change is greater than this amount during a"
                "cycle of cell refinement."
        .type = float(allow_none=True)
    }
    prediction
      .expert_level = 1
    {
      d_min = None
        .type = float(allow_none=True)
      probability = 0.997300
        .type = float(allow_none=True)
    }
  }
  gaussian_rs
    .help = "An extension class implementing a reciprocal space gaussian"
            "profile model."
  {
    scan_varying = False
      .help = "Calculate a scan varying model"
      .type = bool
    min_spots
      .help = "if (total_reflections > overall or reflections_per_degree >"
              "per_degree) then do the profile modelling."
    {
      overall = 50
        .help = "The minimum number of spots needed to do the profile"
                "modelling"
        .type = int(value_min=0, allow_none=True)
      per_degree = 20
        .help = "The minimum number of spots needed to do the profile"
                "modelling"
        .type = int(value_min=0, allow_none=True)
    }
    sigma_m_algorithm = basic *extended
      .help = "The algorithm to compute mosaicity"
      .type = choice
    centroid_definition = com *s1
      .help = "The centroid to use as beam divergence (centre of mass or s1)"
      .type = choice
    parameters {
      n_sigma = 3.0
        .help = "Sigma multiplier for shoebox"
        .type = float(value_min=0, allow_none=True)
      sigma_b = None
        .help = "Override the sigma_b value (degrees)"
        .type = float(value_min=0, allow_none=True)
      sigma_m = None
        .help = "Override the sigma_m value (degrees)"
        .type = float(value_min=0, allow_none=True)
    }
    filter {
      min_zeta = 0.05
        .help = "Filter reflections by min zeta"
        .type = float(allow_none=True)
    }
    fitting {
      scan_step = 5
        .help = "Space between profiles in degrees"
        .type = float(allow_none=True)
      grid_size = 5
        .help = "The size of the profile grid."
        .type = int(allow_none=True)
      threshold = 0.02
        .help = "The threshold to use in reference profile"
        .type = float(allow_none=True)
      grid_method = single *regular_grid circular_grid spherical_grid
        .help = "Select the profile grid method"
        .type = choice
      fit_method = *reciprocal_space detector_space
        .help = "The fitting method"
        .type = choice
      detector_space {
        deconvolution = False
          .help = "Do deconvolution in detector space"
          .type = bool
      }
    }
  }
}

```