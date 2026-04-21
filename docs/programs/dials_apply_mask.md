# dials.apply_mask

## Introduction
This program augments a experiments JSON file with one or more masks specified by the
user.  Its only function is to input the mask file paths to the experiments JSON file,
but means that the user does not have to edit the experiments file by hand.
Crucially, the mask files must be provided in the same order as their corresponding
imagesets (sequences) appear in the experiments JSON file.
Examples:
```
dials.apply_mask models.expt input.mask=pixels.mask

dials.apply_mask models.expt input.mask=pixels1.mask input.mask=pixels2.mask

```

## Basic parameters
```
input {
  mask = None
}
output {
  experiments = masked.expt
}

```

## Full parameter definitions
```
input {
  mask = None
    .help = "The mask filenames, one mask per imageset"
    .type = str
    .multiple = True
}
output {
  experiments = masked.expt
    .help = "Name of output experiments file"
    .type = str
}

```