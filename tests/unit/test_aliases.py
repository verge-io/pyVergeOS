"""Unit tests for NetworkAliasManager."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from pyvergeos import VergeClient
from pyvergeos.exceptions import NotFoundError
from pyvergeos.resources.aliases import NetworkAlias, NetworkAliasManager
from pyvergeos.resources.networks import Network, NetworkManager


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
def alias_manager(mock_client: MagicMock, mock_network: Network) -> NetworkAliasManager:
    """Create a NetworkAliasManager for testing."""
    return NetworkAliasManager(mock_client, mock_network)


@pytest.fixture
def sample_alias_data() -> dict[str, Any]:
    """Sample alias data from API."""
    return {
        "$key": 17,
        "vnet": 3,
        "vnet_name": "External",
        "ip": "10.0.0.100",
        "hostname": "webserver",
        "description": "Main web server",
        "mac": None,
        "type": "ipalias",
    }


@pytest.fixture
def sample_alias_list() -> list[dict[str, Any]]:
    """Sample list of alias data from API."""
    return [
        {
            "$key": 17,
            "vnet": 3,
            "vnet_name": "External",
            "ip": "10.0.0.100",
            "hostname": "webserver",
            "description": "Main web server",
            "mac": None,
            "type": "ipalias",
        },
        {
            "$key": 18,
            "vnet": 3,
            "vnet_name": "External",
            "ip": "10.0.0.101",
            "hostname": "dbserver",
            "description": "Database server",
            "mac": None,
            "type": "ipalias",
        },
    ]


class TestNetworkAlias:
    """Tests for NetworkAlias object."""

    def test_alias_properties(
        self, alias_manager: NetworkAliasManager, sample_alias_data: dict[str, Any]
    ) -> None:
        """Test NetworkAlias property access."""
        alias = NetworkAlias(sample_alias_data, alias_manager)

        assert alias.key == 17
        assert alias.network_key == 3
        assert alias.network_name == "External"
        assert alias.ip == "10.0.0.100"
        assert alias.hostname == "webserver"
        assert alias.alias_name == "webserver"  # Alias for hostname
        assert alias.description == "Main web server"
        assert alias.mac is None

    def test_alias_name_property(
        self, alias_manager: NetworkAliasManager, sample_alias_data: dict[str, Any]
    ) -> None:
        """Test alias_name is same as hostname."""
        alias = NetworkAlias(sample_alias_data, alias_manager)

        assert alias.alias_name == alias.hostname

    def test_alias_missing_vnet_raises(self, alias_manager: NetworkAliasManager) -> None:
        """Test ValueError when vnet is missing."""
        data: dict[str, Any] = {"$key": 1, "ip": "10.0.0.1"}
        alias = NetworkAlias(data, alias_manager)

        with pytest.raises(ValueError, match="no network"):
            _ = alias.network_key

    def test_alias_missing_ip_raises(self, alias_manager: NetworkAliasManager) -> None:
        """Test ValueError when IP is missing."""
        data: dict[str, Any] = {"$key": 1, "vnet": 3}
        alias = NetworkAlias(data, alias_manager)

        with pytest.raises(ValueError, match="no IP"):
            _ = alias.ip


class TestNetworkAliasManagerList:
    """Tests for NetworkAliasManager.list()."""

    def test_list_all_aliases(
        self,
        mock_client: MagicMock,
        alias_manager: NetworkAliasManager,
        sample_alias_list: list[dict[str, Any]],
    ) -> None:
        """Test listing all aliases."""
        mock_client._request.return_value = sample_alias_list

        aliases = alias_manager.list()

        assert len(aliases) == 2
        assert aliases[0].hostname == "webserver"
        assert aliases[1].hostname == "dbserver"
        mock_client._request.assert_called_once()
        call_args = mock_client._request.call_args
        assert call_args[0][0] == "GET"
        assert call_args[0][1] == "vnet_addresses"
        assert "vnet eq 3" in call_args[1]["params"]["filter"]
        assert "type eq 'ipalias'" in call_args[1]["params"]["filter"]

    def test_list_with_ip_filter(
        self,
        mock_client: MagicMock,
        alias_manager: NetworkAliasManager,
        sample_alias_data: dict[str, Any],
    ) -> None:
        """Test filtering by IP address."""
        mock_client._request.return_value = [sample_alias_data]

        aliases = alias_manager.list(ip="10.0.0.100")

        assert len(aliases) == 1
        call_args = mock_client._request.call_args
        assert "ip eq '10.0.0.100'" in call_args[1]["params"]["filter"]

    def test_list_with_hostname_filter(
        self,
        mock_client: MagicMock,
        alias_manager: NetworkAliasManager,
        sample_alias_data: dict[str, Any],
    ) -> None:
        """Test filtering by hostname."""
        mock_client._request.return_value = [sample_alias_data]

        aliases = alias_manager.list(hostname="webserver")

        assert len(aliases) == 1
        call_args = mock_client._request.call_args
        assert "hostname eq 'webserver'" in call_args[1]["params"]["filter"]

    def test_list_with_custom_filter(
        self,
        mock_client: MagicMock,
        alias_manager: NetworkAliasManager,
        sample_alias_data: dict[str, Any],
    ) -> None:
        """Test with additional OData filter."""
        mock_client._request.return_value = [sample_alias_data]

        alias_manager.list(filter="description ne ''")

        call_args = mock_client._request.call_args
        assert "(description ne '')" in call_args[1]["params"]["filter"]

    def test_list_empty_response(
        self, mock_client: MagicMock, alias_manager: NetworkAliasManager
    ) -> None:
        """Test handling empty response."""
        mock_client._request.return_value = None

        aliases = alias_manager.list()

        assert aliases == []

    def test_list_single_alias_response(
        self,
        mock_client: MagicMock,
        alias_manager: NetworkAliasManager,
        sample_alias_data: dict[str, Any],
    ) -> None:
        """Test handling single alias response (not in list)."""
        mock_client._request.return_value = sample_alias_data

        aliases = alias_manager.list()

        assert len(aliases) == 1
        assert aliases[0].hostname == "webserver"

    def test_list_sorted_by_ip(
        self,
        mock_client: MagicMock,
        alias_manager: NetworkAliasManager,
        sample_alias_list: list[dict[str, Any]],
    ) -> None:
        """Test that results are sorted by IP."""
        mock_client._request.return_value = sample_alias_list

        alias_manager.list()

        call_args = mock_client._request.call_args
        assert call_args[1]["params"]["sort"] == "+ip"


class TestNetworkAliasManagerGet:
    """Tests for NetworkAliasManager.get()."""

    def test_get_by_key(
        self,
        mock_client: MagicMock,
        alias_manager: NetworkAliasManager,
        sample_alias_data: dict[str, Any],
    ) -> None:
        """Test getting an alias by key."""
        mock_client._request.return_value = sample_alias_data

        alias = alias_manager.get(17)

        assert alias.key == 17
        assert alias.hostname == "webserver"
        mock_client._request.assert_called_once()
        call_args = mock_client._request.call_args
        assert call_args[0][0] == "GET"
        assert call_args[0][1] == "vnet_addresses/17"

    def test_get_by_ip(
        self,
        mock_client: MagicMock,
        alias_manager: NetworkAliasManager,
        sample_alias_data: dict[str, Any],
    ) -> None:
        """Test getting an alias by IP address."""
        mock_client._request.return_value = [sample_alias_data]

        alias = alias_manager.get(ip="10.0.0.100")

        assert alias.ip == "10.0.0.100"

    def test_get_by_hostname(
        self,
        mock_client: MagicMock,
        alias_manager: NetworkAliasManager,
        sample_alias_data: dict[str, Any],
    ) -> None:
        """Test getting an alias by hostname."""
        mock_client._request.return_value = [sample_alias_data]

        alias = alias_manager.get(hostname="webserver")

        assert alias.hostname == "webserver"

    def test_get_by_name_alias(
        self,
        mock_client: MagicMock,
        alias_manager: NetworkAliasManager,
        sample_alias_data: dict[str, Any],
    ) -> None:
        """Test that name is an alias for hostname."""
        mock_client._request.return_value = [sample_alias_data]

        alias = alias_manager.get(name="webserver")

        assert alias.hostname == "webserver"

    def test_get_by_key_not_found(
        self, mock_client: MagicMock, alias_manager: NetworkAliasManager
    ) -> None:
        """Test NotFoundError when alias key doesn't exist."""
        mock_client._request.return_value = None

        with pytest.raises(NotFoundError, match="not found"):
            alias_manager.get(999)

    def test_get_by_ip_not_found(
        self, mock_client: MagicMock, alias_manager: NetworkAliasManager
    ) -> None:
        """Test NotFoundError when IP doesn't exist."""
        mock_client._request.return_value = []

        with pytest.raises(NotFoundError, match="IP .* not found"):
            alias_manager.get(ip="10.10.10.10")

    def test_get_by_hostname_not_found(
        self, mock_client: MagicMock, alias_manager: NetworkAliasManager
    ) -> None:
        """Test NotFoundError when hostname doesn't exist."""
        mock_client._request.return_value = []

        with pytest.raises(NotFoundError, match="hostname .* not found"):
            alias_manager.get(hostname="nonexistent")

    def test_get_requires_identifier(self, alias_manager: NetworkAliasManager) -> None:
        """Test that get requires some identifier."""
        with pytest.raises(ValueError, match="Either key, ip, or hostname must be provided"):
            alias_manager.get()


