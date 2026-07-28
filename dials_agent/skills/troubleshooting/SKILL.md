---
name: troubleshooting
description: Diagnosing common DIALS processing problems with parameter-level fixes
---

## Problem Diagnosis

You have access to a `diagnose_problem` tool that maps common crystallography problems to specific parameter-level solutions. Use this when:
- A command fails or produces poor results
- The user reports issues like "too few spots", "indexing failed", "high Rmerge"
- You need to suggest specific parameter adjustments

The tool covers problems in all workflow stages: spot finding, indexing, refinement, integration, scaling, and special cases (ice rings, electron diffraction, high-pressure DAC).

## Troubleshooting

### "No experiments found" during import
- Check file paths and patterns
- Verify image format is supported (CBF, HDF5/NXS, SMV, TIFF)
- Try using `input.template=image_####.cbf` parameter
- For HDF5/NXS: check the file is not corrupted with `h5dump -H file.nxs`

### "No solution found" during indexing
- Try different method: `indexing.method=fft1d` or `indexing.method=real_space_grid_search`
- Provide known unit cell: `indexing.known_symmetry.unit_cell=a,b,c,alpha,beta,gamma`
- Check for multiple lattices: `indexing.max_lattices=2`
- Verify beam center: run `dials.search_beam_position` first
- Increase search scope: `indexing.mm_search_scope=8.0`
- Try with fewer spots: use `spotfinder.scan_range=1,100` to find spots on a subset

### Low indexed percentage (< 70%)
- Crystal may have multiple domains → `indexing.max_lattices=2`
- Ice rings present → `spotfinder.filter.ice_rings.filter=True`
- Increase HKL tolerance → `indexing.index_assignment.simple.hkl_tolerance=0.4`
- Wrong beam centre → run `dials.search_beam_position`

### Refinement fails or diverges
- Fix detector: `refinement.parameterisation.detector.fix=all`
- Fix beam: `refinement.parameterisation.beam.fix=all`
- Disable scan-varying: `refinement.parameterisation.scan_varying=False`
- More static cycles: `n_static_macrocycles=3`
- Change outlier rejection: `refinement.reflections.outlier.algorithm=tukey`

### Integration out of memory
- Reduce memory: `integration.block.max_memory_usage=0.50`
- Fewer processors: `integration.mp.nproc=2`
- Smaller blocks: `integration.block.size=5 integration.block.units=degrees`

### High Rmerge during scaling
- Apply absorption correction: `physical.absorption_correction=True physical.absorption_level=medium`
- Enable ΔCC½ filtering: `filtering.method=deltacchalf filtering.deltacchalf.stdcutoff=4.0`
- Try array model: `model=array`
- Apply resolution cutoff: `d_min=2.5`
- Check indexing consistency: `scaling_options.check_consistent_indexing=True`
- Exclude damaged images: `exclude_images=0:start:end`

### Ice rings in data
- Filter during spot finding: `spotfinder.filter.ice_rings.filter=True`
- Generate mask: `dials.generate_mask imported.expt ice_rings.filter=True`
- Filter during integration: `integration.filter.ice_rings=True`
- Filter during export: `mtz.filter_ice_rings=True`

### Electron diffraction (MicroED/cRED)
- Set probe type: `geometry.beam.probe=electron` during import
- Adjust spot finding: `spotfinder.threshold.dispersion.sigma_strong=4.0`
- For cRED: `exclude_images_multiple=20` to skip positioning images

### High-pressure DAC data
- Apply anvil correction: `dials.anvil_correction integrated.expt integrated.refl anvil.thickness=1.5925`
- Generate shadow mask: `dials.generate_mask imported.expt`

### Multiple crystals / multi-lattice
- Index multiple lattices: `indexing.max_lattices=5`
- Use cosym for symmetry: `dials.cosym` instead of `dials.symmetry`
- Check consistent indexing during scaling: `scaling_options.check_consistent_indexing=True`

### Weak diffraction / low resolution
- Lower sigma threshold: `spotfinder.threshold.dispersion.sigma_strong=2.0`
- Use summation integration: `integration.profile.fitting=False`
- Apply resolution cutoff: `d_min=3.0` during scaling
- Use dose_decay model: `model=dose_decay` for radiation-sensitive crystals
