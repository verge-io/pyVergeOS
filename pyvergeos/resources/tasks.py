"""Task resource manager with wait functionality."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from pyvergeos.exceptions import TaskError, TaskTimeoutError
from pyvergeos.resources.base import ResourceManager, ResourceObject

if TYPE_CHECKING:
    from pyvergeos.client import VergeClient


class Task(ResourceObject):
    """Task resource object."""

    @property
    def is_complete(self) -> bool:
        """Check if task is complete."""
        return self.get("status") == "idle"

    @property
    def is_running(self) -> bool:
        """Check if task is running."""
        return self.get("status") not in ("idle", "error")

    @property
    def has_error(self) -> bool:
        """Check if task has an error."""
        return self.get("status") == "error"

    @property
    def progress(self) -> int:
        """Get task progress percentage."""
        return int(self.get("progress", 0))


class TaskManager(ResourceManager[Task]):
    """Manager for Task operations with wait functionality."""

    _endpoint = "tasks"

    def __init__(self, client: VergeClient) -> None:
        super().__init__(client)

    def _to_model(self, data: dict[str, Any]) -> Task:
        return Task(data, self)

    def wait(
        self,
        key: int,
        timeout: int = 300,
        poll_interval: int = 2,
        raise_on_error: bool = True,
    ) -> Task:
        """Wait for a task to complete.

        Args:
            key: Task $key.
            timeout: Maximum wait time in seconds (0 = infinite).
            poll_interval: Seconds between status checks.
            raise_on_error: Raise TaskError if task fails.

        Returns:
            Completed task object.

        Raises:
            TaskTimeoutError: If timeout exceeded.
            TaskError: If task fails and raise_on_error=True.
        """
        start_time = time.time()

        while True:
            task = self.get(key)

            if task.is_complete:
                return task

            if task.has_error:
                if raise_on_error:
                    error_msg = task.get("error", "Task failed")
                    raise TaskError(str(error_msg), task_id=key)
                return task

            # Check timeout
            if timeout > 0 and (time.time() - start_time) > timeout:
                raise TaskTimeoutError(
                    f"Task {key} did not complete within {timeout} seconds",
                    task_id=key,
                )

            time.sleep(poll_interval)

    def cancel(self, key: int) -> Task:
        """Cancel a running task.

        Args:
            key: Task $key.

        Returns:
            Updated task object.
        """
        self.action(key, "cancel")
        return self.get(key)
