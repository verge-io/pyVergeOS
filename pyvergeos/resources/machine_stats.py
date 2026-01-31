"""Machine Stats & Monitoring resource managers.

This module provides access to machine performance metrics, status,
and logs. A "machine" in VergeOS represents both VMs and physical nodes.

Example:
    >>> # Access VM stats
    >>> vm = client.vms.get(name="web-server")
    >>> stats = vm.stats.get()
    >>> print(f"CPU: {stats.total_cpu}%, RAM: {stats.ram_used_mb}MB")

    >>> # Access stats history
    >>> history = vm.stats.history_short()
    >>> for point in history:
    ...     print(f"{point.timestamp}: CPU {point.total_cpu}%")

    >>> # Access machine status
    >>> status = vm.machine_status.get()
    >>> print(f"Status: {status.status}, Node: {status.node_name}")

    >>> # Access machine logs
    >>> logs = vm.machine_logs.list(level="error")
    >>> for log in logs:
    ...     print(f"[{log.level}] {log.text}")
"""

from __future__ import annotations

import builtins
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Literal

from pyvergeos.exceptions import NotFoundError
from pyvergeos.filters import build_filter
from pyvergeos.resources.base import ResourceManager, ResourceObject

if TYPE_CHECKING:
    from pyvergeos.client import VergeClient


# Status display mappings
STATUS_DISPLAY = {
    "initializing": "Initializing",
    "starting": "Starting",
    "running": "Running",
    "stopping": "Stopping",
    "unresponsive": "Unresponsive",
    "stopped": "Stopped",
    "hibernated": "Hibernated",
    "hibernating": "Hibernating",
    "initmigrate": "Migration Initializing",
    "startmigrate": "Migration Starting",
    "migrating": "Migrating",
    "migratecomplete": "Migration Complete",
    "importing": "Importing",
    "maintenance": "Maintenance Mode",
    "leavingmaintenance": "Leaving Maintenance",
    "unlicensed": "Unlicensed",
    "needsrefresh": "Needs Refresh",
    "needsrestart": "Needs Restart",
    "waitingforresources": "Waiting For Resources",
    "error": "Error",
    "driversreloading": "Drivers Reloading",
}

STATE_DISPLAY = {
    "online": "Online",
    "offline": "Offline",
    "warning": "Warning",
    "error": "Error",
}

LOG_LEVEL_DISPLAY = {
    "audit": "Audit",
    "message": "Message",
    "warning": "Warning",
    "error": "Error",
    "critical": "Critical",
    "summary": "Summary",
    "debug": "Debug",
}


# =============================================================================
# Machine Stats
# =============================================================================


