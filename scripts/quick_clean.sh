#!/bin/bash

set -e

# Determine script directory dynamically
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

source ./scripts/utils/utils.sh

show_help() {
    echo "Usage:"
    echo "  $0 [--remove] [--force] [--workspace] [--dumps]"
    echo
    echo "Description:"
    echo "  Cleans the Auto Upgrader workspace and/or dumps. Optionally removes or marks the current version for reinstall."
    echo
    echo "Options:"
    echo "  --workspace   Clean workspace (default: false)"
    echo "  --dumps       Clean dumps (default: false)"
    echo "  --remove      Remove the current version (will stop the component)"
    echo "  --force       Mark current version for reinstall"
    echo "  --help        Show this help message"
    exit 0
}

# Default values
REMOVE_LATEST=false
FORCE_REINSTALL=false
CLEAN_WORKSPACE=false
CLEAN_DUMPS=false

# Parse arguments
while [ "$#" -ge 1 ]; do
    case "$1" in
        --remove)
            REMOVE_LATEST=true
            shift
            ;;
        --force)
            FORCE_REINSTALL=true
            shift
            ;;
        --workspace)
            CLEAN_WORKSPACE=true
            shift
            ;;
        --dumps)
            CLEAN_DUMPS=true
            shift
            ;;
        -h|--help)
            show_help
            ;;
        *)
            echo "❌ Unrecognized option '$1'"
            exit 1
            ;;
    esac
done

# Build clean_workspace command
if [[ "$CLEAN_WORKSPACE" == "true" || "$FORCE_REINSTALL" == "true" ]]; then
    CLEAN_CMD="./scripts/cleaner/clean_workspace.sh"
    [[ "$REMOVE_LATEST" == "true" ]] && CLEAN_CMD+=" --remove"
    [[ "$FORCE_REINSTALL" == "true" ]] && CLEAN_CMD+=" --force"
    eval "$CLEAN_CMD"
fi

# Clean dumps
if [[ "$CLEAN_DUMPS" == "true" ]]; then
    ./scripts/cleaner/clean_dumps.sh
fi
