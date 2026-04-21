# dials.combine_experiments

## Introduction
Utility script to combine multiple reflections and experiments files into
one multi-experiment reflections and one experiments file. Experiments are
matched to reflections in the order they are provided as input.
Reference models can be chosen from any of the input experiments files. These
will replace all other models of that type in the output experiments file.
This is useful, for example, for combining multiple experiments that should
differ only in their crystal models. No checks are made to ensure that a
reference model is a good replacement model.
Although only one reference model of each type is allowed, more complex
combinations of experiments can be created by repeat runs.
Examples:
```
dials.combine_experiments experiments_0.expt experiments_1.expt \
  reflections_0.refl reflections_1.refl \
  reference_from_experiment.beam=0 \
  reference_from_experiment.detector=0

```

## Basic parameters
```
output {
  log = dials.combine_experiments.log
}
reference_from_experiment {
  beam = None
  scan = None
  crystal = None
  goniometer = None
  detector = None
  average_detector = False
  compare_models = True
  average_hierarchy_level = None
}
clustering {
  use = False
  dendrogram = False
  threshold = 1000
  max_clusters = None
  exclude_single_crystal_clusters = True
}
output {
  experiments_filename = combined.expt
  reflections_filename = combined.refl
  n_subset = None
  n_subset_method = *random n_refl significance_filter
  n_refl_panel_list = None
}

```

## Full parameter definitions
```
output {
  log = dials.combine_experiments.log
    .type = str
}
reference_from_experiment {
  beam = None
    .help = "Take beam model from this experiment to overwrite all other beam"
            "models in the combined experiments"
    .type = int(value_min=0, allow_none=True)
  scan = None
    .help = "Take scan model from this experiment to overwrite all other scan"
            "models in the combined experiments"
    .type = int(value_min=0, allow_none=True)
  crystal = None
    .help = "Take crystal model from this experiment to overwrite all other"
            "crystal models in the combined experiments"
    .type = int(value_min=0, allow_none=True)
  goniometer = None
    .help = "Take goniometer model from this experiment to overwrite all other"
            "goniometer models in the combined experiments"
    .type = int(value_min=0, allow_none=True)
  detector = None
    .help = "Take detector model from this experiment to overwrite all other"
            "detector models in the combined experiments"
    .type = int(value_min=0, allow_none=True)
  average_detector = False
    .help = "Create an average detector model from all the input detector"
            "models and use it as the reference. Not compatible with"
            "reference_from_experiment.detector"
    .type = bool
  compare_models = True
    .help = "Whether to compare a model with the reference model before"
            "replacing it. If the comparison falls outside the tolerance, the"
            "combination will not be allowed. Disable comparison to force"
            "overwriting of models with the reference"
    .type = bool
  average_hierarchy_level = None
    .help = "For hierarchical detectors, optionally provide a single level to"
            "do averaging at."
    .type = int(value_min=0, allow_none=True)
  tolerance
    .help = "Tolerances used to determine shared models"
    .expert_level = 2
  {
    beam {
      wavelength = 1e-6
        .help = "The wavelength tolerance"
        .type = float(value_min=0, allow_none=True)
      direction = 1e-6
        .help = "The direction tolerance"
        .type = float(value_min=0, allow_none=True)
      polarization_normal = 1e-6
        .help = "The polarization normal tolerance"
        .type = float(value_min=0, allow_none=True)
      polarization_fraction = 1e-6
        .help = "The polarization fraction tolerance"
        .type = float(value_min=0, allow_none=True)
    }
    detector {
      fast_axis = 1e-6
        .help = "The fast axis tolerance"
        .type = float(value_min=0, allow_none=True)
      slow_axis = 1e-6
        .help = "The slow axis tolerance"
        .type = float(value_min=0, allow_none=True)
      origin = 5e-2
        .help = "The origin tolerance"
        .type = float(value_min=0, allow_none=True)
    }
    goniometer {
      rotation_axis = 1e-6
        .help = "The rotation axis tolerance"
        .type = float(value_min=0, allow_none=True)
      fixed_rotation = 1e-6
        .help = "The fixed rotation tolerance"
        .type = float(value_min=0, allow_none=True)
      setting_rotation = 1e-6
        .help = "The setting rotation tolerance"
        .type = float(value_min=0, allow_none=True)
    }
    scan {
      oscillation = 0.03
        .help = "The oscillation tolerance for the scan, as a fraction of the"
                "image width"
        .type = float(value_min=0, allow_none=True)
    }
  }
}
clustering {
  use = False
    .help = "Separate experiments into subsets using the clustering toolkit."
            "One json per cluster will be saved."
    .type = bool
  dendrogram = False
    .help = "Display dendrogram of the clustering results. Should not be used"
            "with parallel processing."
    .type = bool
  threshold = 1000
    .help = "Threshold used in the dendrogram to separate into clusters."
    .type = int(allow_none=True)
  max_clusters = None
    .help = "Maximum number of clusters to save as jsons."
    .type = int(allow_none=True)
  exclude_single_crystal_clusters = True
    .help = "Don't produce a 'cluster' containing only one crystal."
    .type = bool
}
output {
  experiments_filename = combined.expt
    .help = "The filename for combined experimental models"
    .type = str
  reflections_filename = combined.refl
    .help = "The filename for combined reflections"
    .type = str
  n_subset = None
    .help = "If not None, keep a subset of size n_subset when saving the"
            "combined experiments"
    .type = int(allow_none=True)
  n_subset_method = *random n_refl significance_filter
    .help = "Algorithm to be used for choosing the n_subset images/"
            "experiments for refinement.  n_refl chooses the set with the"
            "largest numbers of reflections listed in the pickle files"
            "significance filter used to select n_subset images based on"
            "I/sig(I) cutoff"
    .type = choice
  n_refl_panel_list = None
    .help = "If n_subset_method is n_refl, specify which panels to search on."
    .type = ints
  max_batch_size = None
    .help = "If not None, split the resultant combined set of experiments into"
            "separate files, each at most max_batch_size number of"
            "experiments. Example, if there were 5500 experiments and"
            "max_batch_size is 1000, 6 experiment lists will be created, of"
            "sizes 917, 917, 917, 917, 916, 916"
    .type = int(allow_none=True)
    .expert_level = 2
  delete_shoeboxes = False
    .help = "If true, delete shoeboxes from reflection tables while comb-"
            "ining them to save on memory."
    .type = bool
    .expert_level = 2
  min_reflections_per_experiment = None
    .help = "If not None, throw out any experiment with fewer than this many"
            "reflections"
    .type = int(allow_none=True)
    .expert_level = 2
  max_reflections_per_experiment = None
    .help = "If not None, throw out any experiment with more than this many"
            "reflections"
    .type = int(allow_none=True)
    .expert_level = 2
  sort_by_imageset_path_and_image_index = False
    .help = "If True, sort the experiments and reflections first by path then"
            "by image number (for composite files like HDF5)"
    .type = bool
    .expert_level = 2
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
}

```