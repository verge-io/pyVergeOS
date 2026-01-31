"""Cluster Tier Management for VergeOS vSAN.

This module provides access to cluster storage tiers, their status,
performance stats, and historical metrics.

Example:
    >>> # Access tiers for a cluster
    >>> cluster = client.clusters.get(name="Production")
    >>> for tier in cluster.tiers.list():
    ...     print(f"Tier {tier.tier}: {tier.used_percent}% used")

    >>> # Get tier status
    >>> tier = cluster.tiers.get(tier=1)
    >>> status = tier.get_status()
    >>> print(f"Status: {status.status}, Redundant: {status.is_redundant}")

    >>> # Get tier stats
    >>> stats = tier.get_stats()
    >>> print(f"IOPS: {stats.read_ops} read, {stats.write_ops} write")

    >>> # Get stats history
    >>> history = tier.stats_history_short(limit=100)
    >>> for point in history:
    ...     print(f"{point.timestamp}: {point.read_ops} IOPS")
"""

from __future__ import annotations

import builtins
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from pyvergeos.exceptions import NotFoundError
from pyvergeos.filters import build_filter
from pyvergeos.resources.base import ResourceManager, ResourceObject

if TYPE_CHECKING:
    from pyvergeos.client import VergeClient


# Status display mappings
TIER_STATUS_DISPLAY = {
    "online": "Online",
    "offline": "Offline",
    "repairing": "Repairing",
    "initializing": "Initializing",
    "verifying": "Verifying",
    "noredundant": "Online - No Redundancy",
    "outofspace": "Tier Throttled (Low Space)",
}

TIER_STATE_DISPLAY = {
    "online": "Online",
    "offline": "Offline",
    "warning": "Warning",
    "error": "Error",
}


# =============================================================================
# Cluster Tier Stats History (Long-term)
# =============================================================================


class ClusterTierStatsHistoryLong(ResourceObject):
    """Long-term cluster tier stats history record.

    Contains peak and average metrics with longer retention but lower resolution.
    """

    @property
    def tier_key(self) -> int:
        """Parent tier key."""
        return int(self.get("tier", 0))

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

    # Peak metrics
    @property
    def read_ops_peak(self) -> int:
        """Peak read operations per second."""
        return int(self.get("rops_peak", 0))

    @property
    def write_ops_peak(self) -> int:
        """Peak write operations per second."""
        return int(self.get("wops_peak", 0))

    @property
    def read_bps_peak(self) -> int:
        """Peak read bytes per second."""
        return int(self.get("rbps_peak", 0))

    @property
    def write_bps_peak(self) -> int:
        """Peak write bytes per second."""
        return int(self.get("wbps_peak", 0))

    # Average metrics
    @property
    def read_ops_avg(self) -> int:
        """Average read operations per second."""
        return int(self.get("rops_avg", 0))

    @property
    def write_ops_avg(self) -> int:
        """Average write operations per second."""
        return int(self.get("wops_avg", 0))

    @property
    def read_bps_avg(self) -> int:
        """Average read bytes per second."""
        return int(self.get("rbps_avg", 0))

    @property
    def write_bps_avg(self) -> int:
        """Average write bytes per second."""
        return int(self.get("wbps_avg", 0))

    # Cumulative metrics
    @property
    def total_reads(self) -> int:
        """Total read operations."""
        return int(self.get("reads", 0))

    @property
    def total_writes(self) -> int:
        """Total write operations."""
        return int(self.get("writes", 0))

    @property
    def total_read_bytes(self) -> int:
        """Total bytes read."""
        return int(self.get("read_bytes", 0))

    @property
    def total_write_bytes(self) -> int:
        """Total bytes written."""
        return int(self.get("write_bytes", 0))

    # Capacity metrics
    @property
    def capacity_bytes(self) -> int:
        """Capacity in bytes at this point."""
        return int(self.get("capacity", 0))

    @property
    def capacity_gb(self) -> float:
        """Capacity in GB."""
        return round(self.capacity_bytes / 1073741824, 2) if self.capacity_bytes else 0.0

    @property
    def used_bytes(self) -> int:
        """Used space in bytes at this point."""
        return int(self.get("used", 0))

    @property
    def used_gb(self) -> float:
        """Used space in GB."""
        return round(self.used_bytes / 1073741824, 2) if self.used_bytes else 0.0

    @property
    def used_percent(self) -> float:
        """Usage percentage at this point."""
        if self.capacity_bytes > 0:
            return round((self.used_bytes / self.capacity_bytes) * 100, 1)
        return 0.0

    def __repr__(self) -> str:
        ts = self.timestamp.isoformat() if self.timestamp else "?"
        return (
            f"<ClusterTierStatsHistoryLong ts={ts} "
            f"rops_avg={self.read_ops_avg} wops_avg={self.write_ops_avg}>"
        )


