# Processing 🐮🐷🧑 with DIALS (CCP4 / DLS 2024)

## Introduction

DIALS data processing may be run by automated tools such as `xia2` or interactively on the command line. For a tutorial it is more useful to use the latter, to explain the opportunities afforded by the software. In any data processing package the workflow requires reading data, finding spots, indexing to get an orientation matrix, refinement, integration and then scaling / correction: DIALS is no different.

This tutorial deviates slightly from the mainstream by _starting_ with data from a number of crystals, first from a single sample type and then from a mixture, which will show you how to classify data with subtle differences (e.g. presence or absence of a ligand.)

## The Data

[The data](https://zenodo.org/records/13890874) (~6GB) were taken on i24 at Diamond Light Source as part of routine commissioning work, with a number of small rotation data sets recorded from different crystals. Crystals were prepared of the protein insulin from cows, pigs and people (as described on the Zenodo deposition; bovine, porcine and human insulin, of course all grown in e-coli anyway).

All data have symmetry I213 and very similar unit cell constants so you can _try_ to merge them together and it will work, but won't give you good results as you will be measuring a mixture of structures. The data on the deposition are in `tar` archives so I am assuming you have already downloaded them all and unpacked them into `../data`: if you have done something different you will need to take a little care at the `dials.import` stage.

If you are at the workshop in real life, the data are already in:

```
/dls/i04/data/2024/mx39148-1/tutorial_data/cows_pigs_people
```

so you don't need to download the data - but you'll need to use this path in place of `../data` - you do not need to follow these instructions here.

If you don't already have the data downloaded, you can do this with this script on linux / UNIX:

```
mkdir data
cd data
for set in CIX1_1 CIX2_1 CIX3_1 CIX5_1 CIX6_1 CIX8_1 CIX9_1 CIX10_1 CIX11_1 CIX12_1 CIX14_1 CIX15_1 PIX5_1 PIX6_1 PIX7_1 PIX8_1 PIX9_1 PIX10_1 PIX11_1 PIX12_1 PIX13_1 PIX14_1 PIX15_1 PIX16_1 X1_1 X2_1 X3_1 X4_1 X5_1 X6_1 X7_1 X8_1 X9_1 X11_1 X13_1 X14_1 ; do
wget https://zenodo.org/records/13890874/files/${set}.tar
tar xvf ${set}.tar
rm -v ${set}.tar
done
```

## The Workflow

The [workflow](./WORKFLOW.md) is the same with one data set as with many, with some small deviations - data from multiple crystals will not in general share an orientation matrix so the indexing will need to _not_ join all the lattices.

As mentioned above the flow is to read the data, find spots, index, refine, integrate and then derive some corrections from symmetry related reflections, which involves assigning the symmetry. In DIALS we use the following tools:

- `dials.import` - read all the image headers to make sense of the metadata
- `dials.find_spots` - find the spots - with DIALS we find spots across the whole data set and one spot across multiple images is "found" in 3D
- `dials.index` - assign indices to the spots and derive unit cell, symmetry
- `dials.refine` - improve the models from indexing (separate as allows "wobbles")
- `dials.integrate` - measure the background subtracted spot intensity
- `dials.symmetry` - derive the Patterson symmetry of the crystal from the data
- `dials.scale` - correct the data for sample decay, overall scale from beam or illuminated volume and absorption
- `dials.export` - output processed data for e.g. use in CCP4 or PHENIX

With multiple sweeps from a single crystal, we can assign a single orientation matrix and then use this throughout the processing (the default) - however if you have data from multiple crystals some of the assumptions will break down so we need to (i) tell the software that the crystals _do not_ share a matrix and in the symmetry determination also resolve any indexing ambiguity: we therefore replace `dials.symmetry` with `dials.cosym`.

## Import

The data are in `../data`: for the first pass through this tutorial we will just process the "cow" data `CIX...` to keep things simple. There are data from 12 crystals in here and if we simply import every frame, `dials.import` will make sense of what it finds:

```
dials.import ../data/CIX*gz
```

to get:

```
DIALS (2018) Acta Cryst. D74, 85-97. https://doi.org/10.1107/S2059798317017235
DIALS 3.dev.1184-gb491c224e
The following parameters have been modified:

input {
  experiments = <image files>
}

--------------------------------------------------------------------------------
  format: <class 'dxtbx.format.FormatCBFFullPilatus.FormatCBFFullPilatus'>
  template: /Users/graeme/data/ccp4-aps-tutorials/cix/data/CIX1_1_#####.cbf.gz:1:100
  template: /Users/graeme/data/ccp4-aps-tutorials/cix/data/CIX2_1_#####.cbf.gz:1:100
  template: /Users/graeme/data/ccp4-aps-tutorials/cix/data/CIX3_1_#####.cbf.gz:1:100
  template: /Users/graeme/data/ccp4-aps-tutorials/cix/data/CIX5_1_#####.cbf.gz:1:100
  template: /Users/graeme/data/ccp4-aps-tutorials/cix/data/CIX6_1_#####.cbf.gz:1:100
  template: /Users/graeme/data/ccp4-aps-tutorials/cix/data/CIX8_1_#####.cbf.gz:1:100
  template: /Users/graeme/data/ccp4-aps-tutorials/cix/data/CIX9_1_#####.cbf.gz:1:100
  template: /Users/graeme/data/ccp4-aps-tutorials/cix/data/CIX10_1_#####.cbf.gz:1:100
  template: /Users/graeme/data/ccp4-aps-tutorials/cix/data/CIX11_1_#####.cbf.gz:1:100
  template: /Users/graeme/data/ccp4-aps-tutorials/cix/data/CIX12_1_#####.cbf.gz:1:100
  template: /Users/graeme/data/ccp4-aps-tutorials/cix/data/CIX14_1_#####.cbf.gz:1:100
  template: /Users/graeme/data/ccp4-aps-tutorials/cix/data/CIX15_1_#####.cbf.gz:1:100
  num images: 1200
  sequences:
    still:    0
    sweep:    12
  num stills: 0
--------------------------------------------------------------------------------
Writing experiments to imported.expt
```

This shows the filename patterns, how many images for each and the total it found - 12 sweeps each of 100 images. We can get much more detail on this with `dials.show` which can print the "DIALS understanding" of what the data look like. There are ways to streamline this for very large numbers of images, but for now this is fine.

At this point: scan the output - do you have what you expected? Many problems with DIALS processing can be solved here.

## Spot Finding

Spot finding is exactly what it sounds like: finding where all the spots are in the data sets. In DIALS spots in the same place on adjacent images are considered to be joined so the spot is a three dimensional object. You can explore the spot finding by opening the images in `dials.image_viewer` with

```
dials.image_viewer imported.expt
```

and then clicking through the options at the bottom of the control window (I will demo this in real life, and make a video, but you can click through the steps to "threshold" which is the set of pixels the spot fiding will pick out). The spot finding:

```
dials.find_spots imported.expt
```

will give a summary of the number of signal pixels on every image, the number of found spots on each run and at the end a histogram of the distribution of spots across the images on each run, as:

```
Histogram of per-image spot count for imageset 10:
7446 spots found on 100 images (max 231 / bin)
*                                              *
*                                              *
*                                              *
*                                              *
*                                              *
** *    *   **  *           *  **    * *** *   *   *
*************************** * *** *** ** ********** ********
************************************************************
************************************************************
1                         image                          100
```

This shows that the spots are reasonably evenly distributed across the images, which is what you would expect for a well-diffracting crystal. The output is written to `strong.refl` which contains the spot positions and intensities.

## Indexing

Indexing is the process of assigning Miller indices to the spots, which requires determining the unit cell and orientation of the crystal. For multiple crystals we need to tell DIALS that the crystals do not share an orientation matrix:

```
dials.index imported.expt strong.refl joint=false
```

The `joint=false` parameter tells DIALS to index each sweep independently. The output will show the unit cell and space group for each crystal.

## Refinement

After indexing, we refine the crystal and detector models:

```
dials.refine indexed.expt indexed.refl
```

This improves the models from indexing and allows for "wobbles" in the crystal orientation during the scan.

## Integration

Integration measures the background-subtracted spot intensity:

```
dials.integrate refined.expt refined.refl
```

## Symmetry and Scaling

For multiple crystals, we use `dials.cosym` instead of `dials.symmetry` to resolve any indexing ambiguity:

```
dials.cosym integrated.expt integrated.refl
```

Then scale the data:

```
dials.scale symmetrized.expt symmetrized.refl
```

## Export

Finally, export the processed data for use in CCP4 or PHENIX:

```
dials.export scaled.expt scaled.refl
```

This will create an MTZ file that can be used for structure determination.

## Processing All Data

Once you have processed the cow data, you can repeat the process for the pig (`PIX*`) and human (`X*`) data, or process all data together and use clustering to separate the different sample types.

## Further Reading

- [DIALS documentation](https://dials.github.io/)
- [DIALS tutorials](https://dials.github.io/documentation/tutorials/index.html)
- [xia2 documentation](https://xia2.github.io/)
