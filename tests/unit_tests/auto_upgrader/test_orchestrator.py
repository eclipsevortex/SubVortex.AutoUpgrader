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
import os
import pytest
import shutil
import tempfile
from unittest import mock
from unittest.mock import patch

import subvortex.auto_upgrader.src.constants as sauc
from subvortex.auto_upgrader.src.orchestrator import Orchestrator
from subvortex.auto_upgrader.src.service import Service


@pytest.fixture(autouse=True)
def orchestrator():
    # --- Patch subprocess.run ---
    subprocess_patcher = patch(
        "subvortex.auto_upgrader.src.orchestrator.subprocess.run"
    )
    mock_subprocess_run = subprocess_patcher.start()

    # --- Patch os.path.exists ---
    exists_patcher = patch(
        "subvortex.auto_upgrader.src.orchestrator.os.path.exists", return_value=True
    )
    mock_exists = exists_patcher.start()

    # --- Patch os.makedirs ---
    makedirs_patcher = patch("subvortex.auto_upgrader.src.orchestrator.os.makedirs")
    mock_makedirs = makedirs_patcher.start()

    orch = Orchestrator()

    # Store the mock so tests can use it
    orch.mock_subprocess_run = mock_subprocess_run
    orch.mock_exists = mock_exists
    orch.mock_makedirs = mock_makedirs

    # Pre-set for test overrides
    orch.current_version = None
    orch.latest_version = None
    orch.services = []

    # Checks
    orch.check_version_assets_exists = mock.MagicMock()

    # GitHub and metadata mocking
    orch.github.get_local_version = mock.MagicMock()
    orch.github.get_latest_version = mock.MagicMock()
    orch.github.download_and_unzip_assets = mock.MagicMock()
    orch.metadata_resolver.list_directory = mock.MagicMock()
    orch.metadata_resolver.get_metadata = mock.MagicMock(
        return_value={
            "id": "subvortex-validator-neuron",
            "name": "neuron",
            "version": "1.0.1",
            "execution": "process",
            "setup_command": "subvortex-validator/neuron/setup.sh",
        }
    )

    # Mock internal steps in run_plan
    # orch._get_current_version = mock.MagicMock()
    # orch._get_latest_version = mock.MagicMock()
    orch._pull_current_assets = mock.MagicMock()
    orch._pull_latest_assets = mock.MagicMock()
    orch._load_current_services = mock.MagicMock()
    orch._load_latest_services = mock.MagicMock()
    orch._copy_env_files = mock.MagicMock()
    # orch._run = mock.MagicMock()

    # Removal
    orch._remove_assets = mock.MagicMock()
    orch._pull_assets = mock.MagicMock()

    yield orch  # <- yield the orchestrator instance for the tests

    # --- Stop patches after the test ---
    subprocess_patcher.stop()
    exists_patcher.stop()


@pytest.fixture(autouse=True)
def patch_execution_method():
    with patch("subvortex.auto_upgrader.src.constants.SV_EXECUTION_METHOD", "process"):
        yield


def validator_template_files(directory, filenames=None):
    """
    Create mock validator template files with optional filenames.
    Returns a list of full paths to the created files.
    """
    filenames = filenames
    filepaths = []

    for fname in filenames:
        fpath = os.path.join(directory, fname)
        with open(fpath, "w") as f:
            f.write(f"# content for {fname}")
        filepaths.append(fpath)

    return filepaths


def create_service(
    version: str, id="subvortex-neuron", execution="process", name="neuron"
):
    return Service(
        id=id,
        name=name,
        version=version,
        component_version=version,
        service_version=version,
        execution=execution,
        migration="",
        setup_command="deployment/neuron_process_setup.sh",
        start_command="deployment/neuron_process_start.sh",
        stop_command="deployment/neuron_process_stop.sh",
        teardown_command="deployment/neuron_process_teardown.sh",
    )


def create_migration_file(path, revision, down_revision):
    revision_str = f'"{revision}"' if revision else None
    down_revision_str = f'"{down_revision}"' if down_revision else None
    content = f"""
revision = {revision_str}
down_revision = {down_revision_str}

async def rollout(database):
    print("rollout {revision}")

async def rollback(database):
    print("rollback {revision}")
"""
    with open(os.path.join(path, f"{revision}.py"), "w") as f:
        f.write(content)


