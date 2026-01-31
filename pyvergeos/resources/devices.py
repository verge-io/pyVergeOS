"""VM Device resource manager for device passthrough.

This module provides management of hardware devices attached to VMs,
including GPU passthrough, NVIDIA vGPU, USB, PCI, SR-IOV NICs, and TPM.

Example:
    >>> # List devices attached to a VM
    >>> devices = vm.devices.list()
    >>> for device in devices:
    ...     print(f"{device.name}: {device.device_type}")

    >>> # Attach a vGPU to a VM
    >>> device = vm.devices.create_vgpu(
    ...     resource_group=vgpu_pool.key,
    ...     frame_rate_limit=60,
    ...     attach_guest_drivers=True,
    ... )

    >>> # Attach a USB device
    >>> device = vm.devices.create_usb(
    ...     resource_group=usb_pool.key,
    ...     allow_guest_reset=True,
    ... )
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


# Device type display mappings
DEVICE_TYPE_DISPLAY = {
    "gpu": "GPU Passthrough (Legacy)",
    "nvidia_vgpu": "NVIDIA vGPU (Legacy)",
    "tpm": "Trusted Platform Module (vTPM)",
    "node_usb_devices": "USB",
    "node_sriov_nic_devices": "SR-IOV NIC",
    "node_pci_devices": "PCI",
    "node_host_gpu_devices": "Host GPU",
    "node_nvidia_vgpu_devices": "NVIDIA vGPU",
}

# Device status display mappings
DEVICE_STATUS_DISPLAY = {
    "online": "Online",
    "offline": "Offline",
    "errors": "Errors",
    "warning": "Warning",
    "hotplug": "Hot plugging",
    "initializing": "Initializing",
    "missing": "Missing",
    "idle": "Idle",
}


class Device(ResourceObject):
    """VM device resource object.

    Represents a hardware device attached to a VM (GPU, TPM, USB, PCI, SR-IOV, etc.).

    Example:
        >>> device = vm.devices.get(name="vGPU-1")
        >>> print(f"Type: {device.device_type}, Status: {device.status}")
    """

    @property
    def machine_key(self) -> int:
        """Parent machine (VM) key."""
        return int(self.get("machine", 0))

    @property
    def machine_name(self) -> str:
        """Parent machine (VM) name."""
        return str(self.get("machine_name", ""))

    @property
    def machine_type(self) -> str:
        """Machine type (vm, node, etc.)."""
        return str(self.get("machine_type", ""))

    @property
    def name(self) -> str:
        """Device name."""
        return str(self.get("name", ""))

    @property
    def description(self) -> str:
        """Device description."""
        return str(self.get("description", ""))

    @property
    def device_type(self) -> str:
        """Device type (human-readable)."""
        raw = str(self.get("type", ""))
        return DEVICE_TYPE_DISPLAY.get(raw, raw)

    @property
    def device_type_raw(self) -> str:
        """Raw device type value."""
        return str(self.get("type", ""))

    @property
    def orderid(self) -> int:
        """Device order ID."""
        return int(self.get("orderid", 0))

    @property
    def uuid(self) -> str:
        """Device UUID."""
        return str(self.get("uuid", ""))

    @property
    def is_enabled(self) -> bool:
        """Check if device is enabled."""
        return bool(self.get("enabled", True))

    @property
    def is_optional(self) -> bool:
        """Check if device is optional (machine can start without it)."""
        return bool(self.get("optional", False))

    @property
    def resource_group_key(self) -> int | None:
        """Associated resource group key."""
        rg = self.get("resource_group")
        return int(rg) if rg else None

    @property
    def resource_group_name(self) -> str:
        """Associated resource group name."""
        return str(self.get("resource_group_name", ""))

    @property
    def status(self) -> str:
        """Device status (human-readable)."""
        raw = str(self.get("device_status", ""))
        return DEVICE_STATUS_DISPLAY.get(raw, raw)

    @property
    def status_raw(self) -> str:
        """Raw device status value."""
        return str(self.get("device_status", ""))

    @property
    def status_info(self) -> str:
        """Additional status information."""
        return str(self.get("status_info", ""))

    @property
    def created_at(self) -> datetime | None:
        """Timestamp when device was created."""
        ts = self.get("created")
        if ts:
            return datetime.fromtimestamp(int(ts), tz=timezone.utc)
        return None

    @property
    def modified_at(self) -> datetime | None:
        """Timestamp when device was last modified."""
        ts = self.get("modified")
        if ts:
            return datetime.fromtimestamp(int(ts), tz=timezone.utc)
        return None

    @property
    def is_gpu(self) -> bool:
        """Check if this is a GPU device (passthrough or vGPU)."""
        return self.device_type_raw in (
            "gpu",
            "node_host_gpu_devices",
            "nvidia_vgpu",
            "node_nvidia_vgpu_devices",
        )

    @property
    def is_vgpu(self) -> bool:
        """Check if this is an NVIDIA vGPU device."""
        return self.device_type_raw in ("nvidia_vgpu", "node_nvidia_vgpu_devices")

    @property
    def is_host_gpu(self) -> bool:
        """Check if this is a host GPU passthrough device."""
        return self.device_type_raw in ("gpu", "node_host_gpu_devices")

    @property
    def is_tpm(self) -> bool:
        """Check if this is a TPM device."""
        return self.device_type_raw == "tpm"

    @property
    def is_usb(self) -> bool:
        """Check if this is a USB device."""
        return self.device_type_raw == "node_usb_devices"

    @property
    def is_pci(self) -> bool:
        """Check if this is a PCI device."""
        return self.device_type_raw == "node_pci_devices"

    @property
    def is_sriov(self) -> bool:
        """Check if this is an SR-IOV NIC device."""
        return self.device_type_raw == "node_sriov_nic_devices"

    def refresh(self) -> Device:
        """Refresh this device's data from the server.

        Returns:
            Updated Device object.
        """
        from typing import cast

        manager = cast("DeviceManager", self._manager)
        return manager.get(self.key)

    def save(self, **kwargs: Any) -> Device:
        """Update this device with the given values.

        Args:
            **kwargs: Fields to update.

        Returns:
            Updated Device object.
        """
        from typing import cast

        manager = cast("DeviceManager", self._manager)
        return manager.update(self.key, **kwargs)

    def delete(self) -> None:
        """Delete this device.

        Note:
            Machine should typically be powered off before removing devices.
        """
        from typing import cast

        manager = cast("DeviceManager", self._manager)
        manager.delete(self.key)

    def __repr__(self) -> str:
        return (
            f"<Device key={self.get('$key', '?')} name={self.name!r} type={self.device_type_raw}>"
        )


class DeviceManager(ResourceManager[Device]):
    """Manager for VM device operations.

    Provides CRUD operations for hardware devices attached to VMs,
    including GPU passthrough, NVIDIA vGPU, USB, PCI, and SR-IOV NICs.

    Example:
        >>> # List all devices on a VM
        >>> for device in vm.devices.list():
        ...     print(f"{device.name}: {device.device_type}")

        >>> # Attach a vGPU
        >>> device = vm.devices.create_vgpu(
        ...     resource_group=vgpu_pool.key,
        ...     frame_rate_limit=60,
        ... )

        >>> # Attach a USB device
        >>> device = vm.devices.create_usb(
        ...     resource_group=usb_pool.key,
        ... )
    """

    _endpoint = "machine_devices"

    _default_fields = [
        "$key",
        "machine",
        "machine#name as machine_name",
        "machine_type",
        "name",
        "description",
        "type",
        "orderid",
        "uuid",
        "enabled",
        "optional",
        "resource_group",
        "resource_group#name as resource_group_name",
        "status#status as device_status",
        "status#status_info as status_info",
        "created",
        "modified",
    ]

    def __init__(self, client: VergeClient, machine_key: int) -> None:
        super().__init__(client)
        self._machine_key = machine_key

    def _to_model(self, data: dict[str, Any]) -> Device:
        return Device(data, self)

    def list(
        self,
        filter: str | None = None,  # noqa: A002
        fields: builtins.list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        *,
        device_type: Literal[
            "gpu",
            "nvidia_vgpu",
            "tpm",
            "node_usb_devices",
            "node_sriov_nic_devices",
            "node_pci_devices",
            "node_host_gpu_devices",
            "node_nvidia_vgpu_devices",
        ]
        | None = None,
        enabled_only: bool = False,
        **filter_kwargs: Any,
    ) -> builtins.list[Device]:
        """List devices attached to this machine.

        Args:
            filter: OData filter string.
            fields: List of fields to return.
            limit: Maximum number of results.
            offset: Skip this many results.
            device_type: Filter by device type.
            enabled_only: Only return enabled devices.
            **filter_kwargs: Additional filter arguments.

        Returns:
            List of Device objects.

        Example:
            >>> # List all devices
            >>> devices = vm.devices.list()

            >>> # List vGPUs only
            >>> vgpus = vm.devices.list(device_type="node_nvidia_vgpu_devices")

            >>> # List enabled devices
            >>> enabled = vm.devices.list(enabled_only=True)
        """
        if fields is None:
            fields = self._default_fields

        filters = [f"machine eq {self._machine_key}"]

        if filter:
            filters.append(filter)

        if device_type is not None:
            filters.append(f"type eq '{device_type}'")

        if enabled_only:
            filters.append("enabled eq true")

        if filter_kwargs:
            filters.append(build_filter(**filter_kwargs))

        params: dict[str, Any] = {
            "filter": " and ".join(filters),
            "fields": ",".join(fields),
            "sort": "+orderid",
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

    def get(
        self,
        key: int | None = None,
        *,
        name: str | None = None,
        fields: builtins.list[str] | None = None,
    ) -> Device:
        """Get a specific device by key or name.

        Args:
            key: Device $key (ID).
            name: Device name.
            fields: List of fields to return.

        Returns:
            Device object.

        Raises:
            NotFoundError: If device not found.
            ValueError: If neither key nor name provided.
        """
        if fields is None:
            fields = self._default_fields

        if key is not None:
            params: dict[str, Any] = {"fields": ",".join(fields)}
            response = self._client._request("GET", f"{self._endpoint}/{key}", params=params)

            if response is None:
                raise NotFoundError(f"Device {key} not found")
            if not isinstance(response, dict):
                raise NotFoundError(f"Device {key} returned invalid response")
            return self._to_model(response)

        if name is not None:
            escaped = name.replace("'", "''")
            devices = self.list(filter=f"name eq '{escaped}'", fields=fields, limit=1)
            if not devices:
                raise NotFoundError(f"Device with name '{name}' not found")
            return devices[0]

        raise ValueError("Either key or name must be provided")

    def create(  # type: ignore[override]
        self,
        device_type: Literal[
            "gpu",
            "nvidia_vgpu",
            "tpm",
            "node_usb_devices",
            "node_sriov_nic_devices",
            "node_pci_devices",
            "node_host_gpu_devices",
            "node_nvidia_vgpu_devices",
        ],
        name: str | None = None,
        description: str = "",
        enabled: bool = True,
        optional: bool = False,
        resource_group: int | None = None,
        count: int = 1,
        settings: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> Device:
        """Create a new device for this machine.

        Args:
            device_type: Type of device to create.
            name: Device name (auto-generated if not provided).
            description: Device description.
            enabled: Whether device is enabled.
            optional: Allow machine to start without this device.
            resource_group: Resource group key for the device.
            count: Number of devices to create from the resource group.
            settings: Device-specific settings (passed as settings_args).
            **kwargs: Additional device fields.

        Returns:
            Created Device object.

        Example:
            >>> device = vm.devices.create(
            ...     device_type="node_nvidia_vgpu_devices",
            ...     resource_group=vgpu_pool.key,
            ...     settings={"frame_rate_limiter": 60}
            ... )
        """
        body: dict[str, Any] = {
            "machine": self._machine_key,
            "type": device_type,
            "enabled": enabled,
            "optional": optional,
        }

        if name:
            body["name"] = name
        if description:
            body["description"] = description
        if resource_group is not None:
            body["resource_group"] = resource_group
        if count > 1:
            body["count"] = count
        if settings:
            body["settings_args"] = settings

        body.update(kwargs)

        response = self._client._request("POST", self._endpoint, json_data=body)
        if response is None:
            raise ValueError("No response from create operation")
        if not isinstance(response, dict):
            raise ValueError("Create operation returned invalid response")

        device = self._to_model(response)
        return self.get(device.key)

    def create_vgpu(
        self,
        resource_group: int,
        name: str | None = None,
        *,
        frame_rate_limit: int = 60,
        attach_guest_drivers: bool = False,
        disable_console_vnc: bool = False,
        enable_unified_memory: bool = False,
        enable_cuda_debuggers: bool = False,
        enable_cuda_profilers: bool = False,
        profile_type: str = "any",
        enabled: bool = True,
        optional: bool = False,
        count: int = 1,
    ) -> Device:
        """Create an NVIDIA vGPU device.

        Args:
            resource_group: Resource group key for the vGPU pool.
            name: Device name (auto-generated if not provided).
            frame_rate_limit: Frame rate limiter (0 to disable, default 60).
            attach_guest_drivers: Attach guest drivers ISO to this machine.
            disable_console_vnc: Disable VNC console (use RDP instead).
            enable_unified_memory: Enable NVIDIA unified memory.
            enable_cuda_debuggers: Enable NVIDIA CUDA Toolkit debuggers.
            enable_cuda_profilers: Enable NVIDIA CUDA Toolkit profilers.
            profile_type: vGPU profile type filter (default "any").
            enabled: Whether device is enabled.
            optional: Allow machine to start without this device.
            count: Number of vGPU devices to attach.

        Returns:
            Created Device object.

        Example:
            >>> device = vm.devices.create_vgpu(
            ...     resource_group=vgpu_pool.key,
            ...     frame_rate_limit=0,  # Compute only, no graphics
            ...     attach_guest_drivers=True,
            ... )
        """
        settings = {
            "frame_rate_limiter": frame_rate_limit,
            "attach_drivers": attach_guest_drivers,
            "disable_vnc": disable_console_vnc,
            "enable_uvm": enable_unified_memory,
            "enable_debugging": enable_cuda_debuggers,
            "enable_profiling": enable_cuda_profilers,
            "profile_type": profile_type,
        }

        return self.create(
            device_type="node_nvidia_vgpu_devices",
            name=name,
            resource_group=resource_group,
            enabled=enabled,
            optional=optional,
            count=count,
            settings=settings,
        )

    def create_host_gpu(
        self,
        resource_group: int,
        name: str | None = None,
        *,
        enabled: bool = True,
        optional: bool = False,
        count: int = 1,
    ) -> Device:
        """Create a host GPU passthrough device.

        This provides full GPU passthrough to a single VM (1:1 mapping).

        Args:
            resource_group: Resource group key for the host GPU pool.
            name: Device name (auto-generated if not provided).
            enabled: Whether device is enabled.
            optional: Allow machine to start without this device.
            count: Number of GPUs to attach from the pool.

        Returns:
            Created Device object.

        Example:
            >>> device = vm.devices.create_host_gpu(
            ...     resource_group=gpu_pool.key,
            ... )
        """
        return self.create(
            device_type="node_host_gpu_devices",
            name=name,
            resource_group=resource_group,
            enabled=enabled,
            optional=optional,
            count=count,
        )

    def create_usb(
        self,
        resource_group: int,
        name: str | None = None,
        *,
        allow_guest_reset: bool = True,
        allow_guest_reset_all: bool = False,
        enabled: bool = True,
        optional: bool = False,
    ) -> Device:
        """Create a USB passthrough device.

        Args:
            resource_group: Resource group key for the USB device pool.
            name: Device name (auto-generated if not provided).
            allow_guest_reset: Allow VM to reset the USB device.
            allow_guest_reset_all: Allow VM to reset the USB hub.
            enabled: Whether device is enabled.
            optional: Allow machine to start without this device.

        Returns:
            Created Device object.

        Example:
            >>> device = vm.devices.create_usb(
            ...     resource_group=usb_pool.key,
            ...     allow_guest_reset=True,
            ... )
        """
        settings = {
            "guest_reset": allow_guest_reset,
            "guest_resets_all": allow_guest_reset_all,
        }

        return self.create(
            device_type="node_usb_devices",
            name=name,
            resource_group=resource_group,
            enabled=enabled,
            optional=optional,
            settings=settings,
        )

    def create_pci(
        self,
        resource_group: int,
        name: str | None = None,
        *,
        enabled: bool = True,
        optional: bool = False,
        count: int = 1,
    ) -> Device:
        """Create a PCI passthrough device.

        Args:
            resource_group: Resource group key for the PCI device pool.
            name: Device name (auto-generated if not provided).
            enabled: Whether device is enabled.
            optional: Allow machine to start without this device.
            count: Number of PCI devices to attach from the pool.

        Returns:
            Created Device object.

        Example:
            >>> device = vm.devices.create_pci(
            ...     resource_group=pci_pool.key,
            ...     count=2,
            ... )
        """
        return self.create(
            device_type="node_pci_devices",
            name=name,
            resource_group=resource_group,
            enabled=enabled,
            optional=optional,
            count=count,
        )

    def create_sriov_nic(
        self,
        resource_group: int,
        name: str | None = None,
        *,
        mac_address: str | None = None,
        native_vlan: int = 0,
        vlan_qos: int = 0,
        vlan_protocol: Literal["802.1Q", "802.1ad"] = "802.1Q",
        max_tx_rate: int = 0,
        min_tx_rate: int = 0,
        trust: Literal["default", "on", "off"] = "off",
        spoof_checking: Literal["default", "on", "off"] = "on",
        query_rss: Literal["default", "on", "off"] = "default",
        virtual_link_state: Literal["default", "auto", "enable", "disable"] = "default",
        enabled: bool = True,
        optional: bool = False,
        count: int = 1,
    ) -> Device:
        """Create an SR-IOV NIC device.

        Args:
            resource_group: Resource group key for the SR-IOV NIC pool.
            name: Device name (auto-generated if not provided).
            mac_address: MAC address (auto-generated if not provided).
            native_vlan: VLAN tag (0 disables VLAN tagging).
            vlan_qos: VLAN QOS priority (0-7).
            vlan_protocol: VLAN protocol (802.1Q or 802.1ad for QinQ).
            max_tx_rate: Maximum transmit bandwidth in Mbps (0 disables).
            min_tx_rate: Minimum transmit bandwidth in Mbps (0 disables).
            trust: Enable VF trust mode for special features.
            spoof_checking: Enable MAC spoof checking.
            query_rss: Allow querying RSS configuration.
            virtual_link_state: Virtual link state (auto mirrors PF state).
            enabled: Whether device is enabled.
            optional: Allow machine to start without this device.
            count: Number of SR-IOV VFs to attach.

        Returns:
            Created Device object.

        Example:
            >>> device = vm.devices.create_sriov_nic(
            ...     resource_group=sriov_pool.key,
            ...     native_vlan=100,
            ...     max_tx_rate=1000,  # 1 Gbps cap
            ... )
        """
        settings: dict[str, Any] = {
            "vlan": native_vlan,
            "qos": vlan_qos,
            "proto": vlan_protocol,
            "max_tx_rate": max_tx_rate,
            "min_tx_rate": min_tx_rate,
            "trust": trust,
            "spoofchk": spoof_checking,
            "query_rss": query_rss,
            "state": virtual_link_state,
        }

        if mac_address:
            settings["macaddress"] = mac_address

        return self.create(
            device_type="node_sriov_nic_devices",
            name=name,
            resource_group=resource_group,
            enabled=enabled,
            optional=optional,
            count=count,
            settings=settings,
        )

    def create_tpm(
        self,
        name: str | None = None,
        *,
        enabled: bool = True,
        optional: bool = False,
    ) -> Device:
        """Create a virtual TPM (Trusted Platform Module) device.

        TPM provides hardware-based security features for the VM.

        Args:
            name: Device name (auto-generated if not provided).
            enabled: Whether device is enabled.
            optional: Allow machine to start without this device.

        Returns:
            Created Device object.

        Example:
            >>> device = vm.devices.create_tpm()
        """
        return self.create(
            device_type="tpm",
            name=name,
            enabled=enabled,
            optional=optional,
        )

    def update(self, key: int, **kwargs: Any) -> Device:
        """Update a device.

        Args:
            key: Device $key (ID).
            **kwargs: Fields to update. Common fields:
                - name: Device name
                - description: Description
                - enabled: Whether enabled
                - optional: Whether optional
                - settings_args: Device-specific settings

        Returns:
            Updated Device object.

        Example:
            >>> device = vm.devices.update(
            ...     device.key,
            ...     enabled=False,
            ... )
        """
        response = self._client._request("PUT", f"{self._endpoint}/{key}", json_data=kwargs)
        if response is None:
            return self.get(key)
        if not isinstance(response, dict):
            return self.get(key)
        return self._to_model(response)

    def delete(self, key: int) -> None:
        """Delete a device.

        Args:
            key: Device $key (ID).

        Note:
            Machine should typically be powered off before removing devices.
        """
        self._client._request("DELETE", f"{self._endpoint}/{key}")