# =============================================================================
# Cluster Tier Stats History (Short-term)
# =============================================================================


class ClusterTierStatsHistoryShort(ResourceObject):
    """Short-term cluster tier stats history record.

    Contains high-resolution metrics with shorter retention.
    """

    @property
    def tier_key(self) -> int:
        """Parent tier key."""
        return int(self.get("tier", 0))

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
    def read_ops(self) -> int:
        """Read operations per second."""
        return int(self.get("rops", 0))

    @property
    def write_ops(self) -> int:
        """Write operations per second."""
        return int(self.get("wops", 0))

    @property
    def read_bps(self) -> int:
        """Read bytes per second."""
        return int(self.get("rbps", 0))

    @property
    def write_bps(self) -> int:
        """Write bytes per second."""
        return int(self.get("wbps", 0))

    @property
    def total_reads(self) -> int:
        """Total read operations."""
        return int(self.get("reads", 0))

    @property
    def total_writes(self) -> int:
        """Total write operations."""
        return int(self.get("writes", 0))

    @property
    def total_read_bytes(self) -> int:
        """Total bytes read."""
        return int(self.get("read_bytes", 0))

    @property
    def total_write_bytes(self) -> int:
        """Total bytes written."""
        return int(self.get("write_bytes", 0))

    @property
    def capacity_bytes(self) -> int:
        """Capacity in bytes at this point."""
        return int(self.get("capacity", 0))

    @property
    def capacity_gb(self) -> float:
        """Capacity in GB."""
        return round(self.capacity_bytes / 1073741824, 2) if self.capacity_bytes else 0.0

    @property
    def used_bytes(self) -> int:
        """Used space in bytes at this point."""
        return int(self.get("used", 0))

    @property
    def used_gb(self) -> float:
        """Used space in GB."""
        return round(self.used_bytes / 1073741824, 2) if self.used_bytes else 0.0

    @property
    def used_percent(self) -> float:
        """Usage percentage at this point."""
        if self.capacity_bytes > 0:
            return round((self.used_bytes / self.capacity_bytes) * 100, 1)
        return 0.0

    def __repr__(self) -> str:
        ts = self.timestamp.isoformat() if self.timestamp else "?"
        return f"<ClusterTierStatsHistoryShort ts={ts} rops={self.read_ops} wops={self.write_ops}>"


# =============================================================================
# Cluster Tier Stats
# =============================================================================


