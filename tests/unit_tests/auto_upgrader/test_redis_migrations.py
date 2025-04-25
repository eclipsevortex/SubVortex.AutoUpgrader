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
    InvalidRevisionLinkError,
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
    redis_service.version = None

    create_migration_file(redis_service.migration, "001", None)
    create_migration_file(redis_service.migration, "002", "001")
    create_migration_file(redis_service.migration, "003", "002")

    mock_get_migration_dir.return_value = redis_service.migration

    redis = RedisMigrations(redis_service)

    mocked_db = AsyncMock()

    # Action
    with patch.object(redis, "_create_redis_instance", return_value=mocked_db):
        await redis.apply()

    assert redis_service.version == "003"


@pytest.mark.asyncio
@patch(
    "subvortex.auto_upgrader.src.migrations.redis_migrations.saup.get_migration_directory"
)
async def test_rollback_all_migrations(mock_get_migration_dir, redis_service):
    # Arrange
    redis_service.next_version = "003"

    create_migration_file(redis_service.migration, "001", None)
    create_migration_file(redis_service.migration, "002", "001")
    create_migration_file(redis_service.migration, "003", "002")

    mock_get_migration_dir.return_value = redis_service.migration

    redis = RedisMigrations(redis_service)
    mocked_db = AsyncMock()

    # Action
    with patch.object(redis, "_create_redis_instance", return_value=mocked_db):
        await redis.rollback()

    # Assert
    assert redis_service.version is None


@pytest.mark.asyncio
@patch(
    "subvortex.auto_upgrader.src.migrations.redis_migrations.saup.get_migration_directory"
)
async def test_apply_does_nothing_when_up_to_date(
    mock_get_migration_dir, redis_service
):
    # Arrange
    create_migration_file(redis_service.migration, "001", None)

    mock_get_migration_dir.return_value = redis_service.migration

    redis_service.version = "001"

    redis = RedisMigrations(redis_service)
    mocked_db = AsyncMock()

    # Action
    with patch.object(redis, "_create_redis_instance", return_value=mocked_db):
        redis.apply()

    # Assert
    assert redis_service.version == "001"


@pytest.mark.asyncio
@patch(
    "subvortex.auto_upgrader.src.migrations.redis_migrations.saup.get_migration_directory"
)
async def test_rollback_does_nothing_when_at_base(
    mock_get_migration_dir, redis_service
):
    # Arrange
    create_migration_file(redis_service.migration, "001", None)

    mock_get_migration_dir.return_value = redis_service.migration

    redis_service.version = None

    redis = RedisMigrations(redis_service)
    mocked_db = AsyncMock()

    # Action
    with patch.object(redis, "_create_redis_instance", return_value=mocked_db):
        await redis.rollback()

    # Assert
    assert redis_service.version is None


@pytest.mark.asyncio
@patch(
    "subvortex.auto_upgrader.src.migrations.redis_migrations.saup.get_migration_directory"
)
async def test_rollback_skips_base(mock_get_migration_dir, redis_service):
    # Arrange
    create_migration_file(redis_service.migration, "001", None)

    mock_get_migration_dir.return_value = redis_service.migration

    redis_service.version = "001"

    redis = RedisMigrations(redis_service)
    mocked_db = AsyncMock()

    # Action
    with patch.object(redis, "_create_redis_instance", return_value=mocked_db):
        await redis.rollback()

    # Assert
    assert redis_service.version is None


@pytest.mark.asyncio
@patch(
    "subvortex.auto_upgrader.src.migrations.redis_migrations.saup.get_migration_directory"
)
@patch("os.path.exists")
async def test_raise_exception_when_migration_path_does_not_exist(
    mock_os_path_exists, mock_get_migration_directory, redis_service
):
    # Arrange
    create_migration_file(redis_service.migration, "001", None)

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
# @patch("os.listdir")
async def test_raise_exception_when_migration_file_is_malformed(
    mock_os_path_exists, mock_get_migration_directory, redis_service
):
    # Arrange
    create_malformed_migration_file(redis_service.migration, "001", None)

    mock_get_migration_directory.return_value = redis_service.migration
    mock_os_path_exists.return_value = True

    redis_service.version = "001"

    redis = RedisMigrations(redis_service)
    mocked_db = AsyncMock()

    # Action
    with patch.object(redis, "_create_redis_instance", return_value=mocked_db):
        with pytest.raises(MalformedMigrationFileError) as exc:
            redis._load_migrations()

    # Assert
    assert "[AU1004] Malformed migration file: File: 001.py" == str(exc.value)


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

    # Action
    with pytest.raises(RevisionNotFoundError) as exc:
        redis._load_migrations()

    # Assert
    assert "[AU1005] Revision not found" == str(exc.value)


@pytest.mark.asyncio
@patch(
    "subvortex.auto_upgrader.src.migrations.redis_migrations.saup.get_migration_directory"
)
async def test_raise_exception_when_revision_revision_is_invalid(
    mock_get_migration_dir, redis_service
):
    # Arrange
    create_migration_file(redis_service.migration, "100", "100")

    mock_get_migration_dir.return_value = redis_service.migration

    redis = RedisMigrations(redis_service)

    # Action
    with pytest.raises(InvalidRevisionLinkError) as exc:
        redis._load_migrations()

    # Assert
    assert (
        "[AU1006] Invalid migration revision: Revision: 100, Down Revision: 100"
        == str(exc.value)
    )


@pytest.mark.asyncio
@patch(
    "subvortex.auto_upgrader.src.migrations.redis_migrations.saup.get_migration_directory"
)
async def test_raise_exception_when_revision_revision_does_not_exist(
    mock_get_migration_dir, redis_service
):
    # Arrange
    create_migration_file(redis_service.migration, "100", "101")

    mock_get_migration_dir.return_value = redis_service.migration

    redis_service.version = "002"

    redis = RedisMigrations(redis_service)
    mocked_db = AsyncMock()

    # Action
    with patch.object(redis, "_create_redis_instance", return_value=mocked_db):
        with pytest.raises(RevisionNotFoundError) as exc:
            await redis.rollback()

    # Assert
    assert "[AU1005] Revision not found: Revision: 002" == str(exc.value)


@pytest.mark.asyncio
@patch(
    "subvortex.auto_upgrader.src.migrations.redis_migrations.saup.get_migration_directory"
)
async def test_raise_exception_when_down_revision_revision_does_not_exist(
    mock_get_migration_dir, redis_service
):
    # Arrange
    create_migration_file(redis_service.migration, "100", "101")

    mock_get_migration_dir.return_value = redis_service.migration

    redis_service.version = "100"
    redis_service.rollback_version = "002"

    redis = RedisMigrations(redis_service)

    # Action
    with pytest.raises(RevisionNotFoundError) as exc:
        await redis.rollback()

    # Assert
    assert "[AU1005] Revision not found: Revision: 002" == str(exc.value)
