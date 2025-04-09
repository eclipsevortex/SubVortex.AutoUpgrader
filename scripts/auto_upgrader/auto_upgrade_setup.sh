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

if [[ "$METHOD" == "container" || "${SUBVORTEX_EXECUTION_METHOD,,}" == "container" ]]; then
    # Check if docker is installed
    if ! command -v docker &> /dev/null; then
        echo "❌ Docker is not installed. Installing it now."
        ./../docker/docker_setup.sh
    fi

    # Check which compose command is available
    if docker compose version &> /dev/null; then
        DOCKER_CMD="docker compose"
    elif command -v docker-compose &> /dev/null; then
        DOCKER_CMD="docker-compose"
    else
        echo "❌ Neither 'docker compose' nor 'docker-compose' is installed. Please install Docker Compose."
        exit 1
    fi
fi

# 🧠 Function: Setup for process mode
setup_process() {
    echo "⚙️  Setting up for 'process' mode..."
    
    # Install pm2
    ./scripts/install_pm2.sh
    
    # Setup the auto upgrade as process
    ./subvortex/auto_upgrader/deployment/proecss/auto_upgrader_process_setup.sh
    
    # Add any other logic specific to process mode here
    echo "✅ Process setup complete."
}

# 🐳 Function: Setup for container mode
setup_container() {
    echo "🐳 Setting up for 'container' mode..."
    
    # Install docker
    ./scripts/docker/docker_setup.sh
    
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
    case "$METHOD" in
        process)
            setup_process
        ;;
        container)
            setup_container
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
