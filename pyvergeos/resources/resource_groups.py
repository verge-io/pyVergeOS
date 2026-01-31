"""Resource group management for VergeOS hardware device pools."""

from __future__ import annotations

import builtins
import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Literal

from pyvergeos.exceptions import NotFoundError
from pyvergeos.resources.base import ResourceManager, ResourceObject

if TYPE_CHECKING:
    from pyvergeos.client import VergeClient

logger = logging.getLogger(__name__)

# Device type mappings
DEVICE_TYPE_MAP = {
    "node_pci_devices": "PCI",
    "node_sriov_nic_devices": "SR-IOV NIC",
    "node_usb_devices": "USB",
    "node_host_gpu_devices": "Host GPU",
    "node_nvidia_vgpu_devices": "NVIDIA vGPU",
}

DEVICE_TYPE_REVERSE_MAP = {v: k for k, v in DEVICE_TYPE_MAP.items()}

# Device class mappings
DEVICE_CLASS_MAP = {
    "gpu": "GPU",
    "vgpu": "vGPU",
    "storage": "Storage",
    "hid": "Human Input Device",
    "usb": "Generic USB Device",
    "network": "Network",
    "media": "Media",
    "audio": "Audio",
    "fpga": "FPGA",
    "pci": "Generic PCI",
    "unknown": "Unknown",
}

DEVICE_CLASS_REVERSE_MAP = {v.lower(): k for k, v in DEVICE_CLASS_MAP.items()}


class ResourceGroup(ResourceObject):
    """Represents a resource group in VergeOS.

    Resource groups define collections of hardware devices (GPU, PCI, USB,
    SR-IOV NIC, vGPU) that can be assigned to virtual machines for device
    passthrough.

    Resource groups are read-only - they are typically configured through
    the VergeOS UI to associate physical devices with virtual machines.

    Note:
        Resource groups use UUID as their primary key, not integer IDs.
        The `key` property returns the UUID string.
    """

    @property
    def key(self) -> str:  # type: ignore[override]
        """Resource group key (UUID).

        Resource groups use UUID as their primary identifier.
        """
        uuid = self.get("uuid")
        if uuid is None:
            raise ValueError("Resource group has no UUID")
        return str(uuid)

    @property
    def uuid(self) -> str:
        """Resource group UUID (same as key)."""
        return str(self.get("uuid", ""))

    @property
    def name(self) -> str:
        """Resource group name."""
        return str(self.get("name", ""))

    @property
    def description(self) -> str:
        """Resource group description."""
        return str(self.get("description", ""))

    @property
    def device_type(self) -> str:
        """Device type (raw API value).

        One of: node_pci_devices, node_sriov_nic_devices, node_usb_devices,
        node_host_gpu_devices, node_nvidia_vgpu_devices
        """
        return str(self.get("type", ""))

    @property
    def device_type_display(self) -> str:
        """Human-readable device type.

        One of: PCI, SR-IOV NIC, USB, Host GPU, NVIDIA vGPU
        """
        type_display = self.get("type_display")
        if type_display:
            return str(type_display)
        return DEVICE_TYPE_MAP.get(self.device_type, self.device_type)

    @property
    def device_class(self) -> str:
        """Device class (raw API value).

        One of: gpu, vgpu, storage, hid, usb, network, media, audio, fpga, pci, unknown
        """
        return str(self.get("class", ""))

    @property
    def device_class_display(self) -> str:
        """Human-readable device class.

        One of: GPU, vGPU, Storage, Human Input Device, Generic USB Device,
        Network, Media, Audio, FPGA, Generic PCI, Unknown
        """
        class_display = self.get("class_display")
        if class_display:
            return str(class_display)
        return DEVICE_CLASS_MAP.get(self.device_class, self.device_class)

    @property
    def is_enabled(self) -> bool:
        """Whether the resource group is enabled."""
        return bool(self.get("enabled", False))

    @property
    def resource_count(self) -> int:
        """Number of resources (devices) in this group."""
        return int(self.get("resource_count", 0))

    @property
    def created_at(self) -> datetime | None:
        """Creation timestamp."""
        ts = self.get("created")
        if ts:
            return datetime.fromtimestamp(int(ts), tz=timezone.utc)
        return None

    @property
    def modified_at(self) -> datetime | None:
        """Last modification timestamp."""
        ts = self.get("modified")
        if ts:
            return datetime.fromtimestamp(int(ts), tz=timezone.utc)
        return None

    @property
    def rules(self) -> ResourceRuleManager:
        """Access resource rules for this resource group.

        Returns:
            ResourceRuleManager scoped to this resource group.

        Example:
            >>> # List rules for this group
            >>> for rule in group.rules.list():
            ...     print(f"{rule.name}: {rule.filter_expression}")

            >>> # Create a rule
            >>> rule = group.rules.create(
            ...     name="Intel NICs",
            ...     filter_expression="vendor ct 'Intel'",
            ... )
        """
        from typing import cast

        manager = cast("ResourceGroupManager", self._manager)
        return ResourceRuleManager(manager._client, self.key)

    def refresh(self) -> ResourceGroup:
        """Refresh this resource group's data from the server."""
        from typing import cast

        manager = cast("ResourceGroupManager", self._manager)
        return manager.get(self.key)

    def save(self, **kwargs: Any) -> ResourceGroup:
        """Update this resource group with the given values."""
        from typing import cast

        manager = cast("ResourceGroupManager", self._manager)
        return manager.update(self.key, **kwargs)

    def delete(self) -> None:
        """Delete this resource group."""
        from typing import cast

        manager = cast("ResourceGroupManager", self._manager)
        manager.delete(self.key)

    def __repr__(self) -> str:
        return (
            f"<ResourceGroup uuid={self.uuid!r} name={self.name!r} "
            f"type={self.device_type_display!r} class={self.device_class_display!r}>"
        )


