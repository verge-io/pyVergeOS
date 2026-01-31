"""Billing resource managers for tracking resource usage and chargeback.

This module provides access to system-wide billing records and report generation
for tracking resource utilization across the VergeOS system.

Example:
    >>> # List billing records
    >>> records = client.billing.list(limit=100)
    >>> for record in records:
    ...     print(f"{record.created}: {record.used_cores} cores, {record.used_ram_gb}GB RAM")

    >>> # Get total storage usage across tiers
    >>> record = client.billing.get_latest()
    >>> print(f"Tier 0: {record.tier0_used_gb}GB / {record.tier0_total_gb}GB")

    >>> # Generate a new billing report
    >>> result = client.billing.generate()
    >>> print(f"Generated billing report: {result}")

    >>> # Get billing data for a time range
    >>> from datetime import datetime, timedelta
    >>> since = datetime.now() - timedelta(days=30)
    >>> records = client.billing.list(since=since)
"""

from __future__ import annotations

import builtins
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from pyvergeos.exceptions import NotFoundError
from pyvergeos.resources.base import ResourceManager, ResourceObject

if TYPE_CHECKING:
    from pyvergeos.client import VergeClient


class BillingRecord(ResourceObject):
    """Billing record representing resource usage at a point in time.

    Billing records capture system-wide resource utilization metrics
    for billing and chargeback purposes.
    """

    # Timestamp properties
    @property
    def created(self) -> datetime | None:
        """When this billing record was created."""
        ts = self.get("created")
        if ts:
            return datetime.fromtimestamp(int(ts), tz=timezone.utc)
        return None

    @property
    def created_epoch(self) -> int:
        """Created timestamp as Unix epoch."""
        return int(self.get("created", 0))

    @property
    def from_time(self) -> datetime | None:
        """Start of the billing period."""
        ts = self.get("from")
        if ts:
            return datetime.fromtimestamp(int(ts), tz=timezone.utc)
        return None

    @property
    def from_epoch(self) -> int:
        """From timestamp as Unix epoch."""
        return int(self.get("from", 0))

    @property
    def to_time(self) -> datetime | None:
        """End of the billing period."""
        ts = self.get("to")
        if ts:
            return datetime.fromtimestamp(int(ts), tz=timezone.utc)
        return None

    @property
    def to_epoch(self) -> int:
        """To timestamp as Unix epoch."""
        return int(self.get("to", 0))

    @property
    def sent(self) -> datetime | None:
        """When this billing record was sent/reported."""
        ts = self.get("sent")
        if ts:
            return datetime.fromtimestamp(int(ts), tz=timezone.utc)
        return None

    @property
    def sent_epoch(self) -> int:
        """Sent timestamp as Unix epoch."""
        return int(self.get("sent", 0))

    # Description
    @property
    def description(self) -> str:
        """Description of the billing record."""
        return str(self.get("description", ""))

    # CPU metrics
    @property
    def used_cores(self) -> int:
        """Number of CPU cores used."""
        return int(self.get("used_cores", 0))

    @property
    def total_cores(self) -> int:
        """Total CPU cores available."""
        return int(self.get("total_cores", 0))

    @property
    def online_cores(self) -> int:
        """Number of CPU cores currently online."""
        return int(self.get("online_cores", 0))

    @property
    def phys_total_cpu(self) -> int:
        """Total physical CPU percentage."""
        return int(self.get("phys_total_cpu", 0))

    # Node metrics
    @property
    def total_nodes(self) -> int:
        """Total number of nodes."""
        return int(self.get("total_nodes", 0))

    @property
    def online_nodes(self) -> int:
        """Number of nodes currently online."""
        return int(self.get("online_nodes", 0))

    @property
    def running_machines(self) -> int:
        """Number of VMs currently running."""
        return int(self.get("running_machines", 0))

    # RAM metrics
    @property
    def used_ram(self) -> int:
        """RAM used in MB."""
        return int(self.get("used_ram", 0))

    @property
    def used_ram_gb(self) -> float:
        """RAM used in GB."""
        return self.used_ram / 1024

    @property
    def total_ram(self) -> int:
        """Total RAM available in MB."""
        return int(self.get("total_ram", 0))

    @property
    def total_ram_gb(self) -> float:
        """Total RAM available in GB."""
        return self.total_ram / 1024

    @property
    def online_ram(self) -> int:
        """RAM currently online in MB."""
        return int(self.get("online_ram", 0))

    @property
    def online_ram_gb(self) -> float:
        """RAM currently online in GB."""
        return self.online_ram / 1024

    @property
    def phys_ram_used(self) -> int:
        """Physical RAM used in bytes."""
        return int(self.get("phys_ram_used", 0))

    @property
    def phys_ram_used_gb(self) -> float:
        """Physical RAM used in GB."""
        return self.phys_ram_used / (1024 * 1024 * 1024)

    @property
    def phys_vram_used(self) -> int:
        """Physical VRAM used in bytes."""
        return int(self.get("phys_vram_used", 0))

    @property
    def phys_vram_used_gb(self) -> float:
        """Physical VRAM used in GB."""
        return self.phys_vram_used / (1024 * 1024 * 1024)

    # Storage tier 0 metrics
    @property
    def tier0_used(self) -> int:
        """Tier 0 storage used in bytes."""
        return int(self.get("tier_0_used", 0))

    @property
    def tier0_used_gb(self) -> float:
        """Tier 0 storage used in GB."""
        return self.tier0_used / (1024 * 1024 * 1024)

    @property
    def tier0_total(self) -> int:
        """Tier 0 storage total in bytes."""
        return int(self.get("tier_0_total", 0))

    @property
    def tier0_total_gb(self) -> float:
        """Tier 0 storage total in GB."""
        return self.tier0_total / (1024 * 1024 * 1024)

    # Storage tier 1 metrics
    @property
    def tier1_used(self) -> int:
        """Tier 1 storage used in bytes."""
        return int(self.get("tier_1_used", 0))

    @property
    def tier1_used_gb(self) -> float:
        """Tier 1 storage used in GB."""
        return self.tier1_used / (1024 * 1024 * 1024)

    @property
    def tier1_total(self) -> int:
        """Tier 1 storage total in bytes."""
        return int(self.get("tier_1_total", 0))

    @property
    def tier1_total_gb(self) -> float:
        """Tier 1 storage total in GB."""
        return self.tier1_total / (1024 * 1024 * 1024)

    # Storage tier 2 metrics
    @property
    def tier2_used(self) -> int:
        """Tier 2 storage used in bytes."""
        return int(self.get("tier_2_used", 0))

    @property
    def tier2_used_gb(self) -> float:
        """Tier 2 storage used in GB."""
        return self.tier2_used / (1024 * 1024 * 1024)

    @property
    def tier2_total(self) -> int:
        """Tier 2 storage total in bytes."""
        return int(self.get("tier_2_total", 0))

    @property
    def tier2_total_gb(self) -> float:
        """Tier 2 storage total in GB."""
        return self.tier2_total / (1024 * 1024 * 1024)

    # Storage tier 3 metrics
    @property
    def tier3_used(self) -> int:
        """Tier 3 storage used in bytes."""
        return int(self.get("tier_3_used", 0))

    @property
    def tier3_used_gb(self) -> float:
        """Tier 3 storage used in GB."""
        return self.tier3_used / (1024 * 1024 * 1024)

    @property
    def tier3_total(self) -> int:
        """Tier 3 storage total in bytes."""
        return int(self.get("tier_3_total", 0))

    @property
    def tier3_total_gb(self) -> float:
        """Tier 3 storage total in GB."""
        return self.tier3_total / (1024 * 1024 * 1024)

    # Storage tier 4 metrics
    @property
    def tier4_used(self) -> int:
        """Tier 4 storage used in bytes."""
        return int(self.get("tier_4_used", 0))

    @property
    def tier4_used_gb(self) -> float:
        """Tier 4 storage used in GB."""
        return self.tier4_used / (1024 * 1024 * 1024)

    @property
    def tier4_total(self) -> int:
        """Tier 4 storage total in bytes."""
        return int(self.get("tier_4_total", 0))

    @property
    def tier4_total_gb(self) -> float:
        """Tier 4 storage total in GB."""
        return self.tier4_total / (1024 * 1024 * 1024)

    # Storage tier 5 metrics
    @property
    def tier5_used(self) -> int:
        """Tier 5 storage used in bytes."""
        return int(self.get("tier_5_used", 0))

    @property
    def tier5_used_gb(self) -> float:
        """Tier 5 storage used in GB."""
        return self.tier5_used / (1024 * 1024 * 1024)

    @property
    def tier5_total(self) -> int:
        """Tier 5 storage total in bytes."""
        return int(self.get("tier_5_total", 0))

    @property
    def tier5_total_gb(self) -> float:
        """Tier 5 storage total in GB."""
        return self.tier5_total / (1024 * 1024 * 1024)

    # GPU metrics
    @property
    def gpus_total(self) -> int:
        """Total number of physical GPUs."""
        return int(self.get("gpus_total", 0))

    @property
    def gpus_used(self) -> int:
        """Number of physical GPUs in use."""
        return int(self.get("gpus", 0))

    @property
    def gpus_idle(self) -> int:
        """Number of idle physical GPUs."""
        return int(self.get("gpus_idle", 0))

    @property
    def vgpus_total(self) -> int:
        """Total number of vGPUs."""
        return int(self.get("vgpus_total", 0))

    @property
    def vgpus_used(self) -> int:
        """Number of vGPUs in use."""
        return int(self.get("vgpus", 0))

    @property
    def vgpus_idle(self) -> int:
        """Number of idle vGPUs."""
        return int(self.get("vgpus_idle", 0))

    # Data point counts
    @property
    def workload_datapoints(self) -> int:
        """Number of workload data points collected."""
        return int(self.get("workload_datapoints", 0))

    @property
    def storage_datapoints(self) -> int:
        """Number of storage data points collected."""
        return int(self.get("storage_datapoints", 0))

    # Helper methods
    def get_tier_stats(self, tier: int) -> dict[str, Any]:
        """Get stats for a specific storage tier.

        Args:
            tier: Tier number (0-5).

        Returns:
            Dict with used and total values in bytes and GB.

        Raises:
            ValueError: If tier is not 0-5.
        """
        if tier < 0 or tier > 5:
            raise ValueError("Tier must be 0-5")
        return {
            "used": getattr(self, f"tier{tier}_used"),
            "used_gb": getattr(self, f"tier{tier}_used_gb"),
            "total": getattr(self, f"tier{tier}_total"),
            "total_gb": getattr(self, f"tier{tier}_total_gb"),
        }

    @property
    def total_storage_used(self) -> int:
        """Total storage used across all tiers in bytes."""
        return sum(getattr(self, f"tier{i}_used", 0) for i in range(6))

    @property
    def total_storage_used_gb(self) -> float:
        """Total storage used across all tiers in GB."""
        return self.total_storage_used / (1024 * 1024 * 1024)

    @property
    def total_storage_total(self) -> int:
        """Total storage capacity across all tiers in bytes."""
        return sum(getattr(self, f"tier{i}_total", 0) for i in range(6))

    @property
    def total_storage_total_gb(self) -> float:
        """Total storage capacity across all tiers in GB."""
        return self.total_storage_total / (1024 * 1024 * 1024)

    @property
    def cpu_utilization_pct(self) -> float:
        """CPU utilization percentage (used_cores / total_cores)."""
        if self.total_cores == 0:
            return 0.0
        return (self.used_cores / self.total_cores) * 100

    @property
    def ram_utilization_pct(self) -> float:
        """RAM utilization percentage (used_ram / total_ram)."""
        if self.total_ram == 0:
            return 0.0
        return (self.used_ram / self.total_ram) * 100

    @property
    def gpu_utilization_pct(self) -> float:
        """GPU utilization percentage (gpus_used / gpus_total)."""
        if self.gpus_total == 0:
            return 0.0
        return (self.gpus_used / self.gpus_total) * 100

    @property
    def vgpu_utilization_pct(self) -> float:
        """vGPU utilization percentage (vgpus_used / vgpus_total)."""
        if self.vgpus_total == 0:
            return 0.0
        return (self.vgpus_used / self.vgpus_total) * 100

    def __repr__(self) -> str:
        created = self.created.isoformat() if self.created else "?"
        return (
            f"<BillingRecord created={created} "
            f"cores={self.used_cores}/{self.total_cores} "
            f"ram={self.used_ram_gb:.1f}/{self.total_ram_gb:.1f}GB>"
        )


