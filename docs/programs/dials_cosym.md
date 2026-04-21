# dials.cosym

## Introduction
This program implements the methods of Gildea, R. J. & Winter, G. (2018).
Acta Cryst. D74, 405-410 for
determination of Patterson group symmetry from sparse multi-crystal data sets in
the presence of an indexing ambiguity.
The program takes as input a set of integrated experiments and reflections,
either in one file per experiment, or with all experiments combined in a single
models.expt and observations.refl file. It will perform analysis of the
symmetry elements present in the datasets and, if necessary, reindex experiments
and reflections as necessary to ensure that all output experiments and
reflections are indexed consistently.
Examples:
```
dials.cosym models.expt observations.refl

dials.cosym models.expt observations.refl space_group=I23

dials.cosym models.expt observations.refl space_group=I23 lattice_group=I23

```

## Basic parameters
```
partiality_threshold = 0.4
unit_cell_clustering {
  threshold = 5000
  log = False
}
reference_model {
}
min_reflections = 10
seed = 230
normalisation = kernel quasi *ml_iso ml_aniso
d_min = Auto
min_i_mean_over_sigma_mean = 4
min_cc_half = 0.6
dimensions = Auto
use_curvatures = True
weights = *count standard_error
cc_weights = None sigma
min_pairs = 3
minimization {
  engine = *scitbx scipy
  max_iterations = 100
  max_calls = None
}
nproc = Auto
lattice_group = None
space_group = None
lattice_symmetry_max_delta = 5.0
best_monoclinic_beta = True
relative_length_tolerance = 0.05
absolute_angle_tolerance = 2
exclude_inconsistent_unit_cells = True
output {
  suffix = "_reindexed"
  log = dials.cosym.log
  experiments = "symmetrized.expt"
  reflections = "symmetrized.refl"
  excluded = False
  excluded_prefix = "excluded"
  json = dials.cosym.json
  html = dials.cosym.html
}

```

## Example
Run `dials.cosym`, providing the integrated experiment (`.expt`) and reflection (`.refl`)
files as input:
```
dials.cosym experiments_0.expt experiments_1.expt experiments_2.expt experiments_3.expt reflections_0.refl reflections_1.refl reflections_2.refl reflections_3.refl

```

The first step is to analyse the metric symmetry of the input unit cells, and perform
hierarchical unit cell clustering to identify any outlier datasets that aren’t consistent
with the rest of the datasets. The largest common cluster is carried forward in the
analysis. You can modify the threshold that is used for determining outliers by setting
the `unit_cell_clustering.threshold` parameter.
```
Using Andrews-Bernstein distance from Andrews & Bernstein J Appl Cryst 47:346 (2014)
Distances have been calculated
0 singletons:

Point group    a           b           c          alpha        beta         gamma

1 cluster

Cluster_id       N_xtals  Med_a         Med_b         Med_c         Med_alpha    Med_beta     Med_gamma   Delta(deg)
4 in P 4 2 2.
cluster_1        4        68.36 (0.01 ) 68.36 (0.01 ) 103.95(0.02 ) 90.00 (0.00) 90.00 (0.00) 90.00 (0.00)
     P 4/m m m (No. 123)  68.36         68.36         103.95        90.00        90.00        90.00         0.0
Standard deviations are in brackets.
Each cluster:
        Input lattice count, with integration Bravais setting space group.
        Cluster median with Niggli cell parameters (std dev in brackets).
        Highest possible metric symmetry and unit cell using LePage (J Appl Cryst 1982, 15:255) method, maximum delta 3deg.

```

