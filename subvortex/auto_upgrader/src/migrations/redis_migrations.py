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

# Load the env file
load_dotenv(dotenv_path=env_path)


class RedisMigrations(Migration):
    def __init__(self, service: Service):
        super().__init__(service)
        self.service = service
        self.migration = service.migration
        self.modules = {}  # revision -> module
        self.graph = {}  # revision -> down_revision
        self.sorted_revisions = []  # Topologically sorted list

    def _load_migrations(self):
        # Build the migration path
        migration_path = saup.get_migration_directory(service=self.service)
        if migration_path is None:
            return

        # Check if the provided migration path exists
        if not os.path.exists(migration_path):
            raise saue.MissingDirectoryError(directory_path=migration_path)

        for fname in os.listdir(migration_path):
            if not fname.endswith(".py"):
                continue

            # Load the migration module
            module = self._load_module(path=migration_path, name=fname)

            if not hasattr(module, "rollout") or not hasattr(module, "rollback"):
                raise saue.MalformedMigrationFileError(file=fname)

            revision = getattr(module, "revision", None)
            down_revision = getattr(module, "down_revision", None)

            if revision is None:
                raise saue.RevisionNotFoundError()

            if down_revision == revision:
                raise saue.InvalidRevisionLinkError(
                    revision=revision, down_revision=down_revision
                )

            self.modules[revision] = module
            self.graph[revision] = down_revision

        self.sorted_revisions = self._topological_sort()

    def _topological_sort(self):
        visited = set()
        result = []

        def visit(rev):
            if rev in visited or rev is None:
                return

            parent = self.graph.get(rev)
            visit(parent)
            if rev not in visited:
                visited.add(rev)
                result.append(rev)

        for rev in self.modules:
            visit(rev)

        return result

    async def apply(self):
        # Load the migrations
        self._load_migrations()
        btul.logging.debug(
            f"# of migrations: {len(self.sorted_revisions)}",
            prefix=sauc.SV_LOGGER_NAME,
        )

        # TODO: Filter migration from the current version until the latest one

        # Set the current and target verions
        current = self.service.version
        target = self.sorted_revisions[-1] if self.sorted_revisions else None

        if current == target:
            return

        # Store rollback target (previous version)
        self.service.rollback_version = current

        # Create a database instance
        database = self._create_redis_instance()

        # Get the path for each revisions
        path = []
        reached = current == None
        for rev in self.sorted_revisions:
            if rev == current:
                reached = True
            elif reached:
                path.append(rev)

            if rev == target:
                break

        # Loop through the path to rollout the migration
        for rev in path:
            btul.logging.info(
                f"⬆️  Applying migration: {rev}", prefix=sauc.SV_LOGGER_NAME
            )

            # Set mode to dual so app reads/writes both if needed
            await database.set(f"migration_mode:{self.service.version}", "dual")

            # Rollout migration
            await self.modules[rev].rollout(database)

            # Set version
            self.service.version = rev

            # Set mode to dual so app reads/writes both if needed
            await database.set("version", self.service.version)
            await database.set(f"migration_mode:{self.service.version}", "new")

    async def rollback(self):
        # Load the migrations
        self._load_migrations()
        btul.logging.debug(
            f"# of migrations: {len(self.sorted_revisions)}", prefix=sauc.SV_LOGGER_NAME
        )

        # Set the current and target verions
        current = self.service.version
        target = self.service.rollback_version

        if current == target:
            return

        if current not in self.sorted_revisions:
            raise saue.RevisionNotFoundError(revision=current)

        if target and target not in self.sorted_revisions:
            raise saue.RevisionNotFoundError(revision=target)

        # Create a database instance
        database = self._create_redis_instance()

        # Get the path for each revisions
        path = []
        for rev in reversed(self.sorted_revisions):
            if rev == current:
                path.append(rev)
            elif path:
                path.append(rev)

            if rev == target:
                break

        # Loop through the path to rollout the migration
        for rev in path:
            btul.logging.info(
                f"⬇️  Rolling back migration: {rev}", prefix=sauc.SV_LOGGER_NAME
            )

            # Set mode to dual so app reads/writes both if needed
            await database.set(f"migration_mode:{self.service.version}", "dual")

            # Rollback migration
            await self.modules[rev].rollback(database)

            # Update the version
            self.service.version = self.graph[rev]

            # Set mode to dual so app reads/writes both if needed
            if self.service.version is not None:
                await database.set("version", self.service.version)
                await database.set(f"migration_mode:{rev}", "legacy")
            else:
                await database.set("version", "0.0.0")

    def _create_redis_instance(self):
        # Create the instance of redis
        database = aioredis.StrictRedis(
            host=os.getenv("SUBVORTEX_REDIS_HOST", "localhost"),
            port=os.getenv("SUBVORTEX_REDIS_PORT", 6379),
            db=os.getenv("SUBVORTEX_REDIS_INDEX", 0),
            password=os.getenv("SUBVORTEX_REDIS_PASSWORD"),
        )

        return database

    def _load_module(self, path: str, name: str):
        try:
            fpath = os.path.join(path, name)
            spec = importlib.util.spec_from_file_location(name[:-3], fpath)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            return module
        except Exception as e:
            raise saue.ModuleMigrationError(name=name, details=str(e))
