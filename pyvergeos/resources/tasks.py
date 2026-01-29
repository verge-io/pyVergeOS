"""Task resource manager with wait functionality."""

from __future__ import annotations

import builtins
import time
from typing import TYPE_CHECKING, Any

from pyvergeos.exceptions import NotFoundError, TaskError, TaskTimeoutError
from pyvergeos.filters import build_filter
from pyvergeos.resources.base import ResourceManager, ResourceObject

if TYPE_CHECKING:
    from pyvergeos.client import VergeClient


# Default fields to request for task list operations
_DEFAULT_LIST_FIELDS = [
    "$key",
    "name",
    "description",
    "enabled",
    "status",
    "action",
    "action_display",
    "table",
    "owner",
    "owner#$display as owner_display",
    "creator",
    "creator#$display as creator_display",
    "last_run",
    "delete_after_run",
    "id",
]


class Task(ResourceObject):
    """Task resource object.

    Represents a scheduled or running task in VergeOS.

    Properties:
        name: Task name.
        description: Task description.
        status: Task status ('idle' or 'running').
        is_complete: True if task is complete (idle).
        is_running: True if task is currently running.
        is_enabled: True if task is enabled.
        has_error: True if task has an error status.
        progress: Task progress percentage (0-100).
        action: The action type this task performs.
        action_display: Human-readable action description.
        owner_key: Key of the owner object.
        owner_display: Display name of the owner.
        creator_key: Key of the user who created the task.
        creator_display: Display name of the creator.
        last_run: Timestamp of last run.
        delete_after_run: Whether task deletes itself after running.
        task_id: Unique task identifier (40-char hex string).
    """

    @property
    def is_complete(self) -> bool:
        """Check if task is complete (idle)."""
        return self.get("status") == "idle"

    @property
    def is_running(self) -> bool:
        """Check if task is running."""
        return self.get("status") == "running"

    @property
    def is_enabled(self) -> bool:
        """Check if task is enabled."""
        return bool(self.get("enabled", False))

    @property
    def has_error(self) -> bool:
        """Check if task has an error."""
        return self.get("status") == "error"

    @property
    def progress(self) -> int:
        """Get task progress percentage."""
        return int(self.get("progress", 0))

    @property
    def owner_key(self) -> int | None:
        """Get owner object key."""
        owner = self.get("owner")
        return int(owner) if owner is not None else None

    @property
    def owner_display(self) -> str:
        """Get owner display name."""
        return str(self.get("owner_display", ""))

    @property
    def creator_key(self) -> int | None:
        """Get creator user key."""
        creator = self.get("creator")
        return int(creator) if creator is not None else None

    @property
    def creator_display(self) -> str:
        """Get creator display name."""
        return str(self.get("creator_display", ""))

    @property
    def task_id(self) -> str:
        """Get unique task ID (40-char hex string)."""
        return str(self.get("id", ""))

    def enable(self) -> Task:
        """Enable this task.

        Returns:
            Updated Task object.
        """
        from typing import cast

        manager = cast("TaskManager", self._manager)
        return manager.enable(self.key)

    def disable(self) -> Task:
        """Disable this task.

        Returns:
            Updated Task object.
        """
        from typing import cast

        manager = cast("TaskManager", self._manager)
        return manager.disable(self.key)

    def execute(self, **params: Any) -> Task:
        """Execute this task immediately.

        Args:
            **params: Optional parameters to pass to the task.

        Returns:
            Updated Task object.
        """
        from typing import cast

        manager = cast("TaskManager", self._manager)
        return manager.execute(self.key, **params)

    def wait(
        self,
        timeout: int = 300,
        poll_interval: int = 2,
        raise_on_error: bool = True,
    ) -> Task:
        """Wait for this task to complete.

        Args:
            timeout: Maximum wait time in seconds (0 = infinite).
            poll_interval: Seconds between status checks.
            raise_on_error: Raise TaskError if task fails.

        Returns:
            Completed Task object.

        Raises:
            TaskTimeoutError: If timeout exceeded.
            TaskError: If task fails and raise_on_error=True.
        """
        from typing import cast

        manager = cast("TaskManager", self._manager)
        return manager.wait(
            self.key,
            timeout=timeout,
            poll_interval=poll_interval,
            raise_on_error=raise_on_error,
        )


