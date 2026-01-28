"""System management for VergeOS - settings, statistics, licenses, and inventory."""

from __future__ import annotations

import builtins
import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from pyvergeos.resources.base import ResourceManager, ResourceObject

if TYPE_CHECKING:
    from pyvergeos.client import VergeClient

logger = logging.getLogger(__name__)


# =============================================================================
# System Settings
# =============================================================================


class SystemSetting(ResourceObject):
    """Represents a system setting in VergeOS.

    System settings are key-value pairs that control various aspects
    of VergeOS behavior.
    """

    @property
    def key(self) -> str:  # type: ignore[override]
        """Setting key (unique identifier)."""
        return str(self.get("key", ""))

    @property
    def value(self) -> str | None:
        """Current setting value."""
        return self.get("value")

    @property
    def default_value(self) -> str | None:
        """Default setting value."""
        return self.get("default_value")

    @property
    def description(self) -> str:
        """Setting description."""
        return str(self.get("description", ""))

    @property
    def is_modified(self) -> bool:
        """Whether the setting has been modified from default."""
        return self.value != self.default_value

    def __repr__(self) -> str:
        modified = " (modified)" if self.is_modified else ""
        return f"<SystemSetting {self.key}={self.value!r}{modified}>"


class SettingsManager(ResourceManager[SystemSetting]):
    """Manages system settings in VergeOS.

    Settings control various aspects of VergeOS behavior including
    connection limits, API rate limits, UI settings, and more.

    Example:
        >>> # List all settings
        >>> for setting in client.settings.list():
        ...     print(f"{setting.key}: {setting.value}")

        >>> # Get a specific setting
        >>> setting = client.settings.get("max_connections")
        >>> print(f"Max connections: {setting.value}")

        >>> # Find modified settings
        >>> modified = [s for s in client.settings.list() if s.is_modified]
    """

    _endpoint = "settings"

    def _to_model(self, data: dict[str, Any]) -> SystemSetting:
        return SystemSetting(data, self)

    def list(  # type: ignore[override]  # noqa: A003
        self,
        filter: str | None = None,  # noqa: A002
        fields: builtins.list[str] | None = None,
        key_contains: str | None = None,
        **filter_kwargs: Any,
    ) -> builtins.list[SystemSetting]:
        """List system settings.

        Args:
            filter: OData filter string.
            fields: List of fields to return.
            key_contains: Filter settings where key contains this string.
            **filter_kwargs: Additional filter arguments.

        Returns:
            List of SystemSetting objects.

        Example:
            >>> # List all settings
            >>> settings = client.settings.list()

            >>> # List UI-related settings
            >>> ui_settings = client.settings.list(key_contains="ui_")
        """
        # Use "all" to get all available fields by default
        if fields is None:
            fields = ["all"]

        filters = []
        if filter:
            filters.append(filter)
        if key_contains:
            filters.append(f"key ct '{key_contains}'")

        combined_filter = " and ".join(filters) if filters else None

        return super().list(filter=combined_filter, fields=fields, **filter_kwargs)

    def get(  # type: ignore[override]
        self,
        key: str | None = None,
        *,
        fields: builtins.list[str] | None = None,
    ) -> SystemSetting:
        """Get a system setting by key.

        Args:
            key: Setting key name (e.g., "max_connections").
            fields: List of fields to return.

        Returns:
            SystemSetting object.

        Raises:
            NotFoundError: If setting not found.
            ValueError: If key not provided.

        Example:
            >>> setting = client.settings.get("max_connections")
            >>> print(f"Value: {setting.value}, Default: {setting.default_value}")
        """
        if key is None:
            raise ValueError("Setting key must be provided")

        # Use "all" to get all available fields by default
        if fields is None:
            fields = ["all"]

        # Settings uses 'key' as the keyfield, not $key
        params: dict[str, Any] = {
            "filter": f"key eq '{key}'",
            "fields": ",".join(fields),
        }

        response = self._client._request("GET", self._endpoint, params=params)
        if not response:
            from pyvergeos.exceptions import NotFoundError

            raise NotFoundError(f"Setting '{key}' not found")

        results = response if isinstance(response, list) else [response]
        if not results:
            from pyvergeos.exceptions import NotFoundError

            raise NotFoundError(f"Setting '{key}' not found")

        return self._to_model(results[0])


