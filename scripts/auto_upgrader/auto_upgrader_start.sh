#!/bin/bash

set -e

# Help function
show_help() {
    echo "Usage: $0 [--execution=process|container|service]"
    echo
    echo "Options:"
    echo "  --execution   Specify the execution method (default: service)"
    echo "  --help        Show this help message"
    exit 0
}

OPTIONS="e:h"
LONGOPTIONS="execution:,help:"

# Parse the options and their arguments
params="$(getopt -o $OPTIONS -l $LONGOPTIONS: --name "$0" -- "$@")"

# Check for getopt errors
if [ $? -ne 0 ]; then
    exit 1
fi

METHOD=service

# Parse arguments
while [ "$#" -gt 0 ]; do
    case "$1" in
        -e |--execution)
            METHOD="$2"
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

# Parse arguments
while [ "$#" -gt 0 ]; do
    case "$1" in
        -e |--execution)
            METHOD="$2"
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

# 🧠 Function: Setup for process mode
setup_process() {
    echo "⚙️  Setting up for 'process' mode..."
    
    # Start the auto upgrade as process
    ./subvortex/auto_upgrader/deployment/process/auto_upgrader_process_start.sh
    
    # Add any other logic specific to process mode here
    echo "✅ Process started."
}

# 🐳 Function: Setup for container mode
setup_container() {
    echo "🐳 Setting up for 'container' mode..."
    
    # Start the auto upgrade as service
    ./subvortex/auto_upgrader/deployment/container/auto_upgrader_container_start.sh
    
    # Add any other container-specific logic here
    echo "✅ Container started."
}

# 🧩 Function: Setup for service mode
setup_service() {
    echo "🧩 Setting up for 'service' mode..."
    
    # Start the auto upgrade as service
    ./subvortex/auto_upgrader/deployment/service/auto_upgrader_service_start.sh
    
    # Add logic for systemd, service checks, etc. if needed
    echo "✅ Service started."
}

# 🚀 Function: Dispatch based on method
run_setup() {
    if [[ "$SUBVORTEX_EXECUTION_METHOD" == "container" ]]; then
        ./scripts/watchtower/watchtower_start.sh
    fi

    case "$METHOD" in
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
            echo "❌ Unknown SUBVORTEX_EXECUTION_METHOD: '$METHOD'"
            exit 1
        ;;
    esac
}

# 🔥 Execute
run_setup
