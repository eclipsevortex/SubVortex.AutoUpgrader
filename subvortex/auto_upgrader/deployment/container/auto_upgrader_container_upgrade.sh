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

# Load environment variables
export $(grep -v '^#' .env | xargs)

# Check which command is available
if command -v docker &> /dev/null && docker compose version &> /dev/null; then
    DOCKER_CMD="docker compose"
    elif command -v docker-compose &> /dev/null; then
    DOCKER_CMD="docker-compose"
else
    echo "❌ Neither 'docker compose' nor 'docker-compose' is installed. Please install Docker Compose."
    exit 1
fi

# Install watchtower
./../../scripts/watchtower/watchtower_start.sh

echo "📥 Pulling latest image for $SERVICE_NAME..."
docker compose pull "$SERVICE_NAME"

echo "🔄 Recreating container with updated image..."
$DOCKER_CMD -f ../../docker-compose.yml up auto_upgrader -d --no-deps --force-recreate

echo "✅ Auto Upgrader upgraded successfully"
