"""System management for VergeOS - settings, statistics, licenses, diagnostics, and inventory."""

from __future__ import annotations

import builtins
import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from pyvergeos.constants import POLL_INTERVAL, TASK_WAIT_TIMEOUT
from pyvergeos.resources.base import ResourceManager, ResourceObject

if TYPE_CHECKING:
    from pyvergeos.client import VergeClient

logger = logging.getLogger(__name__)


# Diagnostic status values
DIAG_STATUS_INITIALIZING = "initializing"
DIAG_STATUS_BUILDING = "building"
DIAG_STATUS_UPLOADING = "uploading"
DIAG_STATUS_COMPLETE = "complete"
DIAG_STATUS_ERROR = "error"

DIAG_STATUS_DISPLAY = {
    DIAG_STATUS_INITIALIZING: "Initializing",
    DIAG_STATUS_BUILDING: "Building",
    DIAG_STATUS_UPLOADING: "Sending to Support",
    DIAG_STATUS_COMPLETE: "Complete",
    DIAG_STATUS_ERROR: "Error",
}


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

    def update(  # type: ignore[override]
        self,
        key: str,
        value: str,
    ) -> SystemSetting:
        """Update a system setting value.

        Args:
            key: Setting key name (e.g., "max_connections").
            value: New value for the setting.

        Returns:
            Updated SystemSetting object.

        Raises:
            NotFoundError: If setting not found.
            ValueError: If key not provided.

        Example:
            >>> setting = client.system.settings.update("max_connections", "1000")
            >>> print(f"New value: {setting.value}")
        """
        if not key:
            raise ValueError("Setting key must be provided")

        # Settings API uses the key as the identifier in the URL
        body = {"value": value}

        # First, we need to get the setting to find its row key
        # Settings uses 'key' as the keyfield, so we filter by it
        params: dict[str, Any] = {
            "filter": f"key eq '{key}'",
            "fields": "all",
        }

        response = self._client._request("GET", self._endpoint, params=params)
        if not response:
            from pyvergeos.exceptions import NotFoundError

            raise NotFoundError(f"Setting '{key}' not found")

        results = response if isinstance(response, list) else [response]
        if not results:
            from pyvergeos.exceptions import NotFoundError

            raise NotFoundError(f"Setting '{key}' not found")

        # Use the row identifier for PUT
        row_key = results[0].get("$key") or results[0].get("key")

        # For settings, we PUT with the key value in the body
        body["key"] = key
        self._client._request("PUT", f"{self._endpoint}/{row_key}", json_data=body)

        # Fetch and return the updated setting
        return self.get(key)

    def reset(self, key: str) -> SystemSetting:
        """Reset a system setting to its default value.

        Args:
            key: Setting key name.

        Returns:
            Updated SystemSetting object with default value.

        Raises:
            NotFoundError: If setting not found.

        Example:
            >>> setting = client.system.settings.reset("max_connections")
            >>> print(f"Reset to: {setting.value}")
        """
        # Get the current setting to find the default value
        current = self.get(key)
        if current.default_value is not None:
            return self.update(key, current.default_value)
        return current

    def list_modified(self) -> builtins.list[SystemSetting]:
        """List only settings that have been modified from defaults.

        Returns:
            List of modified SystemSetting objects.

        Example:
            >>> for setting in client.system.settings.list_modified():
            ...     print(f"{setting.key}: {setting.value} (default: {setting.default_value})")
        """
        return [s for s in self.list() if s.is_modified]


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

    def generate_payload(self) -> str:
        """Generate a license request payload for air-gapped systems.

        For systems without internet connectivity, this generates a payload
        that can be sent to Verge.io support to obtain a license file.

        Returns:
            License request payload as a string.

        Raises:
            APIError: If payload generation fails.

        Example:
            >>> payload = client.system.licenses.generate_payload()
            >>> # Save payload to a file and send to support
            >>> with open("license_request.txt", "w") as f:
            ...     f.write(payload)
        """
        response = self._client._request(
            "POST",
            "license_actions",
            json_data={"action": "generate"},
        )

        if response is None:
            from pyvergeos.exceptions import APIError

            raise APIError("License payload generation returned no response")

        # Response may contain the payload directly or wrapped
        if isinstance(response, dict):
            # Try common response fields
            payload = response.get("payload") or response.get("result") or response.get("data")
            if payload:
                return str(payload)
            # If no specific field, return the whole response as JSON
            import json

            return json.dumps(response)

        return str(response)

    def add(self, license_text: str) -> License:
        """Add a new license to the system.

        Args:
            license_text: The license text/key provided by Verge.io.

        Returns:
            The newly added License object.

        Raises:
            ValidationError: If the license is invalid.
            ConflictError: If the license already exists.

        Example:
            >>> license_data = open("license.txt").read()
            >>> lic = client.system.licenses.add(license_data)
            >>> print(f"Added license: {lic.name}")
        """
        response = self._client._request(
            "POST",
            self._endpoint,
            json_data={"license": license_text},
        )

        if response is None:
            from pyvergeos.exceptions import APIError

            raise APIError("License add returned no response")

        if isinstance(response, dict):
            key = response.get("$key")
            if key is not None:
                return self.get(int(key))
            return self._to_model(response)

        from pyvergeos.exceptions import APIError

        raise APIError("Unexpected response format from license add")


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
        """Unique identifier for the VM."""
        return int(self._data.get("$key", 0))

    @property
    def name(self) -> str:
        """VM name."""
        return str(self._data.get("name", ""))

    @property
    def description(self) -> str:
        """VM description."""
        return str(self._data.get("description", ""))

    @property
    def power_state(self) -> str:
        """Current power state (e.g., 'running', 'stopped')."""
        return str(self._data.get("power_state", ""))

    @property
    def cpu_cores(self) -> int:
        """Number of CPU cores allocated to the VM."""
        return int(self._data.get("cpu_cores", 0))

    @property
    def ram_mb(self) -> int:
        """RAM allocated to the VM in megabytes."""
        return int(self._data.get("ram", 0))

    @property
    def ram_gb(self) -> float:
        """RAM allocated to the VM in gigabytes."""
        return round(self.ram_mb / 1024, 1)

    @property
    def os_family(self) -> str:
        """Operating system family (e.g., 'linux', 'windows')."""
        return str(self._data.get("os_family", ""))

    @property
    def cluster(self) -> str:
        """Name of the cluster hosting this VM."""
        return str(self._data.get("cluster_name", ""))

    @property
    def node(self) -> str:
        """Name of the node hosting this VM."""
        return str(self._data.get("node_name", ""))


