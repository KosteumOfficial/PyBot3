class PyBot3Error(Exception):
    """Base exception for PyBot3."""


class AuthenticationError(PyBot3Error):
    """Raised when authentication for a platform fails."""


class PlatformError(PyBot3Error):
    """Raised when a platform-specific operation fails."""


class RateLimitError(PyBot3Error):
    """Raised when API rate limits are reached."""


class NetworkError(PyBot3Error):
    """Raised for network-related failures."""


class UnsupportedFeatureError(PyBot3Error):
    """Raised when a platform does not support a requested feature."""


class HandlerError(PyBot3Error):
    """Raised when a handler or middleware fails."""


class InvalidConfigurationError(PyBot3Error):
    """Raised when a bot is configured incorrectly."""
