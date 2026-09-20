# dials.integrate

## Introduction
This program is used to integrate the reflections on the diffraction images. It
is called with an experiment list outputted from dials.index or dials.refine and
a corresponding set of strong spots from which a profile model is calculated.
The program will output a set of integrated reflections and an experiment list
with additional profile model data. The data can be reintegrated using the same
profile model by inputting this integrated.expt file back into
dials.integrate.
Examples:
```
dials.integrate models.expt refined.refl

dials.integrate models.expt refined.refl output.reflections=integrated.refl

dials.integrate models.expt refined.refl profile.fitting=False

dials.integrate models.expt refined.refl background.algorithm=glm

```

## Basic parameters
```
output {
  experiments = 'integrated.expt'
  reflections = 'integrated.refl'
  phil = 'dials.integrate.phil'
  log = 'dials.integrate.log'
  report = None
  include_bad_reference = False
}
scan_range = None
create_profile_model = True
integration {
  lookup {
    mask = None
  }
  block {
    size = auto
    units = *degrees radians frames
    threshold = 0.95
    force = False
    max_memory_usage = 0.80
  }
  use_dynamic_mask = True
  debug {
    reference {
      filename = "reference_profiles.refl"
      output = False
    }
    during = modelling *integration
    output = False
    separate_files = True
    delete_shoeboxes = False
    select = None
    split_experiments = True
  }
  profile {
    fitting = True
    validation {
      number_of_partitions = 1
      min_partition_size = 100
    }
  }
  overlaps_filter {
    foreground_foreground {
      enable = False
    }
    foreground_background {
      enable = False
    }
  }
  mp {
    method = *multiprocessing drmaa sge lsf pbs
    njobs = 1
    nproc = 1
    multiprocessing.n_subset_split = None
  }
  summation {
    detector_gain = 1
  }
  background {
    algorithm = *Auto glm gmodel null simple
    glm {
      robust {
        tuning_constant = 1.345
      }
      model {
        algorithm = constant2d *constant3d loglinear2d loglinear3d
      }
      min_pixels = 10
    }
    gmodel {
      robust {
        algorithm = False
        tuning_constant = 1.345
      }
      min_pixels = 10
      model = None
    }
    simple {
      outlier {
        algorithm = *null nsigma truncated normal plane tukey
      }
      model {
        algorithm = constant2d *constant3d linear2d linear3d
      }
      min_pixels = 10
    }
  }
  centroid {
    algorithm = *simple
  }
}
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
absorption_correction {
  apply = False
  algorithm = fuller_kapton kapton_2019 other
  fuller_kapton {
    xtal_height_above_kapton_mm {
      value = 0.02
      sigma = 0.01
    }
    rotation_angle_deg {
      value = 1.15
      sigma = 0.1
    }
    kapton_half_width_mm {
      value = 1.5875
      sigma = 0.5
    }
    kapton_thickness_mm {
      value = 0.05
      sigma = 0.005
    }
    smart_sigmas = False
    within_spot_sigmas = True
  }
}

```