class MachineStats(ResourceObject):
    """Machine statistics resource object.

    Provides current performance metrics for a machine (VM or node).
    """

    @property
    def machine_key(self) -> int:
        """Parent machine key."""
        return int(self.get("machine", 0))

    @property
    def total_cpu(self) -> int:
        """Total CPU usage percentage (0-100)."""
        return int(self.get("total_cpu", 0))

    @property
    def user_cpu(self) -> int:
        """User CPU usage percentage."""
        return int(self.get("user_cpu", 0))

    @property
    def system_cpu(self) -> int:
        """System CPU usage percentage."""
        return int(self.get("system_cpu", 0))

    @property
    def iowait_cpu(self) -> int:
        """IO wait CPU percentage."""
        return int(self.get("iowait_cpu", 0))

    @property
    def vmusage_cpu(self) -> int:
        """VM usage CPU percentage (for nodes)."""
        return int(self.get("vmusage_cpu", 0))

    @property
    def irq_cpu(self) -> int:
        """IRQ CPU percentage."""
        return int(self.get("irq_cpu", 0))

    @property
    def ram_used_mb(self) -> int:
        """Physical RAM used in MB."""
        return int(self.get("ram_used", 0))

    @property
    def ram_pct(self) -> int:
        """Physical RAM used percentage."""
        return int(self.get("ram_pct", 0))

    @property
    def vram_used_mb(self) -> int:
        """Virtual RAM used in MB."""
        return int(self.get("vram_used", 0))

    @property
    def core_usagelist(self) -> list[Any]:
        """Per-core usage list."""
        usage = self.get("core_usagelist")
        if isinstance(usage, list):
            return usage
        return []

    @property
    def core_temp(self) -> int | None:
        """Average core temperature in Celsius."""
        temp = self.get("core_temp")
        return int(temp) if temp is not None else None

    @property
    def core_temp_top(self) -> int | None:
        """Top (highest) core temperature in Celsius."""
        temp = self.get("core_temp_top")
        return int(temp) if temp is not None else None

    @property
    def core_peak(self) -> int:
        """Peak core usage percentage."""
        return int(self.get("core_peak", 0))

    @property
    def cores_gt_25_pct(self) -> int:
        """Count of cores above 25% usage."""
        return int(self.get("core_count_gt_25", 0))

    @property
    def cores_gt_50_pct(self) -> int:
        """Count of cores above 50% usage."""
        return int(self.get("core_count_gt_50", 0))

    @property
    def cores_gt_75_pct(self) -> int:
        """Count of cores above 75% usage."""
        return int(self.get("core_count_gt_75", 0))

    @property
    def modified_at(self) -> datetime | None:
        """Timestamp when stats were last updated."""
        ts = self.get("modified")
        if ts:
            return datetime.fromtimestamp(int(ts), tz=timezone.utc)
        return None

    def __repr__(self) -> str:
        return (
            f"<MachineStats machine={self.machine_key} "
            f"cpu={self.total_cpu}% ram={self.ram_used_mb}MB>"
        )


class MachineStatsHistory(ResourceObject):
    """Machine statistics history record.

    Represents a single time point in the stats history.
    """

    @property
    def machine_key(self) -> int:
        """Parent machine key."""
        return int(self.get("machine", 0))

    @property
    def timestamp(self) -> datetime | None:
        """Timestamp for this history point."""
        ts = self.get("timestamp")
        if ts:
            return datetime.fromtimestamp(int(ts), tz=timezone.utc)
        return None

    @property
    def timestamp_epoch(self) -> int:
        """Timestamp as Unix epoch."""
        return int(self.get("timestamp", 0))

    @property
    def total_cpu(self) -> int:
        """Total CPU usage percentage."""
        return int(self.get("total_cpu", 0))

    @property
    def user_cpu(self) -> int:
        """User CPU usage percentage."""
        return int(self.get("user_cpu", 0))

    @property
    def system_cpu(self) -> int:
        """System CPU usage percentage."""
        return int(self.get("system_cpu", 0))

    @property
    def iowait_cpu(self) -> int:
        """IO wait CPU percentage."""
        return int(self.get("iowait_cpu", 0))

    @property
    def vmusage_cpu(self) -> int:
        """VM usage CPU percentage."""
        return int(self.get("vmusage_cpu", 0))

    @property
    def irq_cpu(self) -> int:
        """IRQ CPU percentage."""
        return int(self.get("irq_cpu", 0))

    @property
    def ram_used_mb(self) -> int:
        """Physical RAM used in MB."""
        return int(self.get("ram_used", 0))

    @property
    def vram_used_mb(self) -> int:
        """Virtual RAM used in MB."""
        return int(self.get("vram_used", 0))

    @property
    def core_temp(self) -> int | None:
        """Average core temperature."""
        temp = self.get("core_temp")
        return int(temp) if temp is not None else None

    @property
    def core_temp_top(self) -> int | None:
        """Top core temperature."""
        temp = self.get("core_temp_top")
        return int(temp) if temp is not None else None

    @property
    def core_peak(self) -> int:
        """Peak core usage percentage."""
        return int(self.get("core_peak", 0))

    def __repr__(self) -> str:
        ts = self.timestamp.isoformat() if self.timestamp else "?"
        return f"<MachineStatsHistory ts={ts} cpu={self.total_cpu}%>"


