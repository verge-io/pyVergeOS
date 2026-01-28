"""Integration tests for Tenant Context and Shared Objects."""

import time

import pytest

from pyvergeos import VergeClient
from pyvergeos.exceptions import NotFoundError


@pytest.mark.integration
class TestSharedObjects:
    """Integration tests for Shared Object operations."""

    @pytest.fixture
    def test_tenant(self, live_client: VergeClient):
        """Create a test tenant for shared object tests."""
        import random

        tenant_name = f"pysdk-shobj-integ-{random.randint(10000, 99999)}"

        tenant = live_client.tenants.create(
            name=tenant_name,
            description="Test tenant for shared object integration tests",
        )

        yield tenant

        # Cleanup: delete tenant
        import contextlib

        with contextlib.suppress(Exception):
            live_client.tenants.delete(tenant.key)

    @pytest.fixture
    def test_vm(self, live_client: VergeClient):
        """Get the existing test VM, or skip if not available."""
        try:
            return live_client.vms.get(name="test")
        except NotFoundError:
            pytest.skip("Test VM 'test' not available")

    def test_list_shared_objects_empty(
        self, live_client: VergeClient, test_tenant
    ) -> None:
        """Test listing shared objects for a new tenant returns empty list."""
        shared = live_client.shared_objects.list(tenant_key=test_tenant.key)
        assert isinstance(shared, list)
        assert len(shared) == 0

    def test_list_shared_objects_with_tenant_object(
        self, live_client: VergeClient, test_tenant
    ) -> None:
        """Test listing shared objects using tenant object."""
        shared = live_client.shared_objects.list(tenant=test_tenant)
        assert isinstance(shared, list)
        assert len(shared) == 0

    def test_list_for_tenant_method(
        self, live_client: VergeClient, test_tenant
    ) -> None:
        """Test list_for_tenant convenience method."""
        shared = live_client.shared_objects.list_for_tenant(test_tenant)
        assert isinstance(shared, list)
        assert len(shared) == 0

    def test_tenant_shared_objects_property(
        self, live_client: VergeClient, test_tenant
    ) -> None:
        """Test accessing shared objects via tenant property."""
        shared = test_tenant.shared_objects
        assert isinstance(shared, list)
        assert len(shared) == 0

    def test_manager_shared_objects_method(
        self, live_client: VergeClient, test_tenant
    ) -> None:
        """Test TenantManager.shared_objects() method."""
        shared = live_client.tenants.shared_objects(test_tenant.key)
        assert isinstance(shared, list)
        assert len(shared) == 0

    def test_create_shared_object(
        self, live_client: VergeClient, test_tenant, test_vm
    ) -> None:
        """Test creating a shared object (sharing a VM with a tenant)."""
        shared = live_client.shared_objects.create(
            tenant_key=test_tenant.key,
            vm_key=test_vm.key,
            name="Shared Test VM",
            description="Integration test shared object",
        )

        try:
            assert shared.name == "Shared Test VM"
            assert shared.tenant_key == test_tenant.key
            assert shared.object_type == "vm"
            # The id field is auto-set by the API (not the vms/{key} format)
            assert shared.object_id is not None
            assert shared.key > 0
            # Should have a snapshot reference
            assert shared.snapshot_path is not None
            assert "machine_snapshots" in shared.snapshot_path
        finally:
            # Cleanup
            live_client.shared_objects.delete(shared.key)

    def test_create_shared_object_with_tenant_object(
        self, live_client: VergeClient, test_tenant, test_vm
    ) -> None:
        """Test creating a shared object using tenant object."""
        shared = live_client.shared_objects.create(
            tenant=test_tenant,
            vm_key=test_vm.key,
            name="Shared Via Tenant Object",
        )

        try:
            assert shared.name == "Shared Via Tenant Object"
            assert shared.tenant_key == test_tenant.key
        finally:
            live_client.shared_objects.delete(shared.key)

    def test_create_shared_object_defaults_name_to_vm_name(
        self, live_client: VergeClient, test_tenant, test_vm
    ) -> None:
        """Test that shared object name defaults to VM name."""
        shared = live_client.shared_objects.create(
            tenant_key=test_tenant.key,
            vm_key=test_vm.key,
        )

        try:
            # Should default to VM name
            assert shared.name == test_vm.name
        finally:
            live_client.shared_objects.delete(shared.key)

    def test_get_shared_object_by_key(
        self, live_client: VergeClient, test_tenant, test_vm
    ) -> None:
        """Test getting a shared object by key."""
        created = live_client.shared_objects.create(
            tenant_key=test_tenant.key,
            vm_key=test_vm.key,
            name="Get By Key Test",
        )

        try:
            fetched = live_client.shared_objects.get(created.key)
            assert fetched.key == created.key
            assert fetched.name == "Get By Key Test"
        finally:
            live_client.shared_objects.delete(created.key)

    def test_get_shared_object_by_tenant_and_name(
        self, live_client: VergeClient, test_tenant, test_vm
    ) -> None:
        """Test getting a shared object by tenant key and name."""
        created = live_client.shared_objects.create(
            tenant_key=test_tenant.key,
            vm_key=test_vm.key,
            name="Get By Name Test",
        )

        try:
            fetched = live_client.shared_objects.get(
                tenant_key=test_tenant.key, name="Get By Name Test"
            )
            assert fetched.key == created.key
            assert fetched.name == "Get By Name Test"
        finally:
            live_client.shared_objects.delete(created.key)

    def test_get_shared_object_not_found(
        self, live_client: VergeClient, test_tenant
    ) -> None:
        """Test getting a non-existent shared object."""
        with pytest.raises(NotFoundError):
            live_client.shared_objects.get(
                tenant_key=test_tenant.key, name="NonExistent-12345"
            )

    def test_list_shared_objects_after_create(
        self, live_client: VergeClient, test_tenant, test_vm
    ) -> None:
        """Test listing shared objects after creating one."""
        created = live_client.shared_objects.create(
            tenant_key=test_tenant.key,
            vm_key=test_vm.key,
            name="List After Create Test",
        )

        try:
            shared_list = live_client.shared_objects.list(tenant_key=test_tenant.key)
            assert len(shared_list) == 1
            assert shared_list[0].name == "List After Create Test"
        finally:
            live_client.shared_objects.delete(created.key)

    def test_list_shared_objects_with_name_filter(
        self, live_client: VergeClient, test_tenant, test_vm
    ) -> None:
        """Test listing shared objects with name filter."""
        shared1 = live_client.shared_objects.create(
            tenant_key=test_tenant.key,
            vm_key=test_vm.key,
            name="Filter Test 1",
        )
        time.sleep(1)  # Brief delay to ensure distinct creates
        shared2 = live_client.shared_objects.create(
            tenant_key=test_tenant.key,
            vm_key=test_vm.key,
            name="Filter Test 2",
        )

        try:
            # Filter by name
            filtered = live_client.shared_objects.list(
                tenant_key=test_tenant.key, name="Filter Test 1"
            )
            assert len(filtered) == 1
            assert filtered[0].name == "Filter Test 1"
        finally:
            live_client.shared_objects.delete(shared1.key)
            live_client.shared_objects.delete(shared2.key)

    def test_delete_shared_object(
        self, live_client: VergeClient, test_tenant, test_vm
    ) -> None:
        """Test deleting a shared object."""
        shared = live_client.shared_objects.create(
            tenant_key=test_tenant.key,
            vm_key=test_vm.key,
            name="Delete Test",
        )
        shared_key = shared.key

        # Delete it
        live_client.shared_objects.delete(shared_key)

        # Verify deletion
        shared_list = live_client.shared_objects.list(tenant_key=test_tenant.key)
        assert len(shared_list) == 0

    def test_delete_shared_object_via_object(
        self, live_client: VergeClient, test_tenant, test_vm
    ) -> None:
        """Test deleting a shared object via object.delete() method."""
        shared = live_client.shared_objects.create(
            tenant_key=test_tenant.key,
            vm_key=test_vm.key,
            name="Object Delete Test",
        )

        # Delete via object method
        shared.delete()

        # Verify deletion
        shared_list = live_client.shared_objects.list(tenant_key=test_tenant.key)
        assert len(shared_list) == 0

    def test_shared_object_properties(
        self, live_client: VergeClient, test_tenant, test_vm
    ) -> None:
        """Test shared object property accessors."""
        shared = live_client.shared_objects.create(
            tenant_key=test_tenant.key,
            vm_key=test_vm.key,
            name="Properties Test",
            description="Test description",
        )

        try:
            # Test all properties
            assert shared.key > 0
            assert shared.name == "Properties Test"
            assert shared.description == "Test description"
            assert shared.tenant_key == test_tenant.key
            assert shared.tenant_name == test_tenant.name
            assert shared.object_type == "vm"
            # object_id is auto-set by the API (the id field)
            assert shared.object_id is not None
            # inbox should be False since it's not an inbox item
            assert shared.is_inbox is False
            # created_at should be set
            assert shared.created_at is not None
            # snapshot_path should be set since we created with a snapshot
            assert shared.snapshot_path is not None
            assert "machine_snapshots" in shared.snapshot_path
        finally:
            live_client.shared_objects.delete(shared.key)

    def test_refresh_shared_object(
        self, live_client: VergeClient, test_tenant, test_vm
    ) -> None:
        """Test refreshing a shared object."""
        shared = live_client.shared_objects.create(
            tenant_key=test_tenant.key,
            vm_key=test_vm.key,
            name="Refresh Test",
        )

        try:
            # Refresh the object
            refreshed = shared.refresh()
            assert refreshed.key == shared.key
            assert refreshed.name == "Refresh Test"
        finally:
            live_client.shared_objects.delete(shared.key)

    def test_multiple_shared_objects(
        self, live_client: VergeClient, test_tenant, test_vm
    ) -> None:
        """Test creating and managing multiple shared objects."""
        shared_objects = []
        try:
            # Create multiple shared objects
            for i in range(3):
                shared = live_client.shared_objects.create(
                    tenant_key=test_tenant.key,
                    vm_key=test_vm.key,
                    name=f"Multi Test {i + 1}",
                )
                shared_objects.append(shared)
                time.sleep(0.5)  # Brief delay to ensure distinct creates

            # Verify all are listed
            shared_list = live_client.shared_objects.list(tenant_key=test_tenant.key)
            assert len(shared_list) == 3

            # Verify names
            names = [s.name for s in shared_list]
            assert "Multi Test 1" in names
            assert "Multi Test 2" in names
            assert "Multi Test 3" in names
        finally:
            # Cleanup
            for shared in shared_objects:
                import contextlib

                with contextlib.suppress(Exception):
                    live_client.shared_objects.delete(shared.key)


