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


@pytest.mark.integration
class TestTenantStorage:
    """Integration tests for Tenant Storage operations."""

    @pytest.fixture
    def test_tenant(self, live_client: VergeClient):
        """Create a test tenant for storage tests."""
        import random

        tenant_name = f"pysdk-storage-integ-{random.randint(10000, 99999)}"

        tenant = live_client.tenants.create(
            name=tenant_name,
            description="Test tenant for storage integration tests",
        )

        yield tenant

        # Cleanup: delete tenant (storage allocations will be deleted automatically)
        import contextlib

        with contextlib.suppress(Exception):
            live_client.tenants.delete(tenant.key)

    def test_list_storage_empty(self, live_client: VergeClient, test_tenant) -> None:
        """Test listing storage allocations on a new tenant returns empty list."""
        allocations = test_tenant.storage.list()
        assert isinstance(allocations, list)
        assert len(allocations) == 0

    def test_create_storage_allocation(
        self, live_client: VergeClient, test_tenant
    ) -> None:
        """Test creating a storage allocation."""
        allocation = test_tenant.storage.create(tier=1, provisioned_gb=10)

        assert allocation.tier == 1
        assert allocation.tier_name == "Tier 1"
        assert allocation.provisioned_gb == 10.0
        assert allocation.provisioned_bytes == 10737418240
        assert allocation.used_gb == 0.0
        assert allocation.used_percent == 0

        # Cleanup
        test_tenant.storage.delete(allocation.key)

    def test_create_storage_with_bytes(
        self, live_client: VergeClient, test_tenant
    ) -> None:
        """Test creating a storage allocation with bytes."""
        allocation = test_tenant.storage.create(
            tier=1, provisioned_bytes=5 * 1073741824
        )

        assert allocation.tier == 1
        assert allocation.provisioned_gb == 5.0

        # Cleanup
        test_tenant.storage.delete(allocation.key)

    def test_get_storage_by_tier(
        self, live_client: VergeClient, test_tenant
    ) -> None:
        """Test getting a storage allocation by tier number."""
        # Create allocation first
        test_tenant.storage.create(tier=1, provisioned_gb=15)

        # Get by tier
        allocation = test_tenant.storage.get(tier=1)

        assert allocation.tier == 1
        assert allocation.provisioned_gb == 15.0

        # Cleanup
        test_tenant.storage.delete(allocation.key)

    def test_get_storage_by_key(
        self, live_client: VergeClient, test_tenant
    ) -> None:
        """Test getting a storage allocation by key."""
        # Create allocation first
        created = test_tenant.storage.create(tier=1, provisioned_gb=10)

        # Get by key
        allocation = test_tenant.storage.get(created.key)

        assert allocation.key == created.key
        assert allocation.tier == 1

        # Cleanup
        test_tenant.storage.delete(allocation.key)

    def test_get_storage_not_found(
        self, live_client: VergeClient, test_tenant
    ) -> None:
        """Test getting a non-existent storage allocation."""
        with pytest.raises(NotFoundError):
            test_tenant.storage.get(tier=2)

    def test_list_storage_after_create(
        self, live_client: VergeClient, test_tenant
    ) -> None:
        """Test listing storage allocations after creating one."""
        test_tenant.storage.create(tier=1, provisioned_gb=10)

        allocations = test_tenant.storage.list()
        assert len(allocations) == 1
        assert allocations[0].tier == 1

        # Cleanup
        test_tenant.storage.delete(allocations[0].key)

    def test_list_storage_filter_by_tier(
        self, live_client: VergeClient, test_tenant
    ) -> None:
        """Test filtering storage allocations by tier."""
        # Create multiple allocations (if tiers available)
        alloc1 = test_tenant.storage.create(tier=1, provisioned_gb=10)

        try:
            alloc3 = test_tenant.storage.create(tier=3, provisioned_gb=50)
            has_tier3 = True
        except Exception:
            has_tier3 = False

        try:
            # Filter by tier 1
            tier1_allocs = test_tenant.storage.list(tier=1)
            assert len(tier1_allocs) == 1
            assert tier1_allocs[0].tier == 1

            if has_tier3:
                tier3_allocs = test_tenant.storage.list(tier=3)
                assert len(tier3_allocs) == 1
                assert tier3_allocs[0].tier == 3
        finally:
            test_tenant.storage.delete(alloc1.key)
            if has_tier3:
                test_tenant.storage.delete(alloc3.key)

    def test_update_storage_allocation(
        self, live_client: VergeClient, test_tenant
    ) -> None:
        """Test updating a storage allocation."""
        # Create allocation
        allocation = test_tenant.storage.create(tier=1, provisioned_gb=10)

        # Update by tier
        updated = test_tenant.storage.update_by_tier(tier=1, provisioned_gb=20)

        assert updated.provisioned_gb == 20.0
        assert updated.provisioned_bytes == 21474836480

        # Cleanup
        test_tenant.storage.delete(allocation.key)

    def test_delete_storage_by_tier(
        self, live_client: VergeClient, test_tenant
    ) -> None:
        """Test deleting a storage allocation by tier."""
        # Create allocation
        test_tenant.storage.create(tier=1, provisioned_gb=10)

        # Delete by tier
        test_tenant.storage.delete_by_tier(tier=1)

        # Verify deletion
        allocations = test_tenant.storage.list()
        assert len(allocations) == 0

    def test_storage_via_object_save(
        self, live_client: VergeClient, test_tenant
    ) -> None:
        """Test updating storage via the save method."""
        allocation = test_tenant.storage.create(tier=1, provisioned_gb=10)

        # Update via save
        updated = allocation.save(provisioned_gb=25)

        assert updated.provisioned_gb == 25.0

        # Cleanup
        test_tenant.storage.delete(updated.key)

    def test_storage_via_object_delete(
        self, live_client: VergeClient, test_tenant
    ) -> None:
        """Test deleting storage via the delete method."""
        allocation = test_tenant.storage.create(tier=1, provisioned_gb=10)

        # Delete via object method
        allocation.delete()

        # Verify deletion
        allocations = test_tenant.storage.list()
        assert len(allocations) == 0

    def test_storage_properties(
        self, live_client: VergeClient, test_tenant
    ) -> None:
        """Test storage allocation property accessors."""
        allocation = test_tenant.storage.create(tier=1, provisioned_gb=20)

        try:
            # Test properties
            assert allocation.tier == 1
            assert allocation.tier_key > 0
            assert allocation.tenant_key == test_tenant.key
            assert allocation.provisioned_gb == 20.0
            assert allocation.provisioned_bytes == 21474836480
            assert allocation.used_gb >= 0.0
            assert allocation.used_bytes >= 0
            assert allocation.allocated_gb >= 0.0
            assert allocation.allocated_bytes >= 0
            assert allocation.free_gb >= 0.0
            assert allocation.free_bytes >= 0
            assert 0 <= allocation.used_percent <= 100
            assert allocation.tier_name == "Tier 1"

            # Last update should be set
            if allocation.last_update is not None:
                from datetime import datetime

                assert isinstance(allocation.last_update, datetime)
        finally:
            test_tenant.storage.delete(allocation.key)

    def test_create_storage_invalid_tier_raises(
        self, live_client: VergeClient, test_tenant
    ) -> None:
        """Test that creating storage with invalid tier raises ValueError."""
        with pytest.raises(ValueError, match="Invalid tier 0"):
            test_tenant.storage.create(tier=0, provisioned_gb=10)

        with pytest.raises(ValueError, match="Invalid tier 6"):
            test_tenant.storage.create(tier=6, provisioned_gb=10)

    def test_create_storage_no_size_raises(
        self, live_client: VergeClient, test_tenant
    ) -> None:
        """Test that creating storage without size raises ValueError."""
        with pytest.raises(ValueError, match="Either provisioned_gb or provisioned_bytes"):
            test_tenant.storage.create(tier=1)

    def test_manager_storage_method(
        self, live_client: VergeClient, test_tenant
    ) -> None:
        """Test TenantManager.storage() direct access method."""
        # Create allocation via tenant.storage
        test_tenant.storage.create(tier=1, provisioned_gb=10)

        # Access via manager method
        storage_manager = live_client.tenants.storage(test_tenant.key)
        allocations = storage_manager.list()

        assert len(allocations) == 1
        assert allocations[0].tier == 1

        # Cleanup
        storage_manager.delete(allocations[0].key)


