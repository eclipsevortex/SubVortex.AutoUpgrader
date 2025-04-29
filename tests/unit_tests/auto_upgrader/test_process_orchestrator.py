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
from unittest import mock
from unittest.mock import patch

import subvortex.auto_upgrader.src.constants as sauc
from subvortex.auto_upgrader.src.orchestrator import Orchestrator
from subvortex.auto_upgrader.src.service import Service
from subvortex.auto_upgrader.src.exception import (
    MissingDirectoryError,
    MissingFileError,
    ServicesLoadError,
)

from tests.unit_tests.utils import get_call_arg


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

    orch = Orchestrator()

    # Store the mock so tests can use it
    orch.mock_subprocess_run = mock_subprocess_run
    orch.mock_exists = mock_exists

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


@pytest.mark.asyncio
async def test_run_plan_calls_all_steps_in_order(orchestrator):
    # Arrange
    called_steps = []

    def make_step(name):
        async def async_step(*args, **kwargs):
            called_steps.append(name)

        def sync_step(*args, **kwargs):
            called_steps.append(name)

        return async_step if "migrations" in name else sync_step

    # Mock all steps
    orchestrator._get_current_version = make_step("get_current_version")
    orchestrator._get_latest_version = make_step("get_latest_version")
    orchestrator._pull_current_assets = make_step("pull_current_version")
    orchestrator._pull_latest_assets = make_step("pull_latest_version")
    orchestrator._load_current_services = make_step("load_current_services")
    orchestrator._load_latest_services = make_step("load_latest_services")
    orchestrator._check_versions = make_step("check_versions")
    orchestrator._copy_env_files = make_step("copy_env_files")
    orchestrator._rollout_service = make_step("rollout_service")
    orchestrator._rollout_migrations = make_step("rollout_migrations")
    orchestrator._stop_current_services = make_step("stop_current_services")
    orchestrator._switch_services = make_step("switch_services")
    orchestrator._start_latest_services = make_step("start_latest_services")
    orchestrator._prune_services = make_step("prune_services")
    orchestrator._remove_services = make_step("remove_services")
    orchestrator._finalize_versions = make_step("finalize_versions")

    # Simulate versions
    orchestrator.current_version = "1.0.0"
    orchestrator.latest_version = "1.0.1"

    # Simulate services
    orchestrator.services = []
    orchestrator.current_services = []
    orchestrator.latest_services = []

    # Action
    await orchestrator.run_plan()

    # Expected order
    expected_steps = [
        "get_current_version",
        "get_latest_version",
        "pull_current_version",
        "pull_latest_version",
        "load_current_services",
        "load_latest_services",
        "check_versions",
        "copy_env_files",
        "rollout_service",
        "rollout_migrations",
        "stop_current_services",
        "switch_services",
        "start_latest_services",
        "prune_services",
        "remove_services",
        "finalize_versions",
    ]

    # Assert
    assert called_steps == expected_steps


@pytest.mark.asyncio
async def test_rollback_calls_all_steps_in_reverse_order(orchestrator):
    # Arrange
    called_rollback_steps = []

    def make_rollback_step(name):
        async def async_step(*args, **kwargs):
            called_rollback_steps.append(name)

        def sync_step(*args, **kwargs):
            called_rollback_steps.append(name)

        return async_step if "async" in name else sync_step

    # Register rollback steps in the order they would be registered during run_plan
    orchestrator.rollback_steps = [
        ("Get current version", make_rollback_step("Get current version")),
        ("Get latest version", make_rollback_step("Get latest version")),
        ("Pull current version", make_rollback_step("Pull current version")),
        ("Pull latest version", make_rollback_step("Pull latest version")),
        ("Load current services", make_rollback_step("Load current services")),
        ("Load latest services", make_rollback_step("Load latest services")),
        ("Check versions", make_rollback_step("Check versions")),
        (
            "Copying environment variables",
            make_rollback_step("Copying environment variables"),
        ),
        ("Upgrade services", make_rollback_step("Upgrade services")),
        ("Run migrations", make_rollback_step("Run migrations")),
        ("Stop previous services", make_rollback_step("Stop previous services")),
        ("Switching to new version", make_rollback_step("Switching to new version")),
        ("Start new services", make_rollback_step("Start new services")),
        ("Remove prune services", make_rollback_step("Remove prune services")),
        ("Remove previous version", make_rollback_step("Remove previous version")),
        ("Finalize service versions", make_rollback_step("Finalize service versions")),
    ]

    # Act
    await orchestrator.run_rollback_plan()

    # Assert: rollback should call steps in reverse registration order
    expected_rollback_order = [
        "Finalize service versions",
        "Remove previous version",
        "Remove prune services",
        "Start new services",
        "Switching to new version",
        "Stop previous services",
        "Run migrations",
        "Upgrade services",
        "Copying environment variables",
        "Check versions",
        "Load latest services",
        "Load current services",
        "Pull latest version",
        "Pull current version",
        "Get latest version",
        "Get current version",
    ]

    assert called_rollback_steps == expected_rollback_order


