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
    service._revision = None
    service.get_current_revision = lambda: service._revision
    service.set_current_revision = lambda rev: setattr(service, "_revision", rev)
    yield service

    # Recursively remove migration directory
    shutil.rmtree(service.migration)


def create_migration_file(path, revision, down_revision):
    down_revision_str = f'"{down_revision}"' if down_revision else None
    content = f"""
revision = \"{revision}\"
down_revision = {down_revision_str}

def rollout(database):
    print("rollout {revision}")

def rollback(database):
    print("rollback {revision}")
"""
    with open(os.path.join(path, f"{revision}.py"), "w") as f:
        f.write(content)


def test_apply_all_migrations(redis_service):
    redis_service.version = None

    create_migration_file(redis_service.migration, "001", None)
    create_migration_file(redis_service.migration, "002", "001")
    create_migration_file(redis_service.migration, "003", "002")

    redis = RedisMigrations(redis_service)

    mocked_db = AsyncMock()

    with patch.object(redis, "_create_redis_instance", return_value=mocked_db):
        redis.apply()

    assert redis_service.version == "003"


def test_rollback_all_migrations(redis_service):
    redis_service.next_version = "003"

    create_migration_file(redis_service.migration, "001", None)
    create_migration_file(redis_service.migration, "002", "001")
    create_migration_file(redis_service.migration, "003", "002")

    redis = RedisMigrations(redis_service)
    redis.rollback()

    assert redis_service.version is None


def test_apply_does_nothing_when_up_to_date(redis_service):
    create_migration_file(redis_service.migration, "001", None)

    redis_service.version = "001"

    redis = RedisMigrations(redis_service)
    redis.apply()

    assert redis_service.version == "001"


def test_rollback_does_nothing_when_at_base(redis_service):
    create_migration_file(redis_service.migration, "001", None)

    redis_service.version = None

    redis = RedisMigrations(redis_service)
    redis.rollback()

    assert redis_service.version is None


def test_rollback_skips_base(redis_service):
    create_migration_file(redis_service.migration, "001", None)

    redis_service.version = "001"

    redis = RedisMigrations(redis_service)
    redis.rollback()

    assert redis_service.version is None
