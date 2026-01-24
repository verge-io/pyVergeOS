"""Tests for exception classes."""

from pyvergeos.exceptions import (
    APIError,
    AuthenticationError,
    NotConnectedError,
    NotFoundError,
    TaskError,
    TaskTimeoutError,
    VergeConnectionError,
    VergeError,
    VergeTimeoutError,
)


class TestExceptions:
    """Tests for exception hierarchy."""

    def test_verge_error_is_base(self) -> None:
        assert issubclass(VergeConnectionError, VergeError)
        assert issubclass(VergeTimeoutError, VergeError)
        assert issubclass(NotConnectedError, VergeError)
        assert issubclass(APIError, VergeError)
        assert issubclass(TaskError, VergeError)

    def test_verge_connection_error(self) -> None:
        error = VergeConnectionError("Connection failed")
        assert str(error) == "Connection failed"
        assert isinstance(error, VergeError)

    def test_verge_timeout_error(self) -> None:
        error = VergeTimeoutError("Request timed out")
        assert str(error) == "Request timed out"
        assert isinstance(error, VergeError)

    def test_api_error_has_status_code(self) -> None:
        error = APIError("Something went wrong", status_code=500)
        assert error.status_code == 500
        assert str(error) == "Something went wrong"

    def test_api_error_subclasses(self) -> None:
        assert issubclass(AuthenticationError, APIError)
        assert issubclass(NotFoundError, APIError)

    def test_authentication_error(self) -> None:
        error = AuthenticationError("Invalid credentials", status_code=401)
        assert error.status_code == 401

    def test_not_found_error(self) -> None:
        error = NotFoundError("VM not found", status_code=404)
        assert error.status_code == 404

    def test_task_error_has_task_id(self) -> None:
        error = TaskError("Task failed", task_id=123)
        assert error.task_id == 123
        assert str(error) == "Task failed"

    def test_task_timeout_error(self) -> None:
        error = TaskTimeoutError("Timed out", task_id=456)
        assert error.task_id == 456
        assert issubclass(TaskTimeoutError, TaskError)
