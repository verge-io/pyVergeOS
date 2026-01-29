"""Alarm resource manager for VergeOS system monitoring."""

from __future__ import annotations

import builtins
import time
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from pyvergeos.exceptions import NotFoundError
from pyvergeos.filters import build_filter
from pyvergeos.resources.base import ResourceManager, ResourceObject

if TYPE_CHECKING:
    from pyvergeos.client import VergeClient


# Alarm severity levels
ALARM_LEVELS = ["critical", "error", "warning", "message", "audit", "summary", "debug"]

# Owner type mappings (friendly name -> API value)
OWNER_TYPE_MAP = {
    "VM": "vms",
    "Network": "vnets",
    "Node": "nodes",
    "Tenant": "tenant_nodes",
    "User": "users",
    "System": "system",
    "CloudSnapshot": "cloud_snapshots",
}

# Reverse mapping (API value -> friendly name)
OWNER_TYPE_DISPLAY = {v: k for k, v in OWNER_TYPE_MAP.items()}


# Default fields for alarm list operations
_DEFAULT_ALARM_FIELDS = [
    "$key",
    "owner",
    "owner#name as owner_name",
    "owner_type",
    "sub_owner",
    "alarm_type",
    "alarm_type#name as alarm_type_name",
    "alarm_type#description as alarm_type_description",
    "level",
    "status",
    "alarm_id",
    "resolvable",
    "resolve_text",
    "created",
    "modified",
    "snooze",
    "snoozed_by",
]

# Default fields for alarm history list operations
_DEFAULT_HISTORY_FIELDS = [
    "$key",
    "alarm_raised",
    "alarm_lowered",
    "archived_by",
    "owner",
    "alarm_type",
    "level",
    "status",
    "alarm_id",
]


