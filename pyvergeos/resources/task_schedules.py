"""Task schedule resource manager for VergeOS scheduling system.

Task schedules specify when and how often tasks should run (e.g., daily,
weekly, monthly). Schedules are reusable - you can create a schedule once
and apply it to multiple tasks for consistent configuration management.

Supported repeat intervals:
    - minute: Run every N minutes
    - hour: Run every N hours
    - day: Run every N days
    - week: Run every N weeks (with day-of-week options)
    - month: Run every N months (with day-of-month options)
    - year: Run every N years
    - never: Does not repeat (run once)

Schedule-Based Task Examples:
    - Check for and download system updates every Saturday at 5:00 PM
    - Power off a tenant on a specific date
    - Disable a user account 30 days after creation

Example:
    >>> # Create a schedule that runs every hour
    >>> schedule = client.task_schedules.create(
    ...     name="Hourly Backup",
    ...     repeat_every="hour",
    ...     repeat_iteration=1,
    ... )

    >>> # Create a schedule for Fridays at 6:00 PM (64800 seconds from midnight)
    >>> schedule = client.task_schedules.create(
    ...     name="Friday EOB",
    ...     repeat_every="week",
    ...     start_time_of_day=64800,  # 18:00 (6 PM)
    ...     monday=False,
    ...     tuesday=False,
    ...     wednesday=False,
    ...     thursday=False,
    ...     friday=True,
    ...     saturday=False,
    ...     sunday=False,
    ... )

    >>> # Create a weekday-only schedule
    >>> schedule = client.task_schedules.create(
    ...     name="Weekday Reports",
    ...     repeat_every="day",
    ...     saturday=False,
    ...     sunday=False,
    ... )
"""

from __future__ import annotations

import builtins
from typing import TYPE_CHECKING, Any

from pyvergeos.exceptions import NotFoundError
from pyvergeos.filters import build_filter
from pyvergeos.resources.base import ResourceManager, ResourceObject

if TYPE_CHECKING:
    from pyvergeos.client import VergeClient


# Repeat interval options
REPEAT_INTERVALS = {
    "minute": "Minute(s)",
    "hour": "Hour(s)",
    "day": "Day(s)",
    "week": "Week(s)",
    "month": "Month(s)",
    "year": "Year(s)",
    "never": "Does Not Repeat",
}

# Day of month options
DAY_OF_MONTH_OPTIONS = {
    "first": "First",
    "last": "Last",
    "15th": "15th",
    "start_date": "Start Date",
}


