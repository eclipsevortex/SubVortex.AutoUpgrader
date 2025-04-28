#!/usr/bin/env bash
set -euo pipefail

COMPONENT="$1"
WHEEL_IMAGE="$2"
VERSION_TAG="$3"

VERSION="${VERSION_TAG#v}"
DOCKERFILE="subvortex/$COMPONENT/Dockerfile"
REPO_OWNER="${GITHUB_REPOSITORY_OWNER:-eclipsevortex}"
REPO_NAME="subvortex-${COMPONENT//_/-}"
IMAGE="ghcr.io/$REPO_OWNER/$REPO_NAME"

echo "🔍 Building image for component: $COMPONENT"
echo "📦 Image name: $IMAGE"
echo "🏷️  Tag: $VERSION"

COMPONENT_PATH="subvortex/$COMPONENT"
if [[ -f "$COMPONENT_PATH/pyproject.toml" ]]; then
  echo "✅ Found pyproject.toml"
  COMPONENT_VERSION=$(grep -E '^version\s*=' "$COMPONENT_PATH/pyproject.toml" | head -1 | sed -E 's/version\s*=\s*"([^"]+)"/\1/')
elif [[ -f "$COMPONENT_PATH/version.py" ]]; then
  echo "✅ Found version.py"
  COMPONENT_VERSION=$(python -c "import ast; f=open('$COMPONENT_PATH/version.py'); print([n.value.s for n in ast.walk(ast.parse(f.read())) if isinstance(n, ast.Assign) and n.targets[0].id == '__version__'][0])")
else
  echo "❌ No version file found for component: $COMPONENT"
  exit 1
fi

echo "🧾 Resolved Versions:"
echo "VERSION=$VERSION"
echo "COMPONENT_VERSION=$COMPONENT_VERSION"

# -- Check if local image already matches
LABEL_KEY="$COMPONENT.$SERVICE.version"

# Try to read the label from local docker images
EXISTING_COMPONENT_VERSION=$(docker image inspect "$IMAGE:$VERSION" --format "{{ index .Config.Labels \"$LABEL_KEY\" }}" 2>/dev/null || echo "")

if [[ "$EXISTING_COMPONENT_VERSION" == "$COMPONENT_VERSION" ]]; then
  echo "✅ Image already built for $COMPONENT/$SERVICE with version $COMPONENT_VERSION. Skipping build."
  exit 0
fi

echo "🚀 Building and pushing image: $IMAGE:$VERSION"

docker buildx build \
  --squash \
  --platform linux/amd64 \
  --build-context wheelbuilder=docker-image://$WHEEL_IMAGE \
  --build-arg VERSION="$VERSION" \
  --build-arg COMPONENT_VERSION="$COMPONENT_VERSION" \
  --cache-from=type=gha,scope=wheels_${COMPONENT}_amd64 \
  --cache-to=type=gha,mode=max,scope=wheels_${COMPONENT}_amd64 \
  --label "org.opencontainers.image.source=https://github.com/${GITHUB_REPOSITORY}" \
  --tag "$IMAGE:$VERSION" \
  --file "$DOCKERFILE" \
  --push \
  .