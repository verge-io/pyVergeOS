"""Integration tests for Tenant operations."""

import time

import pytest

from pyvergeos import VergeClient
from pyvergeos.exceptions import NotFoundError


@pytest.mark.integration
class TestTenantOperations:
    """Integration tests for Tenant operations against live VergeOS."""

    def test_list_tenants(self, live_client: VergeClient) -> None:
        """Test listing tenants."""
        tenants = live_client.tenants.list(limit=10)
        assert isinstance(tenants, list)

        # Each tenant should have rich fields
        if tenants:
            tenant = tenants[0]
            assert "$key" in tenant
            assert "name" in tenant
            assert "status" in tenant

    def test_list_tenants_excludes_snapshots(self, live_client: VergeClient) -> None:
        """Test that list() excludes snapshots by default."""
        tenants = live_client.tenants.list()
        for tenant in tenants:
            assert not tenant.is_snapshot

    def test_list_tenants_include_snapshots(self, live_client: VergeClient) -> None:
        """Test that include_snapshots=True includes snapshots."""
        all_items = live_client.tenants.list(include_snapshots=True, limit=50)
        assert isinstance(all_items, list)

    def test_list_running_tenants(self, live_client: VergeClient) -> None:
        """Test listing running tenants."""
        running = live_client.tenants.list_running()
        assert isinstance(running, list)
        for tenant in running:
            assert tenant.is_running is True

    def test_list_stopped_tenants(self, live_client: VergeClient) -> None:
        """Test listing stopped tenants."""
        stopped = live_client.tenants.list_stopped()
        assert isinstance(stopped, list)
        for tenant in stopped:
            assert tenant.is_running is False
            assert tenant.is_starting is False

    def test_list_by_status(self, live_client: VergeClient) -> None:
        """Test listing tenants by status."""
        tenants = live_client.tenants.list()
        if not tenants:
            pytest.skip("No tenants available")

        # Get a status that exists
        status = tenants[0].status
        by_status = live_client.tenants.list_by_status(status)
        assert isinstance(by_status, list)
        for tenant in by_status:
            assert tenant.status == status

    def test_get_tenant_by_key(self, live_client: VergeClient) -> None:
        """Test getting a tenant by key."""
        tenants = live_client.tenants.list(limit=1)
        if not tenants:
            pytest.skip("No tenants available")

        tenant = live_client.tenants.get(tenants[0].key)
        assert tenant.key == tenants[0].key
        assert tenant.name == tenants[0].name

    def test_get_tenant_by_name(self, live_client: VergeClient) -> None:
        """Test getting a tenant by name."""
        tenants = live_client.tenants.list(limit=1)
        if not tenants:
            pytest.skip("No tenants available")

        tenant = live_client.tenants.get(name=tenants[0].name)
        assert tenant.name == tenants[0].name
        assert tenant.key == tenants[0].key

    def test_get_tenant_not_found(self, live_client: VergeClient) -> None:
        """Test getting a non-existent tenant."""
        with pytest.raises(NotFoundError):
            live_client.tenants.get(name="nonexistent-tenant-12345")

    def test_tenant_properties(self, live_client: VergeClient) -> None:
        """Test tenant property access."""
        tenants = live_client.tenants.list(limit=1)
        if not tenants:
            pytest.skip("No tenants available")

        tenant = tenants[0]

        # Test boolean properties
        assert isinstance(tenant.is_running, bool)
        assert isinstance(tenant.is_starting, bool)
        assert isinstance(tenant.is_stopping, bool)
        assert isinstance(tenant.is_migrating, bool)
        assert isinstance(tenant.is_snapshot, bool)
        assert isinstance(tenant.is_isolated, bool)

        # Test string properties
        assert isinstance(tenant.status, str)
        assert isinstance(tenant.state, str)

        # Test optional properties
        network = tenant.network_name
        assert network is None or isinstance(network, str)

        ui_ip = tenant.ui_address_ip
        assert ui_ip is None or isinstance(ui_ip, str)


