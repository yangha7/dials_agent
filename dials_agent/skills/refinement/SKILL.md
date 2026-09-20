---
name: refinement
description: Improving crystal and detector models (dials.refine)
---

### Refinement Quality Indicators
- RMSD should decrease during refinement
- Scan-varying refinement should show smooth parameter changes
- Large jumps in scan-varying parameters, or RMSDs that stay high/unstable, often look
  like the crystal is "moving" or "drifting" during the rotation — but before treating
  this as real crystal motion (or reaching for `indexing.max_lattices` if it also looks
  like multiple lattices), rule out an incorrect initial beam centre. Confirm with
  `dials.check_indexing_symmetry indexed.expt indexed.refl` first — a systematic offset
  (e.g. delta_h=1, delta_k=1, delta_l=1) is the concrete signature of a beam-centre
  problem — then run `dials.search_beam_position imported.expt strong.refl` and
  re-index/re-refine. This single fix commonly resolves both symptoms at once. See the
  `troubleshooting` skill's "Multiple crystals / multi-lattice" and "Refinement fails or
  diverges" sections.

### After Refinement (Geometry Check + Visualization)
Run the reciprocal-lattice linearity check (see your base instructions) again on
`refined.expt`/`refined.refl` right after `dials.refine` succeeds — don't wait to be asked,
and don't skip it just because it already looked fine after indexing (refinement can reveal
or introduce drift that wasn't visible before).
- **Clean result**: note briefly, mention `dials.reciprocal_lattice_viewer refined.expt
  refined.refl` is available if they want to look themselves, and default to suggesting
  `dials.integrate` directly in the same message — don't ask and wait.
- **Flagged**: explain the finding, actively point the user at
  `dials.reciprocal_lattice_viewer refined.expt refined.refl` to confirm visually themselves,
  and propose the specific fix (e.g. `dials.search_beam_position`, then re-index/re-refine)
  rather than just reporting the number — worth pausing on here rather than defaulting onward,
  same reasoning as the indexing step's flagged case.
