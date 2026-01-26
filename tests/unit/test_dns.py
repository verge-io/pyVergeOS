"""Unit tests for DNS zone and record operations."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from pyvergeos.exceptions import NotFoundError
from pyvergeos.resources.dns import (
    DNS_RECORD_DEFAULT_FIELDS,
    DNS_ZONE_DEFAULT_FIELDS,
    ZONE_TYPE_DISPLAY,
    DNSRecord,
    DNSRecordManager,
    DNSZone,
    DNSZoneManager,
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
    from pyvergeos.resources.networks import NetworkManager

    manager = MagicMock(spec=NetworkManager)
    manager._client = mock_client
    return Network(
        {
            "$key": 1,
            "name": "test-network",
            "dns": "bind",
        },
        manager,
    )


@pytest.fixture
def zone_manager(mock_client: MagicMock, mock_network: Network) -> DNSZoneManager:
    """Create a DNSZoneManager instance."""
    return DNSZoneManager(mock_client, mock_network)


@pytest.fixture
def mock_zone(zone_manager: DNSZoneManager) -> DNSZone:
    """Create a mock DNSZone object."""
    return DNSZone(
        {
            "$key": 1,
            "view": 1,
            "domain": "test.local",
            "type": "master",
            "nameserver": "ns1.test.local",
            "email": "admin@test.local",
            "default_ttl": "1h",
            "serial_number": 1,
        },
        zone_manager,
        view_key=1,
        view_name="default",
    )


@pytest.fixture
def record_manager(mock_client: MagicMock, mock_zone: DNSZone) -> DNSRecordManager:
    """Create a DNSRecordManager instance."""
    return DNSRecordManager(mock_client, mock_zone)


# =============================================================================
# DNSZone Object Tests
# =============================================================================


class TestDNSZone:
    """Tests for DNSZone resource object."""

    def test_zone_properties(self, mock_zone: DNSZone) -> None:
        """Test DNS zone properties."""
        assert mock_zone.key == 1
        assert mock_zone.domain == "test.local"
        assert mock_zone.zone_type == "master"
        assert mock_zone.zone_type_display == "Primary"
        assert mock_zone.view_key == 1
        assert mock_zone.view_name == "default"
        assert mock_zone.nameserver == "ns1.test.local"
        assert mock_zone.email == "admin@test.local"
        assert mock_zone.default_ttl == "1h"
        assert mock_zone.serial_number == 1

    def test_zone_type_display_mapping(self) -> None:
        """Test all zone type display mappings."""
        assert ZONE_TYPE_DISPLAY["master"] == "Primary"
        assert ZONE_TYPE_DISPLAY["slave"] == "Secondary"
        assert ZONE_TYPE_DISPLAY["redirect"] == "Redirect"
        assert ZONE_TYPE_DISPLAY["forward"] == "Forward"
        assert ZONE_TYPE_DISPLAY["static-stub"] == "Static Stub"
        assert ZONE_TYPE_DISPLAY["stub"] == "Stub"

    def test_zone_records_property(self, mock_client: MagicMock, mock_zone: DNSZone) -> None:
        """Test zone.records property returns DNSRecordManager."""
        records_mgr = mock_zone.records
        assert isinstance(records_mgr, DNSRecordManager)
        assert records_mgr.zone_key == mock_zone.key

    def test_zone_view_key_from_data(self, zone_manager: DNSZoneManager) -> None:
        """Test zone view_key when not passed explicitly."""
        zone = DNSZone({"$key": 1, "view": 5, "domain": "example.com"}, zone_manager)
        assert zone.view_key == 5

    def test_zone_view_key_missing_raises(self, zone_manager: DNSZoneManager) -> None:
        """Test zone view_key raises when not available."""
        zone = DNSZone({"$key": 1, "domain": "example.com"}, zone_manager)
        with pytest.raises(ValueError, match="Zone has no view key"):
            _ = zone.view_key

    def test_zone_empty_domain(self, zone_manager: DNSZoneManager) -> None:
        """Test zone with empty domain."""
        zone = DNSZone({"$key": 1, "view": 1}, zone_manager)
        assert zone.domain == ""


# =============================================================================
# DNSZoneManager Tests
# =============================================================================


class TestDNSZoneManager:
    """Tests for DNSZoneManager operations."""

    def test_network_key_property(self, zone_manager: DNSZoneManager) -> None:
        """Test network_key property."""
        assert zone_manager.network_key == 1

    def test_list_zones_empty_views(
        self, zone_manager: DNSZoneManager, mock_client: MagicMock
    ) -> None:
        """Test list returns empty when no views."""
        mock_client._request.return_value = None
        zones = zone_manager.list()
        assert zones == []

    def test_list_zones_empty_zones(
        self, zone_manager: DNSZoneManager, mock_client: MagicMock
    ) -> None:
        """Test list returns empty when views exist but no zones."""
        mock_client._request.side_effect = [
            [{"$key": 1, "name": "default"}],  # views
            None,  # zones
        ]
        zones = zone_manager.list()
        assert zones == []

    def test_list_zones_success(self, zone_manager: DNSZoneManager, mock_client: MagicMock) -> None:
        """Test list zones successfully."""
        mock_client._request.side_effect = [
            [{"$key": 1, "name": "default"}],  # views
            [
                {"$key": 1, "domain": "test.local", "type": "master"},
                {"$key": 2, "domain": "example.com", "type": "master"},
            ],  # zones
        ]
        zones = zone_manager.list()
        assert len(zones) == 2
        assert zones[0].domain == "test.local"
        assert zones[1].domain == "example.com"

    def test_list_zones_single_response(
        self, zone_manager: DNSZoneManager, mock_client: MagicMock
    ) -> None:
        """Test list zones with single zone response (not list)."""
        mock_client._request.side_effect = [
            [{"$key": 1, "name": "default"}],  # views
            {"$key": 1, "domain": "test.local", "type": "master"},  # single zone
        ]
        zones = zone_manager.list()
        assert len(zones) == 1
        assert zones[0].domain == "test.local"

    def test_list_zones_with_domain_filter(
        self, zone_manager: DNSZoneManager, mock_client: MagicMock
    ) -> None:
        """Test list zones with domain filter."""
        mock_client._request.side_effect = [
            [{"$key": 1, "name": "default"}],
            [{"$key": 1, "domain": "test.local", "type": "master"}],
        ]
        zones = zone_manager.list(domain="test.local")
        assert len(zones) == 1

        # Verify filter was included
        call_args = mock_client._request.call_args_list[1]
        assert "domain eq 'test.local'" in call_args[1]["params"]["filter"]

    def test_list_zones_with_type_filter(
        self, zone_manager: DNSZoneManager, mock_client: MagicMock
    ) -> None:
        """Test list zones with type filter."""
        mock_client._request.side_effect = [
            [{"$key": 1, "name": "default"}],
            [{"$key": 1, "domain": "test.local", "type": "forward"}],
        ]
        zones = zone_manager.list(zone_type="forward")
        assert len(zones) == 1

        call_args = mock_client._request.call_args_list[1]
        assert "type eq 'forward'" in call_args[1]["params"]["filter"]

    def test_list_zones_multiple_views(
        self, zone_manager: DNSZoneManager, mock_client: MagicMock
    ) -> None:
        """Test list zones across multiple views."""
        mock_client._request.side_effect = [
            [
                {"$key": 1, "name": "internal"},
                {"$key": 2, "name": "external"},
            ],  # views
            [{"$key": 1, "domain": "internal.local", "type": "master"}],
            [{"$key": 2, "domain": "external.local", "type": "master"}],
        ]
        zones = zone_manager.list()
        assert len(zones) == 2

    def test_get_zone_by_key(self, zone_manager: DNSZoneManager, mock_client: MagicMock) -> None:
        """Test get zone by key."""
        mock_client._request.return_value = {
            "$key": 1,
            "domain": "test.local",
            "type": "master",
        }
        zone = zone_manager.get(1)
        assert zone.key == 1
        assert zone.domain == "test.local"

    def test_get_zone_by_domain(self, zone_manager: DNSZoneManager, mock_client: MagicMock) -> None:
        """Test get zone by domain."""
        mock_client._request.side_effect = [
            [{"$key": 1, "name": "default"}],  # views
            [{"$key": 1, "domain": "test.local", "type": "master"}],  # zones
        ]
        zone = zone_manager.get(domain="test.local")
        assert zone.domain == "test.local"

    def test_get_zone_not_found_by_key(
        self, zone_manager: DNSZoneManager, mock_client: MagicMock
    ) -> None:
        """Test get zone raises NotFoundError for non-existent key."""
        mock_client._request.return_value = None
        with pytest.raises(NotFoundError, match="DNS zone 999 not found"):
            zone_manager.get(999)

    def test_get_zone_not_found_by_domain(
        self, zone_manager: DNSZoneManager, mock_client: MagicMock
    ) -> None:
        """Test get zone raises NotFoundError for non-existent domain."""
        mock_client._request.side_effect = [
            [{"$key": 1, "name": "default"}],  # views
            [],  # no zones
        ]
        with pytest.raises(NotFoundError, match="DNS zone 'nonexistent'"):
            zone_manager.get(domain="nonexistent")

    def test_get_zone_no_identifier_raises(self, zone_manager: DNSZoneManager) -> None:
        """Test get zone raises ValueError when no identifier provided."""
        with pytest.raises(ValueError, match="Either key or domain must be provided"):
            zone_manager.get()


# =============================================================================
# DNSRecord Object Tests
# =============================================================================


class TestDNSRecord:
    """Tests for DNSRecord resource object."""

    def test_record_properties(self, record_manager: DNSRecordManager) -> None:
        """Test DNS record properties."""
        record = DNSRecord(
            {
                "$key": 1,
                "zone": 1,
                "host": "www",
                "type": "A",
                "value": "192.168.1.100",
                "ttl": "1h",
                "mx_preference": 0,
                "weight": 0,
                "port": 0,
                "description": "Web server",
            },
            record_manager,
        )
        assert record.key == 1
        assert record.zone_key == 1
        assert record.host == "www"
        assert record.record_type == "A"
        assert record.value == "192.168.1.100"
        assert record.ttl == "1h"
        assert record.mx_preference == 0
        assert record.weight == 0
        assert record.port == 0
        assert record.description == "Web server"

    def test_record_mx_properties(self, record_manager: DNSRecordManager) -> None:
        """Test MX record properties."""
        record = DNSRecord(
            {
                "$key": 1,
                "zone": 1,
                "host": "",
                "type": "MX",
                "value": "mail.example.com",
                "mx_preference": 10,
            },
            record_manager,
        )
        assert record.record_type == "MX"
        assert record.mx_preference == 10
        assert record.host == ""

    def test_record_srv_properties(self, record_manager: DNSRecordManager) -> None:
        """Test SRV record properties."""
        record = DNSRecord(
            {
                "$key": 1,
                "zone": 1,
                "host": "_http._tcp",
                "type": "SRV",
                "value": "web.example.com",
                "weight": 5,
                "port": 80,
            },
            record_manager,
        )
        assert record.record_type == "SRV"
        assert record.weight == 5
        assert record.port == 80

    def test_record_zone_key_missing_raises(self, record_manager: DNSRecordManager) -> None:
        """Test record zone_key raises when not available."""
        record = DNSRecord({"$key": 1, "host": "www", "value": "1.2.3.4"}, record_manager)
        with pytest.raises(ValueError, match="Record has no zone key"):
            _ = record.zone_key

    def test_record_defaults(self, record_manager: DNSRecordManager) -> None:
        """Test record default values."""
        record = DNSRecord({"$key": 1, "zone": 1}, record_manager)
        assert record.host == ""
        assert record.record_type == "A"
        assert record.value == ""
        assert record.ttl is None
        assert record.mx_preference == 0
        assert record.weight == 0
        assert record.port == 0
        assert record.description is None


# =============================================================================
# DNSRecordManager Tests
# =============================================================================


class TestDNSRecordManager:
    """Tests for DNSRecordManager operations."""

    def test_zone_key_property(self, record_manager: DNSRecordManager) -> None:
        """Test zone_key property."""
        assert record_manager.zone_key == 1

    def test_list_records_empty(
        self, record_manager: DNSRecordManager, mock_client: MagicMock
    ) -> None:
        """Test list returns empty when no records."""
        mock_client._request.return_value = None
        records = record_manager.list()
        assert records == []

    def test_list_records_success(
        self, record_manager: DNSRecordManager, mock_client: MagicMock
    ) -> None:
        """Test list records successfully."""
        mock_client._request.return_value = [
            {"$key": 1, "zone": 1, "host": "www", "type": "A", "value": "1.2.3.4"},
            {"$key": 2, "zone": 1, "host": "mail", "type": "A", "value": "1.2.3.5"},
        ]
        records = record_manager.list()
        assert len(records) == 2
        assert records[0].host == "www"
        assert records[1].host == "mail"

    def test_list_records_single_response(
        self, record_manager: DNSRecordManager, mock_client: MagicMock
    ) -> None:
        """Test list records with single record response."""
        mock_client._request.return_value = {
            "$key": 1,
            "zone": 1,
            "host": "www",
            "type": "A",
            "value": "1.2.3.4",
        }
        records = record_manager.list()
        assert len(records) == 1

    def test_list_records_with_host_filter(
        self, record_manager: DNSRecordManager, mock_client: MagicMock
    ) -> None:
        """Test list records with host filter."""
        mock_client._request.return_value = [
            {"$key": 1, "zone": 1, "host": "www", "type": "A", "value": "1.2.3.4"},
        ]
        records = record_manager.list(host="www")
        assert len(records) == 1

        call_args = mock_client._request.call_args
        assert "host eq 'www'" in call_args[1]["params"]["filter"]

    def test_list_records_with_type_filter(
        self, record_manager: DNSRecordManager, mock_client: MagicMock
    ) -> None:
        """Test list records with type filter."""
        mock_client._request.return_value = [
            {"$key": 1, "zone": 1, "host": "", "type": "MX", "value": "mail.test.local"},
        ]
        records = record_manager.list(record_type="MX")
        assert len(records) == 1

        call_args = mock_client._request.call_args
        assert "type eq 'MX'" in call_args[1]["params"]["filter"]

    def test_get_record_by_key(
        self, record_manager: DNSRecordManager, mock_client: MagicMock
    ) -> None:
        """Test get record by key."""
        mock_client._request.return_value = {
            "$key": 1,
            "zone": 1,
            "host": "www",
            "type": "A",
            "value": "1.2.3.4",
        }
        record = record_manager.get(1)
        assert record.key == 1
        assert record.host == "www"

    def test_get_record_by_host(
        self, record_manager: DNSRecordManager, mock_client: MagicMock
    ) -> None:
        """Test get record by host."""
        mock_client._request.return_value = [
            {"$key": 1, "zone": 1, "host": "www", "type": "A", "value": "1.2.3.4"},
        ]
        record = record_manager.get(host="www")
        assert record.host == "www"

    def test_get_record_by_type(
        self, record_manager: DNSRecordManager, mock_client: MagicMock
    ) -> None:
        """Test get record by type."""
        mock_client._request.return_value = [
            {"$key": 1, "zone": 1, "host": "", "type": "MX", "value": "mail.test.local"},
        ]
        record = record_manager.get(record_type="MX")
        assert record.record_type == "MX"

    def test_get_record_not_found_by_key(
        self, record_manager: DNSRecordManager, mock_client: MagicMock
    ) -> None:
        """Test get record raises NotFoundError for non-existent key."""
        mock_client._request.return_value = None
        with pytest.raises(NotFoundError, match="DNS record 999 not found"):
            record_manager.get(999)

    def test_get_record_not_found_by_host(
        self, record_manager: DNSRecordManager, mock_client: MagicMock
    ) -> None:
        """Test get record raises NotFoundError for non-existent host."""
        mock_client._request.return_value = []
        with pytest.raises(NotFoundError, match="DNS record with host 'nonexistent'"):
            record_manager.get(host="nonexistent")

    def test_get_record_not_found_by_type(
        self, record_manager: DNSRecordManager, mock_client: MagicMock
    ) -> None:
        """Test get record raises NotFoundError for non-existent type."""
        mock_client._request.return_value = []
        with pytest.raises(NotFoundError, match="DNS record with type 'TXT'"):
            record_manager.get(record_type="TXT")

    def test_get_record_no_identifier_raises(self, record_manager: DNSRecordManager) -> None:
        """Test get record raises ValueError when no identifier provided."""
        with pytest.raises(ValueError, match="Either key, host, or record_type must be provided"):
            record_manager.get()

    def test_create_a_record(
        self, record_manager: DNSRecordManager, mock_client: MagicMock
    ) -> None:
        """Test create A record."""
        mock_client._request.side_effect = [
            {"$key": 1},  # create response
            {"$key": 1, "zone": 1, "host": "www", "type": "A", "value": "1.2.3.4"},
        ]
        record = record_manager.create(host="www", record_type="A", value="1.2.3.4", ttl="1h")
        assert record.key == 1
        assert record.host == "www"

        # Verify POST body
        call_args = mock_client._request.call_args_list[0]
        body = call_args[1]["json_data"]
        assert body["zone"] == 1
        assert body["host"] == "www"
        assert body["type"] == "A"
        assert body["value"] == "1.2.3.4"
        assert body["ttl"] == "1h"

    def test_create_mx_record(
        self, record_manager: DNSRecordManager, mock_client: MagicMock
    ) -> None:
        """Test create MX record."""
        mock_client._request.side_effect = [
            {"$key": 1},
            {
                "$key": 1,
                "zone": 1,
                "host": "",
                "type": "MX",
                "value": "mail.test.local",
                "mx_preference": 10,
            },
        ]
        record = record_manager.create(
            host="", record_type="MX", value="mail.test.local", mx_preference=10
        )
        assert record.record_type == "MX"
        assert record.mx_preference == 10

        call_args = mock_client._request.call_args_list[0]
        body = call_args[1]["json_data"]
        assert body["mx_preference"] == 10

    def test_create_srv_record(
        self, record_manager: DNSRecordManager, mock_client: MagicMock
    ) -> None:
        """Test create SRV record."""
        mock_client._request.side_effect = [
            {"$key": 1},
            {
                "$key": 1,
                "zone": 1,
                "host": "_http._tcp",
                "type": "SRV",
                "value": "web.test.local",
                "weight": 5,
                "port": 80,
            },
        ]
        record = record_manager.create(
            host="_http._tcp",
            record_type="SRV",
            value="web.test.local",
            weight=5,
            port=80,
        )
        assert record.weight == 5
        assert record.port == 80

    def test_create_record_with_description(
        self, record_manager: DNSRecordManager, mock_client: MagicMock
    ) -> None:
        """Test create record with description."""
        mock_client._request.side_effect = [
            {"$key": 1},
            {
                "$key": 1,
                "zone": 1,
                "host": "www",
                "type": "A",
                "value": "1.2.3.4",
                "description": "Web server",
            },
        ]
        record = record_manager.create(
            host="www",
            record_type="A",
            value="1.2.3.4",
            description="Web server",
        )
        assert record.description == "Web server"

    def test_create_record_no_response_raises(
        self, record_manager: DNSRecordManager, mock_client: MagicMock
    ) -> None:
        """Test create record raises when no response."""
        mock_client._request.return_value = None
        with pytest.raises(ValueError, match="No response from create operation"):
            record_manager.create(host="www", record_type="A", value="1.2.3.4")

    def test_create_record_invalid_response_raises(
        self, record_manager: DNSRecordManager, mock_client: MagicMock
    ) -> None:
        """Test create record raises when response is not dict."""
        mock_client._request.return_value = []
        with pytest.raises(ValueError, match="Create operation returned invalid response"):
            record_manager.create(host="www", record_type="A", value="1.2.3.4")

    def test_create_record_no_key_raises(
        self, record_manager: DNSRecordManager, mock_client: MagicMock
    ) -> None:
        """Test create record raises when no key in response."""
        mock_client._request.return_value = {"location": "/v4/records/1"}
        with pytest.raises(ValueError, match="Create response missing \\$key"):
            record_manager.create(host="www", record_type="A", value="1.2.3.4")

    def test_delete_record(self, record_manager: DNSRecordManager, mock_client: MagicMock) -> None:
        """Test delete record."""
        mock_client._request.return_value = None
        record_manager.delete(1)

        mock_client._request.assert_called_once_with("DELETE", "vnet_dns_zone_records/1")


# =============================================================================
# Network Integration Tests
# =============================================================================


class TestNetworkDNSIntegration:
    """Tests for Network.dns_zones property."""

    def test_network_dns_zones_property(
        self, mock_client: MagicMock, mock_network: Network
    ) -> None:
        """Test Network.dns_zones returns DNSZoneManager."""
        manager = mock_network.dns_zones
        assert isinstance(manager, DNSZoneManager)
        assert manager.network_key == mock_network.key

    def test_network_dns_zones_multiple_access(
        self, mock_client: MagicMock, mock_network: Network
    ) -> None:
        """Test Network.dns_zones creates new manager each time."""
        manager1 = mock_network.dns_zones
        manager2 = mock_network.dns_zones
        # Each access creates a new manager instance
        assert manager1.network_key == manager2.network_key


# =============================================================================
# Default Fields Tests
# =============================================================================


class TestDefaultFields:
    """Tests for default field constants."""

    def test_zone_default_fields(self) -> None:
        """Test DNS zone default fields include essential fields."""
        assert "$key" in DNS_ZONE_DEFAULT_FIELDS
        assert "domain" in DNS_ZONE_DEFAULT_FIELDS
        assert "type" in DNS_ZONE_DEFAULT_FIELDS
        assert "view" in DNS_ZONE_DEFAULT_FIELDS
        assert "nameserver" in DNS_ZONE_DEFAULT_FIELDS

    def test_record_default_fields(self) -> None:
        """Test DNS record default fields include essential fields."""
        assert "$key" in DNS_RECORD_DEFAULT_FIELDS
        assert "host" in DNS_RECORD_DEFAULT_FIELDS
        assert "type" in DNS_RECORD_DEFAULT_FIELDS
        assert "value" in DNS_RECORD_DEFAULT_FIELDS
        assert "zone" in DNS_RECORD_DEFAULT_FIELDS
        assert "mx_preference" in DNS_RECORD_DEFAULT_FIELDS
