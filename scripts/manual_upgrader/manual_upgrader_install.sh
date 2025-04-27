#!/bin/bash

set -e

# Determine script directory dynamically to ensure everything runs in ./scripts/api/
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
    echo "  --neuron      Specify the neuron you want to install between miner or validator (default miner)"
    echo "  --help        Show this help message"
    exit 0
}

OPTIONS="e:n:h"
LONGOPTIONS="execution:,neurone:,help:"

# Parse the options and their arguments
PARSED="$(getopt -o $OPTIONS -l $LONGOPTIONS: --name "$0" -- "$@")"
if [ $? -ne 0 ]; then
    exit 1
fi

# Evaluate the parsed result to reset positional parameters
eval set -- "$PARSED"

# Set defaults from env (can be overridden by arguments)
EXECUTION="service"
NEURON="miner"

# Parse arguments
while true; do
    case "$1" in
        -e |--execution)
            EXECUTION="$2"
            shift 2
        ;;
        -e |--neuron)
            NEURON="$2"
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

# Define the function
get_version() {
    local enabled="${SUBVORTEX_PRERELEASE_ENABLED:-}"
    local type="${SUBVORTEX_PRERELEASE_TYPE:-}"
    
    if [[ "$enabled" = "False" || "$enabled" = "false" ]]; then
        echo "latest"
        elif [ "$type" = "alpha" ]; then
        echo "dev"
        elif [ "$type" = "rc" ]; then
        echo "stable"
    else
        echo "latest"
    fi
}

download_and_unzip_assets() {
    local role="$1"
    local version="$2"
    local repo_owner="eclipsevortex"
    local repo_name="SubVortex"
    local asset_dir="./assets"
    
    mkdir -p "$asset_dir"
    
    # Normalize version
    local normalized_version="${version#v}"
    local archive_name="subvortex_${role}-${normalized_version}.tar.gz"
    local target_path="${asset_dir}/${archive_name}"
    local url="https://github.com/${repo_owner}/${repo_name}/releases/download/v${version}/${archive_name}"
    
    echo "🌐 Downloading: $url"
    
    if [[ ! -f "$target_path" ]]; then
        curl -fL --retry 5 --retry-delay 2 -o "$target_path" "$url"
    else
        echo "✅ Archive already downloaded: $target_path"
    fi
    
    if [[ ! -f "$target_path" ]]; then
        echo "❌ Error: Archive $target_path does not exist after download."
        exit 1
    fi
    
    echo "📦 Download complete: $target_path"
    
    # Extract
    local top_dir
    top_dir=$(tar -tzf "$target_path" | head -1 | cut -f1 -d"/")
    local target_dir="${asset_dir}/${top_dir}"
    
    if [[ -d "$target_dir" ]]; then
        echo "🧹 Removing old extracted directory: $target_dir"
        rm -rf "$target_dir"
    fi
    
    echo "📂 Extracting archive..."
    tar -xzf "$target_path" -C "$asset_dir"
    
    if [[ ! -d "$target_dir" ]]; then
        echo "❌ Error: Extraction failed to directory $target_dir"
        exit 1
    fi
    
    echo "🧹 Removing archive file: $target_path"
    rm -f "$target_path"
    
    echo "✅ Asset ready in: $target_dir"
}

# Clean workspace?
"./../cleaner/clean_worspace.sh --remove"

# Download and unzip the assets
VERSION=$(get_version)
download_and_unzip_assets "$NEURON" "$VERSION"

# Copy the env file

# Setup/Start the neuron
"./$HOME/subvortex/subvortex/$NEURON/scripts/quick_start.sh --execution \"$EXECUTION\""