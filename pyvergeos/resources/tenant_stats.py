"""Tenant Stats & Monitoring resource managers.

This module provides access to tenant performance metrics, status, logs,
and dashboard information for monitoring and billing/chargeback purposes.

Example:
    >>> # Access tenant stats
    >>> tenant = client.tenants.get(name="customer-a")
    >>> stats = tenant.stats.get()
    >>> print(f"RAM: {stats.ram_used_mb}MB")

    >>> # Access stats history for billing/capacity planning
    >>> history = tenant.stats.history_short(limit=100)
    >>> for point in history:
    ...     print(f"{point.timestamp}: CPU {point.total_cpu}%, RAM {point.ram_used_mb}MB")

    >>> # Access tenant-specific logs
    >>> logs = tenant.logs.list(level="error")
    >>> for log in logs:
    ...     print(f"[{log.level}] {log.text}")

    >>> # Access dashboard summary
    >>> dashboard = client.tenant_dashboard.get()
    >>> print(f"Online: {dashboard.tenants_online}/{dashboard.tenants_count}")
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
    from pyvergeos.resources.tenant_manager import Tenant


# Log level display mappings
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
# Tenant Stats
# =============================================================================


class TenantStats(ResourceObject):
    """Tenant statistics resource object.

    Provides current performance metrics for a tenant.
    """

    @property
    def tenant_key(self) -> int:
        """Parent tenant key."""
        return int(self.get("tenant", 0))

    @property
    def ram_used_mb(self) -> int:
        """RAM used in MB."""
        return int(self.get("ram_used", 0))

    @property
    def last_update(self) -> datetime | None:
        """Timestamp when stats were last updated."""
        ts = self.get("last_update")
        if ts:
            return datetime.fromtimestamp(int(ts), tz=timezone.utc)
        return None

    def __repr__(self) -> str:
        return f"<TenantStats tenant={self.tenant_key} ram={self.ram_used_mb}MB>"


class TenantStatsHistory(ResourceObject):
    """Tenant statistics history record.

    Represents a single time point in the stats history with comprehensive
    resource utilization metrics for billing and capacity planning.
    """

    @property
    def tenant_key(self) -> int:
        """Parent tenant key."""
        return int(self.get("tenant", 0))

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

    # CPU metrics
    @property
    def total_cpu(self) -> int:
        """Total CPU usage percentage."""
        return int(self.get("total_cpu", 0))

    @property
    def core_count(self) -> int:
        """Number of allocated CPU cores."""
        return int(self.get("core_count", 0))

    # RAM metrics
    @property
    def ram_used_mb(self) -> int:
        """Physical RAM used in MB."""
        return int(self.get("ram_used", 0))

    @property
    def vram_used_mb(self) -> int:
        """Virtual RAM used in MB."""
        return int(self.get("vram_used", 0))

    @property
    def ram_allocated_mb(self) -> int:
        """RAM allocated to tenant in MB."""
        return int(self.get("ram_allocated", 0))

    @property
    def ram_pct(self) -> int:
        """RAM usage percentage."""
        return int(self.get("ram_pct", 0))

    # Network metrics
    @property
    def ip_count(self) -> int:
        """Number of IP addresses assigned."""
        return int(self.get("ip_count", 0))

    # Storage tier metrics (Tier 0)
    @property
    def tier0_provisioned(self) -> int:
        """Tier 0 storage provisioned in bytes."""
        return int(self.get("tier0_provisioned", 0))

    @property
    def tier0_used(self) -> int:
        """Tier 0 storage used in bytes."""
        return int(self.get("tier0_used", 0))

    @property
    def tier0_allocated(self) -> int:
        """Tier 0 storage allocated in bytes."""
        return int(self.get("tier0_allocated", 0))

    @property
    def tier0_pct(self) -> int:
        """Tier 0 storage usage percentage."""
        return int(self.get("tier0_pct", 0))

    # Storage tier metrics (Tier 1)
    @property
    def tier1_provisioned(self) -> int:
        """Tier 1 storage provisioned in bytes."""
        return int(self.get("tier1_provisioned", 0))

    @property
    def tier1_used(self) -> int:
        """Tier 1 storage used in bytes."""
        return int(self.get("tier1_used", 0))

    @property
    def tier1_allocated(self) -> int:
        """Tier 1 storage allocated in bytes."""
        return int(self.get("tier1_allocated", 0))

    @property
    def tier1_pct(self) -> int:
        """Tier 1 storage usage percentage."""
        return int(self.get("tier1_pct", 0))

    # Storage tier metrics (Tier 2)
    @property
    def tier2_provisioned(self) -> int:
        """Tier 2 storage provisioned in bytes."""
        return int(self.get("tier2_provisioned", 0))

    @property
    def tier2_used(self) -> int:
        """Tier 2 storage used in bytes."""
        return int(self.get("tier2_used", 0))

    @property
    def tier2_allocated(self) -> int:
        """Tier 2 storage allocated in bytes."""
        return int(self.get("tier2_allocated", 0))

    @property
    def tier2_pct(self) -> int:
        """Tier 2 storage usage percentage."""
        return int(self.get("tier2_pct", 0))

    # Storage tier metrics (Tier 3)
    @property
    def tier3_provisioned(self) -> int:
        """Tier 3 storage provisioned in bytes."""
        return int(self.get("tier3_provisioned", 0))

    @property
    def tier3_used(self) -> int:
        """Tier 3 storage used in bytes."""
        return int(self.get("tier3_used", 0))

    @property
    def tier3_allocated(self) -> int:
        """Tier 3 storage allocated in bytes."""
        return int(self.get("tier3_allocated", 0))

    @property
    def tier3_pct(self) -> int:
        """Tier 3 storage usage percentage."""
        return int(self.get("tier3_pct", 0))

    # Storage tier metrics (Tier 4)
    @property
    def tier4_provisioned(self) -> int:
        """Tier 4 storage provisioned in bytes."""
        return int(self.get("tier4_provisioned", 0))

    @property
    def tier4_used(self) -> int:
        """Tier 4 storage used in bytes."""
        return int(self.get("tier4_used", 0))

    @property
    def tier4_allocated(self) -> int:
        """Tier 4 storage allocated in bytes."""
        return int(self.get("tier4_allocated", 0))

    @property
    def tier4_pct(self) -> int:
        """Tier 4 storage usage percentage."""
        return int(self.get("tier4_pct", 0))

    # Storage tier metrics (Tier 5)
    @property
    def tier5_provisioned(self) -> int:
        """Tier 5 storage provisioned in bytes."""
        return int(self.get("tier5_provisioned", 0))

    @property
    def tier5_used(self) -> int:
        """Tier 5 storage used in bytes."""
        return int(self.get("tier5_used", 0))

    @property
    def tier5_allocated(self) -> int:
        """Tier 5 storage allocated in bytes."""
        return int(self.get("tier5_allocated", 0))

    @property
    def tier5_pct(self) -> int:
        """Tier 5 storage usage percentage."""
        return int(self.get("tier5_pct", 0))

    # GPU metrics
    @property
    def gpus_used(self) -> int:
        """Number of physical GPUs in use."""
        return int(self.get("gpus_used", 0))

    @property
    def gpus_total(self) -> int:
        """Total physical GPUs allocated."""
        return int(self.get("gpus_total", 0))

    @property
    def gpus_pct(self) -> int:
        """GPU usage percentage."""
        return int(self.get("gpus_pct", 0))

    @property
    def vgpus_used(self) -> int:
        """Number of vGPUs in use."""
        return int(self.get("vgpus_used", 0))

    @property
    def vgpus_total(self) -> int:
        """Total vGPUs allocated."""
        return int(self.get("vgpus_total", 0))

    @property
    def vgpus_pct(self) -> int:
        """vGPU usage percentage."""
        return int(self.get("vgpus_pct", 0))

    # Helper methods for storage totals
    def get_tier_stats(self, tier: int) -> dict[str, int]:
        """Get stats for a specific storage tier.

        Args:
            tier: Tier number (0-5).

        Returns:
            Dict with provisioned, used, allocated, and pct values.

        Raises:
            ValueError: If tier is not 0-5.
        """
        if tier < 0 or tier > 5:
            raise ValueError("Tier must be 0-5")
        return {
            "provisioned": getattr(self, f"tier{tier}_provisioned"),
            "used": getattr(self, f"tier{tier}_used"),
            "allocated": getattr(self, f"tier{tier}_allocated"),
            "pct": getattr(self, f"tier{tier}_pct", 0),
        }

    @property
    def total_storage_used(self) -> int:
        """Total storage used across all tiers in bytes."""
        return sum(getattr(self, f"tier{i}_used", 0) for i in range(6))

    @property
    def total_storage_provisioned(self) -> int:
        """Total storage provisioned across all tiers in bytes."""
        return sum(getattr(self, f"tier{i}_provisioned", 0) for i in range(6))

    @property
    def total_storage_allocated(self) -> int:
        """Total storage allocated across all tiers in bytes."""
        return sum(getattr(self, f"tier{i}_allocated", 0) for i in range(6))

    def __repr__(self) -> str:
        ts = self.timestamp.isoformat() if self.timestamp else "?"
        return (
            f"<TenantStatsHistory ts={ts} cpu={self.total_cpu}% "
            f"ram={self.ram_used_mb}MB cores={self.core_count}>"
        )


class TenantStatsManager(ResourceManager[TenantStats]):
    """Manager for tenant statistics.

    Provides access to current and historical performance metrics for a tenant.
    Scoped to a specific tenant.

    Example:
        >>> # Get current stats
        >>> stats = manager.get()
        >>> print(f"RAM: {stats.ram_used_mb}MB")

        >>> # Get short-term history (high resolution)
        >>> history = manager.history_short(limit=100)

        >>> # Get long-term history (lower resolution, longer retention)
        >>> history = manager.history_long(limit=1000)
    """

    _endpoint = "tenant_stats"

    _default_fields = [
        "$key",
        "tenant",
        "ram_used",
        "last_update",
    ]

    _history_fields = [
        "$key",
        "tenant",
        "timestamp",
        "total_cpu",
        "core_count",
        "ram_used",
        "vram_used",
        "ram_allocated",
        "ram_pct",
        "ip_count",
        "tier0_provisioned",
        "tier0_used",
        "tier0_allocated",
        "tier0_pct",
        "tier1_provisioned",
        "tier1_used",
        "tier1_allocated",
        "tier1_pct",
        "tier2_provisioned",
        "tier2_used",
        "tier2_allocated",
        "tier2_pct",
        "tier3_provisioned",
        "tier3_used",
        "tier3_allocated",
        "tier3_pct",
        "tier4_provisioned",
        "tier4_used",
        "tier4_allocated",
        "tier4_pct",
        "tier5_provisioned",
        "tier5_used",
        "tier5_allocated",
        "tier5_pct",
        "gpus_used",
        "gpus_total",
        "gpus_pct",
        "vgpus_used",
        "vgpus_total",
        "vgpus_pct",
    ]

    def __init__(self, client: VergeClient, tenant: Tenant) -> None:
        super().__init__(client)
        self._tenant = tenant
        self._tenant_key = tenant.key

    def _to_model(self, data: dict[str, Any]) -> TenantStats:
        return TenantStats(data, self)

    def _to_history_model(self, data: dict[str, Any]) -> TenantStatsHistory:
        return TenantStatsHistory(data, self)

    def get(self, fields: builtins.list[str] | None = None) -> TenantStats:  # type: ignore[override]
        """Get current tenant statistics.

        Args:
            fields: List of fields to return.

        Returns:
            TenantStats object.

        Raises:
            NotFoundError: If stats not found for this tenant.
        """
        if fields is None:
            fields = self._default_fields

        params: dict[str, Any] = {
            "filter": f"tenant eq {self._tenant_key}",
            "fields": ",".join(fields),
            "limit": 1,
        }

        response = self._client._request("GET", self._endpoint, params=params)

        if response is None:
            raise NotFoundError(f"Stats not found for tenant {self._tenant_key}")

        if isinstance(response, list):
            if not response:
                raise NotFoundError(f"Stats not found for tenant {self._tenant_key}")
            return self._to_model(response[0])

        return self._to_model(response)

    def history_short(
        self,
        limit: int | None = None,
        offset: int | None = None,
        since: datetime | int | None = None,
        until: datetime | int | None = None,
        fields: builtins.list[str] | None = None,
    ) -> builtins.list[TenantStatsHistory]:
        """Get short-term stats history (high resolution).

        Args:
            limit: Maximum number of records to return.
            offset: Skip this many records.
            since: Return records after this time (datetime or epoch).
            until: Return records before this time (datetime or epoch).
            fields: List of fields to return.

        Returns:
            List of TenantStatsHistory objects, sorted by timestamp descending.
        """
        return self._get_history(
            "tenant_stats_history_short",
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
    ) -> builtins.list[TenantStatsHistory]:
        """Get long-term stats history (lower resolution, longer retention).

        Args:
            limit: Maximum number of records to return.
            offset: Skip this many records.
            since: Return records after this time (datetime or epoch).
            until: Return records before this time (datetime or epoch).
            fields: List of fields to return.

        Returns:
            List of TenantStatsHistory objects, sorted by timestamp descending.
        """
        return self._get_history(
            "tenant_stats_history_long",
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
    ) -> builtins.list[TenantStatsHistory]:
        """Internal helper to get history from short or long endpoint."""
        if fields is None:
            fields = self._history_fields

        filters = [f"tenant eq {self._tenant_key}"]

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
# Tenant Logs
# =============================================================================


class TenantLog(ResourceObject):
    """Tenant log entry resource object."""

    @property
    def tenant_key(self) -> int:
        """Parent tenant key."""
        return int(self.get("tenant", 0))

    @property
    def tenant_name(self) -> str:
        """Parent tenant name."""
        return str(self.get("tenant_name", ""))

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
        return f"<TenantLog [{self.level}] {ts}: {text_preview!r}>"


class TenantLogManager(ResourceManager[TenantLog]):
    """Manager for tenant logs.

    Provides access to log entries for a tenant.
    Scoped to a specific tenant.

    Example:
        >>> # Get recent logs
        >>> logs = manager.list(limit=20)

        >>> # Get errors only
        >>> errors = manager.list(level="error")

        >>> # Get logs since a specific time
        >>> logs = manager.list(since=datetime.now() - timedelta(hours=1))
    """

    _endpoint = "tenant_logs"

    _default_fields = [
        "$key",
        "tenant",
        "tenant#name as tenant_name",
        "level",
        "text",
        "user",
        "timestamp",
    ]

    def __init__(self, client: VergeClient, tenant: Tenant) -> None:
        super().__init__(client)
        self._tenant = tenant
        self._tenant_key = tenant.key

    def _to_model(self, data: dict[str, Any]) -> TenantLog:
        return TenantLog(data, self)

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
    ) -> builtins.list[TenantLog]:
        """List tenant log entries.

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
            List of TenantLog objects, sorted by timestamp descending.
        """
        if fields is None:
            fields = self._default_fields

        filters = [f"tenant eq {self._tenant_key}"]

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
    ) -> TenantLog:
        """Get a specific log entry by key.

        Args:
            key: Log entry $key (ID).
            fields: List of fields to return.

        Returns:
            TenantLog object.

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


