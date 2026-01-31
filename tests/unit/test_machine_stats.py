"""Unit tests for machine stats and monitoring managers."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock

import pytest

from pyvergeos.exceptions import NotFoundError
from pyvergeos.resources.devices import Device, DeviceManager
from pyvergeos.resources.machine_stats import (
    MachineLog,
    MachineLogManager,
    MachineStats,
    MachineStatsHistory,
    MachineStatsManager,
    MachineStatus,
    MachineStatusManager,
)


@pytest.fixture
def mock_client() -> MagicMock:
    """Create a mock VergeClient."""
    client = MagicMock()
    client._request = MagicMock()
    return client


# =============================================================================
# Sample Data Fixtures
# =============================================================================


@pytest.fixture
def sample_stats_data() -> dict[str, Any]:
    """Sample machine stats data from API."""
    return {
        "$key": 1,
        "machine": 100,
        "total_cpu": 45,
        "user_cpu": 30,
        "system_cpu": 10,
        "iowait_cpu": 5,
        "vmusage_cpu": 0,
        "irq_cpu": 0,
        "ram_used": 4096,
        "ram_pct": 50,
        "vram_used": 2048,
        "core_usagelist": [45, 50, 40, 55],
        "core_temp": 65,
        "core_temp_top": 72,
        "core_peak": 80,
        "core_count_gt_25": 4,
        "core_count_gt_50": 2,
        "core_count_gt_75": 1,
        "modified": 1704067200,
    }


@pytest.fixture
def sample_stats_history_data() -> dict[str, Any]:
    """Sample machine stats history data from API."""
    return {
        "$key": 1,
        "machine": 100,
        "timestamp": 1704067200,
        "total_cpu": 45,
        "user_cpu": 30,
        "system_cpu": 10,
        "iowait_cpu": 5,
        "vmusage_cpu": 0,
        "irq_cpu": 0,
        "ram_used": 4096,
        "vram_used": 2048,
        "core_temp": 65,
        "core_temp_top": 72,
        "core_peak": 80,
    }


@pytest.fixture
def sample_status_data() -> dict[str, Any]:
    """Sample machine status data from API."""
    return {
        "$key": 1,
        "machine": 100,
        "running": True,
        "migratable": True,
        "status": "running",
        "status_info": "",
        "state": "online",
        "powerstate": True,
        "node": 1,
        "node_name": "node1",
        "migrated_node": None,
        "migration_destination": None,
        "started": 1704067200,
        "local_time": 1704153600,
        "last_update": 1704153600,
        "running_cores": 4,
        "running_ram": 4096,
        "agent_version": "4.0.0",
        "agent_features": {"file-open": True, "file-close": True},
        "agent_guest_info": {"os": "Linux", "hostname": "test-vm"},
    }


@pytest.fixture
def sample_log_data() -> dict[str, Any]:
    """Sample machine log data from API."""
    return {
        "$key": 1,
        "machine": 100,
        "machine_name": "test-vm",
        "level": "message",
        "text": "VM started successfully",
        "user": "admin",
        "timestamp": 1704067200000000,  # microseconds
    }


@pytest.fixture
def sample_log_list() -> list[dict[str, Any]]:
    """Sample list of machine logs."""
    return [
        {
            "$key": 1,
            "machine": 100,
            "machine_name": "test-vm",
            "level": "message",
            "text": "VM started successfully",
            "user": "admin",
            "timestamp": 1704067200000000,
        },
        {
            "$key": 2,
            "machine": 100,
            "machine_name": "test-vm",
            "level": "error",
            "text": "Disk write error",
            "user": "system",
            "timestamp": 1704067201000000,
        },
        {
            "$key": 3,
            "machine": 100,
            "machine_name": "test-vm",
            "level": "warning",
            "text": "High memory usage",
            "user": "system",
            "timestamp": 1704067202000000,
        },
    ]


@pytest.fixture
def sample_device_data() -> dict[str, Any]:
    """Sample machine device data from API."""
    return {
        "$key": 1,
        "machine": 100,
        "machine_name": "test-vm",
        "machine_type": "vm",
        "name": "gpu_0",
        "description": "NVIDIA GPU",
        "type": "node_nvidia_vgpu_devices",
        "orderid": 0,
        "uuid": "abc-123-def",
        "enabled": True,
        "optional": False,
        "resource_group": 5,
        "resource_group_name": "GPU Pool",
        "device_status": "online",
        "status_info": "",
        "created": 1704067200,
        "modified": 1704067200,
    }


@pytest.fixture
def sample_device_list() -> list[dict[str, Any]]:
    """Sample list of machine devices."""
    return [
        {
            "$key": 1,
            "machine": 100,
            "machine_name": "test-vm",
            "machine_type": "vm",
            "name": "gpu_0",
            "type": "node_nvidia_vgpu_devices",
            "orderid": 0,
            "enabled": True,
            "device_status": "online",
        },
        {
            "$key": 2,
            "machine": 100,
            "machine_name": "test-vm",
            "machine_type": "vm",
            "name": "tpm_0",
            "type": "tpm",
            "orderid": 1,
            "enabled": True,
            "device_status": "online",
        },
    ]


# =============================================================================
# MachineStats Model Tests
# =============================================================================


class TestMachineStats:
    """Tests for MachineStats model."""

    def test_stats_properties(self, sample_stats_data: dict[str, Any]) -> None:
        """Test stats properties."""
        manager = MagicMock()
        stats = MachineStats(sample_stats_data, manager)

        assert stats.machine_key == 100
        assert stats.total_cpu == 45
        assert stats.user_cpu == 30
        assert stats.system_cpu == 10
        assert stats.iowait_cpu == 5
        assert stats.vmusage_cpu == 0
        assert stats.irq_cpu == 0
        assert stats.ram_used_mb == 4096
        assert stats.ram_pct == 50
        assert stats.vram_used_mb == 2048
        assert stats.core_temp == 65
        assert stats.core_temp_top == 72
        assert stats.core_peak == 80
        assert stats.cores_gt_25_pct == 4
        assert stats.cores_gt_50_pct == 2
        assert stats.cores_gt_75_pct == 1

    def test_stats_core_usagelist(self, sample_stats_data: dict[str, Any]) -> None:
        """Test core usage list."""
        manager = MagicMock()
        stats = MachineStats(sample_stats_data, manager)

        assert stats.core_usagelist == [45, 50, 40, 55]

    def test_stats_core_usagelist_empty(self) -> None:
        """Test empty core usage list."""
        manager = MagicMock()
        stats = MachineStats({"$key": 1, "machine": 100}, manager)

        assert stats.core_usagelist == []

    def test_stats_modified_at(self, sample_stats_data: dict[str, Any]) -> None:
        """Test modified timestamp."""
        manager = MagicMock()
        stats = MachineStats(sample_stats_data, manager)

        assert stats.modified_at is not None
        assert stats.modified_at.year == 2024
        assert stats.modified_at.tzinfo == timezone.utc

    def test_stats_modified_at_none(self) -> None:
        """Test modified timestamp when not set."""
        manager = MagicMock()
        stats = MachineStats({"$key": 1, "machine": 100}, manager)

        assert stats.modified_at is None

    def test_stats_repr(self, sample_stats_data: dict[str, Any]) -> None:
        """Test stats repr."""
        manager = MagicMock()
        stats = MachineStats(sample_stats_data, manager)

        assert "MachineStats" in repr(stats)
        assert "machine=100" in repr(stats)
        assert "cpu=45%" in repr(stats)
        assert "ram=4096MB" in repr(stats)


# =============================================================================
# MachineStatsHistory Model Tests
# =============================================================================


class TestMachineStatsHistory:
    """Tests for MachineStatsHistory model."""

    def test_history_properties(self, sample_stats_history_data: dict[str, Any]) -> None:
        """Test history properties."""
        manager = MagicMock()
        history = MachineStatsHistory(sample_stats_history_data, manager)

        assert history.machine_key == 100
        assert history.timestamp_epoch == 1704067200
        assert history.total_cpu == 45
        assert history.ram_used_mb == 4096

    def test_history_timestamp(self, sample_stats_history_data: dict[str, Any]) -> None:
        """Test timestamp property."""
        manager = MagicMock()
        history = MachineStatsHistory(sample_stats_history_data, manager)

        assert history.timestamp is not None
        assert history.timestamp.year == 2024
        assert history.timestamp.tzinfo == timezone.utc

    def test_history_repr(self, sample_stats_history_data: dict[str, Any]) -> None:
        """Test history repr."""
        manager = MagicMock()
        history = MachineStatsHistory(sample_stats_history_data, manager)

        assert "MachineStatsHistory" in repr(history)
        assert "cpu=45%" in repr(history)


# =============================================================================
# MachineStatsManager Tests
# =============================================================================


class TestMachineStatsManager:
    """Tests for MachineStatsManager."""

    def test_get_stats(
        self,
        mock_client: MagicMock,
        sample_stats_data: dict[str, Any],
    ) -> None:
        """Test getting current stats."""
        mock_client._request.return_value = [sample_stats_data]
        manager = MachineStatsManager(mock_client, machine_key=100)

        stats = manager.get()

        assert stats.total_cpu == 45
        mock_client._request.assert_called_once()
        call_args = mock_client._request.call_args
        assert call_args[0][0] == "GET"
        assert call_args[0][1] == "machine_stats"
        assert "machine eq 100" in call_args[1]["params"]["filter"]

    def test_get_stats_not_found(self, mock_client: MagicMock) -> None:
        """Test getting stats when not found."""
        mock_client._request.return_value = []
        manager = MachineStatsManager(mock_client, machine_key=100)

        with pytest.raises(NotFoundError):
            manager.get()

    def test_history_short(
        self,
        mock_client: MagicMock,
        sample_stats_history_data: dict[str, Any],
    ) -> None:
        """Test getting short history."""
        mock_client._request.return_value = [sample_stats_history_data]
        manager = MachineStatsManager(mock_client, machine_key=100)

        history = manager.history_short(limit=100)

        assert len(history) == 1
        assert history[0].total_cpu == 45
        mock_client._request.assert_called_once()
        call_args = mock_client._request.call_args
        assert "machine_stats_history_short" in call_args[0][1]

    def test_history_long(
        self,
        mock_client: MagicMock,
        sample_stats_history_data: dict[str, Any],
    ) -> None:
        """Test getting long history."""
        mock_client._request.return_value = [sample_stats_history_data]
        manager = MachineStatsManager(mock_client, machine_key=100)

        history = manager.history_long(limit=100)

        assert len(history) == 1
        mock_client._request.assert_called_once()
        call_args = mock_client._request.call_args
        assert "machine_stats_history_long" in call_args[0][1]

    def test_history_with_datetime_filter(
        self,
        mock_client: MagicMock,
        sample_stats_history_data: dict[str, Any],
    ) -> None:
        """Test history with datetime filter."""
        mock_client._request.return_value = [sample_stats_history_data]
        manager = MachineStatsManager(mock_client, machine_key=100)

        since = datetime(2024, 1, 1, tzinfo=timezone.utc)
        history = manager.history_short(since=since)

        assert len(history) == 1
        call_args = mock_client._request.call_args
        assert "timestamp ge" in call_args[1]["params"]["filter"]

    def test_history_with_epoch_filter(
        self,
        mock_client: MagicMock,
        sample_stats_history_data: dict[str, Any],
    ) -> None:
        """Test history with epoch timestamp filter."""
        mock_client._request.return_value = [sample_stats_history_data]
        manager = MachineStatsManager(mock_client, machine_key=100)

        history = manager.history_short(since=1704067200, until=1704153600)

        assert len(history) == 1
        call_args = mock_client._request.call_args
        assert "timestamp ge 1704067200" in call_args[1]["params"]["filter"]
        assert "timestamp le 1704153600" in call_args[1]["params"]["filter"]


# =============================================================================
# MachineStatus Model Tests
# =============================================================================


class TestMachineStatus:
    """Tests for MachineStatus model."""

    def test_status_properties(self, sample_status_data: dict[str, Any]) -> None:
        """Test status properties."""
        manager = MagicMock()
        status = MachineStatus(sample_status_data, manager)

        assert status.machine_key == 100
        assert status.is_running is True
        assert status.is_migratable is True
        assert status.status == "Running"
        assert status.status_raw == "running"
        assert status.state == "Online"
        assert status.state_raw == "online"
        assert status.powerstate is True
        assert status.node_key == 1
        assert status.node_name == "node1"
        assert status.running_cores == 4
        assert status.running_ram_mb == 4096

    def test_status_agent_info(self, sample_status_data: dict[str, Any]) -> None:
        """Test agent information."""
        manager = MagicMock()
        status = MachineStatus(sample_status_data, manager)

        assert status.agent_version == "4.0.0"
        assert status.has_agent is True
        assert status.agent_features.get("file-open") is True
        assert status.agent_guest_info.get("os") == "Linux"

    def test_status_no_agent(self) -> None:
        """Test when no agent is installed."""
        manager = MagicMock()
        status = MachineStatus({"$key": 1, "machine": 100}, manager)

        assert status.agent_version == ""
        assert status.has_agent is False
        assert status.agent_features == {}
        assert status.agent_guest_info == {}

    def test_status_timestamps(self, sample_status_data: dict[str, Any]) -> None:
        """Test status timestamps."""
        manager = MagicMock()
        status = MachineStatus(sample_status_data, manager)

        assert status.started_at is not None
        assert status.started_at.tzinfo == timezone.utc
        assert status.last_update is not None

    def test_status_repr(self, sample_status_data: dict[str, Any]) -> None:
        """Test status repr."""
        manager = MagicMock()
        status = MachineStatus(sample_status_data, manager)

        assert "MachineStatus" in repr(status)
        assert "status=running" in repr(status)


# =============================================================================
# MachineStatusManager Tests
# =============================================================================


class TestMachineStatusManager:
    """Tests for MachineStatusManager."""

    def test_get_status(
        self,
        mock_client: MagicMock,
        sample_status_data: dict[str, Any],
    ) -> None:
        """Test getting status."""
        mock_client._request.return_value = [sample_status_data]
        manager = MachineStatusManager(mock_client, machine_key=100)

        status = manager.get()

        assert status.is_running is True
        mock_client._request.assert_called_once()
        call_args = mock_client._request.call_args
        assert "machine eq 100" in call_args[1]["params"]["filter"]

    def test_get_status_not_found(self, mock_client: MagicMock) -> None:
        """Test getting status when not found."""
        mock_client._request.return_value = []
        manager = MachineStatusManager(mock_client, machine_key=100)

        with pytest.raises(NotFoundError):
            manager.get()


# =============================================================================
# MachineLog Model Tests
# =============================================================================


class TestMachineLog:
    """Tests for MachineLog model."""

    def test_log_properties(self, sample_log_data: dict[str, Any]) -> None:
        """Test log properties."""
        manager = MagicMock()
        log = MachineLog(sample_log_data, manager)

        assert log.machine_key == 100
        assert log.machine_name == "test-vm"
        assert log.level == "Message"
        assert log.level_raw == "message"
        assert log.text == "VM started successfully"
        assert log.user == "admin"

    def test_log_timestamp(self, sample_log_data: dict[str, Any]) -> None:
        """Test log timestamp (microsecond precision)."""
        manager = MagicMock()
        log = MachineLog(sample_log_data, manager)

        assert log.timestamp is not None
        assert log.timestamp_epoch_us == 1704067200000000

    def test_log_level_checks(self, sample_log_list: list[dict[str, Any]]) -> None:
        """Test log level helper properties."""
        manager = MagicMock()

        message_log = MachineLog(sample_log_list[0], manager)
        error_log = MachineLog(sample_log_list[1], manager)
        warning_log = MachineLog(sample_log_list[2], manager)

        assert message_log.is_error is False
        assert message_log.is_warning is False
        assert message_log.is_audit is False

        assert error_log.is_error is True
        assert error_log.is_warning is False

        assert warning_log.is_warning is True
        assert warning_log.is_error is False

    def test_log_repr(self, sample_log_data: dict[str, Any]) -> None:
        """Test log repr."""
        manager = MagicMock()
        log = MachineLog(sample_log_data, manager)

        assert "MachineLog" in repr(log)
        assert "Message" in repr(log)


# =============================================================================
# MachineLogManager Tests
# =============================================================================


class TestMachineLogManager:
    """Tests for MachineLogManager."""

    def test_list_logs(
        self,
        mock_client: MagicMock,
        sample_log_list: list[dict[str, Any]],
    ) -> None:
        """Test listing logs."""
        mock_client._request.return_value = sample_log_list
        manager = MachineLogManager(mock_client, machine_key=100)

        logs = manager.list()

        assert len(logs) == 3
        mock_client._request.assert_called_once()

    def test_list_logs_by_level(
        self,
        mock_client: MagicMock,
        sample_log_list: list[dict[str, Any]],
    ) -> None:
        """Test listing logs filtered by level."""
        mock_client._request.return_value = [sample_log_list[1]]
        manager = MachineLogManager(mock_client, machine_key=100)

        logs = manager.list(level="error")

        assert len(logs) == 1
        call_args = mock_client._request.call_args
        assert "level eq 'error'" in call_args[1]["params"]["filter"]

    def test_list_errors_only(
        self,
        mock_client: MagicMock,
        sample_log_list: list[dict[str, Any]],
    ) -> None:
        """Test listing errors only."""
        mock_client._request.return_value = [sample_log_list[1]]
        manager = MachineLogManager(mock_client, machine_key=100)

        logs = manager.list(errors_only=True)

        assert len(logs) == 1
        call_args = mock_client._request.call_args
        assert "level eq 'error' or level eq 'critical'" in call_args[1]["params"]["filter"]

    def test_list_warnings_only(
        self,
        mock_client: MagicMock,
        sample_log_list: list[dict[str, Any]],
    ) -> None:
        """Test listing warnings only."""
        mock_client._request.return_value = [sample_log_list[2]]
        manager = MachineLogManager(mock_client, machine_key=100)

        logs = manager.list(warnings_only=True)

        assert len(logs) == 1
        call_args = mock_client._request.call_args
        assert "level eq 'warning'" in call_args[1]["params"]["filter"]

    def test_list_logs_with_time_filter(
        self,
        mock_client: MagicMock,
        sample_log_list: list[dict[str, Any]],
    ) -> None:
        """Test listing logs with time filter."""
        mock_client._request.return_value = sample_log_list
        manager = MachineLogManager(mock_client, machine_key=100)

        since = datetime(2024, 1, 1, tzinfo=timezone.utc)
        logs = manager.list(since=since)

        assert len(logs) == 3
        call_args = mock_client._request.call_args
        assert "timestamp ge" in call_args[1]["params"]["filter"]

    def test_get_log(
        self,
        mock_client: MagicMock,
        sample_log_data: dict[str, Any],
    ) -> None:
        """Test getting a specific log."""
        mock_client._request.return_value = sample_log_data
        manager = MachineLogManager(mock_client, machine_key=100)

        log = manager.get(key=1)

        assert log.text == "VM started successfully"

    def test_get_log_not_found(self, mock_client: MagicMock) -> None:
        """Test getting a log that doesn't exist."""
        mock_client._request.return_value = None
        manager = MachineLogManager(mock_client, machine_key=100)

        with pytest.raises(NotFoundError):
            manager.get(key=999)

    def test_get_log_key_required(self, mock_client: MagicMock) -> None:
        """Test that key is required for get."""
        manager = MachineLogManager(mock_client, machine_key=100)

        with pytest.raises(ValueError, match="key must be provided"):
            manager.get()


