#!/bin/bash

set -e

SERVICE_NAME=subvortex-auto-upgrader

# Determine script directory dynamically to ensure everything runs in ./scripts/api/
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/../.."

# Check for uncommitted changes
if ! git diff --quiet || ! git diff --cached --quiet; then
    echo "📦 Stashing local changes..."
    git stash push -u -m "Auto stash before pull"
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
git pull --ff-only

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

# Check if the service exists
if ! systemctl list-units --type=service --all | grep -qw "$SERVICE_NAME"; then
  echo "❌ Service $SERVICE_NAME not found."
  exit 1
fi

# Check if the service is active
if systemctl is-active --quiet "$SERVICE_NAME"; then
  echo "🔄 Restarting $SERVICE_NAME..."
  sudo systemctl restart "$SERVICE_NAME"
else
  echo "🚀 Starting $SERVICE_NAME..."
  sudo systemctl start "$SERVICE_NAME"
fi

echo "✅ Auto Upgrader setup successfully"
