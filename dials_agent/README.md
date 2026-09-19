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

| Provider | API Key Variable | Default Model | Notes |
|----------|-----------------|---------------|-------|
| **CBORG** | `CBORG_API_KEY` | `anthropic/claude-sonnet` | Recommended for LBL users |
| **OpenAI** | `OPENAI_API_KEY` | `gpt-4o` | Direct OpenAI API |
| **Google Gemini** | `GEMINI_API_KEY` | `gemini-2.5-pro` | Google's Gemini models |
| **Anthropic** | `ANTHROPIC_API_KEY` | `claude-sonnet-4-20250514` | Direct Anthropic API |

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
| `MAX_TOKENS` | Maximum response tokens | 4096 |
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

## Version History

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
- **PHIL Parameter Documentation**: Fetched complete parameter docs for all 82 DIALS commands using `dials.program -c -e2 -a2` (15,343 lines total, stored in `docs/phil_params/`)
- **`lookup_phil_params` tool**: On-demand parameter lookup for any DIALS command with keyword search
- **`diagnose_problem` tool**: Maps 15+ common problems (indexing failures, high Rmerge, ice rings, etc.) to specific parameter-level solutions
- **62 commands known**: Expanded from 21 to 62 commands across 5 categories (workflow, utility, serial crystallography, visualization, format conversion)
- **Enhanced system prompt**: 56K chars with 20+ new utility command references, SSX commands, electron diffraction support, DAC support, and comprehensive troubleshooting
- **Reusable fetch script**: `docs/fetch_phil_params.sh` to regenerate parameter docs

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