# =============================================================================
# Device Model Tests
# =============================================================================


class TestDevice:
    """Tests for Device model."""

    def test_device_properties(self, sample_device_data: dict[str, Any]) -> None:
        """Test device properties."""
        manager = MagicMock()
        device = Device(sample_device_data, manager)

        assert device.machine_key == 100
        assert device.machine_name == "test-vm"
        assert device.machine_type == "vm"
        assert device.name == "gpu_0"
        assert device.description == "NVIDIA GPU"
        assert device.device_type == "NVIDIA vGPU"
        assert device.device_type_raw == "node_nvidia_vgpu_devices"
        assert device.orderid == 0
        assert device.uuid == "abc-123-def"
        assert device.is_enabled is True
        assert device.is_optional is False
        assert device.resource_group_key == 5
        assert device.resource_group_name == "GPU Pool"

    def test_device_status(self, sample_device_data: dict[str, Any]) -> None:
        """Test device status."""
        manager = MagicMock()
        device = Device(sample_device_data, manager)

        assert device.status == "Online"
        assert device.status_raw == "online"

    def test_device_type_checks(self, sample_device_list: list[dict[str, Any]]) -> None:
        """Test device type helper properties."""
        manager = MagicMock()

        gpu_device = Device(sample_device_list[0], manager)
        tpm_device = Device(sample_device_list[1], manager)

        assert gpu_device.is_gpu is True
        assert gpu_device.is_tpm is False
        assert gpu_device.is_usb is False

        assert tpm_device.is_tpm is True
        assert tpm_device.is_gpu is False

    def test_device_repr(self, sample_device_data: dict[str, Any]) -> None:
        """Test device repr."""
        manager = MagicMock()
        device = Device(sample_device_data, manager)

        assert "Device" in repr(device)
        assert "gpu_0" in repr(device)


