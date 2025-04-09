#!/bin/bash

set -e

ENV_FILE="subvortex/auto_upgrader/.env"

# Load .env
if [ ! -f "$ENV_FILE" ]; then
    echo "❌ .env file not found!"
    exit 1
fi

export $(grep -v '^#' "$ENV_FILE" | xargs)

# Help function
print_help() {
    echo "Usage: $0 [--execution=process|container|service]"
    echo
    echo "Options:"
    echo "  --execution   Specify the execution method (default: service)"
    echo "  --help        Show this help message"
    exit 0
}

METHOD=service

# Parse arguments
for arg in "$@"; do
    case $arg in
        --execution=*)
            METHOD="${arg#*=}"
            shift
            ;;
        --help|-h)
            print_help
            ;;
        *)
            echo "❌ Unknown option: $arg"
            print_help
            ;;
    esac
done

# Setup the auto upgrader
./auto_upgrader/auto_upgrader.setup.sh --execution $METHOD

# Start the auo upgrader
./auto_upgrader/auto_upgrader.start.sh --execution $METHOD