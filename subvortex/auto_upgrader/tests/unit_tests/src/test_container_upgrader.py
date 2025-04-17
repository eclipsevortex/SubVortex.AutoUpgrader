# The MIT License (MIT)
# Copyright © 2025 Eclipse Vortex

# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
# documentation files (the “Software”), to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all copies or substantial portions of
# the Software.

# THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO
# THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.
import pytest
from unittest.mock import AsyncMock, patch, Mock

import subvortex.auto_upgrader.src.constants as sauc
import subvortex.auto_upgrader.src.upgraders.container_upgrader as sauucu


# get_latest_version tests
@pytest.mark.asyncio
async def test_get_latest_version_when_at_least_one_digest_has_changed_should_return_new_latest():
    # Arrange
    upgrader = sauucu.ContainerUpgrader()
    upgrader.current_versions = {}
    upgrader.latest_versions = {
        "subvorx-miner-neuron": "sha256:7c81f8eacb1c0d9f512ce31e1d7c9dce261f635a1c41e5f9a727b5d2a1b3c3cf"
    }

    # Act
    result = upgrader.get_latest_version()

    # Asert
    assert "new-latest" == result


@pytest.mark.asyncio
async def test_get_latest_version_when_no_digest_have_changed_should_return_latest():
    # Arrange
    upgrader = sauucu.ContainerUpgrader()
    upgrader.current_versions = {
        "subvorx-miner-neuron": "sha256:7c81f8eacb1c0d9f512ce31e1d7c9dce261f635a1c41e5f9a727b5d2a1b3c3cf"
    }
    upgrader.latest_versions = {
        "subvorx-miner-neuron": "sha256:7c81f8eacb1c0d9f512ce31e1d7c9dce261f635a1c41e5f9a727b5d2a1b3c3cf"
    }

    # Act
    result = upgrader.get_latest_version()

    # Asert
    assert "latest" == result


# get_current tests
@pytest.mark.asyncio
async def test_get_current_version_when_at_least_one_digest_has_changed_should_return_latest():
    # Arrange
    upgrader = sauucu.ContainerUpgrader()
    upgrader.current_versions = {}
    upgrader.latest_versions = {
        "subvorx-miner-neuron": "sha256:7c81f8eacb1c0d9f512ce31e1d7c9dce261f635a1c41e5f9a727b5d2a1b3c3cf"
    }

    # Act
    result = upgrader.get_current_version()

    # Asert
    assert "latest" == result


@pytest.mark.asyncio
async def test_get_current_version_when_no_digest_have_changed_should_return_latest():
    # Arrange
    upgrader = sauucu.ContainerUpgrader()
    upgrader.current_versions = {
        "subvorx-miner-neuron": "sha256:7c81f8eacb1c0d9f512ce31e1d7c9dce261f635a1c41e5f9a727b5d2a1b3c3cf"
    }
    upgrader.latest_versions = {
        "subvorx-miner-neuron": "sha256:7c81f8eacb1c0d9f512ce31e1d7c9dce261f635a1c41e5f9a727b5d2a1b3c3cf"
    }

    # Act
    result = upgrader.get_current_version()

    # Asert
    assert "latest" == result


# get_latest_component_version tests
@pytest.mark.asyncio
async def test_get_latest_component_version_when_at_least_one_digest_has_changed_should_return_new_latest():
    # Arrange
    upgrader = sauucu.ContainerUpgrader()
    upgrader.current_versions = {}
    upgrader.latest_versions = {
        "subvorx-miner-neuron": "sha256:7c81f8eacb1c0d9f512ce31e1d7c9dce261f635a1c41e5f9a727b5d2a1b3c3cf"
    }

    # Act
    result = upgrader.get_latest_component_version(path="subvorx-miner-neuron")

    # Asert
    assert "new-latest" == result


@pytest.mark.asyncio
async def test_get_latest_component_version_when_no_digest_have_changed_should_return_latest():
    # Arrange
    upgrader = sauucu.ContainerUpgrader()
    upgrader.current_versions = {
        "subvorx-miner-neuron": "sha256:7c81f8eacb1c0d9f512ce31e1d7c9dce261f635a1c41e5f9a727b5d2a1b3c3cf"
    }
    upgrader.latest_versions = {
        "subvorx-miner-neuron": "sha256:7c81f8eacb1c0d9f512ce31e1d7c9dce261f635a1c41e5f9a727b5d2a1b3c3cf"
    }

    # Act
    result = upgrader.get_latest_component_version(path="subvorx-miner-neuron")

    # Asert
    assert "latest" == result


# get_current_component_version tests
@pytest.mark.asyncio
async def test_get_current_component_version_version_when_at_least_one_digest_has_changed_should_return_latest():
    # Arrange
    upgrader = sauucu.ContainerUpgrader()
    upgrader.current_versions = {}
    upgrader.latest_versions = {
        "subvorx-miner-neuron": "sha256:7c81f8eacb1c0d9f512ce31e1d7c9dce261f635a1c41e5f9a727b5d2a1b3c3cf"
    }

    # Act
    result = upgrader.get_current_component_version(path="subvorx-miner-neuron")

    # Asert
    assert "latest" == result


@pytest.mark.asyncio
async def test_get_current_component_version_version_when_no_digest_have_changed_should_return_latest():
    # Arrange
    upgrader = sauucu.ContainerUpgrader()
    upgrader.current_versions = {
        "subvorx-miner-neuron": "sha256:7c81f8eacb1c0d9f512ce31e1d7c9dce261f635a1c41e5f9a727b5d2a1b3c3cf"
    }
    upgrader.latest_versions = {
        "subvorx-miner-neuron": "sha256:7c81f8eacb1c0d9f512ce31e1d7c9dce261f635a1c41e5f9a727b5d2a1b3c3cf"
    }

    # Act
    result = upgrader.get_current_component_version(path="subvorx-miner-neuron")

    # Asert
    assert "latest" == result