class BillingManager(ResourceManager[BillingRecord]):
    """Manager for billing records.

    Provides access to system-wide resource usage records for billing
    and chargeback purposes. Records are automatically generated and
    stored by VergeOS.

    Example:
        >>> # List billing records
        >>> records = client.billing.list(limit=100)

        >>> # Get the latest billing record
        >>> latest = client.billing.get_latest()
        >>> print(f"CPU: {latest.cpu_utilization_pct:.1f}%")

        >>> # Get records for a specific time range
        >>> from datetime import datetime, timedelta
        >>> since = datetime.now() - timedelta(days=7)
        >>> records = client.billing.list(since=since)

        >>> # Generate a new billing report
        >>> result = client.billing.generate()
    """

    _endpoint = "billing"

    _default_fields = [
        "$key",
        "created",
        "from",
        "to",
        "sent",
        "description",
        "used_cores",
        "total_cores",
        "online_cores",
        "total_nodes",
        "online_nodes",
        "running_machines",
        "used_ram",
        "total_ram",
        "online_ram",
        "phys_ram_used",
        "phys_vram_used",
        "phys_total_cpu",
        "tier_0_used",
        "tier_0_total",
        "tier_1_used",
        "tier_1_total",
        "tier_2_used",
        "tier_2_total",
        "tier_3_used",
        "tier_3_total",
        "tier_4_used",
        "tier_4_total",
        "tier_5_used",
        "tier_5_total",
        "gpus_total",
        "gpus",
        "gpus_idle",
        "vgpus_total",
        "vgpus",
        "vgpus_idle",
        "workload_datapoints",
        "storage_datapoints",
    ]

    def __init__(self, client: VergeClient) -> None:
        super().__init__(client)

    def _to_model(self, data: dict[str, Any]) -> BillingRecord:
        return BillingRecord(data, self)

    def list(
        self,
        filter: str | None = None,  # noqa: A002
        fields: builtins.list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        *,
        since: datetime | int | None = None,
        until: datetime | int | None = None,
        **filter_kwargs: Any,
    ) -> builtins.list[BillingRecord]:
        """List billing records.

        Args:
            filter: OData filter string.
            fields: List of fields to return.
            limit: Maximum number of results.
            offset: Skip this many results.
            since: Return records created after this time (datetime or epoch).
            until: Return records created before this time (datetime or epoch).
            **filter_kwargs: Shorthand filter arguments.

        Returns:
            List of BillingRecord objects, sorted by created descending.
        """
        if fields is None:
            fields = self._default_fields

        filters = []
        if filter:
            filters.append(filter)

        # Convert datetime to epoch if needed
        if since is not None:
            since_epoch = int(since.timestamp()) if isinstance(since, datetime) else int(since)
            filters.append(f"created ge {since_epoch}")

        if until is not None:
            until_epoch = int(until.timestamp()) if isinstance(until, datetime) else int(until)
            filters.append(f"created le {until_epoch}")

        combined_filter = " and ".join(filters) if filters else None

        params: dict[str, Any] = {"sort": "-created"}
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

        if isinstance(response, list):
            return [self._to_model(item) for item in response]

        return [self._to_model(response)]

    def get(  # type: ignore[override]
        self,
        key: int | None = None,
        *,
        fields: builtins.list[str] | None = None,
    ) -> BillingRecord:
        """Get a specific billing record by key.

        Args:
            key: Billing record $key (ID).
            fields: List of fields to return.

        Returns:
            BillingRecord object.

        Raises:
            NotFoundError: If record not found.
            ValueError: If key not provided.
        """
        if key is None:
            raise ValueError("key must be provided")

        if fields is None:
            fields = self._default_fields

        params: dict[str, Any] = {"fields": ",".join(fields)}
        response = self._client._request("GET", f"{self._endpoint}/{key}", params=params)

        if response is None:
            raise NotFoundError(f"Billing record {key} not found")

        if not isinstance(response, dict):
            raise NotFoundError(f"Billing record {key} returned invalid response")

        return self._to_model(response)

    def get_latest(self, fields: builtins.list[str] | None = None) -> BillingRecord:
        """Get the most recent billing record.

        Args:
            fields: List of fields to return.

        Returns:
            Most recent BillingRecord object.

        Raises:
            NotFoundError: If no billing records exist.
        """
        records = self.list(limit=1, fields=fields)
        if not records:
            raise NotFoundError("No billing records found")
        return records[0]

    def generate(self) -> dict[str, Any] | None:
        """Generate a new billing report.

        Triggers the generation of a new billing record with current
        resource usage data.

        Returns:
            Action response from the billing_actions endpoint.

        Example:
            >>> result = client.billing.generate()
            >>> print(f"Generated billing report")
        """
        body = {"action": "generate"}
        result = self._client._request("POST", "billing_actions", json_data=body)
        return result if isinstance(result, dict) else None

    def get_summary(
        self,
        since: datetime | int | None = None,
        until: datetime | int | None = None,
    ) -> dict[str, Any]:
        """Get a summary of billing data over a time period.

        Calculates average and peak usage across all billing records
        in the specified time range.

        Args:
            since: Start of time range (datetime or epoch).
            until: End of time range (datetime or epoch).

        Returns:
            Dict with summary statistics including:
            - record_count: Number of billing records
            - avg_cpu_utilization: Average CPU utilization percentage
            - peak_cpu_cores: Peak CPU cores used
            - avg_ram_utilization: Average RAM utilization percentage
            - peak_ram_gb: Peak RAM usage in GB
            - avg_storage_used_gb: Average storage used in GB
            - peak_storage_used_gb: Peak storage used in GB
            - total_gpus: Total GPUs available
            - avg_gpus_used: Average GPUs in use
            - total_vgpus: Total vGPUs available
            - avg_vgpus_used: Average vGPUs in use
        """
        records = self.list(since=since, until=until)

        if not records:
            return {
                "record_count": 0,
                "avg_cpu_utilization": 0.0,
                "peak_cpu_cores": 0,
                "avg_ram_utilization": 0.0,
                "peak_ram_gb": 0.0,
                "avg_storage_used_gb": 0.0,
                "peak_storage_used_gb": 0.0,
                "total_gpus": 0,
                "avg_gpus_used": 0.0,
                "total_vgpus": 0,
                "avg_vgpus_used": 0.0,
            }

        cpu_utils = [r.cpu_utilization_pct for r in records]
        ram_utils = [r.ram_utilization_pct for r in records]
        storage_used = [r.total_storage_used_gb for r in records]
        cpu_cores = [r.used_cores for r in records]
        ram_gb = [r.used_ram_gb for r in records]
        gpus_used = [r.gpus_used for r in records]
        vgpus_used = [r.vgpus_used for r in records]

        return {
            "record_count": len(records),
            "avg_cpu_utilization": sum(cpu_utils) / len(cpu_utils),
            "peak_cpu_cores": max(cpu_cores),
            "avg_ram_utilization": sum(ram_utils) / len(ram_utils),
            "peak_ram_gb": max(ram_gb),
            "avg_storage_used_gb": sum(storage_used) / len(storage_used),
            "peak_storage_used_gb": max(storage_used),
            "total_gpus": records[0].gpus_total,
            "avg_gpus_used": sum(gpus_used) / len(gpus_used),
            "total_vgpus": records[0].vgpus_total,
            "avg_vgpus_used": sum(vgpus_used) / len(vgpus_used),
        }
