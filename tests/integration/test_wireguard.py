"""Integration tests for WireGuardManager and WireGuardPeerManager.

These tests require a live VergeOS system.
Configure with environment variables:
    VERGE_HOST, VERGE_USERNAME, VERGE_PASSWORD, VERGE_VERIFY_SSL
"""

from __future__ import annotations

import base64
import contextlib
import os
import secrets

import pytest

from pyvergeos import VergeClient
from pyvergeos.exceptions import NotFoundError
from pyvergeos.resources.networks import Network
from pyvergeos.resources.wireguard import WireGuardInterface

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
def test_network(client: VergeClient) -> Network:
    """Get an external network to test WireGuard on.

    WireGuard is typically configured on external networks.
    """
    # Try to get External network
    try:
        return client.networks.get(name="External")
    except NotFoundError:
        pass

    # Fall back to first external network
    networks = client.networks.list_external()
    if not networks:
        pytest.skip("No external networks available for WireGuard testing")
    return networks[0]


def generate_fake_pubkey() -> str:
    """Generate a fake WireGuard public key for testing."""
    return base64.b64encode(secrets.token_bytes(32)).decode("ascii")


@pytest.fixture
def cleanup_interfaces(test_network: Network):
    """Fixture to track and cleanup test WireGuard interfaces."""
    created_keys: list[int] = []

    yield created_keys

    # Cleanup any interfaces we created (also removes peers)
    for key in created_keys:
        with contextlib.suppress(NotFoundError):
            test_network.wireguard.delete(key)


class TestWireGuardManagerIntegration:
    """Integration tests for WireGuardManager."""

    def test_list_interfaces(self, test_network: Network) -> None:
        """Test listing WireGuard interfaces on a network."""
        interfaces = test_network.wireguard.list()

        assert isinstance(interfaces, list)
        for iface in interfaces:
            assert isinstance(iface, WireGuardInterface)
            assert iface.key is not None
            assert iface.name is not None

    def test_create_and_delete_interface(
        self, test_network: Network, cleanup_interfaces: list[int]
    ) -> None:
        """Test creating and deleting a WireGuard interface."""
        # Create a test interface
        iface = test_network.wireguard.create(
            name="pytest-wg-001",
            ip_address="10.200.0.1/24",
            listen_port=51820,
            description="Integration test interface",
        )
        cleanup_interfaces.append(iface.key)

        assert iface.name == "pytest-wg-001"
        assert iface.ip_address == "10.200.0.1/24"
        assert iface.ip_only == "10.200.0.1"
        assert iface.subnet_mask == "24"
        assert iface.listen_port == 51820
        assert iface.is_enabled is True
        assert iface.public_key  # Should have auto-generated public key

        # Delete the interface
        test_network.wireguard.delete(iface.key)
        cleanup_interfaces.remove(iface.key)

        # Verify it's gone
        with pytest.raises(NotFoundError):
            test_network.wireguard.get(iface.key)

    def test_create_with_options(
        self, test_network: Network, cleanup_interfaces: list[int]
    ) -> None:
        """Test creating an interface with various options."""
        iface = test_network.wireguard.create(
            name="pytest-wg-opts",
            ip_address="10.200.1.1/24",
            listen_port=51821,
            mtu=1420,
            endpoint_ip="203.0.113.50",
            description="Custom MTU interface",
            enabled=True,
        )
        cleanup_interfaces.append(iface.key)

        assert iface.mtu == 1420
        assert iface.mtu_display == "1420"
        assert iface.endpoint_ip == "203.0.113.50"
        assert iface.get("description") == "Custom MTU interface"

    def test_get_interface_by_key(
        self, test_network: Network, cleanup_interfaces: list[int]
    ) -> None:
        """Test getting an interface by key."""
        created = test_network.wireguard.create(
            name="pytest-wg-bykey",
            ip_address="10.200.2.1/24",
        )
        cleanup_interfaces.append(created.key)

        fetched = test_network.wireguard.get(created.key)

        assert fetched.key == created.key
        assert fetched.name == created.name
        assert fetched.ip_address == created.ip_address

    def test_get_interface_by_name(
        self, test_network: Network, cleanup_interfaces: list[int]
    ) -> None:
        """Test getting an interface by name."""
        test_name = "pytest-wg-byname"
        created = test_network.wireguard.create(
            name=test_name,
            ip_address="10.200.3.1/24",
        )
        cleanup_interfaces.append(created.key)

        fetched = test_network.wireguard.get(name=test_name)

        assert fetched.key == created.key
        assert fetched.name == test_name

    def test_get_interface_not_found(self, test_network: Network) -> None:
        """Test getting a non-existent interface raises NotFoundError."""
        with pytest.raises(NotFoundError):
            test_network.wireguard.get(999999)

        with pytest.raises(NotFoundError):
            test_network.wireguard.get(name="nonexistent-interface-xyz")

    def test_update_interface(self, test_network: Network, cleanup_interfaces: list[int]) -> None:
        """Test updating an interface."""
        iface = test_network.wireguard.create(
            name="pytest-wg-update",
            ip_address="10.200.4.1/24",
            description="Original description",
        )
        cleanup_interfaces.append(iface.key)

        updated = test_network.wireguard.update(
            iface.key,
            description="Updated description",
            mtu=1380,
        )

        assert updated.get("description") == "Updated description"
        assert updated.mtu == 1380