class InventoryNetwork:
    """Network inventory item."""

    def __init__(self, data: dict[str, Any]) -> None:
        self._data = data

    @property
    def key(self) -> int:
        """Unique identifier for the network."""
        return int(self._data.get("$key", 0))

    @property
    def name(self) -> str:
        """Network name."""
        return str(self._data.get("name", ""))

    @property
    def description(self) -> str:
        """Network description."""
        return str(self._data.get("description", ""))

    @property
    def network_type(self) -> str:
        """Type of network (e.g., 'internal', 'external')."""
        return str(self._data.get("type", ""))

    @property
    def power_state(self) -> str:
        """Current power state (e.g., 'running', 'stopped')."""
        return str(self._data.get("power_state", ""))

    @property
    def network_address(self) -> str:
        """Network address in CIDR notation."""
        return str(self._data.get("network", ""))

    @property
    def ip_address(self) -> str:
        """IP address assigned to the network interface."""
        return str(self._data.get("ip", ""))


class InventoryStorageTier:
    """Storage tier inventory item."""

    def __init__(self, data: dict[str, Any]) -> None:
        self._data = data

    @property
    def tier(self) -> int:
        """Storage tier number."""
        return int(self._data.get("tier", 0))

    @property
    def description(self) -> str:
        """Storage tier description."""
        return str(self._data.get("description", ""))

    @property
    def capacity_bytes(self) -> int:
        """Total capacity of the storage tier in bytes."""
        return int(self._data.get("capacity", 0))

    @property
    def capacity_gb(self) -> float:
        """Total capacity of the storage tier in gigabytes."""
        return round(self.capacity_bytes / 1073741824, 2)

    @property
    def used_bytes(self) -> int:
        """Used space in the storage tier in bytes."""
        return int(self._data.get("used", 0))

    @property
    def used_gb(self) -> float:
        """Used space in the storage tier in gigabytes."""
        return round(self.used_bytes / 1073741824, 2)

    @property
    def used_percent(self) -> float:
        """Percentage of storage tier capacity currently in use."""
        if self.capacity_bytes > 0:
            return round((self.used_bytes / self.capacity_bytes) * 100, 1)
        return 0.0


