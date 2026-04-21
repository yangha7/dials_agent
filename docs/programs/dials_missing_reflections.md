# dials.missing_reflections

## Introduction
Identify connected regions of missing reflections in the asymmetric unit.
This is achieved by first generating the complete set of possible miller indices,
then performing connected components analysis on a graph of nearest neighbours in
the list of missing reflections.
Examples:
```
dials.missing_reflections integrated.expt integrated.refl

dials.missing_reflections scaled.expt scaled.refl min_component_size=10

```

## Full parameter definitions
```
min_component_size = 0
  .help = "Only show connected regions larger than or equal to this."
  .type = int(value_min=0, allow_none=True)
d_min = None
  .type = float(value_min=0, allow_none=True)
d_max = None
  .type = float(value_min=0, allow_none=True)

```