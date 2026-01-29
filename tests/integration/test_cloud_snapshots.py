"""Integration tests for Cloud Snapshot operations.

These tests require a live VergeOS system and will be skipped
if the environment variables are not set.
"""

from __future__ import annotations

import uuid
from datetime import timedelta

import pytest

from pyvergeos import VergeClient
from pyvergeos.exceptions import NotFoundError


def unique_name(prefix: str = "pyvergeos-test") -> str:
    """Generate a unique name for test resources."""
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


@pytest.fixture
def test_snapshot_name() -> str:
    """Generate a unique test snapshot name."""
    return unique_name("pyvergeos-cloudsnap")


@pytest.mark.integration
class TestCloudSnapshotListIntegration:
    """Integration tests for CloudSnapshotManager list operations."""

    def test_list_snapshots(self, live_client: VergeClient) -> None:
        """Test listing cloud snapshots from live system."""
        snapshots = live_client.cloud_snapshots.list()

        # Should return a list (may be empty)
        assert isinstance(snapshots, list)

        # Each snapshot should have expected properties
        for snapshot in snapshots:
            assert hasattr(snapshot, "key")
            assert hasattr(snapshot, "name")
            assert hasattr(snapshot, "description")
            assert hasattr(snapshot, "created_at")
            assert hasattr(snapshot, "expires_at")
            assert hasattr(snapshot, "never_expires")
            assert hasattr(snapshot, "is_immutable")
            assert hasattr(snapshot, "status")

    def test_list_snapshots_with_limit(self, live_client: VergeClient) -> None:
        """Test listing snapshots with limit."""
        snapshots = live_client.cloud_snapshots.list(limit=1)

        assert isinstance(snapshots, list)
        assert len(snapshots) <= 1

    def test_list_snapshots_include_expired(self, live_client: VergeClient) -> None:
        """Test listing snapshots with expired included."""
        active_snapshots = live_client.cloud_snapshots.list()
        all_snapshots = live_client.cloud_snapshots.list(include_expired=True)

        assert isinstance(all_snapshots, list)
        # All snapshots should include at least as many as active
        assert len(all_snapshots) >= len(active_snapshots)

    def test_list_snapshots_include_vms(self, live_client: VergeClient) -> None:
        """Test listing snapshots with VMs included."""
        snapshots = live_client.cloud_snapshots.list(include_vms=True)

        assert isinstance(snapshots, list)
        for snapshot in snapshots:
            # vms should be loaded (may be empty list)
            assert snapshot.vms is not None
            assert isinstance(snapshot.vms, list)

    def test_list_snapshots_include_tenants(self, live_client: VergeClient) -> None:
        """Test listing snapshots with tenants included."""
        snapshots = live_client.cloud_snapshots.list(include_tenants=True)

        assert isinstance(snapshots, list)
        for snapshot in snapshots:
            # tenants should be loaded (may be empty list)
            assert snapshot.tenants is not None
            assert isinstance(snapshot.tenants, list)


@pytest.mark.integration
class TestCloudSnapshotGetIntegration:
    """Integration tests for CloudSnapshotManager get operations."""

    def test_get_snapshot_by_key(self, live_client: VergeClient) -> None:
        """Test getting a snapshot by key."""
        snapshots = live_client.cloud_snapshots.list()
        if not snapshots:
            pytest.skip("No cloud snapshots available for testing")

        snapshot = snapshots[0]
        fetched = live_client.cloud_snapshots.get(snapshot.key)

        assert fetched.key == snapshot.key
        assert fetched.name == snapshot.name

    def test_get_snapshot_by_name(self, live_client: VergeClient) -> None:
        """Test getting a snapshot by name."""
        snapshots = live_client.cloud_snapshots.list()
        if not snapshots:
            pytest.skip("No cloud snapshots available for testing")

        snapshot = snapshots[0]
        fetched = live_client.cloud_snapshots.get(name=snapshot.name)

        assert fetched.key == snapshot.key
        assert fetched.name == snapshot.name

    def test_get_snapshot_with_vms(self, live_client: VergeClient) -> None:
        """Test getting a snapshot with VMs included."""
        snapshots = live_client.cloud_snapshots.list()
        if not snapshots:
            pytest.skip("No cloud snapshots available for testing")

        snapshot = snapshots[0]
        fetched = live_client.cloud_snapshots.get(snapshot.key, include_vms=True)

        assert fetched.vms is not None
        assert isinstance(fetched.vms, list)

    def test_get_snapshot_with_tenants(self, live_client: VergeClient) -> None:
        """Test getting a snapshot with tenants included."""
        snapshots = live_client.cloud_snapshots.list()
        if not snapshots:
            pytest.skip("No cloud snapshots available for testing")

        snapshot = snapshots[0]
        fetched = live_client.cloud_snapshots.get(snapshot.key, include_tenants=True)

        assert fetched.tenants is not None
        assert isinstance(fetched.tenants, list)

    def test_get_snapshot_not_found(self, live_client: VergeClient) -> None:
        """Test getting a non-existent snapshot."""
        with pytest.raises(NotFoundError):
            live_client.cloud_snapshots.get(name="non-existent-snapshot-12345")


