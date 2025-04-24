import os
import importlib
from dotenv import load_dotenv
from redis import asyncio as aioredis

import bittensor.utils.btlogging as btul

import subvortex.auto_upgrader.src.constants as sauc
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
        for fname in os.listdir(self.migration):
            if not fname.endswith(".py"):
                continue

            fpath = os.path.join(self.migration, fname)
            spec = importlib.util.spec_from_file_location(fname[:-3], fpath)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)

            revision = getattr(mod, "revision", None)
            down_revision = getattr(mod, "down_revision", None)

            if (
                not revision
                or not hasattr(mod, "rollout")
                or not hasattr(mod, "rollback")
            ):
                raise ValueError(f"Invalid migration file: {fname}")

            if revision is None or down_revision == revision:
                raise ValueError(f"Invalid migration file: {fname}")

            self.modules[revision] = mod
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

    def apply(self):
        # Load the migrations
        self._load_migrations()
        btul.logging.debug(
            f"# of migrations: {len(self.sorted_revisions)}", prefix=sauc.SV_LOGGER_NAME
        )

        # Set the current and target verions
        current = self.service.version
        target = self.sorted_revisions[-1] if self.sorted_revisions else None

        if current == target:
            return

        if target not in self.sorted_revisions:
            raise ValueError(f"Target revision {target} not found.")

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

            # Rollout migration
            self.modules[rev].rollout(database)

            # Set version
            self.service.version = rev

    def rollback(self):
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

        if current not in self.sorted_revisions or (
            target and target not in self.sorted_revisions
        ):
            raise ValueError("Revisions not found in migration history.")

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

            # Rollback migration
            self.modules[rev].rollback(database)

            # Update the version
            self.service.version = self.graph[rev]

    def _create_redis_instance(self):
        # Create the instance of redis
        database = aioredis.StrictRedis(
            host=os.getenv("SUBVORTEX_REDIS_HOST", "localhost"),
            port=os.getenv("SUBVORTEX_REDIS_PORT", 6379),
            db=os.getenv("SUBVORTEX_REDIS_INDEX", 0),
            password=os.getenv("SUBVORTEX_REDIS_PASSWORD"),
        )

        return database
