"""Unit tests for Cloud Snapshot operations."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from pyvergeos import VergeClient
from pyvergeos.exceptions import (
    APIError,
    AuthenticationError,
    ConflictError,
    NotFoundError,
    ValidationError,
    VergeTimeoutError,
)
from pyvergeos.resources.cloud_snapshots import (
    CloudSnapshot,
    CloudSnapshotTenant,
    CloudSnapshotVM,
)

# =============================================================================
# Sample Data Fixtures
# =============================================================================


@pytest.fixture
def sample_snapshot_data() -> dict[str, Any]:
    """Sample cloud snapshot data."""
    # Using exact UTC timestamps
    # 2025-01-01 00:00:00 UTC = 1735689600
    # 2025-01-02 00:00:00 UTC = 1735776000
    # 2025-01-03 00:00:00 UTC = 1735862400
    return {
        "$key": 1,
        "name": "Test Snapshot",
        "description": "A test cloud snapshot",
        "created": 1735689600,
        "expires": 1735776000,
        "expires_type": "time",
        "snapshot_profile": 5,
        "private": False,
        "remote_sync": False,
        "immutable": True,
        "immutable_status": "locked",
        "immutable_lock_expires": 1735862400,
        "status": "normal",
        "status_info": "",
    }


@pytest.fixture
def sample_vm_data() -> dict[str, Any]:
    """Sample cloud snapshot VM data."""
    return {
        "$key": 100,
        "name": "TestVM",
        "description": "A test VM in snapshot",
        "uuid": "550e8400-e29b-41d4-a716-446655440000",
        "machine_uuid": "660e8400-e29b-41d4-a716-446655440001",
        "cpu_cores": 2,
        "ram": 2048,
        "os_family": "linux",
        "is_snapshot": True,
        "status": "idle",
        "status_info": "",
        "original_key": 50,
        "cloud_snapshot": 1,
    }


@pytest.fixture
def sample_tenant_data() -> dict[str, Any]:
    """Sample cloud snapshot tenant data."""
    return {
        "$key": 200,
        "name": "TestTenant",
        "description": "A test tenant in snapshot",
        "uuid": "770e8400-e29b-41d4-a716-446655440002",
        "nodes": 2,
        "cpu_cores": 8,
        "ram": 16384,
        "is_snapshot": True,
        "status": "idle",
        "status_info": "",
        "original_key": 10,
        "cloud_snapshot": 1,
    }


# =============================================================================
# CloudSnapshotVM Model Tests
# =============================================================================


class TestCloudSnapshotVM:
    """Unit tests for CloudSnapshotVM model."""

    def test_vm_properties(self, mock_client: VergeClient, sample_vm_data: dict[str, Any]) -> None:
        """Test CloudSnapshotVM property accessors."""
        vm = CloudSnapshotVM(sample_vm_data, mock_client.cloud_snapshots.vms(1))

        assert vm.key == 100
        assert vm.name == "TestVM"
        assert vm.description == "A test VM in snapshot"
        assert vm.uuid == "550e8400-e29b-41d4-a716-446655440000"
        assert vm.machine_uuid == "660e8400-e29b-41d4-a716-446655440001"
        assert vm.cpu_cores == 2
        assert vm.ram_mb == 2048
        assert vm.os_family == "linux"
        assert vm.is_snapshot is True
        assert vm.status == "idle"
        assert vm.status_info == ""
        assert vm.original_key == 50
        assert vm.cloud_snapshot_key == 1

    def test_vm_repr(self, mock_client: VergeClient, sample_vm_data: dict[str, Any]) -> None:
        """Test CloudSnapshotVM string representation."""
        vm = CloudSnapshotVM(sample_vm_data, mock_client.cloud_snapshots.vms(1))
        assert repr(vm) == "<CloudSnapshotVM key=100 name='TestVM'>"

    def test_vm_missing_optional_fields(self, mock_client: VergeClient) -> None:
        """Test CloudSnapshotVM with minimal data."""
        data = {"$key": 1, "name": "MinimalVM", "cloud_snapshot": 1}
        vm = CloudSnapshotVM(data, mock_client.cloud_snapshots.vms(1))

        assert vm.key == 1
        assert vm.name == "MinimalVM"
        assert vm.description == ""
        assert vm.uuid is None
        assert vm.machine_uuid is None
        assert vm.cpu_cores == 0
        assert vm.ram_mb == 0
        assert vm.os_family == ""
        assert vm.is_snapshot is False
        assert vm.status == "idle"
        assert vm.original_key is None


# =============================================================================
# CloudSnapshotTenant Model Tests
# =============================================================================


class TestCloudSnapshotTenant:
    """Unit tests for CloudSnapshotTenant model."""

    def test_tenant_properties(
        self, mock_client: VergeClient, sample_tenant_data: dict[str, Any]
    ) -> None:
        """Test CloudSnapshotTenant property accessors."""
        tenant = CloudSnapshotTenant(sample_tenant_data, mock_client.cloud_snapshots.tenants(1))

        assert tenant.key == 200
        assert tenant.name == "TestTenant"
        assert tenant.description == "A test tenant in snapshot"
        assert tenant.uuid == "770e8400-e29b-41d4-a716-446655440002"
        assert tenant.nodes == 2
        assert tenant.cpu_cores == 8
        assert tenant.ram_mb == 16384
        assert tenant.is_snapshot is True
        assert tenant.status == "idle"
        assert tenant.status_info == ""
        assert tenant.original_key == 10
        assert tenant.cloud_snapshot_key == 1

    def test_tenant_repr(
        self, mock_client: VergeClient, sample_tenant_data: dict[str, Any]
    ) -> None:
        """Test CloudSnapshotTenant string representation."""
        tenant = CloudSnapshotTenant(sample_tenant_data, mock_client.cloud_snapshots.tenants(1))
        assert repr(tenant) == "<CloudSnapshotTenant key=200 name='TestTenant'>"

    def test_tenant_missing_optional_fields(self, mock_client: VergeClient) -> None:
        """Test CloudSnapshotTenant with minimal data."""
        data = {"$key": 1, "name": "MinimalTenant", "cloud_snapshot": 1}
        tenant = CloudSnapshotTenant(data, mock_client.cloud_snapshots.tenants(1))

        assert tenant.key == 1
        assert tenant.name == "MinimalTenant"
        assert tenant.description == ""
        assert tenant.uuid is None
        assert tenant.nodes == 0
        assert tenant.cpu_cores == 0
        assert tenant.ram_mb == 0
        assert tenant.is_snapshot is False
        assert tenant.original_key is None


# =============================================================================
# CloudSnapshot Model Tests
# =============================================================================


class TestCloudSnapshot:
    """Unit tests for CloudSnapshot model."""

    def test_snapshot_properties(
        self, mock_client: VergeClient, sample_snapshot_data: dict[str, Any]
    ) -> None:
        """Test CloudSnapshot property accessors."""
        snapshot = CloudSnapshot(sample_snapshot_data, mock_client.cloud_snapshots)

        assert snapshot.key == 1
        assert snapshot.name == "Test Snapshot"
        assert snapshot.description == "A test cloud snapshot"
        assert snapshot.created_at == datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        assert snapshot.expires_at == datetime(2025, 1, 2, 0, 0, 0, tzinfo=timezone.utc)
        assert snapshot.never_expires is False
        assert snapshot.snapshot_profile_key == 5
        assert snapshot.is_private is False
        assert snapshot.is_remote_sync is False
        assert snapshot.is_immutable is True
        assert snapshot.immutable_status == "locked"
        assert snapshot.is_locked is True
        assert snapshot.immutable_lock_expires_at == datetime(
            2025, 1, 3, 0, 0, 0, tzinfo=timezone.utc
        )
        assert snapshot.status == "normal"
        assert snapshot.status_info == ""

    def test_snapshot_never_expires(self, mock_client: VergeClient) -> None:
        """Test never_expires detection via zero expires value."""
        data = {
            "$key": 1,
            "name": "Never Expires",
            "expires": 0,
        }
        snapshot = CloudSnapshot(data, mock_client.cloud_snapshots)
        assert snapshot.never_expires is True
        assert snapshot.expires_at is None

    def test_snapshot_repr(
        self, mock_client: VergeClient, sample_snapshot_data: dict[str, Any]
    ) -> None:
        """Test CloudSnapshot string representation."""
        snapshot = CloudSnapshot(sample_snapshot_data, mock_client.cloud_snapshots)
        assert repr(snapshot) == "<CloudSnapshot key=1 name='Test Snapshot'>"

    def test_snapshot_immutable_unlocked(self, mock_client: VergeClient) -> None:
        """Test immutable snapshot in unlocked state."""
        data = {
            "$key": 1,
            "name": "Unlocked",
            "immutable": True,
            "immutable_status": "unlocked",
        }
        snapshot = CloudSnapshot(data, mock_client.cloud_snapshots)
        assert snapshot.is_immutable is True
        assert snapshot.immutable_status == "unlocked"
        assert snapshot.is_locked is False

    def test_snapshot_with_vms_and_tenants(
        self,
        mock_client: VergeClient,
        sample_snapshot_data: dict[str, Any],
        sample_vm_data: dict[str, Any],
        sample_tenant_data: dict[str, Any],
    ) -> None:
        """Test CloudSnapshot with pre-loaded VMs and tenants."""
        vm = CloudSnapshotVM(sample_vm_data, mock_client.cloud_snapshots.vms(1))
        tenant = CloudSnapshotTenant(sample_tenant_data, mock_client.cloud_snapshots.tenants(1))

        snapshot = CloudSnapshot(
            sample_snapshot_data,
            mock_client.cloud_snapshots,
            vms=[vm],
            tenants=[tenant],
        )

        assert snapshot.vms is not None
        assert len(snapshot.vms) == 1
        assert snapshot.vms[0].name == "TestVM"

        assert snapshot.tenants is not None
        assert len(snapshot.tenants) == 1
        assert snapshot.tenants[0].name == "TestTenant"

    def test_snapshot_without_vms_and_tenants(
        self, mock_client: VergeClient, sample_snapshot_data: dict[str, Any]
    ) -> None:
        """Test CloudSnapshot without pre-loaded VMs and tenants."""
        snapshot = CloudSnapshot(sample_snapshot_data, mock_client.cloud_snapshots)

        assert snapshot.vms is None
        assert snapshot.tenants is None


# =============================================================================
# CloudSnapshotVMManager Tests
# =============================================================================


class TestCloudSnapshotVMManager:
    """Unit tests for CloudSnapshotVMManager."""

    def test_list_vms(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        sample_vm_data: dict[str, Any],
    ) -> None:
        """Existing membership is returned from the GET, with no find_vms POST."""
        # A 403 queued behind the rows would fire if list() still posted first.
        mock_session.request.side_effect = [
            _resp([sample_vm_data]),
            _error(403, "Permission denied"),
        ]
        mock_session.request.reset_mock()

        vm_manager = mock_client.cloud_snapshots.vms(1)
        vms = vm_manager.list()

        assert len(vms) == 1
        assert vms[0].name == "TestVM"

        # Scope stays the snapshot. is_snapshot is not a default filter.
        call_args = mock_session.request.call_args
        assert call_args.kwargs.get("method") == "GET"
        assert "cloud_snapshot_vms" in call_args.kwargs.get("url", "")
        assert call_args.kwargs.get("params", {}).get("filter", "") == "cloud_snapshot eq 1"
        assert _find_vms_posts(mock_session) == []
        assert len(mock_session.request.call_args_list) == 1

    def test_list_vms_combines_caller_filter(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        sample_vm_data: dict[str, Any],
    ) -> None:
        """A caller filter is ANDed after the snapshot scope."""
        mock_session.request.return_value.json.return_value = [sample_vm_data]

        mock_client.cloud_snapshots.vms(4).list(filter="name eq 'TestVM'")

        filt = mock_session.request.call_args.kwargs.get("params", {}).get("filter", "")
        assert filt == "cloud_snapshot eq 4 and (name eq 'TestVM')"

    def test_list_vms_caller_can_filter_is_snapshot(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        sample_vm_data: dict[str, Any],
    ) -> None:
        """The lab membership query is a caller filter, not the default."""
        mock_session.request.return_value.json.return_value = [sample_vm_data]

        mock_client.cloud_snapshots.vms(4).list(is_snapshot=False)

        filt = mock_session.request.call_args.kwargs.get("params", {}).get("filter", "")
        assert filt == "cloud_snapshot eq 4 and is_snapshot eq false"

    def test_get_vm_by_key(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        sample_vm_data: dict[str, Any],
    ) -> None:
        """Test getting a VM by key."""
        mock_session.request.return_value.json.return_value = sample_vm_data

        vm_manager = mock_client.cloud_snapshots.vms(1)
        vm = vm_manager.get(100)

        assert vm.key == 100
        assert vm.name == "TestVM"

    def test_get_vm_by_key_wrong_snapshot(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        sample_vm_data: dict[str, Any],
    ) -> None:
        """Test getting a VM that belongs to a different snapshot."""
        # VM belongs to snapshot 1, but we're querying snapshot 2
        mock_session.request.return_value.json.return_value = sample_vm_data

        vm_manager = mock_client.cloud_snapshots.vms(2)
        with pytest.raises(NotFoundError, match="does not belong to snapshot"):
            vm_manager.get(100)

    def test_get_vm_by_name(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        sample_vm_data: dict[str, Any],
    ) -> None:
        """Test getting a VM by name."""
        mock_session.request.return_value.json.return_value = [sample_vm_data]

        vm_manager = mock_client.cloud_snapshots.vms(1)
        vm = vm_manager.get(name="TestVM")

        assert vm.name == "TestVM"

    def test_get_vm_not_found(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test getting a VM that doesn't exist."""
        mock_session.request.return_value.json.return_value = []

        vm_manager = mock_client.cloud_snapshots.vms(1)
        with pytest.raises(NotFoundError, match="not found"):
            vm_manager.get(name="NonExistent")

    def test_get_vm_no_params(self, mock_client: VergeClient) -> None:
        """Test get() without key or name raises ValueError."""
        vm_manager = mock_client.cloud_snapshots.vms(1)
        with pytest.raises(ValueError, match="Either key or name must be provided"):
            vm_manager.get()


