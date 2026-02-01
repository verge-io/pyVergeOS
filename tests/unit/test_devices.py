"""Unit tests for VM device operations."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from pyvergeos import VergeClient
from pyvergeos.exceptions import NotFoundError
from pyvergeos.resources.devices import (
    DEVICE_STATUS_DISPLAY,
    DEVICE_TYPE_DISPLAY,
    Device,
    DeviceManager,
)


class TestDeviceManager:
    """Unit tests for DeviceManager."""

    @pytest.fixture
    def device_manager(self, mock_client: VergeClient) -> DeviceManager:
        """Create a DeviceManager scoped to a machine."""
        return DeviceManager(mock_client, machine_key=100)

    def test_list_devices(self, device_manager: DeviceManager, mock_session: MagicMock) -> None:
        """Test listing devices for a machine."""
        mock_session.request.return_value.json.return_value = [
            {
                "$key": 1,
                "name": "vGPU-1",
                "type": "node_nvidia_vgpu_devices",
                "machine": 100,
                "enabled": True,
            },
            {
                "$key": 2,
                "name": "TPM",
                "type": "tpm",
                "machine": 100,
                "enabled": True,
            },
        ]

        devices = device_manager.list()

        assert len(devices) == 2
        assert devices[0].name == "vGPU-1"
        assert devices[1].name == "TPM"

    def test_list_devices_filters_by_machine(
        self, device_manager: DeviceManager, mock_session: MagicMock
    ) -> None:
        """Test that list adds machine filter."""
        mock_session.request.return_value.json.return_value = []

        device_manager.list()

        call_args = mock_session.request.call_args
        params = call_args.kwargs.get("params", {})
        assert "machine eq 100" in params.get("filter", "")

    def test_list_devices_by_type(
        self, device_manager: DeviceManager, mock_session: MagicMock
    ) -> None:
        """Test filtering devices by type."""
        mock_session.request.return_value.json.return_value = []

        device_manager.list(device_type="node_nvidia_vgpu_devices")

        call_args = mock_session.request.call_args
        params = call_args.kwargs.get("params", {})
        assert "type eq 'node_nvidia_vgpu_devices'" in params.get("filter", "")

    def test_list_devices_enabled_only(
        self, device_manager: DeviceManager, mock_session: MagicMock
    ) -> None:
        """Test filtering for enabled devices only."""
        mock_session.request.return_value.json.return_value = []

        device_manager.list(enabled_only=True)

        call_args = mock_session.request.call_args
        params = call_args.kwargs.get("params", {})
        assert "enabled eq true" in params.get("filter", "")

    def test_list_devices_empty(
        self, device_manager: DeviceManager, mock_session: MagicMock
    ) -> None:
        """Test listing when no devices exist."""
        mock_session.request.return_value.json.return_value = None

        devices = device_manager.list()

        assert devices == []

    def test_get_device_by_key(
        self, device_manager: DeviceManager, mock_session: MagicMock
    ) -> None:
        """Test getting a device by key."""
        mock_session.request.return_value.json.return_value = {
            "$key": 1,
            "name": "vGPU-1",
            "type": "node_nvidia_vgpu_devices",
            "machine": 100,
        }

        device = device_manager.get(1)

        assert device.key == 1
        assert device.name == "vGPU-1"

    def test_get_device_by_name(
        self, device_manager: DeviceManager, mock_session: MagicMock
    ) -> None:
        """Test getting a device by name."""
        mock_session.request.return_value.json.return_value = [
            {
                "$key": 2,
                "name": "TPM",
                "type": "tpm",
                "machine": 100,
            }
        ]

        device = device_manager.get(name="TPM")

        assert device.name == "TPM"
        assert device.key == 2

    def test_get_device_not_found(
        self, device_manager: DeviceManager, mock_session: MagicMock
    ) -> None:
        """Test NotFoundError when device not found by key."""
        mock_session.request.return_value.json.return_value = None

        with pytest.raises(NotFoundError):
            device_manager.get(999)

    def test_get_device_not_found_by_name(
        self, device_manager: DeviceManager, mock_session: MagicMock
    ) -> None:
        """Test NotFoundError when device not found by name."""
        mock_session.request.return_value.json.return_value = []

        with pytest.raises(NotFoundError):
            device_manager.get(name="nonexistent")

    def test_get_device_requires_key_or_name(self, device_manager: DeviceManager) -> None:
        """Test ValueError when neither key nor name provided."""
        with pytest.raises(ValueError, match="Either key or name must be provided"):
            device_manager.get()

    def test_create_device(self, device_manager: DeviceManager, mock_session: MagicMock) -> None:
        """Test creating a device."""
        mock_session.request.return_value.json.side_effect = [
            {"$key": 10, "name": "vGPU-1", "type": "node_nvidia_vgpu_devices"},
            {"$key": 10, "name": "vGPU-1", "type": "node_nvidia_vgpu_devices"},
        ]

        device = device_manager.create(
            device_type="node_nvidia_vgpu_devices",
            name="vGPU-1",
            resource_group=5,
        )

        assert device.key == 10
        assert device.name == "vGPU-1"

    def test_create_device_with_settings(
        self, device_manager: DeviceManager, mock_session: MagicMock
    ) -> None:
        """Test creating a device with settings."""
        mock_session.request.return_value.json.side_effect = [
            {"$key": 10, "name": "vGPU", "type": "node_nvidia_vgpu_devices"},
            {"$key": 10, "name": "vGPU", "type": "node_nvidia_vgpu_devices"},
        ]

        device_manager.create(
            device_type="node_nvidia_vgpu_devices",
            resource_group=5,
            settings={"frame_rate_limiter": 60},
        )

        post_calls = [
            call
            for call in mock_session.request.call_args_list
            if call.kwargs.get("method") == "POST"
        ]
        assert len(post_calls) == 1
        body = post_calls[0].kwargs.get("json", {})
        assert body["settings_args"] == {"frame_rate_limiter": 60}

    def test_create_vgpu(self, device_manager: DeviceManager, mock_session: MagicMock) -> None:
        """Test creating a vGPU device."""
        mock_session.request.return_value.json.side_effect = [
            {"$key": 10, "type": "node_nvidia_vgpu_devices"},
            {"$key": 10, "type": "node_nvidia_vgpu_devices"},
        ]

        device_manager.create_vgpu(
            resource_group=5,
            frame_rate_limit=60,
            attach_guest_drivers=True,
        )

        post_calls = [
            call
            for call in mock_session.request.call_args_list
            if call.kwargs.get("method") == "POST"
        ]
        body = post_calls[0].kwargs.get("json", {})
        assert body["type"] == "node_nvidia_vgpu_devices"
        assert body["settings_args"]["frame_rate_limiter"] == 60
        assert body["settings_args"]["attach_drivers"] is True

    def test_create_host_gpu(self, device_manager: DeviceManager, mock_session: MagicMock) -> None:
        """Test creating a host GPU passthrough device."""
        mock_session.request.return_value.json.side_effect = [
            {"$key": 11, "type": "node_host_gpu_devices"},
            {"$key": 11, "type": "node_host_gpu_devices"},
        ]

        device_manager.create_host_gpu(resource_group=6, count=2)

        post_calls = [
            call
            for call in mock_session.request.call_args_list
            if call.kwargs.get("method") == "POST"
        ]
        body = post_calls[0].kwargs.get("json", {})
        assert body["type"] == "node_host_gpu_devices"
        assert body["count"] == 2

    def test_create_usb(self, device_manager: DeviceManager, mock_session: MagicMock) -> None:
        """Test creating a USB passthrough device."""
        mock_session.request.return_value.json.side_effect = [
            {"$key": 12, "type": "node_usb_devices"},
            {"$key": 12, "type": "node_usb_devices"},
        ]

        device_manager.create_usb(
            resource_group=7,
            allow_guest_reset=True,
            allow_guest_reset_all=False,
        )

        post_calls = [
            call
            for call in mock_session.request.call_args_list
            if call.kwargs.get("method") == "POST"
        ]
        body = post_calls[0].kwargs.get("json", {})
        assert body["type"] == "node_usb_devices"
        assert body["settings_args"]["guest_reset"] is True
        assert body["settings_args"]["guest_resets_all"] is False

    def test_create_pci(self, device_manager: DeviceManager, mock_session: MagicMock) -> None:
        """Test creating a PCI passthrough device."""
        mock_session.request.return_value.json.side_effect = [
            {"$key": 13, "type": "node_pci_devices"},
            {"$key": 13, "type": "node_pci_devices"},
        ]

        device_manager.create_pci(resource_group=8, count=1)

        post_calls = [
            call
            for call in mock_session.request.call_args_list
            if call.kwargs.get("method") == "POST"
        ]
        body = post_calls[0].kwargs.get("json", {})
        assert body["type"] == "node_pci_devices"

    def test_create_sriov_nic(self, device_manager: DeviceManager, mock_session: MagicMock) -> None:
        """Test creating an SR-IOV NIC device."""
        mock_session.request.return_value.json.side_effect = [
            {"$key": 14, "type": "node_sriov_nic_devices"},
            {"$key": 14, "type": "node_sriov_nic_devices"},
        ]

        device_manager.create_sriov_nic(
            resource_group=9,
            native_vlan=100,
            max_tx_rate=1000,
        )

        post_calls = [
            call
            for call in mock_session.request.call_args_list
            if call.kwargs.get("method") == "POST"
        ]
        body = post_calls[0].kwargs.get("json", {})
        assert body["type"] == "node_sriov_nic_devices"
        assert body["settings_args"]["vlan"] == 100
        assert body["settings_args"]["max_tx_rate"] == 1000

    def test_create_tpm(self, device_manager: DeviceManager, mock_session: MagicMock) -> None:
        """Test creating a TPM device."""
        mock_session.request.return_value.json.side_effect = [
            {"$key": 15, "type": "tpm"},
            {"$key": 15, "type": "tpm"},
        ]

        device_manager.create_tpm(name="TPM")

        post_calls = [
            call
            for call in mock_session.request.call_args_list
            if call.kwargs.get("method") == "POST"
        ]
        body = post_calls[0].kwargs.get("json", {})
        assert body["type"] == "tpm"
        assert body["name"] == "TPM"

    def test_update_device(self, device_manager: DeviceManager, mock_session: MagicMock) -> None:
        """Test updating a device."""
        mock_session.request.return_value.json.return_value = {
            "$key": 1,
            "name": "vGPU-1",
            "enabled": False,
        }

        device = device_manager.update(1, enabled=False)

        put_calls = [
            call
            for call in mock_session.request.call_args_list
            if call.kwargs.get("method") == "PUT"
        ]
        assert len(put_calls) == 1
        assert device.get("enabled") is False

    def test_delete_device(self, device_manager: DeviceManager, mock_session: MagicMock) -> None:
        """Test deleting a device."""
        mock_session.request.return_value.status_code = 204
        mock_session.request.return_value.text = ""

        device_manager.delete(1)

        call_args = mock_session.request.call_args
        assert call_args.kwargs["method"] == "DELETE"
        assert "machine_devices/1" in call_args.kwargs["url"]


class TestDevice:
    """Unit tests for Device object."""

    @pytest.fixture
    def device_data(self) -> dict[str, Any]:
        """Sample device data."""
        return {
            "$key": 1,
            "name": "vGPU-1",
            "description": "Test vGPU",
            "type": "node_nvidia_vgpu_devices",
            "machine": 100,
            "machine_name": "test-vm",
            "enabled": True,
            "optional": False,
            "resource_group": 5,
            "resource_group_name": "vGPU Pool",
            "device_status": "online",
            "status_info": "Active",
            "uuid": "abc-123",
            "orderid": 1,
            "created": 1704067200,
            "modified": 1704153600,
        }

    @pytest.fixture
    def mock_manager(self, mock_client: VergeClient) -> DeviceManager:
        """Create a mock device manager."""
        return DeviceManager(mock_client, machine_key=100)

    def test_device_properties(
        self, device_data: dict[str, Any], mock_manager: DeviceManager
    ) -> None:
        """Test Device property accessors."""
        device = Device(device_data, mock_manager)

        assert device.key == 1
        assert device.name == "vGPU-1"
        assert device.description == "Test vGPU"
        assert device.device_type_raw == "node_nvidia_vgpu_devices"
        assert device.device_type == "NVIDIA vGPU"
        assert device.machine_key == 100
        assert device.machine_name == "test-vm"
        assert device.is_enabled is True
        assert device.is_optional is False
        assert device.resource_group_key == 5
        assert device.resource_group_name == "vGPU Pool"
        assert device.status_raw == "online"
        assert device.status == "Online"
        assert device.status_info == "Active"
        assert device.uuid == "abc-123"
        assert device.orderid == 1

    def test_device_timestamps(
        self, device_data: dict[str, Any], mock_manager: DeviceManager
    ) -> None:
        """Test Device timestamp properties."""
        device = Device(device_data, mock_manager)

        assert device.created_at is not None
        assert device.modified_at is not None
        assert device.created_at.year == 2024

    def test_device_timestamps_none(self, mock_manager: DeviceManager) -> None:
        """Test Device timestamp properties when not set."""
        device = Device({"$key": 1}, mock_manager)

        assert device.created_at is None
        assert device.modified_at is None

    def test_device_type_helpers(
        self, device_data: dict[str, Any], mock_manager: DeviceManager
    ) -> None:
        """Test Device type helper properties."""
        device = Device(device_data, mock_manager)

        assert device.is_vgpu is True
        assert device.is_gpu is True
        assert device.is_host_gpu is False
        assert device.is_tpm is False
        assert device.is_usb is False
        assert device.is_pci is False
        assert device.is_sriov is False

    def test_device_is_host_gpu(self, mock_manager: DeviceManager) -> None:
        """Test is_host_gpu property."""
        device = Device({"$key": 1, "type": "node_host_gpu_devices"}, mock_manager)

        assert device.is_host_gpu is True
        assert device.is_gpu is True
        assert device.is_vgpu is False

    def test_device_is_tpm(self, mock_manager: DeviceManager) -> None:
        """Test is_tpm property."""
        device = Device({"$key": 1, "type": "tpm"}, mock_manager)

        assert device.is_tpm is True
        assert device.is_gpu is False

    def test_device_is_usb(self, mock_manager: DeviceManager) -> None:
        """Test is_usb property."""
        device = Device({"$key": 1, "type": "node_usb_devices"}, mock_manager)

        assert device.is_usb is True

    def test_device_is_pci(self, mock_manager: DeviceManager) -> None:
        """Test is_pci property."""
        device = Device({"$key": 1, "type": "node_pci_devices"}, mock_manager)

        assert device.is_pci is True

    def test_device_is_sriov(self, mock_manager: DeviceManager) -> None:
        """Test is_sriov property."""
        device = Device({"$key": 1, "type": "node_sriov_nic_devices"}, mock_manager)

        assert device.is_sriov is True

    def test_device_repr(self, device_data: dict[str, Any], mock_manager: DeviceManager) -> None:
        """Test Device string representation."""
        device = Device(device_data, mock_manager)

        repr_str = repr(device)
        assert "Device" in repr_str
        assert "key=1" in repr_str
        assert "vGPU-1" in repr_str

    def test_device_refresh(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test Device refresh method."""
        mock_session.request.return_value.json.return_value = {
            "$key": 1,
            "name": "vGPU-1-updated",
            "type": "node_nvidia_vgpu_devices",
        }

        manager = DeviceManager(mock_client, machine_key=100)
        device = Device({"$key": 1, "name": "vGPU-1"}, manager)

        refreshed = device.refresh()

        assert refreshed.name == "vGPU-1-updated"

    def test_device_save(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test Device save method."""
        mock_session.request.return_value.json.return_value = {
            "$key": 1,
            "name": "vGPU-1",
            "description": "Updated description",
        }

        manager = DeviceManager(mock_client, machine_key=100)
        device = Device({"$key": 1, "name": "vGPU-1"}, manager)

        updated = device.save(description="Updated description")

        assert updated.get("description") == "Updated description"

    def test_device_delete(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test Device delete method."""
        mock_session.request.return_value.status_code = 204
        mock_session.request.return_value.text = ""

        manager = DeviceManager(mock_client, machine_key=100)
        device = Device({"$key": 1, "name": "vGPU-1"}, manager)

        device.delete()

        delete_calls = [
            call
            for call in mock_session.request.call_args_list
            if call.kwargs.get("method") == "DELETE"
        ]
        assert len(delete_calls) == 1


class TestDeviceTypeMappings:
    """Test device type and status display mappings."""

    def test_device_type_display_mappings(self) -> None:
        """Test all device type display mappings exist."""
        expected_types = [
            "gpu",
            "nvidia_vgpu",
            "tpm",
            "node_usb_devices",
            "node_sriov_nic_devices",
            "node_pci_devices",
            "node_host_gpu_devices",
            "node_nvidia_vgpu_devices",
        ]
        for device_type in expected_types:
            assert device_type in DEVICE_TYPE_DISPLAY

    def test_device_status_display_mappings(self) -> None:
        """Test all device status display mappings exist."""
        expected_statuses = [
            "online",
            "offline",
            "errors",
            "warning",
            "hotplug",
            "initializing",
            "missing",
            "idle",
        ]
        for status in expected_statuses:
            assert status in DEVICE_STATUS_DISPLAY