# =============================================================================
# Licenses
# =============================================================================


class License(ResourceObject):
    """Represents a license in VergeOS.

    Licenses control feature availability and system capabilities.
    """

    @property
    def name(self) -> str:
        """License name."""
        return str(self.get("name", ""))

    @property
    def description(self) -> str:
        """License description."""
        return str(self.get("description", ""))

    @property
    def features(self) -> dict[str, Any] | None:
        """License features as a dictionary."""
        features = self.get("features")
        if features is None:
            return None
        if isinstance(features, dict):
            return features
        # If it's a string (JSON), try to parse it
        if isinstance(features, str):
            import json

            try:
                return json.loads(features)  # type: ignore[no-any-return]
            except json.JSONDecodeError:
                return None
        return None

    @property
    def is_valid(self) -> bool:
        """Whether the license is currently valid."""
        now = datetime.now(timezone.utc).timestamp()

        valid_from = self.get("valid_from")
        if valid_from and now < int(valid_from):
            return False

        valid_until = self.get("valid_until")
        return not (valid_until and now > int(valid_until))

    @property
    def valid_from(self) -> datetime | None:
        """License validity start date."""
        ts = self.get("valid_from")
        if ts:
            return datetime.fromtimestamp(int(ts), tz=timezone.utc)
        return None

    @property
    def valid_until(self) -> datetime | None:
        """License validity end date."""
        ts = self.get("valid_until")
        if ts:
            return datetime.fromtimestamp(int(ts), tz=timezone.utc)
        return None

    @property
    def issued(self) -> datetime | None:
        """When the license was issued."""
        ts = self.get("issued")
        if ts:
            return datetime.fromtimestamp(int(ts), tz=timezone.utc)
        return None

    @property
    def added(self) -> datetime | None:
        """When the license was added to the system."""
        ts = self.get("added")
        if ts:
            return datetime.fromtimestamp(int(ts), tz=timezone.utc)
        return None

    @property
    def added_by(self) -> str:
        """User who added the license."""
        return str(self.get("added_by", ""))

    @property
    def allow_branding(self) -> bool:
        """Whether branding is allowed."""
        return bool(self.get("allow_branding", False))

    @property
    def auto_renewal(self) -> bool:
        """Whether auto-renewal is enabled."""
        return bool(self.get("auto_renewal", False))

    @property
    def note(self) -> str:
        """License note."""
        return str(self.get("note", ""))

    def __repr__(self) -> str:
        status = "valid" if self.is_valid else "invalid"
        return f"<License {self.name!r} ({status})>"


