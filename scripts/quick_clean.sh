#!/bin/bash

set -e

show_help() {
    echo "Usage: $0 [--execution=process|service] [--role=miner|validator] [--remove]"
    echo
    echo "Description:"
    echo "  This script clean the working directory of the Auto Uprader"
    echo "  without removing the lastest version."
    echo "  If you remove the latest version, the components will be stopped and teardown"
    echo
    echo "Options:"
    echo "  --execution   Specify the execution method (default: taken from .env)"
    echo "  --role        Role of the Auto Upgrader between miner or validator (default: taken from .env)"
    echo "  --remove      True if you want to remove the latest version, false otherwise (default: false)"
    echo "  --help        Show this help message"
    exit 0
}

OPTIONS="e:o:rh"
LONGOPTIONS="execution:,role:,remove,help"

# Parse the options and their arguments
PARSED=$(getopt --options=$OPTIONS --longoptions=$LONGOPTIONS --name "$0" -- "$@")
if [ $? -ne 0 ]; then
    exit 1
fi
eval set -- "$PARSED"

# Set defaults from env (can be overridden by arguments)
EXECUTION="service"
ROLE="miner"
REMOVE_LATEST=false

# Parse command-line arguments
while true; do
    case "$1" in
        -e|--execution)
            EXECUTION="$2"
            shift 2
        ;;
        -o|--role)
            ROLE="$2"
            shift 2
        ;;
        -r|--remove)
            REMOVE_LATEST=true
            shift
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

# Validate EXECUTION and ROLE
if [ -z "$EXECUTION" ]; then
    echo "❌ Error: --execution not provided and EXECUTION not set in .env"
    exit 1
fi

if [ -z "$ROLE" ]; then
    echo "❌ Error: --role not provided and ROLE not set in .env"
    exit 1
fi

# Stop the neuron if requested
if [[ "$REMOVE_LATEST" == "true" ]]; then
    "./script/$ROLE/quick_stop.sh" --execution "$EXECUTION"
fi

# Clean the workspace with --remove if requested
CLEAN_CMD="./scripts/cleaner/clean_worspace.sh"
if [[ "$REMOVE_LATEST" == "true" ]]; then
    CLEAN_CMD+=" --remove"
fi

eval "$CLEAN_CMD"
