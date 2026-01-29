"""Log resource manager for VergeOS system logs."""

from __future__ import annotations

import builtins
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from pyvergeos.exceptions import NotFoundError
from pyvergeos.filters import build_filter
from pyvergeos.resources.base import ResourceManager, ResourceObject

if TYPE_CHECKING:
    from pyvergeos.client import VergeClient


# Log levels
LOG_LEVELS = ["critical", "error", "warning", "message", "audit", "summary", "debug"]

# Object type mappings (friendly name -> API value)
OBJECT_TYPE_MAP = {
    "VM": "vm",
    "Network": "vnet",
    "Tenant": "tenant",
    "User": "user",
    "System": "system",
    "Node": "node",
    "Cluster": "cluster",
    "File": "file",
    "Group": "group",
    "Permission": "permission",
    "SMTP": "smtp",
    "Task": "task",
    "Site": "site",
    "SystemSnapshot": "cloud_snapshots",
    "CatalogRepository": "catalog_repository",
    "OIDCApplication": "oidc_application",
    "ServiceContainer": "service_container",
    "NASService": "vm_service",
    "VMImport": "vm_import",
    "VMwareBackup": "vmware_container",
    "SnapshotProfile": "snapshot_profile",
    "ImportExport": "import_export",
    "Update": "updates",
    "Other": "other",
}

# Reverse mapping (API value -> friendly name)
OBJECT_TYPE_DISPLAY = {v: k for k, v in OBJECT_TYPE_MAP.items()}
# Add extra display mappings for full names from API schema
OBJECT_TYPE_DISPLAY.update(
    {
        "vm": "VM",
        "vnet": "Network",
        "tenant": "Tenant",
        "user": "User",
        "system": "System",
        "node": "Node",
        "cluster": "Cluster",
        "file": "File",
        "group": "Group",
        "permission": "Permission",
        "smtp": "SMTP",
        "task": "Task",
        "site": "Site",
        "cloud_snapshots": "SystemSnapshot",
        "catalog_repository": "CatalogRepository",
        "oidc_application": "OIDCApplication",
        "service_container": "ServiceContainer",
        "vm_service": "NASService",
        "vm_import": "VMImport",
        "vmware_container": "VMwareBackup",
        "snapshot_profile": "SnapshotProfile",
        "import_export": "ImportExport",
        "updates": "Update",
        "other": "Other",
    }
)


# Default fields for log list operations
_DEFAULT_LOG_FIELDS = [
    "$key",
    "level",
    "text",
    "timestamp",
    "user",
    "object_type",
    "object_name",
]


class Log(ResourceObject):
    """Log resource object.

    Represents a log entry in VergeOS system logs including audit events,
    messages, warnings, errors, and critical events.

    Properties:
        level: Log severity (critical, error, warning, message, audit, summary, debug).
        level_display: Capitalized display name for level.
        text: Log message text.
        user: User who performed the action.
        object_type: API object type value (vm, vnet, etc.).
        object_type_display: Friendly object type name (VM, Network, etc.).
        object_name: Name of the related object.
        created_at: Datetime when log was created (from microsecond timestamp).
        timestamp_us: Raw timestamp in microseconds.
    """

    @property
    def level(self) -> str:
        """Get log severity level."""
        return str(self.get("level", ""))

    @property
    def level_display(self) -> str:
        """Get capitalized level display name."""
        level = self.level
        return level.capitalize() if level else ""

    @property
    def text(self) -> str:
        """Get log message text."""
        return str(self.get("text", ""))

    @property
    def user(self) -> str:
        """Get user who performed the action."""
        return str(self.get("user", ""))

    @property
    def object_type(self) -> str:
        """Get API object type value."""
        return str(self.get("object_type", ""))

    @property
    def object_type_display(self) -> str:
        """Get friendly object type name."""
        return OBJECT_TYPE_DISPLAY.get(self.object_type, self.object_type)

    @property
    def object_name(self) -> str:
        """Get name of the related object."""
        return str(self.get("object_name", ""))

    @property
    def timestamp_us(self) -> int:
        """Get raw timestamp in microseconds."""
        ts = self.get("timestamp")
        return int(ts) if ts is not None else 0

    @property
    def created_at(self) -> datetime | None:
        """Get datetime when log was created.

        Converts the microsecond timestamp to a datetime object.
        """
        ts = self.get("timestamp")
        if ts is None or ts == 0:
            return None
        # Timestamp is in microseconds, convert to seconds for datetime
        ts_seconds = int(ts) / 1_000_000
        return datetime.fromtimestamp(ts_seconds, tz=timezone.utc)

    def __repr__(self) -> str:
        key = self.get("$key", "?")
        level = self.level_display
        text = self.text[:30] + "..." if len(self.text) > 30 else self.text
        return f"<Log key={key} level={level!r} text={text!r}>"