class LicenseManager(ResourceManager[License]):
    """Manages licenses in VergeOS.

    Licenses control which features are available and the capabilities
    of the VergeOS system.

    Example:
        >>> # List all licenses
        >>> for lic in client.licenses.list():
        ...     print(f"{lic.name}: {'valid' if lic.is_valid else 'invalid'}")

        >>> # Get license details
        >>> lic = client.licenses.get(name="Production")
        >>> print(f"Valid until: {lic.valid_until}")
    """

    _endpoint = "licenses"

    def _to_model(self, data: dict[str, Any]) -> License:
        return License(data, self)

    def list(  # type: ignore[override]  # noqa: A003
        self,
        filter: str | None = None,  # noqa: A002
        fields: builtins.list[str] | None = None,
        name: str | None = None,
        **filter_kwargs: Any,
    ) -> builtins.list[License]:
        """List licenses.

        Args:
            filter: OData filter string.
            fields: List of fields to return.
            name: Filter by license name (supports wildcards).
            **filter_kwargs: Additional filter arguments.

        Returns:
            List of License objects.

        Example:
            >>> # List all licenses
            >>> licenses = client.licenses.list()

            >>> # Filter by name
            >>> prod_licenses = client.licenses.list(name="Production")
        """
        if fields is None:
            fields = [
                "$key",
                "name",
                "description",
                "added",
                "added_by",
                "issued",
                "valid_from",
                "valid_until",
                "features",
                "allow_branding",
                "auto_renewal",
                "note",
            ]

        filters = []
        if filter:
            filters.append(filter)
        if name:
            filters.append(f"name eq '{name}'")

        combined_filter = " and ".join(filters) if filters else None

        return super().list(filter=combined_filter, fields=fields, **filter_kwargs)

    def get(
        self,
        key: int | None = None,
        *,
        name: str | None = None,
        fields: builtins.list[str] | None = None,
    ) -> License:
        """Get a license by key or name.

        Args:
            key: License $key.
            name: License name - alternative to key.
            fields: List of fields to return.

        Returns:
            License object.

        Raises:
            NotFoundError: If license not found.
            ValueError: If neither key nor name provided.

        Example:
            >>> lic = client.licenses.get(name="Production")
            >>> print(f"Features: {lic.features}")
        """
        # Use default fields if not specified
        if fields is None:
            fields = [
                "$key",
                "name",
                "description",
                "added",
                "added_by",
                "issued",
                "valid_from",
                "valid_until",
                "features",
                "allow_branding",
                "auto_renewal",
                "note",
            ]

        if key is not None:
            return super().get(key, fields=fields)

        if name is not None:
            results = self.list(name=name, fields=fields)
            if not results:
                from pyvergeos.exceptions import NotFoundError

                raise NotFoundError(f"License '{name}' not found")
            return results[0]

        raise ValueError("Either key or name must be provided")


# =============================================================================
# System Statistics (Dashboard)
# =============================================================================