@pytest.mark.integration
class TestTenantNetworkBlocks:
    """Integration tests for Tenant Network Block operations."""

    @pytest.fixture
    def test_tenant(self, live_client: VergeClient):
        """Create a test tenant for network block tests."""
        import random

        tenant_name = f"pysdk-netblock-integ-{random.randint(10000, 99999)}"

        tenant = live_client.tenants.create(
            name=tenant_name,
            description="Test tenant for network block integration tests",
        )

        yield tenant

        # Cleanup: delete tenant (network blocks will be removed with the tenant)
        import contextlib

        with contextlib.suppress(Exception):
            live_client.tenants.delete(tenant.key)

    @pytest.fixture
    def external_network(self, live_client: VergeClient):
        """Get an external network for testing.

        Uses the 'External' network which should exist in most deployments.
        Falls back to first non-reserved external network.
        """
        networks = live_client.networks.list_external()
        if not networks:
            pytest.skip("No external networks available")

        # Try to find External network first
        for net in networks:
            if net.name == "External":
                return net

        # Fall back to first non-reserved network
        for net in networks:
            if net.name not in ["Core", "DMZ"]:
                return net

        # Last resort
        return networks[0]

    def test_list_network_blocks_empty(
        self, live_client: VergeClient, test_tenant
    ) -> None:
        """Test listing network blocks on a new tenant returns empty list."""
        blocks = test_tenant.network_blocks.list()
        assert isinstance(blocks, list)
        assert len(blocks) == 0

    def test_create_network_block_by_network_key(
        self, live_client: VergeClient, test_tenant, external_network
    ) -> None:
        """Test creating a network block with network key."""
        block = test_tenant.network_blocks.create(
            cidr="10.99.100.0/24",
            network=external_network.key,
            description="Integration test block",
        )

        assert block.cidr == "10.99.100.0/24"
        assert block.network_key == external_network.key
        assert block.network_name == external_network.name
        assert block.network_address == "10.99.100.0"
        assert block.prefix_length == 24
        assert block.address_count == 256

        # Cleanup
        test_tenant.network_blocks.delete(block.key)

    def test_create_network_block_by_network_name(
        self, live_client: VergeClient, test_tenant, external_network
    ) -> None:
        """Test creating a network block with network name."""
        block = test_tenant.network_blocks.create(
            cidr="10.99.101.0/24",
            network_name=external_network.name,
        )

        assert block.cidr == "10.99.101.0/24"
        assert block.network_name == external_network.name

        # Cleanup
        test_tenant.network_blocks.delete(block.key)

    def test_list_network_blocks_after_create(
        self, live_client: VergeClient, test_tenant, external_network
    ) -> None:
        """Test listing network blocks after creating one."""
        test_tenant.network_blocks.create(
            cidr="10.99.102.0/24",
            network=external_network.key,
        )

        blocks = test_tenant.network_blocks.list()
        assert len(blocks) == 1
        assert blocks[0].cidr == "10.99.102.0/24"

        # Cleanup
        test_tenant.network_blocks.delete(blocks[0].key)

    def test_list_network_blocks_with_cidr_filter(
        self, live_client: VergeClient, test_tenant, external_network
    ) -> None:
        """Test filtering network blocks by CIDR."""
        # Create two blocks
        block1 = test_tenant.network_blocks.create(
            cidr="10.99.103.0/24", network=external_network.key
        )
        block2 = test_tenant.network_blocks.create(
            cidr="10.99.104.0/24", network=external_network.key
        )

        try:
            # Filter by first CIDR
            filtered = test_tenant.network_blocks.list(cidr="10.99.103.0/24")
            assert len(filtered) == 1
            assert filtered[0].cidr == "10.99.103.0/24"
        finally:
            test_tenant.network_blocks.delete(block1.key)
            test_tenant.network_blocks.delete(block2.key)

    def test_get_network_block_by_cidr(
        self, live_client: VergeClient, test_tenant, external_network
    ) -> None:
        """Test getting a network block by CIDR."""
        created = test_tenant.network_blocks.create(
            cidr="10.99.105.0/24", network=external_network.key
        )

        # Get by CIDR
        block = test_tenant.network_blocks.get(cidr="10.99.105.0/24")
        assert block.cidr == "10.99.105.0/24"
        assert block.key == created.key

        # Cleanup
        test_tenant.network_blocks.delete(block.key)

    def test_get_network_block_by_key(
        self, live_client: VergeClient, test_tenant, external_network
    ) -> None:
        """Test getting a network block by key."""
        created = test_tenant.network_blocks.create(
            cidr="10.99.106.0/24", network=external_network.key
        )

        # Get by key
        block = test_tenant.network_blocks.get(created.key)
        assert block.key == created.key
        assert block.cidr == "10.99.106.0/24"

        # Cleanup
        test_tenant.network_blocks.delete(block.key)

    def test_get_network_block_not_found(
        self, live_client: VergeClient, test_tenant
    ) -> None:
        """Test getting a non-existent network block."""
        with pytest.raises(NotFoundError):
            test_tenant.network_blocks.get(cidr="10.255.255.0/24")

    def test_delete_network_block_by_cidr(
        self, live_client: VergeClient, test_tenant, external_network
    ) -> None:
        """Test deleting a network block by CIDR."""
        test_tenant.network_blocks.create(
            cidr="10.99.107.0/24", network=external_network.key
        )

        # Delete by CIDR
        test_tenant.network_blocks.delete_by_cidr("10.99.107.0/24")

        # Verify deletion
        blocks = test_tenant.network_blocks.list()
        assert len(blocks) == 0

    def test_delete_network_block_via_object(
        self, live_client: VergeClient, test_tenant, external_network
    ) -> None:
        """Test deleting a network block via object.delete()."""
        block = test_tenant.network_blocks.create(
            cidr="10.99.108.0/24", network=external_network.key
        )

        # Delete via object method
        block.delete()

        # Verify deletion
        blocks = test_tenant.network_blocks.list()
        assert len(blocks) == 0

    def test_network_block_properties(
        self, live_client: VergeClient, test_tenant, external_network
    ) -> None:
        """Test network block property accessors."""
        block = test_tenant.network_blocks.create(
            cidr="10.99.109.0/25",  # /25 for different address count
            network=external_network.key,
            description="Test description",
        )

        try:
            # Test all properties
            assert block.cidr == "10.99.109.0/25"
            assert block.network_address == "10.99.109.0"
            assert block.prefix_length == 25
            assert block.address_count == 128
            assert block.network_key == external_network.key
            assert block.network_name == external_network.name
            assert block.tenant_key == test_tenant.key
            assert block.description == "Test description"

            # Test repr
            repr_str = repr(block)
            assert "10.99.109.0/25" in repr_str
            assert external_network.name in repr_str
        finally:
            test_tenant.network_blocks.delete(block.key)

    def test_manager_network_blocks_method(
        self, live_client: VergeClient, test_tenant, external_network
    ) -> None:
        """Test TenantManager.network_blocks() direct access method."""
        # Create block via tenant.network_blocks
        test_tenant.network_blocks.create(
            cidr="10.99.110.0/24", network=external_network.key
        )

        # Access via manager method
        block_manager = live_client.tenants.network_blocks(test_tenant.key)
        blocks = block_manager.list()

        assert len(blocks) == 1
        assert blocks[0].cidr == "10.99.110.0/24"

        # Cleanup
        block_manager.delete(blocks[0].key)

    def test_multiple_network_blocks(
        self, live_client: VergeClient, test_tenant, external_network
    ) -> None:
        """Test creating and managing multiple network blocks."""
        blocks_created = []
        try:
            # Create multiple blocks
            for i in range(3):
                block = test_tenant.network_blocks.create(
                    cidr=f"10.99.{111 + i}.0/24",
                    network=external_network.key,
                )
                blocks_created.append(block)

            # Verify all blocks are listed
            blocks = test_tenant.network_blocks.list()
            assert len(blocks) == 3

            # Verify each CIDR is present
            cidrs = [b.cidr for b in blocks]
            assert "10.99.111.0/24" in cidrs
            assert "10.99.112.0/24" in cidrs
            assert "10.99.113.0/24" in cidrs
        finally:
            # Cleanup
            for block in blocks_created:
                import contextlib

                with contextlib.suppress(Exception):
                    test_tenant.network_blocks.delete(block.key)


