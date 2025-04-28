# The MIT License (MIT)
# Copyright © 2025 Eclipse Vortex
import pytest
from unittest.mock import patch, MagicMock

import subvortex.auto_upgrader.src.constants as sauc

from subvortex.auto_upgrader.src.github import Github


@patch("subvortex.auto_upgrader.src.constants.SV_EXECUTION_METHOD", "service")
@patch("subvortex.auto_upgrader.src.github.os.listdir")
@patch("subvortex.auto_upgrader.src.github.os.path.isdir")
def test_get_local_version_service_returns_version(mock_isdir, mock_listdir):
    # Arrange
    github = Github()

    # Simulate /var/tmp/subvortex directory listing
    mock_listdir.return_value = [
        "subvortex-1.2.3",  # Valid version folder
        "subvortex-1.1.0",  # Older valid version
        "random-folder",  # Should be ignored
    ]

    # Simulate os.path.isdir always returning True
    mock_isdir.return_value = True

    # Act
    version = github.get_local_version()

    # Assert
    assert version == "1.2.3"
    mock_listdir.assert_called_once_with("/var/tmp/subvortex")
    assert mock_isdir.call_count == 4


@patch("subvortex.auto_upgrader.src.constants.SV_EXECUTION_METHOD", "service")
@patch("subvortex.auto_upgrader.src.github.os.listdir")
@patch("subvortex.auto_upgrader.src.github.os.path.isdir")
def test_get_local_version_service_returns_none_when_no_valid_versions(
    mock_isdir, mock_listdir
):
    # Arrange
    github = Github()

    # Simulate /var/tmp/subvortex directory listing with no valid versions
    mock_listdir.return_value = [
        "random-folder",
        "another-folder",
        "not-a-version",
    ]

    # Simulate os.path.isdir always returning True
    mock_isdir.return_value = True

    # Act
    version = github.get_local_version()

    # Assert
    assert version is None
    mock_listdir.assert_called_once_with("/var/tmp/subvortex")
    assert mock_isdir.call_count == 4  # 1 check for base dir + 3 entries


@patch("subvortex.auto_upgrader.src.github.requests.get")
def test_get_latest_version_returns_version(mock_requests_get):
    # Arrange
    github = Github()

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {"tag_name": "v1.2.3", "published_at": "2025-04-20T12:34:56Z"},
    ]
    mock_requests_get.return_value = mock_response

    # Act
    version, published_at = github.get_latest_version()

    # Assert
    assert version == "1.2.3"
    assert published_at == "2025-04-20T12:34:56Z"
    mock_requests_get.assert_called_once()


@patch("subvortex.auto_upgrader.src.github.requests.get")
def test_get_latest_version_returns_none_when_no_releases(mock_requests_get):
    # Arrange
    github = Github()

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = []
    mock_requests_get.return_value = mock_response

    # Act
    version, published_at = github.get_latest_version()

    # Assert
    assert version is None
    assert published_at is None
    mock_requests_get.assert_called_once()


@patch("subvortex.auto_upgrader.src.github.requests.get")
def test_get_latest_version_raises_on_api_error(mock_requests_get):
    # Arrange
    github = Github()

    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.raise_for_status.side_effect = Exception("API Error")
    mock_requests_get.return_value = mock_response

    # Act & Assert
    with pytest.raises(Exception) as excinfo:
        github.get_latest_version()
    assert "API Error" in str(excinfo.value)
    mock_requests_get.assert_called_once()