@pytest.mark.integration
class TestCloudSnapshotCRUDIntegration:
    """Integration tests for CloudSnapshot CRUD operations."""

    def test_create_and_delete_snapshot(
        self, live_client: VergeClient, test_snapshot_name: str
    ) -> None:
        """Test creating and deleting a cloud snapshot."""
        # Create snapshot
        snapshot = live_client.cloud_snapshots.create(
            name=test_snapshot_name,
            retention_seconds=3600,  # 1 hour retention
            wait=True,
            wait_timeout=180,
        )

        try:
            assert snapshot.name == test_snapshot_name
            assert snapshot.key is not None
            assert snapshot.created_at is not None

            # Verify it exists
            fetched = live_client.cloud_snapshots.get(snapshot.key)
            assert fetched.key == snapshot.key
        finally:
            # Cleanup
            live_client.cloud_snapshots.delete(snapshot.key)

        # Verify deletion
        with pytest.raises(NotFoundError):
            live_client.cloud_snapshots.get(name=test_snapshot_name)

    def test_create_snapshot_with_timedelta(
        self, live_client: VergeClient, test_snapshot_name: str
    ) -> None:
        """Test creating a snapshot with timedelta retention."""
        snapshot = live_client.cloud_snapshots.create(
            name=test_snapshot_name,
            retention=timedelta(days=1),
            wait=True,
            wait_timeout=180,
        )

        try:
            assert snapshot.name == test_snapshot_name
            # Verify snapshot has an expiration set (not never-expires)
            assert snapshot.never_expires is False
            assert snapshot.expires_at is not None
        finally:
            live_client.cloud_snapshots.delete(snapshot.key)

    def test_create_snapshot_default_name(self, live_client: VergeClient) -> None:
        """Test creating a snapshot with auto-generated name."""
        snapshot = live_client.cloud_snapshots.create(
            retention_seconds=3600,
            wait=True,
            wait_timeout=180,
        )

        try:
            # Should have generated a name starting with "Snapshot_"
            assert snapshot.name.startswith("Snapshot_")
        finally:
            live_client.cloud_snapshots.delete(snapshot.key)

    def test_snapshot_object_delete_method(
        self, live_client: VergeClient, test_snapshot_name: str
    ) -> None:
        """Test snapshot.delete() method."""
        # Create snapshot
        snapshot = live_client.cloud_snapshots.create(
            name=test_snapshot_name,
            retention_seconds=3600,
            wait=True,
            wait_timeout=180,
        )

        # Delete using object method
        snapshot.delete()

        # Verify deletion
        with pytest.raises(NotFoundError):
            live_client.cloud_snapshots.get(name=test_snapshot_name)


@pytest.mark.integration
class TestCloudSnapshotVMSubmanagerIntegration:
    """Integration tests for CloudSnapshotVMManager operations."""

    def test_list_vms_in_snapshot(self, live_client: VergeClient) -> None:
        """Test listing VMs in a cloud snapshot."""
        snapshots = live_client.cloud_snapshots.list()
        if not snapshots:
            pytest.skip("No cloud snapshots available for testing")

        snapshot = snapshots[0]
        vms = live_client.cloud_snapshots.vms(snapshot.key).list()

        assert isinstance(vms, list)
        for vm in vms:
            assert hasattr(vm, "key")
            assert hasattr(vm, "name")
            assert hasattr(vm, "cpu_cores")
            assert hasattr(vm, "ram_mb")
            assert hasattr(vm, "cloud_snapshot_key")
            assert vm.cloud_snapshot_key == snapshot.key

    def test_get_vms_via_object_method(self, live_client: VergeClient) -> None:
        """Test snapshot.get_vms() method."""
        snapshots = live_client.cloud_snapshots.list()
        if not snapshots:
            pytest.skip("No cloud snapshots available for testing")

        snapshot = snapshots[0]
        vms = snapshot.get_vms()

        assert isinstance(vms, list)


