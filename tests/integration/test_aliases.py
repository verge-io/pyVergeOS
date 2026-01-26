"""Integration tests for NetworkAliasManager.

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
from pyvergeos.resources.aliases import NetworkAlias
from pyvergeos.resources.networks import Network

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
    """Get a network to test aliases on.

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
def cleanup_aliases(test_network: Network):
    """Fixture to track and cleanup test aliases."""
    created_keys: list[int] = []

    yield created_keys

    # Cleanup any aliases we created
    for key in created_keys:
        with contextlib.suppress(NotFoundError):
            test_network.aliases.delete(key)


class TestNetworkAliasManagerIntegration:
    """Integration tests for NetworkAliasManager."""

    def test_list_aliases(self, test_network: Network) -> None:
        """Test listing aliases on a network."""
        aliases = test_network.aliases.list()

        assert isinstance(aliases, list)
        # Aliases may or may not exist
        for alias in aliases:
            assert isinstance(alias, NetworkAlias)
            assert alias.key is not None
            assert alias.ip is not None

    def test_create_and_delete_alias(
        self, test_network: Network, cleanup_aliases: list[int]
    ) -> None:
        """Test creating and deleting an alias."""
        # Create a test alias
        alias = test_network.aliases.create(
            ip="192.168.200.100",
            name="pytest-webserver",
            description="Integration test alias",
        )
        cleanup_aliases.append(alias.key)

        assert alias.ip == "192.168.200.100"
        assert alias.hostname == "pytest-webserver"
        assert alias.description == "Integration test alias"
        assert alias.network_key == test_network.key
        assert alias.network_name == test_network.name

        # Delete the alias
        test_network.aliases.delete(alias.key)
        cleanup_aliases.remove(alias.key)

        # Verify it's gone
        with pytest.raises(NotFoundError):
            test_network.aliases.get(alias.key)

    def test_get_alias_by_key(self, test_network: Network, cleanup_aliases: list[int]) -> None:
        """Test getting an alias by key."""
        # Create an alias
        created = test_network.aliases.create(
            ip="192.168.200.101",
            name="pytest-getbykey",
        )
        cleanup_aliases.append(created.key)

        # Get by key
        fetched = test_network.aliases.get(created.key)

        assert fetched.key == created.key
        assert fetched.ip == created.ip
        assert fetched.hostname == created.hostname

    def test_get_alias_by_ip(self, test_network: Network, cleanup_aliases: list[int]) -> None:
        """Test getting an alias by IP address."""
        test_ip = "192.168.200.102"

        # Create an alias
        created = test_network.aliases.create(
            ip=test_ip,
            name="pytest-getbyip",
        )
        cleanup_aliases.append(created.key)

        # Get by IP
        fetched = test_network.aliases.get(ip=test_ip)

        assert fetched.key == created.key
        assert fetched.ip == test_ip

    def test_get_alias_by_hostname(self, test_network: Network, cleanup_aliases: list[int]) -> None:
        """Test getting an alias by hostname."""
        test_hostname = "pytest-getbyhostname"

        # Create an alias
        created = test_network.aliases.create(
            ip="192.168.200.103",
            name=test_hostname,
        )
        cleanup_aliases.append(created.key)

        # Get by hostname
        fetched = test_network.aliases.get(hostname=test_hostname)

        assert fetched.key == created.key
        assert fetched.hostname == test_hostname

    def test_get_alias_by_name(self, test_network: Network, cleanup_aliases: list[int]) -> None:
        """Test getting an alias by name (alias for hostname)."""
        test_name = "pytest-getbyname"

        # Create an alias
        created = test_network.aliases.create(
            ip="192.168.200.104",
            name=test_name,
        )
        cleanup_aliases.append(created.key)

        # Get by name (should work as alias for hostname)
        fetched = test_network.aliases.get(name=test_name)

        assert fetched.key == created.key
        assert fetched.hostname == test_name

    def test_list_with_ip_filter(self, test_network: Network, cleanup_aliases: list[int]) -> None:
        """Test listing aliases with IP filter."""
        # Create two aliases
        alias1 = test_network.aliases.create(
            ip="192.168.200.110",
            name="pytest-filter1",
        )
        cleanup_aliases.append(alias1.key)

        alias2 = test_network.aliases.create(
            ip="192.168.200.111",
            name="pytest-filter2",
        )
        cleanup_aliases.append(alias2.key)

        # Filter by specific IP
        filtered = test_network.aliases.list(ip="192.168.200.110")

        assert len(filtered) == 1
        assert filtered[0].ip == "192.168.200.110"

    def test_list_with_hostname_filter(
        self, test_network: Network, cleanup_aliases: list[int]
    ) -> None:
        """Test listing aliases with hostname filter."""
        unique_name = "pytest-hostnamefilter"

        # Create an alias
        alias = test_network.aliases.create(
            ip="192.168.200.120",
            name=unique_name,
        )
        cleanup_aliases.append(alias.key)

        # Filter by hostname
        filtered = test_network.aliases.list(hostname=unique_name)

        assert len(filtered) == 1
        assert filtered[0].hostname == unique_name

    def test_get_nonexistent_alias(self, test_network: Network) -> None:
        """Test that getting a nonexistent alias raises NotFoundError."""
        with pytest.raises(NotFoundError):
            test_network.aliases.get(999999)

    def test_get_by_ip_nonexistent(self, test_network: Network) -> None:
        """Test that getting by nonexistent IP raises NotFoundError."""
        with pytest.raises(NotFoundError, match="IP .* not found"):
            test_network.aliases.get(ip="10.255.255.254")

    def test_get_by_hostname_nonexistent(self, test_network: Network) -> None:
        """Test that getting by nonexistent hostname raises NotFoundError."""
        with pytest.raises(NotFoundError, match="hostname .* not found"):
            test_network.aliases.get(hostname="nonexistent-alias-12345")

    def test_create_without_description(
        self, test_network: Network, cleanup_aliases: list[int]
    ) -> None:
        """Test creating an alias without a description."""
        alias = test_network.aliases.create(
            ip="192.168.200.130",
            name="pytest-nodesc",
        )
        cleanup_aliases.append(alias.key)

        assert alias.ip == "192.168.200.130"
        assert alias.hostname == "pytest-nodesc"
        # Description may be None or empty string
        assert alias.description is None or alias.description == ""

    def test_alias_properties(self, test_network: Network, cleanup_aliases: list[int]) -> None:
        """Test all alias properties."""
        alias = test_network.aliases.create(
            ip="192.168.200.140",
            name="pytest-properties",
            description="Test all properties",
        )
        cleanup_aliases.append(alias.key)

        # Check all properties
        assert alias.key > 0
        assert alias.network_key == test_network.key
        assert alias.network_name == test_network.name
        assert alias.ip == "192.168.200.140"
        assert alias.hostname == "pytest-properties"
        assert alias.alias_name == "pytest-properties"  # Same as hostname
        assert alias.description == "Test all properties"
        # MAC is typically None or empty for IP aliases
        assert alias.mac is None or alias.mac == ""

    def test_multiple_aliases(self, test_network: Network, cleanup_aliases: list[int]) -> None:
        """Test creating and listing multiple aliases."""
        # Create multiple aliases
        aliases = []
        for i in range(3):
            alias = test_network.aliases.create(
                ip=f"192.168.200.{150 + i}",
                name=f"pytest-multi-{i}",
            )
            cleanup_aliases.append(alias.key)
            aliases.append(alias)

        # List all aliases and verify our test aliases are present
        all_aliases = test_network.aliases.list()
        test_ips = {a.ip for a in aliases}

        found_count = sum(1 for a in all_aliases if a.ip in test_ips)
        assert found_count == 3
