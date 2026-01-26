"""Integration tests for IPSecConnectionManager and IPSecPolicyManager.

These tests require a live VergeOS system.
Configure with environment variables:
    VERGE_HOST, VERGE_USERNAME, VERGE_PASSWORD, VERGE_VERIFY_SSL
"""

from __future__ import annotations

import contextlib
import os

import pytest

from pyvergeos import VergeClient
from pyvergeos.exceptions import NotFoundError
from pyvergeos.resources.ipsec import IPSecConnection
from pyvergeos.resources.networks import Network

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
    """Get an external network to test IPSec on.

    IPSec is typically configured on external networks.
    """
    # Try to get External network
    try:
        return client.networks.get(name="External")
    except NotFoundError:
        pass

    # Fall back to first external network
    networks = client.networks.list_external()
    if not networks:
        pytest.skip("No external networks available for IPSec testing")
    return networks[0]


@pytest.fixture
def cleanup_connections(test_network: Network):
    """Fixture to track and cleanup test IPSec connections."""
    created_keys: list[int] = []

    yield created_keys

    # Cleanup any connections we created (also removes policies)
    for key in created_keys:
        with contextlib.suppress(NotFoundError):
            test_network.ipsec.delete(key)


class TestIPSecConnectionManagerIntegration:
    """Integration tests for IPSecConnectionManager."""

    def test_list_connections(self, test_network: Network) -> None:
        """Test listing IPSec connections on a network."""
        connections = test_network.ipsec.list()

        assert isinstance(connections, list)
        for conn in connections:
            assert isinstance(conn, IPSecConnection)
            assert conn.key is not None
            assert conn.name is not None

    def test_create_and_delete_connection(
        self, test_network: Network, cleanup_connections: list[int]
    ) -> None:
        """Test creating and deleting an IPSec connection."""
        # Create a test connection
        conn = test_network.ipsec.create(
            name="pytest-ipsec-001",
            remote_gateway="203.0.113.1",
            pre_shared_key="TestPSK12345!",
            description="Integration test connection",
        )
        cleanup_connections.append(conn.key)

        assert conn.name == "pytest-ipsec-001"
        assert conn.remote_gateway == "203.0.113.1"
        assert conn.is_enabled is True
        assert conn.auth_method_display == "Pre-Shared Key"

        # Delete the connection
        test_network.ipsec.delete(conn.key)
        cleanup_connections.remove(conn.key)

        # Verify it's gone
        with pytest.raises(NotFoundError):
            test_network.ipsec.get(conn.key)

    def test_create_with_options(
        self, test_network: Network, cleanup_connections: list[int]
    ) -> None:
        """Test creating a connection with various options."""
        conn = test_network.ipsec.create(
            name="pytest-ipsec-opts",
            remote_gateway="203.0.113.2",
            pre_shared_key="TestPSK12345!",
            key_exchange="ikev2",
            connection_mode="start",
            dpd_action="restart",
            dpd_delay=60,
            force_udp_encap=True,
            description="IKEv2 test connection",
        )
        cleanup_connections.append(conn.key)

        assert conn.key_exchange_display == "IKEv2"
        assert conn.connection_mode_display == "Always Start"
        assert conn.dpd_action_display == "Restart"
        assert conn.get("dpddelay") == 60
        assert conn.get("forceencaps") is True

    def test_get_connection_by_key(
        self, test_network: Network, cleanup_connections: list[int]
    ) -> None:
        """Test getting a connection by key."""
        created = test_network.ipsec.create(
            name="pytest-ipsec-bykey",
            remote_gateway="203.0.113.3",
            pre_shared_key="TestPSK12345!",
        )
        cleanup_connections.append(created.key)

        fetched = test_network.ipsec.get(created.key)

        assert fetched.key == created.key
        assert fetched.name == created.name
        assert fetched.remote_gateway == created.remote_gateway

    def test_get_connection_by_name(
        self, test_network: Network, cleanup_connections: list[int]
    ) -> None:
        """Test getting a connection by name."""
        test_name = "pytest-ipsec-byname"
        created = test_network.ipsec.create(
            name=test_name,
            remote_gateway="203.0.113.4",
            pre_shared_key="TestPSK12345!",
        )
        cleanup_connections.append(created.key)

        fetched = test_network.ipsec.get(name=test_name)

        assert fetched.key == created.key
        assert fetched.name == test_name

    def test_get_connection_not_found(self, test_network: Network) -> None:
        """Test getting a non-existent connection raises NotFoundError."""
        with pytest.raises(NotFoundError):
            test_network.ipsec.get(999999)

        with pytest.raises(NotFoundError):
            test_network.ipsec.get(name="nonexistent-connection-xyz")

    def test_update_connection(self, test_network: Network, cleanup_connections: list[int]) -> None:
        """Test updating a connection."""
        conn = test_network.ipsec.create(
            name="pytest-ipsec-update",
            remote_gateway="203.0.113.5",
            pre_shared_key="TestPSK12345!",
            description="Original description",
        )
        cleanup_connections.append(conn.key)

        updated = test_network.ipsec.update(
            conn.key,
            description="Updated description",
            dpd_delay=90,
        )

        assert updated.get("description") == "Updated description"
        assert updated.get("dpddelay") == 90


