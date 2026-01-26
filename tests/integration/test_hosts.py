"""Integration tests for NetworkHostManager.

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
from pyvergeos.resources.hosts import NetworkHost
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
    """Get a network to test hosts on.

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
def cleanup_hosts(test_network: Network):
    """Fixture to track and cleanup test hosts."""
    created_keys: list[int] = []

    yield created_keys

    # Cleanup any hosts we created
    for key in created_keys:
        with contextlib.suppress(NotFoundError):
            test_network.hosts.delete(key)


class TestNetworkHostManagerIntegration:
    """Integration tests for NetworkHostManager."""

    def test_list_hosts(self, test_network: Network) -> None:
        """Test listing hosts on a network."""
        hosts = test_network.hosts.list()

        assert isinstance(hosts, list)
        # Hosts may or may not exist
        for host in hosts:
            assert isinstance(host, NetworkHost)
            assert host.key is not None
            assert host.hostname is not None
            assert host.ip is not None

    def test_create_and_delete_host(self, test_network: Network, cleanup_hosts: list[int]) -> None:
        """Test creating and deleting a host override."""
        # Create a test host
        host = test_network.hosts.create(
            hostname="pytest-server01",
            ip="192.168.200.50",
        )
        cleanup_hosts.append(host.key)

        assert host.hostname == "pytest-server01"
        assert host.ip == "192.168.200.50"
        assert host.host_type == "host"
        assert host.is_host is True
        assert host.is_domain is False
        assert host.network_key == test_network.key
        assert host.network_name == test_network.name

        # Delete the host
        test_network.hosts.delete(host.key)
        cleanup_hosts.remove(host.key)

        # Verify it's gone
        with pytest.raises(NotFoundError):
            test_network.hosts.get(host.key)

    def test_create_domain_type(self, test_network: Network, cleanup_hosts: list[int]) -> None:
        """Test creating a domain type override."""
        host = test_network.hosts.create(
            hostname="mail.pytest.local",
            ip="192.168.200.51",
            host_type="domain",
        )
        cleanup_hosts.append(host.key)

        assert host.hostname == "mail.pytest.local"
        assert host.host_type == "domain"
        assert host.is_domain is True
        assert host.is_host is False

    def test_get_host_by_key(self, test_network: Network, cleanup_hosts: list[int]) -> None:
        """Test getting a host by key."""
        # Create a host
        created = test_network.hosts.create(
            hostname="pytest-getbykey",
            ip="192.168.200.52",
        )
        cleanup_hosts.append(created.key)

        # Get by key
        fetched = test_network.hosts.get(created.key)

        assert fetched.key == created.key
        assert fetched.hostname == created.hostname
        assert fetched.ip == created.ip

    def test_get_host_by_hostname(self, test_network: Network, cleanup_hosts: list[int]) -> None:
        """Test getting a host by hostname."""
        test_hostname = "pytest-getbyhostname"

        # Create a host
        created = test_network.hosts.create(
            hostname=test_hostname,
            ip="192.168.200.53",
        )
        cleanup_hosts.append(created.key)

        # Get by hostname
        fetched = test_network.hosts.get(hostname=test_hostname)

        assert fetched.key == created.key
        assert fetched.hostname == test_hostname

    def test_get_host_by_ip(self, test_network: Network, cleanup_hosts: list[int]) -> None:
        """Test getting a host by IP address."""
        test_ip = "192.168.200.54"

        # Create a host
        created = test_network.hosts.create(
            hostname="pytest-getbyip",
            ip=test_ip,
        )
        cleanup_hosts.append(created.key)

        # Get by IP
        fetched = test_network.hosts.get(ip=test_ip)

        assert fetched.key == created.key
        assert fetched.ip == test_ip

    def test_update_host_ip(self, test_network: Network, cleanup_hosts: list[int]) -> None:
        """Test updating a host's IP address."""
        # Create a host
        host = test_network.hosts.create(
            hostname="pytest-updateip",
            ip="192.168.200.60",
        )
        cleanup_hosts.append(host.key)

        # Update IP
        updated = test_network.hosts.update(host.key, ip="192.168.200.61")

        assert updated.ip == "192.168.200.61"
        assert updated.hostname == "pytest-updateip"

    def test_update_host_hostname(self, test_network: Network, cleanup_hosts: list[int]) -> None:
        """Test updating a host's hostname."""
        # Create a host
        host = test_network.hosts.create(
            hostname="pytest-updatename-old",
            ip="192.168.200.62",
        )
        cleanup_hosts.append(host.key)

        # Update hostname
        updated = test_network.hosts.update(host.key, hostname="pytest-updatename-new")

        assert updated.hostname == "pytest-updatename-new"
        assert updated.ip == "192.168.200.62"

    def test_update_host_type(self, test_network: Network, cleanup_hosts: list[int]) -> None:
        """Test updating a host's type."""
        # Create a host type
        host = test_network.hosts.create(
            hostname="pytest-updatetype",
            ip="192.168.200.63",
            host_type="host",
        )
        cleanup_hosts.append(host.key)

        assert host.is_host is True

        # Update to domain type
        updated = test_network.hosts.update(host.key, host_type="domain")

        assert updated.is_domain is True
        assert updated.is_host is False

    def test_list_with_hostname_filter(
        self, test_network: Network, cleanup_hosts: list[int]
    ) -> None:
        """Test listing hosts with hostname filter."""
        unique_hostname = "pytest-listfilter-hostname"

        # Create a host
        host = test_network.hosts.create(
            hostname=unique_hostname,
            ip="192.168.200.70",
        )
        cleanup_hosts.append(host.key)

        # Filter by hostname
        filtered = test_network.hosts.list(hostname=unique_hostname)

        assert len(filtered) == 1
        assert filtered[0].hostname == unique_hostname

    def test_list_with_ip_filter(self, test_network: Network, cleanup_hosts: list[int]) -> None:
        """Test listing hosts with IP filter."""
        test_ip = "192.168.200.71"

        # Create a host
        host = test_network.hosts.create(
            hostname="pytest-listfilter-ip",
            ip=test_ip,
        )
        cleanup_hosts.append(host.key)

        # Filter by IP
        filtered = test_network.hosts.list(ip=test_ip)

        assert len(filtered) == 1
        assert filtered[0].ip == test_ip

    def test_list_with_type_filter(self, test_network: Network, cleanup_hosts: list[int]) -> None:
        """Test listing hosts with type filter."""
        # Create one of each type
        host = test_network.hosts.create(
            hostname="pytest-typefilter-host",
            ip="192.168.200.72",
            host_type="host",
        )
        cleanup_hosts.append(host.key)

        domain = test_network.hosts.create(
            hostname="pytest-typefilter-domain",
            ip="192.168.200.73",
            host_type="domain",
        )
        cleanup_hosts.append(domain.key)

        # Filter by type
        hosts_only = test_network.hosts.list(host_type="host")
        domains_only = test_network.hosts.list(host_type="domain")

        # Check our test hosts are in the right lists
        host_hostnames = [h.hostname for h in hosts_only]
        domain_hostnames = [d.hostname for d in domains_only]

        assert "pytest-typefilter-host" in host_hostnames
        assert "pytest-typefilter-domain" in domain_hostnames
        assert "pytest-typefilter-host" not in domain_hostnames
        assert "pytest-typefilter-domain" not in host_hostnames

    def test_get_nonexistent_host(self, test_network: Network) -> None:
        """Test that getting a nonexistent host raises NotFoundError."""
        with pytest.raises(NotFoundError):
            test_network.hosts.get(999999)

    def test_get_by_hostname_nonexistent(self, test_network: Network) -> None:
        """Test that getting by nonexistent hostname raises NotFoundError."""
        with pytest.raises(NotFoundError, match="hostname.*not found"):
            test_network.hosts.get(hostname="nonexistent-host-12345")

    def test_get_by_ip_nonexistent(self, test_network: Network) -> None:
        """Test that getting by nonexistent IP raises NotFoundError."""
        with pytest.raises(NotFoundError, match="IP.*not found"):
            test_network.hosts.get(ip="10.255.255.254")

    def test_multiple_hosts(self, test_network: Network, cleanup_hosts: list[int]) -> None:
        """Test creating and listing multiple hosts."""
        # Create multiple hosts
        hosts = []
        for i in range(3):
            host = test_network.hosts.create(
                hostname=f"pytest-multi-{i}",
                ip=f"192.168.200.{80 + i}",
            )
            cleanup_hosts.append(host.key)
            hosts.append(host)

        # List all hosts and verify our test hosts are present
        all_hosts = test_network.hosts.list()
        test_hostnames = {h.hostname for h in hosts}

        found_count = sum(1 for h in all_hosts if h.hostname in test_hostnames)
        assert found_count == 3

    def test_host_properties(self, test_network: Network, cleanup_hosts: list[int]) -> None:
        """Test all host properties."""
        host = test_network.hosts.create(
            hostname="pytest-properties",
            ip="192.168.200.90",
            host_type="host",
        )
        cleanup_hosts.append(host.key)

        # Check all properties
        assert host.key > 0
        assert host.network_key == test_network.key
        assert host.network_name == test_network.name
        assert host.hostname == "pytest-properties"
        assert host.ip == "192.168.200.90"
        assert host.host_type == "host"
        assert host.is_host is True
        assert host.is_domain is False
