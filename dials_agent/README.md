# DIALS AI Agent

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

## Installation

1. Ensure you have Python 3.10+ installed
2. Install DIALS (https://dials.github.io/installation.html)
3. Install the agent package:

```bash
cd dials_agent
pip install -e .
```

This installs the package in "editable" mode, making the `dials_agent` module available in your Python environment.

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

## Acknowledgments

- DIALS development team
- Anthropic for the Claude API
- CBORG (Claude at Berkeley) for LBL API access
