from typing import List

from subvortex.auto_upgrader.src.migrations.base import Migration

MIGRATION_TYPES = {}


class MigrationManager:
    def __init__(self, services: List):
        self.services = services
        self.migrations: List[Migration] = []

    def collect_migrations(self):
        for service in self.services:
            migration_type = getattr(service, "migration_type", None)
            if not migration_type:
                continue

            if migration_type not in MIGRATION_TYPES:
                # Lazy import when needed
                if migration_type == "redis":
                    try:
                        from subvortex.auto_upgrader.src.migrations.redis_migrations import (
                            RedisMigrations,
                        )

                        MIGRATION_TYPES["redis"] = RedisMigrations
                    except ImportError as e:
                        raise ImportError(
                            "Redis migrations require redis packages to be installed."
                        ) from e
                else:
                    raise ValueError(f"Unsupported migration type: {migration_type}")

            migration_class = MIGRATION_TYPES[migration_type]
            self.migrations.append(migration_class(service))

    async def apply(self):
        for migration in self.migrations:
            await migration.apply()

    async def rollback(self):
        for migration in reversed(self.migrations):
            await migration.rollback()
