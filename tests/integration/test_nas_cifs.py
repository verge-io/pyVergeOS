"""Integration tests for NASCIFSShareManager.

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
from pyvergeos.resources.nas_cifs import NASCIFSShare
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
        pytest.skip("No NAS services available for CIFS share testing")
    return services[0]


@pytest.fixture(scope="module")
def test_volume(client: VergeClient, test_service: NASService) -> NASVolume:
    """Get or create a NAS volume for testing CIFS shares."""
    # Try to find an existing volume
    volumes = client.nas_volumes.list(service=test_service.key)
    if volumes:
        return volumes[0]

    # Create a test volume if none exist
    vol = client.nas_volumes.create(
        name="pytest-cifs-vol",
        service=test_service.key,
        size_gb=5,
        description="Volume for CIFS share integration tests",
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
            client.cifs_shares.delete(key)


class TestNASCIFSShareManagerIntegration:
    """Integration tests for NASCIFSShareManager."""

    def test_list_shares(self, client: VergeClient) -> None:
        """Test listing all CIFS shares."""
        shares = client.cifs_shares.list()

        assert isinstance(shares, list)
        for share in shares:
            assert isinstance(share, NASCIFSShare)
            assert share.key is not None
            assert len(share.key) == 40  # 40-char hex string

    def test_list_shares_with_volume_filter(
        self, client: VergeClient, test_volume: NASVolume, cleanup_shares: list[str]
    ) -> None:
        """Test listing shares filtered by volume."""
        # Create a test share first
        share = client.cifs_shares.create(
            name="pytest-cifs-filter",
            volume=test_volume.key,
            comment="Integration test share",
        )
        cleanup_shares.append(share.key)

        # List shares for the volume
        shares = client.cifs_shares.list(volume=test_volume.key)

        assert len(shares) >= 1
        assert any(s.key == share.key for s in shares)

    def test_list_shares_with_enabled_filter(
        self, client: VergeClient, test_volume: NASVolume, cleanup_shares: list[str]
    ) -> None:
        """Test listing shares filtered by enabled status."""
        # Create an enabled share
        share = client.cifs_shares.create(
            name="pytest-cifs-enabled",
            volume=test_volume.key,
            enabled=True,
        )
        cleanup_shares.append(share.key)

        # List enabled shares
        enabled_shares = client.cifs_shares.list(enabled=True)

        assert all(s.is_enabled for s in enabled_shares)

    def test_create_and_delete_share(
        self, client: VergeClient, test_volume: NASVolume, cleanup_shares: list[str]
    ) -> None:
        """Test creating and deleting a CIFS share."""
        # Create a test share
        share = client.cifs_shares.create(
            name="pytest-cifs-crud",
            volume=test_volume.key,
            share_path="/pytest-crud",
            comment="CRUD test share",
            browseable=True,
            guest_ok=False,
        )
        cleanup_shares.append(share.key)

        assert share.name == "pytest-cifs-crud"
        assert share.get("share_path") == "/pytest-crud"
        assert share.get("comment") == "CRUD test share"
        assert share.is_enabled is True
        assert len(share.key) == 40

        # Delete the share
        client.cifs_shares.delete(share.key)
        cleanup_shares.remove(share.key)

        # Verify it's gone
        with pytest.raises(NotFoundError):
            client.cifs_shares.get(share.key)

    def test_create_with_access_options(
        self, client: VergeClient, test_volume: NASVolume, cleanup_shares: list[str]
    ) -> None:
        """Test creating a share with access options."""
        share = client.cifs_shares.create(
            name="pytest-cifs-access",
            volume=test_volume.key,
            read_only=True,
            guest_ok=True,
            browseable=False,
        )
        cleanup_shares.append(share.key)

        assert share.is_read_only is True
        assert share.allows_guests is True
        assert share.get("browseable") is False

    def test_get_share_by_key(
        self, client: VergeClient, test_volume: NASVolume, cleanup_shares: list[str]
    ) -> None:
        """Test getting a share by key."""
        # Create a share first
        created = client.cifs_shares.create(
            name="pytest-cifs-getkey",
            volume=test_volume.key,
        )
        cleanup_shares.append(created.key)

        # Get by key
        fetched = client.cifs_shares.get(created.key)

        assert fetched.key == created.key
        assert fetched.name == "pytest-cifs-getkey"

    def test_get_share_by_name(
        self, client: VergeClient, test_volume: NASVolume, cleanup_shares: list[str]
    ) -> None:
        """Test getting a share by name."""
        # Create a share first
        created = client.cifs_shares.create(
            name="pytest-cifs-getname",
            volume=test_volume.key,
        )
        cleanup_shares.append(created.key)

        # Get by name
        fetched = client.cifs_shares.get(name="pytest-cifs-getname")

        assert fetched.key == created.key
        assert fetched.name == "pytest-cifs-getname"

    def test_get_share_not_found(self, client: VergeClient) -> None:
        """Test getting a non-existent share raises NotFoundError."""
        with pytest.raises(NotFoundError):
            client.cifs_shares.get("0000000000000000000000000000000000000000")

    def test_update_share(
        self, client: VergeClient, test_volume: NASVolume, cleanup_shares: list[str]
    ) -> None:
        """Test updating a CIFS share."""
        # Create a share first
        share = client.cifs_shares.create(
            name="pytest-cifs-update",
            volume=test_volume.key,
            comment="Original comment",
        )
        cleanup_shares.append(share.key)

        # Update the share
        updated = client.cifs_shares.update(
            share.key,
            comment="Updated comment",
            browseable=False,
        )

        assert updated.get("comment") == "Updated comment"
        assert updated.get("browseable") is False

    def test_enable_disable_share(
        self, client: VergeClient, test_volume: NASVolume, cleanup_shares: list[str]
    ) -> None:
        """Test enabling and disabling a CIFS share."""
        # Create an enabled share
        share = client.cifs_shares.create(
            name="pytest-cifs-toggle",
            volume=test_volume.key,
            enabled=True,
        )
        cleanup_shares.append(share.key)
        assert share.is_enabled is True

        # Disable it
        disabled = client.cifs_shares.disable(share.key)
        assert disabled.is_enabled is False

        # Enable it
        enabled = client.cifs_shares.enable(share.key)
        assert enabled.is_enabled is True

    def test_share_refresh(
        self, client: VergeClient, test_volume: NASVolume, cleanup_shares: list[str]
    ) -> None:
        """Test refreshing share data."""
        # Create a share
        share = client.cifs_shares.create(
            name="pytest-cifs-refresh",
            volume=test_volume.key,
        )
        cleanup_shares.append(share.key)

        # Update it via manager
        client.cifs_shares.update(share.key, comment="Refreshed comment")

        # Refresh the original object
        refreshed = share.refresh()

        assert refreshed.get("comment") == "Refreshed comment"

    def test_share_save(
        self, client: VergeClient, test_volume: NASVolume, cleanup_shares: list[str]
    ) -> None:
        """Test saving share changes via instance method."""
        # Create a share
        share = client.cifs_shares.create(
            name="pytest-cifs-save",
            volume=test_volume.key,
        )
        cleanup_shares.append(share.key)

        # Save changes via instance
        saved = share.save(comment="Saved comment")

        assert saved.get("comment") == "Saved comment"

    def test_share_delete_instance(self, client: VergeClient, test_volume: NASVolume) -> None:
        """Test deleting share via instance method."""
        # Create a share
        share = client.cifs_shares.create(
            name="pytest-cifs-delinst",
            volume=test_volume.key,
        )

        # Delete via instance
        share.delete()

        # Verify it's gone
        with pytest.raises(NotFoundError):
            client.cifs_shares.get(share.key)
