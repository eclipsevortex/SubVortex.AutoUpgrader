#!/bin/bash

set -e

SERVICE_NAME=subvortex-auto-upgrader

# Determine script directory dynamically to ensure everything runs in ./scripts/api/
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/../.."

# Track whether we stashed anything
STASHED=0

# Check for uncommitted changes
if ! git diff --quiet || ! git diff --cached --quiet; then
    echo "📦 Stashing local changes..."
    git stash push -u -m "Auto stash before pull"
    STASHED=1
fi

# Check if branch is tracking a remote
BRANCH=$(git rev-parse --abbrev-ref HEAD)
UPSTREAM=$(git rev-parse --abbrev-ref "$BRANCH@{upstream}" 2>/dev/null || true)

if [[ -z "$UPSTREAM" ]]; then
    echo "❌ Branch '$BRANCH' is not tracking any remote branch. Cannot pull safely."
    exit 1
fi

# Pull latest changes from upstream
echo "🔄 Pulling latest changes from $UPSTREAM..."
if ! git pull --ff-only; then
    echo "⚠️ Fast-forward pull failed. Trying forced sync with origin/$BRANCH..."
    git fetch origin
    git reset --hard origin/"$BRANCH"
fi

# Restore stashed changes if we made one
if [[ "$STASHED" -eq 1 ]]; then
    echo "🧵 Restoring stashed local changes..."
    git stash pop || {
        echo "⚠️ Conflicts while restoring stash. You may need to resolve manually."
    }
fi

# Install python if not already done
if ! command -v python3 &> /dev/null; then
    echo "Python3 not found. Installing..."
    bash "../../python/python_setup.sh"
fi

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install dependencies
if [[ -f "requirements.txt" ]]; then
    pip install -r requirements.txt
else
    echo "⚠️ requirements.txt not found. Skipping dependency installation."
fi

# Load environment variables
export $(grep -v '^#' .env | xargs)

# Install dependencies specific to the observer
pip install ".[$SUBVORTEX_EXECUTION_ROLE]"

# Install SubVortex in Editable Mode
pip install -e ../../

# Start or restart the process
if pm2 list | grep -qw "$SERVICE_NAME"; then
    echo "🔄 Restarting PM2 service: $SERVICE_NAME"
    pm2 restart "$SERVICE_NAME"
else
    ./deployment/process/auto_upgrader_process.start.sh
fi

echo "✅ Auto Upgrader upgraded successfully"
