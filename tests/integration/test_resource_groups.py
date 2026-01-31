"""Integration tests for ResourceGroup operations.

These tests require a live VergeOS system and will be skipped
if the environment variables are not set.
"""

from __future__ import annotations

import contextlib

import pytest

from pyvergeos import VergeClient
from pyvergeos.exceptions import NotFoundError
from pyvergeos.resources.resource_groups import (
    DEVICE_CLASS_MAP,
    DEVICE_TYPE_MAP,
    ResourceGroup,
)


@pytest.mark.integration
class TestResourceGroupListIntegration:
    """Integration tests for ResourceGroupManager list operations."""

    def test_list_resource_groups(self, live_client: VergeClient) -> None:
        """Test listing resource groups from live system."""
        groups = live_client.resource_groups.list()

        # Should return a list (may be empty if no resource groups configured)
        assert isinstance(groups, list)

        # Each group should have expected properties
        for group in groups:
            assert isinstance(group, ResourceGroup)
            assert hasattr(group, "key")
            assert hasattr(group, "uuid")
            assert hasattr(group, "name")
            assert hasattr(group, "device_type")
            assert hasattr(group, "device_type_display")
            assert hasattr(group, "device_class")
            assert hasattr(group, "device_class_display")
            assert hasattr(group, "is_enabled")
            assert hasattr(group, "resource_count")

    def test_list_resource_groups_with_limit(self, live_client: VergeClient) -> None:
        """Test listing resource groups with limit."""
        groups = live_client.resource_groups.list(limit=1)

        assert isinstance(groups, list)
        assert len(groups) <= 1

    def test_list_enabled_resource_groups(self, live_client: VergeClient) -> None:
        """Test listing enabled resource groups."""
        groups = live_client.resource_groups.list_enabled()

        assert isinstance(groups, list)
        for group in groups:
            assert group.is_enabled is True

    def test_list_disabled_resource_groups(self, live_client: VergeClient) -> None:
        """Test listing disabled resource groups."""
        groups = live_client.resource_groups.list_disabled()

        assert isinstance(groups, list)
        for group in groups:
            assert group.is_enabled is False


@pytest.mark.integration
class TestResourceGroupGetIntegration:
    """Integration tests for ResourceGroupManager get operations."""

    def test_get_resource_group_by_key(self, live_client: VergeClient) -> None:
        """Test getting a resource group by key."""
        # First get a group from the list
        groups = live_client.resource_groups.list()
        if not groups:
            pytest.skip("No resource groups available for testing")

        group = groups[0]
        fetched = live_client.resource_groups.get(group.key)

        assert fetched.key == group.key
        assert fetched.name == group.name
        assert fetched.uuid == group.uuid

    def test_get_resource_group_by_name(self, live_client: VergeClient) -> None:
        """Test getting a resource group by name."""
        # First get a group from the list
        groups = live_client.resource_groups.list()
        if not groups:
            pytest.skip("No resource groups available for testing")

        group = groups[0]
        fetched = live_client.resource_groups.get(name=group.name)

        assert fetched.key == group.key
        assert fetched.name == group.name

    def test_get_resource_group_by_uuid(self, live_client: VergeClient) -> None:
        """Test getting a resource group by UUID."""
        # First get a group from the list
        groups = live_client.resource_groups.list()
        if not groups:
            pytest.skip("No resource groups available for testing")

        group = groups[0]
        fetched = live_client.resource_groups.get(uuid=group.uuid)

        assert fetched.key == group.key
        assert fetched.uuid == group.uuid

    def test_get_resource_group_not_found(self, live_client: VergeClient) -> None:
        """Test getting a non-existent resource group."""
        with pytest.raises(NotFoundError):
            live_client.resource_groups.get(name="non-existent-resource-group-12345")


