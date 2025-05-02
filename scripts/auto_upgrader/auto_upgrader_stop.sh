#!/bin/bash

set -e

# Help function
show_help() {
    echo "Usage: $0 [--execution=process|container|service]"
    echo
    echo "Description:"
    echo "  This script stop the auto upgrader"
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

# Evaluate the parsed result to reset positional parameters
eval set -- "$PARSED"

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

# Load environment variables
export $(grep -v '^#' ./subvortex/auto_upgrader/.env | xargs)

# 🧠 Function: Setup for process mode
setup_process() {
    echo "⚙️  Stopping for 'process' mode..."
    
    # Stop the auto upgrade as process
    ./subvortex/auto_upgrader/deployment/process/auto_upgrader_process_stop.sh
    
    # Add any other logic specific to process mode here
    echo "✅ Process stopped."
}

# 🐳 Function: Setup for container mode
setup_container() {
    echo "🐳 Stopping for 'container' mode..."
    
    # Stop the auto upgrade as service
    ./subvortex/auto_upgrader/deployment/container/auto_upgrader_container_stop.sh
    
    # Add any other container-specific logic here
    echo "✅ Container stopped."
}

# 🧩 Function: Setup for service mode
setup_service() {
    echo "🧩 Stopping for 'service' mode..."
    
    # Stop the auto upgrade as service
    ./subvortex/auto_upgrader/deployment/service/auto_upgrader_service_stop.sh
    
    # Add logic for systemd, service checks, etc. if needed
    echo "✅ Service stopped."
}

# 🚀 Function: Dispatch based on method
run_setup() {
    case "$EXECUTION" in
        process)
            setup_process
        ;;
        container)
            # setup_container
            echo "⚠️  Auto Upgrader is not available to be run as container yet!"
        ;;
        service)
            setup_service
        ;;
        *)
            echo "❌ Unknown SUBVORTEX_EXECUTION_METHOD: '$EXECUTION'"
            exit 1
        ;;
    esac
}

# 🔥 Execute
run_setup