@pytest.mark.asyncio
async def test_run_plan_when_no_new_version_should_execute_until_load_current_services_step(
    orchestrator,
):
    # Arrange
    mock_all_steps(orchestrator)

    # Fake _get_current_version and _get_latest_version behavior
    orchestrator._get_current_version.side_effect = lambda: setattr(
        orchestrator, "current_version", "1.0.0"
    )
    orchestrator._get_latest_version.side_effect = lambda: setattr(
        orchestrator, "latest_version", "1.0.0"
    )

    # Create fake services
    current_service_1 = create_service(
        id="subvortex-validator-neuron", version="1.0.0", name="neuron"
    )
    current_service_2 = create_service(
        id="subvortex-validator-redis", version="1.0.0", name="redis"
    )

    latest_service_1 = create_service(
        id="subvortex-validator-neuron", version="1.0.0", name="neuron"
    )
    latest_service_2 = create_service(
        id="subvortex-validator-redis", version="1.0.0", name="redis"
    )

    orchestrator._load_current_services.side_effect = lambda: setattr(
        orchestrator, "current_services", [current_service_1, current_service_2]
    )
    orchestrator._load_latest_services.side_effect = lambda: setattr(
        orchestrator, "latest_services", [latest_service_1, latest_service_2]
    )

    # Action
    await orchestrator.run_plan()

    # Assert
    assert 4 == len(orchestrator.rollback_steps)
    assert orchestrator._get_current_version.called
    assert orchestrator._get_latest_version.called
    assert orchestrator._pull_current_assets.called
    assert orchestrator._pull_latest_assets.called
    assert not orchestrator._load_current_services.called
    assert not orchestrator._load_latest_services.called
    assert not orchestrator._check_versions.called
    assert not orchestrator._rollout_service.called
    assert not orchestrator._rollout_migrations.called
    assert not orchestrator._stop_current_services.called
    assert not orchestrator._switch_services.called
    assert not orchestrator._start_latest_services.called
    assert not orchestrator._prune_services.called
    assert not orchestrator._remove_services.called
    assert not orchestrator._finalize_versions.called


@pytest.mark.asyncio
async def test_run_plan_when_new_version_for_all_services_should_execute_all_steps_for_all_services(
    orchestrator,
):
    # Arrange
    orchestrator.github.get_local_version.return_value = "1.0.0"
    orchestrator.github.get_latest_version.return_value = "1.0.1"

    # Create fake services
    current_service_1 = create_service(
        id="subvortex-validator-neuron", version="1.0.0", name="neuron"
    )
    current_service_2 = create_service(
        id="subvortex-validator-redis", version="1.0.0", name="redis"
    )

    latest_service_1 = create_service(
        id="subvortex-validator-neuron", version="1.0.1", name="neuron"
    )
    latest_service_2 = create_service(
        id="subvortex-validator-redis", version="1.0.1", name="redis"
    )

    orchestrator._load_current_services.side_effect = lambda: setattr(
        orchestrator, "current_services", [current_service_1, current_service_2]
    )
    orchestrator._load_latest_services.side_effect = lambda: setattr(
        orchestrator, "latest_services", [latest_service_1, latest_service_2]
    )

    # Action
    await orchestrator.run_plan()

    # Assert
    assert 16 == len(orchestrator.rollback_steps)
    assert_run_calls(
        subprocess_mock=orchestrator.mock_subprocess_run,
        setup=["neuron", "redis"],
        start=["neuron", "redis"],
        stop=["redis", "neuron"],
        teardown=[],
        version="1.0.1",
    )
    orchestrator._remove_assets.assert_called_with(version="1.0.0")


@pytest.mark.asyncio
async def test_run_plan_when_new_version_for_few_services_should_execute_all_steps_for_new_services_only(
    orchestrator,
):
    # Arrange
    orchestrator.github.get_local_version.return_value = "1.0.0"
    orchestrator.github.get_latest_version.return_value = "1.0.1"

    # Create fake services
    current_service_1 = create_service(
        id="subvortex-validator-neuron", version="1.0.0", name="neuron"
    )
    current_service_2 = create_service(
        id="subvortex-validator-redis", version="1.0.0", name="redis"
    )

    latest_service_1 = create_service(
        id="subvortex-validator-neuron", version="1.0.1", name="neuron"
    )
    latest_service_2 = create_service(
        id="subvortex-validator-redis", version="1.0.0", name="redis"
    )

    orchestrator._load_current_services.side_effect = lambda: setattr(
        orchestrator, "current_services", [current_service_1, current_service_2]
    )
    orchestrator._load_latest_services.side_effect = lambda: setattr(
        orchestrator, "latest_services", [latest_service_1, latest_service_2]
    )

    # Action
    await orchestrator.run_plan()

    # Assert
    assert 16 == len(orchestrator.rollback_steps)
    assert_run_calls(
        subprocess_mock=orchestrator.mock_subprocess_run,
        setup=["neuron"],
        start=["neuron"],
        stop=["neuron"],
        teardown=[],
        version="1.0.1",
    )
    orchestrator._remove_assets.assert_called_with(version="1.0.0")


