#!/bin/bash
# DIALS AI Agent — Pre-flight environment check
#
# Run this BEFORE `setup.sh` on any new machine (a new cluster, a fresh VM,
# an unfamiliar OOD/Slurm virtual desktop, etc.) to answer the questions
# that otherwise take several rounds of guessing:
#
#   - Is this compute node ephemeral (Slurm-scheduled), or a stable host?
#   - How is DIALS activated here — conda (dials_env.sh), SBGrid (already
#     on PATH, no activation script), or not installed at all?
#   - Is there a persistent, shared filesystem to install into?
#   - Can this node actually reach GitHub (to clone) and your LLM
#     provider's API endpoint (to run)?
#   - Is Python 3.10+ with `venv` available?
#
# Usage:
#   ./preflight_check.sh
#
# This makes no changes to the system — it's read-only/diagnostic only.

echo "=== DIALS AI Agent — Pre-flight Check ==="
echo ""

echo "--- Host ---"
echo "hostname: $(hostname -f 2>/dev/null || hostname)"
echo "whoami:   $(whoami)"
if command -v ip &>/dev/null; then
    echo "ip:       $(hostname -I 2>/dev/null || ip -4 addr show 2>/dev/null | grep inet | awk '{print $2}' | tr '\n' ' ')"
fi
if [ -f /etc/os-release ]; then
    echo "os:       $(grep -E '^(NAME|VERSION)=' /etc/os-release | tr '\n' ' ')"
fi
echo ""

echo "--- Ephemeral / scheduled session? ---"
if env | grep -qi '^SLURM_JOB_ID='; then
    echo "SLURM job detected (JOB_ID=$SLURM_JOB_ID, node=$SLURMD_NODENAME)."
    if [ -n "$SLURM_JOB_END_TIME" ] && [ -n "$SLURM_JOB_START_TIME" ]; then
        secs=$(( SLURM_JOB_END_TIME - SLURM_JOB_START_TIME ))
        echo "  Job window: ~$(( secs / 3600 ))h. This node will disappear when the job ends —"
        echo "  install into a persistent/shared home directory, not local scratch."
    fi
elif env | grep -qi '^PBS_JOBID='; then
    echo "PBS job detected (JOBID=$PBS_JOBID) — likely an ephemeral compute node."
else
    echo "No Slurm/PBS job env vars found — looks like a stable/persistent host."
fi
echo ""

echo "--- Home filesystem ---"
df -h "$HOME" 2>/dev/null
echo "(Check this is a shared/network mount, not node-local storage, if the"
echo " session above is ephemeral — otherwise your install vanishes with the node.)"
echo ""

echo "--- DIALS ---"
if command -v dials.version &>/dev/null; then
    echo "dials.version found on PATH:"
    dials.version 2>&1 | sed 's/^/  /'
    echo "  -> DIALS_PATH can be left blank in .env; commands already resolve via PATH."
else
    echo "dials.version NOT found on PATH."
fi
dials_env=$(find / -maxdepth 6 -iname 'dials_env.sh' 2>/dev/null | head -3)
if [ -n "$dials_env" ]; then
    echo "Found dials_env.sh (conda-style DIALS install) at:"
    echo "$dials_env" | sed 's/^/  /'
    echo "  -> source this before running the agent (activates DIALS's conda env)."
elif command -v dials.version &>/dev/null; then
    echo "No dials_env.sh found, but dials.version is on PATH anyway —"
    echo "  this is likely an SBGrid-style install (or a module system) where"
    echo "  DIALS is already active in your shell with no separate activation step."
else
    echo "DIALS does not appear to be installed/activated in this shell."
    echo "  -> Either activate it (module load / source dials_env.sh / sbgrid setup)"
    echo "     or install it first: https://dials.github.io/installation.html"
fi
echo ""

echo "--- Python / git ---"
PYTHON_CMD="$(command -v python3 || command -v python)"
if [ -n "$PYTHON_CMD" ]; then
    ver=$("$PYTHON_CMD" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    echo "python3: $PYTHON_CMD ($ver)"
    major=$("$PYTHON_CMD" -c "import sys; print(sys.version_info.major)")
    minor=$("$PYTHON_CMD" -c "import sys; print(sys.version_info.minor)")
    if [ "$major" -ge 3 ] && [ "$minor" -ge 10 ]; then
        echo "  -> version OK (3.10+ required)"
    else
        echo "  -> too old, need 3.10+"
    fi
    if "$PYTHON_CMD" -c "import venv" 2>/dev/null; then
        echo "  -> venv module available"
    else
        echo "  -> venv module NOT available (may need python3-venv package, or use conda instead)"
    fi
else
    echo "No python3/python found on PATH."
fi
echo "git: $(command -v git || echo 'NOT FOUND') $(git --version 2>/dev/null)"
echo ""

echo "--- Network reachability ---"
if command -v curl &>/dev/null; then
    gh_code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 8 https://github.com 2>/dev/null)
    echo "github.com:          HTTP $gh_code $( [ "$gh_code" = "200" ] && echo '(OK — repo clone should work)' || echo '(unexpected — clone may fail; check proxy/firewall)' )"

    cborg_code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 8 https://api.cborg.lbl.gov 2>/dev/null)
    echo "api.cborg.lbl.gov:   HTTP $cborg_code $( [ -n "$cborg_code" ] && [ "$cborg_code" != "000" ] && echo '(reachable — a 403/404 here is normal without an API key; 000 means unreachable)' )"

    anthropic_code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 8 https://api.anthropic.com 2>/dev/null)
    echo "api.anthropic.com:   HTTP $anthropic_code"

    pypi_code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 8 https://pypi.org 2>/dev/null)
    echo "pypi.org:            HTTP $pypi_code $( [ "$pypi_code" = "200" ] && echo '(OK — pip install should work)' )"
else
    echo "curl not found — cannot check reachability."
fi
echo ""

echo "=== Summary ==="
echo "If DIALS is active and github.com/pypi.org are reachable, you're clear to run:"
echo "  git clone https://github.com/yangha7/dials_agent.git"
echo "  cd dials_agent/dials_agent"
echo "  ./setup.sh"
echo "  # then edit .env with your API key, and: python -m dials_agent.cli"
