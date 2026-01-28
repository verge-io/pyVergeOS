"""Node resource manager."""

from __future__ import annotations

import builtins
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Literal

from pyvergeos.exceptions import NotFoundError
from pyvergeos.filters import build_filter
from pyvergeos.resources.base import ResourceManager, ResourceObject

if TYPE_CHECKING:
    from pyvergeos.client import VergeClient


# Status display mappings
STATUS_DISPLAY = {
    "running": "Running",
    "stopped": "Stopped",
    "online": "Online",
    "offline": "Offline",
    "maintenance": "Maintenance",
    "error": "Error",
    "warning": "Warning",
}

# Device type code mappings (PCI class codes)
DEVICE_TYPE_CODES = {
    "00": "Unclassified device",
    "01": "Mass storage controller",
    "02": "Network controller",
    "03": "Display controller",
    "04": "Multimedia controller",
    "05": "Memory controller",
    "06": "Bridge",
    "07": "Communication controller",
    "08": "Generic system peripheral",
    "09": "Input device controller",
    "0a": "Docking station",
    "0b": "Processor",
    "0c": "Serial bus controller",
    "0d": "Wireless controller",
    "0e": "Intelligent controller",
    "0f": "Satellite communications controller",
    "10": "Encryption controller",
    "11": "Signal processing controller",
    "12": "Processing accelerators",
    "13": "Non-Essential Instrumentation",
    "40": "Coprocessor",
    "ff": "Unassigned class",
}

# Driver status mappings
DRIVER_STATUS_DISPLAY = {
    "complete": "Installed",
    "verifying": "Verifying",
    "error": "Error",
}


