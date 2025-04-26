import os
from dotenv import load_dotenv

load_dotenv()

SV_LOGGER_NAME = "Auto Updater"

# Directories
SV_EXECUTION_DIR = os.path.abspath(os.path.expanduser("~/subvortex"))
SV_WORKING_DIRECTORY = os.path.expandvars(
    os.getenv("SUBVORTEX_WORKING_DIRECTORY", "$HOME")
)

# Time in seconds to run the check of new release
SV_CHECK_INTERVAL = int(os.getenv("SUBVORTEX_CHECK_INTERVAL", 60))

# Github
SV_GITHUB_TOKEN = os.getenv("SUBVORTEX_GITHUB_TOKEN")

# Prerelease
SV_PRERELEASE_ENABLED = os.getenv("SUBVORTEX_PRERELEASE_ENABLED", "False").lower() == "true"
SV_PRERELEASE_TYPE = os.getenv("SUBVORTEX_PRERELEASE_TYPE", "")

# Variables about execution
SV_EXECUTION_ROLE = os.getenv("SUBVORTEX_EXECUTION_ROLE", "miner")
SV_EXECUTION_METHOD = os.getenv("SUBVORTEX_EXECUTION_METHOD", "service")

# Variables about assets
SV_ASSET_DIR = os.getenv("SUBVORTEX_ASSET_DIR", "/var/tmp/subvortex")

# Variables about versions before releasing Auto Upgrader
DEFAULT_LAST_RELEASE = {
    "global": "2.3.3",
    "miner.neuron": "2.3.3",
    "validator.neuron": "2.3.3",
    "validator.redis": "2.2.0",
}

SV_DISABLE_ROLLBACK = os.getenv("SUBVORTEX_DISABLE_ROLLBACK", "False").lower() == "true"
