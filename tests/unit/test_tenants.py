"""Unit tests for Tenant operations."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from pyvergeos import VergeClient
from pyvergeos.exceptions import NotFoundError
from pyvergeos.resources.tenants import Tenant, TenantManager


class TestTenantManager:
    """Unit tests for TenantManager."""

    def test_list_tenants(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test listing tenants."""
        mock_session.request.return_value.json.return_value = [
            {
                "$key": 1,
                "name": "tenant-1",
                "status": "online",
                "running": True,
                "is_snapshot": False,
            },
            {
                "$key": 2,
                "name": "tenant-2",
                "status": "offline",
                "running": False,
                "is_snapshot": False,
            },
        ]

        tenants = mock_client.tenants.list()

        assert len(tenants) == 2
        assert tenants[0].name == "tenant-1"
        assert tenants[1].name == "tenant-2"

    def test_list_tenants_excludes_snapshots_by_default(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test that list() adds filter to exclude snapshots."""
        mock_session.request.return_value.json.return_value = []

        mock_client.tenants.list()

        call_args = mock_session.request.call_args
        params = call_args.kwargs.get("params", {})
        assert "is_snapshot eq false" in params.get("filter", "")

    def test_list_tenants_include_snapshots(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test that include_snapshots=True doesn't add the filter."""
        mock_session.request.return_value.json.return_value = []

        mock_client.tenants.list(include_snapshots=True)

        call_args = mock_session.request.call_args
        params = call_args.kwargs.get("params", {})
        filter_value = params.get("filter", "")
        assert "is_snapshot" not in filter_value or filter_value is None

    def test_get_tenant_by_key(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test getting a tenant by key."""
        mock_session.request.return_value.json.return_value = {
            "$key": 123,
            "name": "test-tenant",
            "status": "online",
        }

        tenant = mock_client.tenants.get(123)

        assert tenant.key == 123
        assert tenant.name == "test-tenant"

    def test_get_tenant_by_name(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test getting a tenant by name."""
        mock_session.request.return_value.json.return_value = [
            {
                "$key": 456,
                "name": "my-tenant",
                "status": "offline",
            }
        ]

        tenant = mock_client.tenants.get(name="my-tenant")

        assert tenant.name == "my-tenant"
        assert tenant.key == 456

    def test_get_tenant_not_found(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test that NotFoundError is raised when tenant not found."""
        mock_session.request.return_value.json.return_value = []

        with pytest.raises(NotFoundError):
            mock_client.tenants.get(name="nonexistent")

    def test_get_tenant_requires_key_or_name(self, mock_client: VergeClient) -> None:
        """Test that ValueError is raised when neither key nor name provided."""
        with pytest.raises(ValueError, match="Either key or name must be provided"):
            mock_client.tenants.get()

    def test_create_tenant(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test creating a tenant."""
        mock_session.request.return_value.json.side_effect = [
            {"$key": 789, "name": "new-tenant"},
            {"$key": 789, "name": "new-tenant", "status": "offline"},
        ]

        tenant = mock_client.tenants.create(
            name="new-tenant",
            description="Test description",
            password="TestPass123!",
        )

        assert tenant.name == "new-tenant"
        assert tenant.key == 789

    def test_create_tenant_with_all_options(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test creating a tenant with all options."""
        mock_session.request.return_value.json.side_effect = [
            {"$key": 1, "name": "full-tenant"},
            {"$key": 1, "name": "full-tenant"},
        ]

        mock_client.tenants.create(
            name="full-tenant",
            password="Pass123!",
            description="Full description",
            url="https://example.com",
            note="Test note",
            expose_cloud_snapshots=False,
            allow_branding=True,
            require_password_change=True,
        )

        post_calls = [
            call
            for call in mock_session.request.call_args_list
            if call.kwargs.get("method") == "POST" and "tenants" in call.kwargs.get("url", "")
        ]
        assert len(post_calls) == 1
        body = post_calls[0].kwargs.get("json", {})
        assert body["name"] == "full-tenant"
        assert body["password"] == "Pass123!"
        assert body["description"] == "Full description"
        assert body["url"] == "https://example.com"
        assert body["note"] == "Test note"
        assert body["expose_cloud_snapshots"] is False
        assert body["allow_branding"] is True
        assert body["change_password"] is True

    def test_update_tenant(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test updating a tenant."""
        mock_session.request.return_value.json.return_value = {
            "$key": 123,
            "name": "updated-tenant",
            "description": "New description",
        }

        tenant = mock_client.tenants.update(123, description="New description")

        assert tenant.get("description") == "New description"

    def test_delete_tenant(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test deleting a tenant."""
        mock_session.request.return_value.status_code = 204
        mock_session.request.return_value.text = ""

        mock_client.tenants.delete(123)

        call_args = mock_session.request.call_args
        assert call_args.kwargs["method"] == "DELETE"
        assert "tenants/123" in call_args.kwargs["url"]

    def test_power_on_tenant(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test powering on a tenant via manager."""
        mock_session.request.return_value.json.return_value = {"$key": 1}

        result = mock_client.tenants.power_on(123)

        call_args = mock_session.request.call_args
        body = call_args.kwargs.get("json", {})
        assert body["tenant"] == 123
        assert body["action"] == "poweron"
        assert result == {"$key": 1}

    def test_power_on_tenant_with_preferred_node(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test powering on a tenant with preferred node."""
        mock_session.request.return_value.json.return_value = {}

        mock_client.tenants.power_on(123, preferred_node=5)

        call_args = mock_session.request.call_args
        body = call_args.kwargs.get("json", {})
        assert body["params"]["preferred_node"] == 5

    def test_power_off_tenant(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test powering off a tenant via manager."""
        mock_session.request.return_value.json.return_value = {"$key": 2}

        result = mock_client.tenants.power_off(123)

        call_args = mock_session.request.call_args
        body = call_args.kwargs.get("json", {})
        assert body["tenant"] == 123
        assert body["action"] == "poweroff"
        assert result == {"$key": 2}

    def test_reset_tenant(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test resetting a tenant via manager."""
        mock_session.request.return_value.json.return_value = {}

        mock_client.tenants.reset(123)

        call_args = mock_session.request.call_args
        body = call_args.kwargs.get("json", {})
        assert body["tenant"] == 123
        assert body["action"] == "reset"

    def test_restart_tenant(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test restart is alias for reset."""
        mock_session.request.return_value.json.return_value = {}

        mock_client.tenants.restart(123)

        call_args = mock_session.request.call_args
        body = call_args.kwargs.get("json", {})
        assert body["action"] == "reset"

    def test_clone_tenant(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test cloning a tenant."""
        mock_session.request.return_value.json.return_value = {"response": {"tenantkey": "456"}}

        mock_client.tenants.clone(123, name="clone-tenant")

        call_args = mock_session.request.call_args
        body = call_args.kwargs.get("json", {})
        assert body["tenant"] == 123
        assert body["action"] == "clone"
        assert body["params"]["name"] == "clone-tenant"

    def test_clone_tenant_with_exclusions(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test cloning a tenant with exclusion options."""
        mock_session.request.return_value.json.return_value = {}

        mock_client.tenants.clone(
            123,
            name="clone",
            no_network=True,
            no_storage=True,
            no_nodes=True,
        )

        call_args = mock_session.request.call_args
        body = call_args.kwargs.get("json", {})
        assert body["params"]["no_vnet"] is True
        assert body["params"]["no_storage"] is True
        assert body["params"]["no_nodes"] is True


class TestTenant:
    """Unit tests for Tenant object."""

    @pytest.fixture
    def tenant_data(self) -> dict[str, Any]:
        """Sample tenant data."""
        return {
            "$key": 100,
            "name": "test-tenant",
            "description": "Test description",
            "status": "online",
            "state": "online",
            "running": True,
            "starting": False,
            "stopping": False,
            "migrating": False,
            "is_snapshot": False,
            "isolate": False,
            "vnet": 50,
            "network_name": "tenant_test-tenant",
            "ui_address_ip": "192.168.10.100",
            "expose_cloud_snapshots": True,
            "allow_branding": False,
            "note": "Test note",
        }

    @pytest.fixture
    def mock_manager(self, mock_client: VergeClient) -> TenantManager:
        """Create a mock tenant manager."""
        return mock_client.tenants

    def test_tenant_properties(
        self, tenant_data: dict[str, Any], mock_manager: TenantManager
    ) -> None:
        """Test tenant property accessors."""
        tenant = Tenant(tenant_data, mock_manager)

        assert tenant.key == 100
        assert tenant.name == "test-tenant"
        assert tenant.status == "online"
        assert tenant.state == "online"
        assert tenant.is_running is True
        assert tenant.is_starting is False
        assert tenant.is_stopping is False
        assert tenant.is_migrating is False
        assert tenant.is_snapshot is False
        assert tenant.is_isolated is False
        assert tenant.network_name == "tenant_test-tenant"
        assert tenant.ui_address_ip == "192.168.10.100"

    def test_tenant_is_running_false(
        self, tenant_data: dict[str, Any], mock_manager: TenantManager
    ) -> None:
        """Test is_running when tenant is stopped."""
        tenant_data["running"] = False
        tenant = Tenant(tenant_data, mock_manager)

        assert tenant.is_running is False

    def test_tenant_is_snapshot_true(
        self, tenant_data: dict[str, Any], mock_manager: TenantManager
    ) -> None:
        """Test is_snapshot property."""
        tenant_data["is_snapshot"] = True
        tenant = Tenant(tenant_data, mock_manager)

        assert tenant.is_snapshot is True

    def test_tenant_is_isolated_true(
        self, tenant_data: dict[str, Any], mock_manager: TenantManager
    ) -> None:
        """Test is_isolated property."""
        tenant_data["isolate"] = True
        tenant = Tenant(tenant_data, mock_manager)

        assert tenant.is_isolated is True

    def test_power_on(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        tenant_data: dict[str, Any],
    ) -> None:
        """Test powering on a tenant."""
        tenant = Tenant(tenant_data, mock_client.tenants)

        tenant.power_on()

        call_args = mock_session.request.call_args
        body = call_args.kwargs.get("json", {})
        assert body["action"] == "poweron"
        assert body["tenant"] == 100

    def test_power_on_with_preferred_node(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        tenant_data: dict[str, Any],
    ) -> None:
        """Test powering on a tenant with preferred node."""
        tenant = Tenant(tenant_data, mock_client.tenants)

        tenant.power_on(preferred_node=5)

        call_args = mock_session.request.call_args
        body = call_args.kwargs.get("json", {})
        assert body["params"]["preferred_node"] == 5

    def test_power_on_snapshot_raises(
        self,
        mock_client: VergeClient,
        tenant_data: dict[str, Any],
    ) -> None:
        """Test that powering on a snapshot raises ValueError."""
        tenant_data["is_snapshot"] = True
        tenant = Tenant(tenant_data, mock_client.tenants)

        with pytest.raises(ValueError, match="Cannot power on a snapshot"):
            tenant.power_on()

    def test_power_off(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        tenant_data: dict[str, Any],
    ) -> None:
        """Test powering off a tenant."""
        tenant = Tenant(tenant_data, mock_client.tenants)

        tenant.power_off()

        call_args = mock_session.request.call_args
        body = call_args.kwargs.get("json", {})
        assert body["action"] == "poweroff"

    def test_power_off_snapshot_raises(
        self,
        mock_client: VergeClient,
        tenant_data: dict[str, Any],
    ) -> None:
        """Test that powering off a snapshot raises ValueError."""
        tenant_data["is_snapshot"] = True
        tenant = Tenant(tenant_data, mock_client.tenants)

        with pytest.raises(ValueError, match="Cannot power off a snapshot"):
            tenant.power_off()

    def test_reset(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        tenant_data: dict[str, Any],
    ) -> None:
        """Test resetting a tenant."""
        tenant = Tenant(tenant_data, mock_client.tenants)

        tenant.reset()

        call_args = mock_session.request.call_args
        body = call_args.kwargs.get("json", {})
        assert body["action"] == "reset"

    def test_reset_snapshot_raises(
        self,
        mock_client: VergeClient,
        tenant_data: dict[str, Any],
    ) -> None:
        """Test that resetting a snapshot raises ValueError."""
        tenant_data["is_snapshot"] = True
        tenant = Tenant(tenant_data, mock_client.tenants)

        with pytest.raises(ValueError, match="Cannot reset a snapshot"):
            tenant.reset()

    def test_restart(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        tenant_data: dict[str, Any],
    ) -> None:
        """Test restart is alias for reset."""
        tenant = Tenant(tenant_data, mock_client.tenants)

        tenant.restart()

        call_args = mock_session.request.call_args
        body = call_args.kwargs.get("json", {})
        assert body["action"] == "reset"

    def test_clone(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        tenant_data: dict[str, Any],
    ) -> None:
        """Test cloning a tenant."""
        mock_session.request.return_value.json.return_value = {"response": {"tenantkey": "101"}}

        tenant = Tenant(tenant_data, mock_client.tenants)
        tenant.clone(name="test-clone")

        call_args = mock_session.request.call_args
        body = call_args.kwargs.get("json", {})
        assert body["action"] == "clone"
        assert body["params"]["name"] == "test-clone"

    def test_clone_with_exclusions(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        tenant_data: dict[str, Any],
    ) -> None:
        """Test cloning a tenant with exclusions."""
        mock_session.request.return_value.json.return_value = {}

        tenant = Tenant(tenant_data, mock_client.tenants)
        tenant.clone(
            name="clone",
            no_network=True,
            no_storage=True,
            no_nodes=True,
        )

        call_args = mock_session.request.call_args
        body = call_args.kwargs.get("json", {})
        assert body["params"]["no_vnet"] is True
        assert body["params"]["no_storage"] is True
        assert body["params"]["no_nodes"] is True

    def test_clone_snapshot_raises(
        self,
        mock_client: VergeClient,
        tenant_data: dict[str, Any],
    ) -> None:
        """Test that cloning a snapshot raises ValueError."""
        tenant_data["is_snapshot"] = True
        tenant = Tenant(tenant_data, mock_client.tenants)

        with pytest.raises(ValueError, match="Cannot clone a snapshot"):
            tenant.clone(name="clone")

    def test_refresh(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        tenant_data: dict[str, Any],
    ) -> None:
        """Test refreshing tenant data."""
        mock_session.request.return_value.json.return_value = {
            **tenant_data,
            "status": "offline",
        }

        tenant = Tenant(tenant_data, mock_client.tenants)
        refreshed = tenant.refresh()

        assert refreshed.status == "offline"

    def test_save(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        tenant_data: dict[str, Any],
    ) -> None:
        """Test saving tenant changes."""
        mock_session.request.return_value.json.return_value = {
            **tenant_data,
            "description": "Updated description",
        }

        tenant = Tenant(tenant_data, mock_client.tenants)
        saved = tenant.save(description="Updated description")

        assert saved.description == "Updated description"


class TestTenantListHelpers:
    """Test tenant list helper methods."""

    def test_list_running(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test list_running method."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "name": "t1", "running": True, "starting": False, "is_snapshot": False},
            {"$key": 2, "name": "t2", "running": False, "starting": False, "is_snapshot": False},
            {"$key": 3, "name": "t3", "running": True, "starting": False, "is_snapshot": False},
        ]

        running = mock_client.tenants.list_running()

        assert len(running) == 2
        assert all(t.is_running for t in running)

    def test_list_stopped(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test list_stopped method."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "name": "t1", "running": True, "starting": False, "is_snapshot": False},
            {"$key": 2, "name": "t2", "running": False, "starting": False, "is_snapshot": False},
            {"$key": 3, "name": "t3", "running": False, "starting": True, "is_snapshot": False},
        ]

        stopped = mock_client.tenants.list_stopped()

        # t3 is starting, so only t2 should be in stopped list
        assert len(stopped) == 1
        assert stopped[0].name == "t2"

    def test_list_by_status(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test list_by_status method."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "name": "t1", "status": "online", "is_snapshot": False},
            {"$key": 2, "name": "t2", "status": "offline", "is_snapshot": False},
            {"$key": 3, "name": "t3", "status": "online", "is_snapshot": False},
        ]

        online = mock_client.tenants.list_by_status("online")

        assert len(online) == 2
        assert all(t.status == "online" for t in online)


class TestTenantDefaultFields:
    """Test that default fields are requested."""

    def test_list_uses_default_fields(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test that list() uses default fields."""
        mock_session.request.return_value.json.return_value = []

        mock_client.tenants.list()

        call_args = mock_session.request.call_args
        params = call_args.kwargs.get("params", {})
        fields = params.get("fields", "")
        # Check some expected default fields
        assert "$key" in fields
        assert "name" in fields
        assert "status#status" in fields

    def test_get_uses_default_fields(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test that get() uses default fields."""
        mock_session.request.return_value.json.return_value = {"$key": 1, "name": "t"}

        mock_client.tenants.get(1)

        call_args = mock_session.request.call_args
        params = call_args.kwargs.get("params", {})
        fields = params.get("fields", "")
        assert "$key" in fields
        assert "name" in fields
