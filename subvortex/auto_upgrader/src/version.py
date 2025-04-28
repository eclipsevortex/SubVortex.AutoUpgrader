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
import re
import os
from os import path
from pathlib import Path
from packaging.version import Version

import subvortex.auto_upgrader.src.constants as sauc

here = path.abspath(path.dirname(__file__))


def normalize_version(version: str) -> str:
    # Remove leading "v" if present
    version = version.lstrip("v")

    # Replace pre-release suffix
    return re.sub(
        r"-(alpha|beta|rc)\.(\d+)",
        lambda m: {"alpha": "a", "beta": "b", "rc": "rc"}[m.group(1)] + m.group(2),
        version,
    )


def denormalize_version(version: str) -> str:
    # Revert pre-release suffixes
    version = re.sub(
        r"(a|b|rc)(\d+)",
        lambda m: {"a": "-alpha.", "b": "-beta.", "rc": "-rc."}[m.group(1)]
        + m.group(2),
        version,
    )

    return version


def get_local_version() -> str:
    """
    Scans the working directory for local versions of subvortex,
    matches versioned folders, and returns the latest semantic version.
    """
    version_pattern = re.compile(r"subvortex-(\d+\.\d+\.\d+(?:[a-z]+\d+)?)")
    candidates = []

    if not os.path.exists(sauc.SV_WORKING_DIRECTORY):
        return None

    for entry in os.listdir(sauc.SV_WORKING_DIRECTORY):
        match = version_pattern.match(entry)
        if match:
            version_str = match.group(1)
            try:
                version_obj = Version(version_str)
                candidates.append((version_obj, entry))
            except Exception:
                continue  # skip malformed versions

    if not candidates:
        return None

    # Sort and return the highest version
    latest_version_dir = sorted(candidates, key=lambda x: x[0], reverse=True)[0][0]
    return str(latest_version_dir)


def is_version_before_auto_upgrader(version: str):
    return version == sauc.DEFAULT_LAST_RELEASE.get("global")


def _get_version():
    pyproject = Path(path.join(here, "../pyproject.toml"))
    if not pyproject.exists():
        return "0.0.0"

    content = pyproject.read_text()
    match = re.search(r'version\s*=\s*"([^"]+)"', content)
    return match.group(1) if match else None


__VERSION__ = _get_version()
