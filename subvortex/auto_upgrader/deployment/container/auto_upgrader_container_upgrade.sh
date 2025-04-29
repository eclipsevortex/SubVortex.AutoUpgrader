#!/bin/bash

set -e

SERVICE_NAME=subvortex-auto-upgrader

# Determine script directory dynamically to ensure everything runs in ./scripts/api/
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/../.."

# Help function
show_help() {
    echo "Usage: $0 [--branch=<BRANCH> --tag=<TAG>]"
    echo
    echo "Options:"
    echo "  --tag         Checkout a specific Git tag before upgrading"
    echo "  --branch      Checkout a specific Git branch before upgrading (default: main)"
    echo "  --help        Show this help message"
    exit 0
}

OPTIONS="t:b:h"
LONGOPTIONS="tag:,branch:,help:"

# Parse the options and their arguments
params="$(getopt -o $OPTIONS -l $LONGOPTIONS: --name "$0" -- "$@")"

# Check for getopt errors
if [ $? -ne 0 ]; then
    exit 1
fi

TAG=""
BRANCH=$(git rev-parse --abbrev-ref HEAD)

# Parse arguments
while [ "$#" -gt 0 ]; do
    case "$1" in
        -t |--tag)
            TAG="$2"
            shift 2
            ;;
        -b |--branch)
            BRANCH="$2"
            shift 2
            ;;
        -h | --help)
            show_help
            exit 0
        ;;
        *)
            echo "Unrecognized option '$1'"
            exit 1
        ;;
    esac
done

# Track whether we stashed anything
STASHED=0

# Check for uncommitted changes
if ! git diff --quiet || ! git diff --cached --quiet; then
    echo "📦 Stashing local changes..."
    git stash push -u -m "Auto stash before pull"
    STASHED=1
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
# ./../../scripts/watchtower/watchtower_start.sh

# Start or restart the container
./deployment/process/auto_upgrader_container_start.sh

echo "✅ Auto Upgrader upgraded successfully"
