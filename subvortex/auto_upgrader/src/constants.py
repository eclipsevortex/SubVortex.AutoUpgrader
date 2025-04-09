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
from dotenv import load_dotenv

load_dotenv()

SV_LOGGER_NAME = "Auto Updater"

SV_WORKING_DIRECTORY = os.path.expandvars(
    os.getenv("SUBVORTEX_WORKING_DIRECTORY", "$HOME")
)

# Variables about the releases
SV_PRERELEASE_ENABLED = os.getenv("SUBVORTEX_PRERELEASE_ENABLED", False)

# Variables about the repository
SV_GITHUB_REPO_OWNER = os.getenv("SUBVORTEX_GITHUB_REPO_OWNER", "eclipsevortex")
SV_GITHUB_REPO_NAME = os.getenv("SUBVORTEX_GITHUB_REPO_NAME", "SubVortex")
SV_GITHUB_TOKEN = os.getenv("SUBVORTEX_GITHUB_TOKEN")

# Variables about assets
SV_ASSET_DIR = os.getenv("SUBVORTEX_ASSET_DIR", "/var/tmp/subvortex")

SV_EXECUTION_METHOD = os.getenv("SUBVORTEX_EXECUTION_METHOD", "service")