class TestIPSecPolicyManagerIntegration:
    """Integration tests for IPSecPolicyManager."""

    def test_list_policies(self, test_network: Network, cleanup_connections: list[int]) -> None:
        """Test listing policies for a connection."""
        conn = test_network.ipsec.create(
            name="pytest-ipsec-policies",
            remote_gateway="203.0.113.10",
            pre_shared_key="TestPSK12345!",
        )
        cleanup_connections.append(conn.key)

        policies = conn.policies.list()

        assert isinstance(policies, list)
        # New connection has no policies
        assert len(policies) == 0

    def test_create_and_delete_policy(
        self, test_network: Network, cleanup_connections: list[int]
    ) -> None:
        """Test creating and deleting a policy."""
        conn = test_network.ipsec.create(
            name="pytest-ipsec-policy-crud",
            remote_gateway="203.0.113.11",
            pre_shared_key="TestPSK12345!",
        )
        cleanup_connections.append(conn.key)

        # Create a policy
        policy = conn.policies.create(
            name="pytest-policy-001",
            local_network="10.0.0.0/24",
            remote_network="192.168.100.0/24",
            description="Test policy",
        )

        assert policy.name == "pytest-policy-001"
        assert policy.local_network == "10.0.0.0/24"
        assert policy.remote_network == "192.168.100.0/24"
        assert policy.is_enabled is True
        assert policy.mode_display == "Tunnel"
        assert policy.protocol_display == "ESP (Encrypted)"

        # Verify it's in the list
        policies = conn.policies.list()
        assert len(policies) == 1
        assert policies[0].name == "pytest-policy-001"

        # Delete the policy
        conn.policies.delete(policy.key)

        # Verify it's gone
        policies = conn.policies.list()
        assert len(policies) == 0

    def test_create_policy_with_options(
        self, test_network: Network, cleanup_connections: list[int]
    ) -> None:
        """Test creating a policy with various options."""
        conn = test_network.ipsec.create(
            name="pytest-ipsec-policy-opts",
            remote_gateway="203.0.113.12",
            pre_shared_key="TestPSK12345!",
        )
        cleanup_connections.append(conn.key)

        policy = conn.policies.create(
            name="pytest-policy-opts",
            local_network="10.10.0.0/16",
            remote_network="172.16.0.0/12",
            lifetime=7200,
            ciphers="aes256-sha512-modp4096",
        )

        assert policy.get("lifetime") == 7200
        assert policy.get("ciphers") == "aes256-sha512-modp4096"

    def test_get_policy_by_key(self, test_network: Network, cleanup_connections: list[int]) -> None:
        """Test getting a policy by key."""
        conn = test_network.ipsec.create(
            name="pytest-ipsec-getpolicy",
            remote_gateway="203.0.113.13",
            pre_shared_key="TestPSK12345!",
        )
        cleanup_connections.append(conn.key)

        created = conn.policies.create(
            name="pytest-policy-bykey",
            local_network="10.0.0.0/8",
        )

        fetched = conn.policies.get(created.key)

        assert fetched.key == created.key
        assert fetched.name == created.name

    def test_get_policy_by_name(
        self, test_network: Network, cleanup_connections: list[int]
    ) -> None:
        """Test getting a policy by name."""
        conn = test_network.ipsec.create(
            name="pytest-ipsec-getpolicy-name",
            remote_gateway="203.0.113.14",
            pre_shared_key="TestPSK12345!",
        )
        cleanup_connections.append(conn.key)

        test_name = "pytest-policy-byname"
        created = conn.policies.create(
            name=test_name,
            local_network="10.0.0.0/8",
        )

        fetched = conn.policies.get(name=test_name)

        assert fetched.key == created.key
        assert fetched.name == test_name

    def test_update_policy(self, test_network: Network, cleanup_connections: list[int]) -> None:
        """Test updating a policy."""
        conn = test_network.ipsec.create(
            name="pytest-ipsec-updpolicy",
            remote_gateway="203.0.113.15",
            pre_shared_key="TestPSK12345!",
        )
        cleanup_connections.append(conn.key)

        policy = conn.policies.create(
            name="pytest-policy-update",
            local_network="10.0.0.0/24",
            remote_network="192.168.0.0/24",
            lifetime=3600,
        )

        updated = conn.policies.update(
            policy.key,
            lifetime=7200,
            description="Updated policy",
        )

        assert updated.get("lifetime") == 7200
        assert updated.get("description") == "Updated policy"

    def test_multiple_policies(self, test_network: Network, cleanup_connections: list[int]) -> None:
        """Test creating multiple policies on one connection."""
        conn = test_network.ipsec.create(
            name="pytest-ipsec-multipol",
            remote_gateway="203.0.113.16",
            pre_shared_key="TestPSK12345!",
        )
        cleanup_connections.append(conn.key)

        # Create multiple policies
        conn.policies.create(
            name="pytest-policy-lan1",
            local_network="10.0.0.0/24",
            remote_network="192.168.1.0/24",
        )
        conn.policies.create(
            name="pytest-policy-lan2",
            local_network="10.0.1.0/24",
            remote_network="192.168.2.0/24",
        )

        # Verify both exist
        policies = conn.policies.list()
        assert len(policies) == 2

        policy_names = {p.name for p in policies}
        assert "pytest-policy-lan1" in policy_names
        assert "pytest-policy-lan2" in policy_names