class ClusterTierStats(ResourceObject):
    """Current cluster tier statistics.

    Provides real-time I/O performance metrics for a tier.
    """

    @property
    def tier_key(self) -> int:
        """Parent tier key."""
        return int(self.get("tier", 0))

    @property
    def read_ops(self) -> int:
        """Current read operations per second."""
        return int(self.get("rops", 0))

    @property
    def write_ops(self) -> int:
        """Current write operations per second."""
        return int(self.get("wops", 0))

    @property
    def read_bps(self) -> int:
        """Current read bytes per second."""
        return int(self.get("rbps", 0))

    @property
    def write_bps(self) -> int:
        """Current write bytes per second."""
        return int(self.get("wbps", 0))

    @property
    def read_mbps(self) -> float:
        """Current read MB per second."""
        return round(self.read_bps / 1048576, 2) if self.read_bps else 0.0

    @property
    def write_mbps(self) -> float:
        """Current write MB per second."""
        return round(self.write_bps / 1048576, 2) if self.write_bps else 0.0

    @property
    def total_reads(self) -> int:
        """Total read operations."""
        return int(self.get("reads", 0))

    @property
    def total_writes(self) -> int:
        """Total write operations."""
        return int(self.get("writes", 0))

    @property
    def total_read_bytes(self) -> int:
        """Total bytes read."""
        return int(self.get("read_bytes", 0))

    @property
    def total_write_bytes(self) -> int:
        """Total bytes written."""
        return int(self.get("write_bytes", 0))

    @property
    def last_update(self) -> datetime | None:
        """Timestamp of last update."""
        ts = self.get("last_update")
        if ts:
            return datetime.fromtimestamp(int(ts), tz=timezone.utc)
        return None

    def __repr__(self) -> str:
        return f"<ClusterTierStats tier={self.tier_key} rops={self.read_ops} wops={self.write_ops}>"


# =============================================================================
# Cluster Tier Status
# =============================================================================


class ClusterTierStatus(ResourceObject):
    """Cluster tier health and capacity status.

    Provides operational status, capacity metrics, and health indicators.
    """

    @property
    def tier_key(self) -> int:
        """Parent tier key."""
        return int(self.get("tier", 0))

    @property
    def status(self) -> str:
        """Status (Online, Offline, Repairing, etc.)."""
        raw = str(self.get("status", "offline"))
        return TIER_STATUS_DISPLAY.get(raw, raw)

    @property
    def status_raw(self) -> str:
        """Raw status value."""
        return str(self.get("status", "offline"))

    @property
    def state(self) -> str:
        """State (Online, Offline, Warning, Error)."""
        raw = str(self.get("state", "offline"))
        return TIER_STATE_DISPLAY.get(raw, raw)

    @property
    def state_raw(self) -> str:
        """Raw state value."""
        return str(self.get("state", "offline"))

    @property
    def is_online(self) -> bool:
        """Check if tier is online."""
        return self.status_raw == "online"

    @property
    def is_healthy(self) -> bool:
        """Check if tier is healthy (online state)."""
        return self.state_raw == "online"

    @property
    def is_warning(self) -> bool:
        """Check if tier is in warning state."""
        return self.state_raw == "warning"

    @property
    def is_error(self) -> bool:
        """Check if tier is in error state."""
        return self.state_raw == "error"

    @property
    def capacity_bytes(self) -> int:
        """Total capacity in bytes."""
        return int(self.get("capacity", 0))

    @property
    def capacity_gb(self) -> float:
        """Total capacity in GB."""
        return round(self.capacity_bytes / 1073741824, 2) if self.capacity_bytes else 0.0

    @property
    def capacity_tb(self) -> float:
        """Total capacity in TB."""
        return round(self.capacity_bytes / 1099511627776, 2) if self.capacity_bytes else 0.0

    @property
    def used_bytes(self) -> int:
        """Used space in bytes."""
        return int(self.get("used", 0))

    @property
    def used_gb(self) -> float:
        """Used space in GB."""
        return round(self.used_bytes / 1073741824, 2) if self.used_bytes else 0.0

    @property
    def used_tb(self) -> float:
        """Used space in TB."""
        return round(self.used_bytes / 1099511627776, 2) if self.used_bytes else 0.0

    @property
    def used_percent(self) -> float:
        """Usage percentage."""
        pct = self.get("used_pct")
        if pct is not None:
            return float(pct)
        if self.capacity_bytes > 0:
            return round((self.used_bytes / self.capacity_bytes) * 100, 1)
        return 0.0

    @property
    def free_bytes(self) -> int:
        """Free space in bytes."""
        return max(0, self.capacity_bytes - self.used_bytes)

    @property
    def free_gb(self) -> float:
        """Free space in GB."""
        return round(self.free_bytes / 1073741824, 2) if self.free_bytes else 0.0

    @property
    def is_redundant(self) -> bool:
        """Check if tier has redundancy."""
        return bool(self.get("redundant", False))

    @property
    def is_encrypted(self) -> bool:
        """Check if tier is encrypted."""
        return bool(self.get("encrypted", False))

    @property
    def is_working(self) -> bool:
        """Check if tier is actively working."""
        return bool(self.get("working", False))

    @property
    def last_walk_time_ms(self) -> int:
        """Last walk time in milliseconds."""
        return int(self.get("last_walk_time_ms", 0))

    @property
    def last_fullwalk_time_ms(self) -> int:
        """Last full walk time in milliseconds."""
        return int(self.get("last_fullwalk_time_ms", 0))

    @property
    def transaction(self) -> int:
        """Current transaction ID."""
        return int(self.get("transaction", 0))

    @property
    def repairs(self) -> int:
        """Number of repairs."""
        return int(self.get("repairs", 0))

    @property
    def bad_drives(self) -> int:
        """Number of unavailable drives."""
        return int(self.get("bad_drives", 0))

    @property
    def is_fullwalk(self) -> bool:
        """Check if full walk is in progress."""
        return bool(self.get("fullwalk", False))

    @property
    def walk_progress(self) -> float:
        """Walk progress percentage (0-100)."""
        return float(self.get("progress", 0))

    @property
    def index_unique(self) -> int:
        """Unique index count."""
        return int(self.get("index_unique", 0))

    @property
    def throttle_ms(self) -> float:
        """Current space throttle in milliseconds."""
        return float(self.get("cur_space_throttle_ms", 0))

    @property
    def is_throttled(self) -> bool:
        """Check if tier is being throttled due to low space."""
        return self.throttle_ms > 0

    @property
    def transaction_start(self) -> datetime | None:
        """Transaction start timestamp."""
        ts = self.get("transaction_start_stamp")
        if ts:
            return datetime.fromtimestamp(int(ts), tz=timezone.utc)
        return None

    @property
    def state_timestamp(self) -> datetime | None:
        """Timestamp when state last changed."""
        ts = self.get("state_timestamp")
        if ts:
            return datetime.fromtimestamp(int(ts), tz=timezone.utc)
        return None

    def __repr__(self) -> str:
        return (
            f"<ClusterTierStatus tier={self.tier_key} "
            f"status={self.status_raw} used={self.used_percent}%>"
        )


