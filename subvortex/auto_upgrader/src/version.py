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
        lambda m: {
            "a": "-alpha.",
            "b": "-beta.",
            "rc": "-rc."
        }[m.group(1)] + m.group(2),
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


def _get_version():
    pyproject = Path(path.join(here, "../pyproject.toml"))
    if not pyproject.exists():
        return "0.0.0"

    content = pyproject.read_text()
    match = re.search(r'version\s*=\s*"([^"]+)"', content)
    return match.group(1) if match else None


__VERSION__ = _get_version()