@pytest.mark.asyncio
async def test_run_plan_when_new_version_removes_an_old_service_should_call_the_right_steps(
    orchestrator,
):
    # Arrange
    orchestrator.github.get_local_version.return_value = "1.0.0"
    orchestrator.github.get_latest_version.return_value = "1.0.1"

    # Create fake services
    current_service_1 = create_service(
        id="subvortex-validator-neuron", version="1.0.0", name="neuron"
    )
    current_service_2 = create_service(
        id="subvortex-validator-redis", version="1.0.0", name="redis"
    )

    latest_service_1 = create_service(
        id="subvortex-validator-neuron", version="1.0.0", name="neuron"
    )

    orchestrator._load_current_services.side_effect = lambda: setattr(
        orchestrator, "current_services", [current_service_1, current_service_2]
    )
    orchestrator._load_latest_services.side_effect = lambda: setattr(
        orchestrator, "latest_services", [latest_service_1]
    )

    # Action
    await orchestrator.run_plan()

    # Assert
    assert 16 == len(orchestrator.rollback_steps)
    assert_run_calls(
        subprocess_mock=orchestrator.mock_subprocess_run,
        setup=[],
        start=[],
        stop=["redis"],
        teardown=["redis"],
        version="1.0.1",
    )
    orchestrator._remove_assets.assert_called_with(version="1.0.0")


@pytest.mark.asyncio
async def test_run_plan_when_new_version_removes_an_old_service_and_update_another_one_should_call_the_right_steps(
    orchestrator,
):
    # Arrange
    orchestrator.github.get_local_version.return_value = "1.0.0"
    orchestrator.github.get_latest_version.return_value = "1.0.1"

    # Create fake services
    current_service_1 = create_service(
        id="subvortex-validator-neuron", version="1.0.0", name="neuron"
    )
    current_service_2 = create_service(
        id="subvortex-validator-redis", version="1.0.0", name="redis"
    )

    latest_service_1 = create_service(
        id="subvortex-validator-neuron", version="1.0.1", name="neuron"
    )

    orchestrator._load_current_services.side_effect = lambda: setattr(
        orchestrator, "current_services", [current_service_1, current_service_2]
    )
    orchestrator._load_latest_services.side_effect = lambda: setattr(
        orchestrator, "latest_services", [latest_service_1]
    )

    # Action
    await orchestrator.run_plan()

    # Assert
    assert 16 == len(orchestrator.rollback_steps)
    assert_run_calls(
        subprocess_mock=orchestrator.mock_subprocess_run,
        setup=["neuron"],
        start=["neuron"],
        stop=["neuron", "redis"],
        teardown=["redis"],
        version="1.0.1",
    )
    orchestrator._remove_assets.assert_called_with(version="1.0.0")


@pytest.mark.asyncio
async def test_run_plan_when_new_version_creates_a_new_service_should_call_the_right_steps(
    orchestrator,
):
    # Arrange
    orchestrator.github.get_local_version.return_value = "1.0.0"
    orchestrator.github.get_latest_version.return_value = "1.0.1"

    # Create fake services
    current_service_1 = create_service(
        id="subvortex-validator-neuron", version="1.0.0", name="neuron"
    )

    latest_service_1 = create_service(
        id="subvortex-validator-neuron", version="1.0.0", name="neuron"
    )
    latest_service_2 = create_service(
        id="subvortex-validator-redis", version="1.0.0", name="redis"
    )

    orchestrator._load_current_services.side_effect = lambda: setattr(
        orchestrator, "current_services", [current_service_1]
    )
    orchestrator._load_latest_services.side_effect = lambda: setattr(
        orchestrator, "latest_services", [latest_service_1, latest_service_2]
    )

    # Action
    await orchestrator.run_plan()

    # Assert
    assert 16 == len(orchestrator.rollback_steps)
    assert_run_calls(
        subprocess_mock=orchestrator.mock_subprocess_run,
        setup=["redis"],
        start=["redis"],
        stop=[],
        teardown=[],
        version="1.0.1",
    )
    orchestrator._remove_assets.assert_called_with(version="1.0.0")


@pytest.mark.asyncio
async def test_run_plan_when_new_version_creates_a_new_service_and_update_another_one_should_call_the_right_steps(
    orchestrator,
):
    # Arrange
    orchestrator.github.get_local_version.return_value = "1.0.0"
    orchestrator.github.get_latest_version.return_value = "1.0.1"

    # Create fake services
    current_service_1 = create_service(
        id="subvortex-validator-neuron", version="1.0.0", name="neuron"
    )

    latest_service_1 = create_service(
        id="subvortex-validator-neuron", version="1.0.1", name="neuron"
    )
    latest_service_2 = create_service(
        id="subvortex-validator-redis", version="1.0.0", name="redis"
    )

    orchestrator._load_current_services.side_effect = lambda: setattr(
        orchestrator, "current_services", [current_service_1]
    )
    orchestrator._load_latest_services.side_effect = lambda: setattr(
        orchestrator, "latest_services", [latest_service_1, latest_service_2]
    )

    # Action
    await orchestrator.run_plan()

    # Assert
    assert 16 == len(orchestrator.rollback_steps)
    assert_run_calls(
        subprocess_mock=orchestrator.mock_subprocess_run,
        setup=["neuron", "redis"],
        start=["neuron", "redis"],
        stop=["neuron"],
        teardown=[],
        version="1.0.1",
    )
    orchestrator._remove_assets.assert_called_with(version="1.0.0")


