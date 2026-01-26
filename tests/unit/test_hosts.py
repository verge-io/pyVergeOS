"""Unit tests for NetworkHostManager."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from pyvergeos.exceptions import NotFoundError
from pyvergeos.resources.hosts import NetworkHost, NetworkHostManager
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
        "$key": 1,
        "name": "TestNetwork",
        "type": "internal",
    }
    # Create a mock manager
    manager = MagicMock()
    manager._client = mock_client
    return Network(network_data, manager)


@pytest.fixture
def host_manager(mock_client: MagicMock, mock_network: Network) -> NetworkHostManager:
    """Create a NetworkHostManager with mock dependencies."""
    return NetworkHostManager(mock_client, mock_network)


@pytest.fixture
def sample_host_data() -> dict[str, Any]:
    """Sample host override data from API."""
    return {
        "$key": 10,
        "vnet": 1,
        "vnet_name": "TestNetwork",
        "type": "host",
        "host": "server01",
        "ip": "10.0.0.50",
    }


@pytest.fixture
def sample_domain_data() -> dict[str, Any]:
    """Sample domain override data from API."""
    return {
        "$key": 11,
        "vnet": 1,
        "vnet_name": "TestNetwork",
        "type": "domain",
        "host": "mail.example.com",
        "ip": "10.0.0.25",
    }


class TestNetworkHost:
    """Tests for NetworkHost resource object."""

    def test_hostname_property(
        self, host_manager: NetworkHostManager, sample_host_data: dict[str, Any]
    ) -> None:
        """Test hostname property."""
        host = NetworkHost(sample_host_data, host_manager)
        assert host.hostname == "server01"

    def test_ip_property(
        self, host_manager: NetworkHostManager, sample_host_data: dict[str, Any]
    ) -> None:
        """Test ip property."""
        host = NetworkHost(sample_host_data, host_manager)
        assert host.ip == "10.0.0.50"

    def test_network_key_property(
        self, host_manager: NetworkHostManager, sample_host_data: dict[str, Any]
    ) -> None:
        """Test network_key property."""
        host = NetworkHost(sample_host_data, host_manager)
        assert host.network_key == 1

    def test_network_name_property(
        self, host_manager: NetworkHostManager, sample_host_data: dict[str, Any]
    ) -> None:
        """Test network_name property."""
        host = NetworkHost(sample_host_data, host_manager)
        assert host.network_name == "TestNetwork"

    def test_host_type_property(
        self, host_manager: NetworkHostManager, sample_host_data: dict[str, Any]
    ) -> None:
        """Test host_type property."""
        host = NetworkHost(sample_host_data, host_manager)
        assert host.host_type == "host"

    def test_is_host_property(
        self, host_manager: NetworkHostManager, sample_host_data: dict[str, Any]
    ) -> None:
        """Test is_host property."""
        host = NetworkHost(sample_host_data, host_manager)
        assert host.is_host is True
        assert host.is_domain is False

    def test_is_domain_property(
        self, host_manager: NetworkHostManager, sample_domain_data: dict[str, Any]
    ) -> None:
        """Test is_domain property."""
        host = NetworkHost(sample_domain_data, host_manager)
        assert host.is_domain is True
        assert host.is_host is False

    def test_hostname_missing_raises(self, host_manager: NetworkHostManager) -> None:
        """Test that missing hostname raises ValueError."""
        host = NetworkHost({"$key": 1, "ip": "10.0.0.1"}, host_manager)
        with pytest.raises(ValueError, match="no hostname"):
            _ = host.hostname

    def test_ip_missing_raises(self, host_manager: NetworkHostManager) -> None:
        """Test that missing IP raises ValueError."""
        host = NetworkHost({"$key": 1, "host": "test"}, host_manager)
        with pytest.raises(ValueError, match="no IP"):
            _ = host.ip

    def test_network_key_missing_raises(self, host_manager: NetworkHostManager) -> None:
        """Test that missing network key raises ValueError."""
        host = NetworkHost({"$key": 1, "host": "test", "ip": "10.0.0.1"}, host_manager)
        with pytest.raises(ValueError, match="no network"):
            _ = host.network_key


class TestNetworkHostManagerList:
    """Tests for NetworkHostManager.list() method."""

    def test_list_returns_hosts(
        self,
        host_manager: NetworkHostManager,
        mock_client: MagicMock,
        sample_host_data: dict[str, Any],
    ) -> None:
        """Test that list returns host objects."""
        mock_client._request.return_value = [sample_host_data]

        hosts = host_manager.list()

        assert len(hosts) == 1
        assert isinstance(hosts[0], NetworkHost)
        assert hosts[0].hostname == "server01"

    def test_list_with_empty_response(
        self, host_manager: NetworkHostManager, mock_client: MagicMock
    ) -> None:
        """Test list with no hosts."""
        mock_client._request.return_value = None

        hosts = host_manager.list()

        assert hosts == []

    def test_list_builds_correct_filter(
        self, host_manager: NetworkHostManager, mock_client: MagicMock
    ) -> None:
        """Test that list builds correct filter with network key."""
        mock_client._request.return_value = []

        host_manager.list()

        call_args = mock_client._request.call_args
        params = call_args[1]["params"]
        assert "vnet eq 1" in params["filter"]

    def test_list_with_hostname_filter(
        self, host_manager: NetworkHostManager, mock_client: MagicMock
    ) -> None:
        """Test list with hostname filter."""
        mock_client._request.return_value = []

        host_manager.list(hostname="server01")

        call_args = mock_client._request.call_args
        params = call_args[1]["params"]
        assert "host eq 'server01'" in params["filter"]

    def test_list_with_ip_filter(
        self, host_manager: NetworkHostManager, mock_client: MagicMock
    ) -> None:
        """Test list with IP filter."""
        mock_client._request.return_value = []

        host_manager.list(ip="10.0.0.50")

        call_args = mock_client._request.call_args
        params = call_args[1]["params"]
        assert "ip eq '10.0.0.50'" in params["filter"]

    def test_list_with_type_filter(
        self, host_manager: NetworkHostManager, mock_client: MagicMock
    ) -> None:
        """Test list with host_type filter."""
        mock_client._request.return_value = []

        host_manager.list(host_type="domain")

        call_args = mock_client._request.call_args
        params = call_args[1]["params"]
        assert "type eq 'domain'" in params["filter"]

    def test_list_with_custom_filter(
        self, host_manager: NetworkHostManager, mock_client: MagicMock
    ) -> None:
        """Test list with additional OData filter."""
        mock_client._request.return_value = []

        host_manager.list(filter="host ne 'test'")

        call_args = mock_client._request.call_args
        params = call_args[1]["params"]
        assert "(host ne 'test')" in params["filter"]

    def test_list_sorted_by_hostname(
        self, host_manager: NetworkHostManager, mock_client: MagicMock
    ) -> None:
        """Test that list sorts by hostname."""
        mock_client._request.return_value = []

        host_manager.list()

        call_args = mock_client._request.call_args
        params = call_args[1]["params"]
        assert params["sort"] == "+host"

    def test_list_single_object_response(
        self,
        host_manager: NetworkHostManager,
        mock_client: MagicMock,
        sample_host_data: dict[str, Any],
    ) -> None:
        """Test list handles single object response."""
        mock_client._request.return_value = sample_host_data

        hosts = host_manager.list()

        assert len(hosts) == 1
        assert hosts[0].hostname == "server01"


class TestNetworkHostManagerGet:
    """Tests for NetworkHostManager.get() method."""

    def test_get_by_key(
        self,
        host_manager: NetworkHostManager,
        mock_client: MagicMock,
        sample_host_data: dict[str, Any],
    ) -> None:
        """Test getting host by key."""
        mock_client._request.return_value = sample_host_data

        host = host_manager.get(10)

        assert host.key == 10
        mock_client._request.assert_called_once()
        assert "vnet_hosts/10" in mock_client._request.call_args[0][1]

    def test_get_by_hostname(
        self,
        host_manager: NetworkHostManager,
        mock_client: MagicMock,
        sample_host_data: dict[str, Any],
    ) -> None:
        """Test getting host by hostname."""
        mock_client._request.return_value = [sample_host_data]

        host = host_manager.get(hostname="server01")

        assert host.hostname == "server01"

    def test_get_by_ip(
        self,
        host_manager: NetworkHostManager,
        mock_client: MagicMock,
        sample_host_data: dict[str, Any],
    ) -> None:
        """Test getting host by IP."""
        mock_client._request.return_value = [sample_host_data]

        host = host_manager.get(ip="10.0.0.50")

        assert host.ip == "10.0.0.50"

    def test_get_by_key_not_found(
        self, host_manager: NetworkHostManager, mock_client: MagicMock
    ) -> None:
        """Test get by key raises NotFoundError when not found."""
        mock_client._request.return_value = None

        with pytest.raises(NotFoundError, match="not found"):
            host_manager.get(999)

    def test_get_by_hostname_not_found(
        self, host_manager: NetworkHostManager, mock_client: MagicMock
    ) -> None:
        """Test get by hostname raises NotFoundError when not found."""
        mock_client._request.return_value = []

        with pytest.raises(NotFoundError, match="hostname.*not found"):
            host_manager.get(hostname="nonexistent")

    def test_get_by_ip_not_found(
        self, host_manager: NetworkHostManager, mock_client: MagicMock
    ) -> None:
        """Test get by IP raises NotFoundError when not found."""
        mock_client._request.return_value = []

        with pytest.raises(NotFoundError, match="IP.*not found"):
            host_manager.get(ip="10.255.255.255")

    def test_get_without_identifier_raises(self, host_manager: NetworkHostManager) -> None:
        """Test that get without any identifier raises ValueError."""
        with pytest.raises(ValueError, match="Either key, hostname, or ip"):
            host_manager.get()


class TestNetworkHostManagerCreate:
    """Tests for NetworkHostManager.create() method."""

    def test_create_host(
        self,
        host_manager: NetworkHostManager,
        mock_client: MagicMock,
        sample_host_data: dict[str, Any],
    ) -> None:
        """Test creating a host override."""
        mock_client._request.side_effect = [
            {"$key": 10},  # POST response
            sample_host_data,  # GET response
        ]

        host = host_manager.create(
            hostname="server01",
            ip="10.0.0.50",
        )

        assert host.hostname == "server01"
        # Verify POST was called with correct data
        post_call = mock_client._request.call_args_list[0]
        assert post_call[0][0] == "POST"
        body = post_call[1]["json_data"]
        assert body["host"] == "server01"
        assert body["ip"] == "10.0.0.50"
        assert body["type"] == "host"  # default
        assert body["vnet"] == 1

    def test_create_domain(
        self,
        host_manager: NetworkHostManager,
        mock_client: MagicMock,
        sample_domain_data: dict[str, Any],
    ) -> None:
        """Test creating a domain override."""
        mock_client._request.side_effect = [
            {"$key": 11},
            sample_domain_data,
        ]

        host = host_manager.create(
            hostname="mail.example.com",
            ip="10.0.0.25",
            host_type="domain",
        )

        assert host.is_domain is True
        post_call = mock_client._request.call_args_list[0]
        body = post_call[1]["json_data"]
        assert body["type"] == "domain"

    def test_create_no_response_raises(
        self, host_manager: NetworkHostManager, mock_client: MagicMock
    ) -> None:
        """Test that create with no response raises ValueError."""
        mock_client._request.return_value = None

        with pytest.raises(ValueError, match="No response"):
            host_manager.create(hostname="test", ip="10.0.0.1")

    def test_create_missing_key_raises(
        self, host_manager: NetworkHostManager, mock_client: MagicMock
    ) -> None:
        """Test that create response without $key raises ValueError."""
        mock_client._request.return_value = {}

        with pytest.raises(ValueError, match="missing.*key"):
            host_manager.create(hostname="test", ip="10.0.0.1")


class TestNetworkHostManagerUpdate:
    """Tests for NetworkHostManager.update() method."""

    def test_update_ip(
        self,
        host_manager: NetworkHostManager,
        mock_client: MagicMock,
        sample_host_data: dict[str, Any],
    ) -> None:
        """Test updating host IP."""
        updated_data = {**sample_host_data, "ip": "10.0.0.51"}
        mock_client._request.side_effect = [
            None,  # PUT response
            updated_data,  # GET response
        ]

        host = host_manager.update(10, ip="10.0.0.51")

        assert host.ip == "10.0.0.51"
        put_call = mock_client._request.call_args_list[0]
        assert put_call[0][0] == "PUT"
        assert "vnet_hosts/10" in put_call[0][1]
        assert put_call[1]["json_data"]["ip"] == "10.0.0.51"

    def test_update_hostname(
        self,
        host_manager: NetworkHostManager,
        mock_client: MagicMock,
        sample_host_data: dict[str, Any],
    ) -> None:
        """Test updating hostname."""
        updated_data = {**sample_host_data, "host": "newname"}
        mock_client._request.side_effect = [None, updated_data]

        host_manager.update(10, hostname="newname")

        put_call = mock_client._request.call_args_list[0]
        assert put_call[1]["json_data"]["host"] == "newname"

    def test_update_type(
        self,
        host_manager: NetworkHostManager,
        mock_client: MagicMock,
        sample_host_data: dict[str, Any],
    ) -> None:
        """Test updating host type."""
        updated_data = {**sample_host_data, "type": "domain"}
        mock_client._request.side_effect = [None, updated_data]

        host_manager.update(10, host_type="domain")

        put_call = mock_client._request.call_args_list[0]
        assert put_call[1]["json_data"]["type"] == "domain"

    def test_update_multiple_fields(
        self,
        host_manager: NetworkHostManager,
        mock_client: MagicMock,
        sample_host_data: dict[str, Any],
    ) -> None:
        """Test updating multiple fields at once."""
        updated_data = {**sample_host_data, "host": "newname", "ip": "10.0.0.99"}
        mock_client._request.side_effect = [None, updated_data]

        host_manager.update(10, hostname="newname", ip="10.0.0.99")

        put_call = mock_client._request.call_args_list[0]
        body = put_call[1]["json_data"]
        assert body["host"] == "newname"
        assert body["ip"] == "10.0.0.99"

    def test_update_no_fields_raises(self, host_manager: NetworkHostManager) -> None:
        """Test that update with no fields raises ValueError."""
        with pytest.raises(ValueError, match="At least one field"):
            host_manager.update(10)


class TestNetworkHostManagerDelete:
    """Tests for NetworkHostManager.delete() method."""

    def test_delete_host(self, host_manager: NetworkHostManager, mock_client: MagicMock) -> None:
        """Test deleting a host."""
        mock_client._request.return_value = None

        host_manager.delete(10)

        mock_client._request.assert_called_once()
        call_args = mock_client._request.call_args
        assert call_args[0][0] == "DELETE"
        assert "vnet_hosts/10" in call_args[0][1]


class TestNetworkHostsProperty:
    """Tests for Network.hosts property."""

    def test_hosts_property_returns_manager(
        self, mock_client: MagicMock, mock_network: Network
    ) -> None:
        """Test that Network.hosts returns a NetworkHostManager."""
        manager = mock_network.hosts

        assert isinstance(manager, NetworkHostManager)

    def test_hosts_property_has_correct_network(
        self, mock_client: MagicMock, mock_network: Network
    ) -> None:
        """Test that the manager has the correct network key."""
        manager = mock_network.hosts

        assert manager.network_key == mock_network.key
