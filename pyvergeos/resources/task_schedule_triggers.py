"""Task schedule trigger resource manager for VergeOS scheduling system.

Task schedule triggers link tasks to schedules. When a schedule's trigger time
arrives, all tasks linked via triggers are executed.

Example:
    >>> # Get a task and schedule
    >>> task = client.tasks.get(name="Backup Task")
    >>> schedule = client.task_schedules.get(name="Nightly")

    >>> # Create a trigger to link them
    >>> trigger = client.task_schedule_triggers.create(
    ...     task=task.key,
    ...     schedule=schedule.key,
    ... )

    >>> # List all triggers for a schedule
    >>> for trigger in schedule.triggers.list():
    ...     print(f"Task: {trigger.task_display}")
"""

from __future__ import annotations

import builtins
from typing import TYPE_CHECKING, Any

from pyvergeos.exceptions import NotFoundError
from pyvergeos.filters import build_filter
from pyvergeos.resources.base import ResourceManager, ResourceObject

if TYPE_CHECKING:
    from pyvergeos.client import VergeClient


class TaskScheduleTrigger(ResourceObject):
    """Task schedule trigger resource object.

    Represents a link between a task and a schedule.

    Properties:
        task_key: The linked task's $key.
        task_display: Display name of the linked task.
        schedule_key: The linked schedule's $key.
        schedule_display: Display name of the linked schedule.
        schedule_enabled: Whether the linked schedule is enabled.
        trigger: Timer value for the trigger.
    """

    @property
    def task_key(self) -> int | None:
        """Get the linked task key."""
        task = self.get("task")
        return int(task) if task is not None else None

    @property
    def task_display(self) -> str:
        """Get the linked task display name."""
        return str(self.get("task_display", ""))

    @property
    def schedule_key(self) -> int | None:
        """Get the linked schedule key."""
        schedule = self.get("schedule")
        return int(schedule) if schedule is not None else None

    @property
    def schedule_display(self) -> str:
        """Get the linked schedule display name."""
        return str(self.get("schedule_display", ""))

    @property
    def is_schedule_enabled(self) -> bool:
        """Check if the linked schedule is enabled."""
        return bool(self.get("sch_enabled", False))

    @property
    def schedule_repeat_every(self) -> str | None:
        """Get the schedule's repeat interval."""
        return self.get("sch_repeat_every")

    @property
    def schedule_start_time(self) -> int | None:
        """Get the schedule's start time of day in seconds."""
        start = self.get("sch_start_time_of_day")
        return int(start) if start is not None else None

    def trigger_now(self) -> dict[str, Any] | None:
        """Trigger the task immediately.

        Returns:
            Action response dict or None.
        """
        from typing import cast

        manager = cast("TaskScheduleTriggerManager", self._manager)
        return manager.trigger(self.key)