class Alarm(ResourceObject):
    """Alarm resource object.

    Represents an active alarm in VergeOS indicating a condition requiring
    attention such as errors, warnings, or critical issues.

    Properties:
        level: Alarm severity (critical, error, warning, message, audit).
        level_display: Capitalized display name for level.
        status: Alarm status message.
        alarm_type: Alarm type name.
        alarm_type_key: Alarm type $key.
        description: Alarm type description.
        alarm_id: Unique alarm identifier (8-char string).
        owner_name: Name of the owner object.
        owner_key: Key of the owner object.
        owner_type: API owner type value (vms, vnets, etc.).
        owner_type_display: Friendly owner type name (VM, Network, etc.).
        sub_owner: Sub-owner key if applicable.
        is_resolvable: True if alarm can be resolved.
        resolve_text: Text describing how to resolve.
        is_snoozed: True if alarm is currently snoozed.
        snoozed_by: User who snoozed the alarm.
        snooze_until: Datetime when snooze expires.
        created_at: Datetime when alarm was raised.
        modified_at: Datetime when alarm was last modified.
    """

    @property
    def level(self) -> str:
        """Get alarm severity level."""
        return str(self.get("level", ""))

    @property
    def level_display(self) -> str:
        """Get capitalized level display name."""
        level = self.level
        return level.capitalize() if level else ""

    @property
    def status(self) -> str:
        """Get alarm status message."""
        return str(self.get("status", ""))

    @property
    def alarm_type(self) -> str:
        """Get alarm type name."""
        return str(self.get("alarm_type_name", ""))

    @property
    def alarm_type_key(self) -> int | None:
        """Get alarm type $key."""
        val = self.get("alarm_type")
        return int(val) if val is not None else None

    @property
    def description(self) -> str:
        """Get alarm type description."""
        return str(self.get("alarm_type_description", ""))

    @property
    def alarm_id(self) -> str:
        """Get unique alarm identifier (8-char string)."""
        return str(self.get("alarm_id", ""))

    @property
    def owner_name(self) -> str:
        """Get owner object name."""
        return str(self.get("owner_name", ""))

    @property
    def owner_key(self) -> int | None:
        """Get owner object key."""
        val = self.get("owner")
        return int(val) if val is not None else None

    @property
    def owner_type(self) -> str:
        """Get API owner type value."""
        return str(self.get("owner_type", ""))

    @property
    def owner_type_display(self) -> str:
        """Get friendly owner type name."""
        return OWNER_TYPE_DISPLAY.get(self.owner_type, self.owner_type)

    @property
    def sub_owner(self) -> int | None:
        """Get sub-owner key if applicable."""
        val = self.get("sub_owner")
        return int(val) if val is not None else None

    @property
    def is_resolvable(self) -> bool:
        """Check if alarm can be resolved."""
        return bool(self.get("resolvable", False))

    @property
    def resolve_text(self) -> str:
        """Get text describing how to resolve."""
        return str(self.get("resolve_text", ""))

    @property
    def is_snoozed(self) -> bool:
        """Check if alarm is currently snoozed."""
        snooze_ts = self.get("snooze", 0)
        if not snooze_ts or snooze_ts == 0:
            return False
        now_ts = int(datetime.now(timezone.utc).timestamp())
        return int(snooze_ts) > now_ts

    @property
    def snoozed_by(self) -> str:
        """Get user who snoozed the alarm."""
        return str(self.get("snoozed_by", ""))

    @property
    def snooze_until(self) -> datetime | None:
        """Get datetime when snooze expires."""
        snooze_ts = self.get("snooze", 0)
        if not snooze_ts or snooze_ts == 0:
            return None
        return datetime.fromtimestamp(int(snooze_ts), tz=timezone.utc)

    @property
    def created_at(self) -> datetime | None:
        """Get datetime when alarm was raised."""
        ts = self.get("created")
        if ts is None:
            return None
        return datetime.fromtimestamp(int(ts), tz=timezone.utc)

    @property
    def modified_at(self) -> datetime | None:
        """Get datetime when alarm was last modified."""
        ts = self.get("modified")
        if ts is None:
            return None
        return datetime.fromtimestamp(int(ts), tz=timezone.utc)

    def snooze(self, hours: int = 24) -> Alarm:
        """Snooze this alarm for a specified duration.

        Args:
            hours: Number of hours to snooze (default: 24, max: 8760).

        Returns:
            Updated Alarm object.
        """
        from typing import cast

        manager = cast("AlarmManager", self._manager)
        return manager.snooze(self.key, hours=hours)

    def snooze_to(self, until: datetime) -> Alarm:
        """Snooze this alarm until a specific time.

        Args:
            until: Datetime when snooze should expire.

        Returns:
            Updated Alarm object.
        """
        from typing import cast

        manager = cast("AlarmManager", self._manager)
        return manager.snooze_to(self.key, until=until)

    def unsnooze(self) -> Alarm:
        """Remove snooze from this alarm, making it active again.

        Returns:
            Updated Alarm object.
        """
        from typing import cast

        manager = cast("AlarmManager", self._manager)
        return manager.unsnooze(self.key)

    def resolve(self) -> None:
        """Resolve this alarm.

        Raises:
            ValueError: If alarm is not resolvable.
            APIError: If resolve action fails.
        """
        from typing import cast

        manager = cast("AlarmManager", self._manager)
        manager.resolve(self.key)

    def __repr__(self) -> str:
        key = self.get("$key", "?")
        level = self.level_display
        status = self.status[:30] + "..." if len(self.status) > 30 else self.status
        return f"<Alarm key={key} level={level!r} status={status!r}>"


