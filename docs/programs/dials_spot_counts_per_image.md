# dials.spot_counts_per_image

## Introduction
Reports the number of strong spots and computes an estimate of the resolution
limit for each image, given the results of dials.find_spots. Optionally
generates a plot of the per-image statistics (plot=image.png).
Examples:
```
dials.spot_counts_per_image imported.expt strong.refl

dials.spot_counts_per_image imported.expt strong.refl plot=per_image.png

```

## Basic parameters
```
resolution_analysis = True
plot = None
json = None
split_json = False
joint_json = True
id = None

```

## Full parameter definitions
```
resolution_analysis = True
  .type = bool
plot = None
  .type = path
json = None
  .type = path
split_json = False
  .type = bool
joint_json = True
  .type = bool
id = None
  .type = int(value_min=0, allow_none=True)

```