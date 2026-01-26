"""Integration tests for NASNFSShareManager.

These tests require a live VergeOS system with at least one NAS service and volume.
Configure with environment variables:
    VERGE_HOST, VERGE_USERNAME, VERGE_PASSWORD, VERGE_VERIFY_SSL
"""

from __future__ import annotations

import contextlib
import os

import pytest

from pyvergeos import VergeClient
from pyvergeos.exceptions import NotFoundError
from pyvergeos.resources.nas_nfs import NASNFSShare
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
    """Get a NAS service for testing.

    Uses the first available NAS service.
    """
    services = client.nas_services.list()
    if not services:
        pytest.skip("No NAS services available for NFS share testing")
    return services[0]


@pytest.fixture(scope="module")
def test_volume(client: VergeClient, test_service: NASService) -> NASVolume:
    """Get or create a NAS volume for testing NFS shares."""
    # Try to find an existing volume
    volumes = client.nas_volumes.list(service=test_service.key)
    if volumes:
        return volumes[0]

    # Create a test volume if none exist
    vol = client.nas_volumes.create(
        name="pytest-nfs-vol",
        service=test_service.key,
        size_gb=5,
        description="Volume for NFS share integration tests",
    )
    yield vol
    # Cleanup
    with contextlib.suppress(NotFoundError):
        client.nas_volumes.delete(vol.key)


@pytest.fixture
def cleanup_shares(client: VergeClient):
    """Fixture to track and cleanup test shares."""
    created_keys: list[str] = []

    yield created_keys

    # Cleanup any shares we created
    for key in created_keys:
        with contextlib.suppress(NotFoundError):
            client.nfs_shares.delete(key)


