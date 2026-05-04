#!/bin/bash
# DIALS AI Agent — Setup Script
#
# This script creates a virtual environment and installs the agent.
# Works on systems with PEP 668 restrictions (Debian 12+, Ubuntu 23.04+).
#
# Usage:
#   ./setup.sh                    # Create venv and install
#   source venv/bin/activate      # Activate the environment
#   python -m dials_agent.cli     # Run the agent
#
# If DIALS is installed via conda, you can also install into the DIALS conda env:
#   conda activate <dials_env>
#   pip install -e .

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${SCRIPT_DIR}/venv"

echo "=== DIALS AI Agent Setup ==="
echo ""

# Check Python version
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
    echo "Install it with: sudo apt install python3 python3-venv python3-pip"
    exit 1
fi

# Check for venv module
if ! "$PYTHON_CMD" -c "import venv" 2>/dev/null; then
    echo "Error: python3-venv is not installed."
    echo "Install it with: sudo apt install python3-venv"
    exit 1
fi

# Create virtual environment
if [ -d "$VENV_DIR" ]; then
    echo "Virtual environment already exists at $VENV_DIR"
else
    echo "Creating virtual environment at $VENV_DIR..."
    "$PYTHON_CMD" -m venv "$VENV_DIR"
fi

# Activate and install
echo "Installing dials-agent..."
"$VENV_DIR/bin/pip" install --upgrade pip
"$VENV_DIR/bin/pip" install -e "$SCRIPT_DIR"

# Setup .env if not exists
if [ ! -f "$SCRIPT_DIR/.env" ]; then
    if [ -f "$SCRIPT_DIR/.env.example" ]; then
        cp "$SCRIPT_DIR/.env.example" "$SCRIPT_DIR/.env"
        echo ""
        echo "Created .env from .env.example — edit it with your API key:"
        echo "  nano $SCRIPT_DIR/.env"
    fi
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
