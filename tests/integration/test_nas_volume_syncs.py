"""Integration tests for NAS volume sync operations.

These tests require a live VergeOS system with:
- A running NAS service
- At least 2 volumes for sync testing

Run with: pytest tests/integration/test_nas_volume_syncs.py -v
"""

import pytest

from pyvergeos import VergeClient
from pyvergeos.exceptions import NotFoundError, ValidationError


@pytest.fixture(scope="module")
def client():
    """Create a live client for integration tests.

    Requires environment variables:
        VERGE_HOST, VERGE_USERNAME, VERGE_PASSWORD, VERGE_VERIFY_SSL
    """
    client = VergeClient.from_env()
    yield client
    client.disconnect()


@pytest.fixture(scope="module")
def nas_service(client):
    """Get an available NAS service with at least 2 volumes."""
    services = client.nas_services.list()
    if not services:
        pytest.skip("No NAS services available")
    # Find a service that isn't a snapshot and has at least 2 volumes
    for svc in services:
        if "snap_" not in svc.name.lower() and svc.volume_count >= 2:
            return svc
    # Fallback: any service with at least 2 volumes
    for svc in services:
        if svc.volume_count >= 2:
            return svc
    pytest.skip("No NAS service with at least 2 volumes found")


@pytest.fixture(scope="module")
def volumes(client, nas_service):
    """Get at least 2 volumes for sync testing."""
    volumes = client.nas_volumes.list(service=nas_service.key)
    if len(volumes) < 2:
        pytest.skip("Need at least 2 volumes for sync testing")
    return volumes


class TestNASVolumeSyncList:
    """Tests for listing volume syncs."""

    def test_list_all_syncs(self, client):
        """Test listing all volume syncs."""
        syncs = client.volume_syncs.list()
        assert isinstance(syncs, list)
        # Just verify we can list - may be empty or have syncs

    def test_list_returns_sync_objects(self, client):
        """Test that list returns NASVolumeSync objects."""
        syncs = client.volume_syncs.list()
        if syncs:
            from pyvergeos.resources.nas_volume_syncs import NASVolumeSync

            assert all(isinstance(sync, NASVolumeSync) for sync in syncs)

    def test_list_with_service_filter(self, client, nas_service):
        """Test listing syncs filtered by service."""
        syncs = client.volume_syncs.list(service=nas_service.key)
        assert isinstance(syncs, list)
        # All returned syncs should belong to the service
        for sync in syncs:
            assert sync.service_key == nas_service.key


class TestNASVolumeSyncGet:
    """Tests for getting volume syncs."""

    def test_get_existing_sync_by_key(self, client):
        """Test getting an existing sync by key."""
        syncs = client.volume_syncs.list(limit=1)
        if not syncs:
            pytest.skip("No volume syncs available for testing")

        sync = client.volume_syncs.get(syncs[0].key)
        assert sync.key == syncs[0].key
        assert sync.name == syncs[0].name

    def test_get_existing_sync_by_name(self, client):
        """Test getting an existing sync by name."""
        syncs = client.volume_syncs.list(limit=1)
        if not syncs:
            pytest.skip("No volume syncs available for testing")

        sync = client.volume_syncs.get(name=syncs[0].name)
        assert sync.key == syncs[0].key
        assert sync.name == syncs[0].name

    def test_get_nonexistent_sync_raises(self, client):
        """Test that getting a nonexistent sync raises NotFoundError."""
        with pytest.raises(NotFoundError):
            client.volume_syncs.get("nonexistent_key_12345")

    def test_get_nonexistent_sync_by_name_raises(self, client):
        """Test that getting a nonexistent sync by name raises NotFoundError."""
        with pytest.raises(NotFoundError):
            client.volume_syncs.get(name="NonexistentSyncName12345")


