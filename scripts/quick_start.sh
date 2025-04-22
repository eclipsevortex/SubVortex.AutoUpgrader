#!/bin/bash

set -e

show_help() {
    echo "Usage: $0 [--execution=process|service]"
    echo
    echo "Options:"
    echo "  --execution   Specify the execution method (default: service)"
    echo "  --help        Show this help message"
    exit 0
}

OPTIONS="e:h"
LONGOPTIONS="execution:,help:"

# Parse the options and their arguments
PARSED="$(getopt -o $OPTIONS -l $LONGOPTIONS: --name "$0" -- "$@")"
if [ $? -ne 0 ]; then
    exit 1
fi

# Set defaults from env (can be overridden by arguments)
EXECUTION="service"

# Parse arguments
while [ "$#" -gt 0 ]; do
    case "$1" in
        -e |--execution)
            EXECUTION="$2"
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

# Setup the auto upgrader
./scripts/auto_upgrader/auto_upgrader_setup.sh --execution $EXECUTION

# Start the auo upgrader
./scripts/auto_upgrader/auto_upgrader_start.sh --execution $EXECUTION