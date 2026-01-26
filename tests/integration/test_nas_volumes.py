"""Integration tests for NASVolumeManager and NASVolumeSnapshotManager.

These tests require a live VergeOS system with at least one NAS service.
Configure with environment variables:
    VERGE_HOST, VERGE_USERNAME, VERGE_PASSWORD, VERGE_VERIFY_SSL
"""

from __future__ import annotations

import contextlib
import os

import pytest

from pyvergeos import VergeClient
from pyvergeos.exceptions import NotFoundError
from pyvergeos.resources.nas_services import NASService
from pyvergeos.resources.nas_volumes import NASVolume

# Skip all tests in this module if not running integration tests
pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def client() -> VergeClient:
    """Create a connected client for the test module."""
    if not os.environ.get("VERGE_HOST"):
        pytest.skip("VERGE_HOST not set")

    client = VergeClient.from_env()
    client.connect()
    yield client
    client.disconnect()


@pytest.fixture(scope="module")
def test_service(client: VergeClient) -> NASService:
    """Get a NAS service to test volumes on.

    Uses the first available NAS service.
    """
    services = client.nas_services.list()
    if not services:
        pytest.skip("No NAS services available for volume testing")
    return services[0]


@pytest.fixture
def cleanup_volumes(client: VergeClient):
    """Fixture to track and cleanup test volumes."""
    created_keys: list[str] = []

    yield created_keys

    # Cleanup any volumes we created (also removes snapshots)
    for key in created_keys:
        try:
            # First delete any snapshots
            snap_mgr = client.nas_volumes.snapshots(key)
            for snap in snap_mgr.list():
                with contextlib.suppress(NotFoundError):
                    snap_mgr.delete(snap.key)
            # Then delete the volume
            client.nas_volumes.delete(key)
        except NotFoundError:
            pass  # Already deleted


