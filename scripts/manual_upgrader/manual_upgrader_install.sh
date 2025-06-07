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
    echo "  --branch      Specify the branch you want to install"
    echo "  --neuron      Specify the neuron you want to install between miner or validator (default miner)"
    echo "  --help        Show this help message"
    exit 0
}

OPTIONS="e:n:b:h"
LONGOPTIONS="execution:,neuron:,branch:,help:"

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
BRANCH=""

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
        -b |--branch)
            BRANCH="$2"
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

stop_auto_upgrader() {
    echo "🛑 Attempting to stop auto upgrader (subvortex-auto-upgrader)..."
    
    # Try PM2
    if command -v pm2 &>/dev/null && pm2 list | grep -q "subvortex-auto-upgrader"; then
        echo "⚙️ Stopping via PM2"
        pm2 stop subvortex-auto-upgrader || true
        return
    fi
    
    # Try systemd
    if systemctl list-units --type=service --all | grep -q "subvortex-auto-upgrader.service"; then
        echo "⚙️ Stopping via systemd"
        sudo systemctl stop subvortex-auto-upgrader.service || true
        return
    fi
    
    # Try Docker
    if command -v docker &>/dev/null && docker ps -a --format '{{.Names}}' | grep -q "^subvortex-auto-upgrader$"; then
        echo "⚙️ Stopping via Docker"
        docker stop subvortex-auto-upgrader || true
        return
    fi
    
    echo "⚠️ Auto upgrader not running via PM2, systemd, or Docker."
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

clone_branch() {
    local branch="$1"
    local repo="https://github.com/eclipsevortex/SubVortex.git"
    local base_dir="/var/tmp/subvortex"
    local clone_dir="${base_dir}/subvortex-${branch}"

    echo "🌱 Cloning branch '$branch' into: $clone_dir"
    mkdir -p "$base_dir"
    [[ -d "$clone_dir" ]] && rm -rf "$clone_dir"

    git clone --branch "$branch" --depth 1 "$repo" "$clone_dir" || {
        echo "❌ Failed to clone branch '$branch'"
        exit 1
    }

    # Locate version file
    local version_file="$clone_dir/VERSION"
    if [[ ! -f "$version_file" ]]; then
        echo "❌ Error: Could not find version file in $clone_dir"
        exit 1
    fi

    # Read and normalize version
    local version
    version="$(<"$version_file" tr -d '[:space:]')"
    [[ -z "$version" ]] && { echo "❌ Error: Version file is empty"; exit 1; }

    local norm_version="${version//alpha/a}"
    norm_version="${norm_version//-rc/-rc}"

    # Append branch name to directory
    local target_dir="${base_dir}/subvortex-${norm_version}-${branch}"

    echo "🔁 Renaming $clone_dir → $target_dir"
    rm -rf "$target_dir"
    mv "$clone_dir" "$target_dir"

    # Optionally copy the neuron-specific pyproject.toml
    local py_src="${target_dir}/pyproject-${NEURON}.toml"
    local py_dst="${target_dir}/pyproject.toml"
    if [[ -f "$py_src" ]]; then
        echo "📄 Copying $py_src → $py_dst"
        cp "$py_src" "$py_dst"
    else
        echo "⚠️  $py_src not found, skipping pyproject.toml override"
    fi

    # Set global variable for neuron path
    SUBVORTEX_DIR="${target_dir}/subvortex"
    echo "✅ Branch ready in: $SUBVORTEX_DIR"
}

copy_env_files() {
    local source_dir="./subvortex/auto_upgrader/environment"
    local prefix="env.subvortex.${NEURON}."
    
    echo "📁 Searching for env files in: $source_dir matching $prefix*"
    for env_file in "$source_dir"/${prefix}*; do
        [[ -f "$env_file" ]] || continue
        
        local filename
        filename="$(basename "$env_file")"
        local component="${filename#$prefix}"  # Extract component name
        
        local target_dir="$SUBVORTEX_DIR/$NEURON/$component"
        local target_path="${target_dir}/.env"
        
        echo "📄 Copying $filename → $target_path"
        mkdir -p "$target_dir"
        cp "$env_file" "$target_path"
    done
}

get_sorted_components() {
    local source_dir="./subvortex/auto_upgrader/environment"
    local prefix="env.subvortex.${NEURON}."
    local components=()
    declare -A dependencies

    for env_file in "$source_dir"/${prefix}*; do
        [[ -f "$env_file" ]] || continue
        local filename="$(basename "$env_file")"
        local component="${filename#$prefix}"
        components+=("$component")

        local manifest="$SUBVORTEX_DIR/${NEURON}/${component}/manifest.json"
        if [[ -f "$manifest" ]]; then
            local deps
            deps=$(jq -r '.depends_on[]?' "$manifest")
            dependencies["$component"]="$deps"
        else
            dependencies["$component"]=""
        fi
    done

    local sorted=()
    declare -A visited

    visit() {
        local comp="$1"
        [[ ${visited[$comp]} == 1 ]] && return
        visited[$comp]=1

        for dep in ${dependencies[$comp]}; do
            local dep_name="${dep#${NEURON}-}"
            visit "$dep_name"
        done
        sorted+=("$comp")
    }

    for comp in "${components[@]}"; do
        visit "$comp"
    done

    echo "${sorted[@]}"
}

setup_components() {
    local source_dir="./subvortex/auto_upgrader/environment"
    local prefix="env.subvortex.${NEURON}."

    echo "🛠️ Setting up components for neuron: $NEURON"

    for env_file in "$source_dir"/${prefix}*; do
        [[ -f "$env_file" ]] || continue

        local filename
        filename="$(basename "$env_file")"
        local component="${filename#$prefix}"

        # Get absolute path to /var/tmp/subvortex/... repo
        local full_repo_path
        full_repo_path="$(dirname "$SUBVORTEX_DIR")"

        local script="${full_repo_path}/subvortex/${NEURON}/${component}/scripts/${component}_setup.sh"

        if [[ -x "$script" ]]; then
            echo "⚙️  Setting up component: $component"
            "$script" --execution "$EXECUTION"
        else
            echo "⚠️  Setup script not found or not executable: $script"
        fi
    done
}

start_components() {
    local sorted_components=( $(get_sorted_components) )

    echo "🚀 Starting components for neuron: $NEURON"
    for component in "${sorted_components[@]}"; do
        local script="/root/subvortex/subvortex/${NEURON}/${component}/scripts/${component}_start.sh"
        if [[ -x "$script" ]]; then
            echo "➡️  Starting component: $component"
            "$script" --execution "$EXECUTION"
        else
            echo "⚠️  Start script not found or not executable: $script"
        fi
    done
}

stop_components() {
    local sorted_components=( $(get_sorted_components) )
    local reversed_components=( $(for (( idx=${#sorted_components[@]}-1 ; idx>=0 ; idx-- )) ; do echo "${sorted_components[idx]}" ; done) )

    echo "🛑 Stopping existing components for neuron: $NEURON"
    for (( idx=${#sorted_components[@]}-1 ; idx>=0 ; idx-- )); do
        local component="${sorted_components[idx]}"
        local script="/root/subvortex/subvortex/${NEURON}/${component}/scripts/${component}_stop.sh"
        if [[ -x "$script" ]]; then
            echo "➡️  Stopping component: $component"
            "$script" --execution "$EXECUTION"
        else
            echo "⚠️  Stop script not found or not executable: $script"
        fi
    done
}

# Ask the user for migration confirmation
echo "⚠️ WARNING: This script does not handle data migration between versions."
echo "You are about to proceed with installation without preserving or migrating previous data."
read -rp "Do you want to continue? [y/N]: " confirm
if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
    echo "❌ Operation cancelled. Migration step must be handled manually."
    exit 1
fi

# Stop auto upgader
stop_auto_upgrader

# Download the assets or git pull a specific branch
if [[ -n "$BRANCH" ]]; then
    # Clone the version
    clone_branch "$BRANCH"
else
    # Download and unzip the assets
    VERSION=$(get_version)
    download_and_unzip_assets "$NEURON" "$VERSION"
fi

# Copy the env file
copy_env_files

# Setup components (new version)
setup_components

# Stop components (old version)
stop_components

# Update or create /root/subvortex symlink
echo "🔗 Managing symlink: /root/subvortex"
if [[ -L /root/subvortex || -e /root/subvortex ]]; then
    echo "🔄 Updating existing symlink or file"
    rm -rf /root/subvortex
fi
ln -s "$(dirname "$SUBVORTEX_DIR")" /root/subvortex
echo "✅ /root/subvortex → $(readlink -f /root/subvortex)"

# Start component (new version)
start_components

# TODO: implement the migration

# Clean prune version
./scripts/quick_clean.sh --workspace