# =============================================================================
# CloudSnapshotTenantManager Tests
# =============================================================================


class TestCloudSnapshotTenantManager:
    """Unit tests for CloudSnapshotTenantManager."""

    def test_list_tenants(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        sample_tenant_data: dict[str, Any],
    ) -> None:
        """Test listing tenants in a snapshot."""
        mock_session.request.return_value.json.return_value = [sample_tenant_data]

        tenant_manager = mock_client.cloud_snapshots.tenants(1)
        tenants = tenant_manager.list()

        assert len(tenants) == 1
        assert tenants[0].name == "TestTenant"

        # Verify the filter includes cloud_snapshot
        call_args = mock_session.request.call_args
        assert "cloud_snapshot eq 1" in call_args.kwargs.get("params", {}).get("filter", "")

    def test_get_tenant_by_key(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        sample_tenant_data: dict[str, Any],
    ) -> None:
        """Test getting a tenant by key."""
        mock_session.request.return_value.json.return_value = sample_tenant_data

        tenant_manager = mock_client.cloud_snapshots.tenants(1)
        tenant = tenant_manager.get(200)

        assert tenant.key == 200
        assert tenant.name == "TestTenant"

    def test_get_tenant_by_name(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        sample_tenant_data: dict[str, Any],
    ) -> None:
        """Test getting a tenant by name."""
        mock_session.request.return_value.json.return_value = [sample_tenant_data]

        tenant_manager = mock_client.cloud_snapshots.tenants(1)
        tenant = tenant_manager.get(name="TestTenant")

        assert tenant.name == "TestTenant"


# =============================================================================
# CloudSnapshotManager Tests
# =============================================================================


