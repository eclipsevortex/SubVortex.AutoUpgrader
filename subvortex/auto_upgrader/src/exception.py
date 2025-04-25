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
            details=f"Revision: {revision}" if revision else None
        )


class InvalidRevisionLinkError(AutoUpgraderError):
    def __init__(self, revision: str, down_revision: str):
        super().__init__(
            code="AU1006",
            message="Invalid migration revision",
            details=f"Revision: {revision}, Down Revision: {down_revision}",
        )


class UnexpectedError(AutoUpgraderError):
    def __init__(self, reason: str = "An unexpected error occurred"):
        super().__init__(
            code="AU9999", message="Unknown internal error", details=reason
        )
