# dials.generate_mask

## Introduction
Mask images to remove unwanted pixels.
This program is used to generate mask to specify which pixels should be
considered “invalid” during spot finding and integration. It provides a few
options to create simple masks using the detector trusted range, or from
simple shapes or by setting different resolution ranges.
Masks can also be combined by including them as arguments.
Examples:
```
dials.generate_mask models.expt border=5

dials.generate_mask models.expt \
  untrusted.rectangle=50,100,50,100 \
  untrusted.circle=200,200,100

dials.generate_mask models.expt d_max=2.00

dials.generate_mask models.expt d_max=2.00 existing.mask

dials.generate_mask backstop.mask shadow.mask

```

## Basic parameters
```
output {
  mask = pixels.mask
  experiments = None
  log = 'dials.generate_mask.log'
}
merge_imageset_mask = False
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

```

## Full parameter definitions
```
output {
  mask = pixels.mask
    .help = "Name of output mask file."
    .type = path
  experiments = None
    .help = "Name of output experiment list file.  If this is set, a copy of "
            "the experiments, modified with the generated pixel masks,  will"
            "be saved to this location."
    .type = path
  log = 'dials.generate_mask.log'
    .help = "The log filename."
    .type = str
}
merge_imageset_mask = False
  .help = "If True, merge pixel masks defined in the imageset, such as one"
          "specified  during dials.import and one provided by the dxtbx class."
  .type = bool
border = 0
  .help = "The border around the edge of the image."
  .type = int(allow_none=True)
d_min = None
  .help = "The high resolution limit in Angstrom for a pixel to be accepted by"
          "the filtering algorithm."
  .type = float(value_min=0, allow_none=True)
d_max = None
  .help = "The low resolution limit in Angstrom for a pixel to be accepted by"
          "the filtering algorithm."
  .type = float(value_min=0, allow_none=True)
disable_parallax_correction = False
  .help = "Set to ``True`` to use a faster, but less accurate, simple px-to-mm"
          " mapping by disabling accounting for parallax correction when"
          "generating  resolution masks."
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

```