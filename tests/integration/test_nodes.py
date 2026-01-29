"""Integration tests for Node operations.

These tests require a live VergeOS system and will be skipped
if the environment variables are not set.
"""

from __future__ import annotations

import pytest

from pyvergeos import VergeClient
from pyvergeos.exceptions import NotFoundError


@pytest.mark.integration
class TestNodeListIntegration:
    """Integration tests for NodeManager.list()."""

    def test_list_nodes(self, live_client: VergeClient) -> None:
        """Test listing nodes from live system."""
        nodes = live_client.nodes.list()

        # Should have at least one node
        assert isinstance(nodes, list)
        if not nodes:
            pytest.skip("No nodes found on system")

        # Each node should have expected properties
        for node in nodes:
            assert hasattr(node, "key")
            assert hasattr(node, "name")
            assert node.key > 0
            assert node.name

    def test_list_nodes_with_limit(self, live_client: VergeClient) -> None:
        """Test listing nodes with limit."""
        nodes = live_client.nodes.list(limit=1)

        assert isinstance(nodes, list)
        assert len(nodes) <= 1

    def test_list_nodes_with_name_filter(self, live_client: VergeClient) -> None:
        """Test listing nodes filtered by name."""
        # First get all nodes
        all_nodes = live_client.nodes.list()
        if not all_nodes:
            pytest.skip("No nodes found on system")

        # Filter by the first node's name
        target_name = all_nodes[0].name
        filtered = live_client.nodes.list(name=target_name)

        assert len(filtered) >= 1
        assert all(n.name == target_name for n in filtered)

    def test_list_online_nodes(self, live_client: VergeClient) -> None:
        """Test listing only online nodes."""
        # First get all nodes to see if any are online
        all_nodes = live_client.nodes.list()
        online_nodes = [n for n in all_nodes if n.is_online]

        if not online_nodes:
            pytest.skip("No online nodes found")

        # List using the filter
        nodes = live_client.nodes.list(filter="running eq true")
        assert len(nodes) == len(online_nodes)

    def test_list_nodes_by_cluster(self, live_client: VergeClient) -> None:
        """Test listing nodes filtered by cluster."""
        # First get all nodes
        all_nodes = live_client.nodes.list()
        if not all_nodes:
            pytest.skip("No nodes found on system")

        # Find a node with a cluster assigned
        node_with_cluster = None
        for node in all_nodes:
            if node.cluster_key:
                node_with_cluster = node
                break

        if not node_with_cluster:
            pytest.skip("No nodes with clusters found")

        # Filter by cluster key using OData filter
        filtered = live_client.nodes.list(filter=f"cluster eq {node_with_cluster.cluster_key}")
        assert len(filtered) >= 1
        assert all(n.cluster_key == node_with_cluster.cluster_key for n in filtered)


@pytest.mark.integration
class TestNodeGetIntegration:
    """Integration tests for NodeManager.get()."""

    def test_get_node_by_key(self, live_client: VergeClient) -> None:
        """Test getting a node by key."""
        # First list to get a valid key
        nodes = live_client.nodes.list()
        if not nodes:
            pytest.skip("No nodes found on system")

        node = live_client.nodes.get(nodes[0].key)

        assert node.key == nodes[0].key
        assert node.name == nodes[0].name

    def test_get_node_by_name(self, live_client: VergeClient) -> None:
        """Test getting a node by name."""
        nodes = live_client.nodes.list()
        if not nodes:
            pytest.skip("No nodes found on system")

        node = live_client.nodes.get(name=nodes[0].name)

        assert node.name == nodes[0].name
        assert node.key == nodes[0].key

    def test_get_nonexistent_node(self, live_client: VergeClient) -> None:
        """Test that NotFoundError is raised for nonexistent node."""
        with pytest.raises(NotFoundError):
            live_client.nodes.get(999999)