@pytest.mark.integration
class TestCloudSnapshotTenantSubmanagerIntegration:
    """Integration tests for CloudSnapshotTenantManager operations."""

    def test_list_tenants_in_snapshot(self, live_client: VergeClient) -> None:
        """Test listing tenants in a cloud snapshot."""
        snapshots = live_client.cloud_snapshots.list()
        if not snapshots:
            pytest.skip("No cloud snapshots available for testing")

        snapshot = snapshots[0]
        tenants = live_client.cloud_snapshots.tenants(snapshot.key).list()

        assert isinstance(tenants, list)
        for tenant in tenants:
            assert hasattr(tenant, "key")
            assert hasattr(tenant, "name")
            assert hasattr(tenant, "nodes")
            assert hasattr(tenant, "cpu_cores")
            assert hasattr(tenant, "ram_mb")
            assert hasattr(tenant, "cloud_snapshot_key")
            assert tenant.cloud_snapshot_key == snapshot.key

    def test_get_tenants_via_object_method(self, live_client: VergeClient) -> None:
        """Test snapshot.get_tenants() method."""
        snapshots = live_client.cloud_snapshots.list()
        if not snapshots:
            pytest.skip("No cloud snapshots available for testing")

        snapshot = snapshots[0]
        tenants = snapshot.get_tenants()

        assert isinstance(tenants, list)


@pytest.mark.integration
class TestCloudSnapshotPropertiesIntegration:
    """Integration tests for CloudSnapshot property accessors."""

    def test_snapshot_properties(self, live_client: VergeClient) -> None:
        """Test that all snapshot properties are accessible."""
        snapshots = live_client.cloud_snapshots.list()
        if not snapshots:
            pytest.skip("No cloud snapshots available for testing")

        snapshot = snapshots[0]

        # Test all property accessors don't raise exceptions
        _ = snapshot.key
        _ = snapshot.name
        _ = snapshot.description
        _ = snapshot.created_at
        _ = snapshot.expires_at
        _ = snapshot.never_expires
        _ = snapshot.snapshot_profile_key
        _ = snapshot.is_private
        _ = snapshot.is_remote_sync
        _ = snapshot.is_immutable
        _ = snapshot.immutable_status
        _ = snapshot.is_locked
        _ = snapshot.immutable_lock_expires_at
        _ = snapshot.status
        _ = snapshot.status_info

    def test_vm_properties(self, live_client: VergeClient) -> None:
        """Test that all VM properties are accessible."""
        snapshots = live_client.cloud_snapshots.list()
        if not snapshots:
            pytest.skip("No cloud snapshots available for testing")

        snapshot = snapshots[0]
        vms = live_client.cloud_snapshots.vms(snapshot.key).list()
        if not vms:
            pytest.skip("No VMs in cloud snapshot for testing")

        vm = vms[0]

        # Test all property accessors don't raise exceptions
        _ = vm.key
        _ = vm.name
        _ = vm.description
        _ = vm.uuid
        _ = vm.machine_uuid
        _ = vm.cpu_cores
        _ = vm.ram_mb
        _ = vm.os_family
        _ = vm.is_snapshot
        _ = vm.status
        _ = vm.status_info
        _ = vm.original_key
        _ = vm.cloud_snapshot_key

    def test_tenant_properties(self, live_client: VergeClient) -> None:
        """Test that all tenant properties are accessible."""
        snapshots = live_client.cloud_snapshots.list()
        if not snapshots:
            pytest.skip("No cloud snapshots available for testing")

        snapshot = snapshots[0]
        tenants = live_client.cloud_snapshots.tenants(snapshot.key).list()
        if not tenants:
            pytest.skip("No tenants in cloud snapshot for testing")

        tenant = tenants[0]

        # Test all property accessors don't raise exceptions
        _ = tenant.key
        _ = tenant.name
        _ = tenant.description
        _ = tenant.uuid
        _ = tenant.nodes
        _ = tenant.cpu_cores
        _ = tenant.ram_mb
        _ = tenant.is_snapshot
        _ = tenant.status
        _ = tenant.status_info
        _ = tenant.original_key
        _ = tenant.cloud_snapshot_key
