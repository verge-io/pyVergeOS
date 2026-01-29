"""Unit tests for Cloud Snapshot operations."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import MagicMock

import pytest

from pyvergeos import VergeClient
from pyvergeos.exceptions import NotFoundError, ValidationError
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

    def test_vm_properties(
        self, mock_client: VergeClient, sample_vm_data: dict[str, Any]
    ) -> None:
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

    def test_vm_repr(
        self, mock_client: VergeClient, sample_vm_data: dict[str, Any]
    ) -> None:
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
        tenant = CloudSnapshotTenant(
            sample_tenant_data, mock_client.cloud_snapshots.tenants(1)
        )

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
        tenant = CloudSnapshotTenant(
            sample_tenant_data, mock_client.cloud_snapshots.tenants(1)
        )
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

    def test_snapshot_never_expires_by_type(self, mock_client: VergeClient) -> None:
        """Test never_expires detection via expires_type."""
        data = {
            "$key": 1,
            "name": "Never Expires",
            "expires_type": "never",
            "expires": 0,
        }
        snapshot = CloudSnapshot(data, mock_client.cloud_snapshots)
        assert snapshot.never_expires is True
        assert snapshot.expires_at is None

    def test_snapshot_never_expires_by_zero(self, mock_client: VergeClient) -> None:
        """Test never_expires detection via zero expires value."""
        data = {
            "$key": 1,
            "name": "Never Expires",
            "expires_type": "time",
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
        tenant = CloudSnapshotTenant(
            sample_tenant_data, mock_client.cloud_snapshots.tenants(1)
        )

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
        """Test listing VMs in a snapshot."""
        mock_session.request.return_value.json.return_value = [sample_vm_data]

        vm_manager = mock_client.cloud_snapshots.vms(1)
        vms = vm_manager.list()

        assert len(vms) == 1
        assert vms[0].name == "TestVM"

        # Verify the filter includes cloud_snapshot
        call_args = mock_session.request.call_args
        assert "cloud_snapshot eq 1" in call_args.kwargs.get("params", {}).get(
            "filter", ""
        )

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

    def test_get_vm_not_found(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
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
        assert "cloud_snapshot eq 1" in call_args.kwargs.get("params", {}).get(
            "filter", ""
        )

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

    def test_create_snapshot_default(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test creating a snapshot with defaults."""
        created_data = {
            "$key": 5,
            "name": "Snapshot_20250101_1234",
            "created": 1735689600,
            "expires": 1735948800,  # 3 days later
        }
        mock_session.request.return_value.json.return_value = created_data

        snapshot = mock_client.cloud_snapshots.create(name="Test Create")

        assert snapshot.key == 5

        # Verify POST call - check any call that had json body with "name" key
        found_create = False
        for call in mock_session.request.call_args_list:
            body = call.kwargs.get("json", {})
            if body and body.get("name") == "Test Create":
                found_create = True
                assert body.get("retention") == 259200  # Default 3 days
                break
        assert found_create, "Create call not found"

    def test_create_snapshot_custom_retention(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test creating a snapshot with custom retention_seconds."""
        created_data = {"$key": 6, "name": "Custom Retention"}
        mock_session.request.return_value.json.return_value = created_data

        mock_client.cloud_snapshots.create(
            name="Custom Retention", retention_seconds=3600
        )

        found = False
        for call in mock_session.request.call_args_list:
            body = call.kwargs.get("json", {})
            if body and body.get("name") == "Custom Retention":
                found = True
                assert body.get("retention") == 3600
                break
        assert found, "Create call not found"

    def test_create_snapshot_timedelta_retention(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test creating a snapshot with timedelta retention."""
        created_data = {"$key": 7, "name": "Timedelta Retention"}
        mock_session.request.return_value.json.return_value = created_data

        mock_client.cloud_snapshots.create(
            name="Timedelta Retention", retention=timedelta(hours=2)
        )

        found = False
        for call in mock_session.request.call_args_list:
            body = call.kwargs.get("json", {})
            if body and body.get("name") == "Timedelta Retention":
                found = True
                assert body.get("retention") == 7200  # 2 hours
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
                assert body.get("retention") == 0
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

    def test_delete_snapshot(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
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
        """Test CloudSnapshot.get_vms() method."""
        # First call returns VMs
        mock_session.request.return_value.json.return_value = [sample_vm_data]

        snapshot = CloudSnapshot(sample_snapshot_data, mock_client.cloud_snapshots)
        vms = snapshot.get_vms()

        assert len(vms) == 1
        assert vms[0].name == "TestVM"

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
