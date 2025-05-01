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
import copy
import shutil
import pytest
import tempfile
from unittest.mock import AsyncMock, patch, call

from subvortex.auto_upgrader.src.service import Service
from subvortex.auto_upgrader.src.exception import (
    MissingDirectoryError,
    MalformedMigrationFileError,
    InvalidRevisionError,
    RevisionNotFoundError,
)
from subvortex.auto_upgrader.src.migrations.redis_migrations import RedisMigrations


@pytest.fixture
def redis_service():
    migration_dir = tempfile.mkdtemp()
    service = Service(
        id="svc-1",
        name="test-service",
        version=None,
        component_version=None,
        service_version=None,
        execution="process",
        migration=migration_dir,
        setup_command="",
        start_command="",
        stop_command="",
        teardown_command="",
        depends_on=[],
    )
    yield service

    # Recursively remove migration directory
    shutil.rmtree(service.migration)


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


def create_malformed_migration_file(path, revision, down_revision):
    revision_str = f'"{revision}"' if revision else None
    down_revision_str = f'"{down_revision}"' if down_revision else None
    content = f"""
revision = {revision_str}
down_revision = {down_revision_str}

async def _rollout(database):
    print("rollout {revision}")

async def _rollback(database):
    print("rollback {revision}")
"""
    with open(os.path.join(path, f"{revision}.py"), "w") as f:
        f.write(content)


def assert_version_calls(mocked_db, expected_versions):
    version_calls = [c for c in mocked_db.set.call_args_list if c.args[0] == "version"]

    actual_versions = [c.args[1] for c in version_calls]
    expected_calls = [call("version", v) for v in expected_versions]

    assert (
        actual_versions == expected_versions
    ), f"Expected version calls {expected_versions}, but got {actual_versions}"


@pytest.mark.asyncio
async def test_apply_all_migrations(redis_service):
    # Arrange
    new_redis_service = copy.deepcopy(redis_service)
    new_redis_service.migration = tempfile.mkdtemp()

    create_migration_file(new_redis_service.migration, "0.0.1", None)
    create_migration_file(new_redis_service.migration, "0.0.2", "0.0.1")
    create_migration_file(new_redis_service.migration, "0.0.3", "0.0.2")

    redis = RedisMigrations(new_redis_service, redis_service)
    redis.new_migration_path = new_redis_service.migration
    redis.old_migration_path = redis_service.migration

    mocked_db = AsyncMock()
    mocked_db.get.return_value = b"0.0.0"

    # Action
    with patch.object(redis, "_create_redis_instance", return_value=mocked_db):
        await redis.apply()

    # Assert
    assert_version_calls(mocked_db, ["0.0.1", "0.0.2", "0.0.3"])


@pytest.mark.asyncio
async def test_rollout_migration(redis_service):
    # Arrange
    create_migration_file(redis_service.migration, "0.0.1", None)
    create_migration_file(redis_service.migration, "0.0.2", "0.0.1")

    new_redis_service = copy.deepcopy(redis_service)
    new_redis_service.migration = tempfile.mkdtemp()

    create_migration_file(new_redis_service.migration, "0.0.1", None)
    create_migration_file(new_redis_service.migration, "0.0.2", "0.0.1")
    create_migration_file(new_redis_service.migration, "0.0.3", "0.0.2")

    redis = RedisMigrations(new_redis_service, redis_service)
    redis.new_migration_path = new_redis_service.migration
    redis.old_migration_path = redis_service.migration

    mocked_db = AsyncMock()
    mocked_db.get.return_value = b"0.0.2"

    # Action
    with patch.object(redis, "_create_redis_instance", return_value=mocked_db):
        await redis.apply()

    # Assert
    mocked_db.set.assert_any_call("version", "0.0.3")


@pytest.mark.asyncio
async def test_rollback_all_migration(redis_service):
    # Arrange
    create_migration_file(redis_service.migration, "0.0.1", None)
    create_migration_file(redis_service.migration, "0.0.2", "0.0.1")
    create_migration_file(redis_service.migration, "0.0.3", "0.0.2")

    new_redis_service = copy.deepcopy(redis_service)
    new_redis_service.migration = tempfile.mkdtemp()

    redis = RedisMigrations(new_redis_service, redis_service)
    redis.new_migration_path = new_redis_service.migration
    redis.old_migration_path = redis_service.migration
    redis._load_migrations_from_path(redis.old_migration_path)
    redis.applied_revisions = ["0.0.1", "0.0.2", "0.0.3"]

    mocked_db = AsyncMock()
    mocked_db.get.return_value = b"0.0.3"

    # Action
    with patch.object(redis, "_create_redis_instance", return_value=mocked_db):
        await redis.rollback()

    # Assert
    assert_version_calls(mocked_db, ["0.0.2", "0.0.1", "0.0.0"])


