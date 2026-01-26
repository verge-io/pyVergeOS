"""Unit tests for NAS volume sync operations."""

from unittest.mock import MagicMock

import pytest

from pyvergeos import VergeClient
from pyvergeos.exceptions import NotFoundError
from pyvergeos.resources.nas_volume_syncs import NASVolumeSync, NASVolumeSyncManager


@pytest.fixture
def mock_client():
    """Create a mock VergeClient."""
    client = MagicMock(spec=VergeClient)
    client._request = MagicMock()
    return client


@pytest.fixture
def sync_manager(mock_client):
    """Create a NASVolumeSyncManager with mock client."""
    return NASVolumeSyncManager(mock_client)


@pytest.fixture
def sample_volume_sync():
    """Sample volume sync data from API."""
    return {
        "$key": "735baabd93e83512035e5dbd62dc0810a468242a",
        "id": "735baabd93e83512035e5dbd62dc0810a468242a",
        "name": "DailyBackup",
        "description": "Daily backup sync",
        "enabled": True,
        "service": 2,
        "service_name": "NAS01",
        "source_volume": "a769f52bb8b78cd1a83763da5e665da173a6ed25",
        "source_volume_name": "SourceVol",
        "source_path": "",
        "destination_volume": "8f73f8bcc9c9f1aaba32f733bfc295acaf548554",
        "destination_volume_name": "DestVol",
        "destination_path": "",
        "include": "",
        "exclude": "",
        "sync_method": "ysync",
        "destination_delete": "never",
        "workers": 4,
        "preserve_ACLs": True,
        "preserve_permissions": True,
        "preserve_owner": True,
        "preserve_groups": True,
        "preserve_mod_time": True,
        "preserve_xattrs": True,
        "copy_symlinks": True,
        "fsfreeze": False,
        "status": "complete",
        "syncing": False,
        "files_transferred": 100,
        "bytes_transferred": 1048576,
        "transfer_rate": "1.0 MB/s",
        "sync_errors": 0,
        "start_time": 1700000000,
        "stop_time": 1700001000,
        "created": 1699900000,
        "modified": 1700001000,
    }


