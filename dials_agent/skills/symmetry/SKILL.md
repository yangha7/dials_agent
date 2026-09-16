---
name: symmetry
description: Determining space group and resolving indexing ambiguity (dials.symmetry / dials.cosym)
---

### Choosing dials.symmetry vs. dials.cosym
- Single crystal: use `dials.symmetry`
- Multiple crystals / multi-lattice: use `dials.cosym` instead — it also resolves indexing ambiguity across datasets
- Before committing to a space group, recall the centring vs. pseudo-centring check from the
  `integration` step (see your base instructions) — if it flagged an axis, use
  `dials.refine_bravais_settings` to specifically test the corresponding centred setting and
  compare refinement statistics, rather than picking a setting based on apparent systematic
  absences alone. A pseudo-centred axis looks like it implies a centred space group, but
  treating those reflections as truly absent discards real (if weak) data.

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
