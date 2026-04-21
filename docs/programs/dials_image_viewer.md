# dials.image_viewer

## Introduction
This program can be used for viewing diffraction images, optionally overlaid
with the results of spot finding, indexing or integration.
Examples:
```
dials.image_viewer image.cbf

dials.image_viewer models.expt

dials.image_viewer models.expt strong.refl

dials.image_viewer models.expt integrated.refl

```

## Basic parameters
```
brightness = 10
color_scheme = *grayscale rainbow heatmap invert
projection = lab *image
show_beam_center = True
show_resolution_rings = False
show_ice_rings = False
show_ctr_mass = True
show_max_pix = True
show_all_pix = True
show_threshold_pix = False
show_shoebox = True
show_predictions = True
show_miller_indices = False
show_indexed = False
show_integrated = False
show_mask = False
show_rotation_axis = False
display = *image mean variance dispersion sigma_b sigma_s threshold \
          global_threshold
nsigma_b = 6
nsigma_s = 3
global_threshold = 0
kernel_size = 3,3
min_local = 2
gain = 1
n_iqr = 6
blur = narrow wide
n_bins = 100
stack_mode = max mean *sum
d_min = None
mask = None
powder_arcs {
  show = False
  code = None
}
calibrate_silver = False
calibrate_pdb {
  code = None
  d_min = 20.
}
calibrate_unit_cell {
  unit_cell = None
  d_min = 20.
  space_group = None
  show_hkl = None
}
masking {
  border = 0
  d_min = None
  d_max = None
  disable_parallax_correction = False
  resolution_range = None
  untrusted {
    panel = None
    circle = None
    rectangle = None
    polygon = None
    pixel = None
  }
  ice_rings {
    filter = False
  }
}
output {
  mask = pixels.mask
  mask_params = mask.phil
  ellipse_params = ellipse.phil
}
predict_reflections = False
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
load_models = True

```

