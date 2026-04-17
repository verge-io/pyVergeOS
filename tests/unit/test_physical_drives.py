"""Unit tests for physical drive (SMART health) operations."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from pyvergeos.resources.physical_drives import (
    PhysicalDrive,
    PhysicalDriveManager,
)


SAMPLE_DRIVE = {
    "$key": 1,
    "model": "SOLIDIGM SSDPFKKW020X7",
    "serial": "SJC7N44291180790B",
    "fw": "001C",
    "path": "/dev/nvme0n1",
    "location": "nvme0",
    "size": 2048408248320,
    "temp": 63,
    "temp_warn": False,
    "realloc_sectors": 0,
    "realloc_sectors_warn": False,
    "wear_level": 1,
    "wear_level_warn": False,
    "current_pending_sector": 0,
    "current_pending_sector_warn": False,
    "offline_uncorrectable": 0,
    "offline_uncorrectable_warn": False,
    "hours": 5892,
    "hours_warn": False,
    "smart": True,
    "vsan_read_errors": 0,
    "vsan_write_errors": 0,
    "vsan_last_error": "",
    "vsan_throttle": 0,
    "vsan_tier": 1,
    "vsan_used": 443225735168,
    "vsan_max": 2042034651136,
    "vsan_online_since": 1774716017,
    "vsan_driveid": 0,
    "vsan_avg_latency": 0,
    "vsan_max_latency": 0,
    "vsan_repairing": 0,
    "vsan_repair_estimate": 0,
    "boot": True,
    "swap": True,
    "spare": False,
    "encrypted": False,
    "parent_drive": 1,
    "modified": 1776387996,
}

SAMPLE_WARN_DRIVE = {
    "$key": 2,
    "model": "WDC WD40EFRX",
    "serial": "WD-WCC4E1234567",
    "fw": "82.00A82",
    "path": "/dev/sda",
    "location": "sata0",
    "size": 4000787030016,
    "temp": 45,
    "temp_warn": True,
    "realloc_sectors": 8,
    "realloc_sectors_warn": True,
    "wear_level": 0,
    "wear_level_warn": False,
    "current_pending_sector": 2,
    "current_pending_sector_warn": True,
    "offline_uncorrectable": 1,
    "offline_uncorrectable_warn": True,
    "hours": 43000,
    "hours_warn": True,
    "smart": True,
    "vsan_read_errors": 5,
    "vsan_write_errors": 3,
    "vsan_last_error": "I/O error on sector 12345",
    "vsan_throttle": 104857600,
    "vsan_tier": 1,
    "vsan_used": 0,
    "vsan_max": 0,
    "vsan_online_since": 0,
    "vsan_driveid": 1,
    "vsan_avg_latency": 15,
    "vsan_max_latency": 200,
    "vsan_repairing": 1,
    "vsan_repair_estimate": 3600,
    "boot": False,
    "swap": False,
    "spare": True,
    "encrypted": True,
    "parent_drive": 2,
    "modified": 1776300000,
}


class TestPhysicalDrive:
    """Tests for PhysicalDrive resource object."""

    def test_key_property(self) -> None:
        data = {"$key": 1}
        drive = PhysicalDrive(data, MagicMock())
        assert drive.key == 1

    def test_model_property(self) -> None:
        drive = PhysicalDrive(SAMPLE_DRIVE, MagicMock())
        assert drive.model == "SOLIDIGM SSDPFKKW020X7"

    def test_serial_property(self) -> None:
        drive = PhysicalDrive(SAMPLE_DRIVE, MagicMock())
        assert drive.serial == "SJC7N44291180790B"

    def test_firmware_property(self) -> None:
        drive = PhysicalDrive(SAMPLE_DRIVE, MagicMock())
        assert drive.firmware == "001C"

    def test_path_property(self) -> None:
        drive = PhysicalDrive(SAMPLE_DRIVE, MagicMock())
        assert drive.path == "/dev/nvme0n1"

    def test_location_property(self) -> None:
        drive = PhysicalDrive(SAMPLE_DRIVE, MagicMock())
        assert drive.location == "nvme0"

    def test_size_bytes_property(self) -> None:
        drive = PhysicalDrive(SAMPLE_DRIVE, MagicMock())
        assert drive.size_bytes == 2048408248320

    def test_temperature(self) -> None:
        drive = PhysicalDrive(SAMPLE_DRIVE, MagicMock())
        assert drive.temperature == 63

    def test_temp_warn_false(self) -> None:
        drive = PhysicalDrive(SAMPLE_DRIVE, MagicMock())
        assert drive.temp_warn is False

    def test_temp_warn_true(self) -> None:
        drive = PhysicalDrive(SAMPLE_WARN_DRIVE, MagicMock())
        assert drive.temp_warn is True

    def test_realloc_sectors(self) -> None:
        drive = PhysicalDrive(SAMPLE_WARN_DRIVE, MagicMock())
        assert drive.realloc_sectors == 8

    def test_realloc_sectors_warn(self) -> None:
        drive = PhysicalDrive(SAMPLE_WARN_DRIVE, MagicMock())
        assert drive.realloc_sectors_warn is True

    def test_wear_level(self) -> None:
        drive = PhysicalDrive(SAMPLE_DRIVE, MagicMock())
        assert drive.wear_level == 1

    def test_wear_level_warn(self) -> None:
        drive = PhysicalDrive(SAMPLE_DRIVE, MagicMock())
        assert drive.wear_level_warn is False

    def test_current_pending_sector(self) -> None:
        drive = PhysicalDrive(SAMPLE_WARN_DRIVE, MagicMock())
        assert drive.current_pending_sector == 2

    def test_current_pending_sector_warn(self) -> None:
        drive = PhysicalDrive(SAMPLE_WARN_DRIVE, MagicMock())
        assert drive.current_pending_sector_warn is True

    def test_offline_uncorrectable(self) -> None:
        drive = PhysicalDrive(SAMPLE_WARN_DRIVE, MagicMock())
        assert drive.offline_uncorrectable == 1

    def test_offline_uncorrectable_warn(self) -> None:
        drive = PhysicalDrive(SAMPLE_WARN_DRIVE, MagicMock())
        assert drive.offline_uncorrectable_warn is True

    def test_hours(self) -> None:
        drive = PhysicalDrive(SAMPLE_DRIVE, MagicMock())
        assert drive.hours == 5892

    def test_hours_warn(self) -> None:
        drive = PhysicalDrive(SAMPLE_WARN_DRIVE, MagicMock())
        assert drive.hours_warn is True

    def test_smart_enabled(self) -> None:
        drive = PhysicalDrive(SAMPLE_DRIVE, MagicMock())
        assert drive.smart_enabled is True

    def test_vsan_read_errors(self) -> None:
        drive = PhysicalDrive(SAMPLE_WARN_DRIVE, MagicMock())
        assert drive.vsan_read_errors == 5

    def test_vsan_write_errors(self) -> None:
        drive = PhysicalDrive(SAMPLE_WARN_DRIVE, MagicMock())
        assert drive.vsan_write_errors == 3

    def test_vsan_last_error(self) -> None:
        drive = PhysicalDrive(SAMPLE_WARN_DRIVE, MagicMock())
        assert drive.vsan_last_error == "I/O error on sector 12345"

    def test_vsan_last_error_empty(self) -> None:
        drive = PhysicalDrive(SAMPLE_DRIVE, MagicMock())
        assert drive.vsan_last_error == ""

    def test_vsan_throttle(self) -> None:
        drive = PhysicalDrive(SAMPLE_WARN_DRIVE, MagicMock())
        assert drive.vsan_throttle == 104857600

    def test_vsan_tier(self) -> None:
        drive = PhysicalDrive(SAMPLE_DRIVE, MagicMock())
        assert drive.vsan_tier == 1

    def test_vsan_repairing(self) -> None:
        drive = PhysicalDrive(SAMPLE_WARN_DRIVE, MagicMock())
        assert drive.vsan_repairing is True

    def test_vsan_repairing_false(self) -> None:
        drive = PhysicalDrive(SAMPLE_DRIVE, MagicMock())
        assert drive.vsan_repairing is False

    def test_vsan_online_since(self) -> None:
        drive = PhysicalDrive(SAMPLE_DRIVE, MagicMock())
        assert drive.vsan_online_since == datetime(
            2026, 3, 28, 16, 40, 17, tzinfo=timezone.utc
        )

    def test_vsan_online_since_zero(self) -> None:
        drive = PhysicalDrive(SAMPLE_WARN_DRIVE, MagicMock())
        assert drive.vsan_online_since is None

    def test_is_boot(self) -> None:
        drive = PhysicalDrive(SAMPLE_DRIVE, MagicMock())
        assert drive.is_boot is True

    def test_is_spare(self) -> None:
        drive = PhysicalDrive(SAMPLE_WARN_DRIVE, MagicMock())
        assert drive.is_spare is True

    def test_is_encrypted(self) -> None:
        drive = PhysicalDrive(SAMPLE_WARN_DRIVE, MagicMock())
        assert drive.is_encrypted is True

    def test_has_warnings_false(self) -> None:
        drive = PhysicalDrive(SAMPLE_DRIVE, MagicMock())
        assert drive.has_warnings is False

    def test_has_warnings_true(self) -> None:
        drive = PhysicalDrive(SAMPLE_WARN_DRIVE, MagicMock())
        assert drive.has_warnings is True

    def test_has_vsan_errors_false(self) -> None:
        drive = PhysicalDrive(SAMPLE_DRIVE, MagicMock())
        assert drive.has_vsan_errors is False

    def test_has_vsan_errors_true(self) -> None:
        drive = PhysicalDrive(SAMPLE_WARN_DRIVE, MagicMock())
        assert drive.has_vsan_errors is True

    def test_repr(self) -> None:
        drive = PhysicalDrive(SAMPLE_DRIVE, MagicMock())
        r = repr(drive)
        assert "PhysicalDrive" in r
        assert "SOLIDIGM" in r
        assert "nvme0" in r


class TestPhysicalDriveManager:
    """Tests for PhysicalDriveManager."""

    def test_list_returns_physical_drives(self) -> None:
        mock_client = MagicMock()
        mock_client._request.return_value = [SAMPLE_DRIVE, SAMPLE_WARN_DRIVE]
        manager = PhysicalDriveManager(mock_client)

        drives = manager.list()

        assert len(drives) == 2
        assert all(isinstance(d, PhysicalDrive) for d in drives)

    def test_list_empty(self) -> None:
        mock_client = MagicMock()
        mock_client._request.return_value = []
        manager = PhysicalDriveManager(mock_client)

        drives = manager.list()
        assert drives == []

    def test_list_none_response(self) -> None:
        mock_client = MagicMock()
        mock_client._request.return_value = None
        manager = PhysicalDriveManager(mock_client)

        drives = manager.list()
        assert drives == []

    def test_get_by_key(self) -> None:
        mock_client = MagicMock()
        mock_client._request.return_value = SAMPLE_DRIVE
        manager = PhysicalDriveManager(mock_client)

        drive = manager.get(key=1)

        assert isinstance(drive, PhysicalDrive)
        assert drive.key == 1

    def test_list_with_node_filter(self) -> None:
        mock_client = MagicMock()
        mock_client._request.return_value = [SAMPLE_DRIVE]
        manager = PhysicalDriveManager(mock_client, node_key=1)

        _ = manager.list()

        call_args = mock_client._request.call_args
        params = call_args[1].get("params") or call_args[0][2]
        assert "node eq 1" in params.get("filter", "")

    def test_endpoint(self) -> None:
        mock_client = MagicMock()
        manager = PhysicalDriveManager(mock_client)
        assert manager._endpoint == "machine_drive_phys"