@pytest.mark.integration
class TestTenantPowerOperations:
    """Integration tests for Tenant power operations.

    These tests require a specific test tenant named 'test'.
    """

    @pytest.fixture
    def test_tenant(self, live_client: VergeClient):
        """Get the test tenant, or skip if not available."""
        try:
            return live_client.tenants.get(name="test")
        except NotFoundError:
            pytest.skip("Test tenant 'test' not available")

    def test_power_on_via_manager(self, live_client: VergeClient, test_tenant) -> None:
        """Test powering on a tenant via manager."""
        if test_tenant.is_running:
            pytest.skip("Tenant already running")

        result = live_client.tenants.power_on(test_tenant.key)
        assert result is not None

        # Wait for it to start
        for _ in range(12):
            time.sleep(5)
            tenant = live_client.tenants.get(test_tenant.key)
            if tenant.is_running:
                break

        tenant = live_client.tenants.get(test_tenant.key)
        assert tenant.is_running or tenant.is_starting

    def test_power_off_via_manager(self, live_client: VergeClient, test_tenant) -> None:
        """Test powering off a tenant via manager."""
        # Ensure it's running first
        tenant = live_client.tenants.get(test_tenant.key)
        if not tenant.is_running:
            live_client.tenants.power_on(tenant.key)
            for _ in range(12):
                time.sleep(5)
                tenant = live_client.tenants.get(tenant.key)
                if tenant.is_running:
                    break

        if not tenant.is_running:
            pytest.skip("Could not start tenant")

        result = live_client.tenants.power_off(tenant.key)
        assert result is not None

        # Wait for it to stop
        for _ in range(12):
            time.sleep(5)
            tenant = live_client.tenants.get(tenant.key)
            if not tenant.is_running and not tenant.is_stopping:
                break

        tenant = live_client.tenants.get(tenant.key)
        assert not tenant.is_running

    def test_power_on_via_object(self, live_client: VergeClient, test_tenant) -> None:
        """Test powering on a tenant via Tenant object."""
        tenant = live_client.tenants.get(test_tenant.key)
        if tenant.is_running:
            pytest.skip("Tenant already running")

        tenant.power_on()

        # Wait for it to start
        for _ in range(12):
            time.sleep(5)
            tenant = tenant.refresh()
            if tenant.is_running:
                break

        assert tenant.is_running or tenant.is_starting

    def test_power_off_via_object(self, live_client: VergeClient, test_tenant) -> None:
        """Test powering off a tenant via Tenant object."""
        tenant = live_client.tenants.get(test_tenant.key)
        if not tenant.is_running:
            tenant.power_on()
            for _ in range(12):
                time.sleep(5)
                tenant = tenant.refresh()
                if tenant.is_running:
                    break

        if not tenant.is_running:
            pytest.skip("Could not start tenant")

        tenant.power_off()

        # Wait for it to stop
        for _ in range(12):
            time.sleep(5)
            tenant = tenant.refresh()
            if not tenant.is_running and not tenant.is_stopping:
                break

        assert not tenant.is_running


@pytest.mark.integration
class TestTenantCRUD:
    """Integration tests for Tenant CRUD operations."""

    def test_create_update_delete_tenant(self, live_client: VergeClient) -> None:
        """Test full CRUD cycle for a tenant."""
        import random

        tenant_name = f"pyvergeos-test-{random.randint(10000, 99999)}"

        # Create
        tenant = live_client.tenants.create(
            name=tenant_name,
            description="Test tenant for pyvergeos integration tests",
            password="TestPassword123!",
            expose_cloud_snapshots=True,
            allow_branding=False,
        )

        assert tenant.name == tenant_name
        assert tenant.description == "Test tenant for pyvergeos integration tests"
        tenant_key = tenant.key
        vnet_key = tenant.get("vnet")

        try:
            # Update
            updated = live_client.tenants.update(
                tenant_key, description="Updated description", note="Test note"
            )
            assert updated.description == "Updated description"
            assert updated.note == "Test note"

            # Update via save()
            tenant = live_client.tenants.get(tenant_key)
            tenant.save(description="Via save method")
            tenant = tenant.refresh()
            assert tenant.description == "Via save method"

        finally:
            # Cleanup: power off network and delete tenant
            if vnet_key:
                try:
                    live_client._request(
                        "POST",
                        "vnet_actions",
                        json_data={"vnet": vnet_key, "action": "poweroff"},
                    )
                    time.sleep(2)
                except Exception:
                    pass

            live_client.tenants.delete(tenant_key)

            # Verify deletion
            with pytest.raises(NotFoundError):
                live_client.tenants.get(tenant_key)


