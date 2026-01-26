"""Unit tests for NetworkRuleManager."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from pyvergeos import VergeClient
from pyvergeos.exceptions import NotFoundError, ValidationError
from pyvergeos.resources.networks import Network, NetworkManager
from pyvergeos.resources.rules import NetworkRule, NetworkRuleManager


@pytest.fixture
def mock_client() -> MagicMock:
    """Create a mock VergeClient."""
    client = MagicMock(spec=VergeClient)
    client._request = MagicMock()
    return client


@pytest.fixture
def mock_network(mock_client: MagicMock) -> Network:
    """Create a mock Network object."""
    network_data = {
        "$key": 3,
        "name": "External",
        "type": "external",
        "running": True,
    }
    manager = NetworkManager(mock_client)
    return Network(network_data, manager)


@pytest.fixture
def rule_manager(mock_client: MagicMock, mock_network: Network) -> NetworkRuleManager:
    """Create a NetworkRuleManager for testing."""
    return NetworkRuleManager(mock_client, mock_network)


@pytest.fixture
def sample_rule_data() -> dict[str, Any]:
    """Sample rule data from API."""
    return {
        "$key": 10,
        "vnet": 3,
        "vnet_name": "External",
        "name": "Allow HTTPS",
        "description": "Allow incoming HTTPS",
        "enabled": True,
        "orderid": 5,
        "pin": None,
        "direction": "incoming",
        "action": "accept",
        "protocol": "tcp",
        "interface": "auto",
        "source_ip": None,
        "source_ports": None,
        "destination_ip": None,
        "destination_ports": "443",
        "target_ip": None,
        "target_ports": None,
        "ct_state": None,
        "statistics": False,
        "log": True,
        "trace": False,
        "throttle": None,
        "drop_throttle": False,
        "packets": 1234,
        "bytes": 567890,
        "system_rule": False,
        "modified": 1705000000,
    }


@pytest.fixture
def system_rule_data() -> dict[str, Any]:
    """Sample system rule data."""
    return {
        "$key": 1,
        "vnet": 3,
        "vnet_name": "External",
        "name": "System UI",
        "description": "System-generated rule",
        "enabled": True,
        "orderid": 1,
        "direction": "incoming",
        "action": "translate",
        "protocol": "tcp",
        "system_rule": True,
    }


class TestNetworkRule:
    """Tests for NetworkRule object."""

    def test_rule_properties(
        self, rule_manager: NetworkRuleManager, sample_rule_data: dict[str, Any]
    ) -> None:
        """Test NetworkRule property access."""
        rule = NetworkRule(sample_rule_data, rule_manager)

        assert rule.key == 10
        assert rule.network_key == 3
        assert rule.network_name == "External"
        assert rule.name == "Allow HTTPS"
        assert rule.is_enabled is True
        assert rule.is_system_rule is False
        assert rule.order == 5
        assert rule.direction == "incoming"
        assert rule.action == "accept"
        assert rule.protocol == "tcp"
        assert rule.destination_ports == "443"
        assert rule.is_logging is True
        assert rule.has_statistics is False
        assert rule.packet_count == 1234
        assert rule.byte_count == 567890

    def test_system_rule_properties(
        self, rule_manager: NetworkRuleManager, system_rule_data: dict[str, Any]
    ) -> None:
        """Test system rule detection."""
        rule = NetworkRule(system_rule_data, rule_manager)

        assert rule.is_system_rule is True
        assert rule.name == "System UI"

    def test_rule_enable_disable(
        self,
        mock_client: MagicMock,
        rule_manager: NetworkRuleManager,
        sample_rule_data: dict[str, Any],
    ) -> None:
        """Test enable/disable methods."""
        rule = NetworkRule(sample_rule_data, rule_manager)

        # Mock the update call
        mock_client._request.return_value = None

        # Test disable
        with patch.object(rule_manager, "get") as mock_get:
            disabled_data = {**sample_rule_data, "enabled": False}
            mock_get.return_value = NetworkRule(disabled_data, rule_manager)
            result = rule.disable()
            assert result.is_enabled is False

        # Test enable
        with patch.object(rule_manager, "get") as mock_get:
            enabled_data = {**sample_rule_data, "enabled": True}
            mock_get.return_value = NetworkRule(enabled_data, rule_manager)
            result = rule.enable()
            assert result.is_enabled is True

    def test_system_rule_cannot_enable_disable(
        self, rule_manager: NetworkRuleManager, system_rule_data: dict[str, Any]
    ) -> None:
        """Test that system rules cannot be enabled/disabled."""
        rule = NetworkRule(system_rule_data, rule_manager)

        with pytest.raises(ValidationError, match="Cannot modify system rule"):
            rule.enable()

        with pytest.raises(ValidationError, match="Cannot modify system rule"):
            rule.disable()


class TestNetworkRuleManagerList:
    """Tests for NetworkRuleManager.list()."""

    def test_list_all_rules(
        self,
        mock_client: MagicMock,
        rule_manager: NetworkRuleManager,
        sample_rule_data: dict[str, Any],
    ) -> None:
        """Test listing all rules."""
        mock_client._request.return_value = [sample_rule_data]

        rules = rule_manager.list()

        assert len(rules) == 1
        assert rules[0].name == "Allow HTTPS"
        mock_client._request.assert_called_once()
        call_args = mock_client._request.call_args
        assert call_args[0][0] == "GET"
        assert call_args[0][1] == "vnet_rules"
        assert "vnet eq 3" in call_args[1]["params"]["filter"]

    def test_list_with_direction_filter(
        self,
        mock_client: MagicMock,
        rule_manager: NetworkRuleManager,
        sample_rule_data: dict[str, Any],
    ) -> None:
        """Test filtering by direction."""
        mock_client._request.return_value = [sample_rule_data]

        rules = rule_manager.list(direction="incoming")

        assert len(rules) == 1
        call_args = mock_client._request.call_args
        assert "direction eq 'incoming'" in call_args[1]["params"]["filter"]

    def test_list_with_action_filter(
        self,
        mock_client: MagicMock,
        rule_manager: NetworkRuleManager,
        sample_rule_data: dict[str, Any],
    ) -> None:
        """Test filtering by action."""
        mock_client._request.return_value = [sample_rule_data]

        rule_manager.list(action="accept")

        call_args = mock_client._request.call_args
        assert "action eq 'accept'" in call_args[1]["params"]["filter"]

    def test_list_with_protocol_filter(
        self,
        mock_client: MagicMock,
        rule_manager: NetworkRuleManager,
        sample_rule_data: dict[str, Any],
    ) -> None:
        """Test filtering by protocol."""
        mock_client._request.return_value = [sample_rule_data]

        rule_manager.list(protocol="tcp")

        call_args = mock_client._request.call_args
        assert "protocol eq 'tcp'" in call_args[1]["params"]["filter"]

    def test_list_with_enabled_filter(
        self,
        mock_client: MagicMock,
        rule_manager: NetworkRuleManager,
        sample_rule_data: dict[str, Any],
    ) -> None:
        """Test filtering by enabled status."""
        mock_client._request.return_value = [sample_rule_data]

        rule_manager.list(enabled=True)

        call_args = mock_client._request.call_args
        assert "enabled eq true" in call_args[1]["params"]["filter"]

    def test_list_incoming(
        self,
        mock_client: MagicMock,
        rule_manager: NetworkRuleManager,
        sample_rule_data: dict[str, Any],
    ) -> None:
        """Test list_incoming helper."""
        mock_client._request.return_value = [sample_rule_data]

        rule_manager.list_incoming()

        call_args = mock_client._request.call_args
        assert "direction eq 'incoming'" in call_args[1]["params"]["filter"]

    def test_list_outgoing(
        self,
        mock_client: MagicMock,
        rule_manager: NetworkRuleManager,
        sample_rule_data: dict[str, Any],
    ) -> None:
        """Test list_outgoing helper."""
        mock_client._request.return_value = [sample_rule_data]

        rule_manager.list_outgoing()

        call_args = mock_client._request.call_args
        assert "direction eq 'outgoing'" in call_args[1]["params"]["filter"]

    def test_list_empty_response(
        self, mock_client: MagicMock, rule_manager: NetworkRuleManager
    ) -> None:
        """Test handling empty response."""
        mock_client._request.return_value = None

        rules = rule_manager.list()

        assert rules == []


class TestNetworkRuleManagerGet:
    """Tests for NetworkRuleManager.get()."""

    def test_get_by_key(
        self,
        mock_client: MagicMock,
        rule_manager: NetworkRuleManager,
        sample_rule_data: dict[str, Any],
    ) -> None:
        """Test getting a rule by key."""
        mock_client._request.return_value = sample_rule_data

        rule = rule_manager.get(10)

        assert rule.key == 10
        assert rule.name == "Allow HTTPS"
        mock_client._request.assert_called_once()
        call_args = mock_client._request.call_args
        assert call_args[0][0] == "GET"
        assert call_args[0][1] == "vnet_rules/10"

    def test_get_by_name(
        self,
        mock_client: MagicMock,
        rule_manager: NetworkRuleManager,
        sample_rule_data: dict[str, Any],
    ) -> None:
        """Test getting a rule by name."""
        mock_client._request.return_value = [sample_rule_data]

        rule = rule_manager.get(name="Allow HTTPS")

        assert rule.name == "Allow HTTPS"

    def test_get_not_found(self, mock_client: MagicMock, rule_manager: NetworkRuleManager) -> None:
        """Test NotFoundError when rule doesn't exist."""
        mock_client._request.return_value = None

        with pytest.raises(NotFoundError):
            rule_manager.get(999)

    def test_get_by_name_not_found(
        self, mock_client: MagicMock, rule_manager: NetworkRuleManager
    ) -> None:
        """Test NotFoundError when rule name doesn't exist."""
        mock_client._request.return_value = []

        with pytest.raises(NotFoundError, match="not found on this network"):
            rule_manager.get(name="NonExistent")

    def test_get_requires_key_or_name(self, rule_manager: NetworkRuleManager) -> None:
        """Test that get requires either key or name."""
        with pytest.raises(ValueError, match="Either key or name must be provided"):
            rule_manager.get()