class TaskSchedule(ResourceObject):
    """Task schedule resource object.

    Represents a schedule definition for task automation.

    Properties:
        name: Schedule name.
        description: Schedule description.
        is_enabled: Whether the schedule is enabled.
        repeat_every: Repeat interval (minute, hour, day, week, month, year, never).
        repeat_iteration: Number of intervals between executions.
        start_date: Start date in YYYY-MM-DD format.
        end_date: Expiration date in YYYY-MM-DD HH:MM:SS format.
        start_time_of_day: Start time in seconds from midnight.
        end_time_of_day: End time in seconds from midnight.
        day_of_month: Day of month setting for monthly schedules.
        monday-sunday: Boolean flags for weekly schedules.
        task_key: Bound task key (if schedule is task-specific).
        is_system_created: Whether created by system.
        creator_key: Key of the user who created the schedule.
    """

    @property
    def is_enabled(self) -> bool:
        """Check if the schedule is enabled."""
        return bool(self.get("enabled", True))

    @property
    def repeat_every_display(self) -> str:
        """Get human-readable repeat interval."""
        repeat = self.get("repeat_every", "hour")
        return str(REPEAT_INTERVALS.get(repeat, repeat))

    @property
    def repeat_count(self) -> int:
        """Get the repeat iteration count."""
        return int(self.get("repeat_iteration", 1))

    @property
    def task_key(self) -> int | None:
        """Get the bound task key if any."""
        task = self.get("task")
        return int(task) if task is not None else None

    @property
    def is_system_created(self) -> bool:
        """Check if created by system."""
        return bool(self.get("system_created", False))

    @property
    def creator_key(self) -> int | None:
        """Get creator user key."""
        creator = self.get("creator")
        return int(creator) if creator is not None else None

    @property
    def runs_on_monday(self) -> bool:
        """Check if schedule runs on Monday."""
        return bool(self.get("monday", True))

    @property
    def runs_on_tuesday(self) -> bool:
        """Check if schedule runs on Tuesday."""
        return bool(self.get("tuesday", True))

    @property
    def runs_on_wednesday(self) -> bool:
        """Check if schedule runs on Wednesday."""
        return bool(self.get("wednesday", True))

    @property
    def runs_on_thursday(self) -> bool:
        """Check if schedule runs on Thursday."""
        return bool(self.get("thursday", True))

    @property
    def runs_on_friday(self) -> bool:
        """Check if schedule runs on Friday."""
        return bool(self.get("friday", True))

    @property
    def runs_on_saturday(self) -> bool:
        """Check if schedule runs on Saturday."""
        return bool(self.get("saturday", True))

    @property
    def runs_on_sunday(self) -> bool:
        """Check if schedule runs on Sunday."""
        return bool(self.get("sunday", True))

    @property
    def active_days(self) -> builtins.list[str]:
        """Get list of days when schedule is active."""
        days = []
        if self.runs_on_monday:
            days.append("Monday")
        if self.runs_on_tuesday:
            days.append("Tuesday")
        if self.runs_on_wednesday:
            days.append("Wednesday")
        if self.runs_on_thursday:
            days.append("Thursday")
        if self.runs_on_friday:
            days.append("Friday")
        if self.runs_on_saturday:
            days.append("Saturday")
        if self.runs_on_sunday:
            days.append("Sunday")
        return days

    @property
    def triggers(self) -> TaskScheduleTriggerManager:
        """Get trigger manager scoped to this schedule.

        Returns:
            TaskScheduleTriggerManager for this schedule.
        """
        from typing import cast

        from pyvergeos.resources.task_schedule_triggers import TaskScheduleTriggerManager

        manager = cast("TaskScheduleManager", self._manager)
        return TaskScheduleTriggerManager(manager._client, schedule_key=self.key)

    def enable(self) -> TaskSchedule:
        """Enable this schedule.

        Returns:
            Updated TaskSchedule object.
        """
        from typing import cast

        manager = cast("TaskScheduleManager", self._manager)
        return manager.update(self.key, enabled=True)

    def disable(self) -> TaskSchedule:
        """Disable this schedule.

        Returns:
            Updated TaskSchedule object.
        """
        from typing import cast

        manager = cast("TaskScheduleManager", self._manager)
        return manager.update(self.key, enabled=False)

    def get_schedule(
        self,
        max_results: int = 100,
        start_time: int | None = None,
        end_time: int | None = None,
    ) -> builtins.list[dict[str, Any]]:
        """Get upcoming scheduled execution times.

        Args:
            max_results: Maximum number of results (1-1440).
            start_time: Start timestamp for range.
            end_time: End timestamp for range.

        Returns:
            List of scheduled execution time dicts.
        """
        from typing import cast

        manager = cast("TaskScheduleManager", self._manager)
        return manager.get_schedule(
            self.key,
            max_results=max_results,
            start_time=start_time,
            end_time=end_time,
        )