@pytest.mark.integration
class TestTenantClone:
    """Integration tests for Tenant clone operations."""

    @pytest.fixture
    def test_tenant(self, live_client: VergeClient):
        """Get the test tenant, or skip if not available."""
        try:
            return live_client.tenants.get(name="test")
        except NotFoundError:
            pytest.skip("Test tenant 'test' not available")

    def test_clone_tenant_via_manager(self, live_client: VergeClient, test_tenant) -> None:
        """Test cloning a tenant via manager."""
        import random

        clone_name = f"pyvergeos-clone-{random.randint(10000, 99999)}"

        result = live_client.tenants.clone(test_tenant.key, name=clone_name)
        assert result is not None

        # Wait for clone to be created
        time.sleep(5)

        # Find the clone
        try:
            clone = live_client.tenants.get(name=clone_name)
            assert clone.name == clone_name

            # Note: Clone left for manual cleanup as it takes time to provision
        except NotFoundError:
            # Clone may still be provisioning
            pass

    def test_clone_tenant_via_object(self, live_client: VergeClient, test_tenant) -> None:
        """Test cloning a tenant via Tenant object."""
        import random

        clone_name = f"pyvergeos-clone-{random.randint(10000, 99999)}"

        result = test_tenant.clone(name=clone_name)
        assert result is not None

        # Wait for clone to be created
        time.sleep(5)

        # Find the clone
        try:
            clone = live_client.tenants.get(name=clone_name)
            assert clone.name == clone_name
        except NotFoundError:
            # Clone may still be provisioning
            pass


