# dials.stereographic_projection

## Introduction
Calculates a stereographic projection image for the given crystal models and
the given miller indices (either specified individually, or for all miller indices
up to a given hkl_limit). By default the projection is in the plane
perpendicular to 0,0,1 reflection for the first crystal, however the projection
can optionally be performed in the laboratory frame (frame=laboratory) in the
plane perpendicular to the beam. Setting the parameter expand_to_p1=True will
also plot all symmetry equivalents of the given miller indices, and
eliminate_sys_absent=False will eliminate systematically absent reflections
before generating the projection.
Examples:
```
dials.stereographic_projection indexed.expt hkl=1,0,0 hkl=0,1,0

dials.stereographic_projection indexed.expt hkl_limit=2

dials.stereographic_projection indexed_1.expt indexed_2.expt hkl=1,0,0 expand_to_p1=True

```

## Basic parameters
```
hkl = None
hkl_limit = None
expand_to_p1 = True
eliminate_sys_absent = False
frame = *laboratory crystal
phi_angle = 0
use_starting_angle = False
plane_normal = None
save_coordinates = True
plot {
  filename = stereographic_projection.png
  label_indices = False
  colours = None
  marker_size = 3
  font_size = 6
  colour_map = None
  gridsize = None
  labels = None
}
json {
  filename = None
}

```

## Full parameter definitions
```
hkl = None
  .type = ints(size=3)
  .multiple = True
hkl_limit = None
  .type = int(value_min=1, allow_none=True)
expand_to_p1 = True
  .help = "Expand the given miller indices to symmetry equivalent reflections"
  .type = bool
eliminate_sys_absent = False
  .help = "Eliminate systematically absent reflections"
  .type = bool
frame = *laboratory crystal
  .type = choice
phi_angle = 0
  .help = "Phi rotation angle (degrees)"
  .type = float(allow_none=True)
use_starting_angle = False
  .help = "If True, then the projection will be done for each crystal at the "
          "starting phi angle for the scan associated with the crystal."
  .type = bool
plane_normal = None
  .type = ints(size=3)
save_coordinates = True
  .type = bool
plot {
  filename = stereographic_projection.png
    .type = path
  label_indices = False
    .type = bool
  colours = None
    .type = strings
  marker_size = 3
    .type = int(value_min=1, allow_none=True)
  font_size = 6
    .type = float(value_min=0, allow_none=True)
  colour_map = None
    .type = str
  gridsize = None
    .type = int(allow_none=True)
  labels = None
    .type = strings
}
json {
  filename = None
    .type = path
}

```