@pytest.mark.integration
class TestNodePropertiesIntegration:
    """Integration tests for Node property accessors."""

    def test_node_properties(self, live_client: VergeClient) -> None:
        """Test node property accessors on live data."""
        nodes = live_client.nodes.list()
        if not nodes:
            pytest.skip("No nodes found on system")

        node = nodes[0]

        # Test all properties are accessible
        _ = node.key
        _ = node.name
        _ = node.description
        _ = node.model
        _ = node.cpu
        _ = node.is_online
        _ = node.is_maintenance
        _ = node.is_physical
        _ = node.status
        _ = node.status_raw
        _ = node.ram_mb
        _ = node.ram_gb
        _ = node.vm_ram_mb
        _ = node.overcommit_ram_mb
        _ = node.failover_ram_mb
        _ = node.cores
        _ = node.has_iommu
        _ = node.needs_restart
        _ = node.restart_reason
        _ = node.vsan_node_id
        _ = node.vsan_connected
        _ = node.cluster_key
        _ = node.cluster_name
        _ = node.asset_tag
        _ = node.ipmi_address
        _ = node.ipmi_status
        _ = node.vergeos_version
        _ = node.os_version
        _ = node.kernel_version
        _ = node.started_at

    def test_node_repr(self, live_client: VergeClient) -> None:
        """Test node string representation."""
        nodes = live_client.nodes.list()
        if not nodes:
            pytest.skip("No nodes found on system")

        node = nodes[0]
        repr_str = repr(node)

        assert "Node" in repr_str
        assert node.name in repr_str


@pytest.mark.integration
class TestNodeDriversIntegration:
    """Integration tests for NodeManager driver operations."""

    def test_list_all_drivers(self, live_client: VergeClient) -> None:
        """Test listing all drivers across nodes."""
        drivers = live_client.nodes.all_drivers.list()

        assert isinstance(drivers, list)
        # May or may not have drivers depending on system

    def test_list_drivers_for_node(self, live_client: VergeClient) -> None:
        """Test listing drivers for a specific node."""
        nodes = live_client.nodes.list()
        if not nodes:
            pytest.skip("No nodes found on system")

        drivers = live_client.nodes.drivers(nodes[0].key).list()

        assert isinstance(drivers, list)
        # All drivers should be for the specified node
        for driver in drivers:
            assert driver.node_key == nodes[0].key


@pytest.mark.integration
class TestNodePCIDevicesIntegration:
    """Integration tests for NodeManager PCI device operations."""

    def test_list_all_pci_devices(self, live_client: VergeClient) -> None:
        """Test listing all PCI devices across nodes."""
        devices = live_client.nodes.all_pci_devices.list()

        assert isinstance(devices, list)
        if not devices:
            pytest.skip("No PCI devices found")

        for device in devices:
            _ = device.key
            _ = device.node_key
            _ = device.name
            _ = device.slot
            _ = device.device_class
            _ = device.device_type
            _ = device.vendor

    def test_list_pci_devices_for_node(self, live_client: VergeClient) -> None:
        """Test listing PCI devices for a specific node."""
        nodes = live_client.nodes.list()
        if not nodes:
            pytest.skip("No nodes found on system")

        devices = live_client.nodes.pci_devices(nodes[0].key).list()

        assert isinstance(devices, list)
        # All devices should be for the specified node
        for device in devices:
            assert device.node_key == nodes[0].key

    def test_list_gpu_devices(self, live_client: VergeClient) -> None:
        """Test listing GPU devices."""
        devices = live_client.nodes.all_pci_devices.list(device_type="GPU")

        assert isinstance(devices, list)
        for device in devices:
            assert device.is_gpu is True


@pytest.mark.integration
class TestNodeUSBDevicesIntegration:
    """Integration tests for NodeManager USB device operations."""

    def test_list_all_usb_devices(self, live_client: VergeClient) -> None:
        """Test listing all USB devices across nodes."""
        devices = live_client.nodes.all_usb_devices.list()

        assert isinstance(devices, list)
        # May or may not have USB devices

    def test_list_usb_devices_for_node(self, live_client: VergeClient) -> None:
        """Test listing USB devices for a specific node."""
        nodes = live_client.nodes.list()
        if not nodes:
            pytest.skip("No nodes found on system")

        devices = live_client.nodes.usb_devices(nodes[0].key).list()

        assert isinstance(devices, list)
        # All devices should be for the specified node
        for device in devices:
            assert device.node_key == nodes[0].key