class TaskScheduleManager(ResourceManager[TaskSchedule]):
    """Manager for task schedule operations.

    Task schedules define when and how often tasks should run.

    Example:
        >>> # List all schedules
        >>> for schedule in client.task_schedules.list():
        ...     print(f"{schedule.name}: {schedule.repeat_every_display}")

        >>> # Create a daily schedule
        >>> schedule = client.task_schedules.create(
        ...     name="Daily Backup",
        ...     repeat_every="day",
        ...     start_time_of_day=7200,  # 2 AM
        ... )

        >>> # Enable/disable
        >>> schedule.disable()
        >>> schedule.enable()

        >>> # Get upcoming execution times
        >>> times = schedule.get_schedule(max_results=10)
    """

    _endpoint = "task_schedules"

    _default_fields = [
        "$key",
        "name",
        "description",
        "enabled",
        "task",
        "task#$display as task_display",
        "repeat_every",
        "repeat_iteration",
        "start_date",
        "start_date_epoch",
        "end_date",
        "start_time_of_day",
        "end_time_of_day",
        "all_day",
        "day_of_month",
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
        "saturday",
        "sunday",
        "system_created",
        "creator",
        "creator#$display as creator_display",
    ]

    def __init__(self, client: VergeClient) -> None:
        super().__init__(client)

    def _to_model(self, data: dict[str, Any]) -> TaskSchedule:
        return TaskSchedule(data, self)

    def list(
        self,
        filter: str | None = None,
        fields: builtins.list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        *,
        enabled: bool | None = None,
        repeat_every: str | None = None,
        name: str | None = None,
        **filter_kwargs: Any,
    ) -> builtins.list[TaskSchedule]:
        """List task schedules with optional filtering.

        Args:
            filter: OData filter string.
            fields: List of fields to return.
            limit: Maximum number of results.
            offset: Skip this many results.
            enabled: Filter by enabled state.
            repeat_every: Filter by repeat interval.
            name: Filter by name.
            **filter_kwargs: Additional filter arguments.

        Returns:
            List of TaskSchedule objects.

        Example:
            >>> # All schedules
            >>> schedules = client.task_schedules.list()

            >>> # Enabled daily schedules
            >>> daily = client.task_schedules.list(enabled=True, repeat_every="day")

            >>> # Schedules by name pattern
            >>> backups = client.task_schedules.list(name="Backup*")
        """
        params: dict[str, Any] = {}

        # Build filter conditions
        filters: builtins.list[str] = []

        if filter:
            filters.append(f"({filter})")

        if enabled is not None:
            filters.append(f"enabled eq {str(enabled).lower()}")

        if repeat_every is not None:
            filters.append(f"repeat_every eq '{repeat_every}'")

        if name is not None:
            if "*" in name or "?" in name:
                search_term = name.replace("*", "").replace("?", "")
                if search_term:
                    filters.append(f"name ct '{search_term}'")
            else:
                escaped_name = name.replace("'", "''")
                filters.append(f"name eq '{escaped_name}'")

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

    def get(
        self,
        key: int | None = None,
        *,
        name: str | None = None,
        fields: builtins.list[str] | None = None,
    ) -> TaskSchedule:
        """Get a task schedule by key or name.

        Args:
            key: Schedule $key (ID).
            name: Schedule name.
            fields: List of fields to return.

        Returns:
            TaskSchedule object.

        Raises:
            NotFoundError: If schedule not found.
            ValueError: If neither key nor name provided.
        """
        if key is not None:
            params: dict[str, Any] = {}
            if fields:
                params["fields"] = ",".join(fields)
            else:
                params["fields"] = ",".join(self._default_fields)

            response = self._client._request("GET", f"{self._endpoint}/{key}", params=params)
            if response is None:
                raise NotFoundError(f"Task schedule {key} not found")
            if not isinstance(response, dict):
                raise NotFoundError(f"Task schedule {key} returned invalid response")
            return self._to_model(response)

        if name is not None:
            escaped_name = name.replace("'", "''")
            results = self.list(filter=f"name eq '{escaped_name}'", fields=fields, limit=1)
            if not results:
                raise NotFoundError(f"Task schedule with name '{name}' not found")
            return results[0]

        raise ValueError("Either key or name must be provided")

    def create(  # type: ignore[override]
        self,
        name: str,
        *,
        description: str | None = None,
        enabled: bool = True,
        repeat_every: str = "hour",
        repeat_iteration: int = 1,
        start_date: str | None = None,
        end_date: str | None = None,
        start_time_of_day: int = 0,
        end_time_of_day: int = 86400,
        day_of_month: str = "start_date",
        monday: bool = True,
        tuesday: bool = True,
        wednesday: bool = True,
        thursday: bool = True,
        friday: bool = True,
        saturday: bool = True,
        sunday: bool = True,
        task: int | None = None,
    ) -> TaskSchedule:
        """Create a new task schedule.

        Args:
            name: Schedule name (required).
            description: Schedule description.
            enabled: Whether schedule is enabled (default True).
            repeat_every: Repeat interval (minute, hour, day, week, month, year, never).
            repeat_iteration: Number of intervals between executions (default 1).
            start_date: Start date in YYYY-MM-DD format.
            end_date: Expiration date in YYYY-MM-DD HH:MM:SS format.
            start_time_of_day: Start time in seconds from midnight (0-86400).
            end_time_of_day: End time in seconds from midnight (0-86400).
            day_of_month: Day of month for monthly schedules (first, last, 15th, start_date).
            monday-sunday: Boolean flags for weekly schedules.
            task: Bind to specific task key.

        Returns:
            Created TaskSchedule object.

        Example:
            >>> # Hourly schedule
            >>> schedule = client.task_schedules.create(
            ...     name="Hourly Check",
            ...     repeat_every="hour",
            ...     repeat_iteration=1,
            ... )

            >>> # Daily at 2 AM (7200 seconds from midnight)
            >>> schedule = client.task_schedules.create(
            ...     name="Nightly Backup",
            ...     repeat_every="day",
            ...     start_time_of_day=7200,
            ... )

            >>> # Weekly on weekdays only
            >>> schedule = client.task_schedules.create(
            ...     name="Weekday Report",
            ...     repeat_every="week",
            ...     saturday=False,
            ...     sunday=False,
            ... )
        """
        body: dict[str, Any] = {
            "name": name,
            "enabled": enabled,
            "repeat_every": repeat_every,
            "repeat_iteration": repeat_iteration,
            "start_time_of_day": start_time_of_day,
            "end_time_of_day": end_time_of_day,
            "day_of_month": day_of_month,
            "monday": monday,
            "tuesday": tuesday,
            "wednesday": wednesday,
            "thursday": thursday,
            "friday": friday,
            "saturday": saturday,
            "sunday": sunday,
        }

        if description is not None:
            body["description"] = description

        if start_date is not None:
            body["start_date"] = start_date

        if end_date is not None:
            body["end_date"] = end_date

        if task is not None:
            body["task"] = task

        response = self._client._request("POST", self._endpoint, json_data=body)

        if response is None:
            raise ValueError("No response from create operation")
        if not isinstance(response, dict):
            raise ValueError("Create operation returned invalid response")

        # Get the full object with all fields
        key = response.get("$key")
        if key is not None:
            return self.get(int(key))

        return self._to_model(response)

    def update(  # type: ignore[override]
        self,
        key: int,
        *,
        name: str | None = None,
        description: str | None = None,
        enabled: bool | None = None,
        repeat_every: str | None = None,
        repeat_iteration: int | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        start_time_of_day: int | None = None,
        end_time_of_day: int | None = None,
        day_of_month: str | None = None,
        monday: bool | None = None,
        tuesday: bool | None = None,
        wednesday: bool | None = None,
        thursday: bool | None = None,
        friday: bool | None = None,
        saturday: bool | None = None,
        sunday: bool | None = None,
    ) -> TaskSchedule:
        """Update an existing task schedule.

        Args:
            key: Schedule $key (ID).
            name: New name.
            description: New description.
            enabled: Enable/disable.
            repeat_every: New repeat interval.
            repeat_iteration: New iteration count.
            start_date: New start date.
            end_date: New expiration date.
            start_time_of_day: New start time.
            end_time_of_day: New end time.
            day_of_month: New day of month setting.
            monday-sunday: Day flags.

        Returns:
            Updated TaskSchedule object.
        """
        body: dict[str, Any] = {}

        if name is not None:
            body["name"] = name
        if description is not None:
            body["description"] = description
        if enabled is not None:
            body["enabled"] = enabled
        if repeat_every is not None:
            body["repeat_every"] = repeat_every
        if repeat_iteration is not None:
            body["repeat_iteration"] = repeat_iteration
        if start_date is not None:
            body["start_date"] = start_date
        if end_date is not None:
            body["end_date"] = end_date
        if start_time_of_day is not None:
            body["start_time_of_day"] = start_time_of_day
        if end_time_of_day is not None:
            body["end_time_of_day"] = end_time_of_day
        if day_of_month is not None:
            body["day_of_month"] = day_of_month
        if monday is not None:
            body["monday"] = monday
        if tuesday is not None:
            body["tuesday"] = tuesday
        if wednesday is not None:
            body["wednesday"] = wednesday
        if thursday is not None:
            body["thursday"] = thursday
        if friday is not None:
            body["friday"] = friday
        if saturday is not None:
            body["saturday"] = saturday
        if sunday is not None:
            body["sunday"] = sunday

        if not body:
            return self.get(key)

        self._client._request("PUT", f"{self._endpoint}/{key}", json_data=body)
        return self.get(key)

    def delete(self, key: int) -> None:
        """Delete a task schedule.

        Note:
            Schedules with active triggers cannot be deleted.

        Args:
            key: Schedule $key (ID).

        Raises:
            ConflictError: If schedule has active triggers.
        """
        self._client._request("DELETE", f"{self._endpoint}/{key}")

    def enable(self, key: int) -> TaskSchedule:
        """Enable a task schedule.

        Args:
            key: Schedule $key (ID).

        Returns:
            Updated TaskSchedule object.
        """
        return self.update(key, enabled=True)

    def disable(self, key: int) -> TaskSchedule:
        """Disable a task schedule.

        Args:
            key: Schedule $key (ID).

        Returns:
            Updated TaskSchedule object.
        """
        return self.update(key, enabled=False)

    def get_schedule(
        self,
        key: int,
        max_results: int = 100,
        start_time: int | None = None,
        end_time: int | None = None,
    ) -> builtins.list[dict[str, Any]]:
        """Get upcoming scheduled execution times for a schedule.

        Args:
            key: Schedule $key (ID).
            max_results: Maximum number of results (1-1440, default 100).
            start_time: Start timestamp for range.
            end_time: End timestamp for range.

        Returns:
            List of scheduled execution time dicts.

        Example:
            >>> # Get next 10 scheduled times
            >>> times = client.task_schedules.get_schedule(schedule.key, max_results=10)
            >>> for t in times:
            ...     print(t)
        """
        params: dict[str, Any] = {"max": min(max(max_results, 1), 1440)}

        if start_time is not None:
            params["start_time"] = start_time
        if end_time is not None:
            params["end_time"] = end_time

        response = self.action(key, "get_schedule", **params)

        if response is None:
            return []
        if isinstance(response, dict):
            # Response might contain a list of times
            times = response.get("times") or response.get("schedule") or []
            if isinstance(times, list):
                return times
            return [response]
        if isinstance(response, list):
            return response

        return []

    def list_enabled(
        self,
        fields: builtins.list[str] | None = None,
        limit: int | None = None,
    ) -> builtins.list[TaskSchedule]:
        """List enabled schedules.

        Args:
            fields: List of fields to return.
            limit: Maximum number of results.

        Returns:
            List of enabled TaskSchedule objects.
        """
        return self.list(enabled=True, fields=fields, limit=limit)

    def list_disabled(
        self,
        fields: builtins.list[str] | None = None,
        limit: int | None = None,
    ) -> builtins.list[TaskSchedule]:
        """List disabled schedules.

        Args:
            fields: List of fields to return.
            limit: Maximum number of results.

        Returns:
            List of disabled TaskSchedule objects.
        """
        return self.list(enabled=False, fields=fields, limit=limit)

    def triggers(self, key: int) -> TaskScheduleTriggerManager:
        """Get trigger manager scoped to a specific schedule.

        Args:
            key: Schedule $key (ID).

        Returns:
            TaskScheduleTriggerManager for the schedule.
        """
        from pyvergeos.resources.task_schedule_triggers import TaskScheduleTriggerManager

        return TaskScheduleTriggerManager(self._client, schedule_key=key)


# Import for type hints only to avoid circular import
if TYPE_CHECKING:
    from pyvergeos.resources.task_schedule_triggers import TaskScheduleTriggerManager