@pytest.mark.integration
class TestTenantConnect:
    """Integration tests for Tenant Context connection.

    Note: These tests require a running tenant with known credentials.
    The tenant context tests are limited because we cannot easily
    create a tenant with known credentials and wait for it to be fully
    operational in a test environment.
    """

    def test_connect_validation_stopped_tenant(self, live_client: VergeClient) -> None:
        """Test that connecting to a stopped tenant raises error."""
        import random

        tenant_name = f"pysdk-connect-test-{random.randint(10000, 99999)}"

        tenant = live_client.tenants.create(
            name=tenant_name,
            description="Test tenant for connect validation",
        )

        try:
            # Tenant should be stopped by default
            tenant = live_client.tenants.get(tenant.key)
            if tenant.is_running:
                pytest.skip("Tenant is unexpectedly running")

            # Attempt to connect should fail
            with pytest.raises(ValueError, match="not running"):
                tenant.connect(username="admin", password="test")
        finally:
            # Cleanup
            import contextlib

            with contextlib.suppress(Exception):
                live_client.tenants.delete(tenant.key)

    def test_connect_validation_snapshot(self, live_client: VergeClient) -> None:
        """Test that connecting to a tenant snapshot raises error."""
        # Find any tenant snapshot
        all_items = live_client.tenants.list(include_snapshots=True, limit=50)
        snapshots = [t for t in all_items if t.is_snapshot]

        if not snapshots:
            pytest.skip("No tenant snapshots available")

        snapshot = snapshots[0]

        with pytest.raises(ValueError, match="snapshot"):
            snapshot.connect(username="admin", password="test")

    def test_connect_validation_no_ui_address(self, live_client: VergeClient) -> None:
        """Test that connecting to a tenant without UI address raises error."""
        import random

        tenant_name = f"pysdk-noui-test-{random.randint(10000, 99999)}"

        tenant = live_client.tenants.create(
            name=tenant_name,
            description="Test tenant for no UI address validation",
        )

        try:
            # Manually override running state for testing
            # Since Tenant is a dict subclass, we can modify directly
            tenant["running"] = True
            tenant["ui_address_ip"] = None

            with pytest.raises(ValueError, match="no UI address"):
                tenant.connect(username="admin", password="test")
        finally:
            # Cleanup
            import contextlib

            with contextlib.suppress(Exception):
                live_client.tenants.delete(tenant.key)

    def test_connect_context_by_name(self, live_client: VergeClient) -> None:
        """Test connect_context by name validates tenant state."""
        import random

        tenant_name = f"pysdk-ctx-name-{random.randint(10000, 99999)}"

        tenant = live_client.tenants.create(
            name=tenant_name,
            description="Test tenant for connect context by name",
        )

        try:
            # Connect should fail since tenant is stopped
            with pytest.raises(ValueError, match="not running"):
                live_client.tenants.connect_context(
                    name=tenant_name,
                    username="admin",
                    password="test",
                )
        finally:
            # Cleanup
            import contextlib

            with contextlib.suppress(Exception):
                live_client.tenants.delete(tenant.key)

    def test_connect_context_by_key(self, live_client: VergeClient) -> None:
        """Test connect_context by key validates tenant state."""
        import random

        tenant_name = f"pysdk-ctx-key-{random.randint(10000, 99999)}"

        tenant = live_client.tenants.create(
            name=tenant_name,
            description="Test tenant for connect context by key",
        )

        try:
            # Connect should fail since tenant is stopped
            with pytest.raises(ValueError, match="not running"):
                live_client.tenants.connect_context(
                    key=tenant.key,
                    username="admin",
                    password="test",
                )
        finally:
            # Cleanup
            import contextlib

            with contextlib.suppress(Exception):
                live_client.tenants.delete(tenant.key)