@pytest.mark.integration
class TestResourceGroupFilterIntegration:
    """Integration tests for ResourceGroupManager filter operations."""

    def test_list_by_type(self, live_client: VergeClient) -> None:
        """Test listing resource groups by device type."""
        groups = live_client.resource_groups.list()
        if not groups:
            pytest.skip("No resource groups available for testing")

        # Get a type from existing groups
        device_type = groups[0].device_type

        # Filter by that type
        filtered = live_client.resource_groups.list_by_type(device_type)

        assert isinstance(filtered, list)
        for group in filtered:
            assert group.device_type == device_type

    def test_list_by_type_with_display_name(self, live_client: VergeClient) -> None:
        """Test listing resource groups by device type display name."""
        groups = live_client.resource_groups.list()
        if not groups:
            pytest.skip("No resource groups available for testing")

        # Get a display name from existing groups
        device_type_display = groups[0].device_type_display

        # Filter by that display name
        filtered = live_client.resource_groups.list_by_type(device_type_display)

        assert isinstance(filtered, list)
        for group in filtered:
            assert group.device_type_display == device_type_display

    def test_list_by_class(self, live_client: VergeClient) -> None:
        """Test listing resource groups by device class."""
        groups = live_client.resource_groups.list()
        if not groups:
            pytest.skip("No resource groups available for testing")

        # Get a class from existing groups
        device_class = groups[0].device_class

        # Filter by that class
        filtered = live_client.resource_groups.list_by_class(device_class)

        assert isinstance(filtered, list)
        for group in filtered:
            assert group.device_class == device_class

    def test_list_by_type_with_enabled_filter(self, live_client: VergeClient) -> None:
        """Test listing resource groups by type with enabled filter."""
        groups = live_client.resource_groups.list()
        if not groups:
            pytest.skip("No resource groups available for testing")

        # Get a type from existing groups
        device_type = groups[0].device_type

        # Filter by type and enabled
        filtered = live_client.resource_groups.list_by_type(device_type, enabled=True)

        assert isinstance(filtered, list)
        for group in filtered:
            assert group.device_type == device_type
            assert group.is_enabled is True

    def test_list_by_class_with_enabled_filter(self, live_client: VergeClient) -> None:
        """Test listing resource groups by class with enabled filter."""
        groups = live_client.resource_groups.list()
        if not groups:
            pytest.skip("No resource groups available for testing")

        # Get a class from existing groups
        device_class = groups[0].device_class

        # Filter by class and enabled
        filtered = live_client.resource_groups.list_by_class(device_class, enabled=True)

        assert isinstance(filtered, list)
        for group in filtered:
            assert group.device_class == device_class
            assert group.is_enabled is True


@pytest.mark.integration
class TestResourceGroupPropertiesIntegration:
    """Integration tests for ResourceGroup properties."""

    def test_resource_group_properties(self, live_client: VergeClient) -> None:
        """Test that resource group properties are correctly populated."""
        groups = live_client.resource_groups.list()
        if not groups:
            pytest.skip("No resource groups available for testing")

        group = groups[0]

        # Test all property accessors work without error
        assert isinstance(group.key, int)
        assert isinstance(group.uuid, str)
        assert isinstance(group.name, str)
        assert isinstance(group.description, str)
        assert isinstance(group.device_type, str)
        assert isinstance(group.device_type_display, str)
        assert isinstance(group.device_class, str)
        assert isinstance(group.device_class_display, str)
        assert isinstance(group.is_enabled, bool)
        assert isinstance(group.resource_count, int)

        # UUID should be valid format
        if group.uuid:
            assert len(group.uuid) == 36  # UUID format: 8-4-4-4-12

        # Device type should be a known value
        assert (
            group.device_type in DEVICE_TYPE_MAP
            or group.device_type_display in DEVICE_TYPE_MAP.values()
        )

        # Device class should be a known value
        assert (
            group.device_class in DEVICE_CLASS_MAP
            or group.device_class_display in DEVICE_CLASS_MAP.values()
        )

    def test_resource_group_timestamps(self, live_client: VergeClient) -> None:
        """Test that resource group timestamps are valid."""
        groups = live_client.resource_groups.list()
        if not groups:
            pytest.skip("No resource groups available for testing")

        group = groups[0]

        # created_at and modified_at may be None or datetime
        if group.created_at is not None:
            assert group.created_at.year >= 2020  # Sanity check

        if group.modified_at is not None:
            assert group.modified_at.year >= 2020  # Sanity check

            # modified_at should be >= created_at if both exist
            if group.created_at is not None:
                assert group.modified_at >= group.created_at

    def test_resource_group_repr(self, live_client: VergeClient) -> None:
        """Test resource group string representation."""
        groups = live_client.resource_groups.list()
        if not groups:
            pytest.skip("No resource groups available for testing")

        group = groups[0]
        repr_str = repr(group)

        assert "ResourceGroup" in repr_str
        assert group.name in repr_str


