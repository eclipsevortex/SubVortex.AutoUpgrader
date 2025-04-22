#!/bin/bash

set -e

# Help function
show_help() {
    echo "Usage: $0 [--execution=process|container|service --branch=<BRANCH> --tag=<TAG>]"
    echo
    echo "Options:"
    echo "  --execution   Specify the execution method (default: service)"
    echo "  --tag         Checkout a specific Git tag before upgrading"
    echo "  --branch      Checkout a specific Git branch before upgrading (default: main)"
    echo "  --help        Show this help message"
    exit 0
}

OPTIONS="e:t:b:h"
LONGOPTIONS="execution:,tag:,branch:,help:"

# Parse the options and their arguments
PARSED="$(getopt -o $OPTIONS -l $LONGOPTIONS: --name "$0" -- "$@")"
if [ $? -ne 0 ]; then
    exit 1
fi

# Set defaults from env (can be overridden by arguments)
EXECUTION="service"
TAG=""
BRANCH="main"

# Parse arguments
while [ "$#" -gt 0 ]; do
    case "$1" in
        -e |--execution)
            EXECUTION="$2"
            shift 2
            ;;
        -t |--tag)
            TAG="$2"
            shift 2
            ;;
        -b |--branch)
            BRANCH="$2"
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

    # Upgrade the auto upgrader as process
    ./subvortex/auto_upgrader/deployment/process/auto_upgrader_process_upgrade.sh --tag "$TAG" --branch "$BRANCH"
    
    # Add any other logic specific to process mode here
    echo "✅ Process started."
}

# 🐳 Function: Setup for container mode
setup_container() {
    echo "🐳 Setting up for 'container' mode..."
    
    # Start the auto upgrader as service
    ./subvortex/auto_upgrader/deployment/container/auto_upgrader_container_upgrade.sh --tag "$TAG" --branch "$BRANCH"
    
    # Add any other container-specific logic here
    echo "✅ Container started."
}

# 🧩 Function: Setup for service mode
setup_service() {
    echo "🧩 Setting up for 'service' mode..."
    
    # Start the auto upgrader as service
    ./subvortex/auto_upgrader/deployment/service/auto_upgrader_service_upgrade.sh --tag "$TAG" --branch "$BRANCH"
    
    # Add logic for systemd, service checks, etc. if needed
    echo "✅ Service started."
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
