import re
import os
from packaging.version import Version

import subvortex.auto_upgrader.src.constants as sauc


def normalize_version(version: str) -> str:
    # Remove leading "v" if present
    version = version.lstrip("v")

    # Replace pre-release suffix
    return re.sub(
        r"-(alpha|beta|rc)\.(\d+)",
        lambda m: {"alpha": "a", "beta": "b", "rc": "rc"}[m.group(1)] + m.group(2),
        version,
    )


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
        raise RuntimeError("No valid local subvortex versions found.")

    # Sort and return the highest version
    latest_version_dir = sorted(candidates, key=lambda x: x[0], reverse=True)[0][0]
    return str(latest_version_dir)