class MachineStatsManager(ResourceManager[MachineStats]):
    """Manager for machine statistics.

    Provides access to current and historical performance metrics.
    Scoped to a specific machine.

    Example:
        >>> # Get current stats
        >>> stats = manager.get()
        >>> print(f"CPU: {stats.total_cpu}%")

        >>> # Get short-term history (high resolution)
        >>> history = manager.history_short(limit=100)

        >>> # Get long-term history (lower resolution, longer retention)
        >>> history = manager.history_long(limit=1000)
    """

    _endpoint = "machine_stats"

    _default_fields = [
        "$key",
        "machine",
        "total_cpu",
        "user_cpu",
        "system_cpu",
        "iowait_cpu",
        "vmusage_cpu",
        "irq_cpu",
        "ram_used",
        "ram_pct",
        "vram_used",
        "core_usagelist",
        "core_temp",
        "core_temp_top",
        "core_peak",
        "core_count_gt_25",
        "core_count_gt_50",
        "core_count_gt_75",
        "modified",
    ]

    _history_fields = [
        "$key",
        "machine",
        "timestamp",
        "total_cpu",
        "user_cpu",
        "system_cpu",
        "iowait_cpu",
        "vmusage_cpu",
        "irq_cpu",
        "ram_used",
        "vram_used",
        "core_temp",
        "core_temp_top",
        "core_peak",
        "core_count_gt_25",
        "core_count_gt_50",
        "core_count_gt_75",
    ]

    def __init__(self, client: VergeClient, machine_key: int) -> None:
        super().__init__(client)
        self._machine_key = machine_key

    def _to_model(self, data: dict[str, Any]) -> MachineStats:
        return MachineStats(data, self)

    def _to_history_model(self, data: dict[str, Any]) -> MachineStatsHistory:
        return MachineStatsHistory(data, self)

    def get(self, fields: builtins.list[str] | None = None) -> MachineStats:  # type: ignore[override]
        """Get current machine statistics.

        Args:
            fields: List of fields to return.

        Returns:
            MachineStats object.

        Raises:
            NotFoundError: If stats not found for this machine.
        """
        if fields is None:
            fields = self._default_fields

        params: dict[str, Any] = {
            "filter": f"machine eq {self._machine_key}",
            "fields": ",".join(fields),
            "limit": 1,
        }

        response = self._client._request("GET", self._endpoint, params=params)

        if response is None:
            raise NotFoundError(f"Stats not found for machine {self._machine_key}")

        if isinstance(response, list):
            if not response:
                raise NotFoundError(f"Stats not found for machine {self._machine_key}")
            return self._to_model(response[0])

        return self._to_model(response)

    def history_short(
        self,
        limit: int | None = None,
        offset: int | None = None,
        since: datetime | int | None = None,
        until: datetime | int | None = None,
        fields: builtins.list[str] | None = None,
    ) -> builtins.list[MachineStatsHistory]:
        """Get short-term stats history (high resolution).

        Args:
            limit: Maximum number of records to return.
            offset: Skip this many records.
            since: Return records after this time (datetime or epoch).
            until: Return records before this time (datetime or epoch).
            fields: List of fields to return.

        Returns:
            List of MachineStatsHistory objects, sorted by timestamp descending.
        """
        return self._get_history(
            "machine_stats_history_short",
            limit=limit,
            offset=offset,
            since=since,
            until=until,
            fields=fields,
        )

    def history_long(
        self,
        limit: int | None = None,
        offset: int | None = None,
        since: datetime | int | None = None,
        until: datetime | int | None = None,
        fields: builtins.list[str] | None = None,
    ) -> builtins.list[MachineStatsHistory]:
        """Get long-term stats history (lower resolution, longer retention).

        Args:
            limit: Maximum number of records to return.
            offset: Skip this many records.
            since: Return records after this time (datetime or epoch).
            until: Return records before this time (datetime or epoch).
            fields: List of fields to return.

        Returns:
            List of MachineStatsHistory objects, sorted by timestamp descending.
        """
        return self._get_history(
            "machine_stats_history_long",
            limit=limit,
            offset=offset,
            since=since,
            until=until,
            fields=fields,
        )

    def _get_history(
        self,
        endpoint: str,
        limit: int | None = None,
        offset: int | None = None,
        since: datetime | int | None = None,
        until: datetime | int | None = None,
        fields: builtins.list[str] | None = None,
    ) -> builtins.list[MachineStatsHistory]:
        """Internal helper to get history from short or long endpoint."""
        if fields is None:
            fields = self._history_fields

        filters = [f"machine eq {self._machine_key}"]

        # Convert datetime to epoch if needed
        if since is not None:
            since_epoch = int(since.timestamp()) if isinstance(since, datetime) else int(since)
            filters.append(f"timestamp ge {since_epoch}")

        if until is not None:
            until_epoch = int(until.timestamp()) if isinstance(until, datetime) else int(until)
            filters.append(f"timestamp le {until_epoch}")

        params: dict[str, Any] = {
            "filter": " and ".join(filters),
            "fields": ",".join(fields),
            "sort": "-timestamp",
        }

        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset

        response = self._client._request("GET", endpoint, params=params)

        if response is None:
            return []

        if isinstance(response, list):
            return [self._to_history_model(item) for item in response]

        return [self._to_history_model(response)]


