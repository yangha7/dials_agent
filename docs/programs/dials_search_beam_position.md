# dials.search_beam_position

## Introduction
A function to find beam center from diffraction images
The default method (based on the work of Sauter et al., J. Appl. Cryst.
37, 399-409 (2004)) is using the results from spot finding.

Example:dials.search_beam_position imported.expt strong.refl

Other methods are based on horizontal and vertical projection, and only
require an imported experiment.

Example:dials.search_beam_position method=midpoint imported.expt

More information about the projection methods can be found at
https://autoed.readthedocs.io/en/latest/pages/beam_position_methods.html

## Basic parameters
```
method = default midpoint maximum inversion
default {
  nproc = Auto
  plot_search_scope = False
  max_cell = None
  image_range = None
  max_reflections = 10000
  mm_search_scope = 4.0
  wide_search_binning = 2
  n_macro_cycles = 1
  d_min = None
  seed = 42
}
projection {
  method_x = midpoint maximum inversion
  method_y = midpoint maximum inversion
  plot = True
  bar = True
  exclude_pixel_range_x = None
  exclude_pixel_range_y = None
  per_image = False
  color_cutoff = None
  midpoint {
    exclude_intensity_percent = 0.01
    intersection_range = (0.3, 0.9, 0.01)
    convolution_width = 80
    dead_pixel_range_x = None
    dead_pixel_range_y = None
    intersection_min_width = 10
  }
  maximum {
    bad_pixel_threshold = None
    n_convolutions = 1
    convolution_width = 1
    bin_width = 20
    bin_step = 10
  }
  inversion {
    bad_pixel_threshold = None
    guess_position = None
    inversion_window_width = 400
    background_cutoff = None
    convolution_width = 1
  }
}
output {
  experiments = optimised.expt
  log = "dials.search_beam_position.log"
  json = "beam_positions.json"
}

```

## Full parameter definitions
```
method = default midpoint maximum inversion
default {
  nproc = Auto
    .type = int(value_min=1, allow_none=True)
  plot_search_scope = False
    .type = bool
  max_cell = None
    .help = "Known max cell (otherwise will compute from spot positions)"
    .type = float(allow_none=True)
  image_range = None
    .help = "The range of images to use in indexing. Number of arguments must"
            "be a factor of two. Specifying  0 0\" will use all images\" by"
            "default. The given range follows C conventions (e.g. j0 <= j <"
            "j1)."
    .type = ints(size=2)
    .multiple = True
  max_reflections = 10000
    .help = "Maximum number of reflections to use in the search for better"
            "experimental model. If the number of input reflections is "
            "greater then a random subset of reflections will be used."
    .type = int(value_min=1, allow_none=True)
  mm_search_scope = 4.0
    .help = "Global radius of origin offset search."
    .type = float(value_min=0, allow_none=True)
  wide_search_binning = 2
    .help = "Modify the coarseness of the wide grid search for  the beam"
            "centre."
    .type = float(value_min=0, allow_none=True)
  n_macro_cycles = 1
    .help = "Number of macro cycles for an iterative beam centre search."
    .type = int(allow_none=True)
  d_min = None
    .type = float(value_min=0, allow_none=True)
  seed = 42
    .type = int(value_min=0, allow_none=True)
}
projection {
  method_x = midpoint maximum inversion
    .help = "The projection method along the x-axis."
    .type = str
  method_y = midpoint maximum inversion
    .help = "The projection method along the y-axis."
    .type = str
  plot = True
    .help = "Plot the diffraction image with the computed beam center."
    .type = bool
  bar = True
    .help = "Print progress bar."
    .type = bool
  exclude_pixel_range_x = None
    .help = "List of comma-separated pairs of numbers specifying pixel ranges "
            "in the x direction to exclude from projection to the y-axis "
            "(e.g., exclude_pixel_range_x=20,350,700,800 would exclude ranges "
            "20-350 and 700-800). Indexing assumes Python (or C)  conventions."
            "The first pixel has an index 0, the last pixel has  an index N-1"
            "(here N is the number of pixels along the x-axis).  The last"
            "pixel in the range is not included, e.g., '0,N' would  exclude"
            "the entire range, while '0,3' would exclude pixels 0, 1,  and 2."
    .type = ints
    .multiple = True
  exclude_pixel_range_y = None
    .help = "List of pixel ranges to exclude from projection to the y-axis. "
            "See `exclude_pixel_range_x` for more details."
    .type = ints
    .multiple = True
  per_image = False
    .help = "Compute the beam position for each image. Otherwise, compute the "
            "beam position for a single (average) image."
    .type = bool
  color_cutoff = None
    .help = "The maximum of the colorbar range in the plotted beam position "
            "figure. Use this option to adjust the visibility of the plotted "
            "diffraction image."
    .type = float(allow_none=True)
  midpoint {
    exclude_intensity_percent = 0.01
      .help = "Order all pixels by intensity and discard this percentage from"
              "the top (by setting them to zero)."
      .type = float(allow_none=True)
    intersection_range = (0.3, 0.9, 0.01)
      .help = "Compute midpoints in this range (start, end, step)."
      .type = floats
    convolution_width = 80
      .help = "Convolution kernel width used for smoothing (in pixels)."
      .type = int(allow_none=True)
    dead_pixel_range_x = None
      .help = "List of comma-separated pairs of numbers specifying pixel "
              "ranges in the x direction to exclude from midpoint "
              "calculation. Indexing assumes the same rules as with  the"
              "exclude_pixel_range_x."
      .type = ints
      .multiple = True
    dead_pixel_range_y = None
      .help = "List of comma-separated pairs of numbers specifying pixel "
              "ranges in the y direction to exclude from midpoint "
              "calculation. Indexing assumes the same rules as with "
              "exclude_pixel_range_y."
      .type = ints
      .multiple = True
    intersection_min_width = 10
      .help = "Do not consider midpoint intersections below this width."
      .type = int(allow_none=True)
  }
  maximum {
    bad_pixel_threshold = None
      .help = "Set all pixels above this value to zero."
      .type = int(allow_none=True)
    n_convolutions = 1
      .help = "The number of smoothing convolutions."
      .type = int(allow_none=True)
    convolution_width = 1
      .help = "Convolution kernel width used for smoothing (in pixels)."
      .type = int(allow_none=True)
    bin_width = 20
      .help = "The width of the averaging bin used to find the region  of max"
              "intensity (pixels)."
      .type = int(allow_none=True)
    bin_step = 10
      .help = "Distance in pixels between neighboring bins used to find the "
              "region of maximal intensity."
      .type = int(allow_none=True)
  }
  inversion {
    bad_pixel_threshold = None
      .help = "Set all pixels above this value to zero."
      .type = int(allow_none=True)
    guess_position = None
      .help = "Initial guess for the beam position (x, y) in pixels.  If not"
              "supplied, it will be set to the center of the image."
      .type = ints(size=2)
    inversion_window_width = 400
      .help = "Do profile inversion within this window (in pixels)."
      .type = int(allow_none=True)
    background_cutoff = None
      .help = "Set all the pixels with intensity above this value to zero."
      .type = int(allow_none=True)
    convolution_width = 1
      .help = "Convolution kernel width used for smoothing (in pixels)."
      .type = int(allow_none=True)
  }
}
output {
  experiments = optimised.expt
    .type = path
  log = "dials.search_beam_position.log"
    .type = str
  json = "beam_positions.json"
    .type = str
}

```