class AlarmHistory(ResourceObject):
    """Alarm history resource object.

    Represents a resolved/lowered alarm in the history.

    Properties:
        level: Alarm severity when raised.
        level_display: Capitalized display name for level.
        status: Alarm status message.
        alarm_type: Alarm type name.
        alarm_id: Unique alarm identifier.
        owner: Owner object description (string in history).
        archived_by: How the alarm was archived (auto, user, etc.).
        raised_at: Datetime when alarm was raised.
        lowered_at: Datetime when alarm was lowered/resolved.
    """

    @property
    def level(self) -> str:
        """Get alarm severity level."""
        return str(self.get("level", ""))

    @property
    def level_display(self) -> str:
        """Get capitalized level display name."""
        level = self.level
        return level.capitalize() if level else ""

    @property
    def status(self) -> str:
        """Get alarm status message."""
        return str(self.get("status", ""))

    @property
    def alarm_type(self) -> str:
        """Get alarm type name."""
        return str(self.get("alarm_type", ""))

    @property
    def alarm_id(self) -> str:
        """Get unique alarm identifier."""
        return str(self.get("alarm_id", ""))

    @property
    def owner(self) -> str:
        """Get owner description."""
        return str(self.get("owner", ""))

    @property
    def archived_by(self) -> str:
        """Get how alarm was archived."""
        return str(self.get("archived_by", ""))

    @property
    def raised_at(self) -> datetime | None:
        """Get datetime when alarm was raised."""
        ts = self.get("alarm_raised")
        if ts is None:
            return None
        return datetime.fromtimestamp(int(ts), tz=timezone.utc)

    @property
    def lowered_at(self) -> datetime | None:
        """Get datetime when alarm was lowered/resolved."""
        ts = self.get("alarm_lowered")
        if ts is None:
            return None
        return datetime.fromtimestamp(int(ts), tz=timezone.utc)

    def __repr__(self) -> str:
        key = self.get("$key", "?")
        level = self.level_display
        status = self.status[:30] + "..." if len(self.status) > 30 else self.status
        return f"<AlarmHistory key={key} level={level!r} status={status!r}>"


