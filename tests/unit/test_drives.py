"""Unit tests for VM Drive operations."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from pyvergeos import VergeClient
from pyvergeos.exceptions import NotFoundError
from pyvergeos.resources.drives import (
    INTERFACE_DISPLAY_MAP,
    MEDIA_DISPLAY_MAP,
    Drive,
    DriveManager,
)
from pyvergeos.resources.vms import VM


class TestDriveManager:
    """Unit tests for DriveManager."""

    @pytest.fixture
    def vm(self, mock_client: VergeClient) -> VM:
        """Create a mock VM."""
        return VM(
            {"$key": 100, "name": "test-vm", "machine": 200},
            mock_client.vms,
        )

    def test_list_drives(self, mock_client: VergeClient, mock_session: MagicMock, vm: VM) -> None:
        """Test listing drives."""
        mock_session.request.return_value.json.return_value = [
            {
                "$key": 1,
                "name": "OS",
                "interface": "virtio-scsi",
                "media": "disk",
                "disksize": 53687091200,
            },
            {
                "$key": 2,
                "name": "Data",
                "interface": "virtio-scsi",
                "media": "disk",
                "disksize": 107374182400,
            },
        ]

        drives = vm.drives.list()

        assert len(drives) == 2
        assert drives[0].name == "OS"
        assert drives[1].name == "Data"

    def test_list_drives_filters_by_machine(
        self, mock_client: VergeClient, mock_session: MagicMock, vm: VM
    ) -> None:
        """Test that list() filters by machine key."""
        mock_session.request.return_value.json.return_value = []

        vm.drives.list()

        call_args = mock_session.request.call_args
        params = call_args.kwargs.get("params", {})
        assert "machine eq 200" in params.get("filter", "")

    def test_list_drives_by_media(
        self, mock_client: VergeClient, mock_session: MagicMock, vm: VM
    ) -> None:
        """Test filtering by media type."""
        mock_session.request.return_value.json.return_value = []

        vm.drives.list(media="cdrom")

        call_args = mock_session.request.call_args
        params = call_args.kwargs.get("params", {})
        filter_str = params.get("filter", "")
        assert "media eq 'cdrom'" in filter_str

    def test_get_drive_by_key(
        self, mock_client: VergeClient, mock_session: MagicMock, vm: VM
    ) -> None:
        """Test getting a drive by key."""
        mock_session.request.return_value.json.return_value = {
            "$key": 1,
            "name": "OS",
            "interface": "virtio-scsi",
        }

        drive = vm.drives.get(1)

        assert drive.key == 1
        assert drive.name == "OS"

    def test_get_drive_by_name(
        self, mock_client: VergeClient, mock_session: MagicMock, vm: VM
    ) -> None:
        """Test getting a drive by name."""
        mock_session.request.return_value.json.return_value = [
            {
                "$key": 1,
                "name": "OS",
                "interface": "virtio-scsi",
            }
        ]

        drive = vm.drives.get(name="OS")

        assert drive.name == "OS"

    def test_get_drive_not_found(
        self, mock_client: VergeClient, mock_session: MagicMock, vm: VM
    ) -> None:
        """Test NotFoundError when drive not found."""
        mock_session.request.return_value.json.return_value = []

        with pytest.raises(NotFoundError):
            vm.drives.get(name="nonexistent")

    def test_create_drive(self, mock_client: VergeClient, mock_session: MagicMock, vm: VM) -> None:
        """Test creating a drive."""
        # First call is POST (create), second is GET (fetch full data)
        mock_session.request.return_value.json.side_effect = [
            {
                "$key": 3,
                "name": "NewDrive",
                "interface": "nvme",
                "media": "disk",
                "disksize": 53687091200,
            },
            {
                "$key": 3,
                "name": "NewDrive",
                "interface": "nvme",
                "media": "disk",
                "disksize": 53687091200,
            },
        ]

        drive = vm.drives.create(size_gb=50, name="NewDrive", interface="nvme")

        assert drive.name == "NewDrive"
        # Find the POST call to machine_drives endpoint
        post_calls = [
            call
            for call in mock_session.request.call_args_list
            if call.kwargs.get("method") == "POST"
            and "machine_drives" in call.kwargs.get("url", "")
        ]
        assert len(post_calls) == 1
        body = post_calls[0].kwargs.get("json", {})
        assert body["machine"] == 200
        assert body["disksize"] == 50 * (1024**3)

    def test_create_drive_requires_size_for_disk(self, mock_client: VergeClient, vm: VM) -> None:
        """Test that size_gb is required for disk media."""
        with pytest.raises(ValueError, match="size_gb is required"):
            vm.drives.create(media="disk")

    def test_create_drive_with_tier(
        self, mock_client: VergeClient, mock_session: MagicMock, vm: VM
    ) -> None:
        """Test creating a drive with storage tier."""
        # First call is POST (create), second is GET (fetch full data)
        mock_session.request.return_value.json.side_effect = [
            {"$key": 4, "name": "TieredDrive", "preferred_tier": "1"},
            {"$key": 4, "name": "TieredDrive", "preferred_tier": "1"},
        ]

        vm.drives.create(size_gb=100, tier=1)

        # Find the POST call to machine_drives endpoint
        post_calls = [
            call
            for call in mock_session.request.call_args_list
            if call.kwargs.get("method") == "POST"
            and "machine_drives" in call.kwargs.get("url", "")
        ]
        assert len(post_calls) == 1
        body = post_calls[0].kwargs.get("json", {})
        assert body["preferred_tier"] == "1"

    def test_delete_drive(self, mock_client: VergeClient, mock_session: MagicMock, vm: VM) -> None:
        """Test deleting a drive."""
        mock_session.request.return_value.status_code = 204
        mock_session.request.return_value.text = ""

        vm.drives.delete(1)

        call_args = mock_session.request.call_args
        assert call_args.kwargs["method"] == "DELETE"
        assert "machine_drives/1" in call_args.kwargs["url"]

    def test_update_drive(self, mock_client: VergeClient, mock_session: MagicMock, vm: VM) -> None:
        """Test updating a drive."""
        mock_session.request.return_value.json.return_value = {
            "$key": 1,
            "name": "UpdatedDrive",
            "description": "New description",
        }

        drive = vm.drives.update(1, description="New description")

        assert drive.get("description") == "New description"

    def test_import_drive_by_file_key(
        self, mock_client: VergeClient, mock_session: MagicMock, vm: VM
    ) -> None:
        """Test importing a drive by file key."""
        # First call is POST (create), second is GET (fetch full data)
        mock_session.request.return_value.json.side_effect = [
            {
                "$key": 5,
                "name": "ImportedDisk",
                "interface": "virtio-scsi",
                "media": "import",
                "media_source": 999,
            },
            {
                "$key": 5,
                "name": "ImportedDisk",
                "interface": "virtio-scsi",
                "media": "import",
                "media_source": 999,
            },
        ]

        drive = vm.drives.import_drive(file_key=999, name="ImportedDisk")

        assert drive.name == "ImportedDisk"
        # Find the POST call to machine_drives endpoint
        post_calls = [
            call
            for call in mock_session.request.call_args_list
            if call.kwargs.get("method") == "POST"
            and "machine_drives" in call.kwargs.get("url", "")
        ]
        assert len(post_calls) == 1
        body = post_calls[0].kwargs.get("json", {})
        assert body["machine"] == 200
        assert body["media"] == "import"
        assert body["media_source"] == 999
        assert body["interface"] == "virtio-scsi"
        assert body["preserve_drive_format"] is False

    def test_import_drive_by_file_name(
        self, mock_client: VergeClient, mock_session: MagicMock, vm: VM
    ) -> None:
        """Test importing a drive by file name."""
        # First call is GET files (lookup), second is POST (create), third is GET (fetch)
        mock_session.request.return_value.json.side_effect = [
            [{"$key": 888, "name": "debian-12-generic-amd64.qcow2"}],
            {
                "$key": 6,
                "name": "ImportedQCOW",
                "interface": "nvme",
                "media": "import",
                "media_source": 888,
            },
            {
                "$key": 6,
                "name": "ImportedQCOW",
                "interface": "nvme",
                "media": "import",
                "media_source": 888,
            },
        ]

        drive = vm.drives.import_drive(
            file_name="debian-12-generic-amd64.qcow2",
            name="ImportedQCOW",
            interface="nvme",
            tier=1,
        )

        assert drive.name == "ImportedQCOW"
        # Find the POST call to machine_drives endpoint
        post_calls = [
            call
            for call in mock_session.request.call_args_list
            if call.kwargs.get("method") == "POST"
            and "machine_drives" in call.kwargs.get("url", "")
        ]
        assert len(post_calls) == 1
        body = post_calls[0].kwargs.get("json", {})
        assert body["media_source"] == 888
        assert body["interface"] == "nvme"
        assert body["preferred_tier"] == "1"

    def test_import_drive_preserve_format(
        self, mock_client: VergeClient, mock_session: MagicMock, vm: VM
    ) -> None:
        """Test importing a drive with preserve_drive_format option."""
        mock_session.request.return_value.json.side_effect = [
            {"$key": 7, "name": "PreservedDisk", "media": "import"},
            {"$key": 7, "name": "PreservedDisk", "media": "import"},
        ]

        vm.drives.import_drive(file_key=999, preserve_drive_format=True)

        post_calls = [
            call
            for call in mock_session.request.call_args_list
            if call.kwargs.get("method") == "POST"
            and "machine_drives" in call.kwargs.get("url", "")
        ]
        assert len(post_calls) == 1
        body = post_calls[0].kwargs.get("json", {})
        assert body["preserve_drive_format"] is True

    def test_import_drive_requires_file_key_or_name(self, mock_client: VergeClient, vm: VM) -> None:
        """Test that file_key or file_name is required."""
        with pytest.raises(ValueError, match="Either file_key or file_name must be provided"):
            vm.drives.import_drive()

    def test_import_drive_file_not_found(
        self, mock_client: VergeClient, mock_session: MagicMock, vm: VM
    ) -> None:
        """Test error when file not found by name."""
        mock_session.request.return_value.json.return_value = []

        with pytest.raises(ValueError, match="not found in media catalog"):
            vm.drives.import_drive(file_name="nonexistent.qcow2")


class TestDrive:
    """Unit tests for Drive object."""

    @pytest.fixture
    def drive_data(self) -> dict[str, Any]:
        """Sample drive data."""
        return {
            "$key": 1,
            "name": "OS",
            "interface": "virtio-scsi",
            "media": "disk",
            "disksize": 53687091200,  # 50 GB
            "used_bytes": 21474836480,  # 20 GB
            "enabled": True,
            "readonly": False,
        }

    @pytest.fixture
    def mock_drive_manager(self, mock_client: VergeClient) -> DriveManager:
        """Create a mock drive manager."""
        vm = VM({"$key": 100, "name": "test-vm", "machine": 200}, mock_client.vms)
        return DriveManager(mock_client, vm)

    def test_size_gb(self, drive_data: dict[str, Any], mock_drive_manager: DriveManager) -> None:
        """Test size_gb property."""
        drive = Drive(drive_data, mock_drive_manager)
        assert drive.size_gb == 50.0

    def test_used_gb(self, drive_data: dict[str, Any], mock_drive_manager: DriveManager) -> None:
        """Test used_gb property."""
        drive = Drive(drive_data, mock_drive_manager)
        assert drive.used_gb == 20.0

    def test_interface_display(
        self, drive_data: dict[str, Any], mock_drive_manager: DriveManager
    ) -> None:
        """Test interface_display property."""
        drive = Drive(drive_data, mock_drive_manager)
        assert drive.interface_display == "Virtio-SCSI"

    def test_interface_display_unknown(
        self, drive_data: dict[str, Any], mock_drive_manager: DriveManager
    ) -> None:
        """Test interface_display for unknown interface."""
        drive_data["interface"] = "custom"
        drive = Drive(drive_data, mock_drive_manager)
        assert drive.interface_display == "custom"

    def test_media_display(
        self, drive_data: dict[str, Any], mock_drive_manager: DriveManager
    ) -> None:
        """Test media_display property."""
        drive = Drive(drive_data, mock_drive_manager)
        assert drive.media_display == "Disk"

    def test_is_enabled(self, drive_data: dict[str, Any], mock_drive_manager: DriveManager) -> None:
        """Test is_enabled property."""
        drive = Drive(drive_data, mock_drive_manager)
        assert drive.is_enabled is True

    def test_is_readonly(
        self, drive_data: dict[str, Any], mock_drive_manager: DriveManager
    ) -> None:
        """Test is_readonly property."""
        drive = Drive(drive_data, mock_drive_manager)
        assert drive.is_readonly is False

        drive_data["readonly"] = True
        drive = Drive(drive_data, mock_drive_manager)
        assert drive.is_readonly is True


class TestDriveMaps:
    """Test interface and media display maps."""

    def test_interface_display_map(self) -> None:
        """Test all interface display mappings."""
        expected = {
            "virtio": "Virtio (Legacy)",
            "ide": "IDE",
            "ahci": "SATA (AHCI)",
            "nvme": "NVMe",
            "virtio-scsi": "Virtio-SCSI",
            "virtio-scsi-dedicated": "Virtio-SCSI (Dedicated)",
            "lsi53c895a": "LSI SCSI",
            "megasas": "LSI MegaRAID SAS",
            "megasas-gen2": "LSI MegaRAID SAS 2",
            "usb": "USB",
        }
        assert expected == INTERFACE_DISPLAY_MAP

    def test_media_display_map(self) -> None:
        """Test all media display mappings."""
        expected = {
            "cdrom": "CD-ROM",
            "disk": "Disk",
            "efidisk": "EFI Disk",
            "import": "Import Disk",
            "9p": "Pass-Through (9P)",
            "dir": "Pass-Through (Directory)",
            "clone": "Clone Disk",
            "nonpersistent": "Non-Persistent",
        }
        assert expected == MEDIA_DISPLAY_MAP
