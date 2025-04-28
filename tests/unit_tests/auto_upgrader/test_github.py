# The MIT License (MIT)
# Copyright © 2025 Eclipse Vortex

import os
import pytest
import tempfile
from unittest.mock import patch, MagicMock, mock_open

from subvortex.auto_upgrader.src.github import Github
from subvortex.auto_upgrader.src.exception import MissingFileError


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
    version = github.get_latest_version()

    # Assert
    assert version == "1.2.3"
    assert github.latest_version == "1.2.3"
    assert github.published_at == "2025-04-20T12:34:56Z"
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
    version = github.get_latest_version()

    # Assert
    assert version is None
    assert github.latest_version is None
    assert github.published_at is None
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
