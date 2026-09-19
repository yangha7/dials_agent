---
name: symmetry
description: Determining space group and resolving indexing ambiguity (dials.symmetry / dials.cosym)
---

### Choosing dials.symmetry vs. dials.cosym
- Single crystal: use `dials.symmetry`
- Multiple crystals / multi-lattice: use `dials.cosym` instead — it also resolves indexing ambiguity across datasets
- Before committing to a space group, recall the centring vs. pseudo-centring check from the
  `integration` step (see your base instructions). If it flagged an axis, **do not** just run
  `dials.refine_bravais_settings` on the current (primitive) indexing and treat an absence of
  centred candidates as the answer — it only ever finds subgroups of whatever cell it's given,
  so it structurally cannot discover a centred description the input cell was never reindexed
  toward. Concluding "no centred candidates were found, so this must be pseudo-centring" from
  that alone is a real failure mode found live-testing this exact DPF3 tutorial dataset, whose
  actual answer is the opposite: a genuine C222₁ centred setting that only becomes visible once
  the cell is reindexed toward it. The correct sequence: `dials.reindex` toward the centred
  space group matching the flagged axis FIRST, THEN re-run `dials.refine_bravais_settings` on
  that reindexed result (centred candidates only appear once the input cell's metric symmetry
  admits them), THEN compare real refinement R-factors between the primitive and centred
  settings — that comparison is the decisive test, not the I/sigma(I) reading of the weak
  reflections on their own (real systematic absences are rarely perfectly zero in practice, so
  even clearly-nonzero I/sigma(I) does not rule out true centring by itself).

### After Symmetry (Visualization)
- **After `dials.cosym`** (multi-crystal case): since cosym can reindex individual datasets
  to a consistent setting, offer to confirm this visually: "Would you like to check that all
  datasets are now consistently indexed?" → `dials.reciprocal_lattice_viewer` with the
  reindexed experiment/reflection files together — datasets that are still inconsistent will
  show as misaligned reciprocal lattices rather than overlapping cleanly.
- **After `dials.symmetry`** (single crystal): no image/reciprocal-lattice viewer needed here
  — the lattice geometry was already checked after indexing/refinement, and symmetry
  determination doesn't change it. Look at the symmetry log / HTML report if generated
  instead.
