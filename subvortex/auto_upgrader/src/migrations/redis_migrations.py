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
import re
import shutil
import importlib
from dotenv import load_dotenv
from redis import asyncio as aioredis

import bittensor.utils.btlogging as btul
import subvortex.auto_upgrader.src.constants as sauc
import subvortex.auto_upgrader.src.version as sauv
import subvortex.auto_upgrader.src.path as saup
import subvortex.auto_upgrader.src.exception as saue
from subvortex.auto_upgrader.src.service import Service
from subvortex.auto_upgrader.src.migrations.base import Migration
from packaging.version import Version

# Resolve the path two levels up from the current file
env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), f"../../.env"))
load_dotenv(dotenv_path=env_path)


SV_REDIS_DIR = "/var/tmp/subvortex-dump"
SV_REDIS_DB_FILENAME = "subvortex-validator-redis.dump"


class RedisMigrations(Migration):
    @property
    def service_name(self):
        service = self.previous_service or self.new_service
        return service.name if service else None

    def __init__(self, service: Service, previous_service: Service = None):
        self.new_service = service
        self.previous_service = previous_service

        self.new_migration_path = (
            saup.get_migration_directory(service=service) if service else None
        )
        self.old_migration_path = (
            saup.get_migration_directory(service=previous_service)
            if previous_service
            else None
        )

        self.modules = {}  # revision -> module
        self.graph = {}  # revision -> down_revision
        self.sorted_revisions = []
        self.applied_revisions = []  # Keep track of what we applied during apply()

    async def prepare(self):
        config_name = f"template-subvortex-{sauc.SV_EXECUTION_ROLE}-redis"

        # Get the config of the previous config
        previous_config = next(
            (
                x
                for x in saup.get_service_template(self.previous_service)
                if x == config_name
            ),
            None,
        )

        # Get the config of the new config
        new_config = next(
            (
                x
                for x in saup.get_service_template(self.new_service)
                if x == config_name
            ),
            None,
        )

        # Get the dump dir of the previous version
        previous_dump_dir, previous_dump_filename = self._get_redis_dump_config(
            previous_config
        )
        if not os.path.exists(f"{previous_dump_dir}/{previous_dump_filename}"):
            return

        # Get the dump dir of the new version
        new_dump_dir, new_dump_filename = self._get_redis_dump_config(new_config)

        # Compare the dir
        if previous_dump_dir == new_dump_dir:
            btul.logging.debug(
                "Redis dump file location unchanged; no copy needed",
                prefix=sauc.SV_LOGGER_NAME,
            )
            return

        # Ensure the destination exists
        os.makedirs(new_dump_dir, exist_ok=True)

        # Copy the dump from previous to new
        shutil.copy2(
            f"{previous_dump_dir}/{previous_dump_filename}",
            f"{new_dump_dir}/{new_dump_filename}",
        )

        btul.logging.debug(
            f"Copied dump file from {previous_dump_dir}/{previous_dump_filename} "
            f"to {new_dump_dir}/{new_dump_filename}",
            prefix=sauc.SV_LOGGER_NAME,
        )

    async def apply(self):
        database = self._create_redis_instance()

        # Load migrations
        new_revisions = self._load_migrations_from_path(self.new_migration_path)
        old_revisions = (
            self._load_migrations_from_path(self.old_migration_path)
            if self.previous_service
            else []
        )

        # Read current DB version
        current_version = await self._get_current_version(database)
        btul.logging.debug(
            f"🔍 Current database version for {self.service_name}: {current_version}",
            prefix=sauc.SV_LOGGER_NAME,
        )

        # Determine the highest revions
        highest_revision = (
            sorted(new_revisions, key=lambda v: Version(v))[-1]
            if len(new_revisions) > 0
            else "0.0.0"
        )

        if Version(current_version) < Version(highest_revision):
            await self._upgrade(
                database=database,
                revisions=new_revisions,
                current_version=current_version,
            )
        elif Version(current_version) > Version(highest_revision):
            await self._downgrade(
                database=database,
                revisions=old_revisions,
                current_version=highest_revision,
            )
        else:
            btul.logging.info(
                f"✅ Database already at target version for {self.service_name}",
                prefix=sauc.SV_LOGGER_NAME,
            )

    async def rollback(self):
        if not self.applied_revisions:
            btul.logging.info(
                "ℹ️ No applied migrations to rollback.", prefix=sauc.SV_LOGGER_NAME
            )
            return

        database = self._create_redis_instance()

        btul.logging.info(
            f"↩️ Rolling back applied migrations for {self.service_name}: {self.applied_revisions}",
            prefix=sauc.SV_LOGGER_NAME,
        )

        # Rollback in reverse order
        for rev in reversed(self.applied_revisions):
            btul.logging.info(
                f"⬇️  Rolling back migration for {self.service_name}: {rev}",
                prefix=sauc.SV_LOGGER_NAME,
            )
            await database.set(f"migration_mode:{rev}", "dual")
            await self.modules[rev].rollback(database)

            parent_version = self.graph.get(rev)
            if parent_version:
                await database.set("version", parent_version)
                await database.set(f"migration_mode:{parent_version}", "legacy")
            else:
                await database.set("version", "0.0.0")

        # Clear applied revisions after rollback
        self.applied_revisions.clear()

    async def _upgrade(self, database, revisions, current_version):
        btul.logging.info(
            f"⬆️  Running upgrade migrations for {self.service_name}...",
            prefix=sauc.SV_LOGGER_NAME,
        )

        # Sort correctly
        started = current_version == "0.0.0"
        for rev in sorted(revisions, key=lambda v: Version(v)):
            if not started:
                if rev == current_version:
                    started = True

                continue  # skip until current_version is reached

            btul.logging.info(
                f"⬆️  Applying migration for {self.service_name}: {rev}",
                prefix=sauc.SV_LOGGER_NAME,
            )

            await database.set(f"migration_mode:{rev}", "dual")
            await self.modules[rev].rollout(database)
            await database.set("version", rev)
            await database.set(f"migration_mode:{rev}", "new")

            self.applied_revisions.append(rev)

    async def _downgrade(self, database, revisions, current_version):
        btul.logging.info(
            f"⬇️  Running downgrade migrations for {self.service_name}...",
            prefix=sauc.SV_LOGGER_NAME,
        )

        for rev in sorted(revisions, key=lambda v: Version(v), reverse=True):
            if Version(rev) <= Version(current_version):
                break

            btul.logging.info(
                f"⬇️  Rolling back migration for {self.service_name}: {rev}",
                prefix=sauc.SV_LOGGER_NAME,
            )
            await database.set(f"migration_mode:{rev}", "dual")
            await self.modules[rev].rollback(database)

            parent_version = self.graph.get(rev)
            if parent_version:
                await database.set("version", parent_version)
                await database.set(f"migration_mode:{parent_version}", "legacy")
            else:
                await database.set("version", "0.0.0")

            self.applied_revisions.append(rev)

    def _create_redis_instance(self):
        password = os.getenv("SUBVORTEX_DATABASE_PASSWORD")
        if not password:
            btul.logging.warning(
                f"No password configured. It is recommended to have one.",
                prefix=sauc.SV_LOGGER_NAME,
            )

        return aioredis.StrictRedis(
            host=os.getenv("SUBVORTEX_DATABASE_HOST", "localhost"),
            port=int(os.getenv("SUBVORTEX_DATABASE_PORT", 6379)),
            db=int(os.getenv("SUBVORTEX_DATABASE_INDEX", 0)),
            password=os.getenv("SUBVORTEX_DATABASE_PASSWORD"),
        )

    async def _get_current_version(self, database):
        value = await database.get("version")
        if value is None:
            return "0.0.0"
        return value.decode().strip()

    def _load_migrations_from_path(self, migration_path):
        revisions = []

        if not migration_path or not os.path.exists(migration_path):
            raise saue.MissingDirectoryError(directory_path=migration_path)

        for fname in os.listdir(migration_path):
            if not fname.endswith(".py"):
                continue

            module = self._load_module(path=migration_path, name=fname)

            if not hasattr(module, "rollout") or not hasattr(module, "rollback"):
                raise saue.MalformedMigrationFileError(file=fname)

            revision = getattr(module, "revision", None)
            down_revision = getattr(module, "down_revision", None)

            if revision is None:
                raise saue.RevisionNotFoundError()

            if down_revision == revision:
                raise saue.InvalidRevisionError(
                    revision=revision, down_revision=down_revision
                )

            self.modules[revision] = module
            self.graph[revision] = down_revision
            revisions.append(revision)

        return revisions

    def _load_module(self, path: str, name: str):
        try:
            fpath = os.path.join(path, name)
            spec = importlib.util.spec_from_file_location(name[:-3], fpath)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module
        except Exception as e:
            raise saue.ModuleMigrationError(name=name, details=str(e))

    def _get_redis_dump_config(self, conf_path: str) -> str | None:
        dump_dir = SV_REDIS_DIR
        db_filename = SV_REDIS_DB_FILENAME

        with open(conf_path, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue

                dir_match = re.match(r"^\s*dir\s+(.+)", line)
                if dir_match:
                    dump_dir = dir_match.group(1).strip()
                    continue

                file_match = re.match(r"^\s*dbfilename\s+(.+)", line)
                if file_match:
                    db_filename = file_match.group(1).strip()
                    continue

        return dump_dir, db_filename
