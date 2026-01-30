"""Integration tests for network routing protocol managers.

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
from pyvergeos.resources.networks import Network
from pyvergeos.resources.routing import (
    BGPIPCommand,
    BGPRouteMap,
    BGPRouter,
    BGPRouterCommand,
    EIGRPRouter,
    EIGRPRouterCommand,
    OSPFCommand,
)

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
    """Get an external network to test routing on.

    Routing protocols are typically configured on external networks.
    """
    try:
        return client.networks.get(name="External")
    except NotFoundError:
        pass

    networks = client.networks.list_external()
    if not networks:
        pytest.skip("No external networks available for routing testing")
    return networks[0]


# =============================================================================
# BGP Router Tests
# =============================================================================


@pytest.fixture
def cleanup_bgp_routers(test_network: Network):
    """Fixture to track and cleanup test BGP routers."""
    created_keys: list[int] = []

    yield created_keys

    routing = test_network.routing
    for key in created_keys:
        with contextlib.suppress(NotFoundError):
            # Delete commands first
            router = routing.bgp_routers.get(key=key)
            for cmd in router.commands.list():
                router.commands.delete(cmd.key)
            routing.bgp_routers.delete(key)


class TestBGPRouterIntegration:
    """Integration tests for BGP router management."""

    def test_list_bgp_routers(self, test_network: Network) -> None:
        """Test listing BGP routers on a network."""
        routing = test_network.routing
        routers = routing.bgp_routers.list()

        assert isinstance(routers, list)
        for router in routers:
            assert isinstance(router, BGPRouter)
            assert router.key is not None

    def test_create_and_delete_bgp_router(
        self, test_network: Network, cleanup_bgp_routers: list[int]
    ) -> None:
        """Test creating and deleting a BGP router."""
        routing = test_network.routing

        router = routing.bgp_routers.create(asn=64900)
        cleanup_bgp_routers.append(router.key)

        assert router.key is not None
        assert router.get("asn") == 64900

        # Delete the router
        routing.bgp_routers.delete(router.key)
        cleanup_bgp_routers.remove(router.key)

        # Verify it's gone
        with pytest.raises(NotFoundError):
            routing.bgp_routers.get(key=router.key)

    def test_get_bgp_router_by_key(
        self, test_network: Network, cleanup_bgp_routers: list[int]
    ) -> None:
        """Test getting a BGP router by key."""
        routing = test_network.routing

        created = routing.bgp_routers.create(asn=64901)
        cleanup_bgp_routers.append(created.key)

        fetched = routing.bgp_routers.get(key=created.key)

        assert fetched.key == created.key
        assert fetched.get("asn") == 64901

    def test_bgp_router_commands_crud(
        self, test_network: Network, cleanup_bgp_routers: list[int]
    ) -> None:
        """Test creating, listing, updating, and deleting BGP router commands."""
        routing = test_network.routing

        router = routing.bgp_routers.create(asn=64902)
        cleanup_bgp_routers.append(router.key)

        # Create commands
        cmd1 = router.commands.create(
            command="neighbor",
            params="10.0.0.2 remote-as 65000",
        )
        assert isinstance(cmd1, BGPRouterCommand)
        assert cmd1.get("command") == "neighbor"
        assert cmd1.get("params") == "10.0.0.2 remote-as 65000"

        cmd2 = router.commands.create(
            command="network",
            params="192.168.0.0/24",
        )

        # List commands
        commands = router.commands.list()
        assert len(commands) == 2

        # Update command
        updated = router.commands.update(cmd1.key, params="10.0.0.3 remote-as 65001")
        assert updated.get("params") == "10.0.0.3 remote-as 65001"

        # Delete commands
        router.commands.delete(cmd1.key)
        router.commands.delete(cmd2.key)

        # Verify deleted
        commands = router.commands.list()
        assert len(commands) == 0


# =============================================================================
# BGP Route Map Tests
# =============================================================================


@pytest.fixture
def cleanup_bgp_route_maps(test_network: Network):
    """Fixture to track and cleanup test BGP route maps."""
    created_keys: list[int] = []

    yield created_keys

    routing = test_network.routing
    for key in created_keys:
        with contextlib.suppress(NotFoundError):
            route_map = routing.bgp_route_maps.get(key=key)
            for cmd in route_map.commands.list():
                route_map.commands.delete(cmd.key)
            routing.bgp_route_maps.delete(key)


class TestBGPRouteMapIntegration:
    """Integration tests for BGP route map management."""

    def test_list_bgp_route_maps(self, test_network: Network) -> None:
        """Test listing BGP route maps on a network."""
        routing = test_network.routing
        route_maps = routing.bgp_route_maps.list()

        assert isinstance(route_maps, list)
        for rm in route_maps:
            assert isinstance(rm, BGPRouteMap)
            assert rm.key is not None

    def test_create_and_delete_route_map(
        self, test_network: Network, cleanup_bgp_route_maps: list[int]
    ) -> None:
        """Test creating and deleting a BGP route map."""
        routing = test_network.routing

        route_map = routing.bgp_route_maps.create(
            tag="PYTEST-FILTER",
            sequence=10,
            permit=True,
        )
        cleanup_bgp_route_maps.append(route_map.key)

        assert route_map.key is not None
        assert route_map.get("tag") == "PYTEST-FILTER"
        assert route_map.get("sequence") == 10
        assert route_map.get("permit") is True

        # Delete
        routing.bgp_route_maps.delete(route_map.key)
        cleanup_bgp_route_maps.remove(route_map.key)

        # Verify gone
        with pytest.raises(NotFoundError):
            routing.bgp_route_maps.get(key=route_map.key)

    def test_route_map_with_commands(
        self, test_network: Network, cleanup_bgp_route_maps: list[int]
    ) -> None:
        """Test route map with match/set commands."""
        routing = test_network.routing

        route_map = routing.bgp_route_maps.create(
            tag="PYTEST-MATCH",
            sequence=20,
            permit=True,
        )
        cleanup_bgp_route_maps.append(route_map.key)

        # Add match command
        match_cmd = route_map.commands.create(
            command="match",
            params="ip address prefix-list TEST-PREFIXES",
        )
        assert match_cmd.get("command") == "match"

        # Add set command
        set_cmd = route_map.commands.create(
            command="set",
            params="local-preference 150",
        )
        assert set_cmd.get("command") == "set"

        # List commands
        commands = route_map.commands.list()
        assert len(commands) == 2

        # Cleanup commands
        route_map.commands.delete(match_cmd.key)
        route_map.commands.delete(set_cmd.key)

    def test_multiple_route_map_entries(
        self, test_network: Network, cleanup_bgp_route_maps: list[int]
    ) -> None:
        """Test creating multiple route map entries with same tag."""
        routing = test_network.routing

        # Create permit entry
        permit_entry = routing.bgp_route_maps.create(
            tag="PYTEST-MULTI",
            sequence=10,
            permit=True,
        )
        cleanup_bgp_route_maps.append(permit_entry.key)

        # Create deny entry
        deny_entry = routing.bgp_route_maps.create(
            tag="PYTEST-MULTI",
            sequence=100,
            permit=False,
        )
        cleanup_bgp_route_maps.append(deny_entry.key)

        # Verify both exist
        route_maps = routing.bgp_route_maps.list()
        pytest_maps = [rm for rm in route_maps if rm.get("tag") == "PYTEST-MULTI"]
        assert len(pytest_maps) == 2


# =============================================================================
# BGP IP Command Tests
# =============================================================================


@pytest.fixture
def cleanup_bgp_ip_commands(test_network: Network):
    """Fixture to track and cleanup test BGP IP commands."""
    created_keys: list[int] = []

    yield created_keys

    routing = test_network.routing
    for key in created_keys:
        with contextlib.suppress(NotFoundError):
            routing.bgp_ip_commands.delete(key)


class TestBGPIPCommandIntegration:
    """Integration tests for BGP IP command management."""

    def test_list_bgp_ip_commands(self, test_network: Network) -> None:
        """Test listing BGP IP commands on a network."""
        routing = test_network.routing
        commands = routing.bgp_ip_commands.list()

        assert isinstance(commands, list)
        for cmd in commands:
            assert isinstance(cmd, BGPIPCommand)
            assert cmd.key is not None

    def test_create_prefix_list(
        self, test_network: Network, cleanup_bgp_ip_commands: list[int]
    ) -> None:
        """Test creating a prefix-list command."""
        routing = test_network.routing

        cmd = routing.bgp_ip_commands.create(
            command="prefix-list",
            params="PYTEST-PREFIXES seq 10 permit 10.0.0.0/8 le 24",
        )
        cleanup_bgp_ip_commands.append(cmd.key)

        assert cmd.key is not None
        assert cmd.get("command") == "prefix-list"
        assert "PYTEST-PREFIXES" in cmd.get("params")

    def test_create_as_path(
        self, test_network: Network, cleanup_bgp_ip_commands: list[int]
    ) -> None:
        """Test creating an AS-path access-list command."""
        routing = test_network.routing

        cmd = routing.bgp_ip_commands.create(
            command="as-path",
            params="access-list 10 permit ^65000_",
        )
        cleanup_bgp_ip_commands.append(cmd.key)

        assert cmd.get("command") == "as-path"

    def test_delete_ip_command(
        self, test_network: Network, cleanup_bgp_ip_commands: list[int]
    ) -> None:
        """Test deleting a BGP IP command."""
        routing = test_network.routing

        cmd = routing.bgp_ip_commands.create(
            command="prefix-list",
            params="PYTEST-DELETE seq 10 deny any",
        )

        # Delete immediately
        routing.bgp_ip_commands.delete(cmd.key)

        # Verify gone
        with pytest.raises(NotFoundError):
            routing.bgp_ip_commands.get(key=cmd.key)


# =============================================================================
# OSPF Command Tests
# =============================================================================


@pytest.fixture
def cleanup_ospf_commands(test_network: Network):
    """Fixture to track and cleanup test OSPF commands."""
    created_keys: list[int] = []

    yield created_keys

    routing = test_network.routing
    for key in created_keys:
        with contextlib.suppress(NotFoundError):
            routing.ospf_commands.delete(key)


class TestOSPFCommandIntegration:
    """Integration tests for OSPF command management."""

    def test_list_ospf_commands(self, test_network: Network) -> None:
        """Test listing OSPF commands on a network."""
        routing = test_network.routing
        commands = routing.ospf_commands.list()

        assert isinstance(commands, list)
        for cmd in commands:
            assert isinstance(cmd, OSPFCommand)
            assert cmd.key is not None

    def test_create_ospf_router_id(
        self, test_network: Network, cleanup_ospf_commands: list[int]
    ) -> None:
        """Test creating an OSPF router-id command."""
        routing = test_network.routing

        cmd = routing.ospf_commands.create(
            command="router-id",
            params="10.255.255.1",
        )
        cleanup_ospf_commands.append(cmd.key)

        assert cmd.key is not None
        assert cmd.get("command") == "router-id"
        assert cmd.get("params") == "10.255.255.1"

    def test_create_ospf_network(
        self, test_network: Network, cleanup_ospf_commands: list[int]
    ) -> None:
        """Test creating an OSPF network command."""
        routing = test_network.routing

        cmd = routing.ospf_commands.create(
            command="network",
            params="10.0.0.0/24 area 0",
        )
        cleanup_ospf_commands.append(cmd.key)

        assert cmd.get("command") == "network"

    def test_update_ospf_command(
        self, test_network: Network, cleanup_ospf_commands: list[int]
    ) -> None:
        """Test updating an OSPF command."""
        routing = test_network.routing

        cmd = routing.ospf_commands.create(
            command="router-id",
            params="10.255.255.2",
        )
        cleanup_ospf_commands.append(cmd.key)

        updated = routing.ospf_commands.update(
            cmd.key,
            params="10.255.255.100",
        )

        assert updated.get("params") == "10.255.255.100"

    def test_ospf_multiple_commands(
        self, test_network: Network, cleanup_ospf_commands: list[int]
    ) -> None:
        """Test creating multiple OSPF commands."""
        routing = test_network.routing

        cmd1 = routing.ospf_commands.create(
            command="router-id",
            params="10.255.255.3",
        )
        cleanup_ospf_commands.append(cmd1.key)

        cmd2 = routing.ospf_commands.create(
            command="network",
            params="172.16.0.0/16 area 1",
        )
        cleanup_ospf_commands.append(cmd2.key)

        cmd3 = routing.ospf_commands.create(
            command="redistribute",
            params="connected",
        )
        cleanup_ospf_commands.append(cmd3.key)

        # Verify all exist
        commands = routing.ospf_commands.list()
        our_commands = [c for c in commands if c.key in cleanup_ospf_commands]
        assert len(our_commands) == 3


# =============================================================================
# EIGRP Router Tests
# =============================================================================


@pytest.fixture
def cleanup_eigrp_routers(test_network: Network):
    """Fixture to track and cleanup test EIGRP routers."""
    created_keys: list[int] = []

    yield created_keys

    routing = test_network.routing
    for key in created_keys:
        with contextlib.suppress(NotFoundError):
            router = routing.eigrp_routers.get(key=key)
            for cmd in router.commands.list():
                router.commands.delete(cmd.key)
            routing.eigrp_routers.delete(key)


class TestEIGRPRouterIntegration:
    """Integration tests for EIGRP router management."""

    def test_list_eigrp_routers(self, test_network: Network) -> None:
        """Test listing EIGRP routers on a network."""
        routing = test_network.routing
        routers = routing.eigrp_routers.list()

        assert isinstance(routers, list)
        for router in routers:
            assert isinstance(router, EIGRPRouter)
            assert router.key is not None

    def test_create_and_delete_eigrp_router(
        self, test_network: Network, cleanup_eigrp_routers: list[int]
    ) -> None:
        """Test creating and deleting an EIGRP router."""
        routing = test_network.routing

        router = routing.eigrp_routers.create(asn=900)
        cleanup_eigrp_routers.append(router.key)

        assert router.key is not None
        assert router.get("asn") == 900

        # Delete
        routing.eigrp_routers.delete(router.key)
        cleanup_eigrp_routers.remove(router.key)

        # Verify gone
        with pytest.raises(NotFoundError):
            routing.eigrp_routers.get(key=router.key)

    def test_get_eigrp_router_by_key(
        self, test_network: Network, cleanup_eigrp_routers: list[int]
    ) -> None:
        """Test getting an EIGRP router by key."""
        routing = test_network.routing

        created = routing.eigrp_routers.create(asn=901)
        cleanup_eigrp_routers.append(created.key)

        fetched = routing.eigrp_routers.get(key=created.key)

        assert fetched.key == created.key
        assert fetched.get("asn") == 901

    def test_eigrp_router_commands(
        self, test_network: Network, cleanup_eigrp_routers: list[int]
    ) -> None:
        """Test EIGRP router command management."""
        routing = test_network.routing

        router = routing.eigrp_routers.create(asn=902)
        cleanup_eigrp_routers.append(router.key)

        # Create commands
        cmd1 = router.commands.create(
            command="network",
            params="10.0.0.0/8",
        )
        assert isinstance(cmd1, EIGRPRouterCommand)
        assert cmd1.get("command") == "network"

        cmd2 = router.commands.create(
            command="redistribute",
            params="connected",
        )

        # List commands
        commands = router.commands.list()
        assert len(commands) == 2

        # Delete commands
        router.commands.delete(cmd1.key)
        router.commands.delete(cmd2.key)

        # Verify deleted
        commands = router.commands.list()
        assert len(commands) == 0


# =============================================================================
# Routing Manager Access Tests
# =============================================================================


class TestNetworkRoutingAccess:
    """Test accessing routing from network object."""

    def test_routing_property_access(self, test_network: Network) -> None:
        """Test accessing routing via network.routing property."""
        routing = test_network.routing

        assert routing is not None
        assert hasattr(routing, "bgp_routers")
        assert hasattr(routing, "bgp_interfaces")
        assert hasattr(routing, "bgp_route_maps")
        assert hasattr(routing, "bgp_ip_commands")
        assert hasattr(routing, "ospf_commands")
        assert hasattr(routing, "eigrp_routers")

    def test_routing_managers_are_functional(self, test_network: Network) -> None:
        """Test that all routing managers can list resources."""
        routing = test_network.routing

        # All managers should return lists (possibly empty)
        assert isinstance(routing.bgp_routers.list(), list)
        assert isinstance(routing.bgp_interfaces.list(), list)
        assert isinstance(routing.bgp_route_maps.list(), list)
        assert isinstance(routing.bgp_ip_commands.list(), list)
        assert isinstance(routing.ospf_commands.list(), list)
        assert isinstance(routing.eigrp_routers.list(), list)
