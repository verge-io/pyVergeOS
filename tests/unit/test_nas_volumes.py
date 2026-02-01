"""Unit tests for NAS volume operations."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from pyvergeos import VergeClient
from pyvergeos.exceptions import NotFoundError
from pyvergeos.resources.nas_volumes import (
    NASVolume,
    NASVolumeManager,
    NASVolumeSnapshot,
    NASVolumeSnapshotManager,
)


class TestNASVolumeManager:
    """Unit tests for NASVolumeManager."""

    def test_list_volumes(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test listing NAS volumes."""
        mock_session.request.return_value.json.return_value = [
            {
                "$key": "abc123def456789012345678901234567890abcd",
                "name": "FileShare",
                "maxsize": 536870912000,
                "enabled": True,
                "service": 1,
            },
            {
                "$key": "def456abc789012345678901234567890abcdef",
                "name": "Archive",
                "maxsize": 1073741824000,
                "enabled": True,
                "service": 1,
            },
        ]

        volumes = mock_client.nas_volumes.list()

        assert len(volumes) == 2
        assert volumes[0].name == "FileShare"
        assert volumes[1].name == "Archive"

    def test_list_volumes_empty(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test listing when no volumes exist."""
        mock_session.request.return_value.json.return_value = None

        volumes = mock_client.nas_volumes.list()

        assert volumes == []

    def test_list_volumes_by_enabled(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test filtering volumes by enabled state."""
        mock_session.request.return_value.json.return_value = []

        mock_client.nas_volumes.list(enabled=True)

        call_args = mock_session.request.call_args
        params = call_args.kwargs.get("params", {})
        assert "enabled eq 1" in params.get("filter", "")

    def test_list_volumes_by_fs_type(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test filtering volumes by filesystem type."""
        mock_session.request.return_value.json.return_value = []

        mock_client.nas_volumes.list(fs_type="ext4")

        call_args = mock_session.request.call_args
        params = call_args.kwargs.get("params", {})
        assert "fs_type eq 'ext4'" in params.get("filter", "")

    def test_list_volumes_by_service_key(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test filtering volumes by service key."""
        mock_session.request.return_value.json.return_value = []

        mock_client.nas_volumes.list(service=1)

        call_args = mock_session.request.call_args
        params = call_args.kwargs.get("params", {})
        assert "service eq 1" in params.get("filter", "")

    def test_list_volumes_by_service_name(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test filtering volumes by service name."""
        mock_session.request.return_value.json.side_effect = [
            [{"$key": 1, "name": "NAS01"}],  # Service lookup
            [],  # Volume list
        ]

        mock_client.nas_volumes.list(service="NAS01")

        # Verify the service lookup was made
        get_calls = [
            call
            for call in mock_session.request.call_args_list
            if call.kwargs.get("method") == "GET"
        ]
        assert len(get_calls) >= 1

    def test_get_volume_by_key(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test getting a volume by key."""
        vol_key = "abc123def456789012345678901234567890abcd"
        mock_session.request.return_value.json.return_value = [
            {
                "$key": vol_key,
                "name": "FileShare",
                "maxsize": 536870912000,
            }
        ]

        volume = mock_client.nas_volumes.get(vol_key)

        assert volume.key == vol_key
        assert volume.name == "FileShare"

    def test_get_volume_by_name(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test getting a volume by name."""
        mock_session.request.return_value.json.return_value = [
            {
                "$key": "abc123def456789012345678901234567890abcd",
                "name": "Archive",
                "maxsize": 1073741824000,
            }
        ]

        volume = mock_client.nas_volumes.get(name="Archive")

        assert volume.name == "Archive"

    def test_get_volume_not_found_by_key(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test NotFoundError when volume not found by key."""
        mock_session.request.return_value.json.return_value = []

        with pytest.raises(NotFoundError):
            mock_client.nas_volumes.get("nonexistent123456789012345678901234")

    def test_get_volume_not_found_by_name(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test NotFoundError when volume not found by name."""
        mock_session.request.return_value.json.return_value = []

        with pytest.raises(NotFoundError):
            mock_client.nas_volumes.get(name="nonexistent")

    def test_get_volume_requires_key_or_name(self, mock_client: VergeClient) -> None:
        """Test ValueError when neither key nor name provided."""
        with pytest.raises(ValueError, match="Either key or name must be provided"):
            mock_client.nas_volumes.get()

    def test_create_volume(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test creating a volume."""
        vol_key = "newvol123456789012345678901234567890abcd"
        mock_session.request.return_value.json.side_effect = [
            [{"$key": 1, "name": "NAS01"}],  # Service lookup
            {"$key": vol_key, "name": "NewVolume"},  # POST response
            [{"$key": vol_key, "name": "NewVolume", "maxsize": 536870912000}],  # GET
        ]

        volume = mock_client.nas_volumes.create(
            name="NewVolume",
            service="NAS01",
            size_gb=500,
            tier=1,
        )

        assert volume.name == "NewVolume"
        post_calls = [
            call
            for call in mock_session.request.call_args_list
            if call.kwargs.get("method") == "POST"
        ]
        assert len(post_calls) == 1
        body = post_calls[0].kwargs.get("json", {})
        assert body["name"] == "NewVolume"
        assert body["maxsize"] == 500 * 1073741824
        assert body["preferred_tier"] == "1"

    def test_create_volume_service_not_found(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test ValueError when service not found."""
        mock_session.request.return_value.json.return_value = []

        with pytest.raises(ValueError, match="not found"):
            mock_client.nas_volumes.create(
                name="NewVolume",
                service="NonexistentNAS",
                size_gb=500,
            )

    def test_update_volume(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test updating a volume."""
        vol_key = "abc123def456789012345678901234567890abcd"
        mock_session.request.return_value.json.side_effect = [
            {},  # PUT response
            [{"$key": vol_key, "name": "FileShare", "description": "Updated"}],
        ]

        volume = mock_client.nas_volumes.update(vol_key, description="Updated")

        put_calls = [
            call
            for call in mock_session.request.call_args_list
            if call.kwargs.get("method") == "PUT"
        ]
        assert len(put_calls) == 1
        assert volume.get("description") == "Updated"

    def test_update_volume_size(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test updating volume size."""
        vol_key = "abc123def456789012345678901234567890abcd"
        mock_session.request.return_value.json.side_effect = [
            {},
            [{"$key": vol_key, "maxsize": 1073741824000}],
        ]

        mock_client.nas_volumes.update(vol_key, size_gb=1000)

        put_calls = [
            call
            for call in mock_session.request.call_args_list
            if call.kwargs.get("method") == "PUT"
        ]
        body = put_calls[0].kwargs.get("json", {})
        assert body["maxsize"] == 1000 * 1073741824

    def test_delete_volume(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test deleting a volume."""
        vol_key = "abc123def456789012345678901234567890abcd"
        mock_session.request.return_value.status_code = 204
        mock_session.request.return_value.text = ""

        mock_client.nas_volumes.delete(vol_key)

        call_args = mock_session.request.call_args
        assert call_args.kwargs["method"] == "DELETE"
        assert vol_key in call_args.kwargs["url"]

    def test_enable_volume(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test enabling a volume."""
        vol_key = "abc123def456789012345678901234567890abcd"
        mock_session.request.return_value.json.side_effect = [
            {},
            [{"$key": vol_key, "enabled": True}],
        ]

        _ = mock_client.nas_volumes.enable(vol_key)

        put_calls = [
            call
            for call in mock_session.request.call_args_list
            if call.kwargs.get("method") == "PUT"
        ]
        body = put_calls[0].kwargs.get("json", {})
        assert body["enabled"] is True

    def test_disable_volume(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test disabling a volume."""
        vol_key = "abc123def456789012345678901234567890abcd"
        mock_session.request.return_value.json.side_effect = [
            {},
            [{"$key": vol_key, "enabled": False}],
        ]

        _ = mock_client.nas_volumes.disable(vol_key)

        put_calls = [
            call
            for call in mock_session.request.call_args_list
            if call.kwargs.get("method") == "PUT"
        ]
        body = put_calls[0].kwargs.get("json", {})
        assert body["enabled"] is False

    def test_reset_volume(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test resetting a volume."""
        vol_key = "abc123def456789012345678901234567890abcd"
        mock_session.request.return_value.json.return_value = {"task": 123}

        result = mock_client.nas_volumes.reset(vol_key)

        assert result == {"task": 123}
        put_calls = [
            call
            for call in mock_session.request.call_args_list
            if call.kwargs.get("method") == "PUT"
        ]
        assert any("action=reset" in call.kwargs.get("url", "") for call in put_calls)

    def test_snapshots_manager(self, mock_client: VergeClient) -> None:
        """Test getting a snapshot manager for a volume."""
        vol_key = "abc123def456789012345678901234567890abcd"

        manager = mock_client.nas_volumes.snapshots(vol_key)

        assert isinstance(manager, NASVolumeSnapshotManager)
        assert manager._volume_key == vol_key


class TestNASVolume:
    """Unit tests for NASVolume object."""

    @pytest.fixture
    def volume_data(self) -> dict[str, Any]:
        """Sample NAS volume data."""
        return {
            "$key": "abc123def456789012345678901234567890abcd",
            "id": "abc123def456789012345678901234567890abcd",
            "name": "FileShare",
            "description": "Main file share",
            "enabled": True,
            "maxsize": 536870912000,  # 500 GB
            "used_bytes": 107374182400,  # 100 GB
            "allocated_bytes": 214748364800,  # 200 GB
            "preferred_tier": "1",
            "fs_type": "ext4",
            "read_only": False,
            "discard": True,
            "owner_user": "root",
            "owner_group": "root",
            "encrypt": False,
            "automount_snapshots": True,
            "is_snapshot": False,
            "service": 1,
            "mounted": True,
            "mount_status": "mounted",
        }

    @pytest.fixture
    def mock_manager(self, mock_client: VergeClient) -> NASVolumeManager:
        """Create a mock NAS volume manager."""
        return mock_client.nas_volumes

    def test_volume_properties(
        self, volume_data: dict[str, Any], mock_manager: NASVolumeManager
    ) -> None:
        """Test NASVolume property accessors."""
        volume = NASVolume(volume_data, mock_manager)

        assert volume.key == "abc123def456789012345678901234567890abcd"
        assert volume.name == "FileShare"
        assert volume.get("description") == "Main file share"
        assert volume.get("enabled") is True
        assert volume.get("fs_type") == "ext4"
        assert volume.service_key == 1
        assert volume.is_mounted is True

    def test_volume_size_properties(
        self, volume_data: dict[str, Any], mock_manager: NASVolumeManager
    ) -> None:
        """Test NASVolume size property calculations."""
        volume = NASVolume(volume_data, mock_manager)

        assert volume.max_size_gb == 500.0
        assert volume.used_gb == 100.0
        assert volume.allocated_gb == 200.0

    def test_volume_size_properties_zero(self, mock_manager: NASVolumeManager) -> None:
        """Test NASVolume size properties when zero."""
        volume = NASVolume({"$key": "abc123"}, mock_manager)

        assert volume.max_size_gb == 0
        assert volume.used_gb == 0
        assert volume.allocated_gb == 0

    def test_volume_is_mounted_by_status(
        self, volume_data: dict[str, Any], mock_manager: NASVolumeManager
    ) -> None:
        """Test is_mounted using mount_status."""
        volume_data["mounted"] = False
        volume_data["mount_status"] = "mounted"
        volume = NASVolume(volume_data, mock_manager)

        assert volume.is_mounted is True

    def test_volume_is_mounted_false(self, mock_manager: NASVolumeManager) -> None:
        """Test is_mounted when volume is not mounted."""
        volume = NASVolume(
            {"$key": "abc123", "mounted": False, "mount_status": "unmounted"},
            mock_manager,
        )

        assert volume.is_mounted is False

    def test_volume_service_key_none(self, mock_manager: NASVolumeManager) -> None:
        """Test service_key when not set."""
        volume = NASVolume({"$key": "abc123"}, mock_manager)

        assert volume.service_key is None

    def test_volume_key_raises_without_key(self, mock_manager: NASVolumeManager) -> None:
        """Test that key property raises when no $key."""
        volume = NASVolume({}, mock_manager)

        with pytest.raises(ValueError, match="no \\$key"):
            _ = volume.key

    def test_volume_refresh(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test NASVolume refresh method."""
        vol_key = "abc123def456789012345678901234567890abcd"
        mock_session.request.return_value.json.return_value = [
            {"$key": vol_key, "name": "FileShare-updated"}
        ]

        volume = NASVolume({"$key": vol_key, "name": "FileShare"}, mock_client.nas_volumes)

        refreshed = volume.refresh()

        assert refreshed.name == "FileShare-updated"

    def test_volume_save(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test NASVolume save method."""
        vol_key = "abc123def456789012345678901234567890abcd"
        mock_session.request.return_value.json.side_effect = [
            {},
            [{"$key": vol_key, "name": "FileShare", "description": "New desc"}],
        ]

        volume = NASVolume({"$key": vol_key}, mock_client.nas_volumes)

        updated = volume.save(description="New desc")

        assert updated.get("description") == "New desc"

    def test_volume_delete(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test NASVolume delete method."""
        vol_key = "abc123def456789012345678901234567890abcd"
        mock_session.request.return_value.status_code = 204
        mock_session.request.return_value.text = ""

        volume = NASVolume({"$key": vol_key}, mock_client.nas_volumes)

        volume.delete()

        delete_calls = [
            call
            for call in mock_session.request.call_args_list
            if call.kwargs.get("method") == "DELETE"
        ]
        assert len(delete_calls) == 1


class TestNASVolumeSnapshotManager:
    """Unit tests for NASVolumeSnapshotManager."""

    def test_list_snapshots(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test listing volume snapshots."""
        mock_session.request.return_value.json.return_value = [
            {
                "$key": 1,
                "name": "daily-backup",
                "volume": "abc123",
                "created": 1704067200,
                "expires_type": "date",
            },
            {
                "$key": 2,
                "name": "pre-update",
                "volume": "abc123",
                "created": 1704153600,
                "expires_type": "never",
            },
        ]

        vol_key = "abc123def456789012345678901234567890abcd"
        snapshots = mock_client.nas_volumes.snapshots(vol_key).list()

        assert len(snapshots) == 2
        assert snapshots[0].name == "daily-backup"
        assert snapshots[1].name == "pre-update"

    def test_list_snapshots_empty(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test listing when no snapshots exist."""
        mock_session.request.return_value.json.return_value = None

        vol_key = "abc123def456789012345678901234567890abcd"
        snapshots = mock_client.nas_volumes.snapshots(vol_key).list()

        assert snapshots == []

    def test_list_snapshots_scoped(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test that scoped manager filters by volume."""
        mock_session.request.return_value.json.return_value = []

        vol_key = "abc123def456789012345678901234567890abcd"
        mock_client.nas_volumes.snapshots(vol_key).list()

        call_args = mock_session.request.call_args
        params = call_args.kwargs.get("params", {})
        assert f"volume eq '{vol_key}'" in params.get("filter", "")

    def test_get_snapshot_by_key(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test getting a snapshot by key."""
        mock_session.request.return_value.json.return_value = {
            "$key": 1,
            "name": "daily-backup",
            "volume": "abc123",
        }

        vol_key = "abc123def456789012345678901234567890abcd"
        snapshot = mock_client.nas_volumes.snapshots(vol_key).get(1)

        assert snapshot.key == 1
        assert snapshot.name == "daily-backup"

    def test_get_snapshot_by_name(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test getting a snapshot by name."""
        mock_session.request.return_value.json.return_value = [
            {
                "$key": 2,
                "name": "pre-update",
                "volume": "abc123",
            }
        ]

        vol_key = "abc123def456789012345678901234567890abcd"
        snapshot = mock_client.nas_volumes.snapshots(vol_key).get(name="pre-update")

        assert snapshot.name == "pre-update"

    def test_get_snapshot_not_found(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test NotFoundError when snapshot not found."""
        mock_session.request.return_value.json.return_value = None

        vol_key = "abc123def456789012345678901234567890abcd"
        with pytest.raises(NotFoundError):
            mock_client.nas_volumes.snapshots(vol_key).get(999)

    def test_create_snapshot(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test creating a snapshot."""
        mock_session.request.return_value.json.side_effect = [
            {"$key": 10, "name": "new-snap"},
            {"$key": 10, "name": "new-snap", "volume": "abc123"},
        ]

        vol_key = "abc123def456789012345678901234567890abcd"
        snapshot = mock_client.nas_volumes.snapshots(vol_key).create(
            "new-snap",
            description="Test snapshot",
            expires_days=7,
        )

        assert snapshot.name == "new-snap"
        post_calls = [
            call
            for call in mock_session.request.call_args_list
            if call.kwargs.get("method") == "POST"
        ]
        body = post_calls[0].kwargs.get("json", {})
        assert body["name"] == "new-snap"
        assert body["volume"] == vol_key
        assert body["description"] == "Test snapshot"
        assert body["expires_type"] == "date"

    def test_create_snapshot_never_expires(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test creating a snapshot that never expires."""
        mock_session.request.return_value.json.side_effect = [
            {"$key": 11, "name": "permanent"},
            {"$key": 11, "name": "permanent"},
        ]

        vol_key = "abc123def456789012345678901234567890abcd"
        mock_client.nas_volumes.snapshots(vol_key).create("permanent", never_expires=True)

        post_calls = [
            call
            for call in mock_session.request.call_args_list
            if call.kwargs.get("method") == "POST"
        ]
        body = post_calls[0].kwargs.get("json", {})
        assert body["expires_type"] == "never"
        assert body["expires"] == 0

    def test_create_snapshot_requires_volume(self, mock_client: VergeClient) -> None:
        """Test ValueError when volume not specified for unscoped manager."""
        manager = NASVolumeSnapshotManager(mock_client)  # No volume_key

        with pytest.raises(ValueError, match="Volume key is required"):
            manager.create("snapshot")

    def test_delete_snapshot(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test deleting a snapshot."""
        mock_session.request.return_value.status_code = 204
        mock_session.request.return_value.text = ""

        vol_key = "abc123def456789012345678901234567890abcd"
        mock_client.nas_volumes.snapshots(vol_key).delete(1)

        call_args = mock_session.request.call_args
        assert call_args.kwargs["method"] == "DELETE"
        assert "volume_snapshots/1" in call_args.kwargs["url"]


class TestNASVolumeSnapshot:
    """Unit tests for NASVolumeSnapshot object."""

    @pytest.fixture
    def snapshot_data(self) -> dict[str, Any]:
        """Sample volume snapshot data."""
        return {
            "$key": 1,
            "name": "daily-backup",
            "description": "Daily backup snapshot",
            "volume": "abc123def456789012345678901234567890abcd",
            "volume_name": "FileShare",
            "created": 1704067200,
            "expires": 1704672000,
            "expires_type": "date",
            "enabled": True,
            "created_manually": False,
            "quiesce": True,
        }

    @pytest.fixture
    def mock_manager(self, mock_client: VergeClient) -> NASVolumeSnapshotManager:
        """Create a mock snapshot manager."""
        return NASVolumeSnapshotManager(mock_client)

    def test_snapshot_properties(
        self, snapshot_data: dict[str, Any], mock_manager: NASVolumeSnapshotManager
    ) -> None:
        """Test NASVolumeSnapshot property accessors."""
        snapshot = NASVolumeSnapshot(snapshot_data, mock_manager)

        assert snapshot.key == 1
        assert snapshot.name == "daily-backup"
        assert snapshot.volume_key == "abc123def456789012345678901234567890abcd"
        assert snapshot.get("created_manually") is False
        assert snapshot.get("quiesce") is True

    def test_snapshot_never_expires_false(
        self, snapshot_data: dict[str, Any], mock_manager: NASVolumeSnapshotManager
    ) -> None:
        """Test never_expires when snapshot has expiration."""
        snapshot = NASVolumeSnapshot(snapshot_data, mock_manager)

        assert snapshot.never_expires is False

    def test_snapshot_never_expires_true_by_type(
        self, snapshot_data: dict[str, Any], mock_manager: NASVolumeSnapshotManager
    ) -> None:
        """Test never_expires when expires_type is never."""
        snapshot_data["expires_type"] = "never"
        snapshot = NASVolumeSnapshot(snapshot_data, mock_manager)

        assert snapshot.never_expires is True

    def test_snapshot_never_expires_true_by_zero(
        self, snapshot_data: dict[str, Any], mock_manager: NASVolumeSnapshotManager
    ) -> None:
        """Test never_expires when expires is 0."""
        snapshot_data["expires"] = 0
        snapshot = NASVolumeSnapshot(snapshot_data, mock_manager)

        assert snapshot.never_expires is True

    def test_snapshot_volume_key_none(self, mock_manager: NASVolumeSnapshotManager) -> None:
        """Test volume_key when not set."""
        snapshot = NASVolumeSnapshot({"$key": 1}, mock_manager)

        assert snapshot.volume_key is None
