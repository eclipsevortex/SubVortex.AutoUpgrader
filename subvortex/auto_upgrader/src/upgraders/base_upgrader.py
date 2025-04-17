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
import typing
from abc import ABC, abstractmethod


class BaseUpgrader(ABC):
    @abstractmethod
    def should_skip(self):
        pass

    @abstractmethod
    def is_upgrade(self):
        pass

    @abstractmethod
    async def get_latest_version(self):
        pass

    @abstractmethod
    def get_current_version(self):
        pass

    @abstractmethod
    def get_latest_components(self) -> typing.Dict[str, str]:
        pass

    @abstractmethod
    def get_current_components(self) -> typing.Dict[str, str]:
        pass

    @abstractmethod
    def get_latest_component_version(self, name: str, path: str):
        pass

    @abstractmethod
    def get_current_component_version(self, name: str, path: str):
        pass

    @abstractmethod
    def upgrade(self):
        pass

    @abstractmethod
    def downgrade(self):
        pass

    @abstractmethod
    def teardown(self):
        pass

    @abstractmethod
    def pre_upgrade(self, previous_version: str, version: str):
        pass

    @abstractmethod
    def copy_env_file(self, component_name: str, component_path: str):
        pass