class InventoryNode:
    """Node inventory item."""

    def __init__(self, data: dict[str, Any]) -> None:
        self._data = data

    @property
    def key(self) -> int:
        """Unique identifier for the node."""
        return int(self._data.get("$key", 0))

    @property
    def name(self) -> str:
        """Node name."""
        return str(self._data.get("name", ""))

    @property
    def status(self) -> str:
        """Current node status."""
        return str(self._data.get("status_display", ""))

    @property
    def cluster(self) -> str:
        """Name of the cluster this node belongs to."""
        return str(self._data.get("cluster_name", ""))

    @property
    def cores(self) -> int:
        """Number of CPU cores available on the node."""
        return int(self._data.get("cores", 0))

    @property
    def ram_mb(self) -> int:
        """Total RAM on the node in megabytes."""
        return int(self._data.get("ram", 0))

    @property
    def ram_gb(self) -> float:
        """Total RAM on the node in gigabytes."""
        return round(self.ram_mb / 1024, 1)


class InventoryCluster:
    """Cluster inventory item."""

    def __init__(self, data: dict[str, Any]) -> None:
        self._data = data

    @property
    def key(self) -> int:
        """Unique identifier for the cluster."""
        return int(self._data.get("$key", 0))

    @property
    def name(self) -> str:
        """Cluster name."""
        return str(self._data.get("name", ""))

    @property
    def description(self) -> str:
        """Cluster description."""
        return str(self._data.get("description", ""))

    @property
    def status(self) -> str:
        """Current cluster status."""
        return str(self._data.get("status_display", ""))

    @property
    def total_nodes(self) -> int:
        """Total number of nodes in the cluster."""
        return int(self._data.get("total_nodes", 0))

    @property
    def online_nodes(self) -> int:
        """Number of nodes currently online in the cluster."""
        return int(self._data.get("online_nodes", 0))


class InventoryTenant:
    """Tenant inventory item."""

    def __init__(self, data: dict[str, Any]) -> None:
        self._data = data

    @property
    def key(self) -> int:
        """Unique identifier for the tenant."""
        return int(self._data.get("$key", 0))

    @property
    def name(self) -> str:
        """Tenant name."""
        return str(self._data.get("name", ""))

    @property
    def description(self) -> str:
        """Tenant description."""
        return str(self._data.get("description", ""))

    @property
    def status(self) -> str:
        """Current tenant status."""
        return str(self._data.get("status_display", ""))

    @property
    def is_running(self) -> bool:
        """Whether the tenant is currently running."""
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
# System Diagnostics
# =============================================================================


