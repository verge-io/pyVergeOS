"""Resource group management for VergeOS hardware device pools."""

from __future__ import annotations

import builtins
import logging
from datetime import datetime, timezone
from typing import Any

from pyvergeos.exceptions import NotFoundError
from pyvergeos.resources.base import ResourceManager, ResourceObject

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
    """

    @property
    def uuid(self) -> str:
        """Resource group UUID."""
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

    def __repr__(self) -> str:
        return (
            f"<ResourceGroup key={self.get('$key')} name={self.name!r} "
            f"type={self.device_type_display!r} class={self.device_class_display!r}>"
        )


class ResourceGroupManager(ResourceManager[ResourceGroup]):
    """Manages resource groups in VergeOS.

    Resource groups define collections of hardware devices (GPU, PCI, USB,
    SR-IOV NIC, vGPU) that can be assigned to VMs for device passthrough.

    Note:
        Resource groups are read-only in this SDK. They are typically configured
        through the VergeOS UI and associate physical devices with virtual machines.

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
        key: int | None = None,
        *,
        name: str | None = None,
        uuid: str | None = None,
        fields: builtins.list[str] | None = None,
    ) -> ResourceGroup:
        """Get a resource group by key, name, or UUID.

        Args:
            key: Resource group $key (ID).
            name: Resource group name.
            uuid: Resource group UUID.
            fields: List of fields to return.

        Returns:
            ResourceGroup object.

        Raises:
            NotFoundError: If resource group not found.
            ValueError: If no identifier provided.

        Example:
            >>> # Get by key
            >>> rg = client.resource_groups.get(123)

            >>> # Get by name
            >>> rg = client.resource_groups.get(name="GPU Pool")

            >>> # Get by UUID
            >>> rg = client.resource_groups.get(uuid="12345678-1234-1234-1234-123456789abc")
        """
        if fields is None:
            fields = self._default_fields

        if key is not None:
            return super().get(key, fields=fields)

        if name is not None:
            # Search by name
            escaped_name = name.replace("'", "''")
            results = self.list(filter=f"name eq '{escaped_name}'", fields=fields, limit=1)
            if not results:
                raise NotFoundError(f"Resource group with name '{name}' not found")
            return results[0]

        if uuid is not None:
            # Search by UUID
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
