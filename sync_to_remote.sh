#!/bin/bash
# Sync local dials_agent code to remote xfel.lbl.gov
#
# Usage: ./sync_to_remote.sh
#
# This syncs the local dials_agent/ directory to the remote machine,
# excluding .env files (to preserve remote API keys), __pycache__, and egg-info.

LOCAL_DIR="./dials_agent/"
REMOTE_DIR="xfel:/net/dials/raid1/yangha/DIALS_Dev2025/dials_agent/"

echo "Syncing dials_agent to xfel.lbl.gov..."
rsync -avz --progress \
    --exclude '__pycache__' \
    --exclude '*.pyc' \
    --exclude '.env' \
    --exclude '*.egg-info' \
    --exclude '.git' \
    "$LOCAL_DIR" "$REMOTE_DIR"

echo ""
echo "Sync complete! To test on remote:"
echo "  ssh xfel 'cd /net/dials/raid1/yangha/DIALS_Dev2025 && conda_base/bin/python -m dials_agent.cli'"
