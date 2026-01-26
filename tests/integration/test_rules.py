"""Integration tests for NetworkRuleManager.

These tests require a live VergeOS system.
Configure with environment variables:
    VERGE_HOST, VERGE_USERNAME, VERGE_PASSWORD, VERGE_VERIFY_SSL
"""

from __future__ import annotations

import contextlib
import os

import pytest

from pyvergeos import VergeClient
from pyvergeos.exceptions import NotFoundError, ValidationError
from pyvergeos.resources.networks import Network
from pyvergeos.resources.rules import NetworkRule

# Skip all tests in this module if not running integration tests
pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def client() -> VergeClient:
    """Create a connected client for the test module."""
    # Check for required environment variables
    if not os.environ.get("VERGE_HOST"):
        pytest.skip("VERGE_HOST not set")

    client = VergeClient.from_env()
    client.connect()
    yield client
    client.disconnect()


@pytest.fixture(scope="module")
def test_network(client: VergeClient) -> Network:
    """Get a network to test rules on.

    Uses External network if available, otherwise first available network.
    """
    # Try to get External network
    try:
        return client.networks.get(name="External")
    except NotFoundError:
        pass

    # Fall back to first available network
    networks = client.networks.list()
    if not networks:
        pytest.skip("No networks available for testing")
    return networks[0]


@pytest.fixture
def cleanup_rules(test_network: Network):
    """Fixture to track and cleanup test rules."""
    created_keys: list[int] = []

    yield created_keys

    # Cleanup any rules we created
    for key in created_keys:
        with contextlib.suppress(NotFoundError, ValidationError):
            test_network.rules.delete(key)


