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

    def test_list_resource_groups(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
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

        rg = mock_client.resource_groups.get(key="12345678-1234-1234-1234-123456789abc")

        assert rg.name == "GPU Pool"
        assert rg.key == "12345678-1234-1234-1234-123456789abc"
        assert rg.uuid == "12345678-1234-1234-1234-123456789abc"

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

    def test_list_all_device_types(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
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

        # ResourceGroup.key now returns UUID (resource groups use UUID as primary key)
        assert rg.key == "12345678-1234-1234-1234-123456789abc"
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

    def test_resource_group_type_display_fallback(self, mock_client: VergeClient) -> None:
        """Test device type display falls back to mapping when not provided."""
        data = {
            "$key": 1,
            "name": "Test",
            "type": "node_sriov_nic_devices",
            # No type_display field
        }
        rg = ResourceGroup(data, mock_client.resource_groups)

        assert rg.device_type_display == "SR-IOV NIC"

    def test_resource_group_class_display_fallback(self, mock_client: VergeClient) -> None:
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
            "uuid": "12345678-1234-1234-1234-123456789abc",
            "name": "GPU Pool",
            "type": "node_host_gpu_devices",
            "type_display": "Host GPU",
            "class": "gpu",
            "class_display": "GPU",
        }
        rg = ResourceGroup(data, mock_client.resource_groups)

        repr_str = repr(rg)
        assert "ResourceGroup" in repr_str
        assert "uuid='12345678-1234-1234-1234-123456789abc'" in repr_str
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


class TestResourceGroupCRUD:
    """Tests for ResourceGroup CRUD operations."""

    def test_create_resource_group(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test creating a resource group."""
        test_uuid = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
        # First call returns the created object, second call returns full object
        mock_session.request.return_value.json.side_effect = [
            {"$key": 10, "uuid": test_uuid, "name": "Test Pool"},
            [
                {
                    "$key": 10,
                    "uuid": test_uuid,
                    "name": "Test Pool",
                    "type": "node_pci_devices",
                    "enabled": True,
                }
            ],
        ]

        rg = mock_client.resource_groups.create(
            name="Test Pool",
            device_type="node_pci_devices",
            description="Test description",
            device_class="pci",
        )

        assert rg.key == test_uuid
        assert rg.name == "Test Pool"

        # Verify POST was called with expected data
        call_str = str(mock_session.request.call_args_list)
        assert "POST" in call_str
        assert "resource_groups" in call_str
        assert "'name': 'Test Pool'" in call_str
        assert "'type': 'node_pci_devices'" in call_str

    def test_create_nvidia_vgpu(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test creating an NVIDIA vGPU resource group."""
        test_uuid = "11111111-2222-3333-4444-555555555555"
        mock_session.request.return_value.json.side_effect = [
            {"$key": 11, "uuid": test_uuid},
            [
                {
                    "$key": 11,
                    "uuid": test_uuid,
                    "name": "vGPU Pool",
                    "type": "node_nvidia_vgpu_devices",
                }
            ],
        ]

        rg = mock_client.resource_groups.create_nvidia_vgpu(
            name="vGPU Pool",
            driver_file=100,
            nvidia_vgpu_profile=50,
            make_guest_driver_iso=True,
        )

        assert rg.key == test_uuid

        # Verify settings_args
        call_str = str(mock_session.request.call_args_list)
        assert "'type': 'node_nvidia_vgpu_devices'" in call_str
        assert "'driver_file': 100" in call_str
        assert "'nvidia_vgpu_profile': 50" in call_str
        assert "'make_guest_driver_iso': True" in call_str

    def test_create_usb(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test creating a USB resource group."""
        test_uuid = "22222222-3333-4444-5555-666666666666"
        mock_session.request.return_value.json.side_effect = [
            {"$key": 12, "uuid": test_uuid},
            [{"$key": 12, "uuid": test_uuid, "name": "USB Pool", "type": "node_usb_devices"}],
        ]

        rg = mock_client.resource_groups.create_usb(
            name="USB Pool",
            allow_guest_reset=False,
            device_class="hid",
        )

        assert rg.key == test_uuid

        call_str = str(mock_session.request.call_args_list)
        assert "'type': 'node_usb_devices'" in call_str
        assert "'guest_reset': False" in call_str

    def test_create_sriov_nic(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test creating an SR-IOV NIC resource group."""
        test_uuid = "33333333-4444-5555-6666-777777777777"
        mock_session.request.return_value.json.side_effect = [
            {"$key": 13, "uuid": test_uuid},
            [
                {
                    "$key": 13,
                    "uuid": test_uuid,
                    "name": "SR-IOV Pool",
                    "type": "node_sriov_nic_devices",
                }
            ],
        ]

        rg = mock_client.resource_groups.create_sriov_nic(
            name="SR-IOV Pool",
            vf_count=8,
            native_vlan=100,
            trust="on",
        )

        assert rg.key == test_uuid

        call_str = str(mock_session.request.call_args_list)
        assert "'type': 'node_sriov_nic_devices'" in call_str
        assert "'numvfs': 8" in call_str
        assert "'vlan': 100" in call_str
        assert "'trust': 'on'" in call_str

    def test_create_pci(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test creating a PCI resource group."""
        test_uuid = "44444444-5555-6666-7777-888888888888"
        mock_session.request.return_value.json.side_effect = [
            {"$key": 14, "uuid": test_uuid},
            [{"$key": 14, "uuid": test_uuid, "name": "PCI Pool", "type": "node_pci_devices"}],
        ]

        rg = mock_client.resource_groups.create_pci(
            name="PCI Pool",
            device_class="storage",
        )

        assert rg.key == test_uuid

        call_str = str(mock_session.request.call_args_list)
        assert "'type': 'node_pci_devices'" in call_str
        assert "'class': 'storage'" in call_str

    def test_create_host_gpu(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test creating a host GPU resource group."""
        test_uuid = "55555555-6666-7777-8888-999999999999"
        mock_session.request.return_value.json.side_effect = [
            {"$key": 15, "uuid": test_uuid},
            [{"$key": 15, "uuid": test_uuid, "name": "GPU Pool", "type": "node_host_gpu_devices"}],
        ]

        rg = mock_client.resource_groups.create_host_gpu(
            name="GPU Pool",
            device_keys=[1, 2, 3],
        )

        assert rg.key == test_uuid

        call_str = str(mock_session.request.call_args_list)
        assert "'type': 'node_host_gpu_devices'" in call_str
        assert "'class': 'gpu'" in call_str
        assert "'key_args': [1, 2, 3]" in call_str

    def test_update_resource_group(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test updating a resource group."""
        mock_session.request.return_value.json.return_value = {
            "$key": 1,
            "name": "Updated Pool",
            "enabled": False,
        }

        rg = mock_client.resource_groups.update(1, name="Updated Pool", enabled=False)

        assert rg.name == "Updated Pool"

        call_str = str(mock_session.request.call_args)
        assert "PUT" in call_str
        assert "resource_groups/1" in call_str
        assert "'name': 'Updated Pool'" in call_str

    def test_delete_resource_group(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test deleting a resource group."""
        mock_session.request.return_value.json.return_value = None

        mock_client.resource_groups.delete(1)

        call_str = str(mock_session.request.call_args)
        assert "DELETE" in call_str
        assert "resource_groups/1" in call_str

    def test_resource_group_save(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test ResourceGroup.save() method."""
        test_uuid = "66666666-7777-8888-9999-aaaaaaaaaaaa"
        data = {"$key": 1, "uuid": test_uuid, "name": "Original"}
        rg = ResourceGroup(data, mock_client.resource_groups)

        mock_session.request.return_value.json.return_value = {
            "$key": 1,
            "uuid": test_uuid,
            "name": "Modified",
        }

        updated = rg.save(name="Modified")
        assert updated.name == "Modified"

    def test_resource_group_delete(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test ResourceGroup.delete() method."""
        test_uuid = "77777777-8888-9999-aaaa-bbbbbbbbbbbb"
        data = {"$key": 1, "uuid": test_uuid, "name": "Test"}
        rg = ResourceGroup(data, mock_client.resource_groups)

        mock_session.request.return_value.json.return_value = None
        rg.delete()

        call_str = str(mock_session.request.call_args)
        assert "DELETE" in call_str

    def test_resource_group_refresh(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test ResourceGroup.refresh() method."""
        test_uuid = "88888888-9999-aaaa-bbbb-cccccccccccc"
        data = {"$key": 1, "uuid": test_uuid, "name": "Original"}
        rg = ResourceGroup(data, mock_client.resource_groups)

        mock_session.request.return_value.json.return_value = [
            {
                "$key": 1,
                "uuid": test_uuid,
                "name": "Refreshed",
                "description": "New description",
            }
        ]

        refreshed = rg.refresh()
        assert refreshed.description == "New description"


class TestResourceRuleManager:
    """Tests for ResourceRuleManager operations."""

    def test_list_rules(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test listing resource rules."""
        mock_session.request.return_value.json.return_value = [
            {
                "$key": 1,
                "resource_group": 10,
                "resource_group_display": "GPU Pool",
                "name": "Intel GPUs",
                "enabled": True,
                "type": "node_host_gpu_devices",
                "filter": "vendor ct 'Intel'",
                "resource_count": 2,
            },
        ]

        rules = mock_client.resource_groups.rules.list()

        assert len(rules) == 1
        assert rules[0].name == "Intel GPUs"
        assert rules[0].filter_expression == "vendor ct 'Intel'"
        assert rules[0].resource_count == 2

    def test_list_rules_scoped_to_group(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test listing rules scoped to a resource group."""
        test_uuid = "99999999-aaaa-bbbb-cccc-dddddddddddd"
        # First get the resource group
        mock_session.request.return_value.json.return_value = [
            {
                "$key": 10,
                "uuid": test_uuid,
                "name": "GPU Pool",
            }
        ]
        rg = mock_client.resource_groups.get(key=test_uuid)

        # Then list rules for that group
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "resource_group": test_uuid, "name": "Rule 1"},
        ]

        rules = rg.rules.list()

        assert len(rules) == 1

        # Verify filter includes resource_group with UUID in quotes
        call_args = mock_session.request.call_args
        params = call_args[1].get("params", {})
        assert f"resource_group eq '{test_uuid}'" in params.get("filter", "")

    def test_get_rule_by_key(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test getting a rule by key."""
        mock_session.request.return_value.json.return_value = {
            "$key": 1,
            "name": "Test Rule",
            "filter": "slot eq '03:00.0'",
        }

        rule = mock_client.resource_groups.rules.get(key=1)

        assert rule.key == 1
        assert rule.name == "Test Rule"

    def test_get_rule_by_name(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test getting a rule by name."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "name": "NVIDIA GPUs"},
        ]

        rule = mock_client.resource_groups.rules.get(name="NVIDIA GPUs")

        assert rule.name == "NVIDIA GPUs"

    def test_get_rule_not_found(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test NotFoundError when rule not found."""
        mock_session.request.return_value.json.return_value = []

        with pytest.raises(NotFoundError, match="not found"):
            mock_client.resource_groups.rules.get(name="Nonexistent")

    def test_create_rule_requires_scoped_manager(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test that create requires a scoped manager."""
        with pytest.raises(ValueError, match="scoped"):
            mock_client.resource_groups.rules.create(
                name="Test",
                filter_expression="vendor ct 'Intel'",
            )

    def test_create_rule(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test creating a rule via scoped manager."""
        test_uuid = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
        # Get resource group first
        mock_session.request.return_value.json.return_value = [
            {
                "$key": 10,
                "uuid": test_uuid,
                "name": "GPU Pool",
            }
        ]
        rg = mock_client.resource_groups.get(key=test_uuid)

        # Create rule
        mock_session.request.return_value.json.side_effect = [
            {"$key": 1, "resource_group": test_uuid},
            {"$key": 1, "resource_group": test_uuid, "name": "Intel Rule"},
        ]

        rule = rg.rules.create(
            name="Intel Rule",
            filter_expression="vendor ct 'Intel'",
            node=5,
        )

        assert rule.key == 1

        # Verify the POST was called with expected data
        call_str = str(mock_session.request.call_args_list)
        assert f"'resource_group': '{test_uuid}'" in call_str
        assert "'name': 'Intel Rule'" in call_str
        assert "'filter': \"vendor ct 'Intel'\"" in call_str
        assert "'node': 5" in call_str

    def test_update_rule(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test updating a rule."""
        mock_session.request.return_value.json.return_value = {
            "$key": 1,
            "name": "Updated Rule",
            "enabled": False,
        }

        rule = mock_client.resource_groups.rules.update(1, name="Updated Rule", enabled=False)

        assert rule.name == "Updated Rule"

        call_str = str(mock_session.request.call_args)
        assert "PUT" in call_str

    def test_delete_rule(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test deleting a rule."""
        mock_session.request.return_value.json.return_value = None

        mock_client.resource_groups.rules.delete(1)

        call_str = str(mock_session.request.call_args)
        assert "DELETE" in call_str
        assert "resource_rules/1" in call_str


class TestResourceRuleModel:
    """Tests for ResourceRule model."""

    def test_rule_properties(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test ResourceRule property accessors."""
        from pyvergeos.resources.resource_groups import ResourceRule, ResourceRuleManager

        data = {
            "$key": 1,
            "resource_group": 10,
            "resource_group_display": "GPU Pool",
            "name": "Intel Rule",
            "enabled": True,
            "type": "node_host_gpu_devices",
            "type_display": "Host GPU",
            "node": 5,
            "node_display": "node1",
            "filter": "vendor ct 'Intel'",
            "filter_configuration": {"vendor": "Intel"},
            "resource_count": 3,
            "system_created": False,
            "modified": 1700000000,
        }
        manager = ResourceRuleManager(mock_client)
        rule = ResourceRule(data, manager)

        assert rule.key == 1
        assert rule.resource_group_key == 10
        assert rule.resource_group_name == "GPU Pool"
        assert rule.name == "Intel Rule"
        assert rule.is_enabled is True
        assert rule.device_type == "node_host_gpu_devices"
        assert rule.device_type_display == "Host GPU"
        assert rule.node_key == 5
        assert rule.node_name == "node1"
        assert rule.filter_expression == "vendor ct 'Intel'"
        assert rule.filter_configuration == {"vendor": "Intel"}
        assert rule.resource_count == 3
        assert rule.is_system_created is False
        assert rule.modified_at is not None

    def test_rule_repr(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test ResourceRule string representation."""
        from pyvergeos.resources.resource_groups import ResourceRule, ResourceRuleManager

        data = {
            "$key": 1,
            "name": "Test Rule",
            "type": "node_pci_devices",
            "type_display": "PCI",
            "resource_count": 5,
        }
        manager = ResourceRuleManager(mock_client)
        rule = ResourceRule(data, manager)

        repr_str = repr(rule)
        assert "ResourceRule" in repr_str
        assert "key=1" in repr_str
        assert "Test Rule" in repr_str
        assert "resources=5" in repr_str