class SystemDiagnostic(ResourceObject):
    """Represents a system diagnostic report in VergeOS.

    System diagnostics capture comprehensive system information including logs,
    configuration, network state, and other metrics useful for troubleshooting.

    Properties:
        name: Diagnostic report name.
        description: Report description.
        status: Current status (initializing, building, uploading, complete, error).
        status_display: Human-readable status.
        status_info: Additional status information (e.g., current node being processed).
        file_key: Associated file $key for download.
        is_complete: Whether the diagnostic build is complete.
        is_building: Whether the diagnostic is currently building.
        has_error: Whether the diagnostic encountered an error.
        created_at: When the diagnostic was created.
    """

    @property
    def name(self) -> str:
        """Diagnostic report name."""
        return str(self.get("name", ""))

    @property
    def description(self) -> str:
        """Report description."""
        return str(self.get("description", ""))

    @property
    def status(self) -> str:
        """Current status (API value)."""
        return str(self.get("status", DIAG_STATUS_INITIALIZING))

    @property
    def status_display(self) -> str:
        """Human-readable status."""
        return DIAG_STATUS_DISPLAY.get(self.status, self.status)

    @property
    def status_info(self) -> str:
        """Additional status information."""
        return str(self.get("status_info", ""))

    @property
    def file_key(self) -> int | None:
        """Associated file $key for download."""
        val = self.get("file")
        return int(val) if val else None

    @property
    def is_complete(self) -> bool:
        """Whether the diagnostic build is complete."""
        return self.status == DIAG_STATUS_COMPLETE

    @property
    def is_building(self) -> bool:
        """Whether the diagnostic is currently building."""
        return self.status in (DIAG_STATUS_INITIALIZING, DIAG_STATUS_BUILDING)

    @property
    def has_error(self) -> bool:
        """Whether the diagnostic encountered an error."""
        return self.status == DIAG_STATUS_ERROR

    @property
    def created_at(self) -> datetime | None:
        """When the diagnostic was created."""
        ts = self.get("timestamp")
        if ts:
            return datetime.fromtimestamp(int(ts), tz=timezone.utc)
        return None

    def refresh(self) -> SystemDiagnostic:
        """Refresh diagnostic data from API.

        Returns:
            Updated SystemDiagnostic object.
        """
        from typing import cast

        manager = cast("SystemDiagnosticManager", self._manager)
        return manager.get(self.key)

    def send_to_support(self) -> None:
        """Send this diagnostic report to Verge.io support.

        Requires the diagnostic to be complete.

        Raises:
            ValueError: If diagnostic is not complete.
        """
        from typing import cast

        if not self.is_complete:
            raise ValueError("Diagnostic must be complete before sending to support")

        manager = cast("SystemDiagnosticManager", self._manager)
        manager.send_to_support(self.key)

    def wait_for_completion(
        self,
        timeout: float = TASK_WAIT_TIMEOUT,
        poll_interval: float = POLL_INTERVAL,
    ) -> SystemDiagnostic:
        """Wait for the diagnostic build to complete.

        Args:
            timeout: Maximum time to wait in seconds.
            poll_interval: Time between status checks in seconds.

        Returns:
            The completed SystemDiagnostic object.

        Raises:
            TaskTimeoutError: If timeout is reached before completion.
        """
        import time

        from pyvergeos.exceptions import TaskTimeoutError

        start_time = time.time()
        while True:
            current = self.refresh()
            if current.is_complete or current.has_error:
                return current

            elapsed = time.time() - start_time
            if elapsed >= timeout:
                raise TaskTimeoutError(
                    f"Diagnostic build did not complete within {timeout} seconds"
                )

            time.sleep(poll_interval)

    def delete(self) -> None:
        """Delete this diagnostic report."""
        from typing import cast

        manager = cast("SystemDiagnosticManager", self._manager)
        manager.delete(self.key)

    def __repr__(self) -> str:
        return (
            f"<SystemDiagnostic key={self.key} name={self.name!r} status={self.status_display!r}>"
        )


