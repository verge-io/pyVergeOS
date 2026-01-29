"""Unit tests for VM import management."""

from unittest.mock import MagicMock

import pytest

from pyvergeos import VergeClient
from pyvergeos.exceptions import NotFoundError
from pyvergeos.resources.vm_imports import (
    VmImport,
    VmImportLog,
    VmImportLogManager,
    VmImportManager,
)


@pytest.fixture
def mock_client():
    """Create a mock VergeClient."""
    client = MagicMock(spec=VergeClient)
    client._request = MagicMock()
    return client


@pytest.fixture
def vm_import_manager(mock_client):
    """Create a VmImportManager with mock client."""
    return VmImportManager(mock_client)


@pytest.fixture
def vm_import_log_manager(mock_client):
    """Create a VmImportLogManager with mock client."""
    return VmImportLogManager(mock_client)


@pytest.fixture
def scoped_log_manager(mock_client):
    """Create a scoped VmImportLogManager with mock client."""
    return VmImportLogManager(
        mock_client, import_key="8f73f8bcc9c9f1aaba32f733bfc295acaf548554"
    )


@pytest.fixture
def sample_vm_import():
    """Sample VM import data from API."""
    return {
        "$key": "8f73f8bcc9c9f1aaba32f733bfc295acaf548554",
        "id": "8f73f8bcc9c9f1aaba32f733bfc295acaf548554",
        "name": "imported-vm",
        "vm": 10,
        "vm_display": "imported-vm",
        "uuid": "abc123-def456-ghi789",
        "file": 1,
        "file_display": "ubuntu.ova",
        "volume": None,
        "volume_display": None,
        "volume_path": None,
        "status": "complete",
        "status_info": "Import completed successfully",
        "importing": False,
        "aborted": False,
        "preserve_macs": True,
        "preserve_drive_format": False,
        "preferred_tier": "1",
        "timestamp": 1700000000,
        "modified": 1700001000,
    }


@pytest.fixture
def sample_vm_import_in_progress():
    """Sample VM import data for an in-progress import."""
    return {
        "$key": "9a84a8bdd0d0e2bcbb43e844cec3a6bdbe659665",
        "id": "9a84a8bdd0d0e2bcbb43e844cec3a6bdbe659665",
        "name": "importing-vm",
        "vm": None,
        "uuid": None,
        "file": 2,
        "file_display": "windows.vmdk",
        "status": "importing",
        "status_info": "Converting disk 1 of 2",
        "importing": True,
        "aborted": False,
        "preserve_macs": True,
        "preserve_drive_format": False,
        "preferred_tier": "1",
        "timestamp": 1700002000,
        "modified": 1700003000,
    }


@pytest.fixture
def sample_vm_import_log():
    """Sample VM import log data from API."""
    return {
        "$key": 1,
        "vm_import": "8f73f8bcc9c9f1aaba32f733bfc295acaf548554",
        "level": "message",
        "text": "Starting import process",
        "timestamp": 1700000000,
        "user": "admin",
    }


