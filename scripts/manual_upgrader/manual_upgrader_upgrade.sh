#!/bin/bash

set -e

# Determine script directory dynamically to ensure everything runs in ./scripts/api/
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/../.."

# Help function
show_help() {
    echo "Usage: $0 [--execution=process|container|service]"
    echo
    echo "Description:"
    echo "  This script setup the auto upgrader"
    echo
    echo "Options:"
    echo "  --execution   Specify the execution method (default: service)"
    echo "  --neuron      Specify the neuron you want to install between miner or validator (default miner)"
    echo "  --help        Show this help message"
    exit 0
}

OPTIONS="e:n:h"
LONGOPTIONS="execution:,neurone:,help:"

# Parse the options and their arguments
PARSED="$(getopt -o $OPTIONS -l $LONGOPTIONS: --name "$0" -- "$@")"
if [ $? -ne 0 ]; then
    exit 1
fi

# Evaluate the parsed result to reset positional parameters
eval set -- "$PARSED"

# Set defaults from env (can be overridden by arguments)
EXECUTION="service"
NEURON="miner"

# Parse arguments
while true; do
    case "$1" in
        -e |--execution)
            EXECUTION="$2"
            shift 2
        ;;
        -e |--neuron)
            NEURON="$2"
            shift 2
        ;;
        -h | --help)
            show_help
            exit 0
        ;;
        --)
            shift
            break
        ;;
        *)
            echo "Unrecognized option '$1'"
            exit 1
        ;;
    esac
done

# Clean workspace?

# Download and unzip the assets

# Copy the env file


# Setup/Start the neuron
$HOME/subvortex/subvortex/$NEURON/scripts/quick_start.sh --execution "$EXECUTION"