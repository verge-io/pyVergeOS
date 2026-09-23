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


class FieldNotProjectedError(VergeError):
    """An accessor's backing field was not included in the projection.

    Raised instead of inventing a value when the field an accessor reads is
    absent from the row, which happens whenever the caller narrowed ``fields``
    (issue #117). Notably ``fields=["all"]`` is not a superset of a manager's
    default projection: ``all`` expands server-side to the resource's own
    columns, so aliased traversals such as ``machine#status#running as running``
    are never included.

    Before this existed, ``is_running`` answered ``False`` for a running VM and
    ``status`` answered ``"unknown"`` -- indistinguishable from a real answer,
    and exactly the guard a caller puts in front of a destructive operation.

    Deliberately *not* an ``AttributeError``. ``ResourceObject.__getattr__``
    is the dict fallback, and Python calls it whenever normal attribute lookup
    raises ``AttributeError`` -- so an ``AttributeError`` subclass raised
    inside a property is swallowed and re-raised as a bare "has no attribute",
    losing the diagnostic. It would also make ``hasattr()`` answer ``False``
    for a field that exists but was not fetched, which is the same silent lie
    in a new place.

    Attributes:
        field: Name of the field that was not projected.
    """

    def __init__(self, field: str, owner: str = "resource") -> None:
        self.field = field
        super().__init__(
            f"{owner} has no {field!r} field: it was not included in the "
            f"projection, so no value can be reported. Re-fetch with the "
            f"manager's default fields, or add {field!r} to the fields "
            f"argument. Note that fields=['all'] does not include aliased "
            f"joins such as {field!r}."
        )


class TaskError(VergeError):
    """Task execution failed."""

    def __init__(self, message: str, task_id: Optional[int] = None) -> None:
        super().__init__(message)
        self.task_id = task_id


class TaskTimeoutError(TaskError):
    """Task wait timed out."""

    pass