class SystemDiagnosticManager(ResourceManager[SystemDiagnostic]):
    """Manages system diagnostic reports in VergeOS.

    System diagnostics capture comprehensive system information for
    troubleshooting and support purposes.

    Example:
        >>> # Build a new diagnostic report
        >>> diag = client.system.diagnostics.build(
        ...     name="Support Case #12345",
        ...     description="Network connectivity issue",
        ...     send_to_support=True
        ... )
        >>>
        >>> # Wait for completion
        >>> diag = diag.wait_for_completion()
        >>> print(f"Status: {diag.status_display}")
        >>>
        >>> # List all diagnostics
        >>> for d in client.system.diagnostics.list():
        ...     print(f"{d.name}: {d.status_display}")
    """

    _endpoint = "system_diagnostics"

    def _to_model(self, data: dict[str, Any]) -> SystemDiagnostic:
        return SystemDiagnostic(data, self)

    def list(  # noqa: A003
        self,
        filter: str | None = None,  # noqa: A002
        fields: builtins.list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        *,
        status: str | None = None,
        **filter_kwargs: Any,
    ) -> builtins.list[SystemDiagnostic]:
        """List system diagnostic reports.

        Args:
            filter: OData filter string.
            fields: List of fields to return.
            limit: Maximum number of results.
            offset: Skip this many results.
            status: Filter by status (initializing, building, complete, error).
            **filter_kwargs: Additional filter arguments.

        Returns:
            List of SystemDiagnostic objects.

        Example:
            >>> # List all diagnostics
            >>> diagnostics = client.system.diagnostics.list()
            >>>
            >>> # List completed diagnostics only
            >>> completed = client.system.diagnostics.list(status="complete")
        """
        if fields is None:
            fields = [
                "$key",
                "name",
                "description",
                "status",
                "status_info",
                "file",
                "timestamp",
            ]

        filters = []
        if filter:
            filters.append(filter)
        if status:
            filters.append(f"status eq '{status}'")

        combined_filter = " and ".join(filters) if filters else None

        return super().list(
            filter=combined_filter,
            fields=fields,
            limit=limit,
            offset=offset,
            **filter_kwargs,
        )

    def get(  # type: ignore[override]
        self, key: int, *, fields: builtins.list[str] | None = None
    ) -> SystemDiagnostic:
        """Get a diagnostic report by key.

        Args:
            key: Diagnostic $key.
            fields: List of fields to return.

        Returns:
            SystemDiagnostic object.

        Raises:
            NotFoundError: If diagnostic not found.
        """
        if fields is None:
            fields = [
                "$key",
                "name",
                "description",
                "status",
                "status_info",
                "file",
                "timestamp",
            ]

        return super().get(key, fields=fields)

    def build(
        self,
        name: str | None = None,
        description: str | None = None,
        *,
        send_to_support: bool = False,
    ) -> SystemDiagnostic:
        """Build a new system diagnostic report.

        Triggers collection of comprehensive system information from all nodes.
        This operation may take several minutes depending on system size.

        Args:
            name: Report name. If not provided, auto-generated with timestamp.
            description: Report description.
            send_to_support: If True, automatically send to Verge.io support
                when complete (requires internet connectivity).

        Returns:
            The new SystemDiagnostic object (initially in 'initializing' status).

        Example:
            >>> # Build diagnostic for support case
            >>> diag = client.system.diagnostics.build(
            ...     name="Support-12345",
            ...     description="High CPU usage investigation",
            ...     send_to_support=True
            ... )
            >>> diag = diag.wait_for_completion()
        """
        body: dict[str, Any] = {}

        if name:
            body["name"] = name
        if description:
            body["description"] = description
        if send_to_support:
            body["send2support"] = True

        response = self._client._request("POST", self._endpoint, json_data=body)

        if response is None:
            from pyvergeos.exceptions import APIError

            raise APIError("Diagnostic build returned no response")

        if isinstance(response, dict):
            key = response.get("$key")
            if key is not None:
                return self.get(int(key))
            return self._to_model(response)

        from pyvergeos.exceptions import APIError

        raise APIError("Unexpected response format from diagnostic build")

    def send_to_support(self, key: int) -> None:
        """Send a diagnostic report to Verge.io support.

        The diagnostic must be complete before sending.

        Args:
            key: Diagnostic $key.

        Raises:
            NotFoundError: If diagnostic not found.
            ValueError: If diagnostic is not complete.
        """
        # First verify the diagnostic exists and is complete
        diag = self.get(key)
        if not diag.is_complete:
            raise ValueError("Diagnostic must be complete before sending to support")

        # Use the actions endpoint
        self._client._request(
            "POST",
            "system_diagnostic_actions",
            json_data={
                "system_diagnostic": key,
                "action": "send2support",
            },
        )

    def delete(self, key: int) -> None:
        """Delete a diagnostic report.

        Args:
            key: Diagnostic $key.

        Raises:
            NotFoundError: If diagnostic not found.
        """
        self._client._request("DELETE", f"{self._endpoint}/{key}")

    def update(  # type: ignore[override]
        self,
        key: int,
        *,
        name: str | None = None,
        description: str | None = None,
    ) -> SystemDiagnostic:
        """Update a diagnostic report's name or description.

        Args:
            key: Diagnostic $key.
            name: New name.
            description: New description.

        Returns:
            Updated SystemDiagnostic object.

        Raises:
            NotFoundError: If diagnostic not found.
        """
        body: dict[str, Any] = {}

        if name is not None:
            body["name"] = name
        if description is not None:
            body["description"] = description

        if not body:
            return self.get(key)

        self._client._request("PUT", f"{self._endpoint}/{key}", json_data=body)
        return self.get(key)

    def get_download_url(self, key: int) -> str | None:
        """Get the download URL for a completed diagnostic file.

        Args:
            key: Diagnostic $key.

        Returns:
            Download URL string, or None if file not available.

        Raises:
            NotFoundError: If diagnostic not found.
            ValueError: If diagnostic is not complete.
        """
        diag = self.get(key)
        if not diag.is_complete:
            raise ValueError("Diagnostic must be complete to download")

        if diag.file_key is None:
            return None

        # Get the file information
        file_response = self._client._request(
            "GET",
            f"files/{diag.file_key}",
            params={"fields": "$key,name,path"},
        )

        if file_response and isinstance(file_response, dict):
            path = file_response.get("path")
            if path:
                return f"https://{self._client.host}/files/{path}"

        return None


