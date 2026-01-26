"""Integration tests for DNS zone and record operations.

These tests require a live VergeOS system with DNS configured.
Run with: pytest tests/integration/test_dns_integration.py -v

Environment variables:
    VERGE_HOST: VergeOS hostname/IP
    VERGE_USERNAME: Username
    VERGE_PASSWORD: Password
"""

from __future__ import annotations

import os

import pytest

from pyvergeos import VergeClient
from pyvergeos.exceptions import NotFoundError
from pyvergeos.resources.dns import DNSRecordManager, DNSZone, DNSZoneManager

# Skip all tests if not in integration mode
pytestmark = pytest.mark.skipif(
    not os.environ.get("VERGE_HOST"),
    reason="Integration tests require VERGE_HOST environment variable",
)


@pytest.fixture(scope="module")
def client() -> VergeClient:
    """Create a connected VergeClient for integration tests."""
    client = VergeClient(
        host=os.environ.get("VERGE_HOST", ""),
        username=os.environ.get("VERGE_USERNAME", ""),
        password=os.environ.get("VERGE_PASSWORD", ""),
        verify_ssl=False,
    )
    yield client
    client.disconnect()


@pytest.fixture(scope="module")
def dns_network(client: VergeClient):
    """Get or create a network with DNS enabled for testing."""
    # Try to find a network with bind DNS enabled
    networks = client.networks.list()
    for network in networks:
        if network.get("dns") == "bind":
            zones = network.dns_zones.list()
            if zones:
                return network

    # If no suitable network found, skip tests
    pytest.skip("No network with bind DNS and zones found")


@pytest.fixture(scope="module")
def test_zone(dns_network) -> DNSZone:
    """Get a DNS zone for testing."""
    zones = dns_network.dns_zones.list()
    if not zones:
        pytest.skip("No DNS zones available for testing")
    return zones[0]


class TestDNSZoneIntegration:
    """Integration tests for DNS zone operations."""

    def test_list_zones(self, dns_network) -> None:
        """Test listing DNS zones."""
        zones = dns_network.dns_zones.list()
        assert isinstance(zones, list)
        if zones:
            assert isinstance(zones[0], DNSZone)

    def test_dns_zones_manager_type(self, dns_network) -> None:
        """Test dns_zones property returns correct type."""
        assert isinstance(dns_network.dns_zones, DNSZoneManager)

    def test_zone_properties(self, test_zone: DNSZone) -> None:
        """Test DNS zone properties are accessible."""
        assert test_zone.key > 0
        assert test_zone.domain
        assert test_zone.zone_type in [
            "master",
            "slave",
            "redirect",
            "forward",
            "static-stub",
            "stub",
        ]
        assert test_zone.view_key > 0

    def test_get_zone_by_key(self, dns_network, test_zone: DNSZone) -> None:
        """Test getting zone by key."""
        zone = dns_network.dns_zones.get(test_zone.key)
        assert zone.key == test_zone.key
        assert zone.domain == test_zone.domain

    def test_get_zone_by_domain(self, dns_network, test_zone: DNSZone) -> None:
        """Test getting zone by domain."""
        zone = dns_network.dns_zones.get(domain=test_zone.domain)
        assert zone.domain == test_zone.domain

    def test_get_zone_not_found(self, dns_network) -> None:
        """Test getting non-existent zone raises NotFoundError."""
        with pytest.raises(NotFoundError):
            dns_network.dns_zones.get(domain="nonexistent.invalid.domain")

    def test_zone_records_property(self, test_zone: DNSZone) -> None:
        """Test zone.records property returns DNSRecordManager."""
        assert isinstance(test_zone.records, DNSRecordManager)
        assert test_zone.records.zone_key == test_zone.key


