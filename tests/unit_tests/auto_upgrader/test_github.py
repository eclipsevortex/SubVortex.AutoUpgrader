# The MIT License (MIT)
# Copyright © 2024 Eclipse Vortex
import pytest
from unittest.mock import patch, MagicMock

import subvortex.auto_upgrader.src.constants as sauc
import subvortex.auto_upgrader.src.exception as saue

from subvortex.auto_upgrader.src.github import Github


@patch("subvortex.auto_upgrader.src.github.os.readlink")
@patch("subvortex.auto_upgrader.src.github.os.path.islink", return_value=True)
@patch("subvortex.auto_upgrader.src.github.os.path.isfile", return_value=False)
def test_get_local_version_symlink_returns_version(mock_isfile, mock_islink, mock_readlink):
    # Arrange
    github = Github()
    mock_readlink.return_value = "/var/tmp/subvortex/subvortex-1.2.3"

    # Act
    version = github.get_local_version()

    # Assert
    assert version == "1.2.3"
    mock_readlink.assert_called_once()


@patch("subvortex.auto_upgrader.src.github.os.readlink")
@patch("subvortex.auto_upgrader.src.github.os.path.islink", return_value=True)
def test_get_local_version_symlink_invalid_path(mock_islink, mock_readlink):
    # Arrange
    github = Github()
    mock_readlink.return_value = "/some/unknown/path/no-version-here"

    # Act
    version = github.get_local_version()

    # Assert
    assert version is None


@patch("subvortex.auto_upgrader.src.github.os.readlink")
@patch("subvortex.auto_upgrader.src.github.os.path.islink", return_value=True)
@patch("subvortex.auto_upgrader.src.github.os.path.isfile", return_value=True)
@patch("subvortex.auto_upgrader.src.github.os.remove")
def test_get_local_version_symlink_force_marker(mock_remove, mock_isfile, mock_islink, mock_readlink):
    # Arrange
    github = Github()
    mock_readlink.return_value = "/var/tmp/subvortex/subvortex-3.0.0a40"

    # Act
    version = github.get_local_version()

    # Assert
    assert version is None
    mock_remove.assert_called_once()


@patch("subvortex.auto_upgrader.src.github.requests.get")
def test_get_latest_version_service_returns_version(mock_requests_get):
    # Arrange
    github = Github()

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {"tag_name": "v1.2.3", "published_at": "2025-04-20T12:34:56Z"},
        {"tag_name": "v1.2.2", "published_at": "2025-04-19T12:34:56Z"},
    ]
    mock_requests_get.return_value = mock_response

    # Act
    version = github.get_latest_version()

    # Assert
    assert version == "1.2.3"
    mock_requests_get.assert_called_once()


@patch("subvortex.auto_upgrader.src.github.requests.get")
def test_get_latest_version_service_raise_release_url_not_found(mock_requests_get):
    # Arrange
    github = Github()

    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_requests_get.return_value = mock_response

    # Act
    with pytest.raises(saue.ReleaseNotFoundError) as exc:
        github.get_latest_version()

    # Assert
    assert (
        "[AU1011] Release link not found: Url: https://api.github.com/repos/eclipsevortex/SubVortex/releases"
        == str(exc.value)
    )


@patch("subvortex.auto_upgrader.src.github.requests.get")
def test_get_latest_version_service_raise_no_release_available_found(mock_requests_get):
    # Arrange
    github = Github()

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = []
    mock_requests_get.return_value = mock_response

    # Act
    with pytest.raises(saue.NoReleaseAvailableError) as exc:
        github.get_latest_version()

    # Assert
    assert "[AU1012] No release available" == str(exc.value)


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


