#!/bin/bash
# Sync local dials_agent code to remote dials.lbl.gov
#
# Usage: ./sync_to_remote.sh
#
# This syncs the local dials_agent/ directory to the remote machine,
# excluding .env files (to preserve remote API keys), __pycache__, and egg-info.
#
# dials.lbl.gov (alias: dials-remote) and xfel.lbl.gov share the same home
# filesystem, but dials.lbl.gov runs a newer OS (Rocky 9 vs. CentOS 7) with
# a newer glibc, which is what VS Code Remote-SSH needs — so that's the
# preferred host going forward. See ~/.ssh/config for both aliases.

LOCAL_DIR="./dials_agent/"
REMOTE_DIR="dials-remote:/net/dials/raid1/yangha/DIALS_Dev2025/dials_agent/"

echo "Syncing dials_agent to dials.lbl.gov..."
rsync -avz --progress \
    --exclude '__pycache__' \
    --exclude '*.pyc' \
    --exclude '.env' \
    --exclude '*.egg-info' \
    --exclude '.git' \
    "$LOCAL_DIR" "$REMOTE_DIR"

echo ""
echo "Sync complete! To test on remote:"
echo "  ssh dials-remote 'cd /net/dials/raid1/yangha/DIALS_Dev2025 && conda_base/bin/python -m dials_agent.cli'"