@pytest.mark.integration
class TestResourceGroupIterationIntegration:
    """Integration tests for ResourceGroupManager iteration."""

    def test_iter_all_resource_groups(self, live_client: VergeClient) -> None:
        """Test iterating through all resource groups."""
        # Use iter_all with small page size to test pagination
        count = 0
        for group in live_client.resource_groups.iter_all(page_size=2):
            assert isinstance(group, ResourceGroup)
            count += 1

        # Count should match list() count
        all_groups = live_client.resource_groups.list()
        assert count == len(all_groups)

    def test_manager_iteration(self, live_client: VergeClient) -> None:
        """Test direct iteration over manager."""
        groups_from_iter = list(live_client.resource_groups)
        groups_from_list = live_client.resource_groups.list()

        assert len(groups_from_iter) == len(groups_from_list)


@pytest.mark.integration
class TestResourceGroupCRUDIntegration:
    """Integration tests for ResourceGroup CRUD operations.

    Note: These tests create, modify, and delete resource groups on a live system.
    They clean up after themselves but may leave orphaned resources if interrupted.
    """

    def test_create_pci_resource_group(self, live_client: VergeClient) -> None:
        """Test creating a PCI resource group."""
        group = None
        try:
            group = live_client.resource_groups.create_pci(
                name="SDK-Test-PCI-Pool",
                device_class="storage",
                description="Test PCI resource group from SDK integration tests",
            )

            assert group.key is not None
            assert group.name == "SDK-Test-PCI-Pool"
            assert group.device_type == "node_pci_devices"
            assert group.device_class == "storage"
            assert group.is_enabled is True
        finally:
            if group:
                with contextlib.suppress(Exception):
                    live_client.resource_groups.delete(group.key)

    def test_create_usb_resource_group(self, live_client: VergeClient) -> None:
        """Test creating a USB resource group."""
        group = None
        try:
            group = live_client.resource_groups.create_usb(
                name="SDK-Test-USB-Pool",
                allow_guest_reset=True,
                allow_guest_reset_all=False,
                device_class="hid",
                description="Test USB resource group from SDK",
            )

            assert group.key is not None
            assert group.name == "SDK-Test-USB-Pool"
            assert group.device_type == "node_usb_devices"
        finally:
            if group:
                with contextlib.suppress(Exception):
                    live_client.resource_groups.delete(group.key)

    def test_create_host_gpu_resource_group(self, live_client: VergeClient) -> None:
        """Test creating a host GPU resource group."""
        group = None
        try:
            group = live_client.resource_groups.create_host_gpu(
                name="SDK-Test-GPU-Pool",
                description="Test GPU resource group from SDK",
            )

            assert group.key is not None
            assert group.name == "SDK-Test-GPU-Pool"
            assert group.device_type == "node_host_gpu_devices"
            assert group.device_class == "gpu"
        finally:
            if group:
                with contextlib.suppress(Exception):
                    live_client.resource_groups.delete(group.key)

    def test_update_resource_group(self, live_client: VergeClient) -> None:
        """Test updating a resource group."""
        group = None
        try:
            # Create
            group = live_client.resource_groups.create_pci(
                name="SDK-Test-Update-Pool",
                description="Original description",
            )

            # Update
            updated = live_client.resource_groups.update(
                group.key,
                description="Updated description",
                enabled=False,
            )

            assert updated.description == "Updated description"
            assert updated.is_enabled is False

            # Verify with fresh get
            fetched = live_client.resource_groups.get(group.key)
            assert fetched.description == "Updated description"
        finally:
            if group:
                with contextlib.suppress(Exception):
                    live_client.resource_groups.delete(group.key)

    def test_resource_group_save_method(self, live_client: VergeClient) -> None:
        """Test ResourceGroup.save() method."""
        group = None
        try:
            group = live_client.resource_groups.create_pci(name="SDK-Test-Save-Pool")

            # Update via save()
            updated = group.save(description="Saved description")

            assert updated.description == "Saved description"
        finally:
            if group:
                with contextlib.suppress(Exception):
                    live_client.resource_groups.delete(group.key)

    def test_resource_group_refresh_method(self, live_client: VergeClient) -> None:
        """Test ResourceGroup.refresh() method."""
        group = None
        try:
            group = live_client.resource_groups.create_pci(name="SDK-Test-Refresh-Pool")

            # Update via manager
            live_client.resource_groups.update(group.key, description="New desc")

            # Refresh the original object
            refreshed = group.refresh()

            assert refreshed.description == "New desc"
        finally:
            if group:
                with contextlib.suppress(Exception):
                    live_client.resource_groups.delete(group.key)

    def test_delete_resource_group(self, live_client: VergeClient) -> None:
        """Test deleting a resource group."""
        # Create
        group = live_client.resource_groups.create_pci(name="SDK-Test-Delete-Pool")
        group_key = group.key

        # Delete
        live_client.resource_groups.delete(group_key)

        # Verify deleted
        with pytest.raises(NotFoundError):
            live_client.resource_groups.get(group_key)