@pytest.mark.integration
@pytest.mark.skip(reason="Requires running tenant with known credentials")
class TestTenantConnectLive:
    """Integration tests for actual tenant context connection.

    These tests require a running tenant with known credentials.
    They are skipped by default and should be run manually when
    a properly configured tenant is available.

    To run these tests:
    1. Create a tenant and start it
    2. Note the tenant name and admin password
    3. Update the fixture below with the credentials
    4. Remove the skip marker and run the tests
    """

    @pytest.fixture
    def running_tenant_config(self):
        """Configuration for a running tenant.

        Update these values for your test environment.
        """
        return {
            "name": "test",
            "username": "admin",
            "password": "your-tenant-password",
        }

    def test_connect_to_running_tenant(
        self, live_client: VergeClient, running_tenant_config
    ) -> None:
        """Test connecting to a running tenant."""
        tenant = live_client.tenants.get(name=running_tenant_config["name"])

        if not tenant.is_running:
            pytest.skip("Tenant is not running")

        tenant_client = tenant.connect(
            username=running_tenant_config["username"],
            password=running_tenant_config["password"],
        )

        try:
            # Verify we can list VMs in the tenant
            vms = tenant_client.vms.list()
            assert isinstance(vms, list)

            # Verify client has tenant context markers
            assert tenant_client._is_tenant_context is True
            assert tenant_client._parent_tenant_name == tenant.name
        finally:
            tenant_client.disconnect()

    def test_connect_context_method(
        self, live_client: VergeClient, running_tenant_config
    ) -> None:
        """Test connecting via connect_context method."""
        tenant_client = live_client.tenants.connect_context(
            name=running_tenant_config["name"],
            username=running_tenant_config["username"],
            password=running_tenant_config["password"],
        )

        try:
            # Verify we're connected
            assert tenant_client.is_connected
            assert tenant_client._is_tenant_context is True
        finally:
            tenant_client.disconnect()
