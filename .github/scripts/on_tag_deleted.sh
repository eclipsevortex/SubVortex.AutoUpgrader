#!/usr/bin/env bash
set -euo pipefail

COMPONENT="$1"
SERVICE="$2"
TAG="$3"

VERSION="${TAG#v}"
REPO_OWNER="${GITHUB_REPOSITORY_OWNER:-eclipsevortex}"
REPO_NAME="subvortex-${COMPONENT//_/-}"
IMAGE="ghcr.io/$REPO_OWNER/$REPO_NAME"

GHCR_USERNAME="${GHCR_USERNAME:-}"
GHCR_TOKEN="${GHCR_TOKEN:-}"

if [[ -z "$GHCR_USERNAME" || -z "$GHCR_TOKEN" ]]; then
    echo "❌ Missing Docker credentials (GHCR_USERNAME / GHCR_TOKEN)"
    exit 1
fi

echo "🔍 Deleting $IMAGE:$VERSION from GitHub Container Registry..."

RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" -X DELETE \
    -H "Authorization: Bearer $GHCR_TOKEN" \
    -H "Accept: application/vnd.github.v3+json" \
"https://api.github.com/orgs/${GHCR_USERNAME}/packages/container/${REPO_NAME}/versions/$VERSION")

case "$RESPONSE" in
    204)
        echo "✅ Deleted $IMAGE:$VERSION"
    ;;
    404)
        echo "⚠️ Tag not found: $IMAGE:$VERSION"
    ;;
    *)
        echo "❌ Failed to delete tag: HTTP $RESPONSE"
        exit 1
    ;;
esac