class TestVmImport:
    """Tests for VmImport model."""

    def test_key_is_string(self, vm_import_manager, sample_vm_import):
        """Test that import key is a string (40-char hex)."""
        vm_import = VmImport(sample_vm_import, vm_import_manager)
        assert isinstance(vm_import.key, str)
        assert len(vm_import.key) == 40

    def test_key_missing(self, vm_import_manager):
        """Test key property raises ValueError when missing."""
        vm_import = VmImport({}, vm_import_manager)
        with pytest.raises(ValueError, match="has no \\$key"):
            _ = vm_import.key

    def test_is_complete_true(self, vm_import_manager, sample_vm_import):
        """Test is_complete returns True when status is complete."""
        vm_import = VmImport(sample_vm_import, vm_import_manager)
        assert vm_import.is_complete is True

    def test_is_complete_false(self, vm_import_manager, sample_vm_import_in_progress):
        """Test is_complete returns False when importing."""
        vm_import = VmImport(sample_vm_import_in_progress, vm_import_manager)
        assert vm_import.is_complete is False

    def test_is_importing_true(self, vm_import_manager, sample_vm_import_in_progress):
        """Test is_importing returns True when importing."""
        vm_import = VmImport(sample_vm_import_in_progress, vm_import_manager)
        assert vm_import.is_importing is True

    def test_is_importing_false(self, vm_import_manager, sample_vm_import):
        """Test is_importing returns False when complete."""
        vm_import = VmImport(sample_vm_import, vm_import_manager)
        assert vm_import.is_importing is False

    def test_has_error_true(self, vm_import_manager, sample_vm_import):
        """Test has_error returns True for error status."""
        sample_vm_import["status"] = "error"
        vm_import = VmImport(sample_vm_import, vm_import_manager)
        assert vm_import.has_error is True

    def test_has_error_aborted(self, vm_import_manager, sample_vm_import):
        """Test has_error returns True for aborted status."""
        sample_vm_import["status"] = "aborted"
        vm_import = VmImport(sample_vm_import, vm_import_manager)
        assert vm_import.has_error is True

    def test_has_error_false(self, vm_import_manager, sample_vm_import):
        """Test has_error returns False for complete status."""
        vm_import = VmImport(sample_vm_import, vm_import_manager)
        assert vm_import.has_error is False

    def test_vm_key(self, vm_import_manager, sample_vm_import):
        """Test vm_key property."""
        vm_import = VmImport(sample_vm_import, vm_import_manager)
        assert vm_import.vm_key == 10

    def test_vm_key_none(self, vm_import_manager, sample_vm_import_in_progress):
        """Test vm_key returns None when not set."""
        vm_import = VmImport(sample_vm_import_in_progress, vm_import_manager)
        assert vm_import.vm_key is None


class TestVmImportManagerList:
    """Tests for VmImportManager.list()."""

    def test_list_all(self, vm_import_manager, mock_client, sample_vm_import):
        """Test listing all imports."""
        mock_client._request.return_value = [sample_vm_import]

        result = vm_import_manager.list()

        assert len(result) == 1
        assert result[0].name == "imported-vm"
        mock_client._request.assert_called_once()
        args = mock_client._request.call_args
        assert args[0][0] == "GET"
        assert args[0][1] == "vm_imports"

    def test_list_empty(self, vm_import_manager, mock_client):
        """Test listing when no imports exist."""
        mock_client._request.return_value = None

        result = vm_import_manager.list()

        assert result == []

    def test_list_with_filter(self, vm_import_manager, mock_client, sample_vm_import):
        """Test listing with filter."""
        mock_client._request.return_value = [sample_vm_import]

        result = vm_import_manager.list(filter="name eq 'imported-vm'")

        assert len(result) == 1
        args = mock_client._request.call_args
        assert "filter" in args[1]["params"]
        assert args[1]["params"]["filter"] == "name eq 'imported-vm'"

    def test_list_with_status_filter(
        self, vm_import_manager, mock_client, sample_vm_import_in_progress
    ):
        """Test listing with status filter."""
        mock_client._request.return_value = [sample_vm_import_in_progress]

        result = vm_import_manager.list(status="importing")

        assert len(result) == 1
        args = mock_client._request.call_args
        assert "status eq 'importing'" in args[1]["params"]["filter"]

    def test_list_with_pagination(self, vm_import_manager, mock_client, sample_vm_import):
        """Test listing with pagination."""
        mock_client._request.return_value = [sample_vm_import]

        result = vm_import_manager.list(limit=10, offset=5)

        assert len(result) == 1
        args = mock_client._request.call_args
        assert args[1]["params"]["limit"] == 10
        assert args[1]["params"]["offset"] == 5


class TestVmImportManagerGet:
    """Tests for VmImportManager.get()."""

    def test_get_by_key(self, vm_import_manager, mock_client, sample_vm_import):
        """Test getting import by key."""
        mock_client._request.return_value = [sample_vm_import]

        result = vm_import_manager.get(key="8f73f8bcc9c9f1aaba32f733bfc295acaf548554")

        assert result.name == "imported-vm"
        args = mock_client._request.call_args
        assert args[0][0] == "GET"
        assert "id eq '8f73f8bcc9c9f1aaba32f733bfc295acaf548554'" in args[1]["params"]["filter"]

    def test_get_by_name(self, vm_import_manager, mock_client, sample_vm_import):
        """Test getting import by name."""
        mock_client._request.return_value = [sample_vm_import]

        result = vm_import_manager.get(name="imported-vm")

        assert result.name == "imported-vm"
        args = mock_client._request.call_args
        assert "name eq 'imported-vm'" in args[1]["params"]["filter"]

    def test_get_not_found_by_key(self, vm_import_manager, mock_client):
        """Test getting non-existent import by key."""
        mock_client._request.return_value = []

        with pytest.raises(NotFoundError, match="not found"):
            vm_import_manager.get(key="nonexistent")

    def test_get_not_found_by_name(self, vm_import_manager, mock_client):
        """Test getting non-existent import by name."""
        mock_client._request.return_value = []

        with pytest.raises(NotFoundError, match="not found"):
            vm_import_manager.get(name="nonexistent")

    def test_get_no_key_or_name(self, vm_import_manager):
        """Test get without key or name raises ValueError."""
        with pytest.raises(ValueError, match="Either key or name must be provided"):
            vm_import_manager.get()