class TestNASNFSShareManagerIntegration:
    """Integration tests for NASNFSShareManager."""

    def test_list_shares(self, client: VergeClient) -> None:
        """Test listing all NFS shares."""
        shares = client.nfs_shares.list()

        assert isinstance(shares, list)
        for share in shares:
            assert isinstance(share, NASNFSShare)
            assert share.key is not None
            assert len(share.key) == 40  # 40-char hex string

    def test_list_shares_with_volume_filter(
        self, client: VergeClient, test_volume: NASVolume, cleanup_shares: list[str]
    ) -> None:
        """Test listing shares filtered by volume."""
        # Create a test share first
        share = client.nfs_shares.create(
            name="pytest-nfs-filter",
            volume=test_volume.key,
            allowed_hosts=["192.168.0.0/16"],
        )
        cleanup_shares.append(share.key)

        # List shares for the volume
        shares = client.nfs_shares.list(volume=test_volume.key)

        assert len(shares) >= 1
        assert any(s.key == share.key for s in shares)

    def test_list_shares_with_enabled_filter(
        self, client: VergeClient, test_volume: NASVolume, cleanup_shares: list[str]
    ) -> None:
        """Test listing shares filtered by enabled status."""
        # Create an enabled share
        share = client.nfs_shares.create(
            name="pytest-nfs-enabled",
            volume=test_volume.key,
            allowed_hosts=["192.168.0.0/16"],
            enabled=True,
        )
        cleanup_shares.append(share.key)

        # List enabled shares
        enabled_shares = client.nfs_shares.list(enabled=True)

        assert all(s.is_enabled for s in enabled_shares)

    def test_create_and_delete_share_with_hosts(
        self, client: VergeClient, test_volume: NASVolume, cleanup_shares: list[str]
    ) -> None:
        """Test creating and deleting an NFS share with allowed hosts."""
        # Create a test share
        share = client.nfs_shares.create(
            name="pytest-nfs-crud",
            volume=test_volume.key,
            share_path="/pytest-crud",
            description="CRUD test share",
            allowed_hosts=["192.168.1.0/24", "10.0.0.0/8"],
            data_access="rw",
            squash="root_squash",
        )
        cleanup_shares.append(share.key)

        assert share.name == "pytest-nfs-crud"
        assert share.get("share_path") == "/pytest-crud"
        assert share.get("description") == "CRUD test share"
        assert share.is_enabled is True
        assert len(share.key) == 40

        # Delete the share
        client.nfs_shares.delete(share.key)
        cleanup_shares.remove(share.key)

        # Verify it's gone
        with pytest.raises(NotFoundError):
            client.nfs_shares.get(share.key)

    def test_create_and_delete_share_with_allow_all(
        self, client: VergeClient, test_volume: NASVolume, cleanup_shares: list[str]
    ) -> None:
        """Test creating an NFS share with allow_all."""
        # Create a test share
        share = client.nfs_shares.create(
            name="pytest-nfs-allowall",
            volume=test_volume.key,
            allow_all=True,
        )
        cleanup_shares.append(share.key)

        assert share.name == "pytest-nfs-allowall"
        assert share.allows_all_hosts is True

        # Delete the share
        client.nfs_shares.delete(share.key)
        cleanup_shares.remove(share.key)

    def test_create_with_access_options(
        self, client: VergeClient, test_volume: NASVolume, cleanup_shares: list[str]
    ) -> None:
        """Test creating a share with various access options."""
        share = client.nfs_shares.create(
            name="pytest-nfs-access",
            volume=test_volume.key,
            allowed_hosts=["*"],
            data_access="ro",
            squash="all_squash",
        )
        cleanup_shares.append(share.key)

        assert share.is_read_only is True
        assert share.squash_display == "Squash All"

    def test_get_share_by_key(
        self, client: VergeClient, test_volume: NASVolume, cleanup_shares: list[str]
    ) -> None:
        """Test getting a share by key."""
        # Create a share first
        created = client.nfs_shares.create(
            name="pytest-nfs-getkey",
            volume=test_volume.key,
            allow_all=True,
        )
        cleanup_shares.append(created.key)

        # Get by key
        fetched = client.nfs_shares.get(created.key)

        assert fetched.key == created.key
        assert fetched.name == "pytest-nfs-getkey"

    def test_get_share_by_name(
        self, client: VergeClient, test_volume: NASVolume, cleanup_shares: list[str]
    ) -> None:
        """Test getting a share by name."""
        # Create a share first
        created = client.nfs_shares.create(
            name="pytest-nfs-getname",
            volume=test_volume.key,
            allow_all=True,
        )
        cleanup_shares.append(created.key)

        # Get by name
        fetched = client.nfs_shares.get(name="pytest-nfs-getname")

        assert fetched.key == created.key
        assert fetched.name == "pytest-nfs-getname"

    def test_get_share_not_found(self, client: VergeClient) -> None:
        """Test getting a non-existent share raises NotFoundError."""
        with pytest.raises(NotFoundError):
            client.nfs_shares.get("0000000000000000000000000000000000000000")

    def test_update_share(
        self, client: VergeClient, test_volume: NASVolume, cleanup_shares: list[str]
    ) -> None:
        """Test updating an NFS share."""
        # Create a share first
        share = client.nfs_shares.create(
            name="pytest-nfs-update",
            volume=test_volume.key,
            allowed_hosts=["192.168.1.0/24"],
            description="Original description",
        )
        cleanup_shares.append(share.key)

        # Update the share
        updated = client.nfs_shares.update(
            share.key,
            description="Updated description",
            data_access="ro",
        )

        assert updated.get("description") == "Updated description"
        assert updated.get("data_access") == "ro"

    def test_update_allowed_hosts(
        self, client: VergeClient, test_volume: NASVolume, cleanup_shares: list[str]
    ) -> None:
        """Test updating allowed hosts."""
        # Create a share first
        share = client.nfs_shares.create(
            name="pytest-nfs-uphosts",
            volume=test_volume.key,
            allowed_hosts=["192.168.1.0/24"],
        )
        cleanup_shares.append(share.key)

        # Update allowed hosts
        updated = client.nfs_shares.update(
            share.key,
            allowed_hosts=["10.0.0.0/8", "172.16.0.0/12"],
        )

        # Verify hosts were updated (format may vary: comma-delimited or JSON array)
        hosts = updated.get("allowed_hosts", "")
        # Check for IP addresses regardless of format (handles escaped slashes too)
        assert "10.0.0.0" in hosts
        assert "172.16.0.0" in hosts

    def test_enable_disable_share(
        self, client: VergeClient, test_volume: NASVolume, cleanup_shares: list[str]
    ) -> None:
        """Test enabling and disabling an NFS share."""
        # Create an enabled share
        share = client.nfs_shares.create(
            name="pytest-nfs-toggle",
            volume=test_volume.key,
            allow_all=True,
            enabled=True,
        )
        cleanup_shares.append(share.key)
        assert share.is_enabled is True

        # Disable it
        disabled = client.nfs_shares.disable(share.key)
        assert disabled.is_enabled is False

        # Enable it
        enabled = client.nfs_shares.enable(share.key)
        assert enabled.is_enabled is True

    def test_share_refresh(
        self, client: VergeClient, test_volume: NASVolume, cleanup_shares: list[str]
    ) -> None:
        """Test refreshing share data."""
        # Create a share
        share = client.nfs_shares.create(
            name="pytest-nfs-refresh",
            volume=test_volume.key,
            allow_all=True,
        )
        cleanup_shares.append(share.key)

        # Update it via manager
        client.nfs_shares.update(share.key, description="Refreshed description")

        # Refresh the original object
        refreshed = share.refresh()

        assert refreshed.get("description") == "Refreshed description"

    def test_share_save(
        self, client: VergeClient, test_volume: NASVolume, cleanup_shares: list[str]
    ) -> None:
        """Test saving share changes via instance method."""
        # Create a share
        share = client.nfs_shares.create(
            name="pytest-nfs-save",
            volume=test_volume.key,
            allow_all=True,
        )
        cleanup_shares.append(share.key)

        # Save changes via instance
        saved = share.save(description="Saved description")

        assert saved.get("description") == "Saved description"

    def test_share_delete_instance(self, client: VergeClient, test_volume: NASVolume) -> None:
        """Test deleting share via instance method."""
        # Create a share
        share = client.nfs_shares.create(
            name="pytest-nfs-delinst",
            volume=test_volume.key,
            allow_all=True,
        )

        # Delete via instance
        share.delete()

        # Verify it's gone
        with pytest.raises(NotFoundError):
            client.nfs_shares.get(share.key)

    def test_squash_modes(
        self, client: VergeClient, test_volume: NASVolume, cleanup_shares: list[str]
    ) -> None:
        """Test different squash modes."""
        squash_modes = [
            ("root_squash", "Squash Root"),
            ("all_squash", "Squash All"),
            ("no_root_squash", "No Squashing"),
        ]

        for mode, display in squash_modes:
            share = client.nfs_shares.create(
                name=f"pytest-nfs-{mode.replace('_', '')}",
                volume=test_volume.key,
                allow_all=True,
                squash=mode,
            )
            cleanup_shares.append(share.key)

            assert share.get("squash") == mode
            assert share.squash_display == display

    def test_data_access_modes(
        self, client: VergeClient, test_volume: NASVolume, cleanup_shares: list[str]
    ) -> None:
        """Test different data access modes."""
        # Read-only
        ro_share = client.nfs_shares.create(
            name="pytest-nfs-readonly",
            volume=test_volume.key,
            allow_all=True,
            data_access="ro",
        )
        cleanup_shares.append(ro_share.key)
        assert ro_share.is_read_only is True
        assert ro_share.data_access_display == "Read Only"

        # Read-write
        rw_share = client.nfs_shares.create(
            name="pytest-nfs-readwrite",
            volume=test_volume.key,
            allow_all=True,
            data_access="rw",
        )
        cleanup_shares.append(rw_share.key)
        assert rw_share.is_read_only is False
        assert rw_share.data_access_display == "Read and Write"
