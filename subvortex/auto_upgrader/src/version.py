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
import tomllib


def to_detailed_version(version_str):
    parts = version_str.split(".")
    if len(parts) != 3:
        raise ValueError("Invalid version string format")

    return (int(parts[0]), int(parts[1]), int(parts[2]))


def to_spec_version(version: str):
    details = (version.split("-")[0]).split(".")
    return (100 * int(details[0])) + (10 * int(details[1])) + (1 * int(details[2]))


def normalize_version(version: str) -> str:
    # Remove leading "v" if present
    tag = version[1:] if version.startswith("v") else version

    # Replace pre-release suffix
    return re.sub(
        r"-(alpha|beta|rc)\.(\d+)",
        lambda m: {"alpha": "a", "beta": "b", "rc": "rc"}[m.group(1)] + m.group(2),
        tag,
    )

def _get_version():
    with open("pyproject.toml", "rb") as f:
        data = tomllib.load(f)

    version = data["project"]["version"]
    return version

__VERSION__ = _get_version()