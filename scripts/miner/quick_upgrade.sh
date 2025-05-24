#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/../.."

source ./scripts/utils/utils.sh

show_help() {
    echo "Usage: $0 [--execution=process|service]"
    echo
    echo "Description:"
    echo "  Dynamically restarts and migrates all miner services based on manifest dependencies"
    echo
    echo "Options:"
    echo "  --execution   Specify the execution method (default: service)"
    echo "  --help        Show this help message"
    exit 0
}

EXECUTION="${SUBVORTEX_EXECUTION_METHOD:-service}"

while [ "$#" -ge 1 ]; do
    case "$1" in
        -e|--execution)
            EXECUTION="$2"
            shift 2
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

check_required_args EXECUTION

if [ -f ./subvortex/auto_upgrader/.env ]; then
    export $(grep -v '^#' ./subvortex/auto_upgrader/.env | xargs)
fi

export SUBVORTEX_FLOATTING_FLAG=$(get_tag)
export SUBVORTEX_WORKING_DIR="$HOME/subvortex"
neuron_dir="$SUBVORTEX_WORKING_DIR/subvortex/miner"

if [ ! -d "$neuron_dir" ]; then
    echo "❌ Error: Neuron directory '$neuron_dir' does not exist."
    exit 1
fi

# Build dependency graph
declare -A deps
declare -A scripts
services=()

for service_path in "$neuron_dir"/*; do
    [ -d "$service_path" ] || continue
    service=$(basename "$service_path")
    manifest="$service_path/manifest.json"

    if [ ! -f "$manifest" ]; then
        echo "⚠️ Skipping '$service': no manifest.json"
        continue
    fi

    depends_on=$(jq -r '.depends_on // [] | join(" ")' "$manifest")
    deps[$service]="$depends_on"
    scripts[$service]="$service_path"
    services+=("$service")

done

# Topological sort
toposort() {
    local visited=()
    local order=()

    visit() {
        local s="$1"
        [[ " ${visited[*]} " =~ " $s " ]] && return
        visited+=("$s")
        for d in ${deps[$s]}; do
            visit "$d"
        done
        order+=("$s")
    }

    for s in "${services[@]}"; do
        visit "$s"
    done

    echo "${order[@]}"
}

sorted_services=($(toposort))

# Setup all services
for svc in "${sorted_services[@]}"; do
    echo "🔧 Setting up $svc..."
    "$neuron_dir/$svc/scripts/${svc}_setup.sh" --execution $EXECUTION
    echo "✅ $svc setup complete"
done

# Dump Redis before restart
python3 ./scripts/redis/redis_dump.py --run_type create

# Restart Redis
"$neuron_dir/redis/scripts/redis_start.sh" --execution $EXECUTION

# Migrate Redis
python3 "$neuron_dir/scripts/redis/redis_migration.py" --neuron miner

# Start all services
for svc in "${sorted_services[@]}"; do
    echo "🚀 Starting $svc..."
    "$neuron_dir/$svc/scripts/${svc}_start.sh" --execution $EXECUTION
    echo "✅ $svc started"
done