class TestNetworkAliasManagerCreate:
    """Tests for NetworkAliasManager.create()."""

    def test_create_basic_alias(
        self, mock_client: MagicMock, alias_manager: NetworkAliasManager
    ) -> None:
        """Test creating a basic alias."""
        mock_client._request.side_effect = [
            {"$key": 20},  # POST response
            {  # GET response for fetching created alias
                "$key": 20,
                "vnet": 3,
                "vnet_name": "External",
                "ip": "10.0.0.200",
                "hostname": "newserver",
                "description": "New server",
                "type": "ipalias",
            },
        ]

        alias = alias_manager.create(
            ip="10.0.0.200",
            name="newserver",
            description="New server",
        )

        assert alias.key == 20
        assert alias.ip == "10.0.0.200"
        assert alias.hostname == "newserver"

        # Verify POST was called with correct data
        create_call = mock_client._request.call_args_list[0]
        assert create_call[0][0] == "POST"
        assert create_call[0][1] == "vnet_addresses"
        body = create_call[1]["json_data"]
        assert body["vnet"] == 3
        assert body["ip"] == "10.0.0.200"
        assert body["hostname"] == "newserver"
        assert body["type"] == "ipalias"
        assert body["description"] == "New server"

    def test_create_alias_without_description(
        self, mock_client: MagicMock, alias_manager: NetworkAliasManager
    ) -> None:
        """Test creating an alias without description."""
        mock_client._request.side_effect = [
            {"$key": 21},
            {
                "$key": 21,
                "vnet": 3,
                "ip": "10.0.0.201",
                "hostname": "simpleserver",
                "type": "ipalias",
            },
        ]

        alias = alias_manager.create(ip="10.0.0.201", name="simpleserver")

        assert alias.key == 21

        # Verify description not in body
        create_call = mock_client._request.call_args_list[0]
        body = create_call[1]["json_data"]
        assert "description" not in body

    def test_create_no_response_raises(
        self, mock_client: MagicMock, alias_manager: NetworkAliasManager
    ) -> None:
        """Test that no response raises ValueError."""
        mock_client._request.return_value = None

        with pytest.raises(ValueError, match="No response from create"):
            alias_manager.create(ip="10.0.0.1", name="test")

    def test_create_missing_key_raises(
        self, mock_client: MagicMock, alias_manager: NetworkAliasManager
    ) -> None:
        """Test that missing $key raises ValueError."""
        mock_client._request.return_value = {"status": "ok"}

        with pytest.raises(ValueError, match="missing \\$key"):
            alias_manager.create(ip="10.0.0.1", name="test")


class TestNetworkAliasManagerDelete:
    """Tests for NetworkAliasManager.delete()."""

    def test_delete_alias(
        self,
        mock_client: MagicMock,
        alias_manager: NetworkAliasManager,
    ) -> None:
        """Test deleting an alias."""
        mock_client._request.return_value = None

        alias_manager.delete(17)

        mock_client._request.assert_called_once()
        call_args = mock_client._request.call_args
        assert call_args[0][0] == "DELETE"
        assert call_args[0][1] == "vnet_addresses/17"


class TestNetworkAliasesProperty:
    """Tests for Network.aliases property."""

    def test_network_aliases_property(self, mock_network: Network) -> None:
        """Test accessing aliases through network object."""
        aliases = mock_network.aliases

        assert isinstance(aliases, NetworkAliasManager)
        assert aliases.network_key == 3
