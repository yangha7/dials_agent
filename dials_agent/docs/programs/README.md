# DIALS Program Documentation Reference

This directory contains detailed documentation for each DIALS program, fetched from the
[official DIALS documentation](https://dials.github.io/documentation/programs/index.html).

## Main Processing Commands (Workflow Order)

| # | Program | Purpose | Input | Output |
|---|---------|---------|-------|--------|
| 1 | [dials.import](dials_import.md) | Import images, create experiment file | Images (CBF/NXS/H5) | imported.expt |
| 2 | [dials.find_spots](dials_find_spots.md) | Find strong diffraction spots | imported.expt | strong.refl |
| 3 | [dials.index](dials_index.md) | Assign Miller indices, determine unit cell | imported.expt + strong.refl | indexed.expt + indexed.refl |
| 4 | [dials.refine_bravais_settings](dials_refine_bravais_settings.md) | Determine possible Bravais lattices | indexed.expt + indexed.refl | bravais_summary.json + bravais_setting_*.expt |
| 5 | [dials.reindex](dials_reindex.md) | Change indexing/space group | *.expt + *.refl | reindexed.expt + reindexed.refl |
| 6 | [dials.refine](dials_refine.md) | Refine crystal/detector models | indexed.expt + indexed.refl | refined.expt + refined.refl |
| 7 | [dials.integrate](dials_integrate.md) | Measure spot intensities | refined.expt + refined.refl | integrated.expt + integrated.refl |
| 8 | [dials.symmetry](dials_symmetry.md) | Determine space group symmetry | integrated.expt + integrated.refl | symmetrized.expt + symmetrized.refl |
| 9 | [dials.scale](dials_scale.md) | Scale and correct data | symmetrized.expt + symmetrized.refl | scaled.expt + scaled.refl |
| 10 | [dials.export](dials_export.md) | Export to MTZ/NXS/mmCIF/etc. | scaled.expt + scaled.refl | scaled.mtz |

## Standard Workflow

```
dials.import /path/to/images/
    ↓ imported.expt
dials.find_spots imported.expt
    ↓ strong.refl
dials.index imported.expt strong.refl
    ↓ indexed.expt + indexed.refl
dials.refine indexed.expt indexed.refl
    ↓ refined.expt + refined.refl
dials.integrate refined.expt refined.refl
    ↓ integrated.expt + integrated.refl
dials.symmetry integrated.expt integrated.refl
    ↓ symmetrized.expt + symmetrized.refl
dials.scale symmetrized.expt symmetrized.refl
    ↓ scaled.expt + scaled.refl + dials.scale.html
dials.export scaled.expt scaled.refl
    ↓ scaled.mtz
```

## Key Parameters Quick Reference

### dials.import
| Parameter | Default | Description |
|-----------|---------|-------------|
| `output.experiments` | imported.expt | Output filename |
| `input.template` | None | Image template (e.g., `image_####.cbf`) |
| `input.directory` | None | Directory with images |
| `input.reference_geometry` | None | Reference geometry .expt file |
| `geometry.beam.wavelength` | None | Override wavelength (Å) |
| `geometry.beam.probe` | x-ray | Probe type: x-ray, electron, neutron |
| `geometry.detector.distance` | None | Override detector distance (mm) |
| `geometry.detector.slow_fast_beam_centre` | None | Override beam centre (mm) |
| `geometry.goniometer.axis` | None | Override rotation axis |
| `lookup.mask` | None | Pixel mask file |

### dials.find_spots
| Parameter | Default | Description |
|-----------|---------|-------------|
| `spotfinder.threshold.algorithm` | dispersion_extended | Algorithm: dispersion, dispersion_extended, radial_profile |
| `spotfinder.threshold.dispersion.sigma_strong` | 3.0 | Sigma threshold (higher = fewer spots) |
| `spotfinder.threshold.dispersion.sigma_background` | 6.0 | Background sigma |
| `spotfinder.threshold.dispersion.global_threshold` | 0 | Global intensity threshold |
| `spotfinder.filter.d_min` | None | High resolution limit (Å) |
| `spotfinder.filter.d_max` | None | Low resolution limit (Å) |
| `spotfinder.filter.min_spot_size` | Auto | Minimum spot size (pixels) |
| `spotfinder.filter.max_spot_size` | 1000 | Maximum spot size (pixels) |
| `spotfinder.filter.ice_rings.filter` | False | Filter ice ring regions |
| `spotfinder.scan_range` | None | Image range (start, end) |
| `spotfinder.mp.nproc` | 1 | Number of processes |

### dials.index
| Parameter | Default | Description |
|-----------|---------|-------------|
| `indexing.method` | fft3d | Method: fft1d, fft3d, real_space_grid_search, ffbidx |
| `indexing.known_symmetry.unit_cell` | None | Known unit cell (a,b,c,α,β,γ) |
| `indexing.known_symmetry.space_group` | None | Known space group |
| `indexing.max_lattices` | 1 | Max lattices to find |
| `indexing.joint_indexing` | Auto | Joint indexing of experiments |
| `indexing.nproc` | 1 | Number of processes |
| `indexing.index_assignment.simple.hkl_tolerance` | 0.3 | HKL tolerance |
| `indexing.refinement_protocol.n_macro_cycles` | 5 | Refinement cycles |
| `indexing.refinement_protocol.d_min_start` | None | Starting resolution |

### dials.refine
| Parameter | Default | Description |
|-----------|---------|-------------|
| `refinement.parameterisation.scan_varying` | Auto | Scan-varying refinement |
| `refinement.parameterisation.interval_width_degrees` | None | Interval for scan-varying |
| `refinement.parameterisation.beam.fix` | in_spindle_plane+wavelength | Fix beam params |
| `refinement.parameterisation.crystal.fix` | None | Fix crystal params |
| `refinement.parameterisation.detector.fix` | None | Fix detector params |
| `refinement.parameterisation.goniometer.fix` | all | Fix goniometer params |
| `refinement.reflections.outlier.algorithm` | auto | Outlier rejection |
| `n_static_macrocycles` | 1 | Static refinement cycles |

### dials.integrate
| Parameter | Default | Description |
|-----------|---------|-------------|
| `integration.profile.fitting` | True | Use profile fitting |
| `integration.background.algorithm` | Auto | Background: Auto, glm, gmodel, null, simple |
| `integration.block.size` | auto | Block size |
| `integration.block.max_memory_usage` | 0.80 | Max memory fraction |
| `integration.mp.nproc` | 1 | Number of processes |
| `prediction.d_min` | None | High resolution limit (Å) |
| `prediction.d_max` | None | Low resolution limit (Å) |

### dials.symmetry
| Parameter | Default | Description |
|-----------|---------|-------------|
| `d_min` | Auto | High resolution limit |
| `min_i_mean_over_sigma_mean` | 4 | Minimum I/sigma |
| `min_cc_half` | 0.6 | Minimum CC1/2 |
| `normalisation` | ml_aniso | Normalisation method |
| `laue_group` | auto | Laue group (auto=test all) |
| `systematic_absences.check` | True | Check systematic absences |

### dials.scale
| Parameter | Default | Description |
|-----------|---------|-------------|
| `model` | physical | Model: KB, array, dose_decay, physical |
| `d_min` | None | High resolution cutoff (Å) |
| `anomalous` | False | Separate anomalous pairs |
| `physical.absorption_correction` | auto | Absorption correction |
| `physical.absorption_level` | None | Level: low, medium, high |
| `physical.decay_correction` | True | B-factor correction |
| `physical.scale_interval` | auto | Scale parameter interval |
| `overwrite_existing_models` | False | For re-scaling |
| `filtering.method` | None | Filtering: None, deltacchalf |

### dials.export
| Parameter | Default | Description |
|-----------|---------|-------------|
| `format` | mtz | Format: mtz, nxs, mmcif, xds_ascii, sadabs, shelx, etc. |
| `intensity` | auto | Intensity: auto, profile, sum, scale |
| `mtz.hklout` | auto | MTZ output filename |
| `mtz.combine_partials` | True | Combine partial reflections |
| `mtz.filter_ice_rings` | False | Filter ice rings |

## Utility Programs

| Program | Purpose | Documentation |
|---------|---------|---------------|
| [dials.show](dials_show.md) | Display experiment/reflection information | [docs](dials_show.md) |
| [dials.image_viewer](dials_image_viewer.md) | Interactive image viewer (GUI) | [docs](dials_image_viewer.md) |
| [dials.generate_mask](dials_generate_mask.md) | Generate pixel mask for bad regions | [docs](dials_generate_mask.md) |
| [dials.apply_mask](dials_apply_mask.md) | Apply mask to experiment file | [docs](dials_apply_mask.md) |
| [dials.check_indexing_symmetry](dials_check_indexing_symmetry.md) | Check indexing symmetry | [docs](dials_check_indexing_symmetry.md) |
| [dials.search_beam_position](dials_search_beam_position.md) | Find optimal beam centre | [docs](dials_search_beam_position.md) |
| [dials.report](dials_report.md) | Generate HTML analysis report | [docs](dials_report.md) |
| [dials.plot_scan_varying_model](dials_plot_scan_varying_model.md) | Plot scan-varying parameters | [docs](dials_plot_scan_varying_model.md) |
| [dials.create_profile_model](dials_create_profile_model.md) | Create profile model for integration | [docs](dials_create_profile_model.md) |
| [dials.estimate_gain](dials_estimate_gain.md) | Estimate detector gain | [docs](dials_estimate_gain.md) |
| [dials.estimate_resolution](dials_estimate_resolution.md) | Estimate resolution limits | [docs](dials_estimate_resolution.md) |
| [dials.predict](dials_predict.md) | Predict reflection positions | [docs](dials_predict.md) |
| [dials.merge_cbf](dials_merge_cbf.md) | Merge CBF files | [docs](dials_merge_cbf.md) |
| [dials.spot_counts_per_image](dials_spot_counts_per_image.md) | Spot counts per image | [docs](dials_spot_counts_per_image.md) |
| [dials.stereographic_projection](dials_stereographic_projection.md) | Stereographic projections | [docs](dials_stereographic_projection.md) |
| [dials.combine_experiments](dials_combine_experiments.md) | Combine experiment files | [docs](dials_combine_experiments.md) |
| [dials.align_crystal](dials_align_crystal.md) | Calculate goniometer alignment | [docs](dials_align_crystal.md) |
| [dials.anvil_correction](dials_anvil_correction.md) | Diamond anvil cell correction | [docs](dials_anvil_correction.md) |
| [dials.missing_reflections](dials_missing_reflections.md) | Find missing reflections | [docs](dials_missing_reflections.md) |
| [dials.filter_reflections](dials_filter_reflections.md) | Filter reflections by criteria | [docs](dials_filter_reflections.md) |
| [dials.import_xds](dials_import_xds.md) | Import XDS results | [docs](dials_import_xds.md) |

## Source

Documentation fetched from https://dials.github.io/documentation/programs/index.html
using `fetch_docs.py` script.