@pytest.mark.asyncio
async def test_rollback_migration(redis_service):
    # Arrange
    create_migration_file(redis_service.migration, "0.0.1", None)
    create_migration_file(redis_service.migration, "0.0.2", "0.0.1")
    create_migration_file(redis_service.migration, "0.0.3", "0.0.2")

    new_redis_service = copy.deepcopy(redis_service)
    new_redis_service.migration = tempfile.mkdtemp()

    create_migration_file(new_redis_service.migration, "0.0.1", None)
    create_migration_file(new_redis_service.migration, "0.0.2", "0.0.1")

    redis = RedisMigrations(new_redis_service, redis_service)
    redis.new_migration_path = new_redis_service.migration
    redis.old_migration_path = redis_service.migration
    redis._load_migrations_from_path(redis.old_migration_path)
    redis.applied_revisions = ["0.0.1", "0.0.2", "0.0.3"]

    mocked_db = AsyncMock()
    mocked_db.get.return_value = b"0.0.3"

    # Action
    with patch.object(redis, "_create_redis_instance", return_value=mocked_db):
        await redis.rollback()

    # Assert
    mocked_db.set.assert_any_call("version", "0.0.2")


@pytest.mark.asyncio
async def test_apply_all_downgrade(redis_service):
    # Arrange
    create_migration_file(redis_service.migration, "0.0.1", None)
    create_migration_file(redis_service.migration, "0.0.2", "0.0.1")
    create_migration_file(redis_service.migration, "0.0.3", "0.0.2")

    new_redis_service = copy.deepcopy(redis_service)
    new_redis_service.migration = tempfile.mkdtemp()

    redis = RedisMigrations(new_redis_service, redis_service)
    redis.previous_service = redis_service
    redis.previous_service.version = "3.0.0"
    redis.new_migration_path = new_redis_service.migration
    redis.old_migration_path = redis_service.migration

    mocked_db = AsyncMock()
    mocked_db.get.return_value = b"0.0.3"

    # Action
    with patch.object(redis, "_create_redis_instance", return_value=mocked_db):
        await redis.apply()

    # Assert
    assert_version_calls(mocked_db, ["0.0.2", "0.0.1", "0.0.0"])


@pytest.mark.asyncio
async def test_apply_downgrade(redis_service):
    # Arrange
    create_migration_file(redis_service.migration, "0.0.1", None)
    create_migration_file(redis_service.migration, "0.0.2", "0.0.1")
    create_migration_file(redis_service.migration, "0.0.3", "0.0.2")

    new_redis_service = copy.deepcopy(redis_service)
    new_redis_service.migration = tempfile.mkdtemp()

    create_migration_file(new_redis_service.migration, "0.0.1", None)
    create_migration_file(new_redis_service.migration, "0.0.2", "0.0.1")

    redis = RedisMigrations(new_redis_service, redis_service)
    redis.previous_service = redis_service
    redis.previous_service.version = "3.0.0"
    redis.new_migration_path = new_redis_service.migration
    redis.old_migration_path = redis_service.migration

    mocked_db = AsyncMock()
    mocked_db.get.return_value = b"0.0.3"

    # Action
    with patch.object(redis, "_create_redis_instance", return_value=mocked_db):
        await redis.apply()

    # Assert
    assert_version_calls(mocked_db, ["0.0.2"])


@pytest.mark.asyncio
async def test_apply_does_nothing_when_up_to_date(redis_service):
    # Arrange
    create_migration_file(redis_service.migration, "0.0.1", None)

    new_redis_service = copy.deepcopy(redis_service)
    new_redis_service.migration = tempfile.mkdtemp()

    create_migration_file(new_redis_service.migration, "0.0.1", None)

    redis = RedisMigrations(new_redis_service, redis_service)
    redis.new_migration_path = new_redis_service.migration
    redis.old_migration_path = redis_service.migration

    mocked_db = AsyncMock()
    mocked_db.get.return_value = b"0.0.1"

    # Action
    with patch.object(redis, "_create_redis_instance", return_value=mocked_db):
        await redis.apply()

    # Assert
    assert not any(
        c.args and c.args[0] == "version" for c in mocked_db.set.call_args_list
    )


@pytest.mark.asyncio
async def test_rollback_does_nothing_when_at_base(redis_service):
    # Arrange
    new_redis_service = copy.deepcopy(redis_service)
    new_redis_service.migration = tempfile.mkdtemp()

    redis = RedisMigrations(new_redis_service, redis_service)
    redis.new_migration_path = new_redis_service.migration
    redis.old_migration_path = redis_service.migration
    redis._load_migrations_from_path(redis.old_migration_path)
    redis.applied_revisions = []

    mocked_db = AsyncMock()
    mocked_db.get.return_value = b"0.0.0"

    # Action
    with patch.object(redis, "_create_redis_instance", return_value=mocked_db):
        await redis.rollback()

    # Assert
    assert not any(
        c.args and c.args[0] == "version" for c in mocked_db.set.call_args_list
    )


@pytest.mark.asyncio
@patch("os.path.exists")
async def test_raise_exception_when_migration_path_does_not_exist(
    mock_os_path_exists, redis_service
):
    # Arrange
    create_migration_file(redis_service.migration, "0.0.1", None)

    mock_os_path_exists.return_value = False

    redis = RedisMigrations(redis_service)

    # Action
    with pytest.raises(MissingDirectoryError) as exc:
        redis._load_migrations_from_path(redis_service.migration)

    # Assert
    assert (
        f"[AU1001] Required directory is missing: Path not found: {redis_service.migration}"
        == str(exc.value)
    )


