#!/usr/bin/env python3
"""
Run script for DIALS AI Agent.

This script can be run directly without installing the package:
    python run_agent.py
    python run_agent.py -d /path/to/data
"""

import sys
import os

# Add the parent directory to the path so we can import dials_agent
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dials_agent.cli import main

if __name__ == "__main__":
    main()
