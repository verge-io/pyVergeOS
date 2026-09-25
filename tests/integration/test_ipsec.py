"""Integration tests for IPSecConnectionManager and IPSecPolicyManager.

These tests require a live VergeOS system.
Configure with environment variables:
    VERGE_HOST, VERGE_USERNAME, VERGE_PASSWORD

TLS verification matches the shared live_client fixture (disabled) so
self-signed lab certificates work.
"""

from __future__ import annotations

import contextlib
import time
from collections.abc import Generator
from typing import Any

import pytest

from pyvergeos import VergeClient
from pyvergeos.exceptions import NotFoundError, VergeError
from pyvergeos.resources.ipsec import IPSecConnection
from pyvergeos.resources.networks import Network
from tests.integration.live_support import create_disposable_network, destroy_network

# Skip all tests in this module if not running integration tests
pytestmark = pytest.mark.integration


def _ipsec_config_records(client: VergeClient, network: Network) -> list[dict[str, Any]]:
    """Return vnet_ipsecs rows for a network. Empty when none exist."""
    try:
        response = client._request(
            "GET",
            "vnet_ipsecs",
            params={"filter": f"vnet eq {network.key}", "fields": "$key"},
        )
    except VergeError:
        return []
    if isinstance(response, list):
        return [row for row in response if isinstance(row, dict)]
    if isinstance(response, dict):
        return [response]
    return []


def remove_ipsec_config(client: VergeClient, network: Network) -> None:
    """Disable, apply, and delete connections plus any vnet_ipsecs row.

    ``IPSecConnectionManager.create`` auto-creates and enables a vnet_ipsecs
    config. Deleting connections leaves that config in place.
    """
    try:
        connections = list(network.ipsec.list())
    except VergeError:
        connections = []
    for conn in connections:
        with contextlib.suppress(VergeError):
            network.ipsec.update(conn.key, enabled=False)
        with contextlib.suppress(VergeError):
            network.ipsec.delete(conn.key)
    with contextlib.suppress(VergeError):
        network.apply_rules()

    for record in _ipsec_config_records(client, network):
        key = record.get("$key")
        if key is None:
            continue
        ipsec_key = int(key)
        with contextlib.suppress(VergeError):
            client._request("PUT", f"vnet_ipsecs/{ipsec_key}", json_data={"enabled": False})
        with contextlib.suppress(VergeError):
            network.apply_rules()
        with contextlib.suppress(VergeError):
            client._request("DELETE", f"vnet_ipsecs/{ipsec_key}")
    with contextlib.suppress(VergeError):
        network.apply_rules()


@pytest.fixture(scope="module")
def client(live_client_module: VergeClient) -> VergeClient:
    """Live client with the same TLS settings as the shared live_client fixture."""
    return live_client_module


@pytest.fixture(scope="module")
def test_network(client: VergeClient) -> Generator[Network, None, None]:
    """Disposable internal network for IPSec tests.

    External is often the management vnet. Creating a connection enables
    vnet_ipsecs on that network, so these tests must not use it.
    """
    network = create_disposable_network(client, prefix="pytest-ipsec")
    try:
        try:
            network.power_on()
        except VergeError:
            pass
        else:
            time.sleep(3)
        yield client.networks.get(network.key)
    finally:
        remove_ipsec_config(client, network)
        destroy_network(client, network)


@pytest.fixture
def cleanup_connections(test_network: Network, client: VergeClient):
    """Fixture to track and cleanup test IPSec connections and vnet_ipsecs."""
    created_keys: list[int] = []

    yield created_keys

    # Cleanup any connections we created (also removes policies).
    for key in created_keys:
        with contextlib.suppress(VergeError):
            test_network.ipsec.update(key, enabled=False)
        with contextlib.suppress(VergeError):
            test_network.ipsec.delete(key)
    # Drop the auto-created vnet_ipsecs row so the network is not left enabled.
    remove_ipsec_config(client, test_network)


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