@pytest.mark.asyncio
async def test_run_rollback_plan_when_new_version_for_all_services_and_exception_raised_at_remove_previous_version_step_should_rollback_correctly(
    orchestrator,
):
    # Arrange
    orchestrator.github.get_local_version.return_value = "1.0.0"
    orchestrator.github.get_latest_version.return_value = "1.0.1"

    # Create fake services
    current_service_1 = create_service(
        id="subvortex-validator-neuron", version="1.0.0", name="neuron"
    )
    current_service_2 = create_service(
        id="subvortex-validator-redis", version="1.0.0", name="redis"
    )

    latest_service_1 = create_service(
        id="subvortex-validator-neuron", version="1.0.1", name="neuron"
    )
    latest_service_2 = create_service(
        id="subvortex-validator-redis", version="1.0.1", name="redis"
    )

    orchestrator._load_current_services.side_effect = lambda: setattr(
        orchestrator, "current_services", [current_service_1, current_service_2]
    )
    orchestrator._load_latest_services.side_effect = lambda: setattr(
        orchestrator, "latest_services", [latest_service_1, latest_service_2]
    )

    # Simulate failure in _remove_services
    orchestrator._remove_services = mock.MagicMock(side_effect=Exception("boom"))

    # Act: simulate `main.py` catching the error and calling rollback
    with pytest.raises(Exception, match="boom"):
        await orchestrator.run_plan()

    # Assert
    assert 15 == len(orchestrator.rollback_steps)
    assert_run_calls(
        subprocess_mock=orchestrator.mock_subprocess_run,
        setup=["neuron", "redis"],
        start=["neuron", "redis"],
        stop=["redis", "neuron"],
        teardown=[],
        version="1.0.1",
    )

    # Reset the mocks
    orchestrator.mock_subprocess_run.reset_mock()

    # Action
    await orchestrator.run_rollback_plan()

    # Assert
    assert 15 == len(orchestrator.rollback_steps)
    orchestrator._pull_assets.assert_called_with(version="1.0.0")
    assert_run_calls(
        subprocess_mock=orchestrator.mock_subprocess_run,
        setup=[],
        start=["redis", "neuron"],
        stop=["redis", "neuron"],
        teardown=[],
        version="1.0.1",
    )


@pytest.mark.asyncio
async def test_run_rollback_plan_when_new_version_for_few_services_and_exception_raised_at_remove_previous_version_step_should_rollback_correctly(
    orchestrator,
):
    # Arrange
    orchestrator.github.get_local_version.return_value = "1.0.0"
    orchestrator.github.get_latest_version.return_value = "1.0.1"

    # Create fake services
    current_service_1 = create_service(
        id="subvortex-validator-neuron", version="1.0.0", name="neuron"
    )
    current_service_2 = create_service(
        id="subvortex-validator-redis", version="1.0.0", name="redis"
    )

    latest_service_1 = create_service(
        id="subvortex-validator-neuron", version="1.0.1", name="neuron"
    )
    latest_service_2 = create_service(
        id="subvortex-validator-redis", version="1.0.1", name="redis"
    )

    orchestrator._load_current_services.side_effect = lambda: setattr(
        orchestrator, "current_services", [current_service_1, current_service_2]
    )
    orchestrator._load_latest_services.side_effect = lambda: setattr(
        orchestrator, "latest_services", [latest_service_1, latest_service_2]
    )

    # Simulate failure in _remove_services
    orchestrator._remove_services = mock.MagicMock(side_effect=Exception("boom"))

    # Act: simulate `main.py` catching the error and calling rollback
    with pytest.raises(Exception, match="boom"):
        await orchestrator.run_plan()

    # Assert
    assert 15 == len(orchestrator.rollback_steps)
    assert_run_calls(
        subprocess_mock=orchestrator.mock_subprocess_run,
        setup=["neuron", "redis"],
        start=["neuron", "redis"],
        stop=["redis", "neuron"],
        teardown=[],
        version="1.0.1",
    )

    # Reset the mocks
    orchestrator.mock_subprocess_run.reset_mock()

    # Action
    await orchestrator.run_rollback_plan()

    # Assert
    assert 15 == len(orchestrator.rollback_steps)
    orchestrator._pull_assets.assert_called_with(version="1.0.0")
    assert_run_calls(
        subprocess_mock=orchestrator.mock_subprocess_run,
        setup=[],
        start=["redis", "neuron"],
        stop=["redis", "neuron"],
        teardown=[],
        version="1.0.1",
    )


