"""Cluster resource manager."""

from __future__ import annotations

import builtins
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from pyvergeos.resources.base import ResourceManager, ResourceObject

if TYPE_CHECKING:
    from pyvergeos.client import VergeClient


# Status display mappings
STATUS_DISPLAY = {
    "online": "Online",
    "offline": "Offline",
    "maintenance": "Maintenance",
    "reduced": "Reduced Capacity",
    "noredundant": "No Redundancy",
    "error": "Error",
    "updating": "Updating",
    "shutdown": "Shutting Down",
    "insufficient": "Insufficient Nodes",
}

STATE_DISPLAY = {
    "online": "Online",
    "offline": "Offline",
    "warning": "Warning",
    "error": "Error",
}

HEALTH_STATUS = {
    "online": "Healthy",
    "warning": "Degraded",
    "error": "Critical",
    "offline": "Offline",
}


class Cluster(ResourceObject):
    """Cluster resource object."""

    @property
    def name(self) -> str:
        """Cluster name."""
        return str(self.get("name", ""))

    @property
    def description(self) -> str:
        """Cluster description."""
        return str(self.get("description", ""))

    @property
    def is_enabled(self) -> bool:
        """Check if cluster is enabled."""
        return bool(self.get("enabled", False))

    @property
    def is_compute(self) -> bool:
        """Check if cluster is a compute cluster."""
        return bool(self.get("compute", False))

    @property
    def is_storage(self) -> bool:
        """Check if cluster is a storage cluster."""
        return bool(self.get("storage", False))


class VSANStatus(ResourceObject):
    """Represents vSAN status for a cluster.

    Provides health status, capacity information, and resource
    utilization metrics for a VergeOS cluster's vSAN.
    """

    @property
    def cluster_name(self) -> str:
        """Cluster name."""
        return str(self.get("name", ""))

    @property
    def description(self) -> str:
        """Cluster description."""
        return str(self.get("description", ""))

    @property
    def is_enabled(self) -> bool:
        """Whether cluster is enabled."""
        return bool(self.get("enabled", False))

    @property
    def is_storage(self) -> bool:
        """Whether cluster provides storage."""
        return bool(self.get("storage", False))

    @property
    def is_compute(self) -> bool:
        """Whether cluster provides compute."""
        return bool(self.get("compute", False))

    @property
    def status(self) -> str:
        """Cluster status (Online, Offline, etc.)."""
        raw = self.get("status", "")
        return STATUS_DISPLAY.get(raw, raw)

    @property
    def status_raw(self) -> str:
        """Raw status value."""
        return str(self.get("status", ""))

    @property
    def state(self) -> str:
        """Cluster state (Online, Warning, Error, Offline)."""
        raw = self.get("state", "")
        return STATE_DISPLAY.get(raw, raw)

    @property
    def state_raw(self) -> str:
        """Raw state value."""
        return str(self.get("state", ""))

    @property
    def health_status(self) -> str:
        """Health status (Healthy, Degraded, Critical, Offline)."""
        raw = self.get("state", "")
        return HEALTH_STATUS.get(raw, "Unknown")

    @property
    def status_info(self) -> str:
        """Status information message."""
        return str(self.get("status_info", ""))

    @property
    def total_nodes(self) -> int:
        """Total number of nodes in cluster."""
        return int(self.get("total_nodes") or 0)

    @property
    def online_nodes(self) -> int:
        """Number of online nodes."""
        return int(self.get("online_nodes") or 0)

    @property
    def running_machines(self) -> int:
        """Number of running VMs."""
        return int(self.get("running_machines") or 0)

    @property
    def total_ram_mb(self) -> int:
        """Total RAM in MB."""
        return int(self.get("total_ram") or 0)

    @property
    def total_ram_gb(self) -> float:
        """Total RAM in GB."""
        return round(self.total_ram_mb / 1024, 2) if self.total_ram_mb else 0.0

    @property
    def online_ram_mb(self) -> int:
        """Online RAM in MB."""
        return int(self.get("online_ram") or 0)

    @property
    def online_ram_gb(self) -> float:
        """Online RAM in GB."""
        return round(self.online_ram_mb / 1024, 2) if self.online_ram_mb else 0.0

    @property
    def used_ram_mb(self) -> int:
        """Used RAM in MB."""
        return int(self.get("used_ram") or 0)

    @property
    def used_ram_gb(self) -> float:
        """Used RAM in GB."""
        return round(self.used_ram_mb / 1024, 2) if self.used_ram_mb else 0.0

    @property
    def ram_used_percent(self) -> float:
        """RAM usage percentage."""
        if self.online_ram_mb > 0:
            return round((self.used_ram_mb / self.online_ram_mb) * 100, 1)
        return 0.0

    @property
    def total_cores(self) -> int:
        """Total CPU cores."""
        return int(self.get("total_cores") or 0)

    @property
    def online_cores(self) -> int:
        """Online CPU cores."""
        return int(self.get("online_cores") or 0)

    @property
    def used_cores(self) -> int:
        """Used CPU cores."""
        return int(self.get("used_cores") or 0)

    @property
    def core_used_percent(self) -> float:
        """CPU core usage percentage."""
        if self.online_cores > 0:
            return round((self.used_cores / self.online_cores) * 100, 1)
        return 0.0

    @property
    def last_update(self) -> datetime | None:
        """Last status update timestamp."""
        ts = self.get("last_update")
        if ts:
            return datetime.fromtimestamp(int(ts), tz=timezone.utc)
        return None

    @property
    def tiers(self) -> builtins.list[dict[str, Any]]:
        """Tier status information (if include_tiers=True)."""
        raw_tiers = self.get("tiers") or []
        result = []
        for tier in raw_tiers:
            used = tier.get("used") or 0
            capacity = tier.get("capacity") or 0
            used_gb = round(used / 1073741824, 2) if used else 0
            capacity_gb = round(capacity / 1073741824, 2) if capacity else 0
            used_pct = round((used / capacity) * 100, 1) if capacity else 0

            result.append({
                "tier": tier.get("tier"),
                "status": tier.get("status"),
                "used_gb": used_gb,
                "capacity_gb": capacity_gb,
                "used_percent": used_pct,
                "read_ops": tier.get("read_ops") or 0,
                "write_ops": tier.get("write_ops") or 0,
                "read_bps": tier.get("read_bps") or 0,
                "write_bps": tier.get("write_bps") or 0,
            })
        return result

    def __repr__(self) -> str:
        return (
            f"<VSANStatus cluster={self.cluster_name!r} "
            f"health={self.health_status} nodes={self.online_nodes}/{self.total_nodes}>"
        )