@pytest.mark.integration
class TestResourceRuleIntegration:
    """Integration tests for ResourceRule operations."""

    def test_list_rules_for_group(self, live_client: VergeClient) -> None:
        """Test listing rules for a resource group."""
        group = None
        try:
            group = live_client.resource_groups.create_pci(name="SDK-Test-Rule-Pool")

            # List rules (may be empty initially)
            rules = group.rules.list()

            assert isinstance(rules, list)
        finally:
            if group:
                with contextlib.suppress(Exception):
                    live_client.resource_groups.delete(group.key)

    def test_create_rule(self, live_client: VergeClient) -> None:
        """Test creating a resource rule."""
        group = None
        try:
            group = live_client.resource_groups.create_pci(name="SDK-Test-RuleCreate-Pool")

            rule = group.rules.create(
                name="SDK-Test-Rule",
                filter_expression="vendor ct 'Intel'",
            )

            assert rule.key is not None
            assert rule.name == "SDK-Test-Rule"
            assert rule.filter_expression == "vendor ct 'Intel'"
            assert rule.resource_group_key == group.key

            # Clean up rule before group
            rule.delete()
        finally:
            if group:
                with contextlib.suppress(Exception):
                    live_client.resource_groups.delete(group.key)

    def test_update_rule(self, live_client: VergeClient) -> None:
        """Test updating a resource rule."""
        group = None
        try:
            group = live_client.resource_groups.create_pci(name="SDK-Test-RuleUpdate-Pool")

            rule = group.rules.create(
                name="SDK-Test-Update-Rule",
                filter_expression="vendor ct 'Intel'",
            )

            # Update via manager
            updated = group.rules.update(rule.key, name="SDK-Test-Updated-Rule", enabled=False)

            assert updated.name == "SDK-Test-Updated-Rule"
            assert updated.is_enabled is False

            # Clean up
            rule.delete()
        finally:
            if group:
                with contextlib.suppress(Exception):
                    live_client.resource_groups.delete(group.key)