class TestNetworkRuleManagerIntegration:
    """Integration tests for NetworkRuleManager."""

    def test_list_rules(self, test_network: Network) -> None:
        """Test listing rules on a network."""
        rules = test_network.rules.list()

        assert isinstance(rules, list)
        # Most networks have at least some rules
        if rules:
            rule = rules[0]
            assert isinstance(rule, NetworkRule)
            assert rule.key is not None
            assert rule.name is not None
            assert rule.direction in ("incoming", "outgoing")

    def test_list_incoming_rules(self, test_network: Network) -> None:
        """Test listing incoming rules."""
        incoming = test_network.rules.list_incoming()

        for rule in incoming:
            assert rule.direction == "incoming"

    def test_list_outgoing_rules(self, test_network: Network) -> None:
        """Test listing outgoing rules."""
        outgoing = test_network.rules.list_outgoing()

        for rule in outgoing:
            assert rule.direction == "outgoing"

    def test_list_with_filters(self, test_network: Network) -> None:
        """Test listing rules with various filters."""
        # Filter by direction
        incoming = test_network.rules.list(direction="incoming")
        for rule in incoming:
            assert rule.direction == "incoming"

        # Filter by enabled
        enabled = test_network.rules.list(enabled=True)
        for rule in enabled:
            assert rule.is_enabled is True

    def test_create_and_delete_rule(self, test_network: Network, cleanup_rules: list[int]) -> None:
        """Test creating and deleting a rule."""
        # Create a test rule
        rule = test_network.rules.create(
            name="PyTest-IntegrationTest-Accept",
            direction="incoming",
            action="accept",
            protocol="tcp",
            destination_ports="9999",
            description="Integration test rule",
        )
        cleanup_rules.append(rule.key)

        assert rule.name == "PyTest-IntegrationTest-Accept"
        assert rule.direction == "incoming"
        assert rule.action == "accept"
        assert rule.protocol == "tcp"
        assert rule.destination_ports == "9999"
        assert rule.is_enabled is True
        assert rule.is_system_rule is False

        # Delete the rule
        test_network.rules.delete(rule.key)
        cleanup_rules.remove(rule.key)

        # Verify it's gone
        with pytest.raises(NotFoundError):
            test_network.rules.get(rule.key)

    def test_create_nat_rule(self, test_network: Network, cleanup_rules: list[int]) -> None:
        """Test creating a NAT/translate rule."""
        rule = test_network.rules.create(
            name="PyTest-IntegrationTest-NAT",
            direction="incoming",
            action="translate",
            protocol="tcp",
            destination_ports="8888",
            target_ip="192.168.100.99",
            target_ports="80",
            description="NAT test rule",
        )
        cleanup_rules.append(rule.key)

        assert rule.action == "translate"
        assert rule.target_ip == "192.168.100.99"
        assert rule.target_ports == "80"

    def test_create_drop_rule(self, test_network: Network, cleanup_rules: list[int]) -> None:
        """Test creating a drop rule."""
        rule = test_network.rules.create(
            name="PyTest-IntegrationTest-Drop",
            direction="incoming",
            action="drop",
            protocol="any",
            source_ip="10.255.255.0/24",
            description="Drop test rule",
        )
        cleanup_rules.append(rule.key)

        assert rule.action == "drop"
        assert rule.protocol == "any"
        assert rule.source_ip == "10.255.255.0/24"

    def test_get_rule_by_key(self, test_network: Network, cleanup_rules: list[int]) -> None:
        """Test getting a rule by key."""
        # Create a rule
        created = test_network.rules.create(
            name="PyTest-IntegrationTest-GetByKey",
            direction="incoming",
            action="accept",
            protocol="udp",
            destination_ports="5353",
        )
        cleanup_rules.append(created.key)

        # Get by key
        fetched = test_network.rules.get(created.key)

        assert fetched.key == created.key
        assert fetched.name == created.name

    def test_get_rule_by_name(self, test_network: Network, cleanup_rules: list[int]) -> None:
        """Test getting a rule by name."""
        rule_name = "PyTest-IntegrationTest-GetByName"

        # Create a rule
        created = test_network.rules.create(
            name=rule_name,
            direction="incoming",
            action="accept",
            protocol="tcp",
            destination_ports="8080",
        )
        cleanup_rules.append(created.key)

        # Get by name
        fetched = test_network.rules.get(name=rule_name)

        assert fetched.key == created.key
        assert fetched.name == rule_name

    def test_update_rule(self, test_network: Network, cleanup_rules: list[int]) -> None:
        """Test updating a rule."""
        # Create a rule
        rule = test_network.rules.create(
            name="PyTest-IntegrationTest-Update",
            direction="incoming",
            action="accept",
            protocol="tcp",
            destination_ports="7777",
            description="Original description",
        )
        cleanup_rules.append(rule.key)

        # Update it
        updated = test_network.rules.update(
            rule.key,
            description="Updated description",
            destination_ports="7777,7778",
        )

        assert updated.get("description") == "Updated description"
        assert updated.destination_ports == "7777,7778"

    def test_enable_disable_rule(self, test_network: Network, cleanup_rules: list[int]) -> None:
        """Test enabling and disabling a rule."""
        # Create a rule
        rule = test_network.rules.create(
            name="PyTest-IntegrationTest-EnableDisable",
            direction="incoming",
            action="accept",
            protocol="tcp",
            destination_ports="6666",
        )
        cleanup_rules.append(rule.key)

        assert rule.is_enabled is True

        # Disable
        disabled = rule.disable()
        assert disabled.is_enabled is False

        # Enable
        enabled = disabled.enable()
        assert enabled.is_enabled is True

    def test_create_with_logging(self, test_network: Network, cleanup_rules: list[int]) -> None:
        """Test creating a rule with logging enabled."""
        rule = test_network.rules.create(
            name="PyTest-IntegrationTest-Logging",
            direction="incoming",
            action="accept",
            protocol="tcp",
            destination_ports="5555",
            log=True,
            statistics=True,
        )
        cleanup_rules.append(rule.key)

        assert rule.is_logging is True
        assert rule.has_statistics is True

    def test_create_with_pin_top(self, test_network: Network, cleanup_rules: list[int]) -> None:
        """Test creating a rule pinned to top."""
        rule = test_network.rules.create(
            name="PyTest-IntegrationTest-PinTop",
            direction="incoming",
            action="drop",
            protocol="any",
            pin="top",
        )
        cleanup_rules.append(rule.key)

        # Rule should have a low order number
        assert rule.order <= 10  # Should be near the top

    def test_system_rule_protection(self, test_network: Network) -> None:
        """Test that system rules cannot be modified or deleted."""
        # Find a system rule
        rules = test_network.rules.list()
        system_rules = [r for r in rules if r.is_system_rule]

        if not system_rules:
            pytest.skip("No system rules found on test network")

        system_rule = system_rules[0]

        # Cannot modify
        with pytest.raises(ValidationError, match="Cannot modify system rule"):
            test_network.rules.update(system_rule.key, description="Modified")

        # Cannot delete
        with pytest.raises(ValidationError, match="Cannot delete system rule"):
            test_network.rules.delete(system_rule.key)

    def test_get_nonexistent_rule(self, test_network: Network) -> None:
        """Test that getting a nonexistent rule raises NotFoundError."""
        with pytest.raises(NotFoundError):
            test_network.rules.get(999999)

    def test_get_by_name_nonexistent(self, test_network: Network) -> None:
        """Test that getting by nonexistent name raises NotFoundError."""
        with pytest.raises(NotFoundError, match="not found on this network"):
            test_network.rules.get(name="NonExistent-Rule-12345")

    def test_rule_properties(self, test_network: Network, cleanup_rules: list[int]) -> None:
        """Test all rule properties."""
        rule = test_network.rules.create(
            name="PyTest-IntegrationTest-Properties",
            direction="incoming",
            action="translate",
            protocol="tcp",
            interface="auto",
            source_ip="10.0.0.0/8",
            source_ports="1024-65535",
            destination_ip="192.168.1.1",
            destination_ports="80,443",
            target_ip="192.168.100.10",
            target_ports="8080",
            description="Full property test",
            log=True,
            statistics=True,
        )
        cleanup_rules.append(rule.key)

        # Check all properties
        assert rule.network_key == test_network.key
        assert rule.network_name == test_network.name
        assert rule.is_enabled is True
        assert rule.is_system_rule is False
        assert rule.direction == "incoming"
        assert rule.action == "translate"
        assert rule.protocol == "tcp"
        assert rule.source_ip == "10.0.0.0/8"
        assert rule.source_ports == "1024-65535"
        assert rule.destination_ip == "192.168.1.1"
        assert rule.destination_ports == "80,443"
        assert rule.target_ip == "192.168.100.10"
        assert rule.target_ports == "8080"
        assert rule.is_logging is True
        assert rule.has_statistics is True

    def test_apply_rules_after_changes(
        self, test_network: Network, cleanup_rules: list[int]
    ) -> None:
        """Test that apply_rules can be called after rule changes."""
        # Create a rule
        rule = test_network.rules.create(
            name="PyTest-IntegrationTest-Apply",
            direction="incoming",
            action="accept",
            protocol="tcp",
            destination_ports="4444",
        )
        cleanup_rules.append(rule.key)

        # Apply rules on the network
        test_network.apply_rules()

        # Should not raise an error
        # Note: needs_rule_apply may still be True depending on timing