class TaskScheduleTriggerManager(ResourceManager[TaskScheduleTrigger]):
    """Manager for task schedule trigger operations.

    Task schedule triggers link tasks to schedules for execution.

    Example:
        >>> # List all triggers
        >>> for trigger in client.task_schedule_triggers.list():
        ...     print(f"{trigger.task_display} -> {trigger.schedule_display}")

        >>> # Create a trigger
        >>> trigger = client.task_schedule_triggers.create(
        ...     task=task_key,
        ...     schedule=schedule_key,
        ... )

        >>> # List triggers for a specific task
        >>> triggers = client.task_schedule_triggers.list(task=task_key)

        >>> # List triggers for a specific schedule
        >>> triggers = client.task_schedule_triggers.list(schedule=schedule_key)
    """

    _endpoint = "task_schedule_triggers"

    _default_fields = [
        "$key",
        "task",
        "display(task) as task_display",
        "schedule",
        "display(schedule) as schedule_display",
        "trigger",
        "flatten(schedule[$key as sch_$key,enabled as sch_enabled,"
        "start_time_of_day as sch_start_time_of_day,repeat_iteration as sch_repeat_iteration,"
        "end_date as sch_end_date,display(day_of_month) as sch_day_of_month,"
        "display(repeat_every) as sch_repeat_every])",
    ]

    def __init__(
        self,
        client: VergeClient,
        *,
        task_key: int | None = None,
        schedule_key: int | None = None,
    ) -> None:
        """Initialize the trigger manager.

        Args:
            client: VergeClient instance.
            task_key: Optional task key to scope the manager.
            schedule_key: Optional schedule key to scope the manager.
        """
        super().__init__(client)
        self._task_key = task_key
        self._schedule_key = schedule_key

    def _to_model(self, data: dict[str, Any]) -> TaskScheduleTrigger:
        return TaskScheduleTrigger(data, self)

    def list(
        self,
        filter: str | None = None,
        fields: builtins.list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        *,
        task: int | None = None,
        schedule: int | None = None,
        **filter_kwargs: Any,
    ) -> builtins.list[TaskScheduleTrigger]:
        """List task schedule triggers with optional filtering.

        Args:
            filter: OData filter string.
            fields: List of fields to return.
            limit: Maximum number of results.
            offset: Skip this many results.
            task: Filter by task key. Ignored if manager is scoped to a task.
            schedule: Filter by schedule key. Ignored if manager is scoped to a schedule.
            **filter_kwargs: Additional filter arguments.

        Returns:
            List of TaskScheduleTrigger objects.

        Example:
            >>> # All triggers
            >>> triggers = client.task_schedule_triggers.list()

            >>> # Triggers for a specific task
            >>> triggers = client.task_schedule_triggers.list(task=task_key)

            >>> # Triggers for a specific schedule
            >>> triggers = client.task_schedule_triggers.list(schedule=schedule_key)
        """
        params: dict[str, Any] = {}

        # Build filter conditions
        filters: builtins.list[str] = []

        if filter:
            filters.append(f"({filter})")

        # Use scoped key or parameter
        task_filter = self._task_key if self._task_key is not None else task
        if task_filter is not None:
            filters.append(f"task eq {task_filter}")

        schedule_filter = self._schedule_key if self._schedule_key is not None else schedule
        if schedule_filter is not None:
            filters.append(f"schedule eq {schedule_filter}")

        if filter_kwargs:
            filters.append(build_filter(**filter_kwargs))

        if filters:
            params["filter"] = " and ".join(filters)

        # Use default fields if not specified
        if fields:
            params["fields"] = ",".join(fields)
        else:
            params["fields"] = ",".join(self._default_fields)

        # Pagination
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

    def get(  # type: ignore[override]
        self,
        key: int | None = None,
        *,
        fields: builtins.list[str] | None = None,
    ) -> TaskScheduleTrigger:
        """Get a task schedule trigger by key.

        Args:
            key: Trigger $key (ID).
            fields: List of fields to return.

        Returns:
            TaskScheduleTrigger object.

        Raises:
            NotFoundError: If trigger not found.
            ValueError: If key not provided.
        """
        if key is None:
            raise ValueError("Key must be provided")

        params: dict[str, Any] = {}
        if fields:
            params["fields"] = ",".join(fields)
        else:
            params["fields"] = ",".join(self._default_fields)

        response = self._client._request("GET", f"{self._endpoint}/{key}", params=params)
        if response is None:
            raise NotFoundError(f"Task schedule trigger {key} not found")
        if not isinstance(response, dict):
            raise NotFoundError(f"Task schedule trigger {key} returned invalid response")
        return self._to_model(response)

    def create(  # type: ignore[override]
        self,
        task: int,
        schedule: int,
    ) -> TaskScheduleTrigger:
        """Create a task schedule trigger.

        Links a task to a schedule so it runs when the schedule fires.

        Args:
            task: Task $key to link.
            schedule: Schedule $key to link.

        Returns:
            Created TaskScheduleTrigger object.

        Example:
            >>> trigger = client.task_schedule_triggers.create(
            ...     task=backup_task.key,
            ...     schedule=nightly_schedule.key,
            ... )
        """
        body: dict[str, Any] = {
            "task": task,
            "schedule": schedule,
        }

        response = self._client._request("POST", self._endpoint, json_data=body)

        if response is None:
            raise ValueError("No response from create operation")
        if not isinstance(response, dict):
            raise ValueError("Create operation returned invalid response")

        # Get the full object
        key = response.get("$key")
        if key is not None:
            return self.get(int(key))

        return self._to_model(response)

    def delete(self, key: int) -> None:
        """Delete a task schedule trigger.

        Removes the link between a task and schedule.

        Args:
            key: Trigger $key (ID).
        """
        self._client._request("DELETE", f"{self._endpoint}/{key}")

    def trigger(self, key: int) -> dict[str, Any] | None:
        """Trigger execution immediately.

        Fires the trigger, causing the linked task to execute.

        Args:
            key: Trigger $key (ID).

        Returns:
            Action response dict or None.
        """
        return self.action(key, "trigger")

    def list_for_task(
        self,
        task_key: int,
        limit: int | None = None,
    ) -> builtins.list[TaskScheduleTrigger]:
        """List all triggers for a specific task.

        Args:
            task_key: Task $key.
            limit: Maximum number of results.

        Returns:
            List of TaskScheduleTrigger objects.
        """
        return self.list(task=task_key, limit=limit)

    def list_for_schedule(
        self,
        schedule_key: int,
        limit: int | None = None,
    ) -> builtins.list[TaskScheduleTrigger]:
        """List all triggers for a specific schedule.

        Args:
            schedule_key: Schedule $key.
            limit: Maximum number of results.

        Returns:
            List of TaskScheduleTrigger objects.
        """
        return self.list(schedule=schedule_key, limit=limit)
