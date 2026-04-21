# dials.create_profile_model

## Introduction
This program computes the profile model from the input reflections. It then
saves a modified models.expt file with the additional profile model
information. Usually this is performed during integration; however, on some
occasions it may be desirable to compute the profile model independently.
Examples:
```
dials.create_profile_model models.expt observations.refl

```

## Basic parameters
```
output = models_with_profiles.expt
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
prediction {
  d_min = None
  d_max = None
  margin = 1
  force_static = False
  padding = 1.0
}

```

## Full parameter definitions
```
subtract_background = False
  .help = "Subtract background from pixel data before computing profile"
  .type = bool
  .expert_level = 2
output = models_with_profiles.expt
  .help = "The filename for the experiments"
  .type = str
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
prediction {
  d_min = None
    .help = "The maximum resolution limit"
    .type = float(allow_none=True)
  d_max = None
    .help = "The minimum resolution limit"
    .type = float(allow_none=True)
  margin = 1
    .help = "The margin to use to scan varying prediction"
    .type = int(allow_none=True)
  force_static = False
    .help = "For scan-varying prediction force scan-static prediction"
    .type = bool
  padding = 1.0
    .help = "The padding in degrees"
    .type = float(value_min=0, allow_none=True)
}

```