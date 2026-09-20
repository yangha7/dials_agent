---
name: indexing
description: Assigning Miller indices and determining the unit cell (dials.index)
---

### Indexing Quality Indicators
- Good: >80% spots indexed
- RMS deviation: <0.3 pixels is excellent, <0.5 is acceptable
- If < 50% indexed: check for multiple lattices, ice rings, or wrong beam centre
- If indexing *succeeds* but reports more than one lattice (or a single crystal that
  looks split), don't assume it's genuinely multi-lattice yet — an incorrect initial
  beam centre commonly produces this exact pattern. Confirm first with
  `dials.check_indexing_symmetry indexed.expt indexed.refl` — a systematic offset
  (e.g. delta_h=1, delta_k=1, delta_l=1) is the concrete signature of a beam-centre
  problem, matching the diagnostic DIALS's own "Correcting Poor Initial Geometry"
  tutorial (DPF3 part 1) uses before reaching for `dials.search_beam_position
  imported.expt strong.refl` and re-indexing; see the `troubleshooting` skill for
  the full reasoning.

### After Indexing (Geometry Check + Visualization)
Run the reciprocal-lattice linearity check (see the numeric check described in your base
instructions) automatically right after `dials.index` succeeds — don't wait to be asked.
- **Clean result**: briefly note geometry checks out, mention `dials.reciprocal_lattice_viewer
  indexed.expt indexed.refl` is available (colored by lattice; switch to "crystal frame" to
  see the reciprocal lattice directly) if they want to look themselves, and default to
  suggesting `dials.refine` directly in the same message — don't ask and wait.
- **Flagged (bent/spiral)**: explain the finding, actively suggest (not just mention) the user
  visually confirm with `dials.reciprocal_lattice_viewer indexed.expt indexed.refl` since you
  can't view it yourself, and propose the specific troubleshooting command(s) (e.g.
  `dials.search_beam_position`) — see `Indexing Quality Indicators` above and the
  `troubleshooting` skill. This is the one case worth pausing on rather than defaulting
  onward, since proceeding to refinement on bad geometry usually just wastes the next step.