class SystemStatistics:
    """System dashboard statistics.

    Contains counts and status information for all major resource types.
    """

    def __init__(self, data: dict[str, Any]) -> None:
        self._data = data

    def _get_count(self, key: str) -> int:
        """Safely extract a count value."""
        value = self._data.get(key)
        if value is None:
            return 0
        if isinstance(value, int):
            return value
        if isinstance(value, dict):
            # Handle objects like {"$count": 0} or {"instances_total": 0}
            if "$count" in value:
                return int(value["$count"])
            if "instances_total" in value:
                return int(value["instances_total"])
        return 0

    # VM Statistics
    @property
    def vms_total(self) -> int:
        """Total number of VMs."""
        return self._get_count("machines_count")

    @property
    def vms_online(self) -> int:
        """Number of online VMs."""
        return self._get_count("machines_online")

    @property
    def vms_warning(self) -> int:
        """Number of VMs with warnings."""
        return self._get_count("machines_warn")

    @property
    def vms_error(self) -> int:
        """Number of VMs with errors."""
        return self._get_count("machines_error")

    # Tenant Statistics
    @property
    def tenants_total(self) -> int:
        """Total number of tenants."""
        return self._get_count("tenants_count")

    @property
    def tenants_online(self) -> int:
        """Number of online tenants."""
        return self._get_count("tenants_online")

    @property
    def tenants_warning(self) -> int:
        """Number of tenants with warnings."""
        return self._get_count("tenants_warn")

    @property
    def tenants_error(self) -> int:
        """Number of tenants with errors."""
        return self._get_count("tenants_error")

    # Network Statistics
    @property
    def networks_total(self) -> int:
        """Total number of networks."""
        return self._get_count("vnets_count")

    @property
    def networks_online(self) -> int:
        """Number of online networks."""
        return self._get_count("vnets_online")

    @property
    def networks_warning(self) -> int:
        """Number of networks with warnings."""
        return self._get_count("vnets_warn")

    @property
    def networks_error(self) -> int:
        """Number of networks with errors."""
        return self._get_count("vnets_error")

    # Node Statistics
    @property
    def nodes_total(self) -> int:
        """Total number of nodes."""
        return self._get_count("nodes_count")

    @property
    def nodes_online(self) -> int:
        """Number of online nodes."""
        return self._get_count("nodes_online")

    @property
    def nodes_warning(self) -> int:
        """Number of nodes with warnings."""
        return self._get_count("nodes_warn")

    @property
    def nodes_error(self) -> int:
        """Number of nodes with errors."""
        return self._get_count("nodes_error")

    # Cluster Statistics
    @property
    def clusters_total(self) -> int:
        """Total number of clusters."""
        return self._get_count("clusters_count")

    @property
    def clusters_online(self) -> int:
        """Number of online clusters."""
        return self._get_count("clusters_online")

    @property
    def clusters_warning(self) -> int:
        """Number of clusters with warnings."""
        return self._get_count("clusters_warn")

    @property
    def clusters_error(self) -> int:
        """Number of clusters with errors."""
        return self._get_count("clusters_error")

    # Storage Statistics
    @property
    def storage_tiers_total(self) -> int:
        """Total number of storage tiers."""
        return self._get_count("storage_tiers_count")

    @property
    def cluster_tiers_total(self) -> int:
        """Total number of cluster tiers."""
        return self._get_count("cluster_tiers_count")

    @property
    def cluster_tiers_online(self) -> int:
        """Number of online cluster tiers."""
        return self._get_count("cluster_tiers_online")

    @property
    def cluster_tiers_warning(self) -> int:
        """Number of cluster tiers with warnings."""
        return self._get_count("cluster_tiers_warn")

    @property
    def cluster_tiers_error(self) -> int:
        """Number of cluster tiers with errors."""
        return self._get_count("cluster_tiers_error")

    # User and Group Statistics
    @property
    def users_total(self) -> int:
        """Total number of users."""
        return self._get_count("users_count")

    @property
    def users_enabled(self) -> int:
        """Number of enabled users."""
        return self._get_count("users_online")

    @property
    def groups_total(self) -> int:
        """Total number of groups."""
        return self._get_count("groups_count")

    @property
    def groups_enabled(self) -> int:
        """Number of enabled groups."""
        return self._get_count("groups_online")

    # Site Statistics
    @property
    def sites_total(self) -> int:
        """Total number of sites."""
        return self._get_count("sites_count")

    @property
    def sites_online(self) -> int:
        """Number of online sites."""
        return self._get_count("sites_online")

    @property
    def sites_warning(self) -> int:
        """Number of sites with warnings."""
        return self._get_count("sites_warn")

    @property
    def sites_error(self) -> int:
        """Number of sites with errors."""
        return self._get_count("sites_error")

    # Repository Statistics
    @property
    def repositories_total(self) -> int:
        """Total number of repositories."""
        return self._get_count("repos_count")

    @property
    def repositories_online(self) -> int:
        """Number of online repositories."""
        return self._get_count("repos_online")

    @property
    def repositories_warning(self) -> int:
        """Number of repositories with warnings."""
        return self._get_count("repos_warn")

    @property
    def repositories_error(self) -> int:
        """Number of repositories with errors."""
        return self._get_count("repos_error")

    # Alarm Statistics
    @property
    def alarms_total(self) -> int:
        """Total number of active alarms."""
        return self._get_count("alarms_count")

    @property
    def alarms_warning(self) -> int:
        """Number of warning alarms."""
        return self._get_count("alarms_warning")

    @property
    def alarms_error(self) -> int:
        """Number of error/critical alarms."""
        return self._get_count("alarms_error")

    # Resource Instance Statistics
    @property
    def resource_instance_count(self) -> int:
        """Current resource instance count."""
        return self._get_count("resource_instance_count")

    @property
    def resource_instance_max(self) -> int:
        """Maximum resource instances."""
        return self._get_count("resource_instance_max")

    def to_dict(self) -> dict[str, Any]:
        """Return statistics as a dictionary."""
        return {
            "vms": {
                "total": self.vms_total,
                "online": self.vms_online,
                "warning": self.vms_warning,
                "error": self.vms_error,
            },
            "tenants": {
                "total": self.tenants_total,
                "online": self.tenants_online,
                "warning": self.tenants_warning,
                "error": self.tenants_error,
            },
            "networks": {
                "total": self.networks_total,
                "online": self.networks_online,
                "warning": self.networks_warning,
                "error": self.networks_error,
            },
            "nodes": {
                "total": self.nodes_total,
                "online": self.nodes_online,
                "warning": self.nodes_warning,
                "error": self.nodes_error,
            },
            "clusters": {
                "total": self.clusters_total,
                "online": self.clusters_online,
                "warning": self.clusters_warning,
                "error": self.clusters_error,
            },
            "storage_tiers": {
                "total": self.storage_tiers_total,
            },
            "cluster_tiers": {
                "total": self.cluster_tiers_total,
                "online": self.cluster_tiers_online,
                "warning": self.cluster_tiers_warning,
                "error": self.cluster_tiers_error,
            },
            "users": {
                "total": self.users_total,
                "enabled": self.users_enabled,
            },
            "groups": {
                "total": self.groups_total,
                "enabled": self.groups_enabled,
            },
            "sites": {
                "total": self.sites_total,
                "online": self.sites_online,
                "warning": self.sites_warning,
                "error": self.sites_error,
            },
            "repositories": {
                "total": self.repositories_total,
                "online": self.repositories_online,
                "warning": self.repositories_warning,
                "error": self.repositories_error,
            },
            "alarms": {
                "total": self.alarms_total,
                "warning": self.alarms_warning,
                "error": self.alarms_error,
            },
            "resource_instances": {
                "count": self.resource_instance_count,
                "max": self.resource_instance_max,
            },
        }

    def __repr__(self) -> str:
        return (
            f"<SystemStatistics "
            f"VMs={self.vms_online}/{self.vms_total}, "
            f"Nodes={self.nodes_online}/{self.nodes_total}, "
            f"Alarms={self.alarms_total}>"
        )