class TestNetworkRuleManagerCreate:
    """Tests for NetworkRuleManager.create()."""

    def test_create_basic_rule(
        self, mock_client: MagicMock, rule_manager: NetworkRuleManager
    ) -> None:
        """Test creating a basic accept rule."""
        mock_client._request.side_effect = [
            {"$key": 20},  # POST response
            {  # GET response for fetching created rule
                "$key": 20,
                "vnet": 3,
                "name": "Test Rule",
                "direction": "incoming",
                "action": "accept",
                "protocol": "tcp",
                "destination_ports": "443",
                "enabled": True,
            },
        ]

        rule = rule_manager.create(
            name="Test Rule",
            direction="incoming",
            action="accept",
            protocol="tcp",
            destination_ports="443",
        )

        assert rule.key == 20
        assert rule.name == "Test Rule"

        # Verify POST was called with correct data
        create_call = mock_client._request.call_args_list[0]
        assert create_call[0][0] == "POST"
        assert create_call[0][1] == "vnet_rules"
        body = create_call[1]["json_data"]
        assert body["vnet"] == 3
        assert body["name"] == "Test Rule"
        assert body["direction"] == "incoming"
        assert body["action"] == "accept"
        assert body["protocol"] == "tcp"
        assert body["destination_ports"] == "443"

    def test_create_nat_rule(
        self, mock_client: MagicMock, rule_manager: NetworkRuleManager
    ) -> None:
        """Test creating a NAT/translate rule."""
        mock_client._request.side_effect = [
            {"$key": 21},
            {
                "$key": 21,
                "vnet": 3,
                "name": "NAT Rule",
                "direction": "incoming",
                "action": "translate",
                "protocol": "tcp",
                "destination_ports": "80",
                "target_ip": "192.168.1.10",
                "target_ports": "8080",
                "enabled": True,
            },
        ]

        rule_manager.create(
            name="NAT Rule",
            action="translate",
            protocol="tcp",
            destination_ports="80",
            target_ip="192.168.1.10",
            target_ports="8080",
        )

        create_call = mock_client._request.call_args_list[0]
        body = create_call[1]["json_data"]
        assert body["action"] == "translate"
        assert body["target_ip"] == "192.168.1.10"
        assert body["target_ports"] == "8080"

    def test_create_with_logging(
        self, mock_client: MagicMock, rule_manager: NetworkRuleManager
    ) -> None:
        """Test creating a rule with logging enabled."""
        mock_client._request.side_effect = [
            {"$key": 22},
            {
                "$key": 22,
                "name": "Logged Rule",
                "log": True,
                "statistics": True,
            },
        ]

        rule_manager.create(
            name="Logged Rule",
            log=True,
            statistics=True,
        )

        create_call = mock_client._request.call_args_list[0]
        body = create_call[1]["json_data"]
        assert body["log"] is True
        assert body["statistics"] is True

    def test_create_with_pin_top(
        self, mock_client: MagicMock, rule_manager: NetworkRuleManager
    ) -> None:
        """Test creating a rule pinned to top."""
        mock_client._request.side_effect = [
            {"$key": 23},
            {"$key": 23, "name": "Top Rule", "orderid": 1},
        ]

        rule_manager.create(name="Top Rule", pin="top")

        create_call = mock_client._request.call_args_list[0]
        body = create_call[1]["json_data"]
        assert body["pin"] == "top"