class TestNASVolumeSyncCRUD:
    """Tests for create, update, delete operations."""

    def test_create_sync(self, client, nas_service, volumes):
        """Test creating a new volume sync."""
        source_vol = volumes[0]
        dest_vol = volumes[1]

        sync = client.volume_syncs.create(
            name="pytest-sync-001",
            service=nas_service.key,
            source_volume=source_vol.key,
            destination_volume=dest_vol.key,
            description="Created by pytest integration test",
            workers=4,
        )

        try:
            assert sync.name == "pytest-sync-001"
            assert sync.get("description") == "Created by pytest integration test"
            assert sync.service_key == nas_service.key
            assert sync.source_volume_key == source_vol.key
            assert sync.destination_volume_key == dest_vol.key
            assert sync.get("workers") == 4
        finally:
            # Cleanup
            client.volume_syncs.delete(sync.key)

    def test_create_sync_with_options(self, client, nas_service, volumes):
        """Test creating a sync with various options."""
        source_vol = volumes[0]
        dest_vol = volumes[1]

        sync = client.volume_syncs.create(
            name="pytest-sync-002",
            service=nas_service.key,
            source_volume=source_vol.key,
            destination_volume=dest_vol.key,
            sync_method="rsync",
            destination_delete="delete-after",
            workers=8,
            preserve_acls=False,
            preserve_xattrs=False,
            enabled=False,
        )

        try:
            assert sync.name == "pytest-sync-002"
            assert sync.get("sync_method") == "rsync"
            assert sync.get("destination_delete") == "delete-after"
            assert sync.get("workers") == 8
            assert sync.get("preserve_ACLs") is False
            assert sync.get("preserve_xattrs") is False
            assert sync.get("enabled") is False
        finally:
            # Cleanup
            client.volume_syncs.delete(sync.key)

    def test_update_sync(self, client, nas_service, volumes):
        """Test updating a volume sync."""
        source_vol = volumes[0]
        dest_vol = volumes[1]

        sync = client.volume_syncs.create(
            name="pytest-sync-003",
            service=nas_service.key,
            source_volume=source_vol.key,
            destination_volume=dest_vol.key,
            workers=4,
        )

        try:
            # Update the sync
            updated = client.volume_syncs.update(
                sync.key,
                description="Updated description",
                workers=6,
            )

            assert updated.get("description") == "Updated description"
            assert updated.get("workers") == 6
        finally:
            # Cleanup
            client.volume_syncs.delete(sync.key)

    def test_enable_disable_sync(self, client, nas_service, volumes):
        """Test enabling and disabling a sync."""
        source_vol = volumes[0]
        dest_vol = volumes[1]

        sync = client.volume_syncs.create(
            name="pytest-sync-004",
            service=nas_service.key,
            source_volume=source_vol.key,
            destination_volume=dest_vol.key,
            enabled=True,
        )

        try:
            # Disable
            disabled = client.volume_syncs.disable(sync.key)
            assert disabled.get("enabled") is False

            # Enable
            enabled = client.volume_syncs.enable(sync.key)
            assert enabled.get("enabled") is True
        finally:
            # Cleanup
            client.volume_syncs.delete(sync.key)

    def test_delete_sync(self, client, nas_service, volumes):
        """Test deleting a volume sync."""
        source_vol = volumes[0]
        dest_vol = volumes[1]

        sync = client.volume_syncs.create(
            name="pytest-sync-005",
            service=nas_service.key,
            source_volume=source_vol.key,
            destination_volume=dest_vol.key,
        )

        # Delete
        client.volume_syncs.delete(sync.key)

        # Verify deleted
        with pytest.raises(NotFoundError):
            client.volume_syncs.get(sync.key)


