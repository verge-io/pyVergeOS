"""Integration tests for DNS View operations.

These tests require a live VergeOS system with a network that has DNS (bind) enabled.
Run with: VERGE_HOST=192.168.10.75 VERGE_USERNAME=admin VERGE_PASSWORD=jenifer8 \
          pytest tests/integration/test_dns_views_integration.py -v

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
from pyvergeos.resources.dns import DNSZone, DNSZoneManager
from pyvergeos.resources.dns_views import DNSView, DNSViewManager

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
    """Get a network with DNS (bind) enabled for testing."""
    networks = client.networks.list()
    for network in networks:
        if network.get("dns") == "bind":
            return network

    pytest.skip("No network with bind DNS found")


# =============================================================================
# DNS View Manager Tests
# =============================================================================


class TestDNSViewIntegration:
    """Integration tests for DNS view operations."""

    def test_list_views(self, dns_network) -> None:
        """Test listing DNS views."""
        views = dns_network.dns_views.list()
        assert isinstance(views, list)
        if views:
            assert isinstance(views[0], DNSView)

    def test_dns_views_manager_type(self, dns_network) -> None:
        """Test dns_views property returns correct type."""
        assert isinstance(dns_network.dns_views, DNSViewManager)

    def test_view_properties(self, dns_network) -> None:
        """Test DNS view properties are accessible."""
        views = dns_network.dns_views.list()
        if not views:
            pytest.skip("No DNS views available")

        view = views[0]
        assert view.key > 0
        assert isinstance(view.name, str)
        assert view.name  # should not be empty
        assert isinstance(view.recursion, bool)
        assert isinstance(view.max_cache_size, int)

    def test_get_view_by_key(self, dns_network) -> None:
        """Test getting view by key."""
        views = dns_network.dns_views.list()
        if not views:
            pytest.skip("No DNS views available")

        view = dns_network.dns_views.get(views[0].key)
        assert view.key == views[0].key
        assert view.name == views[0].name

    def test_get_view_by_name(self, dns_network) -> None:
        """Test getting view by name."""
        views = dns_network.dns_views.list()
        if not views:
            pytest.skip("No DNS views available")

        view = dns_network.dns_views.get(name=views[0].name)
        assert view.name == views[0].name

    def test_get_view_not_found(self, dns_network) -> None:
        """Test getting non-existent view raises NotFoundError."""
        with pytest.raises(NotFoundError):
            dns_network.dns_views.get(name="nonexistent-pytest-view-999")

    def test_view_zones_property(self, dns_network) -> None:
        """Test view.zones returns DNSZoneManager."""
        views = dns_network.dns_views.list()
        if not views:
            pytest.skip("No DNS views available")

        view = views[0]
        assert isinstance(view.zones, DNSZoneManager)
        assert view.zones.view_key == view.key

    def test_list_zones_through_view(self, dns_network) -> None:
        """Test listing zones through a view."""
        views = dns_network.dns_views.list()
        if not views:
            pytest.skip("No DNS views available")

        view = views[0]
        zones = view.zones.list()
        assert isinstance(zones, list)
        if zones:
            assert isinstance(zones[0], DNSZone)

    def test_create_update_delete_view(self, dns_network) -> None:
        """Test full CRUD lifecycle for a DNS view."""
        # Create
        view = dns_network.dns_views.create(
            name="pytest-test-view",
            recursion=False,
        )

        try:
            assert view.key > 0
            assert view.name == "pytest-test-view"
            assert view.recursion is False

            # Verify retrieval
            retrieved = dns_network.dns_views.get(view.key)
            assert retrieved.key == view.key
            assert retrieved.name == "pytest-test-view"

            # Update
            updated = dns_network.dns_views.update(
                view.key,
                recursion=True,
            )
            assert updated.recursion is True
            assert updated.name == "pytest-test-view"

        finally:
            # Delete
            dns_network.dns_views.delete(view.key)

            # Verify deletion
            with pytest.raises(NotFoundError):
                dns_network.dns_views.get(view.key)


# =============================================================================
# DNS Zone CRUD Tests (through views)
# =============================================================================


class TestDNSZoneCRUDIntegration:
    """Integration tests for DNS zone create/delete through views."""

    def test_create_and_delete_zone(self, dns_network) -> None:
        """Test creating and deleting a zone through a view."""
        # Create a view for this test
        view = dns_network.dns_views.create(name="pytest-zone-test-view")

        try:
            # Create a zone through the view
            zone = view.zones.create(
                domain="pytest-example.local",
                zone_type="master",
                default_ttl="5m",
            )

            try:
                assert zone.key > 0
                assert zone.domain == "pytest-example.local"
                assert zone.zone_type == "master"

                # Verify it shows in the view's zone list
                zones = view.zones.list()
                zone_domains = [z.domain for z in zones]
                assert "pytest-example.local" in zone_domains

                # Verify it shows in the network's zone list
                all_zones = dns_network.dns_zones.list(
                    domain="pytest-example.local"
                )
                assert len(all_zones) > 0

            finally:
                # Delete the zone
                view.zones.delete(zone.key)

                # Verify zone deletion
                remaining = view.zones.list(domain="pytest-example.local")
                assert len(remaining) == 0

        finally:
            # Delete the view
            dns_network.dns_views.delete(view.key)

    def test_create_zone_with_records(self, dns_network) -> None:
        """Test creating a zone and adding records through the full hierarchy."""
        view = dns_network.dns_views.create(name="pytest-records-test-view")

        try:
            zone = view.zones.create(
                domain="pytest-records.local",
                zone_type="master",
            )

            try:
                # Add a record through the zone
                record = zone.records.create(
                    host="www",
                    record_type="A",
                    value="10.0.0.99",
                )

                try:
                    assert record.key > 0
                    assert record.host == "www"
                    assert record.value == "10.0.0.99"

                    # Verify record is retrievable
                    records = zone.records.list()
                    hosts = [r.host for r in records]
                    assert "www" in hosts

                finally:
                    zone.records.delete(record.key)

            finally:
                view.zones.delete(zone.key)

        finally:
            dns_network.dns_views.delete(view.key)

    def test_create_zone_without_view_raises(self, dns_network) -> None:
        """Test creating a zone without a view raises ValueError."""
        with pytest.raises(ValueError, match="Zone creation requires a view"):
            dns_network.dns_zones.create(domain="should-fail.local")