# =============================================================================
# System Inventory
# =============================================================================


class InventoryVM:
    """VM inventory item."""

    def __init__(self, data: dict[str, Any]) -> None:
        self._data = data

    @property
    def key(self) -> int:
        return int(self._data.get("$key", 0))

    @property
    def name(self) -> str:
        return str(self._data.get("name", ""))

    @property
    def description(self) -> str:
        return str(self._data.get("description", ""))

    @property
    def power_state(self) -> str:
        return str(self._data.get("power_state", ""))

    @property
    def cpu_cores(self) -> int:
        return int(self._data.get("cpu_cores", 0))

    @property
    def ram_mb(self) -> int:
        return int(self._data.get("ram", 0))

    @property
    def ram_gb(self) -> float:
        return round(self.ram_mb / 1024, 1)

    @property
    def os_family(self) -> str:
        return str(self._data.get("os_family", ""))

    @property
    def cluster(self) -> str:
        return str(self._data.get("cluster_name", ""))

    @property
    def node(self) -> str:
        return str(self._data.get("node_name", ""))


class InventoryNetwork:
    """Network inventory item."""

    def __init__(self, data: dict[str, Any]) -> None:
        self._data = data

    @property
    def key(self) -> int:
        return int(self._data.get("$key", 0))

    @property
    def name(self) -> str:
        return str(self._data.get("name", ""))

    @property
    def description(self) -> str:
        return str(self._data.get("description", ""))

    @property
    def network_type(self) -> str:
        return str(self._data.get("type", ""))

    @property
    def power_state(self) -> str:
        return str(self._data.get("power_state", ""))

    @property
    def network_address(self) -> str:
        return str(self._data.get("network", ""))

    @property
    def ip_address(self) -> str:
        return str(self._data.get("ip", ""))


