# The MIT License (MIT)
# Copyright © 2025 Eclipse Vortex

import pytest
from unittest.mock import patch, MagicMock

from subvortex.auto_upgrader.src.github import Github

@pytest.mark.asyncio
@patch("subvortex.auto_upgrader.src.github.requests.get")
def test_get_latest_version_returns_version(mock_requests_get):
    # Arrange
    github = Github()

    # Simulate GitHub releases response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {
            "tag_name": "v1.2.3",
            "published_at": "2025-04-20T12:34:56Z",
        },
        {
            "tag_name": "v1.2.2",
            "published_at": "2025-03-20T10:20:30Z",
        },
    ]
    mock_requests_get.return_value = mock_response

    # Act
    version = github.get_latest_version()

    # Assert
    assert version == "1.2.3"
    assert github.latest_version == "1.2.3"
    assert github.published_at == "2025-04-20T12:34:56Z"
    mock_requests_get.assert_called_once_with(
        "https://api.github.com/repos/eclipsevortex/SubVortex/releases",
        headers={}
    )

@pytest.mark.asyncio
@patch("subvortex.auto_upgrader.src.github.requests.get")
def test_get_latest_version_returns_none_when_no_releases(mock_requests_get):
    # Arrange
    github = Github()

    # Simulate GitHub empty releases
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = []
    mock_requests_get.return_value = mock_response

    # Act
    version = github.get_latest_version()

    # Assert
    assert version is None
    assert github.latest_version is None
    assert github.published_at is None
    mock_requests_get.assert_called_once()

@pytest.mark.asyncio
@patch("subvortex.auto_upgrader.src.github.requests.get")
def test_get_latest_version_handles_api_failure(mock_requests_get):
    # Arrange
    github = Github()

    # Simulate GitHub API error
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_requests_get.return_value = mock_response

    github.latest_version = "1.0.0"  # Pre-existing version if fallback

    # Act
    version = github.get_latest_version()

    # Assert
    assert version == "1.0.0"   # Should fallback to pre-existing version
    assert github.latest_version == "1.0.0"
    mock_requests_get.assert_called_once()
