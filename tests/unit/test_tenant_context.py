"""Unit tests for tenant context and shared objects."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from pyvergeos.resources.shared_objects import SharedObject, SharedObjectManager
from pyvergeos.resources.tenant_manager import Tenant, TenantManager


class TestTenantConnect:
    """Tests for Tenant.connect() method."""

    def test_connect_to_running_tenant(self) -> None:
        """Test connecting to a running tenant."""
        mock_client = MagicMock()
        mock_client._verify_ssl = False

        manager = TenantManager(mock_client)
        tenant = Tenant(
            {
                "$key": 123,
                "name": "test-tenant",
                "running": True,
                "is_snapshot": False,
                "ui_address_ip": "10.0.0.100",
            },
            manager,
        )

        with patch("pyvergeos.client.VergeClient") as MockClient:
            mock_tenant_client = MagicMock()
            MockClient.return_value = mock_tenant_client

            result = tenant.connect(username="admin", password="secret")

            MockClient.assert_called_once_with(
                host="10.0.0.100",
                username="admin",
                password="secret",
                verify_ssl=False,
                timeout=30,
            )
            assert result == mock_tenant_client

    def test_connect_fails_for_snapshot(self) -> None:
        """Test that connecting to a snapshot fails."""
        mock_client = MagicMock()
        manager = TenantManager(mock_client)
        tenant = Tenant(
            {
                "$key": 123,
                "name": "test-tenant",
                "running": True,
                "is_snapshot": True,
                "ui_address_ip": "10.0.0.100",
            },
            manager,
        )

        with pytest.raises(ValueError, match="Cannot connect to a tenant snapshot"):
            tenant.connect(username="admin", password="secret")

    def test_connect_fails_for_stopped_tenant(self) -> None:
        """Test that connecting to a stopped tenant fails."""
        mock_client = MagicMock()
        manager = TenantManager(mock_client)
        tenant = Tenant(
            {
                "$key": 123,
                "name": "test-tenant",
                "running": False,
                "is_snapshot": False,
                "ui_address_ip": "10.0.0.100",
            },
            manager,
        )

        with pytest.raises(ValueError, match="tenant is not running"):
            tenant.connect(username="admin", password="secret")

    def test_connect_fails_without_ui_address(self) -> None:
        """Test that connecting fails if no UI address is configured."""
        mock_client = MagicMock()
        manager = TenantManager(mock_client)
        tenant = Tenant(
            {
                "$key": 123,
                "name": "test-tenant",
                "running": True,
                "is_snapshot": False,
                "ui_address_ip": None,
            },
            manager,
        )

        with pytest.raises(ValueError, match="no UI address configured"):
            tenant.connect(username="admin", password="secret")

    def test_connect_with_custom_ssl_setting(self) -> None:
        """Test connecting with custom SSL verification setting."""
        mock_client = MagicMock()
        mock_client._verify_ssl = True

        manager = TenantManager(mock_client)
        tenant = Tenant(
            {
                "$key": 123,
                "name": "test-tenant",
                "running": True,
                "is_snapshot": False,
                "ui_address_ip": "10.0.0.100",
            },
            manager,
        )

        with patch("pyvergeos.client.VergeClient") as MockClient:
            MockClient.return_value = MagicMock()

            tenant.connect(username="admin", password="secret", verify_ssl=False)

            MockClient.assert_called_once_with(
                host="10.0.0.100",
                username="admin",
                password="secret",
                verify_ssl=False,
                timeout=30,
            )


class TestTenantManagerConnectContext:
    """Tests for TenantManager.connect_context() method."""

    def test_connect_context_by_key(self) -> None:
        """Test connecting to tenant context by key."""
        mock_client = MagicMock()
        mock_client._verify_ssl = False
        # GET by key returns a dict directly, not a list
        mock_client._request.return_value = {
            "$key": 123,
            "name": "test-tenant",
            "running": True,
            "is_snapshot": False,
            "ui_address_ip": "10.0.0.100",
        }

        manager = TenantManager(mock_client)

        with patch("pyvergeos.client.VergeClient") as MockClient:
            mock_tenant_client = MagicMock()
            MockClient.return_value = mock_tenant_client

            result = manager.connect_context(key=123, username="admin", password="secret")

            assert result == mock_tenant_client

    def test_connect_context_by_name(self) -> None:
        """Test connecting to tenant context by name."""
        mock_client = MagicMock()
        mock_client._verify_ssl = False
        mock_client._request.return_value = [
            {
                "$key": 123,
                "name": "test-tenant",
                "running": True,
                "is_snapshot": False,
                "ui_address_ip": "10.0.0.100",
            }
        ]

        manager = TenantManager(mock_client)

        with patch("pyvergeos.client.VergeClient") as MockClient:
            mock_tenant_client = MagicMock()
            MockClient.return_value = mock_tenant_client

            result = manager.connect_context(
                name="test-tenant", username="admin", password="secret"
            )

            assert result == mock_tenant_client


class TestSharedObject:
    """Tests for SharedObject resource."""

    def test_shared_object_properties(self) -> None:
        """Test SharedObject property accessors."""
        mock_manager = MagicMock()
        obj = SharedObject(
            {
                "$key": 42,
                "recipient": 123,
                "recipient_name": "Test Tenant",
                "type": "vm",
                "name": "My Template",
                "description": "A test template",
                "created": 1706400000,
                "inbox": True,
                "snapshot": "machine_snapshots/456",
                "id": "vms/789",
            },
            mock_manager,
        )

        assert obj.key == 42
        assert obj.tenant_key == 123
        assert obj.tenant_name == "Test Tenant"
        assert obj.object_type == "vm"
        assert obj.name == "My Template"
        assert obj.description == "A test template"
        assert obj.is_inbox is True
        assert obj.snapshot_path == "machine_snapshots/456"
        assert obj.snapshot_key == 456
        assert obj.object_id == "vms/789"
        assert obj.created_at is not None

    def test_shared_object_snapshot_key_parsing(self) -> None:
        """Test snapshot key parsing from path."""
        mock_manager = MagicMock()

        # Valid snapshot path
        obj = SharedObject({"$key": 1, "snapshot": "machine_snapshots/123"}, mock_manager)
        assert obj.snapshot_key == 123

        # No snapshot
        obj = SharedObject({"$key": 1, "snapshot": None}, mock_manager)
        assert obj.snapshot_key is None

        # Invalid format
        obj = SharedObject({"$key": 1, "snapshot": "invalid"}, mock_manager)
        assert obj.snapshot_key is None

    def test_shared_object_import(self) -> None:
        """Test SharedObject.import_object() method."""
        mock_manager = MagicMock()
        mock_manager.import_object.return_value = {"task": 999}

        obj = SharedObject({"$key": 42}, mock_manager)
        result = obj.import_object()

        mock_manager.import_object.assert_called_once_with(42)
        assert result == {"task": 999}

    def test_shared_object_delete(self) -> None:
        """Test SharedObject.delete() method."""
        mock_manager = MagicMock()
        obj = SharedObject({"$key": 42}, mock_manager)

        obj.delete()

        mock_manager.delete.assert_called_once_with(42)

    def test_shared_object_refresh(self) -> None:
        """Test SharedObject.refresh() method."""
        mock_manager = MagicMock()
        refreshed = SharedObject({"$key": 42, "name": "Refreshed"}, mock_manager)
        mock_manager.get.return_value = refreshed

        obj = SharedObject({"$key": 42, "name": "Original"}, mock_manager)
        result = obj.refresh()

        mock_manager.get.assert_called_once_with(42)
        assert result.name == "Refreshed"


class TestSharedObjectManager:
    """Tests for SharedObjectManager."""

    def test_list_shared_objects(self) -> None:
        """Test listing shared objects."""
        mock_client = MagicMock()
        mock_client._request.return_value = [
            {"$key": 1, "name": "Template 1", "recipient": 123},
            {"$key": 2, "name": "Template 2", "recipient": 123},
        ]

        manager = SharedObjectManager(mock_client)
        results = manager.list(tenant_key=123)

        assert len(results) == 2
        assert results[0].name == "Template 1"
        assert results[1].name == "Template 2"
        mock_client._request.assert_called_once()
        call_args = mock_client._request.call_args
        assert "recipient eq 123" in call_args[1]["params"]["filter"]

    def test_list_inbox_only(self) -> None:
        """Test listing inbox items only."""
        mock_client = MagicMock()
        mock_client._request.return_value = [
            {"$key": 1, "name": "Inbox Item", "recipient": 123, "inbox": True},
        ]

        manager = SharedObjectManager(mock_client)
        manager.list(tenant_key=123, inbox_only=True)

        call_args = mock_client._request.call_args
        assert "inbox eq true" in call_args[1]["params"]["filter"]

    def test_list_empty_response(self) -> None:
        """Test listing with no results."""
        mock_client = MagicMock()
        mock_client._request.return_value = None

        manager = SharedObjectManager(mock_client)
        results = manager.list(tenant_key=123)

        assert results == []

    def test_get_by_key(self) -> None:
        """Test getting shared object by key."""
        mock_client = MagicMock()
        mock_client._request.return_value = [
            {"$key": 42, "name": "My Template", "recipient": 123}
        ]

        manager = SharedObjectManager(mock_client)
        result = manager.get(42)

        assert result.key == 42
        assert result.name == "My Template"

    def test_get_by_tenant_and_name(self) -> None:
        """Test getting shared object by tenant key and name."""
        mock_client = MagicMock()
        mock_client._request.return_value = [
            {"$key": 42, "name": "My Template", "recipient": 123}
        ]

        manager = SharedObjectManager(mock_client)
        result = manager.get(tenant_key=123, name="My Template")

        assert result.key == 42
        assert result.name == "My Template"

    def test_get_not_found(self) -> None:
        """Test getting non-existent shared object."""
        mock_client = MagicMock()
        mock_client._request.return_value = []

        manager = SharedObjectManager(mock_client)

        with pytest.raises(Exception, match="not found"):
            manager.get(key=999)

    def test_get_requires_key_or_tenant_name(self) -> None:
        """Test that get() requires either key or tenant_key/name."""
        mock_client = MagicMock()
        manager = SharedObjectManager(mock_client)

        with pytest.raises(ValueError, match="Either key or tenant_key/name"):
            manager.get()

    def test_create_shared_object(self) -> None:
        """Test creating a shared object."""
        mock_client = MagicMock()
        # The create method now:
        # 1. Gets VM to get machine key
        # 2. Creates machine snapshot
        # 3. Creates shared object
        # 4. Gets the created shared object
        mock_client._request.side_effect = [
            {"$key": "99"},  # Create snapshot response
            {"$key": "42"},  # Create shared object response
            [{"$key": 42, "name": "VM Template", "recipient": 123}],  # Get response
        ]
        mock_vm = MagicMock()
        mock_vm.key = 456
        mock_vm.name = "VM Template"
        mock_vm.get.return_value = 789  # machine key
        mock_client.vms.get.return_value = mock_vm

        manager = SharedObjectManager(mock_client)
        result = manager.create(tenant_key=123, vm_key=456, name="VM Template")

        assert result.key == 42
        # Verify snapshot POST was called
        snapshot_call = mock_client._request.call_args_list[0]
        assert snapshot_call[0][0] == "POST"
        assert snapshot_call[0][1] == "machine_snapshots"
        assert snapshot_call[1]["json_data"]["machine"] == 789

        # Verify shared object POST was called with correct body
        shared_call = mock_client._request.call_args_list[1]
        assert shared_call[0][0] == "POST"
        assert shared_call[0][1] == "shared_objects"
        assert shared_call[1]["json_data"]["recipient"] == 123
        assert shared_call[1]["json_data"]["type"] == "vm"
        assert "machine_snapshots/99" in shared_call[1]["json_data"]["snapshot"]

    def test_create_with_vm_name(self) -> None:
        """Test creating shared object by VM name."""
        mock_client = MagicMock()
        mock_client._request.side_effect = [
            {"$key": "99"},  # Create snapshot response
            {"$key": "42"},  # Create shared object response
            [{"$key": 42, "name": "My VM", "recipient": 123}],  # Get response
        ]
        mock_vm = MagicMock()
        mock_vm.key = 456
        mock_vm.name = "My VM"
        mock_vm.get.return_value = 789  # machine key
        mock_client.vms.get.return_value = mock_vm

        manager = SharedObjectManager(mock_client)
        result = manager.create(tenant_key=123, vm_name="My VM")

        # Check that VM was looked up by name (first call)
        calls = mock_client.vms.get.call_args_list
        assert any(call.kwargs.get("name") == "My VM" for call in calls)
        assert result.key == 42

    def test_create_requires_tenant(self) -> None:
        """Test that create() requires tenant."""
        mock_client = MagicMock()
        manager = SharedObjectManager(mock_client)

        with pytest.raises(ValueError, match="Either tenant_key or tenant"):
            manager.create(vm_key=456)

    def test_create_requires_vm(self) -> None:
        """Test that create() requires VM."""
        mock_client = MagicMock()
        manager = SharedObjectManager(mock_client)

        with pytest.raises(ValueError, match="Either vm_key or vm_name"):
            manager.create(tenant_key=123)

    def test_import_object(self) -> None:
        """Test importing a shared object."""
        mock_client = MagicMock()
        mock_client._request.return_value = {"task": 999}

        manager = SharedObjectManager(mock_client)
        result = manager.import_object(42)

        mock_client._request.assert_called_once_with(
            "POST",
            "shared_object_actions",
            json_data={"shared_object": 42, "action": "import"},
        )
        assert result == {"task": 999}

    def test_refresh_object(self) -> None:
        """Test refreshing a shared object."""
        mock_client = MagicMock()
        mock_client._request.return_value = {"task": 999}

        manager = SharedObjectManager(mock_client)
        result = manager.refresh_object(42)

        mock_client._request.assert_called_once_with(
            "POST",
            "shared_object_actions",
            json_data={"shared_object": 42, "action": "refresh"},
        )
        assert result == {"task": 999}

    def test_delete_shared_object(self) -> None:
        """Test deleting a shared object."""
        mock_client = MagicMock()
        mock_client._request.return_value = None

        manager = SharedObjectManager(mock_client)
        manager.delete(42)

        mock_client._request.assert_called_once_with("DELETE", "shared_objects/42")

    def test_list_for_tenant(self) -> None:
        """Test list_for_tenant convenience method."""
        mock_client = MagicMock()
        mock_client._request.return_value = [
            {"$key": 1, "name": "Template", "recipient": 123}
        ]

        mock_tenant = MagicMock()
        mock_tenant.key = 123

        manager = SharedObjectManager(mock_client)
        results = manager.list_for_tenant(mock_tenant)

        assert len(results) == 1
        call_args = mock_client._request.call_args
        assert "recipient eq 123" in call_args[1]["params"]["filter"]


class TestTenantSharedObjectsProperty:
    """Tests for Tenant.shared_objects property."""

    def test_tenant_shared_objects_property(self) -> None:
        """Test accessing shared objects via tenant property."""
        mock_client = MagicMock()
        mock_client._request.return_value = [
            {"$key": 123, "name": "test-tenant"},
        ]
        mock_client.shared_objects.list.return_value = [
            MagicMock(name="Template 1"),
            MagicMock(name="Template 2"),
        ]

        manager = TenantManager(mock_client)
        tenant = Tenant({"$key": 456, "name": "test-tenant"}, manager)

        results = tenant.shared_objects

        mock_client.shared_objects.list.assert_called_once_with(tenant_key=456)
        assert len(results) == 2


class TestTenantManagerSharedObjects:
    """Tests for TenantManager.shared_objects() method."""

    def test_shared_objects_method(self) -> None:
        """Test TenantManager.shared_objects() method."""
        mock_client = MagicMock()
        mock_client.shared_objects.list.return_value = [
            MagicMock(name="Template 1"),
        ]

        manager = TenantManager(mock_client)
        results = manager.shared_objects(123)

        mock_client.shared_objects.list.assert_called_once_with(tenant_key=123)
        assert len(results) == 1
