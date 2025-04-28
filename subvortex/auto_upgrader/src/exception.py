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
class AutoUpgraderError(Exception):
    """Base class for all auto-upgrader errors."""

    def __init__(self, code: str, message: str, details: str = ""):
        self.code = code
        self.message = message
        self.details = details
        if details:
            super().__init__(f"[{code}] {message}: {details}")
        else:
            super().__init__(f"[{code}] {message}")


class MissingDirectoryError(AutoUpgraderError):
    def __init__(self, directory_path: str):
        super().__init__(
            code="AU1001",
            message="Required directory is missing",
            details=f"Path not found: {directory_path}",
        )


class MissingFileError(AutoUpgraderError):
    def __init__(self, file_path: str):
        super().__init__(
            code="AU1002",
            message="Required file is missing",
            details=f"Path not found: {file_path}",
        )


class ServicesLoadError(AutoUpgraderError):
    def __init__(self, version: str):
        super().__init__(
            code="AU1003",
            message="Failed to load services",
            details=f"Version: {version}",
        )


class MalformedMigrationFileError(AutoUpgraderError):
    def __init__(self, file: str):
        super().__init__(
            code="AU1004",
            message="Malformed migration file",
            details=f"File: {file}",
        )


class RevisionNotFoundError(AutoUpgraderError):
    def __init__(self, revision: str = None):
        super().__init__(
            code="AU1005",
            message="Revision not found",
            details=f"Revision: {revision}" if revision else None,
        )


class InvalidRevisionError(AutoUpgraderError):
    def __init__(self, revision: str, down_revision: str):
        super().__init__(
            code="AU1006",
            message="Invalid revision",
            details=f"Revision: {revision}, Down revision: {down_revision}",
        )


class RuntimeError(AutoUpgraderError):
    def __init__(self, action: str, details: str):
        super().__init__(
            code="AU1007",
            message="Runtime error",
            details=f"Action: {action} - {details}",
        )


class ModuleMigrationError(AutoUpgraderError):
    def __init__(self, name: str, details: str):
        super().__init__(
            code="AU1008",
            message="Module migration error",
            details=f"Name: {name} - {details}",
        )


class MissingVersionError(AutoUpgraderError):
    def __init__(self, name: str, type: str):
        super().__init__(
            code="AU1009",
            message="Version missing",
            details=f"Name: {name}, Type: {type}",
        )


class DownRevisionNotFoundError(AutoUpgraderError):
    def __init__(self, down_revision: str):
        super().__init__(
            code="AU1010",
            message="Down revision not found",
            details=f"Down revision: {down_revision}",
        )


class ReleaseNotFoundError(AutoUpgraderError):
    def __init__(self, url: str):
        super().__init__(
            code="AU1011",
            message="Release link not found",
            details=f"Url: {url}",
        )


class NoReleaseAvailableError(AutoUpgraderError):
    def __init__(self):
        super().__init__(code="AU1012", message="No release available")


class PackageNotFoundError(AutoUpgraderError):
    def __init__(self, url: str):
        super().__init__(
            code="AU1014",
            message="Package link not found",
            details=f"Url: {url}",
        )


class UnexpectedError(AutoUpgraderError):
    def __init__(self, reason: str = "An unexpected error occurred"):
        super().__init__(
            code="AU9999", message="Unknown internal error", details=reason
        )
