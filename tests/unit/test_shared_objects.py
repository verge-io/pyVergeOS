"""Unit tests for shared object operations."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from pyvergeos import VergeClient
from pyvergeos.exceptions import NotFoundError
from pyvergeos.resources.shared_objects import SharedObject, SharedObjectManager


class TestSharedObjectManager:
    """Unit tests for SharedObjectManager."""

    def test_list_shared_objects(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test listing shared objects."""
        mock_session.request.return_value.json.return_value = [
            {
                "$key": 1,
                "name": "Ubuntu Template",
                "recipient": 10,
                "recipient_name": "tenant-a",
                "type": "vm",
                "inbox": False,
            },
            {
                "$key": 2,
                "name": "Windows Template",
                "recipient": 10,
                "recipient_name": "tenant-a",
                "type": "vm",
                "inbox": True,
            },
        ]

        shared = mock_client.shared_objects.list()

        assert len(shared) == 2
        assert shared[0].name == "Ubuntu Template"
        assert shared[1].name == "Windows Template"

    def test_list_shared_objects_empty(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test listing when no shared objects exist."""
        mock_session.request.return_value.json.return_value = None

        shared = mock_client.shared_objects.list()

        assert shared == []

    def test_list_shared_objects_by_tenant(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test filtering by tenant key."""
        mock_session.request.return_value.json.return_value = []

        mock_client.shared_objects.list(tenant_key=10)

        call_args = mock_session.request.call_args
        params = call_args.kwargs.get("params", {})
        assert "recipient eq 10" in params.get("filter", "")

    def test_list_shared_objects_by_name(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test filtering by name."""
        mock_session.request.return_value.json.return_value = []

        mock_client.shared_objects.list(name="Ubuntu Template")

        call_args = mock_session.request.call_args
        params = call_args.kwargs.get("params", {})
        assert "name eq 'Ubuntu Template'" in params.get("filter", "")

    def test_list_shared_objects_inbox_only(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test filtering for inbox items only."""
        mock_session.request.return_value.json.return_value = []

        mock_client.shared_objects.list(inbox_only=True)

        call_args = mock_session.request.call_args
        params = call_args.kwargs.get("params", {})
        assert "inbox eq true" in params.get("filter", "")

    def test_get_shared_object_by_key(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test getting a shared object by key."""
        mock_session.request.return_value.json.return_value = [
            {
                "$key": 1,
                "name": "Ubuntu Template",
                "recipient": 10,
                "type": "vm",
            }
        ]

        shared = mock_client.shared_objects.get(1)

        assert shared.key == 1
        assert shared.name == "Ubuntu Template"

    def test_get_shared_object_by_tenant_and_name(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test getting a shared object by tenant and name."""
        mock_session.request.return_value.json.return_value = [
            {
                "$key": 2,
                "name": "Windows Template",
                "recipient": 10,
                "type": "vm",
            }
        ]

        shared = mock_client.shared_objects.get(tenant_key=10, name="Windows Template")

        assert shared.name == "Windows Template"

    def test_get_shared_object_not_found_by_key(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test NotFoundError when shared object not found by key."""
        mock_session.request.return_value.json.return_value = []

        with pytest.raises(NotFoundError):
            mock_client.shared_objects.get(999)

    def test_get_shared_object_not_found_by_name(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test NotFoundError when shared object not found by name."""
        mock_session.request.return_value.json.return_value = []

        with pytest.raises(NotFoundError):
            mock_client.shared_objects.get(tenant_key=10, name="nonexistent")

    def test_get_shared_object_requires_key_or_tenant_name(self, mock_client: VergeClient) -> None:
        """Test ValueError when no identifier provided."""
        with pytest.raises(ValueError, match="Either key or tenant_key/name"):
            mock_client.shared_objects.get()

    def test_create_shared_object(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test creating a shared object."""
        # Responses: VM get, snapshot create, shared object create, get shared object
        mock_session.request.return_value.json.side_effect = [
            {"$key": 100, "name": "template-vm", "machine": 200},  # GET vm
            {"$key": 50, "name": "share-template-vm-12345"},  # POST snapshot
            {"$key": 1, "name": "template-vm"},  # POST shared_objects
            [{"$key": 1, "name": "template-vm", "recipient": 10}],  # GET shared_objects
        ]

        shared = mock_client.shared_objects.create(
            tenant_key=10,
            vm_key=100,
            name="template-vm",
            description="Shared template",
        )

        assert shared.name == "template-vm"

    def test_create_shared_object_requires_tenant(self, mock_client: VergeClient) -> None:
        """Test ValueError when tenant not provided."""
        with pytest.raises(ValueError, match="tenant_key or tenant"):
            mock_client.shared_objects.create(vm_key=100)

    def test_create_shared_object_requires_vm(self, mock_client: VergeClient) -> None:
        """Test ValueError when VM not provided."""
        with pytest.raises(ValueError, match="vm_key or vm_name"):
            mock_client.shared_objects.create(tenant_key=10)

    def test_import_object(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test importing a shared object."""
        mock_session.request.return_value.json.return_value = {"task": 123}

        result = mock_client.shared_objects.import_object(1)

        assert result == {"task": 123}
        post_calls = [
            call
            for call in mock_session.request.call_args_list
            if call.kwargs.get("method") == "POST"
        ]
        assert len(post_calls) == 1
        body = post_calls[0].kwargs.get("json", {})
        assert body["shared_object"] == 1
        assert body["action"] == "import"

    def test_refresh_object(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test refreshing a shared object."""
        mock_session.request.return_value.json.return_value = {"task": 124}

        result = mock_client.shared_objects.refresh_object(1)

        assert result == {"task": 124}
        post_calls = [
            call
            for call in mock_session.request.call_args_list
            if call.kwargs.get("method") == "POST"
        ]
        body = post_calls[0].kwargs.get("json", {})
        assert body["action"] == "refresh"

    def test_delete_shared_object(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test deleting a shared object."""
        mock_session.request.return_value.status_code = 204
        mock_session.request.return_value.text = ""

        mock_client.shared_objects.delete(1)

        call_args = mock_session.request.call_args
        assert call_args.kwargs["method"] == "DELETE"
        assert "shared_objects/1" in call_args.kwargs["url"]

    def test_list_for_tenant(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test list_for_tenant convenience method."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "name": "Template", "recipient": 10}
        ]

        # Create a mock tenant object
        from pyvergeos.resources.tenant_manager import Tenant

        tenant = Tenant({"$key": 10, "name": "tenant-a"}, mock_client.tenants)

        shared = mock_client.shared_objects.list_for_tenant(tenant)

        assert len(shared) == 1
        call_args = mock_session.request.call_args
        params = call_args.kwargs.get("params", {})
        assert "recipient eq 10" in params.get("filter", "")


class TestSharedObject:
    """Unit tests for SharedObject."""

    @pytest.fixture
    def shared_data(self) -> dict[str, Any]:
        """Sample shared object data."""
        return {
            "$key": 1,
            "name": "Ubuntu Template",
            "description": "Pre-configured Ubuntu server",
            "recipient": 10,
            "recipient_name": "tenant-a",
            "type": "vm",
            "id": "vms/100",
            "snapshot": "machine_snapshots/50",
            "inbox": False,
            "created": 1704067200,
        }

    @pytest.fixture
    def mock_manager(self, mock_client: VergeClient) -> SharedObjectManager:
        """Create a mock shared object manager."""
        return mock_client.shared_objects

    def test_shared_object_properties(
        self, shared_data: dict[str, Any], mock_manager: SharedObjectManager
    ) -> None:
        """Test SharedObject property accessors."""
        shared = SharedObject(shared_data, mock_manager)

        assert shared.key == 1
        assert shared.name == "Ubuntu Template"
        assert shared.description == "Pre-configured Ubuntu server"
        assert shared.tenant_key == 10
        assert shared.tenant_name == "tenant-a"
        assert shared.object_type == "vm"
        assert shared.object_id == "vms/100"
        assert shared.snapshot_path == "machine_snapshots/50"
        assert shared.snapshot_key == 50
        assert shared.is_inbox is False

    def test_shared_object_created_at(
        self, shared_data: dict[str, Any], mock_manager: SharedObjectManager
    ) -> None:
        """Test created_at timestamp property."""
        shared = SharedObject(shared_data, mock_manager)

        assert shared.created_at is not None
        assert shared.created_at.year == 2024

    def test_shared_object_created_at_none(self, mock_manager: SharedObjectManager) -> None:
        """Test created_at when not set."""
        shared = SharedObject({"$key": 1}, mock_manager)

        assert shared.created_at is None

    def test_shared_object_snapshot_key_none(self, mock_manager: SharedObjectManager) -> None:
        """Test snapshot_key when snapshot path not set."""
        shared = SharedObject({"$key": 1}, mock_manager)

        assert shared.snapshot_key is None

    def test_shared_object_snapshot_key_invalid_path(
        self, mock_manager: SharedObjectManager
    ) -> None:
        """Test snapshot_key with invalid snapshot path."""
        shared = SharedObject({"$key": 1, "snapshot": "invalid"}, mock_manager)

        assert shared.snapshot_key is None

    def test_shared_object_is_inbox_true(
        self, shared_data: dict[str, Any], mock_manager: SharedObjectManager
    ) -> None:
        """Test is_inbox when item is in inbox."""
        shared_data["inbox"] = True
        shared = SharedObject(shared_data, mock_manager)

        assert shared.is_inbox is True

    def test_shared_object_description_none(self, mock_manager: SharedObjectManager) -> None:
        """Test description when not set."""
        shared = SharedObject({"$key": 1, "name": "Test"}, mock_manager)

        assert shared.description is None

    def test_shared_object_tenant_name_none(self, mock_manager: SharedObjectManager) -> None:
        """Test tenant_name when not set."""
        shared = SharedObject({"$key": 1, "recipient": 10}, mock_manager)

        assert shared.tenant_name is None

    def test_shared_object_import(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test SharedObject import_object method."""
        mock_session.request.return_value.json.return_value = {"task": 125}

        shared = SharedObject({"$key": 1, "name": "Template"}, mock_client.shared_objects)

        result = shared.import_object()

        assert result == {"task": 125}

    def test_shared_object_refresh(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test SharedObject refresh method."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "name": "Template-updated"}
        ]

        shared = SharedObject({"$key": 1, "name": "Template"}, mock_client.shared_objects)

        refreshed = shared.refresh()

        assert refreshed.name == "Template-updated"

    def test_shared_object_delete(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test SharedObject delete method."""
        mock_session.request.return_value.status_code = 204
        mock_session.request.return_value.text = ""

        shared = SharedObject({"$key": 1, "name": "Template"}, mock_client.shared_objects)

        shared.delete()

        delete_calls = [
            call
            for call in mock_session.request.call_args_list
            if call.kwargs.get("method") == "DELETE"
        ]
        assert len(delete_calls) == 1
        assert "shared_objects/1" in delete_calls[0].kwargs["url"]


class TestSharedObjectDefaults:
    """Test default values for SharedObject properties."""

    @pytest.fixture
    def mock_manager(self, mock_client: VergeClient) -> SharedObjectManager:
        """Create a mock shared object manager."""
        return mock_client.shared_objects

    def test_defaults(self, mock_manager: SharedObjectManager) -> None:
        """Test default values for minimal shared object."""
        shared = SharedObject({"$key": 1}, mock_manager)

        assert shared.key == 1
        assert shared.name == ""
        assert shared.description is None
        assert shared.tenant_key == 0
        assert shared.tenant_name is None
        assert shared.object_type == "vm"
        assert shared.object_id is None
        assert shared.snapshot_path is None
        assert shared.snapshot_key is None
        assert shared.is_inbox is False
        assert shared.created_at is None