class ResourceGroupManager(ResourceManager[ResourceGroup]):
    """Manages resource groups in VergeOS.

    Resource groups define collections of hardware devices (GPU, PCI, USB,
    SR-IOV NIC, vGPU) that can be assigned to VMs for device passthrough.

    Device Types:
        - PCI: General PCI passthrough (network cards, storage controllers, etc.)
        - SR-IOV NIC: SR-IOV enabled NICs for direct network virtualization
        - USB: USB device passthrough
        - Host GPU: Full GPU passthrough to a single VM
        - NVIDIA vGPU: NVIDIA vGPU for GPU sharing across multiple VMs

    Device Classes:
        GPU, vGPU, Storage, Human Input Device, Generic USB Device, Network,
        Media, Audio, FPGA, Generic PCI, Unknown

    Example:
        >>> # List all resource groups
        >>> for rg in client.resource_groups.list():
        ...     print(f"{rg.name}: {rg.device_type_display} ({rg.device_class_display})")

        >>> # Get a specific resource group
        >>> gpu_group = client.resource_groups.get(name="GPU Pool")
        >>> print(f"Devices: {gpu_group.resource_count}")

        >>> # Filter by device type
        >>> gpu_groups = client.resource_groups.list_by_type("Host GPU")
        >>> pci_groups = client.resource_groups.list_by_type("PCI")

        >>> # Filter by device class
        >>> network_groups = client.resource_groups.list_by_class("Network")

        >>> # List enabled groups only
        >>> enabled_groups = client.resource_groups.list_enabled()
    """

    _endpoint = "resource_groups"

    # Default fields for list operations
    _default_fields = [
        "$key",
        "uuid",
        "name",
        "description",
        "type",
        "display(type) as type_display",
        "class",
        "display(class) as class_display",
        "enabled",
        "count(resources) as resource_count",
        "created",
        "modified",
    ]

    def _to_model(self, data: dict[str, Any]) -> ResourceGroup:
        return ResourceGroup(data, self)

    def list(  # noqa: A003
        self,
        filter: str | None = None,  # noqa: A002
        fields: builtins.list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        **filter_kwargs: Any,
    ) -> builtins.list[ResourceGroup]:
        """List resource groups with optional filtering.

        Args:
            filter: OData filter string.
            fields: List of fields to return.
            limit: Maximum number of results.
            offset: Skip this many results.
            **filter_kwargs: Shorthand filter arguments.

        Returns:
            List of ResourceGroup objects.

        Example:
            >>> # List all resource groups
            >>> groups = client.resource_groups.list()

            >>> # Filter by enabled status
            >>> enabled = client.resource_groups.list(enabled=True)

            >>> # Filter with OData
            >>> gpu_groups = client.resource_groups.list(
            ...     filter="class eq 'gpu' and enabled eq true"
            ... )
        """
        if fields is None:
            fields = self._default_fields

        return super().list(
            filter=filter, fields=fields, limit=limit, offset=offset, **filter_kwargs
        )

    def get(
        self,
        key: str | int | None = None,
        *,
        name: str | None = None,
        uuid: str | None = None,
        fields: builtins.list[str] | None = None,
    ) -> ResourceGroup:
        """Get a resource group by key (UUID), name, or UUID.

        Args:
            key: Resource group key (UUID string).
            name: Resource group name.
            uuid: Resource group UUID (alias for key).
            fields: List of fields to return.

        Returns:
            ResourceGroup object.

        Raises:
            NotFoundError: If resource group not found.
            ValueError: If no identifier provided.

        Example:
            >>> # Get by UUID key
            >>> rg = client.resource_groups.get("12345678-1234-1234-1234-123456789abc")

            >>> # Get by name
            >>> rg = client.resource_groups.get(name="GPU Pool")

            >>> # Get by uuid parameter (same as key)
            >>> rg = client.resource_groups.get(uuid="12345678-1234-1234-1234-123456789abc")
        """
        if fields is None:
            fields = self._default_fields

        # key parameter is actually UUID for resource groups
        if key is not None:
            key_str = str(key).lower()
            results = self.list(filter=f"uuid eq '{key_str}'", fields=fields, limit=1)
            if not results:
                raise NotFoundError(f"Resource group with UUID '{key}' not found")
            return results[0]

        if name is not None:
            # Search by name
            escaped_name = name.replace("'", "''")
            results = self.list(filter=f"name eq '{escaped_name}'", fields=fields, limit=1)
            if not results:
                raise NotFoundError(f"Resource group with name '{name}' not found")
            return results[0]

        if uuid is not None:
            # Search by UUID (alias for key)
            uuid_lower = uuid.lower()
            results = self.list(filter=f"uuid eq '{uuid_lower}'", fields=fields, limit=1)
            if not results:
                raise NotFoundError(f"Resource group with UUID '{uuid}' not found")
            return results[0]

        raise ValueError("Either key, name, or uuid must be provided")

    def list_enabled(
        self,
        fields: builtins.list[str] | None = None,
    ) -> builtins.list[ResourceGroup]:
        """List enabled resource groups.

        Args:
            fields: List of fields to return.

        Returns:
            List of enabled ResourceGroup objects.

        Example:
            >>> enabled_groups = client.resource_groups.list_enabled()
            >>> for rg in enabled_groups:
            ...     print(f"{rg.name}: {rg.device_type_display}")
        """
        return self.list(filter="enabled eq true", fields=fields)

    def list_disabled(
        self,
        fields: builtins.list[str] | None = None,
    ) -> builtins.list[ResourceGroup]:
        """List disabled resource groups.

        Args:
            fields: List of fields to return.

        Returns:
            List of disabled ResourceGroup objects.
        """
        return self.list(filter="enabled eq false", fields=fields)

    def list_by_type(
        self,
        device_type: str,
        *,
        enabled: bool | None = None,
        fields: builtins.list[str] | None = None,
    ) -> builtins.list[ResourceGroup]:
        """List resource groups by device type.

        Args:
            device_type: Device type - either display name (PCI, SR-IOV NIC, USB,
                Host GPU, NVIDIA vGPU) or API value (node_pci_devices, etc.)
            enabled: Filter by enabled status (optional).
            fields: List of fields to return.

        Returns:
            List of ResourceGroup objects matching the device type.

        Example:
            >>> # List all Host GPU resource groups
            >>> gpu_groups = client.resource_groups.list_by_type("Host GPU")

            >>> # List enabled PCI resource groups
            >>> pci_groups = client.resource_groups.list_by_type("PCI", enabled=True)

            >>> # Use API value
            >>> usb_groups = client.resource_groups.list_by_type("node_usb_devices")
        """
        # Convert display name to API value if needed
        api_type = DEVICE_TYPE_REVERSE_MAP.get(device_type, device_type)

        filters = [f"type eq '{api_type}'"]
        if enabled is not None:
            filters.append(f"enabled eq {str(enabled).lower()}")

        return self.list(filter=" and ".join(filters), fields=fields)

    def list_by_class(
        self,
        device_class: str,
        *,
        enabled: bool | None = None,
        fields: builtins.list[str] | None = None,
    ) -> builtins.list[ResourceGroup]:
        """List resource groups by device class.

        Args:
            device_class: Device class - either display name (GPU, vGPU, Storage,
                Network, etc.) or API value (gpu, vgpu, storage, network, etc.)
            enabled: Filter by enabled status (optional).
            fields: List of fields to return.

        Returns:
            List of ResourceGroup objects matching the device class.

        Example:
            >>> # List all GPU class resource groups
            >>> gpu_groups = client.resource_groups.list_by_class("GPU")

            >>> # List enabled Network resource groups
            >>> net_groups = client.resource_groups.list_by_class("Network", enabled=True)

            >>> # List storage device groups
            >>> storage_groups = client.resource_groups.list_by_class("Storage")
        """
        # Convert display name to API value if needed
        api_class = DEVICE_CLASS_REVERSE_MAP.get(device_class.lower(), device_class.lower())

        filters = [f"class eq '{api_class}'"]
        if enabled is not None:
            filters.append(f"enabled eq {str(enabled).lower()}")

        return self.list(filter=" and ".join(filters), fields=fields)

    def create(  # type: ignore[override]
        self,
        name: str,
        device_type: Literal[
            "node_pci_devices",
            "node_sriov_nic_devices",
            "node_usb_devices",
            "node_host_gpu_devices",
            "node_nvidia_vgpu_devices",
        ],
        *,
        description: str = "",
        device_class: str = "unknown",
        enabled: bool = True,
        settings: dict[str, Any] | None = None,
        device_keys: builtins.list[int] | None = None,
    ) -> ResourceGroup:
        """Create a new resource group.

        Args:
            name: Resource group name.
            device_type: Type of devices in this group.
            description: Resource group description.
            device_class: Device classification for UI icon.
            enabled: Whether the resource group is enabled.
            settings: Type-specific settings (see create_* methods for details).
            device_keys: List of device keys to auto-create rules from.

        Returns:
            Created ResourceGroup object.

        Example:
            >>> # Create a PCI device group
            >>> group = client.resource_groups.create(
            ...     name="GPU Pool",
            ...     device_type="node_host_gpu_devices",
            ...     device_class="gpu",
            ... )
        """
        body: dict[str, Any] = {
            "name": name,
            "type": device_type,
            "enabled": enabled,
        }

        if description:
            body["description"] = description
        if device_class:
            # Convert display name to API value if needed
            api_class = DEVICE_CLASS_REVERSE_MAP.get(device_class.lower(), device_class.lower())
            body["class"] = api_class
        if settings:
            body["settings_args"] = settings
        if device_keys:
            body["key_args"] = device_keys

        response = self._client._request("POST", self._endpoint, json_data=body)
        if response is None:
            raise ValueError("No response from create operation")
        if not isinstance(response, dict):
            raise ValueError("Create operation returned invalid response")

        # Fetch the full object by name (POST response doesn't include UUID)
        return self.get(name=name)

    def create_nvidia_vgpu(
        self,
        name: str,
        driver_file: int,
        *,
        nvidia_vgpu_profile: int | None = None,
        make_guest_driver_iso: bool = False,
        driver_iso: int | None = None,
        scheduler_policy: Literal["1", "2", "3"] = "1",
        strict_round_robin: Literal["", "0", "1"] = "",
        frequency: int = 0,
        averaging_factor: int = 33,
        time_slice_length_ns: int = 0,
        description: str = "",
        enabled: bool = True,
        device_keys: builtins.list[int] | None = None,
    ) -> ResourceGroup:
        """Create an NVIDIA vGPU resource group.

        Args:
            name: Resource group name.
            driver_file: File key for the NVIDIA vGPU driver bundle.
            nvidia_vgpu_profile: vGPU profile key to use.
            make_guest_driver_iso: Auto-create guest driver ISO from bundle.
            driver_iso: Pre-existing guest driver ISO file key.
            scheduler_policy: vGPU scheduler policy (1=Best Effort, 2=Equal Share, 3=Fixed Share).
            strict_round_robin: Enable strict round robin ("", "0", "1").
            frequency: Scheduler frequency (0-960).
            averaging_factor: Averaging factor (1-60, default 33).
            time_slice_length_ns: Time slice length in nanoseconds (0-30000000).
            description: Resource group description.
            enabled: Whether the resource group is enabled.
            device_keys: List of PCI device keys to auto-create rules from.

        Returns:
            Created ResourceGroup object.

        Example:
            >>> group = client.resource_groups.create_nvidia_vgpu(
            ...     name="vGPU A100 Pool",
            ...     driver_file=driver.key,
            ...     nvidia_vgpu_profile=profile.key,
            ...     make_guest_driver_iso=True,
            ... )
        """
        settings: dict[str, Any] = {
            "driver_file": driver_file,
            "scheduler_policy": scheduler_policy,
            "strict_round_robin": strict_round_robin,
            "frequency": frequency,
            "averaging_factor": averaging_factor,
            "time_slice_length_ns": time_slice_length_ns,
        }

        if nvidia_vgpu_profile is not None:
            settings["nvidia_vgpu_profile"] = nvidia_vgpu_profile
        if make_guest_driver_iso:
            settings["make_guest_driver_iso"] = make_guest_driver_iso
        if driver_iso is not None:
            settings["driver_iso"] = driver_iso

        return self.create(
            name=name,
            device_type="node_nvidia_vgpu_devices",
            description=description,
            device_class="vgpu",
            enabled=enabled,
            settings=settings,
            device_keys=device_keys,
        )

    def create_usb(
        self,
        name: str,
        *,
        allow_guest_reset: bool = True,
        allow_guest_reset_all: bool = False,
        device_class: str = "usb",
        description: str = "",
        enabled: bool = True,
        device_keys: builtins.list[int] | None = None,
    ) -> ResourceGroup:
        """Create a USB device resource group.

        Args:
            name: Resource group name.
            allow_guest_reset: Allow VM to reset the USB device.
            allow_guest_reset_all: Allow VM to reset the USB hub.
            device_class: Device classification for UI icon.
            description: Resource group description.
            enabled: Whether the resource group is enabled.
            device_keys: List of USB device keys to auto-create rules from.

        Returns:
            Created ResourceGroup object.

        Example:
            >>> group = client.resource_groups.create_usb(
            ...     name="USB License Keys",
            ...     device_class="hid",
            ...     device_keys=[usb_device.key],
            ... )
        """
        settings = {
            "guest_reset": allow_guest_reset,
            "guest_resets_all": allow_guest_reset_all,
        }

        return self.create(
            name=name,
            device_type="node_usb_devices",
            description=description,
            device_class=device_class,
            enabled=enabled,
            settings=settings,
            device_keys=device_keys,
        )

    def create_sriov_nic(
        self,
        name: str,
        *,
        vf_count: int = 1,
        native_vlan: int = 0,
        vlan_qos: int = 0,
        vlan_protocol: Literal["802.1Q", "802.1ad"] = "802.1Q",
        max_tx_rate: int = 0,
        min_tx_rate: int = 0,
        trust: Literal["default", "on", "off"] = "off",
        spoof_checking: Literal["default", "on", "off"] = "on",
        query_rss: Literal["default", "on", "off"] = "default",
        virtual_link_state: Literal["default", "auto", "enable", "disable"] = "default",
        mac_allow_override: bool = True,
        vlan_allow_override: bool = False,
        qos_allow_override: bool = False,
        proto_allow_override: bool = False,
        max_tx_rate_allow_override: bool = False,
        min_tx_rate_allow_override: bool = False,
        trust_allow_override: bool = False,
        spoofchk_allow_override: bool = False,
        query_rss_allow_override: bool = False,
        state_allow_override: bool = False,
        description: str = "",
        enabled: bool = True,
        device_keys: builtins.list[int] | None = None,
    ) -> ResourceGroup:
        """Create an SR-IOV NIC resource group.

        Args:
            name: Resource group name.
            vf_count: Number of VFs to create per physical device.
            native_vlan: Default VLAN tag (0 disables VLAN tagging).
            vlan_qos: VLAN QOS priority (0-7).
            vlan_protocol: VLAN protocol (802.1Q or 802.1ad for QinQ).
            max_tx_rate: Maximum transmit bandwidth in Mbps (0 disables).
            min_tx_rate: Minimum transmit bandwidth in Mbps (0 disables).
            trust: Enable VF trust mode for special features.
            spoof_checking: Enable MAC spoof checking.
            query_rss: Allow querying RSS configuration.
            virtual_link_state: Virtual link state (auto mirrors PF state).
            mac_allow_override: Allow VMs to override MAC address.
            vlan_allow_override: Allow VMs to override VLAN.
            qos_allow_override: Allow VMs to override QOS.
            proto_allow_override: Allow VMs to override protocol.
            max_tx_rate_allow_override: Allow VMs to override max TX rate.
            min_tx_rate_allow_override: Allow VMs to override min TX rate.
            trust_allow_override: Allow VMs to override trust.
            spoofchk_allow_override: Allow VMs to override spoof checking.
            query_rss_allow_override: Allow VMs to override query RSS.
            state_allow_override: Allow VMs to override link state.
            description: Resource group description.
            enabled: Whether the resource group is enabled.
            device_keys: List of PCI device keys to auto-create rules from.

        Returns:
            Created ResourceGroup object.

        Example:
            >>> group = client.resource_groups.create_sriov_nic(
            ...     name="SR-IOV NIC Pool",
            ...     vf_count=8,
            ...     native_vlan=100,
            ...     device_keys=[pci_device.key],
            ... )
        """
        settings = {
            "numvfs": vf_count,
            "vlan": native_vlan,
            "qos": vlan_qos,
            "proto": vlan_protocol,
            "max_tx_rate": max_tx_rate,
            "min_tx_rate": min_tx_rate,
            "trust": trust,
            "spoofchk": spoof_checking,
            "query_rss": query_rss,
            "state": virtual_link_state,
            "macaddress_allow_override": mac_allow_override,
            "vlan_allow_override": vlan_allow_override,
            "qos_allow_override": qos_allow_override,
            "proto_allow_override": proto_allow_override,
            "max_tx_rate_allow_override": max_tx_rate_allow_override,
            "min_tx_rate_allow_override": min_tx_rate_allow_override,
            "trust_allow_override": trust_allow_override,
            "spoofchk_allow_override": spoofchk_allow_override,
            "query_rss_allow_override": query_rss_allow_override,
            "state_allow_override": state_allow_override,
        }

        return self.create(
            name=name,
            device_type="node_sriov_nic_devices",
            description=description,
            device_class="network",
            enabled=enabled,
            settings=settings,
            device_keys=device_keys,
        )

    def create_pci(
        self,
        name: str,
        *,
        device_class: str = "pci",
        description: str = "",
        enabled: bool = True,
        device_keys: builtins.list[int] | None = None,
    ) -> ResourceGroup:
        """Create a PCI passthrough resource group.

        Args:
            name: Resource group name.
            device_class: Device classification for UI icon (gpu, storage, network, pci, etc.).
            description: Resource group description.
            enabled: Whether the resource group is enabled.
            device_keys: List of PCI device keys to auto-create rules from.

        Returns:
            Created ResourceGroup object.

        Example:
            >>> group = client.resource_groups.create_pci(
            ...     name="NVMe Controllers",
            ...     device_class="storage",
            ...     device_keys=[pci_device.key],
            ... )
        """
        return self.create(
            name=name,
            device_type="node_pci_devices",
            description=description,
            device_class=device_class,
            enabled=enabled,
            device_keys=device_keys,
        )

    def create_host_gpu(
        self,
        name: str,
        *,
        description: str = "",
        enabled: bool = True,
        device_keys: builtins.list[int] | None = None,
    ) -> ResourceGroup:
        """Create a host GPU passthrough resource group.

        Args:
            name: Resource group name.
            description: Resource group description.
            enabled: Whether the resource group is enabled.
            device_keys: List of GPU device keys to auto-create rules from.

        Returns:
            Created ResourceGroup object.

        Example:
            >>> group = client.resource_groups.create_host_gpu(
            ...     name="GPU Passthrough Pool",
            ...     device_keys=[gpu_device.key],
            ... )
        """
        return self.create(
            name=name,
            device_type="node_host_gpu_devices",
            description=description,
            device_class="gpu",
            enabled=enabled,
            device_keys=device_keys,
        )

    def update(self, key: str, **kwargs: Any) -> ResourceGroup:  # type: ignore[override]
        """Update a resource group.

        Args:
            key: Resource group UUID.
            **kwargs: Fields to update. Common fields:
                - name: Resource group name
                - description: Description
                - enabled: Whether enabled
                - settings_args: Type-specific settings dict

        Returns:
            Updated ResourceGroup object.

        Example:
            >>> group = client.resource_groups.update(
            ...     group.key,
            ...     name="Renamed Pool",
            ...     enabled=False,
            ... )
        """
        response = self._client._request("PUT", f"{self._endpoint}/{key}", json_data=kwargs)
        if response is None:
            return self.get(key)
        if not isinstance(response, dict):
            return self.get(key)
        return self._to_model(response)

    def delete(self, key: str) -> None:  # type: ignore[override]
        """Delete a resource group.

        Args:
            key: Resource group UUID.

        Raises:
            ConflictError: If there are machine devices using this group.

        Note:
            All machine devices using this resource group must be removed first.
        """
        self._client._request("DELETE", f"{self._endpoint}/{key}")

    @property
    def rules(self) -> ResourceRuleManager:
        """Access resource rules globally (unscoped).

        Returns:
            ResourceRuleManager for all resource rules.

        Example:
            >>> # List all resource rules
            >>> rules = client.resource_groups.rules.list()
        """
        return ResourceRuleManager(self._client)