# =============================================================================
# Root Certificates (Trusted CAs)
# =============================================================================


class RootCertificate(ResourceObject):
    """Represents a trusted root certificate authority in VergeOS.

    Root certificates are added to the system's trust store to enable
    secure connections to systems using private/internal CA certificates.

    Properties:
        subject: Certificate subject (common name, organization, etc.).
        issuer: Certificate issuer.
        fingerprint: Certificate fingerprint (SHA-256).
        start_date: Certificate validity start date.
        end_date: Certificate validity end date.
        cert_pem: Certificate in PEM format.
        modified_at: When the certificate was last modified.
    """

    @property
    def subject(self) -> str:
        """Certificate subject."""
        return str(self.get("subject", ""))

    @property
    def issuer(self) -> str:
        """Certificate issuer."""
        return str(self.get("issuer", ""))

    @property
    def fingerprint(self) -> str:
        """Certificate fingerprint."""
        return str(self.get("fingerprint", ""))

    @property
    def start_date(self) -> str:
        """Certificate validity start date."""
        return str(self.get("startdate", ""))

    @property
    def end_date(self) -> str:
        """Certificate validity end date."""
        return str(self.get("enddate", ""))

    @property
    def cert_pem(self) -> str:
        """Certificate in PEM format."""
        return str(self.get("cert", ""))

    @property
    def modified_at(self) -> datetime | None:
        """When the certificate was last modified."""
        ts = self.get("modified")
        if ts:
            return datetime.fromtimestamp(int(ts), tz=timezone.utc)
        return None

    def delete(self) -> None:
        """Delete this root certificate."""
        from typing import cast

        manager = cast("RootCertificateManager", self._manager)
        manager.delete(self.key)

    def __repr__(self) -> str:
        return f"<RootCertificate key={self.key} subject={self.subject!r}>"