class Node(ResourceObject):
    """Node resource object.

    Represents a VergeOS node with compute and storage capabilities.

    Example:
        >>> node = client.nodes.get(name="node1")
        >>> print(f"{node.name}: {node.status}")
        >>> print(f"  RAM: {node.ram_mb}MB, Cores: {node.cores}")
        >>> if node.is_maintenance:
        ...     print("  In maintenance mode")
    """

    @property
    def name(self) -> str:
        """Node hostname."""
        return str(self.get("name", ""))

    @property
    def description(self) -> str:
        """Node description."""
        return str(self.get("description", ""))

    @property
    def model(self) -> str:
        """Hardware model."""
        return str(self.get("model", ""))

    @property
    def cpu(self) -> str:
        """CPU model."""
        return str(self.get("cpu", ""))

    @property
    def cpu_speed(self) -> str:
        """CPU speed."""
        return str(self.get("cpu_speed", ""))

    @property
    def is_online(self) -> bool:
        """Check if node is online/running."""
        return bool(self.get("running", False))

    @property
    def is_maintenance(self) -> bool:
        """Check if node is in maintenance mode."""
        return bool(self.get("maintenance", False))

    @property
    def is_physical(self) -> bool:
        """Check if this is a physical node."""
        return bool(self.get("physical", False))

    @property
    def status(self) -> str:
        """Node status (Running, Stopped, Online, Offline, etc.)."""
        raw = str(self.get("status", ""))
        return STATUS_DISPLAY.get(raw, raw)

    @property
    def status_raw(self) -> str:
        """Raw status value."""
        return str(self.get("status", ""))

    @property
    def ram_mb(self) -> int:
        """Total RAM in MB."""
        return int(self.get("ram") or 0)

    @property
    def ram_gb(self) -> float:
        """Total RAM in GB."""
        return round(self.ram_mb / 1024, 2) if self.ram_mb else 0.0

    @property
    def vm_ram_mb(self) -> int:
        """RAM available for VMs in MB."""
        return int(self.get("vm_ram") or 0)

    @property
    def overcommit_ram_mb(self) -> int:
        """Overcommit RAM in MB."""
        return int(self.get("overcommit") or 0)

    @property
    def failover_ram_mb(self) -> int:
        """Failover RAM in MB."""
        return int(self.get("failover_ram") or 0)

    @property
    def cores(self) -> int:
        """Number of CPU cores."""
        return int(self.get("cores") or 0)

    @property
    def ram_used_mb(self) -> int:
        """Used physical RAM in MB."""
        return int(self.get("ram_used") or 0)

    @property
    def vram_used_mb(self) -> int:
        """Used virtual RAM in MB."""
        return int(self.get("vram_used") or 0)

    @property
    def cpu_usage(self) -> float:
        """CPU usage percentage."""
        return float(self.get("cpu_usage") or 0.0)

    @property
    def core_temp(self) -> float | None:
        """Core temperature in Celsius."""
        temp = self.get("core_temp")
        if temp is not None:
            return float(temp)
        return None

    @property
    def has_iommu(self) -> bool:
        """Check if IOMMU (VT-d) is supported."""
        return bool(self.get("iommu", False))

    @property
    def needs_restart(self) -> bool:
        """Check if node needs to be rebooted."""
        return bool(self.get("need_restart", False))

    @property
    def restart_reason(self) -> str:
        """Reason for needing reboot."""
        return str(self.get("restart_reason", ""))

    @property
    def vsan_node_id(self) -> int:
        """vSAN node ID."""
        return int(self.get("vsan_nodeid") or -1)

    @property
    def vsan_connected(self) -> bool:
        """Check if vSAN is connected."""
        return bool(self.get("vsan_connected", False))

    @property
    def cluster_key(self) -> int | None:
        """Parent cluster key."""
        cluster = self.get("cluster")
        if cluster:
            return int(cluster)
        return None

    @property
    def cluster_name(self) -> str:
        """Parent cluster name."""
        return str(self.get("cluster_name", ""))

    @property
    def machine_key(self) -> int | None:
        """Associated machine key."""
        machine = self.get("machine")
        if machine:
            return int(machine)
        return None

    @property
    def asset_tag(self) -> str:
        """Asset tag."""
        return str(self.get("asset_tag", ""))

    @property
    def ipmi_address(self) -> str:
        """IPMI address."""
        return str(self.get("ipmi_address", ""))

    @property
    def ipmi_status(self) -> str:
        """IPMI status."""
        return str(self.get("ipmi_status", ""))

    @property
    def vergeos_version(self) -> str:
        """VergeOS version (yb_version)."""
        return str(self.get("yb_version", ""))

    @property
    def os_version(self) -> str:
        """OS version."""
        return str(self.get("os_version", ""))

    @property
    def kernel_version(self) -> str:
        """Kernel version."""
        return str(self.get("kernel_version", ""))

    @property
    def appserver_version(self) -> str:
        """Appserver version."""
        return str(self.get("appserver_version", ""))

    @property
    def vsan_version(self) -> str:
        """vSAN version."""
        return str(self.get("vsan_version", ""))

    @property
    def qemu_version(self) -> str:
        """QEMU version."""
        return str(self.get("qemu_version", ""))

    @property
    def started_at(self) -> datetime | None:
        """Timestamp when node was started."""
        ts = self.get("started")
        if ts:
            return datetime.fromtimestamp(int(ts), tz=timezone.utc)
        return None

    def enable_maintenance(self) -> Node:
        """Enable maintenance mode on this node.

        Returns:
            Updated Node object.
        """
        from typing import cast

        manager = cast("NodeManager", self._manager)
        return manager.enable_maintenance(self.key)

    def disable_maintenance(self) -> Node:
        """Disable maintenance mode on this node.

        Returns:
            Updated Node object.
        """
        from typing import cast

        manager = cast("NodeManager", self._manager)
        return manager.disable_maintenance(self.key)

    def restart(self) -> dict[str, Any] | None:
        """Perform a maintenance reboot on this node.

        Returns:
            Task information dict or None.
        """
        from typing import cast

        manager = cast("NodeManager", self._manager)
        return manager.restart(self.key)

    @property
    def drivers(self) -> NodeDriverManager:
        """Access drivers for this node.

        Returns:
            NodeDriverManager scoped to this node.
        """
        from typing import cast

        manager = cast("NodeManager", self._manager)
        return manager.drivers(self.key)

    @property
    def pci_devices(self) -> NodePCIDeviceManager:
        """Access PCI devices for this node.

        Returns:
            NodePCIDeviceManager scoped to this node.
        """
        from typing import cast

        manager = cast("NodeManager", self._manager)
        return manager.pci_devices(self.key)

    @property
    def usb_devices(self) -> NodeUSBDeviceManager:
        """Access USB devices for this node.

        Returns:
            NodeUSBDeviceManager scoped to this node.
        """
        from typing import cast

        manager = cast("NodeManager", self._manager)
        return manager.usb_devices(self.key)

    def __repr__(self) -> str:
        return (
            f"<Node key={self.get('$key', '?')} name={self.name!r} "
            f"status={self.status} cores={self.cores} ram={self.ram_mb}MB>"
        )


