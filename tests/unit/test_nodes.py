"""Unit tests for node operations."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from pyvergeos.exceptions import NotFoundError
from pyvergeos.resources.nodes import (
    DEVICE_TYPE_CODES,
    DRIVER_STATUS_DISPLAY,
    STATUS_DISPLAY,
    Node,
    NodeDriver,
    NodeDriverManager,
    NodeManager,
    NodePCIDevice,
    NodePCIDeviceManager,
    NodeUSBDevice,
    NodeUSBDeviceManager,
)


class TestNode:
    """Tests for Node resource object."""

    def test_key_property(self) -> None:
        """Test key property returns int."""
        data = {"$key": 123}
        node = Node(data, MagicMock())
        assert node.key == 123

    def test_key_property_missing(self) -> None:
        """Test key property raises when missing."""
        node = Node({}, MagicMock())
        with pytest.raises(ValueError, match="no \\$key"):
            _ = node.key

    def test_name_property(self) -> None:
        """Test name property."""
        data = {"$key": 1, "name": "node1"}
        node = Node(data, MagicMock())
        assert node.name == "node1"

    def test_name_empty(self) -> None:
        """Test name property when empty."""
        node = Node({"$key": 1}, MagicMock())
        assert node.name == ""

    def test_description_property(self) -> None:
        """Test description property."""
        data = {"$key": 1, "description": "Production node"}
        node = Node(data, MagicMock())
        assert node.description == "Production node"

    def test_model_property(self) -> None:
        """Test model property."""
        data = {"$key": 1, "model": "Dell PowerEdge R740"}
        node = Node(data, MagicMock())
        assert node.model == "Dell PowerEdge R740"

    def test_cpu_property(self) -> None:
        """Test cpu property."""
        data = {"$key": 1, "cpu": "AMD EPYC 7302P"}
        node = Node(data, MagicMock())
        assert node.cpu == "AMD EPYC 7302P"

    def test_is_online_true(self) -> None:
        """Test is_online property when true."""
        data = {"$key": 1, "running": True}
        node = Node(data, MagicMock())
        assert node.is_online is True

    def test_is_online_false(self) -> None:
        """Test is_online property when false."""
        data = {"$key": 1, "running": False}
        node = Node(data, MagicMock())
        assert node.is_online is False

    def test_is_online_default(self) -> None:
        """Test is_online property defaults to False."""
        node = Node({"$key": 1}, MagicMock())
        assert node.is_online is False

    def test_is_maintenance_true(self) -> None:
        """Test is_maintenance property when true."""
        data = {"$key": 1, "maintenance": True}
        node = Node(data, MagicMock())
        assert node.is_maintenance is True

    def test_is_maintenance_false(self) -> None:
        """Test is_maintenance property when false."""
        data = {"$key": 1, "maintenance": False}
        node = Node(data, MagicMock())
        assert node.is_maintenance is False

    def test_is_maintenance_default(self) -> None:
        """Test is_maintenance property defaults to False."""
        node = Node({"$key": 1}, MagicMock())
        assert node.is_maintenance is False

    def test_is_physical_true(self) -> None:
        """Test is_physical property when true."""
        data = {"$key": 1, "physical": True}
        node = Node(data, MagicMock())
        assert node.is_physical is True

    def test_is_physical_false(self) -> None:
        """Test is_physical property when false."""
        data = {"$key": 1, "physical": False}
        node = Node(data, MagicMock())
        assert node.is_physical is False

    def test_status_property_running(self) -> None:
        """Test status property for running."""
        data = {"$key": 1, "status": "running"}
        node = Node(data, MagicMock())
        assert node.status == "Running"

    def test_status_property_stopped(self) -> None:
        """Test status property for stopped."""
        data = {"$key": 1, "status": "stopped"}
        node = Node(data, MagicMock())
        assert node.status == "Stopped"

    def test_status_property_maintenance(self) -> None:
        """Test status property for maintenance."""
        data = {"$key": 1, "status": "maintenance"}
        node = Node(data, MagicMock())
        assert node.status == "Maintenance"

    def test_status_raw_property(self) -> None:
        """Test status_raw property."""
        data = {"$key": 1, "status": "running"}
        node = Node(data, MagicMock())
        assert node.status_raw == "running"

    def test_ram_mb_property(self) -> None:
        """Test ram_mb property."""
        data = {"$key": 1, "ram": 65536}
        node = Node(data, MagicMock())
        assert node.ram_mb == 65536

    def test_ram_gb_property(self) -> None:
        """Test ram_gb property."""
        data = {"$key": 1, "ram": 65536}  # 64 GB
        node = Node(data, MagicMock())
        assert node.ram_gb == 64.0

    def test_ram_gb_zero(self) -> None:
        """Test ram_gb property when zero."""
        data = {"$key": 1, "ram": 0}
        node = Node(data, MagicMock())
        assert node.ram_gb == 0.0

    def test_vm_ram_mb_property(self) -> None:
        """Test vm_ram_mb property."""
        data = {"$key": 1, "vm_ram": 49152}
        node = Node(data, MagicMock())
        assert node.vm_ram_mb == 49152

    def test_overcommit_ram_mb_property(self) -> None:
        """Test overcommit_ram_mb property."""
        data = {"$key": 1, "overcommit": 8192}
        node = Node(data, MagicMock())
        assert node.overcommit_ram_mb == 8192

    def test_failover_ram_mb_property(self) -> None:
        """Test failover_ram_mb property."""
        data = {"$key": 1, "failover_ram": 16384}
        node = Node(data, MagicMock())
        assert node.failover_ram_mb == 16384

    def test_cores_property(self) -> None:
        """Test cores property."""
        data = {"$key": 1, "cores": 32}
        node = Node(data, MagicMock())
        assert node.cores == 32

    def test_cores_default(self) -> None:
        """Test cores property defaults to 0."""
        node = Node({"$key": 1}, MagicMock())
        assert node.cores == 0

    def test_has_iommu_true(self) -> None:
        """Test has_iommu property when true."""
        data = {"$key": 1, "iommu": True}
        node = Node(data, MagicMock())
        assert node.has_iommu is True

    def test_has_iommu_false(self) -> None:
        """Test has_iommu property when false."""
        data = {"$key": 1, "iommu": False}
        node = Node(data, MagicMock())
        assert node.has_iommu is False

    def test_needs_restart_true(self) -> None:
        """Test needs_restart property when true."""
        data = {"$key": 1, "need_restart": True}
        node = Node(data, MagicMock())
        assert node.needs_restart is True

    def test_needs_restart_false(self) -> None:
        """Test needs_restart property when false."""
        data = {"$key": 1, "need_restart": False}
        node = Node(data, MagicMock())
        assert node.needs_restart is False

    def test_restart_reason_property(self) -> None:
        """Test restart_reason property."""
        data = {"$key": 1, "restart_reason": "Kernel update pending"}
        node = Node(data, MagicMock())
        assert node.restart_reason == "Kernel update pending"

    def test_vsan_node_id_property(self) -> None:
        """Test vsan_node_id property."""
        data = {"$key": 1, "vsan_nodeid": 2}
        node = Node(data, MagicMock())
        assert node.vsan_node_id == 2

    def test_vsan_node_id_default(self) -> None:
        """Test vsan_node_id property defaults to -1."""
        node = Node({"$key": 1}, MagicMock())
        assert node.vsan_node_id == -1

    def test_vsan_connected_true(self) -> None:
        """Test vsan_connected property when true."""
        data = {"$key": 1, "vsan_connected": True}
        node = Node(data, MagicMock())
        assert node.vsan_connected is True

    def test_vsan_connected_false(self) -> None:
        """Test vsan_connected property when false."""
        data = {"$key": 1, "vsan_connected": False}
        node = Node(data, MagicMock())
        assert node.vsan_connected is False

    def test_cluster_key_property(self) -> None:
        """Test cluster_key property."""
        data = {"$key": 1, "cluster": 5}
        node = Node(data, MagicMock())
        assert node.cluster_key == 5

    def test_cluster_key_none(self) -> None:
        """Test cluster_key property when not set."""
        node = Node({"$key": 1}, MagicMock())
        assert node.cluster_key is None

    def test_cluster_name_property(self) -> None:
        """Test cluster_name property."""
        data = {"$key": 1, "cluster_name": "Production"}
        node = Node(data, MagicMock())
        assert node.cluster_name == "Production"

    def test_asset_tag_property(self) -> None:
        """Test asset_tag property."""
        data = {"$key": 1, "asset_tag": "ASSET001"}
        node = Node(data, MagicMock())
        assert node.asset_tag == "ASSET001"

    def test_ipmi_address_property(self) -> None:
        """Test ipmi_address property."""
        data = {"$key": 1, "ipmi_address": "192.168.1.100"}
        node = Node(data, MagicMock())
        assert node.ipmi_address == "192.168.1.100"

    def test_ipmi_status_property(self) -> None:
        """Test ipmi_status property."""
        data = {"$key": 1, "ipmi_status": "ready"}
        node = Node(data, MagicMock())
        assert node.ipmi_status == "ready"

    def test_vergeos_version_property(self) -> None:
        """Test vergeos_version property."""
        data = {"$key": 1, "yb_version": "26.0.2.1"}
        node = Node(data, MagicMock())
        assert node.vergeos_version == "26.0.2.1"

    def test_os_version_property(self) -> None:
        """Test os_version property."""
        data = {"$key": 1, "os_version": "Ubuntu 22.04"}
        node = Node(data, MagicMock())
        assert node.os_version == "Ubuntu 22.04"

    def test_kernel_version_property(self) -> None:
        """Test kernel_version property."""
        data = {"$key": 1, "kernel_version": "5.15.0-generic"}
        node = Node(data, MagicMock())
        assert node.kernel_version == "5.15.0-generic"

    def test_started_at_property(self) -> None:
        """Test started_at property."""
        data = {"$key": 1, "started": 1706486400}  # 2024-01-29 00:00:00 UTC
        node = Node(data, MagicMock())
        assert node.started_at == datetime(2024, 1, 29, 0, 0, 0, tzinfo=timezone.utc)

    def test_started_at_none(self) -> None:
        """Test started_at property when not set."""
        node = Node({"$key": 1}, MagicMock())
        assert node.started_at is None

    def test_repr(self) -> None:
        """Test __repr__ method."""
        data = {
            "$key": 1,
            "name": "node1",
            "status": "running",
            "cores": 32,
            "ram": 65536,
        }
        node = Node(data, MagicMock())
        repr_str = repr(node)
        assert "Node" in repr_str
        assert "key=1" in repr_str
        assert "node1" in repr_str
        assert "Running" in repr_str
        assert "cores=32" in repr_str
        assert "ram=65536MB" in repr_str


class TestNodeDriver:
    """Tests for NodeDriver resource object."""

    def test_key_property(self) -> None:
        """Test key property returns int."""
        data = {"$key": 456}
        driver = NodeDriver(data, MagicMock())
        assert driver.key == 456

    def test_node_key_property(self) -> None:
        """Test node_key property."""
        data = {"$key": 1, "node": 5}
        driver = NodeDriver(data, MagicMock())
        assert driver.node_key == 5

    def test_node_key_none(self) -> None:
        """Test node_key property when not set."""
        driver = NodeDriver({"$key": 1}, MagicMock())
        assert driver.node_key is None

    def test_node_name_property(self) -> None:
        """Test node_name property."""
        data = {"$key": 1, "node_name": "node1"}
        driver = NodeDriver(data, MagicMock())
        assert driver.node_name == "node1"

    def test_driver_name_property(self) -> None:
        """Test driver_name property."""
        data = {"$key": 1, "driver_name": "nvidia"}
        driver = NodeDriver(data, MagicMock())
        assert driver.driver_name == "nvidia"

    def test_driver_key_property(self) -> None:
        """Test driver_key property."""
        data = {"$key": 1, "driver_key": "nvidia-535"}
        driver = NodeDriver(data, MagicMock())
        assert driver.driver_key == "nvidia-535"

    def test_status_installed(self) -> None:
        """Test status property for complete."""
        data = {"$key": 1, "status": "complete"}
        driver = NodeDriver(data, MagicMock())
        assert driver.status == "Installed"

    def test_status_verifying(self) -> None:
        """Test status property for verifying."""
        data = {"$key": 1, "status": "verifying"}
        driver = NodeDriver(data, MagicMock())
        assert driver.status == "Verifying"

    def test_status_error(self) -> None:
        """Test status property for error."""
        data = {"$key": 1, "status": "error"}
        driver = NodeDriver(data, MagicMock())
        assert driver.status == "Error"

    def test_status_raw_property(self) -> None:
        """Test status_raw property."""
        data = {"$key": 1, "status": "complete"}
        driver = NodeDriver(data, MagicMock())
        assert driver.status_raw == "complete"

    def test_status_info_property(self) -> None:
        """Test status_info property."""
        data = {"$key": 1, "status_info": "Successfully loaded"}
        driver = NodeDriver(data, MagicMock())
        assert driver.status_info == "Successfully loaded"

    def test_modified_at_property(self) -> None:
        """Test modified_at property."""
        data = {"$key": 1, "modified": 1706486400}
        driver = NodeDriver(data, MagicMock())
        assert driver.modified_at == datetime(2024, 1, 29, 0, 0, 0, tzinfo=timezone.utc)

    def test_repr(self) -> None:
        """Test __repr__ method."""
        data = {"$key": 1, "driver_name": "nvidia", "status": "complete"}
        driver = NodeDriver(data, MagicMock())
        repr_str = repr(driver)
        assert "NodeDriver" in repr_str
        assert "key=1" in repr_str
        assert "nvidia" in repr_str


class TestNodePCIDevice:
    """Tests for NodePCIDevice resource object."""

    def test_key_property(self) -> None:
        """Test key property returns int."""
        data = {"$key": 789}
        device = NodePCIDevice(data, MagicMock())
        assert device.key == 789

    def test_node_key_property(self) -> None:
        """Test node_key property."""
        data = {"$key": 1, "node": 5}
        device = NodePCIDevice(data, MagicMock())
        assert device.node_key == 5

    def test_name_property(self) -> None:
        """Test name property."""
        data = {"$key": 1, "name": "NVIDIA GeForce RTX 4090"}
        device = NodePCIDevice(data, MagicMock())
        assert device.name == "NVIDIA GeForce RTX 4090"

    def test_slot_property(self) -> None:
        """Test slot property."""
        data = {"$key": 1, "slot": "00:02.0"}
        device = NodePCIDevice(data, MagicMock())
        assert device.slot == "00:02.0"

    def test_device_class_property(self) -> None:
        """Test device_class property."""
        data = {"$key": 1, "class": "VGA compatible controller"}
        device = NodePCIDevice(data, MagicMock())
        assert device.device_class == "VGA compatible controller"

    def test_device_type_code_property(self) -> None:
        """Test device_type_code property."""
        data = {"$key": 1, "device_type": "03"}
        device = NodePCIDevice(data, MagicMock())
        assert device.device_type_code == "03"

    def test_device_type_gpu(self) -> None:
        """Test device_type property for GPU."""
        data = {"$key": 1, "device_type": "03"}
        device = NodePCIDevice(data, MagicMock())
        assert device.device_type == "Display controller"

    def test_device_type_network(self) -> None:
        """Test device_type property for network controller."""
        data = {"$key": 1, "device_type": "02"}
        device = NodePCIDevice(data, MagicMock())
        assert device.device_type == "Network controller"

    def test_device_type_storage(self) -> None:
        """Test device_type property for mass storage."""
        data = {"$key": 1, "device_type": "01"}
        device = NodePCIDevice(data, MagicMock())
        assert device.device_type == "Mass storage controller"

    def test_vendor_property(self) -> None:
        """Test vendor property."""
        data = {"$key": 1, "vendor": "NVIDIA Corporation"}
        device = NodePCIDevice(data, MagicMock())
        assert device.vendor == "NVIDIA Corporation"

    def test_device_property(self) -> None:
        """Test device property."""
        data = {"$key": 1, "device": "AD102 [GeForce RTX 4090]"}
        device = NodePCIDevice(data, MagicMock())
        assert device.device == "AD102 [GeForce RTX 4090]"

    def test_driver_property(self) -> None:
        """Test driver property."""
        data = {"$key": 1, "driver": "nvidia"}
        device = NodePCIDevice(data, MagicMock())
        assert device.driver == "nvidia"

    def test_iommu_group_property(self) -> None:
        """Test iommu_group property."""
        data = {"$key": 1, "iommu_group": "15"}
        device = NodePCIDevice(data, MagicMock())
        assert device.iommu_group == "15"

    def test_sriov_total_vfs_property(self) -> None:
        """Test sriov_total_vfs property."""
        data = {"$key": 1, "sriov_totalvfs": 64}
        device = NodePCIDevice(data, MagicMock())
        assert device.sriov_total_vfs == 64

    def test_sriov_num_vfs_property(self) -> None:
        """Test sriov_num_vfs property."""
        data = {"$key": 1, "sriov_numvfs": 16}
        device = NodePCIDevice(data, MagicMock())
        assert device.sriov_num_vfs == 16

    def test_is_gpu_true(self) -> None:
        """Test is_gpu property when true."""
        data = {"$key": 1, "device_type": "03"}
        device = NodePCIDevice(data, MagicMock())
        assert device.is_gpu is True

    def test_is_gpu_false(self) -> None:
        """Test is_gpu property when false."""
        data = {"$key": 1, "device_type": "02"}
        device = NodePCIDevice(data, MagicMock())
        assert device.is_gpu is False

    def test_is_network_controller_true(self) -> None:
        """Test is_network_controller property when true."""
        data = {"$key": 1, "device_type": "02"}
        device = NodePCIDevice(data, MagicMock())
        assert device.is_network_controller is True

    def test_is_storage_controller_true(self) -> None:
        """Test is_storage_controller property when true."""
        data = {"$key": 1, "device_type": "01"}
        device = NodePCIDevice(data, MagicMock())
        assert device.is_storage_controller is True

    def test_repr(self) -> None:
        """Test __repr__ method."""
        data = {"$key": 1, "slot": "00:02.0", "name": "NVIDIA RTX 4090"}
        device = NodePCIDevice(data, MagicMock())
        repr_str = repr(device)
        assert "NodePCIDevice" in repr_str
        assert "key=1" in repr_str
        assert "00:02.0" in repr_str


class TestNodeUSBDevice:
    """Tests for NodeUSBDevice resource object."""

    def test_key_property(self) -> None:
        """Test key property returns int."""
        data = {"$key": 101}
        device = NodeUSBDevice(data, MagicMock())
        assert device.key == 101

    def test_node_key_property(self) -> None:
        """Test node_key property."""
        data = {"$key": 1, "node": 5}
        device = NodeUSBDevice(data, MagicMock())
        assert device.node_key == 5

    def test_bus_property(self) -> None:
        """Test bus property."""
        data = {"$key": 1, "bus": "001"}
        device = NodeUSBDevice(data, MagicMock())
        assert device.bus == "001"

    def test_device_num_property(self) -> None:
        """Test device_num property."""
        data = {"$key": 1, "device": "003"}
        device = NodeUSBDevice(data, MagicMock())
        assert device.device_num == "003"

    def test_path_property(self) -> None:
        """Test path property."""
        data = {"$key": 1, "path": "1-2.1"}
        device = NodeUSBDevice(data, MagicMock())
        assert device.path == "1-2.1"

    def test_vendor_property(self) -> None:
        """Test vendor property."""
        data = {"$key": 1, "vendor": "Logitech"}
        device = NodeUSBDevice(data, MagicMock())
        assert device.vendor == "Logitech"

    def test_vendor_id_property(self) -> None:
        """Test vendor_id property."""
        data = {"$key": 1, "vendor_id": "046d"}
        device = NodeUSBDevice(data, MagicMock())
        assert device.vendor_id == "046d"

    def test_model_property(self) -> None:
        """Test model property."""
        data = {"$key": 1, "model": "Wireless Mouse"}
        device = NodeUSBDevice(data, MagicMock())
        assert device.model == "Wireless Mouse"

    def test_model_id_property(self) -> None:
        """Test model_id property."""
        data = {"$key": 1, "model_id": "c52b"}
        device = NodeUSBDevice(data, MagicMock())
        assert device.model_id == "c52b"

    def test_serial_property(self) -> None:
        """Test serial property."""
        data = {"$key": 1, "serial": "ABC123"}
        device = NodeUSBDevice(data, MagicMock())
        assert device.serial == "ABC123"

    def test_usb_version_property(self) -> None:
        """Test usb_version property."""
        data = {"$key": 1, "usb_version": "2.0"}
        device = NodeUSBDevice(data, MagicMock())
        assert device.usb_version == "2.0"

    def test_speed_property(self) -> None:
        """Test speed property."""
        data = {"$key": 1, "speed": "480"}
        device = NodeUSBDevice(data, MagicMock())
        assert device.speed == "480"

    def test_repr(self) -> None:
        """Test __repr__ method."""
        data = {"$key": 1, "bus": "001", "device": "003", "model": "Mouse"}
        device = NodeUSBDevice(data, MagicMock())
        repr_str = repr(device)
        assert "NodeUSBDevice" in repr_str
        assert "key=1" in repr_str
        assert "bus=001" in repr_str


class TestNodeManager:
    """Tests for NodeManager."""

    def test_init(self) -> None:
        """Test NodeManager initialization."""
        mock_client = MagicMock()
        manager = NodeManager(mock_client)
        assert manager._client == mock_client
        assert manager._endpoint == "nodes"

    def test_to_model(self) -> None:
        """Test _to_model creates Node object."""
        mock_client = MagicMock()
        manager = NodeManager(mock_client)
        data = {"$key": 1, "name": "node1"}
        node = manager._to_model(data)
        assert isinstance(node, Node)
        assert node.name == "node1"


class TestNodeManagerList:
    """Tests for NodeManager.list() method."""

    def test_list_returns_nodes(self) -> None:
        """Test list returns Node objects."""
        mock_client = MagicMock()
        mock_client._request.return_value = [
            {"$key": 1, "name": "node1"},
            {"$key": 2, "name": "node2"},
        ]
        manager = NodeManager(mock_client)

        nodes = manager.list()

        assert len(nodes) == 2
        assert all(isinstance(n, Node) for n in nodes)
        assert nodes[0].name == "node1"
        assert nodes[1].name == "node2"

    def test_list_empty_response(self) -> None:
        """Test list with empty response."""
        mock_client = MagicMock()
        mock_client._request.return_value = None
        manager = NodeManager(mock_client)

        nodes = manager.list()

        assert nodes == []

    def test_list_single_object_response(self) -> None:
        """Test list with single object response."""
        mock_client = MagicMock()
        mock_client._request.return_value = {"$key": 1, "name": "single"}
        manager = NodeManager(mock_client)

        nodes = manager.list()

        assert len(nodes) == 1
        assert nodes[0].name == "single"

    def test_list_with_name_filter(self) -> None:
        """Test list with name filter."""
        mock_client = MagicMock()
        mock_client._request.return_value = [{"$key": 1, "name": "node1"}]
        manager = NodeManager(mock_client)

        manager.list(name="node1")

        call_args = mock_client._request.call_args
        assert "name eq 'node1'" in call_args[1]["params"]["filter"]

    def test_list_with_cluster_filter(self) -> None:
        """Test list with cluster filter."""
        mock_client = MagicMock()
        mock_client._request.return_value = []
        manager = NodeManager(mock_client)

        manager.list(cluster="Production")

        call_args = mock_client._request.call_args
        assert "cluster#name eq 'Production'" in call_args[1]["params"]["filter"]

    def test_list_with_maintenance_filter(self) -> None:
        """Test list with maintenance filter."""
        mock_client = MagicMock()
        mock_client._request.return_value = []
        manager = NodeManager(mock_client)

        manager.list(maintenance=True)

        call_args = mock_client._request.call_args
        assert "maintenance eq true" in call_args[1]["params"]["filter"]

    def test_list_with_pagination(self) -> None:
        """Test list with pagination parameters."""
        mock_client = MagicMock()
        mock_client._request.return_value = []
        manager = NodeManager(mock_client)

        manager.list(limit=10, offset=20)

        call_args = mock_client._request.call_args
        assert call_args[1]["params"]["limit"] == 10
        assert call_args[1]["params"]["offset"] == 20

    def test_list_uses_default_fields(self) -> None:
        """Test list uses default fields."""
        mock_client = MagicMock()
        mock_client._request.return_value = []
        manager = NodeManager(mock_client)

        manager.list()

        call_args = mock_client._request.call_args
        fields = call_args[1]["params"]["fields"]
        assert "$key" in fields
        assert "name" in fields
        assert "ram" in fields
        assert "cores" in fields


class TestNodeManagerGet:
    """Tests for NodeManager.get() method."""

    def test_get_by_key(self) -> None:
        """Test get by key."""
        mock_client = MagicMock()
        mock_client._request.return_value = {"$key": 1, "name": "node1"}
        manager = NodeManager(mock_client)

        node = manager.get(1)

        assert node.key == 1
        assert node.name == "node1"
        mock_client._request.assert_called_once()

    def test_get_by_name(self) -> None:
        """Test get by name."""
        mock_client = MagicMock()
        mock_client._request.return_value = [{"$key": 1, "name": "node1"}]
        manager = NodeManager(mock_client)

        node = manager.get(name="node1")

        assert node.name == "node1"

    def test_get_not_found_raises(self) -> None:
        """Test get raises NotFoundError when not found."""
        mock_client = MagicMock()
        mock_client._request.return_value = None
        manager = NodeManager(mock_client)

        with pytest.raises(NotFoundError):
            manager.get(999)

    def test_get_no_key_or_name_raises(self) -> None:
        """Test get raises ValueError when neither key nor name provided."""
        mock_client = MagicMock()
        manager = NodeManager(mock_client)

        with pytest.raises(ValueError, match="key or name"):
            manager.get()


class TestNodeManagerMaintenance:
    """Tests for NodeManager maintenance methods."""

    def test_enable_maintenance(self) -> None:
        """Test enable_maintenance method."""
        mock_client = MagicMock()
        mock_client._request.side_effect = [
            None,  # POST response
            {"$key": 1, "name": "node1", "maintenance": True},  # GET response
        ]
        manager = NodeManager(mock_client)

        node = manager.enable_maintenance(1)

        assert node.is_maintenance is True
        # Verify POST was called
        post_call = mock_client._request.call_args_list[0]
        assert post_call[0][0] == "POST"
        assert "node_actions/enable_maintenance" in post_call[0][1]
        assert post_call[1]["json_data"]["node"] == 1
        assert post_call[1]["json_data"]["action"] == "maintenance"

    def test_disable_maintenance(self) -> None:
        """Test disable_maintenance method."""
        mock_client = MagicMock()
        mock_client._request.side_effect = [
            None,  # POST response
            {"$key": 1, "name": "node1", "maintenance": False},  # GET response
        ]
        manager = NodeManager(mock_client)

        node = manager.disable_maintenance(1)

        assert node.is_maintenance is False
        # Verify POST was called
        post_call = mock_client._request.call_args_list[0]
        assert post_call[0][0] == "POST"
        assert "node_actions/disable_maintenance" in post_call[0][1]
        assert post_call[1]["json_data"]["node"] == 1
        assert post_call[1]["json_data"]["action"] == "leavemaintenance"

    def test_restart(self) -> None:
        """Test restart method."""
        mock_client = MagicMock()
        mock_client._request.return_value = {"task": 123}
        manager = NodeManager(mock_client)

        result = manager.restart(1)

        assert result == {"task": 123}
        # Verify POST was called
        call_args = mock_client._request.call_args
        assert call_args[0][0] == "POST"
        assert "node_actions/maintenance_reboot" in call_args[0][1]
        assert call_args[1]["json_data"]["node"] == 1
        assert call_args[1]["json_data"]["action"] == "maintenance_reboot"


class TestNodeManagerDeviceManagers:
    """Tests for NodeManager device/driver manager accessors."""

    def test_drivers_returns_scoped_manager(self) -> None:
        """Test drivers() returns NodeDriverManager scoped to node."""
        mock_client = MagicMock()
        manager = NodeManager(mock_client)

        driver_mgr = manager.drivers(1)

        assert isinstance(driver_mgr, NodeDriverManager)
        assert driver_mgr._node_key == 1

    def test_pci_devices_returns_scoped_manager(self) -> None:
        """Test pci_devices() returns NodePCIDeviceManager scoped to node."""
        mock_client = MagicMock()
        manager = NodeManager(mock_client)

        pci_mgr = manager.pci_devices(1)

        assert isinstance(pci_mgr, NodePCIDeviceManager)
        assert pci_mgr._node_key == 1

    def test_usb_devices_returns_scoped_manager(self) -> None:
        """Test usb_devices() returns NodeUSBDeviceManager scoped to node."""
        mock_client = MagicMock()
        manager = NodeManager(mock_client)

        usb_mgr = manager.usb_devices(1)

        assert isinstance(usb_mgr, NodeUSBDeviceManager)
        assert usb_mgr._node_key == 1

    def test_all_drivers_returns_global_manager(self) -> None:
        """Test all_drivers property returns global NodeDriverManager."""
        mock_client = MagicMock()
        manager = NodeManager(mock_client)

        driver_mgr = manager.all_drivers

        assert isinstance(driver_mgr, NodeDriverManager)
        assert driver_mgr._node_key is None

    def test_all_pci_devices_returns_global_manager(self) -> None:
        """Test all_pci_devices property returns global NodePCIDeviceManager."""
        mock_client = MagicMock()
        manager = NodeManager(mock_client)

        pci_mgr = manager.all_pci_devices

        assert isinstance(pci_mgr, NodePCIDeviceManager)
        assert pci_mgr._node_key is None

    def test_all_usb_devices_returns_global_manager(self) -> None:
        """Test all_usb_devices property returns global NodeUSBDeviceManager."""
        mock_client = MagicMock()
        manager = NodeManager(mock_client)

        usb_mgr = manager.all_usb_devices

        assert isinstance(usb_mgr, NodeUSBDeviceManager)
        assert usb_mgr._node_key is None


class TestNodeDriverManager:
    """Tests for NodeDriverManager."""

    def test_init(self) -> None:
        """Test NodeDriverManager initialization."""
        mock_client = MagicMock()
        manager = NodeDriverManager(mock_client)
        assert manager._client == mock_client
        assert manager._endpoint == "node_drivers"
        assert manager._node_key is None

    def test_init_with_node_key(self) -> None:
        """Test NodeDriverManager initialization with node_key."""
        mock_client = MagicMock()
        manager = NodeDriverManager(mock_client, node_key=5)
        assert manager._node_key == 5

    def test_list_applies_node_filter(self) -> None:
        """Test list applies node filter when scoped."""
        mock_client = MagicMock()
        mock_client._request.return_value = []
        manager = NodeDriverManager(mock_client, node_key=5)

        manager.list()

        call_args = mock_client._request.call_args
        assert "node eq 5" in call_args[1]["params"]["filter"]

    def test_list_with_driver_name_filter(self) -> None:
        """Test list with driver_name filter."""
        mock_client = MagicMock()
        mock_client._request.return_value = []
        manager = NodeDriverManager(mock_client)

        manager.list(driver_name="nvidia")

        call_args = mock_client._request.call_args
        assert "driver_name ct 'nvidia'" in call_args[1]["params"]["filter"]

    def test_list_with_status_filter(self) -> None:
        """Test list with status filter."""
        mock_client = MagicMock()
        mock_client._request.return_value = []
        manager = NodeDriverManager(mock_client)

        manager.list(status="Installed")

        call_args = mock_client._request.call_args
        assert "status eq 'complete'" in call_args[1]["params"]["filter"]


class TestNodePCIDeviceManager:
    """Tests for NodePCIDeviceManager."""

    def test_init(self) -> None:
        """Test NodePCIDeviceManager initialization."""
        mock_client = MagicMock()
        manager = NodePCIDeviceManager(mock_client)
        assert manager._client == mock_client
        assert manager._endpoint == "node_pci_devices"
        assert manager._node_key is None

    def test_init_with_node_key(self) -> None:
        """Test NodePCIDeviceManager initialization with node_key."""
        mock_client = MagicMock()
        manager = NodePCIDeviceManager(mock_client, node_key=5)
        assert manager._node_key == 5

    def test_list_applies_node_filter(self) -> None:
        """Test list applies node filter when scoped."""
        mock_client = MagicMock()
        mock_client._request.return_value = []
        manager = NodePCIDeviceManager(mock_client, node_key=5)

        manager.list()

        call_args = mock_client._request.call_args
        assert "node eq 5" in call_args[1]["params"]["filter"]

    def test_list_with_device_type_gpu_filter(self) -> None:
        """Test list with device_type=GPU filter."""
        mock_client = MagicMock()
        mock_client._request.return_value = []
        manager = NodePCIDeviceManager(mock_client)

        manager.list(device_type="GPU")

        call_args = mock_client._request.call_args
        assert "device_type eq '03'" in call_args[1]["params"]["filter"]

    def test_list_with_device_type_network_filter(self) -> None:
        """Test list with device_type=Network filter."""
        mock_client = MagicMock()
        mock_client._request.return_value = []
        manager = NodePCIDeviceManager(mock_client)

        manager.list(device_type="Network")

        call_args = mock_client._request.call_args
        assert "device_type eq '02'" in call_args[1]["params"]["filter"]

    def test_list_with_device_type_storage_filter(self) -> None:
        """Test list with device_type=Storage filter."""
        mock_client = MagicMock()
        mock_client._request.return_value = []
        manager = NodePCIDeviceManager(mock_client)

        manager.list(device_type="Storage")

        call_args = mock_client._request.call_args
        assert "device_type eq '01'" in call_args[1]["params"]["filter"]

    def test_list_with_vendor_filter(self) -> None:
        """Test list with vendor filter."""
        mock_client = MagicMock()
        mock_client._request.return_value = []
        manager = NodePCIDeviceManager(mock_client)

        manager.list(vendor="NVIDIA")

        call_args = mock_client._request.call_args
        assert "vendor ct 'NVIDIA'" in call_args[1]["params"]["filter"]


class TestNodeUSBDeviceManager:
    """Tests for NodeUSBDeviceManager."""

    def test_init(self) -> None:
        """Test NodeUSBDeviceManager initialization."""
        mock_client = MagicMock()
        manager = NodeUSBDeviceManager(mock_client)
        assert manager._client == mock_client
        assert manager._endpoint == "node_usb_devices"
        assert manager._node_key is None

    def test_init_with_node_key(self) -> None:
        """Test NodeUSBDeviceManager initialization with node_key."""
        mock_client = MagicMock()
        manager = NodeUSBDeviceManager(mock_client, node_key=5)
        assert manager._node_key == 5

    def test_list_applies_node_filter(self) -> None:
        """Test list applies node filter when scoped."""
        mock_client = MagicMock()
        mock_client._request.return_value = []
        manager = NodeUSBDeviceManager(mock_client, node_key=5)

        manager.list()

        call_args = mock_client._request.call_args
        assert "node eq 5" in call_args[1]["params"]["filter"]

    def test_list_with_vendor_filter(self) -> None:
        """Test list with vendor filter."""
        mock_client = MagicMock()
        mock_client._request.return_value = []
        manager = NodeUSBDeviceManager(mock_client)

        manager.list(vendor="Logitech")

        call_args = mock_client._request.call_args
        assert "vendor ct 'Logitech'" in call_args[1]["params"]["filter"]

    def test_list_with_model_filter(self) -> None:
        """Test list with model filter."""
        mock_client = MagicMock()
        mock_client._request.return_value = []
        manager = NodeUSBDeviceManager(mock_client)

        manager.list(model="Mouse")

        call_args = mock_client._request.call_args
        assert "model ct 'Mouse'" in call_args[1]["params"]["filter"]


class TestConstants:
    """Tests for module constants."""

    def test_status_display_mappings(self) -> None:
        """Test STATUS_DISPLAY contains expected mappings."""
        assert STATUS_DISPLAY["running"] == "Running"
        assert STATUS_DISPLAY["stopped"] == "Stopped"
        assert STATUS_DISPLAY["online"] == "Online"
        assert STATUS_DISPLAY["offline"] == "Offline"
        assert STATUS_DISPLAY["maintenance"] == "Maintenance"

    def test_device_type_codes(self) -> None:
        """Test DEVICE_TYPE_CODES contains expected mappings."""
        assert DEVICE_TYPE_CODES["00"] == "Unclassified device"
        assert DEVICE_TYPE_CODES["01"] == "Mass storage controller"
        assert DEVICE_TYPE_CODES["02"] == "Network controller"
        assert DEVICE_TYPE_CODES["03"] == "Display controller"

    def test_driver_status_display(self) -> None:
        """Test DRIVER_STATUS_DISPLAY contains expected mappings."""
        assert DRIVER_STATUS_DISPLAY["complete"] == "Installed"
        assert DRIVER_STATUS_DISPLAY["verifying"] == "Verifying"
        assert DRIVER_STATUS_DISPLAY["error"] == "Error"