class TestNASVolumeSyncManager:
    """Tests for NASVolumeSyncManager."""

    def test_list_returns_empty_list_when_no_syncs(self, mock_client):
        """Test listing syncs when none exist."""
        mock_client._request.return_value = []
        manager = NASVolumeSyncManager(mock_client)

        result = manager.list()

        assert result == []
        mock_client._request.assert_called_once()

    def test_list_returns_syncs(self, mock_client):
        """Test listing syncs returns NASVolumeSync objects."""
        mock_client._request.return_value = [
            {
                "$key": "sync1",
                "id": "sync1",
                "name": "DailyBackup",
                "enabled": True,
                "service": 1,
                "source_volume": "vol1",
                "destination_volume": "vol2",
                "sync_method": "ysync",
                "destination_delete": "never",
                "status": "complete",
                "syncing": False,
            },
            {
                "$key": "sync2",
                "id": "sync2",
                "name": "WeeklyBackup",
                "enabled": True,
                "service": 1,
                "source_volume": "vol1",
                "destination_volume": "vol3",
                "sync_method": "rsync",
                "destination_delete": "delete",
                "status": "offline",
                "syncing": False,
            },
        ]
        manager = NASVolumeSyncManager(mock_client)

        result = manager.list()

        assert len(result) == 2
        assert all(isinstance(sync, NASVolumeSync) for sync in result)
        assert result[0].name == "DailyBackup"
        assert result[1].name == "WeeklyBackup"

    def test_list_with_service_filter_int(self, mock_client):
        """Test listing syncs filtered by service key."""
        mock_client._request.return_value = []
        manager = NASVolumeSyncManager(mock_client)

        manager.list(service=1)

        call_args = mock_client._request.call_args
        assert "service eq 1" in call_args.kwargs.get("params", {}).get("filter", "")

    def test_list_with_service_filter_string(self, mock_client):
        """Test listing syncs filtered by service name."""
        # First call returns the service, second returns syncs
        mock_client._request.side_effect = [
            [{"$key": 1, "name": "NAS01"}],  # Service lookup
            [],  # Sync list
        ]
        manager = NASVolumeSyncManager(mock_client)

        manager.list(service="NAS01")

        # Second call should have the service filter
        calls = mock_client._request.call_args_list
        assert len(calls) == 2
        assert "service eq 1" in calls[1].kwargs.get("params", {}).get("filter", "")

    def test_list_with_enabled_filter(self, mock_client):
        """Test listing syncs filtered by enabled state."""
        mock_client._request.return_value = []
        manager = NASVolumeSyncManager(mock_client)

        manager.list(enabled=True)

        call_args = mock_client._request.call_args
        assert "enabled eq 1" in call_args.kwargs.get("params", {}).get("filter", "")

    def test_get_by_key(self, mock_client):
        """Test getting a sync by key."""
        mock_client._request.return_value = [
            {
                "$key": "sync1",
                "id": "sync1",
                "name": "DailyBackup",
                "enabled": True,
            }
        ]
        manager = NASVolumeSyncManager(mock_client)

        result = manager.get("sync1")

        assert isinstance(result, NASVolumeSync)
        assert result.name == "DailyBackup"

    def test_get_by_key_not_found(self, mock_client):
        """Test getting a sync by key that doesn't exist."""
        mock_client._request.return_value = []
        manager = NASVolumeSyncManager(mock_client)

        with pytest.raises(NotFoundError):
            manager.get("nonexistent")

    def test_get_by_name(self, mock_client):
        """Test getting a sync by name."""
        mock_client._request.return_value = [
            {
                "$key": "sync1",
                "id": "sync1",
                "name": "DailyBackup",
                "enabled": True,
            }
        ]
        manager = NASVolumeSyncManager(mock_client)

        result = manager.get(name="DailyBackup")

        assert isinstance(result, NASVolumeSync)
        assert result.name == "DailyBackup"

    def test_get_by_name_not_found(self, mock_client):
        """Test getting a sync by name that doesn't exist."""
        mock_client._request.return_value = []
        manager = NASVolumeSyncManager(mock_client)

        with pytest.raises(NotFoundError):
            manager.get(name="nonexistent")

    def test_get_requires_key_or_name(self, mock_client):
        """Test that get requires either key or name."""
        manager = NASVolumeSyncManager(mock_client)

        with pytest.raises(ValueError):
            manager.get()

    def test_create_basic(self, mock_client):
        """Test creating a basic sync job."""
        mock_client._request.side_effect = [
            [{"$key": 1, "name": "NAS01"}],  # Service lookup
            {"$key": "newsync", "id": "newsync"},  # Create response
            [  # Get response
                {
                    "$key": "newsync",
                    "id": "newsync",
                    "name": "TestSync",
                    "enabled": True,
                    "service": 1,
                }
            ],
        ]
        manager = NASVolumeSyncManager(mock_client)

        result = manager.create(
            name="TestSync",
            service="NAS01",
            source_volume="vol1",
            destination_volume="vol2",
        )

        assert isinstance(result, NASVolumeSync)
        assert result.name == "TestSync"

        # Check the POST call
        create_call = mock_client._request.call_args_list[1]
        assert create_call.args[0] == "POST"
        assert create_call.args[1] == "volume_syncs"
        body = create_call.kwargs.get("json_data", {})
        assert body["name"] == "TestSync"
        assert body["service"] == 1
        assert body["source_volume"] == "vol1"
        assert body["destination_volume"] == "vol2"
        assert body["type"] == "volsync"

    def test_create_with_service_key(self, mock_client):
        """Test creating a sync with service key instead of name."""
        mock_client._request.side_effect = [
            {"$key": "newsync", "id": "newsync"},  # Create response
            [  # Get response
                {
                    "$key": "newsync",
                    "id": "newsync",
                    "name": "TestSync",
                    "service": 1,
                }
            ],
        ]
        manager = NASVolumeSyncManager(mock_client)

        manager.create(
            name="TestSync",
            service=1,
            source_volume="vol1",
            destination_volume="vol2",
        )

        # Should not have service lookup
        create_call = mock_client._request.call_args_list[0]
        assert create_call.args[0] == "POST"

    def test_create_with_options(self, mock_client):
        """Test creating a sync with all options."""
        mock_client._request.side_effect = [
            {"$key": "newsync"},  # Create response
            [{"$key": "newsync", "name": "TestSync"}],  # Get response
        ]
        manager = NASVolumeSyncManager(mock_client)

        manager.create(
            name="TestSync",
            service=1,
            source_volume="vol1",
            destination_volume="vol2",
            source_path="/data",
            destination_path="/backup",
            description="Test description",
            include=["*.txt", "*.doc"],
            exclude=["temp/*"],
            sync_method="rsync",
            destination_delete="delete-after",
            workers=8,
            preserve_acls=False,
            preserve_permissions=True,
            preserve_owner=True,
            preserve_groups=True,
            preserve_mod_time=True,
            preserve_xattrs=False,
            copy_symlinks=True,
            freeze_filesystem=True,
            enabled=False,
        )

        create_call = mock_client._request.call_args_list[0]
        body = create_call.kwargs.get("json_data", {})
        assert body["source_path"] == "/data"
        assert body["destination_path"] == "/backup"
        assert body["description"] == "Test description"
        assert body["include"] == "*.txt\n*.doc"
        assert body["exclude"] == "temp/*"
        assert body["sync_method"] == "rsync"
        assert body["destination_delete"] == "delete-after"
        assert body["workers"] == 8
        assert body["preserve_ACLs"] is False
        assert body["preserve_xattrs"] is False
        assert body["fsfreeze"] is True
        assert body["enabled"] is False

    def test_create_service_not_found(self, mock_client):
        """Test creating a sync with nonexistent service."""
        mock_client._request.return_value = []  # Service lookup returns empty
        manager = NASVolumeSyncManager(mock_client)

        with pytest.raises(ValueError, match="NAS service 'NonexistentNAS' not found"):
            manager.create(
                name="TestSync",
                service="NonexistentNAS",
                source_volume="vol1",
                destination_volume="vol2",
            )

    def test_update(self, mock_client):
        """Test updating a sync job."""
        mock_client._request.side_effect = [
            None,  # PUT response
            [  # GET response
                {
                    "$key": "sync1",
                    "name": "TestSync",
                    "description": "Updated",
                    "workers": 8,
                }
            ],
        ]
        manager = NASVolumeSyncManager(mock_client)

        result = manager.update("sync1", description="Updated", workers=8)

        assert isinstance(result, NASVolumeSync)
        put_call = mock_client._request.call_args_list[0]
        assert put_call.args[0] == "PUT"
        assert put_call.args[1] == "volume_syncs/sync1"
        body = put_call.kwargs.get("json_data", {})
        assert body["description"] == "Updated"
        assert body["workers"] == 8

    def test_update_with_sync_method_mapping(self, mock_client):
        """Test that update maps sync method names correctly."""
        mock_client._request.side_effect = [
            None,  # PUT
            [{"$key": "sync1", "sync_method": "ysync"}],  # GET
        ]
        manager = NASVolumeSyncManager(mock_client)

        manager.update("sync1", sync_method="vergesync")

        put_call = mock_client._request.call_args_list[0]
        body = put_call.kwargs.get("json_data", {})
        assert body["sync_method"] == "ysync"

    def test_update_with_destination_delete_mapping(self, mock_client):
        """Test that update maps destination delete names correctly."""
        mock_client._request.side_effect = [
            None,  # PUT
            [{"$key": "sync1"}],  # GET
        ]
        manager = NASVolumeSyncManager(mock_client)

        manager.update("sync1", destination_delete="delete_before")

        put_call = mock_client._request.call_args_list[0]
        body = put_call.kwargs.get("json_data", {})
        assert body["destination_delete"] == "delete-before"

    def test_update_no_changes(self, mock_client):
        """Test updating with no changes returns current sync."""
        mock_client._request.return_value = [{"$key": "sync1", "name": "TestSync"}]
        manager = NASVolumeSyncManager(mock_client)

        manager.update("sync1")

        # Should only call GET, not PUT
        assert mock_client._request.call_count == 1
        mock_client._request.assert_called_with(
            "GET",
            "volume_syncs",
            params={
                "filter": "id eq 'sync1'",
                "fields": manager._default_fields[0] + "," + ",".join(manager._default_fields[1:]),
            },
        )

    def test_delete(self, mock_client):
        """Test deleting a sync job."""
        mock_client._request.return_value = None
        manager = NASVolumeSyncManager(mock_client)

        manager.delete("sync1")

        mock_client._request.assert_called_once_with("DELETE", "volume_syncs/sync1")

    def test_enable(self, mock_client):
        """Test enabling a sync job."""
        mock_client._request.side_effect = [
            None,  # PUT
            [{"$key": "sync1", "enabled": True}],  # GET
        ]
        manager = NASVolumeSyncManager(mock_client)

        result = manager.enable("sync1")

        put_call = mock_client._request.call_args_list[0]
        body = put_call.kwargs.get("json_data", {})
        assert body["enabled"] is True
        assert result.get("enabled") is True

    def test_disable(self, mock_client):
        """Test disabling a sync job."""
        mock_client._request.side_effect = [
            None,  # PUT
            [{"$key": "sync1", "enabled": False}],  # GET
        ]
        manager = NASVolumeSyncManager(mock_client)

        result = manager.disable("sync1")

        put_call = mock_client._request.call_args_list[0]
        body = put_call.kwargs.get("json_data", {})
        assert body["enabled"] is False
        assert result.get("enabled") is False

    def test_start(self, mock_client):
        """Test starting a sync job."""
        mock_client._request.return_value = None
        manager = NASVolumeSyncManager(mock_client)

        manager.start("sync1")

        mock_client._request.assert_called_once_with(
            "POST",
            "volume_sync_actions",
            json_data={"sync": "sync1", "action": "start_sync"},
        )

    def test_stop(self, mock_client):
        """Test stopping a sync job."""
        mock_client._request.return_value = None
        manager = NASVolumeSyncManager(mock_client)

        manager.stop("sync1")

        mock_client._request.assert_called_once_with(
            "POST",
            "volume_sync_actions",
            json_data={"sync": "sync1", "action": "stop_sync"},
        )


