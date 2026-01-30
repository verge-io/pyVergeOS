"""Task event resource manager for VergeOS event-driven automation.

Task events (event triggers) link tasks to system events, enabling event-driven
automation. When a specific event occurs on a resource, tasks linked via task
events are automatically executed.

Event triggers allow tasks to run in response to specific system occurrences.
A single task can be triggered by multiple distinct events, enabling you to
consolidate logic and reuse task definitions across scenarios.

Event-Based Task Examples:
    - Power on a VM when a designated user logs into VergeOS
    - Power off VMs when the user logs out
    - Send an email notification when a system update completes
    - Use a webhook to notify Slack when a sync error is detected

Event Configuration:
    - **Type**: The object class (e.g., users, virtual machines, tenants, alarms)
    - **Event**: The event type (e.g., login, logout, poweron, error)
    - **Object Instance**: A specific resource, or use tags to match multiple
    - **Filter Settings**: For logs/alarms, filter by severity or log type

Example:
    >>> # List all task events
    >>> for event in client.task_events.list():
    ...     print(f"{event.event_name_display} -> {event.task_display}")

    >>> # Get events linked to a specific task
    >>> task = client.tasks.get(name="Power On Dev VMs")
    >>> for event in task.events.list():
    ...     print(f"Triggered by: {event.event_name_display}")

    >>> # Create event trigger for user login
    >>> event = client.task_events.create(
    ...     task=task.key,
    ...     owner=user.key,
    ...     event="login",
    ...     table="users",
    ... )

    >>> # Manually trigger an event for testing
    >>> event.trigger_now(context={"custom": "data"})
"""

from __future__ import annotations

import builtins
from typing import TYPE_CHECKING, Any

from pyvergeos.exceptions import NotFoundError
from pyvergeos.filters import build_filter
from pyvergeos.resources.base import ResourceManager, ResourceObject

if TYPE_CHECKING:
    from pyvergeos.client import VergeClient


class TaskEvent(ResourceObject):
    """Task event resource object.

    Represents a link between a task and a system event.

    Properties:
        owner_key: The owner resource $key.
        owner_table: The owner resource table name.
        event: Event identifier.
        event_name: Human-readable event name.
        task_key: Linked task $key.
        task_display: Linked task display name.
        filters: Event filter conditions (JSON).
        context: Event context data (JSON).
        trigger: Timer value for the event trigger.
    """

    @property
    def owner_key(self) -> int | None:
        """Get the owner resource key.

        Note: Some events have non-integer owner values (e.g., 'update_settings/1').
        In those cases, this property returns None.
        """
        owner = self.get("owner")
        if owner is None or owner == "":
            return None
        # Owner can be an integer or a path like 'update_settings/1'
        try:
            return int(owner)
        except (ValueError, TypeError):
            return None

    @property
    def owner_table(self) -> str | None:
        """Get the owner resource table name."""
        return self.get("table")

    @property
    def event_type(self) -> str | None:
        """Get the event identifier."""
        return self.get("event")

    @property
    def event_name_display(self) -> str | None:
        """Get the human-readable event name."""
        return self.get("event_name")

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
    def event_filters(self) -> dict[str, Any] | None:
        """Get the event filter conditions."""
        filters = self.get("table_event_filters")
        if isinstance(filters, dict):
            return filters
        return None

    @property
    def event_context(self) -> dict[str, Any] | None:
        """Get the event context data."""
        context = self.get("context")
        if isinstance(context, dict):
            return context
        return None

    def trigger_now(self, context: dict[str, Any] | None = None) -> dict[str, Any] | None:
        """Manually trigger this event.

        Args:
            context: Optional context data to pass to the task.

        Returns:
            Action response dict or None.
        """
        from typing import cast

        manager = cast("TaskEventManager", self._manager)
        return manager.trigger(self.key, context=context)