@pytest.mark.asyncio
async def test_run_rollback_plan_when_new_version_removes_an_old_service_and_exception_raised_at_remove_previous_version_step_should_rollback_correctly(
    orchestrator,
):
    # Arrange
    orchestrator.github.get_local_version.return_value = "1.0.0"
    orchestrator.github.get_latest_version.return_value = "1.0.1"

    # Create fake services
    current_service_1 = create_service(
        id="subvortex-validator-neuron", version="1.0.0", name="neuron"
    )
    current_service_2 = create_service(
        id="subvortex-validator-redis", version="1.0.0", name="redis"
    )

    latest_service_1 = create_service(
        id="subvortex-validator-neuron", version="1.0.1", name="neuron"
    )

    orchestrator._load_current_services.side_effect = lambda: setattr(
        orchestrator, "current_services", [current_service_1, current_service_2]
    )
    orchestrator._load_latest_services.side_effect = lambda: setattr(
        orchestrator, "latest_services", [latest_service_1]
    )

    # Simulate failure in _remove_services
    orchestrator._remove_services = mock.MagicMock(side_effect=Exception("boom"))

    # Act: simulate `main.py` catching the error and calling rollback
    with pytest.raises(Exception, match="boom"):
        await orchestrator.run_plan()

    # Assert
    assert 15 == len(orchestrator.rollback_steps)
    assert_run_calls(
        subprocess_mock=orchestrator.mock_subprocess_run,
        setup=["neuron"],
        start=["neuron"],
        stop=["neuron", "redis"],
        teardown=["redis"],
        version="1.0.1",
    )

    # Reset the mocks
    orchestrator.mock_subprocess_run.reset_mock()

    # Action
    await orchestrator.run_rollback_plan()

    # Assert
    assert 15 == len(orchestrator.rollback_steps)
    orchestrator._pull_assets.assert_called_with(version="1.0.0")
    assert_run_calls(
        subprocess_mock=orchestrator.mock_subprocess_run,
        setup=["redis"],
        start=["redis", "neuron"],
        stop=["neuron"],
        teardown=[],
        version="1.0.1",
    )


@pytest.mark.asyncio
async def test_run_rollback_plan_when_new_version_new_version_creates_a_new_service_and_exception_raised_at_remove_previous_version_step_should_rollback_correctly(
    orchestrator,
):
    # Arrange
    orchestrator.github.get_local_version.return_value = "1.0.0"
    orchestrator.github.get_latest_version.return_value = "1.0.1"

    # Create fake services
    current_service_1 = create_service(
        id="subvortex-validator-neuron", version="1.0.0", name="neuron"
    )

    latest_service_1 = create_service(
        id="subvortex-validator-neuron", version="1.0.0", name="neuron"
    )
    latest_service_2 = create_service(
        id="subvortex-validator-redis", version="1.0.0", name="redis"
    )

    orchestrator._load_current_services.side_effect = lambda: setattr(
        orchestrator, "current_services", [current_service_1]
    )
    orchestrator._load_latest_services.side_effect = lambda: setattr(
        orchestrator, "latest_services", [latest_service_1, latest_service_2]
    )

    # Simulate failure in _remove_services
    orchestrator._remove_services = mock.MagicMock(side_effect=Exception("boom"))

    # Act: simulate `main.py` catching the error and calling rollback
    with pytest.raises(Exception, match="boom"):
        await orchestrator.run_plan()

    # Assert
    assert 15 == len(orchestrator.rollback_steps)
    assert_run_calls(
        subprocess_mock=orchestrator.mock_subprocess_run,
        setup=["redis"],
        start=["redis"],
        stop=[],
        teardown=[],
        version="1.0.1",
    )

    # Reset the mocks
    orchestrator.mock_subprocess_run.reset_mock()

    # Action
    await orchestrator.run_rollback_plan()

    # Assert
    assert 15 == len(orchestrator.rollback_steps)
    orchestrator._pull_assets.assert_called_with(version="1.0.0")
    assert_run_calls(
        subprocess_mock=orchestrator.mock_subprocess_run,
        setup=[],
        start=[],
        stop=["redis"],
        teardown=["redis"],
        version="1.0.1",
    )


@pytest.mark.asyncio
async def test_run_rollback_plan_when_new_version_new_version_creates_a_new_service_and_update_another_one_and_exception_raised_at_remove_previous_version_step_should_rollback_correctly(
    orchestrator,
):
    # Arrange
    orchestrator.github.get_local_version.return_value = "1.0.0"
    orchestrator.github.get_latest_version.return_value = "1.0.1"

    # Create fake services
    current_service_1 = create_service(
        id="subvortex-validator-neuron", version="1.0.0", name="neuron"
    )

    latest_service_1 = create_service(
        id="subvortex-validator-neuron", version="1.0.1", name="neuron"
    )
    latest_service_2 = create_service(
        id="subvortex-validator-redis", version="1.0.0", name="redis"
    )

    orchestrator._load_current_services.side_effect = lambda: setattr(
        orchestrator, "current_services", [current_service_1]
    )
    orchestrator._load_latest_services.side_effect = lambda: setattr(
        orchestrator, "latest_services", [latest_service_1, latest_service_2]
    )

    # Simulate failure in _remove_services
    orchestrator._remove_services = mock.MagicMock(side_effect=Exception("boom"))

    # Act: simulate `main.py` catching the error and calling rollback
    with pytest.raises(Exception, match="boom"):
        await orchestrator.run_plan()

    # Assert
    assert 15 == len(orchestrator.rollback_steps)
    assert_run_calls(
        subprocess_mock=orchestrator.mock_subprocess_run,
        setup=["neuron", "redis"],
        start=["neuron", "redis"],
        stop=["neuron"],
        teardown=[],
        version="1.0.1",
    )

    # Reset the mocks
    orchestrator.mock_subprocess_run.reset_mock()

    # Action
    await orchestrator.run_rollback_plan()

    # Assert
    assert 15 == len(orchestrator.rollback_steps)
    orchestrator._pull_assets.assert_called_with(version="1.0.0")
    assert_run_calls(
        subprocess_mock=orchestrator.mock_subprocess_run,
        setup=[],
        start=["neuron"],
        stop=["redis", "neuron"],
        teardown=["redis"],
        version="1.0.1",
    )


