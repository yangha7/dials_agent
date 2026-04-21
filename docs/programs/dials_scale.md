# dials.scale

## Introduction
This program performs scaling on integrated datasets, which attempts to improve
the internal consistency of the reflection intensities by correcting for
various experimental effects. By default, a physically motivated scaling model
is used, with a scale, decay (B-factor) and absorption correction.
If the input files contain multiple datasets, all data will be scaled against
a common target of unique reflection intensities.
The program outputs one scaled.refl file, which contains updated reflection
intensities, variances and per-refelction scale factors, and one scaled.expt
containing the scaling models. These values can then be used to merge the data
with dials.merge for downstream structural solution. Alternatively, the
scaled.expt and scaled.refl files can be passed back to dials.scale, and
further scaling will be performed, starting from where the previous job finished.
A dials.scale.html file is also generated, containing interactive plots of merging
statistics and scaling model plots.
Example use cases
Regular single-sequence scaling, with no absorption correction:
```
dials.scale integrated.refl integrated.expt physical.absorption_correction=False

```

Scaling multiple datasets, specifying a resolution limit:
```
dials.scale 1_integrated.refl 1_integrated.expt 2_integrated.refl 2_integrated.expt d_min=1.4

```

Incremental scaling (with different options per dataset):
```
dials.scale integrated.refl integrated.expt physical.scale_interval=10.0

dials.scale integrated_2.refl integrated_2.expt scaled.refl scaled.expt physical.scale_interval=15.0

```

More detailed documentation on usage of dials.scale can be found in the
dials scale user guide

## Basic parameters
```
model = KB array dose_decay physical
output {
  log = dials.scale.log
  experiments = "scaled.expt"
  reflections = "scaled.refl"
  html = "dials.scale.html"
  json = None
  unmerged_mtz = None
  merged_mtz = None
  project_name = DIALS
}
anomalous = False
overwrite_existing_models = False
reflection_selection {
  method = *quasi_random intensity_ranges use_all random
  random {
    multi_dataset {
      Isigma_cutoff = 1.0
    }
  }
  best_unit_cell = None
}
weighting {
  error_model {
    basic {
      stills {
        min_Isigma = 2.0
        min_multiplicity = 4
      }
    }
    reset_error_model = False
    error_model_group = None
  }
}
cut_data {
}
scaling_options {
  check_consistent_indexing = False
  reference_model {
  }
}
cross_validation {
}
filtering {
  method = None deltacchalf
  deltacchalf {
    max_cycles = 6
    max_percent_removed = 10
    min_completeness = None
    mode = *dataset image_group
    group_size = 10
    stdcutoff = 4.0
  }
  output {
    scale_and_filter_results = "scale_and_filter_results.json"
  }
}
dataset_selection {
}

```

