# dials.import

## Introduction
This program is used to import image data files into a format that can be used
within dials. The program looks at the metadata for each image along with the
filenames to determine the relationship between sets of images. Once all the
images have been analysed, a experiments object is written to file which specifies
the relationship between files. For example if two sets of images which belong
to two rotation scans have been given, two image sequences will be saved. Images to
be processed are specified as command line arguments. Sometimes, there is a
maximum number of arguments that can be given on the command line and the number
of files may exceed this. In this case image filenames can be input on stdin
as shown in the examples below. Alternatively a template can be specified using
the template= parameter where the consecutive digits representing the image
numbers in the filenames are replaced with ‘#’ characters.
The geometry can be set manually, either by using the reference_geometry=
parameter to specify an experiment list .expt file containing
the reference geometry, by using the mosflm_beam_centre= parameter to set
the Mosflm beam centre, or by specifying each variable to be overridden
using various geometry parameters.
Examples:
```
dials.import /data/directory-containing-images/

dials.import image_*.cbf

dials.import image_1_*.cbf image_2_*.cbf

dials.import directory/with/images

dials.import template=image_1_####.cbf

dials.import directory=directory/with/images

find . -name "image_*.cbf" | dials.import

dials.import << EOF
image_1.cbf
image_2.cbf
EOF

```

## Basic parameters
```
output {
  experiments = imported.expt
  log = 'dials.import.log'
  compact = False
}
identifier_type = *uuid timestamp None
input {
  ignore_unhandled = True
  template = None
  directory = None
  split = None
  reference_geometry = None
  allow_multiple_sequences = True
}
lookup {
  mask = None
  gain = None
  pedestal = None
  dx = None
  dy = None
}

```

