"""Storage tier management for VergeOS vSAN."""

from __future__ import annotations

import builtins
import logging
from datetime import datetime, timezone
from typing import Any

from pyvergeos.resources.base import ResourceManager, ResourceObject

logger = logging.getLogger(__name__)


class StorageTier(ResourceObject):
    """Represents a storage tier in the VergeOS vSAN.

    Storage tiers represent different performance levels of storage.
    Tier 1 is typically the fastest (SSD/NVMe), while higher tiers
    may be slower but offer more capacity.
    """

    @property
    def tier(self) -> int:
        """Tier number (1-5)."""
        return int(self.get("tier", 0))

    @property
    def description(self) -> str:
        """Tier description."""
        return str(self.get("description", ""))

    @property
    def capacity_bytes(self) -> int:
        """Total capacity in bytes."""
        return int(self.get("capacity") or 0)

    @property
    def capacity_gb(self) -> float:
        """Total capacity in GB."""
        return round(self.capacity_bytes / 1073741824, 2) if self.capacity_bytes else 0.0

    @property
    def used_bytes(self) -> int:
        """Used space in bytes."""
        return int(self.get("used") or 0)

    @property
    def used_gb(self) -> float:
        """Used space in GB."""
        return round(self.used_bytes / 1073741824, 2) if self.used_bytes else 0.0

    @property
    def free_bytes(self) -> int:
        """Free space in bytes."""
        return max(0, self.capacity_bytes - self.used_bytes)

    @property
    def free_gb(self) -> float:
        """Free space in GB."""
        return round(self.free_bytes / 1073741824, 2) if self.free_bytes else 0.0

    @property
    def allocated_bytes(self) -> int:
        """Allocated space in bytes."""
        return int(self.get("allocated") or 0)

    @property
    def allocated_gb(self) -> float:
        """Allocated space in GB."""
        return round(self.allocated_bytes / 1073741824, 2) if self.allocated_bytes else 0.0

    @property
    def used_inflated_bytes(self) -> int:
        """Used space before deduplication in bytes."""
        return int(self.get("used_inflated") or 0)

    @property
    def used_inflated_gb(self) -> float:
        """Used space before deduplication in GB."""
        return round(self.used_inflated_bytes / 1073741824, 2) if self.used_inflated_bytes else 0.0

    @property
    def used_percent(self) -> float:
        """Percentage of capacity used."""
        if self.capacity_bytes > 0:
            return round((self.used_bytes / self.capacity_bytes) * 100, 1)
        return 0.0

    @property
    def dedupe_ratio(self) -> float:
        """Deduplication ratio (e.g., 1.5 = 50% savings)."""
        ratio = self.get("dedupe_ratio")
        if ratio:
            return round(int(ratio) / 100, 2)
        return 1.0

    @property
    def dedupe_savings_percent(self) -> float:
        """Deduplication savings as percentage."""
        if self.dedupe_ratio > 1:
            return round((1 - (1 / self.dedupe_ratio)) * 100, 1)
        return 0.0

    @property
    def modified(self) -> datetime | None:
        """Last modification timestamp."""
        ts = self.get("modified")
        if ts:
            return datetime.fromtimestamp(int(ts), tz=timezone.utc)
        return None

    # Stats properties (from nested stats object)
    @property
    def stats(self) -> dict[str, Any]:
        """Raw stats dictionary."""
        return self.get("stats") or {}

    @property
    def read_ops(self) -> int:
        """Current read operations per second."""
        return int(self.stats.get("rops") or 0)

    @property
    def write_ops(self) -> int:
        """Current write operations per second."""
        return int(self.stats.get("wops") or 0)

    @property
    def read_bytes_per_sec(self) -> int:
        """Current read throughput in bytes per second."""
        return int(self.stats.get("rbps") or 0)

    @property
    def write_bytes_per_sec(self) -> int:
        """Current write throughput in bytes per second."""
        return int(self.stats.get("wbps") or 0)

    @property
    def total_reads(self) -> int:
        """Total read operations."""
        return int(self.stats.get("reads") or 0)

    @property
    def total_writes(self) -> int:
        """Total write operations."""
        return int(self.stats.get("writes") or 0)

    @property
    def total_read_bytes(self) -> int:
        """Total bytes read."""
        return int(self.stats.get("read_bytes") or 0)

    @property
    def total_write_bytes(self) -> int:
        """Total bytes written."""
        return int(self.stats.get("write_bytes") or 0)

    def __repr__(self) -> str:
        return (
            f"<StorageTier {self.tier}: "
            f"{self.used_gb:.1f}/{self.capacity_gb:.1f} GB ({self.used_percent}%)>"
        )