class NodeDriver(ResourceObject):
    """Node driver resource object.

    Represents a driver installed on a VergeOS node.
    """

    @property
    def node_key(self) -> int | None:
        """Parent node key."""
        node = self.get("node")
        if node:
            return int(node)
        return None

    @property
    def node_name(self) -> str:
        """Parent node name."""
        return str(self.get("node_name", ""))

    @property
    def driver_name(self) -> str:
        """Driver name."""
        return str(self.get("driver_name", ""))

    @property
    def driver_key(self) -> str:
        """Driver key identifier."""
        return str(self.get("driver_key", ""))

    @property
    def driver_file_key(self) -> int | None:
        """Driver file key."""
        df = self.get("driver_file")
        if df:
            return int(df)
        return None

    @property
    def driver_file_name(self) -> str:
        """Driver file name."""
        return str(self.get("driver_file_name", ""))

    @property
    def description(self) -> str:
        """Driver description."""
        return str(self.get("description", ""))

    @property
    def status(self) -> str:
        """Driver status (Installed, Verifying, Error)."""
        raw = str(self.get("status", ""))
        return DRIVER_STATUS_DISPLAY.get(raw, raw)

    @property
    def status_raw(self) -> str:
        """Raw status value."""
        return str(self.get("status", ""))

    @property
    def status_info(self) -> str:
        """Status information message."""
        return str(self.get("status_info", ""))

    @property
    def class_filter(self) -> str:
        """Device class filter."""
        return str(self.get("class_filter", ""))

    @property
    def vendor_filter(self) -> str:
        """Vendor filter."""
        return str(self.get("vendor_filter", ""))

    @property
    def modified_at(self) -> datetime | None:
        """Timestamp when driver was last modified."""
        ts = self.get("modified")
        if ts:
            return datetime.fromtimestamp(int(ts), tz=timezone.utc)
        return None

    def __repr__(self) -> str:
        return (
            f"<NodeDriver key={self.get('$key', '?')} "
            f"name={self.driver_name!r} status={self.status}>"
        )


class NodePCIDevice(ResourceObject):
    """Node PCI device resource object.

    Represents a PCI device attached to a VergeOS node.
    """

    @property
    def node_key(self) -> int | None:
        """Parent node key."""
        node = self.get("node")
        if node:
            return int(node)
        return None

    @property
    def node_name(self) -> str:
        """Parent node name."""
        return str(self.get("node_name", ""))

    @property
    def name(self) -> str:
        """Device name."""
        return str(self.get("name", ""))

    @property
    def slot(self) -> str:
        """PCI slot."""
        return str(self.get("slot", ""))

    @property
    def device_class(self) -> str:
        """Device class."""
        return str(self.get("class", ""))

    @property
    def class_hex(self) -> str:
        """Device class in hexadecimal."""
        return str(self.get("class_hex", ""))

    @property
    def device_type_code(self) -> str:
        """Device type code."""
        return str(self.get("device_type", ""))

    @property
    def device_type(self) -> str:
        """Device type description."""
        code = self.device_type_code
        return DEVICE_TYPE_CODES.get(code, code)

    @property
    def vendor(self) -> str:
        """Vendor name."""
        return str(self.get("vendor", ""))

    @property
    def device(self) -> str:
        """Device name."""
        return str(self.get("device", ""))

    @property
    def vendor_device_hex(self) -> str:
        """Vendor/device ID in hexadecimal."""
        return str(self.get("vendor_device_hex", ""))

    @property
    def subsystem_vendor(self) -> str:
        """Subsystem vendor."""
        return str(self.get("svendor", ""))

    @property
    def subsystem_device(self) -> str:
        """Subsystem device."""
        return str(self.get("subsystem_device", ""))

    @property
    def physical_slot(self) -> str:
        """Physical slot."""
        return str(self.get("physical_slot", ""))

    @property
    def driver(self) -> str:
        """Current driver."""
        return str(self.get("driver", ""))

    @property
    def module(self) -> str:
        """Kernel module."""
        return str(self.get("module", ""))

    @property
    def numa_node(self) -> str:
        """NUMA node."""
        return str(self.get("numa", ""))

    @property
    def iommu_group(self) -> str:
        """IOMMU group."""
        return str(self.get("iommu_group", ""))

    @property
    def sriov_total_vfs(self) -> int:
        """Maximum SR-IOV virtual functions."""
        return int(self.get("sriov_totalvfs") or 0)

    @property
    def sriov_num_vfs(self) -> int:
        """Current SR-IOV virtual functions."""
        return int(self.get("sriov_numvfs") or 0)

    @property
    def is_gpu(self) -> bool:
        """Check if this is a GPU/display controller."""
        return self.device_type_code == "03"

    @property
    def is_network_controller(self) -> bool:
        """Check if this is a network controller."""
        return self.device_type_code == "02"

    @property
    def is_storage_controller(self) -> bool:
        """Check if this is a mass storage controller."""
        return self.device_type_code == "01"

    def __repr__(self) -> str:
        return (
            f"<NodePCIDevice key={self.get('$key', '?')} "
            f"slot={self.slot!r} name={self.name!r}>"
        )