# =============================================================================
# Resource Rules
# =============================================================================


class ResourceRule(ResourceObject):
    """Resource rule that defines which devices belong to a resource group.

    Resource rules use filter expressions to match devices by attributes
    such as vendor, slot, serial number, etc.
    """

    @property
    def resource_group_key(self) -> int | None:
        """Parent resource group key."""
        rg = self.get("resource_group")
        return int(rg) if rg else None

    @property
    def resource_group_name(self) -> str:
        """Parent resource group name."""
        return str(self.get("resource_group_display", ""))

    @property
    def name(self) -> str:
        """Rule name."""
        return str(self.get("name", ""))

    @property
    def is_enabled(self) -> bool:
        """Whether the rule is enabled."""
        return bool(self.get("enabled", True))

    @property
    def device_type(self) -> str:
        """Device type (raw API value)."""
        return str(self.get("type", ""))

    @property
    def device_type_display(self) -> str:
        """Human-readable device type."""
        type_display = self.get("type_display")
        if type_display:
            return str(type_display)
        return DEVICE_TYPE_MAP.get(self.device_type, self.device_type)

    @property
    def node_key(self) -> int | None:
        """Node filter (None = all nodes)."""
        node = self.get("node")
        return int(node) if node else None

    @property
    def node_name(self) -> str:
        """Node name filter."""
        return str(self.get("node_display", ""))

    @property
    def filter_expression(self) -> str:
        """OData-style filter expression for matching devices."""
        return str(self.get("filter", ""))

    @property
    def filter_configuration(self) -> dict[str, Any]:
        """Structured filter configuration."""
        config = self.get("filter_configuration")
        return config if isinstance(config, dict) else {}

    @property
    def resource_count(self) -> int:
        """Number of devices matched by this rule."""
        return int(self.get("resource_count", 0))

    @property
    def is_system_created(self) -> bool:
        """Whether this rule was auto-generated by the system."""
        return bool(self.get("system_created", False))

    @property
    def modified_at(self) -> datetime | None:
        """Last modification timestamp."""
        ts = self.get("modified")
        if ts:
            return datetime.fromtimestamp(int(ts), tz=timezone.utc)
        return None

    def refresh(self) -> ResourceRule:
        """Refresh this rule's data from the server."""
        from typing import cast

        manager = cast("ResourceRuleManager", self._manager)
        return manager.get(self.key)

    def save(self, **kwargs: Any) -> ResourceRule:
        """Update this rule with the given values."""
        from typing import cast

        manager = cast("ResourceRuleManager", self._manager)
        return manager.update(self.key, **kwargs)

    def delete(self) -> None:
        """Delete this rule."""
        from typing import cast

        manager = cast("ResourceRuleManager", self._manager)
        manager.delete(self.key)

    def __repr__(self) -> str:
        return (
            f"<ResourceRule key={self.get('$key')} name={self.name!r} "
            f"type={self.device_type_display!r} resources={self.resource_count}>"
        )