# =============================================================================
# DeviceManager Tests
# =============================================================================


class TestDeviceManager:
    """Tests for DeviceManager."""

    def test_list_devices(
        self,
        mock_client: MagicMock,
        sample_device_list: list[dict[str, Any]],
    ) -> None:
        """Test listing devices."""
        mock_client._request.return_value = sample_device_list
        manager = DeviceManager(mock_client, machine_key=100)

        devices = manager.list()

        assert len(devices) == 2
        mock_client._request.assert_called_once()
        call_args = mock_client._request.call_args
        assert "machine eq 100" in call_args[1]["params"]["filter"]

    def test_list_devices_by_type(
        self,
        mock_client: MagicMock,
        sample_device_list: list[dict[str, Any]],
    ) -> None:
        """Test listing devices by type."""
        mock_client._request.return_value = [sample_device_list[0]]
        manager = DeviceManager(mock_client, machine_key=100)

        devices = manager.list(device_type="node_nvidia_vgpu_devices")

        assert len(devices) == 1
        call_args = mock_client._request.call_args
        assert "type eq 'node_nvidia_vgpu_devices'" in call_args[1]["params"]["filter"]

    def test_list_enabled_only(
        self,
        mock_client: MagicMock,
        sample_device_list: list[dict[str, Any]],
    ) -> None:
        """Test listing only enabled devices."""
        mock_client._request.return_value = sample_device_list
        manager = DeviceManager(mock_client, machine_key=100)

        manager.list(enabled_only=True)

        call_args = mock_client._request.call_args
        assert "enabled eq true" in call_args[1]["params"]["filter"]

    def test_get_device_by_key(
        self,
        mock_client: MagicMock,
        sample_device_data: dict[str, Any],
    ) -> None:
        """Test getting a device by key."""
        mock_client._request.return_value = sample_device_data
        manager = DeviceManager(mock_client, machine_key=100)

        device = manager.get(key=1)

        assert device.name == "gpu_0"

    def test_get_device_by_name(
        self,
        mock_client: MagicMock,
        sample_device_data: dict[str, Any],
    ) -> None:
        """Test getting a device by name."""
        mock_client._request.return_value = [sample_device_data]
        manager = DeviceManager(mock_client, machine_key=100)

        device = manager.get(name="gpu_0")

        assert device.key == 1

    def test_get_device_not_found(self, mock_client: MagicMock) -> None:
        """Test getting a device that doesn't exist."""
        mock_client._request.return_value = None
        manager = DeviceManager(mock_client, machine_key=100)

        with pytest.raises(NotFoundError):
            manager.get(key=999)

    def test_get_device_key_or_name_required(self, mock_client: MagicMock) -> None:
        """Test that key or name is required for get."""
        manager = DeviceManager(mock_client, machine_key=100)

        with pytest.raises(ValueError, match="Either key or name must be provided"):
            manager.get()

    def test_create_device(
        self,
        mock_client: MagicMock,
        sample_device_data: dict[str, Any],
    ) -> None:
        """Test creating a device."""
        # First call returns created device, second call returns full device
        mock_client._request.side_effect = [
            sample_device_data,  # POST response
            sample_device_data,  # GET for full device
        ]
        manager = DeviceManager(mock_client, machine_key=100)

        device = manager.create(
            device_type="node_nvidia_vgpu_devices",
            name="gpu_0",
            description="NVIDIA GPU",
            resource_group=5,
        )

        assert device.name == "gpu_0"
        # Check that POST was called with correct body
        post_call = mock_client._request.call_args_list[0]
        assert post_call[0][0] == "POST"
        assert post_call[1]["json_data"]["machine"] == 100
        assert post_call[1]["json_data"]["type"] == "node_nvidia_vgpu_devices"

    def test_update_device(
        self,
        mock_client: MagicMock,
        sample_device_data: dict[str, Any],
    ) -> None:
        """Test updating a device."""
        mock_client._request.return_value = sample_device_data
        manager = DeviceManager(mock_client, machine_key=100)

        device = manager.update(key=1, enabled=False)

        assert device.name == "gpu_0"
        mock_client._request.assert_called()
        call_args = mock_client._request.call_args
        assert call_args[0][0] == "PUT"
        assert call_args[1]["json_data"]["enabled"] is False

    def test_delete_device(self, mock_client: MagicMock) -> None:
        """Test deleting a device."""
        mock_client._request.return_value = None
        manager = DeviceManager(mock_client, machine_key=100)

        manager.delete(key=1)

        mock_client._request.assert_called_once()
        call_args = mock_client._request.call_args
        assert call_args[0][0] == "DELETE"
        assert "machine_devices/1" in call_args[0][1]


