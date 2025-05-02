#!/bin/bash

set -e

# Determine script directory dynamically to ensure everything runs in ./scripts/api/
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

source ./scripts/utils/utils.sh

show_help() {
    echo "Usage:"
    echo "  $0 [--execution=process|service] [--role=miner|validator] [--clean_all] [--clean_workspace] [--clean_all_workspace] [--clean_dumps]"
    echo
    echo "Description:"
    echo "  Gracefully stops and tears down the Auto Upgrader, and optionally"
    echo "  cleans up the workspace and dump files for a fresh environment."
    echo
    echo "Options:"
    echo "  --execution           Set the execution method used to install the Auto Upgrader"
    echo "                        (choices: process, service; default: service)"
    echo "  --role                Role of the Auto Upgrader: miner or validator (default: miner)"
    echo "  --clean_all           Stop, teardown, and clean both workspace and dumps"
    echo "  --clean_workspace     Clean workspace (keep current version)"
    echo "  --clean_all_workspace Clean workspace and remove the current version"
    echo "  --clean_dumps         Clean all dump files"
    echo "  --help                Show this help message and exit"
    exit 0
}

# Defaults
EXECUTION="service"
ROLE="miner"
CLEAN_ALL=false
CLEAN_WORKSPACE=false
CLEAN_ALL_WORKSPACE=false
CLEAN_DUMPS=false

# Parse arguments
while [ "$#" -ge 1 ]; do
    case "$1" in
        -e|--execution)
            EXECUTION="$2"
            shift 2
        ;;
        --role)
            ROLE="$2"
            shift 2
        ;;
        --clean_all)
            CLEAN_ALL=true
            shift
        ;;
        --clean_workspace)
            CLEAN_WORKSPACE=true
            shift
        ;;
        --clean_all_workspace)
            CLEAN_ALL_WORKSPACE=true
            shift
        ;;
        --clean_dumps)
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

check_required_args EXECUTION ROLE

# Stop and teardown
./scripts/auto_upgrader/auto_upgrader_stop.sh --execution "$EXECUTION"
./scripts/auto_upgrader/auto_upgrader_teardown.sh --execution "$EXECUTION"

# Cleanup via central clean script
CLEAN_CMD="./scripts/auto_upgrader/clean.sh --execution $EXECUTION --role $ROLE"

if [ "$CLEAN_ALL" = true ]; then
    $CLEAN_CMD --workspace --dumps
fi

if [ "$CLEAN_WORKSPACE" = true ]; then
    $CLEAN_CMD --workspace
fi

if [ "$CLEAN_ALL_WORKSPACE" = true ]; then
    $CLEAN_CMD --workspace --remove
fi

if [ "$CLEAN_DUMPS" = true ]; then
    $CLEAN_CMD --dumps
fi
