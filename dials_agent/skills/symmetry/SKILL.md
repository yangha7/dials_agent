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
  admits them), THEN compare real refinement statistics (Rmerge/Rmeas/Rpim/CC½/completeness
  from `dials.scale`, not R-cryst/R-free — that needs a structure-refinement program like
  Phenix/Refmac, which is outside DIALS's scope entirely) between the primitive and centred
  settings — that comparison, plus a direct check of the actual systematic-absence intensity
  ratio (see below), is the decisive test, not the I/sigma(I) reading of the weak reflections
  on their own (real systematic absences are rarely perfectly zero in practice, so even
  clearly-nonzero I/sigma(I) does not rule out true centring by itself). Two more real mistakes
  found live-testing this exact sequence, worth avoiding:
  - **`dials.reindex ... space_group="C 2 2 21"` with no change-of-basis operator (or
    `change_of_basis_op=a,b,c`, the identity) only relabels the space group symbol — it does
    NOT transform the Miller indices.** Testing centring on data reindexed this way just
    re-tests the original, unchanged indices under a new label, and will show no signal
    regardless of whether centring is real. Use `reference.experiments=bravais_setting_N.expt`
    (the actual re-refined candidate from `dials.refine_bravais_settings`) so a real
    transformation is applied, or an explicit non-identity `change_of_basis_op=`.
  - **Don't write a new ad hoc Python script to test a specific centering condition (e.g. is
    h+k always even?) directly against intensities** — this is exactly the kind of small
    numeric script that's easy to get subtly wrong under time pressure (a real instance:
    building `even_mask`/`odd_mask` correctly but then computing both group means from the
    full, unmasked array, silently making the whole test a no-op comparison of the data
    against itself). `dials/scripts/centring_vs_pseudocentring_check.py` already has a
    `--verify-centering` mode for exactly this (see your base instructions) — it's tested;
    a fresh script written in the moment isn't.
  - **If `dials.refine_bravais_settings` fails outright** with `DialsRefineConfigError:
    Cannot set statistical weights as some indexed reflections have observed variances equal
    to zero`, this is a numerical edge case (very weak reflections with degenerate
    profile-fit variance under the default 'statistical' weighting) unrelated to the
    reindexing/centring question above -- fix with
    `refinement.reflections.weighting_strategy.override=constant` and re-run. It isn't
    documented in any specific DIALS tutorial; that doesn't mean it won't come up on real
    data, so don't wait for a tutorial reference before applying it. See `diagnose_problem`
    (keyword: "statistical weight" / "zero variance") for the same guidance.

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