class TestVmImportManagerCreate:
    """Tests for VmImportManager.create()."""

    def test_create_from_file(self, vm_import_manager, mock_client, sample_vm_import):
        """Test creating an import from a file."""
        mock_client._request.side_effect = [
            {"$key": "8f73f8bcc9c9f1aaba32f733bfc295acaf548554"},  # Create import
            [sample_vm_import],  # Get created import
        ]

        result = vm_import_manager.create("imported-vm", file=1)

        assert result.name == "imported-vm"
        create_call = mock_client._request.call_args_list[0]
        assert create_call[0][0] == "POST"
        assert create_call[0][1] == "vm_imports"
        assert create_call[1]["json_data"]["name"] == "imported-vm"
        assert create_call[1]["json_data"]["file"] == 1

    def test_create_from_volume(self, vm_import_manager, mock_client, sample_vm_import):
        """Test creating an import from a NAS volume."""
        mock_client._request.side_effect = [
            {"$key": "8f73f8bcc9c9f1aaba32f733bfc295acaf548554"},  # Create import
            [sample_vm_import],  # Get created import
        ]

        result = vm_import_manager.create(
            "imported-vm",
            volume="abc123...",
            volume_path="/exports/vm.vmdk",
        )

        assert result.name == "imported-vm"
        create_call = mock_client._request.call_args_list[0]
        assert create_call[1]["json_data"]["volume"] == "abc123..."
        assert create_call[1]["json_data"]["volume_path"] == "/exports/vm.vmdk"

    def test_create_no_source(self, vm_import_manager):
        """Test creating import without source raises ValueError."""
        with pytest.raises(ValueError, match="One of file, volume, or shared_object must be provided"):
            vm_import_manager.create("imported-vm")

    def test_create_with_all_options(self, vm_import_manager, mock_client, sample_vm_import):
        """Test creating import with all options."""
        mock_client._request.side_effect = [
            {"$key": "8f73f8bcc9c9f1aaba32f733bfc295acaf548554"},  # Create import
            [sample_vm_import],  # Get created import
        ]

        vm_import_manager.create(
            "imported-vm",
            file=1,
            preserve_macs=False,
            preserve_drive_format=True,
            preferred_tier="2",
            no_optical_drives=True,
            override_drive_interface="virtio-scsi",
            override_nic_interface="virtio",
            cleanup_on_delete=True,
        )

        create_call = mock_client._request.call_args_list[0]
        body = create_call[1]["json_data"]
        assert body["preserve_macs"] is False
        assert body["preserve_drive_format"] is True
        assert body["preferred_tier"] == "2"
        assert body["no_optical_drives"] is True
        assert body["override_drive_interface"] == "virtio-scsi"
        assert body["override_nic_interface"] == "virtio"
        assert body["cleanup_on_delete"] is True


