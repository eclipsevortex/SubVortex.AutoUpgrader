#!/bin/bash

set -e

# Define the function
get_tag() {
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
