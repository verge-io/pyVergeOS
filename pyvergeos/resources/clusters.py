"""Cluster resource manager."""

from __future__ import annotations

import builtins
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Literal

from pyvergeos.exceptions import ValidationError
from pyvergeos.filters import build_filter
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

# Valid CPU types for clusters
CPU_TYPES = [
    "qemu64", "kvm64", "host",
    "Broadwell", "Cascadelake-Server", "Conroe", "Cooperlake",
    "core2duo", "coreduo", "Denverton",
    "EPYC", "EPYC-Genoa", "EPYC-Milan", "EPYC-Rome",
    "GraniteRapids", "Haswell", "Icelake-Server", "IvyBridge",
    "KnightsMill", "n270", "Nehalem",
    "Opteron_G1", "Opteron_G2", "Opteron_G3", "Opteron_G4", "Opteron_G5",
    "Penryn", "phenom", "SandyBridge", "SapphireRapids",
    "Skylake-Client", "Skylake-Server", "Snowridge", "Westmere",
]

# Energy performance policy mappings
ENERGY_PERF_POLICY_MAP = {
    "performance": "performance",
    "balance-performance": "balance-performance",
    "balance-power": "balance-power",
    "normal": "normal",
    "power": "power",
}

# Scaling governor mappings
SCALING_GOVERNOR_MAP = {
    "performance": "performance",
    "ondemand": "ondemand",
    "powersave": "powersave",
}