class InventoryStorageTier:
    """Storage tier inventory item."""

    def __init__(self, data: dict[str, Any]) -> None:
        self._data = data

    @property
    def tier(self) -> int:
        return int(self._data.get("tier", 0))

    @property
    def description(self) -> str:
        return str(self._data.get("description", ""))

    @property
    def capacity_bytes(self) -> int:
        return int(self._data.get("capacity", 0))

    @property
    def capacity_gb(self) -> float:
        return round(self.capacity_bytes / 1073741824, 2)

    @property
    def used_bytes(self) -> int:
        return int(self._data.get("used", 0))

    @property
    def used_gb(self) -> float:
        return round(self.used_bytes / 1073741824, 2)

    @property
    def used_percent(self) -> float:
        if self.capacity_bytes > 0:
            return round((self.used_bytes / self.capacity_bytes) * 100, 1)
        return 0.0


class InventoryNode:
    """Node inventory item."""

    def __init__(self, data: dict[str, Any]) -> None:
        self._data = data

    @property
    def key(self) -> int:
        return int(self._data.get("$key", 0))

    @property
    def name(self) -> str:
        return str(self._data.get("name", ""))

    @property
    def status(self) -> str:
        return str(self._data.get("status_display", ""))

    @property
    def cluster(self) -> str:
        return str(self._data.get("cluster_name", ""))

    @property
    def cores(self) -> int:
        return int(self._data.get("cores", 0))

    @property
    def ram_mb(self) -> int:
        return int(self._data.get("ram", 0))

    @property
    def ram_gb(self) -> float:
        return round(self.ram_mb / 1024, 1)


class InventoryCluster:
    """Cluster inventory item."""

    def __init__(self, data: dict[str, Any]) -> None:
        self._data = data

    @property
    def key(self) -> int:
        return int(self._data.get("$key", 0))

    @property
    def name(self) -> str:
        return str(self._data.get("name", ""))

    @property
    def description(self) -> str:
        return str(self._data.get("description", ""))

    @property
    def status(self) -> str:
        return str(self._data.get("status_display", ""))

    @property
    def total_nodes(self) -> int:
        return int(self._data.get("total_nodes", 0))

    @property
    def online_nodes(self) -> int:
        return int(self._data.get("online_nodes", 0))


class InventoryTenant:
    """Tenant inventory item."""

    def __init__(self, data: dict[str, Any]) -> None:
        self._data = data

    @property
    def key(self) -> int:
        return int(self._data.get("$key", 0))

    @property
    def name(self) -> str:
        return str(self._data.get("name", ""))

    @property
    def description(self) -> str:
        return str(self._data.get("description", ""))

    @property
    def status(self) -> str:
        return str(self._data.get("status_display", ""))

    @property
    def is_running(self) -> bool:
        return bool(self._data.get("is_running", False))


class SystemInventory:
    """System inventory containing all resource types.

    Similar to RVtools for VMware, this provides a comprehensive
    view of all VergeOS resources.
    """

    def __init__(
        self,
        vms: builtins.list[InventoryVM],
        networks: builtins.list[InventoryNetwork],
        storage: builtins.list[InventoryStorageTier],
        nodes: builtins.list[InventoryNode],
        clusters: builtins.list[InventoryCluster],
        tenants: builtins.list[InventoryTenant],
        generated_at: datetime,
    ) -> None:
        self.vms = vms
        self.networks = networks
        self.storage = storage
        self.nodes = nodes
        self.clusters = clusters
        self.tenants = tenants
        self.generated_at = generated_at

    @property
    def summary(self) -> dict[str, Any]:
        """Get a summary of the inventory."""
        running_vms = [vm for vm in self.vms if vm.power_state == "running"]
        running_networks = [n for n in self.networks if n.power_state == "running"]
        running_tenants = [t for t in self.tenants if t.is_running]

        total_capacity_bytes = sum(s.capacity_bytes for s in self.storage)
        total_used_bytes = sum(s.used_bytes for s in self.storage)

        return {
            "generated_at": self.generated_at.isoformat(),
            "vms_total": len(self.vms),
            "vms_running": len(running_vms),
            "vms_stopped": len(self.vms) - len(running_vms),
            "total_cpu_cores": sum(vm.cpu_cores for vm in self.vms),
            "total_ram_gb": round(sum(vm.ram_gb for vm in self.vms), 1),
            "networks_total": len(self.networks),
            "networks_running": len(running_networks),
            "storage_tiers": len(self.storage),
            "storage_capacity_gb": round(total_capacity_bytes / 1073741824, 1),
            "storage_used_gb": round(total_used_bytes / 1073741824, 1),
            "nodes_total": len(self.nodes),
            "clusters_total": len(self.clusters),
            "tenants_total": len(self.tenants),
            "tenants_running": len(running_tenants),
        }

    def __repr__(self) -> str:
        return (
            f"<SystemInventory "
            f"VMs={len(self.vms)}, "
            f"Networks={len(self.networks)}, "
            f"Nodes={len(self.nodes)}, "
            f"Clusters={len(self.clusters)}, "
            f"Tenants={len(self.tenants)}>"
        )


