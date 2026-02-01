"""Unit tests for TenantStorage operations."""

from __future__ import annotations

from datetime import timezone
from typing import Any
from unittest.mock import MagicMock

import pytest

from pyvergeos.exceptions import NotFoundError
from pyvergeos.resources.tenant_storage import (
    TenantStorage,
    TenantStorageManager,
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
def sample_storage_data() -> dict[str, Any]:
    """Sample tenant storage data from API."""
    return {
        "$key": 1,
        "tenant": 123,
        "tier": 10,  # tier key
        "tier_number": 1,
        "tier_description": "Fast SSD Storage",
        "provisioned": 107374182400,  # 100 GB
        "used": 53687091200,  # 50 GB
        "allocated": 85899345920,  # 80 GB
        "used_pct": 50,
        "last_update": 1704067200,
    }


@pytest.fixture
def sample_storage_list() -> list[dict[str, Any]]:
    """Sample list of tenant storage allocations."""
    return [
        {
            "$key": 1,
            "tenant": 123,
            "tier": 10,
            "tier_number": 1,
            "tier_description": "Fast SSD",
            "provisioned": 107374182400,
            "used": 53687091200,
            "allocated": 85899345920,
            "used_pct": 50,
            "last_update": 1704067200,
        },
        {
            "$key": 2,
            "tenant": 123,
            "tier": 20,
            "tier_number": 2,
            "tier_description": "Standard HDD",
            "provisioned": 536870912000,  # 500 GB
            "used": 107374182400,  # 100 GB
            "allocated": 214748364800,  # 200 GB
            "used_pct": 20,
            "last_update": 1704067200,
        },
    ]


# =============================================================================
# TenantStorage Model Tests
# =============================================================================


class TestTenantStorage:
    """Tests for TenantStorage model."""

    def test_storage_properties(self, sample_storage_data: dict[str, Any]) -> None:
        """Test storage properties."""
        manager = MagicMock()
        storage = TenantStorage(sample_storage_data, manager)

        assert storage.key == 1
        assert storage.tenant_key == 123
        assert storage.tier_key == 10
        assert storage.tier == 1
        assert storage.tier_description == "Fast SSD Storage"

    def test_storage_tier_name(self, sample_storage_data: dict[str, Any]) -> None:
        """Test tier_name formatted property."""
        manager = MagicMock()
        storage = TenantStorage(sample_storage_data, manager)

        assert storage.tier_name == "Tier 1"

    def test_storage_provisioned_bytes(self, sample_storage_data: dict[str, Any]) -> None:
        """Test provisioned_bytes property."""
        manager = MagicMock()
        storage = TenantStorage(sample_storage_data, manager)

        assert storage.provisioned_bytes == 107374182400

    def test_storage_provisioned_gb(self, sample_storage_data: dict[str, Any]) -> None:
        """Test provisioned_gb property."""
        manager = MagicMock()
        storage = TenantStorage(sample_storage_data, manager)

        assert storage.provisioned_gb == 100.0

    def test_storage_used_bytes(self, sample_storage_data: dict[str, Any]) -> None:
        """Test used_bytes property."""
        manager = MagicMock()
        storage = TenantStorage(sample_storage_data, manager)

        assert storage.used_bytes == 53687091200

    def test_storage_used_gb(self, sample_storage_data: dict[str, Any]) -> None:
        """Test used_gb property."""
        manager = MagicMock()
        storage = TenantStorage(sample_storage_data, manager)

        assert storage.used_gb == 50.0

    def test_storage_allocated_bytes(self, sample_storage_data: dict[str, Any]) -> None:
        """Test allocated_bytes property."""
        manager = MagicMock()
        storage = TenantStorage(sample_storage_data, manager)

        assert storage.allocated_bytes == 85899345920

    def test_storage_allocated_gb(self, sample_storage_data: dict[str, Any]) -> None:
        """Test allocated_gb property."""
        manager = MagicMock()
        storage = TenantStorage(sample_storage_data, manager)

        assert storage.allocated_gb == 80.0

    def test_storage_used_percent(self, sample_storage_data: dict[str, Any]) -> None:
        """Test used_percent property."""
        manager = MagicMock()
        storage = TenantStorage(sample_storage_data, manager)

        assert storage.used_percent == 50

    def test_storage_free_bytes(self, sample_storage_data: dict[str, Any]) -> None:
        """Test free_bytes property."""
        manager = MagicMock()
        storage = TenantStorage(sample_storage_data, manager)

        # 100 GB - 50 GB = 50 GB
        assert storage.free_bytes == 53687091200

    def test_storage_free_gb(self, sample_storage_data: dict[str, Any]) -> None:
        """Test free_gb property."""
        manager = MagicMock()
        storage = TenantStorage(sample_storage_data, manager)

        assert storage.free_gb == 50.0

    def test_storage_free_bytes_never_negative(self) -> None:
        """Test free_bytes is never negative (over-provisioned)."""
        manager = MagicMock()
        storage = TenantStorage(
            {
                "$key": 1,
                "tenant": 123,
                "provisioned": 100000,
                "used": 200000,  # More used than provisioned
            },
            manager,
        )

        assert storage.free_bytes == 0

    def test_storage_last_update(self, sample_storage_data: dict[str, Any]) -> None:
        """Test last_update timestamp."""
        manager = MagicMock()
        storage = TenantStorage(sample_storage_data, manager)

        assert storage.last_update is not None
        assert storage.last_update.year == 2024
        assert storage.last_update.month == 1
        assert storage.last_update.day == 1
        assert storage.last_update.tzinfo == timezone.utc

    def test_storage_last_update_none(self) -> None:
        """Test last_update when not set."""
        manager = MagicMock()
        storage = TenantStorage({"$key": 1, "tenant": 123}, manager)

        assert storage.last_update is None

    def test_storage_tier_description_none(self) -> None:
        """Test tier_description when not set."""
        manager = MagicMock()
        storage = TenantStorage({"$key": 1, "tenant": 123}, manager)

        assert storage.tier_description is None

    def test_storage_default_values(self) -> None:
        """Test default values for missing fields."""
        manager = MagicMock()
        storage = TenantStorage({"$key": 1}, manager)

        assert storage.tenant_key == 0
        assert storage.tier_key == 0
        assert storage.tier == 0
        assert storage.provisioned_bytes == 0
        assert storage.used_bytes == 0
        assert storage.allocated_bytes == 0
        assert storage.used_percent == 0

    def test_storage_save(self, sample_storage_data: dict[str, Any]) -> None:
        """Test save method calls manager update."""
        manager = MagicMock()
        manager.update.return_value = TenantStorage(sample_storage_data, manager)
        storage = TenantStorage(sample_storage_data, manager)

        result = storage.save(provisioned_gb=200)

        # provisioned_gb should be converted to bytes
        manager.update.assert_called_once_with(1, provisioned=214748364800)
        assert isinstance(result, TenantStorage)

    def test_storage_save_with_kwargs(self, sample_storage_data: dict[str, Any]) -> None:
        """Test save method passes through kwargs."""
        manager = MagicMock()
        manager.update.return_value = TenantStorage(sample_storage_data, manager)
        storage = TenantStorage(sample_storage_data, manager)

        storage.save(custom_field="value")

        manager.update.assert_called_once_with(1, custom_field="value")

    def test_storage_delete(self, sample_storage_data: dict[str, Any]) -> None:
        """Test delete method calls manager."""
        manager = MagicMock()
        storage = TenantStorage(sample_storage_data, manager)

        storage.delete()

        manager.delete.assert_called_once_with(1)

    def test_storage_repr(self, sample_storage_data: dict[str, Any]) -> None:
        """Test storage repr."""
        manager = MagicMock()
        storage = TenantStorage(sample_storage_data, manager)

        repr_str = repr(storage)
        assert "TenantStorage" in repr_str
        assert "Tier 1" in repr_str
        assert "50.0/100.0 GB" in repr_str
        assert "50%" in repr_str


# =============================================================================
# TenantStorageManager Tests
# =============================================================================


class TestTenantStorageManager:
    """Tests for TenantStorageManager."""

    def test_list_storage(
        self,
        mock_client: MagicMock,
        mock_tenant: MagicMock,
        sample_storage_list: list[dict[str, Any]],
    ) -> None:
        """Test listing storage allocations."""
        mock_client._request.return_value = sample_storage_list
        manager = TenantStorageManager(mock_client, mock_tenant)

        allocations = manager.list()

        assert len(allocations) == 2
        assert allocations[0].tier == 1
        assert allocations[1].tier == 2
        mock_client._request.assert_called_once()

    def test_list_filters_by_tenant(
        self,
        mock_client: MagicMock,
        mock_tenant: MagicMock,
    ) -> None:
        """Test that list filters by tenant."""
        mock_client._request.return_value = []
        manager = TenantStorageManager(mock_client, mock_tenant)

        manager.list()

        call_args = mock_client._request.call_args
        params = call_args[1]["params"]
        assert "tenant eq 123" in params["filter"]

    def test_list_with_tier_filter(
        self,
        mock_client: MagicMock,
        mock_tenant: MagicMock,
        sample_storage_list: list[dict[str, Any]],
    ) -> None:
        """Test listing with tier filter."""
        mock_client._request.return_value = sample_storage_list
        manager = TenantStorageManager(mock_client, mock_tenant)

        allocations = manager.list(tier=1)

        # Manager filters in-memory by tier number
        assert len(allocations) == 1
        assert allocations[0].tier == 1

    def test_list_with_additional_filter(
        self,
        mock_client: MagicMock,
        mock_tenant: MagicMock,
    ) -> None:
        """Test listing with additional filter."""
        mock_client._request.return_value = []
        manager = TenantStorageManager(mock_client, mock_tenant)

        manager.list(filter="used_pct gt 50")

        call_args = mock_client._request.call_args
        params = call_args[1]["params"]
        assert "used_pct gt 50" in params["filter"]

    def test_list_empty_response(
        self,
        mock_client: MagicMock,
        mock_tenant: MagicMock,
    ) -> None:
        """Test list with None response."""
        mock_client._request.return_value = None
        manager = TenantStorageManager(mock_client, mock_tenant)

        allocations = manager.list()

        assert allocations == []

    def test_list_single_response(
        self,
        mock_client: MagicMock,
        mock_tenant: MagicMock,
        sample_storage_data: dict[str, Any],
    ) -> None:
        """Test list when API returns single item (not list)."""
        mock_client._request.return_value = sample_storage_data
        manager = TenantStorageManager(mock_client, mock_tenant)

        allocations = manager.list()

        assert len(allocations) == 1
        assert allocations[0].tier == 1

    def test_get_by_key(
        self,
        mock_client: MagicMock,
        mock_tenant: MagicMock,
        sample_storage_data: dict[str, Any],
    ) -> None:
        """Test getting a storage allocation by key."""
        mock_client._request.return_value = sample_storage_data
        manager = TenantStorageManager(mock_client, mock_tenant)

        allocation = manager.get(1)

        assert allocation.key == 1
        assert allocation.tier == 1
        call_args = mock_client._request.call_args
        assert call_args[0][1] == "tenant_storage/1"

    def test_get_by_tier(
        self,
        mock_client: MagicMock,
        mock_tenant: MagicMock,
        sample_storage_list: list[dict[str, Any]],
    ) -> None:
        """Test getting a storage allocation by tier number."""
        mock_client._request.return_value = sample_storage_list
        manager = TenantStorageManager(mock_client, mock_tenant)

        allocation = manager.get(tier=1)

        assert allocation.tier == 1

    def test_get_by_key_not_found(
        self,
        mock_client: MagicMock,
        mock_tenant: MagicMock,
    ) -> None:
        """Test get by key when not found."""
        mock_client._request.return_value = None
        manager = TenantStorageManager(mock_client, mock_tenant)

        with pytest.raises(NotFoundError, match="Tenant storage allocation 999 not found"):
            manager.get(999)

    def test_get_by_key_invalid_response(
        self,
        mock_client: MagicMock,
        mock_tenant: MagicMock,
    ) -> None:
        """Test get by key with invalid response type."""
        mock_client._request.return_value = "invalid"
        manager = TenantStorageManager(mock_client, mock_tenant)

        with pytest.raises(NotFoundError):
            manager.get(1)

    def test_get_by_tier_not_found(
        self,
        mock_client: MagicMock,
        mock_tenant: MagicMock,
    ) -> None:
        """Test get by tier when not found."""
        mock_client._request.return_value = []
        manager = TenantStorageManager(mock_client, mock_tenant)

        with pytest.raises(NotFoundError, match="No Tier 3 storage allocation found"):
            manager.get(tier=3)

    def test_get_requires_key_or_tier(
        self,
        mock_client: MagicMock,
        mock_tenant: MagicMock,
    ) -> None:
        """Test that get requires key or tier."""
        manager = TenantStorageManager(mock_client, mock_tenant)

        with pytest.raises(ValueError, match="Either key or tier must be provided"):
            manager.get()

    def test_create_storage_with_gb(
        self,
        mock_client: MagicMock,
        mock_tenant: MagicMock,
        sample_storage_data: dict[str, Any],
    ) -> None:
        """Test creating a storage allocation with GB."""
        mock_client._request.side_effect = [
            [{"$key": 10, "tier": 1}],  # Tier lookup
            None,  # POST response
            [sample_storage_data],  # GET response
        ]
        manager = TenantStorageManager(mock_client, mock_tenant)

        allocation = manager.create(tier=1, provisioned_gb=100)

        assert allocation.tier == 1
        post_call = mock_client._request.call_args_list[1]
        assert post_call[0][0] == "POST"
        assert post_call[1]["json_data"]["tenant"] == 123
        assert post_call[1]["json_data"]["tier"] == 10  # tier key, not number
        assert post_call[1]["json_data"]["provisioned"] == 107374182400

    def test_create_storage_with_bytes(
        self,
        mock_client: MagicMock,
        mock_tenant: MagicMock,
        sample_storage_data: dict[str, Any],
    ) -> None:
        """Test creating a storage allocation with bytes."""
        mock_client._request.side_effect = [
            [{"$key": 10, "tier": 1}],  # Tier lookup
            None,  # POST response
            [sample_storage_data],  # GET response
        ]
        manager = TenantStorageManager(mock_client, mock_tenant)

        manager.create(tier=1, provisioned_bytes=107374182400)

        post_call = mock_client._request.call_args_list[1]
        assert post_call[1]["json_data"]["provisioned"] == 107374182400

    def test_create_on_snapshot_raises_error(
        self,
        mock_client: MagicMock,
        mock_tenant: MagicMock,
    ) -> None:
        """Test that create raises error for snapshot tenant."""
        mock_tenant.is_snapshot = True
        manager = TenantStorageManager(mock_client, mock_tenant)

        with pytest.raises(ValueError, match="Cannot add storage to a tenant snapshot"):
            manager.create(tier=1, provisioned_gb=100)

    def test_create_invalid_tier(
        self,
        mock_client: MagicMock,
        mock_tenant: MagicMock,
    ) -> None:
        """Test that create validates tier number."""
        manager = TenantStorageManager(mock_client, mock_tenant)

        with pytest.raises(ValueError, match="Invalid tier 0"):
            manager.create(tier=0, provisioned_gb=100)

        with pytest.raises(ValueError, match="Invalid tier 6"):
            manager.create(tier=6, provisioned_gb=100)

    def test_create_requires_size(
        self,
        mock_client: MagicMock,
        mock_tenant: MagicMock,
    ) -> None:
        """Test that create requires provisioned_gb or provisioned_bytes."""
        manager = TenantStorageManager(mock_client, mock_tenant)

        with pytest.raises(ValueError, match="Either provisioned_gb or provisioned_bytes"):
            manager.create(tier=1)

    def test_create_minimum_size(
        self,
        mock_client: MagicMock,
        mock_tenant: MagicMock,
    ) -> None:
        """Test that create validates minimum size (1 GB)."""
        mock_client._request.return_value = [{"$key": 10, "tier": 1}]
        manager = TenantStorageManager(mock_client, mock_tenant)

        with pytest.raises(ValueError, match="at least 1 GB"):
            manager.create(tier=1, provisioned_bytes=100000)  # Less than 1 GB

    def test_create_tier_not_found(
        self,
        mock_client: MagicMock,
        mock_tenant: MagicMock,
    ) -> None:
        """Test create when tier not found."""
        mock_client._request.return_value = []
        manager = TenantStorageManager(mock_client, mock_tenant)

        with pytest.raises(NotFoundError, match="Storage tier 3 not found"):
            manager.create(tier=3, provisioned_gb=100)

    def test_update_storage(
        self,
        mock_client: MagicMock,
        mock_tenant: MagicMock,
        sample_storage_data: dict[str, Any],
    ) -> None:
        """Test updating a storage allocation."""
        mock_client._request.side_effect = [
            None,  # PUT response
            sample_storage_data,  # GET response
        ]
        manager = TenantStorageManager(mock_client, mock_tenant)

        allocation = manager.update(1, provisioned=214748364800)

        assert allocation.key == 1
        put_call = mock_client._request.call_args_list[0]
        assert put_call[0][0] == "PUT"
        assert put_call[0][1] == "tenant_storage/1"
        assert put_call[1]["json_data"]["provisioned"] == 214748364800

    def test_update_by_tier(
        self,
        mock_client: MagicMock,
        mock_tenant: MagicMock,
        sample_storage_list: list[dict[str, Any]],
    ) -> None:
        """Test updating a storage allocation by tier."""
        mock_client._request.side_effect = [
            sample_storage_list,  # List response to find allocation
            None,  # PUT response
            sample_storage_list[0],  # GET response
        ]
        manager = TenantStorageManager(mock_client, mock_tenant)

        allocation = manager.update_by_tier(1, provisioned_gb=200)

        assert allocation.tier == 1
        put_call = mock_client._request.call_args_list[1]
        assert put_call[1]["json_data"]["provisioned"] == 214748364800

    def test_update_by_tier_with_bytes(
        self,
        mock_client: MagicMock,
        mock_tenant: MagicMock,
        sample_storage_list: list[dict[str, Any]],
    ) -> None:
        """Test update_by_tier with provisioned_bytes."""
        mock_client._request.side_effect = [
            sample_storage_list,  # List response
            None,  # PUT response
            sample_storage_list[0],  # GET response
        ]
        manager = TenantStorageManager(mock_client, mock_tenant)

        manager.update_by_tier(1, provisioned_bytes=214748364800)

        put_call = mock_client._request.call_args_list[1]
        assert put_call[1]["json_data"]["provisioned"] == 214748364800

    def test_update_by_tier_requires_size(
        self,
        mock_client: MagicMock,
        mock_tenant: MagicMock,
    ) -> None:
        """Test that update_by_tier requires provisioned_gb or provisioned_bytes."""
        manager = TenantStorageManager(mock_client, mock_tenant)

        with pytest.raises(ValueError, match="Either provisioned_gb or provisioned_bytes"):
            manager.update_by_tier(1)

    def test_delete_storage(
        self,
        mock_client: MagicMock,
        mock_tenant: MagicMock,
    ) -> None:
        """Test deleting a storage allocation."""
        manager = TenantStorageManager(mock_client, mock_tenant)

        manager.delete(1)

        mock_client._request.assert_called_once()
        call_args = mock_client._request.call_args
        assert call_args[0][0] == "DELETE"
        assert call_args[0][1] == "tenant_storage/1"

    def test_delete_by_tier(
        self,
        mock_client: MagicMock,
        mock_tenant: MagicMock,
        sample_storage_list: list[dict[str, Any]],
    ) -> None:
        """Test deleting a storage allocation by tier."""
        mock_client._request.side_effect = [
            sample_storage_list,  # List response to find allocation
            None,  # DELETE response
        ]
        manager = TenantStorageManager(mock_client, mock_tenant)

        manager.delete_by_tier(1)

        delete_call = mock_client._request.call_args_list[1]
        assert delete_call[0][0] == "DELETE"
        assert delete_call[0][1] == "tenant_storage/1"

    def test_delete_by_tier_not_found(
        self,
        mock_client: MagicMock,
        mock_tenant: MagicMock,
    ) -> None:
        """Test delete_by_tier when tier not found."""
        mock_client._request.return_value = []
        manager = TenantStorageManager(mock_client, mock_tenant)

        with pytest.raises(NotFoundError):
            manager.delete_by_tier(3)
