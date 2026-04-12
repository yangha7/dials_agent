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

## Installation

1. Ensure you have Python 3.10+ installed
2. Install DIALS (https://dials.github.io/installation.html)
3. Install the agent package:

```bash
cd dials_agent
pip install -e .
```

This installs the package in "editable" mode, making the `dials_agent` module available in your Python environment.

4. Set up your API key (choose one option):

### Option A: Native Anthropic API

```bash
export ANTHROPIC_API_KEY="your-api-key-here"
```

Or create a `.env` file:

```
ANTHROPIC_API_KEY=your-api-key-here
```

### Option B: CBORG (Claude at Berkeley) or other OpenAI-compatible API

If you have access to CBORG or another OpenAI-compatible endpoint:

```bash
export API_PROVIDER="openai"
export OPENAI_API_KEY="your-cborg-api-key"
export OPENAI_BASE_URL="https://api.cborg.lbl.gov"
export MODEL="anthropic/claude-sonnet"
```

Or create a `.env` file:

```
API_PROVIDER=openai
OPENAI_API_KEY=your-cborg-api-key
OPENAI_BASE_URL=https://api.cborg.lbl.gov
MODEL=anthropic/claude-sonnet
```

## Usage

### Interactive CLI

Run the interactive command-line interface:

```bash
python -m dials_agent.cli
```

Or with a specific working directory:

```bash
python -m dials_agent.cli -d /path/to/data
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

## Configuration

Configuration can be set via environment variables or a `.env` file:

| Variable | Description | Default |
|----------|-------------|---------|
| `API_PROVIDER` | API provider: `anthropic` or `openai` | anthropic |
| `ANTHROPIC_API_KEY` | Anthropic API key (for native API) | - |
| `OPENAI_API_KEY` | API key for OpenAI-compatible endpoints (CBORG) | - |
| `OPENAI_BASE_URL` | Base URL for OpenAI-compatible API | https://api.cborg.lbl.gov |
| `MODEL` | Model to use | claude-sonnet-4-20250514 |
| `MAX_TOKENS` | Maximum response tokens | 4096 |
| `DIALS_PATH` | Path to DIALS installation | (system PATH) |
| `WORKING_DIRECTORY` | Default working directory | . |
| `COMMAND_TIMEOUT` | Command timeout in seconds | 3600 |

## Project Structure

```
dials_agent/
├── __init__.py           # Package initialization
├── cli.py                # CLI interface
├── config.py             # Configuration settings
├── requirements.txt      # Dependencies
├── core/
│   ├── __init__.py
│   ├── claude_client.py  # Anthropic API wrapper
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

To run the DIALS agent on a different computer where DIALS is already installed:

### Files to Copy

You only need to copy the `dials_agent/` directory:

```
dials_agent/
├── __init__.py
├── cli.py
├── config.py
├── pyproject.toml
├── requirements.txt
├── run_agent.py
├── core/
│   ├── __init__.py
│   ├── claude_client.py
│   ├── prompts.py
│   └── tools.py
└── dials/
    ├── __init__.py
    ├── commands.py
    ├── executor.py
    ├── parser.py
    └── workflow.py
```

### Quick Deployment Steps

1. **Copy the dials_agent directory** to the target computer:
   ```bash
   scp -r dials_agent/ user@remote:/path/to/destination/
   ```

2. **On the target computer**, ensure DIALS is activated:
   ```bash
   source /path/to/dials/dials_env.sh
   ```

3. **Install the agent**:
   ```bash
   cd /path/to/destination/dials_agent
   pip install -e .
   ```

4. **Set up API key** (create `.env` file in the dials_agent directory):
   ```bash
   # For CBORG (recommended at LBNL):
   cat > .env << EOF
   API_PROVIDER=openai
   OPENAI_API_KEY=your-cborg-api-key
   OPENAI_BASE_URL=https://api.cborg.lbl.gov
   MODEL=anthropic/claude-sonnet
   EOF
   ```

5. **Run the agent**:
   ```bash
   python -m dials_agent.cli
   ```

### Alternative: Single-File Deployment

For even simpler deployment, you can create a tarball:

```bash
# On source computer
tar -czvf dials_agent.tar.gz dials_agent/

# Copy to target
scp dials_agent.tar.gz user@remote:/path/to/destination/

# On target computer
cd /path/to/destination
tar -xzvf dials_agent.tar.gz
cd dials_agent
pip install -e .
```

### Requirements

The target computer needs:
- Python 3.10+
- DIALS installed and in PATH (or set `DIALS_PATH` in `.env`)
- Internet access for API calls
- A valid API key (Anthropic or CBORG)

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