# =============================================================================
# System Manager
# =============================================================================


class SystemManager:
    """Provides system-level operations in VergeOS.

    Includes access to settings, statistics, licenses, and inventory.

    Example:
        >>> # Get system statistics
        >>> stats = client.system.statistics()
        >>> print(f"VMs: {stats.vms_online}/{stats.vms_total}")

        >>> # Get licenses
        >>> for lic in client.system.licenses.list():
        ...     print(f"{lic.name}: {'valid' if lic.is_valid else 'invalid'}")

        >>> # Get system settings
        >>> setting = client.system.settings.get("max_connections")
        >>> print(f"Max connections: {setting.value}")

        >>> # Get full inventory
        >>> inventory = client.system.inventory()
        >>> print(inventory.summary)
    """

    def __init__(self, client: VergeClient) -> None:
        self._client = client
        self._settings: SettingsManager | None = None
        self._licenses: LicenseManager | None = None

    @property
    def settings(self) -> SettingsManager:
        """Access system settings."""
        if self._settings is None:
            self._settings = SettingsManager(self._client)
        return self._settings

    @property
    def licenses(self) -> LicenseManager:
        """Access license management."""
        if self._licenses is None:
            self._licenses = LicenseManager(self._client)
        return self._licenses

    def statistics(self) -> SystemStatistics:
        """Get system dashboard statistics.

        Returns:
            SystemStatistics object with counts for all resource types.

        Example:
            >>> stats = client.system.statistics()
            >>> print(f"Total VMs: {stats.vms_total}")
            >>> print(f"Online VMs: {stats.vms_online}")
            >>> print(f"Active Alarms: {stats.alarms_total}")
        """
        response = self._client._request("GET", "dashboard")
        if not response:
            return SystemStatistics({})

        # Response can be a dict or list with one item
        if isinstance(response, list) and len(response) > 0:
            response = response[0]

        return SystemStatistics(response if isinstance(response, dict) else {})

    def inventory(
        self,
        include_vms: bool = True,
        include_networks: bool = True,
        include_storage: bool = True,
        include_nodes: bool = True,
        include_clusters: bool = True,
        include_tenants: bool = True,
    ) -> SystemInventory:
        """Generate a comprehensive system inventory.

        Similar to RVtools for VMware, this provides a complete view
        of all VergeOS resources.

        Args:
            include_vms: Include VM inventory.
            include_networks: Include network inventory.
            include_storage: Include storage tier inventory.
            include_nodes: Include node inventory.
            include_clusters: Include cluster inventory.
            include_tenants: Include tenant inventory.

        Returns:
            SystemInventory object containing all requested resources.

        Example:
            >>> inventory = client.system.inventory()
            >>> print(f"Total VMs: {len(inventory.vms)}")
            >>> print(f"Summary: {inventory.summary}")
        """
        vms: builtins.list[InventoryVM] = []
        networks: builtins.list[InventoryNetwork] = []
        storage: builtins.list[InventoryStorageTier] = []
        nodes: builtins.list[InventoryNode] = []
        clusters: builtins.list[InventoryCluster] = []
        tenants: builtins.list[InventoryTenant] = []

        if include_vms:
            try:
                vm_response = self._client._request(
                    "GET",
                    "vms",
                    params={
                        "filter": "is_snapshot ne true",
                        "fields": (
                            "$key,name,description,cpu_cores,ram,os_family,"
                            "machine#status#status as power_state,"
                            "machine#cluster#name as cluster_name,"
                            "machine#status#node#name as node_name"
                        ),
                    },
                )
                if vm_response:
                    vm_list = vm_response if isinstance(vm_response, list) else [vm_response]
                    vms = [InventoryVM(v) for v in vm_list if v]
            except Exception as e:
                logger.warning("Failed to collect VM inventory: %s", e)

        if include_networks:
            try:
                net_response = self._client._request(
                    "GET",
                    "vnets",
                    params={
                        "fields": (
                            "$key,name,description,type,network,ip,"
                            "machine#status#status as power_state"
                        ),
                    },
                )
                if net_response:
                    net_list = net_response if isinstance(net_response, list) else [net_response]
                    networks = [InventoryNetwork(n) for n in net_list if n]
            except Exception as e:
                logger.warning("Failed to collect network inventory: %s", e)

        if include_storage:
            try:
                tier_response = self._client._request(
                    "GET",
                    "storage_tiers",
                    params={
                        "fields": "$key,tier,description,capacity,used",
                    },
                )
                if tier_response:
                    tier_list = (
                        tier_response if isinstance(tier_response, list) else [tier_response]
                    )
                    storage = [InventoryStorageTier(t) for t in tier_list if t]
            except Exception as e:
                logger.warning("Failed to collect storage inventory: %s", e)

        if include_nodes:
            try:
                node_response = self._client._request(
                    "GET",
                    "nodes",
                    params={
                        "fields": (
                            "$key,name,cores,ram,"
                            "machine#status#display(status) as status_display,"
                            "cluster#name as cluster_name"
                        ),
                    },
                )
                if node_response:
                    node_list = node_response if isinstance(node_response, list) else [node_response]
                    nodes = [InventoryNode(n) for n in node_list if n]
            except Exception as e:
                logger.warning("Failed to collect node inventory: %s", e)

        if include_clusters:
            try:
                cluster_response = self._client._request(
                    "GET",
                    "clusters",
                    params={
                        "fields": (
                            "$key,name,description,"
                            "status#total_nodes as total_nodes,"
                            "status#online_nodes as online_nodes,"
                            "status#display(status) as status_display"
                        ),
                    },
                )
                if cluster_response:
                    cluster_list = (
                        cluster_response if isinstance(cluster_response, list) else [cluster_response]
                    )
                    clusters = [InventoryCluster(c) for c in cluster_list if c]
            except Exception as e:
                logger.warning("Failed to collect cluster inventory: %s", e)

        if include_tenants:
            try:
                tenant_response = self._client._request(
                    "GET",
                    "tenants",
                    params={
                        "filter": "is_snapshot ne true",
                        "fields": (
                            "$key,name,description,"
                            "status#display(status) as status_display,"
                            "status#status eq 'running' as is_running"
                        ),
                    },
                )
                if tenant_response:
                    tenant_list = (
                        tenant_response if isinstance(tenant_response, list) else [tenant_response]
                    )
                    tenants = [InventoryTenant(t) for t in tenant_list if t]
            except Exception as e:
                logger.warning("Failed to collect tenant inventory: %s", e)

        return SystemInventory(
            vms=vms,
            networks=networks,
            storage=storage,
            nodes=nodes,
            clusters=clusters,
            tenants=tenants,
            generated_at=datetime.now(timezone.utc),
        )