# =============================================================================
# Cluster Tier
# =============================================================================


class ClusterTier(ResourceObject):
    """Cluster storage tier resource object.

    Represents a storage tier within a specific cluster.

    Example:
        >>> tier = cluster.tiers.get(tier=1)
        >>> print(f"Tier {tier.tier}: {tier.description}")
        >>> print(f"  Status: {tier.status}, Capacity: {tier.capacity_gb} GB")
    """

    @property
    def tier(self) -> int:
        """Tier number (0-5)."""
        return int(self.get("tier", 0))

    @property
    def cluster_key(self) -> int:
        """Parent cluster key."""
        return int(self.get("cluster", 0))

    @property
    def description(self) -> str:
        """Tier description."""
        return str(self.get("description", ""))

    @property
    def cost_per_gb(self) -> float:
        """Cost per GB."""
        return float(self.get("cost_per_gb", 0))

    @property
    def price_per_gb(self) -> float:
        """Price per GB."""
        return float(self.get("price_per_gb", 0))

    # Embedded status properties (from list view)
    @property
    def status(self) -> str:
        """Status from embedded status field."""
        raw = str(self.get("display_status") or self.get("status_status", "offline"))
        return TIER_STATUS_DISPLAY.get(raw, raw)

    @property
    def status_raw(self) -> str:
        """Raw status value."""
        return str(self.get("display_status") or self.get("status_status", "offline"))

    @property
    def capacity_bytes(self) -> int:
        """Total capacity in bytes."""
        return int(self.get("capacity") or self.get("status_capacity", 0))

    @property
    def capacity_gb(self) -> float:
        """Total capacity in GB."""
        return round(self.capacity_bytes / 1073741824, 2) if self.capacity_bytes else 0.0

    @property
    def capacity_tb(self) -> float:
        """Total capacity in TB."""
        return round(self.capacity_bytes / 1099511627776, 2) if self.capacity_bytes else 0.0

    @property
    def used_bytes(self) -> int:
        """Used space in bytes."""
        return int(self.get("used") or self.get("status_used", 0))

    @property
    def used_gb(self) -> float:
        """Used space in GB."""
        return round(self.used_bytes / 1073741824, 2) if self.used_bytes else 0.0

    @property
    def used_tb(self) -> float:
        """Used space in TB."""
        return round(self.used_bytes / 1099511627776, 2) if self.used_bytes else 0.0

    @property
    def used_percent(self) -> float:
        """Usage percentage."""
        pct = self.get("used_pct") or self.get("status_used_pct")
        if pct is not None:
            return float(pct)
        if self.capacity_bytes > 0:
            return round((self.used_bytes / self.capacity_bytes) * 100, 1)
        return 0.0

    @property
    def free_bytes(self) -> int:
        """Free space in bytes."""
        return max(0, self.capacity_bytes - self.used_bytes)

    @property
    def free_gb(self) -> float:
        """Free space in GB."""
        return round(self.free_bytes / 1073741824, 2) if self.free_bytes else 0.0

    @property
    def is_redundant(self) -> bool:
        """Check if tier has redundancy."""
        return bool(self.get("redundant") or self.get("status_redundant", False))

    @property
    def is_working(self) -> bool:
        """Check if tier is actively working."""
        return bool(self.get("working") or self.get("status_working", False))

    @property
    def is_encrypted(self) -> bool:
        """Check if tier is encrypted."""
        return bool(self.get("encrypted") or self.get("status_encrypted", False))

    # Embedded stats properties (from list view)
    @property
    def read_ops(self) -> int:
        """Current read operations per second."""
        return int(self.get("rops") or self.get("stats_rops", 0))

    @property
    def write_ops(self) -> int:
        """Current write operations per second."""
        return int(self.get("wops") or self.get("stats_wops", 0))

    @property
    def read_bps(self) -> int:
        """Current read bytes per second."""
        return int(self.get("rbps") or self.get("stats_rbps", 0))

    @property
    def write_bps(self) -> int:
        """Current write bytes per second."""
        return int(self.get("wbps") or self.get("stats_wbps", 0))

    def get_status(self) -> ClusterTierStatus:
        """Get detailed tier status.

        Returns:
            ClusterTierStatus object with full status information.
        """
        from typing import cast

        manager = cast("ClusterTierManager", self._manager)
        return manager.get_tier_status(self.key)

    def get_stats(self) -> ClusterTierStats:
        """Get current tier statistics.

        Returns:
            ClusterTierStats object with current I/O metrics.
        """
        from typing import cast

        manager = cast("ClusterTierManager", self._manager)
        return manager.get_tier_stats(self.key)

    def stats_history_short(
        self,
        limit: int | None = None,
        offset: int | None = None,
        since: datetime | int | None = None,
        until: datetime | int | None = None,
    ) -> builtins.list[ClusterTierStatsHistoryShort]:
        """Get short-term stats history (high resolution).

        Args:
            limit: Maximum number of records.
            offset: Skip this many records.
            since: Return records after this time.
            until: Return records before this time.

        Returns:
            List of ClusterTierStatsHistoryShort objects.
        """
        from typing import cast

        manager = cast("ClusterTierManager", self._manager)
        return manager.get_stats_history_short(
            self.key, limit=limit, offset=offset, since=since, until=until
        )

    def stats_history_long(
        self,
        limit: int | None = None,
        offset: int | None = None,
        since: datetime | int | None = None,
        until: datetime | int | None = None,
    ) -> builtins.list[ClusterTierStatsHistoryLong]:
        """Get long-term stats history (lower resolution, longer retention).

        Args:
            limit: Maximum number of records.
            offset: Skip this many records.
            since: Return records after this time.
            until: Return records before this time.

        Returns:
            List of ClusterTierStatsHistoryLong objects.
        """
        from typing import cast

        manager = cast("ClusterTierManager", self._manager)
        return manager.get_stats_history_long(
            self.key, limit=limit, offset=offset, since=since, until=until
        )

    def __repr__(self) -> str:
        return (
            f"<ClusterTier tier={self.tier} cluster={self.cluster_key} "
            f"{self.used_gb:.1f}/{self.capacity_gb:.1f} GB ({self.used_percent}%)>"
        )


