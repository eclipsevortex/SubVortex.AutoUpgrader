import os
import asyncio
from typing import List

from subvortex.auto_upgrader.src.migrations.base import Migration
from subvortex.auto_upgrader.src.migrations.redis_migrations import RedisMigrations

MIGRATION_TYPES = {
    "redis": RedisMigrations,
}


class MigrationManager:
    def __init__(self, services: List):
        self.services = services
        self.migrations: List[Migration] = []

    def collect_migrations(self):
        for service in self.services:
            if not getattr(service, "migration_type", None):
                continue

            migration_class = MIGRATION_TYPES.get(service.migration_type)
            if not migration_class:
                raise ValueError(
                    f"Unsupported migration type: {service.migration_type}"
                )

            self.migrations.append(migration_class(service))

    async def apply(self):
        for migration in self.migrations:
            await migration.apply()

    async def rollback(self):
        for migration in reversed(self.migrations):
            await migration.rollback()