class TestNASVolumeSync:
    """Tests for NASVolumeSync resource object."""

    def test_key_property(self, mock_client):
        """Test key property returns $key."""
        manager = NASVolumeSyncManager(mock_client)
        sync = NASVolumeSync({"$key": "sync123", "name": "Test"}, manager)

        assert sync.key == "sync123"

    def test_key_property_uses_id_fallback(self, mock_client):
        """Test key property falls back to id."""
        manager = NASVolumeSyncManager(mock_client)
        sync = NASVolumeSync({"id": "sync123", "name": "Test"}, manager)

        assert sync.key == "sync123"

    def test_key_property_raises_if_missing(self, mock_client):
        """Test key property raises ValueError if no key."""
        manager = NASVolumeSyncManager(mock_client)
        sync = NASVolumeSync({"name": "Test"}, manager)

        with pytest.raises(ValueError, match="no \\$key"):
            _ = sync.key

    def test_is_syncing_true(self, mock_client):
        """Test is_syncing returns True when syncing."""
        manager = NASVolumeSyncManager(mock_client)
        sync = NASVolumeSync({"$key": "sync1", "syncing": True}, manager)

        assert sync.is_syncing is True

    def test_is_syncing_false(self, mock_client):
        """Test is_syncing returns False when not syncing."""
        manager = NASVolumeSyncManager(mock_client)
        sync = NASVolumeSync({"$key": "sync1", "syncing": False}, manager)

        assert sync.is_syncing is False

    def test_service_key_property(self, mock_client):
        """Test service_key property."""
        manager = NASVolumeSyncManager(mock_client)
        sync = NASVolumeSync({"$key": "sync1", "service": 1}, manager)

        assert sync.service_key == 1

    def test_service_key_property_none(self, mock_client):
        """Test service_key property when service is None."""
        manager = NASVolumeSyncManager(mock_client)
        sync = NASVolumeSync({"$key": "sync1"}, manager)

        assert sync.service_key is None

    def test_source_volume_key_property(self, mock_client):
        """Test source_volume_key property."""
        manager = NASVolumeSyncManager(mock_client)
        sync = NASVolumeSync({"$key": "sync1", "source_volume": "vol123"}, manager)

        assert sync.source_volume_key == "vol123"

    def test_destination_volume_key_property(self, mock_client):
        """Test destination_volume_key property."""
        manager = NASVolumeSyncManager(mock_client)
        sync = NASVolumeSync({"$key": "sync1", "destination_volume": "vol456"}, manager)

        assert sync.destination_volume_key == "vol456"

    def test_sync_method_display(self, mock_client):
        """Test sync_method_display property."""
        manager = NASVolumeSyncManager(mock_client)

        sync_ysync = NASVolumeSync({"$key": "s1", "sync_method": "ysync"}, manager)
        assert sync_ysync.sync_method_display == "Verge.io sync"

        sync_rsync = NASVolumeSync({"$key": "s2", "sync_method": "rsync"}, manager)
        assert sync_rsync.sync_method_display == "rsync"

        sync_unknown = NASVolumeSync({"$key": "s3", "sync_method": "other"}, manager)
        assert sync_unknown.sync_method_display == "other"

    def test_destination_delete_display(self, mock_client):
        """Test destination_delete_display property."""
        manager = NASVolumeSyncManager(mock_client)

        sync = NASVolumeSync({"$key": "s1", "destination_delete": "never"}, manager)
        assert sync.destination_delete_display == "Never delete"

        sync = NASVolumeSync({"$key": "s2", "destination_delete": "delete"}, manager)
        assert sync.destination_delete_display == "Delete files from destination"

        sync = NASVolumeSync({"$key": "s3", "destination_delete": "delete-before"}, manager)
        assert sync.destination_delete_display == "Delete before transfer"

        sync = NASVolumeSync({"$key": "s4", "destination_delete": "delete-during"}, manager)
        assert sync.destination_delete_display == "Delete during transfer"

        sync = NASVolumeSync({"$key": "s5", "destination_delete": "delete-delay"}, manager)
        assert sync.destination_delete_display == "Delete after transfer (find during)"

        sync = NASVolumeSync({"$key": "s6", "destination_delete": "delete-after"}, manager)
        assert sync.destination_delete_display == "Delete after transfer"

    def test_status_display(self, mock_client):
        """Test status_display property."""
        manager = NASVolumeSyncManager(mock_client)

        statuses = {
            "complete": "Complete",
            "offline": "Offline",
            "syncing": "Syncing",
            "aborted": "Aborted",
            "error": "Error",
            "warning": "Warning",
            "unknown": "unknown",
        }

        for raw, display in statuses.items():
            sync = NASVolumeSync({"$key": "s1", "status": raw}, manager)
            assert sync.status_display == display

    def test_refresh(self, mock_client):
        """Test refresh method."""
        mock_client._request.return_value = [{"$key": "sync1", "name": "Updated"}]
        manager = NASVolumeSyncManager(mock_client)
        sync = NASVolumeSync({"$key": "sync1", "name": "Original"}, manager)

        refreshed = sync.refresh()

        assert refreshed.name == "Updated"

    def test_save(self, mock_client):
        """Test save method."""
        mock_client._request.side_effect = [
            None,  # PUT
            [{"$key": "sync1", "description": "New desc"}],  # GET
        ]
        manager = NASVolumeSyncManager(mock_client)
        sync = NASVolumeSync({"$key": "sync1", "name": "Test"}, manager)

        updated = sync.save(description="New desc")

        assert updated.get("description") == "New desc"

    def test_delete_method(self, mock_client):
        """Test delete method on object."""
        mock_client._request.return_value = None
        manager = NASVolumeSyncManager(mock_client)
        sync = NASVolumeSync({"$key": "sync1"}, manager)

        sync.delete()

        mock_client._request.assert_called_once_with("DELETE", "volume_syncs/sync1")

    def test_start_method(self, mock_client):
        """Test start method on object."""
        mock_client._request.return_value = None
        manager = NASVolumeSyncManager(mock_client)
        sync = NASVolumeSync({"$key": "sync1"}, manager)

        sync.start()

        mock_client._request.assert_called_once_with(
            "POST",
            "volume_sync_actions",
            json_data={"sync": "sync1", "action": "start_sync"},
        )

    def test_stop_method(self, mock_client):
        """Test stop method on object."""
        mock_client._request.return_value = None
        manager = NASVolumeSyncManager(mock_client)
        sync = NASVolumeSync({"$key": "sync1"}, manager)

        sync.stop()

        mock_client._request.assert_called_once_with(
            "POST",
            "volume_sync_actions",
            json_data={"sync": "sync1", "action": "stop_sync"},
        )


