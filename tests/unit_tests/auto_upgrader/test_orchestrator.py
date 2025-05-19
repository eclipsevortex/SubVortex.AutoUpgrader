# The MIT License (MIT)
# Copyright © 2024 Eclipse Vortex

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
        id="miner-neuron", version="1.0.0", name="subvortex-miner-neuron"
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

    # Create template files
    filenames = [
        "template-subvortex-validator-redis.conf",
        "template-subvortex-validator-redis.json",
    ]
    template_files = []
    for fname in filenames:
        path = os.path.join(templates_dir, fname)
        with open(path, "w") as f:
            f.write("# dummy config")
        template_files.append(path)

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

    # Patch get_au_template_files to return template_files regardless of service
    monkeypatch.setattr(
        "subvortex.auto_upgrader.src.path.get_au_template_files",
        lambda: template_files,
    )

    # Patch get_service_template to return the target directory
    monkeypatch.setattr(
        "subvortex.auto_upgrader.src.path.get_service_template",
        lambda service: service_template_dir,
    )

    # Patch logger name
    monkeypatch.setattr(
        "subvortex.auto_upgrader.src.constants.SV_LOGGER_NAME",
        "test",
    )

    # Instantiate orchestrator and inject service
    orch = Orchestrator()
    orch.latest_services = [service]

    # Run the method
    orch._copy_templates_files()

    # Assert: all expected files were copied and renamed properly
    for src_file in template_files:
        expected_filename = os.path.basename(src_file).replace("template-", "")
        expected_path = os.path.join(service_template_dir, expected_filename)
        assert os.path.isfile(expected_path), f"{expected_filename} not found"

    # Cleanup
    shutil.rmtree(templates_dir)
    shutil.rmtree(service_template_dir)


def test_switch_services_only_for_needed_updates(monkeypatch):
    # Arrange
    service1 = create_service(version="1.0.0", name="neuron")
    service1.needs_update = True
    service1.version = "2.0.0"
    service1.switch_to_version = mock.MagicMock()

    service2 = create_service(version="1.0.0", name="redis")
    service2.needs_update = False
    service2.switch_to_version = mock.MagicMock()

    orch = Orchestrator()
    orch.services = [service1, service2]

    # Patch dependency resolver
    monkeypatch.setattr(
        "subvortex.auto_upgrader.src.orchestrator.saudr.DependencyResolver",
        lambda services: mock.Mock(resolve_order=lambda: services),
    )

    # Act
    orch._switch_services()

    # Assert
    service1.switch_to_version.assert_called_once_with(version="2.0.0")
    service2.switch_to_version.assert_not_called()


def test_rollback_switch_services(monkeypatch):
    # Arrange
    service1 = create_service(version="2.0.0", name="neuron")
    service1.needs_update = True
    service1.rollback_version = "1.0.0"
    service1.switch_to_version = mock.MagicMock()

    orch = Orchestrator()
    orch.services = [service1]

    # Patch dependency resolver
    monkeypatch.setattr(
        "subvortex.auto_upgrader.src.orchestrator.saudr.DependencyResolver",
        lambda services: mock.Mock(
            resolve_order=lambda reverse=False: (
                services[::-1] if reverse else services
            )
        ),
    )

    # Act
    orch._rollback_switch_services()

    # Assert
    service1.switch_to_version.assert_called_once_with(version="1.0.0")


def test_switch_services_dependency_order(monkeypatch):
    # Arrange
    svc_a = create_service(version="1.0.0", name="A")
    svc_b = create_service(version="1.0.0", name="B")
    svc_a.needs_update = True
    svc_b.needs_update = True
    svc_a.version = "2.0.0"
    svc_b.version = "2.0.0"
    svc_a.switch_to_version = mock.MagicMock()
    svc_b.switch_to_version = mock.MagicMock()

    orch = Orchestrator()
    orch.services = [svc_a, svc_b]

    # Simulate dependency order: A must come before B
    monkeypatch.setattr(
        "subvortex.auto_upgrader.src.orchestrator.saudr.DependencyResolver",
        lambda services: mock.Mock(resolve_order=lambda: [svc_a, svc_b]),
    )

    # Act
    orch._switch_services()

    # Assert call order
    assert svc_a.switch_to_version.call_args_list[0].kwargs["version"] == "2.0.0"
    assert svc_b.switch_to_version.call_args_list[0].kwargs["version"] == "2.0.0"


def test_rollback_switch_skips_services_without_needs_update(monkeypatch):
    # Arrange
    service = create_service(version="1.0.0", name="unchanged")
    service.needs_update = False
    service.switch_to_version = mock.MagicMock()

    orch = Orchestrator()
    orch.services = [service]

    monkeypatch.setattr(
        "subvortex.auto_upgrader.src.orchestrator.saudr.DependencyResolver",
        lambda services: mock.Mock(
            resolve_order=lambda reverse=False: services[::-1] if reverse else services
        ),
    )

    # Act
    orch._rollback_switch_services()

    # Assert
    service.switch_to_version.assert_not_called()


def test_rollback_switch_skips_none_rollback_version(monkeypatch, caplog):
    # Arrange
    service_with_rollback = create_service(version="2.0.0", name="neuron")
    service_with_rollback.needs_update = True
    service_with_rollback.rollback_version = "1.0.0"
    service_with_rollback.switch_to_version = mock.MagicMock()

    service_without_rollback = create_service(version="2.0.0", name="redis")
    service_without_rollback.needs_update = True
    service_without_rollback.rollback_version = None  # No previous version
    service_without_rollback.switch_to_version = mock.MagicMock()

    orch = Orchestrator()
    orch.services = [service_with_rollback, service_without_rollback]

    # Patch dependency resolver
    monkeypatch.setattr(
        "subvortex.auto_upgrader.src.orchestrator.saudr.DependencyResolver",
        lambda services: mock.Mock(resolve_order=lambda reverse=False: services[::-1] if reverse else services),
    )

    # Enable log capturing
    caplog.set_level("WARNING")

    # Act
    orch
