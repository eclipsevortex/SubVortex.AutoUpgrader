#!/bin/bash

set -e

# Determine script directory dynamically to ensure everything runs in ./scripts/api/
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

source ./scripts/utils/utils.sh

show_help() {
    echo "Usage:"
    echo "  $0 [--execution=process|service] [--role=miner|validator]"
    echo
    echo "Description:"
    echo "  Gracefully stops and tears down the Auto Upgrader, and optionally"
    echo "  cleans up the workspace and dump files for a fresh environment."
    echo
    echo "Options:"
    echo "  --execution           Set the execution method used to install the Auto Upgrader"
    echo "                        (choices: process, service; default: service)"
    echo "  --role                Role of the Auto Upgrader: miner or validator (default: miner)"
    echo "  --help                Show this help message and exit"
    exit 0
}

# Defaults
EXECUTION="service"
ROLE="miner"

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
