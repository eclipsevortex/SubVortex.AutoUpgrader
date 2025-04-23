#!/bin/bash

set -e

# Determine script directory dynamically to ensure everything runs in ./scripts/api/
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/../.."

source ./scripts/utils/utils.sh

show_help() {
    echo "Usage: $0 [--execution=process|service]"
    echo
    echo "Description:"
    echo "  This script restart the miner's components"
    echo
    echo "Options:"
    echo "  --execution   Specify the execution method (default: service)"
    echo "  --recreate    True if you want to recreate the container when starting it, false otherwise."
    echo "  --help        Show this help message"
    exit 0
}

OPTIONS="e:rh"
LONGOPTIONS="execution:recreate,help"

# Parse the options and their arguments
params="$(getopt -o $OPTIONS -l $LONGOPTIONS: --name "$0" -- "$@")"

# Parse the options and their arguments
PARSED="$(getopt -o $OPTIONS -l $LONGOPTIONS: --name "$0" -- "$@")"
if [ $? -ne 0 ]; then
    exit 1
fi

# Load from .env if exists
if [ -f ./subvortex/auto_upgrader/.env ]; then
    export $(grep -v '^#' ./subvortex/auto_upgrader/.env | xargs)
fi

# Determinate flag and expose it as env var
export SUBVORTEX_FLOATTING_FLAG=$(get_tag)

# Set defaults from env (can be overridden by arguments)
EXECUTION="${SUBVORTEX_EXECUTION_METHOD:-}"
RECREATE=false

# Parse arguments
while [ "$#" -gt 0 ]; do
    case "$1" in
        -e |--execution)
            EXECUTION="$2"
            shift 2
        ;;
        -r|--recreate)
            RECREATE=true
            shift
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

# Expand ~ and assign directory
execution_dir="$HOME/subvortex/subvortex/miner"

# Check if directory exists
if [ ! -d "$execution_dir" ]; then
    echo "❌ Error: Execution directory '$execution_dir' does not exist."
    exit 1
fi

# Build the command and arguments
CMD="$execution_dir/scripts/quick_restart.sh --execution $EXECUTION"
if [[ "$RECREATE" == "true" || "$RECREATE" == "True" ]]; then
    CMD+=" --recreate"
fi

# Setup the auto upgrade as container
eval "$CMD"