# dials.find_spots

## Introduction
This program tries to find strong spots on a sequence of images. The program can
be called with either a “models.expt” file or a sequence of image files (see
help for dials.import for more information about how images are imported). Spot
finding will be done against each logically grouped set of images given. Strong
pixels will be found on each image and spots will be formed from connected
components. In the case of rotation images, connected component labelling will
be done in 3D.
Once a set of spots have been found, their centroids and intensities will be
calculated. They will then be filtered according to the particular preferences
of the user. The output will be a file (strong.refl) containing a list of spot
centroids and intensities which can be used in the dials.index program. To view
a list of parameters for spot finding use the –show-config option.
Examples:
```
dials.find_spots image1.cbf

dials.find_spots imager_00*.cbf

dials.find_spots models.expt

dials.find_spots models.expt output.reflections=strong.refl

```

## Basic parameters
```
output {
  reflections = 'strong.refl'
  shoeboxes = True
  experiments = None
  log = 'dials.find_spots.log'
}
per_image_statistics = False
spotfinder {
  lookup {
    mask = None
  }
  write_hot_mask = False
  hot_mask_prefix = 'hot_mask'
  force_2d = False
  scan_range = None
  region_of_interest = None
  compute_mean_background = False
  filter {
    min_spot_size = Auto
    max_spot_size = 1000
    max_strong_pixel_fraction = 0.25
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
  mp {
    method = *none drmaa sge lsf pbs
    njobs = 1
    nproc = 1
    chunksize = auto
    min_chunksize = 20
  }
  tof {
    rs_proximity_threshold_multiplier = None
  }
  laue {
    initial_wavelength = None
  }
  threshold {
    algorithm = dispersion *dispersion_extended radial_profile
    dispersion {
      gain = None
      global_threshold = 0
    }
    radial_profile {
      n_iqr = 6
      blur = narrow wide
      n_bins = 100
    }
  }
}

```

