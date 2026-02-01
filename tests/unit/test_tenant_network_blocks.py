"""Unit tests for TenantNetworkBlock operations."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from pyvergeos.exceptions import NotFoundError
from pyvergeos.resources.tenant_network_blocks import (
    TenantNetworkBlock,
    TenantNetworkBlockManager,
)


@pytest.fixture
def mock_client() -> MagicMock:
    """Create a mock VergeClient."""
    client = MagicMock()
    client._request = MagicMock()
    return client


@pytest.fixture
def mock_tenant() -> MagicMock:
    """Create a mock Tenant object."""
    tenant = MagicMock()
    tenant.key = 123
    tenant.name = "test-tenant"
    tenant.is_snapshot = False
    return tenant


@pytest.fixture
def sample_network_block_data() -> dict[str, Any]:
    """Sample tenant network block data from API."""
    return {
        "$key": 1,
        "vnet": 10,
        "network_name": "Internal",
        "cidr": "192.168.100.0/24",
        "description": "Test network block",
        "owner": "tenants/123",
    }


@pytest.fixture
def sample_network_block_list() -> list[dict[str, Any]]:
    """Sample list of tenant network blocks."""
    return [
        {
            "$key": 1,
            "vnet": 10,
            "network_name": "Internal",
            "cidr": "192.168.100.0/24",
            "description": "Block 1",
            "owner": "tenants/123",
        },
        {
            "$key": 2,
            "vnet": 10,
            "network_name": "Internal",
            "cidr": "192.168.101.0/24",
            "description": "Block 2",
            "owner": "tenants/123",
        },
    ]


# =============================================================================
# TenantNetworkBlock Model Tests
# =============================================================================


class TestTenantNetworkBlock:
    """Tests for TenantNetworkBlock model."""

    def test_block_properties(self, sample_network_block_data: dict[str, Any]) -> None:
        """Test network block properties."""
        manager = MagicMock()
        block = TenantNetworkBlock(sample_network_block_data, manager)

        assert block.key == 1
        assert block.network_key == 10
        assert block.network_name == "Internal"
        assert block.cidr == "192.168.100.0/24"
        assert block.description == "Test network block"

    def test_block_tenant_key_parsing(self, sample_network_block_data: dict[str, Any]) -> None:
        """Test tenant key parsing from owner field."""
        manager = MagicMock()
        block = TenantNetworkBlock(sample_network_block_data, manager)

        assert block.tenant_key == 123

    def test_block_tenant_key_empty_owner(self) -> None:
        """Test tenant key when owner is empty."""
        manager = MagicMock()
        block = TenantNetworkBlock({"$key": 1, "owner": ""}, manager)

        assert block.tenant_key == 0

    def test_block_tenant_key_invalid_owner(self) -> None:
        """Test tenant key when owner is invalid format."""
        manager = MagicMock()
        block = TenantNetworkBlock({"$key": 1, "owner": "invalid"}, manager)

        assert block.tenant_key == 0

    def test_block_network_address(self, sample_network_block_data: dict[str, Any]) -> None:
        """Test network address extraction from CIDR."""
        manager = MagicMock()
        block = TenantNetworkBlock(sample_network_block_data, manager)

        assert block.network_address == "192.168.100.0"

    def test_block_network_address_no_slash(self) -> None:
        """Test network address when CIDR has no slash."""
        manager = MagicMock()
        block = TenantNetworkBlock({"$key": 1, "cidr": "192.168.1.0"}, manager)

        assert block.network_address == "192.168.1.0"

    def test_block_prefix_length(self, sample_network_block_data: dict[str, Any]) -> None:
        """Test prefix length extraction from CIDR."""
        manager = MagicMock()
        block = TenantNetworkBlock(sample_network_block_data, manager)

        assert block.prefix_length == 24

    def test_block_prefix_length_no_slash(self) -> None:
        """Test prefix length when CIDR has no slash."""
        manager = MagicMock()
        block = TenantNetworkBlock({"$key": 1, "cidr": "192.168.1.0"}, manager)

        assert block.prefix_length == 0

    def test_block_address_count(self, sample_network_block_data: dict[str, Any]) -> None:
        """Test address count calculation."""
        manager = MagicMock()
        block = TenantNetworkBlock(sample_network_block_data, manager)

        # /24 = 256 addresses
        assert block.address_count == 256

    def test_block_address_count_various_prefixes(self) -> None:
        """Test address count for various prefix lengths."""
        manager = MagicMock()

        # /30 = 4 addresses
        block30 = TenantNetworkBlock({"$key": 1, "cidr": "10.0.0.0/30"}, manager)
        assert block30.address_count == 4

        # /16 = 65536 addresses
        block16 = TenantNetworkBlock({"$key": 2, "cidr": "10.0.0.0/16"}, manager)
        assert block16.address_count == 65536

        # /32 = 1 address
        block32 = TenantNetworkBlock({"$key": 3, "cidr": "10.0.0.1/32"}, manager)
        assert block32.address_count == 1

    def test_block_address_count_zero_prefix(self) -> None:
        """Test address count when prefix is 0."""
        manager = MagicMock()
        block = TenantNetworkBlock({"$key": 1, "cidr": "192.168.1.0"}, manager)

        assert block.address_count == 0

    def test_block_description_none(self) -> None:
        """Test description when not set."""
        manager = MagicMock()
        block = TenantNetworkBlock({"$key": 1, "cidr": "10.0.0.0/24"}, manager)

        assert block.description is None

    def test_block_network_name_none(self) -> None:
        """Test network name when not set."""
        manager = MagicMock()
        block = TenantNetworkBlock({"$key": 1, "cidr": "10.0.0.0/24"}, manager)

        assert block.network_name is None

    def test_block_delete(self, sample_network_block_data: dict[str, Any]) -> None:
        """Test delete method calls manager."""
        manager = MagicMock()
        block = TenantNetworkBlock(sample_network_block_data, manager)

        block.delete()

        manager.delete.assert_called_once_with(1)

    def test_block_repr(self, sample_network_block_data: dict[str, Any]) -> None:
        """Test network block repr."""
        manager = MagicMock()
        block = TenantNetworkBlock(sample_network_block_data, manager)

        repr_str = repr(block)
        assert "TenantNetworkBlock" in repr_str
        assert "192.168.100.0/24" in repr_str
        assert "Internal" in repr_str


# =============================================================================
# TenantNetworkBlockManager Tests
# =============================================================================


class TestTenantNetworkBlockManager:
    """Tests for TenantNetworkBlockManager."""

    def test_list_network_blocks(
        self,
        mock_client: MagicMock,
        mock_tenant: MagicMock,
        sample_network_block_list: list[dict[str, Any]],
    ) -> None:
        """Test listing network blocks."""
        mock_client._request.return_value = sample_network_block_list
        manager = TenantNetworkBlockManager(mock_client, mock_tenant)

        blocks = manager.list()

        assert len(blocks) == 2
        assert blocks[0].cidr == "192.168.100.0/24"
        assert blocks[1].cidr == "192.168.101.0/24"
        mock_client._request.assert_called_once()

    def test_list_filters_by_tenant_owner(
        self,
        mock_client: MagicMock,
        mock_tenant: MagicMock,
    ) -> None:
        """Test that list filters by tenant owner."""
        mock_client._request.return_value = []
        manager = TenantNetworkBlockManager(mock_client, mock_tenant)

        manager.list()

        call_args = mock_client._request.call_args
        params = call_args[1]["params"]
        assert "owner eq 'tenants/123'" in params["filter"]

    def test_list_with_cidr_filter(
        self,
        mock_client: MagicMock,
        mock_tenant: MagicMock,
        sample_network_block_data: dict[str, Any],
    ) -> None:
        """Test listing with CIDR filter."""
        mock_client._request.return_value = [sample_network_block_data]
        manager = TenantNetworkBlockManager(mock_client, mock_tenant)

        _ = manager.list(cidr="192.168.100.0/24")

        call_args = mock_client._request.call_args
        params = call_args[1]["params"]
        assert "cidr eq '192.168.100.0/24'" in params["filter"]

    def test_list_with_additional_filter(
        self,
        mock_client: MagicMock,
        mock_tenant: MagicMock,
    ) -> None:
        """Test listing with additional filter."""
        mock_client._request.return_value = []
        manager = TenantNetworkBlockManager(mock_client, mock_tenant)

        manager.list(filter="vnet eq 10")

        call_args = mock_client._request.call_args
        params = call_args[1]["params"]
        assert "vnet eq 10" in params["filter"]

    def test_list_empty_response(
        self,
        mock_client: MagicMock,
        mock_tenant: MagicMock,
    ) -> None:
        """Test list with None response."""
        mock_client._request.return_value = None
        manager = TenantNetworkBlockManager(mock_client, mock_tenant)

        blocks = manager.list()

        assert blocks == []

    def test_list_single_response(
        self,
        mock_client: MagicMock,
        mock_tenant: MagicMock,
        sample_network_block_data: dict[str, Any],
    ) -> None:
        """Test list when API returns single item (not list)."""
        mock_client._request.return_value = sample_network_block_data
        manager = TenantNetworkBlockManager(mock_client, mock_tenant)

        blocks = manager.list()

        assert len(blocks) == 1
        assert blocks[0].cidr == "192.168.100.0/24"

    def test_get_by_key(
        self,
        mock_client: MagicMock,
        mock_tenant: MagicMock,
        sample_network_block_data: dict[str, Any],
    ) -> None:
        """Test getting a network block by key."""
        mock_client._request.return_value = sample_network_block_data
        manager = TenantNetworkBlockManager(mock_client, mock_tenant)

        block = manager.get(1)

        assert block.key == 1
        assert block.cidr == "192.168.100.0/24"
        mock_client._request.assert_called_once()
        call_args = mock_client._request.call_args
        assert call_args[0][1] == "vnet_cidrs/1"

    def test_get_by_cidr(
        self,
        mock_client: MagicMock,
        mock_tenant: MagicMock,
        sample_network_block_data: dict[str, Any],
    ) -> None:
        """Test getting a network block by CIDR."""
        mock_client._request.return_value = [sample_network_block_data]
        manager = TenantNetworkBlockManager(mock_client, mock_tenant)

        block = manager.get(cidr="192.168.100.0/24")

        assert block.cidr == "192.168.100.0/24"

    def test_get_by_key_not_found(
        self,
        mock_client: MagicMock,
        mock_tenant: MagicMock,
    ) -> None:
        """Test get by key when not found."""
        mock_client._request.return_value = None
        manager = TenantNetworkBlockManager(mock_client, mock_tenant)

        with pytest.raises(NotFoundError):
            manager.get(999)

    def test_get_by_key_invalid_response(
        self,
        mock_client: MagicMock,
        mock_tenant: MagicMock,
    ) -> None:
        """Test get by key with invalid response type."""
        mock_client._request.return_value = "invalid"
        manager = TenantNetworkBlockManager(mock_client, mock_tenant)

        with pytest.raises(NotFoundError):
            manager.get(1)

    def test_get_by_cidr_not_found(
        self,
        mock_client: MagicMock,
        mock_tenant: MagicMock,
    ) -> None:
        """Test get by CIDR when not found."""
        mock_client._request.return_value = []
        manager = TenantNetworkBlockManager(mock_client, mock_tenant)

        with pytest.raises(NotFoundError, match="Network block.*not found"):
            manager.get(cidr="10.0.0.0/24")

    def test_get_requires_key_or_cidr(
        self,
        mock_client: MagicMock,
        mock_tenant: MagicMock,
    ) -> None:
        """Test that get requires key or cidr."""
        manager = TenantNetworkBlockManager(mock_client, mock_tenant)

        with pytest.raises(ValueError, match="Either key or cidr must be provided"):
            manager.get()

    def test_create_network_block(
        self,
        mock_client: MagicMock,
        mock_tenant: MagicMock,
        sample_network_block_data: dict[str, Any],
    ) -> None:
        """Test creating a network block."""
        mock_client._request.side_effect = [
            None,  # POST response
            [sample_network_block_data],  # GET response
        ]
        manager = TenantNetworkBlockManager(mock_client, mock_tenant)

        block = manager.create(cidr="192.168.100.0/24", network=10)

        assert block.cidr == "192.168.100.0/24"
        # Verify POST was called with correct body
        post_call = mock_client._request.call_args_list[0]
        assert post_call[0][0] == "POST"
        assert post_call[1]["json_data"]["cidr"] == "192.168.100.0/24"
        assert post_call[1]["json_data"]["vnet"] == 10
        assert post_call[1]["json_data"]["owner"] == "tenants/123"

    def test_create_network_block_with_network_name(
        self,
        mock_client: MagicMock,
        mock_tenant: MagicMock,
        sample_network_block_data: dict[str, Any],
    ) -> None:
        """Test creating a network block by network name."""
        mock_client._request.side_effect = [
            [{"$key": 10, "name": "Internal"}],  # Network lookup
            None,  # POST response
            [sample_network_block_data],  # GET response
        ]
        manager = TenantNetworkBlockManager(mock_client, mock_tenant)

        block = manager.create(cidr="192.168.100.0/24", network_name="Internal")

        assert block.cidr == "192.168.100.0/24"

    def test_create_network_block_with_description(
        self,
        mock_client: MagicMock,
        mock_tenant: MagicMock,
        sample_network_block_data: dict[str, Any],
    ) -> None:
        """Test creating a network block with description."""
        mock_client._request.side_effect = [
            None,  # POST response
            [sample_network_block_data],  # GET response
        ]
        manager = TenantNetworkBlockManager(mock_client, mock_tenant)

        manager.create(cidr="192.168.100.0/24", network=10, description="Test block")

        post_call = mock_client._request.call_args_list[0]
        assert post_call[1]["json_data"]["description"] == "Test block"

    def test_create_on_snapshot_raises_error(
        self,
        mock_client: MagicMock,
        mock_tenant: MagicMock,
    ) -> None:
        """Test that create raises error for snapshot tenant."""
        mock_tenant.is_snapshot = True
        manager = TenantNetworkBlockManager(mock_client, mock_tenant)

        with pytest.raises(ValueError, match="Cannot assign network block to a tenant snapshot"):
            manager.create(cidr="192.168.100.0/24", network=10)

    def test_create_requires_network_or_network_name(
        self,
        mock_client: MagicMock,
        mock_tenant: MagicMock,
    ) -> None:
        """Test that create requires network or network_name."""
        manager = TenantNetworkBlockManager(mock_client, mock_tenant)

        with pytest.raises(ValueError, match="Either network or network_name must be provided"):
            manager.create(cidr="192.168.100.0/24")

    def test_create_network_name_not_found(
        self,
        mock_client: MagicMock,
        mock_tenant: MagicMock,
    ) -> None:
        """Test create with network name that doesn't exist."""
        mock_client._request.return_value = []
        manager = TenantNetworkBlockManager(mock_client, mock_tenant)

        with pytest.raises(NotFoundError, match="Network.*not found"):
            manager.create(cidr="192.168.100.0/24", network_name="NonExistent")

    def test_delete_network_block(
        self,
        mock_client: MagicMock,
        mock_tenant: MagicMock,
    ) -> None:
        """Test deleting a network block."""
        manager = TenantNetworkBlockManager(mock_client, mock_tenant)

        manager.delete(1)

        mock_client._request.assert_called_once()
        call_args = mock_client._request.call_args
        assert call_args[0][0] == "DELETE"
        assert call_args[0][1] == "vnet_cidrs/1"

    def test_delete_by_cidr(
        self,
        mock_client: MagicMock,
        mock_tenant: MagicMock,
        sample_network_block_data: dict[str, Any],
    ) -> None:
        """Test deleting a network block by CIDR."""
        mock_client._request.side_effect = [
            [sample_network_block_data],  # GET response
            None,  # DELETE response
        ]
        manager = TenantNetworkBlockManager(mock_client, mock_tenant)

        manager.delete_by_cidr("192.168.100.0/24")

        # Verify DELETE was called
        delete_call = mock_client._request.call_args_list[1]
        assert delete_call[0][0] == "DELETE"
        assert delete_call[0][1] == "vnet_cidrs/1"

    def test_delete_by_cidr_not_found(
        self,
        mock_client: MagicMock,
        mock_tenant: MagicMock,
    ) -> None:
        """Test delete by CIDR when not found."""
        mock_client._request.return_value = []
        manager = TenantNetworkBlockManager(mock_client, mock_tenant)

        with pytest.raises(NotFoundError):
            manager.delete_by_cidr("10.0.0.0/24")
