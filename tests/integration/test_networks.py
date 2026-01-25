"""Integration tests for Network operations."""

import time

import pytest

from pyvergeos import VergeClient
from pyvergeos.exceptions import NotFoundError


@pytest.mark.integration
class TestNetworkOperations:
    """Integration tests for Network operations against live VergeOS."""

    def test_list_networks(self, live_client: VergeClient) -> None:
        """Test listing networks."""
        networks = live_client.networks.list()
        assert isinstance(networks, list)
        assert len(networks) > 0

        # Each network should have key fields
        network = networks[0]
        assert "$key" in network
        assert "name" in network
        assert "type" in network

    def test_list_networks_has_running_status(self, live_client: VergeClient) -> None:
        """Test that list() includes running status by default."""
        networks = live_client.networks.list()
        if not networks:
            pytest.skip("No networks available")

        network = networks[0]
        # Should have running status from default fields
        assert "running" in network or "status" in network

    def test_list_internal_networks(self, live_client: VergeClient) -> None:
        """Test listing internal networks."""
        internal = live_client.networks.list_internal()
        assert isinstance(internal, list)
        for net in internal:
            assert net.get("type") == "internal"

    def test_list_external_networks(self, live_client: VergeClient) -> None:
        """Test listing external networks."""
        external = live_client.networks.list_external()
        assert isinstance(external, list)
        for net in external:
            assert net.get("type") == "external"

    def test_list_running_networks(self, live_client: VergeClient) -> None:
        """Test listing running networks."""
        running = live_client.networks.list_running()
        assert isinstance(running, list)
        for net in running:
            assert net.is_running is True

    def test_list_stopped_networks(self, live_client: VergeClient) -> None:
        """Test listing stopped networks."""
        stopped = live_client.networks.list_stopped()
        assert isinstance(stopped, list)
        for net in stopped:
            assert net.is_running is False

    def test_get_network_by_key(self, live_client: VergeClient) -> None:
        """Test getting a network by key."""
        networks = live_client.networks.list(limit=1)
        if not networks:
            pytest.skip("No networks available")

        network = live_client.networks.get(networks[0].key)
        assert network.key == networks[0].key
        assert network.name == networks[0].name

    def test_get_network_by_name(self, live_client: VergeClient) -> None:
        """Test getting a network by name."""
        networks = live_client.networks.list(limit=1)
        if not networks:
            pytest.skip("No networks available")

        network = live_client.networks.get(name=networks[0].name)
        assert network.name == networks[0].name
        assert network.key == networks[0].key

    def test_get_network_not_found(self, live_client: VergeClient) -> None:
        """Test getting a non-existent network."""
        with pytest.raises(NotFoundError):
            live_client.networks.get(name="nonexistent-network-12345")

    def test_network_properties(self, live_client: VergeClient) -> None:
        """Test network property access."""
        networks = live_client.networks.list(limit=1)
        if not networks:
            pytest.skip("No networks available")

        network = networks[0]

        # Test is_running property
        assert isinstance(network.is_running, bool)

        # Test status property
        assert isinstance(network.status, str)

        # Test needs_* properties
        assert isinstance(network.needs_rule_apply, bool)
        assert isinstance(network.needs_dns_apply, bool)
        assert isinstance(network.needs_restart, bool)


