# The MIT License (MIT)
# Copyright © 2024 Eclipse Vortex

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
from dotenv import load_dotenv

load_dotenv()

SV_LOGGER_NAME = "Auto Upgrader"

# Directories
SV_EXECUTION_DIR = os.path.abspath(os.path.expanduser("~/subvortex"))

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
