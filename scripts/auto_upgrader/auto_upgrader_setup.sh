#!/bin/bash

set -e

# Determine script directory dynamically
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
while true; do
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

# Install if needed docker if the auto uprader is managing the upgrade of containers
if [[ "$SUBVORTEX_EXECUTION_METHOD" == "container" ]]; then
    # Check if docker is installed
    if ! command -v docker &> /dev/null; then
        echo "❌ Docker is not installed. Installing it now."
        ./scripts/docker/docker_setup.sh
    fi
fi

# 🧠 Function: Setup for process mode
setup_process() {
    echo "⚙️  Setting up for 'process' mode..."
    
    # Setup the auto upgrade as process
    ./subvortex/auto_upgrader/deployment/process/auto_upgrader_process_setup.sh
    
    # Add any other logic specific to process mode here
    echo "✅ Process setup complete."
}

# 🐳 Function: Setup for container mode
setup_container() {
    echo "🐳 Setting up for 'container' mode..."
    
    # Setup the auto upgrade as container
    ./subvortex/auto_upgrader/deployment/container/auto_upgrader_container_setup.sh
    
    # Add any other container-specific logic here
    echo "✅ Container setup complete."
}

# 🧩 Function: Setup for service mode
setup_service() {
    echo "🧩 Setting up for 'service' mode..."
    
    # Setup the auto upgrade as service
    ./subvortex/auto_upgrader/deployment/service/auto_upgrader_service_setup.sh
    
    # Add logic for systemd, service checks, etc. if needed
    echo "✅ Service setup complete."
}

# 🚀 Function: Dispatch based on method
run_setup() {
    # Install Auto Upgrade
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
            echo "❌ Unknown EXECUTION: '$EXECUTION'"
            exit 1
        ;;
    esac
}

# 🔥 Execute
run_setup