class ClusterManager(ResourceManager[Cluster]):
    """Manager for Cluster operations.

    Example:
        >>> clusters = client.clusters.list()
        >>> for cluster in clusters:
        ...     print(f"{cluster.name}: compute={cluster.is_compute}")

        >>> # Get vSAN status for all clusters
        >>> status_list = client.clusters.vsan_status()
        >>> for status in status_list:
        ...     print(f"{status.cluster_name}: {status.health_status}")
    """

    _endpoint = "clusters"

    def __init__(self, client: VergeClient) -> None:
        super().__init__(client)

    def _to_model(self, data: dict[str, Any]) -> Cluster:
        return Cluster(data, self)

    def vsan_status(
        self,
        cluster_name: str | None = None,
        include_tiers: bool = False,
    ) -> builtins.list[VSANStatus]:
        """Get vSAN health status for clusters.

        Args:
            cluster_name: Filter by specific cluster name.
            include_tiers: Include per-tier status information.

        Returns:
            List of VSANStatus objects with health and capacity info.

        Example:
            >>> status_list = client.clusters.vsan_status()
            >>> for status in status_list:
            ...     print(f"{status.cluster_name}: {status.health_status}")
            ...     print(f"  RAM: {status.used_ram_gb}/{status.online_ram_gb} GB")
            ...     print(f"  Cores: {status.used_cores}/{status.online_cores}")

            >>> # With tier information
            >>> status_list = client.clusters.vsan_status(include_tiers=True)
            >>> for status in status_list:
            ...     for tier in status.tiers:
            ...         print(f"  Tier {tier['tier']}: {tier['used_percent']}% used")
        """
        # Build field list
        fields = [
            "$key",
            "name",
            "description",
            "enabled",
            "storage",
            "compute",
            "status#status as status",
            "status#state as state",
            "status#status_info as status_info",
            "status#total_nodes as total_nodes",
            "status#online_nodes as online_nodes",
            "status#running_machines as running_machines",
            "status#total_ram as total_ram",
            "status#online_ram as online_ram",
            "status#used_ram as used_ram",
            "status#total_cores as total_cores",
            "status#online_cores as online_cores",
            "status#used_cores as used_cores",
            "status#last_update as last_update",
        ]

        if include_tiers:
            fields.append(
                "tiers[$key,tier,status#status as status,status#used as used,"
                "status#capacity as capacity,stats#rops as read_ops,"
                "stats#wops as write_ops,stats#rbps as read_bps,stats#wbps as write_bps]"
            )

        params: dict[str, Any] = {"fields": ",".join(fields)}

        if cluster_name:
            escaped = cluster_name.replace("'", "''")
            params["filter"] = f"name eq '{escaped}'"

        response = self._client._request("GET", self._endpoint, params=params)

        if response is None:
            return []

        if not isinstance(response, list):
            response = [response]

        return [VSANStatus(item, self) for item in response if item]
