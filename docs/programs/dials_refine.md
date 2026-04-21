# dials.refine

## Introduction
Refine the diffraction geometry of input experiments against the input indexed
reflections. For rotation scans, the model may be either static (the same for
all reflections) or scan-varying (dependent on image number in the scan).
Other basic parameters include control over output filenames, fixing of
certain parameters of each model and options that control the number of
reflections used in refinement.
Examples:
```
dials.refine indexed.expt indexed.refl

dials.refine indexed.expt indexed.refl scan_varying=(False/True/Auto)

```

## Basic parameters
```
output {
  experiments = refined.expt
  reflections = refined.refl
  log = dials.refine.log
}
n_static_macrocycles = 1
separate_independent_sets = True
refinement {
  parameterisation {
    scan_varying = Auto
    interval_width_degrees = None
    set_scan_varying_errors = False
    beam {
      fix = all *in_spindle_plane out_spindle_plane *wavelength
    }
    crystal {
      fix = all cell orientation
    }
    detector {
      fix = all position orientation distance
    }
    goniometer {
      fix = *all in_beam_plane out_beam_plane
    }
  }
  reflections {
    outlier {
      algorithm = null *auto mcd tukey sauter_poon
    }
  }
}

```

## Full parameter definitions
```
output {
  experiments = refined.expt
    .help = "The filename for refined experimental models"
    .type = str
  reflections = refined.refl
    .help = "The filename for reflections with updated predictions"
    .type = str
  include_unused_reflections = True
    .help = "If True, keep reflections unused in refinement in updated"
            "reflections file. Otherwise, remove them"
    .type = bool
    .expert_level = 1
  matches = None
    .help = "The filename for output of the reflection table for reflections"
            "used in refinement, containing extra columns used internally."
            "Intended for debugging purposes only"
    .type = str
    .expert_level = 2
  centroids = None
    .help = "The filename for the table of centroids at the end of refinement"
    .type = str
    .expert_level = 1
  parameter_table = None
    .help = "The filename for the table of scan varying parameter values"
    .type = str
    .expert_level = 1
  log = dials.refine.log
    .type = str
  correlation_plot
    .expert_level = 1
  {
    filename = None
      .help = "The base filename for output of plots of parameter"
              "correlations. A file extension may be added to control the type"
              "of output file, if it is one of matplotlib's supported types. A"
              "JSON file with the same base filename will also be created,"
              "containing the correlation matrix and column labels for later"
              "inspection, replotting etc."
      .type = str
    col_select = None
      .help = "Specific columns to include in the plots of parameter"
              "correlations, either specified by parameter name or 0-based"
              "column index. Defaults to all columns. This option is useful"
              "when there is a large number of parameters"
      .type = strings
    steps = None
      .help = "Steps for which to make correlation plots. By default only the"
              "final step is plotted. Uses zero-based numbering, so the first"
              "step is numbered 0."
      .type = ints(value_min=0)
  }
  history = None
    .help = "The filename for output of the refinement history json"
    .type = str
    .expert_level = 1
}
n_static_macrocycles = 1
  .help = "Number of macro-cycles of static refinement to perform"
  .type = int(value_min=1, allow_none=True)
separate_independent_sets = True
  .help = "If true, the experiment list will be separated into independent"
          "groups that do not share models, and these groups will be refined"
          "separately."
  .type = bool
refinement
  .help = "Parameters to configure the refinement"
{
  mp
    .expert_level = 2
  {
    nproc = 1
      .help = "The number of processes to use. Not all choices of refinement"
              "engine support nproc > 1. Where multiprocessing is possible, it"
              "is helpful only in certain circumstances, so this is not"
              "recommended for typical use."
      .type = int(value_min=1, allow_none=True)
  }
  parameterisation
    .help = "Parameters to control the parameterisation of experimental models"
  {
    auto_reduction
      .help = "determine behaviour when there are too few reflections to"
              "reasonably produce a full parameterisation of the experiment"
              "list"
      .expert_level = 1
    {
      min_nref_per_parameter = 5
        .help = "the smallest number of reflections per parameter for a model"
                "parameterisation below which the parameterisation will not be"
                "made in full, but the action described below will be"
                "triggered."
        .type = int(value_min=1, allow_none=True)
      action = *fail fix remove
        .help = "action to take if there are too few reflections across the"
                "experiments related to a particular model parameterisation."
                "If fail, an exception will be raised and refinement will not"
                "proceed. If fix, refinement will continue but with the"
                "parameters relating to that model remaining fixed at their"
                "initial values. If remove, parameters relating to that model"
                "will be fixed, and in addition all reflections related to"
                "that parameterisation will be removed. This will therefore"
                "remove these reflections from other parameterisations of the"
                "global model too. For example, if a crystal model could not"
                "be parameterised it will be excised completely and not"
                "contribute to the joint refinement of the detector and beam."
                "In the fix mode, reflections emanating from that crystal will"
                "still form residuals and will contribute to detector and beam"
                "refinement."
        .type = choice
    }
    scan_varying = Auto
      .help = "Allow models that are not forced to be static to vary during"
              "the scan, Auto will run one macrocycle with static then scan"
              "varying refinement for the crystal"
      .short_caption = "Scan-varying refinement"
      .type = bool
    interval_width_degrees = None
      .help = "Overall default value of the width of scan between checkpoints"
              "in degrees for scan-varying refinement. If set to None, each"
              "model will use its own specified value."
      .type = float(value_min=0, allow_none=True)
    compose_model_per = image *block
      .help = "For scan-varying parameterisations, compose a new model either"
              "every image or within blocks of a width specified in the"
              "reflections parameters. When this block width is larger than"
              "the image width the result is faster, with a trade-off in"
              "accuracy"
      .type = choice
      .expert_level = 1
    block_width = 1.0
      .help = "Width of a reflection 'block' (in degrees) determining how"
              "fine- grained the model used for scan-varying prediction during"
              "refinement is. Currently only has any effect if the crystal"
              "parameterisation is set to use compose_model_per=block"
      .type = float(value_min=0, allow_none=True)
      .expert_level = 1
    set_scan_varying_errors = False
      .help = "If scan-varying refinement is done, and if the estimated"
              "covariance of the model states have been calculated by the"
              "minimiser, choose whether to return this to the models or not."
              "The default is not to, in order to keep the file size of the"
              "serialized model small. At the moment, this only has an effect"
              "for crystal unit cell (B matrix) errors."
      .type = bool
    trim_scan_to_observations = True
      .help = "For scan-varying refinement, trim scan objects to the range of"
              "observed reflections. This avoids failures in refinement for"
              "cases where the extremes of scans contain no data, such as when"
              "the crystal moves out of the beam."
      .type = bool
      .expert_level = 1
    debug_centroid_analysis = False
      .help = "Set True to write out a file containing the reflections used"
              "for centroid analysis for automatic setting of the "
              "scan-varying interval width. This can then be analysed with"
              "dev.dials.plot_centroid_analysis (requires dials_scratch"
              "repository)."
      .type = bool
      .expert_level = 2
    beam
      .help = "beam parameters"
    {
      fix = all *in_spindle_plane out_spindle_plane *wavelength
        .help = "Whether to fix beam parameters. By default, in_spindle_plane"
                "is selected, and one of the two parameters is fixed. If a"
                "goniometer is present this leads to the beam orientation"
                "being restricted to a direction in the initial spindle-beam"
                "plane. Wavelength is also fixed by default, to allow"
                "refinement of the unit cell volume."
        .short_caption = "Fix beam parameters"
        .type = choice(multi=True)
      fix_list = None
        .help = "Fix specified parameters by a list of 0-based indices or"
                "partial names to match"
        .type = strings
        .expert_level = 1
      constraints
        .help = "Parameter equal shift constraints to use in refinement."
        .multiple = True
        .expert_level = 2
      {
        id = None
          .help = "Select only the specified experiments when looking up which"
                  "parameterisations to apply the constraint to. If an"
                  "identified parameterisation affects multiple experiments"
                  "then the index of any one of those experiments suffices to"
                  "identify that parameterisation. If None (the default) then"
                  "constraints will be applied to all parameterisations of"
                  "this type."
          .type = ints(value_min=0)
        parameter = None
          .help = "Identify which parameter of each parameterisation to"
                  "constrain by a (partial) parameter name to match. Model"
                  "name prefixes such as 'Detector1' will be ignored as"
                  "parameterisations are already identified by experiment id"
          .type = str
      }
      force_static = True
        .help = "Force a static parameterisation for the beam when doing"
                "scan-varying refinement"
        .type = bool
        .expert_level = 1
      smoother
        .help = "Options that affect scan-varying parameterisation"
        .expert_level = 1
      {
        interval_width_degrees = 36.0
          .help = "Width of scan between checkpoints in degrees. Can be set to"
                  "Auto."
          .type = float(value_min=0, allow_none=True)
        absolute_num_intervals = None
          .help = "Number of intervals between checkpoints if scan_varying"
                  "refinement is requested. If set, this overrides"
                  "interval_width_degrees"
          .type = int(value_min=1, allow_none=True)
      }
    }
    crystal
      .help = "crystal parameters"
    {
      fix = all cell orientation
        .help = "Fix crystal parameters"
        .short_caption = "Fix crystal parameters"
        .type = choice
      unit_cell
        .expert_level = 1
      {
        fix_list = None
          .help = "Fix specified parameters by a list of 0-based indices or"
                  "partial names to match"
          .type = strings
          .expert_level = 1
        restraints
          .help = "Least squares unit cell restraints to use in refinement."
          .expert_level = 1
        {
          tie_to_target
            .multiple = True
          {
            values = None
              .help = "Target unit cell parameters for the restraint for this"
                      "parameterisation"
              .type = floats(size=6)
            sigmas = None
              .help = "The unit cell target values are associated with sigmas"
                      "which are used to determine the weight of each"
                      "restraint. A sigma of zero will remove the restraint at"
                      "that position. If symmetry constrains two cell"
                      "dimensions to be equal then only the smaller of the two"
                      "sigmas will be kept"
              .type = floats(size=6, value_min=0)
            id = None
              .help = "Select only the specified experiments when looking up"
                      "which parameterisations to apply these restraints to."
                      "If an identified parameterisation affects multiple"
                      "experiments then the index of any one of those"
                      "experiments suffices to restrain that parameterisation."
                      "If None (the default) then the restraints will be"
                      "applied to all experiments."
              .type = ints(value_min=0)
          }
          tie_to_group
            .multiple = True
          {
            target = *mean low_memory_mean median
              .help = "Function to tie group parameter values to"
              .type = choice
            sigmas = None
              .help = "The unit cell parameters are associated with sigmas"
                      "which are used to determine the weight of each"
                      "restraint. A sigma of zero will remove the restraint at"
                      "that position."
              .type = floats(size=6, value_min=0)
            id = None
              .help = "Select only the specified experiments when looking up"
                      "which  parameterisations to apply these restraints to."
                      "For every parameterisation that requires a restraint at"
                      "least one experiment index must be supplied. If None"
                      "(the default) the restraints will be applied to all"
                      "experiments."
              .type = ints(value_min=0)
          }
        }
        constraints
          .help = "Parameter equal shift constraints to use in refinement."
          .multiple = True
          .expert_level = 2
        {
          id = None
            .help = "Select only the specified experiments when looking up"
                    "which parameterisations to apply the constraint to. If an"
                    "identified parameterisation affects multiple experiments"
                    "then the index of any one of those experiments suffices"
                    "to identify that parameterisation. If None (the default)"
                    "then constraints will be applied to all parameterisations"
                    "of this type."
            .type = ints(value_min=0)
          parameter = None
            .help = "Identify which parameter of each parameterisation to"
                    "constrain by a (partial) parameter name to match. Model"
                    "name prefixes such as 'Detector1' will be ignored as"
                    "parameterisations are already identified by experiment id"
            .type = str
        }
        force_static = False
          .help = "Force a static parameterisation for the crystal unit cell"
                  "when doing scan-varying refinement"
          .type = bool
          .expert_level = 1
        smoother
          .help = "Options that affect scan-varying parameterisation"
          .expert_level = 1
        {
          interval_width_degrees = 36.0
            .help = "Width of scan between checkpoints in degrees. Can be set"
                    "to Auto."
            .type = float(value_min=0, allow_none=True)
          absolute_num_intervals = None
            .help = "Number of intervals between checkpoints if scan_varying"
                    "refinement is requested. If set, this overrides"
                    "interval_width_degrees"
            .type = int(value_min=1, allow_none=True)
        }
      }
      orientation
        .expert_level = 1
      {
        fix_list = None
          .help = "Fix specified parameters by a list of 0-based indices or"
                  "partial names to match"
          .type = strings
          .expert_level = 1
        constraints
          .help = "Parameter equal shift constraints to use in refinement."
          .multiple = True
          .expert_level = 2
        {
          id = None
            .help = "Select only the specified experiments when looking up"
                    "which parameterisations to apply the constraint to. If an"
                    "identified parameterisation affects multiple experiments"
                    "then the index of any one of those experiments suffices"
                    "to identify that parameterisation. If None (the default)"
                    "then constraints will be applied to all parameterisations"
                    "of this type."
            .type = ints(value_min=0)
          parameter = None
            .help = "Identify which parameter of each parameterisation to"
                    "constrain by a (partial) parameter name to match. Model"
                    "name prefixes such as 'Detector1' will be ignored as"
                    "parameterisations are already identified by experiment id"
            .type = str
        }
        force_static = False
          .help = "Force a static parameterisation for the crystal orientation"
                  "when doing scan-varying refinement"
          .type = bool
          .expert_level = 1
        smoother
          .help = "Options that affect scan-varying parameterisation"
          .expert_level = 1
        {
          interval_width_degrees = 36.0
            .help = "Width of scan between checkpoints in degrees. Can be set"
                    "to Auto."
            .type = float(value_min=0, allow_none=True)
          absolute_num_intervals = None
            .help = "Number of intervals between checkpoints if scan_varying"
                    "refinement is requested. If set, this overrides"
                    "interval_width_degrees"
            .type = int(value_min=1, allow_none=True)
        }
      }
    }
    detector
      .help = "detector parameters"
    {
      panels = *automatic single multiple hierarchical
        .help = "Select appropriate detector parameterisation. Both the single"
                "and multiple panel detector options treat the whole detector"
                "as a rigid body. The hierarchical parameterisation treats"
                "groups of panels as separate rigid bodies."
        .type = choice
        .expert_level = 1
      hierarchy_level = 0
        .help = "Level of the detector hierarchy (starting from the root at 0)"
                "at which to determine panel groups to parameterise"
                "independently"
        .type = int(value_min=0, allow_none=True)
        .expert_level = 1
      fix = all position orientation distance
        .help = "Fix detector parameters. The translational parameters"
                "(position) may be set separately to the orientation."
        .short_caption = "Fix detector parameters"
        .type = choice
      fix_list = None
        .help = "Fix specified parameters by a list of 0-based indices or"
                "partial names to match"
        .type = strings
        .expert_level = 1
      constraints
        .help = "Parameter equal shift constraints to use in refinement."
        .multiple = True
        .expert_level = 2
      {
        id = None
          .help = "Select only the specified experiments when looking up which"
                  "parameterisations to apply the constraint to. If an"
                  "identified parameterisation affects multiple experiments"
                  "then the index of any one of those experiments suffices to"
                  "identify that parameterisation. If None (the default) then"
                  "constraints will be applied to all parameterisations of"
                  "this type."
          .type = ints(value_min=0)
        parameter = None
          .help = "Identify which parameter of each parameterisation to"
                  "constrain by a (partial) parameter name to match. Model"
                  "name prefixes such as 'Detector1' will be ignored as"
                  "parameterisations are already identified by experiment id"
          .type = str
      }
      force_static = True
        .help = "Force a static parameterisation for the detector when doing"
                "scan-varying refinement"
        .type = bool
        .expert_level = 1
      smoother
        .help = "Options that affect scan-varying parameterisation"
        .expert_level = 1
      {
        interval_width_degrees = 36.0
          .help = "Width of scan between checkpoints in degrees. Can be set to"
                  "Auto."
          .type = float(value_min=0, allow_none=True)
        absolute_num_intervals = None
          .help = "Number of intervals between checkpoints if scan_varying"
                  "refinement is requested. If set, this overrides"
                  "interval_width_degrees"
          .type = int(value_min=1, allow_none=True)
      }
    }
    goniometer
      .help = "goniometer setting matrix parameters"
    {
      fix = *all in_beam_plane out_beam_plane
        .help = "Whether to fix goniometer parameters. By default, fix all."
                "Alternatively the setting matrix can be constrained to allow"
                "rotation only within the spindle-beam plane or to allow"
                "rotation only around an axis that lies in that plane. Set to"
                "None to refine the in two orthogonal directions."
        .short_caption = "Fix goniometer parameters"
        .type = choice(multi=True)
      fix_list = None
        .help = "Fix specified parameters by a list of 0-based indices or"
                "partial names to match"
        .type = strings
        .expert_level = 1
      constraints
        .help = "Parameter equal shift constraints to use in refinement."
        .multiple = True
        .expert_level = 2
      {
        id = None
          .help = "Select only the specified experiments when looking up which"
                  "parameterisations to apply the constraint to. If an"
                  "identified parameterisation affects multiple experiments"
                  "then the index of any one of those experiments suffices to"
                  "identify that parameterisation. If None (the default) then"
                  "constraints will be applied to all parameterisations of"
                  "this type."
          .type = ints(value_min=0)
        parameter = None
          .help = "Identify which parameter of each parameterisation to"
                  "constrain by a (partial) parameter name to match. Model"
                  "name prefixes such as 'Detector1' will be ignored as"
                  "parameterisations are already identified by experiment id"
          .type = str
      }
      force_static = True
        .help = "Force a static parameterisation for the goniometer when doing"
                "scan-varying refinement"
        .type = bool
        .expert_level = 1
      smoother
        .help = "Options that affect scan-varying parameterisation"
        .expert_level = 1
      {
        interval_width_degrees = 36.0
          .help = "Width of scan between checkpoints in degrees. Can be set to"
                  "Auto."
          .type = float(value_min=0, allow_none=True)
        absolute_num_intervals = None
          .help = "Number of intervals between checkpoints if scan_varying"
                  "refinement is requested. If set, this overrides"
                  "interval_width_degrees"
          .type = int(value_min=1, allow_none=True)
      }
    }
    sparse = Auto
      .help = "Calculate gradients using sparse data structures."
      .type = bool
      .expert_level = 1
    treat_single_image_as_still = False
      .help = "Set this to True to treat a single image scan with a non zero"
              "oscillation width as a still"
      .type = bool
      .expert_level = 1
    spherical_relp_model = False
      .help = "For stills refinement, set true to use the spherical relp model"
              "for prediction and gradients."
      .type = bool
      .expert_level = 1
  }
  refinery
    .help = "Parameters to configure the refinery"
    .expert_level = 1
  {
    engine = SimpleLBFGS LBFGScurvs GaussNewton *LevMar SparseLevMar
      .help = "The minimisation engine to use"
      .type = choice
    max_iterations = None
      .help = "Maximum number of iterations in refinement before termination."
              "None implies the engine supplies its own default."
      .type = int(value_min=1, allow_none=True)
    log = None
      .help = "Filename for an optional log that a minimisation engine may use"
              "to write additional information"
      .type = path
    journal
      .help = "Extra items to track in the refinement history"
    {
      track_step = False
        .help = "Record parameter shifts history in the refinement journal, if"
                "the engine supports it."
        .type = bool
      track_gradient = False
        .help = "Record parameter gradients history in the refinement journal,"
                "if the engine supports it."
        .type = bool
      track_parameter_correlation = False
        .help = "Record correlation matrix between columns of the Jacobian for"
                "each step of refinement."
        .type = bool
      track_jacobian_structure = False
        .help = "Record numbers of explicit and structural zeroes in each"
                "column of the Jacobian at each step of refinement."
        .type = bool
      track_condition_number = False
        .help = "Record condition number of the Jacobian for each step of "
                "refinement."
        .type = bool
      track_normal_matrix = False
        .help = "Record the full normal matrix at each step of refinement"
        .type = bool
      track_out_of_sample_rmsd = False
        .help = "Record RMSDs calculated using the refined experiments with"
                "reflections not used in refinement at each step. Only valid"
                "if a subset of input reflections was taken for refinement"
        .type = bool
    }
  }
  target
    .help = "Parameters to configure the target function"
    .expert_level = 1
  {
    rmsd_cutoff = *fraction_of_bin_size absolute
      .help = "Method to choose rmsd cutoffs. This is currently either as a"
              "fraction of the discrete units of the spot positional data,"
              "i.e. (pixel width, pixel height, image thickness in phi), or a"
              "tuple of absolute values to use as the cutoffs"
      .type = choice
    bin_size_fraction = 0.0
      .help = "Set this to a fractional value, say 0.2, to make a cut off in"
              "the natural discrete units of positional data, viz., (pixel"
              "width, pixel height, image thickness in phi). This would then"
              "determine when the RMSD target is achieved. Only used if"
              "rmsd_cutoff = fraction_of_bin_size."
      .type = float(value_min=0, allow_none=True)
    absolute_cutoffs = None
      .help = "Absolute Values for the RMSD target achieved cutoffs in X, Y"
              "and Phi. The units are (mm, mm, rad)."
      .type = floats(size=3, value_min=0)
    gradient_calculation_blocksize = None
      .help = "Maximum number of reflections to use for gradient calculation."
              "If there are more reflections than this in the manager then the"
              "minimiser must do the full calculation in blocks."
      .type = int(value_min=1, allow_none=True)
  }
  reflections
    .help = "Parameters used by the reflection manager"
  {
    reflections_per_degree = Auto
      .help = "The number of centroids per degree of the sequence to use in"
              "refinement. The default (Auto) uses all reflections unless the"
              "dataset is wider than a single turn. Then the number of"
              "reflections may be reduced until a minimum of 100 per degree of"
              "the sequence is reached to speed up calculations. Set this to"
              "None to force use all of suitable reflections."
      .type = float(value_min=0, allow_none=True)
      .expert_level = 1
    minimum_sample_size = 1000
      .help = "cutoff that determines whether subsetting of the input"
              "reflection list is done"
      .type = int(allow_none=True)
      .expert_level = 1
    maximum_sample_size = None
      .help = "The maximum number of reflections to use in refinement."
              "Overrides reflections_per_degree if that produces a larger"
              "sample size."
      .type = int(value_min=1, allow_none=True)
      .expert_level = 1
    random_seed = 42
      .help = "Random seed to use when sampling to create a working set of"
              "reflections. May be int or None."
      .type = int(allow_none=True)
      .expert_level = 1
    close_to_spindle_cutoff = 0.02
      .help = "The inclusion criterion currently uses the volume of the"
              "parallelepiped formed by the spindle axis, the incident beam"
              "and the scattered beam. If this is lower than some value then"
              "the reflection is excluded from refinement. In detector space,"
              "these are the reflections located close to the rotation axis."
      .type = float(value_min=0, allow_none=True)
      .expert_level = 1
    scan_margin = 0.0
      .help = "Reflections within this value in degrees from the centre of the"
              "first or last image of the scan will be removed before"
              "refinement, unless doing so would result in too few remaining"
              "reflections. Reflections that are truncated at the scan edges"
              "have poorly-determined centroids and can bias the refined model"
              "if they are included."
      .type = float(value_min=0, value_max=5, allow_none=True)
      .expert_level = 1
    weighting_strategy
      .help = "Parameters to configure weighting strategy overrides"
      .expert_level = 1
    {
      override = statistical stills constant external_deltapsi
        .help = "selection of a strategy to override default weighting"
                "behaviour"
        .type = choice
      delpsi_constant = 1000000
        .help = "used by the stills strategy to choose absolute weight value"
                "for the angular distance from Ewald sphere term of the target"
                "function, whilst the X and Y parts use statistical weights"
        .type = float(value_min=0, allow_none=True)
      constants = 1.0 1.0 1.0
        .help = "constant weights for three parts of the target function,"
                "whether the case is for stills or scans. The default gives"
                "unit weighting."
        .type = floats(size=3, value_min=0)
      wavelength_weight = 1e4
        .help = "Weight for the wavelength term in the target function for"
                "Laue refinement"
        .type = float(value_min=0, allow_none=True)
    }
    outlier
      .help = "Outlier rejection after initial reflection prediction."
    {
      algorithm = null *auto mcd tukey sauter_poon
        .help = "Outlier rejection algorithm. If auto is selected, the"
                "algorithm is chosen automatically."
        .short_caption = "Outlier rejection algorithm"
        .type = choice
      nproc = Auto
        .help = "Number of processes over which to split outlier"
                "identification. If set to Auto, DIALS will choose"
                "automatically."
        .type = int(value_min=1, allow_none=True)
        .expert_level = 1
      minimum_number_of_reflections = 20
        .help = "The minimum number of input observations per outlier"
                "rejection job below which all reflections in the job will be"
                "rejected as potential outliers."
        .type = int(value_min=0, allow_none=True)
        .expert_level = 1
      separate_experiments = True
        .help = "If true, outlier rejection will be performed on each"
                "experiment separately. Otherwise, the data from all"
                "experiments will be combined for outlier rejection."
        .type = bool
        .expert_level = 1
      separate_panels = False
        .help = "Perform outlier rejection separately for each panel of a"
                "multi- panel detector model. Otherwise data from across all"
                "panels will be combined for outlier rejection."
        .type = bool
        .expert_level = 1
      separate_blocks = True
        .help = "If true, for scans outlier rejection will be performed"
                "separately in equal-width blocks of phi, controlled by the"
                "parameter outlier.block_width."
        .type = bool
        .expert_level = 1
      block_width = Auto
        .help = "If separate_blocks, a scan will be divided into equal-sized"
                "blocks with width (in degrees) close to this value for"
                "outlier rejection. If Auto, a width of at least 18 degrees"
                "will be determined, such that each block contains enough"
                "reflections to perform outlier rejection."
        .type = float(value_min=1, allow_none=True)
        .expert_level = 1
      separate_images = False
        .help = "If true, every image will be treated separately for outlier"
                "rejection. It is a special case that will override both"
                "separate_experiments and separate_blocks, and will set these"
                "to False if required."
        .type = bool
        .expert_level = 2
      tukey
        .help = "Options for the tukey outlier rejector"
        .expert_level = 1
      {
        iqr_multiplier = 1.5
          .help = "The IQR multiplier used to detect outliers. A value of 1.5"
                  "gives Tukey's rule for outlier detection"
          .type = float(value_min=0, allow_none=True)
      }
      mcd
        .help = "Options for the mcd outlier rejector, which uses an algorithm"
                "based on FAST-MCD by Rousseeuw and van Driessen. See"
                "doi.org/10.1080/00401706.1999.10485670."
        .expert_level = 1
      {
        positional_coordinates = *auto xy radial_transverse \
                                 deltatt_transverse
          .help = "Whether to use xy spot coordinates in image space,"
                  "radial/transverse spot coordinates relative to the beam"
                  "vector, or a mix of delta two theta and transverse"
                  "coordinates."
          .type = choice
        rotational_coordinates = *auto null phi deltapsi delpsidstar
          .help = "Whether to use phi rotation, delta psi angle, or deltapsi"
                  "normalized by resolution as coordinates. Null means only"
                  "use positional_coordinates."
          .type = choice
        alpha = 0.5
          .help = "Decimal fraction controlling the size of subsets over which"
                  "the covariance matrix determinant is minimised."
          .type = float(value_min=0, value_max=1, allow_none=True)
        max_n_groups = 5
          .help = "The maximum number of groups to split the dataset into if"
                  "the dataset is 'large' (more observations than twice the"
                  "min_group_size)."
          .type = int(value_min=1, allow_none=True)
        min_group_size = 300
          .help = "The smallest sub-dataset size when splitting the dataset"
                  "into a number of groups, maximally max_n_groups."
          .type = int(value_min=100, allow_none=True)
        n_trials = 500
          .help = "The number of samples used for initial estimates to seed"
                  "the search within each sub-dataset."
          .type = int(value_min=1, allow_none=True)
        k1 = 2
          .help = "The number of concentration steps to take after initial"
                  "estimates."
          .type = int(value_min=1, allow_none=True)
        k2 = 2
          .help = "If the dataset is 'large', the number of concentration"
                  "steps to take after applying the best subset estimates to"
                  "the merged group."
          .type = int(value_min=1, allow_none=True)
        k3 = 100
          .help = "If the dataset is 'small', the number of concentration"
                  "steps to take after selecting the best of the initial"
                  "estimates, applied to the whole dataset."
          .type = int(value_min=1, allow_none=True)
        threshold_probability = 0.975
          .help = "Quantile probability from the Chi-squared distribution with"
                  "number of degrees of freedom equal to the number of"
                  "dimensions of the data data (e.g. 3 for X, Y and Phi"
                  "residuals). Observations whose robust Mahalanobis distances"
                  "are larger than the obtained quantile will be flagged as"
                  "outliers."
          .type = float(value_min=0, value_max=1, allow_none=True)
      }
      sauter_poon
        .help = "Options for the outlier rejector described in Sauter & Poon"
                "(2010) (https://doi.org/10.1107/S0021889810010782)"
        .expert_level = 1
      {
        px_sz = Auto
          .help = "X, Y pixel size in mm. If Auto, this will be taken from the"
                  "first panel of the first experiment."
          .type = floats(size=2, value_min=0.001)
        verbose = False
          .help = "Verbose output."
          .type = bool
          .multiple = False
        pdf = None
          .help = "Output file name for making graphs of |dr| vs spot number"
                  "and dy vs dx."
          .type = str
          .multiple = False
      }
    }
  }
}

```