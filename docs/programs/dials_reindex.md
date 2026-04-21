# dials.reindex

## Introduction
This program can be used to re-index an indexed.expt and/or indexed.refl
file from one setting to another. The change of basis operator can be
provided in h,k,l, or a,b,c or x,y,z conventions. By default the change of
basis operator will also be applied to the space group in the indexed.expt
file, however, optionally, a space group (including setting) to be applied
AFTER applying the change of basis operator can be provided.
Alternatively, to reindex an integrated dataset in the case of indexing ambiguity,
a reference dataset (models.expt and reflection.refl) in the same space
group can be specified. In this case, any potential twin operators are tested,
and the dataset is reindexed to the setting that gives the highest correlation
with the reference dataset.
Examples:
```
dials.reindex indexed.expt change_of_basis_op=b+c,a+c,a+b

dials.reindex indexed.refl change_of_basis_op=-b,a+b+2*c,-a

dials.reindex indexed.expt indexed.refl change_of_basis_op=l,h,k

dials.reindex indexed.expt indexed.refl reference.experiments=reference.expt
  reference.reflections=reference.refl

```

## Basic parameters
```
change_of_basis_op = a,b,c
hkl_offset = None
space_group = None
reference {
  experiments = None
  reflections = None
  reference_model {
  }
}
output {
  experiments = reindexed.expt
  reflections = reindexed.refl
  log = dials.reindex.log
}

```

## Full parameter definitions
```
change_of_basis_op = a,b,c
  .type = str
hkl_offset = None
  .type = ints(size=3)
space_group = None
  .help = "The space group to be applied AFTER applying the change of basis "
          "operator."
  .type = space_group
reference {
  experiments = None
    .help = "Reference experiment for determination of change of basis"
            "operator."
    .type = path
  reflections = None
    .help = "Reference reflections to allow reindexing to consistent index"
            "between datasets."
    .type = path
  file = None
    .help = "A file containing a reference set of intensities e.g. MTZ/cif, or"
            "a file from which a reference set of intensities can be"
            "calculated e.g. .pdb or .cif . The space group of the reference"
            "file will be used and if an indexing ambiguity is present, the"
            "input data will be reindexed to be consistent with the indexing"
            "mode of this reference file."
    .type = path
    .expert_level = 2
  reference_model {
  }
}
output {
  experiments = reindexed.expt
    .help = "The filename for reindexed experimental models"
    .type = str
  reflections = reindexed.refl
    .help = "The filename for reindexed reflections"
    .type = str
  log = dials.reindex.log
    .type = path
}

```