class TestNASVolumeManagerIntegration:
    """Integration tests for NASVolumeManager."""

    def test_list_volumes(self, client: VergeClient) -> None:
        """Test listing all NAS volumes."""
        volumes = client.nas_volumes.list()

        assert isinstance(volumes, list)
        for vol in volumes:
            assert isinstance(vol, NASVolume)
            assert vol.key is not None
            assert vol.name is not None

    def test_list_volumes_with_filter(
        self, client: VergeClient, test_service: NASService, cleanup_volumes: list[str]
    ) -> None:
        """Test listing volumes with various filters."""
        # Create a test volume first
        vol = client.nas_volumes.create(
            name="pytest-vol-filter",
            service=test_service.key,
            size_gb=5,
        )
        cleanup_volumes.append(vol.key)

        # Test filtering by enabled
        enabled_vols = client.nas_volumes.list(enabled=True)
        assert all(v.get("enabled") for v in enabled_vols)

        # Test filtering by service
        service_vols = client.nas_volumes.list(service=test_service.key)
        assert len(service_vols) >= 1

    def test_create_and_delete_volume(
        self, client: VergeClient, test_service: NASService, cleanup_volumes: list[str]
    ) -> None:
        """Test creating and deleting a NAS volume."""
        # Create a test volume
        vol = client.nas_volumes.create(
            name="pytest-vol-crud",
            service=test_service.key,
            size_gb=5,
            description="Integration test volume",
        )
        cleanup_volumes.append(vol.key)

        assert vol.name == "pytest-vol-crud"
        assert vol.max_size_gb == 5.0
        assert vol.get("description") == "Integration test volume"
        assert vol.get("enabled") is True
        assert len(vol.key) == 40  # 40-char hex string

        # Delete the volume
        client.nas_volumes.delete(vol.key)
        cleanup_volumes.remove(vol.key)

        # Verify it's gone
        with pytest.raises(NotFoundError):
            client.nas_volumes.get(key=vol.key)

    def test_create_with_options(
        self, client: VergeClient, test_service: NASService, cleanup_volumes: list[str]
    ) -> None:
        """Test creating a volume with various options."""
        vol = client.nas_volumes.create(
            name="pytest-vol-opts",
            service=test_service.key,
            size_gb=10,
            tier=1,
            description="Volume with options",
            discard=True,
            read_only=False,
        )
        cleanup_volumes.append(vol.key)

        assert vol.name == "pytest-vol-opts"
        assert vol.max_size_gb == 10.0
        assert vol.get("preferred_tier") == "1"
        assert vol.get("description") == "Volume with options"
        assert vol.get("discard") is True
        assert vol.get("read_only") is False

    def test_get_volume_by_key(
        self, client: VergeClient, test_service: NASService, cleanup_volumes: list[str]
    ) -> None:
        """Test getting a volume by key."""
        created = client.nas_volumes.create(
            name="pytest-vol-bykey",
            service=test_service.key,
            size_gb=5,
        )
        cleanup_volumes.append(created.key)

        fetched = client.nas_volumes.get(key=created.key)

        assert fetched.key == created.key
        assert fetched.name == created.name
        assert fetched.max_size_gb == created.max_size_gb

    def test_get_volume_by_name(
        self, client: VergeClient, test_service: NASService, cleanup_volumes: list[str]
    ) -> None:
        """Test getting a volume by name."""
        test_name = "pytest-vol-byname"
        created = client.nas_volumes.create(
            name=test_name,
            service=test_service.key,
            size_gb=5,
        )
        cleanup_volumes.append(created.key)

        fetched = client.nas_volumes.get(name=test_name)

        assert fetched.key == created.key
        assert fetched.name == test_name

    def test_get_volume_not_found(self, client: VergeClient) -> None:
        """Test getting a non-existent volume raises NotFoundError."""
        with pytest.raises(NotFoundError):
            client.nas_volumes.get(key="0000000000000000000000000000000000000000")

        with pytest.raises(NotFoundError):
            client.nas_volumes.get(name="nonexistent-volume-xyz")

    def test_update_volume(
        self, client: VergeClient, test_service: NASService, cleanup_volumes: list[str]
    ) -> None:
        """Test updating a volume."""
        vol = client.nas_volumes.create(
            name="pytest-vol-update",
            service=test_service.key,
            size_gb=5,
            description="Original description",
        )
        cleanup_volumes.append(vol.key)

        updated = client.nas_volumes.update(
            vol.key,
            description="Updated description",
            size_gb=10,
        )

        assert updated.get("description") == "Updated description"
        assert updated.max_size_gb == 10.0

    def test_enable_disable_volume(
        self, client: VergeClient, test_service: NASService, cleanup_volumes: list[str]
    ) -> None:
        """Test enabling and disabling a volume."""
        vol = client.nas_volumes.create(
            name="pytest-vol-enable",
            service=test_service.key,
            size_gb=5,
        )
        cleanup_volumes.append(vol.key)

        # Initially enabled
        assert vol.get("enabled") is True

        # Disable
        disabled = client.nas_volumes.disable(vol.key)
        assert disabled.get("enabled") is False

        # Re-enable
        enabled = client.nas_volumes.enable(vol.key)
        assert enabled.get("enabled") is True


