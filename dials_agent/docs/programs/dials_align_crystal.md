# dials.align_crystal

## Introduction
Calculation of possible goniometer settings for re-alignment of crystal axes.
By default the program will attempt to calculate possible goniometer settings to
align the primary crystal axes with the principle goniometer axis. Optionally
vectors to align may be specified in pairs using the vector= parameter. If
mode=main (default), then the first vector of a pair will be aligned along the
principle goniometer axis, with the second vector placed in the plane containing
the beam vector and the principle goniometer axis. This allows for rotation of
the crystal around a principle crystal axis. If mode=cusp, then the first vector
is aligned perpendicular to the beam and the principle goniometer axis, with the
second vector placed in the plane containing the first crystal vector and the
principle goniometer axis.
Examples:
```
dials.align_crystal models.expt

dials.align_crystal models.expt vector=0,0,1 vector=0,1,0

dials.align_crystal models.expt frame=direct

```

## Basic parameters
```
space_group = None
align {
  mode = *main cusp
  crystal {
    vector = None
    frame = *reciprocal direct
  }
}
output {
  json = align_crystal.json
}

```

## Full parameter definitions
```
space_group = None
  .type = space_group
align {
  mode = *main cusp
    .type = choice
  crystal {
    vector = None
      .type = str
      .multiple = True
    frame = *reciprocal direct
      .type = choice
  }
}
output {
  json = align_crystal.json
    .type = path
}

```