def mock_all_steps(orch):
    orch._get_current_version = mock.MagicMock()
    orch._get_latest_version = mock.MagicMock()
    orch._pull_current_assets = mock.MagicMock()
    orch._pull_latest_assets = mock.MagicMock()
    orch._rollback_pull_latest_assets = mock.MagicMock()
    orch._copy_env_files = mock.MagicMock()
    orch._load_current_services = mock.MagicMock()
    orch._load_latest_services = mock.MagicMock()
    orch._check_versions = mock.MagicMock()
    orch._rollout_service = mock.MagicMock()
    orch._rollback_services = mock.MagicMock()
    orch._rollout_migrations = mock.MagicMock()
    orch._rollback_migrations = mock.MagicMock()
    orch._stop_current_services = mock.MagicMock()
    orch._rollback_stop_current_services = mock.MagicMock()
    orch._switch_services = mock.MagicMock()
    orch._rollback_switch_services = mock.MagicMock()
    orch._start_latest_services = mock.MagicMock()
    orch._rollback_start_latest_services = mock.MagicMock()
    orch._prune_services = mock.MagicMock()
    orch._rollback_prune_services = mock.MagicMock()
    orch._remove_services = mock.MagicMock()
    orch._finalize_versions = mock.MagicMock()
    orch._ = mock.MagicMock()


def mock_all_scripts(orch):
    orch._execute_setup = mock.MagicMock()
    orch._execute_start = mock.MagicMock()
    orch._execute_stop = mock.MagicMock()
    orch._execute_teardown = mock.MagicMock()


def assert_run_calls(
    subprocess_mock,
    setup: list = None,
    start: list = None,
    stop: list = None,
    teardown: list = None,
    version: str = None,
):
    setup = setup or []
    start = start or []
    stop = stop or []
    teardown = teardown or []

    actions = {
        "setup": setup,
        "start": start,
        "stop": stop,
        "teardown": teardown,
    }

    # Build a list of (action, service_name) tuples from subprocess.call_args_list
    called_actions = []
    for call_obj in subprocess_mock.call_args_list:
        args = call_obj.args[0]  # args to subprocess.run
        env = call_obj.kwargs.get("env", {})
        if not args or not env:
            continue

        if args[0] == "bash":
            script_path = args[1]
            # Infer action from script filename
            if "setup" in script_path:
                action = "setup"
            elif "start" in script_path:
                action = "start"
            elif "stop" in script_path:
                action = "stop"
            elif "teardown" in script_path:
                action = "teardown"
            else:
                continue  # Unknown action

            path = script_path.replace(f"{sauc.SV_ASSET_DIR}/", "").split("/")[0]

            # Infer service name from path (assuming /<role>/<service>/<script>)
            service_name = script_path.split("/")[-1].split("_")[0]
            called_actions.append((action, service_name, path))

    # Now assert each action
    for action, expected_services in actions.items():
        actual_path = list(
            set([path for act, _, path in called_actions if act == action])
        )
        if len(actual_path) > 0:
            # Check we take the script in the version
            assert 1 == len(actual_path)
            assert f"subvortex-{version}" == actual_path[0]

        # Check the services and actions
        actual_services = [svc for act, svc, _ in called_actions if act == action]
        assert set(actual_services) == set(expected_services), (
            f"Mismatch for action '{action}':\n"
            f"  Expected: {expected_services}\n"
            f"  Got:      {actual_services}"
        )


def test_has_migrations_when_no_migration_path_should_return_false(orchestrator):
    # Arrange
    orchestrator.github.get_local_version.return_value = "1.0.0"
    orchestrator.github.get_latest_version.return_value = "1.0.1"

    # Create fake services
    service = create_service(
        id="subvortex-miner-neuron", version="1.0.0", name="neuron"
    )
    service.migration = None

    # Action
    result = orchestrator._has_migrations(service=service)

    # Assert
    assert False == result