class TaskManager(ResourceManager[Task]):
    """Manager for Task operations with wait functionality.

    Tasks in VergeOS represent scheduled automation operations. They can be
    scheduled to run at specific times or triggered by events. Tasks can also
    be run manually.

    Example:
        >>> # List all tasks
        >>> tasks = client.tasks.list()
        >>> for task in tasks:
        ...     print(f"{task.name}: {task.status}")

        >>> # List running tasks
        >>> running = client.tasks.list_running()

        >>> # Wait for a task to complete
        >>> task = client.tasks.wait(task_key, timeout=300)

        >>> # Enable/disable a task
        >>> client.tasks.enable(task_key)
        >>> client.tasks.disable(task_key)

        >>> # Execute a task manually
        >>> task = client.tasks.execute(task_key)
    """

    _endpoint = "tasks"

    def __init__(self, client: VergeClient) -> None:
        super().__init__(client)

    def _to_model(self, data: dict[str, Any]) -> Task:
        return Task(data, self)

    def list(
        self,
        filter: str | None = None,
        fields: builtins.list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        *,
        status: str | None = None,
        running: bool | None = None,
        enabled: bool | None = None,
        name: str | None = None,
        **filter_kwargs: Any,
    ) -> builtins.list[Task]:
        """List tasks with optional filtering.

        Args:
            filter: OData filter string.
            fields: List of fields to return.
            limit: Maximum number of results.
            offset: Skip this many results.
            status: Filter by status ('running' or 'idle').
            running: If True, filter for running tasks only.
            enabled: Filter by enabled state.
            name: Filter by name (supports partial match with 'ct' operator).
            **filter_kwargs: Additional filter arguments.

        Returns:
            List of Task objects.

        Example:
            >>> # All tasks
            >>> tasks = client.tasks.list()

            >>> # Running tasks only
            >>> running = client.tasks.list(running=True)

            >>> # Disabled tasks
            >>> disabled = client.tasks.list(enabled=False)

            >>> # Tasks by name pattern
            >>> backup_tasks = client.tasks.list(name="Backup")
        """
        # Build filter conditions
        conditions: builtins.list[str] = []

        if filter:
            conditions.append(f"({filter})")

        if running is True:
            conditions.append("status eq 'running'")
        elif running is False:
            conditions.append("status eq 'idle'")
        elif status:
            conditions.append(f"status eq '{status.lower()}'")

        if enabled is not None:
            conditions.append(f"enabled eq {str(enabled).lower()}")

        if name:
            # Check if name contains wildcards
            if "*" in name or "?" in name:
                # Use contains for partial match
                search_term = name.replace("*", "").replace("?", "")
                if search_term:
                    conditions.append(f"name ct '{search_term}'")
            else:
                conditions.append(f"name eq '{name}'")

        # Add any additional filter kwargs
        if filter_kwargs:
            conditions.append(build_filter(**filter_kwargs))

        # Combine conditions
        combined_filter = " and ".join(conditions) if conditions else None

        # Use default fields if not specified
        if fields is None:
            fields = _DEFAULT_LIST_FIELDS

        params: dict[str, Any] = {}
        if combined_filter:
            params["filter"] = combined_filter
        if fields:
            params["fields"] = ",".join(fields)
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset

        response = self._client._request("GET", self._endpoint, params=params)

        if response is None:
            return []

        if not isinstance(response, list):
            return [self._to_model(response)]

        return [self._to_model(item) for item in response]

    def list_running(
        self,
        fields: builtins.list[str] | None = None,
        limit: int | None = None,
    ) -> builtins.list[Task]:
        """List running tasks.

        Args:
            fields: List of fields to return.
            limit: Maximum number of results.

        Returns:
            List of running Task objects.
        """
        return self.list(running=True, fields=fields, limit=limit)

    def list_idle(
        self,
        fields: builtins.list[str] | None = None,
        limit: int | None = None,
    ) -> builtins.list[Task]:
        """List idle tasks.

        Args:
            fields: List of fields to return.
            limit: Maximum number of results.

        Returns:
            List of idle Task objects.
        """
        return self.list(running=False, fields=fields, limit=limit)

    def list_enabled(
        self,
        fields: builtins.list[str] | None = None,
        limit: int | None = None,
    ) -> builtins.list[Task]:
        """List enabled tasks.

        Args:
            fields: List of fields to return.
            limit: Maximum number of results.

        Returns:
            List of enabled Task objects.
        """
        return self.list(enabled=True, fields=fields, limit=limit)

    def list_disabled(
        self,
        fields: builtins.list[str] | None = None,
        limit: int | None = None,
    ) -> builtins.list[Task]:
        """List disabled tasks.

        Args:
            fields: List of fields to return.
            limit: Maximum number of results.

        Returns:
            List of disabled Task objects.
        """
        return self.list(enabled=False, fields=fields, limit=limit)

    def get(
        self,
        key: int | None = None,
        *,
        name: str | None = None,
        fields: builtins.list[str] | None = None,
    ) -> Task:
        """Get a task by key or name.

        Args:
            key: Task $key (ID).
            name: Task name.
            fields: List of fields to return.

        Returns:
            Task object.

        Raises:
            NotFoundError: If task not found.
            ValueError: If neither key nor name provided.
        """
        if key is not None:
            params: dict[str, Any] = {}
            if fields is None:
                fields = _DEFAULT_LIST_FIELDS
            if fields:
                params["fields"] = ",".join(fields)

            response = self._client._request("GET", f"{self._endpoint}/{key}", params=params)
            if response is None:
                raise NotFoundError(f"Task {key} not found")
            if not isinstance(response, dict):
                raise NotFoundError(f"Task {key} returned invalid response")
            return self._to_model(response)

        if name is not None:
            escaped_name = name.replace("'", "''")
            results = self.list(filter=f"name eq '{escaped_name}'", fields=fields, limit=1)
            if not results:
                raise NotFoundError(f"Task with name '{name}' not found")
            return results[0]

        raise ValueError("Either key or name must be provided")

    def wait(
        self,
        key: int,
        timeout: int = 300,
        poll_interval: int = 2,
        raise_on_error: bool = True,
    ) -> Task:
        """Wait for a task to complete.

        Polls the task status until it becomes idle or an error occurs.

        Args:
            key: Task $key.
            timeout: Maximum wait time in seconds (0 = infinite).
            poll_interval: Seconds between status checks.
            raise_on_error: Raise TaskError if task fails.

        Returns:
            Completed Task object.

        Raises:
            TaskTimeoutError: If timeout exceeded.
            TaskError: If task fails and raise_on_error=True.

        Example:
            >>> # Wait for task with 5 minute timeout
            >>> task = client.tasks.wait(task_key, timeout=300)

            >>> # Wait indefinitely
            >>> task = client.tasks.wait(task_key, timeout=0)

            >>> # Don't raise on error, handle manually
            >>> task = client.tasks.wait(task_key, raise_on_error=False)
            >>> if task.has_error:
            ...     print(f"Task failed: {task.get('error')}")
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

    def enable(self, key: int) -> Task:
        """Enable a task.

        Enables a previously disabled task so it can run according to its
        schedule or event triggers.

        Args:
            key: Task $key.

        Returns:
            Updated Task object.

        Example:
            >>> task = client.tasks.enable(task_key)
            >>> print(task.is_enabled)  # True
        """
        self._client._request("PUT", f"{self._endpoint}/{key}", json_data={"enabled": True})
        return self.get(key)

    def disable(self, key: int) -> Task:
        """Disable a task.

        Disables a task to prevent it from running. If the task is currently
        running, it will complete but won't run again until re-enabled.

        Args:
            key: Task $key.

        Returns:
            Updated Task object.

        Example:
            >>> task = client.tasks.disable(task_key)
            >>> print(task.is_enabled)  # False
        """
        self._client._request("PUT", f"{self._endpoint}/{key}", json_data={"enabled": False})
        return self.get(key)

    def execute(self, key: int, **params: Any) -> Task:
        """Execute a task immediately.

        Triggers a task to run now, regardless of its schedule.

        Args:
            key: Task $key.
            **params: Optional parameters to pass to the task.

        Returns:
            Updated Task object.

        Example:
            >>> # Run a backup task immediately
            >>> task = client.tasks.execute(backup_task_key)
            >>> task.wait()  # Wait for completion
        """
        self.action(key, "execute", params=params if params else {})
        return self.get(key)

    def cancel(self, key: int) -> Task:
        """Cancel a running task.

        Attempts to cancel a task that is currently running.

        Args:
            key: Task $key.

        Returns:
            Updated Task object.

        Note:
            Not all tasks support cancellation. Some tasks may complete
            their current operation before stopping.
        """
        self.action(key, "cancel")
        return self.get(key)
