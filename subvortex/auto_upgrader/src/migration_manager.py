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
from typing import List

from subvortex.auto_upgrader.src.migrations.base import Migration

MIGRATION_TYPES = {}


from typing import List, Tuple
from subvortex.auto_upgrader.src.migrations.base import Migration

MIGRATION_TYPES = {}


class MigrationManager:
    def __init__(self, service_pairs: List[Tuple]):
        self.service_pairs = service_pairs  # (latest_service, previous_service)
        self.migrations: List[Migration] = []

    def collect_migrations(self):
        for new_service, previous_service in self.service_pairs:
            migration_type = getattr(new_service, "migration_type", None)
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
            self.migrations.append(migration_class(new_service, previous_service))

    async def prepare(self):
        for migration in self.migrations:
            await migration.prepare()
            
    async def apply(self):
        for migration in self.migrations:
            await migration.apply()

    async def rollback(self):
        for migration in reversed(self.migrations):
            await migration.rollback()
