"""Unit tests for routing protocol managers (BGP, OSPF, EIGRP)."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from pyvergeos.exceptions import NotFoundError
from pyvergeos.resources.networks import Network
from pyvergeos.resources.routing import (
    BGPInterface,
    BGPInterfaceCommandManager,
    BGPInterfaceManager,
    BGPIPCommand,
    BGPIPCommandManager,
    BGPRouteMap,
    BGPRouteMapCommandManager,
    BGPRouteMapManager,
    BGPRouter,
    BGPRouterCommand,
    BGPRouterCommandManager,
    BGPRouterManager,
    EIGRPRouter,
    EIGRPRouterCommand,
    EIGRPRouterCommandManager,
    EIGRPRouterManager,
    NetworkRoutingManager,
    OSPFCommand,
    OSPFCommandManager,
)


@pytest.fixture
def mock_client() -> MagicMock:
    """Create a mock VergeClient."""
    client = MagicMock()
    client._request = MagicMock()
    return client


@pytest.fixture
def mock_network(mock_client: MagicMock) -> Network:
    """Create a mock Network object."""
    network_data = {
        "$key": 8,
        "name": "Internal",
        "type": "internal",
    }
    manager = MagicMock()
    manager._client = mock_client
    return Network(network_data, manager)


@pytest.fixture
def routing_manager(mock_client: MagicMock, mock_network: Network) -> NetworkRoutingManager:
    """Create a NetworkRoutingManager with mock dependencies."""
    return NetworkRoutingManager(mock_client, mock_network)


# =============================================================================
# Sample Data Fixtures
# =============================================================================


@pytest.fixture
def sample_bgp_router_data() -> dict[str, Any]:
    """Sample BGP router data from API."""
    return {
        "$key": 1,
        "bgp": 1,
        "asn": 65000,
    }


@pytest.fixture
def sample_bgp_router_command_data() -> dict[str, Any]:
    """Sample BGP router command data from API."""
    return {
        "$key": 1,
        "bgp_router": 1,
        "orderid": 1,
        "enabled": True,
        "no": False,
        "command": "neighbor",
        "params": "192.168.1.1 remote-as 65001",
    }


@pytest.fixture
def sample_bgp_interface_data() -> dict[str, Any]:
    """Sample BGP interface data from API."""
    return {
        "$key": 1,
        "bgp": 1,
        "name": "peer-1",
        "description": "BGP peering interface",
        "ipaddress": "10.255.0.1",
        "network": "10.255.0.0/30",
        "mtu": 9000,
        "layer2_type": "vlan",
        "layer2_id": 100,
        "interface_vnet": 3,
        "bgp_vnet": 10,
        "nic": 5,
    }


@pytest.fixture
def sample_bgp_interface_command_data() -> dict[str, Any]:
    """Sample BGP interface command data from API."""
    return {
        "$key": 1,
        "bgp_interface": 1,
        "orderid": 1,
        "command": "ospf",
        "params": "cost 10",
    }


@pytest.fixture
def sample_bgp_routemap_data() -> dict[str, Any]:
    """Sample BGP route map data from API."""
    return {
        "$key": 1,
        "bgp": 1,
        "tag": "IMPORT-FROM-ISP",
        "permit": True,
        "sequence": 10,
    }


@pytest.fixture
def sample_bgp_routemap_command_data() -> dict[str, Any]:
    """Sample BGP route map command data from API."""
    return {
        "$key": 1,
        "bgp_routemap": 1,
        "orderid": 1,
        "command": "match",
        "params": "ip address prefix-list MY-PREFIX",
    }


@pytest.fixture
def sample_bgp_ip_command_data() -> dict[str, Any]:
    """Sample BGP IP command data from API."""
    return {
        "$key": 1,
        "bgp": 1,
        "orderid": 1,
        "command": "prefix-list",
        "params": "MY-PREFIX seq 10 permit 10.0.0.0/8 le 24",
    }


@pytest.fixture
def sample_ospf_command_data() -> dict[str, Any]:
    """Sample OSPF command data from API."""
    return {
        "$key": 1,
        "bgp": 1,
        "orderid": 1,
        "command": "router-id",
        "params": "1.1.1.1",
    }


@pytest.fixture
def sample_eigrp_router_data() -> dict[str, Any]:
    """Sample EIGRP router data from API."""
    return {
        "$key": 1,
        "bgp": 1,
        "asn": 100,
    }


@pytest.fixture
def sample_eigrp_router_command_data() -> dict[str, Any]:
    """Sample EIGRP router command data from API."""
    return {
        "$key": 1,
        "eigrp_router": 1,
        "orderid": 1,
        "enabled": True,
        "no": False,
        "command": "network",
        "params": "10.0.0.0/24",
    }


# =============================================================================
# BGP Router Tests
# =============================================================================


class TestBGPRouter:
    """Tests for BGPRouter resource object."""

    def test_asn_property(
        self, routing_manager: NetworkRoutingManager, sample_bgp_router_data: dict[str, Any]
    ) -> None:
        """Test ASN property."""
        manager = BGPRouterManager(routing_manager._client, routing_manager)
        router = BGPRouter(sample_bgp_router_data, manager)
        assert router.asn == 65000

    def test_commands_property(
        self, routing_manager: NetworkRoutingManager, sample_bgp_router_data: dict[str, Any]
    ) -> None:
        """Test commands property returns command manager."""
        manager = BGPRouterManager(routing_manager._client, routing_manager)
        router = BGPRouter(sample_bgp_router_data, manager)
        assert isinstance(router.commands, BGPRouterCommandManager)


class TestBGPRouterCommand:
    """Tests for BGPRouterCommand resource object."""

    def test_command_type_property(
        self, routing_manager: NetworkRoutingManager, sample_bgp_router_command_data: dict[str, Any]
    ) -> None:
        """Test command_type property."""
        manager = BGPRouterManager(routing_manager._client, routing_manager)
        router = BGPRouter({"$key": 1, "asn": 65000}, manager)
        cmd_manager = BGPRouterCommandManager(routing_manager._client, router)
        cmd = BGPRouterCommand(sample_bgp_router_command_data, cmd_manager)
        assert cmd.command_type == "neighbor"

    def test_params_property(
        self, routing_manager: NetworkRoutingManager, sample_bgp_router_command_data: dict[str, Any]
    ) -> None:
        """Test params property."""
        manager = BGPRouterManager(routing_manager._client, routing_manager)
        router = BGPRouter({"$key": 1, "asn": 65000}, manager)
        cmd_manager = BGPRouterCommandManager(routing_manager._client, router)
        cmd = BGPRouterCommand(sample_bgp_router_command_data, cmd_manager)
        assert cmd.params == "192.168.1.1 remote-as 65001"

    def test_is_enabled_property(
        self, routing_manager: NetworkRoutingManager, sample_bgp_router_command_data: dict[str, Any]
    ) -> None:
        """Test is_enabled property."""
        manager = BGPRouterManager(routing_manager._client, routing_manager)
        router = BGPRouter({"$key": 1, "asn": 65000}, manager)
        cmd_manager = BGPRouterCommandManager(routing_manager._client, router)
        cmd = BGPRouterCommand(sample_bgp_router_command_data, cmd_manager)
        assert cmd.is_enabled is True

    def test_is_negated_property(
        self, routing_manager: NetworkRoutingManager, sample_bgp_router_command_data: dict[str, Any]
    ) -> None:
        """Test is_negated property."""
        manager = BGPRouterManager(routing_manager._client, routing_manager)
        router = BGPRouter({"$key": 1, "asn": 65000}, manager)
        cmd_manager = BGPRouterCommandManager(routing_manager._client, router)
        cmd = BGPRouterCommand(sample_bgp_router_command_data, cmd_manager)
        assert cmd.is_negated is False


class TestBGPRouterManagerList:
    """Tests for BGPRouterManager.list() method."""

    def test_list_returns_empty_when_no_bgp_config(
        self, routing_manager: NetworkRoutingManager, mock_client: MagicMock
    ) -> None:
        """Test list returns empty when no BGP config exists."""
        mock_client._request.return_value = None
        manager = BGPRouterManager(mock_client, routing_manager)
        result = manager.list()
        assert result == []

    def test_list_returns_routers(
        self,
        routing_manager: NetworkRoutingManager,
        mock_client: MagicMock,
        sample_bgp_router_data: dict[str, Any],
    ) -> None:
        """Test list returns routers."""
        mock_client._request.side_effect = [
            {"$key": 1},  # vnet_bgp query
            [sample_bgp_router_data],  # vnet_bgp_routers query
        ]
        manager = BGPRouterManager(mock_client, routing_manager)
        result = manager.list()
        assert len(result) == 1
        assert result[0].asn == 65000


class TestBGPRouterManagerGet:
    """Tests for BGPRouterManager.get() method."""

    def test_get_by_key(
        self,
        routing_manager: NetworkRoutingManager,
        mock_client: MagicMock,
        sample_bgp_router_data: dict[str, Any],
    ) -> None:
        """Test get router by key."""
        mock_client._request.return_value = sample_bgp_router_data
        manager = BGPRouterManager(mock_client, routing_manager)
        result = manager.get(1)
        assert result.key == 1
        assert result.asn == 65000

    def test_get_by_asn(
        self,
        routing_manager: NetworkRoutingManager,
        mock_client: MagicMock,
        sample_bgp_router_data: dict[str, Any],
    ) -> None:
        """Test get router by ASN."""
        mock_client._request.side_effect = [
            {"$key": 1},  # vnet_bgp query
            [sample_bgp_router_data],  # filter by ASN
        ]
        manager = BGPRouterManager(mock_client, routing_manager)
        result = manager.get(asn=65000)
        assert result.asn == 65000

    def test_get_not_found(
        self, routing_manager: NetworkRoutingManager, mock_client: MagicMock
    ) -> None:
        """Test get raises NotFoundError when not found."""
        mock_client._request.return_value = None
        manager = BGPRouterManager(mock_client, routing_manager)
        with pytest.raises(NotFoundError):
            manager.get(999)

    def test_get_requires_key_or_asn(
        self, routing_manager: NetworkRoutingManager, mock_client: MagicMock
    ) -> None:
        """Test get raises ValueError when neither key nor asn provided."""
        manager = BGPRouterManager(mock_client, routing_manager)
        with pytest.raises(ValueError, match="Either key or asn"):
            manager.get()


class TestBGPRouterManagerCreate:
    """Tests for BGPRouterManager.create() method."""

    def test_create_router(
        self,
        routing_manager: NetworkRoutingManager,
        mock_client: MagicMock,
        sample_bgp_router_data: dict[str, Any],
    ) -> None:
        """Test create router."""
        mock_client._request.side_effect = [
            {"$key": 1},  # vnet_bgp query (exists)
            {"$key": 1},  # POST vnet_bgp_routers
            sample_bgp_router_data,  # GET to fetch created
        ]
        manager = BGPRouterManager(mock_client, routing_manager)
        result = manager.create(asn=65000)
        assert result.asn == 65000

    def test_create_creates_bgp_config_if_missing(
        self,
        routing_manager: NetworkRoutingManager,
        mock_client: MagicMock,
        sample_bgp_router_data: dict[str, Any],
    ) -> None:
        """Test create creates BGP config if not exists."""
        mock_client._request.side_effect = [
            None,  # vnet_bgp query (none exists)
            {"$key": 1},  # POST vnet_bgp (create config)
            {"$key": 1},  # POST vnet_bgp_routers
            sample_bgp_router_data,  # GET to fetch created
        ]
        manager = BGPRouterManager(mock_client, routing_manager)
        manager.create(asn=65000)
        # Verify BGP config was created (4 API calls)
        assert mock_client._request.call_count == 4


class TestBGPRouterManagerDelete:
    """Tests for BGPRouterManager.delete() method."""

    def test_delete_router(
        self, routing_manager: NetworkRoutingManager, mock_client: MagicMock
    ) -> None:
        """Test delete router."""
        mock_client._request.return_value = None
        manager = BGPRouterManager(mock_client, routing_manager)
        manager.delete(1)
        mock_client._request.assert_called_with("DELETE", "vnet_bgp_routers/1")


# =============================================================================
# BGP Interface Tests
# =============================================================================


class TestBGPInterface:
    """Tests for BGPInterface resource object."""

    def test_ip_address_property(
        self, routing_manager: NetworkRoutingManager, sample_bgp_interface_data: dict[str, Any]
    ) -> None:
        """Test ip_address property."""
        manager = BGPInterfaceManager(routing_manager._client, routing_manager)
        iface = BGPInterface(sample_bgp_interface_data, manager)
        assert iface.ip_address == "10.255.0.1"

    def test_network_address_property(
        self, routing_manager: NetworkRoutingManager, sample_bgp_interface_data: dict[str, Any]
    ) -> None:
        """Test network_address property."""
        manager = BGPInterfaceManager(routing_manager._client, routing_manager)
        iface = BGPInterface(sample_bgp_interface_data, manager)
        assert iface.network_address == "10.255.0.0/30"

    def test_mtu_property(
        self, routing_manager: NetworkRoutingManager, sample_bgp_interface_data: dict[str, Any]
    ) -> None:
        """Test mtu property."""
        manager = BGPInterfaceManager(routing_manager._client, routing_manager)
        iface = BGPInterface(sample_bgp_interface_data, manager)
        assert iface.mtu == 9000

    def test_layer2_type_property(
        self, routing_manager: NetworkRoutingManager, sample_bgp_interface_data: dict[str, Any]
    ) -> None:
        """Test layer2_type property."""
        manager = BGPInterfaceManager(routing_manager._client, routing_manager)
        iface = BGPInterface(sample_bgp_interface_data, manager)
        assert iface.layer2_type == "vlan"

    def test_layer2_id_property(
        self, routing_manager: NetworkRoutingManager, sample_bgp_interface_data: dict[str, Any]
    ) -> None:
        """Test layer2_id property."""
        manager = BGPInterfaceManager(routing_manager._client, routing_manager)
        iface = BGPInterface(sample_bgp_interface_data, manager)
        assert iface.layer2_id == 100

    def test_commands_property(
        self, routing_manager: NetworkRoutingManager, sample_bgp_interface_data: dict[str, Any]
    ) -> None:
        """Test commands property returns command manager."""
        manager = BGPInterfaceManager(routing_manager._client, routing_manager)
        iface = BGPInterface(sample_bgp_interface_data, manager)
        assert isinstance(iface.commands, BGPInterfaceCommandManager)


class TestBGPInterfaceManagerList:
    """Tests for BGPInterfaceManager.list() method."""

    def test_list_returns_empty_when_no_bgp_config(
        self, routing_manager: NetworkRoutingManager, mock_client: MagicMock
    ) -> None:
        """Test list returns empty when no BGP config exists."""
        mock_client._request.return_value = None
        manager = BGPInterfaceManager(mock_client, routing_manager)
        result = manager.list()
        assert result == []

    def test_list_returns_interfaces(
        self,
        routing_manager: NetworkRoutingManager,
        mock_client: MagicMock,
        sample_bgp_interface_data: dict[str, Any],
    ) -> None:
        """Test list returns interfaces."""
        mock_client._request.side_effect = [
            {"$key": 1},  # vnet_bgp query
            [sample_bgp_interface_data],  # vnet_bgp_interfaces query
        ]
        manager = BGPInterfaceManager(mock_client, routing_manager)
        result = manager.list()
        assert len(result) == 1
        assert result[0].name == "peer-1"


class TestBGPInterfaceManagerGet:
    """Tests for BGPInterfaceManager.get() method."""

    def test_get_by_key(
        self,
        routing_manager: NetworkRoutingManager,
        mock_client: MagicMock,
        sample_bgp_interface_data: dict[str, Any],
    ) -> None:
        """Test get interface by key."""
        mock_client._request.return_value = sample_bgp_interface_data
        manager = BGPInterfaceManager(mock_client, routing_manager)
        result = manager.get(1)
        assert result.key == 1
        assert result.name == "peer-1"

    def test_get_by_name(
        self,
        routing_manager: NetworkRoutingManager,
        mock_client: MagicMock,
        sample_bgp_interface_data: dict[str, Any],
    ) -> None:
        """Test get interface by name."""
        mock_client._request.side_effect = [
            {"$key": 1},  # vnet_bgp query
            [sample_bgp_interface_data],  # filter by name
        ]
        manager = BGPInterfaceManager(mock_client, routing_manager)
        result = manager.get(name="peer-1")
        assert result.name == "peer-1"


# =============================================================================
# BGP Route Map Tests
# =============================================================================


class TestBGPRouteMap:
    """Tests for BGPRouteMap resource object."""

    def test_tag_property(
        self, routing_manager: NetworkRoutingManager, sample_bgp_routemap_data: dict[str, Any]
    ) -> None:
        """Test tag property."""
        manager = BGPRouteMapManager(routing_manager._client, routing_manager)
        routemap = BGPRouteMap(sample_bgp_routemap_data, manager)
        assert routemap.tag == "IMPORT-FROM-ISP"

    def test_sequence_property(
        self, routing_manager: NetworkRoutingManager, sample_bgp_routemap_data: dict[str, Any]
    ) -> None:
        """Test sequence property."""
        manager = BGPRouteMapManager(routing_manager._client, routing_manager)
        routemap = BGPRouteMap(sample_bgp_routemap_data, manager)
        assert routemap.sequence == 10

    def test_is_permit_property(
        self, routing_manager: NetworkRoutingManager, sample_bgp_routemap_data: dict[str, Any]
    ) -> None:
        """Test is_permit property."""
        manager = BGPRouteMapManager(routing_manager._client, routing_manager)
        routemap = BGPRouteMap(sample_bgp_routemap_data, manager)
        assert routemap.is_permit is True

    def test_commands_property(
        self, routing_manager: NetworkRoutingManager, sample_bgp_routemap_data: dict[str, Any]
    ) -> None:
        """Test commands property returns command manager."""
        manager = BGPRouteMapManager(routing_manager._client, routing_manager)
        routemap = BGPRouteMap(sample_bgp_routemap_data, manager)
        assert isinstance(routemap.commands, BGPRouteMapCommandManager)


class TestBGPRouteMapManagerList:
    """Tests for BGPRouteMapManager.list() method."""

    def test_list_returns_route_maps(
        self,
        routing_manager: NetworkRoutingManager,
        mock_client: MagicMock,
        sample_bgp_routemap_data: dict[str, Any],
    ) -> None:
        """Test list returns route maps."""
        mock_client._request.side_effect = [
            {"$key": 1},  # vnet_bgp query
            [sample_bgp_routemap_data],  # vnet_bgp_routemaps query
        ]
        manager = BGPRouteMapManager(mock_client, routing_manager)
        result = manager.list()
        assert len(result) == 1
        assert result[0].tag == "IMPORT-FROM-ISP"


class TestBGPRouteMapManagerGet:
    """Tests for BGPRouteMapManager.get() method."""

    def test_get_by_key(
        self,
        routing_manager: NetworkRoutingManager,
        mock_client: MagicMock,
        sample_bgp_routemap_data: dict[str, Any],
    ) -> None:
        """Test get route map by key."""
        mock_client._request.return_value = sample_bgp_routemap_data
        manager = BGPRouteMapManager(mock_client, routing_manager)
        result = manager.get(1)
        assert result.tag == "IMPORT-FROM-ISP"

    def test_get_by_tag_and_sequence(
        self,
        routing_manager: NetworkRoutingManager,
        mock_client: MagicMock,
        sample_bgp_routemap_data: dict[str, Any],
    ) -> None:
        """Test get route map by tag and sequence."""
        mock_client._request.side_effect = [
            {"$key": 1},  # vnet_bgp query
            [sample_bgp_routemap_data],  # filter by tag+seq
        ]
        manager = BGPRouteMapManager(mock_client, routing_manager)
        result = manager.get(tag="IMPORT-FROM-ISP", sequence=10)
        assert result.tag == "IMPORT-FROM-ISP"

    def test_get_requires_key_or_tag_and_sequence(
        self, routing_manager: NetworkRoutingManager, mock_client: MagicMock
    ) -> None:
        """Test get raises ValueError when neither key nor tag+sequence provided."""
        manager = BGPRouteMapManager(mock_client, routing_manager)
        with pytest.raises(ValueError, match="Either key or"):
            manager.get()


# =============================================================================
# BGP IP Command Tests
# =============================================================================


class TestBGPIPCommand:
    """Tests for BGPIPCommand resource object."""

    def test_command_type_property(
        self, routing_manager: NetworkRoutingManager, sample_bgp_ip_command_data: dict[str, Any]
    ) -> None:
        """Test command_type property."""
        manager = BGPIPCommandManager(routing_manager._client, routing_manager)
        cmd = BGPIPCommand(sample_bgp_ip_command_data, manager)
        assert cmd.command_type == "prefix-list"

    def test_params_property(
        self, routing_manager: NetworkRoutingManager, sample_bgp_ip_command_data: dict[str, Any]
    ) -> None:
        """Test params property."""
        manager = BGPIPCommandManager(routing_manager._client, routing_manager)
        cmd = BGPIPCommand(sample_bgp_ip_command_data, manager)
        assert cmd.params == "MY-PREFIX seq 10 permit 10.0.0.0/8 le 24"


class TestBGPIPCommandManagerList:
    """Tests for BGPIPCommandManager.list() method."""

    def test_list_returns_commands(
        self,
        routing_manager: NetworkRoutingManager,
        mock_client: MagicMock,
        sample_bgp_ip_command_data: dict[str, Any],
    ) -> None:
        """Test list returns IP commands."""
        mock_client._request.side_effect = [
            {"$key": 1},  # vnet_bgp query
            [sample_bgp_ip_command_data],  # vnet_bgp_ip query
        ]
        manager = BGPIPCommandManager(mock_client, routing_manager)
        result = manager.list()
        assert len(result) == 1
        assert result[0].command_type == "prefix-list"


class TestBGPIPCommandManagerCreate:
    """Tests for BGPIPCommandManager.create() method."""

    def test_create_command(
        self,
        routing_manager: NetworkRoutingManager,
        mock_client: MagicMock,
        sample_bgp_ip_command_data: dict[str, Any],
    ) -> None:
        """Test create IP command."""
        mock_client._request.side_effect = [
            {"$key": 1},  # vnet_bgp query (exists)
            {"$key": 1},  # POST vnet_bgp_ip
            sample_bgp_ip_command_data,  # GET to fetch created
        ]
        manager = BGPIPCommandManager(mock_client, routing_manager)
        result = manager.create(
            command="prefix-list", params="MY-PREFIX seq 10 permit 10.0.0.0/8 le 24"
        )
        assert result.command_type == "prefix-list"


# =============================================================================
# OSPF Command Tests
# =============================================================================


class TestOSPFCommand:
    """Tests for OSPFCommand resource object."""

    def test_command_type_property(
        self, routing_manager: NetworkRoutingManager, sample_ospf_command_data: dict[str, Any]
    ) -> None:
        """Test command_type property."""
        manager = OSPFCommandManager(routing_manager._client, routing_manager)
        cmd = OSPFCommand(sample_ospf_command_data, manager)
        assert cmd.command_type == "router-id"

    def test_params_property(
        self, routing_manager: NetworkRoutingManager, sample_ospf_command_data: dict[str, Any]
    ) -> None:
        """Test params property."""
        manager = OSPFCommandManager(routing_manager._client, routing_manager)
        cmd = OSPFCommand(sample_ospf_command_data, manager)
        assert cmd.params == "1.1.1.1"


class TestOSPFCommandManagerList:
    """Tests for OSPFCommandManager.list() method."""

    def test_list_returns_commands(
        self,
        routing_manager: NetworkRoutingManager,
        mock_client: MagicMock,
        sample_ospf_command_data: dict[str, Any],
    ) -> None:
        """Test list returns OSPF commands."""
        mock_client._request.side_effect = [
            {"$key": 1},  # vnet_bgp query
            [sample_ospf_command_data],  # vnet_ospf_commands query
        ]
        manager = OSPFCommandManager(mock_client, routing_manager)
        result = manager.list()
        assert len(result) == 1
        assert result[0].command_type == "router-id"


class TestOSPFCommandManagerCreate:
    """Tests for OSPFCommandManager.create() method."""

    def test_create_command(
        self,
        routing_manager: NetworkRoutingManager,
        mock_client: MagicMock,
        sample_ospf_command_data: dict[str, Any],
    ) -> None:
        """Test create OSPF command."""
        mock_client._request.side_effect = [
            {"$key": 1},  # vnet_bgp query (exists)
            {"$key": 1},  # POST vnet_ospf_commands
            sample_ospf_command_data,  # GET to fetch created
        ]
        manager = OSPFCommandManager(mock_client, routing_manager)
        result = manager.create(command="router-id", params="1.1.1.1")
        assert result.command_type == "router-id"


# =============================================================================
# EIGRP Router Tests
# =============================================================================


class TestEIGRPRouter:
    """Tests for EIGRPRouter resource object."""

    def test_asn_property(
        self, routing_manager: NetworkRoutingManager, sample_eigrp_router_data: dict[str, Any]
    ) -> None:
        """Test ASN property."""
        manager = EIGRPRouterManager(routing_manager._client, routing_manager)
        router = EIGRPRouter(sample_eigrp_router_data, manager)
        assert router.asn == 100

    def test_commands_property(
        self, routing_manager: NetworkRoutingManager, sample_eigrp_router_data: dict[str, Any]
    ) -> None:
        """Test commands property returns command manager."""
        manager = EIGRPRouterManager(routing_manager._client, routing_manager)
        router = EIGRPRouter(sample_eigrp_router_data, manager)
        assert isinstance(router.commands, EIGRPRouterCommandManager)


class TestEIGRPRouterCommand:
    """Tests for EIGRPRouterCommand resource object."""

    def test_command_type_property(
        self,
        routing_manager: NetworkRoutingManager,
        sample_eigrp_router_command_data: dict[str, Any],
    ) -> None:
        """Test command_type property."""
        manager = EIGRPRouterManager(routing_manager._client, routing_manager)
        router = EIGRPRouter({"$key": 1, "asn": 100}, manager)
        cmd_manager = EIGRPRouterCommandManager(routing_manager._client, router)
        cmd = EIGRPRouterCommand(sample_eigrp_router_command_data, cmd_manager)
        assert cmd.command_type == "network"

    def test_params_property(
        self,
        routing_manager: NetworkRoutingManager,
        sample_eigrp_router_command_data: dict[str, Any],
    ) -> None:
        """Test params property."""
        manager = EIGRPRouterManager(routing_manager._client, routing_manager)
        router = EIGRPRouter({"$key": 1, "asn": 100}, manager)
        cmd_manager = EIGRPRouterCommandManager(routing_manager._client, router)
        cmd = EIGRPRouterCommand(sample_eigrp_router_command_data, cmd_manager)
        assert cmd.params == "10.0.0.0/24"


class TestEIGRPRouterManagerList:
    """Tests for EIGRPRouterManager.list() method."""

    def test_list_returns_routers(
        self,
        routing_manager: NetworkRoutingManager,
        mock_client: MagicMock,
        sample_eigrp_router_data: dict[str, Any],
    ) -> None:
        """Test list returns EIGRP routers."""
        mock_client._request.side_effect = [
            {"$key": 1},  # vnet_bgp query
            [sample_eigrp_router_data],  # vnet_eigrp_routers query
        ]
        manager = EIGRPRouterManager(mock_client, routing_manager)
        result = manager.list()
        assert len(result) == 1
        assert result[0].asn == 100


class TestEIGRPRouterManagerCreate:
    """Tests for EIGRPRouterManager.create() method."""

    def test_create_router(
        self,
        routing_manager: NetworkRoutingManager,
        mock_client: MagicMock,
        sample_eigrp_router_data: dict[str, Any],
    ) -> None:
        """Test create EIGRP router."""
        mock_client._request.side_effect = [
            {"$key": 1},  # vnet_bgp query (exists)
            {"$key": 1},  # POST vnet_eigrp_routers
            sample_eigrp_router_data,  # GET to fetch created
        ]
        manager = EIGRPRouterManager(mock_client, routing_manager)
        result = manager.create(asn=100)
        assert result.asn == 100


# =============================================================================
# Network Routing Manager Tests
# =============================================================================


class TestNetworkRoutingManager:
    """Tests for NetworkRoutingManager."""

    def test_bgp_routers_property(
        self, routing_manager: NetworkRoutingManager
    ) -> None:
        """Test bgp_routers property returns manager."""
        assert isinstance(routing_manager.bgp_routers, BGPRouterManager)

    def test_bgp_interfaces_property(
        self, routing_manager: NetworkRoutingManager
    ) -> None:
        """Test bgp_interfaces property returns manager."""
        assert isinstance(routing_manager.bgp_interfaces, BGPInterfaceManager)

    def test_bgp_route_maps_property(
        self, routing_manager: NetworkRoutingManager
    ) -> None:
        """Test bgp_route_maps property returns manager."""
        assert isinstance(routing_manager.bgp_route_maps, BGPRouteMapManager)

    def test_bgp_ip_commands_property(
        self, routing_manager: NetworkRoutingManager
    ) -> None:
        """Test bgp_ip_commands property returns manager."""
        assert isinstance(routing_manager.bgp_ip_commands, BGPIPCommandManager)

    def test_ospf_commands_property(
        self, routing_manager: NetworkRoutingManager
    ) -> None:
        """Test ospf_commands property returns manager."""
        assert isinstance(routing_manager.ospf_commands, OSPFCommandManager)

    def test_eigrp_routers_property(
        self, routing_manager: NetworkRoutingManager
    ) -> None:
        """Test eigrp_routers property returns manager."""
        assert isinstance(routing_manager.eigrp_routers, EIGRPRouterManager)

    def test_is_configured_true(
        self, routing_manager: NetworkRoutingManager, mock_client: MagicMock
    ) -> None:
        """Test is_configured returns True when BGP config exists."""
        mock_client._request.return_value = {"$key": 1}
        assert routing_manager.is_configured is True

    def test_is_configured_false(
        self, routing_manager: NetworkRoutingManager, mock_client: MagicMock
    ) -> None:
        """Test is_configured returns False when no BGP config."""
        mock_client._request.return_value = None
        assert routing_manager.is_configured is False

    def test_delete_config(
        self, routing_manager: NetworkRoutingManager, mock_client: MagicMock
    ) -> None:
        """Test delete_config removes BGP configuration."""
        mock_client._request.side_effect = [
            {"$key": 1},  # _get_bgp_config query
            None,  # DELETE call
        ]
        routing_manager.delete_config()
        # Verify DELETE was called
        calls = [call for call in mock_client._request.call_args_list if call[0][0] == "DELETE"]
        assert len(calls) == 1
        assert "vnet_bgp/1" in calls[0][0][1]