@pytest.mark.asyncio
@patch("subvortex.auto_upgrader.src.orchestrator.saup.get_version_directory")
@patch("os.path.exists")
async def test_raise_exception_when_version_asset_directory_does_not_exist_after_pulling_the_latest_version(
    mock_os_path_exists, mock_get_version_directory, orchestrator
):
    # Arrange
    mock_all_steps(orchestrator)

    orchestrator._pull_latest_assets = Orchestrator._pull_latest_assets.__get__(
        orchestrator
    )

    orchestrator._get_current_version.side_effect = lambda: setattr(
        orchestrator, "current_version", "1.0.0"
    )
    orchestrator._get_latest_version.side_effect = lambda: setattr(
        orchestrator, "latest_version", "1.0.1"
    )

    orchestrator._pull_assets = mock.MagicMock()

    mock_get_version_directory.return_value = "fake-path"
    mock_os_path_exists.return_value = False

    orchestrator._run = mock.MagicMock()

    # Action
    with pytest.raises(MissingDirectoryError) as exc:
        await orchestrator.run_plan()

    # Assert
    assert "[AU1001] Required directory is missing: Path not found: fake-path" == str(
        exc.value
    )
    assert 4 == len(orchestrator.rollback_steps)
    assert orchestrator._get_current_version.called
    assert orchestrator._get_latest_version.called
    assert orchestrator._pull_current_assets.called
    assert not orchestrator._copy_env_files.called
    assert not orchestrator._load_current_services.called
    assert not orchestrator._load_latest_services.called
    assert not orchestrator._check_versions.called
    assert not orchestrator._copy_env_files.called
    assert not orchestrator._rollout_service.called
    assert not orchestrator._rollout_migrations.called
    assert not orchestrator._stop_current_services.called
    assert not orchestrator._switch_services.called
    assert not orchestrator._start_latest_services.called
    assert not orchestrator._prune_services.called
    assert not orchestrator._remove_services.called
    assert not orchestrator._finalize_versions.called


@pytest.mark.asyncio
@patch("subvortex.auto_upgrader.src.orchestrator.saup.get_au_environment_file")
@patch("os.path.exists")
async def test_raise_exception_when_source_env_file_does_not_exist_during_the_copy_env_files_step(
    mock_os_path_exists, mock_get_au_environment_file, orchestrator
):
    # Arrange
    mock_all_steps(orchestrator)

    orchestrator._copy_env_files = Orchestrator._copy_env_files.__get__(orchestrator)

    orchestrator._get_current_version.side_effect = lambda: setattr(
        orchestrator, "current_version", "1.0.0"
    )
    orchestrator._get_latest_version.side_effect = lambda: setattr(
        orchestrator, "latest_version", "1.0.1"
    )

    # Simulate loaded services
    current_service = create_service("1.0.0")
    latest_service = create_service("1.0.1")

    orchestrator._pull_current_assets.side_effect = lambda: setattr(
        orchestrator, "current_services", [current_service]
    )
    orchestrator._pull_latest_assets.side_effect = lambda: setattr(
        orchestrator, "latest_services", [latest_service]
    )

    mock_get_au_environment_file.return_value = "fake-source-file"
    mock_os_path_exists.side_effect = [False, True]

    orchestrator._run = mock.MagicMock()

    # Action
    with pytest.raises(MissingFileError) as exc:
        await orchestrator.run_plan()

    # Assert
    assert "[AU1002] Required file is missing: Path not found: fake-source-file" == str(
        exc.value
    )
    assert 8 == len(orchestrator.rollback_steps)
    assert orchestrator._get_current_version.called
    assert orchestrator._get_latest_version.called
    assert orchestrator._pull_current_assets.called
    assert orchestrator._pull_latest_assets.called
    assert orchestrator._load_current_services.called
    assert orchestrator._load_latest_services.called
    assert orchestrator._check_versions.called
    assert not orchestrator._rollout_service.called
    assert not orchestrator._rollout_migrations.called
    assert not orchestrator._stop_current_services.called
    assert not orchestrator._switch_services.called
    assert not orchestrator._start_latest_services.called
    assert not orchestrator._prune_services.called
    assert not orchestrator._remove_services.called
    assert not orchestrator._finalize_versions.called


