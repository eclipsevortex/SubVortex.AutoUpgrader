import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock

from subvortex.auto_upgrader.src.docker import Docker


@pytest.mark.asyncio
@patch("subvortex.auto_upgrader.src.docker.sauu.get_tag", return_value="dev")
@patch("asyncio.create_subprocess_exec")
async def test_get_latest_version_success(mock_subproc_exec, mock_get_tag):
    docker = Docker()

    # Mock docker search to return image list
    search_proc = AsyncMock()
    search_proc.communicate.return_value = (b"subvortex/subvortex-miner-neuron\n", b"")
    mock_subproc_exec.side_effect = [search_proc]

    # Inject image digest + label steps (pull + inspect)
    pull_proc = AsyncMock()
    pull_proc.communicate.return_value = (b"Pulled", b"")

    inspect_proc = AsyncMock()
    labels = "version=1.0.2 miner.version=1.0.1 miner.neuron.version=1.0.0"
    inspect_proc.communicate.return_value = (
        labels.encode(),
        b"",
    )

    # Add pull + inspect after search
    mock_subproc_exec.side_effect = [search_proc, pull_proc, inspect_proc]

    result = await docker.get_latest_version()

    assert result == "1.0.2"
    assert docker.latest_versions["neuron"]["version"] == "1.0.2"
    assert docker.latest_versions["neuron"]["miner.version"] == "1.0.1"
    assert docker.latest_versions["neuron"]["miner.neuron.version"] == "1.0.0"


@pytest.mark.asyncio
@patch("subvortex.auto_upgrader.src.docker.sauu.get_tag", return_value="dev")
@patch("subprocess.run")
def test_get_local_version_filters_only_dev_tags(mock_run, mock_get_tag):
    docker = Docker()

    # Step 1: Mock `docker image ls` output with mostly `<none>` tags
    mock_run.side_effect = [
        # First call: `docker image ls`
        MagicMock(
            stdout=(
                "subvortex/subvortex-miner-neuron:dev\n"
                "subvortex/subvortex-miner-redis:dev\n"
            ),
            returncode=0,
        ),
        # Second call: `docker inspect` for validator-neuron:dev
        MagicMock(
            stdout="version=1.0.0 miner.version=1.0.0 miner.neuron.version=1.0.0",
            returncode=0,
        ),
        # Third call: `docker inspect` for validator-redis:dev
        MagicMock(
            stdout="version=1.0.0 miner.version=1.0.0 miner.redis.version=1.0.0",
            returncode=0,
        ),
    ]

    loop = asyncio.get_event_loop()
    result = loop.run_until_complete(docker.get_local_version())

    # Assert
    assert result == "1.0.0"
    assert docker.local_versions["neuron"]["version"] == "1.0.0"
    assert docker.local_versions["redis"]["version"] == "1.0.0"
    assert docker.local_versions["version"] == "1.0.0"
