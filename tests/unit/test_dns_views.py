"""Unit tests for DNS View operations."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from pyvergeos.exceptions import NotFoundError
from pyvergeos.resources.dns import DNSZoneManager
from pyvergeos.resources.dns_views import (
    DNS_VIEW_DEFAULT_FIELDS,
    DNSView,
    DNSViewManager,
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
def view_manager(mock_client: MagicMock, mock_network: Network) -> DNSViewManager:
    """Create a DNSViewManager instance."""
    return DNSViewManager(mock_client, mock_network)


@pytest.fixture
def sample_view_data() -> dict[str, Any]:
    """Sample DNS view data."""
    return {
        "$key": 1,
        "name": "internal",
        "recursion": True,
        "match_clients": "10/8;172.16/16;",
        "match_destinations": None,
        "max_cache_size": 33554432,
        "query_source": None,
        "vnet": 1,
    }


@pytest.fixture
def mock_view(view_manager: DNSViewManager, sample_view_data: dict[str, Any]) -> DNSView:
    """Create a mock DNSView object."""
    return DNSView(sample_view_data, view_manager)


# =============================================================================
# DNSView Object Tests
# =============================================================================


class TestDNSView:
    """Tests for DNSView resource object."""

    def test_view_properties(self, mock_view: DNSView) -> None:
        """Test DNS view properties."""
        assert mock_view.key == 1
        assert mock_view.name == "internal"
        assert mock_view.recursion is True
        assert mock_view.match_clients == "10/8;172.16/16;"
        assert mock_view.match_destinations is None
        assert mock_view.max_cache_size == 33554432
        assert mock_view.query_source is None
        assert mock_view.network_key == 1

    def test_view_defaults(self, view_manager: DNSViewManager) -> None:
        """Test DNS view default values."""
        view = DNSView({"$key": 2, "vnet": 1}, view_manager)
        assert view.name == ""
        assert view.recursion is False
        assert view.match_clients is None
        assert view.match_destinations is None
        assert view.max_cache_size == 0
        assert view.query_source is None

    def test_view_network_key_missing_raises(self, view_manager: DNSViewManager) -> None:
        """Test view network_key raises when not available."""
        view = DNSView({"$key": 1, "name": "test"}, view_manager)
        with pytest.raises(ValueError, match="View has no network key"):
            _ = view.network_key

    def test_view_query_source_int(self, view_manager: DNSViewManager) -> None:
        """Test query_source returns int when set."""
        view = DNSView({"$key": 1, "vnet": 1, "query_source": 5}, view_manager)
        assert view.query_source == 5

    def test_view_zones_property(self, mock_client: MagicMock, mock_view: DNSView) -> None:
        """Test view.zones returns scoped DNSZoneManager."""
        zones_mgr = mock_view.zones
        assert isinstance(zones_mgr, DNSZoneManager)
        assert zones_mgr.view_key == mock_view.key

    def test_view_zones_network_key(self, mock_client: MagicMock, mock_view: DNSView) -> None:
        """Test view.zones manager has correct network key."""
        zones_mgr = mock_view.zones
        assert zones_mgr.network_key == 1


# =============================================================================
# DNSViewManager Tests
# =============================================================================


class TestDNSViewManager:
    """Tests for DNSViewManager operations."""

    def test_network_key_property(self, view_manager: DNSViewManager) -> None:
        """Test network_key property."""
        assert view_manager.network_key == 1

    def test_list_views_empty(self, view_manager: DNSViewManager, mock_client: MagicMock) -> None:
        """Test list returns empty when no views."""
        mock_client._request.return_value = None
        views = view_manager.list()
        assert views == []

    def test_list_views_success(self, view_manager: DNSViewManager, mock_client: MagicMock) -> None:
        """Test list views successfully."""
        mock_client._request.return_value = [
            {"$key": 1, "name": "internal", "vnet": 1},
            {"$key": 2, "name": "external", "vnet": 1},
        ]
        views = view_manager.list()
        assert len(views) == 2
        assert views[0].name == "internal"
        assert views[1].name == "external"

    def test_list_views_single_response(
        self, view_manager: DNSViewManager, mock_client: MagicMock
    ) -> None:
        """Test list views with single view response."""
        mock_client._request.return_value = {
            "$key": 1,
            "name": "default",
            "vnet": 1,
        }
        views = view_manager.list()
        assert len(views) == 1
        assert views[0].name == "default"

    def test_list_views_filters_by_network(
        self, view_manager: DNSViewManager, mock_client: MagicMock
    ) -> None:
        """Test list views filters by network key."""
        mock_client._request.return_value = []
        view_manager.list()

        call_args = mock_client._request.call_args
        assert "vnet eq 1" in call_args[1]["params"]["filter"]

    def test_list_views_with_additional_filter(
        self, view_manager: DNSViewManager, mock_client: MagicMock
    ) -> None:
        """Test list views with additional filter."""
        mock_client._request.return_value = []
        view_manager.list(filter="recursion eq true")

        call_args = mock_client._request.call_args
        filter_str = call_args[1]["params"]["filter"]
        assert "vnet eq 1" in filter_str
        assert "(recursion eq true)" in filter_str

    def test_get_view_by_key(self, view_manager: DNSViewManager, mock_client: MagicMock) -> None:
        """Test get view by key."""
        mock_client._request.return_value = {
            "$key": 1,
            "name": "internal",
            "vnet": 1,
        }
        view = view_manager.get(1)
        assert view.key == 1
        assert view.name == "internal"

    def test_get_view_by_name(
        self,
        view_manager: DNSViewManager,
        mock_client: MagicMock,
    ) -> None:
        """Test get view by name."""
        mock_client._request.return_value = [
            {"$key": 1, "name": "internal", "vnet": 1},
        ]
        view = view_manager.get(name="internal")
        assert view.name == "internal"

        # Verify name filter was included
        call_args = mock_client._request.call_args
        assert "name eq 'internal'" in call_args[1]["params"]["filter"]

    def test_get_view_not_found_by_key(
        self, view_manager: DNSViewManager, mock_client: MagicMock
    ) -> None:
        """Test get view raises NotFoundError for non-existent key."""
        mock_client._request.return_value = None
        with pytest.raises(NotFoundError, match="DNS view 999 not found"):
            view_manager.get(999)

    def test_get_view_not_found_by_name(
        self, view_manager: DNSViewManager, mock_client: MagicMock
    ) -> None:
        """Test get view raises NotFoundError for non-existent name."""
        mock_client._request.return_value = []
        with pytest.raises(NotFoundError, match="DNS view 'nonexistent'"):
            view_manager.get(name="nonexistent")

    def test_get_view_no_identifier_raises(self, view_manager: DNSViewManager) -> None:
        """Test get view raises ValueError when no identifier provided."""
        with pytest.raises(ValueError, match="Either key or name must be provided"):
            view_manager.get()

    def test_get_view_by_key_invalid_response(
        self, view_manager: DNSViewManager, mock_client: MagicMock
    ) -> None:
        """Test get view raises NotFoundError for invalid response."""
        mock_client._request.return_value = []
        with pytest.raises(NotFoundError, match="DNS view 1 returned invalid response"):
            view_manager.get(1)

    def test_create_view_minimal(
        self, view_manager: DNSViewManager, mock_client: MagicMock
    ) -> None:
        """Test create view with minimal params."""
        mock_client._request.side_effect = [
            {"$key": 1},  # create response
            {  # get response
                "$key": 1,
                "name": "internal",
                "recursion": False,
                "vnet": 1,
            },
        ]
        view = view_manager.create(name="internal")
        assert view.key == 1
        assert view.name == "internal"

        # Verify POST body
        call_args = mock_client._request.call_args_list[0]
        body = call_args[1]["json_data"]
        assert body["vnet"] == 1
        assert body["name"] == "internal"
        assert body["recursion"] is False
        assert body["max_cache_size"] == 33554432

    def test_create_view_full_params(
        self, view_manager: DNSViewManager, mock_client: MagicMock
    ) -> None:
        """Test create view with all params."""
        mock_client._request.side_effect = [
            {"$key": 1},
            {
                "$key": 1,
                "name": "internal",
                "recursion": True,
                "match_clients": "10/8;",
                "match_destinations": "172.16/16;",
                "max_cache_size": 67108864,
                "query_source": 5,
                "vnet": 1,
            },
        ]
        view = view_manager.create(
            name="internal",
            recursion=True,
            match_clients="10/8;",
            match_destinations="172.16/16;",
            max_cache_size=67108864,
            query_source=5,
        )
        assert view.recursion is True
        assert view.match_clients == "10/8;"

        call_args = mock_client._request.call_args_list[0]
        body = call_args[1]["json_data"]
        assert body["recursion"] is True
        assert body["match_clients"] == "10/8;"
        assert body["match_destinations"] == "172.16/16;"
        assert body["max_cache_size"] == 67108864
        assert body["query_source"] == 5

    def test_create_view_no_response_raises(
        self, view_manager: DNSViewManager, mock_client: MagicMock
    ) -> None:
        """Test create view raises when no response."""
        mock_client._request.return_value = None
        with pytest.raises(ValueError, match="No response from create"):
            view_manager.create(name="test")

    def test_create_view_invalid_response_raises(
        self, view_manager: DNSViewManager, mock_client: MagicMock
    ) -> None:
        """Test create view raises when response is not dict."""
        mock_client._request.return_value = []
        with pytest.raises(ValueError, match="invalid response"):
            view_manager.create(name="test")

    def test_create_view_no_key_raises(
        self, view_manager: DNSViewManager, mock_client: MagicMock
    ) -> None:
        """Test create view raises when no key in response."""
        mock_client._request.return_value = {"location": "/v4/views/1"}
        with pytest.raises(ValueError, match="missing \\$key"):
            view_manager.create(name="test")

    def test_update_view(self, view_manager: DNSViewManager, mock_client: MagicMock) -> None:
        """Test update view."""
        mock_client._request.side_effect = [
            None,  # PUT response
            {  # GET response
                "$key": 1,
                "name": "internal-updated",
                "recursion": True,
                "vnet": 1,
            },
        ]
        view = view_manager.update(1, name="internal-updated", recursion=True)
        assert view.name == "internal-updated"

        # Verify PUT body
        call_args = mock_client._request.call_args_list[0]
        assert call_args[0][0] == "PUT"
        body = call_args[1]["json_data"]
        assert body["name"] == "internal-updated"
        assert body["recursion"] is True

    def test_update_view_partial(
        self, view_manager: DNSViewManager, mock_client: MagicMock
    ) -> None:
        """Test update view with single field."""
        mock_client._request.side_effect = [
            None,  # PUT response
            {"$key": 1, "name": "internal", "recursion": True, "vnet": 1},
        ]
        view = view_manager.update(1, recursion=True)
        assert view.recursion is True

        call_args = mock_client._request.call_args_list[0]
        body = call_args[1]["json_data"]
        assert body == {"recursion": True}

    def test_update_view_no_changes(
        self, view_manager: DNSViewManager, mock_client: MagicMock
    ) -> None:
        """Test update view with no changes just returns current."""
        mock_client._request.return_value = {
            "$key": 1,
            "name": "internal",
            "vnet": 1,
        }
        view = view_manager.update(1)
        assert view.key == 1

        # Should only call GET, not PUT
        mock_client._request.assert_called_once()

    def test_update_view_all_fields(
        self, view_manager: DNSViewManager, mock_client: MagicMock
    ) -> None:
        """Test update view with all fields."""
        mock_client._request.side_effect = [
            None,  # PUT
            {
                "$key": 1,
                "name": "updated",
                "recursion": True,
                "match_clients": "10/8;",
                "match_destinations": "172.16/16;",
                "max_cache_size": 0,
                "query_source": 3,
                "vnet": 1,
            },
        ]
        _ = view_manager.update(
            1,
            name="updated",
            recursion=True,
            match_clients="10/8;",
            match_destinations="172.16/16;",
            max_cache_size=0,
            query_source=3,
        )

        call_args = mock_client._request.call_args_list[0]
        body = call_args[1]["json_data"]
        assert body["name"] == "updated"
        assert body["recursion"] is True
        assert body["match_clients"] == "10/8;"
        assert body["match_destinations"] == "172.16/16;"
        assert body["max_cache_size"] == 0
        assert body["query_source"] == 3

    def test_delete_view(self, view_manager: DNSViewManager, mock_client: MagicMock) -> None:
        """Test delete view."""
        mock_client._request.return_value = None
        view_manager.delete(1)

        mock_client._request.assert_called_once_with("DELETE", "vnet_dns_views/1")


# =============================================================================
# Network Integration Tests
# =============================================================================


class TestNetworkDNSViewIntegration:
    """Tests for Network.dns_views property."""

    def test_network_dns_views_property(
        self, mock_client: MagicMock, mock_network: Network
    ) -> None:
        """Test Network.dns_views returns DNSViewManager."""
        manager = mock_network.dns_views
        assert isinstance(manager, DNSViewManager)
        assert manager.network_key == mock_network.key

    def test_network_dns_views_multiple_access(
        self, mock_client: MagicMock, mock_network: Network
    ) -> None:
        """Test Network.dns_views creates new manager each time."""
        manager1 = mock_network.dns_views
        manager2 = mock_network.dns_views
        assert manager1.network_key == manager2.network_key


# =============================================================================
# Default Fields Tests
# =============================================================================


class TestDNSViewDefaultFields:
    """Tests for default field constants."""

    def test_view_default_fields(self) -> None:
        """Test DNS view default fields include essential fields."""
        assert "$key" in DNS_VIEW_DEFAULT_FIELDS
        assert "name" in DNS_VIEW_DEFAULT_FIELDS
        assert "recursion" in DNS_VIEW_DEFAULT_FIELDS
        assert "vnet" in DNS_VIEW_DEFAULT_FIELDS
        assert "match_clients" in DNS_VIEW_DEFAULT_FIELDS
        assert "match_destinations" in DNS_VIEW_DEFAULT_FIELDS
        assert "max_cache_size" in DNS_VIEW_DEFAULT_FIELDS
        assert "query_source" in DNS_VIEW_DEFAULT_FIELDS