def test_has_migrations_when_no_migration_files_should_return_false(orchestrator):
    # Arrange
    orchestrator.github.get_local_version.return_value = "1.0.0"
    orchestrator.github.get_latest_version.return_value = "1.0.1"

    # Create fake services
    service = create_service(
        id="subvortex-miner-neuron", version="1.0.0", name="neuron"
    )
    service.migration = tempfile.mkdtemp()

    # Action
    result = orchestrator._has_migrations(service=service)

    # Assert
    assert False == result


def test_has_migrations_when_no_migration_should_return_false(orchestrator):
    # Arrange
    orchestrator.github.get_local_version.return_value = "1.0.0"
    orchestrator.github.get_latest_version.return_value = "1.0.1"

    # Create fake services
    service = create_service(
        id="subvortex-miner-neuron", version="1.0.0", name="neuron"
    )
    service.migration = tempfile.mkdtemp()

    create_migration_file(service.migration, "0.0.1", None)

    # Action
    result = orchestrator._has_migrations(service=service)

    # Assert
    assert True == result


def test_not_pull_current_version_if_different_from_the_one_of_the_auto_upgrader_release(
    orchestrator,
):
    # Arrange
    orchestrator._pull_latest_assets = Orchestrator._pull_latest_assets.__get__(
        orchestrator
    )

    orchestrator.github.get_local_version.return_value = sauc.DEFAULT_LAST_RELEASE.get(
        "global"
    )

    # Action
    orchestrator.run_plan()

    # Assert
    assert not orchestrator._pull_current_assets.called


@patch("subvortex.auto_upgrader.src.orchestrator.os.path.exists")
def test_not_pull_current_version_if_already_pulled(mock_os_path_exists, orchestrator):
    # Arrange
    orchestrator._pull_latest_assets = Orchestrator._pull_latest_assets.__get__(
        orchestrator
    )

    orchestrator.github.get_local_version.return_value = "1.0.0"

    mock_os_path_exists.return_value = True

    # Action
    orchestrator.run_plan()

    # Assert
    assert not orchestrator._pull_current_assets.called


@pytest.mark.asyncio
@patch("subvortex.auto_upgrader.src.orchestrator.os.path.exists")
async def test_not_pull_current_version_if_not_pulled_yet(
    mock_os_path_exists, orchestrator
):
    # Arrange
    orchestrator._pull_latest_assets = Orchestrator._pull_latest_assets.__get__(
        orchestrator
    )

    orchestrator.github.get_local_version.return_value = "1.0.0"
    orchestrator.github.get_latest_version.return_value = "1.0.0"

    mock_os_path_exists.return_value = False

    # Action
    await orchestrator.run_plan()

    # Assert
    assert orchestrator._pull_current_assets.called


def test_copy_templates_files(monkeypatch):
    # Setup temporary template and service directories
    templates_dir = tempfile.mkdtemp()
    service_template_dir = tempfile.mkdtemp()

    # Filenames to simulate
    filenames = [
        "template-subvortex-validator-redis.conf",
        "template-subvortex-validator-redis.json",
    ]
    template_files = validator_template_files(templates_dir, filenames)

    # Mock Service
    service = Service(
        id="validator-redis",
        name="redis",
        version="v3.0.0-alpha.1",
        component_version="v3.0.0-alpha.1",
        service_version="v3.0.0-alpha.1",
        execution="process",
        migration="",
        setup_command="",
        start_command="",
        stop_command="",
        teardown_command="",
    )

    # Patch path methods
    monkeypatch.setattr(
        "subvortex.auto_upgrader.src.path.get_au_template_file",
        lambda service: template_files,
    )
    monkeypatch.setattr(
        "subvortex.auto_upgrader.src.path.get_service_template",
        lambda service: service_template_dir,
    )

    # Patch logger
    monkeypatch.setattr("subvortex.auto_upgrader.src.constants.SV_LOGGER_NAME", "test")

    # Instantiate orchestrator and inject service
    orch = Orchestrator()
    orch.latest_services = [service]

    # Run method
    orch._copy_templates_files()

    # Assert: both files were copied with correct filenames
    for src_file in template_files:
        fname = os.path.basename(src_file).replace("template-", "")
        copied_file = os.path.join(service_template_dir, fname)
        assert os.path.isfile(
            copied_file
        ), f"{fname} not found in {service_template_dir}"

    # Clean up
    shutil.rmtree(templates_dir)
    shutil.rmtree(service_template_dir)