class NodeUSBDevice(ResourceObject):
    """Node USB device resource object.

    Represents a USB device attached to a VergeOS node.
    """

    @property
    def node_key(self) -> int | None:
        """Parent node key."""
        node = self.get("node")
        if node:
            return int(node)
        return None

    @property
    def node_name(self) -> str:
        """Parent node name."""
        return str(self.get("node_name", ""))

    @property
    def bus(self) -> str:
        """USB bus number."""
        return str(self.get("bus", ""))

    @property
    def device_num(self) -> str:
        """USB device number."""
        return str(self.get("device", ""))

    @property
    def path(self) -> str:
        """USB path."""
        return str(self.get("path", ""))

    @property
    def devpath(self) -> str:
        """Device path."""
        return str(self.get("devpath", ""))

    @property
    def vendor(self) -> str:
        """Vendor name."""
        return str(self.get("vendor", ""))

    @property
    def vendor_id(self) -> str:
        """Vendor ID."""
        return str(self.get("vendor_id", ""))

    @property
    def model(self) -> str:
        """Model name."""
        return str(self.get("model", ""))

    @property
    def model_id(self) -> str:
        """Model ID."""
        return str(self.get("model_id", ""))

    @property
    def serial(self) -> str:
        """Serial number."""
        return str(self.get("serial", ""))

    @property
    def usb_version(self) -> str:
        """USB version."""
        return str(self.get("usb_version", ""))

    @property
    def speed(self) -> str:
        """USB speed."""
        return str(self.get("speed", ""))

    @property
    def interface_drivers(self) -> str:
        """Interface drivers."""
        return str(self.get("interface_drivers", ""))

    def __repr__(self) -> str:
        return (
            f"<NodeUSBDevice key={self.get('$key', '?')} "
            f"bus={self.bus} device={self.device_num} model={self.model!r}>"
        )


