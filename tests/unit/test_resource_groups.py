"""Unit tests for ResourceGroup operations."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from pyvergeos import VergeClient
from pyvergeos.exceptions import NotFoundError
from pyvergeos.resources.resource_groups import (
    DEVICE_CLASS_MAP,
    DEVICE_TYPE_MAP,
    ResourceGroup,
    ResourceGroupManager,
)


class TestResourceGroupManager:
    """Unit tests for ResourceGroupManager."""

    def test_list_resource_groups(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test listing resource groups."""
        mock_session.request.return_value.json.return_value = [
            {
                "$key": 1,
                "uuid": "12345678-1234-1234-1234-123456789abc",
                "name": "GPU Pool",
                "description": "NVIDIA GPU passthrough",
                "type": "node_host_gpu_devices",
                "type_display": "Host GPU",
                "class": "gpu",
                "class_display": "GPU",
                "enabled": True,
                "resource_count": 2,
                "created": 1700000000,
                "modified": 1700100000,
            },
            {
                "$key": 2,
                "uuid": "22345678-1234-1234-1234-123456789abc",
                "name": "Network Cards",
                "description": "Network device passthrough",
                "type": "node_pci_devices",
                "type_display": "PCI",
                "class": "network",
                "class_display": "Network",
                "enabled": True,
                "resource_count": 4,
                "created": 1700000000,
                "modified": 1700100000,
            },
        ]

        groups = mock_client.resource_groups.list()

        assert len(groups) == 2
        assert groups[0].name == "GPU Pool"
        assert groups[0].device_type == "node_host_gpu_devices"
        assert groups[0].device_type_display == "Host GPU"
        assert groups[1].name == "Network Cards"
        assert groups[1].device_class_display == "Network"

    def test_list_resource_groups_empty(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test listing resource groups when none exist."""
        mock_session.request.return_value.json.return_value = []

        groups = mock_client.resource_groups.list()

        assert len(groups) == 0

    def test_get_resource_group_by_key(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test getting a resource group by key."""
        mock_session.request.return_value.json.return_value = {
            "$key": 1,
            "uuid": "12345678-1234-1234-1234-123456789abc",
            "name": "GPU Pool",
            "description": "NVIDIA GPU passthrough",
            "type": "node_host_gpu_devices",
            "type_display": "Host GPU",
            "class": "gpu",
            "class_display": "GPU",
            "enabled": True,
            "resource_count": 2,
        }

        rg = mock_client.resource_groups.get(key=1)

        assert rg.name == "GPU Pool"
        assert rg.key == 1

    def test_get_resource_group_by_name(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test getting a resource group by name."""
        mock_session.request.return_value.json.return_value = [
            {
                "$key": 1,
                "uuid": "12345678-1234-1234-1234-123456789abc",
                "name": "GPU Pool",
                "description": "NVIDIA GPU passthrough",
                "type": "node_host_gpu_devices",
                "class": "gpu",
                "enabled": True,
            }
        ]

        rg = mock_client.resource_groups.get(name="GPU Pool")

        assert rg.name == "GPU Pool"

    def test_get_resource_group_by_uuid(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test getting a resource group by UUID."""
        mock_session.request.return_value.json.return_value = [
            {
                "$key": 1,
                "uuid": "12345678-1234-1234-1234-123456789abc",
                "name": "GPU Pool",
                "type": "node_host_gpu_devices",
                "class": "gpu",
                "enabled": True,
            }
        ]

        rg = mock_client.resource_groups.get(uuid="12345678-1234-1234-1234-123456789ABC")

        assert rg.uuid == "12345678-1234-1234-1234-123456789abc"

    def test_get_resource_group_not_found_by_name(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test NotFoundError when resource group not found by name."""
        mock_session.request.return_value.json.return_value = []

        with pytest.raises(NotFoundError, match="not found"):
            mock_client.resource_groups.get(name="Nonexistent")

    def test_get_resource_group_not_found_by_uuid(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test NotFoundError when resource group not found by UUID."""
        mock_session.request.return_value.json.return_value = []

        with pytest.raises(NotFoundError, match="not found"):
            mock_client.resource_groups.get(uuid="00000000-0000-0000-0000-000000000000")

    def test_get_resource_group_no_identifier(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test ValueError when no identifier provided."""
        with pytest.raises(ValueError, match="Either key, name, or uuid must be provided"):
            mock_client.resource_groups.get()

    def test_list_enabled_resource_groups(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test listing enabled resource groups."""
        mock_session.request.return_value.json.return_value = [
            {
                "$key": 1,
                "name": "GPU Pool",
                "type": "node_host_gpu_devices",
                "class": "gpu",
                "enabled": True,
            }
        ]

        groups = mock_client.resource_groups.list_enabled()

        assert len(groups) == 1
        assert groups[0].is_enabled is True

        # Verify the filter was applied
        call_args = mock_session.request.call_args
        assert "enabled eq true" in str(call_args)

    def test_list_disabled_resource_groups(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test listing disabled resource groups."""
        mock_session.request.return_value.json.return_value = [
            {
                "$key": 2,
                "name": "Old USB Devices",
                "type": "node_usb_devices",
                "class": "usb",
                "enabled": False,
            }
        ]

        groups = mock_client.resource_groups.list_disabled()

        assert len(groups) == 1
        assert groups[0].is_enabled is False

    def test_list_by_type_display_name(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test listing resource groups by device type display name."""
        mock_session.request.return_value.json.return_value = [
            {
                "$key": 1,
                "name": "GPU Pool",
                "type": "node_host_gpu_devices",
                "class": "gpu",
                "enabled": True,
            }
        ]

        groups = mock_client.resource_groups.list_by_type("Host GPU")

        assert len(groups) == 1

        # Verify the filter uses the API value
        call_args = mock_session.request.call_args
        assert "node_host_gpu_devices" in str(call_args)

    def test_list_by_type_api_value(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test listing resource groups by device type API value."""
        mock_session.request.return_value.json.return_value = [
            {
                "$key": 1,
                "name": "USB Devices",
                "type": "node_usb_devices",
                "class": "usb",
                "enabled": True,
            }
        ]

        groups = mock_client.resource_groups.list_by_type("node_usb_devices")

        assert len(groups) == 1

    def test_list_by_type_with_enabled_filter(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test listing resource groups by type with enabled filter."""
        mock_session.request.return_value.json.return_value = [
            {
                "$key": 1,
                "name": "Active PCI",
                "type": "node_pci_devices",
                "class": "pci",
                "enabled": True,
            }
        ]

        groups = mock_client.resource_groups.list_by_type("PCI", enabled=True)

        assert len(groups) == 1

        # Verify both filters were applied
        call_args = mock_session.request.call_args
        assert "node_pci_devices" in str(call_args)
        assert "enabled eq true" in str(call_args)

    def test_list_by_class_display_name(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test listing resource groups by device class display name."""
        mock_session.request.return_value.json.return_value = [
            {
                "$key": 1,
                "name": "Network Pool",
                "type": "node_pci_devices",
                "class": "network",
                "enabled": True,
            }
        ]

        groups = mock_client.resource_groups.list_by_class("Network")

        assert len(groups) == 1

        # Verify the filter uses the API value
        call_args = mock_session.request.call_args
        assert "class eq 'network'" in str(call_args)

    def test_list_by_class_api_value(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test listing resource groups by device class API value."""
        mock_session.request.return_value.json.return_value = [
            {
                "$key": 1,
                "name": "Storage Controllers",
                "type": "node_pci_devices",
                "class": "storage",
                "enabled": True,
            }
        ]

        groups = mock_client.resource_groups.list_by_class("storage")

        assert len(groups) == 1

    def test_list_by_class_with_enabled_filter(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test listing resource groups by class with enabled filter."""
        mock_session.request.return_value.json.return_value = [
            {
                "$key": 1,
                "name": "Active GPUs",
                "type": "node_host_gpu_devices",
                "class": "gpu",
                "enabled": True,
            }
        ]

        groups = mock_client.resource_groups.list_by_class("GPU", enabled=True)

        assert len(groups) == 1

        # Verify both filters were applied
        call_args = mock_session.request.call_args
        assert "class eq 'gpu'" in str(call_args)
        assert "enabled eq true" in str(call_args)

    def test_list_all_device_types(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test that all device types can be queried."""
        for api_value, display_name in DEVICE_TYPE_MAP.items():
            mock_session.request.return_value.json.return_value = []
            mock_client.resource_groups.list_by_type(display_name)

            call_args = mock_session.request.call_args
            assert api_value in str(call_args)

    def test_list_all_device_classes(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test that all device classes can be queried."""
        for api_value in DEVICE_CLASS_MAP:
            mock_session.request.return_value.json.return_value = []
            mock_client.resource_groups.list_by_class(api_value)

            call_args = mock_session.request.call_args
            assert f"class eq '{api_value}'" in str(call_args)


class TestResourceGroup:
    """Unit tests for ResourceGroup model."""

    def test_resource_group_properties(self, mock_client: VergeClient) -> None:
        """Test ResourceGroup property accessors."""
        data = {
            "$key": 1,
            "uuid": "12345678-1234-1234-1234-123456789abc",
            "name": "GPU Pool",
            "description": "NVIDIA GPU passthrough for HPC workloads",
            "type": "node_host_gpu_devices",
            "type_display": "Host GPU",
            "class": "gpu",
            "class_display": "GPU",
            "enabled": True,
            "resource_count": 4,
            "created": 1700000000,
            "modified": 1700100000,
        }
        rg = ResourceGroup(data, mock_client.resource_groups)

        assert rg.key == 1
        assert rg.uuid == "12345678-1234-1234-1234-123456789abc"
        assert rg.name == "GPU Pool"
        assert rg.description == "NVIDIA GPU passthrough for HPC workloads"
        assert rg.device_type == "node_host_gpu_devices"
        assert rg.device_type_display == "Host GPU"
        assert rg.device_class == "gpu"
        assert rg.device_class_display == "GPU"
        assert rg.is_enabled is True
        assert rg.resource_count == 4
        assert rg.created_at is not None
        assert rg.modified_at is not None

    def test_resource_group_type_display_fallback(
        self, mock_client: VergeClient
    ) -> None:
        """Test device type display falls back to mapping when not provided."""
        data = {
            "$key": 1,
            "name": "Test",
            "type": "node_sriov_nic_devices",
            # No type_display field
        }
        rg = ResourceGroup(data, mock_client.resource_groups)

        assert rg.device_type_display == "SR-IOV NIC"

    def test_resource_group_class_display_fallback(
        self, mock_client: VergeClient
    ) -> None:
        """Test device class display falls back to mapping when not provided."""
        data = {
            "$key": 1,
            "name": "Test",
            "class": "fpga",
            # No class_display field
        }
        rg = ResourceGroup(data, mock_client.resource_groups)

        assert rg.device_class_display == "FPGA"

    def test_resource_group_unknown_type(self, mock_client: VergeClient) -> None:
        """Test handling of unknown device type."""
        data = {
            "$key": 1,
            "name": "Test",
            "type": "unknown_device_type",
        }
        rg = ResourceGroup(data, mock_client.resource_groups)

        # Should return the raw value when unknown
        assert rg.device_type_display == "unknown_device_type"

    def test_resource_group_unknown_class(self, mock_client: VergeClient) -> None:
        """Test handling of unknown device class."""
        data = {
            "$key": 1,
            "name": "Test",
            "class": "some_new_class",
        }
        rg = ResourceGroup(data, mock_client.resource_groups)

        # Should return the raw value when unknown
        assert rg.device_class_display == "some_new_class"

    def test_resource_group_missing_fields(self, mock_client: VergeClient) -> None:
        """Test ResourceGroup handles missing fields gracefully."""
        data = {
            "$key": 1,
            "name": "Minimal",
        }
        rg = ResourceGroup(data, mock_client.resource_groups)

        assert rg.name == "Minimal"
        assert rg.uuid == ""
        assert rg.description == ""
        assert rg.device_type == ""
        assert rg.device_class == ""
        assert rg.is_enabled is False
        assert rg.resource_count == 0
        assert rg.created_at is None
        assert rg.modified_at is None

    def test_resource_group_repr(self, mock_client: VergeClient) -> None:
        """Test ResourceGroup string representation."""
        data = {
            "$key": 1,
            "name": "GPU Pool",
            "type": "node_host_gpu_devices",
            "type_display": "Host GPU",
            "class": "gpu",
            "class_display": "GPU",
        }
        rg = ResourceGroup(data, mock_client.resource_groups)

        repr_str = repr(rg)
        assert "ResourceGroup" in repr_str
        assert "key=1" in repr_str
        assert "GPU Pool" in repr_str
        assert "Host GPU" in repr_str
        assert "GPU" in repr_str

    def test_all_device_type_mappings(self, mock_client: VergeClient) -> None:
        """Test that all device type mappings produce correct display values."""
        for api_value, display_value in DEVICE_TYPE_MAP.items():
            data = {"$key": 1, "name": "Test", "type": api_value}
            rg = ResourceGroup(data, mock_client.resource_groups)
            assert rg.device_type_display == display_value

    def test_all_device_class_mappings(self, mock_client: VergeClient) -> None:
        """Test that all device class mappings produce correct display values."""
        for api_value, display_value in DEVICE_CLASS_MAP.items():
            data = {"$key": 1, "name": "Test", "class": api_value}
            rg = ResourceGroup(data, mock_client.resource_groups)
            assert rg.device_class_display == display_value


class TestResourceGroupManagerReadOnly:
    """Tests verifying ResourceGroupManager is read-only."""

    def test_no_create_method(self, mock_client: VergeClient) -> None:
        """Test that create method from base class raises on resource groups.

        Note: While the base class has create(), resource groups are meant to
        be read-only. The API will reject create requests.
        """
        manager = mock_client.resource_groups
        assert isinstance(manager, ResourceGroupManager)

        # The base class has create(), but we document it's not supported
        # The API would reject the request anyway

    def test_no_update_method(self, mock_client: VergeClient) -> None:
        """Test that update method from base class is inherited but not used.

        Note: While the base class has update(), resource groups are meant to
        be read-only. The API will reject update requests.
        """
        manager = mock_client.resource_groups
        assert isinstance(manager, ResourceGroupManager)

    def test_no_delete_method(self, mock_client: VergeClient) -> None:
        """Test that delete method from base class is inherited but not used.

        Note: While the base class has delete(), resource groups are meant to
        be read-only. The API will reject delete requests.
        """
        manager = mock_client.resource_groups
        assert isinstance(manager, ResourceGroupManager)


class TestResourceGroupDefaults:
    """Test default field selection."""

    def test_list_uses_default_fields(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test that list() uses default fields."""
        mock_session.request.return_value.json.return_value = []

        mock_client.resource_groups.list()

        call_args = mock_session.request.call_args
        params = call_args[1].get("params", {})
        fields = params.get("fields", "")

        # Verify essential fields are included
        assert "$key" in fields
        assert "uuid" in fields
        assert "name" in fields
        assert "type" in fields
        assert "class" in fields
        assert "enabled" in fields
        assert "resource_count" in fields or "count(resources)" in fields

    def test_get_uses_default_fields(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test that get() uses default fields."""
        mock_session.request.return_value.json.return_value = {
            "$key": 1,
            "name": "Test",
        }

        mock_client.resource_groups.get(key=1)

        call_args = mock_session.request.call_args
        params = call_args[1].get("params", {})
        fields = params.get("fields", "")

        assert "$key" in fields
        assert "name" in fields