@patch("subvortex.auto_upgrader.src.constants.SV_EXECUTION_METHOD", "container")
@patch("subvortex.auto_upgrader.src.github.subprocess.run")
@patch("subvortex.auto_upgrader.src.github.requests.get")
def test_get_latest_version_container_returns_version(
    mock_requests_get, mock_subprocess_run
):
    # Arrange
    github = Github()

    # Mock responses for GitHub API
    packages_response = MagicMock()
    packages_response.status_code = 200
    packages_response.json.return_value = [
        {"name": "subvortex-miner-neuron"},
    ]

    mock_requests_get.side_effect = [
        packages_response,  # First: list packages
    ]

    # Mock subprocess.run() for docker pull and inspect
    mock_subprocess_run.side_effect = [
        MagicMock(returncode=0),  # docker pull --quiet ...
        MagicMock(
            returncode=0,
            stdout='{"version": "1.2.3", "version.miner": "1.2.3", "version.miner.neuorn": "1.2.3"}',
        ),  # docker inspect ...
    ]

    # Act
    version = github.get_latest_version()

    # Assert
    assert version == "1.2.3"
    assert mock_subprocess_run.call_count == 2


@patch("subvortex.auto_upgrader.src.constants.SV_EXECUTION_METHOD", "container")
@patch("subvortex.auto_upgrader.src.constants.SV_EXECUTION_ROLE", "validator")
@patch("subvortex.auto_upgrader.src.github.subprocess.run")
@patch("subvortex.auto_upgrader.src.github.requests.get")
def test_get_latest_version_container_returns_new_version_if_at_least_one_service_has_the_new_version(
    mock_requests_get, mock_subprocess_run
):
    # Arrange
    github = Github()

    # Mock responses for GitHub API
    packages_response = MagicMock()
    packages_response.status_code = 200
    packages_response.json.return_value = [
        {"name": "subvortex-validator-neuron"},
        {"name": "subvortex-validator-redis"},
    ]

    mock_requests_get.side_effect = [
        packages_response,  # First: list packages
    ]

    # Mock subprocess.run() for docker pull and inspect
    mock_subprocess_run.side_effect = [
        MagicMock(returncode=0),  # docker pull --quiet ...
        MagicMock(
            returncode=0,
            stdout='{"version": "1.2.3", "version.validator": "1.2.3", "version.validator.neuron": "1.2.3"}',
        ),
        MagicMock(returncode=0),
        MagicMock(
            returncode=0,
            stdout='{"version": "1.2.2", "version.redis": "1.2.2", "version.validator.redis": "1.2.2"}',
        ),
    ]

    # Act
    version = github.get_latest_version()

    # Assert
    assert version == "1.2.3"
    assert mock_subprocess_run.call_count == 4


@patch("subvortex.auto_upgrader.src.constants.SV_EXECUTION_METHOD", "container")
@patch("subvortex.auto_upgrader.src.constants.SV_EXECUTION_ROLE", "validator")
@patch("subvortex.auto_upgrader.src.github.subprocess.run")
@patch("subvortex.auto_upgrader.src.github.requests.get")
def test_get_latest_version_container_returns_new_version_if_all_service_has_same_global_version(
    mock_requests_get, mock_subprocess_run
):
    # Arrange
    github = Github()

    # Mock responses for GitHub API
    packages_response = MagicMock()
    packages_response.status_code = 200
    packages_response.json.return_value = [
        {"name": "subvortex-validator-neuron"},
        {"name": "subvortex-validator-redis"},
    ]

    mock_requests_get.side_effect = [
        packages_response,  # First: list packages
    ]

    # Mock subprocess.run() for docker pull and inspect
    mock_subprocess_run.side_effect = [
        MagicMock(returncode=0),  # docker pull --quiet ...
        MagicMock(
            returncode=0,
            stdout='{"version": "1.2.3", "version.validator": "1.2.3", "version.validator.neuron": "1.2.3"}',
        ),
        MagicMock(returncode=0),
        MagicMock(
            returncode=0,
            stdout='{"version": "1.2.3", "version.redis": "1.2.3", "version.validator.redis": "1.2.3"}',
        ),
    ]

    # Act
    version = github.get_latest_version()

    # Assert
    assert version == "1.2.3"
    assert mock_subprocess_run.call_count == 4