class NodeDriverManager(ResourceManager[NodeDriver]):
    """Manager for node driver operations.

    Provides access to drivers installed on VergeOS nodes.
    Can be used globally or scoped to a specific node.

    Example:
        >>> # List all drivers across all nodes
        >>> drivers = client.nodes.all_drivers.list()

        >>> # List drivers for a specific node
        >>> node_drivers = client.nodes.drivers(node_key).list()

        >>> # Or via node object
        >>> node = client.nodes.get(name="node1")
        >>> for driver in node.drivers.list():
        ...     print(f"{driver.driver_name}: {driver.status}")
    """

    _endpoint = "node_drivers"

    # Default fields for list operations
    _default_fields = [
        "$key",
        "node",
        "node#name as node_name",
        "driver_file",
        "driver_file#name as driver_file_name",
        "driver_key",
        "driver_name",
        "description",
        "status",
        "status_info",
        "class_filter",
        "vendor_filter",
        "modified",
    ]

    def __init__(self, client: VergeClient, node_key: int | None = None) -> None:
        super().__init__(client)
        self._node_key = node_key

    def _to_model(self, data: dict[str, Any]) -> NodeDriver:
        return NodeDriver(data, self)

    def list(
        self,
        filter: str | None = None,
        fields: builtins.list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        *,
        driver_name: str | None = None,
        status: Literal["Installed", "Verifying", "Error"] | None = None,
        **filter_kwargs: Any,
    ) -> builtins.list[NodeDriver]:
        """List node drivers with optional filtering.

        Args:
            filter: OData filter string.
            fields: List of fields to return.
            limit: Maximum number of results.
            offset: Skip this many results.
            driver_name: Filter by driver name (contains).
            status: Filter by status (Installed, Verifying, Error).
            **filter_kwargs: Additional filter arguments.

        Returns:
            List of NodeDriver objects.

        Example:
            >>> # List all drivers
            >>> drivers = client.nodes.all_drivers.list()

            >>> # List installed drivers
            >>> installed = client.nodes.all_drivers.list(status="Installed")

            >>> # List NVIDIA drivers
            >>> nvidia = client.nodes.all_drivers.list(driver_name="nvidia")
        """
        params: dict[str, Any] = {}
        filters = []

        if filter:
            filters.append(filter)

        # Scope to node if configured
        if self._node_key is not None:
            filters.append(f"node eq {self._node_key}")

        if driver_name is not None:
            escaped = driver_name.replace("'", "''")
            filters.append(f"driver_name ct '{escaped}'")

        if status is not None:
            status_map = {
                "Installed": "complete",
                "Verifying": "verifying",
                "Error": "error",
            }
            if status in status_map:
                filters.append(f"status eq '{status_map[status]}'")

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

    def get(  # type: ignore[override]
        self,
        key: int | None = None,
        *,
        driver_name: str | None = None,
        fields: builtins.list[str] | None = None,
    ) -> NodeDriver:
        """Get a single driver by key or name.

        Args:
            key: Driver $key (ID).
            driver_name: Driver name.
            fields: List of fields to return.

        Returns:
            NodeDriver object.

        Raises:
            NotFoundError: If driver not found.
            ValueError: If neither key nor driver_name provided.
        """
        if fields is None:
            fields = self._default_fields

        if key is not None:
            params: dict[str, Any] = {"fields": ",".join(fields)}
            response = self._client._request(
                "GET", f"{self._endpoint}/{key}", params=params
            )
            if response is None:
                raise NotFoundError(f"Driver with key {key} not found")
            if not isinstance(response, dict):
                raise NotFoundError(f"Driver with key {key} returned invalid response")
            return self._to_model(response)

        if driver_name is not None:
            results = self.list(driver_name=driver_name, fields=fields, limit=1)
            if not results:
                raise NotFoundError(f"Driver '{driver_name}' not found")
            return results[0]

        raise ValueError("Either key or driver_name must be provided")


class NodePCIDeviceManager(ResourceManager[NodePCIDevice]):
    """Manager for node PCI device operations.

    Provides access to PCI devices attached to VergeOS nodes.
    Can be used globally or scoped to a specific node.

    Example:
        >>> # List all PCI devices
        >>> devices = client.nodes.all_pci_devices.list()

        >>> # List GPUs only
        >>> gpus = client.nodes.all_pci_devices.list(device_type="GPU")

        >>> # List devices for a specific node
        >>> node_devices = client.nodes.pci_devices(node_key).list()
    """

    _endpoint = "node_pci_devices"

    # Default fields for list operations
    _default_fields = [
        "$key",
        "node",
        "node#name as node_name",
        "name",
        "slot",
        "class",
        "class_hex",
        "device_type",
        "vendor",
        "device",
        "vendor_device_hex",
        "svendor",
        "subsystem_device",
        "physical_slot",
        "driver",
        "module",
        "numa",
        "iommu_group",
        "sriov_totalvfs",
        "sriov_numvfs",
    ]

    def __init__(self, client: VergeClient, node_key: int | None = None) -> None:
        super().__init__(client)
        self._node_key = node_key

    def _to_model(self, data: dict[str, Any]) -> NodePCIDevice:
        return NodePCIDevice(data, self)

    def list(
        self,
        filter: str | None = None,
        fields: builtins.list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        *,
        device_type: Literal["GPU", "Network", "Storage"] | None = None,
        device_class: str | None = None,
        vendor: str | None = None,
        **filter_kwargs: Any,
    ) -> builtins.list[NodePCIDevice]:
        """List PCI devices with optional filtering.

        Args:
            filter: OData filter string.
            fields: List of fields to return.
            limit: Maximum number of results.
            offset: Skip this many results.
            device_type: Filter by device type (GPU, Network, Storage).
            device_class: Filter by device class (contains).
            vendor: Filter by vendor name (contains).
            **filter_kwargs: Additional filter arguments.

        Returns:
            List of NodePCIDevice objects.

        Example:
            >>> # List all PCI devices
            >>> devices = client.nodes.all_pci_devices.list()

            >>> # List GPUs only
            >>> gpus = client.nodes.all_pci_devices.list(device_type="GPU")

            >>> # List network controllers
            >>> nics = client.nodes.all_pci_devices.list(device_type="Network")
        """
        params: dict[str, Any] = {}
        filters = []

        if filter:
            filters.append(filter)

        # Scope to node if configured
        if self._node_key is not None:
            filters.append(f"node eq {self._node_key}")

        # Device type filter (maps to device_type code)
        if device_type is not None:
            type_map = {
                "GPU": "03",  # Display controller
                "Network": "02",  # Network controller
                "Storage": "01",  # Mass storage controller
            }
            if device_type in type_map:
                filters.append(f"device_type eq '{type_map[device_type]}'")

        if device_class is not None:
            escaped = device_class.replace("'", "''")
            filters.append(f"class ct '{escaped}'")

        if vendor is not None:
            escaped = vendor.replace("'", "''")
            filters.append(f"vendor ct '{escaped}'")

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

    def get(  # type: ignore[override]
        self,
        key: int,
        *,
        fields: builtins.list[str] | None = None,
    ) -> NodePCIDevice:
        """Get a single PCI device by key.

        Args:
            key: Device $key (ID).
            fields: List of fields to return.

        Returns:
            NodePCIDevice object.

        Raises:
            NotFoundError: If device not found.
        """
        if fields is None:
            fields = self._default_fields

        params: dict[str, Any] = {"fields": ",".join(fields)}
        response = self._client._request(
            "GET", f"{self._endpoint}/{key}", params=params
        )
        if response is None:
            raise NotFoundError(f"PCI device with key {key} not found")
        if not isinstance(response, dict):
            raise NotFoundError(f"PCI device with key {key} returned invalid response")
        return self._to_model(response)