In this case, the unit cell analysis found 1 cluster of 4 datasets in \(P\,4\,2\,2\).
As a result, all datasets will be carried forward for symmetry analysis.
Each dataset is then normalised using maximum likelihood isotropic Wilson scaling,
reporting an estimated Wilson \(B\) value and scale factor for each dataset:
```
Normalising intensities for dataset 1

ML estimate of overall B value:
   13.52 A**2
ML estimate of  -log of scale factor:
  -3.04

--------------------------------------------------------------------------------

Normalising intensities for dataset 2

ML estimate of overall B value:
   11.06 A**2
ML estimate of  -log of scale factor:
  -3.50

--------------------------------------------------------------------------------

Normalising intensities for dataset 3

ML estimate of overall B value:
   11.38 A**2
ML estimate of  -log of scale factor:
  -2.96

--------------------------------------------------------------------------------

Normalising intensities for dataset 4

ML estimate of overall B value:
   12.14 A**2
ML estimate of  -log of scale factor:
  -2.67

```

A high resolution cutoff is then determined by analysis of CC½ and <I>/<σ(I)> as a
function of resolution:
```
Estimation of resolution for Laue group analysis

Removing 3 Wilson outliers with E^2 >= 16.0
Resolution estimate from <I>/<σ(I)> > 4.0 : 2.16
Resolution estimate from CC½ > 0.60: 1.80
High resolution limit set to: 1.80
Selecting 148799 reflections with d > 1.80

```

Next, the program performs automatic determination of the number of dimensions for
analysis. This calculates the functional of equation 2 of
Gildea, R. J. & Winter, G. (2018) for each dimension from 2 up to the number of
symmetry operations in the lattice group. The analysis needs to use sufficient
dimensions to be able to separate any indexing ambiguities that may be present, but
using too many dimensions reduces the sensitivity of the procedure. In this case, it is
determined that 8 dimensions will be used for the analysis:
```
Automatic determination of number of dimensions for analysis
Testing dimension: 1/8
Testing dimension: 2/8
Testing dimension: 3/8
Testing dimension: 4/8
Testing dimension: 5/8
Testing dimension: 6/8
Testing dimension: 7/8
Testing dimension: 8/8
+--------------+--------------+
|   Dimensions |   Functional |
|--------------+--------------|
|            1 |    0.0787666 |
|            2 |    0.0582901 |
|            3 |    0.037648  |
|            4 |    0.0337238 |
|            5 |    0.0290806 |
|            6 |    0.0243959 |
|            7 |    0.0208905 |
|            8 |    0.0174515 |
+--------------+--------------+
Best number of dimensions: 3

```

Once the analysis has been performed in the appropriate number of dimensions, the
results are analysed to score all possible symmetry elements, using algorithms similar
to those of POINTLESS, using the fact that the angles between vectors represent
genuine systematic differences between datasets, as made clear by equation 5 of
Diederichs, K. (2017).
```
Scoring individual symmetry elements
+--------------+--------+------+-----+-----------------+
|   likelihood |   Z-CC |   CC |     | Operator        |
|--------------+--------+------+-----+-----------------|
|        0.944 |   9.86 | 0.99 | *** | 4 |(0, 0, 1)    |
|        0.944 |   9.86 | 0.99 | *** | 4^-1 |(0, 0, 1) |
|        0.941 |   9.82 | 0.98 | *** | 2 |(1, 0, 0)    |
|        0.946 |   9.91 | 0.99 | *** | 2 |(0, 1, 0)    |
|        0.936 |   9.73 | 0.97 | *** | 2 |(0, 0, 1)    |
|        0.94  |   9.79 | 0.98 | *** | 2 |(1, 1, 0)    |
|        0.947 |   9.94 | 0.99 | *** | 2 |(-1, 1, 0)   |
+--------------+--------+------+-----+-----------------+

```