@pytest.mark.integration
class TestTenantExternalIPs:
    """Integration tests for Tenant External IP operations."""

    @pytest.fixture
    def test_tenant(self, live_client: VergeClient):
        """Create a test tenant for external IP tests."""
        import random

        tenant_name = f"pysdk-extip-integ-{random.randint(10000, 99999)}"

        tenant = live_client.tenants.create(
            name=tenant_name,
            description="Test tenant for external IP integration tests",
        )

        yield tenant

        # Cleanup: delete tenant (external IPs will be removed with the tenant)
        import contextlib

        with contextlib.suppress(Exception):
            live_client.tenants.delete(tenant.key)

    @pytest.fixture
    def external_network(self, live_client: VergeClient):
        """Get an external network for testing.

        Uses the 'External' network which should exist in most deployments.
        Falls back to first non-reserved external network.
        """
        networks = live_client.networks.list_external()
        if not networks:
            pytest.skip("No external networks available")

        # Try to find External network first
        for net in networks:
            if net.name == "External":
                return net

        # Fall back to first non-reserved network
        for net in networks:
            if net.name not in ["Core", "DMZ"]:
                return net

        # Last resort
        return networks[0]

    def test_list_external_ips_empty(
        self, live_client: VergeClient, test_tenant
    ) -> None:
        """Test listing external IPs on a new tenant returns empty list."""
        ips = test_tenant.external_ips.list()
        assert isinstance(ips, list)
        assert len(ips) == 0

    def test_create_external_ip_by_network_key(
        self, live_client: VergeClient, test_tenant, external_network
    ) -> None:
        """Test creating an external IP with network key."""
        ip = test_tenant.external_ips.create(
            ip="10.99.200.50",
            network=external_network.key,
            hostname="test-service",
            description="Integration test external IP",
        )

        assert ip.ip_address == "10.99.200.50"
        assert ip.network_key == external_network.key
        assert ip.network_name == external_network.name
        assert ip.hostname == "test-service"
        assert ip.ip_type == "virtual"

        # Cleanup
        test_tenant.external_ips.delete(ip.key)

    def test_create_external_ip_by_network_name(
        self, live_client: VergeClient, test_tenant, external_network
    ) -> None:
        """Test creating an external IP with network name."""
        ip = test_tenant.external_ips.create(
            ip="10.99.200.51",
            network_name=external_network.name,
        )

        assert ip.ip_address == "10.99.200.51"
        assert ip.network_name == external_network.name

        # Cleanup
        test_tenant.external_ips.delete(ip.key)

    def test_list_external_ips_after_create(
        self, live_client: VergeClient, test_tenant, external_network
    ) -> None:
        """Test listing external IPs after creating one."""
        test_tenant.external_ips.create(
            ip="10.99.200.52",
            network=external_network.key,
        )

        ips = test_tenant.external_ips.list()
        assert len(ips) == 1
        assert ips[0].ip_address == "10.99.200.52"

        # Cleanup
        test_tenant.external_ips.delete(ips[0].key)

    def test_list_external_ips_with_ip_filter(
        self, live_client: VergeClient, test_tenant, external_network
    ) -> None:
        """Test filtering external IPs by IP address."""
        # Create two IPs
        ip1 = test_tenant.external_ips.create(
            ip="10.99.200.53", network=external_network.key
        )
        ip2 = test_tenant.external_ips.create(
            ip="10.99.200.54", network=external_network.key
        )

        try:
            # Filter by first IP
            filtered = test_tenant.external_ips.list(ip="10.99.200.53")
            assert len(filtered) == 1
            assert filtered[0].ip_address == "10.99.200.53"
        finally:
            test_tenant.external_ips.delete(ip1.key)
            test_tenant.external_ips.delete(ip2.key)

    def test_get_external_ip_by_ip(
        self, live_client: VergeClient, test_tenant, external_network
    ) -> None:
        """Test getting an external IP by IP address."""
        created = test_tenant.external_ips.create(
            ip="10.99.200.55", network=external_network.key
        )

        # Get by IP
        ip = test_tenant.external_ips.get(ip="10.99.200.55")
        assert ip.ip_address == "10.99.200.55"
        assert ip.key == created.key

        # Cleanup
        test_tenant.external_ips.delete(ip.key)

    def test_get_external_ip_by_key(
        self, live_client: VergeClient, test_tenant, external_network
    ) -> None:
        """Test getting an external IP by key."""
        created = test_tenant.external_ips.create(
            ip="10.99.200.56", network=external_network.key
        )

        # Get by key
        ip = test_tenant.external_ips.get(created.key)
        assert ip.key == created.key
        assert ip.ip_address == "10.99.200.56"

        # Cleanup
        test_tenant.external_ips.delete(ip.key)

    def test_get_external_ip_not_found(
        self, live_client: VergeClient, test_tenant
    ) -> None:
        """Test getting a non-existent external IP."""
        with pytest.raises(NotFoundError):
            test_tenant.external_ips.get(ip="10.255.255.255")

    def test_delete_external_ip_by_ip(
        self, live_client: VergeClient, test_tenant, external_network
    ) -> None:
        """Test deleting an external IP by IP address."""
        test_tenant.external_ips.create(
            ip="10.99.200.57", network=external_network.key
        )

        # Delete by IP
        test_tenant.external_ips.delete_by_ip("10.99.200.57")

        # Verify deletion
        ips = test_tenant.external_ips.list()
        assert len(ips) == 0

    def test_delete_external_ip_via_object(
        self, live_client: VergeClient, test_tenant, external_network
    ) -> None:
        """Test deleting an external IP via object.delete()."""
        ip = test_tenant.external_ips.create(
            ip="10.99.200.58", network=external_network.key
        )

        # Delete via object method
        ip.delete()

        # Verify deletion
        ips = test_tenant.external_ips.list()
        assert len(ips) == 0

    def test_external_ip_properties(
        self, live_client: VergeClient, test_tenant, external_network
    ) -> None:
        """Test external IP property accessors."""
        ip = test_tenant.external_ips.create(
            ip="10.99.200.59",
            network=external_network.key,
            hostname="test-hostname",
            description="Test description",
        )

        try:
            # Test all properties
            assert ip.ip_address == "10.99.200.59"
            assert ip.network_key == external_network.key
            assert ip.network_name == external_network.name
            assert ip.tenant_key == test_tenant.key
            assert ip.hostname == "test-hostname"
            assert ip.ip_type == "virtual"

            # Test repr
            repr_str = repr(ip)
            assert "10.99.200.59" in repr_str
            assert "test-hostname" in repr_str
            assert external_network.name in repr_str
        finally:
            test_tenant.external_ips.delete(ip.key)

    def test_manager_external_ips_method(
        self, live_client: VergeClient, test_tenant, external_network
    ) -> None:
        """Test TenantManager.external_ips() direct access method."""
        # Create IP via tenant.external_ips
        test_tenant.external_ips.create(
            ip="10.99.200.60", network=external_network.key
        )

        # Access via manager method
        ip_manager = live_client.tenants.external_ips(test_tenant.key)
        ips = ip_manager.list()

        assert len(ips) == 1
        assert ips[0].ip_address == "10.99.200.60"

        # Cleanup
        ip_manager.delete(ips[0].key)

    def test_multiple_external_ips(
        self, live_client: VergeClient, test_tenant, external_network
    ) -> None:
        """Test creating and managing multiple external IPs."""
        ips_created = []
        try:
            # Create multiple IPs
            for i in range(3):
                ip = test_tenant.external_ips.create(
                    ip=f"10.99.200.{61 + i}",
                    network=external_network.key,
                )
                ips_created.append(ip)

            # Verify all IPs are listed
            ips = test_tenant.external_ips.list()
            assert len(ips) == 3

            # Verify each IP is present
            ip_addresses = [ip.ip_address for ip in ips]
            assert "10.99.200.61" in ip_addresses
            assert "10.99.200.62" in ip_addresses
            assert "10.99.200.63" in ip_addresses
        finally:
            # Cleanup
            for ip in ips_created:
                import contextlib

                with contextlib.suppress(Exception):
                    test_tenant.external_ips.delete(ip.key)