# =============================================================================
# Integration Tests with VM/Node
# =============================================================================


class TestVMIntegration:
    """Tests for VM integration with machine stats."""

    def test_vm_has_stats_property(self, mock_client: MagicMock) -> None:
        """Test that VM has stats property."""
        from pyvergeos.resources.vms import VM

        vm_data = {
            "$key": 1,
            "name": "test-vm",
            "machine": 100,
        }
        manager = MagicMock()
        manager._client = mock_client
        vm = VM(vm_data, manager)

        stats_manager = vm.stats
        assert isinstance(stats_manager, MachineStatsManager)
        assert stats_manager._machine_key == 100

    def test_vm_has_machine_status_property(self, mock_client: MagicMock) -> None:
        """Test that VM has machine_status property."""
        from pyvergeos.resources.vms import VM

        vm_data = {
            "$key": 1,
            "name": "test-vm",
            "machine": 100,
        }
        manager = MagicMock()
        manager._client = mock_client
        vm = VM(vm_data, manager)

        status_manager = vm.machine_status
        assert isinstance(status_manager, MachineStatusManager)

    def test_vm_has_machine_logs_property(self, mock_client: MagicMock) -> None:
        """Test that VM has machine_logs property."""
        from pyvergeos.resources.vms import VM

        vm_data = {
            "$key": 1,
            "name": "test-vm",
            "machine": 100,
        }
        manager = MagicMock()
        manager._client = mock_client
        vm = VM(vm_data, manager)

        logs_manager = vm.machine_logs
        assert isinstance(logs_manager, MachineLogManager)

    def test_vm_has_devices_property(self, mock_client: MagicMock) -> None:
        """Test that VM has devices property."""
        from pyvergeos.resources.vms import VM

        vm_data = {
            "$key": 1,
            "name": "test-vm",
            "machine": 100,
        }
        manager = MagicMock()
        manager._client = mock_client
        vm = VM(vm_data, manager)

        devices_manager = vm.devices
        assert isinstance(devices_manager, DeviceManager)

    def test_vm_machine_key_error(self, mock_client: MagicMock) -> None:
        """Test error when VM has no machine key."""
        from pyvergeos.resources.vms import VM

        vm_data = {
            "$key": 1,
            "name": "test-vm",
            # No machine key
        }
        manager = MagicMock()
        manager._client = mock_client
        vm = VM(vm_data, manager)

        with pytest.raises(ValueError, match="no machine key"):
            _ = vm.stats