@pytest.mark.integration
class TestNodeSriovNicDevices:
    """Integration tests for SR-IOV NIC device discovery."""

    def test_list_all_sriov_nics(self, live_client: VergeClient) -> None:
        """Test listing all SR-IOV NIC devices."""
        devices = live_client.nodes.all_sriov_nics.list()

        assert isinstance(devices, list)
        print(f"Found {len(devices)} SR-IOV NIC device(s)")

        for device in devices:
            print(f"  {device.name} on {device.node_name}")
            print(f"    Slot: {device.slot}")
            print(f"    PF: {device.physical_function}")

    def test_list_sriov_nics_for_node(self, live_client: VergeClient) -> None:
        """Test listing SR-IOV NIC devices for a specific node."""
        nodes = live_client.nodes.list()
        if not nodes:
            pytest.skip("No nodes available")

        for node in nodes:
            devices = node.sriov_nics.list()
            if devices:
                print(f"Node {node.name} has {len(devices)} SR-IOV NIC(s)")
                for device in devices:
                    assert device.node_key == node.key
                return

        print("No SR-IOV NIC devices found on any node")

    def test_list_sriov_nics_by_vendor(self, live_client: VergeClient) -> None:
        """Test filtering SR-IOV NIC devices by vendor."""
        # Try common vendors
        for vendor in ["Intel", "Mellanox", "Broadcom"]:
            devices = live_client.nodes.all_sriov_nics.list(vendor=vendor)
            if devices:
                print(f"Found {len(devices)} {vendor} SR-IOV NIC(s)")
                for device in devices:
                    assert vendor.lower() in device.vendor.lower()
                return

        print("No vendor-specific SR-IOV NICs found")


@pytest.mark.integration
class TestDeviceDiscoveryWorkflow:
    """Integration tests for complete device discovery workflows."""

    def test_pci_device_to_resource_group_workflow(self, live_client: VergeClient) -> None:
        """Test workflow: discover PCI devices -> create resource group -> add rule."""
        # 1. Discover PCI devices
        pci_devices = live_client.nodes.all_pci_devices.list(device_type="Network")
        print(f"Found {len(pci_devices)} network PCI device(s)")

        if not pci_devices:
            pytest.skip("No network PCI devices available")

        device = pci_devices[0]
        print(f"Using device: {device.name} ({device.slot})")

        group = None
        try:
            # 2. Create resource group
            group = live_client.resource_groups.create_pci(
                name="SDK-Test-Workflow-Pool",
                device_class="network",
                description="Created from workflow test",
            )
            print(f"Created resource group: {group.name} (key={group.key})")

            # 3. Create rule to match the device
            rule = group.rules.create(
                name="Match-Test-Device",
                filter_expression=f"slot eq '{device.slot}'",
                node=device.node_key,
            )
            print(f"Created rule: {rule.name}")

            # 4. Verify rule was created
            rules = group.rules.list()
            assert len(rules) >= 1
            assert any(r.name == "Match-Test-Device" for r in rules)

            # Cleanup rule
            rule.delete()
        finally:
            if group:
                with contextlib.suppress(Exception):
                    live_client.resource_groups.delete(group.key)

    def test_usb_device_discovery(self, live_client: VergeClient) -> None:
        """Test discovering USB devices across nodes."""
        usb_devices = live_client.nodes.all_usb_devices.list()
        print(f"Found {len(usb_devices)} USB device(s) across all nodes")

        for device in usb_devices[:5]:  # Print first 5
            print(f"  {device.model} ({device.vendor}) on {device.node_name}")
            print(f"    Path: {device.path}, USB: {device.usb_version}")

    def test_pci_device_gpu_discovery(self, live_client: VergeClient) -> None:
        """Test discovering GPU PCI devices."""
        gpu_devices = live_client.nodes.all_pci_devices.list(device_type="GPU")
        print(f"Found {len(gpu_devices)} GPU device(s)")

        for device in gpu_devices:
            print(f"  {device.name} on {device.node_name}")
            print(f"    Vendor: {device.vendor}")
            print(f"    Slot: {device.slot}")
            print(f"    Driver: {device.driver}")
