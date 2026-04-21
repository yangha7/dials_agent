# dials.anvil_correction

## Introduction
Correct integrated intensities to account for attenuation by a diamond anvil cell.
High pressure X-ray diffraction experiments often involve a diamond anvil pressure
cell, in which the sample is sandwiched between two anvils, effectively parallel flat
plates of diamond.  The passage of the incident and diffracted beam through the
anvils results in attenuation of both beams by the diamond by an amount that is
dependent on the path length of each beam through each anvil.
This utility calculates these path lengths and boosts the integrated reflection
intensities to remove the calculated effect of the diamond attenuation.
It is intended that this program be used to correct reflection intensities after
integration but before scaling.  Call it on the output of dials.integrate.
Examples:
```
dials.anvil_correction integrated.expt integrated.refl

dials.anvil_correction integrated.expt integrated.refl thickness=1.2 normal=1,0,0

```

## Full parameter definitions
```
anvil
  .caption = "Properties of the mounted diamond anvils"
{
  density = 3510
    .help = "The density of the anvil material in kg per cubic metre.   The"
            "default is the typical density of synthetic diamond."
    .type = float(allow_none=True)
  thickness = 1.5925
    .help = "The thickness in mm of each anvil in the pressure cell.   The"
            "default is the thickness of the pressure cells in use on "
            "beamline I19 at Diamond Light Source."
    .type = float(allow_none=True)
  normal = 0, 1, 0
    .help = "A 3-vector orthogonal to the anvil surfaces in the laboratory "
            "frame when the goniometer is at zero datum, i.e. the axes are "
            "all at zero degrees.  The vector may be given un-normalised."
    .type = floats(size=3)
}
output {
  experiments = None
    .help = "The output experiment list file name. If None, don't output an "
            "experiment list file."
    .type = path
  reflections = corrected.refl
    .help = "The output reflection table file."
    .type = path
  log = dials.anvil_correction.log
    .type = path
}

```

## Details
The path lengths \(l_0\) and \(l_1\) of the incident and diffracted beams through the diamond anvils of the pressure cell are illustrated in the schematic below.
The anvils are assumed to have equal thickness \(t\) and to be perfectly parallel.
The cell is fixed to the goniometer, so its orientation depends on the goniometer rotation \(R\).
When the goniometer is at the zero datum, the anvils’ normal is \(\mathbf{\hat{n}}\), so in general, the anvils’ normal is \(R\mathbf{\hat{n}}\).

Since the magnitude of the incident and diffracted beam vectors \(\mathbf{s}_0\) and \(\mathbf{s}_1\) is simply \(\left|\mathbf{s}_i\right| = 1/\lambda\), the path lengths \(l_0\) and \(l_1\) are

\[l_i = \frac{t}{\left|\cos{\left(\alpha_i\right)}\right|} = \frac{t}{\left|\lambda\mathbf{s}_i \cdot R\mathbf{\hat{n}}\right|} \,\text.\]
As a result of absorption in the anvil material, the intensity of each beam is reduced by a factor \(\exp{\left(-\mu l_i\right)}\), where \(\mu\) is the linear absorption coefficient.
Hence each diffraction spot has intensity attenuated by a factor

\[e^{-\mu\left(l_0 + l_1\right)}\text.\]
With knowledge of the density \(\rho\) of the diamond anvils, \(\mu\) can be calculated from tabulated values of the mass attenuation coefficient for carbon \(\left(\mu/\rho\right)_\text{C}\).
The mass attenuation coefficient is taken from data collated by the US National Institute of Standards and Technology [NIST].
After integrating the observed diffraction spot intensities, we can recover an approximation of the intensity that might be expected in the absence of X-ray attenuation by the anvil material.
This is simply achieved by multiplying each of the profile-fitted integrated intensities, the summation integrated intensities and their respective standard deviations by a factor

\[e^{\left(\mu/\rho\right)_\text{C}\,\rho\,\left(l_0 + l_1\right)}\text.\]
Note that in the case of the standard deviations, this correction may subtly contradict certain assumptions in the error model of your chosen scaling utility.
The effect is not anticipated to be very significant in most cases and no attempt is made to account for it at this stage.

[NIST]
Hubbell, J.H. and Seltzer, S.M. (2004), Tables of X-Ray Mass Attenuation Coefficients and Mass Energy-Absorption Coefficients (version 1.4). [Online] Available: http://physics.nist.gov/xaamdi [2020-01-31]. National Institute of Standards and Technology, Gaithersburg, MD, USA.