class TestWireGuardPeerManagerIntegration:
    """Integration tests for WireGuardPeerManager."""

    def test_list_peers(self, test_network: Network, cleanup_interfaces: list[int]) -> None:
        """Test listing peers for an interface."""
        iface = test_network.wireguard.create(
            name="pytest-wg-peers",
            ip_address="10.200.10.1/24",
        )
        cleanup_interfaces.append(iface.key)

        peers = iface.peers.list()

        assert isinstance(peers, list)
        # New interface has no peers
        assert len(peers) == 0

    def test_create_and_delete_peer(
        self, test_network: Network, cleanup_interfaces: list[int]
    ) -> None:
        """Test creating and deleting a peer."""
        iface = test_network.wireguard.create(
            name="pytest-wg-peer-crud",
            ip_address="10.200.11.1/24",
        )
        cleanup_interfaces.append(iface.key)

        # Create a peer
        peer = iface.peers.create(
            name="pytest-peer-001",
            peer_ip="10.200.11.2",
            public_key=generate_fake_pubkey(),
            allowed_ips="192.168.100.0/24",
            description="Test peer",
        )

        assert peer.name == "pytest-peer-001"
        assert peer.peer_ip == "10.200.11.2"
        assert peer.allowed_ips == "192.168.100.0/24"
        assert peer.is_enabled is True
        assert peer.firewall_config_display == "Site-to-Site"

        # Verify it's in the list
        peers = iface.peers.list()
        assert len(peers) == 1
        assert peers[0].name == "pytest-peer-001"

        # Delete the peer
        iface.peers.delete(peer.key)

        # Verify it's gone
        peers = iface.peers.list()
        assert len(peers) == 0

    def test_create_peer_with_options(
        self, test_network: Network, cleanup_interfaces: list[int]
    ) -> None:
        """Test creating a peer with various options."""
        iface = test_network.wireguard.create(
            name="pytest-wg-peer-opts",
            ip_address="10.200.12.1/24",
        )
        cleanup_interfaces.append(iface.key)

        peer = iface.peers.create(
            name="pytest-peer-opts",
            peer_ip="10.200.12.2",
            public_key=generate_fake_pubkey(),
            allowed_ips="10.200.12.2/32",
            endpoint="vpn.example.com",
            port=51821,
            keepalive=25,
            firewall_config="remote_user",
            description="Remote user peer",
        )

        assert peer.endpoint == "vpn.example.com"
        assert peer.port == 51821
        assert peer.keepalive == 25
        assert peer.firewall_config_display == "Remote User"

    def test_create_peer_site_to_site(
        self, test_network: Network, cleanup_interfaces: list[int]
    ) -> None:
        """Test creating a site-to-site peer."""
        iface = test_network.wireguard.create(
            name="pytest-wg-s2s",
            ip_address="10.200.13.1/24",
        )
        cleanup_interfaces.append(iface.key)

        peer = iface.peers.create(
            name="pytest-s2s-peer",
            peer_ip="10.200.13.2",
            public_key=generate_fake_pubkey(),
            allowed_ips="192.168.50.0/24,192.168.51.0/24",
            endpoint="203.0.113.100",
            firewall_config="site_to_site",
        )

        assert peer.firewall_config_display == "Site-to-Site"
        assert "192.168.50.0/24" in peer.allowed_ips
        assert "192.168.51.0/24" in peer.allowed_ips

    def test_get_peer_by_key(self, test_network: Network, cleanup_interfaces: list[int]) -> None:
        """Test getting a peer by key."""
        iface = test_network.wireguard.create(
            name="pytest-wg-getpeer",
            ip_address="10.200.14.1/24",
        )
        cleanup_interfaces.append(iface.key)

        created = iface.peers.create(
            name="pytest-peer-bykey",
            peer_ip="10.200.14.2",
            public_key=generate_fake_pubkey(),
            allowed_ips="10.200.14.2/32",
        )

        fetched = iface.peers.get(created.key)

        assert fetched.key == created.key
        assert fetched.name == created.name

    def test_get_peer_by_name(self, test_network: Network, cleanup_interfaces: list[int]) -> None:
        """Test getting a peer by name."""
        iface = test_network.wireguard.create(
            name="pytest-wg-getpeer-name",
            ip_address="10.200.15.1/24",
        )
        cleanup_interfaces.append(iface.key)

        test_name = "pytest-peer-byname"
        created = iface.peers.create(
            name=test_name,
            peer_ip="10.200.15.2",
            public_key=generate_fake_pubkey(),
            allowed_ips="10.200.15.2/32",
        )

        fetched = iface.peers.get(name=test_name)

        assert fetched.key == created.key
        assert fetched.name == test_name

    def test_update_peer(self, test_network: Network, cleanup_interfaces: list[int]) -> None:
        """Test updating a peer."""
        iface = test_network.wireguard.create(
            name="pytest-wg-updpeer",
            ip_address="10.200.16.1/24",
        )
        cleanup_interfaces.append(iface.key)

        peer = iface.peers.create(
            name="pytest-peer-update",
            peer_ip="10.200.16.2",
            public_key=generate_fake_pubkey(),
            allowed_ips="10.200.16.2/32",
            keepalive=0,
        )

        updated = iface.peers.update(
            peer.key,
            keepalive=30,
            description="Updated peer",
        )

        assert updated.keepalive == 30
        assert updated.get("description") == "Updated peer"

    def test_multiple_peers(self, test_network: Network, cleanup_interfaces: list[int]) -> None:
        """Test creating multiple peers on one interface."""
        iface = test_network.wireguard.create(
            name="pytest-wg-multipeer",
            ip_address="10.200.17.1/24",
        )
        cleanup_interfaces.append(iface.key)

        # Create multiple peers
        iface.peers.create(
            name="pytest-peer-1",
            peer_ip="10.200.17.2",
            public_key=generate_fake_pubkey(),
            allowed_ips="10.200.17.2/32",
        )
        iface.peers.create(
            name="pytest-peer-2",
            peer_ip="10.200.17.3",
            public_key=generate_fake_pubkey(),
            allowed_ips="10.200.17.3/32",
        )
        iface.peers.create(
            name="pytest-peer-3",
            peer_ip="10.200.17.4",
            public_key=generate_fake_pubkey(),
            allowed_ips="10.200.17.4/32",
        )

        # Verify all exist
        peers = iface.peers.list()
        assert len(peers) == 3

        peer_names = {p.name for p in peers}
        assert "pytest-peer-1" in peer_names
        assert "pytest-peer-2" in peer_names
        assert "pytest-peer-3" in peer_names

    def test_peer_get_config_not_auto_generated(
        self, test_network: Network, cleanup_interfaces: list[int]
    ) -> None:
        """Test get_config raises ValueError for non-auto-generated peers."""
        iface = test_network.wireguard.create(
            name="pytest-wg-noconfig",
            ip_address="10.200.18.1/24",
        )
        cleanup_interfaces.append(iface.key)

        peer = iface.peers.create(
            name="pytest-peer-noconfig",
            peer_ip="10.200.18.2",
            public_key=generate_fake_pubkey(),
            allowed_ips="10.200.18.2/32",
        )

        # This peer wasn't created with auto-generate, so config should fail
        with pytest.raises(ValueError, match="Configuration not available"):
            peer.get_config()

    def test_delete_interface_removes_peers(
        self, test_network: Network, cleanup_interfaces: list[int]
    ) -> None:
        """Test that deleting an interface also removes its peers."""
        iface = test_network.wireguard.create(
            name="pytest-wg-cascade",
            ip_address="10.200.19.1/24",
        )
        cleanup_interfaces.append(iface.key)

        # Create peers
        iface.peers.create(
            name="pytest-cascade-1",
            peer_ip="10.200.19.2",
            public_key=generate_fake_pubkey(),
            allowed_ips="10.200.19.2/32",
        )
        iface.peers.create(
            name="pytest-cascade-2",
            peer_ip="10.200.19.3",
            public_key=generate_fake_pubkey(),
            allowed_ips="10.200.19.3/32",
        )

        # Verify peers exist
        peers = iface.peers.list()
        assert len(peers) == 2

        # Delete the interface
        test_network.wireguard.delete(iface.key)
        cleanup_interfaces.remove(iface.key)

        # Interface should be gone
        with pytest.raises(NotFoundError):
            test_network.wireguard.get(iface.key)