class TestNASVolumeSnapshotIntegration:
    """Integration tests for NASVolumeSnapshotManager."""

    def test_list_snapshots(
        self, client: VergeClient, test_service: NASService, cleanup_volumes: list[str]
    ) -> None:
        """Test listing snapshots for a volume."""
        vol = client.nas_volumes.create(
            name="pytest-vol-snaps",
            service=test_service.key,
            size_gb=5,
        )
        cleanup_volumes.append(vol.key)

        snapshots = client.nas_volumes.snapshots(vol.key).list()

        assert isinstance(snapshots, list)
        # New volume has no snapshots
        assert len(snapshots) == 0

    def test_create_and_delete_snapshot(
        self, client: VergeClient, test_service: NASService, cleanup_volumes: list[str]
    ) -> None:
        """Test creating and deleting a snapshot."""
        vol = client.nas_volumes.create(
            name="pytest-vol-snapcrud",
            service=test_service.key,
            size_gb=5,
        )
        cleanup_volumes.append(vol.key)

        snap_mgr = client.nas_volumes.snapshots(vol.key)

        # Create a snapshot
        snap = snap_mgr.create(
            name="pytest-snap-001",
            description="Test snapshot",
        )

        assert snap.name == "pytest-snap-001"
        assert snap.get("description") == "Test snapshot"
        assert snap.volume_key == vol.key

        # Verify it's in the list
        snapshots = snap_mgr.list()
        assert len(snapshots) == 1
        assert snapshots[0].name == "pytest-snap-001"

        # Delete the snapshot
        snap_mgr.delete(snap.key)

        # Verify it's gone
        snapshots = snap_mgr.list()
        assert len(snapshots) == 0

    def test_create_snapshot_with_expiration(
        self, client: VergeClient, test_service: NASService, cleanup_volumes: list[str]
    ) -> None:
        """Test creating a snapshot with expiration."""
        vol = client.nas_volumes.create(
            name="pytest-vol-snapexp",
            service=test_service.key,
            size_gb=5,
        )
        cleanup_volumes.append(vol.key)

        snap_mgr = client.nas_volumes.snapshots(vol.key)

        # Create a snapshot that expires in 1 day
        snap = snap_mgr.create(
            name="pytest-snap-expires",
            expires_days=1,
        )

        assert snap.never_expires is False
        assert snap.get("expires") > 0

    def test_create_snapshot_never_expires(
        self, client: VergeClient, test_service: NASService, cleanup_volumes: list[str]
    ) -> None:
        """Test creating a snapshot that never expires."""
        vol = client.nas_volumes.create(
            name="pytest-vol-snapnever",
            service=test_service.key,
            size_gb=5,
        )
        cleanup_volumes.append(vol.key)

        snap_mgr = client.nas_volumes.snapshots(vol.key)

        # Create a snapshot that never expires
        snap = snap_mgr.create(
            name="pytest-snap-never",
            never_expires=True,
        )

        assert snap.never_expires is True

    def test_get_snapshot_by_key(
        self, client: VergeClient, test_service: NASService, cleanup_volumes: list[str]
    ) -> None:
        """Test getting a snapshot by key."""
        vol = client.nas_volumes.create(
            name="pytest-vol-snapbykey",
            service=test_service.key,
            size_gb=5,
        )
        cleanup_volumes.append(vol.key)

        snap_mgr = client.nas_volumes.snapshots(vol.key)
        created = snap_mgr.create(name="pytest-snap-bykey")

        # Get using the standalone manager
        fetched = client.nas_volume_snapshots.get(key=created.key)

        assert fetched.key == created.key
        assert fetched.name == created.name

    def test_get_snapshot_by_name(
        self, client: VergeClient, test_service: NASService, cleanup_volumes: list[str]
    ) -> None:
        """Test getting a snapshot by name."""
        vol = client.nas_volumes.create(
            name="pytest-vol-snapbyname",
            service=test_service.key,
            size_gb=5,
        )
        cleanup_volumes.append(vol.key)

        snap_mgr = client.nas_volumes.snapshots(vol.key)
        test_name = "pytest-snap-byname"
        created = snap_mgr.create(name=test_name)

        fetched = snap_mgr.get(name=test_name)

        assert fetched.key == created.key
        assert fetched.name == test_name

    def test_list_all_snapshots(
        self, client: VergeClient, test_service: NASService, cleanup_volumes: list[str]
    ) -> None:
        """Test listing all snapshots using standalone manager."""
        vol = client.nas_volumes.create(
            name="pytest-vol-listall",
            service=test_service.key,
            size_gb=5,
        )
        cleanup_volumes.append(vol.key)

        snap_mgr = client.nas_volumes.snapshots(vol.key)

        # Create multiple snapshots
        snap_mgr.create(name="pytest-snap-all-1")
        snap_mgr.create(name="pytest-snap-all-2")

        # List all snapshots (not scoped to volume)
        all_snaps = client.nas_volume_snapshots.list()
        assert len(all_snaps) >= 2

        # List snapshots for this specific volume
        vol_snaps = client.nas_volume_snapshots.list(volume=vol.key)
        assert len(vol_snaps) == 2

        snap_names = {s.name for s in vol_snaps}
        assert "pytest-snap-all-1" in snap_names
        assert "pytest-snap-all-2" in snap_names

    def test_multiple_snapshots(
        self, client: VergeClient, test_service: NASService, cleanup_volumes: list[str]
    ) -> None:
        """Test creating multiple snapshots on one volume."""
        vol = client.nas_volumes.create(
            name="pytest-vol-multisnap",
            service=test_service.key,
            size_gb=5,
        )
        cleanup_volumes.append(vol.key)

        snap_mgr = client.nas_volumes.snapshots(vol.key)

        # Create multiple snapshots
        snap_mgr.create(name="pytest-snap-1")
        snap_mgr.create(name="pytest-snap-2")
        snap_mgr.create(name="pytest-snap-3")

        # Verify all exist
        snapshots = snap_mgr.list()
        assert len(snapshots) == 3

        snap_names = {s.name for s in snapshots}
        assert "pytest-snap-1" in snap_names
        assert "pytest-snap-2" in snap_names
        assert "pytest-snap-3" in snap_names

    def test_delete_volume_removes_snapshots(
        self, client: VergeClient, test_service: NASService
    ) -> None:
        """Test that deleting a volume also removes its snapshots."""
        vol = client.nas_volumes.create(
            name="pytest-vol-cascade",
            service=test_service.key,
            size_gb=5,
        )

        snap_mgr = client.nas_volumes.snapshots(vol.key)

        # Create snapshots
        snap1 = snap_mgr.create(name="pytest-cascade-1")
        snap2 = snap_mgr.create(name="pytest-cascade-2")

        # Verify snapshots exist
        snapshots = snap_mgr.list()
        assert len(snapshots) == 2

        # Delete the volume
        client.nas_volumes.delete(vol.key)

        # Volume should be gone
        with pytest.raises(NotFoundError):
            client.nas_volumes.get(key=vol.key)

        # Snapshots should also be gone
        with pytest.raises(NotFoundError):
            client.nas_volume_snapshots.get(key=snap1.key)
        with pytest.raises(NotFoundError):
            client.nas_volume_snapshots.get(key=snap2.key)


