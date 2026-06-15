# DIALS AI Agent (v1.2)

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
- `compare <dir1> <dir2> [...]` - Compare results from multiple processing runs
- `clear` - Clear conversation history
- `cd <path>` - Change working directory
- `quit` / `exit` - Exit the agent

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

## Project Structure

```
dials_agent/
├── __init__.py           # Package initialization
├── cli.py                # CLI interface
├── config.py             # Configuration settings
├── .env.example          # Example configuration file
├── requirements.txt      # Dependencies
├── core/
│   ├── __init__.py
│   ├── claude_client.py  # LLM API wrapper (multi-provider)
│   ├── prompts.py        # System prompts
│   └── tools.py          # Tool definitions
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