class LogManager(ResourceManager[Log]):
    """Manager for Log operations.

    Logs provide an audit trail and history of events in the VergeOS system,
    including user actions, system events, errors, and warnings.

    Example:
        >>> # List recent logs
        >>> logs = client.logs.list(limit=100)
        >>> for log in logs:
        ...     print(f"{log.level_display}: {log.text}")

        >>> # List errors and critical logs
        >>> errors = client.logs.list(level=["error", "critical"])

        >>> # Filter by object type
        >>> vm_logs = client.logs.list(object_type="VM")

        >>> # Filter by user
        >>> admin_logs = client.logs.list(user="admin")

        >>> # Filter by time range (last hour)
        >>> from datetime import datetime, timedelta, timezone
        >>> since = datetime.now(timezone.utc) - timedelta(hours=1)
        >>> recent = client.logs.list(since=since)

        >>> # Search log text
        >>> power_logs = client.logs.list(text="power")
    """

    _endpoint = "logs"

    def __init__(self, client: VergeClient) -> None:
        super().__init__(client)

    def _to_model(self, data: dict[str, Any]) -> Log:
        return Log(data, self)

    def list(
        self,
        filter: str | None = None,
        fields: builtins.list[str] | None = None,
        limit: int | None = 100,
        offset: int | None = None,
        *,
        level: str | builtins.list[str] | None = None,
        object_type: str | None = None,
        user: str | None = None,
        text: str | None = None,
        since: datetime | None = None,
        before: datetime | None = None,
        errors_only: bool = False,
        **filter_kwargs: Any,
    ) -> builtins.list[Log]:
        """List logs with optional filtering.

        Args:
            filter: OData filter string.
            fields: List of fields to return.
            limit: Maximum number of results (default: 100, max: 10000).
            offset: Skip this many results.
            level: Filter by severity level (or list of levels).
                   Values: critical, error, warning, message, audit, summary, debug.
            object_type: Filter by object type.
                         Values: VM, Network, Tenant, User, System, Node, Cluster,
                         File, Group, Permission, SMTP, Task, Site, etc.
            user: Filter logs by user (contains search).
            text: Filter logs containing this text (contains search).
            since: Return logs since this datetime.
            before: Return logs before this datetime.
            errors_only: Shortcut to filter for error and critical logs only.
            **filter_kwargs: Additional filter arguments.

        Returns:
            List of Log objects sorted by timestamp (newest first).

        Example:
            >>> # Recent logs
            >>> logs = client.logs.list()

            >>> # Error and critical logs only
            >>> errors = client.logs.list(errors_only=True)

            >>> # VM logs from the last hour
            >>> from datetime import datetime, timedelta, timezone
            >>> since = datetime.now(timezone.utc) - timedelta(hours=1)
            >>> vm_logs = client.logs.list(object_type="VM", since=since)

            >>> # Search for specific text
            >>> logs = client.logs.list(text="snapshot")
        """
        conditions: builtins.list[str] = []

        if filter:
            conditions.append(f"({filter})")

        # Handle errors_only shortcut
        if errors_only:
            level = ["error", "critical"]

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

        # Object type filter
        if object_type:
            api_object_type = OBJECT_TYPE_MAP.get(object_type, object_type)
            conditions.append(f"object_type eq '{api_object_type}'")

        # User filter (contains search)
        if user:
            escaped_user = user.replace("'", "''")
            conditions.append(f"user ct '{escaped_user}'")

        # Text filter (contains search)
        if text:
            escaped_text = text.replace("'", "''")
            conditions.append(f"text ct '{escaped_text}'")

        # Time filters (timestamp is in microseconds)
        if since:
            if since.tzinfo is None:
                # Assume local time if no timezone, convert to UTC timestamp
                since_us = int(since.timestamp() * 1_000_000)
            else:
                since_us = int(since.timestamp() * 1_000_000)
            conditions.append(f"timestamp ge {since_us}")

        if before:
            if before.tzinfo is None:
                before_us = int(before.timestamp() * 1_000_000)
            else:
                before_us = int(before.timestamp() * 1_000_000)
            conditions.append(f"timestamp lt {before_us}")

        # Add any additional filter kwargs
        if filter_kwargs:
            conditions.append(build_filter(**filter_kwargs))

        # Combine conditions
        combined_filter = " and ".join(conditions) if conditions else None

        # Use default fields if not specified
        if fields is None:
            fields = _DEFAULT_LOG_FIELDS

        params: dict[str, Any] = {}
        if combined_filter:
            params["filter"] = combined_filter
        if fields:
            params["fields"] = ",".join(fields)
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset

        # Sort by timestamp descending (newest first)
        params["sort"] = "-timestamp"

        response = self._client._request("GET", self._endpoint, params=params)

        if response is None:
            return []

        if not isinstance(response, list):
            return [self._to_model(response)]

        return [self._to_model(item) for item in response]

    def list_errors(
        self,
        limit: int | None = 100,
        since: datetime | None = None,
    ) -> builtins.list[Log]:
        """List error and critical logs.

        Args:
            limit: Maximum number of results.
            since: Return logs since this datetime.

        Returns:
            List of error and critical Log objects.

        Example:
            >>> errors = client.logs.list_errors()
            >>> for log in errors:
            ...     print(f"[{log.level_display}] {log.text}")
        """
        return self.list(errors_only=True, limit=limit, since=since)

    def list_by_level(
        self,
        level: str,
        limit: int | None = 100,
        since: datetime | None = None,
    ) -> builtins.list[Log]:
        """List logs by severity level.

        Args:
            level: Log level (critical, error, warning, message, audit, summary, debug).
            limit: Maximum number of results.
            since: Return logs since this datetime.

        Returns:
            List of Log objects at the specified level.

        Example:
            >>> warnings = client.logs.list_by_level("warning")
        """
        return self.list(level=level, limit=limit, since=since)

    def list_by_object_type(
        self,
        object_type: str,
        limit: int | None = 100,
        since: datetime | None = None,
    ) -> builtins.list[Log]:
        """List logs by object type.

        Args:
            object_type: Object type (VM, Network, Tenant, User, System, Node, etc.).
            limit: Maximum number of results.
            since: Return logs since this datetime.

        Returns:
            List of Log objects for the specified object type.

        Example:
            >>> vm_logs = client.logs.list_by_object_type("VM")
            >>> network_logs = client.logs.list_by_object_type("Network")
        """
        return self.list(object_type=object_type, limit=limit, since=since)

    def list_by_user(
        self,
        user: str,
        limit: int | None = 100,
        since: datetime | None = None,
    ) -> builtins.list[Log]:
        """List logs by user.

        Args:
            user: Username to filter by (contains search).
            limit: Maximum number of results.
            since: Return logs since this datetime.

        Returns:
            List of Log objects for the specified user.

        Example:
            >>> admin_logs = client.logs.list_by_user("admin")
        """
        return self.list(user=user, limit=limit, since=since)

    def search(
        self,
        text: str,
        limit: int | None = 100,
        since: datetime | None = None,
        level: str | builtins.list[str] | None = None,
        object_type: str | None = None,
    ) -> builtins.list[Log]:
        """Search logs by text content.

        Args:
            text: Text to search for (case-insensitive contains search).
            limit: Maximum number of results.
            since: Return logs since this datetime.
            level: Filter by severity level(s).
            object_type: Filter by object type.

        Returns:
            List of Log objects containing the search text.

        Example:
            >>> power_logs = client.logs.search("power")
            >>> snapshot_errors = client.logs.search(
            ...     "snapshot", level=["error", "critical"]
            ... )
        """
        return self.list(
            text=text, limit=limit, since=since, level=level, object_type=object_type
        )

    def get(
        self,
        key: int | None = None,
        *,
        name: str | None = None,
        fields: builtins.list[str] | None = None,
    ) -> Log:
        """Get a log entry by key.

        Note: Logs do not have a name field, so name parameter is not supported.

        Args:
            key: Log $key (ID).
            name: Not supported for logs (will raise ValueError).
            fields: List of fields to return.

        Returns:
            Log object.

        Raises:
            NotFoundError: If log not found.
            ValueError: If key not provided or if name is used.

        Example:
            >>> log = client.logs.get(12345)
            >>> print(f"{log.level_display}: {log.text}")
        """
        if name is not None:
            raise ValueError("Logs do not have a name field. Use key instead.")
        if key is None:
            raise ValueError("key must be provided")

        params: dict[str, Any] = {}
        if fields is None:
            fields = _DEFAULT_LOG_FIELDS
        if fields:
            params["fields"] = ",".join(fields)

        response = self._client._request("GET", f"{self._endpoint}/{key}", params=params)
        if response is None:
            raise NotFoundError(f"Log {key} not found")
        if not isinstance(response, dict):
            raise NotFoundError(f"Log {key} returned invalid response")
        return self._to_model(response)
