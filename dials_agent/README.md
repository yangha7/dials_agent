# DIALS AI Agent (v2.2)

A natural language interface for DIALS (Diffraction Integration for Advanced Light Sources) crystallography data processing.

## Overview

The DIALS AI Agent allows users with less command-line experience to process crystallography data using natural language interactions. It translates user intent into appropriate DIALS commands, executes them with user approval, and provides human-readable summaries of the results.

## Features

- **Natural Language Interface**: Describe your data processing goals in plain English
- **Command Suggestions**: Get appropriate DIALS commands with explanations
- **Semi-Automated Workflow**: Commands require user approval before execution
- **Output Parsing**: Key metrics extracted and summarized in human-readable format
- **Workflow Tracking**: Automatic tracking of processing progress
- **Error Handling**: Troubleshooting suggestions for common problems
- **File Access**: Agent can directly read log files and open HTML reports
- **Visualization**: Integrated support for `dials.image_viewer` and `dials.reciprocal_lattice_viewer`
- **Multi-Provider LLM Support**: Works with CBORG, OpenAI, Google Gemini, and Anthropic Claude
- **MCP Server** *(v2.2)*: Exposes a curated subset of the agent's tools over the Model Context Protocol, so other agents (e.g. a future Phenix agent) can call directly into DIALS processing instead of only through the interactive CLI
- **Skills-Based Architecture** *(v2.0–2.1)*: Domain knowledge, tools, and handlers are organized into self-contained skills (spot finding, indexing, scaling, troubleshooting, etc.), each with its own `SKILL.md`, composed by a `SkillRegistry` with on-demand loading (`load_skill`) to keep the cached prompt small
- **Run Comparison** *(v1.3)*: Compare results from multiple processing runs (human vs agent, different parameters) with consistency assessment
- **PHIL Parameter Lookup** *(v1.2)*: On-demand access to complete parameter documentation for all 82 DIALS commands
- **Problem Diagnosis** *(v1.2)*: Intelligent troubleshooting with specific parameter-level fixes for 15+ common problems
- **62 Commands Known** *(v1.2)*: Comprehensive knowledge of workflow, utility, SSX, visualization, and format conversion commands

## Installation

### Quick Setup (Recommended)

```bash
cd dials_agent
chmod +x setup.sh
./setup.sh
```

This creates a virtual environment, installs all dependencies, and sets up the configuration file. Then:

```bash
source venv/bin/activate
python -m dials_agent.cli
```

### Manual Installation