@patch("subvortex.auto_upgrader.src.constants.SV_EXECUTION_METHOD", "container")
@patch("subvortex.auto_upgrader.src.github.requests.get")
def test_get_latest_version_container_returns_none_when_no_packages(mock_requests_get):
    # Arrange
    github = Github()

    # Mock packages list response (empty list)
    packages_response = MagicMock()
    packages_response.status_code = 200
    packages_response.json.return_value = []

    mock_requests_get.side_effect = [packages_response]

    # Act
    version = github.get_latest_version()

    # Assert
    assert version is None
    assert mock_requests_get.call_count == 1


@patch("subvortex.auto_upgrader.src.constants.SV_EXECUTION_METHOD", "container")
@patch("subvortex.auto_upgrader.src.github.requests.get")
def test_get_latest_version_container_raise_package_url_not_found(mock_requests_get):
    # Arrange
    github = Github()

    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_requests_get.return_value = mock_response

    # Act
    with pytest.raises(saue.PackageNotFoundError) as exc:
        github.get_latest_version()

    # Assert
    assert (
        "[AU1014] Package link not found: Url: https://api.github.com/users/eclipsevortex/packages?package_type=container"
        == str(exc.value)
    )


@patch("subvortex.auto_upgrader.src.constants.SV_EXECUTION_METHOD", "container")
@patch("subvortex.auto_upgrader.src.github.requests.get")
def test_get_latest_version_container_skip_package_if_no_versions_found(
    mock_requests_get,
):
    # Arrange
    github = Github()

    # Mock responses for GitHub API
    packages_response = MagicMock()
    packages_response.status_code = 200
    packages_response.json.return_value = [
        {"name": "subvortex-miner-neuron"},
    ]

    versions_response = MagicMock()
    versions_response.status_code = 404

    mock_requests_get.side_effect = [
        packages_response,  # First: list packages
        versions_response,  # Second: package versions
    ]

    # Act
    version = github.get_latest_version()

    # Assert
    assert version is None


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
        MagicMock(
            stdout='{"version": "1.2.4", "neuron": { "version": "1.2.4", "miner.version": "1.2.3", "miner.neuron.version": "1.2.4" }}',
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
def test_get_local_version_image_returns_version(mock_subprocess_run):
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
            stdout="",
            returncode=0,
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
    assert mock_subprocess_run.call_count == 3


def test_get_latest_container_versions_returns_default_if_missing():
    github = Github()
    github.latest_versions = {}

    default_versions = github.get_latest_container_versions(name="neuron")

    assert default_versions["version"] is not None


def test_get_local_container_versions_returns_default_if_missing():
    github = Github()
    github.local_versions = {}

    default_versions = github.get_local_container_versions(name="neuron")

    assert default_versions["version"] is not None


@patch("subvortex.auto_upgrader.src.constants.SV_EXECUTION_METHOD", "container")
@patch("subvortex.auto_upgrader.src.github.requests.get")
@patch("subvortex.auto_upgrader.src.github.subprocess.run")
@pytest.mark.parametrize(
    "floating_tag,expected_version",
    [
        ("latest", "3.0.0"),
        ("stable", "3.0.0-rc.1"),
        ("dev", "3.0.0-alpha.21"),
    ],
)
def test_get_latest_container_version_different_tags(
    mock_subprocess_run,
    mock_requests_get,
    floating_tag,
    expected_version,
):
    github = Github()

    # Mock sauu.get_tag() to return the floating_tag (latest, stable, dev)
    with patch(
        "subvortex.auto_upgrader.src.github.sauu.get_tag", return_value=floating_tag
    ):

        # Mock requests.get to return a list of container packages
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"name": "subvortex-miner-neuron"},
        ]
        mock_requests_get.return_value = mock_response

        # Mock docker pull and inspect
        mock_subprocess_run.side_effect = [
            MagicMock(returncode=0),  # docker pull success
            MagicMock(
                returncode=0,
                stdout=f'{{"version": "{expected_version}", "miner.version": "{expected_version}", "miner.neuron.version": "{expected_version}"}}',
            ),  # docker inspect output
        ]

        # Act
        version = github.get_latest_version()

        # Assert
        assert version == expected_version
        assert mock_requests_get.call_count == 1
        assert mock_subprocess_run.call_count == 2  # pull + inspect
