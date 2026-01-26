"""Unit tests for IPSecConnectionManager and IPSecPolicyManager."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from pyvergeos.exceptions import NotFoundError
from pyvergeos.resources.ipsec import (
    IPSecConnection,
    IPSecConnectionManager,
    IPSecPolicy,
    IPSecPolicyManager,
)
from pyvergeos.resources.networks import Network


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
def ipsec_manager(mock_client: MagicMock, mock_network: Network) -> IPSecConnectionManager:
    """Create an IPSecConnectionManager with mock dependencies."""
    return IPSecConnectionManager(mock_client, mock_network)


@pytest.fixture
def sample_connection_data() -> dict[str, Any]:
    """Sample IPSec connection data from API."""
    return {
        "$key": 1,
        "ipsec": 1,
        "enabled": True,
        "name": "Site-B",
        "description": "Connection to Site B",
        "keyexchange": "ikev2",
        "remote_gateway": "203.0.113.1",
        "auth": "psk",
        "negotiation": "main",
        "identifier": "",
        "peer_identifier": "",
        "ike": "aes256-sha256-modp2048",
        "ikelifetime": 10800,
        "auto": "route",
        "mobike": False,
        "split_connections": False,
        "forceencaps": False,
        "keyingtries": 3,
        "rekey": True,
        "reauth": True,
        "margintime": 540,
        "dpdaction": "restart",
        "dpddelay": 30,
        "dpdfailures": 5,
        "modified": 1706000000,
    }


@pytest.fixture
def sample_policy_data() -> dict[str, Any]:
    """Sample IPSec policy data from API."""
    return {
        "$key": 1,
        "phase1": 1,
        "enabled": True,
        "name": "LAN-to-LAN",
        "description": "LAN traffic policy",
        "mode": "tunnel",
        "local": "10.0.0.0/24",
        "remote": "192.168.1.0/24",
        "lifetime": 3600,
        "protocol": "esp",
        "ciphers": "aes128-sha256-modp2048",
        "modified": 1706000000,
    }


class TestIPSecConnection:
    """Tests for IPSecConnection resource object."""

    def test_key_exchange_display(
        self, ipsec_manager: IPSecConnectionManager, sample_connection_data: dict[str, Any]
    ) -> None:
        """Test key_exchange_display property."""
        conn = IPSecConnection(sample_connection_data, ipsec_manager)
        assert conn.key_exchange_display == "IKEv2"

    def test_key_exchange_display_auto(self, ipsec_manager: IPSecConnectionManager) -> None:
        """Test key_exchange_display for auto mode."""
        conn = IPSecConnection({"$key": 1, "keyexchange": "ike"}, ipsec_manager)
        assert conn.key_exchange_display == "Auto"

    def test_auth_method_display(
        self, ipsec_manager: IPSecConnectionManager, sample_connection_data: dict[str, Any]
    ) -> None:
        """Test auth_method_display property."""
        conn = IPSecConnection(sample_connection_data, ipsec_manager)
        assert conn.auth_method_display == "Pre-Shared Key"

    def test_connection_mode_display(
        self, ipsec_manager: IPSecConnectionManager, sample_connection_data: dict[str, Any]
    ) -> None:
        """Test connection_mode_display property."""
        conn = IPSecConnection(sample_connection_data, ipsec_manager)
        assert conn.connection_mode_display == "On-Demand"

    def test_connection_mode_display_start(self, ipsec_manager: IPSecConnectionManager) -> None:
        """Test connection_mode_display for start mode."""
        conn = IPSecConnection({"$key": 1, "auto": "start"}, ipsec_manager)
        assert conn.connection_mode_display == "Always Start"

    def test_connection_mode_display_add(self, ipsec_manager: IPSecConnectionManager) -> None:
        """Test connection_mode_display for add mode."""
        conn = IPSecConnection({"$key": 1, "auto": "add"}, ipsec_manager)
        assert conn.connection_mode_display == "Responder Only"

    def test_dpd_action_display(
        self, ipsec_manager: IPSecConnectionManager, sample_connection_data: dict[str, Any]
    ) -> None:
        """Test dpd_action_display property."""
        conn = IPSecConnection(sample_connection_data, ipsec_manager)
        assert conn.dpd_action_display == "Restart"

    def test_dpd_action_display_disabled(self, ipsec_manager: IPSecConnectionManager) -> None:
        """Test dpd_action_display for disabled."""
        conn = IPSecConnection({"$key": 1, "dpdaction": "none"}, ipsec_manager)
        assert conn.dpd_action_display == "Disabled"

    def test_is_enabled(
        self, ipsec_manager: IPSecConnectionManager, sample_connection_data: dict[str, Any]
    ) -> None:
        """Test is_enabled property."""
        conn = IPSecConnection(sample_connection_data, ipsec_manager)
        assert conn.is_enabled is True

    def test_is_enabled_false(self, ipsec_manager: IPSecConnectionManager) -> None:
        """Test is_enabled when disabled."""
        conn = IPSecConnection({"$key": 1, "enabled": False}, ipsec_manager)
        assert conn.is_enabled is False

    def test_remote_gateway(
        self, ipsec_manager: IPSecConnectionManager, sample_connection_data: dict[str, Any]
    ) -> None:
        """Test remote_gateway property."""
        conn = IPSecConnection(sample_connection_data, ipsec_manager)
        assert conn.remote_gateway == "203.0.113.1"

    def test_modified_at(
        self, ipsec_manager: IPSecConnectionManager, sample_connection_data: dict[str, Any]
    ) -> None:
        """Test modified_at property."""
        conn = IPSecConnection(sample_connection_data, ipsec_manager)
        assert conn.modified_at is not None

    def test_modified_at_none(self, ipsec_manager: IPSecConnectionManager) -> None:
        """Test modified_at when not set."""
        conn = IPSecConnection({"$key": 1}, ipsec_manager)
        assert conn.modified_at is None


class TestIPSecPolicy:
    """Tests for IPSecPolicy resource object."""

    def test_mode_display_tunnel(
        self, ipsec_manager: IPSecConnectionManager, sample_policy_data: dict[str, Any]
    ) -> None:
        """Test mode_display for tunnel mode."""
        conn = IPSecConnection({"$key": 1, "name": "Test"}, ipsec_manager)
        policy_manager = IPSecPolicyManager(ipsec_manager._client, conn)
        policy = IPSecPolicy(sample_policy_data, policy_manager)
        assert policy.mode_display == "Tunnel"

    def test_mode_display_transport(self, ipsec_manager: IPSecConnectionManager) -> None:
        """Test mode_display for transport mode."""
        conn = IPSecConnection({"$key": 1, "name": "Test"}, ipsec_manager)
        policy_manager = IPSecPolicyManager(ipsec_manager._client, conn)
        policy = IPSecPolicy({"$key": 1, "mode": "transport"}, policy_manager)
        assert policy.mode_display == "Transport"

    def test_protocol_display_esp(
        self, ipsec_manager: IPSecConnectionManager, sample_policy_data: dict[str, Any]
    ) -> None:
        """Test protocol_display for ESP."""
        conn = IPSecConnection({"$key": 1, "name": "Test"}, ipsec_manager)
        policy_manager = IPSecPolicyManager(ipsec_manager._client, conn)
        policy = IPSecPolicy(sample_policy_data, policy_manager)
        assert policy.protocol_display == "ESP (Encrypted)"

    def test_protocol_display_ah(self, ipsec_manager: IPSecConnectionManager) -> None:
        """Test protocol_display for AH."""
        conn = IPSecConnection({"$key": 1, "name": "Test"}, ipsec_manager)
        policy_manager = IPSecPolicyManager(ipsec_manager._client, conn)
        policy = IPSecPolicy({"$key": 1, "protocol": "ah"}, policy_manager)
        assert policy.protocol_display == "AH (Auth Only)"

    def test_is_enabled(
        self, ipsec_manager: IPSecConnectionManager, sample_policy_data: dict[str, Any]
    ) -> None:
        """Test is_enabled property."""
        conn = IPSecConnection({"$key": 1, "name": "Test"}, ipsec_manager)
        policy_manager = IPSecPolicyManager(ipsec_manager._client, conn)
        policy = IPSecPolicy(sample_policy_data, policy_manager)
        assert policy.is_enabled is True

    def test_local_network(
        self, ipsec_manager: IPSecConnectionManager, sample_policy_data: dict[str, Any]
    ) -> None:
        """Test local_network property."""
        conn = IPSecConnection({"$key": 1, "name": "Test"}, ipsec_manager)
        policy_manager = IPSecPolicyManager(ipsec_manager._client, conn)
        policy = IPSecPolicy(sample_policy_data, policy_manager)
        assert policy.local_network == "10.0.0.0/24"

    def test_remote_network(
        self, ipsec_manager: IPSecConnectionManager, sample_policy_data: dict[str, Any]
    ) -> None:
        """Test remote_network property."""
        conn = IPSecConnection({"$key": 1, "name": "Test"}, ipsec_manager)
        policy_manager = IPSecPolicyManager(ipsec_manager._client, conn)
        policy = IPSecPolicy(sample_policy_data, policy_manager)
        assert policy.remote_network == "192.168.1.0/24"


class TestIPSecConnectionManagerList:
    """Tests for IPSecConnectionManager.list() method."""

    def test_list_returns_empty_when_no_ipsec_config(
        self, ipsec_manager: IPSecConnectionManager, mock_client: MagicMock
    ) -> None:
        """Test list returns empty when no IPSec config exists."""
        mock_client._request.return_value = None
        result = ipsec_manager.list()
        assert result == []

    def test_list_returns_connections(
        self,
        ipsec_manager: IPSecConnectionManager,
        mock_client: MagicMock,
        sample_connection_data: dict[str, Any],
    ) -> None:
        """Test list returns connections."""
        # First call gets IPSec config
        # Second call gets connections
        mock_client._request.side_effect = [
            {"$key": 1},  # vnet_ipsecs query
            [sample_connection_data],  # vnet_ipsec_phase1s query
        ]
        result = ipsec_manager.list()
        assert len(result) == 1
        assert result[0].name == "Site-B"

    def test_list_handles_single_connection(
        self,
        ipsec_manager: IPSecConnectionManager,
        mock_client: MagicMock,
        sample_connection_data: dict[str, Any],
    ) -> None:
        """Test list handles single connection (dict instead of list)."""
        mock_client._request.side_effect = [
            {"$key": 1},
            sample_connection_data,  # Single dict, not list
        ]
        result = ipsec_manager.list()
        assert len(result) == 1


class TestIPSecConnectionManagerGet:
    """Tests for IPSecConnectionManager.get() method."""

    def test_get_by_key(
        self,
        ipsec_manager: IPSecConnectionManager,
        mock_client: MagicMock,
        sample_connection_data: dict[str, Any],
    ) -> None:
        """Test get connection by key."""
        mock_client._request.return_value = sample_connection_data
        result = ipsec_manager.get(1)
        assert result.key == 1
        assert result.name == "Site-B"

    def test_get_by_name(
        self,
        ipsec_manager: IPSecConnectionManager,
        mock_client: MagicMock,
        sample_connection_data: dict[str, Any],
    ) -> None:
        """Test get connection by name."""
        mock_client._request.side_effect = [
            {"$key": 1},  # vnet_ipsecs query
            [sample_connection_data],  # vnet_ipsec_phase1s query
        ]
        result = ipsec_manager.get(name="Site-B")
        assert result.name == "Site-B"

    def test_get_by_key_not_found(
        self, ipsec_manager: IPSecConnectionManager, mock_client: MagicMock
    ) -> None:
        """Test get raises NotFoundError when not found."""
        mock_client._request.return_value = None
        with pytest.raises(NotFoundError):
            ipsec_manager.get(999)

    def test_get_by_name_not_found(
        self, ipsec_manager: IPSecConnectionManager, mock_client: MagicMock
    ) -> None:
        """Test get by name raises NotFoundError when not found."""
        mock_client._request.side_effect = [
            {"$key": 1},  # vnet_ipsecs query
            [],  # empty list
        ]
        with pytest.raises(NotFoundError):
            ipsec_manager.get(name="NonExistent")

    def test_get_requires_key_or_name(self, ipsec_manager: IPSecConnectionManager) -> None:
        """Test get raises ValueError when neither key nor name provided."""
        with pytest.raises(ValueError, match="Either key or name"):
            ipsec_manager.get()


class TestIPSecConnectionManagerCreate:
    """Tests for IPSecConnectionManager.create() method."""

    def test_create_connection(
        self,
        ipsec_manager: IPSecConnectionManager,
        mock_client: MagicMock,
        sample_connection_data: dict[str, Any],
    ) -> None:
        """Test create connection."""
        mock_client._request.side_effect = [
            {"$key": 1},  # vnet_ipsecs query (exists)
            {"$key": 1},  # POST vnet_ipsec_phase1s
            sample_connection_data,  # GET to fetch created
        ]
        result = ipsec_manager.create(
            name="Site-B",
            remote_gateway="203.0.113.1",
            pre_shared_key="TestPSK123",
        )
        assert result.name == "Site-B"

    def test_create_creates_ipsec_config_if_missing(
        self,
        ipsec_manager: IPSecConnectionManager,
        mock_client: MagicMock,
        sample_connection_data: dict[str, Any],
    ) -> None:
        """Test create creates IPSec config if not exists."""
        mock_client._request.side_effect = [
            None,  # vnet_ipsecs query (none exists)
            {"$key": 1},  # POST vnet_ipsecs (create config)
            {"$key": 1},  # POST vnet_ipsec_phase1s
            sample_connection_data,  # GET to fetch created
        ]
        ipsec_manager.create(
            name="Site-B",
            remote_gateway="203.0.113.1",
            pre_shared_key="TestPSK123",
        )
        # Verify IPSec config was created (4 API calls)
        assert mock_client._request.call_count == 4


class TestIPSecConnectionManagerUpdate:
    """Tests for IPSecConnectionManager.update() method."""

    def test_update_connection(
        self,
        ipsec_manager: IPSecConnectionManager,
        mock_client: MagicMock,
        sample_connection_data: dict[str, Any],
    ) -> None:
        """Test update connection."""
        mock_client._request.side_effect = [
            None,  # PUT update
            sample_connection_data,  # GET to fetch updated
        ]
        result = ipsec_manager.update(1, description="Updated")
        assert result.name == "Site-B"

    def test_update_maps_friendly_values(
        self,
        ipsec_manager: IPSecConnectionManager,
        mock_client: MagicMock,
        sample_connection_data: dict[str, Any],
    ) -> None:
        """Test update maps friendly values to API values."""
        mock_client._request.side_effect = [
            None,
            sample_connection_data,
        ]
        ipsec_manager.update(1, key_exchange="ikev2", connection_mode="start")
        # Check the PUT call had correct API values
        put_call = mock_client._request.call_args_list[0]
        assert put_call[1]["json_data"]["keyexchange"] == "ikev2"
        assert put_call[1]["json_data"]["auto"] == "start"

    def test_update_requires_parameters(self, ipsec_manager: IPSecConnectionManager) -> None:
        """Test update raises ValueError when no parameters provided."""
        with pytest.raises(ValueError, match="No update parameters"):
            ipsec_manager.update(1)


class TestIPSecConnectionManagerDelete:
    """Tests for IPSecConnectionManager.delete() method."""

    def test_delete_connection(
        self, ipsec_manager: IPSecConnectionManager, mock_client: MagicMock
    ) -> None:
        """Test delete connection."""
        mock_client._request.return_value = None
        ipsec_manager.delete(1)
        mock_client._request.assert_called_with("DELETE", "vnet_ipsec_phase1s/1")


class TestIPSecPolicyManagerList:
    """Tests for IPSecPolicyManager.list() method."""

    def test_list_policies(
        self,
        ipsec_manager: IPSecConnectionManager,
        mock_client: MagicMock,
        sample_policy_data: dict[str, Any],
    ) -> None:
        """Test list policies."""
        conn = IPSecConnection({"$key": 1, "name": "Test"}, ipsec_manager)
        policy_manager = IPSecPolicyManager(mock_client, conn)
        mock_client._request.return_value = [sample_policy_data]
        result = policy_manager.list()
        assert len(result) == 1
        assert result[0].name == "LAN-to-LAN"

    def test_list_handles_empty(
        self, ipsec_manager: IPSecConnectionManager, mock_client: MagicMock
    ) -> None:
        """Test list handles empty response."""
        conn = IPSecConnection({"$key": 1, "name": "Test"}, ipsec_manager)
        policy_manager = IPSecPolicyManager(mock_client, conn)
        mock_client._request.return_value = None
        result = policy_manager.list()
        assert result == []


class TestIPSecPolicyManagerGet:
    """Tests for IPSecPolicyManager.get() method."""

    def test_get_by_key(
        self,
        ipsec_manager: IPSecConnectionManager,
        mock_client: MagicMock,
        sample_policy_data: dict[str, Any],
    ) -> None:
        """Test get policy by key."""
        conn = IPSecConnection({"$key": 1, "name": "Test"}, ipsec_manager)
        policy_manager = IPSecPolicyManager(mock_client, conn)
        mock_client._request.return_value = sample_policy_data
        result = policy_manager.get(1)
        assert result.name == "LAN-to-LAN"

    def test_get_by_name(
        self,
        ipsec_manager: IPSecConnectionManager,
        mock_client: MagicMock,
        sample_policy_data: dict[str, Any],
    ) -> None:
        """Test get policy by name."""
        conn = IPSecConnection({"$key": 1, "name": "Test"}, ipsec_manager)
        policy_manager = IPSecPolicyManager(mock_client, conn)
        mock_client._request.return_value = [sample_policy_data]
        result = policy_manager.get(name="LAN-to-LAN")
        assert result.name == "LAN-to-LAN"

    def test_get_not_found(
        self, ipsec_manager: IPSecConnectionManager, mock_client: MagicMock
    ) -> None:
        """Test get raises NotFoundError."""
        conn = IPSecConnection({"$key": 1, "name": "Test"}, ipsec_manager)
        policy_manager = IPSecPolicyManager(mock_client, conn)
        mock_client._request.return_value = None
        with pytest.raises(NotFoundError):
            policy_manager.get(999)


class TestIPSecPolicyManagerCreate:
    """Tests for IPSecPolicyManager.create() method."""

    def test_create_policy(
        self,
        ipsec_manager: IPSecConnectionManager,
        mock_client: MagicMock,
        sample_policy_data: dict[str, Any],
    ) -> None:
        """Test create policy."""
        conn = IPSecConnection({"$key": 1, "name": "Test"}, ipsec_manager)
        policy_manager = IPSecPolicyManager(mock_client, conn)
        mock_client._request.side_effect = [
            {"$key": 1},  # POST
            sample_policy_data,  # GET
        ]
        result = policy_manager.create(
            name="LAN-to-LAN",
            local_network="10.0.0.0/24",
            remote_network="192.168.1.0/24",
        )
        assert result.name == "LAN-to-LAN"


class TestIPSecPolicyManagerUpdate:
    """Tests for IPSecPolicyManager.update() method."""

    def test_update_policy(
        self,
        ipsec_manager: IPSecConnectionManager,
        mock_client: MagicMock,
        sample_policy_data: dict[str, Any],
    ) -> None:
        """Test update policy."""
        conn = IPSecConnection({"$key": 1, "name": "Test"}, ipsec_manager)
        policy_manager = IPSecPolicyManager(mock_client, conn)
        mock_client._request.side_effect = [
            None,  # PUT
            sample_policy_data,  # GET
        ]
        result = policy_manager.update(1, lifetime=7200)
        assert result.name == "LAN-to-LAN"

    def test_update_requires_parameters(
        self, ipsec_manager: IPSecConnectionManager, mock_client: MagicMock
    ) -> None:
        """Test update raises ValueError when no parameters."""
        conn = IPSecConnection({"$key": 1, "name": "Test"}, ipsec_manager)
        policy_manager = IPSecPolicyManager(mock_client, conn)
        with pytest.raises(ValueError, match="No update parameters"):
            policy_manager.update(1)


class TestIPSecPolicyManagerDelete:
    """Tests for IPSecPolicyManager.delete() method."""

    def test_delete_policy(
        self, ipsec_manager: IPSecConnectionManager, mock_client: MagicMock
    ) -> None:
        """Test delete policy."""
        conn = IPSecConnection({"$key": 1, "name": "Test"}, ipsec_manager)
        policy_manager = IPSecPolicyManager(mock_client, conn)
        mock_client._request.return_value = None
        policy_manager.delete(1)
        mock_client._request.assert_called_with("DELETE", "vnet_ipsec_phase2s/1")