1. Ensure you have Python 3.10+ installed
2. Install DIALS (https://dials.github.io/installation.html)
3. Create a virtual environment and install:

```bash
cd dials_agent
python3 -m venv venv
source venv/bin/activate
pip install -e .
```

> **Note**: On modern Debian/Ubuntu systems (12+/23.04+), you cannot `pip install` into the system Python due to [PEP 668](https://peps.python.org/pep-0668/). Always use a virtual environment or install into a conda environment.

### Installing into a DIALS Conda Environment

If DIALS is installed via conda, you can install the agent directly into the DIALS environment:

```bash
source /path/to/dials/dials_env.sh   # or: conda activate dials
cd dials_agent
pip install -e .
```

## Configuration

### Quick Start

1. Copy the example configuration file:

```bash
cp .env.example .env
```

2. Edit `.env` and set your API key (uncomment **one** of the options):

```bash
# For CBORG (LBL users):
CBORG_API_KEY=your-cborg-api-key-here

# For OpenAI:
# OPENAI_API_KEY=your-openai-api-key-here

# For Google Gemini:
# GEMINI_API_KEY=your-gemini-api-key-here

# For Anthropic Claude (direct):
# ANTHROPIC_API_KEY=your-anthropic-api-key-here
```

The agent **auto-detects** the provider from whichever API key is set. No need to specify `LLM_PROVIDER` unless you want to override the auto-detection.

### LLM Provider Options

| Provider | API Key Variable | Default Model | Default Max Output Tokens | Notes |
|----------|-----------------|---------------|---------------------------|-------|
| **CBORG** | `CBORG_API_KEY` | `anthropic/claude-sonnet` | 64000 | Recommended for LBL users |
| **OpenAI** | `OPENAI_API_KEY` | `gpt-4o` | 16384 | Direct OpenAI API — this is GPT-4o's actual ceiling, not a conservative choice |
| **Google Gemini** | `GEMINI_API_KEY` | `gemini-2.5-pro` | 16384 | Google's Gemini models — conservative default, may support more |
| **Anthropic** | `ANTHROPIC_API_KEY` | `claude-sonnet-4-20250514` | 64000 | Direct Anthropic API |

Max output tokens genuinely differ by provider — GPT-4o can't go higher than 16384 regardless, while Claude Sonnet 4/4.5 support up to 64K on the standard synchronous API (newer Sonnet generations up to 128K). Set `MAX_TOKENS` explicitly in `.env` only to go lower, or if you've confirmed your specific model supports more.

### Directory Configuration

Configure these in your `.env` file to customize where the agent looks for data and writes output:

| Variable | Description | Default |
|----------|-------------|---------|
| `DIALS_PATH` | Path to DIALS installation `bin/` directory | System PATH |
| `DATA_DIRECTORY` | Directory containing raw input data (images, HDF5, CBF) | (none) |
| `WORKING_DIRECTORY` | Directory where DIALS output files are written | Current directory |

Example:

```bash
DIALS_PATH=/path/to/dials/conda_base/bin/
DATA_DIRECTORY=/path/to/raw/data/
WORKING_DIRECTORY=/path/to/output/
```

If DIALS is already on your PATH (e.g., after running `source dials_env.sh`), you can leave `DIALS_PATH` empty.

### All Configuration Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `CBORG_API_KEY` | CBORG API key (LBL users) | - |
| `OPENAI_API_KEY` | OpenAI API key | - |
| `GEMINI_API_KEY` | Google Gemini API key | - |
| `ANTHROPIC_API_KEY` | Anthropic API key | - |
| `LLM_PROVIDER` | Force a specific provider (`cborg`/`openai`/`gemini`/`anthropic`) | Auto-detected |
| `MODEL` | Override the default model | Per-provider default |
| `LLM_BASE_URL` | Override the API base URL | Per-provider default |
| `MAX_TOKENS` | Maximum response tokens | Per-provider default (see below) |
| `DIALS_PATH` | Path to DIALS `bin/` directory | System PATH |
| `DATA_DIRECTORY` | Raw data directory | (none) |
| `WORKING_DIRECTORY` | Output directory | `.` |
| `COMMAND_TIMEOUT` | Command timeout in seconds | 3600 |
| `LOG_LEVEL` | Logging level | INFO |

### Backward Compatibility

If you have an existing `.env` file using the old `API_PROVIDER` and `OPENAI_BASE_URL` variables, they will continue to work. The agent automatically maps:
- `API_PROVIDER=openai` with a CBORG base URL → `cborg` provider
- `OPENAI_BASE_URL` → `LLM_BASE_URL`

## Usage

### Interactive CLI

Run the interactive command-line interface:

```bash
python -m dials_agent.cli
```

Or with a specific working directory:

```bash
python -m dials_agent.cli -d /path/to/output
```

### CLI Commands

- `help` - Show available commands
- `status` - Show current workflow status
- `history` - Show command history
- `auto` / `auto <message>` - Run the complete workflow unattended (see "Auto Mode" below for multi-dataset behavior)
- `compare <dir1> <dir2> [...]` - Compare results from multiple processing runs
- `clear` - Clear conversation history
- `cd <path>` - Change working directory
- `quit` / `exit` - Exit the agent

### Auto Mode

`auto` (or `--auto` on the command line) runs the complete workflow — import through
export — without stopping for confirmation. If `DATA_DIRECTORY` contains multiple
subdirectories that each look like an independent dataset (i.e. each has its own
diffraction data files), **every one of them is processed automatically, one at a time,
each into its own output subdirectory** — you don't need to run `auto` separately per
dataset. For example:

```
data/
├── insulin/       (image_0001.cbf, ...)
├── lysozyme/      (image_0001.h5, ...)
└── proteinaseK/   (image_0001.h5, ...)
```

with `DATA_DIRECTORY=data/` and `WORKING_DIRECTORY=/scratch/results/` produces:

```
/scratch/results/
├── insulin/       (imported.expt, ..., scaled.mtz)
├── lysozyme/
└── proteinaseK/
```

If you only want one specific dataset processed, name it in the request —
`auto process the lysozyme dataset` — and only that subdirectory runs. A flat data
directory (files directly in it, no subdirectories) behaves exactly as before: a single
dataset, processed into the configured working directory.

### Natural Language Examples

```
You: Import my images from /data/insulin
Agent: I suggest running: dials.import /data/insulin/*.cbf
       This will read your image headers and create an experiment file.
       Execute this command? [y/n]

You: Find spots with a higher threshold
Agent: I suggest running: dials.find_spots imported.expt spotfinder.threshold.dispersion.sigma_strong=6
       This will find strong spots using a higher threshold to reduce noise.
       Execute this command? [y/n]

You: What's the current unit cell?
Agent: Based on the indexed data, the unit cell is:
       a=37.2 Å, b=79.1 Å, c=79.3 Å
       α=90°, β=90°, γ=90°
       Space group: P212121

You: Why did indexing fail?
Agent: Indexing failed because no solution was found. This could be due to:
       1. Incorrect beam center
       2. Multiple lattices in the data
       3. Weak or sparse spots
       
       I suggest trying: dials.index imported.expt strong.refl indexing.method=fft1d
```

### MCP Server *(v2.2)*

For letting other agents (e.g. a future Phenix agent, or any orchestrator) call into this agent's tools directly, instead of only through the interactive CLI:

```bash
pip install "dials-agent[mcp]"   # or: pip install mcp
python -m dials_agent.mcp_server -d /path/to/output
```

This is a narrower, curated tool surface than the CLI — see the module docstring in [`dials_agent/mcp_server.py`](dials_agent/mcp_server.py) for exactly what's excluded and why (arbitrary shell execution, and the two tools whose UX only makes sense inside the CLI's own approve-then-execute loop). DIALS command execution is exposed as `execute_dials_command`, which runs immediately — an external agent's decision to call the tool over MCP is itself the approval, there's no separate confirmation step. Stdio transport only for now; `mcp`'s `streamable-http` transport is a natural next step if a caller needs to connect over the network rather than as a local subprocess.

## Project Structure

```
dials_agent/
├── __init__.py           # Package initialization
├── cli.py                # CLI interface (dispatches tool calls via SkillRegistry)
├── config.py             # Configuration settings
├── .env.example          # Example configuration file
├── requirements.txt      # Dependencies
├── core/
│   ├── __init__.py
│   ├── claude_client.py  # LLM API wrapper (multi-provider), composes prompt/tools from a SkillRegistry
│   ├── base_tools.py     # The 3 tools shared across all skills
│   ├── prompts.py        # Shared base system prompt
│   └── tools.py          # Shared utilities (data file discovery)
├── skills/                # Skills: modular domain knowledge, tools, and handlers
│   ├── __init__.py        # SkillRegistry + create_default_registry()
│   ├── base.py             # BaseSkill, SkillContext
│   ├── data_import.py      # dials.import
│   ├── spot_finding.py      # dials.find_spots
│   ├── indexing.py         # dials.index
│   ├── refinement.py       # dials.refine
│   ├── integration.py      # dials.integrate
│   ├── symmetry.py         # dials.symmetry / dials.cosym
│   ├── scaling.py          # dials.scale
│   ├── export.py           # dials.export / dials.merge
│   ├── troubleshooting.py  # diagnose_problem, suggest_troubleshooting
│   ├── workspace.py        # File access, shell commands, directory management
│   ├── phil_params.py       # PHIL parameter lookup
│   └── tutorials.py         # Guided tutorial walkthroughs
└── dials/
    ├── __init__.py
    ├── commands.py       # Command definitions
    ├── compare.py        # Run comparison tool
    ├── executor.py       # Command execution
    ├── parser.py         # Output parsing
    └── workflow.py       # Workflow state management
```

## DIALS Workflow

The standard DIALS processing workflow:

1. **Import** (`dials.import`) - Read image headers and create experiment file
2. **Spot Finding** (`dials.find_spots`) - Locate diffraction spots on images
3. **Indexing** (`dials.index`) - Assign Miller indices and determine unit cell
4. **Refinement** (`dials.refine`) - Improve crystal and detector models
5. **Integration** (`dials.integrate`) - Measure spot intensities
6. **Symmetry** (`dials.symmetry`/`dials.cosym`) - Determine space group
7. **Scaling** (`dials.scale`) - Apply corrections and scale data
8. **Export** (`dials.export`) - Output data for downstream analysis

## Deploying to Another Computer

### Unfamiliar Environment? Run the Pre-flight Check First

Before deploying to a machine you haven't used before — a new cluster, an
OOD/Slurm virtual desktop, an unfamiliar VM — run
[`scripts/preflight_check.sh`](scripts/preflight_check.sh). It's read-only
(makes no changes) and answers the questions that otherwise take several
rounds of trial and error:

```bash
curl -sO https://raw.githubusercontent.com/yangha7/dials_agent/main/scripts/preflight_check.sh
chmod +x preflight_check.sh
./preflight_check.sh
```

(Or, if you've already cloned the repo: `./dials_agent/scripts/preflight_check.sh`.)

It checks:
- **Ephemeral vs. stable host** — detects a Slurm/PBS-scheduled session (e.g.
  an OOD "Desktop" app job) and warns if the node itself will disappear when
  the job ends, so you know to install into a shared/persistent home
  directory rather than local scratch.
- **How DIALS is activated** — three patterns seen in practice:
  1. **Conda**, via `dials_env.sh` (see "Installing into a DIALS Conda
     Environment" below)
  2. **SBGrid** (or a module system) — `dials.*` commands are already on
     `PATH` with no separate activation script; leave `DIALS_PATH` blank
  3. **Not installed/activated** — needs `module load` / sourcing / install
     first
- **Network reachability** — GitHub (to clone), PyPI (to `pip install`), and
  your LLM provider's API endpoint (CBORG, Anthropic, etc.), since compute
  nodes on a cluster are sometimes NAT'd through restricted egress even when
  the browser-based session itself works fine.
- **Python 3.10+ with `venv`**, and `git`.

### Quick Deployment Steps

1. **Clone the repository**:
   ```bash
   git clone https://github.com/yangha7/dials_agent.git
   cd dials_agent/dials_agent
   ```

2. **Activate DIALS** on the target computer:
   ```bash
   source /path/to/dials/dials_env.sh
   ```

3. **Install the agent**:
   ```bash
   pip install -e .
   ```

4. **Configure** (copy and edit the example):
   ```bash
   cp .env.example .env
   # Edit .env with your API key and directory paths
   ```

5. **Run the agent**:
   ```bash
   python -m dials_agent.cli
   ```

### Alternative: Copy via SCP

```bash
# On source computer
scp -r dials_agent/ user@remote:/path/to/destination/

# On target computer
cd /path/to/destination/dials_agent
source /path/to/dials/dials_env.sh
pip install -e .
cp .env.example .env
# Edit .env with your settings
python -m dials_agent.cli
```

### Requirements

The target computer needs:
- Python 3.10+
- DIALS installed and in PATH (or set `DIALS_PATH` in `.env`)
- Internet access for API calls
- A valid API key (CBORG, OpenAI, Gemini, or Anthropic)

### Docker Container Deployment

For containerized deployment (DIALS must be installed on the host):

1. **Build the container**:
   ```bash
   cd dials_agent
   docker build -t dials-agent .
   ```

2. **Configure** (create `.env` with your API key):
   ```bash
   cp .env.example .env
   # Edit .env with your API key
   ```

3. **Run interactively**:
   ```bash
   docker run -it --rm \
     -v /path/to/dials/conda_base/bin:/opt/dials/bin:ro \
     -v /path/to/data:/data:ro \
     -v $(pwd)/output:/output \
     --env-file .env \
     dials-agent -d /output
   ```

4. **Run in auto mode**:
   ```bash
   docker run -it --rm \
     -v /path/to/dials/conda_base/bin:/opt/dials/bin:ro \
     -v /path/to/data:/data:ro \
     -v $(pwd)/output:/output \
     --env-file .env \
     dials-agent -d /output --auto
   ```

5. **Using docker-compose** (edit `docker-compose.yml` volume paths first):
   ```bash
   docker compose run --rm dials-agent
   ```

#### Volume Mounts

| Mount | Purpose | Mode |
|-------|---------|------|
| `/opt/dials/bin` | DIALS binaries from host | Read-only |
| `/data` | Raw diffraction data | Read-only |
| `/output` | DIALS processing output | Read-write |

#### Container Requirements

- Docker 20.10+ or Podman
- DIALS installed on the host system
- Internet access for LLM API calls

## Comparing Runs

The comparison feature lets you compare results from multiple DIALS processing runs to assess consistency. This is useful for:

- **Human vs Agent**: Verify the agent produces results comparable to expert processing
- **Parameter Tuning**: Compare runs with different parameters to find optimal settings
- **Reproducibility**: Check that repeated runs produce consistent results

### From the Command Line

```bash
# Compare two directories
dials-agent --compare run_agent/ run_human/

# With custom labels
dials-agent --compare run1/ run2/ run3/ --compare-labels "agent,human,v2"

# Save report to JSON
dials-agent --compare run1/ run2/ --compare-output comparison_report.json
```

### From the Interactive CLI

```
You: compare run_agent run_human
```

Or with options:

```
You: compare run_agent run_human --labels agent,human --output report.json
```

### What Gets Compared

The tool extracts and compares these metrics from each run's log files:

| Category | Metrics |
|----------|---------|
| **Spot Finding** | Number of spots found |
| **Indexing** | Indexed reflections, unit cell, space group, RMSD |
| **Integration** | Number of integrated reflections |
| **Scaling** | Resolution, completeness, multiplicity, Rmerge, Rmeas, Rpim, CC1/2, I/σ(I) |
| **Timing** | Per-step and total processing time |
| **Workflow** | Completion status, final stage |

### Consistency Assessment

Each metric is assessed as:
- **✓ consistent** — Values agree within expected tolerance
- **~ close** — Minor differences (within acceptable range)
- **✗ differs** — Significant differences that warrant investigation

Tolerances are metric-specific:
- Spot/reflection counts: 5% relative variation
- Resolution: 0.1 Å absolute
- R-values: 10% relative variation
- CC1/2: 0.005 absolute
- Completeness: 1% absolute
- Timing: 20% relative variation

### JSON Report Format

The `--compare-output` flag saves a structured JSON report:

```json
{
  "num_runs": 2,
  "labels": ["agent", "human"],
  "directories": ["/path/to/run1", "/path/to/run2"],
  "metrics": {
    "Spots Found": [25000, 24800],
    "Space Group": ["P213", "P213"],
    "CC1/2": [0.998, 0.997]
  },
  "consistency": {
    "Spots Found": "consistent",
    "Space Group": "consistent",
    "CC1/2": "consistent"
  },
  "summary": "..."
}
```

## Development

### Running Tests

```bash
pytest tests/
```

### Code Formatting

```bash
black dials_agent/
ruff check dials_agent/
```

## License

This project is part of the DIALS software suite.

### v2.11.1 — Fix a Confusing Dead End: a Chained Command Suggestion Was Silently Dropped in Interactive Mode
- **Found live**: after `dials.find_spots` completed, the agent's result-analysis response proactively suggested `dials.index` next (exactly the behavior this project encourages) — but no "Suggested Command"/y/n approval panel appeared for it. The agent's text just said "Ready to run when you are — let me know," with nothing actually pending to approve. Typing `y` went to the LLM as an ordinary chat message (not a confirmation, since nothing was waiting), producing another dead-end reply ("Go ahead — the command should now execute") with nothing actually executing
- **Root cause**: `run_interactive()`'s `if self.pending_command:` block ran the approved command, then fed its output back to the LLM via a *nested* `self.chat()` call for analysis. If that nested call itself called `suggest_dials_command` for the next step, it correctly set a new `self.pending_command` — which then got unconditionally overwritten back to `None` immediately after the block, regardless of what the nested call had just set. The "Next Step" panel the user saw was a separate, purely-informational display hint (`display_next_step_suggestion()`, never sent to the LLM) — unrelated to, and not a substitute for, the actual suggestion that got silently dropped
- Fixed by restructuring to a `while self.pending_command:` loop that consumes (clears) the command immediately before acting on it, so a freshly re-set suggestion from the nested analysis call survives to be picked up on the next loop check instead of being wiped afterward — commands now chain naturally within a single turn, each still getting its own explicit y/n approval, exactly matching `run_auto()`'s (already-correct, differently-structured) chaining behavior
- 186 tests (1 new regression test simulating the exact live scenario via mocked `chat()`/`executor.execute()`/`Confirm.ask()`/`input()` calls — confirmed it fails against the old code and passes against the fix, not just passing by construction)

### v2.11.0 — New Numeric Check: Import Geometry Sanity (Beam Centre/Distance/Wavelength/Oscillation)
- **User request**: also numerically check the raw images after import, the same way `reciprocal_lattice_linearity.py` checks reciprocal-space geometry after indexing — the agent can't see `dials.image_viewer`'s rendered output either
- **Scoped deliberately to header/geometry only, not pixel content**, after estimating cost for both: this check reads only `imported.expt`'s beam/detector/scan *models* (`check_format=False`, no image files touched at all), so its cost is fixed (~1.2s measured locally, dominated by dxtbx import startup) regardless of dataset size. A pixel-content check (saturation, hot pixels, background, real spot presence) would need to actually read image data, so its cost *does* scale with dataset size unless deliberately sampled — flagged in both the code and guidance as a known, explicitly not-yet-built follow-up, not started here
- New `dials/scripts/import_geometry_check.py`: checks whether the direct beam lands on any detector panel (in pixel coordinates — discovered and worked around a real dxtbx pitfall during validation: `Panel.is_coord_valid()` does not reliably bounds-check against the panel's physical extent, confirmed empirically returning `True` for a coordinate far outside it; computing pixel coordinates via `get_beam_centre_px()` and comparing directly against `get_image_size()` is the correct, verified approach), wavelength within a broad plausible X-ray range, detector distance within a broad plausible range, oscillation width non-zero on genuine rotation scans (correctly not flagged for stills, where a `None`/zero-width scan is legitimate), and the best achievable resolution at any panel's farthest corner (advisory only). Validated against real dxtbx model objects (via the local DIALS build's own Python, not guessed) for a clean case and every flagged case individually, plus the stills (`scan=None`) case
- Wired into `core/prompts.py` (new `_get_import_geometry_check_note()`, alongside the other two) and `data_import/SKILL.md`'s "After Import" section: runs automatically right after `dials.import` succeeds, before suggesting `dials.find_spots` — same "don't wait to be asked" pattern as the other two checks, and same "flagged → pause and propose the fix" vs. "clean → note briefly and proceed" split as indexing/refinement's geometry check
- 185 tests (extended `test_standard_workflow_integration.py`'s full mocked pipeline to include this as a 12th step, catching and fixing 4 now-stale hardcoded step-index/stage-sequence assumptions in the process — the new script itself isn't unit-tested in the plain suite, same as `reciprocal_lattice_linearity.py`, since dxtbx isn't available there; validated manually instead, as documented in this entry). System prompt now ~5.4K tokens — a reasonable, deliberate increase past the earlier ~5.3K target for a genuine third numeric check, not tightened further

### v2.10.5 — Visualization Offers: Mention and Move On, Not Ask and Wait; Excluded Only Where Genuinely Not Useful Yet
- **User request**: after each processing step, mention `dials.image_viewer`/`dials.reciprocal_lattice_viewer` as available on that step's output, but default to proceeding to the next step rather than blocking on the answer — reflected in interactive mode, skipped entirely in auto mode (already true — `run_auto`'s instruction already excludes GUI commands, rule 2, unchanged here)
- Converted every stage's visualization guidance (`data_import`, `spot_finding`, `indexing`, `refinement`, `integration`, `symmetry`) from "ask and wait" to "mention, then default to the next command in the same message" — matching the CPU-cores pattern (v2.10.4), not the full-vs-subset pattern (v2.10.2), since visualization here is genuinely optional context, not a workflow decision. Kept indexing/refinement's *flagged* (bent/spiral geometry) case as a deliberate pause rather than defaulting onward — proceeding to the next step on bad geometry usually just wastes it
- **Corrected mid-edit from direct user feedback**: initially over-applied "not after import" to both viewers; `dials.image_viewer` is genuinely useful right after import (beam center/detector distance/image quality) — only `dials.reciprocal_lattice_viewer` needs indexed data and stays excluded until after indexing
- `scaling`/`export` untouched — their existing guidance already correctly says neither viewer applies there (merged-intensity statistics and MTZ output respectively, not per-image geometry)
- 185 tests, all still passing (guidance-text only; trimmed wording to keep the system prompt at ~5.21K tokens, comfortably under the ~5.3K budget after this touched six files)

### v2.10.4 — CPU Core Count Defaults to Auto with an Override, Unlike the Full-vs-Subset Choice
- **User request**: for the spot-finding/integration CPU-core-count decision specifically, default to `nproc=Auto` and suggest the command directly, naming the override in the same message — the opposite pattern from the full-vs-subset import choice (v2.10.2), which stays a genuine ask-and-wait
- This is a deliberate, requested asymmetry, not a contradiction: full-vs-subset is a workflow choice with real downstream consequences worth deliberating; CPU core count is a pure performance knob where "Auto" is always a safe, non-mysterious default. `core/prompts.py`'s "Parallel Computing Options" updated accordingly; "Offering Options to Users" (the full-vs-subset guidance) untouched
- 185 tests, all still passing (guidance-text only; system prompt ~5.16K tokens, within the ~5.3K budget)

### v2.10.3 — Number Options for Fast Reply, Always Keep a Custom-Command Escape Hatch
- **User request**: when offering multiple-choice options (e.g. full vs. quick import), number them so the user can reply with just a digit instead of retyping the choice — a small but real friction reducer for the workshop's non-technical attendees — while always keeping an explicit way to type an exact custom command instead of picking from the list
- Added to `core/prompts.py`'s "Offering Options to Users" (general rule, applies to any options the agent presents, not just import) and updated `data_import/SKILL.md`'s worked example to `1. .../2. ...` with "Reply with 1 or 2, or tell me exactly what you'd like to run instead."
- 185 tests, all still passing (guidance-text only; system prompt ~5.1K tokens, within the ~5.3K budget)

### v2.10.2 — Revert v2.10.1: the User Wanted the Real Two-Turn Ask-Then-Suggest Back
- **Direct user correction, twice**: v2.10.1's "default + one-line override in the same message" redesign was a misread of the actual request. The user explicitly wants the older, genuine two-turn behavior — ask "quick or full?" as a real question, wait, then suggest the one command matching the answer — not a command suggested immediately with the alternative mentioned as a footnote
- Root cause of the *original* bug (asking AND suggesting a specific command in the same turn) turned out to be self-inflicted: v2.10.1's own `data_import/SKILL.md` text explicitly told the model "call `suggest_dials_command` ... in this same response — don't split ... across two separate turns", so the observed behavior after that fix was the model correctly following the (wrong) instruction just written, not a reliability failure
- Reverted `core/prompts.py`'s "Offering Options to Users" and "Parallel Computing Options" sections and `data_import/SKILL.md`'s import-options text back to genuine ask-then-wait, with a stronger negative example than the original (pre-v2.10.1) wording had, naming both failed framings explicitly (bare suggestion, or dressed up as a default) so a future variant of the same mistake is easier to recognize and avoid
- 185 tests, all still passing (guidance-text only; system prompt ~5.0K tokens, within budget)

### v2.10.1 — Stop Asking a Question and Suggesting a Command for It in the Same Confusing Turn
- **Found live, on the same Insulin dataset**: the agent presented "quick vs. full processing" and "how many CPU cores" as open questions to answer, then *immediately* suggested one specific `dials.import` command anyway (implicitly the full-dataset default) — a confusing turn with an unresolved question sitting right next to a y/n approval prompt. The base prompt already had an instruction against this ("do NOT use suggest_dials_command until the user has chosen"), which the model violated anyway — re-asserting the same instruction wasn't likely to be much more reliable, since it had already failed once
- **Fixed the failure mode structurally instead of just re-stating the rule**: reframed from "ask an open question, then wait" to "pick the sensible default, suggest that command directly, and name the alternative as a one-line override in the same message" (e.g. "I'll import the full dataset below — say `image_range=1,1200` before approving if you'd rather test with a subset"). This removes the two-step ask-then-wait structure the model wasn't reliably respecting, collapsing it into one coherent turn — and matches what a first-time, non-Linux user actually wants better anyway: a sensible thing happens by default, with an easy way to redirect, rather than an open question they may not know how to answer
- Also fixed: the CPU-core-count question (correctly scoped to `find_spots`/`integrate` in the prompt) got front-loaded into the unrelated `dials.import` step anyway — now explicit that it only belongs in the message that's actually suggesting `find_spots`/`integrate`. `data_import/SKILL.md`'s "present two options, wait" example, which directly contradicted the new base-prompt guidance, rewritten to match
- Reserved the genuine blocking-question case (no default exists, e.g. data location truly unknown) as the one place asking-and-waiting still applies
- 185 tests, all still passing (guidance-text-only change; trimmed elsewhere to keep the system prompt at ~5.0K tokens, back under the ~5.3K budget after this addition pushed it to ~5.24K)

### v2.10.0 — New `select_dataset` Tool: Reliable Dataset Lookup by Name, for Non-Technical Users
- **Prompted directly by the user's stated goal**: this dataset (Insulin, sitting alongside DPF3) will be the first thing most workshop attendees ever touch, many with no Linux experience — the agent must reliably find a dataset the user names in plain language, without the user needing to know exact paths or specific tool names
- **The gap v2.9.5 didn't close**: that fix only helped literal `auto process...` messages, which go through `run_auto()`'s Python-level multi-dataset discovery. A normal conversational message ("please process the insulin data") has no equivalent structured mechanism — the LLM was left to invent its own `run_shell_command`/`find` search each time, which is exactly what failed live (a `find -iname "*ins*"` came back empty for a directory that demonstrably exists, most likely due to directory-listing caching on the shared NFS filesystem — a shell search over a live filesystem is far more exposed to that than a direct path check)
- Added `select_dataset` (new tool, `data_import` skill): takes an optional `name_hint`, matches it case-insensitively against dataset subdirectories found via the same tested `discover_dataset_subdirectories()` used by auto mode (extracted to `core/tools.py` so this can never diverge into a second, un-synced copy again — the exact class of bug fixed in v2.9.5), and switches to it automatically on an unambiguous match. Returns the real list of datasets found on `no_match`/`ambiguous`/`listed`, never a bare "not found" when other data is sitting right there. The tool's own description tells the LLM to call this *first*, before reaching for a shell search, whenever a user names a dataset — and since tool schemas (unlike SKILL.md prose) are always visible from the very first turn regardless of progressive disclosure, this applies from a user's very first message, not just once a skill has been explicitly loaded
- Wired into `cli.py` (applies the directory switch on `status: "selected"`, mirroring `change_data_directory`) and `mcp_server.py` (same wiring, plus updated the server's explicit tool allowlist — which caught this immediately by design, exactly the kind of safety net that should exist for a project-wide tool addition)
- 185 tests (6 new for `select_dataset`, covering the exact DPF3+Insulin scenario plus ambiguous/no-match/empty cases)

### v2.9.5 — Multi-Dataset Discovery Couldn't See Compressed-Image-Only Directories
- **Found live**: on a fresh, new workshop machine session, `auto process the insulin data` against a data directory containing sibling `DPF3/` and `Insulin/` subdirectories (both `.img.bz2`-only) failed to discover either as a valid dataset. The agent's conversational (pre-auto) response correctly identified real DPF3 filenames, but claimed "no insulin dataset available" — wrong, `Insulin/` clearly existed. Once auto mode engaged, it fell back to single-dataset mode (since discovery found 0, not 2, qualifying subdirectories) and suggested a `dials.import` command pointing at a fabricated-looking path that matched neither the real `DPF3/` nor `Insulin/` location
- **Root cause**: `cli.py`'s `_directory_has_data_files()` (used only by the v2.4.0 multi-dataset discovery feature) duplicated, rather than reused, the compressed-file-aware logic already fixed in `core/tools.py`'s `is_recognized_data_file()` back in v2.5.2. It checked `item.suffix.lower() in DATA_FILE_EXTENSIONS` directly — and `Path.suffix` on `t1.0001.img.bz2` returns only `.bz2`, never in that set — so any directory containing exclusively compressed images was invisible to discovery. All 16 existing multi-dataset tests used `.cbf`/`.h5` fixtures, never a compressed extension, so this divergence had no test coverage
- Fixed: `_directory_has_data_files()` now calls the shared `is_recognized_data_file()` helper instead of its own diverged copy — one code path, not two. Added 2 regression tests reproducing the exact scenario (a compressed-only directory; a `DPF3`+`Insulin` pair both using `.img.bz2`). 179 tests (2 new)

### v2.9.4 — `--verify-centering` is Decisive Evidence on Its Own; the Base Alternation Check Can Be Blind to a Real Signal It Misses
- **Found live, minutes after v2.9.3 shipped, on the same DPF3 part 2 `v4` re-test**: sent the agent an explicit prompt to actively test a centred hypothesis (per v2.9.3's fix). It pushed back with a legitimate, correct geometric argument (a simple doubled-cell C/A/B/I description requires two or three primitive axis lengths to be exactly equal — verified sound crystallography — and this dataset's refined cell has none close), then ran `--verify-centering` directly on the as-indexed data anyway. The result: the base (non-named) alternation check found nothing on any axis (consistent with v2.9.3's finding), but `--verify-centering`'s direct test of the 'A' condition found an unambiguous, massive signal — 425,004 forbidden reflections with mean I/sigma(I) = 0.15, the same quality of evidence as dials.symmetry's own screw-axis absences
- **Investigated whether this is a bug in the base check** (it reports "clean" on data that has an obvious, decisive named-condition signal) by reproducing with synthetic data twice — once idealized, once with per-reflection noise matched to this dataset's actual reported I/sigma(I) levels. Both reproductions correctly detected a comparable planted signal with huge variance ratios (55-500×), confirming the base check's algorithm is not simply broken; real datasets can apparently have reciprocal-space coverage geometry (bounded by a resolution sphere, uneven under the row-selection cap) that suppresses its specific row-level statistical test even when a direct, pooled-by-parity test finds an obvious answer. Root cause of the *coverage* effect itself not fully pinned down — noted as an open question, not asserted as solved
- **Fixed the guidance, not the algorithm** (since the algorithm isn't wrong, just lower-powered on some real data than initially assumed): `--verify-centering` is no longer framed as an optional add-on for after reindexing or after the base check flags something — it's now always run alongside the base check, unconditionally, in `core/prompts.py`'s default suggested command and both SKILL.md files. A large, clean named-condition result (near-zero I/sigma(I) across a big, ~balanced-split population) is now explicitly called out as decisive evidence on its own, not something requiring a `refine_bravais_settings` centred candidate or prior reindexing to trust
- 177 tests, all still passing (guidance-text-only change; system prompt now ~4.9K tokens, still within the ~5.3K progressive-disclosure budget but getting closer — worth watching on future additions)

### v2.9.3 — Fix a Real Wrong Conclusion (Again): a Clean Numeric-Check Result on Unreindexed Data Isn't Evidence of "No Centring"
- **Found live, on a fresh `v4` copy of the DPF3 part 2 dataset, specifically to test whether v2.6.0/v2.7.0's earlier guidance held up**: it didn't, fully — the agent reached the same wrong "genuinely primitive, no centring" conclusion as the original v2.6.0 incident, but through a new route rather than the one already guarded against
- **The gap**: the agent correctly ran `centring_vs_pseudocentring_check.py` on `integrated.refl`, got a clean result (variance ratios ~1.05-1.07, no axis flagged), and combined it with `dials.symmetry`'s decisive P2₁2₁2₁ screw-axis call to conclude "not centred" — reasonably, given what the existing guidance said. But that check tests parity of h,k,l *as originally indexed* — exactly the same blind spot documented for `dials.refine_bravais_settings`'s subgroup-only limitation: it can only detect a centering condition that's already a simple parity rule in the current labeling. The real DPF3 tutorial's actual centred-hypothesis reindex (`change_of_basis_op=-b,c,-a`) is a genuine axis permutation, not a relabeling — so the true centering vector isn't expressible as simple h+k/h+l/k+l/h+k+l parity until *after* that transform. A clean result on the untransformed data is therefore uninformative, not reassuring, but the guidance only ever said what to do "if it flags an axis" — the "if nothing is flagged, just note briefly ... and move on" instruction was itself the bug, never warning that a null result needs the same skepticism as an all-primitive Bravais list
- Fixed in both `core/prompts.py`'s centring-check note and `symmetry/SKILL.md`: a clean check on unreindexed data is now explicitly called out as uninformative, and the agent is instructed to check whether the point group found is even compatible with additional centering, and if so, to actively reindex toward at least one plausible centred hypothesis and re-test before concluding primitive — a clean result only counts as evidence *after* actively testing a hypothesis, not from an unprompted null result
- 177 tests, all still passing (guidance-text-only change; system prompt checked at ~4.5K tokens, within budget)

### v2.9.2 — Codify the Zero-Variance Weighting Fix as General Troubleshooting Knowledge
- **Prompted by explicit user pushback** on v2.9.1's framing: "The tutorial did not mention it does not mean it does not exist. I believe we should keep that." Correct — the fact that neither DPF3 tutorial documents the `DialsRefineConfigError: Cannot set statistical weights...` error doesn't mean it's not a real, recurring DIALS failure mode worth the agent knowing about; it just means this specific fix came from first principles/PHIL docs rather than a tutorial. Not codifying it anywhere would mean every future user hits the exact same wall a human had to solve manually this time
- Added as a new `zero_variance_weights` entry in `skills/troubleshooting/__init__.py`'s `PROBLEM_SOLUTIONS` (stage: refine) with matching `_KEYWORD_MAP` entries (`"statistical weight"`, `"variances equal to zero"`, `"zero variance"`, `"dialsrefineconfigerror"`), so `diagnose_problem` surfaces `refinement.reflections.weighting_strategy.override=constant` directly from the actual DIALS error text
- Also added the same fix to `dials.refine_bravais_settings`'s `CommandDefinition` description (alongside its existing "only finds subgroups" warning) and to `symmetry/SKILL.md`'s reindex/centring sequence, so it surfaces regardless of which path the agent takes to it
- 177 tests (1 new: `test_diagnose_problem_finds_zero_variance_weighting_fix`)

### v2.9.1 — Add the Missing Diagnostic Step for Beam-Centre Problems: `dials.check_indexing_symmetry`
- **Found by checking the actual tutorial pages directly** rather than relying on memory, prompted by the user asking whether the agent's approach to a live troubleshooting session matched the official DIALS tutorials. Fetched both DPF3 tutorials (Part 1 "Correcting Poor Initial Geometry" and Part 2 "A Question of Centring") and compared their real command sequences against our guidance
- **Gap found**: existing guidance (in `troubleshooting`'s `multiple_lattices`/`refinement_failed` entries, `indexing`/`refinement` SKILL.md, and the base-prompt geometry-check note) jumps straight from "looks like multiple lattices / unstable refinement" to "try `dials.search_beam_position`" — but the tutorial's actual sequence inserts `dials.check_indexing_symmetry indexed.expt indexed.refl` first, as a cheap, concrete diagnostic: a systematic index offset (e.g. `delta_h=1, delta_k=1, delta_l=1`) *confirms* the problem is a bad beam centre before spending time re-indexing, rather than just guessing. The command itself was already registered in `dials/commands.py` (so the agent could always run it if asked) but never appeared anywhere in the guidance that leads the agent toward suggesting a beam-centre fix in the first place — the same class of gap as the v2.3.0 `search_beam_position` fix, one diagnostic step earlier in the chain
- Fixed: added `dials.check_indexing_symmetry` as the recommended first step, before `dials.search_beam_position`, in all four guidance locations, plus enriched its thin `CommandDefinition` description (previously just "Check the indexing symmetry of indexed reflections") to explain what the diagnostic signature actually means
- Also confirmed and documented (not changed in code, just worth recording): the Part 2 tutorial's real reindex sequence is `dials.reindex bravais_setting_N.expt indexed.refl space_group=<centred>` → re-run `dials.refine_bravais_settings` → a further axis-permutation `dials.reindex ... change_of_basis_op=...` to reach the canonical centred setting — matching what v2.6.0/v2.7.0's guidance already describes. Also confirmed the tutorial's decisive R-cryst/R-free numbers (0.18/0.21 centred vs. 0.27/0.29 primitive) come from real structure refinement against a model (e.g. `phenix.refine`), not from `dials.scale`/`dials.merge` statistics alone — the `--verify-centering` numeric check and merging stats are a good proxy but not literally the same benchmark; worth not overclaiming equivalence
- 176 tests, all still passing (guidance/prompt text changes only, no new automated tests — verified system prompt token size stayed within budget, ~4.1K tokens)

### v2.9.0 — Fix `lookup_phil_params`'s Primary Source Never Shipping to Any Deployed Copy
- **Found live, from a direct user question** ("The agent should know all the phil thing already, correct?") after the agent needed a `dials.refine_bravais_settings` fix (`weighting_strategy.override=constant`) that a human had to look up manually instead of the agent finding it itself
- **Root cause, precisely**: `lookup_phil_params` checks two sources in order, both of which lived in a `docs/` directory *one level above* `dials_agent/` in this repo — outside the package. (1) `docs/phil_params/*.txt` — 84 machine-generated PHIL dumps (`dials.program -c -e2 -a2`), the preferred/richest source — was never committed to git at all (confirmed untracked, not gitignored, just never `git add`-ed), so it never shipped to *any* deployed copy, via either `git clone` (sbcloud) or `sync_to_remote.sh` (dials.lbl.gov, which only rsyncs the `dials_agent/` subtree). (2) `docs/programs/*.md` — 35 human-readable fallback docs — *was* already committed and pushed, so it *was* present on the sbcloud git clone at the old path (just never on dials.lbl.gov, since rsync's scope excludes the outer `docs/` regardless of git status). So the sbcloud agent likely could have found this specific parameter via the fallback path if it had called `lookup_phil_params` for it — the `.txt` gap is the confirmed universal failure; whether the `.md` fallback was actually consulted in that live session is unconfirmed
- Fixed: moved both directories (plus the `fetch_phil_params.sh` regeneration script) to `dials_agent/docs/phil_params/` and `dials_agent/docs/programs/`, i.e. *inside* the package, so one fix covers both deployment paths without depending on which files happen to already be tracked. Updated `_DOCS_ROOT` in `skills/phil_params/__init__.py` from 4 `.parent` calls to 3 to match
- Added a regression test (`test_phil_params_docs_ship_inside_the_package`) asserting the docs directories resolve to somewhere inside the package and actually contain files, plus a real-lookup test for the exact `weighting_strategy` parameter that triggered this investigation — neither would have passed against the old broken layout

### v2.8.0 — Fix a Real Selection-Bias Bug in the Centring Check Itself
- **Found live, from the agent's own follow-up investigation**: `centring_vs_pseudocentring_check.py` filtered reflections to the `indexed` flag before any intensity analysis — the same choice `reciprocal_lattice_linearity.py` makes, which is fine for *that* script's position-based geometry check, but wrong here. `indexed` marks the original strong-spot list used for orientation during `dials.index` — a subset inherently biased toward *strong* reflections, since that's how spot-finding/indexing selects candidates in the first place. Systematic absences are, by definition, weak, so filtering an intensity-based absence test to the indexed subset systematically under-samples exactly the reflections the test exists to characterize
- **Validated with a real `flex.reflection_table`, not just reasoning about it**: built a synthetic case with a genuine systematic absence (I/sigma(I) ≈ 0 for the forbidden class across the full population) where only the top 15% by raw intensity carry the `indexed` flag. The old selection found **zero** forbidden-class reflections at all — not weaker evidence, complete blindness to the axis. The fix correctly recovers the full, balanced population and the true near-zero signal
- Fixed: select on `integrated_prf`/`integrated_sum` (matching whichever intensity column is in use) instead of `indexed`, with a fallback to `indexed` only if the file predates `dials.integrate` (so the documented pre-integration mode still works rather than silently analyzing zero reflections). `n_indexed_reflections` renamed to `n_analyzed_reflections` in the output to match
- Not unit-testable in the plain test suite (`main()` needs a real DIALS environment, per the module's own docstring) — validated manually via `cctbx.python` instead, same as the script's original development

### v2.7.4 — Per-Provider MAX_TOKENS Defaults (64K for Claude, Not a Shared Global 16384)
- **Prompted directly by the v2.7.3 truncation bug**: raising the old single global default (16384, shared across all four providers) isn't safe to do blindly — GPT-4o's actual output-token ceiling genuinely IS 16384 (raising it further just causes API errors, doesn't help), while Claude Sonnet 4/4.5 (what `cborg`/`anthropic` resolve to here) support up to 64K on the standard synchronous API. One global number can't be both "high enough for Claude" and "not exceed OpenAI's real ceiling"
- `config.py`'s `max_tokens` field now defaults to `0` (sentinel for "use the provider default"); new `DEFAULT_MAX_TOKENS` dict (matching the existing `DEFAULT_MODELS`/`DEFAULT_BASE_URLS` pattern) and `get_resolved_max_tokens()` resolve it per-provider: 64000 for cborg/anthropic, 16384 (unchanged) for openai/gemini. `MAX_TOKENS` in `.env` still overrides explicitly when set. Also fixed a stale discrepancy in the README/`.env.example` docs (previously claimed the default was 4096, when the code had already been at 16384)
- No `.env` edit needed to pick this up for CBORG/Anthropic users — pulling the update alone raises the effective default from 16384 to 64000 automatically; only set `MAX_TOKENS` explicitly to go lower, or higher still if you've confirmed your specific model supports it (newer Claude Sonnet generations support up to 128K)
- 7 new tests (`tests/test_config.py`) — 174 total, up from 167

### v2.7.3 — Surface Silently-Truncated (MAX_TOKENS-Cut-Off) Turns
- **Real bug, found live**: after a long, context-heavy turn, the CLI printed the token-usage line (`19,186 in / 16,384 out`) — output tokens exactly equal to the configured `MAX_TOKENS` — and then nothing else at all: no "Agent" header, no text, no next step, straight back to the `You:` prompt, despite a full-price, maximum-length API call having just run. `AgentResponse.stop_reason` was captured on every response (`"length"` for OpenAI-compatible providers, `"max_tokens"` for native Anthropic) but never actually checked anywhere in the codebase — a response cut off by the token limit with no visible text and no tool call in its final round just silently produced nothing, with no indication anything had gone wrong
- Fixed: `DIALSAgent._warn_if_response_truncated()` now checks `stop_reason` after every turn (both interactive and auto mode, since both go through the same `chat()` method) and prints a clear warning — a loud one naming the actual cause when the turn produced nothing at all, a lighter note when it produced partial text/a tool call that may just be incomplete. No automatic retry (deliberately — an automatic retry loop could itself compound token costs unpredictably); the fix is making the failure visible and actionable, not silently invisible
- 5 new tests — 167 total, up from 162

### v2.7.2 — Stop Repeating "Workflow Complete!" After Every Unrelated Command
- **Real bug, noticed live mid-session**: `display_result()` unconditionally shows the "🎉 Workflow Complete!" banner after every successful command, purely from checking whether a `.mtz` file exists anywhere in the working directory. That's correct the *first* time a run genuinely finishes, but confusing (and it was confusing) when resuming in a directory copied from a prior finished run for further investigation (e.g. the v2/v3 centring-investigation directories, which start with `scaled.mtz`/`merged.mtz` already present) — every single subsequent command, including read-only diagnostic scripts with nothing to do with finishing anything, re-announced "workflow complete"
- Fixed narrowly: `execute_command()` now snapshots whether the workflow was already complete *before* the command ran; `display_result()` only shows the automatic completion banner if this specific command was the one that just finished it. The explicit `next` command (asked for directly) is untouched — it still reports completion on request regardless
- 3 new tests — 162 total, up from 159

### v2.7.1 — End-to-End Standard-Workflow Integration Test + Two More Display Polish Fixes
- **New `tests/test_standard_workflow_integration.py`**: drives the real `execute_command`/`display_result`/`display_command_suggestion`/`display_timing_summary`/`display_workflow_status` code and the real, file-based `WorkflowManager` stage detection through a full mocked import-through-merge pipeline (including both numeric checks invoked exactly as the base prompt tells the LLM to invoke them), with no real DIALS install or LLM calls needed. Exists specifically to catch the class of bug recent fixes were for — things only visible in the actual rendered text of a full run, not in isolated unit tests of individual functions
- **Two more truncation-adjacent issues found by actually reading the rendered output**: the per-command `"Executing: ..."` line and the pre-approval `"Suggested Command"` panel were both still printing `dials.python`'s raw absolute script path — unlike the summary tables (fixed in v2.5.3), and Rich's default text wrapping breaks a long path with no spaces mid-word (`reciprocal_la` / `ttice_linearity.py`) rather than at a clean word boundary. Both now use the same `_display_command_label()` shortening as the tables — display-only, the real full command is still what actually executes
- 7 new tests — 159 total, up from 152

### v2.7.0 — Fix the "Still Pending" Approval Loop + Harden the Centring Follow-up
- **Real bug, found live-testing the corrected v2.6.0 sequence**: the LLM sometimes called `suggest_dials_command` twice within one turn ("Both commands are awaiting your approval..."). `DIALSAgent.pending_command` is a single field, not a queue — the second call silently overwrote the first. The CLI would only ever confirm/run the second command, while the LLM (having received a `"pending_approval"` acknowledgment for the first call too) kept believing both were still awaiting approval on later turns, producing a repeating "still pending on my end, please confirm" loop that burned real turns and tokens (one live session reached several million tokens partly because of this) for zero benefit. `_handle_tool_call` now rejects a second `suggest_dials_command` while one is already pending, with a clear error telling the LLM to wait for the first one's real result instead of silently discarding it
- **Two more real mistakes found in that same session, now guarded against explicitly**: (1) `dials.reindex ... space_group="C 2 2 21"` with no change-of-basis operator (or the identity `change_of_basis_op=a,b,c`) only relabels the space group symbol — it does not transform the Miller indices, producing a flat, meaningless test result. Guidance (`symmetry/SKILL.md`, `core/prompts.py`) now explicitly says to use `reference.experiments=bravais_setting_N.expt` (the actual re-refined candidate) or an explicit non-identity cb_op instead. (2) The agent wrote ad hoc verification scripts on the fly to test specific centering conditions directly against intensities, and got the masking wrong (built `even_mask`/`odd_mask` correctly but then computed both group means from the *unmasked* array, silently comparing the data against itself)
- **New `--verify-centering` mode** on `centring_vs_pseudocentring_check.py`: `test_named_centering_condition()`/`verify_all_centerings()` directly test all four named centering conditions (A/B/C/I) against real intensities, replacing the need for the agent to write untested one-off code for exactly this follow-up question. Guidance now points at this instead
- 7 new tests (1 for the pending-command fix, 6 for the new centering-verification functions, including one specifically shaped to catch the exact unmasked-mean bug found live) — 152 total, up from 145

### v2.6.0 — Fix a Real Wrong Conclusion in the Centring vs. Pseudo-centring Check
- **Found live-testing the actual DPF3 "Centring vs. Pseudo-centring" tutorial dataset, not a hypothetical**: the agent correctly detected the intensity alternation along c*, but concluded "pseudo-centring, stay primitive" — the *opposite* of the tutorial's own answer (a genuine C222₁ centred setting, R-cryst 0.18/R-free 0.21 vs. 0.27/0.29 for primitive). Root cause, confirmed against the actual `dials.refine_bravais_settings` output from that session: the agent ran it on the *original, untransformed* primitive indexing and took "no centred candidates shown" as evidence against centring — but `refine_bravais_settings` only ever finds subgroups of the cell it's given; it structurally cannot discover a centred description unless the input has *already* been reindexed toward that hypothesis. Compounded by the v2.5.0 check's own I/sigma(I) classification being too confident — real systematic absences are rarely perfectly zero in practice, so a clearly-nonzero I/sigma(I) doesn't rule out true centring the way the tool's wording implied
- Fixed in three places that all had the same incomplete framing: `dials/scripts/centring_vs_pseudocentring_check.py`'s verdict text (no longer states a confident TRUE/PSEUDO conclusion from I/sigma(I) alone — spells out the actual decisive sequence: reindex toward the flagged axis's centred hypothesis, re-run `refine_bravais_settings` on *that*, compare real refinement R-factors), `skills/symmetry/SKILL.md`, and `core/prompts.py`'s base-prompt note — all three now explicitly name this as a documented failure mode and give the correct three-step sequence
- Also added a `dials.damage_analysis` entry to `dials/commands.py` (found in the same session — it ran successfully but logged a spurious "Unknown DIALS command" warning since it was missing from the internal catalog, purely cosmetic but easy to fix while in there)
- 1 new regression test locking in that every flagged verdict (low or high I/sigma(I)) names the decisive test rather than stating a conclusion — 145 total, up from 144

### v2.5.3 — Fix Silent Command Truncation in Timing/History Tables
- **Real bug, confirmed against a live DPF3 run**: `display_timing_summary()`'s "Command Timing Summary" table (and `display_command_history`'s "Command History" table) hard-sliced each command string to 60 (resp. 50) characters with no ellipsis or any other indicator that anything was cut — e.g. `dials.import /shared/data/projects/yangha/DPF3/x247398/t1.*.img.bz2` lost its trailing `.bz2`, and every `dials.python /long/absolute/path/.../<script>.py ...` invocation (four of them in one run — the geometry check after indexing, again after re-indexing, again after refinement, and the centring check after integration) looked identical and unreadable, hiding exactly the information that would show the new checks were actually running
- New `DIALSAgent._display_command_label()`: shortens `dials.python`/`cctbx.python`/`libtbx.python <script>.py ...` invocations to just the script's filename (the installation-specific absolute path is boilerplate) rather than truncating blindly. Removed both hard slices entirely and set `overflow="fold"` on the Command column in both tables, so Rich wraps across lines instead of silently dropping text — nothing is ever lost now, at most an occasional mid-word line break for an unbroken long token (a path with no spaces)
- 6 new tests — 144 total, up from 138

### v2.5.2 — Recognize Compressed Images (.bz2/.gz), No Decompression Needed
- **Real bug, not a tutorial-specific fix**: found live-testing the DPF3 "Correcting Poor Initial Geometry" tutorial, whose data ships as `t1.NNNN.img.bz2` files. dxtbx/DIALS reads `.bz2`/`.gz`-compressed images directly (`dials.import t1.0*.img.bz2` works with no extra step) — the tutorial itself notes this, distinguishing it from extracting the outer `.tar` archive the images ship in (a one-time packaging step, unrelated to per-image compression). Two compounding gaps caused the agent to try `bunzip2`-ing hundreds of images into a duplicate copy before importing: (1) `core/tools.py`'s file-discovery never recognized compressed files at all (`Path.suffix` on `t1.0001.img.bz2` returns just `.bz2`, not `.img`, so these files never appeared in "Available diffraction data files"), and (2) `skills/data_import/SKILL.md` never mentioned compressed-format support, so even when told about the files directly, the agent had no reason to know DIALS handles them natively
- Fixed both: new `COMPRESSED_EXTENSIONS`/`is_recognized_data_file()` in `core/tools.py` (a compressed file is recognized if the extension *before* `.bz2`/`.gz` matches a known format — used at all three file-discovery sites), descriptive type labels (`IMG.BZ2`, `H5.GZ`) instead of just `BZ2`/`GZ`, and explicit guidance in `data_import/SKILL.md` + `dials.import`'s command description
- 10 new tests (`tests/test_data_file_discovery.py`) — 138 total, up from 128

### v2.5.1 — Version Display + Data Directory in Status Table
- **Agent version was never displayed anywhere**: `cli.py` printed DIALS's own version (`✓ DIALS available: DIALS 3.30`) but not the agent's own — now shown in both the interactive and auto-mode startup banners (`DIALS AI Agent v2.5.1`)
- **`display_workflow_status()`'s table was missing `Data Directory`**: the startup sequence prints it once as a scrolling line before the table appears, but the persistent "Workflow Status" table — the part that actually stays on screen as the welcome view — only had `Working Directory`. Found by a user testing the workshop deployment. Added a `Data Directory` row (showing `(not configured)` when unset), matching the output-vs-data-directory distinction from v2.3.0's prompt fix, now carried into the human-facing table too, not just the LLM-facing context
- 3 new regression tests in `tests/test_cli_dispatch.py` — 128 total, up from 125

### v2.5.0 — Centring vs. Pseudo-centring Check
- **`dials/scripts/centring_vs_pseudocentring_check.py`**: New numeric (no rendering) check for a hidden translational pseudo-symmetry — grounded directly in DIALS's "Centring vs. Pseudo-centring" tutorial. Unlike the v2.3.0 geometry check (which only used reciprocal-lattice *positions*), this one is intensity-based: along a systematic row, it compares the variance of lag-1 intensity differences (adjacent Miller index, opposite parity) to lag-2 differences (two apart, same parity) via an F-test on values pooled across every row in a family (a single row's own ~10-20 points are nowhere near enough to trust in isolation). A significantly larger lag-1 variance means the intensities are alternating strong/weak along that axis; the pooled I/sigma(I) of the weaker set then distinguishes a genuine systematic absence (TRUE centring) from a weak-but-real reflection (PSEUDO-centring) — the actual distinction the tutorial is teaching, and the reason it matters (treating pseudo-centric reflections as absent discards real data and hurts refinement, exactly as the tutorial's own R-factor comparison shows)
- **A real bug caught and fixed during validation, not just designed away**: the first implementation detrended each row with a low-order polynomial fit and looked at the lag-1 autocorrelation of the residuals — validated against a pure-noise synthetic dataset (no structure at all), it still falsely flagged an axis, because fitting a polynomial to ~10-20 points and inspecting its own residuals is overfitting, which *artificially induces negative autocorrelation even under the null*. Rebuilt around the lag-1/lag-2 variance ratio instead (no curve fitting at all), re-validated against pure noise, a smooth resolution fall-off, and both centring scenarios — zero false positives, and true/pseudo-centring correctly localized to the one axis carrying the effect and correctly classified
- **Shared row-grouping logic extracted** into `dials/scripts/_systematic_rows.py` (used by both this script and `reciprocal_lattice_linearity.py`); refactor confirmed behavior-preserving against the original v2.3.0 synthetic validation numbers
- Wired into the base prompt (`core/prompts.py::_get_centring_vs_pseudocentring_note`) the same way as the geometry check — no new skill, no new tool schema, invoked via the existing `suggest_dials_command`/`analyze_dials_output` path. Runs proactively after `dials.integrate` (needs real intensities, so this is the earliest point it's possible), feeding into the `symmetry` skill's `dials.symmetry`/`dials.cosym`/`dials.refine_bravais_settings` decision rather than being a standalone diagnostic
- 13 new tests (`tests/test_centring_vs_pseudocentring_check.py`) — 125 total, up from 112. `scipy` added to the `dev` extras (only for testing this script's pure-Python parts locally; production execution always goes through `dials.python`/`cctbx.python`/`libtbx.python`, which already bundle scipy as a cctbx dependency)

### v2.4.0 — Multi-Dataset Auto Processing
- **`run_auto` now handles multiple datasets by default**: previously it always processed exactly one dataset into the configured working directory. It now calls a new `_discover_dataset_subdirectories()` — an immediate-subdirectory scan of `DATA_DIRECTORY` for anything containing recognized diffraction data files — and, when 2+ are found, loops over all of them (via a new `_switch_to_dataset()`, which creates `<working_directory>/<dataset_name>/` and points input/output at the right places, clearing conversation history between datasets so context doesn't bleed across them), unless the user's request names one specifically (a single case-insensitive substring match against the discovered names), in which case only that one runs. A flat data directory (no subdirectories) is unchanged — same single-dataset behavior as before
- The original single-dataset loop body was extracted unchanged into `_run_auto_single()` (now returns whether the workflow completed within its iteration budget, `max_iterations=30` **per dataset** rather than shared across all of them) so multi-dataset processing is a thin wrapper around exactly the same per-dataset logic, not a reimplementation
- `Ctrl+C` during one dataset now stops the whole multi-dataset run (rather than silently skipping to the next) while still printing the same graceful message as before for the single-dataset case
- Documented in README ("Auto Mode" section) and in-app help (`help` command, `--auto`/`--auto-message` CLI help text)
- 16 new tests in `tests/test_auto_multi_dataset.py` (dataset discovery, output-directory creation, conversation-history isolation, single-vs-multi dispatch, named-dataset narrowing, interrupt handling) — 112 total, up from 96

### v2.3.0 — Reciprocal-Lattice Linearity Check + Beam-Centre Knowledge Fix
- **`dials/scripts/reciprocal_lattice_linearity.py`**: New numeric (no rendering, no vision model) check for whether a crystal's reciprocal lattice is straight, statically bent, or spiraling — computed directly from `indexed.refl`'s Miller indices, `rlp` coordinates, and rotation angles. For each "systematic row" (fix two Miller indices, vary the third), fits a straight line via total-least-squares/SVD and reports the normalized perpendicular residual (curvature) plus how strongly the residual direction correlates with rotation angle (`phi_correlation_r2` — near 1 means the curvature is phi-locked, i.e. a spiral; near 0 with real curvature means a static/fixed geometry error). Model-free: never needs the "true" unit cell, only checks self-consistency with *some* straight lattice. Run via `dials.python <script> indexed.expt indexed.refl` (or `libtbx.python`/`cctbx.python` as a fallback on installs that omit `dials.python`) — wired into the always-present base system prompt (`core/prompts.py`) with a runtime-resolved absolute path, so the LLM can invoke it through the existing `suggest_dials_command`/`analyze_dials_output` tools with no new tool-handling code needed. Validated against synthetic data (straight/statically-bent/spiral scenarios) built with the real `dials.array_family.flex`/cctbx APIs — see the version-history entry below for numbers
- **Beam-centre knowledge gap fixed**: the agent previously suggested `indexing.max_lattices=N` for apparent multi-lattice patterns without ever connecting that symptom (plus high/unstable refinement RMSDs, sometimes described as "the crystal moving in the beam") to an incorrect initial beam centre — a well-known real-world failure mode (see DIALS's "Correcting Poor Initial Geometry" tutorial), not something to hardcode per-dataset. Added `dials.search_beam_position` as a first-suggested fix in `skills/troubleshooting/__init__.py`'s `multiple_lattices` and `refinement_failed` entries, new keyword mappings (`"beam mov"`, `"crystal mov"`, `"large jumps"`, etc.), and matching guidance in `skills/indexing/SKILL.md` and `skills/refinement/SKILL.md` (the latter previously had a dead-end observation — "large jumps suggest problems" — with no next step attached)
- **Runs proactively at each relevant step**, not just when asked: the base prompt now instructs the agent to run this automatically right after `dials.index` and again after `dials.refine`, and — when it flags a problem — to (1) explain the finding, (2) point the user at `dials.reciprocal_lattice_viewer`/`dials.image_viewer` to confirm visually themselves (the agent still can't render/view images), and (3) propose the specific fix command rather than only reporting a number. `skills/indexing/SKILL.md` and `skills/refinement/SKILL.md` updated to match ("After Indexing/Refinement (Geometry Check)")
- **Measured runtime**: ~2s fixed interpreter-startup cost (`dials.python`/`cctbx.python` + dxtbx/dials imports) plus ~0.3-0.4s of actual analysis per crystal at full-sweep scale (benchmarked with a real `dials.array_family.flex` reflection table sized to ~90k/~70k indexed reflections) — roughly 2.5-3s total per run, negligible next to `dials.index` itself (typically tens of seconds to minutes)
- **Directory clarity fix**: `core/prompts.py`'s dynamic context block previously labeled the output location as generic "Working directory" and only showed the data directory line when one happened to be configured — a real conflation risk (especially for a shared install where the data directory is common but each user's output directory differs, as in the workshop setup). Now always shows both, explicitly labeled "Output directory" and "Data directory", with an explicit instruction not to refer to either as just "the working directory"
- **Visualization offered at every later step, not just on a flagged geometry check**: restored an always-available (not just problem-triggered) offer to open `dials.reciprocal_lattice_viewer`/`dials.image_viewer` after indexing and refinement even when the geometry check comes back clean; reinforced the existing offer after integration; added one after `dials.cosym` (checking consistent reindexing across datasets); and added explicit "not applicable here" notes at symmetry (single-crystal case)/scaling/export so the agent doesn't awkwardly reach for an image viewer where a per-image/reciprocal-lattice view genuinely isn't the right diagnostic
- 96 tests still pass; no test changes needed since this only extends prompt/knowledge content and adds a new bundled script, no new tool schemas

### v2.2.1 — Pre-flight Environment Check
- **`scripts/preflight_check.sh`**: New read-only diagnostic script for deploying to an unfamiliar machine — detects an ephemeral Slurm/PBS-scheduled session (e.g. an OOD virtual-desktop job) vs. a stable host, identifies which of the three observed DIALS-activation patterns applies (conda `dials_env.sh`, SBGrid/module system with `dials.*` already on `PATH`, or not installed), checks Python 3.10+/`venv`/`git`, and checks reachability of GitHub, PyPI, and the LLM provider endpoints (CBORG, Anthropic). Written after deploying to an AWS ParallelCluster/SBGrid-cloud OOD desktop node where DIALS had no `dials_env.sh` at all (SBGrid puts `dials.*` directly on `PATH`) — a case the README's existing deployment steps didn't call out
- README: new "Unfamiliar Environment? Run the Pre-flight Check First" section documenting the three DIALS-activation patterns

### v2.2.0 — MCP Server
- **`dials_agent/mcp_server.py`**: New `DIALSMCPHost` + `build_server()` expose 15 of the agent's tools over the Model Context Protocol (`python -m dials_agent.mcp_server`), so an external agent (e.g. a future Phenix agent) can call directly into DIALS processing rather than only through the interactive CLI
- **Curated surface, not full parity**: excludes `run_shell_command` (arbitrary shell — bigger blast radius with no human confirming), and `suggest_dials_command` / `explain_dials_concept` / `suggest_troubleshooting` (designed around the CLI's own approve-then-execute loop or its own LLM answering in the same turn — neither maps onto a stateless external tool call)
- **`execute_dials_command`**: new tool replacing `suggest_dials_command`'s role for MCP callers — runs a validated DIALS command immediately, since the calling agent's decision to invoke it over MCP is itself the approval
- Built against `mcp` SDK 2.0.0's `MCPServer` API (`mcp.server.mcpserver`); stdio transport for now
- 96 tests pass (up from 85), plus a manual end-to-end smoke test over real stdio (tool listing + representative calls across all 15 tools, including confirming `execute_dials_command` rejects non-`dials.`-prefixed commands)

### v2.1.0 — Progressive Disclosure + SKILL.md
- **`load_skill` tool**: The system prompt no longer injects every skill's full guidance up front — `SkillRegistry.get_composed_prompt()` now returns a compact index (name + one-line description per skill), and the LLM calls `load_skill` on demand to pull a skill's full guidance into the conversation. Mirrors how Claude Code loads its own skills. Cuts the cached system+tools prefix from ~12.2K to ~5.3K tokens (~56%)
- **`SKILL.md` per skill**: Each skill's prompt-fragment content now lives in `dials_agent/skills/<name>/SKILL.md` (YAML-ish frontmatter with `name`/`description`, markdown body) instead of a Python string literal — `<name>/__init__.py` holds the tool schemas and handler logic and loads the guidance text via `load_skill_md()` at import time. Every flat `skills/<name>.py` module became a `skills/<name>/` package
- **`get_full_prompt()`**: Preserves the old always-everything concatenation (used by tests to guard against content loss during the split)
- 85 tests pass (up from 77)
- **Measured impact**: two live `--auto` full-pipeline runs on the insulin (ins10) dataset averaged **351,109 tokens**, vs. 458,032 for the equivalent v2.0.0 runs (**−23.3%**) and 442,460 for the original pre-skills v1.3 baseline (**−20.6%**) — see [`docs/token_usage_comparison_v2.0_vs_v2.1.md`](docs/token_usage_comparison_v2.0_vs_v2.1.md)

### v2.0.0 — Skills-Based Architecture
- **Modular skills**: The monolithic system prompt, tool list, and tool-dispatch chain are split into 12 self-contained skills (`data_import`, `spot_finding`, `indexing`, `refinement`, `integration`, `symmetry`, `scaling`, `export`, `troubleshooting`, `workspace`, `phil_params`, `tutorials`), each owning its own prompt fragment, tool schemas, and handler logic
- **`SkillRegistry`**: Composes all skill prompt fragments into the system prompt and dispatches tool calls to the owning skill; `ClaudeClient` and `cli.py` both consume it
- **Decoupled handlers**: Skill handlers return plain data dicts with no CLI dependency — an `_cli_print` convention carries display-only messages, and destructive shell commands use a `requires_confirmation` / `_confirmed` round-trip instead of calling `Confirm.ask` directly, so a future MCP server can substitute its own consent mechanism
- **Behavior-preserving**: Composed prompt and full tool set are unchanged from v1.3; 76 tests cover skill/tool schemas, registry dispatch, and the CLI wrapper layer

### v1.3.0 — Run Comparison
- **`compare` command**: Compare results from multiple DIALS processing runs side-by-side
- **CLI `--compare` flag**: Standalone comparison mode (no API key needed)
- **Consistency assessment**: Automatic evaluation of metric agreement with metric-specific tolerances
- **JSON reports**: Save comparison results for programmatic analysis
- **Markdown output**: Generate comparison reports in Markdown format
- **31 unit/integration tests**: Comprehensive test coverage for the comparison module

### v1.2.0 — PHIL Parameter Knowledge & Problem Diagnosis
- **PHIL Parameter Documentation**: Fetched complete parameter docs for all 82 DIALS commands using `dials.program -c -e2 -a2` (15,343 lines total, stored in `dials_agent/docs/phil_params/`)
- **`lookup_phil_params` tool**: On-demand parameter lookup for any DIALS command with keyword search
- **`diagnose_problem` tool**: Maps 15+ common problems (indexing failures, high Rmerge, ice rings, etc.) to specific parameter-level solutions
- **62 commands known**: Expanded from 21 to 62 commands across 5 categories (workflow, utility, serial crystallography, visualization, format conversion)
- **Enhanced system prompt**: 56K chars with 20+ new utility command references, SSX commands, electron diffraction support, DAC support, and comprehensive troubleshooting
- **Reusable fetch script**: `dials_agent/docs/fetch_phil_params.sh` to regenerate parameter docs

### v1.1.0 — Core Agent
- Natural language interface with multi-provider LLM support
- Semi-automated workflow with command approval
- Output parsing and metric extraction
- Workflow tracking and file management
- Visualization support (image viewer, reciprocal lattice viewer)
- Auto mode for unattended processing
- Tutorial system with guided walkthroughs

## Acknowledgments

- DIALS development team
- Anthropic for the Claude API
- CBORG (Claude at Berkeley) for LBL API access
