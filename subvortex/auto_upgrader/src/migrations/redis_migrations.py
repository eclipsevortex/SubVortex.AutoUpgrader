import os
import importlib
from dotenv import load_dotenv
from redis import asyncio as aioredis

import bittensor.utils.btlogging as btul

import subvortex.auto_upgrader.src.constants as sauc
import subvortex.auto_upgrader.src.path as saup
import subvortex.auto_upgrader.src.exception as saue
from subvortex.auto_upgrader.src.service import Service
from subvortex.auto_upgrader.src.migrations.base import Migration

# Resolve the path two levels up from the current file
env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), f"../../.env"))
load_dotenv(dotenv_path=env_path)


class RedisMigrations(Migration):
    def __init__(self, service: Service):
        self.migration_path = saup.get_migration_directory(service=service)
        self.previous_version = None
        self.modules = {}  # revision -> module
        self.graph = {}  # revision -> down_revision
        self.sorted_revisions = []  # Topologically sorted list

    async def apply(self):
        # Create a database instance
        database = self._create_redis_instance()

        # Load the migrations
        self._load_migrations()
        btul.logging.debug(
            f"# of migrations: {len(self.sorted_revisions)}",
            prefix=sauc.SV_LOGGER_NAME,
        )

        # Get the current version
        current_version = await self._get_current_version(database)
        btul.logging.debug(
            f"🔍 Current database version: {current_version}",
            prefix=sauc.SV_LOGGER_NAME,
        )

        # Set rollback target
        self.previous_version = current_version

        # Set reached variable
        reached = current_version == "0.0.0"

        # Determinate all the revisions that need to be applied
        path = []
        for rev in self.sorted_revisions:
            if not reached:
                if rev == current_version:
                    reached = True
                continue
            else:
                if rev != current_version:
                    path.append(rev)

        if not path:
            btul.logging.debug(
                "✅ No migrations to apply.",
                prefix=sauc.SV_LOGGER_NAME,
            )
            return

        for rev in path:
            btul.logging.debug(
                f"⬆️  Applying migration: {rev}",
                prefix=sauc.SV_LOGGER_NAME,
            )

            # Set the mode
            await database.set(f"migration_mode:{rev}", "dual")

            # Rollout the migration
            await self.modules[rev].rollout(database)

            # Set the mode and version
            await database.set("version", rev)
            await database.set(f"migration_mode:{rev}", "new")

    async def rollback(self):
        # Create the database instance
        database = self._create_redis_instance()

        # Load the migrations
        self._load_migrations()
        btul.logging.debug(
            f"# of migrations: {len(self.sorted_revisions)}",
            prefix=sauc.SV_LOGGER_NAME,
        )

        # Get the current version
        current_version = await self._get_current_version(database)
        btul.logging.debug(
            f"🔍 Current database version: {current_version}",
            prefix=sauc.SV_LOGGER_NAME,
        )

        # Set the previous version as target version
        target_version = self.previous_version
        if not target_version:
            btul.logging.info(
                "ℹ️ No rollback target version set. Skipping rollback.",
                prefix=sauc.SV_LOGGER_NAME,
            )
            return

        if current_version == target_version:
            btul.logging.info(
                "✅ Current version matches rollback target. No rollback needed.",
                prefix=sauc.SV_LOGGER_NAME,
            )
            return

        if current_version not in self.sorted_revisions:
            raise saue.RevisionNotFoundError(revision=current_version)

        if (
            not target_version or target_version != "0.0.0"
        ) and target_version not in self.sorted_revisions:
            raise saue.RevisionNotFoundError(revision=target_version)

        # Determinate all the migrations that have to be applied
        path = []
        collecting = False
        for rev in reversed(self.sorted_revisions):
            if rev == current_version:
                collecting = True
            if collecting:
                path.append(rev)
            if rev == target_version:
                break

        if not path:
            btul.logging.info(
                "✅ No rollback actions needed.",
                prefix=sauc.SV_LOGGER_NAME,
            )
            return

        btul.logging.info(
            f"↩️ Rollback path: {path}",
            prefix=sauc.SV_LOGGER_NAME,
        )

        for rev in path:
            btul.logging.info(
                f"⬇️  Rolling back migration: {rev}",
                prefix=sauc.SV_LOGGER_NAME,
            )

            # Set the mode
            await database.set(f"migration_mode:{rev}", "dual")

            # Rollback the migration
            await self.modules[rev].rollback(database)

            # Set the mode and version
            parent_version = self.graph.get(rev)
            if parent_version:
                await database.set("version", parent_version)
                await database.set(f"migration_mode:{parent_version}", "legacy")
            else:
                await database.set("version", "0.0.0")

    def _create_redis_instance(self):
        return aioredis.StrictRedis(
            host=os.getenv("SUBVORTEX_DATABASE_HOST", "localhost"),
            port=int(os.getenv("SUBVORTEX_DATABASE_PORT", 6379)),
            db=int(os.getenv("SUBVORTEX_DATABASE_INDEX", 0)),
            password=os.getenv("SUBVORTEX_DATABASE_PASSWORD"),
        )

    def _load_migrations(self):
        if not self.migration_path or not os.path.exists(self.migration_path):
            raise saue.MissingDirectoryError(directory_path=self.migration_path)

        # 1. Load all migration files
        for fname in os.listdir(self.migration_path):
            if not fname.endswith(".py"):
                continue

            module = self._load_module(path=self.migration_path, name=fname)

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

        # 2. Check that every non-None down_revision exists
        for revision, down_revision in self.graph.items():
            if down_revision is not None and down_revision not in self.modules:
                raise saue.DownRevisionNotFoundError(
                    down_revision=down_revision,
                )

        self.sorted_revisions = self._topological_sort()

    def _topological_sort(self):
        visited = set()
        result = []

        def visit(rev):
            if rev in visited or rev is None:
                return
            parent = self.graph.get(rev)
            visit(parent)
            visited.add(rev)
            result.append(rev)

        for rev in self.modules:
            visit(rev)

        return result

    async def _get_current_version(self, database):
        value = await database.get("version")
        if value is None:
            return "0.0.0"
        return value.decode().strip()

    def _load_module(self, path: str, name: str):
        try:
            fpath = os.path.join(path, name)
            spec = importlib.util.spec_from_file_location(name[:-3], fpath)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module
        except Exception as e:
            raise saue.ModuleMigrationError(name=name, details=str(e))
