"""Unit tests for WireGuardManager and WireGuardPeerManager."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from pyvergeos.exceptions import NotFoundError
from pyvergeos.resources.networks import Network
from pyvergeos.resources.wireguard import (
    WireGuardInterface,
    WireGuardManager,
    WireGuardPeer,
    WireGuardPeerManager,
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
        "$key": 3,
        "name": "External",
        "type": "external",
    }
    manager = MagicMock()
    manager._client = mock_client
    return Network(network_data, manager)


@pytest.fixture
def wireguard_manager(mock_client: MagicMock, mock_network: Network) -> WireGuardManager:
    """Create a WireGuardManager with mock dependencies."""
    return WireGuardManager(mock_client, mock_network)


@pytest.fixture
def sample_interface_data() -> dict[str, Any]:
    """Sample WireGuard interface data from API."""
    return {
        "$key": 1,
        "vnet": 3,
        "name": "wg0",
        "description": "Main WireGuard interface",
        "enabled": True,
        "ip": "10.100.0.1/24",
        "listenport": 51820,
        "mtu": 0,
        "public_key": "KP9AYuQFdIV5H87ssPNezDrGlrJCGY9rZt7s6aGZ5nE=",
        "endpoint_ip": "203.0.113.50",
        "modified": 1706000000,
    }


@pytest.fixture
def sample_peer_data() -> dict[str, Any]:
    """Sample WireGuard peer data from API."""
    return {
        "$key": 1,
        "wireguard": 1,
        "name": "remote-office",
        "description": "Remote office connection",
        "enabled": True,
        "endpoint": "vpn.remote-office.com",
        "port": 51820,
        "peer_ip": "10.100.0.2",
        "public_key": "abc123publickey==",
        "preshared_key": "",
        "allowed_ips": "192.168.1.0/24",
        "keepalive": 25,
        "configure_firewall": "site-to-site",
        "modified": 1706000000,
    }


class TestWireGuardInterface:
    """Tests for WireGuardInterface resource object."""

    def test_is_enabled(
        self, wireguard_manager: WireGuardManager, sample_interface_data: dict[str, Any]
    ) -> None:
        """Test is_enabled property."""
        iface = WireGuardInterface(sample_interface_data, wireguard_manager)
        assert iface.is_enabled is True

    def test_is_enabled_false(self, wireguard_manager: WireGuardManager) -> None:
        """Test is_enabled when disabled."""
        iface = WireGuardInterface({"$key": 1, "enabled": False}, wireguard_manager)
        assert iface.is_enabled is False

    def test_ip_address(
        self, wireguard_manager: WireGuardManager, sample_interface_data: dict[str, Any]
    ) -> None:
        """Test ip_address property."""
        iface = WireGuardInterface(sample_interface_data, wireguard_manager)
        assert iface.ip_address == "10.100.0.1/24"

    def test_ip_only(
        self, wireguard_manager: WireGuardManager, sample_interface_data: dict[str, Any]
    ) -> None:
        """Test ip_only property."""
        iface = WireGuardInterface(sample_interface_data, wireguard_manager)
        assert iface.ip_only == "10.100.0.1"

    def test_ip_only_without_cidr(self, wireguard_manager: WireGuardManager) -> None:
        """Test ip_only when no CIDR mask."""
        iface = WireGuardInterface({"$key": 1, "ip": "10.100.0.1"}, wireguard_manager)
        assert iface.ip_only == "10.100.0.1"

    def test_subnet_mask(
        self, wireguard_manager: WireGuardManager, sample_interface_data: dict[str, Any]
    ) -> None:
        """Test subnet_mask property."""
        iface = WireGuardInterface(sample_interface_data, wireguard_manager)
        assert iface.subnet_mask == "24"

    def test_subnet_mask_default(self, wireguard_manager: WireGuardManager) -> None:
        """Test subnet_mask default when no mask."""
        iface = WireGuardInterface({"$key": 1, "ip": "10.100.0.1"}, wireguard_manager)
        assert iface.subnet_mask == "32"

    def test_listen_port(
        self, wireguard_manager: WireGuardManager, sample_interface_data: dict[str, Any]
    ) -> None:
        """Test listen_port property."""
        iface = WireGuardInterface(sample_interface_data, wireguard_manager)
        assert iface.listen_port == 51820

    def test_mtu(
        self, wireguard_manager: WireGuardManager, sample_interface_data: dict[str, Any]
    ) -> None:
        """Test mtu property."""
        iface = WireGuardInterface(sample_interface_data, wireguard_manager)
        assert iface.mtu == 0

    def test_mtu_display_auto(
        self, wireguard_manager: WireGuardManager, sample_interface_data: dict[str, Any]
    ) -> None:
        """Test mtu_display for auto (0)."""
        iface = WireGuardInterface(sample_interface_data, wireguard_manager)
        assert iface.mtu_display == "Auto"

    def test_mtu_display_value(self, wireguard_manager: WireGuardManager) -> None:
        """Test mtu_display for specific value."""
        iface = WireGuardInterface({"$key": 1, "mtu": 1420}, wireguard_manager)
        assert iface.mtu_display == "1420"

    def test_public_key(
        self, wireguard_manager: WireGuardManager, sample_interface_data: dict[str, Any]
    ) -> None:
        """Test public_key property."""
        iface = WireGuardInterface(sample_interface_data, wireguard_manager)
        assert iface.public_key == "KP9AYuQFdIV5H87ssPNezDrGlrJCGY9rZt7s6aGZ5nE="

    def test_endpoint_ip(
        self, wireguard_manager: WireGuardManager, sample_interface_data: dict[str, Any]
    ) -> None:
        """Test endpoint_ip property."""
        iface = WireGuardInterface(sample_interface_data, wireguard_manager)
        assert iface.endpoint_ip == "203.0.113.50"

    def test_modified_at(
        self, wireguard_manager: WireGuardManager, sample_interface_data: dict[str, Any]
    ) -> None:
        """Test modified_at property."""
        iface = WireGuardInterface(sample_interface_data, wireguard_manager)
        assert iface.modified_at is not None

    def test_modified_at_none(self, wireguard_manager: WireGuardManager) -> None:
        """Test modified_at when not set."""
        iface = WireGuardInterface({"$key": 1}, wireguard_manager)
        assert iface.modified_at is None


class TestWireGuardPeer:
    """Tests for WireGuardPeer resource object."""

    def test_is_enabled(
        self, wireguard_manager: WireGuardManager, sample_peer_data: dict[str, Any]
    ) -> None:
        """Test is_enabled property."""
        iface = WireGuardInterface({"$key": 1, "name": "wg0"}, wireguard_manager)
        peer_manager = WireGuardPeerManager(wireguard_manager._client, iface)
        peer = WireGuardPeer(sample_peer_data, peer_manager)
        assert peer.is_enabled is True

    def test_endpoint(
        self, wireguard_manager: WireGuardManager, sample_peer_data: dict[str, Any]
    ) -> None:
        """Test endpoint property."""
        iface = WireGuardInterface({"$key": 1, "name": "wg0"}, wireguard_manager)
        peer_manager = WireGuardPeerManager(wireguard_manager._client, iface)
        peer = WireGuardPeer(sample_peer_data, peer_manager)
        assert peer.endpoint == "vpn.remote-office.com"

    def test_port(
        self, wireguard_manager: WireGuardManager, sample_peer_data: dict[str, Any]
    ) -> None:
        """Test port property."""
        iface = WireGuardInterface({"$key": 1, "name": "wg0"}, wireguard_manager)
        peer_manager = WireGuardPeerManager(wireguard_manager._client, iface)
        peer = WireGuardPeer(sample_peer_data, peer_manager)
        assert peer.port == 51820

    def test_peer_ip(
        self, wireguard_manager: WireGuardManager, sample_peer_data: dict[str, Any]
    ) -> None:
        """Test peer_ip property."""
        iface = WireGuardInterface({"$key": 1, "name": "wg0"}, wireguard_manager)
        peer_manager = WireGuardPeerManager(wireguard_manager._client, iface)
        peer = WireGuardPeer(sample_peer_data, peer_manager)
        assert peer.peer_ip == "10.100.0.2"

    def test_public_key(
        self, wireguard_manager: WireGuardManager, sample_peer_data: dict[str, Any]
    ) -> None:
        """Test public_key property."""
        iface = WireGuardInterface({"$key": 1, "name": "wg0"}, wireguard_manager)
        peer_manager = WireGuardPeerManager(wireguard_manager._client, iface)
        peer = WireGuardPeer(sample_peer_data, peer_manager)
        assert peer.public_key == "abc123publickey=="

    def test_has_preshared_key_false(
        self, wireguard_manager: WireGuardManager, sample_peer_data: dict[str, Any]
    ) -> None:
        """Test has_preshared_key when empty."""
        iface = WireGuardInterface({"$key": 1, "name": "wg0"}, wireguard_manager)
        peer_manager = WireGuardPeerManager(wireguard_manager._client, iface)
        peer = WireGuardPeer(sample_peer_data, peer_manager)
        assert peer.has_preshared_key is False

    def test_has_preshared_key_true(self, wireguard_manager: WireGuardManager) -> None:
        """Test has_preshared_key when set."""
        iface = WireGuardInterface({"$key": 1, "name": "wg0"}, wireguard_manager)
        peer_manager = WireGuardPeerManager(wireguard_manager._client, iface)
        peer = WireGuardPeer({"$key": 1, "preshared_key": "somesecretkey"}, peer_manager)
        assert peer.has_preshared_key is True

    def test_allowed_ips(
        self, wireguard_manager: WireGuardManager, sample_peer_data: dict[str, Any]
    ) -> None:
        """Test allowed_ips property."""
        iface = WireGuardInterface({"$key": 1, "name": "wg0"}, wireguard_manager)
        peer_manager = WireGuardPeerManager(wireguard_manager._client, iface)
        peer = WireGuardPeer(sample_peer_data, peer_manager)
        assert peer.allowed_ips == "192.168.1.0/24"

    def test_keepalive(
        self, wireguard_manager: WireGuardManager, sample_peer_data: dict[str, Any]
    ) -> None:
        """Test keepalive property."""
        iface = WireGuardInterface({"$key": 1, "name": "wg0"}, wireguard_manager)
        peer_manager = WireGuardPeerManager(wireguard_manager._client, iface)
        peer = WireGuardPeer(sample_peer_data, peer_manager)
        assert peer.keepalive == 25

    def test_firewall_config(
        self, wireguard_manager: WireGuardManager, sample_peer_data: dict[str, Any]
    ) -> None:
        """Test firewall_config property."""
        iface = WireGuardInterface({"$key": 1, "name": "wg0"}, wireguard_manager)
        peer_manager = WireGuardPeerManager(wireguard_manager._client, iface)
        peer = WireGuardPeer(sample_peer_data, peer_manager)
        assert peer.firewall_config == "site-to-site"

    def test_firewall_config_display_site_to_site(
        self, wireguard_manager: WireGuardManager, sample_peer_data: dict[str, Any]
    ) -> None:
        """Test firewall_config_display for site-to-site."""
        iface = WireGuardInterface({"$key": 1, "name": "wg0"}, wireguard_manager)
        peer_manager = WireGuardPeerManager(wireguard_manager._client, iface)
        peer = WireGuardPeer(sample_peer_data, peer_manager)
        assert peer.firewall_config_display == "Site-to-Site"

    def test_firewall_config_display_remote_user(self, wireguard_manager: WireGuardManager) -> None:
        """Test firewall_config_display for remote-user."""
        iface = WireGuardInterface({"$key": 1, "name": "wg0"}, wireguard_manager)
        peer_manager = WireGuardPeerManager(wireguard_manager._client, iface)
        peer = WireGuardPeer({"$key": 1, "configure_firewall": "remote-user"}, peer_manager)
        assert peer.firewall_config_display == "Remote User"

    def test_firewall_config_display_none(self, wireguard_manager: WireGuardManager) -> None:
        """Test firewall_config_display for none."""
        iface = WireGuardInterface({"$key": 1, "name": "wg0"}, wireguard_manager)
        peer_manager = WireGuardPeerManager(wireguard_manager._client, iface)
        peer = WireGuardPeer({"$key": 1, "configure_firewall": "none"}, peer_manager)
        assert peer.firewall_config_display == "None"


class TestWireGuardManagerList:
    """Tests for WireGuardManager.list() method."""

    def test_list_returns_empty_when_none(
        self, wireguard_manager: WireGuardManager, mock_client: MagicMock
    ) -> None:
        """Test list returns empty when no interfaces exist."""
        mock_client._request.return_value = None
        result = wireguard_manager.list()
        assert result == []

    def test_list_returns_interfaces(
        self,
        wireguard_manager: WireGuardManager,
        mock_client: MagicMock,
        sample_interface_data: dict[str, Any],
    ) -> None:
        """Test list returns interfaces."""
        mock_client._request.return_value = [sample_interface_data]
        result = wireguard_manager.list()
        assert len(result) == 1
        assert result[0].name == "wg0"

    def test_list_handles_single_interface(
        self,
        wireguard_manager: WireGuardManager,
        mock_client: MagicMock,
        sample_interface_data: dict[str, Any],
    ) -> None:
        """Test list handles single interface (dict instead of list)."""
        mock_client._request.return_value = sample_interface_data
        result = wireguard_manager.list()
        assert len(result) == 1

    def test_list_includes_network_filter(
        self,
        wireguard_manager: WireGuardManager,
        mock_client: MagicMock,
    ) -> None:
        """Test list includes network filter in query."""
        mock_client._request.return_value = []
        wireguard_manager.list()
        call_args = mock_client._request.call_args
        assert "vnet eq 3" in call_args[1]["params"]["filter"]


class TestWireGuardManagerGet:
    """Tests for WireGuardManager.get() method."""

    def test_get_by_key(
        self,
        wireguard_manager: WireGuardManager,
        mock_client: MagicMock,
        sample_interface_data: dict[str, Any],
    ) -> None:
        """Test get interface by key."""
        mock_client._request.return_value = sample_interface_data
        result = wireguard_manager.get(1)
        assert result.key == 1
        assert result.name == "wg0"

    def test_get_by_name(
        self,
        wireguard_manager: WireGuardManager,
        mock_client: MagicMock,
        sample_interface_data: dict[str, Any],
    ) -> None:
        """Test get interface by name."""
        mock_client._request.return_value = [sample_interface_data]
        result = wireguard_manager.get(name="wg0")
        assert result.name == "wg0"

    def test_get_by_key_not_found(
        self, wireguard_manager: WireGuardManager, mock_client: MagicMock
    ) -> None:
        """Test get raises NotFoundError when not found."""
        mock_client._request.return_value = None
        with pytest.raises(NotFoundError):
            wireguard_manager.get(999)

    def test_get_by_name_not_found(
        self, wireguard_manager: WireGuardManager, mock_client: MagicMock
    ) -> None:
        """Test get by name raises NotFoundError when not found."""
        mock_client._request.return_value = []
        with pytest.raises(NotFoundError):
            wireguard_manager.get(name="NonExistent")

    def test_get_requires_key_or_name(self, wireguard_manager: WireGuardManager) -> None:
        """Test get raises ValueError when neither key nor name provided."""
        with pytest.raises(ValueError, match="Either key or name"):
            wireguard_manager.get()


class TestWireGuardManagerCreate:
    """Tests for WireGuardManager.create() method."""

    def test_create_interface(
        self,
        wireguard_manager: WireGuardManager,
        mock_client: MagicMock,
        sample_interface_data: dict[str, Any],
    ) -> None:
        """Test create interface."""
        mock_client._request.side_effect = [
            {"$key": 1},  # POST
            sample_interface_data,  # GET
        ]
        result = wireguard_manager.create(
            name="wg0",
            ip_address="10.100.0.1/24",
            listen_port=51820,
        )
        assert result.name == "wg0"

    def test_create_with_optional_params(
        self,
        wireguard_manager: WireGuardManager,
        mock_client: MagicMock,
        sample_interface_data: dict[str, Any],
    ) -> None:
        """Test create with all optional parameters."""
        mock_client._request.side_effect = [
            {"$key": 1},
            sample_interface_data,
        ]
        wireguard_manager.create(
            name="wg0",
            ip_address="10.100.0.1/24",
            listen_port=51821,
            mtu=1420,
            endpoint_ip="203.0.113.50",
            description="Test interface",
            enabled=False,
        )
        # Check POST call has correct params
        post_call = mock_client._request.call_args_list[0]
        body = post_call[1]["json_data"]
        assert body["name"] == "wg0"
        assert body["ip"] == "10.100.0.1/24"
        assert body["listenport"] == 51821
        assert body["mtu"] == 1420
        assert body["endpoint_ip"] == "203.0.113.50"
        assert body["description"] == "Test interface"
        assert body["enabled"] is False

    def test_create_no_response(
        self, wireguard_manager: WireGuardManager, mock_client: MagicMock
    ) -> None:
        """Test create raises error on no response."""
        mock_client._request.return_value = None
        with pytest.raises(ValueError, match="No response"):
            wireguard_manager.create(name="wg0", ip_address="10.100.0.1/24")


class TestWireGuardManagerUpdate:
    """Tests for WireGuardManager.update() method."""

    def test_update_interface(
        self,
        wireguard_manager: WireGuardManager,
        mock_client: MagicMock,
        sample_interface_data: dict[str, Any],
    ) -> None:
        """Test update interface."""
        mock_client._request.side_effect = [
            None,  # PUT
            sample_interface_data,  # GET
        ]
        result = wireguard_manager.update(1, description="Updated")
        assert result.name == "wg0"

    def test_update_maps_field_names(
        self,
        wireguard_manager: WireGuardManager,
        mock_client: MagicMock,
        sample_interface_data: dict[str, Any],
    ) -> None:
        """Test update maps field names to API format."""
        mock_client._request.side_effect = [
            None,
            sample_interface_data,
        ]
        wireguard_manager.update(
            1,
            ip_address="10.100.0.2/24",
            listen_port=51821,
        )
        put_call = mock_client._request.call_args_list[0]
        body = put_call[1]["json_data"]
        assert body["ip"] == "10.100.0.2/24"
        assert body["listenport"] == 51821

    def test_update_requires_parameters(self, wireguard_manager: WireGuardManager) -> None:
        """Test update raises ValueError when no parameters provided."""
        with pytest.raises(ValueError, match="No update parameters"):
            wireguard_manager.update(1)


class TestWireGuardManagerDelete:
    """Tests for WireGuardManager.delete() method."""

    def test_delete_interface(
        self, wireguard_manager: WireGuardManager, mock_client: MagicMock
    ) -> None:
        """Test delete interface."""
        mock_client._request.return_value = None
        wireguard_manager.delete(1)
        mock_client._request.assert_called_with("DELETE", "vnet_wireguards/1")


class TestWireGuardPeerManagerList:
    """Tests for WireGuardPeerManager.list() method."""

    def test_list_peers(
        self,
        wireguard_manager: WireGuardManager,
        mock_client: MagicMock,
        sample_peer_data: dict[str, Any],
    ) -> None:
        """Test list peers."""
        iface = WireGuardInterface({"$key": 1, "name": "wg0"}, wireguard_manager)
        peer_manager = WireGuardPeerManager(mock_client, iface)
        mock_client._request.return_value = [sample_peer_data]
        result = peer_manager.list()
        assert len(result) == 1
        assert result[0].name == "remote-office"

    def test_list_handles_empty(
        self, wireguard_manager: WireGuardManager, mock_client: MagicMock
    ) -> None:
        """Test list handles empty response."""
        iface = WireGuardInterface({"$key": 1, "name": "wg0"}, wireguard_manager)
        peer_manager = WireGuardPeerManager(mock_client, iface)
        mock_client._request.return_value = None
        result = peer_manager.list()
        assert result == []

    def test_list_includes_wireguard_filter(
        self, wireguard_manager: WireGuardManager, mock_client: MagicMock
    ) -> None:
        """Test list includes wireguard filter in query."""
        iface = WireGuardInterface({"$key": 1, "name": "wg0"}, wireguard_manager)
        peer_manager = WireGuardPeerManager(mock_client, iface)
        mock_client._request.return_value = []
        peer_manager.list()
        call_args = mock_client._request.call_args
        assert "wireguard eq 1" in call_args[1]["params"]["filter"]


class TestWireGuardPeerManagerGet:
    """Tests for WireGuardPeerManager.get() method."""

    def test_get_by_key(
        self,
        wireguard_manager: WireGuardManager,
        mock_client: MagicMock,
        sample_peer_data: dict[str, Any],
    ) -> None:
        """Test get peer by key."""
        iface = WireGuardInterface({"$key": 1, "name": "wg0"}, wireguard_manager)
        peer_manager = WireGuardPeerManager(mock_client, iface)
        mock_client._request.return_value = sample_peer_data
        result = peer_manager.get(1)
        assert result.name == "remote-office"

    def test_get_by_name(
        self,
        wireguard_manager: WireGuardManager,
        mock_client: MagicMock,
        sample_peer_data: dict[str, Any],
    ) -> None:
        """Test get peer by name."""
        iface = WireGuardInterface({"$key": 1, "name": "wg0"}, wireguard_manager)
        peer_manager = WireGuardPeerManager(mock_client, iface)
        mock_client._request.return_value = [sample_peer_data]
        result = peer_manager.get(name="remote-office")
        assert result.name == "remote-office"

    def test_get_not_found(
        self, wireguard_manager: WireGuardManager, mock_client: MagicMock
    ) -> None:
        """Test get raises NotFoundError."""
        iface = WireGuardInterface({"$key": 1, "name": "wg0"}, wireguard_manager)
        peer_manager = WireGuardPeerManager(mock_client, iface)
        mock_client._request.return_value = None
        with pytest.raises(NotFoundError):
            peer_manager.get(999)


class TestWireGuardPeerManagerCreate:
    """Tests for WireGuardPeerManager.create() method."""

    def test_create_peer(
        self,
        wireguard_manager: WireGuardManager,
        mock_client: MagicMock,
        sample_peer_data: dict[str, Any],
    ) -> None:
        """Test create peer."""
        iface = WireGuardInterface({"$key": 1, "name": "wg0"}, wireguard_manager)
        peer_manager = WireGuardPeerManager(mock_client, iface)
        mock_client._request.side_effect = [
            {"$key": 1},  # POST
            sample_peer_data,  # GET
        ]
        result = peer_manager.create(
            name="remote-office",
            peer_ip="10.100.0.2",
            public_key="abc123==",
            allowed_ips="192.168.1.0/24",
        )
        assert result.name == "remote-office"

    def test_create_with_all_params(
        self,
        wireguard_manager: WireGuardManager,
        mock_client: MagicMock,
        sample_peer_data: dict[str, Any],
    ) -> None:
        """Test create with all parameters."""
        iface = WireGuardInterface({"$key": 1, "name": "wg0"}, wireguard_manager)
        peer_manager = WireGuardPeerManager(mock_client, iface)
        mock_client._request.side_effect = [
            {"$key": 1},
            sample_peer_data,
        ]
        peer_manager.create(
            name="remote-office",
            peer_ip="10.100.0.2",
            public_key="abc123==",
            allowed_ips="192.168.1.0/24",
            endpoint="vpn.example.com",
            port=51821,
            preshared_key="secretkey==",
            keepalive=30,
            firewall_config="remote_user",
            description="Test peer",
            enabled=False,
        )
        post_call = mock_client._request.call_args_list[0]
        body = post_call[1]["json_data"]
        assert body["name"] == "remote-office"
        assert body["peer_ip"] == "10.100.0.2"
        assert body["endpoint"] == "vpn.example.com"
        assert body["port"] == 51821
        assert body["preshared_key"] == "secretkey=="
        assert body["keepalive"] == 30
        assert body["configure_firewall"] == "remote-user"
        assert body["enabled"] is False

    def test_create_maps_firewall_config(
        self,
        wireguard_manager: WireGuardManager,
        mock_client: MagicMock,
        sample_peer_data: dict[str, Any],
    ) -> None:
        """Test create maps firewall_config to API value."""
        iface = WireGuardInterface({"$key": 1, "name": "wg0"}, wireguard_manager)
        peer_manager = WireGuardPeerManager(mock_client, iface)
        mock_client._request.side_effect = [
            {"$key": 1},
            sample_peer_data,
        ]
        peer_manager.create(
            name="test",
            peer_ip="10.100.0.2",
            public_key="abc==",
            allowed_ips="0.0.0.0/0",
            firewall_config="site_to_site",
        )
        post_call = mock_client._request.call_args_list[0]
        body = post_call[1]["json_data"]
        assert body["configure_firewall"] == "site-to-site"


class TestWireGuardPeerManagerUpdate:
    """Tests for WireGuardPeerManager.update() method."""

    def test_update_peer(
        self,
        wireguard_manager: WireGuardManager,
        mock_client: MagicMock,
        sample_peer_data: dict[str, Any],
    ) -> None:
        """Test update peer."""
        iface = WireGuardInterface({"$key": 1, "name": "wg0"}, wireguard_manager)
        peer_manager = WireGuardPeerManager(mock_client, iface)
        mock_client._request.side_effect = [
            None,  # PUT
            sample_peer_data,  # GET
        ]
        result = peer_manager.update(1, keepalive=30)
        assert result.name == "remote-office"

    def test_update_maps_firewall_config(
        self,
        wireguard_manager: WireGuardManager,
        mock_client: MagicMock,
        sample_peer_data: dict[str, Any],
    ) -> None:
        """Test update maps firewall_config to API value."""
        iface = WireGuardInterface({"$key": 1, "name": "wg0"}, wireguard_manager)
        peer_manager = WireGuardPeerManager(mock_client, iface)
        mock_client._request.side_effect = [
            None,
            sample_peer_data,
        ]
        peer_manager.update(1, firewall_config="remote_user")
        put_call = mock_client._request.call_args_list[0]
        body = put_call[1]["json_data"]
        assert body["configure_firewall"] == "remote-user"

    def test_update_requires_parameters(
        self, wireguard_manager: WireGuardManager, mock_client: MagicMock
    ) -> None:
        """Test update raises ValueError when no parameters."""
        iface = WireGuardInterface({"$key": 1, "name": "wg0"}, wireguard_manager)
        peer_manager = WireGuardPeerManager(mock_client, iface)
        with pytest.raises(ValueError, match="No update parameters"):
            peer_manager.update(1)


class TestWireGuardPeerManagerDelete:
    """Tests for WireGuardPeerManager.delete() method."""

    def test_delete_peer(self, wireguard_manager: WireGuardManager, mock_client: MagicMock) -> None:
        """Test delete peer."""
        iface = WireGuardInterface({"$key": 1, "name": "wg0"}, wireguard_manager)
        peer_manager = WireGuardPeerManager(mock_client, iface)
        mock_client._request.return_value = None
        peer_manager.delete(1)
        mock_client._request.assert_called_with("DELETE", "vnet_wireguard_peers/1")


class TestWireGuardPeerManagerGetConfig:
    """Tests for WireGuardPeerManager.get_config() method."""

    def test_get_config(self, wireguard_manager: WireGuardManager, mock_client: MagicMock) -> None:
        """Test get_config returns configuration."""
        iface = WireGuardInterface({"$key": 1, "name": "wg0"}, wireguard_manager)
        peer_manager = WireGuardPeerManager(mock_client, iface)
        mock_client._request.return_value = {
            "wg_config": "[Interface]\nPrivateKey=abc123==\nAddress=10.100.0.2/24"
        }
        result = peer_manager.get_config(1)
        assert "[Interface]" in result

    def test_get_config_not_found(
        self, wireguard_manager: WireGuardManager, mock_client: MagicMock
    ) -> None:
        """Test get_config raises NotFoundError."""
        iface = WireGuardInterface({"$key": 1, "name": "wg0"}, wireguard_manager)
        peer_manager = WireGuardPeerManager(mock_client, iface)
        mock_client._request.return_value = None
        with pytest.raises(NotFoundError):
            peer_manager.get_config(999)

    def test_get_config_empty(
        self, wireguard_manager: WireGuardManager, mock_client: MagicMock
    ) -> None:
        """Test get_config raises ValueError when empty."""
        iface = WireGuardInterface({"$key": 1, "name": "wg0"}, wireguard_manager)
        peer_manager = WireGuardPeerManager(mock_client, iface)
        mock_client._request.return_value = {"wg_config": ""}
        with pytest.raises(ValueError, match="No configuration available"):
            peer_manager.get_config(1)

    def test_get_config_handles_api_error(
        self, wireguard_manager: WireGuardManager, mock_client: MagicMock
    ) -> None:
        """Test get_config handles API error gracefully."""
        iface = WireGuardInterface({"$key": 1, "name": "wg0"}, wireguard_manager)
        peer_manager = WireGuardPeerManager(mock_client, iface)
        mock_client._request.side_effect = NotFoundError("Not found")
        with pytest.raises(ValueError, match="Configuration not available"):
            peer_manager.get_config(1)


class TestWireGuardInterfacePeersProperty:
    """Tests for WireGuardInterface.peers property."""

    def test_peers_returns_manager(
        self,
        wireguard_manager: WireGuardManager,
        sample_interface_data: dict[str, Any],
    ) -> None:
        """Test peers property returns WireGuardPeerManager."""
        iface = WireGuardInterface(sample_interface_data, wireguard_manager)
        peers = iface.peers
        assert isinstance(peers, WireGuardPeerManager)

    def test_peers_manager_has_correct_interface(
        self,
        wireguard_manager: WireGuardManager,
        sample_interface_data: dict[str, Any],
    ) -> None:
        """Test peers manager is bound to correct interface."""
        iface = WireGuardInterface(sample_interface_data, wireguard_manager)
        peers = iface.peers
        assert peers._interface.key == 1


class TestWireGuardPeerGetConfigMethod:
    """Tests for WireGuardPeer.get_config() method."""

    def test_peer_get_config(
        self, wireguard_manager: WireGuardManager, mock_client: MagicMock
    ) -> None:
        """Test peer.get_config() calls manager method."""
        iface = WireGuardInterface({"$key": 1, "name": "wg0"}, wireguard_manager)
        peer_manager = WireGuardPeerManager(mock_client, iface)
        peer = WireGuardPeer({"$key": 1, "name": "test"}, peer_manager)
        mock_client._request.return_value = {"wg_config": "[Interface]\nTest=1"}
        result = peer.get_config()
        assert "[Interface]" in result
