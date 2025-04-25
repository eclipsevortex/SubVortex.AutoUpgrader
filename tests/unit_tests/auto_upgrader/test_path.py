# The MIT License (MIT)
# Copyright © 2025 Eclipse Vortex

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the “Software”), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import os
import pytest
from unittest import mock

import subvortex.auto_upgrader.src.path as saup
from subvortex.auto_upgrader.src.service import Service

@pytest.fixture
def fake_service():
    return Service(
        id="miner-neuron",
        name="neuron",
        version="v3.0.0-alpha.1",
        execution="process",
        migration="migrations",
        setup_command="",
        start_command="",
        stop_command="",
        teardown_command=""
    )

def test_get_version_directory():
    version = "v3.0.0-alpha.1"
    expected = "/var/tmp/subvortex/subvortex-3.0.0a1"
    assert saup.get_version_directory(version) == expected

def test_get_role_directory():
    version = "v3.0.0-alpha.1"
    expected = "/var/tmp/subvortex/subvortex-3.0.0a1/subvortex/miner"
    assert saup.get_role_directory(version) == expected

def test_get_service_directory(fake_service):
    expected = "/var/tmp/subvortex/subvortex-3.0.0a1/subvortex/miner/neuron"
    assert saup.get_service_directory(fake_service) == expected

def test_get_au_environment_file(fake_service):
    expected_suffix = f"env.subvortex.miner.neuron"
    env_path = saup.get_au_environment_file(fake_service)
    assert env_path.endswith(expected_suffix)

def test_get_environment_file(fake_service):
    path = saup.get_environment_file(fake_service)
    assert path.endswith(".env")
    assert "neuron" in path

def test_get_migration_directory(fake_service):
    # fake_service.root_path = "/var/tmp/subvortex/subvortex-3.0.0a1"
    expected = "/var/tmp/subvortex/subvortex-3.0.0a1/subvortex/miner/neuron/migrations"
    assert saup.get_migration_directory(fake_service) == expected

def test_get_service_script(fake_service):
    path = saup.get_service_script(fake_service, "start")
    assert path.endswith("neuron_service_start.sh")