class ResourceRuleManager(ResourceManager[ResourceRule]):
    """Manages resource rules for device passthrough.

    Resource rules define which physical devices belong to a resource group
    using filter expressions that match device attributes.

    Example:
        >>> # List all rules for a resource group
        >>> rules = resource_group.rules.list()

        >>> # Create a rule matching devices by vendor
        >>> rule = resource_group.rules.create(
        ...     name="Intel NICs",
        ...     filter="vendor ct 'Intel'",
        ... )

        >>> # Create a rule for a specific PCI slot
        >>> rule = resource_group.rules.create(
        ...     name="GPU in slot 3",
        ...     filter="slot eq '03:00.0'",
        ...     node=node.key,
        ... )
    """

    _endpoint = "resource_rules"

    _default_fields = [
        "$key",
        "resource_group",
        "display(resource_group) as resource_group_display",
        "name",
        "enabled",
        "type",
        "display(type) as type_display",
        "node",
        "display(node) as node_display",
        "filter",
        "filter_configuration",
        "count(resources) as resource_count",
        "system_created",
        "modified",
    ]

    def __init__(self, client: VergeClient, resource_group_key: str | int | None = None) -> None:
        super().__init__(client)
        self._resource_group_key = resource_group_key

    def _to_model(self, data: dict[str, Any]) -> ResourceRule:
        return ResourceRule(data, self)

    def list(  # noqa: A003
        self,
        filter: str | None = None,  # noqa: A002
        fields: builtins.list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        *,
        node_key: int | None = None,
        enabled_only: bool = False,
        **filter_kwargs: Any,
    ) -> builtins.list[ResourceRule]:
        """List resource rules.

        Args:
            filter: OData filter string.
            fields: List of fields to return.
            limit: Maximum number of results.
            offset: Skip this many results.
            node_key: Filter by node.
            enabled_only: Only return enabled rules.
            **filter_kwargs: Shorthand filter arguments.

        Returns:
            List of ResourceRule objects.
        """
        if fields is None:
            fields = self._default_fields

        filters = []

        if filter:
            filters.append(filter)

        if self._resource_group_key is not None:
            # Resource groups use UUID strings, which need quotes in filters
            rg_key = str(self._resource_group_key)
            if "-" in rg_key:  # UUID format needs quotes
                filters.append(f"resource_group eq '{rg_key}'")
            else:  # Integer key (for backwards compatibility)
                filters.append(f"resource_group eq {rg_key}")

        if node_key is not None:
            filters.append(f"node eq {node_key}")

        if enabled_only:
            filters.append("enabled eq true")

        if filter_kwargs:
            from pyvergeos.filters import build_filter

            filters.append(build_filter(**filter_kwargs))

        params: dict[str, Any] = {"fields": ",".join(fields)}

        if filters:
            params["filter"] = " and ".join(filters)
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

    def get(
        self,
        key: int | None = None,
        *,
        name: str | None = None,
        fields: builtins.list[str] | None = None,
    ) -> ResourceRule:
        """Get a resource rule by key or name.

        Args:
            key: Rule $key (ID).
            name: Rule name.
            fields: List of fields to return.

        Returns:
            ResourceRule object.

        Raises:
            NotFoundError: If rule not found.
            ValueError: If no identifier provided.
        """
        if fields is None:
            fields = self._default_fields

        if key is not None:
            params: dict[str, Any] = {"fields": ",".join(fields)}
            response = self._client._request("GET", f"{self._endpoint}/{key}", params=params)
            if response is None:
                raise NotFoundError(f"Resource rule with key {key} not found")
            if not isinstance(response, dict):
                raise NotFoundError(f"Resource rule with key {key} returned invalid response")
            return self._to_model(response)

        if name is not None:
            escaped_name = name.replace("'", "''")
            results = self.list(filter=f"name eq '{escaped_name}'", fields=fields, limit=1)
            if not results:
                raise NotFoundError(f"Resource rule with name '{name}' not found")
            return results[0]

        raise ValueError("Either key or name must be provided")

    def create(  # type: ignore[override]
        self,
        name: str,
        filter_expression: str,
        *,
        node: int | None = None,
        enabled: bool = True,
        auto_create_from_device: int | None = None,
    ) -> ResourceRule:
        """Create a new resource rule.

        Args:
            name: Rule name.
            filter_expression: OData-style filter for matching devices.
                Examples: "vendor ct 'Intel'", "slot eq '03:00.0'",
                "vendor_device_hex eq '8086:8c31'"
            node: Restrict to a specific node (None = all nodes).
            enabled: Whether the rule is enabled.
            auto_create_from_device: Device key to auto-generate filter from.

        Returns:
            Created ResourceRule object.

        Raises:
            ValueError: If not scoped to a resource group.

        Example:
            >>> rule = group.rules.create(
            ...     name="Intel X710 NICs",
            ...     filter_expression="vendor ct 'Intel' and device ct 'X710'",
            ... )
        """
        if self._resource_group_key is None:
            raise ValueError(
                "Must use a scoped ResourceRuleManager to create rules. "
                "Access via resource_group.rules.create()"
            )

        body: dict[str, Any] = {
            "resource_group": self._resource_group_key,
            "name": name,
            "filter": filter_expression,
            "enabled": enabled,
        }

        if node is not None:
            body["node"] = node
        if auto_create_from_device is not None:
            body["auto_create_based_on"] = auto_create_from_device

        response = self._client._request("POST", self._endpoint, json_data=body)
        if response is None:
            raise ValueError("No response from create operation")
        if not isinstance(response, dict):
            raise ValueError("Create operation returned invalid response")

        rule = self._to_model(response)
        return self.get(rule.key)

    def update(self, key: int, **kwargs: Any) -> ResourceRule:
        """Update a resource rule.

        Args:
            key: Rule $key (ID).
            **kwargs: Fields to update. Common fields:
                - name: Rule name
                - filter: Filter expression
                - node: Node filter (None = all nodes)
                - enabled: Whether enabled

        Returns:
            Updated ResourceRule object.
        """
        response = self._client._request("PUT", f"{self._endpoint}/{key}", json_data=kwargs)
        if response is None:
            return self.get(key)
        if not isinstance(response, dict):
            return self.get(key)
        return self._to_model(response)

    def delete(self, key: int) -> None:
        """Delete a resource rule.

        Args:
            key: Rule $key (ID).
        """
        self._client._request("DELETE", f"{self._endpoint}/{key}")