class TestSyncMethodMapping:
    """Tests for sync method name mapping."""

    def test_create_maps_vergesync(self, mock_client):
        """Test that 'vergesync' is mapped to 'ysync'."""
        mock_client._request.side_effect = [
            {"$key": "s1"},  # Create
            [{"$key": "s1"}],  # Get
        ]
        manager = NASVolumeSyncManager(mock_client)

        manager.create(
            "Test", service=1, source_volume="v1", destination_volume="v2", sync_method="vergesync"
        )

        body = mock_client._request.call_args_list[0].kwargs.get("json_data", {})
        assert body["sync_method"] == "ysync"

    def test_create_maps_verge_sync(self, mock_client):
        """Test that 'verge_sync' is mapped to 'ysync'."""
        mock_client._request.side_effect = [
            {"$key": "s1"},  # Create
            [{"$key": "s1"}],  # Get
        ]
        manager = NASVolumeSyncManager(mock_client)

        manager.create(
            "Test", service=1, source_volume="v1", destination_volume="v2", sync_method="verge_sync"
        )

        body = mock_client._request.call_args_list[0].kwargs.get("json_data", {})
        assert body["sync_method"] == "ysync"

    def test_create_preserves_rsync(self, mock_client):
        """Test that 'rsync' is preserved."""
        mock_client._request.side_effect = [
            {"$key": "s1"},  # Create
            [{"$key": "s1"}],  # Get
        ]
        manager = NASVolumeSyncManager(mock_client)

        manager.create(
            "Test", service=1, source_volume="v1", destination_volume="v2", sync_method="rsync"
        )

        body = mock_client._request.call_args_list[0].kwargs.get("json_data", {})
        assert body["sync_method"] == "rsync"


class TestDestinationDeleteMapping:
    """Tests for destination delete mode mapping."""

    def test_create_maps_delete_underscore_variations(self, mock_client):
        """Test that underscore variations are mapped correctly."""
        mappings = [
            ("delete_before", "delete-before"),
            ("deletebefore", "delete-before"),
            ("delete_during", "delete-during"),
            ("deleteduring", "delete-during"),
            ("delete_delay", "delete-delay"),
            ("deletedelay", "delete-delay"),
            ("delete_after", "delete-after"),
            ("deleteafter", "delete-after"),
        ]

        for input_val, expected in mappings:
            mock_client._request.reset_mock()
            mock_client._request.side_effect = [
                {"$key": "s1"},  # Create
                [{"$key": "s1"}],  # Get
            ]
            manager = NASVolumeSyncManager(mock_client)

            manager.create(
                "Test",
                service=1,
                source_volume="v1",
                destination_volume="v2",
                destination_delete=input_val,
            )

            body = mock_client._request.call_args_list[0].kwargs.get("json_data", {})
            assert body["destination_delete"] == expected, f"Failed for {input_val}"
