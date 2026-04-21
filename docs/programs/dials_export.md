# dials.export

## Introduction
This program is used to export the results of dials processing in various
formats.
The output formats currently supported are:
MTZ format exports the files as an unmerged mtz file, ready for input to
downstream programs such as Pointless and Aimless. For exporting integrated,
but unscaled data, the required input is an integrated.expt file and an
integrated.refl file. For exporting scaled data, the required input is a
scaled.expt file and a scaled.refl file, in which case the intensity=scale
flag will be set implicitly.
NXS format exports the files as an NXmx file. The required input is an
integrated.expt file and an integrated.refl file.
MMCIF format exports the files as an mmcif file. The required input is an
integrated.expt file and an integrated.refl file.
XDS_ASCII format exports intensity data and the experiment metadata in the
same format as used by the output of XDS in the CORRECT step - output can
be scaled with XSCALE.
SADABS format exports intensity data (and geometry by direction cosines)
as an ersatz-SADABS format reverse engineered from the file format used by
EvalCCD for input to SADABS.
MOSFLM format exports the files as an index.mat mosflm-format matrix file and a
mosflm.in file containing basic instructions for input to mosflm. The required
input is an models.expt file.
XDS format exports experiment files as XDS.INP and XPARM.XDS files. If a
reflection file is given it will be exported as a SPOT.XDS file.
SHELX format exports intensity data in HKLF 4 format for use in the SHELX suite
of programs. As this file format does not contain unit cell parameters or
symmetry information a minimal instruction file is also written. Optionally the
expected contents of the asymmetric unit can be added to this instruciton file.
PETS format exports intensity data and diffraction data in the CIF format
used by PETS. This is primarily intended to produce files suitable for
dynamic diffraction refinement using Jana2020, which requires this format.
Examples:
```
# Export to mtz
dials.export integrated.expt integrated.refl
dials.export integrated.expt integrated.refl mtz.hklout=integrated.mtz
dials.export scaled.expt scaled.refl
dials.export scaled.expt scaled.refl intensity=scale mtz.hklout=scaled.mtz

# Export to nexus
dials.export integrated.expt integrated.refl format=nxs
dials.export integrated.expt integrated.refl format=nxs nxs.hklout=integrated.nxs

# Export to mmcif
dials.export integrated.expt integrated.refl format=mmcif
dials.export integrated.expt integrated.refl format=mmcif mmcif.hklout=integrated.mmcif

# Export to xds
dials.export strong.refl format=xds
dials.export indexed.refl format=xds
dials.export indexed.expt indexed.refl format=xds

# Export to shelx
dials.export scaled.expt scaled.refl format=shelx
dials.export scaled.expt scaled.refl format=shelx shelx.hklout=dials.hkl
dials.export scaled.expt scaled.refl format=shelx composition=C3H7NO2S

```

## Basic parameters
```
format = *mtz sadabs nxs mmcif mosflm xds xds_ascii json shelx pets
intensity = *auto profile sum scale
debug = False
mtz {
  combine_partials = True
  partiality_threshold = 0.4
  min_isigi = -5
  force_static_model = False
  filter_ice_rings = False
  d_min = None
  hklout = auto
  crystal_name = XTAL
  project_name = DIALS
  best_unit_cell = None
  wavelength_tolerance = 1e-4
}
sadabs {
  hklout = integrated.sad
  run = 1
  predict = False
}
xds_ascii {
  hklout = DIALS.HKL
}
nxs {
  hklout = integrated.nxs
  instrument_name = Unknown
  instrument_short_name = Unknown
  source_name = Unknown
  source_short_name = Unknown
}
mmcif {
  hklout = auto
  compress = gz bz2 xz
  pdb_version = *v5 v5_next
  scale = True
  min_scale = -999999.0
}
mosflm {
  directory = mosflm
}
xds {
  directory = xds
}
json {
  filename = rlp.json
  compact = True
  n_digits = 6
}
shelx {
  hklout = dials.hkl
  ins = dials.ins
  composition = CH
  scale = True
  scale_range = -9999.0, 9999.0
}
pets {
  filename_prefix = dials_dyn
  id = None
  partiality_cutoff = 0.99
  flag_filtering = False
  virtual_frame {
    excitation_error_cutoff = 0.04
    n_merged = 1
    step = 1
  }
}
output {
  log = dials.export.log
}

```