Scores for the possible Laue groups are obtained by analysing the scores for the
symmetry elements that are present or absent from each group, and the groups are ranked
by their likelihood.
```
Scoring all possible sub-groups
+-------------------+-----+--------------+----------+--------+--------+---------+--------------------+
| Patterson group   |     |   Likelihood |   NetZcc |   Zcc+ |   Zcc- |   delta | Reindex operator   |
|-------------------+-----+--------------+----------+--------+--------+---------+--------------------|
| P 4/m m m         | *** |            1 |     9.85 |   9.85 |   0    |       0 | -a,-b,c            |
| P 4/m             |     |            0 |    -0.05 |   9.82 |   9.86 |       0 | -a,-b,c            |
| P m m m           |     |            0 |    -0.04 |   9.82 |   9.86 |       0 | -a,-b,c            |
| C m m m           |     |            0 |    -0.04 |   9.82 |   9.86 |       0 | a+b,-a+b,c         |
| C 1 2/m 1         |     |            0 |     0.11 |   9.94 |   9.83 |       0 | a+b,-a+b,c         |
| P 1 2/m 1         |     |            0 |     0.07 |   9.91 |   9.83 |       0 | -a,-b,c            |
| P 1 2/m 1         |     |            0 |    -0.03 |   9.82 |   9.85 |       0 | -b,-a,-c           |
| C 1 2/m 1         |     |            0 |    -0.06 |   9.79 |   9.85 |       0 | a-b,a+b,c          |
| P 1 2/m 1         |     |            0 |    -0.14 |   9.73 |   9.86 |       0 | -a,-c,-b           |
| P -1              |     |            0 |    -9.85 |   0    |   9.85 |       0 | -a,-b,c            |
+-------------------+-----+--------------+----------+--------+--------+---------+--------------------+
Best solution: P 4/m m m
Unit cell: 68.360, 68.360, 103.953, 90.000, 90.000, 90.000
Reindex operator: -a,-b,c
Laue group probability: 1.000
Laue group confidence: 1.000

```

The program then concludes by reporting any reindexing operations that are necessary to
ensure consistent indexing between datasets. In this case, no indexing ambiguity is
present, so the reindexing operator is simply the identity operator for all datasets.
```
Reindexing operators:
x,y,z: [0, 1, 2, 3]

```

The correctly reindexed experiments and reflections are then saved to file, along with
a HTML report:
```
Writing html report to: dials.cosym.html
Writing json to: dials.cosym.json
Saving reindexed experiments to symmetrized.expt
Saving reindexed reflections to symmetrized.refl

```

The full log file can be viewed here:

