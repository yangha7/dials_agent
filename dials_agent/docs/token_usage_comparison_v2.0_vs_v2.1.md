# Token Usage Comparison: v2.0.0 vs. v2.1.0 (Progressive Disclosure)

## Overview

v2.0.0 split the monolithic system prompt into 12 self-contained skills
(`dials_agent/skills/`), but a follow-up measurement
(`token_usage_comparison_before_after_skills.md`, run 2026-07-16) showed
that refactor alone *increased* total session tokens ~3.5–5% versus the
original v1.3 monolithic prompt — every skill's full guidance was still
concatenated into every request, so splitting the code didn't reduce what
was sent to the LLM.

v2.1.0 (2026-07-28, commits `00d035b` and `bb1894b`) fixes this with
progressive disclosure, mirroring how Claude Code loads its own skills:

- `SkillRegistry.get_composed_prompt()` now returns a compact index
  (name + one-line description per skill) instead of every skill's full
  guidance.
- A new `load_skill` tool lets the LLM pull a specific skill's full
  guidance into the conversation on demand, once per skill per session.
- Each skill's guidance text was also extracted out of its Python file
  into a real `dials_agent/skills/<name>/SKILL.md` (YAML-ish frontmatter
  + markdown body), matching the actual Claude Code/Anthropic skill
  packaging convention — content separate from code.

This document reruns the same before/after methodology used for the
original v1.3→v2.0.0 comparison, this time for v2.0.0→v2.1.0, using two
fresh `--auto` full-pipeline runs on the same insulin (ins10) dataset,
`image_range=1,1200` ("fast version"), on `dials-remote` (dials.lbl.gov).

## Aggregate Comparison

| Version | Total tokens (avg of 2 runs) | Wall-clock (avg) | Change vs. v2.0.0 |
|---|---:|---:|---:|
| v1.3 (pre-skills, monolithic) | 442,460 | 11m 21.7s | — |
| v2.0.0 (skills split, no disclosure gating) | 458,032 | 10m 54.6s | +15,572 (+3.5%) |
| **v2.1.0 (progressive disclosure)** | **351,109** | 7m 43.2s | **−106,923 (−23.3%)** |

v2.1.0 vs. the original pre-skills v1.3 baseline: **−91,351 tokens (−20.6%)**.
So this isn't just clawing back the v2.0.0 regression — it's a net
reduction versus the very first monolithic-prompt version of the agent.

## Per-Run Detail (v2.1.0)

Both runs: `--auto --auto-message "Process the insulin data, fast version"`,
fresh working directories under
`/net/dials/raid1/yangha/Tutorial/ins10_files_4_token_cost/` on
`dials-remote`, full pipeline import → merge, no errors, no manual
intervention.

**Run 1** (`dials_agent_auto`):
- Total tokens: 346,144
- Wall-clock: 8m 50.3s (5m 37.0s DIALS command time)
- Command timing: import 38.9s, find_spots 1m 29.7s, index 29.6s,
  refine 21.7s, integrate 1m 30.8s, symmetry 35.7s, scale 22.3s, merge 8.3s

**Run 2** (`dials_agent_auto_2`):
- Total tokens: 356,074
- Wall-clock: 6m 36.1s (4m 20.9s DIALS command time)
- Command timing: import 5.0s, find_spots 1m 13.4s, index 26.0s,
  refine 20.9s, integrate 1m 29.1s, symmetry 19.3s, scale 20.7s, merge 6.6s

Both runs used the identical `dials.import ... image_range=1,1200`
subset, so the comparison is apples-to-apples. As with the original
before/after report, wall-clock time is dominated by DIALS compute
(find_spots/integrate) and cluster load at run time, not agent-side LLM
logic — it's reported for completeness, not as evidence of the token
change.

Per-turn session totals (from the CLI's live token-usage line) confirm
the caching pattern progressive disclosure is meant to produce: a large
first turn (system-prompt cache write + initial context), then much
smaller per-turn deltas for the rest of the run, rather than every turn
re-paying the cost of all 12 skills' full guidance.

## Interpretation

- Progressive disclosure delivers a real, measured ~23% token reduction
  versus v2.0.0, confirming the mechanism works as designed rather than
  just looking smaller on paper (prompt caching makes cache-write vs.
  cache-read costs and per-turn token *counts* — as opposed to billed
  cost — behave differently from naive char-count math, so this was
  worth verifying live rather than trusting the static ~56% cached-prefix
  estimate alone).
- It also beats the original pre-skills v1.3 baseline, meaning the
  modular skills architecture (12 self-contained skills + registry) is
  now a net win on tokens, not just on code organization.
- Sample size is small (n=2 per version, matching the original
  methodology) — treat as indicative. The original report's caveat
  applies here too: more trials would help confirm this holds up beyond
  run-to-run noise.

---
*Reference: `dials_agent/skills/__init__.py` (`SkillRegistry`),
`dials_agent/skills/base.py` (`load_skill_md`), and the 12
`dials_agent/skills/<name>/SKILL.md` files. Raw run logs captured
2026-07-28 from `--auto` runs on `dials-remote`.*