class StorageTierManager(ResourceManager[StorageTier]):
    """Manages storage tier information in VergeOS.

    Storage tiers represent different levels of storage performance
    in the vSAN. Each tier has its own capacity, usage statistics,
    and I/O metrics.

    Example:
        >>> # List all storage tiers
        >>> for tier in client.storage_tiers.list():
        ...     print(f"Tier {tier.tier}: {tier.used_percent}% used")

        >>> # Get a specific tier
        >>> tier1 = client.storage_tiers.get(tier=1)
        >>> print(f"Free: {tier1.free_gb} GB")

        >>> # Check tiers with high usage
        >>> high_usage = [t for t in client.storage_tiers.list() if t.used_percent > 80]
    """

    _endpoint = "storage_tiers"

    def _to_model(self, data: dict[str, Any]) -> StorageTier:
        return StorageTier(data, self)

    def list(  # type: ignore[override]  # noqa: A003
        self,
        filter: str | None = None,  # noqa: A002
        fields: builtins.list[str] | None = None,
        include_stats: bool = True,
        **filter_kwargs: Any,
    ) -> builtins.list[StorageTier]:
        """List all storage tiers.

        Args:
            filter: OData filter string.
            fields: List of fields to return.
            include_stats: Include I/O statistics (default True).
            **filter_kwargs: Additional filter arguments.

        Returns:
            List of StorageTier objects.

        Example:
            >>> tiers = client.storage_tiers.list()
            >>> for tier in tiers:
            ...     print(f"Tier {tier.tier}: {tier.used_percent}% used, "
            ...           f"{tier.read_ops} IOPS read, {tier.write_ops} IOPS write")
        """
        if fields is None and include_stats:
            # Default fields including stats
            fields = [
                "$key",
                "tier",
                "description",
                "capacity",
                "used",
                "allocated",
                "used_inflated",
                "dedupe_ratio",
                "modified",
                "stats[reads,writes,read_bytes,write_bytes,rops,wops,rbps,wbps]",
            ]

        return super().list(filter=filter, fields=fields, **filter_kwargs)

    def get(  # type: ignore[override]
        self,
        key: int | None = None,
        *,
        tier: int | None = None,
        fields: builtins.list[str] | None = None,
    ) -> StorageTier:
        """Get a storage tier by key or tier number.

        Args:
            key: Storage tier $key.
            tier: Tier number (1-5) - alternative to key.
            fields: List of fields to return.

        Returns:
            StorageTier object.

        Raises:
            NotFoundError: If tier not found.
            ValueError: If neither key nor tier provided.

        Example:
            >>> tier1 = client.storage_tiers.get(tier=1)
            >>> print(f"Tier 1 has {tier1.free_gb} GB free")
        """
        if key is not None:
            return super().get(key, fields=fields)

        if tier is not None:
            # Search by tier number
            results = self.list(filter=f"tier eq {tier}", fields=fields)
            if not results:
                from pyvergeos.exceptions import NotFoundError

                raise NotFoundError(f"Storage tier {tier} not found")
            return results[0]

        raise ValueError("Either key or tier must be provided")

    def get_summary(self) -> dict[str, Any]:
        """Get a summary of all storage tiers.

        Returns:
            Dictionary with aggregate storage information.

        Example:
            >>> summary = client.storage_tiers.get_summary()
            >>> print(f"Total: {summary['total_capacity_gb']} GB")
            >>> print(f"Used: {summary['total_used_gb']} GB ({summary['used_percent']}%)")
        """
        tiers = self.list()

        total_capacity = sum(t.capacity_bytes for t in tiers)
        total_used = sum(t.used_bytes for t in tiers)
        total_allocated = sum(t.allocated_bytes for t in tiers)
        total_free = sum(t.free_bytes for t in tiers)

        return {
            "tier_count": len(tiers),
            "total_capacity_bytes": total_capacity,
            "total_capacity_gb": round(total_capacity / 1073741824, 2),
            "total_used_bytes": total_used,
            "total_used_gb": round(total_used / 1073741824, 2),
            "total_allocated_bytes": total_allocated,
            "total_allocated_gb": round(total_allocated / 1073741824, 2),
            "total_free_bytes": total_free,
            "total_free_gb": round(total_free / 1073741824, 2),
            "used_percent": round((total_used / total_capacity) * 100, 1) if total_capacity else 0,
            "tiers": {t.tier: {"used_percent": t.used_percent, "free_gb": t.free_gb} for t in tiers},
        }