Show/Hide Log
```
DIALS 3.dev.1428-gd99e5841f-release
The following parameters have been modified:

input {
  experiments = experiments_0.expt
  experiments = experiments_1.expt
  experiments = experiments_2.expt
  experiments = experiments_3.expt
  reflections = reflections_0.refl
  reflections = reflections_1.refl
  reflections = reflections_2.refl
  reflections = reflections_3.refl
}

Using Andrews-Bernstein distance from Andrews & Bernstein J Appl Cryst 47:346 (2014)
Distances have been calculated
0 singletons:

Point group    a           b           c          alpha        beta         gamma

1 cluster

Cluster_id       N_xtals  Med_a         Med_b         Med_c         Med_alpha    Med_beta     Med_gamma   Delta(deg)
4 in P 4 2 2.
cluster_1        4        68.36 (0.01 ) 68.36 (0.01 ) 103.95(0.02 ) 90.00 (0.00) 90.00 (0.00) 90.00 (0.00)
     P 4/m m m (No. 123)  68.36         68.36         103.95        90.00        90.00        90.00         0.0
Standard deviations are in brackets.
Each cluster:
        Input lattice count, with integration Bravais setting space group.
        Cluster median with Niggli cell parameters (std dev in brackets).
        Highest possible metric symmetry and unit cell using LePage (J Appl Cryst 1982, 15:255) method, maximum delta 3deg.
Mapping all input cells to a common minimum cell
Filtering reflections for dataset 0
Read 76079 predicted reflections
Selected 54367 reflections integrated by profile and summation methods
Combined 1127 partial reflections with other partial reflections
Removed 20 reflections below partiality threshold
Removed 0 intensity.sum.value reflections with I/Sig(I) < -5
Removed 14 intensity.prf.value reflections with I/Sig(I) < -5
Filtering reflections for dataset 1
Read 75607 predicted reflections
Selected 54845 reflections integrated by profile and summation methods
Combined 1284 partial reflections with other partial reflections
Removed 50 reflections below partiality threshold
Removed 0 intensity.sum.value reflections with I/Sig(I) < -5
Removed 14 intensity.prf.value reflections with I/Sig(I) < -5
Filtering reflections for dataset 2
Read 77983 predicted reflections
Selected 54461 reflections integrated by profile and summation methods
Combined 1404 partial reflections with other partial reflections
Removed 38 reflections below partiality threshold
Removed 0 intensity.sum.value reflections with I/Sig(I) < -5
Removed 8 intensity.prf.value reflections with I/Sig(I) < -5
Filtering reflections for dataset 3
Read 76468 predicted reflections
Selected 53877 reflections integrated by profile and summation methods
Combined 1062 partial reflections with other partial reflections
Removed 8 reflections below partiality threshold
Removed 0 intensity.sum.value reflections with I/Sig(I) < -5
Removed 5 intensity.prf.value reflections with I/Sig(I) < -5
Patterson group: P 4/m m m

--------------------------------------------------------------------------------

Normalising intensities for dataset 1

ML estimate of overall B value:
   13.52 A**2
ML estimate of  -log of scale factor:
  -3.04

--------------------------------------------------------------------------------

Normalising intensities for dataset 2

ML estimate of overall B value:
   11.06 A**2
ML estimate of  -log of scale factor:
  -3.50

--------------------------------------------------------------------------------

Normalising intensities for dataset 3

ML estimate of overall B value:
   11.38 A**2
ML estimate of  -log of scale factor:
  -2.96

--------------------------------------------------------------------------------

Normalising intensities for dataset 4

ML estimate of overall B value:
   12.14 A**2
ML estimate of  -log of scale factor:
  -2.67

--------------------------------------------------------------------------------

Estimation of resolution for Laue group analysis

Removing 3 Wilson outliers with E^2 >= 16.0
Resolution estimate from <I>/<σ(I)> > 4.0 : 2.16
Resolution estimate from CC½ > 0.60: 1.80
High resolution limit set to: 1.80
Selecting 148799 reflections with d > 1.80
Setting nproc=72
Calculating rij matrix elements in 4 row-blocks
Calculated rij matrix for row-block 1
Calculated rij matrix for row-block 2
Calculated rij matrix for row-block 3
Calculated rij matrix for row-block 4
================================================================================

Automatic determination of number of dimensions for analysis
Testing dimension: 1/8
Testing dimension: 2/8
Testing dimension: 3/8
Testing dimension: 4/8
Testing dimension: 5/8
Testing dimension: 6/8
Testing dimension: 7/8
Testing dimension: 8/8
+--------------+--------------+
|   Dimensions |   Functional |
|--------------+--------------|
|            1 |    0.0787666 |
|            2 |    0.0582901 |
|            3 |    0.037648  |
|            4 |    0.0337238 |
|            5 |    0.0290806 |
|            6 |    0.0243959 |
|            7 |    0.0208905 |
|            8 |    0.0174515 |
+--------------+--------------+
Best number of dimensions: 3
Using 3 dimensions for analysis
Principal component analysis:
Explained variance: 0.0069, 0.0069, 4e-05
Explained variance ratio: 0.5, 0.5, 0.0029
Scoring individual symmetry elements
+--------------+--------+------+-----+-----------------+
|   likelihood |   Z-CC |   CC |     | Operator        |
|--------------+--------+------+-----+-----------------|
|        0.944 |   9.86 | 0.99 | *** | 4 |(0, 0, 1)    |
|        0.944 |   9.86 | 0.99 | *** | 4^-1 |(0, 0, 1) |
|        0.941 |   9.82 | 0.98 | *** | 2 |(1, 0, 0)    |
|        0.946 |   9.91 | 0.99 | *** | 2 |(0, 1, 0)    |
|        0.936 |   9.73 | 0.97 | *** | 2 |(0, 0, 1)    |
|        0.94  |   9.79 | 0.98 | *** | 2 |(1, 1, 0)    |
|        0.947 |   9.94 | 0.99 | *** | 2 |(-1, 1, 0)   |
+--------------+--------+------+-----+-----------------+
Scoring all possible sub-groups
+-------------------+-----+--------------+----------+--------+--------+---------+--------------------+
| Patterson group   |     |   Likelihood |   NetZcc |   Zcc+ |   Zcc- |   delta | Reindex operator   |
|-------------------+-----+--------------+----------+--------+--------+---------+--------------------|
| P 4/m m m         | *** |            1 |     9.85 |   9.85 |   0    |       0 | -a,-b,c            |
| P 4/m             |     |            0 |    -0.05 |   9.82 |   9.86 |       0 | -a,-b,c            |
| P m m m           |     |            0 |    -0.04 |   9.82 |   9.86 |       0 | -a,-b,c            |
| C m m m           |     |            0 |    -0.04 |   9.82 |   9.86 |       0 | a+b,-a+b,c         |
| C 1 2/m 1         |     |            0 |     0.11 |   9.94 |   9.83 |       0 | a+b,-a+b,c         |
| P 1 2/m 1         |     |            0 |     0.07 |   9.91 |   9.83 |       0 | -a,-b,c            |
| P 1 2/m 1         |     |            0 |    -0.03 |   9.82 |   9.85 |       0 | -b,-a,-c           |
| C 1 2/m 1         |     |            0 |    -0.06 |   9.79 |   9.85 |       0 | a-b,a+b,c          |
| P 1 2/m 1         |     |            0 |    -0.14 |   9.73 |   9.86 |       0 | -a,-c,-b           |
| P -1              |     |            0 |    -9.85 |   0    |   9.85 |       0 | -a,-b,c            |
+-------------------+-----+--------------+----------+--------+--------+---------+--------------------+
Best solution: P 4/m m m
Unit cell: 68.360, 68.360, 103.953, 90.000, 90.000, 90.000
Reindex operator: -a,-b,c
Laue group probability: 1.000
Laue group confidence: 1.000
Reindexing operators:
x,y,z: [0, 1, 2, 3]
Writing html report to: dials.cosym.html
Writing json to: dials.cosym.json
Saving reindexed experiments to symmetrized.expt
Saving reindexed reflections to symmetrized.refl

```