class TestCloudSnapshotManager:
    """Unit tests for CloudSnapshotManager."""

    def test_list_snapshots(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        sample_snapshot_data: dict[str, Any],
    ) -> None:
        """Test listing cloud snapshots."""
        mock_session.request.return_value.json.return_value = [sample_snapshot_data]

        snapshots = mock_client.cloud_snapshots.list()

        assert len(snapshots) == 1
        assert snapshots[0].name == "Test Snapshot"

        # Verify filter excludes expired by default
        call_args = mock_session.request.call_args
        params = call_args.kwargs.get("params", {})
        assert "expires eq 0 or expires gt" in params.get("filter", "")

    def test_list_snapshots_include_expired(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        sample_snapshot_data: dict[str, Any],
    ) -> None:
        """Test listing snapshots with include_expired=True."""
        mock_session.request.return_value.json.return_value = [sample_snapshot_data]

        snapshots = mock_client.cloud_snapshots.list(include_expired=True)

        assert len(snapshots) == 1

        # Verify no expiration filter
        call_args = mock_session.request.call_args
        params = call_args.kwargs.get("params", {})
        assert "expires eq 0" not in params.get("filter", "")

    def test_get_snapshot_by_key(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        sample_snapshot_data: dict[str, Any],
    ) -> None:
        """Test getting a snapshot by key."""
        mock_session.request.return_value.json.return_value = sample_snapshot_data

        snapshot = mock_client.cloud_snapshots.get(1)

        assert snapshot.key == 1
        assert snapshot.name == "Test Snapshot"

    def test_get_snapshot_by_name(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        sample_snapshot_data: dict[str, Any],
    ) -> None:
        """Test getting a snapshot by name."""
        mock_session.request.return_value.json.return_value = [sample_snapshot_data]

        snapshot = mock_client.cloud_snapshots.get(name="Test Snapshot")

        assert snapshot.name == "Test Snapshot"

    def test_get_snapshot_not_found(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test getting a snapshot that doesn't exist."""
        mock_session.request.return_value.json.return_value = []

        with pytest.raises(NotFoundError, match="not found"):
            mock_client.cloud_snapshots.get(name="NonExistent")

    def test_get_snapshot_no_params(self, mock_client: VergeClient) -> None:
        """Test get() without key or name raises ValueError."""
        with pytest.raises(ValueError, match="Either key or name must be provided"):
            mock_client.cloud_snapshots.get()

    @patch("pyvergeos.resources.cloud_snapshots.time")
    def test_create_snapshot_default(
        self, mock_time: MagicMock, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test creating a snapshot with defaults."""
        mock_time.time.return_value = 1735689600.0
        created_data = {
            "$key": 5,
            "name": "Snapshot_20250101_1234",
            "created": 1735689600,
            "expires": 1735948800,  # 3 days later
        }
        mock_session.request.return_value.json.return_value = created_data

        snapshot = mock_client.cloud_snapshots.create(name="Test Create")

        assert snapshot.key == 5

        # Verify POST call
        found_create = False
        for call in mock_session.request.call_args_list:
            body = call.kwargs.get("json", {})
            if body and body.get("name") == "Test Create":
                found_create = True
                assert body.get("expires") == 1735689600 + 259200
                assert body.get("expires_type") == "date"
                assert "retention" not in body
                break
        assert found_create, "Create call not found"

    @patch("pyvergeos.resources.cloud_snapshots.time")
    def test_create_snapshot_custom_retention(
        self, mock_time: MagicMock, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test creating a snapshot with custom retention_seconds."""
        mock_time.time.return_value = 1735689600.0
        created_data = {"$key": 6, "name": "Custom Retention"}
        mock_session.request.return_value.json.return_value = created_data

        mock_client.cloud_snapshots.create(name="Custom Retention", retention_seconds=3600)

        found = False
        for call in mock_session.request.call_args_list:
            body = call.kwargs.get("json", {})
            if body and body.get("name") == "Custom Retention":
                found = True
                assert body.get("expires") == 1735689600 + 3600
                assert body.get("expires_type") == "date"
                assert "retention" not in body
                break
        assert found, "Create call not found"

    @patch("pyvergeos.resources.cloud_snapshots.time")
    def test_create_snapshot_timedelta_retention(
        self, mock_time: MagicMock, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test creating a snapshot with timedelta retention."""
        mock_time.time.return_value = 1735689600.0
        created_data = {"$key": 7, "name": "Timedelta Retention"}
        mock_session.request.return_value.json.return_value = created_data

        mock_client.cloud_snapshots.create(name="Timedelta Retention", retention=timedelta(hours=2))

        found = False
        for call in mock_session.request.call_args_list:
            body = call.kwargs.get("json", {})
            if body and body.get("name") == "Timedelta Retention":
                found = True
                assert body.get("expires") == 1735689600 + 7200
                assert body.get("expires_type") == "date"
                assert "retention" not in body
                break
        assert found, "Create call not found"

    def test_create_snapshot_never_expire(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test creating a snapshot that never expires."""
        created_data = {"$key": 8, "name": "Never Expire", "expires": 0}
        mock_session.request.return_value.json.return_value = created_data

        mock_client.cloud_snapshots.create(name="Never Expire", never_expire=True)

        found = False
        for call in mock_session.request.call_args_list:
            body = call.kwargs.get("json", {})
            if body and body.get("name") == "Never Expire":
                found = True
                assert body.get("expires") == 0
                assert body.get("expires_type") == "never"
                assert "retention" not in body
                break
        assert found, "Create call not found"

    def test_create_snapshot_immutable(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test creating an immutable snapshot."""
        created_data = {"$key": 9, "name": "Immutable", "immutable": True}
        mock_session.request.return_value.json.return_value = created_data

        mock_client.cloud_snapshots.create(name="Immutable", immutable=True)

        found = False
        for call in mock_session.request.call_args_list:
            body = call.kwargs.get("json", {})
            if body and body.get("name") == "Immutable":
                found = True
                assert body.get("immutable") is True
                break
        assert found, "Create call not found"

    def test_create_snapshot_private(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test creating a private snapshot."""
        created_data = {"$key": 10, "name": "Private", "private": True}
        mock_session.request.return_value.json.return_value = created_data

        mock_client.cloud_snapshots.create(name="Private", private=True)

        found = False
        for call in mock_session.request.call_args_list:
            body = call.kwargs.get("json", {})
            if body and body.get("name") == "Private":
                found = True
                assert body.get("private") is True
                break
        assert found, "Create call not found"

    def test_delete_snapshot(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test deleting a snapshot."""
        mock_session.request.return_value.status_code = 204
        mock_session.request.return_value.text = ""

        mock_client.cloud_snapshots.delete(1)

        # Verify DELETE call
        found_delete = False
        for call in mock_session.request.call_args_list:
            url = call.kwargs.get("url", "")
            method = call.kwargs.get("method", "")
            if method == "DELETE" and "cloud_snapshots/1" in url:
                found_delete = True
                break
        assert found_delete, "DELETE call not found"

    def test_vm_sub_manager_cached(self, mock_client: VergeClient) -> None:
        """Test that VM sub-manager is cached."""
        vm_mgr1 = mock_client.cloud_snapshots.vms(1)
        vm_mgr2 = mock_client.cloud_snapshots.vms(1)
        assert vm_mgr1 is vm_mgr2

    def test_tenant_sub_manager_cached(self, mock_client: VergeClient) -> None:
        """Test that tenant sub-manager is cached."""
        tenant_mgr1 = mock_client.cloud_snapshots.tenants(1)
        tenant_mgr2 = mock_client.cloud_snapshots.tenants(1)
        assert tenant_mgr1 is tenant_mgr2

    def test_restore_vm(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        sample_vm_data: dict[str, Any],
    ) -> None:
        """Test restoring a VM from a snapshot."""
        # Return VMs list, then action result
        mock_session.request.return_value.json.return_value = [sample_vm_data]

        # Call restore with vm_key to avoid the lookup
        result = mock_client.cloud_snapshots.restore_vm(
            snapshot_key=1, vm_key=100, new_name="TestVM-Restored"
        )

        assert result["status"] == "initiated"
        assert result["snapshot_key"] == 1
        assert result["vm_key"] == 100

    def test_find_vms_posts_action(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """find_vms posts the action body from issue #201 and returns an object."""
        mock_session.request.return_value.json.return_value = {"response": "ok"}

        result = mock_client.cloud_snapshots.find_vms(7)

        assert result == {"response": "ok"}
        call = mock_session.request.call_args
        assert call.kwargs.get("method") == "POST"
        assert str(call.kwargs.get("url", "")).endswith("cloud_snapshot_actions")
        assert call.kwargs.get("json") == {"action": "find_vms", "cloud_snapshot": 7}

    def test_find_vms_ignores_non_object_body(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """A list or empty action body is not treated as fields we know."""
        mock_session.request.return_value.text = "[]"
        mock_session.request.return_value.json.return_value = [{"$key": 1}]
        assert mock_client.cloud_snapshots.find_vms(3) is None

        mock_session.request.return_value.text = ""
        assert mock_client.cloud_snapshots.find_vms(3) is None

    def test_include_vms_posts_find_vms_only_when_membership_empty(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        sample_snapshot_data: dict[str, Any],
        sample_vm_data: dict[str, Any],
    ) -> None:
        """include_vms posts find_vms only after an empty membership read."""
        mock_session.request.side_effect = [
            _resp([sample_snapshot_data]),
            _resp([]),
            _resp({}),
            _resp([sample_vm_data]),
        ]
        mock_session.request.reset_mock()

        snapshots = mock_client.cloud_snapshots.list(include_vms=True)

        assert snapshots[0].vms is not None
        assert snapshots[0].vms[0].name == "TestVM"
        cloud_calls = [
            call
            for call in mock_session.request.call_args_list
            if "cloud_snapshot" in str(call.kwargs.get("url", ""))
        ]
        assert cloud_calls[0].kwargs["method"] == "GET"
        assert "cloud_snapshots" in cloud_calls[0].kwargs["url"]
        assert cloud_calls[1].kwargs["method"] == "GET"
        assert "cloud_snapshot_vms" in cloud_calls[1].kwargs["url"]
        assert cloud_calls[2].kwargs["method"] == "POST"
        assert cloud_calls[2].kwargs["json"] == {"action": "find_vms", "cloud_snapshot": 1}
        assert cloud_calls[3].kwargs["method"] == "GET"
        assert "cloud_snapshot_vms" in cloud_calls[3].kwargs["url"]

    def test_restore_vm_missing_params(self, mock_client: VergeClient) -> None:
        """Test restore_vm with missing parameters."""
        with pytest.raises(ValueError, match="snapshot_key or snapshot_name"):
            mock_client.cloud_snapshots.restore_vm(vm_name="TestVM")

        with pytest.raises(ValueError, match="vm_key or vm_name"):
            mock_client.cloud_snapshots.restore_vm(snapshot_key=1)

    def test_restore_tenant(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        sample_tenant_data: dict[str, Any],
    ) -> None:
        """Test restoring a tenant from a snapshot."""
        mock_session.request.return_value.json.return_value = [sample_tenant_data]

        # Call restore with tenant_key to avoid the lookup
        result = mock_client.cloud_snapshots.restore_tenant(
            snapshot_key=1, tenant_key=200, new_name="TestTenant-DR"
        )

        assert result["status"] == "initiated"
        assert result["snapshot_key"] == 1
        assert result["tenant_key"] == 200

    def test_restore_tenant_missing_params(self, mock_client: VergeClient) -> None:
        """Test restore_tenant with missing parameters."""
        with pytest.raises(ValueError, match="snapshot_key or snapshot_name"):
            mock_client.cloud_snapshots.restore_tenant(tenant_name="TestTenant")

        with pytest.raises(ValueError, match="tenant_key or tenant_name"):
            mock_client.cloud_snapshots.restore_tenant(snapshot_key=1)


# =============================================================================
# Integration Tests (Object Method Tests)
# =============================================================================


class TestCloudSnapshotObjectMethods:
    """Test object methods on CloudSnapshot."""

    def test_get_vms_method(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        sample_snapshot_data: dict[str, Any],
        sample_vm_data: dict[str, Any],
    ) -> None:
        """get_vms() returns existing rows and does not post find_vms."""
        mock_session.request.side_effect = [
            _resp([sample_vm_data]),
            _error(403, "Permission denied"),
        ]
        mock_session.request.reset_mock()

        snapshot = CloudSnapshot(sample_snapshot_data, mock_client.cloud_snapshots)
        vms = snapshot.get_vms()

        assert len(vms) == 1
        assert vms[0].name == "TestVM"
        assert _find_vms_posts(mock_session) == []

    def test_find_vms_method(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        sample_snapshot_data: dict[str, Any],
    ) -> None:
        """CloudSnapshot.find_vms() posts this snapshot's key."""
        mock_session.request.return_value.json.return_value = {"response": "ok"}

        snapshot = CloudSnapshot(sample_snapshot_data, mock_client.cloud_snapshots)
        result = snapshot.find_vms()

        assert result == {"response": "ok"}
        assert mock_session.request.call_args.kwargs.get("json") == {
            "action": "find_vms",
            "cloud_snapshot": 1,
        }

    def test_get_tenants_method(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        sample_snapshot_data: dict[str, Any],
        sample_tenant_data: dict[str, Any],
    ) -> None:
        """Test CloudSnapshot.get_tenants() method."""
        mock_session.request.return_value.json.return_value = [sample_tenant_data]

        snapshot = CloudSnapshot(sample_snapshot_data, mock_client.cloud_snapshots)
        tenants = snapshot.get_tenants()

        assert len(tenants) == 1
        assert tenants[0].name == "TestTenant"

    def test_delete_method(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        sample_snapshot_data: dict[str, Any],
    ) -> None:
        """Test CloudSnapshot.delete() method."""
        mock_session.request.return_value.status_code = 204
        mock_session.request.return_value.text = ""

        # Not immutable
        data = {**sample_snapshot_data, "immutable": False}
        snapshot = CloudSnapshot(data, mock_client.cloud_snapshots)

        snapshot.delete()

        # Verify DELETE was called
        found_delete = False
        for call in mock_session.request.call_args_list:
            method = call.kwargs.get("method", "")
            url = call.kwargs.get("url", "")
            if method == "DELETE" and "cloud_snapshots" in url:
                found_delete = True
                break
        assert found_delete, "DELETE call not found"

    def test_delete_immutable_locked(
        self,
        mock_client: VergeClient,
        sample_snapshot_data: dict[str, Any],
    ) -> None:
        """Test that delete() raises error for locked immutable snapshot."""
        snapshot = CloudSnapshot(sample_snapshot_data, mock_client.cloud_snapshots)

        # sample_snapshot_data has immutable=True and immutable_status=locked
        with pytest.raises(ValidationError, match="immutable.*locked"):
            snapshot.delete()


# =============================================================================
# Partial (tag-scoped) snapshots — issue #129
# =============================================================================


def _post_body(mock_session: MagicMock, name: str) -> dict[str, Any]:
    """Return the POST body whose 'name' matches, from recorded calls."""
    for call in mock_session.request.call_args_list:
        body = call.kwargs.get("json", {})
        if body and body.get("name") == name:
            return body
    raise AssertionError(f"no create POST found for {name!r}")


class TestPartialSnapshotCreate:
    """create() must express tag-scoped partial snapshots (issue #129)."""

    @patch("pyvergeos.resources.cloud_snapshots.time")
    def test_include_tags_by_key(
        self, mock_time: MagicMock, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        mock_time.time.return_value = 1735689600.0
        mock_session.request.return_value.json.return_value = {"$key": 5, "name": "inc"}
        mock_client.cloud_snapshots.create(name="inc", include_tags=[3])
        body = _post_body(mock_session, "inc")
        assert body["type"] == "partial_include"
        assert body["partial_tags"] == "3"

    @patch("pyvergeos.resources.cloud_snapshots.time")
    def test_exclude_tags_multiple_keys(
        self, mock_time: MagicMock, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        mock_time.time.return_value = 1735689600.0
        mock_session.request.return_value.json.return_value = {"$key": 6, "name": "exc"}
        mock_client.cloud_snapshots.create(name="exc", exclude_tags=[1, 2])
        body = _post_body(mock_session, "exc")
        assert body["type"] == "partial_exclude"
        assert body["partial_tags"] == "1,2"

    @patch("pyvergeos.resources.cloud_snapshots.time")
    def test_single_tag_not_iterated_as_string(
        self, mock_time: MagicMock, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """A single numeric-string tag must not be split into characters."""
        mock_time.time.return_value = 1735689600.0
        mock_session.request.return_value.json.return_value = {"$key": 7, "name": "one"}
        mock_client.cloud_snapshots.create(name="one", include_tags="3")
        assert _post_body(mock_session, "one")["partial_tags"] == "3"

    @patch("pyvergeos.resources.cloud_snapshots.time")
    def test_quiesce_tags_included(
        self, mock_time: MagicMock, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        mock_time.time.return_value = 1735689600.0
        mock_session.request.return_value.json.return_value = {"$key": 8, "name": "q"}
        mock_client.cloud_snapshots.create(name="q", include_tags=[3], quiesce_tags=[3])
        body = _post_body(mock_session, "q")
        assert body["type"] == "partial_include"
        assert body["quiesce_tags"] == "3"

    @patch("pyvergeos.resources.cloud_snapshots.time")
    def test_full_snapshot_sends_no_type(
        self, mock_time: MagicMock, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """A non-partial create is unchanged: no type/partial_tags (backward compat)."""
        mock_time.time.return_value = 1735689600.0
        mock_session.request.return_value.json.return_value = {"$key": 9, "name": "full"}
        mock_client.cloud_snapshots.create(name="full")
        body = _post_body(mock_session, "full")
        assert "type" not in body
        assert "partial_tags" not in body

    def test_include_and_exclude_are_mutually_exclusive(self, mock_client: VergeClient) -> None:
        with pytest.raises(ValueError, match="mutually exclusive"):
            mock_client.cloud_snapshots.create(name="bad", include_tags=[1], exclude_tags=[2])

    def test_quiesce_requires_partial(self, mock_client: VergeClient) -> None:
        with pytest.raises(ValueError, match="only to a partial"):
            mock_client.cloud_snapshots.create(name="bad", quiesce_tags=[1])


class TestTagResolution:
    """_resolve_tag_keys converts names/objects to the key string the API wants."""

    def _mgr(self) -> Any:
        from pyvergeos.resources.cloud_snapshots import CloudSnapshotManager

        client = MagicMock()
        client._request = MagicMock()
        return CloudSnapshotManager(client), client

    def test_none_is_none(self) -> None:
        mgr, _ = self._mgr()
        assert mgr._resolve_tag_keys(None) is None

    def test_int_keys(self) -> None:
        mgr, _ = self._mgr()
        assert mgr._resolve_tag_keys([1, 2, 3]) == "1,2,3"

    def test_resource_object_uses_key(self) -> None:
        mgr, _ = self._mgr()
        tag = CloudSnapshot({"$key": 4}, MagicMock())
        assert mgr._resolve_tag_keys([tag]) == "4"

    def test_name_resolved_to_key(self) -> None:
        mgr, client = self._mgr()
        client._request.return_value = [{"$key": 3}]
        assert mgr._resolve_tag_keys(["DB"]) == "3"
        assert "name eq" in client._request.call_args.kwargs["params"]["filter"]

    def test_ambiguous_name_raises(self) -> None:
        mgr, client = self._mgr()
        client._request.return_value = [{"$key": 3}, {"$key": 9}]
        with pytest.raises(ValueError, match="ambiguous"):
            mgr._resolve_tag_keys(["gold"])

    def test_missing_name_raises(self) -> None:
        mgr, client = self._mgr()
        client._request.return_value = []
        with pytest.raises(ValueError, match="no tag named"):
            mgr._resolve_tag_keys(["nope"])

    def test_bool_rejected(self) -> None:
        mgr, _ = self._mgr()
        with pytest.raises(TypeError):
            mgr._resolve_tag_keys([True])


class TestPartialSnapshotEdgeCases:
    """Cover the new error branches added for #129."""

    def test_tag_object_without_key_raises(self) -> None:
        from pyvergeos.resources.cloud_snapshots import CloudSnapshotManager

        mgr = CloudSnapshotManager(MagicMock())
        keyless = CloudSnapshot({}, MagicMock())  # a ResourceObject with no $key
        with pytest.raises(ValueError, match="no \\$key"):
            mgr._resolve_tag_keys([keyless])

    def test_empty_include_tags_raises(self, mock_client: VergeClient) -> None:
        with pytest.raises(ValueError, match="include_tags must name at least one"):
            mock_client.cloud_snapshots.create(name="x", include_tags=[])

    def test_empty_exclude_tags_raises(self, mock_client: VergeClient) -> None:
        with pytest.raises(ValueError, match="exclude_tags must name at least one"):
            mock_client.cloud_snapshots.create(name="x", exclude_tags=[])

    @patch("pyvergeos.resources.cloud_snapshots.time")
    def test_empty_quiesce_tags_is_a_noop_not_an_error(
        self, mock_time: MagicMock, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """quiesce_tags=[] alongside a valid partial adds no quiesce, does not raise."""
        mock_time.time.return_value = 1735689600.0
        mock_session.request.return_value.json.return_value = {"$key": 10, "name": "nq"}
        mock_client.cloud_snapshots.create(name="nq", include_tags=[3], quiesce_tags=[])
        body = _post_body(mock_session, "nq")
        assert body["type"] == "partial_include"
        assert "quiesce_tags" not in body


def _resp(payload: Any) -> MagicMock:
    """Build a mock HTTP response the connection layer will accept."""
    r = MagicMock()
    r.status_code = 200
    r.text = "{}"
    r.json.return_value = payload
    return r


def _error(status: int, message: str) -> MagicMock:
    """Build an error response ``_handle_response`` will turn into an APIError."""
    response = MagicMock()
    response.status_code = status
    response.text = message
    response.json.return_value = {"err": message}
    return response


def _find_vms_posts(mock_session: MagicMock) -> list[Any]:
    """POSTs of the ``find_vms`` action."""
    return [
        call
        for call in mock_session.request.call_args_list
        if call.kwargs.get("method") == "POST"
        and str(call.kwargs.get("url", "")).endswith("cloud_snapshot_actions")
        and (call.kwargs.get("json") or {}).get("action") == "find_vms"
    ]


def _field_tokens(fields: Any) -> list[str]:
    return [part.strip() for part in str(fields or "").split(",") if part.strip()]


class TestCreateWait:
    """Cover the wait=True completion path fixed for issue #133.

    Snapshot creation is not backed by a task row (the POST response carries
    no ``task`` key), so ``wait=True`` must poll the snapshot row's ``status``
    until it leaves ``building``. Before the fix the wait branch was dead and
    ``wait=True`` returned immediately with a stale status.
    """

    @patch("pyvergeos.resources.cloud_snapshots.time")
    def test_wait_true_polls_until_status_leaves_building(
        self, mock_time: MagicMock, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        # Constant clock keeps us under the timeout for the whole poll loop.
        mock_time.time.return_value = 1000.0
        post = _resp(
            {
                "$key": 5,
                "$row": 5,
                "dbpath": "cloud_snapshots/5",
                "location": "/v4/cloud_snapshots/5",
            }
        )
        building = _resp({"$key": 5, "name": "wait-me", "status": "building"})
        normal = _resp({"$key": 5, "name": "wait-me", "status": "normal"})
        # POST, then three GET polls: building, building, normal.
        mock_session.request.reset_mock()
        mock_session.request.side_effect = [post, building, building, normal]

        snapshot = mock_client.cloud_snapshots.create(name="wait-me", wait=True)

        # The returned object reflects the real, post-wait status -- not the
        # stale value the POST response would have implied.
        assert snapshot.status == "normal"
        # It actually blocked: POST + three status polls.
        assert mock_session.request.call_count == 4
        # And slept between polls, but not after the terminal one.
        assert mock_time.sleep.call_count == 2
        gets = [
            call.kwargs
            for call in mock_session.request.call_args_list
            if call.kwargs.get("method") == "GET"
        ]
        assert gets
        assert all("all" in _field_tokens(call["params"].get("fields")) for call in gets)

    @patch("pyvergeos.resources.cloud_snapshots.time")
    def test_wait_true_raises_on_timeout_still_building(
        self, mock_time: MagicMock, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        # never_expire avoids a time.time() call in create(), so the only
        # clock reads are start + one timeout check inside the wait loop.
        mock_time.time.side_effect = [1000.0, 2000.0]
        post = _resp({"$key": 6, "location": "/v4/cloud_snapshots/6"})
        building = _resp({"$key": 6, "name": "stuck", "status": "building"})
        mock_session.request.reset_mock()
        mock_session.request.side_effect = [post, building]

        with pytest.raises(VergeTimeoutError, match="did not finish building within 10 seconds"):
            mock_client.cloud_snapshots.create(
                name="stuck", never_expire=True, wait=True, wait_timeout=10
            )

    @patch("pyvergeos.resources.cloud_snapshots.time")
    def test_wait_false_does_not_poll(
        self, mock_time: MagicMock, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        mock_time.time.return_value = 1000.0
        post = _resp({"$key": 7, "location": "/v4/cloud_snapshots/7"})
        row = _resp({"$key": 7, "name": "nowait", "status": "building"})
        mock_session.request.reset_mock()
        mock_session.request.side_effect = [post, row]

        snapshot = mock_client.cloud_snapshots.create(name="nowait", wait=False)

        # Default path: POST plus a single get(); no polling, never sleeps.
        assert snapshot.key == 7
        assert mock_session.request.call_count == 2
        mock_time.sleep.assert_not_called()

    @patch("pyvergeos.resources.cloud_snapshots.time")
    def test_wait_returns_unprojected_when_no_key(
        self, mock_time: MagicMock, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        # A response with no $key cannot be fetched or waited on; create()
        # hands back the raw POST body without polling.
        mock_time.time.return_value = 1000.0
        mock_session.request.reset_mock()
        mock_session.request.side_effect = [_resp({"name": "keyless"})]

        snapshot = mock_client.cloud_snapshots.create(name="keyless", wait=True)

        assert snapshot.get("name") == "keyless"
        assert mock_session.request.call_count == 1
        mock_time.sleep.assert_not_called()


class TestCreateWaitPreBuildingRace:
    """Guard the pre-``building`` window (issue #133 skeptical retest).

    Right after the POST the snapshot row's ``status`` can be absent or null
    before it flips to ``building``. The ``status`` accessor masks a missing
    field as ``"normal"``, so a naive ``!= "building"`` check on the accessor
    would treat that first poll as settled and return immediately -- exactly
    the no-op the fix removes. The wait must poll the raw field and keep
    waiting while the status is missing/blank.
    """

    @patch("pyvergeos.resources.cloud_snapshots.time")
    def test_wait_keeps_polling_through_absent_then_null_status(
        self, mock_time: MagicMock, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        mock_time.time.return_value = 1000.0
        post = _resp({"$key": 5, "location": "/v4/cloud_snapshots/5"})
        # Timeline: field absent -> null -> building -> normal.
        absent = _resp({"$key": 5, "name": "race"})
        null_status = _resp({"$key": 5, "name": "race", "status": None})
        building = _resp({"$key": 5, "name": "race", "status": "building"})
        normal = _resp({"$key": 5, "name": "race", "status": "normal"})
        mock_session.request.reset_mock()
        mock_session.request.side_effect = [post, absent, null_status, building, normal]

        snapshot = mock_client.cloud_snapshots.create(name="race", wait=True)

        assert snapshot.status == "normal"
        # POST + four polls: it did not shortcut on the absent/null/building rows.
        assert mock_session.request.call_count == 5
        assert mock_time.sleep.call_count == 3

    @patch("pyvergeos.resources.cloud_snapshots.time")
    def test_absent_status_accessor_would_have_shortcut_but_raw_check_does_not(
        self, mock_time: MagicMock, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        # Regression pin: a single absent-status poll then normal. The accessor
        # would read the absent row as "normal" and stop after one poll; the raw
        # check must wait for the real terminal row instead.
        mock_time.time.return_value = 1000.0
        post = _resp({"$key": 6, "location": "/v4/cloud_snapshots/6"})
        absent = _resp({"$key": 6, "name": "pin"})
        normal = _resp({"$key": 6, "name": "pin", "status": "normal"})
        mock_session.request.reset_mock()
        mock_session.request.side_effect = [post, absent, normal]

        snapshot = mock_client.cloud_snapshots.create(name="pin", wait=True)

        assert snapshot.status == "normal"
        assert snapshot.get("status") == "normal"  # the real terminal row
        assert mock_session.request.call_count == 3  # POST + absent + normal
        assert mock_time.sleep.call_count == 1


def _dispatch(payloads: dict[str, list[MagicMock]], **kwargs: Any) -> MagicMock:
    """Return a scripted body for ``fields=all``, and a settled row otherwise.

    The settled row is what ``get()`` returned on the lab while
    ``fields=all`` of the same snapshot still said ``building``.
    """
    if kwargs.get("method") == "POST":
        return payloads["post"].pop(0)
    fields = (kwargs.get("params") or {}).get("fields")
    if "all" in _field_tokens(fields):
        return payloads["all"].pop(0)
    return _resp({"$key": 5, "name": "early", "status": "normal"})


class TestCreateWaitFieldsAll:
    """``wait=True`` must follow the read that still says ``building`` (#202)."""

    @patch("pyvergeos.resources.cloud_snapshots.time")
    def test_default_get_looking_settled_does_not_finish_the_wait(
        self, mock_time: MagicMock, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        mock_time.time.return_value = 1000.0
        payloads: dict[str, list[MagicMock]] = {
            "post": [_resp({"$key": 5, "location": "/v4/cloud_snapshots/5"})],
            "all": [
                _resp({"$key": 5, "name": "early", "status": "building"}),
                _resp({"$key": 5, "name": "early", "status": "normal"}),
            ],
        }
        mock_session.request.reset_mock()
        mock_session.request.side_effect = lambda **kwargs: _dispatch(payloads, **kwargs)

        snapshot = mock_client.cloud_snapshots.create(name="early", never_expire=True, wait=True)

        assert snapshot.get("status") == "normal"
        assert payloads["all"] == []
        assert mock_time.sleep.call_count == 1
        gets = [
            call.kwargs
            for call in mock_session.request.call_args_list
            if call.kwargs.get("method") == "GET"
        ]
        assert len(gets) == 2
        assert all("all" in _field_tokens(call["params"].get("fields")) for call in gets)

    @patch("pyvergeos.resources.cloud_snapshots.time")
    def test_timeout_uses_fields_all_not_the_settled_default_read(
        self, mock_time: MagicMock, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        # start, then the timeout check on the first fields=all poll.
        mock_time.time.side_effect = [1000.0, 2000.0]
        payloads: dict[str, list[MagicMock]] = {
            "post": [_resp({"$key": 6, "location": "/v4/cloud_snapshots/6"})],
            "all": [_resp({"$key": 6, "name": "stuck", "status": "building"})],
        }
        mock_session.request.reset_mock()
        mock_session.request.side_effect = lambda **kwargs: _dispatch(payloads, **kwargs)

        with pytest.raises(VergeTimeoutError, match="did not finish building within 10 seconds"):
            mock_client.cloud_snapshots.create(
                name="stuck", never_expire=True, wait=True, wait_timeout=10
            )

        mock_time.sleep.assert_not_called()


class TestCreateRetryIfBusy:
    """Opt-in retry for 'System snapshot is still building' (#202)."""

    @patch("pyvergeos.resources.cloud_snapshots.time")
    def test_retries_with_bounded_backoff_then_creates(
        self, mock_time: MagicMock, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        mock_time.time.return_value = 1000.0
        busy = _error(422, "System snapshot is still building")
        created = _resp({"$key": 11, "name": "retry-me"})
        mock_session.request.reset_mock()
        mock_session.request.side_effect = [busy, busy, busy, busy, busy, busy, created, created]

        snapshot = mock_client.cloud_snapshots.create(
            name="retry-me", never_expire=True, retry_if_busy=True
        )

        assert snapshot.key == 11
        assert [call.args[0] for call in mock_time.sleep.call_args_list] == [
            2,
            4,
            8,
            16,
            30,
            30,
        ]
        posts = [
            call.kwargs
            for call in mock_session.request.call_args_list
            if call.kwargs.get("method") == "POST"
        ]
        assert len(posts) == 7

    @patch("pyvergeos.resources.cloud_snapshots.time")
    def test_other_validation_error_is_not_retried(
        self, mock_time: MagicMock, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        mock_time.time.return_value = 1000.0
        mock_session.request.reset_mock()
        mock_session.request.side_effect = [
            _error(422, "System snapshot is still building"),
            _error(422, "Name already exists"),
        ]

        with pytest.raises(ValidationError, match="Name already exists"):
            mock_client.cloud_snapshots.create(name="taken", never_expire=True, retry_if_busy=True)

        assert mock_time.sleep.call_count == 1
        assert mock_session.request.call_count == 2

    @patch("pyvergeos.resources.cloud_snapshots.time")
    def test_conflict_with_the_same_text_is_not_retried(
        self, mock_time: MagicMock, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        mock_time.time.return_value = 1000.0
        mock_session.request.reset_mock()
        mock_session.request.side_effect = [
            _error(409, "System snapshot is still building"),
        ]

        with pytest.raises(ConflictError, match="still building"):
            mock_client.cloud_snapshots.create(
                name="conflict", never_expire=True, retry_if_busy=True
            )

        mock_time.sleep.assert_not_called()
        assert mock_session.request.call_count == 1

    @patch("pyvergeos.resources.cloud_snapshots.time")
    def test_busy_error_is_immediate_without_the_flag(
        self, mock_time: MagicMock, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        mock_time.time.return_value = 1000.0
        mock_session.request.reset_mock()
        mock_session.request.side_effect = [
            _error(422, "System snapshot is still building"),
        ]

        with pytest.raises(ValidationError, match="still building"):
            mock_client.cloud_snapshots.create(name="busy", never_expire=True)

        mock_time.sleep.assert_not_called()
        assert mock_session.request.call_count == 1

    @patch("pyvergeos.resources.cloud_snapshots.time")
    def test_retry_budget_raises_timeout(
        self, mock_time: MagicMock, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        mock_time.time.side_effect = [1000.0, 1010.0]
        mock_session.request.reset_mock()
        mock_session.request.side_effect = [
            _error(422, "System snapshot is still building"),
        ]

        with pytest.raises(VergeTimeoutError, match="still building after 10 seconds"):
            mock_client.cloud_snapshots.create(
                name="late",
                never_expire=True,
                retry_if_busy=True,
                wait_timeout=10,
            )

        mock_time.sleep.assert_not_called()


# =============================================================================
# Read-only cloud snapshot VM membership — issue #206
# =============================================================================


class TestCloudSnapshotVMReadOnly:
    """Membership reads must work without permission to post find_vms."""

    def test_permission_denied_classifier(self) -> None:
        """403 and the Permission denied message are the tolerated refusal."""
        from pyvergeos.resources.cloud_snapshots import _find_vms_permission_denied

        assert _find_vms_permission_denied(AuthenticationError("Permission denied"))
        assert _find_vms_permission_denied(AuthenticationError("nope", status_code=403))
        assert not _find_vms_permission_denied(
            AuthenticationError("Permission denied", status_code=401)
        )
        assert not _find_vms_permission_denied(AuthenticationError("session expired"))

    def test_empty_membership_posts_find_vms_then_rereads(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        sample_vm_data: dict[str, Any],
    ) -> None:
        """No rows yet: find_vms runs, then the membership GET is repeated."""
        mock_session.request.side_effect = [
            _resp([]),
            _resp({"response": "ok"}),
            _resp([sample_vm_data]),
        ]
        mock_session.request.reset_mock()

        vms = mock_client.cloud_snapshots.vms(1).list()

        assert [vm.name for vm in vms] == ["TestVM"]
        posts = _find_vms_posts(mock_session)
        assert len(posts) == 1
        assert posts[0].kwargs["json"] == {"action": "find_vms", "cloud_snapshot": 1}
        calls = mock_session.request.call_args_list
        assert calls[0].kwargs["method"] == "GET"
        assert calls[1].kwargs["method"] == "POST"
        assert calls[2].kwargs["method"] == "GET"
        assert "cloud_snapshot_vms" in calls[0].kwargs["url"]
        assert "cloud_snapshot_vms" in calls[2].kwargs["url"]

    def test_permission_denied_on_empty_membership_returns_rows(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
    ) -> None:
        """HTTP 403 on find_vms falls back to the membership rows already read."""
        mock_session.request.side_effect = [
            _resp([]),
            _error(403, "Permission denied"),
        ]
        mock_session.request.reset_mock()

        vms = mock_client.cloud_snapshots.vms(1).list()

        assert vms == []
        assert len(_find_vms_posts(mock_session)) == 1
        # The refused POST is not followed by another read.
        assert len(mock_session.request.call_args_list) == 2

    def test_unauthorized_find_vms_is_not_an_empty_list(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
    ) -> None:
        """HTTP 401 on find_vms is an authentication failure, not zero VMs."""
        mock_session.request.side_effect = [
            _resp([]),
            _error(401, "Permission denied"),
        ]

        with pytest.raises(AuthenticationError, match="Permission denied"):
            mock_client.cloud_snapshots.vms(1).list()

    def test_find_vms_server_error_is_raised(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
    ) -> None:
        """A failed find_vms is not reported as an empty membership."""
        mock_session.request.side_effect = [
            _resp([]),
            _error(500, "find failed"),
        ]

        with pytest.raises(APIError, match="find failed"):
            mock_client.cloud_snapshots.vms(1).list()

    def test_filtered_miss_does_not_post_when_rows_exist(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        sample_vm_data: dict[str, Any],
    ) -> None:
        """A filter that matches nothing is not an empty membership."""
        mock_session.request.side_effect = [
            _resp([]),
            _resp([sample_vm_data]),
            _error(403, "Permission denied"),
        ]
        mock_session.request.reset_mock()

        vms = mock_client.cloud_snapshots.vms(4).list(is_snapshot=False)

        assert vms == []
        assert _find_vms_posts(mock_session) == []
        gets = [
            call
            for call in mock_session.request.call_args_list
            if call.kwargs.get("method") == "GET"
        ]
        assert len(gets) == 2
        assert gets[0].kwargs["params"]["filter"] == (
            "cloud_snapshot eq 4 and is_snapshot eq false"
        )
        assert gets[1].kwargs["params"]["filter"] == "cloud_snapshot eq 4"
        assert gets[1].kwargs["params"]["limit"] == 1

    def test_list_include_vms_skips_find_vms_when_rows_exist(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        sample_snapshot_data: dict[str, Any],
        sample_vm_data: dict[str, Any],
    ) -> None:
        """list(include_vms=True) does not POST once per snapshot with rows."""
        second = {**sample_snapshot_data, "$key": 2, "name": "Other"}
        other_vm = {**sample_vm_data, "$key": 101, "name": "OtherVM", "cloud_snapshot": 2}
        mock_session.request.side_effect = [
            _resp([sample_snapshot_data, second]),
            _resp([sample_vm_data]),
            _resp([other_vm]),
            _error(403, "Permission denied"),
        ]

        snapshots = mock_client.cloud_snapshots.list(include_vms=True)

        assert snapshots[0].vms is not None
        assert [vm.name for vm in snapshots[0].vms] == ["TestVM"]
        assert snapshots[1].vms is not None
        assert [vm.name for vm in snapshots[1].vms] == ["OtherVM"]
        assert _find_vms_posts(mock_session) == []

    def test_list_include_vms_posts_only_for_empty_snapshot(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        sample_snapshot_data: dict[str, Any],
        sample_vm_data: dict[str, Any],
    ) -> None:
        """One POST for the snapshot that has no rows, none for the rest."""
        second = {**sample_snapshot_data, "$key": 2, "name": "New"}
        filled = {**sample_vm_data, "$key": 101, "name": "Filled", "cloud_snapshot": 2}
        mock_session.request.side_effect = [
            _resp([sample_snapshot_data, second]),
            _resp([sample_vm_data]),
            _resp([]),
            _resp({"response": "ok"}),
            _resp([filled]),
        ]

        snapshots = mock_client.cloud_snapshots.list(include_vms=True)

        assert [vm.name for vm in snapshots[0].vms or []] == ["TestVM"]
        assert [vm.name for vm in snapshots[1].vms or []] == ["Filled"]
        posts = _find_vms_posts(mock_session)
        assert len(posts) == 1
        assert posts[0].kwargs["json"] == {"action": "find_vms", "cloud_snapshot": 2}

    def test_get_include_vms_keeps_rows_for_readonly_user(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        sample_snapshot_data: dict[str, Any],
        sample_vm_data: dict[str, Any],
    ) -> None:
        """get(include_vms=True) returns existing rows when find_vms is forbidden."""
        mock_session.request.side_effect = [
            _resp(sample_snapshot_data),
            _resp([sample_vm_data]),
            _error(403, "Permission denied"),
        ]

        snapshot = mock_client.cloud_snapshots.get(1, include_vms=True)

        assert snapshot.vms is not None
        assert [vm.name for vm in snapshot.vms] == ["TestVM"]
        assert _find_vms_posts(mock_session) == []

    def test_get_include_vms_permission_denied_on_empty_membership(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        sample_snapshot_data: dict[str, Any],
    ) -> None:
        """An empty read plus a refused find_vms stays an empty VM list."""
        mock_session.request.side_effect = [
            _resp(sample_snapshot_data),
            _resp([]),
            _error(403, "Permission denied"),
        ]

        snapshot = mock_client.cloud_snapshots.get(1, include_vms=True)

        assert snapshot.vms == []

    def test_get_include_vms_raises_vm_read_errors(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        sample_snapshot_data: dict[str, Any],
    ) -> None:
        """A failed membership GET is raised from get(include_vms=True)."""
        mock_session.request.side_effect = [
            _resp(sample_snapshot_data),
            _error(500, "membership read failed"),
        ]

        with pytest.raises(APIError, match="membership read failed"):
            mock_client.cloud_snapshots.get(1, include_vms=True)

    def test_list_include_vms_raises_vm_read_errors(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        sample_snapshot_data: dict[str, Any],
    ) -> None:
        """A failed membership GET is raised from list(include_vms=True)."""
        mock_session.request.side_effect = [
            _resp([sample_snapshot_data]),
            _error(500, "membership read failed"),
        ]

        with pytest.raises(APIError, match="membership read failed"):
            mock_client.cloud_snapshots.list(include_vms=True)

    @patch("pyvergeos.resources.cloud_snapshots.time.sleep")
    def test_find_vms_retries_when_still_building(
        self,
        mock_sleep: MagicMock,
        mock_client: VergeClient,
        mock_session: MagicMock,
    ) -> None:
        """find_vms retries when server reports snapshot is still building (issue #209)."""
        mock_session.request.reset_mock()
        mock_session.request.side_effect = [
            ValidationError("System snapshot is still building"),
            _resp({"response": "ok"}),
        ]
        result = mock_client.cloud_snapshots.find_vms(7)
        assert result == {"response": "ok"}
        assert mock_session.request.call_count == 2
        assert mock_sleep.called

    @patch("pyvergeos.resources.cloud_snapshots.time.sleep")
    def test_find_vms_still_building_raises_on_timeout(
        self,
        mock_sleep: MagicMock,
        mock_client: VergeClient,
        mock_session: MagicMock,
    ) -> None:
        """find_vms raises ValidationError when still building exceeds timeout."""
        mock_session.request.side_effect = ValidationError("System snapshot is still building")
        with pytest.raises(ValidationError, match="System snapshot is still building"):
            mock_client.cloud_snapshots.find_vms(7, timeout=0.01)

    @patch("pyvergeos.resources.cloud_snapshots.time.sleep")
    def test_empty_membership_polls_until_vms_appear(
        self,
        mock_sleep: MagicMock,
        mock_client: VergeClient,
        mock_session: MagicMock,
        sample_vm_data: dict[str, Any],
    ) -> None:
        """vms.list() polls when find_vms runs asynchronously (issue #209)."""
        mock_session.request.side_effect = [
            _resp([]),
            _resp({"response": "ok"}),
            _resp([]),
            _resp([sample_vm_data]),
        ]
        mock_session.request.reset_mock()

        vms = mock_client.cloud_snapshots.vms(1).list()

        assert [vm.name for vm in vms] == ["TestVM"]
        assert mock_sleep.called
        calls = mock_session.request.call_args_list
        assert len(calls) == 4
        assert calls[0].kwargs["method"] == "GET"
        assert calls[1].kwargs["method"] == "POST"
        assert calls[2].kwargs["method"] == "GET"
        assert calls[3].kwargs["method"] == "GET"

    @patch("pyvergeos.resources.cloud_snapshots.time.sleep")
    def test_empty_membership_wait_false_does_not_poll(
        self,
        mock_sleep: MagicMock,
        mock_client: VergeClient,
        mock_session: MagicMock,
    ) -> None:
        """vms.list(wait=False) does not poll after the first re-read."""
        mock_session.request.side_effect = [
            _resp([]),
            _resp({"response": "ok"}),
            _resp([]),
        ]
        mock_session.request.reset_mock()

        vms = mock_client.cloud_snapshots.vms(1).list(wait=False)

        assert vms == []
        assert not mock_sleep.called
        assert len(mock_session.request.call_args_list) == 3

    @patch("pyvergeos.resources.cloud_snapshots.time.sleep")
    def test_find_vms_timeout_zero_or_negative_does_not_retry(
        self,
        mock_sleep: MagicMock,
        mock_client: VergeClient,
        mock_session: MagicMock,
    ) -> None:
        """find_vms with timeout=0 or negative raises immediately without retrying (issue #212)."""
        mock_session.request.side_effect = ValidationError("System snapshot is still building")
        mock_session.request.reset_mock()
        with pytest.raises(ValidationError, match="System snapshot is still building"):
            mock_client.cloud_snapshots.find_vms(7, timeout=0)
        assert mock_session.request.call_count == 1
        assert not mock_sleep.called

        mock_session.request.reset_mock()
        with pytest.raises(ValidationError, match="System snapshot is still building"):
            mock_client.cloud_snapshots.find_vms(7, timeout=-1)
        assert mock_session.request.call_count == 1
        assert not mock_sleep.called

    @patch("pyvergeos.resources.cloud_snapshots.time.time")
    @patch("pyvergeos.resources.cloud_snapshots.time.sleep")
    def test_empty_membership_second_call_does_not_poll_or_post(
        self,
        mock_sleep: MagicMock,
        mock_time: MagicMock,
        mock_client: VergeClient,
        mock_session: MagicMock,
    ) -> None:
        """vms.list() remembers find_vms already ran after timeout so subsequent reads do not poll or POST (issue #212)."""
        mock_time.side_effect = [1000.0, 1000.0, 1020.0]
        mock_session.request.side_effect = [
            _resp([]),
            _resp({"response": "ok"}),
            _resp([]),
        ]
        mock_session.request.reset_mock()

        # First call: wait=True polls until timeout expires on empty snapshot
        vms1 = mock_client.cloud_snapshots.vms(1).list(wait=True)
        assert vms1 == []

        # Second call: rows still empty, but find_vms already settled for this snapshot
        mock_session.request.reset_mock()
        mock_session.request.side_effect = [_resp([])]

        vms2 = mock_client.cloud_snapshots.vms(1).list(wait=True)
        assert vms2 == []
        assert mock_session.request.call_count == 1
        assert mock_session.request.call_args.kwargs["method"] == "GET"
        assert not mock_sleep.called

    @patch("pyvergeos.resources.cloud_snapshots.time.sleep")
    def test_filtered_miss_stops_polling_once_membership_appears(
        self,
        mock_sleep: MagicMock,
        mock_client: VergeClient,
        mock_session: MagicMock,
        sample_vm_data: dict[str, Any],
    ) -> None:
        """Filtered read stops polling as soon as snapshot membership rows appear (issue #212)."""
        mock_session.request.side_effect = [
            _resp([]),
            _resp([]),
            _resp({"response": "ok"}),
            _resp([]),
            _resp([sample_vm_data]),
        ]
        mock_session.request.reset_mock()

        with pytest.raises(NotFoundError, match="VM 'zz-not-a-vm' not found"):
            mock_client.cloud_snapshots.vms(1).get(name="zz-not-a-vm")

        # Stopped polling as soon as membership rows appeared, rather than timing out
        assert mock_sleep.call_count == 0

    @patch("pyvergeos.resources.cloud_snapshots.time.time")
    @patch("pyvergeos.resources.cloud_snapshots.time.sleep")
    def test_cloud_snapshot_get_vms_second_call_skips_post_and_poll(
        self,
        mock_sleep: MagicMock,
        mock_time: MagicMock,
        mock_client: VergeClient,
        mock_session: MagicMock,
        sample_snapshot_data: dict[str, Any],
    ) -> None:
        """CloudSnapshot.get_vms() on an empty snapshot skips POST and polling after timeout (issue #212)."""
        mock_time.side_effect = [1000.0, 1000.0, 1020.0]
        snapshot = CloudSnapshot(sample_snapshot_data, mock_client.cloud_snapshots)
        mock_session.request.side_effect = [
            _resp([]),
            _resp({"response": "ok"}),
            _resp([]),
        ]
        mock_session.request.reset_mock()

        # Call 1: wait=True polls until timeout
        vms1 = snapshot.get_vms(wait=True)
        assert vms1 == []

        # Call 2 (wait=True)
        mock_session.request.reset_mock()
        mock_session.request.side_effect = [_resp([])]

        vms2 = snapshot.get_vms(wait=True)
        assert vms2 == []
        assert mock_session.request.call_count == 1
        assert mock_session.request.call_args.kwargs["method"] == "GET"
        assert not mock_sleep.called

    @patch("pyvergeos.resources.cloud_snapshots.time.sleep")
    def test_read_after_find_vms_polls_for_vms(
        self,
        mock_sleep: MagicMock,
        mock_client: VergeClient,
        mock_session: MagicMock,
        sample_vm_data: dict[str, Any],
    ) -> None:
        """vms.list() right after find_vms() polls until rows appear instead of returning empty list (issue #217)."""
        mock_session.request.side_effect = [
            _resp({"response": "ok"}),  # find_vms POST
            _resp([]),  # first read in list()
            _resp({"response": "ok"}),  # list() find_vms POST
            _resp([]),  # first poll in list()
            _resp([sample_vm_data]),  # second poll in list()
        ]
        mock_session.request.reset_mock()

        mock_client.cloud_snapshots.find_vms(1)
        vms = mock_client.cloud_snapshots.vms(1).list()
        assert [vm.name for vm in vms] == ["TestVM"]
        assert mock_sleep.called

    @patch("pyvergeos.resources.cloud_snapshots.time.sleep")
    def test_get_vms_after_find_vms_polls_for_vms(
        self,
        mock_sleep: MagicMock,
        mock_client: VergeClient,
        mock_session: MagicMock,
        sample_snapshot_data: dict[str, Any],
        sample_vm_data: dict[str, Any],
    ) -> None:
        """CloudSnapshot.get_vms() right after find_vms() polls until rows appear (issue #217)."""
        snapshot = CloudSnapshot(sample_snapshot_data, mock_client.cloud_snapshots)
        mock_session.request.side_effect = [
            _resp({"response": "ok"}),  # find_vms POST
            _resp([]),  # first read in get_vms()
            _resp({"response": "ok"}),  # get_vms() find_vms POST
            _resp([]),  # first poll in get_vms()
            _resp([sample_vm_data]),  # second poll in get_vms()
        ]
        mock_session.request.reset_mock()

        mock_client.cloud_snapshots.find_vms(snapshot.key)
        vms = snapshot.get_vms()
        assert [vm.name for vm in vms] == ["TestVM"]
        assert mock_sleep.called

    @patch("pyvergeos.resources.cloud_snapshots.time.sleep")
    def test_read_wait_true_after_wait_false_polls_for_vms(
        self,
        mock_sleep: MagicMock,
        mock_client: VergeClient,
        mock_session: MagicMock,
        sample_vm_data: dict[str, Any],
    ) -> None:
        """list(wait=True) after list(wait=False) polls until rows appear (issue #217)."""
        mock_session.request.side_effect = [
            _resp([]),  # list(wait=False) initial read
            _resp({"response": "ok"}),  # list(wait=False) find_vms POST
            _resp([]),  # list(wait=False) re-read
            _resp([]),  # list(wait=True) initial read
            _resp({"response": "ok"}),  # list(wait=True) find_vms POST
            _resp([]),  # list(wait=True) first poll
            _resp([sample_vm_data]),  # list(wait=True) second poll
        ]
        mock_session.request.reset_mock()

        vms1 = mock_client.cloud_snapshots.vms(1).list(wait=False)
        assert vms1 == []
        assert not mock_sleep.called

        vms2 = mock_client.cloud_snapshots.vms(1).list(wait=True)
        assert [vm.name for vm in vms2] == ["TestVM"]
        assert mock_sleep.called