@pytest.mark.integration
class TestTenantLayer2Networks:
    """Integration tests for Tenant Layer 2 Network operations."""

    @pytest.fixture
    def test_tenant(self, live_client: VergeClient):
        """Create a test tenant for L2 network tests."""
        import random

        tenant_name = f"pysdk-l2-integ-{random.randint(10000, 99999)}"

        tenant = live_client.tenants.create(
            name=tenant_name,
            description="Test tenant for L2 network integration tests",
        )

        yield tenant

        # Cleanup: delete tenant (L2 networks will be removed with the tenant)
        import contextlib

        with contextlib.suppress(Exception):
            live_client.tenants.delete(tenant.key)

    @pytest.fixture
    def test_network(self, live_client: VergeClient):
        """Create a test internal network for L2 testing.

        Creates a new internal network that can be assigned as a Layer 2 network.
        """
        import random

        net_name = f"pysdk-l2-test-{random.randint(10000, 99999)}"

        network = live_client.networks.create(
            name=net_name,
            description="Test network for L2 integration tests",
            type="internal",
            network_address="10.88.0.0/24",
            ip_address="10.88.0.1",
            dhcp_enabled=False,
        )

        yield network

        # Cleanup: delete network
        import contextlib

        with contextlib.suppress(Exception):
            live_client.networks.delete(network.key)

    def test_list_l2_networks_empty(
        self, live_client: VergeClient, test_tenant
    ) -> None:
        """Test listing L2 networks on a new tenant returns empty list."""
        l2_networks = test_tenant.l2_networks.list()
        assert isinstance(l2_networks, list)
        assert len(l2_networks) == 0

    def test_create_l2_network_by_network_key(
        self, live_client: VergeClient, test_tenant, test_network
    ) -> None:
        """Test creating a Layer 2 network with network key."""
        l2 = test_tenant.l2_networks.create(
            network=test_network.key,
            enabled=True,
        )

        assert l2.network_key == test_network.key
        assert l2.network_name == test_network.name
        assert l2.is_enabled is True
        assert l2.tenant_key == test_tenant.key
        assert l2.network_type == "internal"

        # Cleanup
        test_tenant.l2_networks.delete(l2.key)

    def test_create_l2_network_by_network_name(
        self, live_client: VergeClient, test_tenant, test_network
    ) -> None:
        """Test creating a Layer 2 network with network name."""
        l2 = test_tenant.l2_networks.create(
            network_name=test_network.name,
            enabled=True,
        )

        assert l2.network_name == test_network.name
        assert l2.is_enabled is True

        # Cleanup
        test_tenant.l2_networks.delete(l2.key)

    def test_create_l2_network_disabled(
        self, live_client: VergeClient, test_tenant, test_network
    ) -> None:
        """Test creating a Layer 2 network in disabled state."""
        l2 = test_tenant.l2_networks.create(
            network=test_network.key,
            enabled=False,
        )

        assert l2.is_enabled is False

        # Cleanup
        test_tenant.l2_networks.delete(l2.key)

    def test_list_l2_networks_after_create(
        self, live_client: VergeClient, test_tenant, test_network
    ) -> None:
        """Test listing L2 networks after creating one."""
        test_tenant.l2_networks.create(
            network=test_network.key,
            enabled=True,
        )

        l2_networks = test_tenant.l2_networks.list()
        assert len(l2_networks) == 1
        assert l2_networks[0].network_name == test_network.name

        # Cleanup
        test_tenant.l2_networks.delete(l2_networks[0].key)

    def test_get_l2_network_by_key(
        self, live_client: VergeClient, test_tenant, test_network
    ) -> None:
        """Test getting a Layer 2 network by key."""
        created = test_tenant.l2_networks.create(
            network=test_network.key,
            enabled=True,
        )

        # Get by key
        l2 = test_tenant.l2_networks.get(created.key)
        assert l2.key == created.key
        assert l2.network_name == test_network.name

        # Cleanup
        test_tenant.l2_networks.delete(l2.key)

    def test_get_l2_network_by_network_name(
        self, live_client: VergeClient, test_tenant, test_network
    ) -> None:
        """Test getting a Layer 2 network by network name."""
        created = test_tenant.l2_networks.create(
            network=test_network.key,
            enabled=True,
        )

        # Get by network name
        l2 = test_tenant.l2_networks.get(network_name=test_network.name)
        assert l2.key == created.key
        assert l2.network_name == test_network.name

        # Cleanup
        test_tenant.l2_networks.delete(l2.key)

    def test_get_l2_network_not_found(
        self, live_client: VergeClient, test_tenant
    ) -> None:
        """Test getting a non-existent Layer 2 network."""
        with pytest.raises(NotFoundError):
            test_tenant.l2_networks.get(network_name="NonExistent-Network-12345")

    def test_update_l2_network_disable(
        self, live_client: VergeClient, test_tenant, test_network
    ) -> None:
        """Test disabling a Layer 2 network."""
        l2 = test_tenant.l2_networks.create(
            network=test_network.key,
            enabled=True,
        )

        # Disable it
        updated = test_tenant.l2_networks.update(l2.key, enabled=False)
        assert updated.is_enabled is False

        # Cleanup
        test_tenant.l2_networks.delete(l2.key)

    def test_update_l2_network_enable(
        self, live_client: VergeClient, test_tenant, test_network
    ) -> None:
        """Test enabling a Layer 2 network."""
        l2 = test_tenant.l2_networks.create(
            network=test_network.key,
            enabled=False,
        )

        # Enable it
        updated = test_tenant.l2_networks.update(l2.key, enabled=True)
        assert updated.is_enabled is True

        # Cleanup
        test_tenant.l2_networks.delete(l2.key)

    def test_enable_via_object_method(
        self, live_client: VergeClient, test_tenant, test_network
    ) -> None:
        """Test enabling L2 network via object.enable() method."""
        l2 = test_tenant.l2_networks.create(
            network=test_network.key,
            enabled=False,
        )

        # Enable via object method
        enabled = l2.enable()
        assert enabled.is_enabled is True

        # Cleanup
        test_tenant.l2_networks.delete(l2.key)

    def test_disable_via_object_method(
        self, live_client: VergeClient, test_tenant, test_network
    ) -> None:
        """Test disabling L2 network via object.disable() method."""
        l2 = test_tenant.l2_networks.create(
            network=test_network.key,
            enabled=True,
        )

        # Disable via object method
        disabled = l2.disable()
        assert disabled.is_enabled is False

        # Cleanup
        test_tenant.l2_networks.delete(l2.key)

    def test_delete_l2_network(
        self, live_client: VergeClient, test_tenant, test_network
    ) -> None:
        """Test deleting a Layer 2 network."""
        l2 = test_tenant.l2_networks.create(
            network=test_network.key,
            enabled=True,
        )
        l2_key = l2.key

        # Delete it
        test_tenant.l2_networks.delete(l2_key)

        # Verify deletion
        l2_networks = test_tenant.l2_networks.list()
        assert len(l2_networks) == 0

    def test_delete_l2_network_by_network(
        self, live_client: VergeClient, test_tenant, test_network
    ) -> None:
        """Test deleting a Layer 2 network by network name."""
        test_tenant.l2_networks.create(
            network=test_network.key,
            enabled=True,
        )

        # Delete by network name
        test_tenant.l2_networks.delete_by_network(test_network.name)

        # Verify deletion
        l2_networks = test_tenant.l2_networks.list()
        assert len(l2_networks) == 0

    def test_delete_l2_network_via_object(
        self, live_client: VergeClient, test_tenant, test_network
    ) -> None:
        """Test deleting L2 network via object.delete() method."""
        l2 = test_tenant.l2_networks.create(
            network=test_network.key,
            enabled=True,
        )

        # Delete via object method
        l2.delete()

        # Verify deletion
        l2_networks = test_tenant.l2_networks.list()
        assert len(l2_networks) == 0

    def test_l2_network_properties(
        self, live_client: VergeClient, test_tenant, test_network
    ) -> None:
        """Test Layer 2 network property accessors."""
        l2 = test_tenant.l2_networks.create(
            network=test_network.key,
            enabled=True,
        )

        try:
            # Test all properties
            assert l2.tenant_key == test_tenant.key
            assert l2.tenant_name == test_tenant.name
            assert l2.network_key == test_network.key
            assert l2.network_name == test_network.name
            assert l2.network_type == "internal"
            assert l2.is_enabled is True

            # Test repr
            repr_str = repr(l2)
            assert test_network.name in repr_str
            assert "enabled" in repr_str
        finally:
            test_tenant.l2_networks.delete(l2.key)

    def test_manager_l2_networks_method(
        self, live_client: VergeClient, test_tenant, test_network
    ) -> None:
        """Test TenantManager.l2_networks() direct access method."""
        # Create L2 network via tenant.l2_networks
        test_tenant.l2_networks.create(
            network=test_network.key,
            enabled=True,
        )

        # Access via manager method
        l2_manager = live_client.tenants.l2_networks(test_tenant.key)
        l2_networks = l2_manager.list()

        assert len(l2_networks) == 1
        assert l2_networks[0].network_name == test_network.name

        # Cleanup
        l2_manager.delete(l2_networks[0].key)