class NodeUSBDeviceManager(ResourceManager[NodeUSBDevice]):
    """Manager for node USB device operations.

    Provides access to USB devices attached to VergeOS nodes.
    Can be used globally or scoped to a specific node.

    Example:
        >>> # List all USB devices
        >>> devices = client.nodes.all_usb_devices.list()

        >>> # List USB devices for a specific node
        >>> node_devices = client.nodes.usb_devices(node_key).list()
    """

    _endpoint = "node_usb_devices"

    # Default fields for list operations
    _default_fields = [
        "$key",
        "node",
        "node#name as node_name",
        "bus",
        "device",
        "path",
        "devpath",
        "vendor",
        "vendor_id",
        "model",
        "model_id",
        "serial",
        "usb_version",
        "speed",
        "interface_drivers",
    ]

    def __init__(self, client: VergeClient, node_key: int | None = None) -> None:
        super().__init__(client)
        self._node_key = node_key

    def _to_model(self, data: dict[str, Any]) -> NodeUSBDevice:
        return NodeUSBDevice(data, self)

    def list(
        self,
        filter: str | None = None,
        fields: builtins.list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        *,
        vendor: str | None = None,
        model: str | None = None,
        **filter_kwargs: Any,
    ) -> builtins.list[NodeUSBDevice]:
        """List USB devices with optional filtering.

        Args:
            filter: OData filter string.
            fields: List of fields to return.
            limit: Maximum number of results.
            offset: Skip this many results.
            vendor: Filter by vendor name (contains).
            model: Filter by model name (contains).
            **filter_kwargs: Additional filter arguments.

        Returns:
            List of NodeUSBDevice objects.

        Example:
            >>> # List all USB devices
            >>> devices = client.nodes.all_usb_devices.list()

            >>> # List USB devices by vendor
            >>> devices = client.nodes.all_usb_devices.list(vendor="Logitech")
        """
        params: dict[str, Any] = {}
        filters = []

        if filter:
            filters.append(filter)

        # Scope to node if configured
        if self._node_key is not None:
            filters.append(f"node eq {self._node_key}")

        if vendor is not None:
            escaped = vendor.replace("'", "''")
            filters.append(f"vendor ct '{escaped}'")

        if model is not None:
            escaped = model.replace("'", "''")
            filters.append(f"model ct '{escaped}'")

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

    def get(  # type: ignore[override]
        self,
        key: int,
        *,
        fields: builtins.list[str] | None = None,
    ) -> NodeUSBDevice:
        """Get a single USB device by key.

        Args:
            key: Device $key (ID).
            fields: List of fields to return.

        Returns:
            NodeUSBDevice object.

        Raises:
            NotFoundError: If device not found.
        """
        if fields is None:
            fields = self._default_fields

        params: dict[str, Any] = {"fields": ",".join(fields)}
        response = self._client._request(
            "GET", f"{self._endpoint}/{key}", params=params
        )
        if response is None:
            raise NotFoundError(f"USB device with key {key} not found")
        if not isinstance(response, dict):
            raise NotFoundError(f"USB device with key {key} returned invalid response")
        return self._to_model(response)


