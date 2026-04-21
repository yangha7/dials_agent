# dials.merge_cbf

## Introduction
This program can be used to merge a given number of consecutive cbf files into
a smaller number of images For example, running dials.merge_cbf on a experiments
with 100 images, using the default value of merge_n_images=2, will output 50
summed images, with every consecutive pair of images being summed into a single
output image. Currently only cbf format images are supported as input.
Examples:
```
dials.merge_cbf image_*.cbf

dials.merge_cbf image_*.cbf merge_n_images=10

```

## Basic parameters
```
merge_n_images = 2
output {
  image_prefix = sum_
}

```

## Full parameter definitions
```
merge_n_images = 2
  .help = "Number of input images to average into a single output image"
  .type = int(value_min=1, allow_none=True)
get_raw_data_from_imageset = True
  .help = "By default the raw data is read via the imageset. This limits use"
          "to single panel detectors where the format class does not make"
          "modifications to the array size in the file. Set this option to"
          "false in order to bypass the imageset and read the data as-is from"
          "the CBF file"
  .type = bool
  .expert_level = 2
output {
  image_prefix = sum_
    .type = path
}

```