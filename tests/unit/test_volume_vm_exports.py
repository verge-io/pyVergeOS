"""Unit tests for Volume VM export management."""

from unittest.mock import MagicMock

import pytest

from pyvergeos import VergeClient
from pyvergeos.exceptions import NotFoundError
from pyvergeos.resources.volume_vm_exports import (
    VolumeVmExport,
    VolumeVmExportManager,
    VolumeVmExportStat,
    VolumeVmExportStatManager,
)


@pytest.fixture
def mock_client():
    """Create a mock VergeClient."""
    client = MagicMock(spec=VergeClient)
    client._request = MagicMock()
    return client


@pytest.fixture
def export_manager(mock_client):
    """Create a VolumeVmExportManager with mock client."""
    return VolumeVmExportManager(mock_client)


@pytest.fixture
def stat_manager(mock_client):
    """Create a VolumeVmExportStatManager with mock client."""
    return VolumeVmExportStatManager(mock_client)


@pytest.fixture
def scoped_stat_manager(mock_client):
    """Create a scoped VolumeVmExportStatManager with mock client."""
    return VolumeVmExportStatManager(mock_client, export_key=1)


@pytest.fixture
def sample_export():
    """Sample volume VM export data from API."""
    return {
        "$key": 1,
        "volume": 10,
        "volume_display": "ExportVolume",
        "volume_name": "ExportVolume",
        "quiesced": True,
        "status": "idle",
        "status_info": "",
        "create_current": True,
        "max_exports": 3,
    }


@pytest.fixture
def sample_export_building():
    """Sample volume VM export data for a building export."""
    return {
        "$key": 2,
        "volume": 20,
        "volume_display": "BackupVolume",
        "volume_name": "BackupVolume",
        "quiesced": True,
        "status": "building",
        "status_info": "Exporting VM 1 of 5",
        "create_current": True,
        "max_exports": 5,
    }


@pytest.fixture
def sample_export_stat():
    """Sample volume VM export stat data from API."""
    return {
        "$key": 1,
        "volume_vm_exports": 1,
        "duration": 3600,
        "virtual_machines": 5,
        "export_success": 5,
        "errors": 0,
        "quiesced": True,
        "size_bytes": 107374182400,  # 100 GB
        "file_name": "export-2024-01-15",
        "timestamp": 1700000000,
    }


class TestVolumeVmExport:
    """Tests for VolumeVmExport model."""

    def test_is_idle_true(self, export_manager, sample_export):
        """Test is_idle returns True when idle."""
        export = VolumeVmExport(sample_export, export_manager)
        assert export.is_idle is True

    def test_is_idle_false(self, export_manager, sample_export_building):
        """Test is_idle returns False when building."""
        export = VolumeVmExport(sample_export_building, export_manager)
        assert export.is_idle is False

    def test_is_building_true(self, export_manager, sample_export_building):
        """Test is_building returns True when building."""
        export = VolumeVmExport(sample_export_building, export_manager)
        assert export.is_building is True

    def test_is_building_false(self, export_manager, sample_export):
        """Test is_building returns False when idle."""
        export = VolumeVmExport(sample_export, export_manager)
        assert export.is_building is False

    def test_has_error_true(self, export_manager, sample_export):
        """Test has_error returns True for error status."""
        sample_export["status"] = "error"
        export = VolumeVmExport(sample_export, export_manager)
        assert export.has_error is True

    def test_has_error_false(self, export_manager, sample_export):
        """Test has_error returns False for idle status."""
        export = VolumeVmExport(sample_export, export_manager)
        assert export.has_error is False

    def test_volume_key(self, export_manager, sample_export):
        """Test volume_key property."""
        export = VolumeVmExport(sample_export, export_manager)
        assert export.volume_key == 10

    def test_volume_key_none(self, export_manager):
        """Test volume_key returns None when not set."""
        export = VolumeVmExport({"$key": 1}, export_manager)
        assert export.volume_key is None