## Full parameter definitions
```
brightness = 10
  .type = int(allow_none=True)
color_scheme = *grayscale rainbow heatmap invert
  .type = choice
projection = lab *image
  .type = choice
show_beam_center = True
  .type = bool
show_resolution_rings = False
  .type = bool
show_ice_rings = False
  .type = bool
show_ctr_mass = True
  .type = bool
show_max_pix = True
  .type = bool
show_all_pix = True
  .type = bool
show_threshold_pix = False
  .type = bool
show_shoebox = True
  .type = bool
show_predictions = True
  .type = bool
show_miller_indices = False
  .type = bool
show_indexed = False
  .type = bool
show_integrated = False
  .type = bool
show_mask = False
  .type = bool
show_rotation_axis = False
  .type = bool
display = *image mean variance dispersion sigma_b sigma_s threshold \
          global_threshold
  .type = choice
nsigma_b = 6
  .type = float(value_min=0, allow_none=True)
nsigma_s = 3
  .type = float(value_min=0, allow_none=True)
global_threshold = 0
  .type = float(value_min=0, allow_none=True)
kernel_size = 3,3
  .type = ints(size=2, value_min=1)
min_local = 2
  .type = int(allow_none=True)
gain = 1
  .help = "Set gain for the dispersion algorithm. This does not override the"
          "detector's panel gain, but acts as a multiplier for it."
  .type = float(value_min=0, allow_none=True)
n_iqr = 6
  .help = "IQR multiplier for determining the threshold value"
  .type = int(allow_none=True)
blur = narrow wide
  .help = "Optional preprocessing of the image by a convolution with a simple"
          "Gaussian kernel of size either 3×3 (narrow) or 5×5 (wide). This may"
          "help to reduce noise peaks and to combine split spots."
  .type = choice
n_bins = 100
  .help = "Number of 2θ bins in which to calculate background"
  .type = int(allow_none=True)
stack_images = 1
  .type = int(value_min=1, allow_none=True)
  .expert_level = 2
stack_mode = max mean *sum
  .type = choice
d_min = None
  .type = float(value_min=0, allow_none=True)
mask = None
  .help = "path to mask pickle file"
  .type = path
powder_arcs {
  show = False
    .help = "show powder arcs calculated from PDB file."
    .type = bool
  code = None
    .help = "PDB code (4 characters) for file; fetch it from the Internet."
    .type = str
}
calibrate_silver = False
  .help = "Open special GUI for distance/metrology from silver behenate."
  .type = bool
calibrate_pdb {
  code = None
    .help = "Option is mutually exclusive with calibrate silver, unit cell and"
            "powder arcs options."
    .type = str
  d_min = 20.
    .help = "Limiting resolution to calculate powder rings"
    .type = float(allow_none=True)
}
calibrate_unit_cell {
  unit_cell = None
    .help = "Option is mutually exclusive with calibrate silver, pdb and"
            "powder arcs options."
    .type = unit_cell
  d_min = 20.
    .help = "Limiting resolution to calculate powder rings"
    .type = float(allow_none=True)
  space_group = None
    .help = "Specify spacegroup for the unit cell"
    .type = str
  show_hkl = None
    .help = "Limit display of rings to these Miller indices"
    .type = ints(size=3)
    .multiple = True
}
format
  .help = "Options to pass to the Format class"
  .expert_level = 2
{
  dynamic_shadowing = auto
    .help = "Enable dynamic shadowing"
    .type = bool
  multi_panel = False
    .help = "Enable a multi-panel detector model. (Not supported by all"
            "detector formats)"
    .type = bool
}
masking {
  border = 0
    .help = "The border around the edge of the image."
    .type = int(allow_none=True)
  d_min = None
    .help = "The high resolution limit in Angstrom for a pixel to be accepted"
            "by the filtering algorithm."
    .type = float(value_min=0, allow_none=True)
  d_max = None
    .help = "The low resolution limit in Angstrom for a pixel to be accepted"
            "by the filtering algorithm."
    .type = float(value_min=0, allow_none=True)
  disable_parallax_correction = False
    .help = "Set to ``True`` to use a faster, but less accurate, simple"
            "px-to-mm  mapping by disabling accounting for parallax correction"
            "when generating  resolution masks."
    .type = bool
  resolution_range = None
    .help = "an untrusted resolution range"
    .type = floats(size=2)
    .multiple = True
  untrusted
    .multiple = True
  {
    panel = None
      .help = "then the whole panel is masked out"
      .type = int(allow_none=True)
    circle = None
      .help = "An untrusted circle (xc, yc, r)"
      .type = ints(size=3)
    rectangle = None
      .help = "An untrusted rectangle (x0, x1, y0, y1)"
      .type = ints(size=4)
    polygon = None
      .help = "The pixel coordinates (fast, slow) that define the corners  of"
              "the untrusted polygon. Spots whose centroids fall within  the"
              "bounds of the untrusted polygon will be rejected."
      .type = ints(value_min=0)
    pixel = None
      .help = "An untrusted pixel (y, x)"
      .type = ints(size=2, value_min=0)
  }
  ice_rings {
    filter = False
      .type = bool
    unit_cell = 4.498,4.498,7.338,90,90,120
      .help = "The unit cell to generate d_spacings for powder rings."
      .type = unit_cell
      .expert_level = 1
    space_group = 194
      .help = "The space group used to generate d_spacings for powder rings."
      .type = space_group
      .expert_level = 1
    width = 0.002
      .help = "The width of an ice ring (in 1/d^2)."
      .type = float(value_min=0, allow_none=True)
      .expert_level = 1
    d_min = None
      .help = "The high resolution limit (otherwise use detector d_min)"
      .type = float(value_min=0, allow_none=True)
      .expert_level = 1
  }
}
output {
  mask = pixels.mask
    .help = "Name of output mask file"
    .type = path
  mask_params = mask.phil
    .help = "Name of output mask parameter file"
    .type = path
  ellipse_params = ellipse.phil
    .help = "Name of output ellipse parameter file"
    .type = path
}
predict_reflections = False
  .help = "Predict reflections if no reflections provided in input"
  .type = bool
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
load_models = True
  .help = "Whether to load every model, which matters for large image files"
  .type = bool

```