class TestVmImportManagerUpdate:
    """Tests for VmImportManager.update()."""

    def test_update_name(self, vm_import_manager, mock_client, sample_vm_import):
        """Test updating import name."""
        mock_client._request.side_effect = [
            None,  # Update
            [sample_vm_import],  # Get updated import
        ]

        result = vm_import_manager.update(
            "8f73f8bcc9c9f1aaba32f733bfc295acaf548554",
            name="new-name",
        )

        assert result is not None
        update_call = mock_client._request.call_args_list[0]
        assert update_call[0][0] == "PUT"
        assert "8f73f8bcc9c9f1aaba32f733bfc295acaf548554" in update_call[0][1]
        assert update_call[1]["json_data"]["name"] == "new-name"

    def test_update_preserve_macs(self, vm_import_manager, mock_client, sample_vm_import):
        """Test updating preserve_macs setting."""
        mock_client._request.side_effect = [
            None,  # Update
            [sample_vm_import],  # Get updated import
        ]

        vm_import_manager.update(
            "8f73f8bcc9c9f1aaba32f733bfc295acaf548554",
            preserve_macs=False,
        )

        update_call = mock_client._request.call_args_list[0]
        assert update_call[1]["json_data"]["preserve_macs"] is False

    def test_update_no_changes(self, vm_import_manager, mock_client, sample_vm_import):
        """Test update with no changes."""
        mock_client._request.return_value = [sample_vm_import]

        vm_import_manager.update("8f73f8bcc9c9f1aaba32f733bfc295acaf548554")

        # Should only call get, not update
        assert mock_client._request.call_count == 1


class TestVmImportManagerDelete:
    """Tests for VmImportManager.delete()."""

    def test_delete(self, vm_import_manager, mock_client):
        """Test deleting an import."""
        mock_client._request.return_value = None

        vm_import_manager.delete("8f73f8bcc9c9f1aaba32f733bfc295acaf548554")

        delete_call = mock_client._request.call_args
        assert delete_call[0][0] == "DELETE"
        assert "8f73f8bcc9c9f1aaba32f733bfc295acaf548554" in delete_call[0][1]


class TestVmImportManagerActions:
    """Tests for VM import actions."""

    def test_start_import(self, vm_import_manager, mock_client):
        """Test starting an import."""
        mock_client._request.return_value = {"task": 123}

        result = vm_import_manager.start_import("8f73f8bcc9c9f1aaba32f733bfc295acaf548554")

        assert result == {"task": 123}
        action_call = mock_client._request.call_args
        assert action_call[0][0] == "PUT"
        assert "action=import" in action_call[0][1]

    def test_abort_import(self, vm_import_manager, mock_client):
        """Test aborting an import."""
        mock_client._request.return_value = {"task": 123}

        result = vm_import_manager.abort_import("8f73f8bcc9c9f1aaba32f733bfc295acaf548554")

        assert result == {"task": 123}
        action_call = mock_client._request.call_args
        assert action_call[0][0] == "PUT"
        assert "action=abort" in action_call[0][1]

    def test_get_logs_manager(self, vm_import_manager, mock_client):
        """Test getting a scoped logs manager."""
        log_mgr = vm_import_manager.logs("8f73f8bcc9c9f1aaba32f733bfc295acaf548554")

        assert isinstance(log_mgr, VmImportLogManager)
        assert log_mgr._import_key == "8f73f8bcc9c9f1aaba32f733bfc295acaf548554"


# =============================================================================
# VM Import Log Tests
# =============================================================================


class TestVmImportLog:
    """Tests for VmImportLog model."""

    def test_is_error_true(self, vm_import_log_manager, sample_vm_import_log):
        """Test is_error returns True for error level."""
        sample_vm_import_log["level"] = "error"
        log = VmImportLog(sample_vm_import_log, vm_import_log_manager)
        assert log.is_error is True

    def test_is_error_critical(self, vm_import_log_manager, sample_vm_import_log):
        """Test is_error returns True for critical level."""
        sample_vm_import_log["level"] = "critical"
        log = VmImportLog(sample_vm_import_log, vm_import_log_manager)
        assert log.is_error is True

    def test_is_error_false(self, vm_import_log_manager, sample_vm_import_log):
        """Test is_error returns False for message level."""
        log = VmImportLog(sample_vm_import_log, vm_import_log_manager)
        assert log.is_error is False

    def test_is_warning_true(self, vm_import_log_manager, sample_vm_import_log):
        """Test is_warning returns True for warning level."""
        sample_vm_import_log["level"] = "warning"
        log = VmImportLog(sample_vm_import_log, vm_import_log_manager)
        assert log.is_warning is True

    def test_is_warning_false(self, vm_import_log_manager, sample_vm_import_log):
        """Test is_warning returns False for message level."""
        log = VmImportLog(sample_vm_import_log, vm_import_log_manager)
        assert log.is_warning is False