class TestVolumeVmExportManagerList:
    """Tests for VolumeVmExportManager.list()."""

    def test_list_all(self, export_manager, mock_client, sample_export):
        """Test listing all exports."""
        mock_client._request.return_value = [sample_export]

        result = export_manager.list()

        assert len(result) == 1
        assert result[0].volume_key == 10
        mock_client._request.assert_called_once()
        args = mock_client._request.call_args
        assert args[0][0] == "GET"
        assert args[0][1] == "volume_vm_exports"

    def test_list_empty(self, export_manager, mock_client):
        """Test listing when no exports exist."""
        mock_client._request.return_value = None

        result = export_manager.list()

        assert result == []

    def test_list_with_filter(self, export_manager, mock_client, sample_export):
        """Test listing with filter."""
        mock_client._request.return_value = [sample_export]

        result = export_manager.list(filter="volume eq 10")

        assert len(result) == 1
        args = mock_client._request.call_args
        assert "filter" in args[1]["params"]
        assert args[1]["params"]["filter"] == "volume eq 10"

    def test_list_with_status_filter(self, export_manager, mock_client, sample_export_building):
        """Test listing with status filter."""
        mock_client._request.return_value = [sample_export_building]

        result = export_manager.list(status="building")

        assert len(result) == 1
        args = mock_client._request.call_args
        assert "status eq 'building'" in args[1]["params"]["filter"]

    def test_list_with_volume_filter(self, export_manager, mock_client, sample_export):
        """Test listing with volume filter."""
        mock_client._request.return_value = [sample_export]

        result = export_manager.list(volume=10)

        assert len(result) == 1
        args = mock_client._request.call_args
        assert "volume eq 10" in args[1]["params"]["filter"]

    def test_list_with_pagination(self, export_manager, mock_client, sample_export):
        """Test listing with pagination."""
        mock_client._request.return_value = [sample_export]

        result = export_manager.list(limit=10, offset=5)

        assert len(result) == 1
        args = mock_client._request.call_args
        assert args[1]["params"]["limit"] == 10
        assert args[1]["params"]["offset"] == 5


class TestVolumeVmExportManagerGet:
    """Tests for VolumeVmExportManager.get()."""

    def test_get_by_key(self, export_manager, mock_client, sample_export):
        """Test getting export by key."""
        mock_client._request.return_value = sample_export

        result = export_manager.get(key=1)

        assert result.key == 1
        args = mock_client._request.call_args
        assert args[0][0] == "GET"
        assert args[0][1] == "volume_vm_exports/1"

    def test_get_by_volume(self, export_manager, mock_client, sample_export):
        """Test getting export by volume."""
        mock_client._request.return_value = [sample_export]

        result = export_manager.get(volume=10)

        assert result.volume_key == 10
        args = mock_client._request.call_args
        assert "volume eq 10" in args[1]["params"]["filter"]

    def test_get_not_found_by_key(self, export_manager, mock_client):
        """Test getting non-existent export by key."""
        mock_client._request.return_value = None

        with pytest.raises(NotFoundError, match="not found"):
            export_manager.get(key=999)

    def test_get_not_found_by_volume(self, export_manager, mock_client):
        """Test getting non-existent export by volume."""
        mock_client._request.return_value = []

        with pytest.raises(NotFoundError, match="not found"):
            export_manager.get(volume=999)

    def test_get_no_key_or_volume(self, export_manager):
        """Test get without key or volume raises ValueError."""
        with pytest.raises(ValueError, match="Either key or volume must be provided"):
            export_manager.get()


class TestVolumeVmExportManagerCreate:
    """Tests for VolumeVmExportManager.create()."""

    def test_create_basic(self, export_manager, mock_client, sample_export):
        """Test creating an export configuration."""
        mock_client._request.side_effect = [
            {"$key": 1},  # Create export
            sample_export,  # Get created export
        ]

        result = export_manager.create(volume=10)

        assert result.volume_key == 10
        create_call = mock_client._request.call_args_list[0]
        assert create_call[0][0] == "POST"
        assert create_call[0][1] == "volume_vm_exports"
        assert create_call[1]["json_data"]["volume"] == 10
        assert create_call[1]["json_data"]["quiesced"] is True
        assert create_call[1]["json_data"]["create_current"] is True
        assert create_call[1]["json_data"]["max_exports"] == 3

    def test_create_with_options(self, export_manager, mock_client, sample_export):
        """Test creating export with custom options."""
        mock_client._request.side_effect = [
            {"$key": 1},  # Create export
            sample_export,  # Get created export
        ]

        export_manager.create(
            volume=10,
            quiesced=False,
            create_current=False,
            max_exports=10,
        )

        create_call = mock_client._request.call_args_list[0]
        body = create_call[1]["json_data"]
        assert body["quiesced"] is False
        assert body["create_current"] is False
        assert body["max_exports"] == 10