class TestNetworkRuleManagerUpdate:
    """Tests for NetworkRuleManager.update()."""

    def test_update_rule(
        self,
        mock_client: MagicMock,
        rule_manager: NetworkRuleManager,
        sample_rule_data: dict[str, Any],
    ) -> None:
        """Test updating a rule."""
        # First call: get to check system_rule
        # Second call: PUT to update
        # Third call: get to return updated rule
        mock_client._request.side_effect = [
            sample_rule_data,  # GET for system_rule check
            None,  # PUT response
            {**sample_rule_data, "description": "Updated"},  # GET for return
        ]

        updated = rule_manager.update(10, description="Updated")

        assert updated.get("description") == "Updated"
        put_call = mock_client._request.call_args_list[1]
        assert put_call[0][0] == "PUT"
        assert put_call[0][1] == "vnet_rules/10"

    def test_update_system_rule_blocked(
        self,
        mock_client: MagicMock,
        rule_manager: NetworkRuleManager,
        system_rule_data: dict[str, Any],
    ) -> None:
        """Test that updating system rule raises ValidationError."""
        mock_client._request.return_value = system_rule_data

        with pytest.raises(ValidationError, match="Cannot modify system rule"):
            rule_manager.update(1, description="Should fail")


class TestNetworkRuleManagerDelete:
    """Tests for NetworkRuleManager.delete()."""

    def test_delete_rule(
        self,
        mock_client: MagicMock,
        rule_manager: NetworkRuleManager,
        sample_rule_data: dict[str, Any],
    ) -> None:
        """Test deleting a rule."""
        mock_client._request.side_effect = [
            sample_rule_data,  # GET for system_rule check
            None,  # DELETE response
        ]

        rule_manager.delete(10)

        delete_call = mock_client._request.call_args_list[1]
        assert delete_call[0][0] == "DELETE"
        assert delete_call[0][1] == "vnet_rules/10"

    def test_delete_system_rule_blocked(
        self,
        mock_client: MagicMock,
        rule_manager: NetworkRuleManager,
        system_rule_data: dict[str, Any],
    ) -> None:
        """Test that deleting system rule raises ValidationError."""
        mock_client._request.return_value = system_rule_data

        with pytest.raises(ValidationError, match="Cannot delete system rule"):
            rule_manager.delete(1)


class TestNetworkRulesProperty:
    """Tests for Network.rules property."""

    def test_network_rules_property(self, mock_network: Network) -> None:
        """Test accessing rules through network object."""
        rules = mock_network.rules

        assert isinstance(rules, NetworkRuleManager)
        assert rules.network_key == 3
