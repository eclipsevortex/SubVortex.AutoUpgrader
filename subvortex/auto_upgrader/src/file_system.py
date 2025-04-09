import os
import re
from os import path

import bittensor.utils.btlogging as btul

here = path.abspath(path.dirname(__file__))


def get_components(path: str, role: str):
    base_path = os.path.join(path, f"subvortex/{role}")
    excluded = {"subvortex.egg-info", "__pycache__", "core", "auto_upgrader"}

    services = []
    for item in os.listdir(base_path):
        full_path = os.path.join(base_path, item)
        if os.path.isdir(full_path) and item not in excluded:
            services.append((item, full_path))

    return services


def get_version(component_path: str):
    # Get the version file
    version_path = os.path.join(component_path, "version.py")
    if not os.path.exists(version_path):
        version_path = os.path.join(component_path, "pyproject.toml")
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