class Cluster(ResourceObject):
    """Cluster resource object.

    Represents a VergeOS cluster with compute and storage capabilities.

    Example:
        >>> cluster = client.clusters.get(name="Production")
        >>> print(f"{cluster.name}: {cluster.status}")
        >>> print(f"  Nodes: {cluster.online_nodes}/{cluster.total_nodes}")
        >>> print(f"  RAM: {cluster.used_ram_gb}/{cluster.online_ram_gb} GB")
    """

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

    @property
    def default_cpu(self) -> str:
        """Default CPU type for VMs in this cluster."""
        return str(self.get("default_cpu", ""))

    @property
    def recommended_cpu_type(self) -> str:
        """Recommended CPU type based on cluster hardware."""
        return str(self.get("recommended_cpu_type", ""))

    @property
    def nested_virtualization(self) -> bool:
        """Check if nested virtualization is enabled."""
        return bool(self.get("kvm_nested", False))

    @property
    def ram_per_unit(self) -> int:
        """RAM per billing unit in MB."""
        return int(self.get("ram_per_unit") or 0)

    @property
    def cores_per_unit(self) -> int:
        """CPU cores per billing unit."""
        return int(self.get("cores_per_unit") or 0)

    @property
    def max_ram_per_vm(self) -> int:
        """Maximum RAM allowed per VM in MB."""
        return int(self.get("max_ram_per_vm") or 0)

    @property
    def max_cores_per_vm(self) -> int:
        """Maximum CPU cores allowed per VM."""
        return int(self.get("max_cores_per_vm") or 0)

    @property
    def target_ram_percent(self) -> float:
        """Target maximum RAM utilization percentage."""
        return float(self.get("target_ram_pct") or 0)

    @property
    def ram_overcommit_percent(self) -> float:
        """Percentage of reserve RAM to use for machines."""
        return float(self.get("ram_overcommit_pct") or 0)

    @property
    def created_at(self) -> datetime | None:
        """Timestamp when cluster was created."""
        ts = self.get("created")
        if ts:
            return datetime.fromtimestamp(int(ts), tz=timezone.utc)
        return None

    # Status properties (from status# fields)
    @property
    def status(self) -> str:
        """Cluster status (Online, Offline, etc.)."""
        raw = str(self.get("status_state", ""))
        return STATE_DISPLAY.get(raw, raw)

    @property
    def status_raw(self) -> str:
        """Raw status value."""
        return str(self.get("status_state", ""))

    @property
    def total_nodes(self) -> int:
        """Total number of nodes in cluster."""
        return int(self.get("total_nodes") or 0)

    @property
    def online_nodes(self) -> int:
        """Number of online nodes."""
        return int(self.get("online_nodes") or 0)

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
    def cores_used_percent(self) -> float:
        """CPU core usage percentage."""
        if self.online_cores > 0:
            return round((self.used_cores / self.online_cores) * 100, 1)
        return 0.0

    @property
    def running_machines(self) -> int:
        """Number of running VMs."""
        return int(self.get("running_machines") or 0)

    def __repr__(self) -> str:
        return (
            f"<Cluster key={self.get('$key', '?')} name={self.name!r} "
            f"status={self.status} nodes={self.online_nodes}/{self.total_nodes}>"
        )


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
        raw = str(self.get("status", ""))
        return STATUS_DISPLAY.get(raw, raw)

    @property
    def status_raw(self) -> str:
        """Raw status value."""
        return str(self.get("status", ""))

    @property
    def state(self) -> str:
        """Cluster state (Online, Warning, Error, Offline)."""
        raw = str(self.get("state", ""))
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

    Provides CRUD operations for VergeOS clusters including compute and
    storage configuration.

    Example:
        >>> # List all clusters
        >>> clusters = client.clusters.list()
        >>> for cluster in clusters:
        ...     print(f"{cluster.name}: {cluster.status}")
        ...     print(f"  Nodes: {cluster.online_nodes}/{cluster.total_nodes}")

        >>> # Get a specific cluster
        >>> cluster = client.clusters.get(name="Production")

        >>> # Create a new cluster
        >>> new_cluster = client.clusters.create(
        ...     name="Development",
        ...     compute=True,
        ...     max_ram_per_vm=65536,
        ...     max_cores_per_vm=32,
        ... )

        >>> # Update cluster settings
        >>> client.clusters.update(cluster.key, max_ram_per_vm=131072)

        >>> # Get vSAN status for all clusters
        >>> status_list = client.clusters.vsan_status()
        >>> for status in status_list:
        ...     print(f"{status.cluster_name}: {status.health_status}")
    """

    _endpoint = "clusters"

    # Default fields for list operations (includes status info)
    _default_fields = [
        "$key",
        "name",
        "description",
        "enabled",
        "storage",
        "compute",
        "default_cpu",
        "recommended_cpu_type",
        "kvm_nested",
        "ram_per_unit",
        "cores_per_unit",
        "max_ram_per_vm",
        "max_cores_per_vm",
        "target_ram_pct",
        "ram_overcommit_pct",
        "created",
        "status#status as status_state",
        "status#total_nodes as total_nodes",
        "status#online_nodes as online_nodes",
        "status#total_ram as total_ram",
        "status#online_ram as online_ram",
        "status#used_ram as used_ram",
        "status#total_cores as total_cores",
        "status#online_cores as online_cores",
        "status#used_cores as used_cores",
        "status#running_machines as running_machines",
    ]

    def __init__(self, client: VergeClient) -> None:
        super().__init__(client)

    def _to_model(self, data: dict[str, Any]) -> Cluster:
        return Cluster(data, self)

    def list(
        self,
        filter: str | None = None,
        fields: builtins.list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        *,
        name: str | None = None,
        enabled: bool | None = None,
        compute: bool | None = None,
        storage: bool | None = None,
        **filter_kwargs: Any,
    ) -> builtins.list[Cluster]:
        """List clusters with optional filtering.

        Args:
            filter: OData filter string.
            fields: List of fields to return (defaults to comprehensive set).
            limit: Maximum number of results.
            offset: Skip this many results.
            name: Filter by cluster name (supports wildcards with 'ct').
            enabled: Filter by enabled status.
            compute: Filter by compute capability.
            storage: Filter by storage capability.
            **filter_kwargs: Additional filter arguments.

        Returns:
            List of Cluster objects.

        Example:
            >>> # List all clusters
            >>> clusters = client.clusters.list()

            >>> # List only compute clusters
            >>> compute_clusters = client.clusters.list(compute=True)

            >>> # List enabled clusters
            >>> enabled = client.clusters.list(enabled=True)
        """
        params: dict[str, Any] = {}

        # Build filter
        filters = []
        if filter:
            filters.append(filter)

        if name is not None:
            escaped = name.replace("'", "''")
            filters.append(f"name eq '{escaped}'")

        if enabled is not None:
            filters.append(f"enabled eq {str(enabled).lower()}")

        if compute is not None:
            filters.append(f"compute eq {str(compute).lower()}")

        if storage is not None:
            filters.append(f"storage eq {str(storage).lower()}")

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
    ) -> Cluster:
        """Get a single cluster by key or name.

        Args:
            key: Cluster $key (ID).
            name: Cluster name.
            fields: List of fields to return.

        Returns:
            Cluster object.

        Raises:
            NotFoundError: If cluster not found.
            ValueError: If neither key nor name provided.

        Example:
            >>> cluster = client.clusters.get(key=1)
            >>> cluster = client.clusters.get(name="Production")
        """
        # Use default fields if not specified
        if fields is None:
            fields = self._default_fields

        return super().get(key, name=name, fields=fields)

    def create(  # type: ignore[override]
        self,
        name: str,
        *,
        description: str | None = None,
        enabled: bool = True,
        compute: bool = False,
        nested_virtualization: bool = False,
        allow_nested_virt_migration: bool = True,
        allow_vgpu_migration: bool = False,
        default_cpu: str | None = None,
        disable_cpu_security_mitigations: bool = False,
        disable_smt: bool = False,
        enable_split_lock_detection: bool = False,
        energy_perf_policy: Literal[
            "performance", "balance-performance", "balance-power", "normal", "power"
        ] = "performance",
        scaling_governor: Literal["performance", "ondemand", "powersave"] = "performance",
        ram_per_unit: int = 4096,
        cores_per_unit: int = 1,
        cost_per_unit: float = 0,
        price_per_unit: float = 0,
        max_ram_per_vm: int = 65536,
        max_cores_per_vm: int = 16,
        target_ram_percent: float = 80,
        ram_overcommit_percent: float = 0,
        storage_cache_per_node: int | None = None,
        storage_buffer_per_node: int | None = None,
        storage_hugepages: bool = True,
        enable_nvme_power_management: bool = False,
        swap_tier: int = -1,
        swap_per_drive: int | None = None,
        max_core_temp: int | None = None,
        critical_core_temp: int | None = None,
        max_core_temp_warn_percent: int = 10,
        disable_sleep: bool = False,
        log_filter: str | None = None,
    ) -> Cluster:
        """Create a new cluster.

        Args:
            name: Cluster name (1-128 characters, must be unique).
            description: Optional description (max 2048 characters).
            enabled: Enable the cluster after creation.
            compute: Enable compute workloads on this cluster.
            nested_virtualization: Enable nested virtualization (VMs inside VMs).
            allow_nested_virt_migration: Allow live migration of VMs with nested virt.
            allow_vgpu_migration: Allow live migration of VMs with vGPU devices.
            default_cpu: Default CPU type for VMs (e.g., 'host', 'EPYC-Milan').
            disable_cpu_security_mitigations: Disable CPU security mitigations.
            disable_smt: Disable Simultaneous Multi-Threading (hyper-threading).
            enable_split_lock_detection: Enable split lock detection.
            energy_perf_policy: CPU energy-performance policy.
            scaling_governor: CPU scaling governor.
            ram_per_unit: RAM per billing unit in MB.
            cores_per_unit: CPU cores per billing unit.
            cost_per_unit: Cost per billing unit.
            price_per_unit: Price per billing unit.
            max_ram_per_vm: Maximum RAM allowed per VM in MB.
            max_cores_per_vm: Maximum CPU cores allowed per VM.
            target_ram_percent: Target maximum RAM utilization percentage (0-100).
            ram_overcommit_percent: Percentage of reserve RAM for machines (0-100).
            storage_cache_per_node: Storage cache per node in MB.
            storage_buffer_per_node: Storage buffer per node in MB.
            storage_hugepages: Allocate hugepages for storage.
            enable_nvme_power_management: Enable NVMe power management.
            swap_tier: Storage tier for swap (-1 to disable, 0-5 for tier).
            swap_per_drive: Swap space per drive in MB.
            max_core_temp: Maximum core temperature in Celsius.
            critical_core_temp: Critical core temperature in Celsius.
            max_core_temp_warn_percent: Temperature warning threshold percentage.
            disable_sleep: Disable CPU sleep states.
            log_filter: System log filter expression.

        Returns:
            Created Cluster object.

        Raises:
            ValidationError: If parameters are invalid.
            ConflictError: If cluster name already exists.

        Example:
            >>> cluster = client.clusters.create(
            ...     name="Development",
            ...     description="Development workloads",
            ...     compute=True,
            ...     max_ram_per_vm=65536,
            ...     max_cores_per_vm=32,
            ... )
        """
        # Validate name
        if not name or len(name) > 128:
            raise ValidationError("Cluster name must be 1-128 characters")

        if description and len(description) > 2048:
            raise ValidationError("Description must be max 2048 characters")

        if default_cpu and default_cpu not in CPU_TYPES:
            raise ValidationError(f"Invalid CPU type. Must be one of: {', '.join(CPU_TYPES)}")

        # Build request body
        body: dict[str, Any] = {
            "name": name,
            "enabled": enabled,
            "compute": compute,
            "kvm_nested": nested_virtualization,
            "allow_nested_virt_migration": allow_nested_virt_migration,
            "allow_vgpu_migration": allow_vgpu_migration,
            "disable_cpu_security_mitigations": disable_cpu_security_mitigations,
            "disable_smt": disable_smt,
            "enable_split_lock_detection": enable_split_lock_detection,
            "x86_energy_perf_policy": energy_perf_policy,
            "scaling_governor": scaling_governor,
            "ram_per_unit": ram_per_unit,
            "cores_per_unit": cores_per_unit,
            "cost_per_unit": cost_per_unit,
            "price_per_unit": price_per_unit,
            "max_ram_per_vm": max_ram_per_vm,
            "max_cores_per_vm": max_cores_per_vm,
            "target_ram_pct": target_ram_percent,
            "ram_overcommit_pct": ram_overcommit_percent,
            "storage_hugepages": storage_hugepages,
            "enable_nvme_power_management": enable_nvme_power_management,
            "swap_tier": swap_tier,
            "disable_sleep": disable_sleep,
            "max_core_temp_warn_perc": max_core_temp_warn_percent,
        }

        # Add optional parameters
        if description:
            body["description"] = description

        if default_cpu:
            body["default_cpu"] = default_cpu

        if storage_cache_per_node is not None:
            body["storage_cachesize"] = storage_cache_per_node

        if storage_buffer_per_node is not None:
            body["storage_buffersize"] = storage_buffer_per_node

        if swap_per_drive is not None:
            body["swap_per_drive"] = swap_per_drive

        if max_core_temp is not None:
            body["max_core_temp"] = max_core_temp

        if critical_core_temp is not None:
            body["critical_core_temp"] = critical_core_temp

        if log_filter:
            body["log_filter"] = log_filter

        response = self._client._request("POST", self._endpoint, json_data=body)
        if response is None:
            raise ValueError("No response from create operation")
        if not isinstance(response, dict):
            raise ValueError("Create operation returned invalid response")

        # Get the created cluster key and fetch full details
        cluster_key = response.get("$key") or response.get("key")
        if cluster_key:
            return self.get(int(cluster_key))

        return self._to_model(response)

    def update(  # type: ignore[override]
        self,
        key: int,
        *,
        name: str | None = None,
        description: str | None = None,
        enabled: bool | None = None,
        compute: bool | None = None,
        nested_virtualization: bool | None = None,
        allow_nested_virt_migration: bool | None = None,
        allow_vgpu_migration: bool | None = None,
        default_cpu: str | None = None,
        disable_cpu_security_mitigations: bool | None = None,
        disable_smt: bool | None = None,
        enable_split_lock_detection: bool | None = None,
        energy_perf_policy: Literal[
            "performance", "balance-performance", "balance-power", "normal", "power"
        ] | None = None,
        scaling_governor: Literal["performance", "ondemand", "powersave"] | None = None,
        ram_per_unit: int | None = None,
        cores_per_unit: int | None = None,
        cost_per_unit: float | None = None,
        price_per_unit: float | None = None,
        max_ram_per_vm: int | None = None,
        max_cores_per_vm: int | None = None,
        target_ram_percent: float | None = None,
        ram_overcommit_percent: float | None = None,
        storage_cache_per_node: int | None = None,
        storage_buffer_per_node: int | None = None,
        storage_hugepages: bool | None = None,
        enable_nvme_power_management: bool | None = None,
        swap_tier: int | None = None,
        swap_per_drive: int | None = None,
        max_core_temp: int | None = None,
        critical_core_temp: int | None = None,
        max_core_temp_warn_percent: int | None = None,
        disable_sleep: bool | None = None,
        log_filter: str | None = None,
    ) -> Cluster:
        """Update an existing cluster.

        Args:
            key: Cluster $key (ID).
            name: New cluster name.
            description: New description.
            enabled: Enable or disable the cluster.
            compute: Enable or disable compute workloads.
            nested_virtualization: Enable or disable nested virtualization.
            allow_nested_virt_migration: Allow live migration with nested virt.
            allow_vgpu_migration: Allow live migration with vGPU.
            default_cpu: Default CPU type for VMs.
            disable_cpu_security_mitigations: Disable CPU security mitigations.
            disable_smt: Disable Simultaneous Multi-Threading.
            enable_split_lock_detection: Enable split lock detection.
            energy_perf_policy: CPU energy-performance policy.
            scaling_governor: CPU scaling governor.
            ram_per_unit: RAM per billing unit in MB.
            cores_per_unit: CPU cores per billing unit.
            cost_per_unit: Cost per billing unit.
            price_per_unit: Price per billing unit.
            max_ram_per_vm: Maximum RAM allowed per VM in MB.
            max_cores_per_vm: Maximum CPU cores allowed per VM.
            target_ram_percent: Target maximum RAM utilization percentage.
            ram_overcommit_percent: Percentage of reserve RAM for machines.
            storage_cache_per_node: Storage cache per node in MB.
            storage_buffer_per_node: Storage buffer per node in MB.
            storage_hugepages: Allocate hugepages for storage.
            enable_nvme_power_management: Enable NVMe power management.
            swap_tier: Storage tier for swap.
            swap_per_drive: Swap space per drive in MB.
            max_core_temp: Maximum core temperature in Celsius.
            critical_core_temp: Critical core temperature in Celsius.
            max_core_temp_warn_percent: Temperature warning threshold percentage.
            disable_sleep: Disable CPU sleep states.
            log_filter: System log filter expression.

        Returns:
            Updated Cluster object.

        Example:
            >>> updated = client.clusters.update(
            ...     cluster.key,
            ...     max_ram_per_vm=131072,
            ...     max_cores_per_vm=64,
            ... )
        """
        body: dict[str, Any] = {}

        if name is not None:
            if len(name) > 128:
                raise ValidationError("Cluster name must be max 128 characters")
            body["name"] = name

        if description is not None:
            if len(description) > 2048:
                raise ValidationError("Description must be max 2048 characters")
            body["description"] = description

        if enabled is not None:
            body["enabled"] = enabled

        if compute is not None:
            body["compute"] = compute

        if nested_virtualization is not None:
            body["kvm_nested"] = nested_virtualization

        if allow_nested_virt_migration is not None:
            body["allow_nested_virt_migration"] = allow_nested_virt_migration

        if allow_vgpu_migration is not None:
            body["allow_vgpu_migration"] = allow_vgpu_migration

        if default_cpu is not None:
            if default_cpu not in CPU_TYPES:
                raise ValidationError(f"Invalid CPU type. Must be one of: {', '.join(CPU_TYPES)}")
            body["default_cpu"] = default_cpu

        if disable_cpu_security_mitigations is not None:
            body["disable_cpu_security_mitigations"] = disable_cpu_security_mitigations

        if disable_smt is not None:
            body["disable_smt"] = disable_smt

        if enable_split_lock_detection is not None:
            body["enable_split_lock_detection"] = enable_split_lock_detection

        if energy_perf_policy is not None:
            body["x86_energy_perf_policy"] = energy_perf_policy

        if scaling_governor is not None:
            body["scaling_governor"] = scaling_governor

        if ram_per_unit is not None:
            body["ram_per_unit"] = ram_per_unit

        if cores_per_unit is not None:
            body["cores_per_unit"] = cores_per_unit

        if cost_per_unit is not None:
            body["cost_per_unit"] = cost_per_unit

        if price_per_unit is not None:
            body["price_per_unit"] = price_per_unit

        if max_ram_per_vm is not None:
            body["max_ram_per_vm"] = max_ram_per_vm

        if max_cores_per_vm is not None:
            body["max_cores_per_vm"] = max_cores_per_vm

        if target_ram_percent is not None:
            body["target_ram_pct"] = target_ram_percent

        if ram_overcommit_percent is not None:
            body["ram_overcommit_pct"] = ram_overcommit_percent

        if storage_cache_per_node is not None:
            body["storage_cachesize"] = storage_cache_per_node

        if storage_buffer_per_node is not None:
            body["storage_buffersize"] = storage_buffer_per_node

        if storage_hugepages is not None:
            body["storage_hugepages"] = storage_hugepages

        if enable_nvme_power_management is not None:
            body["enable_nvme_power_management"] = enable_nvme_power_management

        if swap_tier is not None:
            body["swap_tier"] = swap_tier

        if swap_per_drive is not None:
            body["swap_per_drive"] = swap_per_drive

        if max_core_temp is not None:
            body["max_core_temp"] = max_core_temp

        if critical_core_temp is not None:
            body["critical_core_temp"] = critical_core_temp

        if max_core_temp_warn_percent is not None:
            body["max_core_temp_warn_perc"] = max_core_temp_warn_percent

        if disable_sleep is not None:
            body["disable_sleep"] = disable_sleep

        if log_filter is not None:
            body["log_filter"] = log_filter

        if not body:
            # No changes specified, just return current state
            return self.get(key)

        self._client._request("PUT", f"{self._endpoint}/{key}", json_data=body)
        return self.get(key)

    def delete(self, key: int) -> None:
        """Delete a cluster.

        Clusters cannot be deleted if they have nodes or running machines
        assigned to them. Reassign resources before deletion.

        Args:
            key: Cluster $key (ID).

        Raises:
            ValidationError: If cluster has nodes or running machines.
            NotFoundError: If cluster not found.

        Example:
            >>> client.clusters.delete(cluster.key)
        """
        # Get cluster to check for safety
        cluster = self.get(key)

        if cluster.total_nodes > 0:
            raise ValidationError(
                f"Cannot delete cluster '{cluster.name}': "
                f"Cluster has {cluster.total_nodes} node(s) assigned. "
                "Reassign nodes to another cluster first."
            )

        if cluster.running_machines > 0:
            raise ValidationError(
                f"Cannot delete cluster '{cluster.name}': "
                f"Cluster has {cluster.running_machines} running machine(s). "
                "Stop and reassign VMs first."
            )

        self._client._request("DELETE", f"{self._endpoint}/{key}")

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
