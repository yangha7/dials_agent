#!/bin/bash
# DIALS AI Agent — Setup Script
#
# This script installs the agent using the best available method:
#   1. If DIALS conda environment is active → install directly into it
#   2. If python3-venv is available → create a virtual environment
#   3. Otherwise → provide instructions
#
# Usage:
#   source /path/to/dials/dials_env.sh   # activate DIALS first (recommended)
#   ./setup.sh
#   python -m dials_agent.cli

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=== DIALS AI Agent Setup ==="
echo ""

# ── Method 1: Check if we're in a conda environment (e.g., DIALS) ──
if [ -n "$CONDA_PREFIX" ]; then
    echo "Detected conda environment: $CONDA_PREFIX"
    PYTHON_CMD="$(which python3 2>/dev/null || which python 2>/dev/null)"
    
    if [ -n "$PYTHON_CMD" ]; then
        version=$("$PYTHON_CMD" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
        echo "Using conda Python $version: $PYTHON_CMD"
        echo ""
        echo "Installing dials-agent into conda environment..."
        pip install -e "$SCRIPT_DIR"
        
        # Setup .env if not exists
        if [ ! -f "$SCRIPT_DIR/.env" ] && [ -f "$SCRIPT_DIR/.env.example" ]; then
            cp "$SCRIPT_DIR/.env.example" "$SCRIPT_DIR/.env"
            echo ""
            echo "Created .env from .env.example — edit it with your API key:"
            echo "  nano $SCRIPT_DIR/.env"
        fi
        
        echo ""
        echo "=== Setup Complete ==="
        echo ""
        echo "Run the agent with:"
        echo "  python -m dials_agent.cli"
        exit 0
    fi
fi

# ── Method 2: Try creating a virtual environment ──
PYTHON_CMD=""
for cmd in python3 python; do
    if command -v "$cmd" &>/dev/null; then
        version=$("$cmd" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null)
        major=$("$cmd" -c "import sys; print(sys.version_info.major)" 2>/dev/null)
        minor=$("$cmd" -c "import sys; print(sys.version_info.minor)" 2>/dev/null)
        if [ "$major" -ge 3 ] && [ "$minor" -ge 10 ]; then
            PYTHON_CMD="$cmd"
            echo "Found Python $version ($cmd)"
            break
        fi
    fi
done

if [ -z "$PYTHON_CMD" ]; then
    echo "Error: Python 3.10+ is required but not found."
    echo ""
    echo "Options:"
    echo "  1. Activate your DIALS environment first:"
    echo "     source /path/to/dials/dials_env.sh"
    echo "     ./setup.sh"
    echo ""
    echo "  2. Install Python 3.10+:"
    echo "     sudo apt install python3 python3-venv python3-pip"
    exit 1
fi

# Check for venv module
if "$PYTHON_CMD" -c "import venv" 2>/dev/null; then
    VENV_DIR="${SCRIPT_DIR}/venv"
    
    if [ -d "$VENV_DIR" ]; then
        echo "Virtual environment already exists at $VENV_DIR"
    else
        echo "Creating virtual environment at $VENV_DIR..."
        "$PYTHON_CMD" -m venv "$VENV_DIR"
    fi
    
    echo "Installing dials-agent..."
    "$VENV_DIR/bin/pip" install --upgrade pip
    "$VENV_DIR/bin/pip" install -e "$SCRIPT_DIR"
    
    # Setup .env if not exists
    if [ ! -f "$SCRIPT_DIR/.env" ] && [ -f "$SCRIPT_DIR/.env.example" ]; then
        cp "$SCRIPT_DIR/.env.example" "$SCRIPT_DIR/.env"
        echo ""
        echo "Created .env from .env.example — edit it with your API key:"
        echo "  nano $SCRIPT_DIR/.env"
    fi
    
    echo ""
    echo "=== Setup Complete ==="
    echo ""
    echo "To use the agent:"
    echo "  1. Activate the environment:"
    echo "     source $VENV_DIR/bin/activate"
    echo ""
    echo "  2. (Optional) Activate DIALS if not already in PATH:"
    echo "     source /path/to/dials/dials_env.sh"
    echo ""
    echo "  3. Run the agent:"
    echo "     python -m dials_agent.cli"
    echo ""
    echo "  Or run directly without activating:"
    echo "     $VENV_DIR/bin/python -m dials_agent.cli"
    exit 0
fi

# ── Method 3: Neither conda nor venv available ──
echo ""
echo "Error: Cannot create a virtual environment."
echo "The python3-venv package is not installed."
echo ""
echo "Choose one of these options:"
echo ""
echo "  Option A (Recommended): Use the DIALS conda environment"
echo "    source /path/to/dials/dials_env.sh"
echo "    ./setup.sh"
echo ""
echo "  Option B: Install python3-venv (requires sudo)"
echo "    sudo apt install python3-venv"
echo "    ./setup.sh"
echo ""
echo "  Option C: Use pip with --break-system-packages (not recommended)"
echo "    pip install --break-system-packages -e ."
echo ""
echo "  Option D: Use Docker"
echo "    docker build -t dials-agent ."
echo "    docker run -it --rm --env-file .env dials-agent"
exit 1
