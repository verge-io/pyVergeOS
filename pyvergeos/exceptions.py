"""Custom exceptions for pyvergeos.

Note: Exception names are prefixed with 'Verge' to avoid shadowing
Python builtins (ConnectionError, TimeoutError).
"""

from typing import Any, Optional


class VergeError(Exception):
    """Base exception for all pyvergeos errors."""

    pass


class VergeConnectionError(VergeError):
    """Connection to VergeOS failed."""

    pass


class NotConnectedError(VergeError):
    """Operation attempted without an active connection."""

    pass


class VergeTimeoutError(VergeError):
    """Request timed out."""

    pass


class APIError(VergeError):
    """Base class for API errors.

    Attributes:
        status_code: HTTP status code, when available.
        response_body: Complete parsed JSON error body, or raw text for non-JSON
            responses. Defaults to None for errors without a response body.
            May contain sensitive data; inspect it before logging or sharing it.
    """

    def __init__(
        self, message: str, status_code: Optional[int] = None, *, response_body: Any = None
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


class AuthenticationError(APIError):
    """Authentication failed (401/403)."""

    pass


class NotFoundError(APIError):
    """Resource not found (404)."""

    pass


class ConflictError(APIError):
    """Resource conflict (409)."""

    pass


class ValidationError(APIError):
    """Validation error (422)."""

    pass


class TaskError(VergeError):
    """Task execution failed."""

    def __init__(self, message: str, task_id: Optional[int] = None) -> None:
        super().__init__(message)
        self.task_id = task_id


class TaskTimeoutError(TaskError):
    """Task wait timed out."""

    pass