# =============================================================================
# Machine Status
# =============================================================================


class MachineStatus(ResourceObject):
    """Machine status resource object.

    Provides operational status for a machine (VM or node).
    """

    @property
    def machine_key(self) -> int:
        """Parent machine key."""
        return int(self.get("machine", 0))

    @property
    def is_running(self) -> bool:
        """Check if machine is currently running."""
        return bool(self.get("running", False))

    @property
    def is_migratable(self) -> bool:
        """Check if machine can be migrated."""
        return bool(self.get("migratable", True))

    @property
    def status(self) -> str:
        """Current status (running, stopped, migrating, etc.)."""
        raw = str(self.get("status", "stopped"))
        return STATUS_DISPLAY.get(raw, raw)

    @property
    def status_raw(self) -> str:
        """Raw status value."""
        return str(self.get("status", "stopped"))

    @property
    def status_info(self) -> str:
        """Additional status information."""
        return str(self.get("status_info", ""))

    @property
    def state(self) -> str:
        """State (online, offline, warning, error)."""
        raw = str(self.get("state", "offline"))
        return STATE_DISPLAY.get(raw, raw)

    @property
    def state_raw(self) -> str:
        """Raw state value."""
        return str(self.get("state", "offline"))

    @property
    def powerstate(self) -> bool:
        """Power state (on/off)."""
        return bool(self.get("powerstate", False))

    @property
    def node_key(self) -> int | None:
        """Node where machine is running."""
        node = self.get("node")
        return int(node) if node else None

    @property
    def node_name(self) -> str:
        """Name of node where machine is running."""
        return str(self.get("node_name", ""))

    @property
    def migrated_node_key(self) -> int | None:
        """Node the machine was migrated from."""
        node = self.get("migrated_node")
        return int(node) if node else None

    @property
    def migration_destination_key(self) -> int | None:
        """Node the machine is migrating to."""
        node = self.get("migration_destination")
        return int(node) if node else None

    @property
    def started_at(self) -> datetime | None:
        """Timestamp when machine was started."""
        ts = self.get("started")
        if ts:
            return datetime.fromtimestamp(int(ts), tz=timezone.utc)
        return None

    @property
    def local_time(self) -> datetime | None:
        """Machine local time."""
        ts = self.get("local_time")
        if ts:
            return datetime.fromtimestamp(int(ts), tz=timezone.utc)
        return None

    @property
    def last_update(self) -> datetime | None:
        """Timestamp of last status update."""
        ts = self.get("last_update")
        if ts:
            return datetime.fromtimestamp(int(ts), tz=timezone.utc)
        return None

    @property
    def running_cores(self) -> int:
        """Number of running CPU cores."""
        return int(self.get("running_cores", 0))

    @property
    def running_ram_mb(self) -> int:
        """Amount of running RAM in MB."""
        return int(self.get("running_ram", 0))

    @property
    def agent_version(self) -> str:
        """Guest agent version."""
        return str(self.get("agent_version", ""))

    @property
    def has_agent(self) -> bool:
        """Check if guest agent is installed."""
        return bool(self.get("agent_version"))

    @property
    def agent_features(self) -> dict[str, Any]:
        """Guest agent supported features."""
        features = self.get("agent_features")
        return features if isinstance(features, dict) else {}

    @property
    def agent_guest_info(self) -> dict[str, Any]:
        """Guest OS information from agent."""
        info = self.get("agent_guest_info")
        return info if isinstance(info, dict) else {}

    def __repr__(self) -> str:
        return (
            f"<MachineStatus machine={self.machine_key} "
            f"status={self.status_raw} running={self.is_running}>"
        )


