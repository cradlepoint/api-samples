"""Custom exceptions for the Ericsson Inventory SDK."""


class CradlepointSDKError(Exception):
    """Base exception for all SDK errors."""

    def __init__(self, message: str, status_code: int | None = None):
        self.status_code = status_code
        super().__init__(message)


class AuthenticationError(CradlepointSDKError):
    """Raised when authentication fails (401/403)."""


class NotFoundError(CradlepointSDKError):
    """Raised when a resource is not found (404)."""


class RateLimitError(CradlepointSDKError):
    """Raised when the API rate limit is exceeded (429)."""


class BadRequestError(CradlepointSDKError):
    """Raised on a 400 Bad Request response."""
