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
import shutil
import pytest
import tempfile
from unittest.mock import AsyncMock, patch

from subvortex.auto_upgrader.src.service import Service
from subvortex.auto_upgrader.src.exception import (
    MissingDirectoryError,
    MalformedMigrationFileError,
    InvalidRevisionError,
    RevisionNotFoundError,
    DownRevisionNotFoundError
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


@pytest.mark.asyncio
@patch(
    "subvortex.auto_upgrader.src.migrations.redis_migrations.saup.get_migration_directory"
)
async def test_apply_all_migrations(mock_get_migration_dir, redis_service):
    # Arrange
    create_migration_file(redis_service.migration, "0.0.1", None)
    create_migration_file(redis_service.migration, "0.0.2", "0.0.1")
    create_migration_file(redis_service.migration, "0.0.3", "0.0.2")

    mock_get_migration_dir.return_value = redis_service.migration

    redis = RedisMigrations(redis_service)

    mocked_db = AsyncMock()
    mocked_db.get.return_value = b"0.0.0"

    # Action
    with patch.object(redis, "_create_redis_instance", return_value=mocked_db):
        await redis.apply()

    # Assert
    mocked_db.set.assert_any_call("version", "0.0.3")


@pytest.mark.asyncio
@patch(
    "subvortex.auto_upgrader.src.migrations.redis_migrations.saup.get_migration_directory"
)
async def test_rollout_migration(mock_get_migration_dir, redis_service):
    # Arrange
    create_migration_file(redis_service.migration, "0.0.1", None)
    create_migration_file(redis_service.migration, "0.0.2", "0.0.1")
    create_migration_file(redis_service.migration, "0.0.3", "0.0.2")

    mock_get_migration_dir.return_value = redis_service.migration

    redis = RedisMigrations(redis_service)

    mocked_db = AsyncMock()
    mocked_db.get.return_value = b"0.0.2"

    # Action
    with patch.object(redis, "_create_redis_instance", return_value=mocked_db):
        await redis.apply()

    # Assert
    mocked_db.set.assert_any_call("version", "0.0.3")


@pytest.mark.asyncio
@patch(
    "subvortex.auto_upgrader.src.migrations.redis_migrations.saup.get_migration_directory"
)
async def test_rollback_migration(mock_get_migration_dir, redis_service):
    # Arrange
    create_migration_file(redis_service.migration, "0.0.1", None)
    create_migration_file(redis_service.migration, "0.0.2", "0.0.1")
    create_migration_file(redis_service.migration, "0.0.3", "0.0.2")

    mock_get_migration_dir.return_value = redis_service.migration

    redis = RedisMigrations(redis_service)
    redis.previous_version = "0.0.2"

    mocked_db = AsyncMock()
    mocked_db.get.return_value = b"0.0.3"

    # Action
    with patch.object(redis, "_create_redis_instance", return_value=mocked_db):
        await redis.rollback()

    # Assert
    mocked_db.set.assert_any_call("version", "0.0.2")


@pytest.mark.asyncio
@patch(
    "subvortex.auto_upgrader.src.migrations.redis_migrations.saup.get_migration_directory"
)
async def test_apply_does_nothing_when_up_to_date(
    mock_get_migration_dir, redis_service
):
    # Arrange
    create_migration_file(redis_service.migration, "0.0.1", None)

    mock_get_migration_dir.return_value = redis_service.migration

    redis = RedisMigrations(redis_service)

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
@patch(
    "subvortex.auto_upgrader.src.migrations.redis_migrations.saup.get_migration_directory"
)
async def test_rollback_does_nothing_when_at_base(
    mock_get_migration_dir, redis_service
):
    # Arrange
    create_migration_file(redis_service.migration, "0.0.1", None)

    mock_get_migration_dir.return_value = redis_service.migration

    redis_service.version = None

    redis = RedisMigrations(redis_service)

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
@patch(
    "subvortex.auto_upgrader.src.migrations.redis_migrations.saup.get_migration_directory"
)
@patch("os.path.exists")
async def test_raise_exception_when_migration_path_does_not_exist(
    mock_os_path_exists, mock_get_migration_directory, redis_service
):
    # Arrange
    create_migration_file(redis_service.migration, "0.0.1", None)

    mock_get_migration_directory.return_value = "fake-dir"
    mock_os_path_exists.return_value = False

    redis = RedisMigrations(redis_service)

    # Action
    with pytest.raises(MissingDirectoryError) as exc:
        redis._load_migrations()

    # Assert
    assert "[AU1001] Required directory is missing: Path not found: fake-dir" == str(
        exc.value
    )


@pytest.mark.asyncio
@patch(
    "subvortex.auto_upgrader.src.migrations.redis_migrations.saup.get_migration_directory"
)
@patch("os.path.exists")
async def test_raise_exception_when_migration_file_is_malformed(
    mock_os_path_exists, mock_get_migration_directory, redis_service
):
    # Arrange
    create_malformed_migration_file(redis_service.migration, "0.0.1", None)

    mock_get_migration_directory.return_value = redis_service.migration
    mock_os_path_exists.return_value = True

    redis = RedisMigrations(redis_service)

    mocked_db = AsyncMock()
    mocked_db.get.return_value = b"0.0.0"

    # Action
    with patch.object(redis, "_create_redis_instance", return_value=mocked_db):
        with pytest.raises(MalformedMigrationFileError) as exc:
            redis._load_migrations()

    # Assert
    assert "[AU1004] Malformed migration file: File: 0.0.1.py" == str(exc.value)


@pytest.mark.asyncio
@patch(
    "subvortex.auto_upgrader.src.migrations.redis_migrations.saup.get_migration_directory"
)
async def test_raise_exception_when_revision_is_not_found(
    mock_get_migration_dir, redis_service
):
    # Arrange
    create_migration_file(redis_service.migration, None, None)

    mock_get_migration_dir.return_value = redis_service.migration

    redis = RedisMigrations(redis_service)

    mocked_db = AsyncMock()
    mocked_db.get.return_value = b"0.0.2"

    # Action
    with patch.object(redis, "_create_redis_instance", return_value=mocked_db):
        with pytest.raises(RevisionNotFoundError) as exc:
            redis._load_migrations()

    # Assert
    assert "[AU1005] Revision not found" == str(exc.value)


@pytest.mark.asyncio
@patch(
    "subvortex.auto_upgrader.src.migrations.redis_migrations.saup.get_migration_directory"
)
async def test_raise_exception_when_revision_is_invalid(
    mock_get_migration_dir, redis_service
):
    # Arrange
    create_migration_file(redis_service.migration, "0.0.1", "0.0.1")

    mock_get_migration_dir.return_value = redis_service.migration

    redis = RedisMigrations(redis_service)

    mocked_db = AsyncMock()
    mocked_db.get.return_value = b"0.0.0"

    # Action
    with patch.object(redis, "_create_redis_instance", return_value=mocked_db):
        with pytest.raises(InvalidRevisionError) as exc:
            redis._load_migrations()

    # Assert
    assert (
        "[AU1006] Invalid revision: Revision: 0.0.1, Down revision: 0.0.1"
        == str(exc.value)
    )


@pytest.mark.asyncio
@patch(
    "subvortex.auto_upgrader.src.migrations.redis_migrations.saup.get_migration_directory"
)
async def test_raise_exception_when_down_revision_does_not_exist(
    mock_get_migration_dir, redis_service
):
    # Arrange
    create_migration_file(
        redis_service.migration, "0.0.2", "0.0.1"
    )  # 0.0.1 does not exist!

    mock_get_migration_dir.return_value = redis_service.migration

    redis = RedisMigrations(redis_service)

    mocked_db = AsyncMock()
    mocked_db.get.return_value = b"0.0.0"

    # Action
    with patch.object(redis, "_create_redis_instance", return_value=mocked_db):
        with pytest.raises(DownRevisionNotFoundError) as exc:
            redis._load_migrations()

    # Assert
    assert (
        "[AU1010] Down revision not found: Down revision: 0.0.1"
        == str(exc.value)
    )