class MachineStatusManager(ResourceManager[MachineStatus]):
    """Manager for machine status.

    Provides access to operational status for a machine.
    Scoped to a specific machine.

    Example:
        >>> status = manager.get()
        >>> print(f"Status: {status.status}")
        >>> if status.is_running:
        ...     print(f"Running on node: {status.node_name}")
    """

    _endpoint = "machine_status"

    _default_fields = [
        "$key",
        "machine",
        "running",
        "migratable",
        "status",
        "status_info",
        "state",
        "powerstate",
        "node",
        "node#name as node_name",
        "migrated_node",
        "migration_destination",
        "started",
        "local_time",
        "last_update",
        "running_cores",
        "running_ram",
        "agent_version",
        "agent_features",
        "agent_guest_info",
    ]

    def __init__(self, client: VergeClient, machine_key: int) -> None:
        super().__init__(client)
        self._machine_key = machine_key

    def _to_model(self, data: dict[str, Any]) -> MachineStatus:
        return MachineStatus(data, self)

    def get(self, fields: builtins.list[str] | None = None) -> MachineStatus:  # type: ignore[override]
        """Get machine status.

        Args:
            fields: List of fields to return.

        Returns:
            MachineStatus object.

        Raises:
            NotFoundError: If status not found for this machine.
        """
        if fields is None:
            fields = self._default_fields

        params: dict[str, Any] = {
            "filter": f"machine eq {self._machine_key}",
            "fields": ",".join(fields),
            "limit": 1,
        }

        response = self._client._request("GET", self._endpoint, params=params)

        if response is None:
            raise NotFoundError(f"Status not found for machine {self._machine_key}")

        if isinstance(response, list):
            if not response:
                raise NotFoundError(f"Status not found for machine {self._machine_key}")
            return self._to_model(response[0])

        return self._to_model(response)


# =============================================================================
# Machine Logs
# =============================================================================


class MachineLog(ResourceObject):
    """Machine log entry resource object."""

    @property
    def machine_key(self) -> int:
        """Parent machine key."""
        return int(self.get("machine", 0))

    @property
    def machine_name(self) -> str:
        """Parent machine name."""
        return str(self.get("machine_name", ""))

    @property
    def level(self) -> str:
        """Log level (Audit, Message, Warning, Error, Critical)."""
        raw = str(self.get("level", "message"))
        return LOG_LEVEL_DISPLAY.get(raw, raw)

    @property
    def level_raw(self) -> str:
        """Raw log level value."""
        return str(self.get("level", "message"))

    @property
    def text(self) -> str:
        """Log message text."""
        return str(self.get("text", ""))

    @property
    def user(self) -> str:
        """User who generated the log entry."""
        return str(self.get("user", ""))

    @property
    def timestamp(self) -> datetime | None:
        """Timestamp of log entry (microseconds precision)."""
        ts = self.get("timestamp")
        if ts:
            # timestamp is in microseconds
            return datetime.fromtimestamp(int(ts) / 1_000_000, tz=timezone.utc)
        return None

    @property
    def timestamp_epoch_us(self) -> int:
        """Timestamp as Unix epoch in microseconds."""
        return int(self.get("timestamp", 0))

    @property
    def is_error(self) -> bool:
        """Check if this is an error or critical log."""
        return self.level_raw in ("error", "critical")

    @property
    def is_warning(self) -> bool:
        """Check if this is a warning log."""
        return self.level_raw == "warning"

    @property
    def is_audit(self) -> bool:
        """Check if this is an audit log."""
        return self.level_raw == "audit"

    def __repr__(self) -> str:
        ts = self.timestamp.isoformat() if self.timestamp else "?"
        text_preview = self.text[:40] + "..." if len(self.text) > 40 else self.text
        return f"<MachineLog [{self.level}] {ts}: {text_preview!r}>"