class RootCertificateManager(ResourceManager[RootCertificate]):
    """Manages trusted root certificates in VergeOS.

    Root certificates allow adding custom Certificate Authorities to the
    system's trust store, enabling secure connections to systems using
    private/enterprise CA certificates.

    Common use cases:
    - Enabling secure site syncs with internal CA certificates
    - Trusting enterprise PKI for LDAP/AD connections
    - Development environments with self-signed CAs

    Example:
        >>> # Add a root CA
        >>> ca_cert = open("enterprise-ca.pem").read()
        >>> root_ca = client.system.root_certificates.create(cert=ca_cert)
        >>> print(f"Added CA: {root_ca.subject}")
        >>>
        >>> # List trusted CAs
        >>> for ca in client.system.root_certificates.list():
        ...     print(f"{ca.subject} (expires: {ca.end_date})")
    """

    _endpoint = "root_certificates"

    def _to_model(self, data: dict[str, Any]) -> RootCertificate:
        return RootCertificate(data, self)

    def list(  # noqa: A003
        self,
        filter: str | None = None,  # noqa: A002
        fields: builtins.list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        **filter_kwargs: Any,
    ) -> builtins.list[RootCertificate]:
        """List trusted root certificates.

        Args:
            filter: OData filter string.
            fields: List of fields to return.
            limit: Maximum number of results.
            offset: Skip this many results.
            **filter_kwargs: Additional filter arguments.

        Returns:
            List of RootCertificate objects.

        Example:
            >>> # List all trusted CAs
            >>> for ca in client.system.root_certificates.list():
            ...     print(f"{ca.subject}")
        """
        if fields is None:
            fields = [
                "$key",
                "subject",
                "issuer",
                "fingerprint",
                "startdate",
                "enddate",
                "modified",
            ]

        return super().list(
            filter=filter,
            fields=fields,
            limit=limit,
            offset=offset,
            **filter_kwargs,
        )

    def get(  # type: ignore[override]
        self, key: int, *, fields: builtins.list[str] | None = None
    ) -> RootCertificate:
        """Get a root certificate by key.

        Args:
            key: Certificate $key.
            fields: List of fields to return.

        Returns:
            RootCertificate object.

        Raises:
            NotFoundError: If certificate not found.
        """
        if fields is None:
            fields = [
                "$key",
                "cert",
                "subject",
                "issuer",
                "fingerprint",
                "startdate",
                "enddate",
                "modified",
            ]

        return super().get(key, fields=fields)

    def get_by_subject(self, subject: str) -> RootCertificate:
        """Get a root certificate by subject.

        Args:
            subject: Certificate subject (partial match supported).

        Returns:
            RootCertificate object.

        Raises:
            NotFoundError: If certificate not found.
        """
        results = self.list(filter=f"subject ct '{subject}'", limit=1)
        if not results:
            from pyvergeos.exceptions import NotFoundError

            raise NotFoundError(f"Root certificate with subject containing '{subject}' not found")
        return results[0]

    def get_by_fingerprint(self, fingerprint: str) -> RootCertificate:
        """Get a root certificate by fingerprint.

        Args:
            fingerprint: Certificate fingerprint.

        Returns:
            RootCertificate object.

        Raises:
            NotFoundError: If certificate not found.
        """
        results = self.list(filter=f"fingerprint eq '{fingerprint}'", limit=1)
        if not results:
            from pyvergeos.exceptions import NotFoundError

            raise NotFoundError(f"Root certificate with fingerprint '{fingerprint}' not found")
        return results[0]

    def create(self, cert: str) -> RootCertificate:  # type: ignore[override]
        """Add a new trusted root certificate.

        Args:
            cert: Certificate in PEM format.

        Returns:
            The new RootCertificate object.

        Raises:
            ValidationError: If the certificate is invalid.
            ConflictError: If the certificate already exists.

        Example:
            >>> ca_cert = '''-----BEGIN CERTIFICATE-----
            ... MIIDXTCCAkWgAwIBAgIJAJC1...
            ... -----END CERTIFICATE-----'''
            >>> root_ca = client.system.root_certificates.create(cert=ca_cert)
        """
        response = self._client._request(
            "POST",
            self._endpoint,
            json_data={"cert": cert},
        )

        if response is None:
            from pyvergeos.exceptions import APIError

            raise APIError("Root certificate creation returned no response")

        if isinstance(response, dict):
            key = response.get("$key")
            if key is not None:
                return self.get(int(key))
            return self._to_model(response)

        from pyvergeos.exceptions import APIError

        raise APIError("Unexpected response format from root certificate creation")

    def delete(self, key: int) -> None:
        """Delete a root certificate.

        Args:
            key: Certificate $key.

        Raises:
            NotFoundError: If certificate not found.
        """
        self._client._request("DELETE", f"{self._endpoint}/{key}")