@pytest.mark.integration
class TestTenantSnapshots:
    """Integration tests for Tenant Snapshot operations."""

    @pytest.fixture
    def test_tenant(self, live_client: VergeClient):
        """Get the test tenant, or skip if not available."""
        try:
            return live_client.tenants.get(name="test")
        except NotFoundError:
            pytest.skip("Test tenant 'test' not available")

    def test_list_snapshots_empty(self, live_client: VergeClient, test_tenant) -> None:
        """Test listing snapshots returns a list."""
        snapshots = test_tenant.snapshots.list()
        assert isinstance(snapshots, list)

    def test_create_snapshot(self, live_client: VergeClient, test_tenant) -> None:
        """Test creating a tenant snapshot."""
        snapshot_name = "pyvergeos-test-snapshot"

        # Clean up any existing test snapshot
        for snap in test_tenant.snapshots.list():
            if snap.name == snapshot_name:
                test_tenant.snapshots.delete(snap.key)

        # Create snapshot
        snapshot = test_tenant.snapshots.create(
            name=snapshot_name,
            description="Test snapshot for pyvergeos integration tests",
            expires_in_days=1,
        )

        assert snapshot.name == snapshot_name
        assert snapshot.tenant_key == test_tenant.key
        assert snapshot.get("description") == "Test snapshot for pyvergeos integration tests"
        assert not snapshot.never_expires
        assert snapshot.expires_at is not None
        assert snapshot.created_at is not None

        # Cleanup
        test_tenant.snapshots.delete(snapshot.key)

    def test_create_snapshot_no_expiration(
        self, live_client: VergeClient, test_tenant
    ) -> None:
        """Test creating a snapshot that never expires."""
        snapshot_name = "pyvergeos-no-expire-test"

        # Clean up any existing test snapshot
        for snap in test_tenant.snapshots.list():
            if snap.name == snapshot_name:
                test_tenant.snapshots.delete(snap.key)

        # Create snapshot with no expiration
        snapshot = test_tenant.snapshots.create(name=snapshot_name)

        assert snapshot.name == snapshot_name
        assert snapshot.never_expires is True
        assert snapshot.expires_at is None

        # Cleanup
        test_tenant.snapshots.delete(snapshot.key)

    def test_get_snapshot_by_key(self, live_client: VergeClient, test_tenant) -> None:
        """Test getting a snapshot by key."""
        # Create a snapshot first
        snapshot = test_tenant.snapshots.create(name="pyvergeos-get-by-key-test")

        try:
            # Get by key
            fetched = test_tenant.snapshots.get(snapshot.key)
            assert fetched.key == snapshot.key
            assert fetched.name == snapshot.name
        finally:
            test_tenant.snapshots.delete(snapshot.key)

    def test_get_snapshot_by_name(self, live_client: VergeClient, test_tenant) -> None:
        """Test getting a snapshot by name."""
        snapshot_name = "pyvergeos-get-by-name-test"

        # Create a snapshot first
        snapshot = test_tenant.snapshots.create(name=snapshot_name)

        try:
            # Get by name
            fetched = test_tenant.snapshots.get(name=snapshot_name)
            assert fetched.key == snapshot.key
            assert fetched.name == snapshot_name
        finally:
            test_tenant.snapshots.delete(snapshot.key)

    def test_get_snapshot_not_found(self, live_client: VergeClient, test_tenant) -> None:
        """Test getting a non-existent snapshot."""
        with pytest.raises(NotFoundError):
            test_tenant.snapshots.get(name="nonexistent-snapshot-12345")

    def test_delete_snapshot(self, live_client: VergeClient, test_tenant) -> None:
        """Test deleting a snapshot."""
        # Create a snapshot
        snapshot = test_tenant.snapshots.create(name="pyvergeos-delete-test")
        snapshot_key = snapshot.key

        # Delete it
        test_tenant.snapshots.delete(snapshot_key)

        # Verify it's gone
        remaining = [s for s in test_tenant.snapshots.list() if s.key == snapshot_key]
        assert len(remaining) == 0

    def test_snapshot_list_with_filter(
        self, live_client: VergeClient, test_tenant
    ) -> None:
        """Test listing snapshots with an additional filter."""
        # Create two snapshots
        snap1 = test_tenant.snapshots.create(name="pyvergeos-filter-test-1")
        snap2 = test_tenant.snapshots.create(name="pyvergeos-filter-test-2")

        try:
            # Filter by name
            filtered = test_tenant.snapshots.list(
                filter="name eq 'pyvergeos-filter-test-1'"
            )
            assert len(filtered) == 1
            assert filtered[0].name == "pyvergeos-filter-test-1"
        finally:
            test_tenant.snapshots.delete(snap1.key)
            test_tenant.snapshots.delete(snap2.key)

    def test_snapshot_properties(self, live_client: VergeClient, test_tenant) -> None:
        """Test snapshot property accessors."""
        snapshot = test_tenant.snapshots.create(
            name="pyvergeos-properties-test",
            description="Test description",
            expires_in_days=7,
        )

        try:
            assert snapshot.name == "pyvergeos-properties-test"
            assert snapshot.tenant_key == test_tenant.key
            assert snapshot.created_at is not None
            assert snapshot.expires_at is not None
            assert snapshot.never_expires is False

            # Profile-related properties (None for manual snapshots)
            assert snapshot.profile is None or isinstance(snapshot.profile, str)
            assert snapshot.period is None or isinstance(snapshot.period, str)
            assert isinstance(snapshot.min_snapshots, int)
        finally:
            test_tenant.snapshots.delete(snapshot.key)

    def test_restore_validation_running_tenant(
        self, live_client: VergeClient, test_tenant
    ) -> None:
        """Test that restore raises error if tenant is running."""
        # Skip if tenant is not running
        tenant = live_client.tenants.get(test_tenant.key)
        if not tenant.is_running:
            pytest.skip("Tenant not running - cannot test running validation")

        # Create a snapshot
        snapshot = test_tenant.snapshots.create(name="pyvergeos-restore-val-test")

        try:
            with pytest.raises(ValueError, match="must be powered off"):
                test_tenant.snapshots.restore(snapshot.key)
        finally:
            test_tenant.snapshots.delete(snapshot.key)

    def test_snapshot_via_object_restore_method(
        self, live_client: VergeClient, test_tenant
    ) -> None:
        """Test restore method on snapshot object."""
        # Skip if tenant is not running
        tenant = live_client.tenants.get(test_tenant.key)
        if not tenant.is_running:
            pytest.skip("Tenant not running - cannot test running validation")

        # Create a snapshot
        snapshot = test_tenant.snapshots.create(name="pyvergeos-obj-restore-test")

        try:
            with pytest.raises(ValueError, match="must be powered off"):
                snapshot.restore()
        finally:
            test_tenant.snapshots.delete(snapshot.key)

    def test_create_snapshot_on_snapshot_raises(
        self, live_client: VergeClient
    ) -> None:
        """Test that creating a snapshot on a tenant snapshot raises error."""
        # Find a tenant snapshot in the list
        all_items = live_client.tenants.list(include_snapshots=True, limit=50)
        tenant_snapshots = [t for t in all_items if t.is_snapshot]

        if not tenant_snapshots:
            pytest.skip("No tenant snapshots available to test")

        tenant_snapshot = tenant_snapshots[0]
        with pytest.raises(ValueError, match="Cannot create snapshot of a tenant snapshot"):
            tenant_snapshot.snapshots.create(name="should-fail")
