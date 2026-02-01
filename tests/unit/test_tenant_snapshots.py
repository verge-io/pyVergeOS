"""Unit tests for TenantSnapshot operations."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock

import pytest

from pyvergeos.exceptions import NotFoundError
from pyvergeos.resources.tenant_snapshots import (
    TenantSnapshot,
    TenantSnapshotManager,
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
    tenant.is_running = False
    tenant.refresh.return_value = tenant
    return tenant


@pytest.fixture
def sample_snapshot_data() -> dict[str, Any]:
    """Sample tenant snapshot data from API."""
    return {
        "$key": 1,
        "tenant": 123,
        "name": "daily-backup",
        "description": "Daily backup snapshot",
        "profile": "daily",
        "period": "daily",
        "min_snapshots": 7,
        "created": 1704067200,  # 2024-01-01 00:00:00 UTC
        "expires": 1704672000,  # 2024-01-08 00:00:00 UTC
    }


@pytest.fixture
def sample_snapshot_never_expires() -> dict[str, Any]:
    """Sample tenant snapshot that never expires."""
    return {
        "$key": 2,
        "tenant": 123,
        "name": "manual-backup",
        "description": "Manual backup",
        "created": 1704067200,
        "expires": 0,
    }


@pytest.fixture
def sample_snapshot_list() -> list[dict[str, Any]]:
    """Sample list of tenant snapshots."""
    return [
        {
            "$key": 1,
            "tenant": 123,
            "name": "daily-backup-1",
            "created": 1704067200,
            "expires": 1704672000,
        },
        {
            "$key": 2,
            "tenant": 123,
            "name": "daily-backup-2",
            "created": 1704153600,
            "expires": 1704758400,
        },
    ]


# =============================================================================
# TenantSnapshot Model Tests
# =============================================================================


class TestTenantSnapshot:
    """Tests for TenantSnapshot model."""

    def test_snapshot_properties(self, sample_snapshot_data: dict[str, Any]) -> None:
        """Test snapshot properties."""
        manager = MagicMock()
        snapshot = TenantSnapshot(sample_snapshot_data, manager)

        assert snapshot.key == 1
        assert snapshot.tenant_key == 123
        assert snapshot.name == "daily-backup"
        assert snapshot.description == "Daily backup snapshot"

    def test_snapshot_profile_and_period(self, sample_snapshot_data: dict[str, Any]) -> None:
        """Test profile and period properties."""
        manager = MagicMock()
        snapshot = TenantSnapshot(sample_snapshot_data, manager)

        assert snapshot.profile == "daily"
        assert snapshot.period == "daily"
        assert snapshot.min_snapshots == 7

    def test_snapshot_profile_none(self) -> None:
        """Test profile when not set (manual snapshot)."""
        manager = MagicMock()
        snapshot = TenantSnapshot({"$key": 1, "tenant": 123, "name": "manual"}, manager)

        assert snapshot.profile is None
        assert snapshot.period is None
        assert snapshot.min_snapshots == 0

    def test_snapshot_created_at(self, sample_snapshot_data: dict[str, Any]) -> None:
        """Test created_at timestamp."""
        manager = MagicMock()
        snapshot = TenantSnapshot(sample_snapshot_data, manager)

        assert snapshot.created_at is not None
        assert snapshot.created_at.year == 2024
        assert snapshot.created_at.month == 1
        assert snapshot.created_at.day == 1
        assert snapshot.created_at.tzinfo == timezone.utc

    def test_snapshot_created_at_none(self) -> None:
        """Test created_at when not set."""
        manager = MagicMock()
        snapshot = TenantSnapshot({"$key": 1, "tenant": 123}, manager)

        assert snapshot.created_at is None

    def test_snapshot_expires_at(self, sample_snapshot_data: dict[str, Any]) -> None:
        """Test expires_at timestamp."""
        manager = MagicMock()
        snapshot = TenantSnapshot(sample_snapshot_data, manager)

        assert snapshot.expires_at is not None
        assert snapshot.expires_at.year == 2024
        assert snapshot.expires_at.month == 1
        assert snapshot.expires_at.day == 8
        assert snapshot.expires_at.tzinfo == timezone.utc

    def test_snapshot_expires_at_none(self) -> None:
        """Test expires_at when not set."""
        manager = MagicMock()
        snapshot = TenantSnapshot({"$key": 1, "tenant": 123}, manager)

        assert snapshot.expires_at is None

    def test_snapshot_expires_at_zero(self, sample_snapshot_never_expires: dict[str, Any]) -> None:
        """Test expires_at when set to 0 (never expires)."""
        manager = MagicMock()
        snapshot = TenantSnapshot(sample_snapshot_never_expires, manager)

        assert snapshot.expires_at is None

    def test_snapshot_never_expires(self, sample_snapshot_never_expires: dict[str, Any]) -> None:
        """Test never_expires property."""
        manager = MagicMock()
        snapshot = TenantSnapshot(sample_snapshot_never_expires, manager)

        assert snapshot.never_expires is True

    def test_snapshot_expires(self, sample_snapshot_data: dict[str, Any]) -> None:
        """Test never_expires is False when snapshot has expiration."""
        manager = MagicMock()
        snapshot = TenantSnapshot(sample_snapshot_data, manager)

        assert snapshot.never_expires is False

    def test_snapshot_never_expires_none(self) -> None:
        """Test never_expires when expires is None."""
        manager = MagicMock()
        snapshot = TenantSnapshot({"$key": 1, "tenant": 123}, manager)

        assert snapshot.never_expires is True

    def test_snapshot_restore(self, sample_snapshot_data: dict[str, Any]) -> None:
        """Test restore method calls manager."""
        manager = MagicMock()
        manager.restore.return_value = {"task": 456}
        snapshot = TenantSnapshot(sample_snapshot_data, manager)

        result = snapshot.restore()

        manager.restore.assert_called_once_with(1)
        assert result == {"task": 456}


# =============================================================================
# TenantSnapshotManager Tests
# =============================================================================


class TestTenantSnapshotManager:
    """Tests for TenantSnapshotManager."""

    def test_list_snapshots(
        self,
        mock_client: MagicMock,
        mock_tenant: MagicMock,
        sample_snapshot_list: list[dict[str, Any]],
    ) -> None:
        """Test listing snapshots."""
        mock_client._request.return_value = sample_snapshot_list
        manager = TenantSnapshotManager(mock_client, mock_tenant)

        snapshots = manager.list()

        assert len(snapshots) == 2
        assert snapshots[0].name == "daily-backup-1"
        assert snapshots[1].name == "daily-backup-2"
        mock_client._request.assert_called_once()

    def test_list_filters_by_tenant(
        self,
        mock_client: MagicMock,
        mock_tenant: MagicMock,
    ) -> None:
        """Test that list filters by tenant."""
        mock_client._request.return_value = []
        manager = TenantSnapshotManager(mock_client, mock_tenant)

        manager.list()

        call_args = mock_client._request.call_args
        params = call_args[1]["params"]
        assert "tenant eq 123" in params["filter"]

    def test_list_sorts_by_created_descending(
        self,
        mock_client: MagicMock,
        mock_tenant: MagicMock,
    ) -> None:
        """Test that list sorts by created descending."""
        mock_client._request.return_value = []
        manager = TenantSnapshotManager(mock_client, mock_tenant)

        manager.list()

        call_args = mock_client._request.call_args
        params = call_args[1]["params"]
        assert params["sort"] == "-created"

    def test_list_with_additional_filter(
        self,
        mock_client: MagicMock,
        mock_tenant: MagicMock,
    ) -> None:
        """Test listing with additional filter."""
        mock_client._request.return_value = []
        manager = TenantSnapshotManager(mock_client, mock_tenant)

        manager.list(filter="profile eq 'daily'")

        call_args = mock_client._request.call_args
        params = call_args[1]["params"]
        assert "profile eq 'daily'" in params["filter"]
        assert "tenant eq 123" in params["filter"]

    def test_list_empty_response(
        self,
        mock_client: MagicMock,
        mock_tenant: MagicMock,
    ) -> None:
        """Test list with None response."""
        mock_client._request.return_value = None
        manager = TenantSnapshotManager(mock_client, mock_tenant)

        snapshots = manager.list()

        assert snapshots == []

    def test_list_single_response(
        self,
        mock_client: MagicMock,
        mock_tenant: MagicMock,
        sample_snapshot_data: dict[str, Any],
    ) -> None:
        """Test list when API returns single item (not list)."""
        mock_client._request.return_value = sample_snapshot_data
        manager = TenantSnapshotManager(mock_client, mock_tenant)

        snapshots = manager.list()

        assert len(snapshots) == 1
        assert snapshots[0].name == "daily-backup"

    def test_get_by_key(
        self,
        mock_client: MagicMock,
        mock_tenant: MagicMock,
        sample_snapshot_data: dict[str, Any],
    ) -> None:
        """Test getting a snapshot by key."""
        mock_client._request.return_value = sample_snapshot_data
        manager = TenantSnapshotManager(mock_client, mock_tenant)

        snapshot = manager.get(1)

        assert snapshot.key == 1
        assert snapshot.name == "daily-backup"
        call_args = mock_client._request.call_args
        assert call_args[0][1] == "tenant_snapshots/1"

    def test_get_by_name(
        self,
        mock_client: MagicMock,
        mock_tenant: MagicMock,
        sample_snapshot_data: dict[str, Any],
    ) -> None:
        """Test getting a snapshot by name."""
        mock_client._request.return_value = [sample_snapshot_data]
        manager = TenantSnapshotManager(mock_client, mock_tenant)

        snapshot = manager.get(name="daily-backup")

        assert snapshot.name == "daily-backup"

    def test_get_by_key_not_found(
        self,
        mock_client: MagicMock,
        mock_tenant: MagicMock,
    ) -> None:
        """Test get by key when not found."""
        mock_client._request.return_value = None
        manager = TenantSnapshotManager(mock_client, mock_tenant)

        with pytest.raises(NotFoundError, match="Tenant snapshot 999 not found"):
            manager.get(999)

    def test_get_by_key_invalid_response(
        self,
        mock_client: MagicMock,
        mock_tenant: MagicMock,
    ) -> None:
        """Test get by key with invalid response type."""
        mock_client._request.return_value = "invalid"
        manager = TenantSnapshotManager(mock_client, mock_tenant)

        with pytest.raises(NotFoundError):
            manager.get(1)

    def test_get_by_name_not_found(
        self,
        mock_client: MagicMock,
        mock_tenant: MagicMock,
    ) -> None:
        """Test get by name when not found."""
        mock_client._request.return_value = []
        manager = TenantSnapshotManager(mock_client, mock_tenant)

        with pytest.raises(NotFoundError, match="Tenant snapshot with name"):
            manager.get(name="nonexistent")

    def test_get_requires_key_or_name(
        self,
        mock_client: MagicMock,
        mock_tenant: MagicMock,
    ) -> None:
        """Test that get requires key or name."""
        manager = TenantSnapshotManager(mock_client, mock_tenant)

        with pytest.raises(ValueError, match="Either key or name must be provided"):
            manager.get()

    def test_create_snapshot(
        self,
        mock_client: MagicMock,
        mock_tenant: MagicMock,
        sample_snapshot_data: dict[str, Any],
    ) -> None:
        """Test creating a snapshot."""
        mock_client._request.side_effect = [
            None,  # POST response
            [sample_snapshot_data],  # GET response
        ]
        manager = TenantSnapshotManager(mock_client, mock_tenant)

        snapshot = manager.create(name="daily-backup")

        assert snapshot.name == "daily-backup"
        post_call = mock_client._request.call_args_list[0]
        assert post_call[0][0] == "POST"
        assert post_call[1]["json_data"]["tenant"] == 123
        assert post_call[1]["json_data"]["name"] == "daily-backup"

    def test_create_snapshot_with_description(
        self,
        mock_client: MagicMock,
        mock_tenant: MagicMock,
        sample_snapshot_data: dict[str, Any],
    ) -> None:
        """Test creating a snapshot with description."""
        mock_client._request.side_effect = [
            None,  # POST response
            [sample_snapshot_data],  # GET response
        ]
        manager = TenantSnapshotManager(mock_client, mock_tenant)

        manager.create(name="daily-backup", description="Test snapshot")

        post_call = mock_client._request.call_args_list[0]
        assert post_call[1]["json_data"]["description"] == "Test snapshot"

    def test_create_snapshot_with_expires_in_days(
        self,
        mock_client: MagicMock,
        mock_tenant: MagicMock,
        sample_snapshot_data: dict[str, Any],
    ) -> None:
        """Test creating a snapshot with expiration in days."""
        mock_client._request.side_effect = [
            None,  # POST response
            [sample_snapshot_data],  # GET response
        ]
        manager = TenantSnapshotManager(mock_client, mock_tenant)

        manager.create(name="daily-backup", expires_in_days=7)

        post_call = mock_client._request.call_args_list[0]
        # Should have an expires timestamp
        assert "expires" in post_call[1]["json_data"]
        assert post_call[1]["json_data"]["expires"] > 0

    def test_create_snapshot_with_expires_at(
        self,
        mock_client: MagicMock,
        mock_tenant: MagicMock,
        sample_snapshot_data: dict[str, Any],
    ) -> None:
        """Test creating a snapshot with specific expiration datetime."""
        mock_client._request.side_effect = [
            None,  # POST response
            [sample_snapshot_data],  # GET response
        ]
        manager = TenantSnapshotManager(mock_client, mock_tenant)

        expires = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        manager.create(name="daily-backup", expires_at=expires)

        post_call = mock_client._request.call_args_list[0]
        assert post_call[1]["json_data"]["expires"] == int(expires.timestamp())

    def test_create_snapshot_never_expires(
        self,
        mock_client: MagicMock,
        mock_tenant: MagicMock,
        sample_snapshot_data: dict[str, Any],
    ) -> None:
        """Test creating a snapshot that never expires."""
        mock_client._request.side_effect = [
            None,  # POST response
            [sample_snapshot_data],  # GET response
        ]
        manager = TenantSnapshotManager(mock_client, mock_tenant)

        manager.create(name="daily-backup", expires_in_days=0)

        post_call = mock_client._request.call_args_list[0]
        # Should not have expires in body when 0 days
        assert "expires" not in post_call[1]["json_data"]

    def test_create_on_snapshot_raises_error(
        self,
        mock_client: MagicMock,
        mock_tenant: MagicMock,
    ) -> None:
        """Test that create raises error for snapshot tenant."""
        mock_tenant.is_snapshot = True
        manager = TenantSnapshotManager(mock_client, mock_tenant)

        with pytest.raises(ValueError, match="Cannot create snapshot of a tenant snapshot"):
            manager.create(name="test")

    def test_delete_snapshot(
        self,
        mock_client: MagicMock,
        mock_tenant: MagicMock,
    ) -> None:
        """Test deleting a snapshot."""
        manager = TenantSnapshotManager(mock_client, mock_tenant)

        manager.delete(1)

        mock_client._request.assert_called_once()
        call_args = mock_client._request.call_args
        assert call_args[0][0] == "DELETE"
        assert call_args[0][1] == "tenant_snapshots/1"

    def test_restore_snapshot(
        self,
        mock_client: MagicMock,
        mock_tenant: MagicMock,
    ) -> None:
        """Test restoring from a snapshot."""
        mock_client._request.return_value = {"task": 456}
        manager = TenantSnapshotManager(mock_client, mock_tenant)

        result = manager.restore(1)

        assert result == {"task": 456}
        mock_client._request.assert_called_once()
        call_args = mock_client._request.call_args
        assert call_args[0][0] == "POST"
        assert call_args[0][1] == "tenant_actions"
        json_data = call_args[1]["json_data"]
        assert json_data["tenant"] == 123
        assert json_data["action"] == "restore"
        assert json_data["params"]["snapshot"] == 1

    def test_restore_tenant_running_raises_error(
        self,
        mock_client: MagicMock,
        mock_tenant: MagicMock,
    ) -> None:
        """Test that restore raises error if tenant is running."""
        mock_tenant.is_running = True
        manager = TenantSnapshotManager(mock_client, mock_tenant)

        with pytest.raises(ValueError, match="Tenant must be powered off"):
            manager.restore(1)

    def test_restore_returns_none_for_non_dict(
        self,
        mock_client: MagicMock,
        mock_tenant: MagicMock,
    ) -> None:
        """Test restore returns None when response is not a dict."""
        mock_client._request.return_value = "success"
        manager = TenantSnapshotManager(mock_client, mock_tenant)

        result = manager.restore(1)

        assert result is None