class MachineLogManager(ResourceManager[MachineLog]):
    """Manager for machine logs.

    Provides access to log entries for a machine.
    Scoped to a specific machine.

    Example:
        >>> # Get recent logs
        >>> logs = manager.list(limit=20)

        >>> # Get errors only
        >>> errors = manager.list(level="error")

        >>> # Get logs since a specific time
        >>> logs = manager.list(since=datetime.now() - timedelta(hours=1))
    """

    _endpoint = "machine_logs"

    _default_fields = [
        "$key",
        "machine",
        "machine#name as machine_name",
        "level",
        "text",
        "user",
        "timestamp",
    ]

    def __init__(self, client: VergeClient, machine_key: int) -> None:
        super().__init__(client)
        self._machine_key = machine_key

    def _to_model(self, data: dict[str, Any]) -> MachineLog:
        return MachineLog(data, self)

    def list(
        self,
        filter: str | None = None,  # noqa: A002
        fields: builtins.list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        *,
        level: Literal["audit", "message", "warning", "error", "critical", "summary", "debug"]
        | None = None,
        errors_only: bool = False,
        warnings_only: bool = False,
        since: datetime | int | None = None,
        until: datetime | int | None = None,
        **filter_kwargs: Any,
    ) -> builtins.list[MachineLog]:
        """List machine log entries.

        Args:
            filter: OData filter string.
            fields: List of fields to return.
            limit: Maximum number of results.
            offset: Skip this many results.
            level: Filter by log level.
            errors_only: Only return error and critical logs.
            warnings_only: Only return warning logs.
            since: Return logs after this time (datetime or epoch microseconds).
            until: Return logs before this time (datetime or epoch microseconds).
            **filter_kwargs: Additional filter arguments.

        Returns:
            List of MachineLog objects, sorted by timestamp descending.
        """
        if fields is None:
            fields = self._default_fields

        filters = [f"machine eq {self._machine_key}"]

        if filter:
            filters.append(filter)

        if level is not None:
            filters.append(f"level eq '{level}'")
        elif errors_only:
            filters.append("(level eq 'error' or level eq 'critical')")
        elif warnings_only:
            filters.append("level eq 'warning'")

        # Convert datetime to microseconds if needed
        if since is not None:
            if isinstance(since, datetime):
                since_us = int(since.timestamp() * 1_000_000)
            else:
                since_us = int(since)
            filters.append(f"timestamp ge {since_us}")

        if until is not None:
            if isinstance(until, datetime):
                until_us = int(until.timestamp() * 1_000_000)
            else:
                until_us = int(until)
            filters.append(f"timestamp le {until_us}")

        if filter_kwargs:
            filters.append(build_filter(**filter_kwargs))

        params: dict[str, Any] = {
            "filter": " and ".join(filters),
            "fields": ",".join(fields),
            "sort": "-timestamp",
        }

        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset

        response = self._client._request("GET", self._endpoint, params=params)

        if response is None:
            return []

        if isinstance(response, list):
            return [self._to_model(item) for item in response]

        return [self._to_model(response)]

    def get(  # type: ignore[override]
        self,
        key: int | None = None,
        *,
        fields: builtins.list[str] | None = None,
    ) -> MachineLog:
        """Get a specific log entry by key.

        Args:
            key: Log entry $key (ID).
            fields: List of fields to return.

        Returns:
            MachineLog object.

        Raises:
            NotFoundError: If log entry not found.
            ValueError: If key not provided.
        """
        if key is None:
            raise ValueError("key must be provided")

        if fields is None:
            fields = self._default_fields

        params: dict[str, Any] = {"fields": ",".join(fields)}
        response = self._client._request("GET", f"{self._endpoint}/{key}", params=params)

        if response is None:
            raise NotFoundError(f"Log entry {key} not found")

        if not isinstance(response, dict):
            raise NotFoundError(f"Log entry {key} returned invalid response")

        return self._to_model(response)