class TestVolumeVmExportManagerUpdate:
    """Tests for VolumeVmExportManager.update()."""

    def test_update_quiesced(self, export_manager, mock_client, sample_export):
        """Test updating quiesced setting."""
        mock_client._request.side_effect = [
            None,  # Update
            sample_export,  # Get updated export
        ]

        result = export_manager.update(1, quiesced=False)

        assert result is not None
        update_call = mock_client._request.call_args_list[0]
        assert update_call[0][0] == "PUT"
        assert update_call[0][1] == "volume_vm_exports/1"
        assert update_call[1]["json_data"]["quiesced"] is False

    def test_update_max_exports(self, export_manager, mock_client, sample_export):
        """Test updating max_exports setting."""
        mock_client._request.side_effect = [
            None,  # Update
            sample_export,  # Get updated export
        ]

        export_manager.update(1, max_exports=10)

        update_call = mock_client._request.call_args_list[0]
        assert update_call[1]["json_data"]["max_exports"] == 10

    def test_update_no_changes(self, export_manager, mock_client, sample_export):
        """Test update with no changes."""
        mock_client._request.return_value = sample_export

        export_manager.update(1)

        # Should only call get, not update
        assert mock_client._request.call_count == 1


class TestVolumeVmExportManagerDelete:
    """Tests for VolumeVmExportManager.delete()."""

    def test_delete(self, export_manager, mock_client):
        """Test deleting an export."""
        mock_client._request.return_value = None

        export_manager.delete(1)

        delete_call = mock_client._request.call_args
        assert delete_call[0][0] == "DELETE"
        assert delete_call[0][1] == "volume_vm_exports/1"


class TestVolumeVmExportManagerActions:
    """Tests for VM export actions."""

    def test_start_export(self, export_manager, mock_client):
        """Test starting an export."""
        mock_client._request.return_value = {"task": 123}

        result = export_manager.start_export(1)

        assert result == {"task": 123}
        action_call = mock_client._request.call_args
        assert action_call[0][0] == "POST"
        assert action_call[0][1] == "volume_vm_export_actions"
        assert action_call[1]["json_data"]["action"] == "start_export"

    def test_start_export_with_options(self, export_manager, mock_client):
        """Test starting an export with options."""
        mock_client._request.return_value = {"task": 123}

        result = export_manager.start_export(1, name="backup-2024", vms=[1, 2, 3])

        assert result == {"task": 123}
        action_call = mock_client._request.call_args
        body = action_call[1]["json_data"]
        assert body["params"]["name"] == "backup-2024"
        assert body["params"]["vms"] == [1, 2, 3]

    def test_stop_export(self, export_manager, mock_client):
        """Test stopping an export."""
        mock_client._request.return_value = {"task": 123}

        result = export_manager.stop_export(1)

        assert result == {"task": 123}
        action_call = mock_client._request.call_args
        assert action_call[1]["json_data"]["action"] == "stop_export"

    def test_cleanup_exports(self, export_manager, mock_client):
        """Test cleaning up exports."""
        mock_client._request.return_value = {"task": 123}

        result = export_manager.cleanup_exports(1)

        assert result == {"task": 123}
        action_call = mock_client._request.call_args
        assert action_call[1]["json_data"]["action"] == "cleanup"

    def test_get_stats_manager(self, export_manager, mock_client):
        """Test getting a scoped stats manager."""
        stat_mgr = export_manager.stats(1)

        assert isinstance(stat_mgr, VolumeVmExportStatManager)
        assert stat_mgr._export_key == 1


# =============================================================================
# Volume VM Export Stat Tests
# =============================================================================