@pytest.mark.integration
class TestNetworkLifecycle:
    """Integration tests for network create/update/delete lifecycle."""

    TEST_NETWORK_NAME = "pytest-network-001"

    @pytest.fixture(autouse=True)
    def cleanup(self, live_client: VergeClient) -> None:
        """Clean up test networks before and after tests."""
        # Cleanup before test
        self._cleanup_network(live_client, self.TEST_NETWORK_NAME)

        yield

        # Cleanup after test
        self._cleanup_network(live_client, self.TEST_NETWORK_NAME)

    def _cleanup_network(self, client: VergeClient, name: str) -> None:
        """Helper to clean up a network by name."""
        try:
            network = client.networks.get(name=name)
            if network.is_running:
                network.power_off()
                time.sleep(3)
            network.delete()
        except NotFoundError:
            pass  # Network doesn't exist, nothing to clean up

    def test_create_network(self, live_client: VergeClient) -> None:
        """Test creating a network."""
        network = live_client.networks.create(
            name=self.TEST_NETWORK_NAME,
            network_type="internal",
            network_address="10.99.99.0/24",
            ip_address="10.99.99.1",
            description="Test network from pytest",
        )

        assert network.name == self.TEST_NETWORK_NAME
        assert network.get("network") == "10.99.99.0/24"
        assert network.get("ipaddress") == "10.99.99.1"
        assert network.is_running is False

    def test_create_network_with_dhcp(self, live_client: VergeClient) -> None:
        """Test creating a network with DHCP enabled."""
        network = live_client.networks.create(
            name=self.TEST_NETWORK_NAME,
            network_type="internal",
            network_address="10.99.99.0/24",
            ip_address="10.99.99.1",
            dhcp_enabled=True,
            dhcp_start="10.99.99.100",
            dhcp_stop="10.99.99.200",
        )

        assert network.get("dhcp_enabled") is True
        assert network.get("dhcp_start") == "10.99.99.100"
        assert network.get("dhcp_stop") == "10.99.99.200"

    def test_update_network(self, live_client: VergeClient) -> None:
        """Test updating a network."""
        # Create network first
        network = live_client.networks.create(
            name=self.TEST_NETWORK_NAME,
            network_address="10.99.99.0/24",
        )

        # Update description
        live_client.networks.update(network.key, description="Updated description")

        # Verify update
        updated = live_client.networks.get(key=network.key)
        assert updated.get("description") == "Updated description"

    def test_delete_network(self, live_client: VergeClient) -> None:
        """Test deleting a network."""
        # Create network
        network = live_client.networks.create(
            name=self.TEST_NETWORK_NAME,
            network_address="10.99.99.0/24",
        )

        # Delete it
        network.delete()

        # Verify it's gone
        with pytest.raises(NotFoundError):
            live_client.networks.get(name=self.TEST_NETWORK_NAME)


@pytest.mark.integration
class TestNetworkPowerOperations:
    """Integration tests for network power operations."""

    TEST_NETWORK_NAME = "pytest-network-002"

    @pytest.fixture(autouse=True)
    def cleanup(self, live_client: VergeClient) -> None:
        """Clean up test networks before and after tests."""
        self._cleanup_network(live_client, self.TEST_NETWORK_NAME)
        yield
        self._cleanup_network(live_client, self.TEST_NETWORK_NAME)

    def _cleanup_network(self, client: VergeClient, name: str) -> None:
        """Helper to clean up a network by name."""
        try:
            network = client.networks.get(name=name)
            if network.is_running:
                network.power_off()
                time.sleep(3)
            network.delete()
        except NotFoundError:
            pass

    def test_power_on(self, live_client: VergeClient) -> None:
        """Test powering on a network."""
        # Create network
        network = live_client.networks.create(
            name=self.TEST_NETWORK_NAME,
            network_address="10.99.98.0/24",
            ip_address="10.99.98.1",
        )
        assert network.is_running is False

        # Power on
        network.power_on()
        time.sleep(3)

        # Verify
        network = live_client.networks.get(key=network.key)
        assert network.is_running is True
        assert network.status == "running"

    def test_power_off(self, live_client: VergeClient) -> None:
        """Test powering off a network."""
        # Create and power on
        network = live_client.networks.create(
            name=self.TEST_NETWORK_NAME,
            network_address="10.99.98.0/24",
            ip_address="10.99.98.1",
        )
        network.power_on()
        time.sleep(3)

        # Power off
        network.power_off()
        time.sleep(3)

        # Verify
        network = live_client.networks.get(key=network.key)
        assert network.is_running is False
        assert network.status == "stopped"

    def test_restart(self, live_client: VergeClient) -> None:
        """Test restarting a network."""
        # Create and power on
        network = live_client.networks.create(
            name=self.TEST_NETWORK_NAME,
            network_address="10.99.98.0/24",
            ip_address="10.99.98.1",
        )
        network.power_on()
        time.sleep(3)

        # Restart
        network.restart()
        time.sleep(3)

        # Verify still running
        network = live_client.networks.get(key=network.key)
        assert network.is_running is True

    def test_apply_rules(self, live_client: VergeClient) -> None:
        """Test applying firewall rules."""
        # Create and power on
        network = live_client.networks.create(
            name=self.TEST_NETWORK_NAME,
            network_address="10.99.98.0/24",
            ip_address="10.99.98.1",
        )
        network.power_on()
        time.sleep(3)

        # Apply rules should not raise an error
        network.apply_rules()

        # Verify network is still running
        network = live_client.networks.get(key=network.key)
        assert network.is_running is True
