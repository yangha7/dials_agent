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
- **Clean result**: report the finding, then offer numbered options and wait (see "Step
  Transitions" in your base instructions): 1. Proceed to `dials.refine` (default) 2. View the
  indexed reflections in reciprocal space first (`dials.reciprocal_lattice_viewer indexed.expt
  indexed.refl` — colored by lattice; switch to "crystal frame" to see the reciprocal lattice
  directly) 3. Something else.
- **Flagged (bent/spiral)**: explain the finding, actively suggest (not just mention) the user
  visually confirm with `dials.reciprocal_lattice_viewer indexed.expt indexed.refl` since you
  can't view it yourself, and propose the specific troubleshooting command(s) (e.g.
  `dials.search_beam_position`) — see `Indexing Quality Indicators` above and the
  `troubleshooting` skill. This is the one case worth pausing on rather than defaulting
  onward, since proceeding to refinement on bad geometry usually just wastes the next step —
  but this is specifically about a genuine geometry/beam-centre problem, not any flagged bend.
- **A small static bend explainable by indexing's own P1 default is NOT a geometry problem —
  don't escalate to `dials.refine_bravais_settings` as if it were required.** `dials.index`
  deliberately starts from the lowest-symmetry (often P1) model before any higher symmetry is
  known or applied; a real crystal with higher true symmetry (e.g. cubic) will generically show
  a small residual bend under that unconstrained model — this is expected, not a defect.
  `dials.refine_bravais_settings` is **explicitly optional** per DIALS's own tutorial
  (dials.github.io "Correcting Poor Initial Geometry" / CCP4-APS workflow docs): "in most cases
  it is absolutely fine to proceed without worrying about the crystal symmetry at this stage" —
  the tutorial's own minimal/TL;DR path skips it entirely, going straight from `dials.index` to
  `dials.refine`. `dials.symmetry` (run later, after integration, using both positions and
  intensities) is the step that actually determines symmetry properly. If the bend is small and
  plausibly explained this way (not correlated with rotation angle, no beam-centre signature),
  keep `dials.refine` as the default option — offer `dials.refine_bravais_settings` as a named,
  optional alternative for an early look, not as a required gate before refinement.