@pytest.mark.asyncio
@patch("subvortex.auto_upgrader.src.orchestrator.saup.get_environment_file")
@patch("os.path.exists")
async def test_raise_exception_when_target_env_dir_does_not_exist_during_the_copy_env_files_step(
    mock_os_path_exists, mock_get_environment_file, orchestrator
):
    # Arrange
    mock_all_steps(orchestrator)

    orchestrator._copy_env_files = Orchestrator._copy_env_files.__get__(orchestrator)

    orchestrator._get_current_version.side_effect = lambda: setattr(
        orchestrator, "current_version", "1.0.0"
    )
    orchestrator._get_latest_version.side_effect = lambda: setattr(
        orchestrator, "latest_version", "1.0.1"
    )

    # Simulate loaded services
    current_service = create_service("1.0.0")
    latest_service = create_service("1.0.1")

    orchestrator._pull_current_assets.side_effect = lambda: setattr(
        orchestrator, "current_services", [current_service]
    )
    orchestrator._pull_latest_assets.side_effect = lambda: setattr(
        orchestrator, "latest_services", [latest_service]
    )

    mock_get_environment_file.return_value = "fake-target-file"
    mock_os_path_exists.side_effect = [True, False]

    orchestrator._run = mock.MagicMock()

    # Action
    with pytest.raises(MissingDirectoryError) as exc:
        await orchestrator.run_plan()

    # Assert
    assert (
        "[AU1001] Required directory is missing: Path not found: /var/tmp/subvortex/subvortex-1.0.1/subvortex/miner/neuron"
        == str(exc.value)
    )
    assert 8 == len(orchestrator.rollback_steps)
    assert orchestrator._get_current_version.called
    assert orchestrator._get_latest_version.called
    assert orchestrator._pull_current_assets.called
    assert orchestrator._pull_latest_assets.called
    assert orchestrator._load_current_services.called
    assert orchestrator._load_latest_services.called
    assert orchestrator._check_versions.called
    assert not orchestrator._rollout_service.called
    assert not orchestrator._rollout_migrations.called
    assert not orchestrator._stop_current_services.called
    assert not orchestrator._switch_services.called
    assert not orchestrator._start_latest_services.called
    assert not orchestrator._prune_services.called
    assert not orchestrator._remove_services.called
    assert not orchestrator._finalize_versions.called


@pytest.mark.asyncio
@patch("subvortex.auto_upgrader.src.orchestrator.saup.get_role_directory")
@patch("os.path.exists")
async def test_raise_exception_when_role_directory_does_not_exist_while_pulling_current_services(
    mock_os_path_exists, mock_get_role_directory, orchestrator
):
    # Arrange
    mock_all_steps(orchestrator)

    orchestrator._load_current_services = Orchestrator._load_current_services.__get__(
        orchestrator
    )

    orchestrator._get_current_version.side_effect = lambda: setattr(
        orchestrator, "current_version", "1.0.0"
    )
    orchestrator._get_latest_version.side_effect = lambda: setattr(
        orchestrator, "latest_version", "1.0.1"
    )

    current_service = create_service("1.0.0")
    latest_service = create_service("1.0.1")

    orchestrator._pull_current_assets.side_effect = lambda: setattr(
        orchestrator, "current_services", [current_service]
    )
    orchestrator._pull_latest_assets.side_effect = lambda: setattr(
        orchestrator, "latest_services", [latest_service]
    )

    mock_get_role_directory.return_value = "fake-role-dir"
    mock_os_path_exists.return_value = False

    orchestrator._run = mock.MagicMock()

    # Action
    with pytest.raises(MissingDirectoryError) as exc:
        await orchestrator.run_plan()

    # Assert
    assert (
        "[AU1001] Required directory is missing: Path not found: fake-role-dir"
        == str(exc.value)
    )
    assert 5 == len(orchestrator.rollback_steps)
    assert orchestrator._get_current_version.called
    assert orchestrator._get_latest_version.called
    assert orchestrator._pull_current_assets.called
    assert orchestrator._pull_latest_assets.called
    assert not orchestrator._load_latest_services.called
    assert not orchestrator._check_versions.called
    assert not orchestrator._copy_env_files.called
    assert not orchestrator._rollout_service.called
    assert not orchestrator._rollout_migrations.called
    assert not orchestrator._stop_current_services.called
    assert not orchestrator._switch_services.called
    assert not orchestrator._start_latest_services.called
    assert not orchestrator._prune_services.called
    assert not orchestrator._remove_services.called
    assert not orchestrator._finalize_versions.called


@pytest.mark.asyncio
@patch("subvortex.auto_upgrader.src.orchestrator.saup.get_role_directory")
@patch("os.path.exists")
async def test_raise_exception_when_role_directory_does_not_exist_while_pulling_latest_services(
    mock_os_path_exists, mock_get_role_directory, orchestrator
):
    # Arrange
    mock_all_steps(orchestrator)

    orchestrator._load_latest_services = Orchestrator._load_latest_services.__get__(
        orchestrator
    )

    orchestrator._get_current_version.side_effect = lambda: setattr(
        orchestrator, "current_version", "1.0.0"
    )
    orchestrator._get_latest_version.side_effect = lambda: setattr(
        orchestrator, "latest_version", "1.0.1"
    )

    current_service = create_service("1.0.0")
    latest_service = create_service("1.0.1")

    orchestrator._pull_current_assets.side_effect = lambda: setattr(
        orchestrator, "current_services", [current_service]
    )
    orchestrator._pull_latest_assets.side_effect = lambda: setattr(
        orchestrator, "latest_services", [latest_service]
    )

    mock_get_role_directory.return_value = "fake-role-dir"
    mock_os_path_exists.return_value = False

    orchestrator._run = mock.MagicMock()

    # Action
    with pytest.raises(MissingDirectoryError) as exc:
        await orchestrator.run_plan()

    # Assert
    assert (
        "[AU1001] Required directory is missing: Path not found: fake-role-dir"
        == str(exc.value)
    )
    assert 6 == len(orchestrator.rollback_steps)
    assert orchestrator._get_current_version.called
    assert orchestrator._get_latest_version.called
    assert orchestrator._pull_current_assets.called
    assert orchestrator._pull_latest_assets.called
    assert orchestrator._load_current_services.called
    assert not orchestrator._check_versions.called
    assert not orchestrator._copy_env_files.called
    assert not orchestrator._rollout_service.called
    assert not orchestrator._rollout_migrations.called
    assert not orchestrator._stop_current_services.called
    assert not orchestrator._switch_services.called
    assert not orchestrator._start_latest_services.called
    assert not orchestrator._prune_services.called
    assert not orchestrator._remove_services.called
    assert not orchestrator._finalize_versions.called