class NodeManager(ResourceManager[Node]):
    """Manager for Node operations.

    Provides CRUD operations and actions for VergeOS nodes.

    Example:
        >>> # List all nodes
        >>> nodes = client.nodes.list()
        >>> for node in nodes:
        ...     print(f"{node.name}: {node.status}")

        >>> # Get a specific node
        >>> node = client.nodes.get(name="node1")

        >>> # Enable maintenance mode
        >>> node = client.nodes.enable_maintenance(node.key)

        >>> # Access node drivers
        >>> for driver in node.drivers.list():
        ...     print(f"{driver.driver_name}: {driver.status}")

        >>> # Access PCI devices (GPUs)
        >>> gpus = client.nodes.all_pci_devices.list(device_type="GPU")
    """

    _endpoint = "nodes"

    # Default fields for list operations (includes status info)
    _default_fields = [
        "$key",
        "name",
        "description",
        "model",
        "cpu",
        "cpu_speed",
        "ram",
        "vm_ram",
        "overcommit",
        "failover_ram",
        "cores",
        "physical",
        "maintenance",
        "iommu",
        "need_restart",
        "restart_reason",
        "asset_tag",
        "ipmi_address",
        "ipmi_status",
        "vsan_nodeid",
        "vsan_connected",
        "yb_version",
        "os_version",
        "kernel_version",
        "appserver_version",
        "vsan_version",
        "qemu_version",
        "cluster",
        "cluster#name as cluster_name",
        "machine",
        "machine#status#status as status",
        "machine#status#running as running",
        "machine#status#started as started",
        "machine#stats#total_cpu as cpu_usage",
        "machine#stats#ram_used as ram_used",
        "machine#stats#vram_used as vram_used",
        "machine#stats#core_temp as core_temp",
    ]

    def __init__(self, client: VergeClient) -> None:
        super().__init__(client)
        self._all_drivers: NodeDriverManager | None = None
        self._all_pci_devices: NodePCIDeviceManager | None = None
        self._all_usb_devices: NodeUSBDeviceManager | None = None

    def _to_model(self, data: dict[str, Any]) -> Node:
        return Node(data, self)

    def list(
        self,
        filter: str | None = None,
        fields: builtins.list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        *,
        name: str | None = None,
        cluster: str | None = None,
        maintenance: bool | None = None,
        **filter_kwargs: Any,
    ) -> builtins.list[Node]:
        """List nodes with optional filtering.

        Args:
            filter: OData filter string.
            fields: List of fields to return (defaults to comprehensive set).
            limit: Maximum number of results.
            offset: Skip this many results.
            name: Filter by node name.
            cluster: Filter by cluster name.
            maintenance: Filter by maintenance mode status.
            **filter_kwargs: Additional filter arguments.

        Returns:
            List of Node objects.

        Example:
            >>> # List all nodes
            >>> nodes = client.nodes.list()

            >>> # List nodes in a specific cluster
            >>> nodes = client.nodes.list(cluster="Cluster1")

            >>> # List nodes in maintenance mode
            >>> nodes = client.nodes.list(maintenance=True)
        """
        params: dict[str, Any] = {}

        # Build filter
        filters = []
        if filter:
            filters.append(filter)

        if name is not None:
            escaped = name.replace("'", "''")
            filters.append(f"name eq '{escaped}'")

        if cluster is not None:
            escaped = cluster.replace("'", "''")
            filters.append(f"cluster#name eq '{escaped}'")

        if maintenance is not None:
            filters.append(f"maintenance eq {str(maintenance).lower()}")

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
    ) -> Node:
        """Get a single node by key or name.

        Args:
            key: Node $key (ID).
            name: Node name (hostname).
            fields: List of fields to return.

        Returns:
            Node object.

        Raises:
            NotFoundError: If node not found.
            ValueError: If neither key nor name provided.

        Example:
            >>> node = client.nodes.get(key=1)
            >>> node = client.nodes.get(name="node1")
        """
        # Use default fields if not specified
        if fields is None:
            fields = self._default_fields

        return super().get(key, name=name, fields=fields)

    def enable_maintenance(self, key: int) -> Node:
        """Enable maintenance mode on a node.

        When in maintenance mode, VMs will be migrated off the node and
        no new workloads will be scheduled to it.

        Args:
            key: Node $key (ID).

        Returns:
            Updated Node object.

        Example:
            >>> node = client.nodes.enable_maintenance(node.key)
            >>> print(f"Maintenance mode: {node.is_maintenance}")
        """
        body = {"node": key, "action": "maintenance"}
        self._client._request("POST", "node_actions/enable_maintenance", json_data=body)
        return self.get(key)

    def disable_maintenance(self, key: int) -> Node:
        """Disable maintenance mode on a node.

        Once disabled, the node will be available to run VMs and receive
        new workloads.

        Args:
            key: Node $key (ID).

        Returns:
            Updated Node object.

        Example:
            >>> node = client.nodes.disable_maintenance(node.key)
            >>> print(f"Maintenance mode: {node.is_maintenance}")
        """
        body = {"node": key, "action": "leavemaintenance"}
        self._client._request(
            "POST", "node_actions/disable_maintenance", json_data=body
        )
        return self.get(key)

    def restart(self, key: int) -> dict[str, Any] | None:
        """Perform a maintenance reboot on a node.

        This safely reboots the node by first migrating workloads
        and then restarting the system.

        Args:
            key: Node $key (ID).

        Returns:
            Task information dict or None.

        Example:
            >>> result = client.nodes.restart(node.key)
            >>> if result and "task" in result:
            ...     client.tasks.wait(result["task"])
        """
        body = {"node": key, "action": "maintenance_reboot"}
        response = self._client._request(
            "POST", "node_actions/maintenance_reboot", json_data=body
        )
        if isinstance(response, dict):
            return response
        return None

    def drivers(self, node_key: int) -> NodeDriverManager:
        """Get driver manager scoped to a specific node.

        Args:
            node_key: Node $key (ID).

        Returns:
            NodeDriverManager for the specified node.

        Example:
            >>> drivers = client.nodes.drivers(node.key).list()
        """
        return NodeDriverManager(self._client, node_key=node_key)

    def pci_devices(self, node_key: int) -> NodePCIDeviceManager:
        """Get PCI device manager scoped to a specific node.

        Args:
            node_key: Node $key (ID).

        Returns:
            NodePCIDeviceManager for the specified node.

        Example:
            >>> devices = client.nodes.pci_devices(node.key).list()
        """
        return NodePCIDeviceManager(self._client, node_key=node_key)

    def usb_devices(self, node_key: int) -> NodeUSBDeviceManager:
        """Get USB device manager scoped to a specific node.

        Args:
            node_key: Node $key (ID).

        Returns:
            NodeUSBDeviceManager for the specified node.

        Example:
            >>> devices = client.nodes.usb_devices(node.key).list()
        """
        return NodeUSBDeviceManager(self._client, node_key=node_key)

    @property
    def all_drivers(self) -> NodeDriverManager:
        """Access all drivers across all nodes.

        Returns:
            NodeDriverManager (global, not scoped to a node).

        Example:
            >>> all_drivers = client.nodes.all_drivers.list()
        """
        if self._all_drivers is None:
            self._all_drivers = NodeDriverManager(self._client)
        return self._all_drivers

    @property
    def all_pci_devices(self) -> NodePCIDeviceManager:
        """Access all PCI devices across all nodes.

        Returns:
            NodePCIDeviceManager (global, not scoped to a node).

        Example:
            >>> all_gpus = client.nodes.all_pci_devices.list(device_type="GPU")
        """
        if self._all_pci_devices is None:
            self._all_pci_devices = NodePCIDeviceManager(self._client)
        return self._all_pci_devices

    @property
    def all_usb_devices(self) -> NodeUSBDeviceManager:
        """Access all USB devices across all nodes.

        Returns:
            NodeUSBDeviceManager (global, not scoped to a node).

        Example:
            >>> all_usb = client.nodes.all_usb_devices.list()
        """
        if self._all_usb_devices is None:
            self._all_usb_devices = NodeUSBDeviceManager(self._client)
        return self._all_usb_devices
