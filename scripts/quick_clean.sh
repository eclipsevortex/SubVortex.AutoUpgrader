#!/bin/bash

set -e

# Determine script directory dynamically
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

source ./scripts/utils/utils.sh

show_help() {
    echo "Usage:"
    echo "  $0 [--execution=process|service] [--role=miner|validator] [--remove] [--workspace] [--dumps]"
    echo
    echo "Description:"
    echo "  Cleans the Auto Upgrader workspace and/or dumps. Optionally removes the current version."
    echo
    echo "Options:"
    echo "  --execution   Execution method (default: from .env)"
    echo "  --role        Role of the Auto Upgrader: miner or validator (default: from .env)"
    echo "  --workspace   Clean workspace (default: false)"
    echo "  --dumps       Clean dumps (default: false)"
    echo "  --remove      Also remove the latest version (will stop the component)"
    echo "  --help        Show this help message"
    exit 0
}

EXECUTION="service"
ROLE="miner"
REMOVE_LATEST=false
CLEAN_WORKSPACE=false
CLEAN_DUMPS=false

while [ "$#" -ge 1 ]; do
    case "$1" in
        -e|--execution)
            EXECUTION="$2"
            shift 2
        ;;
        -o|--role)
            ROLE="$2"
            shift 2
        ;;
        --remove)
            REMOVE_LATEST=true
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

check_required_args EXECUTION ROLE

if [[ "$REMOVE_LATEST" == "true" ]]; then
    "./scripts/$ROLE/quick_stop.sh" --execution "$EXECUTION"
fi

if [[ "$CLEAN_WORKSPACE" == "true" ]]; then
    if [[ "$REMOVE_LATEST" == "true" ]]; then
        ./scripts/cleaner/clean_workspace.sh --remove
    else
        ./scripts/cleaner/clean_workspace.sh
    fi
fi

if [[ "$CLEAN_DUMPS" == "true" ]]; then
    ./scripts/cleaner/clean_dumps.sh
fi
