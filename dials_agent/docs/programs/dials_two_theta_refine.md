# dials.two_theta_refine

## Introduction
Refine the unit cell(s) of input experiments against the input indexed
reflections using a 2θ angle target. Report the refined cell and its
estimated standard deviation.
Examples:
```
dials.two_theta_refine integrated.expt integrated.refl

dials.two_theta_refine integrated.expt integrated.refl     correlation_plot.filename=corrplot.png cif=refined_cell.cif

```

## Basic parameters
```
output {
  experiments = refined_cell.expt
  log = dials.two_theta_refine.log
  cif = None
  mmcif = None
  p4p = None
}
refinement {
  filter_integrated_centroids = True
  partiality_threshold = 0.4
  combine_crystal_models = True
  triclinic = False
}

```

## Full parameter definitions
```
output {
  experiments = refined_cell.expt
    .help = "The filename for experimental models including refined cells"
    .type = str
  log = dials.two_theta_refine.log
    .type = str
  cif = None
    .help = "Write unit cell error information to a Crystallographic"
            "Information File (CIF)"
    .type = str
  mmcif = None
    .help = "Write unit cell error information to a macromolecular"
            "Crystallographic Information File (mmCIF)"
    .type = str
  p4p = None
    .help = "Write output to SHELX / XPREP .p4p file"
    .type = str
  correlation_plot
    .expert_level = 1
  {
    filename = None
      .help = "The base filename for output of plots of parameter"
              "correlations. A file extension may be added to control the type"
              "of output file, if it is one of matplotlib's supported types. A"
              "JSON file with the same base filename will also be created,"
              "containing the correlation matrix and column labels for later"
              "inspection, replotting etc."
      .type = str
    col_select = None
      .help = "Specific columns to include in the plots of parameter"
              "correlations, either specified by parameter name or 0-based"
              "column index. Defaults to all columns. This option is useful"
              "when there is a large number of parameters"
      .type = strings
    steps = None
      .help = "Steps for which to make correlation plots. By default only the"
              "final step is plotted. Uses zero-based numbering, so the first"
              "step is numbered 0."
      .type = ints(value_min=0)
  }
}
refinement
  .help = "Parameters to configure the refinement"
{
  filter_integrated_centroids = True
    .help = "If integrated centroids are provided, filter these so that only"
            "those with both the 'integrated' and 'strong' flags are used"
    .type = bool
  partiality_threshold = 0.4
    .help = "Use only reflections with a partiality above this threshold."
    .type = float(allow_none=True)
  combine_crystal_models = True
    .help = "When multiple experiments are provided as input, combine these to"
            "fit the best single crystal model for all the data, or keep these"
            "models separate."
    .type = bool
  triclinic = False
    .help = "If true remove symmetry constraints and refine a triclinic cell"
            "by converting to P 1"
    .type = bool
}

```