class TestVmImportLogManagerList:
    """Tests for VmImportLogManager.list()."""

    def test_list_all(self, vm_import_log_manager, mock_client, sample_vm_import_log):
        """Test listing all logs."""
        mock_client._request.return_value = [sample_vm_import_log]

        result = vm_import_log_manager.list()

        assert len(result) == 1
        assert result[0].text == "Starting import process"
        mock_client._request.assert_called_once()
        args = mock_client._request.call_args
        assert args[0][0] == "GET"
        assert args[0][1] == "vm_import_logs"

    def test_list_empty(self, vm_import_log_manager, mock_client):
        """Test listing when no logs exist."""
        mock_client._request.return_value = None

        result = vm_import_log_manager.list()

        assert result == []

    def test_list_scoped_to_import(self, scoped_log_manager, mock_client, sample_vm_import_log):
        """Test listing logs scoped to an import."""
        mock_client._request.return_value = [sample_vm_import_log]

        result = scoped_log_manager.list()

        assert len(result) == 1
        args = mock_client._request.call_args
        assert "vm_import eq '8f73f8bcc9c9f1aaba32f733bfc295acaf548554'" in args[1]["params"]["filter"]

    def test_list_with_level_filter(self, vm_import_log_manager, mock_client, sample_vm_import_log):
        """Test listing with level filter."""
        sample_vm_import_log["level"] = "error"
        mock_client._request.return_value = [sample_vm_import_log]

        result = vm_import_log_manager.list(level="error")

        assert len(result) == 1
        args = mock_client._request.call_args
        assert "level eq 'error'" in args[1]["params"]["filter"]

    def test_list_with_vm_import_filter(
        self, vm_import_log_manager, mock_client, sample_vm_import_log
    ):
        """Test listing with vm_import filter."""
        mock_client._request.return_value = [sample_vm_import_log]

        result = vm_import_log_manager.list(
            vm_import="8f73f8bcc9c9f1aaba32f733bfc295acaf548554"
        )

        assert len(result) == 1
        args = mock_client._request.call_args
        assert "vm_import eq '8f73f8bcc9c9f1aaba32f733bfc295acaf548554'" in args[1]["params"]["filter"]

    def test_list_with_pagination(self, vm_import_log_manager, mock_client, sample_vm_import_log):
        """Test listing with pagination."""
        mock_client._request.return_value = [sample_vm_import_log]

        result = vm_import_log_manager.list(limit=10, offset=5)

        assert len(result) == 1
        args = mock_client._request.call_args
        assert args[1]["params"]["limit"] == 10
        assert args[1]["params"]["offset"] == 5


class TestVmImportLogManagerGet:
    """Tests for VmImportLogManager.get()."""

    def test_get_by_key(self, vm_import_log_manager, mock_client, sample_vm_import_log):
        """Test getting log by key."""
        mock_client._request.return_value = sample_vm_import_log

        result = vm_import_log_manager.get(key=1)

        assert result.text == "Starting import process"
        args = mock_client._request.call_args
        assert args[0][0] == "GET"
        assert args[0][1] == "vm_import_logs/1"

    def test_get_not_found(self, vm_import_log_manager, mock_client):
        """Test getting non-existent log."""
        mock_client._request.return_value = None

        with pytest.raises(NotFoundError, match="not found"):
            vm_import_log_manager.get(key=999)

    def test_get_no_key(self, vm_import_log_manager):
        """Test get without key raises ValueError."""
        with pytest.raises(ValueError, match="Key must be provided"):
            vm_import_log_manager.get()


class TestVmImportLogManagerHelpers:
    """Tests for VmImportLogManager helper methods."""

    def test_list_errors(self, scoped_log_manager, mock_client, sample_vm_import_log):
        """Test list_errors helper."""
        sample_vm_import_log["level"] = "error"
        mock_client._request.return_value = [sample_vm_import_log]

        result = scoped_log_manager.list_errors()

        assert len(result) == 1
        args = mock_client._request.call_args
        assert "(level eq 'error') or (level eq 'critical')" in args[1]["params"]["filter"]

    def test_list_warnings(self, scoped_log_manager, mock_client, sample_vm_import_log):
        """Test list_warnings helper."""
        sample_vm_import_log["level"] = "warning"
        mock_client._request.return_value = [sample_vm_import_log]

        result = scoped_log_manager.list_warnings()

        assert len(result) == 1
        args = mock_client._request.call_args
        assert "level eq 'warning'" in args[1]["params"]["filter"]