@pytest.mark.asyncio
@patch("subvortex.auto_upgrader.src.orchestrator.saup.get_role_directory")
@patch("os.path.exists")
async def test_raise_exception_when_latest_services_doe_not_exist_after_pulling_them(
    mock_os_path_exists, mock_get_role_directory, orchestrator
):
    # Arrange
    mock_all_steps(orchestrator)

    orchestrator._load_latest_services = Orchestrator._load_latest_services.__get__(
        orchestrator
    )

    orchestrator._get_current_version.side_effect = lambda: setattr(
        orchestrator, "current_version", "1.0.0"
    )
    orchestrator._get_latest_version.side_effect = lambda: setattr(
        orchestrator, "latest_version", "1.0.1"
    )

    latest_service = create_service("1.0.1")

    orchestrator._load_services = mock.MagicMock()
    orchestrator._load_services.side_effect = [[], [latest_service]]

    mock_get_role_directory.return_value = "valid-role-dir"
    mock_os_path_exists.return_value = True

    orchestrator._run = mock.MagicMock()

    # Action
    with pytest.raises(ServicesLoadError) as exc:
        await orchestrator.run_plan()

    # Assert
    assert "[AU1003] Failed to load services: Version: 1.0.1" == str(exc.value)
    assert 6 == len(orchestrator.rollback_steps)
    assert orchestrator._get_current_version.called
    assert orchestrator._get_latest_version.called
    assert orchestrator._pull_current_assets.called
    assert orchestrator._pull_latest_assets.called
    assert orchestrator._load_current_services.called
    assert not orchestrator._check_versions.called
    assert not orchestrator._copy_env_files.called
    assert not orchestrator._rollout_service.called
    assert not orchestrator._rollout_migrations.called
    assert not orchestrator._stop_current_services.called
    assert not orchestrator._switch_services.called
    assert not orchestrator._start_latest_services.called
    assert not orchestrator._prune_services.called
    assert not orchestrator._remove_services.called
    assert not orchestrator._finalize_versions.called


@pytest.mark.asyncio
@patch("subvortex.auto_upgrader.src.orchestrator.MigrationManager")
async def test_raise_exception_when_migration_path_doe_not_exist_while_rolling_out_migration_step(
    mock_migration_manager_class, orchestrator
):
    # Arrange
    mock_all_steps(orchestrator)

    orchestrator._rollout_migrations = Orchestrator._rollout_migrations.__get__(
        orchestrator
    )

    orchestrator._get_current_version.side_effect = lambda: setattr(
        orchestrator, "current_version", "1.0.0"
    )
    orchestrator._get_latest_version.side_effect = lambda: setattr(
        orchestrator, "latest_version", "1.0.1"
    )

    latest_service = create_service("1.0.1")

    orchestrator._load_services = mock.MagicMock()
    orchestrator._load_services.side_effect = [[], [latest_service]]

    mock_migration_manager = mock.MagicMock()
    mock_migration_manager.collect_migrations.side_effect = MissingDirectoryError(
        directory_path="fake-path"
    )
    mock_migration_manager_class.return_value = mock_migration_manager

    orchestrator._run = mock.MagicMock()

    # Action
    with pytest.raises(MissingDirectoryError) as exc:
        await orchestrator.run_plan()

    # Assert
    assert "[AU1001] Required directory is missing: Path not found: fake-path" == str(
        exc.value
    )
    assert 10 == len(orchestrator.rollback_steps)
    assert orchestrator._get_current_version.called
    assert orchestrator._get_latest_version.called
    assert orchestrator._pull_current_assets.called
    assert orchestrator._pull_latest_assets.called
    assert orchestrator._load_current_services.called
    assert orchestrator._load_latest_services.called
    assert orchestrator._check_versions.called
    assert orchestrator._copy_env_files.called
    assert orchestrator._rollout_service.called
    assert not orchestrator._stop_current_services.called
    assert not orchestrator._switch_services.called
    assert not orchestrator._start_latest_services.called
    assert not orchestrator._prune_services.called
    assert not orchestrator._remove_services.called
    assert not orchestrator._finalize_versions.called