class TaskEventManager(ResourceManager[TaskEvent]):
    """Manager for task event operations.

    Task events enable event-driven automation by linking tasks to system events.

    Example:
        >>> # List all task events
        >>> for event in client.task_events.list():
        ...     print(f"{event.event_name_display}: {event.task_display}")

        >>> # List events for a specific task
        >>> events = client.task_events.list(task=task_key)

        >>> # List events for a specific owner
        >>> events = client.task_events.list(owner=vm_key)

        >>> # Manually trigger an event
        >>> client.task_events.trigger(event_key, context={"key": "value"})
    """

    _endpoint = "task_events"

    _default_fields = [
        "$key",
        "owner",
        "owner#$display as owner_display",
        "table",
        "event",
        "event_name",
        "task",
        "task#$display as task_display",
        "task#name as task_name",
        "table_event_filters",
        "trigger",
        "context",
    ]

    def __init__(
        self,
        client: VergeClient,
        *,
        task_key: int | None = None,
        owner_key: int | None = None,
    ) -> None:
        """Initialize the event manager.

        Args:
            client: VergeClient instance.
            task_key: Optional task key to scope the manager.
            owner_key: Optional owner resource key to scope the manager.
        """
        super().__init__(client)
        self._task_key = task_key
        self._owner_key = owner_key

    def _to_model(self, data: dict[str, Any]) -> TaskEvent:
        return TaskEvent(data, self)

    def list(
        self,
        filter: str | None = None,
        fields: builtins.list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        *,
        task: int | None = None,
        owner: int | None = None,
        table: str | None = None,
        event: str | None = None,
        **filter_kwargs: Any,
    ) -> builtins.list[TaskEvent]:
        """List task events with optional filtering.

        Args:
            filter: OData filter string.
            fields: List of fields to return.
            limit: Maximum number of results.
            offset: Skip this many results.
            task: Filter by task key. Ignored if manager is scoped to a task.
            owner: Filter by owner resource key. Ignored if manager is scoped.
            table: Filter by owner table name.
            event: Filter by event identifier.
            **filter_kwargs: Additional filter arguments.

        Returns:
            List of TaskEvent objects.

        Example:
            >>> # All events
            >>> events = client.task_events.list()

            >>> # Events for a specific task
            >>> events = client.task_events.list(task=task_key)

            >>> # Events for VMs only
            >>> events = client.task_events.list(table="vms")

            >>> # Events for a specific event type
            >>> events = client.task_events.list(event="poweron")
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

        owner_filter = self._owner_key if self._owner_key is not None else owner
        if owner_filter is not None:
            filters.append(f"owner eq {owner_filter}")

        if table is not None:
            filters.append(f"table eq '{table}'")

        if event is not None:
            filters.append(f"event eq '{event}'")

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
    ) -> TaskEvent:
        """Get a task event by key.

        Args:
            key: Event $key (ID).
            fields: List of fields to return.

        Returns:
            TaskEvent object.

        Raises:
            NotFoundError: If event not found.
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
            raise NotFoundError(f"Task event {key} not found")
        if not isinstance(response, dict):
            raise NotFoundError(f"Task event {key} returned invalid response")
        return self._to_model(response)

    def create(  # type: ignore[override]
        self,
        task: int,
        owner: int,
        event: str,
        *,
        table: str | None = None,
        event_name: str | None = None,
        table_event_filters: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
    ) -> TaskEvent:
        """Create a task event.

        Links a task to a system event for event-driven execution.

        Args:
            task: Task $key to link.
            owner: Owner resource $key.
            event: Event identifier.
            table: Owner table name (usually auto-detected).
            event_name: Human-readable event name.
            table_event_filters: JSON filter conditions for the event.
            context: JSON context data to pass to the task.

        Returns:
            Created TaskEvent object.

        Example:
            >>> # Trigger task when a VM powers on
            >>> event = client.task_events.create(
            ...     task=notification_task.key,
            ...     owner=vm.key,
            ...     event="poweron",
            ... )
        """
        body: dict[str, Any] = {
            "task": task,
            "owner": owner,
            "event": event,
        }

        if table is not None:
            body["table"] = table
        if event_name is not None:
            body["event_name"] = event_name
        if table_event_filters is not None:
            body["table_event_filters"] = table_event_filters
        if context is not None:
            body["context"] = context

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

    def update(  # type: ignore[override]
        self,
        key: int,
        *,
        table_event_filters: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
    ) -> TaskEvent:
        """Update a task event.

        Args:
            key: Event $key (ID).
            table_event_filters: New filter conditions.
            context: New context data.

        Returns:
            Updated TaskEvent object.
        """
        body: dict[str, Any] = {}

        if table_event_filters is not None:
            body["table_event_filters"] = table_event_filters
        if context is not None:
            body["context"] = context

        if not body:
            return self.get(key)

        self._client._request("PUT", f"{self._endpoint}/{key}", json_data=body)
        return self.get(key)

    def delete(self, key: int) -> None:
        """Delete a task event.

        Removes the link between a task and event.

        Args:
            key: Event $key (ID).
        """
        self._client._request("DELETE", f"{self._endpoint}/{key}")

    def trigger(
        self,
        key: int,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        """Manually trigger a task event.

        Fires the event, causing the linked task to execute.

        Args:
            key: Event $key (ID).
            context: Optional context data to pass to the task.

        Returns:
            Action response dict or None.

        Example:
            >>> # Trigger an event
            >>> client.task_events.trigger(event_key)

            >>> # Trigger with context
            >>> client.task_events.trigger(event_key, context={"key": "value"})
        """
        params: dict[str, Any] = {}
        if context is not None:
            params["context"] = context

        return self.action(key, "trigger", **params)

    def list_for_task(
        self,
        task_key: int,
        limit: int | None = None,
    ) -> builtins.list[TaskEvent]:
        """List all events for a specific task.

        Args:
            task_key: Task $key.
            limit: Maximum number of results.

        Returns:
            List of TaskEvent objects.
        """
        return self.list(task=task_key, limit=limit)

    def list_for_owner(
        self,
        owner_key: int,
        limit: int | None = None,
    ) -> builtins.list[TaskEvent]:
        """List all events for a specific owner resource.

        Args:
            owner_key: Owner resource $key.
            limit: Maximum number of results.

        Returns:
            List of TaskEvent objects.
        """
        return self.list(owner=owner_key, limit=limit)

    def list_by_table(
        self,
        table: str,
        limit: int | None = None,
    ) -> builtins.list[TaskEvent]:
        """List all events for a specific table/resource type.

        Args:
            table: Table name (e.g., "vms", "vnets", "tenants").
            limit: Maximum number of results.

        Returns:
            List of TaskEvent objects.
        """
        return self.list(table=table, limit=limit)