@pytest.mark.asyncio
@patch("os.path.exists")
async def test_raise_exception_when_migration_file_is_malformed(
    mock_os_path_exists, redis_service
):
    # Arrange
    create_malformed_migration_file(redis_service.migration, "0.0.1", None)

    mock_os_path_exists.return_value = True

    redis = RedisMigrations(redis_service)

    mocked_db = AsyncMock()
    mocked_db.get.return_value = b"0.0.0"

    # Action
    with patch.object(redis, "_create_redis_instance", return_value=mocked_db):
        with pytest.raises(MalformedMigrationFileError) as exc:
            redis._load_migrations_from_path(redis_service.migration)

    # Assert
    assert "[AU1004] Malformed migration file: File: 0.0.1.py" == str(exc.value)


@pytest.mark.asyncio
async def test_raise_exception_when_revision_is_not_found(redis_service):
    # Arrange
    create_migration_file(redis_service.migration, None, None)

    redis = RedisMigrations(redis_service)

    mocked_db = AsyncMock()
    mocked_db.get.return_value = b"0.0.2"

    # Action
    with patch.object(redis, "_create_redis_instance", return_value=mocked_db):
        with pytest.raises(RevisionNotFoundError) as exc:
            redis._load_migrations_from_path(redis_service.migration)

    # Assert
    assert "[AU1005] Revision not found" == str(exc.value)


@pytest.mark.asyncio
async def test_raise_exception_when_revision_is_invalid(redis_service):
    # Arrange
    create_migration_file(redis_service.migration, "0.0.1", "0.0.1")

    redis = RedisMigrations(redis_service)

    mocked_db = AsyncMock()
    mocked_db.get.return_value = b"0.0.0"

    # Action
    with patch.object(redis, "_create_redis_instance", return_value=mocked_db):
        with pytest.raises(InvalidRevisionError) as exc:
            redis._load_migrations_from_path(redis_service.migration)

    # Assert
    assert "[AU1006] Invalid revision: Revision: 0.0.1, Down revision: 0.0.1" == str(
        exc.value
    )


@pytest.mark.asyncio
@patch("shutil.copy2")
@patch("os.makedirs")
@patch("os.path.exists")
@patch(
    "subvortex.auto_upgrader.src.migrations.redis_migrations.RedisMigrations._get_redis_dump_config"
)
async def test_prepare_copies_dump_if_dirs_differ(
    mock_get_dump_config, mock_path_exists, mock_makedirs, mock_copy2, redis_service
):
    # Arrange
    previous_service = copy.deepcopy(redis_service)
    new_service = copy.deepcopy(redis_service)

    redis = RedisMigrations(new_service, previous_service)

    previous_config = "/etc/redis/old_redis.conf"
    new_config = "/etc/redis/new_redis.conf"

    # Patch saup.get_service_template to return mocked config paths
    with patch(
        "subvortex.auto_upgrader.src.migrations.redis_migrations.saup.get_service_template"
    ) as mock_get_template:
        mock_get_template.side_effect = lambda svc: (
            [previous_config] if svc == previous_service else [new_config]
        )

        # Mock _get_redis_dump_config responses
        mock_get_dump_config.side_effect = [
            ("/old/dir", "dump.rdb"),
            ("/new/dir", "dump.rdb"),
        ]

        mock_path_exists.return_value = True

        # Act
        await redis.prepare()

        # Assert
        mock_makedirs.assert_called_once_with("/new/dir", exist_ok=True)
        mock_copy2.assert_called_once_with("/old/dir/dump.rdb", "/new/dir/dump.rdb")


@pytest.mark.asyncio
@patch("shutil.copy2")
@patch("os.makedirs")
@patch("os.path.exists")
@patch(
    "subvortex.auto_upgrader.src.migrations.redis_migrations.RedisMigrations._get_redis_dump_config"
)
async def test_prepare_does_nothing_if_dirs_are_same(
    mock_get_dump_config, mock_path_exists, mock_makedirs, mock_copy2, redis_service
):
    # Arrange
    previous_service = copy.deepcopy(redis_service)
    new_service = copy.deepcopy(redis_service)

    redis = RedisMigrations(new_service, previous_service)

    config_path = "/etc/redis/shared_redis.conf"

    with patch(
        "subvortex.auto_upgrader.src.migrations.redis_migrations.saup.get_service_template"
    ) as mock_get_template:
        mock_get_template.return_value = [config_path]

        # Both configs return the same dir and filename
        mock_get_dump_config.side_effect = [
            ("/shared/dir", "dump.rdb"),
            ("/shared/dir", "dump.rdb"),
        ]

        mock_path_exists.return_value = True

        # Act
        await redis.prepare()

        # Assert
        mock_makedirs.assert_not_called()
        mock_copy2.assert_not_called()