## Full parameter definitions
```
output {
  reflections = 'strong.refl'
    .help = "The output filename"
    .type = str
  shoeboxes = True
    .help = "Save the raw pixel values inside the reflection shoeboxes."
    .type = bool
  experiments = None
    .help = "Save the modified experiments. (usually only modified with hot"
            "pixel mask)"
    .type = str
  log = 'dials.find_spots.log'
    .help = "The log filename"
    .type = str
}
maximum_trusted_value = None
  .help = "Override maximum trusted value for spot finding only"
  .type = float(allow_none=True)
  .expert_level = 2
per_image_statistics = False
  .help = "Whether or not to print a table of per-image statistics."
  .type = bool
spotfinder
  .help = "Parameters used in the spot finding algorithm."
{
  lookup
    .help = "Parameters specifying lookup file path"
  {
    mask = None
      .help = "The path to the mask file."
      .type = str
  }
  write_hot_mask = False
    .help = "Write the hot mask"
    .type = bool
  hot_mask_prefix = 'hot_mask'
    .help = "Prefix for the hot mask pickle file"
    .type = str
  force_2d = False
    .help = "Do spot finding in 2D"
    .type = bool
  scan_range = None
    .help = "The range of images to use in finding spots. The ranges are"
            "inclusive (e.g. j0 <= j < j1). For sequences the scan range is"
            "interpreted as the literal scan range. Whereas for imagesets the"
            "scan range is interpreted as the image number in the imageset."
            "Multiple ranges can be specified by repeating the scan_range="
            "parameter."
    .type = ints(size=2)
    .multiple = True
  exclude_images = None
    .help = "Input in the format exp:start:end Exclude a range of images"
            "(start, stop) from the dataset with experiment identifier exp "
            "(inclusive of frames start, stop). Multiple ranges can be given"
            "in one go, e.g. exclude_images=0:150:200,1:200:250"
            "exclude_images='0:150:200 1:200:250'"
    .short_caption = "Exclude images"
    .type = strings
    .multiple = True
    .expert_level = 1
  exclude_images_multiple = None
    .help = "Exclude this single image and each multiple of this image number"
            "in each experiment. This is provided as a convenient shorthand to"
            "specify image exclusions for cRED data, where the scan of"
            "diffraction images is interrupted at regular intervals by a"
            "crystal positioning image (typically every 20th image)."
    .type = int(value_min=2, allow_none=True)
    .expert_level = 2
  region_of_interest = None
    .help = "A region of interest to look for spots. Specified as: x0,x1,y0,y1"
            "The pixels x0 and y0 are included in the range but the pixels x1"
            "and y1 are not. To specify an ROI covering the whole image set"
            "region_of_interest=0,width,0,height."
    .type = ints(size=4)
  compute_mean_background = False
    .help = "Compute the mean background for each image"
    .type = bool
  filter
    .help = "Parameters used in the spot finding filter strategy."
  {
    min_spot_size = Auto
      .help = "The minimum number of contiguous pixels for a spot to be"
              "accepted by the filtering algorithm."
      .type = int(value_min=1, allow_none=True)
    max_spot_size = 1000
      .help = "The maximum number of contiguous pixels for a spot to be"
              "accepted by the filtering algorithm."
      .type = int(value_min=1)
    max_separation = 2
      .help = "The maximum peak-to-centroid separation (in pixels) for a spot"
              "to be accepted by the filtering algorithm."
      .type = float(value_min=0, allow_none=True)
      .expert_level = 1
    max_strong_pixel_fraction = 0.25
      .help = "If the fraction of pixels in an image marked as strong is"
              "greater than this value, throw an exception"
      .type = float(value_min=0, value_max=1, allow_none=True)
    background_gradient
      .expert_level = 2
    {
      filter = False
        .type = bool
      background_size = 2
        .type = int(value_min=1, allow_none=True)
      gradient_cutoff = 4
        .type = float(value_min=0, allow_none=True)
    }
    spot_density
      .expert_level = 2
    {
      filter = False
        .type = bool
    }
    border = 0
      .help = "The border around the edge of the image."
      .type = int(allow_none=True)
    d_min = None
      .help = "The high resolution limit in Angstrom for a pixel to be"
              "accepted by the filtering algorithm."
      .type = float(value_min=0, allow_none=True)
    d_max = None
      .help = "The low resolution limit in Angstrom for a pixel to be accepted"
              "by the filtering algorithm."
      .type = float(value_min=0, allow_none=True)
    disable_parallax_correction = False
      .help = "Set to ``True`` to use a faster, but less accurate, simple"
              "px-to-mm  mapping by disabling accounting for parallax"
              "correction when generating  resolution masks."
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
        .help = "The pixel coordinates (fast, slow) that define the corners "
                "of the untrusted polygon. Spots whose centroids fall within "
                "the bounds of the untrusted polygon will be rejected."
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
  mp {
    method = *none drmaa sge lsf pbs
      .help = "The cluster method to use"
      .type = choice
    njobs = 1
      .help = "The number of cluster jobs to use"
      .type = int(value_min=1, allow_none=True)
    nproc = 1
      .help = "The number of processes to use per cluster job"
      .type = int(value_min=1, allow_none=True)
    chunksize = auto
      .help = "The number of jobs to process per process"
      .type = int(value_min=1, allow_none=True)
    min_chunksize = 20
      .help = "When chunksize is auto, this is the minimum chunksize"
      .type = int(value_min=1, allow_none=True)
  }
  tof {
    rs_proximity_threshold_multiplier = None
      .help = "If not None, spots in close proximity in reciprocal space are"
              "filtered out based on this value. The distance is calculated as"
              "the first peak of a histrogram of distances, multiplied by the"
              "rs_proximity_threshold_multiplier"
      .type = float(allow_none=True)
  }
  laue {
    initial_wavelength = None
      .help = "Initial wavelength assignment for reflections from Laue data If"
              "None, initial_wavelength will be set as the average of "
              "beam.wavelength_range"
      .type = float(value_min=0.1, allow_none=True)
  }
  threshold
    .help = "Extensions for threshold algorithms to be used in spot finding."
  {
    algorithm = dispersion *dispersion_extended radial_profile
      .help = "The choice of algorithm"
      .type = choice
    dispersion
      .help = "Extensions to do dispersion threshold."
    {
      gain = None
        .help = "Use a flat gain map for the entire detector to act as a"
                "multiplier for the gain set by the format. Cannot be used in"
                "conjunction with lookup.gain_map parameter."
        .type = float(value_min=0, allow_none=True)
      kernel_size = 3 3
        .help = "The size of the local area around the spot in which to"
                "calculate the mean and variance. The kernel is given as a box"
                "of size (2 * nx + 1, 2 * ny + 1) centred at the pixel."
        .type = ints(size=2)
        .expert_level = 1
      sigma_background = 6
        .help = "The number of standard deviations of the index of dispersion"
                "(variance / mean) in the local area below which the pixel"
                "will be classified as background."
        .type = float(allow_none=True)
        .expert_level = 1
      sigma_strong = 3
        .help = "The number of standard deviations above the mean in the local"
                "area above which the pixel will be classified as strong."
        .type = float(allow_none=True)
        .expert_level = 1
      min_local = 2
        .help = "The minimum number of pixels under the image processing"
                "kernel that are need to do the thresholding operation."
                "Setting the value between 2 and the total number of pixels"
                "under the kernel will force the algorithm to use that number"
                "as the minimum. If the value is less than or equal to zero,"
                "then the algorithm will use all pixels under the kernel. In"
                "effect this will add a border of pixels which are always"
                "classed as background around the edge of the image and around"
                "any masked out pixels."
        .type = int(allow_none=True)
        .expert_level = 1
      global_threshold = 0
        .help = "The global threshold value. Consider all pixels less than"
                "this value to be part of the background."
        .type = float(allow_none=True)
    }
    radial_profile
      .help = "Extension to calculate a radial profile threshold. This method"
              "calculates background value and iqr in 2θ shells, then sets a"
              "threshold at a level n_iqr above the radial background. As"
              "such, it is important to have the beam centre correct and to"
              "mask out any significant shadows. The method may be"
              "particularly useful for electron diffraction images, where"
              "there can be considerable inelastic scatter around low"
              "resolution spots. In addition, the algorithm is relatively"
              "insensitive to noise properties of the detector. This helps for"
              "the case of integrating detectors with poorly known gain and"
              "response statistics. A similar algorithm is available in other"
              "programs. The description of 'peakfinder 8' in"
              "https://doi.org/10.1107/S1600576714007626 was helpful in the"
              "development of this method."
    {
      n_iqr = 6
        .help = "IQR multiplier for determining the threshold value"
        .type = int(allow_none=True)
      blur = narrow wide
        .help = "Optional preprocessing of the image by a convolution with a"
                "simple Gaussian kernel of size either 3×3 (narrow) or 5×5"
                "(wide). This may help to reduce noise peaks and to combine"
                "split spots."
        .type = choice
      n_bins = 100
        .help = "Number of 2θ bins in which to calculate background"
        .type = int(allow_none=True)
    }
  }
}

```