class TestDNSRecordIntegration:
    """Integration tests for DNS record operations."""

    def test_list_records(self, test_zone: DNSZone) -> None:
        """Test listing DNS records."""
        records = test_zone.records.list()
        assert isinstance(records, list)

    def test_create_and_delete_a_record(self, test_zone: DNSZone, dns_network) -> None:
        """Test creating and deleting an A record."""
        # Create record
        record = test_zone.records.create(
            host="pytest-test-a",
            record_type="A",
            value="10.0.0.99",
            ttl="5m",
        )

        try:
            assert record.key > 0
            assert record.host == "pytest-test-a"
            assert record.record_type == "A"
            assert record.value == "10.0.0.99"

            # Verify it can be retrieved
            retrieved = test_zone.records.get(record.key)
            assert retrieved.key == record.key
        finally:
            # Clean up
            test_zone.records.delete(record.key)

            # Verify deletion
            with pytest.raises(NotFoundError):
                test_zone.records.get(record.key)

    def test_create_and_delete_cname_record(self, test_zone: DNSZone) -> None:
        """Test creating and deleting a CNAME record."""
        record = test_zone.records.create(
            host="pytest-test-cname",
            record_type="CNAME",
            value="target.example.com",
        )

        try:
            assert record.record_type == "CNAME"
            assert record.value == "target.example.com"
        finally:
            test_zone.records.delete(record.key)

    def test_create_and_delete_mx_record(self, test_zone: DNSZone) -> None:
        """Test creating and deleting an MX record."""
        record = test_zone.records.create(
            host="pytest-mx",
            record_type="MX",
            value="mail.example.com",
            mx_preference=20,
        )

        try:
            assert record.record_type == "MX"
            assert record.mx_preference == 20
        finally:
            test_zone.records.delete(record.key)

    def test_create_and_delete_txt_record(self, test_zone: DNSZone) -> None:
        """Test creating and deleting a TXT record."""
        record = test_zone.records.create(
            host="pytest-txt",
            record_type="TXT",
            value="v=spf1 include:example.com ~all",
        )

        try:
            assert record.record_type == "TXT"
            assert "spf1" in record.value
        finally:
            test_zone.records.delete(record.key)

    def test_create_and_delete_srv_record(self, test_zone: DNSZone) -> None:
        """Test creating and deleting an SRV record."""
        record = test_zone.records.create(
            host="_pytest._tcp",
            record_type="SRV",
            value="pytest.example.com",
            weight=10,
            port=443,
        )

        try:
            assert record.record_type == "SRV"
            assert record.weight == 10
            assert record.port == 443
        finally:
            test_zone.records.delete(record.key)

    def test_get_record_by_host(self, test_zone: DNSZone) -> None:
        """Test getting record by host."""
        record = test_zone.records.create(
            host="pytest-get-host",
            record_type="A",
            value="10.0.0.100",
        )

        try:
            retrieved = test_zone.records.get(host="pytest-get-host")
            assert retrieved.host == "pytest-get-host"
        finally:
            test_zone.records.delete(record.key)

    def test_filter_records_by_type(self, test_zone: DNSZone) -> None:
        """Test filtering records by type."""
        # Create two records of different types
        a_record = test_zone.records.create(
            host="pytest-filter-a",
            record_type="A",
            value="10.0.0.101",
        )
        cname_record = test_zone.records.create(
            host="pytest-filter-cname",
            record_type="CNAME",
            value="target.local",
        )

        try:
            # Filter for A records
            a_records = test_zone.records.list(record_type="A")
            a_hosts = [r.host for r in a_records]
            assert "pytest-filter-a" in a_hosts

            # Filter for CNAME records
            cname_records = test_zone.records.list(record_type="CNAME")
            cname_hosts = [r.host for r in cname_records]
            assert "pytest-filter-cname" in cname_hosts
        finally:
            test_zone.records.delete(a_record.key)
            test_zone.records.delete(cname_record.key)

    def test_get_record_not_found(self, test_zone: DNSZone) -> None:
        """Test getting non-existent record raises NotFoundError."""
        with pytest.raises(NotFoundError):
            test_zone.records.get(host="nonexistent-pytest-record")


class TestDNSApply:
    """Tests for DNS apply functionality."""

    def test_apply_dns_after_changes(self, test_zone: DNSZone, dns_network) -> None:
        """Test applying DNS changes."""
        # Create a record
        record = test_zone.records.create(
            host="pytest-apply",
            record_type="A",
            value="10.0.0.200",
        )

        try:
            # Apply DNS
            dns_network.apply_dns()

            # Verify network's needs_dns_apply flag (if applicable)
            dns_network._manager.get(dns_network.key)
            # The flag should be cleared after apply
        finally:
            test_zone.records.delete(record.key)
            dns_network.apply_dns()