## Full parameter definitions
```
output {
  experiments = imported.expt
    .help = "The output experiment file"
    .type = str
  log = 'dials.import.log'
    .help = "The log filename"
    .type = str
  compact = False
    .help = "For experiment output use compact JSON representation"
    .type = bool
}
identifier_type = *uuid timestamp None
  .help = "Type of unique identifier to generate."
  .type = choice
input {
  ignore_unhandled = True
    .help = "Ignore unhandled input (e.g. log files)"
    .type = bool
  template = None
    .help = "The image sequence template"
    .type = str
    .multiple = True
  directory = None
    .help = "A directory with images"
    .type = str
    .multiple = True
  split = None
    .help = "Scan split: either frames_per_block or 1-indexed"
            "start,end,frames_per_block"
    .type = ints
  reference_geometry = None
    .help = "Experimental geometry from this models.expt  will override the"
            "geometry from the  image headers."
    .type = path
  check_reference_geometry = True
    .help = "If True, assert the reference geometry is similar to the image"
            "geometry"
    .type = bool
    .expert_level = 2
  use_beam_reference = True
    .help = "If True, the beam from reference_geometry will override  the beam"
            "from the image headers."
    .type = bool
    .expert_level = 2
  use_gonio_reference = True
    .help = "If True, the goniometer from reference_geometry will override "
            "the goniometer from the image headers."
    .type = bool
    .expert_level = 2
  use_detector_reference = True
    .help = "If True, the detector from reference_geometry will override  the"
            "detector from the image headers."
    .type = bool
    .expert_level = 2
  allow_multiple_sequences = True
    .help = "If False, raise an error if multiple sequences are found"
    .type = bool
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
geometry
  .help = "Allow overrides of experimental geometry"
  .expert_level = 2
{
  beam
    .short_caption = "Beam overrides"
    .expert_level = 1
  {
    type = *monochromatic polychromatic
      .help = "Override the beam type"
      .short_caption = beam_type
      .type = choice
    probe = *x-ray electron neutron
      .help = "Override the beam probe"
      .short_caption = beam_probe
      .type = choice
    wavelength = None
      .help = "Override the beam wavelength"
      .type = float(allow_none=True)
    direction = None
      .help = "Override the sample to source direction"
      .short_caption = "Sample to source direction"
      .type = floats(size=3)
    divergence = None
      .help = "Override the beam divergence"
      .type = float(allow_none=True)
    sigma_divergence = None
      .help = "Override the beam sigma divergence"
      .type = float(allow_none=True)
    polarization_normal = None
      .help = "Override the polarization normal"
      .short_caption = "Polarization normal"
      .type = floats(size=3)
    polarization_fraction = None
      .help = "Override the polarization fraction"
      .short_caption = "Polarization fraction"
      .type = float(value_min=0, value_max=1, allow_none=True)
    transmission = None
      .help = "Override the transmission"
      .short_caption = transmission
      .type = float(allow_none=True)
    flux = None
      .help = "Override the flux"
      .short_caption = flux
      .type = float(allow_none=True)
    sample_to_source_distance = None
      .help = "Override the distance between sample and source (mm)"
      .type = float(allow_none=True)
    wavelength_range = None
      .help = "Override the wavelength range for polychromatic beams (A)"
      .type = floats(size=2)
  }
  detector
    .short_caption = "Detector overrides"
    .expert_level = 1
  {
    panel
      .multiple = True
    {
      id = 0
        .help = "The panel number"
        .short_caption = "Panel ID"
        .type = int(allow_none=True)
      name = None
        .help = "Override the panel name"
        .short_caption = "Panel name"
        .type = str
      type = None
        .help = "Override the panel type"
        .short_caption = "Panel type"
        .type = str
      gain = None
        .help = "The gain of the detector panel"
        .short_caption = "Gain value"
        .type = float(value_min=0, allow_none=True)
      pedestal = None
        .help = "The pedestal of the detector panel"
        .short_caption = "Pedestal value"
        .type = float(allow_none=True)
      pixel_size = None
        .help = "Override the panel pixel size"
        .short_caption = "Panel pixel size"
        .type = floats(size=2)
      image_size = None
        .help = "Override the panel image size"
        .short_caption = "Panel image size"
        .type = ints(size=2)
      trusted_range = None
        .help = "Override the panel trusted range: [min-trusted-value,"
                "max-trusted-value]"
        .short_caption = "Panel trusted range"
        .type = floats(size=2)
      thickness = None
        .help = "Override the panel thickness"
        .short_caption = "Panel thickness"
        .type = float(allow_none=True)
      material = None
        .help = "Override the panel material"
        .short_caption = "Panel material"
        .type = str
      fast_axis = None
        .help = "Override the panel fast axis. Requires slow_axis and origin."
        .short_caption = "Panel fast axis direction"
        .type = floats(size=3)
      slow_axis = None
        .help = "Override the panel slow axis. Requires fast_axis and origin."
        .short_caption = "Panel slow axis direction"
        .type = floats(size=3)
      origin = None
        .help = "Override the panel origin. Requires fast_axis and slow_axis."
        .short_caption = "Panel origin vector"
        .type = floats(size=3)
      parallax_correction = None
        .help = "Enable parallax correction. By default in overwrite mode, the"
                "value of None does nothing."
        .short_caption = "Enable parallax correction"
        .type = bool
    }
    hierarchy
      .expert_level = 2
    {
      name = None
        .help = "Override the group name"
        .short_caption = "group name"
        .type = str
      fast_axis = None
        .help = "Override the panel fast axis. Requires slow_axis and origin."
        .short_caption = "Panel fast axis direction"
        .type = floats(size=3)
      slow_axis = None
        .help = "Override the panel slow axis. Requires fast_axis and origin."
        .short_caption = "Panel slow axis direction"
        .type = floats(size=3)
      origin = None
        .help = "Override the panel origin. Requires fast_axis and slow_axis."
        .short_caption = "Panel origin vector"
        .type = floats(size=3)
      group
        .multiple = True
      {
        id = None
          .help = "The group identifier specifying the place in the hierarchy"
          .short_caption = "Group ID"
          .type = ints
        name = None
          .help = "Override the group name"
          .short_caption = "Group name"
          .type = str
        fast_axis = None
          .help = "Override the group fast axis. Requires slow_axis and"
                  "origin."
          .short_caption = "Group fast axis direction"
          .type = floats(size=3)
        slow_axis = None
          .help = "Override the group slow axis. Requires fast_axis and"
                  "origin."
          .short_caption = "Group slow axis direction"
          .type = floats(size=3)
        origin = None
          .help = "Override the group origin. Requires fast_axis and"
                  "slow_axis."
          .short_caption = "Group origin vector"
          .type = floats(size=3)
        panel = None
          .help = "The panel id"
          .short_caption = "Panel ID"
          .type = int(allow_none=True)
          .multiple = True
      }
    }
    mosflm_beam_centre = None
      .help = "Override the beam centre from the image headers, following  the"
              "mosflm convention."
      .short_caption = "Beam centre coordinates (mm, mm) using the Mosflm"
                       "convention"
      .type = floats(size=2)
    distance = None
      .help = "The detector distance (used when mosflm_beam_centre is set)"
      .short_caption = "Detector distance"
      .type = float(allow_none=True)
    fast_slow_beam_centre = None
      .help = "Override the beam centre from the image headers. The first two"
              "values are the fast and slow pixel coordinate. If the third is"
              "supplied it specifies a panel number."
      .short_caption = "Beam centre coordinates (px fast, px slow, [panel id])"
      .type = floats(size_min=2, size_max=3)
    slow_fast_beam_centre = None
      .help = "Alternative to fast_slow_beam_centre in which the coordinates"
              "are given in order (px slow, px fast, [panel id]). If"
              "fast_slow_beam_centre is set it will take priority over any"
              "values set here."
      .short_caption = "Beam centre coordinates (px slow, px fast, [panel id])"
      .type = ints(size_min=2, size_max=3)
  }
  goniometer
    .short_caption = "Goniometer overrides"
    .expert_level = 1
  {
    axis = None
      .help = "Override the axis for a single axis goniometer. Equivalent to"
              "providing a single 3D vector to 'axes'."
      .short_caption = "Goniometer axis"
      .type = floats(size=3)
    axes = None
      .help = "Override the goniometer axes. Axes must be provided in the"
              "order crystal-to-goniometer, i.e. for a Kappa goniometer"
              "phi,kappa,omega"
      .short_caption = "Goniometer axes"
      .type = floats
    angles = None
      .help = "Override the goniometer angles. Axes must be provided in the"
              "order crystal-to-goniometer, i.e. for a Kappa goniometer"
              "phi,kappa,omega"
      .short_caption = "Goniometer angles"
      .type = floats
    names = None
      .help = "The multi axis goniometer axis names"
      .short_caption = "The axis names"
      .type = str
    scan_axis = None
      .help = "The scan axis"
      .short_caption = "The scan axis"
      .type = int(allow_none=True)
    fixed_rotation = None
      .help = "Override the fixed rotation matrix"
      .short_caption = "Fixed rotation matrix"
      .type = floats(size=9)
    setting_rotation = None
      .help = "Override the setting rotation matrix"
      .short_caption = "Setting rotation matrix"
      .type = floats(size=9)
    invert_rotation_axis = False
      .help = "Invert the rotation axis"
      .short_caption = "Invert rotation axis"
      .type = bool
  }
  scan
    .short_caption = "Scan overrides"
    .expert_level = 1
  {
    image_range = None
      .help = "Override the image range"
      .short_caption = "Image range"
      .type = ints(size=2)
    extrapolate_scan = False
      .help = "When overriding the image range, extrapolate exposure and epoch"
              "information from existing images"
      .short_caption = "Extrapolate scan"
      .type = bool
    oscillation = None
      .help = "Override the image oscillation"
      .short_caption = Oscillation
      .type = floats(size=2)
    batch_offset = None
      .help = "Override the batch offset"
      .short_caption = "Batch offset"
      .type = int(value_min=0, allow_none=True)
  }
  convert_stills_to_sequences = False
    .help = "When overriding the scan, convert stills into sequences"
    .short_caption = "Convert stills into sequences"
    .type = bool
  convert_sequences_to_stills = False
    .help = "When overriding the scan, convert sequences into stills"
    .short_caption = "Convert sequences into stills"
    .type = bool
}
lookup {
  mask = None
    .help = "Apply a mask to the imported data"
    .type = str
  gain = None
    .help = "Apply a gain to the imported data"
    .type = str
  pedestal = None
    .help = "Apply a pedestal to the imported data"
    .type = str
  dx = None
    .help = "Apply an x geometry offset If both dx and dy are set then"
            "OffsetParallaxCorrectedPxMmStrategy will be used"
    .type = str
  dy = None
    .help = "Apply an y geometry offset If both dx and dy are set then"
            "OffsetParallaxCorrectedPxMmStrategy will be used"
    .type = str
}

```