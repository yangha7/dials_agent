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
  like multiple lattices), rule out an incorrect initial beam centre: run
  `dials.search_beam_position imported.expt strong.refl` and re-index/re-refine. This
  single fix commonly resolves both symptoms at once. See the `troubleshooting` skill's
  "Multiple crystals / multi-lattice" and "Refinement fails or diverges" sections.

### After Refinement (Geometry Check + Visualization)
Run the reciprocal-lattice linearity check (see your base instructions) again on
`refined.expt`/`refined.refl` right after `dials.refine` succeeds — don't wait to be asked,
and don't skip it just because it already looked fine after indexing (refinement can reveal
or introduce drift that wasn't visible before).
- **Clean result**: note briefly, and still offer visualization as a normal option: "Would
  you like to visualize the refined reflections in reciprocal space?" →
  `dials.reciprocal_lattice_viewer refined.expt refined.refl`. Then proceed to integration.
- **Flagged**: explain the finding, actively point the user at
  `dials.reciprocal_lattice_viewer refined.expt refined.refl` to confirm visually themselves,
  and propose the specific fix (e.g. `dials.search_beam_position`, then re-index/re-refine)
  rather than just reporting the number.