## Full parameter definitions
```
output {
  experiments = 'integrated.expt'
    .help = "The experiments output filename"
    .type = str
  output_unintegrated_reflections = False
    .help = "Include unintegrated reflections in output file"
    .type = bool
    .expert_level = 2
  reflections = 'integrated.refl'
    .help = "The integrated output filename"
    .type = str
  phil = 'dials.integrate.phil'
    .help = "The output phil file"
    .type = str
  log = 'dials.integrate.log'
    .help = "The log filename"
    .type = str
  report = None
    .help = "The integration report filename (*.xml or *.json)"
    .type = str
  include_bad_reference = False
    .help = "Include bad reference data including unindexed spots, and"
            "reflections whose predictions are messed up in the reflection"
            "table output. Reflections will have the 'bad_reference' flag set."
    .type = bool
}
scan_range = None
  .help = "Explicitly specify the images to be processed. Only applicable when"
          "experiment list contains a single imageset."
  .type = ints(size=2)
  .multiple = True
create_profile_model = True
  .help = "Create the profile model"
  .type = bool
sampling
  .expert_level = 1
{
  reflections_per_degree = 50
    .help = "The number of predicted reflections per degree of the sequence "
            "to integrate."
    .type = float(value_min=0, allow_none=True)
  minimum_sample_size = 1000
    .help = "cutoff that determines whether subsetting of the input "
            "prediction list is done"
    .type = int(allow_none=True)
  maximum_sample_size = None
    .help = "The maximum number of predictions to integrate. Overrides"
            "reflections_per_degree if that produces a larger sample size."
    .type = int(value_min=1, allow_none=True)
  integrate_all_reflections = True
    .help = "Override reflections_per_degree and integrate all predicted"
            "reflections."
    .type = bool
  random_seed = 0
    .help = "Random seed for sampling"
    .type = int(allow_none=True)
}
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
integration {
  lookup
    .help = "Parameters specifying lookup file path"
  {
    mask = None
      .help = "The path to the mask file."
      .type = str
  }
  block {
    size = auto
      .help = "The block size in rotation angle (degrees)."
      .type = float(allow_none=True)
    units = *degrees radians frames
      .help = "The units of the block size"
      .type = choice
    threshold = 0.95
      .help = "For block size auto the block size is calculated by sorting"
              "reflections by the number of frames they cover and then"
              "selecting the block size to be 2*nframes[threshold] such that"
              "100*threshold % of reflections are guaranteed to be fully"
              "contained in 1 block"
      .type = float(value_min=0, value_max=1, allow_none=True)
    force = False
      .help = "If the number of processors is 1 and force is False, then the"
              "number of blocks may be set to 1. If force is True then the"
              "block size is always calculated."
      .type = bool
    max_memory_usage = 0.80
      .help = "The maximum fraction of available memory to use for allocating"
              "shoebox arrays."
      .type = float(value_min=0, value_max=1, allow_none=True)
  }
  use_dynamic_mask = True
    .help = "Use dynamic mask if available"
    .type = bool
  debug {
    reference {
      filename = "reference_profiles.refl"
        .help = "The filename for the reference profiles"
        .type = str
      output = False
        .help = "Save the reference profiles"
        .type = bool
    }
    during = modelling *integration
      .help = "Do debugging during modelling or integration"
      .type = choice
    output = False
      .help = "Save shoeboxes after each processing task."
      .type = bool
    separate_files = True
      .help = "If this is true, the shoeboxes are saved in separate files from"
              "the output integrated.refl file. This is necessary in most"
              "cases since the amount of memory used by the shoeboxes is"
              "typically greater than the available system memory. If,"
              "however, you know that memory is not an issue, you can saved"
              "the shoeboxes in the integrated.refl file by setting this"
              "option to False. This only works if the debug output is during"
              "integrated and not modelling."
      .type = bool
    delete_shoeboxes = False
      .help = "Delete shoeboxes immediately before saving files. This option"
              "in combination with debug.output=True enables intermediate"
              "processing steps to make use of shoeboxes."
      .type = bool
    select = None
      .help = "A string specifying the selection. The string should be of the"
              "form: select=${COLUMN}[<|<=|==|!=|>=|>]${VALUE}. In addition to"
              "the items in the reflection table, the following implicit"
              "columns are defined if the necessary data is there: "
              "intensity.sum.i_over_sigma  intensity.prf.i_over_sigma"
      .type = reflection_table_selector
    split_experiments = True
      .help = "Split shoeboxes into different files"
      .type = bool
  }
  profile {
    fitting = True
      .help = "Use profile fitting if available"
      .type = bool
    valid_foreground_threshold = 0.75
      .help = "The minimum fraction of foreground pixels that must be valid in"
              "order for a reflection to be integrated by profile fitting."
      .type = float(value_min=0, value_max=1, allow_none=True)
      .expert_level = 2
    validation {
      number_of_partitions = 1
        .help = "The number of subsamples to take from the reference spots. If"
                "the value is 1, then no validation is performed."
        .type = int(value_min=1, allow_none=True)
      min_partition_size = 100
        .help = "The minimum number of spots to use in each subsample."
        .type = int(value_min=1, allow_none=True)
    }
  }
  filter
    .expert_level = 1
  {
    min_zeta = 0.05
      .help = "Filter the reflections by the value of zeta. A value of less"
              "than or equal to zero indicates that this will not be used. A"
              "positive value is used as the minimum permissible value."
      .type = float(value_min=0, value_max=1, allow_none=True)
    ice_rings = False
      .help = "Set the ice ring flags"
      .type = bool
  }
  overlaps_filter {
    foreground_foreground {
      enable = False
        .help = "Remove all spots in which neighbors' foreground impinges on"
                "the spot's foreground"
        .type = bool
    }
    foreground_background {
      enable = False
        .help = "Remove all spots in which neighbors' foreground impinges on"
                "the spot's background"
        .type = bool
    }
  }
  mp {
    method = *multiprocessing drmaa sge lsf pbs
      .help = "The multiprocessing method to use"
      .type = choice
    njobs = 1
      .help = "The number of cluster jobs to use"
      .type = int(value_min=1, allow_none=True)
    nproc = 1
      .help = "The number of processes to use per cluster job"
      .type = int(value_min=1, allow_none=True)
    multiprocessing.n_subset_split = None
      .help = "Number of subsets to split the reflection table for"
              "integration."
      .type = int(value_min=1, allow_none=True)
  }
  summation {
    detector_gain = 1
      .help = "Multiplier for variances after integration of still images. See"
              "Leslie 1999."
      .type = float(allow_none=True)
  }
  background
    .help = "Extensions for background algorithms."
  {
    algorithm = *Auto glm gmodel null simple
      .help = "The choice of algorithm"
      .type = choice
    glm
      .help = "An extension class implementing a robust GLM background"
              "algorithm."
    {
      robust {
        tuning_constant = 1.345
          .help = "The tuning constant for robust estimation"
          .type = float(allow_none=True)
      }
      model {
        algorithm = constant2d *constant3d loglinear2d loglinear3d
          .help = "The background model to fit"
          .type = choice
      }
      min_pixels = 10
        .help = "The minimum number of pixels required"
        .type = int(value_min=1, allow_none=True)
    }
    gmodel
      .help = "An extension class implementing a global background algorithm."
    {
      robust {
        algorithm = False
          .help = "Use the robust algorithm"
          .type = bool
        tuning_constant = 1.345
          .help = "The tuning constant for robust estimation"
          .type = float(allow_none=True)
      }
      min_pixels = 10
        .help = "The minimum number of pixels required"
        .type = int(value_min=1, allow_none=True)
      model = None
        .help = "The model filename"
        .type = str
    }
    simple
      .help = "An extension class implementing simple background subtraction."
    {
      outlier
        .help = "Outlier rejection prior to background fit"
      {
        algorithm = *null nsigma truncated normal plane tukey
          .help = "The outlier rejection algorithm."
          .type = choice
        nsigma
          .help = "Parameters for nsigma outlier rejector"
          .expert_level = 1
        {
          lower = 3
            .help = "Lower n sigma"
            .type = float(allow_none=True)
          upper = 3
            .help = "Upper n sigma"
            .type = float(allow_none=True)
        }
        truncated
          .help = "Parameters for truncated outlier rejector"
          .expert_level = 1
        {
          lower = 0.01
            .help = "Lower bound"
            .type = float(allow_none=True)
          upper = 0.01
            .help = "Upper bound"
            .type = float(allow_none=True)
        }
        normal
          .help = "Parameters for normal outlier rejector"
          .expert_level = 1
        {
          min_pixels = 10
            .help = "The minimum number of pixels to use in calculating the"
                    "background intensity."
            .type = int(allow_none=True)
        }
        plane
          .help = "Parameters for mosflm-like outlier rejector. This algorithm"
                  "is mainly used in conjunction with a linear 2d background."
          .expert_level = 1
        {
          fraction = 1.0
            .help = "The fraction of pixels to use in determining the initial"
                    "plane used for outlier rejection."
            .type = float(allow_none=True)
          n_sigma = 4.0
            .help = "The number of standard deviations above the threshold"
                    "plane to use in rejecting outliers from background"
                    "calculation."
            .type = float(allow_none=True)
        }
        tukey
          .help = "Parameters for tukey outlier rejector"
          .expert_level = 1
        {
          lower = 1.5
            .help = "Lower IQR multiplier"
            .type = float(allow_none=True)
          upper = 1.5
            .help = "Upper IQR multiplier"
            .type = float(allow_none=True)
        }
      }
      model
        .help = "Background model"
      {
        algorithm = constant2d *constant3d linear2d linear3d
          .help = "The choice of background model"
          .type = choice
      }
      min_pixels = 10
        .help = "The minimum number of pixels to compute the background"
        .type = int(value_min=1, allow_none=True)
    }
  }
  centroid
    .help = "Extensions for centroid algorithms."
  {
    algorithm = *simple
      .help = "The choice of algorithm"
      .type = choice
  }
}
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
significance_filter
  .expert_level = 1
{
  enable = False
    .help = "If enabled, the significance filter will, for every experiment,"
            "find the highest resolution where the I/sigI remains above a"
            "certain point (controlled by isigi_cutoff)."
    .type = bool
  d_min = None
    .help = "High resolution cutoff for binning. If None, use the highest"
            "resolution reflection as d_min."
    .type = float(allow_none=True)
  n_bins = 20
    .help = "Number of bins to use when examining resolution falloff"
    .type = int(allow_none=True)
  isigi_cutoff = 1.0
    .help = "I/sigI cutoff. Reflections in and past the first bin that falls"
            "below this cutoff will not be retained"
    .type = float(allow_none=True)
}
absorption_correction
  .multiple = True
{
  apply = False
    .help = "must be supplied as a user-defined function with a specific"
            "interface (not documented)"
    .type = bool
  algorithm = fuller_kapton kapton_2019 other
    .help = "a specific absorption correction, or implementation thereof"
            "kapton_2019 is a more general implementation of fuller_kapton for"
            "use on single/multi-panel detectors"
    .type = choice
  fuller_kapton {
    xtal_height_above_kapton_mm {
      value = 0.02
        .help = "height of the beam (or the irradiated crystal) above the"
                "kapton tape"
        .type = float(allow_none=True)
      sigma = 0.01
        .type = float(allow_none=True)
    }
    rotation_angle_deg {
      value = 1.15
        .help = "angle of the tape from vertical"
        .type = float(allow_none=True)
      sigma = 0.1
        .type = float(allow_none=True)
    }
    kapton_half_width_mm {
      value = 1.5875
        .help = "forward distance from irradiated crystal to edge of tape"
                "nearest detector"
        .type = float(allow_none=True)
      sigma = 0.5
        .type = float(allow_none=True)
    }
    kapton_thickness_mm {
      value = 0.05
        .help = "tape thickness"
        .type = float(allow_none=True)
      sigma = 0.005
        .type = float(allow_none=True)
    }
    smart_sigmas = False
      .help = "apply spot-specific sigma corrections using kapton param sigmas"
      .type = bool
    within_spot_sigmas = True
      .help = "turn this off to get a major speed-up"
      .type = bool
  }
}

```