class TestVolumeVmExportStat:
    """Tests for VolumeVmExportStat model."""

    def test_size_gb(self, stat_manager, sample_export_stat):
        """Test size_gb property."""
        stat = VolumeVmExportStat(sample_export_stat, stat_manager)
        assert stat.size_gb == 100.0

    def test_size_gb_zero(self, stat_manager):
        """Test size_gb returns 0 when not set."""
        stat = VolumeVmExportStat({"$key": 1}, stat_manager)
        assert stat.size_gb == 0

    def test_has_errors_true(self, stat_manager, sample_export_stat):
        """Test has_errors returns True when errors > 0."""
        sample_export_stat["errors"] = 2
        stat = VolumeVmExportStat(sample_export_stat, stat_manager)
        assert stat.has_errors is True

    def test_has_errors_false(self, stat_manager, sample_export_stat):
        """Test has_errors returns False when no errors."""
        stat = VolumeVmExportStat(sample_export_stat, stat_manager)
        assert stat.has_errors is False


class TestVolumeVmExportStatManagerList:
    """Tests for VolumeVmExportStatManager.list()."""

    def test_list_all(self, stat_manager, mock_client, sample_export_stat):
        """Test listing all stats."""
        mock_client._request.return_value = [sample_export_stat]

        result = stat_manager.list()

        assert len(result) == 1
        assert result[0].file_name == "export-2024-01-15"
        mock_client._request.assert_called_once()
        args = mock_client._request.call_args
        assert args[0][0] == "GET"
        assert args[0][1] == "volume_vm_export_stats"

    def test_list_empty(self, stat_manager, mock_client):
        """Test listing when no stats exist."""
        mock_client._request.return_value = None

        result = stat_manager.list()

        assert result == []

    def test_list_scoped_to_export(self, scoped_stat_manager, mock_client, sample_export_stat):
        """Test listing stats scoped to an export."""
        mock_client._request.return_value = [sample_export_stat]

        result = scoped_stat_manager.list()

        assert len(result) == 1
        args = mock_client._request.call_args
        assert "volume_vm_exports eq 1" in args[1]["params"]["filter"]

    def test_list_with_export_filter(self, stat_manager, mock_client, sample_export_stat):
        """Test listing with export filter."""
        mock_client._request.return_value = [sample_export_stat]

        result = stat_manager.list(volume_vm_exports=1)

        assert len(result) == 1
        args = mock_client._request.call_args
        assert "volume_vm_exports eq 1" in args[1]["params"]["filter"]

    def test_list_with_pagination(self, stat_manager, mock_client, sample_export_stat):
        """Test listing with pagination."""
        mock_client._request.return_value = [sample_export_stat]

        result = stat_manager.list(limit=10, offset=5)

        assert len(result) == 1
        args = mock_client._request.call_args
        assert args[1]["params"]["limit"] == 10
        assert args[1]["params"]["offset"] == 5


class TestVolumeVmExportStatManagerGet:
    """Tests for VolumeVmExportStatManager.get()."""

    def test_get_by_key(self, stat_manager, mock_client, sample_export_stat):
        """Test getting stat by key."""
        mock_client._request.return_value = sample_export_stat

        result = stat_manager.get(key=1)

        assert result.file_name == "export-2024-01-15"
        args = mock_client._request.call_args
        assert args[0][0] == "GET"
        assert args[0][1] == "volume_vm_export_stats/1"

    def test_get_not_found(self, stat_manager, mock_client):
        """Test getting non-existent stat."""
        mock_client._request.return_value = None

        with pytest.raises(NotFoundError, match="not found"):
            stat_manager.get(key=999)

    def test_get_no_key(self, stat_manager):
        """Test get without key raises ValueError."""
        with pytest.raises(ValueError, match="Key must be provided"):
            stat_manager.get()


class TestVolumeVmExportStatManagerDelete:
    """Tests for VolumeVmExportStatManager.delete()."""

    def test_delete(self, stat_manager, mock_client):
        """Test deleting a stat."""
        mock_client._request.return_value = None

        stat_manager.delete(1)

        delete_call = mock_client._request.call_args
        assert delete_call[0][0] == "DELETE"
        assert delete_call[0][1] == "volume_vm_export_stats/1"
