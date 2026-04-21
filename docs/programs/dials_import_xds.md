# dials.import_xds

## Introduction
This program imports xds processed data for use in dials.
The files created are the closest mapping from XDS data to DIALS models, however
this is not always exact so care should be taken when interpreting results.
For XDS-integrated data, the main intention for this tool is to enable the use of
DIALS data reduction tools. This tool is likely to be unsuitable for informing
direct comparisons between XDS and DIALS.

It requires up to three things to create an experiment list and reflection table.
an XDS.INP, to specify the geometry,
one of “INTEGRATE.HKL” or “XPARM.XDS”, which is needed to create the experiment (
alternatively “XDS_ASCII.HKL” or “GXPARM.XDS” can be specified with xds_file=)
INTEGRATE.HKL or SPOT.XDS file to create a reflection table.

To run the program, the easiest thing to do is provide a directory containing these files
Example use cases:
```
dials.import_xds /path/to/folder/containing/xds/inp/                          # Extract all the relevant files from this directory (defaults to importing INTEGRATE.HKL if it exists)

dials.import_xds /path/to/folder/containing/xds/inp/INTEGRATE.HKL             # Specify a path to an INTEGRATE.HKL - the XDS.INP must be in the same directory.

dials.import_xds /path/to/folder/containing/xds/inp/ SPOT.XDS                 # Be explicit about which file to use to create reflections (default is to use INTEGRATE.HKL)

dials.import_xds /path/to/folder/containing/xds/inp/ xds_file=XPARM.XDS       # Specify which extra file should be used to create experiment metadata

dials.import_xds /path/to/folder/containing/xds/inp/ /path/to/INTEGRATE.HKL   # Will take XDS.INP from the directory, and everything else needed from the specified INTEGRATE.HKL file

```

## Basic parameters
```
input {
  xds_file = None
}
output {
  reflections = None
  xds_experiments = "xds_models.expt"
  log = dials.import_xds.log
}
remove_invalid = False
add_standard_columns = False
read_varying_crystal = False

```

## Full parameter definitions
```
input {
  xds_file = None
    .help = "Explicitly specify the file to use "
    .type = path
}
output {
  reflections = None
    .help = "The output filname of the reflections file (defaults to either"
            "integrate_hkl.refl or spot_xds.refl)"
    .type = str
  xds_experiments = "xds_models.expt"
    .help = "The output filename of the experiment list created from xds"
    .type = str
  log = dials.import_xds.log
    .type = path
}
remove_invalid = False
  .help = "Remove non-index reflections (if miller indices are present)"
  .type = bool
add_standard_columns = False
  .help = "Add empty standard columns to the reflections. Note columns for"
          "centroid variances are set to contain 1s, not 0s"
  .type = bool
read_varying_crystal = False
  .help = "Attempt to create a scan-varying crystal model from INTEGRATE.LP,"
          "if present"
  .type = bool

```