## Full parameter definitions
```
model = KB array dose_decay physical
  .help = "Set scaling model to be applied to input datasets"
  .type = choice
  .expert_level = 0
KB
  .expert_level = 1
{
  decay_correction = True
    .help = "Option to turn off decay correction (for physical/array/KB
      "
            "     default models)."
    .type = bool
    .expert_level = 1
  correction.fix = None
    .help = "If specified, this correction will not be refined in this scaling"
            "run"
    .type = strings
  analytical_correction = False
    .help = "If True, the  analytical_correction\" column from the reflection"
            "table will\" be used as a fixed correction during scaling (in"
            "addition to any corrections specified as fixed with the option"
            "correction.fix=)"
    .type = bool
}
array
  .expert_level = 1
{
  decay_correction = True
    .help = "Option to turn off decay correction (a 2D grid of parameters as a"
            "function of rotation and resolution (d-value))."
    .type = bool
    .expert_level = 1
  decay_interval = 20.0
    .help = "Rotation (phi) interval between model parameters for the decay"
            "and absorption corrections."
    .type = float(value_min=1, allow_none=True)
    .expert_level = 1
  n_resolution_bins = 10
    .help = "Number of resolution bins to use for the decay term."
    .type = int(value_min=1, allow_none=True)
    .expert_level = 1
  absorption_correction = True
    .help = "Option to turn off absorption correction (a 3D grid of parameters"
            "as a function of rotation angle, detector-x and detector-y"
            "position)."
    .type = bool
    .expert_level = 1
  n_absorption_bins = 3
    .help = "Number of bins in each dimension (applied to both x and y) for"
            "binning the detector position for the absorption term of the"
            "array model."
    .type = int(value_min=1, allow_none=True)
    .expert_level = 1
  modulation_correction = False
    .help = "Option to turn on a detector correction for the array default"
            "model."
    .type = bool
    .expert_level = 2
  n_modulation_bins = 20
    .help = "Number of bins in each dimension (applied to both x and y) for"
            "binning the detector position for the modulation correction."
    .type = int(value_min=1, allow_none=True)
    .expert_level = 2
  correction.fix = None
    .help = "If specified, this correction will not be refined in this scaling"
            "run"
    .type = strings
  analytical_correction = False
    .help = "If True, the  analytical_correction\" column from the reflection"
            "table will\" be used as a fixed correction during scaling (in"
            "addition to any corrections specified as fixed with the option"
            "correction.fix=)"
    .type = bool
}
dose_decay
  .expert_level = 1
{
  scale_interval = 2.0
    .help = "Rotation (phi) interval between model parameters for the scale"
            "component."
    .type = float(value_min=1, allow_none=True)
    .expert_level = 1
  relative_B_correction = True
    .help = "Option to turn off relative B correction."
    .type = bool
    .expert_level = 1
  decay_correction = True
    .help = "Option to turn off decay correction."
    .type = bool
    .expert_level = 1
  share.decay = True
    .help = "Share the decay model between sweeps."
    .type = bool
    .expert_level = 1
  resolution_dependence = *quadratic linear
    .help = "Use a dose model that depends linearly or quadratically on 1/d"
    .type = choice
    .expert_level = 1
  absorption_correction = False
    .help = "Option to turn on spherical harmonic absorption correction."
    .type = bool
    .expert_level = 1
  lmax = 4
    .help = "Number of spherical harmonics to include for absorption"
            "correction, recommended to be no more than 6."
    .type = int(value_min=2, allow_none=True)
    .expert_level = 2
  surface_weight = 1e6
    .help = "Restraint weight applied to spherical harmonic terms in the"
            "absorption correction."
    .type = float(value_min=0, allow_none=True)
    .expert_level = 2
  fix_initial = True
    .help = "If performing full matrix minimisation, in the final cycle,"
            "constrain the initial parameter for more reliable parameter and"
            "scale factor error estimates."
    .type = bool
    .expert_level = 2
  correction.fix = None
    .help = "If specified, this correction will not be refined in this scaling"
            "run"
    .type = strings
  analytical_correction = False
    .help = "If True, the  analytical_correction\" column from the reflection"
            "table will\" be used as a fixed correction during scaling (in"
            "addition to any corrections specified as fixed with the option"
            "correction.fix=)"
    .type = bool
}
physical
  .expert_level = 1
{
  scale_interval = auto
    .help = "Rotation (phi) interval between model parameters for the scale"
            "component (auto scales interval depending on oscillation range)."
    .type = float(value_min=1, allow_none=True)
    .expert_level = 1
  decay_correction = True
    .help = "Option to turn off decay correction."
    .type = bool
    .expert_level = 1
  decay_interval = auto
    .help = "Rotation (phi) interval between model parameters for the decay"
            "component (auto scales interval depending on oscillation range)."
    .type = float(value_min=1, allow_none=True)
    .expert_level = 1
  decay_restraint = 1e-1
    .help = "Weight to weakly restrain B-values to 0."
    .type = float(value_min=0, allow_none=True)
    .expert_level = 2
  absorption_correction = auto
    .help = "Option to turn off absorption correction (default True if"
            "oscillation > 60.0)."
    .type = bool
    .expert_level = 1
  absorption_level = low medium high
    .help = "Expected degree of relative absorption for different scattering"
            "paths through the crystal(s). If an option is selected, the"
            "scaling model parameters lmax and surface_weight will be set to"
            "appropriate values. Relative absorption increases as crystal size"
            "increases, increases as wavelength increases and is increased as"
            "the crystal dimensions become less equal (i.e. is higher for"
            "needle shaped crystals and zero for a spherical crystal)."
            "Definitions of the levels and approximate correction magnitude:"
            "low:    ~1%% relative absorption, expected for typical protein   "
            "     crystals (containing no strongly absorbing atoms) on the    "
            "    order of ~100um measured at ~1A wavelength. medium: ~5%%"
            "relative absorption high:   >25%% relative absorption, e.g. for"
            "measurements at long         wavelength or crystals with high"
            "absorption from heavy atoms."
    .type = choice
    .expert_level = 1
  lmax = auto
    .help = "Number of spherical harmonics to include for absorption"
            "correction, defaults to 4 if no absorption_level is chosen. It is"
            "recommended that the value need be no more than 6."
    .type = int(value_min=2, allow_none=True)
    .expert_level = 1
  surface_weight = auto
    .help = "Restraint weight applied to spherical harmonic terms in the"
            "absorption correction. A lower restraint allows a higher amount"
            "of absorption correction. Defaults to 5e5 if no absorption_level"
            "is chosen."
    .type = float(value_min=0, allow_none=True)
    .expert_level = 1
  share.absorption = False
    .help = "If True, a common absorption correction is refined across all"
            "sweeps ."
    .type = bool
  fix_initial = True
    .help = "If performing full matrix minimisation, in the final cycle,"
            "constrain the initial parameter for more reliable parameter and"
            "scale factor error estimates."
    .type = bool
    .expert_level = 2
  correction.fix = None
    .help = "If specified, this correction will not be refined in this scaling"
            "run"
    .type = strings
  analytical_correction = False
    .help = "If True, the  analytical_correction\" column from the reflection"
            "table will\" be used as a fixed correction during scaling (in"
            "addition to any corrections specified as fixed with the option"
            "correction.fix=)"
    .type = bool
}
output {
  log = dials.scale.log
    .help = "The log filename"
    .type = str
  experiments = "scaled.expt"
    .help = "Option to set filepath for output experiments."
    .type = str
  reflections = "scaled.refl"
    .help = "Option to set filepath for output intensities."
    .type = str
  html = "dials.scale.html"
    .help = "Filename for html report."
    .type = str
  json = None
    .help = "Filename to save html report data in json format."
    .type = str
  unmerged_mtz = None
    .help = "Filename to export an unmerged_mtz file using dials.export."
    .type = str
  merged_mtz = None
    .help = "Filename to export a merged_mtz file."
    .type = str
  crystal_name = XTAL
    .help = "The crystal name to be exported in the mtz file metadata"
    .type = str
    .expert_level = 1
  project_name = DIALS
    .help = "The project name for the mtz file metadata"
    .type = str
  use_internal_variance = False
    .help = "Option to use internal spread of the intensities when merging
   "
            "          reflection groups and calculating sigI, rather than"
            "using the
              sigmas of the individual reflections."
    .type = bool
    .expert_level = 1
  merging.nbins = 20
    .help = "Number of bins to use for calculating and plotting merging stats."
    .type = int(allow_none=True)
    .expert_level = 1
  additional_stats = False
    .help = "Calculate and report the R-split statistic in the merging stats."
    .type = bool
    .expert_level = 2
  delete_integration_shoeboxes = True
    .help = "Discard integration shoebox data from scaling output, to help"
            "with memory management."
    .type = bool
    .expert_level = 2
}
anomalous = False
  .help = "Separate anomalous pairs in scaling and error model optimisation."
  .type = bool
  .expert_level = 0
overwrite_existing_models = False
  .help = "If True, create new scaling models for all datasets"
  .type = bool
  .expert_level = 0
reflection_selection {
  method = *quasi_random intensity_ranges use_all random
    .help = "Method to use when choosing a reflection subset for scaling model"
            "minimisation. The quasi_random option randomly selects"
            "reflections groups within a dataset, and also selects groups"
            "which have good connectedness across datasets for multi-dataset"
            "cases. The random option selects reflection groups randomly for"
            "both single and multi dataset scaling, so for a single dataset"
            "quasi_random == random. The intensity_ranges option uses the"
            "E2_range, Isigma_range and d_range options to the subset of"
            "reflections The use_all option uses all suitable reflections,"
            "which may be slow for large datasets."
    .type = choice
  random {
    multi_dataset {
      Isigma_cutoff = 1.0
        .help = "Minimum average I/sigma of reflection groups to use when"
                "selecting random reflections for minimisation."
        .type = float(allow_none=True)
    }
    min_groups = 2000
      .help = "The minimum number of symmetry groups to use during"
              "minimisation."
      .type = int(allow_none=True)
      .expert_level = 1
    min_reflections = 50000
      .help = "The minimum number of reflections to use during minimisation."
      .type = int(allow_none=True)
      .expert_level = 1
  }
  best_unit_cell = None
    .help = "Best unit cell value, to use when performing resolution cutting"
            "and merging statistics. If None, the median cell will be used."
    .type = unit_cell
  E2_range = 0.8, 5.0
    .help = "Minimum and maximum normalised E^2 value to used to select a"
            "subset of reflections for minimisation."
    .type = floats(size=2)
    .expert_level = 1
  Isigma_range = -5.0, 0.0
    .help = "Minimum and maximum I/sigma values used to select a subset of"
            "reflections for minimisation. A value of 0.0 for the maximum"
            "indicates that no upper limit should be applied."
    .type = floats(size=2)
    .expert_level = 1
  d_range = None
    .help = "Minimum and maximum d-values used to select a subset of"
            "reflections for minimisation."
    .type = floats(size=2)
    .expert_level = 1
  min_partiality = 0.95
    .help = "Minimum partiality to use when selecting reflections to use to"
            "determine the scaling model and error model."
    .type = float(allow_none=True)
    .expert_level = 2
  intensity_choice = profile sum *combine
    .help = "Option to choose from profile fitted or summation intensities,"
            "or
               an optimised combination of profile/sum."
    .type = choice
    .expert_level = 1
    .alias = intensity
  combine.Imid = None
    .help = "A list of values to try for the midpoint, for profile/sum"
            "combination
               calculation: the value with the lowest"
            "Rmeas will be chosen.
               0 and 1 are special values"
            "that can be supplied to include profile
               and sum"
            "respectively in the comparison."
    .type = floats
    .expert_level = 2
  combine.joint_analysis = True
    .help = "Option of whether to do intensity combination optimisation
      "
            "       separately (i.e. different Imid per dataset) or joint for
"
            "             multiple datasets"
    .type = bool
    .expert_level = 2
}
weighting {
  weighting_scheme = *invvar
    .help = "Weighting scheme used during Ih calculation. Weighting schemes
  "
            "           other than invvar and unity may trigger iterative"
            "reweighting
              during minimisation, which may be"
            "unstable for certain minimisation
              engines (LBFGS)."
    .type = choice
    .expert_level = 2
  error_model {
    error_model = *basic None
      .help = "The error model to use."
      .type = choice
      .expert_level = 1
    basic {
      a = None
        .help = "Used this fixed value for the error model 'a' parameter"
        .type = float(allow_none=True)
        .expert_level = 2
      b = None
        .help = "Used this fixed value for the error model 'b' parameter"
        .type = float(allow_none=True)
        .expert_level = 2
      stills {
        min_Isigma = 2.0
          .help = "Minimum uncorrected I/sigma for individual reflections used"
                  "in error model optimisation"
          .type = float(allow_none=True)
        min_multiplicity = 4
          .help = "Only reflections with at least this multiplicity (after"
                  "Isigma filtering) are used in error model optimisation."
          .type = int(allow_none=True)
      }
      min_Ih = 25.0
        .help = "Reflections with expected intensity above this value are to."
                "be used in error model minimisation."
        .type = float(allow_none=True)
        .expert_level = 2
      n_bins = 10
        .help = "The number of intensity bins to use for the error model"
                "optimisation."
        .type = int(allow_none=True)
        .expert_level = 2
    }
    reset_error_model = False
      .help = "If True, the error model is reset to the default at the start"
              "of scaling, as opposed to loading the current error model."
      .type = bool
    grouping = individual grouped *combined
      .help = "This options selects whether one error model is determined for"
              "all sweeps (combined), whether one error model is determined"
              "per-sweep (individual), or whether a custom grouping should be"
              "used. If grouping=grouped, each group should be specified with"
              "the error_model_group=parameter."
      .type = choice
      .expert_level = 2
    error_model_group = None
      .help = "Specify a subset of sweeps which should share an error model."
              "If no groups are specified here, this is interpreted to mean"
              "that all sweeps should share a common error model."
      .type = ints
      .multiple = True
  }
}
cut_data {
  d_min = None
    .help = "Option to apply a high resolution cutoff for the dataset (i.e.
  "
            "            the chosen reflections have d > d_min)."
    .type = float(allow_none=True)
    .expert_level = 1
  d_max = None
    .help = "Option to apply a low resolution cutoff for the dataset (i.e.
   "
            "           the chosen reflections have d < d_max)."
    .type = float(allow_none=True)
    .expert_level = 1
  partiality_cutoff = 0.4
    .help = "Value below which reflections are removed from the dataset due
  "
            "            to low partiality."
    .type = float(allow_none=True)
    .expert_level = 1
  min_isigi = -5
    .help = "Value below which reflections are removed from the dataset due to"
            "low I/sigI in either profile or summation intensity estimates"
    .type = float(allow_none=True)
    .expert_level = 1
}
scaling_options {
  check_consistent_indexing = False
    .help = "If True, run dials.cosym on all data in the data preparation"
            "step, to ensure consistent indexing."
    .type = bool
  target_cycle = True
    .help = "Option to turn of initial round of targeted scaling
             "
            " if some datasets are already scaled."
    .type = bool
    .expert_level = 2
  only_target = False
    .help = "Option to only do targeted scaling if some datasets
             "
            " are already scaled."
    .type = bool
    .expert_level = 2
  only_save_targeted = True
    .help = "If only_target is true, this option to change whether the"
            "dataset
              that is being scaled will be saved on its"
            "own, or combined with the
              already scaled dataset."
    .type = bool
    .expert_level = 2
  target_model = None
    .help = "Path to cif or pdb file to use to calculate target intensities"
            "for scaling. Deprecated, please use the reference= option"
            "instead."
    .type = path
    .expert_level = 2
  target_mtz = None
    .help = "Path to merged mtz file to use as a target for scaling."
            "Deprecated, please use the reference= option instead."
    .type = path
    .expert_level = 2
  reference = None
    .help = "Path to a file to use as a reference for scaling. This can be a"
            "data file containing intensities/amplitudes (.mtz or .cif), or a"
            "model file containing a structure that can be used to calculate"
            "intensities (.cif or .pdb) ."
    .type = path
    .expert_level = 2
  reference_model {
  }
  nproc = 1
    .help = "Number of blocks to divide the data into for minimisation.
      "
            "       This also sets the number of processes to use if the"
            "option is
              available."
    .type = int(value_min=1, allow_none=True)
    .expert_level = 2
  use_free_set = False
    .help = "Option to use a free set during scaling to check for"
            "overbiasing.
              This free set is used to calculate an"
            "RMSD, which is shown alongisde
              the 'working' RMSD"
            "during refinement, but is not currently used
              to"
            "terminate refinement or make any choices on the model."
    .type = bool
    .expert_level = 2
  free_set_percentage = 10.0
    .help = "Percentage of symmetry equivalent groups to use for the free"
            "set,
              if use_free_set is True."
    .type = float(allow_none=True)
    .expert_level = 2
  free_set_offset = 0
    .help = "Offset for choosing unique groups for the free set from the"
            "whole
               set of unique groups."
    .type = int(allow_none=True)
    .expert_level = 2
  full_matrix = True
    .help = "Option to turn off GN/LM refinement round used to determine
     "
            "         error estimates on scale factors."
    .type = bool
    .expert_level = 2
  outlier_rejection = *standard simple
    .help = "Choice of outlier rejection routine. Standard may take a
       "
            "significant amount of time to run for large datasets or high
    "
            "   multiplicities, whereas simple should be quick for these"
            "datasets."
    .type = choice
    .expert_level = 1
  outlier_zmax = 6.0
    .help = "Cutoff z-score value for identifying outliers based on their
    "
            "          normalised deviation within the group of equivalent"
            "reflections"
    .type = float(value_min=3, allow_none=True)
    .expert_level = 1
  emax = 10
    .help = "Reject reflections with normalised intensities E^2 > emax^2"
    .type = float(value_min=0, allow_none=True)
    .expert_level = 2
}
cross_validation {
  cross_validation_mode = multi single
    .help = "Choose the cross validation running mode, for a full description"
            "see the module docstring. Choice is used for testing a parameter"
            "that can only have discrete values (a choice or bool phil"
            "parameter). Variable is used for testing a parameter that can"
            "have a float or int value (that is also not a 'choice' type)."
            "Single just performs cross validation on one parameter"
            "configuration."
    .type = choice
    .expert_level = 2
  parameter = None
    .help = "Optimise a command-line parameter. The full phil path must be :"
            "specified e.g. physical.absorption_correction. The option"
            "parameter_values must also be specified, unless the parameter is"
            "a True/False option."
    .type = str
    .expert_level = 2
  parameter_values = None
    .help = "Parameter values to compare, entered as a string of space"
            "separated values."
    .type = strings
    .expert_level = 2
  nfolds = 1
    .help = "Number of cross-validation folds to perform. If nfolds > 1, the"
            "minimisation for each option is repeated nfolds times, with an"
            "incremental offset for the free set. The max number of folds"
            "allowed is 1/free_set_percentage; if set greater than this then"
            "the repetition will finish after 1/free_set_percentage folds."
    .type = int(value_min=1, allow_none=True)
    .expert_level = 2
}
scaling_refinery
  .help = "Parameters to configure the refinery"
  .expert_level = 1
{
  engine = *SimpleLBFGS GaussNewton LevMar
    .help = "The minimisation engine to use for the main scaling algorithm"
    .type = choice
  refinement_order = *concurrent consecutive
    .help = "Choice of whether to refine all model components concurrently, or"
            "in a consecutive order as allowed/defined by the scaling model."
    .type = choice
    .expert_level = 2
  max_iterations = None
    .help = "Maximum number of iterations in refinement before termination."
            "None implies the engine supplies its own default."
    .type = int(value_min=1, allow_none=True)
  rmsd_tolerance = 0.0001
    .help = "Tolerance at which to stop scaling refinement. This is a"
            "relative
            value, the convergence criterion is (rmsd[i]"
            "- rmsd[i-1])/rmsd[i] <
            rmsd_tolerance."
    .type = float(value_min=1e-06, allow_none=True)
  full_matrix_engine = GaussNewton *LevMar
    .help = "The minimisation engine to use for a full matrix round of
       "
            "     minimisation after the main scaling, in order to determine
 "
            "           error estimates."
    .type = choice
  full_matrix_max_iterations = None
    .help = "Maximum number of iterations before termination in the full"
            "matrix
             minimisation round. None implies the engine"
            "supplies its own default."
    .type = int(value_min=1, allow_none=True)
}
filtering {
  method = None deltacchalf
    .help = "Choice of whether to do any filtering cycles, default None."
    .type = choice
  deltacchalf {
    max_cycles = 6
      .type = int(value_min=1, allow_none=True)
    max_percent_removed = 10
      .type = float(allow_none=True)
    min_completeness = None
      .help = "Desired minimum completeness, as a percentage (0 - 100)."
      .type = float(value_min=0, value_max=100, allow_none=True)
    mode = *dataset image_group
      .help = "Perform analysis on whole datasets or batch groups"
      .type = choice
    group_size = 10
      .help = "The number of images to group together when calculating delta"
              "cchalf in image_group mode"
      .type = int(value_min=1, allow_none=True)
    stdcutoff = 4.0
      .help = "Datasets with a ΔCC½ below (mean - stdcutoff*std) are removed"
      .type = float(allow_none=True)
  }
  output {
    scale_and_filter_results = "scale_and_filter_results.json"
      .help = "Filename for output json of scale and filter results."
      .type = str
  }
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
dataset_selection {
  use_datasets = None
    .help = "Choose a subset of datasets, based on the dataset id (as defined
"
            "              in the reflection table), to use from a"
            "multi-dataset input."
    .type = ints
    .expert_level = 2
  exclude_datasets = None
    .help = "Choose a subset of datasets, based on the dataset id (as defined
"
            "              in the reflection table), to exclude from a"
            "multi-dataset input."
    .type = ints
    .expert_level = 2
}

```