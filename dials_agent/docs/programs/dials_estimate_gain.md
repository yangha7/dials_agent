# dials.estimate_gain

## Introduction
This program can be used to estimate the gain of the detector. For pixel array
detectors the gain is usually set to 1.00. This means that the pixels behave
according to Poisson statistics. However, for older CCD detectors the gain may
have a different value. This value is important because it can affect, amongst
other things, the ability of the spot finding algorithm which can result in
noise being identified as diffraction spots.
Examples:
```
dials.estimate_gain models.expt

```

## Basic parameters
```
kernel_size = 10,10
max_images = 1
output {
  gain_map = None
}

```

## Full parameter definitions
```
kernel_size = 10,10
  .type = ints(size=2, value_min=1)
max_images = 1
  .help = "For multi-file images (NeXus for example), report a gain for each"
          "image, up to max_images, and then report an average gain"
  .type = int(allow_none=True)
output {
  gain_map = None
    .help = "Name of output gain map file"
    .type = str
}

```