class TestNASVolumeObjectMethods:
    """Integration tests for NASVolume object methods."""

    def test_volume_refresh(
        self, client: VergeClient, test_service: NASService, cleanup_volumes: list[str]
    ) -> None:
        """Test refreshing a volume object."""
        vol = client.nas_volumes.create(
            name="pytest-vol-refresh",
            service=test_service.key,
            size_gb=5,
            description="Original",
        )
        cleanup_volumes.append(vol.key)

        # Update via manager
        client.nas_volumes.update(vol.key, description="Updated")

        # Refresh the object
        refreshed = vol.refresh()

        assert refreshed.get("description") == "Updated"

    def test_volume_save(
        self, client: VergeClient, test_service: NASService, cleanup_volumes: list[str]
    ) -> None:
        """Test saving a volume object."""
        vol = client.nas_volumes.create(
            name="pytest-vol-save",
            service=test_service.key,
            size_gb=5,
        )
        cleanup_volumes.append(vol.key)

        # Save with new description
        updated = vol.save(description="Saved via object method")

        assert updated.get("description") == "Saved via object method"

    def test_volume_delete(self, client: VergeClient, test_service: NASService) -> None:
        """Test deleting a volume via object method."""
        vol = client.nas_volumes.create(
            name="pytest-vol-objdel",
            service=test_service.key,
            size_gb=5,
        )

        # Delete via object method
        vol.delete()

        # Verify it's gone
        with pytest.raises(NotFoundError):
            client.nas_volumes.get(key=vol.key)

    def test_volume_snapshots_via_manager(
        self, client: VergeClient, test_service: NASService, cleanup_volumes: list[str]
    ) -> None:
        """Test accessing snapshots via manager with volume key."""
        vol = client.nas_volumes.create(
            name="pytest-vol-snapacc",
            service=test_service.key,
            size_gb=5,
        )
        cleanup_volumes.append(vol.key)

        # Access snapshot manager via volume manager with volume key
        snap_mgr = client.nas_volumes.snapshots(vol.key)

        # Create a snapshot
        snap = snap_mgr.create(name="pytest-snap-accessor")

        assert snap.name == "pytest-snap-accessor"

        # List snapshots for this volume
        snapshots = snap_mgr.list()
        assert len(snapshots) == 1
