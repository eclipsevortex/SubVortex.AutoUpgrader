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
import re
from os import path

here = path.abspath(path.dirname(__file__))


def get_components(path: str, role: str):
    base_path = os.path.join(path, f"subvortex/{role}")
    excluded = {"subvortex.egg-info", "__pycache__", "core", "auto_upgrader"}

    services = {}
    for item in os.listdir(base_path):
        full_path = os.path.join(base_path, item)
        if os.path.isdir(full_path) and item not in excluded:
            services[item] = full_path

    return services


def get_version(path: str):
    if not path:
        return None

    # Get the version file
    version_path = os.path.join(path, "version.py")
    if not os.path.exists(version_path):
        version_path = os.path.join(path, "pyproject.toml")
        if not os.path.exists(version_path):
            return None

    # Get the version
    with open(version_path, encoding="utf-8") as version_file:
        content = version_file.read()

        version_match = re.search(
            r"^__version__\s*=\s*['\"]([0-9]+\.[0-9]+\.[0-9]+(?:-(?:alpha|rc)\.\d+)?)['\"]",
            content,
            re.MULTILINE,
        )
        if version_match:
            return version_match.group(1)

        version_match = re.search(
            r"^version\s*=\s*['\"]([0-9]+\.[0-9]+\.[0-9]+(?:-(?:alpha|rc)\.\d+)?)['\"]",
            content,
            re.MULTILINE,
        )
        if version_match:
            return version_match.group(1)

        raise RuntimeError("Unable to find version string.")