## Full parameter definitions
```
exclude_images = None
  .help = "Input in the format exp:start:end Exclude a range of images (start,"
          "stop) from the dataset with experiment identifier exp  (inclusive"
          "of frames start, stop). Multiple ranges can be given in one go,"
          "e.g. exclude_images=0:150:200,1:200:250 exclude_images='0:150:200"
          "1:200:250'"
  .short_caption = "Exclude images"
  .type = strings
  .multiple = True
  .expert_level = 1
exclude_images_multiple = None
  .help = "Exclude this single image and each multiple of this image number in"
          "each experiment. This is provided as a convenient shorthand to"
          "specify image exclusions for cRED data, where the scan of"
          "diffraction images is interrupted at regular intervals by a crystal"
          "positioning image (typically every 20th image)."
  .type = int(value_min=2, allow_none=True)
  .expert_level = 2
partiality_threshold = 0.4
  .help = "Use reflections with a partiality above the threshold."
  .type = float(allow_none=True)
unit_cell_clustering {
  threshold = 5000
    .help = "Threshold value for the clustering"
    .type = float(value_min=0, allow_none=True)
  log = False
    .help = "Display the dendrogram with a log scale"
    .type = bool
}
reference = None
  .help = "A file containing a reference set of intensities e.g. MTZ/cif, or a"
          "file from which a reference set of intensities can be calculated"
          "e.g. .pdb or .cif . The space group of the reference file will be"
          "used and if an indexing ambiguity is present, the input data will"
          "be reindexed to be consistent with the indexing mode of this"
          "reference file."
  .type = path
  .expert_level = 2
reference_model {
}
min_reflections = 10
  .help = "The minimum number of merged reflections per experiment required to"
          "perform cosym analysis."
  .type = int(value_min=0, allow_none=True)
seed = 230
  .type = int(value_min=0, allow_none=True)
normalisation = kernel quasi *ml_iso ml_aniso
  .type = choice
d_min = Auto
  .type = float(value_min=0, allow_none=True)
min_i_mean_over_sigma_mean = 4
  .short_caption = "Minimum <I>/<σ>"
  .type = float(value_min=0, allow_none=True)
min_cc_half = 0.6
  .short_caption = "Minimum CC½"
  .type = float(value_min=0, value_max=1, allow_none=True)
dimensions = Auto
  .short_caption = Dimensions
  .type = int(value_min=2, allow_none=True)
use_curvatures = True
  .short_caption = "Use curvatures"
  .type = bool
weights = *count standard_error
  .help = "If not None, a weights matrix is used in the cosym procedure."
          "weights=count uses the number of reflections used to calculate a"
          "pairwise correlation coefficient as its weight"
          "weights=standard_error uses the reciprocal of the standard error as"
          "the weight. The standard error is given by (1-CC*2)/sqrt(N), where"
          "N=(n-2) or N=(neff-1) depending on the cc_weights option."
  .short_caption = Weights
  .type = choice
cc_weights = None sigma
  .help = "If not None, a weighted cc-half formula is used for calculating"
          "pairwise correlation coefficients and degrees of freedom in the"
          "cosym procedure. weights=sigma uses the intensity uncertainties to"
          "perform inverse variance weighting during the cc calculation."
  .type = choice
min_pairs = 3
  .help = "Minimum number of pairs for inclusion of correlation coefficient in"
          "calculation of Rij matrix."
  .short_caption = "Minimum number of pairs"
  .type = int(value_min=1, allow_none=True)
minimization
  .short_caption = Minimization
{
  engine = *scitbx scipy
    .short_caption = Engine
    .type = choice
  max_iterations = 100
    .short_caption = "Maximum number of iterations"
    .type = int(value_min=0, allow_none=True)
  max_calls = None
    .short_caption = "Maximum number of calls"
    .type = int(value_min=0, allow_none=True)
}
nproc = Auto
  .help = "Number of processes"
  .type = int(value_min=1, allow_none=True)
lattice_group = None
  .short_caption = "Lattice group"
  .type = space_group
space_group = None
  .short_caption = "Space group"
  .type = space_group
lattice_symmetry_max_delta = 5.0
  .short_caption = "Lattice symmetry max δ"
  .type = float(value_min=0, allow_none=True)
best_monoclinic_beta = True
  .help = "If True, then for monoclinic centered cells, I2 will be preferred"
          "over C2 if it gives a less oblique cell (i.e. smaller beta angle)."
  .short_caption = "Best monoclinic β"
  .type = bool
relative_length_tolerance = 0.05
  .type = float(value_min=0, allow_none=True)
absolute_angle_tolerance = 2
  .type = float(value_min=0, allow_none=True)
exclude_inconsistent_unit_cells = True
  .help = "Exclude datasets with unit cells that cannot be mapped to a common"
          "minimum cell, as controlled by the absolute_angle_tolerance and"
          "relative_length_tolerance parameters. If False, an error will be"
          "raised instead."
  .type = bool
output {
  suffix = "_reindexed"
    .type = str
  log = dials.cosym.log
    .type = str
  experiments = "symmetrized.expt"
    .type = path
  reflections = "symmetrized.refl"
    .type = path
  excluded = False
    .type = bool
  excluded_prefix = "excluded"
    .type = path
  json = dials.cosym.json
    .type = path
  html = dials.cosym.html
    .type = path
}

```