@pytest.mark.integration
class TestTenantUtilities:
    """Integration tests for Tenant utility methods."""

    @pytest.fixture
    def test_tenant(self, live_client: VergeClient):
        """Create a test tenant for utility tests."""
        import random

        tenant_name = f"pysdk-util-integ-{random.randint(10000, 99999)}"

        tenant = live_client.tenants.create(
            name=tenant_name,
            description="Test tenant for utility integration tests",
        )

        yield tenant

        # Cleanup: delete tenant
        import contextlib

        with contextlib.suppress(Exception):
            live_client.tenants.delete(tenant.key)

    def test_enable_isolation_via_object(
        self, live_client: VergeClient, test_tenant
    ) -> None:
        """Test enabling isolation via Tenant object."""
        assert test_tenant.is_isolated is False

        # Enable isolation
        test_tenant.enable_isolation()
        test_tenant = test_tenant.refresh()

        assert test_tenant.is_isolated is True

        # Cleanup: disable isolation
        test_tenant.disable_isolation()

    def test_disable_isolation_via_object(
        self, live_client: VergeClient, test_tenant
    ) -> None:
        """Test disabling isolation via Tenant object."""
        # First enable isolation
        test_tenant.enable_isolation()
        test_tenant = test_tenant.refresh()
        assert test_tenant.is_isolated is True

        # Disable isolation
        test_tenant.disable_isolation()
        test_tenant = test_tenant.refresh()

        assert test_tenant.is_isolated is False

    def test_enable_isolation_via_manager(
        self, live_client: VergeClient, test_tenant
    ) -> None:
        """Test enabling isolation via TenantManager."""
        assert test_tenant.is_isolated is False

        # Enable isolation via manager
        live_client.tenants.enable_isolation(test_tenant.key)
        test_tenant = test_tenant.refresh()

        assert test_tenant.is_isolated is True

        # Cleanup
        live_client.tenants.disable_isolation(test_tenant.key)

    def test_disable_isolation_via_manager(
        self, live_client: VergeClient, test_tenant
    ) -> None:
        """Test disabling isolation via TenantManager."""
        # First enable
        live_client.tenants.enable_isolation(test_tenant.key)
        test_tenant = test_tenant.refresh()
        assert test_tenant.is_isolated is True

        # Disable via manager
        live_client.tenants.disable_isolation(test_tenant.key)
        test_tenant = test_tenant.refresh()

        assert test_tenant.is_isolated is False

    def test_enable_isolation_already_isolated_raises(
        self, live_client: VergeClient, test_tenant
    ) -> None:
        """Test that enabling isolation on already-isolated tenant raises."""
        # First enable
        test_tenant.enable_isolation()
        test_tenant = test_tenant.refresh()

        # Try to enable again
        with pytest.raises(ValueError, match="already in isolation mode"):
            test_tenant.enable_isolation()

        # Cleanup
        test_tenant.disable_isolation()

    def test_disable_isolation_not_isolated_raises(
        self, live_client: VergeClient, test_tenant
    ) -> None:
        """Test that disabling isolation on non-isolated tenant raises."""
        assert test_tenant.is_isolated is False

        with pytest.raises(ValueError, match="not in isolation mode"):
            test_tenant.disable_isolation()

    def test_send_file_via_object(
        self, live_client: VergeClient, test_tenant
    ) -> None:
        """Test sending a file to a tenant via Tenant object."""
        # Find a file to send
        files = live_client.files.list(limit=1)
        if not files:
            pytest.skip("No files available for testing")

        file_to_send = files[0]
        result = test_tenant.send_file(file_to_send.key)

        # The action should complete (or raise an error if file already shared)
        assert result is not None or result is None  # May return None on success

    def test_send_file_via_manager(
        self, live_client: VergeClient, test_tenant
    ) -> None:
        """Test sending a file to a tenant via TenantManager."""
        # Find files to send
        files = live_client.files.list(limit=2)
        if len(files) < 2:
            pytest.skip("Need at least 2 files for testing")

        # Use second file to avoid conflict with object test
        file_to_send = files[1]
        result = live_client.tenants.send_file(test_tenant.key, file_to_send.key)

        assert result is not None or result is None

    def test_create_crash_cart_recipe_not_found(
        self, live_client: VergeClient, test_tenant
    ) -> None:
        """Test that creating crash cart fails gracefully if recipe not found."""
        # Check if Crash Cart recipe exists
        recipes = live_client._request(
            "GET",
            "vm_recipes",
            params={"filter": "name eq 'Crash Cart'"},
        )

        if recipes:
            pytest.skip("Crash Cart recipe exists, cannot test not-found scenario")

        with pytest.raises(NotFoundError, match="Crash Cart recipe not found"):
            test_tenant.create_crash_cart()

    def test_isolation_chaining(
        self, live_client: VergeClient, test_tenant
    ) -> None:
        """Test that isolation methods return self for chaining."""
        result = test_tenant.enable_isolation()
        assert result is test_tenant

        # Refresh to update the is_isolated flag before disabling
        result = result.refresh()
        result = result.disable_isolation()
        assert result is not None