class AlarmManager(ResourceManager[Alarm]):
    """Manager for Alarm operations.

    Alarms indicate conditions requiring attention such as errors, warnings,
    or critical issues with VMs, networks, nodes, or the system.

    Example:
        >>> # List all active alarms
        >>> alarms = client.alarms.list()
        >>> for alarm in alarms:
        ...     print(f"{alarm.level_display}: {alarm.status}")

        >>> # List critical and error alarms
        >>> critical = client.alarms.list(level=["critical", "error"])

        >>> # List alarms by owner type
        >>> vm_alarms = client.alarms.list(owner_type="VM")

        >>> # Snooze an alarm
        >>> client.alarms.snooze(alarm_key, hours=24)

        >>> # Resolve a resolvable alarm
        >>> client.alarms.resolve(alarm_key)

        >>> # Get alarm history
        >>> history = client.alarms.list_history()
    """

    _endpoint = "alarms"

    def __init__(self, client: VergeClient) -> None:
        super().__init__(client)

    def _to_model(self, data: dict[str, Any]) -> Alarm:
        return Alarm(data, self)

    def _to_history_model(self, data: dict[str, Any]) -> AlarmHistory:
        return AlarmHistory(data, self)

    def list(
        self,
        filter: str | None = None,
        fields: builtins.list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        *,
        level: str | builtins.list[str] | None = None,
        owner_type: str | None = None,
        include_snoozed: bool = False,
        **filter_kwargs: Any,
    ) -> builtins.list[Alarm]:
        """List alarms with optional filtering.

        By default, only returns active (non-snoozed) alarms.

        Args:
            filter: OData filter string.
            fields: List of fields to return.
            limit: Maximum number of results.
            offset: Skip this many results.
            level: Filter by severity level (or list of levels).
                   Values: critical, error, warning, message, audit, summary, debug.
            owner_type: Filter by owner type.
                        Values: VM, Network, Node, Tenant, User, System, CloudSnapshot.
            include_snoozed: If True, include snoozed alarms (default: False).
            **filter_kwargs: Additional filter arguments.

        Returns:
            List of Alarm objects sorted by created date (newest first).

        Example:
            >>> # All active alarms
            >>> alarms = client.alarms.list()

            >>> # Critical alarms only
            >>> critical = client.alarms.list(level="critical")

            >>> # Critical and error alarms
            >>> severe = client.alarms.list(level=["critical", "error"])

            >>> # VM alarms
            >>> vm_alarms = client.alarms.list(owner_type="VM")

            >>> # Include snoozed alarms
            >>> all_alarms = client.alarms.list(include_snoozed=True)
        """
        conditions: builtins.list[str] = []

        if filter:
            conditions.append(f"({filter})")

        # Level filter
        if level:
            if isinstance(level, str):
                conditions.append(f"level eq '{level.lower()}'")
            else:
                level_filters = [f"level eq '{lv.lower()}'" for lv in level]
                if len(level_filters) == 1:
                    conditions.append(level_filters[0])
                else:
                    conditions.append(f"({' or '.join(level_filters)})")

        # Owner type filter
        if owner_type:
            api_owner_type = OWNER_TYPE_MAP.get(owner_type, owner_type)
            conditions.append(f"owner_type eq '{api_owner_type}'")

        # Active (non-snoozed) filter - default behavior
        if not include_snoozed:
            # Show alarms where snooze is 0 or snooze time has passed
            conditions.append("(snooze eq 0 or snooze le {$now})")

        # Add any additional filter kwargs
        if filter_kwargs:
            conditions.append(build_filter(**filter_kwargs))

        # Combine conditions
        combined_filter = " and ".join(conditions) if conditions else None

        # Use default fields if not specified
        if fields is None:
            fields = _DEFAULT_ALARM_FIELDS

        params: dict[str, Any] = {}
        if combined_filter:
            params["filter"] = combined_filter
        if fields:
            params["fields"] = ",".join(fields)
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset

        # Sort by created date descending (newest first)
        params["sort"] = "-created"

        response = self._client._request("GET", self._endpoint, params=params)

        if response is None:
            return []

        if not isinstance(response, list):
            return [self._to_model(response)]

        return [self._to_model(item) for item in response]

    def list_critical(
        self,
        include_snoozed: bool = False,
        limit: int | None = None,
    ) -> builtins.list[Alarm]:
        """List critical alarms.

        Args:
            include_snoozed: If True, include snoozed alarms.
            limit: Maximum number of results.

        Returns:
            List of critical Alarm objects.
        """
        return self.list(level="critical", include_snoozed=include_snoozed, limit=limit)

    def list_errors(
        self,
        include_snoozed: bool = False,
        limit: int | None = None,
    ) -> builtins.list[Alarm]:
        """List error alarms.

        Args:
            include_snoozed: If True, include snoozed alarms.
            limit: Maximum number of results.

        Returns:
            List of error Alarm objects.
        """
        return self.list(level="error", include_snoozed=include_snoozed, limit=limit)

    def list_warnings(
        self,
        include_snoozed: bool = False,
        limit: int | None = None,
    ) -> builtins.list[Alarm]:
        """List warning alarms.

        Args:
            include_snoozed: If True, include snoozed alarms.
            limit: Maximum number of results.

        Returns:
            List of warning Alarm objects.
        """
        return self.list(level="warning", include_snoozed=include_snoozed, limit=limit)

    def list_by_owner_type(
        self,
        owner_type: str,
        include_snoozed: bool = False,
        limit: int | None = None,
    ) -> builtins.list[Alarm]:
        """List alarms by owner type.

        Args:
            owner_type: Owner type (VM, Network, Node, Tenant, User, System, CloudSnapshot).
            include_snoozed: If True, include snoozed alarms.
            limit: Maximum number of results.

        Returns:
            List of Alarm objects for the specified owner type.
        """
        return self.list(owner_type=owner_type, include_snoozed=include_snoozed, limit=limit)

    def get(
        self,
        key: int | None = None,
        *,
        name: str | None = None,
        fields: builtins.list[str] | None = None,
    ) -> Alarm:
        """Get an alarm by key.

        Note: Alarms do not have a name field, so name parameter is not supported.

        Args:
            key: Alarm $key (ID).
            name: Not supported for alarms (will raise ValueError).
            fields: List of fields to return.

        Returns:
            Alarm object.

        Raises:
            NotFoundError: If alarm not found.
            ValueError: If key not provided or if name is used.
        """
        if name is not None:
            raise ValueError("Alarms do not have a name field. Use key instead.")
        if key is None:
            raise ValueError("key must be provided")

        params: dict[str, Any] = {}
        if fields is None:
            fields = _DEFAULT_ALARM_FIELDS
        if fields:
            params["fields"] = ",".join(fields)

        response = self._client._request("GET", f"{self._endpoint}/{key}", params=params)
        if response is None:
            raise NotFoundError(f"Alarm {key} not found")
        if not isinstance(response, dict):
            raise NotFoundError(f"Alarm {key} returned invalid response")
        return self._to_model(response)

    def snooze(self, key: int, hours: int = 24) -> Alarm:
        """Snooze an alarm for a specified duration.

        Snoozing temporarily hides the alarm from the active alarm list.

        Args:
            key: Alarm $key.
            hours: Number of hours to snooze (default: 24, max: 8760 / 1 year).

        Returns:
            Updated Alarm object.

        Example:
            >>> # Snooze for 24 hours (default)
            >>> alarm = client.alarms.snooze(alarm_key)

            >>> # Snooze for 48 hours
            >>> alarm = client.alarms.snooze(alarm_key, hours=48)
        """
        if hours < 1:
            raise ValueError("hours must be at least 1")
        if hours > 8760:
            raise ValueError("hours cannot exceed 8760 (1 year)")

        snooze_timestamp = int(time.time()) + (hours * 3600)
        self._client._request(
            "PUT", f"{self._endpoint}/{key}", json_data={"snooze": snooze_timestamp}
        )
        return self.get(key)

    def snooze_to(self, key: int, until: datetime) -> Alarm:
        """Snooze an alarm until a specific time.

        Args:
            key: Alarm $key.
            until: Datetime when snooze should expire.

        Returns:
            Updated Alarm object.

        Example:
            >>> from datetime import datetime, timedelta
            >>> next_week = datetime.now() + timedelta(days=7)
            >>> alarm = client.alarms.snooze_to(alarm_key, until=next_week)
        """
        # Convert to UTC timestamp
        if until.tzinfo is None:
            # Assume local time if no timezone
            snooze_timestamp = int(until.timestamp())
        else:
            snooze_timestamp = int(until.timestamp())

        if snooze_timestamp <= int(time.time()):
            raise ValueError("snooze time must be in the future")

        self._client._request(
            "PUT", f"{self._endpoint}/{key}", json_data={"snooze": snooze_timestamp}
        )
        return self.get(key)

    def unsnooze(self, key: int) -> Alarm:
        """Remove snooze from an alarm, making it active again.

        Args:
            key: Alarm $key.

        Returns:
            Updated Alarm object.

        Example:
            >>> alarm = client.alarms.unsnooze(alarm_key)
            >>> print(alarm.is_snoozed)  # False
        """
        self._client._request("PUT", f"{self._endpoint}/{key}", json_data={"snooze": 0})
        return self.get(key)

    def resolve(self, key: int) -> None:
        """Resolve a resolvable alarm.

        Only alarms with resolvable=True can be resolved. After resolution,
        the alarm may be removed or moved to history.

        Args:
            key: Alarm $key.

        Raises:
            ValueError: If alarm is not resolvable.
            NotFoundError: If alarm not found.
            APIError: If resolve action fails.

        Example:
            >>> alarm = client.alarms.get(alarm_key)
            >>> if alarm.is_resolvable:
            ...     client.alarms.resolve(alarm_key)
        """
        # Verify alarm exists and is resolvable
        alarm = self.get(key)
        if not alarm.is_resolvable:
            raise ValueError(f"Alarm {key} is not resolvable")

        # Use row action endpoint: POST /alarms/{key}/resolve
        self._client._request("POST", f"{self._endpoint}/{key}/resolve")

    def list_history(
        self,
        filter: str | None = None,
        fields: builtins.list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        *,
        level: str | builtins.list[str] | None = None,
        **filter_kwargs: Any,
    ) -> builtins.list[AlarmHistory]:
        """List alarm history (resolved/lowered alarms).

        Args:
            filter: OData filter string.
            fields: List of fields to return.
            limit: Maximum number of results.
            offset: Skip this many results.
            level: Filter by severity level (or list of levels).
            **filter_kwargs: Additional filter arguments.

        Returns:
            List of AlarmHistory objects sorted by lowered date (newest first).

        Example:
            >>> # Recent alarm history
            >>> history = client.alarms.list_history(limit=50)

            >>> # Critical alarm history
            >>> critical_history = client.alarms.list_history(level="critical")
        """
        conditions: builtins.list[str] = []

        if filter:
            conditions.append(f"({filter})")

        # Level filter
        if level:
            if isinstance(level, str):
                conditions.append(f"level eq '{level.lower()}'")
            else:
                level_filters = [f"level eq '{lv.lower()}'" for lv in level]
                if len(level_filters) == 1:
                    conditions.append(level_filters[0])
                else:
                    conditions.append(f"({' or '.join(level_filters)})")

        # Add any additional filter kwargs
        if filter_kwargs:
            conditions.append(build_filter(**filter_kwargs))

        # Combine conditions
        combined_filter = " and ".join(conditions) if conditions else None

        # Use default fields if not specified
        if fields is None:
            fields = _DEFAULT_HISTORY_FIELDS

        params: dict[str, Any] = {}
        if combined_filter:
            params["filter"] = combined_filter
        if fields:
            params["fields"] = ",".join(fields)
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset

        # Sort by lowered date descending (newest first)
        params["sort"] = "-alarm_lowered"

        response = self._client._request("GET", "alarm_history", params=params)

        if response is None:
            return []

        if not isinstance(response, list):
            return [self._to_history_model(response)]

        return [self._to_history_model(item) for item in response]

    def get_history(
        self,
        key: int,
        *,
        fields: builtins.list[str] | None = None,
    ) -> AlarmHistory:
        """Get an alarm history entry by key.

        Args:
            key: Alarm history $key (ID).
            fields: List of fields to return.

        Returns:
            AlarmHistory object.

        Raises:
            NotFoundError: If alarm history not found.
        """
        params: dict[str, Any] = {}
        if fields is None:
            fields = _DEFAULT_HISTORY_FIELDS
        if fields:
            params["fields"] = ",".join(fields)

        response = self._client._request("GET", f"alarm_history/{key}", params=params)
        if response is None:
            raise NotFoundError(f"Alarm history {key} not found")
        if not isinstance(response, dict):
            raise NotFoundError(f"Alarm history {key} returned invalid response")
        return self._to_history_model(response)

    def get_summary(self) -> dict[str, Any]:
        """Get a summary of current alarm status.

        Returns:
            Dictionary with alarm counts by level and status.

        Example:
            >>> summary = client.alarms.get_summary()
            >>> print(f"Critical: {summary['critical']}")
            >>> print(f"Error: {summary['error']}")
            >>> print(f"Warning: {summary['warning']}")
            >>> print(f"Total: {summary['total']}")
            >>> print(f"Snoozed: {summary['snoozed']}")
        """
        # Get all alarms including snoozed
        all_alarms = self.list(include_snoozed=True)
        active_alarms = [a for a in all_alarms if not a.is_snoozed]
        snoozed_alarms = [a for a in all_alarms if a.is_snoozed]

        # Count by level
        critical = len([a for a in active_alarms if a.level == "critical"])
        error = len([a for a in active_alarms if a.level == "error"])
        warning = len([a for a in active_alarms if a.level == "warning"])
        message = len([a for a in active_alarms if a.level == "message"])
        resolvable = len([a for a in active_alarms if a.is_resolvable])

        return {
            "total": len(all_alarms),
            "active": len(active_alarms),
            "snoozed": len(snoozed_alarms),
            "critical": critical,
            "error": error,
            "warning": warning,
            "message": message,
            "resolvable": resolvable,
        }
