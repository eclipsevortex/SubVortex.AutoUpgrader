#!/bin/bash

set -e

# Determine script directory dynamically to ensure everything runs in ./scripts/api/
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/../.."

# Help function
show_help() {
    echo "Usage: $0 [--branch=<BRANCH> --tag=<TAG>]"
    echo
    echo "Options:"
    echo "  --branch      Checkout a specific Git branch before upgrading (default: main)"
    echo "  --help        Show this help message"
    exit 0
}

OPTIONS="b:h"
LONGOPTIONS="branch:,help:"

# Parse the options and their arguments
params="$(getopt -o $OPTIONS -l $LONGOPTIONS: --name "$0" -- "$@")"

# Check for getopt errors
if [ $? -ne 0 ]; then
    exit 1
fi

BRANCH=$(git rev-parse --abbrev-ref HEAD)

# Parse arguments
while [ "$#" -gt 0 ]; do
    case "$1" in
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

# Check if docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Installing it now."
    ./../../scripts/docker/docker_setup.sh
fi

# Track whether we stashed anything
STASHED=0

# Check for uncommitted changes
if ! git diff --quiet || ! git diff --cached --quiet; then
    echo "📦 Stashing local changes..."
    git stash push -u -m "Auto stash before pull"
    STASHED=1
fi

# Check if branch is tracking remote
UPSTREAM=$(git rev-parse --abbrev-ref "$BRANCH@{upstream}" 2>/dev/null || true)

if [[ -z "$UPSTREAM" ]]; then
    echo "⚠️ Branch '$BRANCH' is not tracking a remote. Setting upstream to 'origin/$BRANCH'..."
    git branch --set-upstream-to=origin/"$BRANCH" "$BRANCH" || {
        echo "❌ Failed to set upstream for branch '$BRANCH'."
        exit 1
    }
    UPSTREAM="origin/$BRANCH"
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

echo "✅ Auto Upgrader setup successfully"
