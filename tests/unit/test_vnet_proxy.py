"""Unit tests for network proxy managers (VnetProxy, VnetProxyTenant)."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from pyvergeos.exceptions import NotFoundError
from pyvergeos.resources.networks import Network
from pyvergeos.resources.vnet_proxy import (
    VnetProxy,
    VnetProxyManager,
    VnetProxyTenant,
    VnetProxyTenantManager,
)


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
        "$key": 5,
        "name": "External",
        "type": "external",
        "proxy_enabled": True,
        "need_proxy_apply": False,
    }
    manager = MagicMock()
    manager._client = mock_client
    return Network(network_data, manager)


@pytest.fixture
def proxy_manager(mock_client: MagicMock, mock_network: Network) -> VnetProxyManager:
    """Create a VnetProxyManager with mock dependencies."""
    return VnetProxyManager(mock_client, mock_network)


# =============================================================================
# Sample Data Fixtures
# =============================================================================


@pytest.fixture
def sample_proxy_data() -> dict[str, Any]:
    """Sample proxy configuration data from API."""
    return {
        "$key": 1,
        "vnet": 5,
        "vnet_display": "External",
        "name": "External",
        "listen_address": "0.0.0.0",
        "default_self": True,
        "modified": 1704067200,
    }


@pytest.fixture
def sample_proxy_tenant_data() -> dict[str, Any]:
    """Sample proxy tenant mapping data from API."""
    return {
        "$key": 1,
        "proxy": 1,
        "tenant": 10,
        "tenant_display": "Customer-A",
        "fqdn": "customer-a.example.com",
        "modified": 1704067200,
    }


@pytest.fixture
def sample_proxy_tenant_list() -> list[dict[str, Any]]:
    """Sample list of proxy tenant mappings."""
    return [
        {
            "$key": 1,
            "proxy": 1,
            "tenant": 10,
            "tenant_display": "Customer-A",
            "fqdn": "customer-a.example.com",
            "modified": 1704067200,
        },
        {
            "$key": 2,
            "proxy": 1,
            "tenant": 11,
            "tenant_display": "Customer-B",
            "fqdn": "customer-b.example.com",
            "modified": 1704067200,
        },
    ]


# =============================================================================
# VnetProxy Model Tests
# =============================================================================


class TestVnetProxy:
    """Tests for VnetProxy model."""

    def test_proxy_properties(self, sample_proxy_data: dict[str, Any]) -> None:
        """Test proxy properties."""
        manager = MagicMock()
        proxy = VnetProxy(sample_proxy_data, manager)

        assert proxy.key == 1
        assert proxy.network_key == 5
        assert proxy.network_name == "External"
        assert proxy.listen_address == "0.0.0.0"
        assert proxy.default_self is True

    def test_proxy_default_listen_address(self) -> None:
        """Test default listen address when not set."""
        manager = MagicMock()
        proxy = VnetProxy({"$key": 1, "vnet": 5}, manager)

        assert proxy.listen_address == "0.0.0.0"

    def test_proxy_tenants_property(
        self,
        mock_client: MagicMock,
        sample_proxy_data: dict[str, Any],
    ) -> None:
        """Test accessing tenants manager from proxy."""
        manager = MagicMock()
        manager._client = mock_client
        proxy = VnetProxy(sample_proxy_data, manager)

        tenants_manager = proxy.tenants
        assert isinstance(tenants_manager, VnetProxyTenantManager)

    def test_proxy_refresh(
        self,
        mock_client: MagicMock,
        sample_proxy_data: dict[str, Any],
    ) -> None:
        """Test proxy refresh."""
        manager = MagicMock(spec=VnetProxyManager)
        manager.get.return_value = VnetProxy(sample_proxy_data, manager)
        proxy = VnetProxy(sample_proxy_data, manager)

        refreshed = proxy.refresh()
        manager.get.assert_called_once_with(1)
        assert refreshed.key == 1

    def test_proxy_save(
        self,
        mock_client: MagicMock,
        sample_proxy_data: dict[str, Any],
    ) -> None:
        """Test proxy save."""
        manager = MagicMock(spec=VnetProxyManager)
        updated_data = {**sample_proxy_data, "listen_address": "192.168.1.1"}
        manager.update.return_value = VnetProxy(updated_data, manager)
        proxy = VnetProxy(sample_proxy_data, manager)

        updated = proxy.save(listen_address="192.168.1.1")
        manager.update.assert_called_once_with(1, listen_address="192.168.1.1")
        assert updated.listen_address == "192.168.1.1"

    def test_proxy_delete(
        self,
        mock_client: MagicMock,
        sample_proxy_data: dict[str, Any],
    ) -> None:
        """Test proxy delete."""
        manager = MagicMock(spec=VnetProxyManager)
        proxy = VnetProxy(sample_proxy_data, manager)

        proxy.delete()
        manager.delete.assert_called_once_with(1)


# =============================================================================
# VnetProxyTenant Model Tests
# =============================================================================


class TestVnetProxyTenant:
    """Tests for VnetProxyTenant model."""

    def test_tenant_properties(
        self,
        sample_proxy_tenant_data: dict[str, Any],
    ) -> None:
        """Test tenant mapping properties."""
        manager = MagicMock()
        tenant = VnetProxyTenant(sample_proxy_tenant_data, manager)

        assert tenant.key == 1
        assert tenant.tenant_key == 10
        assert tenant.tenant_name == "Customer-A"
        assert tenant.fqdn == "customer-a.example.com"
        assert tenant.proxy_key == 1

    def test_tenant_refresh(
        self,
        sample_proxy_tenant_data: dict[str, Any],
    ) -> None:
        """Test tenant mapping refresh."""
        manager = MagicMock(spec=VnetProxyTenantManager)
        manager.get.return_value = VnetProxyTenant(sample_proxy_tenant_data, manager)
        tenant = VnetProxyTenant(sample_proxy_tenant_data, manager)

        refreshed = tenant.refresh()
        manager.get.assert_called_once_with(1)
        assert refreshed.key == 1

    def test_tenant_save(
        self,
        sample_proxy_tenant_data: dict[str, Any],
    ) -> None:
        """Test tenant mapping save."""
        manager = MagicMock(spec=VnetProxyTenantManager)
        updated_data = {**sample_proxy_tenant_data, "fqdn": "new-fqdn.example.com"}
        manager.update.return_value = VnetProxyTenant(updated_data, manager)
        tenant = VnetProxyTenant(sample_proxy_tenant_data, manager)

        updated = tenant.save(fqdn="new-fqdn.example.com")
        manager.update.assert_called_once_with(1, fqdn="new-fqdn.example.com")
        assert updated.fqdn == "new-fqdn.example.com"

    def test_tenant_delete(
        self,
        sample_proxy_tenant_data: dict[str, Any],
    ) -> None:
        """Test tenant mapping delete."""
        manager = MagicMock(spec=VnetProxyTenantManager)
        tenant = VnetProxyTenant(sample_proxy_tenant_data, manager)

        tenant.delete()
        manager.delete.assert_called_once_with(1)


# =============================================================================
# VnetProxyManager Tests
# =============================================================================


class TestVnetProxyManager:
    """Tests for VnetProxyManager."""

    def test_manager_initialization(
        self,
        mock_client: MagicMock,
        mock_network: Network,
    ) -> None:
        """Test manager initialization."""
        manager = VnetProxyManager(mock_client, mock_network)
        assert manager._client is mock_client
        assert manager._network is mock_network
        assert manager._endpoint == "vnet_proxy"

    def test_exists_true(
        self,
        proxy_manager: VnetProxyManager,
        sample_proxy_data: dict[str, Any],
    ) -> None:
        """Test exists returns True when proxy is configured."""
        proxy_manager._client._request.return_value = [sample_proxy_data]

        assert proxy_manager.exists() is True

    def test_exists_false(
        self,
        proxy_manager: VnetProxyManager,
    ) -> None:
        """Test exists returns False when proxy is not configured."""
        proxy_manager._client._request.return_value = []

        assert proxy_manager.exists() is False

    def test_get_proxy(
        self,
        proxy_manager: VnetProxyManager,
        sample_proxy_data: dict[str, Any],
    ) -> None:
        """Test getting proxy configuration."""
        proxy_manager._client._request.return_value = [sample_proxy_data]

        proxy = proxy_manager.get()

        assert proxy.key == 1
        assert proxy.listen_address == "0.0.0.0"
        assert proxy.default_self is True

    def test_get_proxy_by_key(
        self,
        proxy_manager: VnetProxyManager,
        sample_proxy_data: dict[str, Any],
    ) -> None:
        """Test getting proxy by key."""
        proxy_manager._client._request.return_value = [sample_proxy_data]

        proxy = proxy_manager.get(key=1)

        assert proxy.key == 1
        # Verify filter includes both key and network
        call_args = proxy_manager._client._request.call_args
        assert "$key eq 1" in call_args[1]["params"]["filter"]
        assert "vnet eq 5" in call_args[1]["params"]["filter"]

    def test_get_proxy_not_found(
        self,
        proxy_manager: VnetProxyManager,
    ) -> None:
        """Test getting proxy raises NotFoundError when not configured."""
        proxy_manager._client._request.return_value = []

        with pytest.raises(NotFoundError, match="Proxy not configured"):
            proxy_manager.get()

    def test_create_proxy(
        self,
        proxy_manager: VnetProxyManager,
        sample_proxy_data: dict[str, Any],
    ) -> None:
        """Test creating proxy configuration."""
        # First call for exists() check, second for create, third for get
        proxy_manager._client._request.side_effect = [
            [],  # exists() check
            {"$key": 1},  # create response
            [sample_proxy_data],  # get after create
        ]

        proxy = proxy_manager.create(
            listen_address="0.0.0.0",
            default_self=True,
        )

        assert proxy.key == 1
        # Verify create was called with correct data
        create_call = proxy_manager._client._request.call_args_list[1]
        assert create_call[0][0] == "POST"
        assert create_call[1]["json_data"]["vnet"] == 5
        assert create_call[1]["json_data"]["listen_address"] == "0.0.0.0"

    def test_create_proxy_already_exists(
        self,
        proxy_manager: VnetProxyManager,
        sample_proxy_data: dict[str, Any],
    ) -> None:
        """Test creating proxy when already exists raises error."""
        proxy_manager._client._request.return_value = [sample_proxy_data]

        with pytest.raises(ValueError, match="Proxy already configured"):
            proxy_manager.create()

    def test_update_proxy(
        self,
        proxy_manager: VnetProxyManager,
        sample_proxy_data: dict[str, Any],
    ) -> None:
        """Test updating proxy configuration."""
        updated_data = {**sample_proxy_data, "listen_address": "192.168.1.1"}
        proxy_manager._client._request.side_effect = [
            [sample_proxy_data],  # get for verification
            None,  # PUT response
            [updated_data],  # get after update
        ]

        proxy = proxy_manager.update(1, listen_address="192.168.1.1")

        assert proxy.listen_address == "192.168.1.1"
        # Verify PUT was called
        put_call = proxy_manager._client._request.call_args_list[1]
        assert put_call[0][0] == "PUT"
        assert put_call[0][1] == "vnet_proxy/1"

    def test_delete_proxy(
        self,
        proxy_manager: VnetProxyManager,
        sample_proxy_data: dict[str, Any],
    ) -> None:
        """Test deleting proxy configuration."""
        proxy_manager._client._request.side_effect = [
            [sample_proxy_data],  # get for verification
            None,  # DELETE response
        ]

        proxy_manager.delete(1)

        # Verify DELETE was called
        delete_call = proxy_manager._client._request.call_args_list[1]
        assert delete_call[0][0] == "DELETE"
        assert delete_call[0][1] == "vnet_proxy/1"

    def test_delete_proxy_auto_key(
        self,
        proxy_manager: VnetProxyManager,
        sample_proxy_data: dict[str, Any],
    ) -> None:
        """Test deleting proxy without specifying key."""
        proxy_manager._client._request.side_effect = [
            [sample_proxy_data],  # get() to find key
            [sample_proxy_data],  # get for verification
            None,  # DELETE response
        ]

        proxy_manager.delete()

        # Verify DELETE was called with the found key
        delete_call = proxy_manager._client._request.call_args_list[2]
        assert delete_call[0][0] == "DELETE"
        assert delete_call[0][1] == "vnet_proxy/1"

    def test_get_or_create_exists(
        self,
        proxy_manager: VnetProxyManager,
        sample_proxy_data: dict[str, Any],
    ) -> None:
        """Test get_or_create returns existing proxy."""
        proxy_manager._client._request.return_value = [sample_proxy_data]

        proxy = proxy_manager.get_or_create()

        assert proxy.key == 1
        # Should only call get, not create
        assert proxy_manager._client._request.call_count == 1

    def test_get_or_create_creates(
        self,
        proxy_manager: VnetProxyManager,
        sample_proxy_data: dict[str, Any],
    ) -> None:
        """Test get_or_create creates when not exists."""
        proxy_manager._client._request.side_effect = [
            [],  # get() - not found
            [],  # exists() check in create
            {"$key": 1},  # create response
            [sample_proxy_data],  # get after create
        ]

        proxy = proxy_manager.get_or_create(listen_address="192.168.1.1")

        assert proxy.key == 1


# =============================================================================
# VnetProxyTenantManager Tests
# =============================================================================


class TestVnetProxyTenantManager:
    """Tests for VnetProxyTenantManager."""

    @pytest.fixture
    def mock_proxy(
        self,
        mock_client: MagicMock,
        sample_proxy_data: dict[str, Any],
    ) -> VnetProxy:
        """Create a mock VnetProxy object."""
        manager = MagicMock()
        manager._client = mock_client
        return VnetProxy(sample_proxy_data, manager)

    @pytest.fixture
    def tenant_manager(
        self,
        mock_client: MagicMock,
        mock_proxy: VnetProxy,
    ) -> VnetProxyTenantManager:
        """Create a VnetProxyTenantManager with mock dependencies."""
        return VnetProxyTenantManager(mock_client, mock_proxy)

    def test_manager_initialization(
        self,
        mock_client: MagicMock,
        mock_proxy: VnetProxy,
    ) -> None:
        """Test manager initialization."""
        manager = VnetProxyTenantManager(mock_client, mock_proxy)
        assert manager._client is mock_client
        assert manager._proxy is mock_proxy
        assert manager._endpoint == "vnet_proxy_tenants"

    def test_list_tenants(
        self,
        tenant_manager: VnetProxyTenantManager,
        sample_proxy_tenant_list: list[dict[str, Any]],
    ) -> None:
        """Test listing tenant mappings."""
        tenant_manager._client._request.return_value = sample_proxy_tenant_list

        tenants = tenant_manager.list()

        assert len(tenants) == 2
        assert tenants[0].fqdn == "customer-a.example.com"
        assert tenants[1].fqdn == "customer-b.example.com"
        # Verify filter is scoped to proxy
        call_args = tenant_manager._client._request.call_args
        assert "proxy eq 1" in call_args[1]["params"]["filter"]

    def test_list_tenants_with_filter(
        self,
        tenant_manager: VnetProxyTenantManager,
        sample_proxy_tenant_data: dict[str, Any],
    ) -> None:
        """Test listing tenant mappings with custom filter."""
        tenant_manager._client._request.return_value = [sample_proxy_tenant_data]

        tenants = tenant_manager.list(filter="tenant eq 10")

        assert len(tenants) == 1
        # Verify custom filter is combined with proxy scope
        call_args = tenant_manager._client._request.call_args
        assert "(tenant eq 10) and proxy eq 1" in call_args[1]["params"]["filter"]

    def test_get_tenant_by_key(
        self,
        tenant_manager: VnetProxyTenantManager,
        sample_proxy_tenant_data: dict[str, Any],
    ) -> None:
        """Test getting tenant mapping by key."""
        tenant_manager._client._request.return_value = [sample_proxy_tenant_data]

        tenant = tenant_manager.get(key=1)

        assert tenant.key == 1
        assert tenant.fqdn == "customer-a.example.com"

    def test_get_tenant_by_fqdn(
        self,
        tenant_manager: VnetProxyTenantManager,
        sample_proxy_tenant_data: dict[str, Any],
    ) -> None:
        """Test getting tenant mapping by FQDN."""
        tenant_manager._client._request.return_value = [sample_proxy_tenant_data]

        tenant = tenant_manager.get(fqdn="customer-a.example.com")

        assert tenant.fqdn == "customer-a.example.com"
        # Verify filter includes FQDN
        call_args = tenant_manager._client._request.call_args
        assert "fqdn eq 'customer-a.example.com'" in call_args[1]["params"]["filter"]

    def test_get_tenant_by_tenant_key(
        self,
        tenant_manager: VnetProxyTenantManager,
        sample_proxy_tenant_data: dict[str, Any],
    ) -> None:
        """Test getting tenant mapping by tenant key."""
        tenant_manager._client._request.return_value = [sample_proxy_tenant_data]

        tenant = tenant_manager.get(tenant=10)

        assert tenant.tenant_key == 10
        # Verify filter includes tenant key
        call_args = tenant_manager._client._request.call_args
        assert "tenant eq 10" in call_args[1]["params"]["filter"]

    def test_get_tenant_no_params(
        self,
        tenant_manager: VnetProxyTenantManager,
    ) -> None:
        """Test getting tenant without params raises error."""
        with pytest.raises(ValueError, match="Must provide key, fqdn, or tenant"):
            tenant_manager.get()

    def test_get_tenant_not_found(
        self,
        tenant_manager: VnetProxyTenantManager,
    ) -> None:
        """Test getting non-existent tenant raises NotFoundError."""
        tenant_manager._client._request.return_value = []

        with pytest.raises(NotFoundError, match="not found"):
            tenant_manager.get(key=999)

    def test_create_tenant(
        self,
        tenant_manager: VnetProxyTenantManager,
        sample_proxy_tenant_data: dict[str, Any],
    ) -> None:
        """Test creating tenant mapping."""
        tenant_manager._client._request.side_effect = [
            {"$key": 1},  # create response
            [sample_proxy_tenant_data],  # get after create
        ]

        tenant = tenant_manager.create(
            tenant=10,
            fqdn="customer-a.example.com",
        )

        assert tenant.key == 1
        assert tenant.fqdn == "customer-a.example.com"
        # Verify create was called with correct data
        create_call = tenant_manager._client._request.call_args_list[0]
        assert create_call[0][0] == "POST"
        assert create_call[1]["json_data"]["proxy"] == 1
        assert create_call[1]["json_data"]["tenant"] == 10
        assert create_call[1]["json_data"]["fqdn"] == "customer-a.example.com"

    def test_update_tenant(
        self,
        tenant_manager: VnetProxyTenantManager,
        sample_proxy_tenant_data: dict[str, Any],
    ) -> None:
        """Test updating tenant mapping."""
        updated_data = {**sample_proxy_tenant_data, "fqdn": "new-fqdn.example.com"}
        tenant_manager._client._request.side_effect = [
            [sample_proxy_tenant_data],  # get for verification
            None,  # PUT response
            [updated_data],  # get after update
        ]

        tenant = tenant_manager.update(1, fqdn="new-fqdn.example.com")

        assert tenant.fqdn == "new-fqdn.example.com"
        # Verify PUT was called
        put_call = tenant_manager._client._request.call_args_list[1]
        assert put_call[0][0] == "PUT"
        assert put_call[0][1] == "vnet_proxy_tenants/1"

    def test_delete_tenant(
        self,
        tenant_manager: VnetProxyTenantManager,
        sample_proxy_tenant_data: dict[str, Any],
    ) -> None:
        """Test deleting tenant mapping."""
        tenant_manager._client._request.side_effect = [
            [sample_proxy_tenant_data],  # get for verification
            None,  # DELETE response
        ]

        tenant_manager.delete(1)

        # Verify DELETE was called
        delete_call = tenant_manager._client._request.call_args_list[1]
        assert delete_call[0][0] == "DELETE"
        assert delete_call[0][1] == "vnet_proxy_tenants/1"


# =============================================================================
# Network Integration Tests
# =============================================================================


class TestNetworkProxyIntegration:
    """Tests for Network.proxy property integration."""

    def test_network_proxy_property(
        self,
        mock_client: MagicMock,
        mock_network: Network,
    ) -> None:
        """Test accessing proxy manager from network."""
        proxy_manager = mock_network.proxy
        assert isinstance(proxy_manager, VnetProxyManager)
        assert proxy_manager._network is mock_network

    def test_network_needs_proxy_apply(self) -> None:
        """Test needs_proxy_apply property."""
        manager = MagicMock()
        network = Network(
            {"$key": 1, "name": "External", "need_proxy_apply": True},
            manager,
        )
        assert network.needs_proxy_apply is True

        network2 = Network(
            {"$key": 2, "name": "Internal", "need_proxy_apply": False},
            manager,
        )
        assert network2.needs_proxy_apply is False

    def test_network_proxy_enabled(self) -> None:
        """Test proxy_enabled property."""
        manager = MagicMock()
        network = Network(
            {"$key": 1, "name": "External", "proxy_enabled": True},
            manager,
        )
        assert network.proxy_enabled is True

        network2 = Network(
            {"$key": 2, "name": "Internal", "proxy_enabled": False},
            manager,
        )
        assert network2.proxy_enabled is False

    def test_network_proxy_enabled_default(self) -> None:
        """Test proxy_enabled defaults to False."""
        manager = MagicMock()
        network = Network({"$key": 1, "name": "Internal"}, manager)
        assert network.proxy_enabled is False


# =============================================================================
# Edge Cases and Error Handling
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_proxy_with_empty_listen_address(
        self,
        mock_client: MagicMock,
    ) -> None:
        """Test proxy with empty listen address defaults correctly."""
        manager = MagicMock()
        proxy = VnetProxy({"$key": 1, "vnet": 5, "listen_address": ""}, manager)
        # Empty string should be returned as-is, not defaulted
        assert proxy.listen_address == ""

    def test_proxy_tenant_empty_display(self) -> None:
        """Test tenant with missing display fields."""
        manager = MagicMock()
        tenant = VnetProxyTenant(
            {"$key": 1, "proxy": 1, "tenant": 10, "fqdn": "test.example.com"},
            manager,
        )
        assert tenant.tenant_name == ""  # Missing tenant_display
        assert tenant.fqdn == "test.example.com"

    def test_create_with_none_response(
        self,
        proxy_manager: VnetProxyManager,
    ) -> None:
        """Test create handles None response."""
        proxy_manager._client._request.side_effect = [
            [],  # exists() check
            None,  # create response
        ]

        with pytest.raises(ValueError, match="No response from create"):
            proxy_manager.create()

    def test_create_with_invalid_response(
        self,
        proxy_manager: VnetProxyManager,
    ) -> None:
        """Test create handles invalid response type."""
        proxy_manager._client._request.side_effect = [
            [],  # exists() check
            "invalid",  # create response
        ]

        with pytest.raises(ValueError, match="invalid response"):
            proxy_manager.create()

    def test_create_with_missing_key(
        self,
        proxy_manager: VnetProxyManager,
    ) -> None:
        """Test create handles response missing $key."""
        proxy_manager._client._request.side_effect = [
            [],  # exists() check
            {"status": "ok"},  # create response without $key
        ]

        with pytest.raises(ValueError, match="missing \\$key"):
            proxy_manager.create()