# =============================================================================
# Tenant Dashboard
# =============================================================================


class TenantDashboard(ResourceObject):
    """Tenant dashboard with aggregated metrics.

    Provides a high-level overview of tenant status and resource utilization
    across all tenants in the system.
    """

    # Tenant counts
    @property
    def tenants_count(self) -> int:
        """Total number of tenants."""
        return int(self.get("tenants_count", 0))

    @property
    def tenants_online(self) -> int:
        """Number of online tenants."""
        return int(self.get("tenants_online", 0))

    @property
    def tenants_warn(self) -> int:
        """Number of tenants in warning state."""
        return int(self.get("tenants_warn", 0))

    @property
    def tenants_error(self) -> int:
        """Number of tenants in error state."""
        return int(self.get("tenants_error", 0))

    @property
    def tenants_offline(self) -> int:
        """Number of offline tenants."""
        return self.tenants_count - self.tenants_online

    # Storage counts
    @property
    def storage_count(self) -> int:
        """Number of tenant storage allocations."""
        return int(self.get("storage_count", 0))

    # Snapshot counts
    @property
    def snapshots_count(self) -> int:
        """Number of tenant snapshots."""
        return int(self.get("snapshots_count", 0))

    @property
    def cloud_snapshots_count(self) -> int:
        """Number of cloud snapshots."""
        return int(self.get("cloud_snapshots_count", 0))

    # Node counts
    @property
    def nodes_count(self) -> int:
        """Total number of tenant nodes."""
        return int(self.get("nodes_count", 0))

    @property
    def nodes_online(self) -> int:
        """Number of online tenant nodes."""
        return int(self.get("nodes_online", 0))

    @property
    def nodes_warn(self) -> int:
        """Number of tenant nodes in warning state."""
        return int(self.get("nodes_warn", 0))

    @property
    def nodes_error(self) -> int:
        """Number of tenant nodes in error state."""
        return int(self.get("nodes_error", 0))

    # Recipe counts
    @property
    def tenant_recipes_count(self) -> int:
        """Total number of tenant recipes."""
        return int(self.get("tenant_recipes_count", 0))

    @property
    def tenant_recipes_online(self) -> int:
        """Number of online tenant recipes."""
        return int(self.get("tenant_recipes_online", 0))

    @property
    def tenant_recipes_warn(self) -> int:
        """Number of tenant recipes in warning state."""
        return int(self.get("tenant_recipes_warn", 0))

    @property
    def tenant_recipes_error(self) -> int:
        """Number of tenant recipes in error state."""
        return int(self.get("tenant_recipes_error", 0))

    # Device counts
    @property
    def devices_count(self) -> int:
        """Total number of tenant devices."""
        return int(self.get("devices_count", 0))

    @property
    def devices_online(self) -> int:
        """Number of online tenant devices."""
        return int(self.get("devices_online", 0))

    @property
    def devices_warn(self) -> int:
        """Number of tenant devices in warning state."""
        return int(self.get("devices_warn", 0))

    @property
    def devices_error(self) -> int:
        """Number of tenant devices in error state."""
        return int(self.get("devices_error", 0))

    # Top resource consumers (raw data access)
    @property
    def running_tenants_cores(self) -> builtins.list[dict[str, Any]]:
        """Top running tenants by CPU cores."""
        data = self.get("running_tenants_cores")
        return data if isinstance(data, list) else []

    @property
    def tenant_storage(self) -> builtins.list[dict[str, Any]]:
        """Top tenant storage by usage."""
        data = self.get("tenant_storage")
        return data if isinstance(data, list) else []

    @property
    def running_nodes_cpu(self) -> builtins.list[dict[str, Any]]:
        """Top tenant nodes by CPU usage."""
        data = self.get("running_nodes_cpu")
        return data if isinstance(data, list) else []

    @property
    def running_nodes_ram(self) -> builtins.list[dict[str, Any]]:
        """Top tenant nodes by RAM usage."""
        data = self.get("running_nodes_ram")
        return data if isinstance(data, list) else []

    @property
    def running_nodes_nic(self) -> builtins.list[dict[str, Any]]:
        """Top tenant nodes by network bandwidth."""
        data = self.get("running_nodes_nic")
        return data if isinstance(data, list) else []

    @property
    def logs(self) -> builtins.list[dict[str, Any]]:
        """Recent tenant-related logs."""
        data = self.get("logs")
        return data if isinstance(data, list) else []

    @property
    def tenant_snapshots(self) -> builtins.list[dict[str, Any]]:
        """Tenant snapshot information."""
        data = self.get("tenant_snapshots")
        return data if isinstance(data, list) else []

    def __repr__(self) -> str:
        return (
            f"<TenantDashboard tenants={self.tenants_online}/{self.tenants_count} "
            f"nodes={self.nodes_online}/{self.nodes_count}>"
        )


class TenantDashboardManager(ResourceManager[TenantDashboard]):
    """Manager for tenant dashboard.

    Provides aggregated tenant metrics and status counts.

    Example:
        >>> dashboard = client.tenant_dashboard.get()
        >>> print(f"Online: {dashboard.tenants_online}/{dashboard.tenants_count}")
        >>> print(f"Errors: {dashboard.tenants_error}")
    """

    _endpoint = "tenant_dashboard"

    def __init__(self, client: VergeClient) -> None:
        super().__init__(client)

    def _to_model(self, data: dict[str, Any]) -> TenantDashboard:
        return TenantDashboard(data, self)

    def get(self) -> TenantDashboard:  # type: ignore[override]
        """Get tenant dashboard.

        Returns:
            TenantDashboard object with aggregated metrics.
        """
        response = self._client._request("GET", self._endpoint)

        if response is None:
            return self._to_model({})

        if isinstance(response, list) and response:
            return self._to_model(response[0])

        if isinstance(response, dict):
            return self._to_model(response)

        return self._to_model({})