@patch("subvortex.auto_upgrader.src.constants.SV_EXECUTION_METHOD", "container")
@patch("subvortex.auto_upgrader.src.github.requests.get")
def test_get_latest_version_container_returns_version(mock_requests_get):
    # Arrange
    github = Github()

    # Mock latest tag
    latest_tag_response = MagicMock()
    latest_tag_response.status_code = 200
    latest_tag_response.json.return_value = [
        {"tag_name": "v1.2.3", "published_at": "2025-04-20T12:34:56Z"},
    ]

    # Mock packages list response
    packages_response = MagicMock()
    packages_response.status_code = 200
    packages_response.json.return_value = [
        {"name": "subvortex-miner-neuron"},
    ]

    # Mock versions list response for miner
    versions_response = MagicMock()
    versions_response.status_code = 200
    versions_response.json.return_value = [
        {
            "created_at": "2025-04-21T12:34:56Z",
            "metadata": {"container": {"tags": ["v1.2.3", "latest"]}},
        }
    ]

    # Mock requests.get calls: first call -> list packages, second call -> versions
    mock_requests_get.side_effect = [
        latest_tag_response,
        packages_response,
        versions_response,
    ]

    # Act
    version, published_at = github.get_latest_version()

    # Assert
    assert version == "1.2.3"
    assert published_at == "2025-04-21T12:34:56Z"
    assert mock_requests_get.call_count == 3


@patch("subvortex.auto_upgrader.src.constants.SV_EXECUTION_METHOD", "container")
@patch("subvortex.auto_upgrader.src.github.requests.get")
def test_get_latest_version_container_returns_none_when_no_packages(mock_requests_get):
    # Arrange
    github = Github()

    # Mock latest tag
    latest_tag_response = MagicMock()
    latest_tag_response.status_code = 200
    latest_tag_response.json.return_value = [
        {"tag_name": "v1.2.3", "published_at": "2025-04-20T12:34:56Z"},
    ]

    # Mock packages list response (empty list)
    packages_response = MagicMock()
    packages_response.status_code = 200
    packages_response.json.return_value = []

    mock_requests_get.side_effect = [latest_tag_response, packages_response]

    # Act
    version, published_at = github.get_latest_version()

    # Assert
    assert version is None
    assert published_at is None
    assert mock_requests_get.call_count == 2


@patch("subvortex.auto_upgrader.src.constants.SV_EXECUTION_METHOD", "container")
@patch("subvortex.auto_upgrader.src.github.requests.get")
def test_get_latest_version_container_raises_on_api_error(mock_requests_get):
    # Arrange
    github = Github()

    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.raise_for_status.side_effect = Exception("API Error")
    mock_requests_get.return_value = mock_response

    # Act & Assert
    with pytest.raises(Exception) as excinfo:
        github.get_latest_version()
    assert "API Error" in str(excinfo.value)
    mock_requests_get.assert_called_once()


@patch("subvortex.auto_upgrader.src.constants.SV_EXECUTION_METHOD", "container")
@patch("subvortex.auto_upgrader.src.github.subprocess.run")
def test_get_local_version_container_returns_version(mock_subprocess_run):
    # Arrange
    github = Github()

    # Mock subprocess.run() behavior:
    # First call: docker image ls
    # Second call: docker inspect
    mock_subprocess_run.side_effect = [
        MagicMock(
            stdout="ghcr.io/eclipsevortex/subvortex-miner-neuron:dev\n", returncode=0
        ),
        MagicMock(
            stdout='{"version": "1.2.3", "neuron": { "version": "1.2.3", "miner.version": "1.2.3", "miner.neuron.version": "1.2.3" }}',
            returncode=0,
        ),
    ]

    # Patch get_tag to return the expected floating tag
    with patch("subvortex.auto_upgrader.src.github.sauu.get_tag", return_value="dev"):
        version = github.get_local_version()

    # Assert
    assert version == "1.2.3"
    assert mock_subprocess_run.call_count == 2


@patch("subvortex.auto_upgrader.src.constants.SV_EXECUTION_METHOD", "container")
@patch("subvortex.auto_upgrader.src.github.subprocess.run")
def test_get_local_version_container_returns_none_when_no_valid_images(
    mock_subprocess_run,
):
    # Arrange
    github = Github()

    # Mock subprocess.run() behavior:
    # First call: docker image ls (no matching images)
    mock_subprocess_run.return_value = MagicMock(
        stdout="",  # No images listed
        returncode=0,
    )

    # Patch get_tag to return the expected floating tag
    with patch("subvortex.auto_upgrader.src.github.sauu.get_tag", return_value="dev"):
        version = github.get_local_version()

    # Assert
    assert version is None
    mock_subprocess_run.assert_called_once()