## Full parameter definitions
```
format = *mtz sadabs nxs mmcif mosflm xds xds_ascii json shelx pets
  .help = "The output file format"
  .type = choice
intensity = *auto profile sum scale
  .help = "Choice of which intensities to export. Allowed combinations:
      "
          "     scale, profile, sum, profile+sum, sum+profile+scale. Auto"
          "will
            default to scale or profile+sum depending on if"
          "the data are scaled."
  .type = choice(multi=True)
debug = False
  .help = "Output additional debugging information"
  .type = bool
mtz {
  combine_partials = True
    .help = "Combine partials that have the same partial id into one
       "
            "reflection, with an updated partiality given by the sum of the
  "
            "     individual partialities."
    .type = bool
  partiality_threshold = 0.4
    .help = "All reflections with partiality values above the partiality
     "
            "  threshold will be retained. This is done after any combination"
            "of
        partials if applicable."
    .type = float(allow_none=True)
  min_isigi = -5
    .help = "Exclude reflections with unfeasible values of I/Sig(I)"
    .type = float(allow_none=True)
  force_static_model = False
    .help = "Force program to use static model even if scan varying is present"
    .type = bool
  filter_ice_rings = False
    .help = "Filter reflections at ice ring resolutions"
    .type = bool
  d_min = None
    .help = "Filter out reflections with d-spacing below d_min"
    .type = float(allow_none=True)
  hklout = auto
    .help = "The output MTZ filename, defaults to integrated.mtz or"
            "scaled_unmerged.mtz depending on if the input data are scaled."
    .type = path
  crystal_name = XTAL
    .help = "The name of the crystal, for the mtz file metadata"
    .type = str
  project_name = DIALS
    .help = "The project name for the mtz file metadata"
    .type = str
  best_unit_cell = None
    .help = "Best unit cell value, to use when performing resolution cutting,"
            "and as the overall unit cell in the exported mtz. If None, the"
            "median cell will be used."
    .type = unit_cell
  wavelength_tolerance = 1e-4
    .help = "An absolute tolerance on the wavelength (in A)"
    .type = float(allow_none=True)
}
sadabs {
  hklout = integrated.sad
    .help = "The output raw sadabs file"
    .type = path
  run = 1
    .help = "Batch number / run number for output file"
    .type = int(allow_none=True)
  predict = False
    .help = "Compute centroids with static model, not observations"
    .type = bool
}
xds_ascii {
  hklout = DIALS.HKL
    .help = "The output raw hkl file"
    .type = path
}
nxs {
  hklout = integrated.nxs
    .help = "The output Nexus file"
    .type = path
  instrument_name = Unknown
    .help = "Name of the instrument/beamline"
    .type = str
  instrument_short_name = Unknown
    .help = "Short name for instrument/beamline, perhaps the acronym"
    .type = str
  source_name = Unknown
    .help = "Name of the source/facility"
    .type = str
  source_short_name = Unknown
    .help = "Short name for source, perhaps the acronym"
    .type = str
}
mmcif {
  hklout = auto
    .help = "The output CIF file, defaults to integrated.cif or"
            "scaled_unmerged.cif
        depending on if the data are scaled."
    .type = path
  compress = gz bz2 xz
    .help = "Choose compression format (also appended to the file name)"
    .type = choice
  pdb_version = *v5 v5_next
    .help = "This controls which pdb mmcif dictionary version the output mmcif"
            "file should comply with. v5_next adds support for recording"
            "unmerged data as well as additional scan metadata and statistics,"
            "however writing can be slow for large datasets."
    .type = choice
  scale = True
    .help = "If True, apply a scale such that the minimum intensity is greater"
            "than (less negative than) the mmcif.min_scale value below."
    .type = bool
  min_scale = -999999.0
    .help = "If mmcif.scale is True, scale all negative intensities such that"
            "they are less negative than this value."
    .type = float(allow_none=True)
}
mosflm {
  directory = mosflm
    .help = "The output directory for mosflm output"
    .type = path
}
xds {
  directory = xds
    .help = "The output directory for xds output"
    .type = path
}
json {
  filename = rlp.json
    .type = path
  compact = True
    .type = bool
  n_digits = 6
    .help = "Number of decimal places to be used for representing the"
            "reciprocal lattice points."
    .type = int(value_min=1, allow_none=True)
}
shelx {
  hklout = dials.hkl
    .help = "The output hkl file"
    .type = path
  ins = dials.ins
    .help = "The output ins file"
    .type = path
  composition = CH
    .help = "The chemical composition of the asymmetric unit"
    .type = str
  scale = True
    .help = "Scale reflections to maximise output precision in SHELX 8.2f"
            "format"
    .type = bool
  scale_range = -9999.0, 9999.0
    .help = "minimum or maximum intensity value after scaling."
    .type = floats(size=2, value_min=-999999, value_max=9999999)
}
pets {
  filename_prefix = dials_dyn
    .help = "The prefix for output files, where the default will produce"
            "dials_dyn.cif_pets"
    .type = str
  id = None
    .help = "The experiment ID to export from a multi-experiment list"
    .type = int(allow_none=True)
  partiality_cutoff = 0.99
    .help = "Cutoff for determining which reflections are deemed to be fully"
            "recorded"
    .type = float(allow_none=True)
  flag_filtering = False
    .help = "If true, keep only the reflections where the relevant"
            "`integrated` flag is set (either `integrated_sum` or"
            "`integrated_prf`). This seems to be quite restrictive compared to"
            "PETS, so is not set by default."
    .type = bool
  virtual_frame {
    excitation_error_cutoff = 0.04
      .help = "Excitation error cutoff determining which reflections are"
              "included in virtual frames"
      .type = float(allow_none=True)
    n_merged = 1
      .help = "Number of frames to merge in a virtual frame"
      .type = int(allow_none=True)
    step = 1
      .help = "Step between frames"
      .type = int(allow_none=True)
  }
}
output {
  log = dials.export.log
    .help = "The log filename"
    .type = path
}

```