# =============================================================================
# Cluster Tier Manager
# =============================================================================


class ClusterTierManager(ResourceManager[ClusterTier]):
    """Manager for cluster tier operations.

    Provides access to storage tiers within a specific cluster, including
    status, statistics, and historical metrics.

    Scoped to a specific cluster.

    Example:
        >>> # Access via cluster object
        >>> cluster = client.clusters.get(name="Production")
        >>> for tier in cluster.tiers.list():
        ...     print(f"Tier {tier.tier}: {tier.used_percent}% used")

        >>> # Get specific tier
        >>> tier = cluster.tiers.get(tier=1)

        >>> # Get tier status
        >>> status = cluster.tiers.get_tier_status(tier.key)
        >>> print(f"Status: {status.status}")

        >>> # Get tier stats
        >>> stats = cluster.tiers.get_tier_stats(tier.key)
        >>> print(f"IOPS: {stats.read_ops} read, {stats.write_ops} write")
    """

    _endpoint = "cluster_tiers"

    _default_fields = [
        "$key",
        "tier",
        "cluster",
        "description",
        "cost_per_gb",
        "price_per_gb",
        "status#status as display_status",
        "status#state as display_state",
        "status#capacity as capacity",
        "status#used as used",
        "status#used_pct as used_pct",
        "status#redundant as redundant",
        "status#encrypted as encrypted",
        "status#working as working",
        "stats#rops as rops",
        "stats#wops as wops",
        "stats#rbps as rbps",
        "stats#wbps as wbps",
    ]

    _status_fields = [
        "$key",
        "tier",
        "status",
        "state",
        "capacity",
        "used",
        "used_pct",
        "redundant",
        "encrypted",
        "working",
        "last_walk_time_ms",
        "last_fullwalk_time_ms",
        "transaction",
        "repairs",
        "bad_drives",
        "fullwalk",
        "progress",
        "index_unique",
        "state_timestamp",
        "cur_space_throttle_ms",
        "transaction_start_stamp",
    ]

    _stats_fields = [
        "$key",
        "tier",
        "rops",
        "wops",
        "rbps",
        "wbps",
        "reads",
        "writes",
        "read_bytes",
        "write_bytes",
        "last_update",
    ]

    _history_short_fields = [
        "$key",
        "tier",
        "timestamp",
        "rops",
        "wops",
        "rbps",
        "wbps",
        "reads",
        "writes",
        "read_bytes",
        "write_bytes",
        "capacity",
        "used",
    ]

    _history_long_fields = [
        "$key",
        "tier",
        "timestamp",
        "rops_peak",
        "wops_peak",
        "rbps_peak",
        "wbps_peak",
        "rops_avg",
        "wops_avg",
        "rbps_avg",
        "wbps_avg",
        "reads",
        "writes",
        "read_bytes",
        "write_bytes",
        "capacity",
        "used",
    ]

    def __init__(self, client: VergeClient, cluster_key: int) -> None:
        super().__init__(client)
        self._cluster_key = cluster_key

    def _to_model(self, data: dict[str, Any]) -> ClusterTier:
        return ClusterTier(data, self)

    def list(
        self,
        filter: str | None = None,  # noqa: A002
        fields: builtins.list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        *,
        tier: int | None = None,
        **filter_kwargs: Any,
    ) -> builtins.list[ClusterTier]:
        """List cluster tiers.

        Args:
            filter: OData filter string.
            fields: List of fields to return.
            limit: Maximum number of results.
            offset: Skip this many results.
            tier: Filter by tier number (0-5).
            **filter_kwargs: Additional filter arguments.

        Returns:
            List of ClusterTier objects.

        Example:
            >>> # List all tiers for this cluster
            >>> for tier in cluster.tiers.list():
            ...     print(f"Tier {tier.tier}: {tier.used_percent}% used")
        """
        params: dict[str, Any] = {}

        # Build filter scoped to this cluster
        filters = [f"cluster eq {self._cluster_key}"]

        if filter:
            filters.append(filter)

        if tier is not None:
            filters.append(f"tier eq {tier}")

        if filter_kwargs:
            filters.append(build_filter(**filter_kwargs))

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

        # Sort by tier number
        params["sort"] = "tier"

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
        tier: int | None = None,
        fields: builtins.list[str] | None = None,
    ) -> ClusterTier:
        """Get a cluster tier by key or tier number.

        Args:
            key: Tier $key.
            tier: Tier number (0-5) - alternative to key.
            fields: List of fields to return.

        Returns:
            ClusterTier object.

        Raises:
            NotFoundError: If tier not found.
            ValueError: If neither key nor tier provided.

        Example:
            >>> tier1 = cluster.tiers.get(tier=1)
            >>> print(f"Tier 1: {tier1.used_gb} GB used")
        """
        if key is not None:
            # Get by key
            if fields is None:
                fields = self._default_fields

            params: dict[str, Any] = {"fields": ",".join(fields)}
            response = self._client._request("GET", f"{self._endpoint}/{key}", params=params)

            if response is None:
                raise NotFoundError(f"Tier {key} not found")

            if not isinstance(response, dict):
                raise NotFoundError(f"Tier {key} returned invalid response")

            return self._to_model(response)

        if tier is not None:
            # Search by tier number within this cluster
            results = self.list(tier=tier, fields=fields)
            if not results:
                raise NotFoundError(f"Tier {tier} not found in cluster {self._cluster_key}")
            return results[0]

        raise ValueError("Either key or tier must be provided")

    def get_tier_status(self, tier_key: int) -> ClusterTierStatus:
        """Get detailed status for a tier.

        Args:
            tier_key: Tier $key.

        Returns:
            ClusterTierStatus object.

        Raises:
            NotFoundError: If status not found.
        """
        params: dict[str, Any] = {
            "filter": f"tier eq {tier_key}",
            "fields": ",".join(self._status_fields),
            "limit": 1,
        }

        response = self._client._request("GET", "cluster_tier_status", params=params)

        if response is None:
            raise NotFoundError(f"Status not found for tier {tier_key}")

        if isinstance(response, list):
            if not response:
                raise NotFoundError(f"Status not found for tier {tier_key}")
            return ClusterTierStatus(response[0], self)

        return ClusterTierStatus(response, self)

    def get_tier_stats(self, tier_key: int) -> ClusterTierStats:
        """Get current statistics for a tier.

        Args:
            tier_key: Tier $key.

        Returns:
            ClusterTierStats object.

        Raises:
            NotFoundError: If stats not found.
        """
        params: dict[str, Any] = {
            "filter": f"tier eq {tier_key}",
            "fields": ",".join(self._stats_fields),
            "limit": 1,
        }

        response = self._client._request("GET", "cluster_tier_stats", params=params)

        if response is None:
            raise NotFoundError(f"Stats not found for tier {tier_key}")

        if isinstance(response, list):
            if not response:
                raise NotFoundError(f"Stats not found for tier {tier_key}")
            return ClusterTierStats(response[0], self)

        return ClusterTierStats(response, self)

    def get_stats_history_short(
        self,
        tier_key: int,
        limit: int | None = None,
        offset: int | None = None,
        since: datetime | int | None = None,
        until: datetime | int | None = None,
    ) -> builtins.list[ClusterTierStatsHistoryShort]:
        """Get short-term stats history for a tier.

        Args:
            tier_key: Tier $key.
            limit: Maximum number of records.
            offset: Skip this many records.
            since: Return records after this time.
            until: Return records before this time.

        Returns:
            List of ClusterTierStatsHistoryShort objects.
        """
        filters = [f"tier eq {tier_key}"]

        # Convert datetime to epoch if needed
        if since is not None:
            since_epoch = int(since.timestamp()) if isinstance(since, datetime) else int(since)
            filters.append(f"timestamp ge {since_epoch}")

        if until is not None:
            until_epoch = int(until.timestamp()) if isinstance(until, datetime) else int(until)
            filters.append(f"timestamp le {until_epoch}")

        params: dict[str, Any] = {
            "filter": " and ".join(filters),
            "fields": ",".join(self._history_short_fields),
            "sort": "-timestamp",
        }

        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset

        response = self._client._request("GET", "cluster_tier_stats_history_short", params=params)

        if response is None:
            return []

        if isinstance(response, list):
            return [ClusterTierStatsHistoryShort(item, self) for item in response]

        return [ClusterTierStatsHistoryShort(response, self)]

    def get_stats_history_long(
        self,
        tier_key: int,
        limit: int | None = None,
        offset: int | None = None,
        since: datetime | int | None = None,
        until: datetime | int | None = None,
    ) -> builtins.list[ClusterTierStatsHistoryLong]:
        """Get long-term stats history for a tier.

        Args:
            tier_key: Tier $key.
            limit: Maximum number of records.
            offset: Skip this many records.
            since: Return records after this time.
            until: Return records before this time.

        Returns:
            List of ClusterTierStatsHistoryLong objects.
        """
        filters = [f"tier eq {tier_key}"]

        # Convert datetime to epoch if needed
        if since is not None:
            since_epoch = int(since.timestamp()) if isinstance(since, datetime) else int(since)
            filters.append(f"timestamp ge {since_epoch}")

        if until is not None:
            until_epoch = int(until.timestamp()) if isinstance(until, datetime) else int(until)
            filters.append(f"timestamp le {until_epoch}")

        params: dict[str, Any] = {
            "filter": " and ".join(filters),
            "fields": ",".join(self._history_long_fields),
            "sort": "-timestamp",
        }

        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset

        response = self._client._request("GET", "cluster_tier_stats_history_long", params=params)

        if response is None:
            return []

        if isinstance(response, list):
            return [ClusterTierStatsHistoryLong(item, self) for item in response]

        return [ClusterTierStatsHistoryLong(response, self)]

    def get_summary(self) -> dict[str, Any]:
        """Get a summary of all tiers in this cluster.

        Returns:
            Dictionary with aggregate tier information.

        Example:
            >>> summary = cluster.tiers.get_summary()
            >>> print(f"Total: {summary['total_capacity_gb']} GB")
            >>> print(f"Used: {summary['total_used_gb']} GB ({summary['used_percent']}%)")
        """
        tiers = self.list()

        total_capacity = sum(t.capacity_bytes for t in tiers)
        total_used = sum(t.used_bytes for t in tiers)
        total_free = sum(t.free_bytes for t in tiers)

        return {
            "cluster_key": self._cluster_key,
            "tier_count": len(tiers),
            "total_capacity_bytes": total_capacity,
            "total_capacity_gb": round(total_capacity / 1073741824, 2),
            "total_capacity_tb": round(total_capacity / 1099511627776, 2),
            "total_used_bytes": total_used,
            "total_used_gb": round(total_used / 1073741824, 2),
            "total_used_tb": round(total_used / 1099511627776, 2),
            "total_free_bytes": total_free,
            "total_free_gb": round(total_free / 1073741824, 2),
            "total_free_tb": round(total_free / 1099511627776, 2),
            "used_percent": round((total_used / total_capacity) * 100, 1) if total_capacity else 0,
            "tiers": {
                t.tier: {
                    "status": t.status,
                    "used_percent": t.used_percent,
                    "capacity_gb": t.capacity_gb,
                    "used_gb": t.used_gb,
                    "free_gb": t.free_gb,
                    "redundant": t.is_redundant,
                }
                for t in tiers
            },
        }
