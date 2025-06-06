#!/bin/bash

set -e

# Determine script directory dynamically to ensure everything runs in ./scripts/api/
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

source ./scripts/utils/utils.sh

show_help() {
    echo "Usage: $0 [--execution=process|service]"
    echo
    echo "Description:"
    echo "  This script setup and start the auto upgrader"
    echo
    echo "Options:"
    echo "  --execution   Specify the execution method to install the Auto Upgrader(default: service)"
    echo "  --help        Show this help message"
    exit 0
}

OPTIONS="e:h"
LONGOPTIONS="execution:,help:"

# Set defaults from env (can be overridden by arguments)
EXECUTION="service"
# Parse command-line arguments
while [ "$#" -ge 1 ]; do
    case "$1" in
        -e|--execution)
            EXECUTION="$2"
            shift 2
        ;;
        -h|--help)
            show_help
        ;;
        --)
            shift
            break
        ;;
        *)
            echo "❌ Unrecognized option '$1'"
            exit 1
        ;;
    esac
done

# Check maandatory args
check_required_args EXECUTION

# Setup the auto upgrader
./scripts/auto_upgrader/auto_upgrader_setup.sh --execution "$EXECUTION"

# Start the auo upgrader
./scripts/auto_upgrader/auto_upgrader_start.sh --execution "$EXECUTION"