# =============================================================================
# System Manager
# =============================================================================


class SystemManager:
    """Provides system-level operations in VergeOS.

    Includes access to settings, statistics, licenses, diagnostics,
    root certificates, and inventory.

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

        >>> # Update a setting
        >>> setting = client.system.settings.update("max_connections", "1000")

        >>> # Build system diagnostics
        >>> diag = client.system.diagnostics.build(
        ...     name="Support Case",
        ...     send_to_support=True
        ... )

        >>> # Add a trusted root CA
        >>> root_ca = client.system.root_certificates.create(cert=pem_text)

        >>> # Get full inventory
        >>> inventory = client.system.inventory()
        >>> print(inventory.summary)
    """

    def __init__(self, client: VergeClient) -> None:
        self._client = client
        self._settings: SettingsManager | None = None
        self._licenses: LicenseManager | None = None
        self._diagnostics: SystemDiagnosticManager | None = None
        self._root_certificates: RootCertificateManager | None = None

    @property
    def settings(self) -> SettingsManager:
        """Access system settings.

        System settings control various aspects of VergeOS behavior
        including connection limits, API rate limits, and more.

        Example:
            >>> # List all settings
            >>> for s in client.system.settings.list():
            ...     print(f"{s.key}: {s.value}")

            >>> # Update a setting
            >>> client.system.settings.update("max_connections", "1000")

            >>> # List modified settings
            >>> for s in client.system.settings.list_modified():
            ...     print(f"{s.key}: {s.value} (default: {s.default_value})")
        """
        if self._settings is None:
            self._settings = SettingsManager(self._client)
        return self._settings

    @property
    def licenses(self) -> LicenseManager:
        """Access license management.

        Licenses control which features are available and the
        capabilities of the VergeOS system.

        Example:
            >>> # List licenses
            >>> for lic in client.system.licenses.list():
            ...     print(f"{lic.name}: {'valid' if lic.is_valid else 'invalid'}")

            >>> # Generate payload for air-gapped licensing
            >>> payload = client.system.licenses.generate_payload()
        """
        if self._licenses is None:
            self._licenses = LicenseManager(self._client)
        return self._licenses

    @property
    def diagnostics(self) -> SystemDiagnosticManager:
        """Access system diagnostics.

        System diagnostics capture comprehensive system information
        for troubleshooting and support purposes.

        Example:
            >>> # Build a diagnostic report
            >>> diag = client.system.diagnostics.build(
            ...     name="Support-12345",
            ...     description="Network issue",
            ...     send_to_support=True
            ... )
            >>> diag = diag.wait_for_completion()

            >>> # List diagnostics
            >>> for d in client.system.diagnostics.list():
            ...     print(f"{d.name}: {d.status_display}")
        """
        if self._diagnostics is None:
            self._diagnostics = SystemDiagnosticManager(self._client)
        return self._diagnostics

    @property
    def root_certificates(self) -> RootCertificateManager:
        """Access root certificate (trusted CA) management.

        Root certificates allow adding custom Certificate Authorities
        to the system's trust store for secure connections.

        Example:
            >>> # Add a trusted CA
            >>> ca_pem = open("enterprise-ca.pem").read()
            >>> ca = client.system.root_certificates.create(cert=ca_pem)

            >>> # List trusted CAs
            >>> for ca in client.system.root_certificates.list():
            ...     print(f"{ca.subject}")
        """
        if self._root_certificates is None:
            self._root_certificates = RootCertificateManager(self._client)
        return self._root_certificates

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
                    node_list = (
                        node_response if isinstance(node_response, list) else [node_response]
                    )
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
                        cluster_response
                        if isinstance(cluster_response, list)
                        else [cluster_response]
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