class TestNASVolumeSyncActions:
    """Tests for start/stop actions."""

    def test_start_sync_api_call(self, client, nas_service, volumes):
        """Test that start() makes the correct API call."""
        source_vol = volumes[0]
        dest_vol = volumes[1]

        sync = client.volume_syncs.create(
            name="pytest-sync-006",
            service=nas_service.key,
            source_volume=source_vol.key,
            destination_volume=dest_vol.key,
        )

        try:
            # Start should not raise an error
            # Note: Sync may not actually run if NAS service is offline
            client.volume_syncs.start(sync.key)
            # If we get here, the API call succeeded
        finally:
            # Cleanup
            client.volume_syncs.delete(sync.key)

    def test_stop_sync_when_not_running(self, client, nas_service, volumes):
        """Test that stop() raises ValidationError when sync not running."""
        source_vol = volumes[0]
        dest_vol = volumes[1]

        sync = client.volume_syncs.create(
            name="pytest-sync-007",
            service=nas_service.key,
            source_volume=source_vol.key,
            destination_volume=dest_vol.key,
        )

        try:
            # Stop should raise ValidationError if sync isn't running
            with pytest.raises(ValidationError):
                client.volume_syncs.stop(sync.key)
        finally:
            # Cleanup
            client.volume_syncs.delete(sync.key)


class TestNASVolumeSyncObjectMethods:
    """Tests for methods on NASVolumeSync objects."""

    def test_refresh(self, client, nas_service, volumes):
        """Test refreshing a sync object."""
        source_vol = volumes[0]
        dest_vol = volumes[1]

        sync = client.volume_syncs.create(
            name="pytest-sync-008",
            service=nas_service.key,
            source_volume=source_vol.key,
            destination_volume=dest_vol.key,
            description="Original",
        )

        try:
            # Update via manager
            client.volume_syncs.update(sync.key, description="Updated")

            # Refresh and check
            refreshed = sync.refresh()
            assert refreshed.get("description") == "Updated"
        finally:
            # Cleanup
            client.volume_syncs.delete(sync.key)

    def test_save(self, client, nas_service, volumes):
        """Test saving changes via object method."""
        source_vol = volumes[0]
        dest_vol = volumes[1]

        sync = client.volume_syncs.create(
            name="pytest-sync-009",
            service=nas_service.key,
            source_volume=source_vol.key,
            destination_volume=dest_vol.key,
        )

        try:
            updated = sync.save(description="Saved via object method")
            assert updated.get("description") == "Saved via object method"
        finally:
            # Cleanup
            client.volume_syncs.delete(sync.key)

    def test_object_delete(self, client, nas_service, volumes):
        """Test deleting via object method."""
        source_vol = volumes[0]
        dest_vol = volumes[1]

        sync = client.volume_syncs.create(
            name="pytest-sync-010",
            service=nas_service.key,
            source_volume=source_vol.key,
            destination_volume=dest_vol.key,
        )

        key = sync.key
        sync.delete()

        # Verify deleted
        with pytest.raises(NotFoundError):
            client.volume_syncs.get(key)


class TestNASVolumeSyncProperties:
    """Tests for NASVolumeSync object properties."""

    def test_sync_method_display(self, client, nas_service, volumes):
        """Test sync_method_display property."""
        source_vol = volumes[0]
        dest_vol = volumes[1]

        sync = client.volume_syncs.create(
            name="pytest-sync-011",
            service=nas_service.key,
            source_volume=source_vol.key,
            destination_volume=dest_vol.key,
            sync_method="ysync",
        )

        try:
            assert sync.sync_method_display == "Verge.io sync"
        finally:
            client.volume_syncs.delete(sync.key)

    def test_destination_delete_display(self, client, nas_service, volumes):
        """Test destination_delete_display property."""
        source_vol = volumes[0]
        dest_vol = volumes[1]

        sync = client.volume_syncs.create(
            name="pytest-sync-012",
            service=nas_service.key,
            source_volume=source_vol.key,
            destination_volume=dest_vol.key,
            destination_delete="never",
        )

        try:
            assert sync.destination_delete_display == "Never delete"
        finally:
            client.volume_syncs.delete(sync.key)

    def test_status_display(self, client):
        """Test status_display property on existing sync."""
        syncs = client.volume_syncs.list(limit=1)
        if not syncs:
            pytest.skip("No volume syncs available")

        sync = syncs[0]
        # Just verify we get a string back
        assert isinstance(sync.status_display, str)
