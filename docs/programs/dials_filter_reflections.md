# dials.filter_reflections

## Introduction
This program takes reflection files as input and filters them based on user-
specified criteria, to write out a subset of the original file.
Filtering is first done by evaluating the optional boolean ‘flag_expression’
using reflection flag values. The operators allowed are ‘&’ for ‘and’, ‘|’ for
‘or’, and ‘~’ for ‘not’. Expressions may contain nested sub-expressions using
parentheses.
Following this, optional additional filters are applied according to values in
the reflection table, such as by resolution or user-defined masks.
If a reflection file is passed in to the program but no filtering parameters
are set, a table will be printed, giving the flag values present in the
reflection file.
Examples:
```
dials.filter_reflections refined.refl     flag_expression=used_in_refinement

dials.filter_reflections integrated.refl     flag_expression="integrated & ~reference_spot"

dials.filter_reflections integrated.refl     flag_expression="indexed & (failed_during_summation | failed_during_profile_fitting)"

dials.filter_reflections indexed.refl indexed.expt     d_max=20 d_min=2.5

```

## Basic parameters
```
output {
  reflections = 'filtered.refl'
}
flag_expression = None
id = None
panel = None
d_min = None
d_max = None
partiality {
  min = None
  max = None
}
select_good_intensities = False
dead_time {
  value = 0
  reject_fraction = 0
}
ice_rings {
  filter = False
}

```

## Full parameter definitions
```
output {
  reflections = 'filtered.refl'
    .help = "The filtered reflections output filename"
    .type = str
}
flag_expression = None
  .help = "Boolean expression to select reflections based on flag values"
  .type = str
id = None
  .help = "Select reflections by experiment IDs"
  .type = ints(value_min=0)
panel = None
  .help = "Select reflections by panels they intersect"
  .type = ints(value_min=0)
d_min = None
  .help = "The maximum resolution"
  .type = float(allow_none=True)
d_max = None
  .help = "The minimum resolution"
  .type = float(allow_none=True)
partiality {
  min = None
    .help = "The minimum reflection partiality for inclusion."
    .type = float(value_min=0, value_max=1, allow_none=True)
  max = None
    .help = "The maximum reflection partiality for inclusion."
    .type = float(value_min=0, value_max=1, allow_none=True)
}
select_good_intensities = False
  .help = "Combined filter to select only fully integrated and trustworthy"
          "intensities"
  .type = bool
dead_time {
  value = 0
    .help = "Detector dead time in ms, assumed to be at the end of the"
            "exposure time."
    .type = float(value_min=0, allow_none=True)
  reject_fraction = 0
    .help = "Reject reflections which overlap by more than the given fraction"
            "with the dead region of the image."
    .type = float(value_min=0, value_max=1, allow_none=True)
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