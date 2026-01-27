"""Unit tests for Tenant operations."""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from pyvergeos import VergeClient
from pyvergeos.exceptions import NotFoundError
from pyvergeos.resources.tenants import (
    Tenant,
    TenantManager,
    TenantNetworkBlock,
    TenantNetworkBlockManager,
    TenantSnapshot,
    TenantSnapshotManager,
    TenantStorage,
    TenantStorageManager,
)


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


class TestTenantSnapshot:
    """Unit tests for TenantSnapshot object."""

    @pytest.fixture
    def snapshot_data(self) -> dict[str, Any]:
        """Sample tenant snapshot data."""
        return {
            "$key": 10,
            "tenant": 100,
            "name": "test-snapshot",
            "description": "Test snapshot description",
            "profile": "daily",
            "period": "daily",
            "min_snapshots": 7,
            "created": 1737900000,  # Unix timestamp
            "expires": 1738504800,  # Unix timestamp, 7 days later
        }

    @pytest.fixture
    def tenant_data(self) -> dict[str, Any]:
        """Sample tenant data."""
        return {
            "$key": 100,
            "name": "test-tenant",
            "status": "offline",
            "running": False,
            "is_snapshot": False,
        }

    def test_snapshot_properties(
        self, snapshot_data: dict[str, Any], mock_client: VergeClient, tenant_data: dict[str, Any]
    ) -> None:
        """Test snapshot property accessors."""
        tenant = Tenant(tenant_data, mock_client.tenants)
        manager = TenantSnapshotManager(mock_client, tenant)
        snapshot = TenantSnapshot(snapshot_data, manager)

        assert snapshot.key == 10
        assert snapshot.tenant_key == 100
        assert snapshot.name == "test-snapshot"
        assert snapshot.profile == "daily"
        assert snapshot.period == "daily"
        assert snapshot.min_snapshots == 7

    def test_snapshot_created_at(
        self, snapshot_data: dict[str, Any], mock_client: VergeClient, tenant_data: dict[str, Any]
    ) -> None:
        """Test created_at datetime conversion."""
        tenant = Tenant(tenant_data, mock_client.tenants)
        manager = TenantSnapshotManager(mock_client, tenant)
        snapshot = TenantSnapshot(snapshot_data, manager)

        created = snapshot.created_at
        assert created is not None
        assert isinstance(created, datetime)
        assert created.tzinfo == timezone.utc

    def test_snapshot_expires_at(
        self, snapshot_data: dict[str, Any], mock_client: VergeClient, tenant_data: dict[str, Any]
    ) -> None:
        """Test expires_at datetime conversion."""
        tenant = Tenant(tenant_data, mock_client.tenants)
        manager = TenantSnapshotManager(mock_client, tenant)
        snapshot = TenantSnapshot(snapshot_data, manager)

        expires = snapshot.expires_at
        assert expires is not None
        assert isinstance(expires, datetime)

    def test_snapshot_never_expires_false(
        self, snapshot_data: dict[str, Any], mock_client: VergeClient, tenant_data: dict[str, Any]
    ) -> None:
        """Test never_expires is False when expires is set."""
        tenant = Tenant(tenant_data, mock_client.tenants)
        manager = TenantSnapshotManager(mock_client, tenant)
        snapshot = TenantSnapshot(snapshot_data, manager)

        assert snapshot.never_expires is False

    def test_snapshot_never_expires_true(
        self, snapshot_data: dict[str, Any], mock_client: VergeClient, tenant_data: dict[str, Any]
    ) -> None:
        """Test never_expires is True when expires is 0."""
        snapshot_data["expires"] = 0
        tenant = Tenant(tenant_data, mock_client.tenants)
        manager = TenantSnapshotManager(mock_client, tenant)
        snapshot = TenantSnapshot(snapshot_data, manager)

        assert snapshot.never_expires is True
        assert snapshot.expires_at is None

    def test_snapshot_never_expires_none(
        self, snapshot_data: dict[str, Any], mock_client: VergeClient, tenant_data: dict[str, Any]
    ) -> None:
        """Test never_expires is True when expires is None."""
        snapshot_data["expires"] = None
        tenant = Tenant(tenant_data, mock_client.tenants)
        manager = TenantSnapshotManager(mock_client, tenant)
        snapshot = TenantSnapshot(snapshot_data, manager)

        assert snapshot.never_expires is True


class TestTenantSnapshotManager:
    """Unit tests for TenantSnapshotManager."""

    @pytest.fixture
    def tenant_data(self) -> dict[str, Any]:
        """Sample tenant data."""
        return {
            "$key": 100,
            "name": "test-tenant",
            "status": "offline",
            "running": False,
            "is_snapshot": False,
        }

    @pytest.fixture
    def snapshot_data(self) -> dict[str, Any]:
        """Sample snapshot data."""
        return {
            "$key": 10,
            "tenant": 100,
            "name": "test-snapshot",
            "description": "Test description",
            "created": 1737900000,
            "expires": 0,
        }

    def test_list_snapshots(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        tenant_data: dict[str, Any],
    ) -> None:
        """Test listing tenant snapshots."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "tenant": 100, "name": "snap1", "created": 1737900000},
            {"$key": 2, "tenant": 100, "name": "snap2", "created": 1737900100},
        ]

        tenant = Tenant(tenant_data, mock_client.tenants)
        snapshots = tenant.snapshots.list()

        assert len(snapshots) == 2
        assert snapshots[0].name == "snap1"
        assert snapshots[1].name == "snap2"

    def test_list_snapshots_filters_by_tenant(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        tenant_data: dict[str, Any],
    ) -> None:
        """Test that list() filters by tenant key."""
        mock_session.request.return_value.json.return_value = []

        tenant = Tenant(tenant_data, mock_client.tenants)
        tenant.snapshots.list()

        call_args = mock_session.request.call_args
        params = call_args.kwargs.get("params", {})
        assert "tenant eq 100" in params.get("filter", "")

    def test_list_snapshots_with_additional_filter(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        tenant_data: dict[str, Any],
    ) -> None:
        """Test list() combines tenant filter with additional filter."""
        mock_session.request.return_value.json.return_value = []

        tenant = Tenant(tenant_data, mock_client.tenants)
        tenant.snapshots.list(filter="name eq 'daily'")

        call_args = mock_session.request.call_args
        params = call_args.kwargs.get("params", {})
        filter_str = params.get("filter", "")
        assert "tenant eq 100" in filter_str
        assert "name eq 'daily'" in filter_str

    def test_get_snapshot_by_key(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        tenant_data: dict[str, Any],
        snapshot_data: dict[str, Any],
    ) -> None:
        """Test getting a snapshot by key."""
        mock_session.request.return_value.json.return_value = snapshot_data

        tenant = Tenant(tenant_data, mock_client.tenants)
        snapshot = tenant.snapshots.get(10)

        assert snapshot.key == 10
        assert snapshot.name == "test-snapshot"

    def test_get_snapshot_by_name(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        tenant_data: dict[str, Any],
        snapshot_data: dict[str, Any],
    ) -> None:
        """Test getting a snapshot by name."""
        mock_session.request.return_value.json.return_value = [snapshot_data]

        tenant = Tenant(tenant_data, mock_client.tenants)
        snapshot = tenant.snapshots.get(name="test-snapshot")

        assert snapshot.name == "test-snapshot"

    def test_get_snapshot_not_found(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        tenant_data: dict[str, Any],
    ) -> None:
        """Test NotFoundError when snapshot not found."""
        mock_session.request.return_value.json.return_value = []

        tenant = Tenant(tenant_data, mock_client.tenants)
        with pytest.raises(NotFoundError):
            tenant.snapshots.get(name="nonexistent")

    def test_get_snapshot_requires_key_or_name(
        self,
        mock_client: VergeClient,
        tenant_data: dict[str, Any],
    ) -> None:
        """Test ValueError when neither key nor name provided."""
        tenant = Tenant(tenant_data, mock_client.tenants)
        with pytest.raises(ValueError, match="Either key or name must be provided"):
            tenant.snapshots.get()

    @patch("time.sleep")
    def test_create_snapshot(
        self,
        mock_sleep: MagicMock,
        mock_client: VergeClient,
        mock_session: MagicMock,
        tenant_data: dict[str, Any],
        snapshot_data: dict[str, Any],
    ) -> None:
        """Test creating a snapshot."""
        mock_session.request.return_value.json.side_effect = [
            {},  # POST response
            [snapshot_data],  # GET to fetch created snapshot
        ]

        tenant = Tenant(tenant_data, mock_client.tenants)
        snapshot = tenant.snapshots.create(
            name="test-snapshot",
            description="Test description",
        )

        assert snapshot.name == "test-snapshot"

        # Find the POST request to tenant_snapshots
        post_call = None
        for call in mock_session.request.call_args_list:
            if (
                call.kwargs.get("method") == "POST"
                and "tenant_snapshots" in call.kwargs.get("url", "")
            ):
                post_call = call
                break

        assert post_call is not None
        body = post_call.kwargs.get("json", {})
        assert body["tenant"] == 100
        assert body["name"] == "test-snapshot"
        assert body["description"] == "Test description"

    @patch("time.sleep")
    def test_create_snapshot_with_expiration_days(
        self,
        mock_sleep: MagicMock,
        mock_client: VergeClient,
        mock_session: MagicMock,
        tenant_data: dict[str, Any],
        snapshot_data: dict[str, Any],
    ) -> None:
        """Test creating a snapshot with expiration in days."""
        mock_session.request.return_value.json.side_effect = [
            {},  # POST response
            [snapshot_data],  # GET to fetch created snapshot
        ]

        tenant = Tenant(tenant_data, mock_client.tenants)
        tenant.snapshots.create(name="test", expires_in_days=7)

        # Find the POST request to tenant_snapshots
        post_call = None
        for call in mock_session.request.call_args_list:
            if (
                call.kwargs.get("method") == "POST"
                and "tenant_snapshots" in call.kwargs.get("url", "")
            ):
                post_call = call
                break

        assert post_call is not None
        body = post_call.kwargs.get("json", {})
        # Should have an expires timestamp
        assert "expires" in body
        assert body["expires"] > int(time.time())

    @patch("time.sleep")
    def test_create_snapshot_with_expires_at(
        self,
        mock_sleep: MagicMock,
        mock_client: VergeClient,
        mock_session: MagicMock,
        tenant_data: dict[str, Any],
        snapshot_data: dict[str, Any],
    ) -> None:
        """Test creating a snapshot with specific expiration datetime."""
        mock_session.request.return_value.json.side_effect = [
            {},
            [snapshot_data],
        ]

        expire_time = datetime(2026, 2, 1, 12, 0, 0, tzinfo=timezone.utc)
        tenant = Tenant(tenant_data, mock_client.tenants)
        tenant.snapshots.create(name="test", expires_at=expire_time)

        # Find the POST request to tenant_snapshots
        post_call = None
        for call in mock_session.request.call_args_list:
            if (
                call.kwargs.get("method") == "POST"
                and "tenant_snapshots" in call.kwargs.get("url", "")
            ):
                post_call = call
                break

        assert post_call is not None
        body = post_call.kwargs.get("json", {})
        assert body["expires"] == int(expire_time.timestamp())

    def test_create_snapshot_on_snapshot_raises(
        self,
        mock_client: VergeClient,
        tenant_data: dict[str, Any],
    ) -> None:
        """Test creating snapshot on a tenant snapshot raises ValueError."""
        tenant_data["is_snapshot"] = True
        tenant = Tenant(tenant_data, mock_client.tenants)

        with pytest.raises(ValueError, match="Cannot create snapshot of a tenant snapshot"):
            tenant.snapshots.create(name="test")

    def test_delete_snapshot(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        tenant_data: dict[str, Any],
    ) -> None:
        """Test deleting a snapshot."""
        mock_session.request.return_value.status_code = 204

        tenant = Tenant(tenant_data, mock_client.tenants)
        tenant.snapshots.delete(10)

        call_args = mock_session.request.call_args
        assert call_args.kwargs["method"] == "DELETE"
        assert "tenant_snapshots/10" in call_args.kwargs["url"]

    def test_restore_snapshot(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        tenant_data: dict[str, Any],
    ) -> None:
        """Test restoring from a snapshot."""
        mock_session.request.return_value.json.side_effect = [
            tenant_data,  # Refresh tenant
            {},  # Restore response
        ]

        tenant = Tenant(tenant_data, mock_client.tenants)
        tenant.snapshots.restore(10)

        # Find the POST call to tenant_actions
        restore_call = None
        for call in mock_session.request.call_args_list:
            if "tenant_actions" in call.kwargs.get("url", ""):
                restore_call = call
                break

        assert restore_call is not None
        body = restore_call.kwargs.get("json", {})
        assert body["tenant"] == 100
        assert body["action"] == "restore"
        assert body["params"]["snapshot"] == 10

    def test_restore_running_tenant_raises(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        tenant_data: dict[str, Any],
    ) -> None:
        """Test that restore raises ValueError if tenant is running."""
        tenant_data["running"] = True
        mock_session.request.return_value.json.return_value = tenant_data

        tenant = Tenant(tenant_data, mock_client.tenants)
        with pytest.raises(ValueError, match="must be powered off"):
            tenant.snapshots.restore(10)


class TestTenantSnapshotViaObject:
    """Test snapshot operations via TenantSnapshot object."""

    @pytest.fixture
    def tenant_data(self) -> dict[str, Any]:
        """Sample tenant data."""
        return {
            "$key": 100,
            "name": "test-tenant",
            "status": "offline",
            "running": False,
            "is_snapshot": False,
        }

    @pytest.fixture
    def snapshot_data(self) -> dict[str, Any]:
        """Sample snapshot data."""
        return {
            "$key": 10,
            "tenant": 100,
            "name": "test-snapshot",
            "created": 1737900000,
            "expires": 0,
        }

    def test_snapshot_restore_method(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        tenant_data: dict[str, Any],
        snapshot_data: dict[str, Any],
    ) -> None:
        """Test restore via snapshot object."""
        mock_session.request.return_value.json.side_effect = [
            tenant_data,  # Refresh tenant
            {},  # Restore response
        ]

        tenant = Tenant(tenant_data, mock_client.tenants)
        manager = TenantSnapshotManager(mock_client, tenant)
        snapshot = TenantSnapshot(snapshot_data, manager)

        snapshot.restore()

        # Verify restore was called
        restore_call = None
        for call in mock_session.request.call_args_list:
            if "tenant_actions" in call.kwargs.get("url", ""):
                restore_call = call
                break

        assert restore_call is not None
        body = restore_call.kwargs.get("json", {})
        assert body["action"] == "restore"
        assert body["params"]["snapshot"] == 10


class TestTenantSnapshotsProperty:
    """Test accessing snapshots via tenant.snapshots property."""

    @pytest.fixture
    def tenant_data(self) -> dict[str, Any]:
        """Sample tenant data."""
        return {
            "$key": 100,
            "name": "test-tenant",
            "running": False,
            "is_snapshot": False,
        }

    def test_snapshots_property_returns_manager(
        self,
        mock_client: VergeClient,
        tenant_data: dict[str, Any],
    ) -> None:
        """Test that tenant.snapshots returns TenantSnapshotManager."""
        tenant = Tenant(tenant_data, mock_client.tenants)
        manager = tenant.snapshots

        assert isinstance(manager, TenantSnapshotManager)

    def test_snapshots_manager_has_correct_tenant(
        self,
        mock_client: VergeClient,
        tenant_data: dict[str, Any],
    ) -> None:
        """Test that snapshot manager references the correct tenant."""
        tenant = Tenant(tenant_data, mock_client.tenants)
        manager = tenant.snapshots

        assert manager._tenant.key == tenant.key


class TestTenantStorage:
    """Unit tests for TenantStorage object."""

    @pytest.fixture
    def storage_data(self) -> dict[str, Any]:
        """Sample storage allocation data."""
        return {
            "$key": 7,
            "tenant": 100,
            "tier": 1,
            "tier_number": 1,
            "tier_description": "Fast SSD",
            "provisioned": 10737418240,  # 10 GB
            "used": 1073741824,  # 1 GB
            "allocated": 2147483648,  # 2 GB
            "used_pct": 10,
            "last_update": 1737900000,
        }

    @pytest.fixture
    def tenant_data(self) -> dict[str, Any]:
        """Sample tenant data."""
        return {
            "$key": 100,
            "name": "test-tenant",
            "status": "offline",
            "running": False,
            "is_snapshot": False,
        }

    def test_storage_properties(
        self, storage_data: dict[str, Any], mock_client: VergeClient, tenant_data: dict[str, Any]
    ) -> None:
        """Test storage property accessors."""
        tenant = Tenant(tenant_data, mock_client.tenants)
        manager = TenantStorageManager(mock_client, tenant)
        storage = TenantStorage(storage_data, manager)

        assert storage.key == 7
        assert storage.tenant_key == 100
        assert storage.tier_key == 1
        assert storage.tier == 1
        assert storage.tier_name == "Tier 1"
        assert storage.tier_description == "Fast SSD"
        assert storage.provisioned_bytes == 10737418240
        assert storage.provisioned_gb == 10.0
        assert storage.used_bytes == 1073741824
        assert storage.used_gb == 1.0
        assert storage.allocated_bytes == 2147483648
        assert storage.allocated_gb == 2.0
        assert storage.used_percent == 10
        assert storage.free_bytes == 10737418240 - 1073741824
        assert storage.free_gb == round((10737418240 - 1073741824) / 1073741824, 2)

    def test_storage_last_update(
        self, storage_data: dict[str, Any], mock_client: VergeClient, tenant_data: dict[str, Any]
    ) -> None:
        """Test last_update datetime conversion."""
        tenant = Tenant(tenant_data, mock_client.tenants)
        manager = TenantStorageManager(mock_client, tenant)
        storage = TenantStorage(storage_data, manager)

        last_update = storage.last_update
        assert last_update is not None
        assert isinstance(last_update, datetime)
        assert last_update.tzinfo == timezone.utc

    def test_storage_repr(
        self, storage_data: dict[str, Any], mock_client: VergeClient, tenant_data: dict[str, Any]
    ) -> None:
        """Test storage __repr__."""
        tenant = Tenant(tenant_data, mock_client.tenants)
        manager = TenantStorageManager(mock_client, tenant)
        storage = TenantStorage(storage_data, manager)

        repr_str = repr(storage)
        assert "Tier 1" in repr_str
        assert "10.0" in repr_str
        assert "10%" in repr_str


class TestTenantStorageManager:
    """Unit tests for TenantStorageManager."""

    @pytest.fixture
    def tenant_data(self) -> dict[str, Any]:
        """Sample tenant data."""
        return {
            "$key": 100,
            "name": "test-tenant",
            "status": "offline",
            "running": False,
            "is_snapshot": False,
        }

    @pytest.fixture
    def storage_data(self) -> dict[str, Any]:
        """Sample storage allocation data."""
        return {
            "$key": 7,
            "tenant": 100,
            "tier": 1,
            "tier_number": 1,
            "tier_description": "Fast SSD",
            "provisioned": 10737418240,
            "used": 0,
            "allocated": 0,
            "used_pct": 0,
            "last_update": 1737900000,
        }

    def test_list_storage(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        tenant_data: dict[str, Any],
    ) -> None:
        """Test listing tenant storage allocations."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "tenant": 100, "tier_number": 1, "provisioned": 10737418240},
            {"$key": 2, "tenant": 100, "tier_number": 3, "provisioned": 53687091200},
        ]

        tenant = Tenant(tenant_data, mock_client.tenants)
        allocations = tenant.storage.list()

        assert len(allocations) == 2
        assert allocations[0].tier == 1
        assert allocations[1].tier == 3

    def test_list_storage_filters_by_tenant(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        tenant_data: dict[str, Any],
    ) -> None:
        """Test that list() filters by tenant key."""
        mock_session.request.return_value.json.return_value = []

        tenant = Tenant(tenant_data, mock_client.tenants)
        tenant.storage.list()

        call_args = mock_session.request.call_args
        params = call_args.kwargs.get("params", {})
        assert "tenant eq 100" in params.get("filter", "")

    def test_list_storage_with_tier_filter(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        tenant_data: dict[str, Any],
    ) -> None:
        """Test list() filters by tier number."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "tenant": 100, "tier_number": 1, "provisioned": 10737418240},
            {"$key": 2, "tenant": 100, "tier_number": 3, "provisioned": 53687091200},
        ]

        tenant = Tenant(tenant_data, mock_client.tenants)
        allocations = tenant.storage.list(tier=1)

        assert len(allocations) == 1
        assert allocations[0].tier == 1

    def test_get_storage_by_key(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        tenant_data: dict[str, Any],
        storage_data: dict[str, Any],
    ) -> None:
        """Test getting storage allocation by key."""
        mock_session.request.return_value.json.return_value = storage_data

        tenant = Tenant(tenant_data, mock_client.tenants)
        allocation = tenant.storage.get(7)

        assert allocation.key == 7
        assert allocation.tier == 1

    def test_get_storage_by_tier(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        tenant_data: dict[str, Any],
        storage_data: dict[str, Any],
    ) -> None:
        """Test getting storage allocation by tier number."""
        mock_session.request.return_value.json.return_value = [storage_data]

        tenant = Tenant(tenant_data, mock_client.tenants)
        allocation = tenant.storage.get(tier=1)

        assert allocation.tier == 1

    def test_get_storage_not_found(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        tenant_data: dict[str, Any],
    ) -> None:
        """Test NotFoundError when storage allocation not found."""
        mock_session.request.return_value.json.return_value = []

        tenant = Tenant(tenant_data, mock_client.tenants)
        with pytest.raises(NotFoundError):
            tenant.storage.get(tier=2)

    def test_get_storage_requires_key_or_tier(
        self,
        mock_client: VergeClient,
        tenant_data: dict[str, Any],
    ) -> None:
        """Test ValueError when neither key nor tier provided."""
        tenant = Tenant(tenant_data, mock_client.tenants)
        with pytest.raises(ValueError, match="Either key or tier must be provided"):
            tenant.storage.get()

    @patch("time.sleep")
    def test_create_storage(
        self,
        mock_sleep: MagicMock,
        mock_client: VergeClient,
        mock_session: MagicMock,
        tenant_data: dict[str, Any],
        storage_data: dict[str, Any],
    ) -> None:
        """Test creating a storage allocation."""
        mock_session.request.return_value.json.side_effect = [
            [{"$key": 1, "tier": 1}],  # GET storage_tiers
            {},  # POST response
            [storage_data],  # GET to fetch created allocation
        ]

        tenant = Tenant(tenant_data, mock_client.tenants)
        allocation = tenant.storage.create(tier=1, provisioned_gb=10)

        assert allocation.tier == 1
        assert allocation.provisioned_bytes == 10737418240

        # Find the POST request to tenant_storage
        post_call = None
        for call in mock_session.request.call_args_list:
            if (
                call.kwargs.get("method") == "POST"
                and "tenant_storage" in call.kwargs.get("url", "")
            ):
                post_call = call
                break

        assert post_call is not None
        body = post_call.kwargs.get("json", {})
        assert body["tenant"] == 100
        assert body["tier"] == 1
        assert body["provisioned"] == 10 * 1073741824

    @patch("time.sleep")
    def test_create_storage_with_bytes(
        self,
        mock_sleep: MagicMock,
        mock_client: VergeClient,
        mock_session: MagicMock,
        tenant_data: dict[str, Any],
        storage_data: dict[str, Any],
    ) -> None:
        """Test creating storage allocation with provisioned_bytes."""
        mock_session.request.return_value.json.side_effect = [
            [{"$key": 1, "tier": 1}],  # GET storage_tiers
            {},  # POST response
            [storage_data],  # GET to fetch created allocation
        ]

        tenant = Tenant(tenant_data, mock_client.tenants)
        tenant.storage.create(tier=1, provisioned_bytes=5368709120)

        # Find the POST request
        post_call = None
        for call in mock_session.request.call_args_list:
            if (
                call.kwargs.get("method") == "POST"
                and "tenant_storage" in call.kwargs.get("url", "")
            ):
                post_call = call
                break

        assert post_call is not None
        body = post_call.kwargs.get("json", {})
        assert body["provisioned"] == 5368709120

    def test_create_storage_on_snapshot_raises(
        self,
        mock_client: VergeClient,
        tenant_data: dict[str, Any],
    ) -> None:
        """Test creating storage on a tenant snapshot raises ValueError."""
        tenant_data["is_snapshot"] = True
        tenant = Tenant(tenant_data, mock_client.tenants)

        with pytest.raises(ValueError, match="Cannot add storage to a tenant snapshot"):
            tenant.storage.create(tier=1, provisioned_gb=10)

    def test_create_storage_invalid_tier_0_raises(
        self,
        mock_client: VergeClient,
        tenant_data: dict[str, Any],
    ) -> None:
        """Test creating storage with tier 0 raises ValueError."""
        tenant = Tenant(tenant_data, mock_client.tenants)

        with pytest.raises(ValueError, match="Invalid tier 0"):
            tenant.storage.create(tier=0, provisioned_gb=10)

    def test_create_storage_invalid_tier_6_raises(
        self,
        mock_client: VergeClient,
        tenant_data: dict[str, Any],
    ) -> None:
        """Test creating storage with tier 6 raises ValueError."""
        tenant = Tenant(tenant_data, mock_client.tenants)

        with pytest.raises(ValueError, match="Invalid tier 6"):
            tenant.storage.create(tier=6, provisioned_gb=10)

    def test_create_storage_no_size_raises(
        self,
        mock_client: VergeClient,
        tenant_data: dict[str, Any],
    ) -> None:
        """Test creating storage without size raises ValueError."""
        tenant = Tenant(tenant_data, mock_client.tenants)

        with pytest.raises(ValueError, match="Either provisioned_gb or provisioned_bytes"):
            tenant.storage.create(tier=1)

    def test_update_storage(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        tenant_data: dict[str, Any],
        storage_data: dict[str, Any],
    ) -> None:
        """Test updating a storage allocation."""
        mock_session.request.return_value.json.return_value = {
            **storage_data,
            "provisioned": 21474836480,
        }

        tenant = Tenant(tenant_data, mock_client.tenants)
        manager = TenantStorageManager(mock_client, tenant)
        allocation = manager.update(7, provisioned=21474836480)

        assert allocation.provisioned_bytes == 21474836480

    def test_update_storage_by_tier(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        tenant_data: dict[str, Any],
        storage_data: dict[str, Any],
    ) -> None:
        """Test updating storage allocation by tier."""
        mock_session.request.return_value.json.side_effect = [
            [storage_data],  # GET by tier
            {**storage_data, "provisioned": 21474836480},  # PUT response
            {**storage_data, "provisioned": 21474836480},  # GET updated
        ]

        tenant = Tenant(tenant_data, mock_client.tenants)
        allocation = tenant.storage.update_by_tier(tier=1, provisioned_gb=20)

        assert allocation.provisioned_bytes == 21474836480

    def test_update_by_tier_no_size_raises(
        self,
        mock_client: VergeClient,
        tenant_data: dict[str, Any],
    ) -> None:
        """Test update_by_tier without size raises ValueError."""
        tenant = Tenant(tenant_data, mock_client.tenants)

        with pytest.raises(ValueError, match="Either provisioned_gb or provisioned_bytes"):
            tenant.storage.update_by_tier(tier=1)

    def test_delete_storage(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        tenant_data: dict[str, Any],
    ) -> None:
        """Test deleting a storage allocation."""
        mock_session.request.return_value.status_code = 204

        tenant = Tenant(tenant_data, mock_client.tenants)
        tenant.storage.delete(7)

        call_args = mock_session.request.call_args
        assert call_args.kwargs["method"] == "DELETE"
        assert "tenant_storage/7" in call_args.kwargs["url"]

    def test_delete_storage_by_tier(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        tenant_data: dict[str, Any],
        storage_data: dict[str, Any],
    ) -> None:
        """Test deleting storage allocation by tier."""
        # Need to create separate mock responses for each call
        response1 = MagicMock()
        response1.json.return_value = [storage_data]
        response1.status_code = 200

        response2 = MagicMock()
        response2.status_code = 204
        response2.text = ""

        mock_session.request.side_effect = [response1, response2]

        tenant = Tenant(tenant_data, mock_client.tenants)
        tenant.storage.delete_by_tier(tier=1)

        # Find the DELETE call
        delete_call = None
        for call in mock_session.request.call_args_list:
            if call.kwargs.get("method") == "DELETE":
                delete_call = call
                break

        assert delete_call is not None
        assert "tenant_storage/7" in delete_call.kwargs["url"]


class TestTenantStorageViaObject:
    """Test storage operations via TenantStorage object."""

    @pytest.fixture
    def tenant_data(self) -> dict[str, Any]:
        """Sample tenant data."""
        return {
            "$key": 100,
            "name": "test-tenant",
            "status": "offline",
            "running": False,
            "is_snapshot": False,
        }

    @pytest.fixture
    def storage_data(self) -> dict[str, Any]:
        """Sample storage allocation data."""
        return {
            "$key": 7,
            "tenant": 100,
            "tier": 1,
            "tier_number": 1,
            "provisioned": 10737418240,
            "used": 0,
            "allocated": 0,
            "used_pct": 0,
        }

    def test_storage_save_method(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        tenant_data: dict[str, Any],
        storage_data: dict[str, Any],
    ) -> None:
        """Test save via storage object."""
        mock_session.request.return_value.json.return_value = {
            **storage_data,
            "provisioned": 21474836480,
        }

        tenant = Tenant(tenant_data, mock_client.tenants)
        manager = TenantStorageManager(mock_client, tenant)
        storage = TenantStorage(storage_data, manager)

        updated = storage.save(provisioned_gb=20)

        assert updated.provisioned_bytes == 21474836480

    def test_storage_delete_method(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        tenant_data: dict[str, Any],
        storage_data: dict[str, Any],
    ) -> None:
        """Test delete via storage object."""
        mock_session.request.return_value.status_code = 204

        tenant = Tenant(tenant_data, mock_client.tenants)
        manager = TenantStorageManager(mock_client, tenant)
        storage = TenantStorage(storage_data, manager)

        storage.delete()

        call_args = mock_session.request.call_args
        assert call_args.kwargs["method"] == "DELETE"
        assert "tenant_storage/7" in call_args.kwargs["url"]


class TestTenantStorageProperty:
    """Test accessing storage via tenant.storage property."""

    @pytest.fixture
    def tenant_data(self) -> dict[str, Any]:
        """Sample tenant data."""
        return {
            "$key": 100,
            "name": "test-tenant",
            "running": False,
            "is_snapshot": False,
        }

    def test_storage_property_returns_manager(
        self,
        mock_client: VergeClient,
        tenant_data: dict[str, Any],
    ) -> None:
        """Test that tenant.storage returns TenantStorageManager."""
        tenant = Tenant(tenant_data, mock_client.tenants)
        manager = tenant.storage

        assert isinstance(manager, TenantStorageManager)

    def test_storage_manager_has_correct_tenant(
        self,
        mock_client: VergeClient,
        tenant_data: dict[str, Any],
    ) -> None:
        """Test that storage manager references the correct tenant."""
        tenant = Tenant(tenant_data, mock_client.tenants)
        manager = tenant.storage

        assert manager._tenant.key == tenant.key


class TestTenantManagerStorageMethod:
    """Test TenantManager.storage() method."""

    @pytest.fixture
    def tenant_data(self) -> dict[str, Any]:
        """Sample tenant data."""
        return {
            "$key": 100,
            "name": "test-tenant",
            "running": False,
            "is_snapshot": False,
        }

    def test_storage_method_returns_manager(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        tenant_data: dict[str, Any],
    ) -> None:
        """Test that tenants.storage(key) returns TenantStorageManager."""
        mock_session.request.return_value.json.return_value = tenant_data

        manager = mock_client.tenants.storage(100)

        assert isinstance(manager, TenantStorageManager)
        assert manager._tenant.key == 100


# =============================================================================
# TenantNetworkBlock Tests
# =============================================================================


class TestTenantNetworkBlock:
    """Unit tests for TenantNetworkBlock resource object."""

    @pytest.fixture
    def block_data(self) -> dict[str, Any]:
        """Sample network block data."""
        return {
            "$key": 42,
            "vnet": 3,
            "network_name": "External",
            "cidr": "192.168.100.0/24",
            "description": "Test block",
            "owner": "tenants/100",
        }

    def test_tenant_key_from_owner(self, block_data: dict[str, Any]) -> None:
        """Test extracting tenant key from owner field."""
        block = TenantNetworkBlock(block_data, None)  # type: ignore[arg-type]
        assert block.tenant_key == 100

    def test_tenant_key_invalid_owner(self) -> None:
        """Test tenant_key with invalid owner."""
        block = TenantNetworkBlock({"owner": "vms/123"}, None)  # type: ignore[arg-type]
        assert block.tenant_key == 0

    def test_tenant_key_empty_owner(self) -> None:
        """Test tenant_key with empty owner."""
        block = TenantNetworkBlock({}, None)  # type: ignore[arg-type]
        assert block.tenant_key == 0

    def test_network_key(self, block_data: dict[str, Any]) -> None:
        """Test network_key property."""
        block = TenantNetworkBlock(block_data, None)  # type: ignore[arg-type]
        assert block.network_key == 3

    def test_network_name(self, block_data: dict[str, Any]) -> None:
        """Test network_name property."""
        block = TenantNetworkBlock(block_data, None)  # type: ignore[arg-type]
        assert block.network_name == "External"

    def test_cidr(self, block_data: dict[str, Any]) -> None:
        """Test cidr property."""
        block = TenantNetworkBlock(block_data, None)  # type: ignore[arg-type]
        assert block.cidr == "192.168.100.0/24"

    def test_cidr_empty(self) -> None:
        """Test cidr with no data."""
        block = TenantNetworkBlock({}, None)  # type: ignore[arg-type]
        assert block.cidr == ""

    def test_network_address(self, block_data: dict[str, Any]) -> None:
        """Test network_address property."""
        block = TenantNetworkBlock(block_data, None)  # type: ignore[arg-type]
        assert block.network_address == "192.168.100.0"

    def test_network_address_no_slash(self) -> None:
        """Test network_address without prefix."""
        block = TenantNetworkBlock({"cidr": "10.0.0.0"}, None)  # type: ignore[arg-type]
        assert block.network_address == "10.0.0.0"

    def test_prefix_length(self, block_data: dict[str, Any]) -> None:
        """Test prefix_length property."""
        block = TenantNetworkBlock(block_data, None)  # type: ignore[arg-type]
        assert block.prefix_length == 24

    def test_prefix_length_no_slash(self) -> None:
        """Test prefix_length without prefix."""
        block = TenantNetworkBlock({"cidr": "10.0.0.0"}, None)  # type: ignore[arg-type]
        assert block.prefix_length == 0

    def test_address_count_24(self, block_data: dict[str, Any]) -> None:
        """Test address_count for /24 block."""
        block = TenantNetworkBlock(block_data, None)  # type: ignore[arg-type]
        assert block.address_count == 256

    def test_address_count_16(self) -> None:
        """Test address_count for /16 block."""
        block = TenantNetworkBlock({"cidr": "10.0.0.0/16"}, None)  # type: ignore[arg-type]
        assert block.address_count == 65536

    def test_address_count_32(self) -> None:
        """Test address_count for /32 block."""
        block = TenantNetworkBlock({"cidr": "10.0.0.1/32"}, None)  # type: ignore[arg-type]
        assert block.address_count == 1

    def test_address_count_no_prefix(self) -> None:
        """Test address_count without prefix."""
        block = TenantNetworkBlock({"cidr": "10.0.0.0"}, None)  # type: ignore[arg-type]
        assert block.address_count == 0

    def test_repr(self, block_data: dict[str, Any]) -> None:
        """Test __repr__ method."""
        block = TenantNetworkBlock(block_data, None)  # type: ignore[arg-type]
        repr_str = repr(block)
        assert "192.168.100.0/24" in repr_str
        assert "External" in repr_str


class TestTenantNetworkBlockManager:
    """Unit tests for TenantNetworkBlockManager."""

    @pytest.fixture
    def tenant_data(self) -> dict[str, Any]:
        """Sample tenant data."""
        return {
            "$key": 100,
            "name": "test-tenant",
            "status": "offline",
            "running": False,
            "is_snapshot": False,
        }

    @pytest.fixture
    def block_data(self) -> dict[str, Any]:
        """Sample network block data."""
        return {
            "$key": 42,
            "vnet": 3,
            "network_name": "External",
            "cidr": "192.168.100.0/24",
            "description": "Test block",
            "owner": "tenants/100",
        }

    def test_list_network_blocks(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        tenant_data: dict[str, Any],
    ) -> None:
        """Test listing tenant network blocks."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "cidr": "10.0.0.0/24", "vnet": 3, "owner": "tenants/100"},
            {"$key": 2, "cidr": "10.0.1.0/24", "vnet": 3, "owner": "tenants/100"},
        ]

        tenant = Tenant(tenant_data, mock_client.tenants)
        blocks = tenant.network_blocks.list()

        assert len(blocks) == 2
        assert blocks[0].cidr == "10.0.0.0/24"
        assert blocks[1].cidr == "10.0.1.0/24"

    def test_list_network_blocks_filters_by_owner(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        tenant_data: dict[str, Any],
    ) -> None:
        """Test that list() filters by tenant owner."""
        mock_session.request.return_value.json.return_value = []

        tenant = Tenant(tenant_data, mock_client.tenants)
        tenant.network_blocks.list()

        call_args = mock_session.request.call_args
        params = call_args.kwargs.get("params", {})
        assert "owner eq 'tenants/100'" in params.get("filter", "")

    def test_list_network_blocks_with_cidr_filter(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        tenant_data: dict[str, Any],
    ) -> None:
        """Test list() with CIDR filter."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "cidr": "10.0.0.0/24", "vnet": 3, "owner": "tenants/100"},
        ]

        tenant = Tenant(tenant_data, mock_client.tenants)
        tenant.network_blocks.list(cidr="10.0.0.0/24")

        call_args = mock_session.request.call_args
        params = call_args.kwargs.get("params", {})
        filter_value = params.get("filter", "")
        assert "cidr eq '10.0.0.0/24'" in filter_value

    def test_list_network_blocks_empty(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        tenant_data: dict[str, Any],
    ) -> None:
        """Test list() returns empty list when no blocks."""
        mock_session.request.return_value.json.return_value = None

        tenant = Tenant(tenant_data, mock_client.tenants)
        blocks = tenant.network_blocks.list()

        assert blocks == []

    def test_get_network_block_by_key(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        tenant_data: dict[str, Any],
        block_data: dict[str, Any],
    ) -> None:
        """Test getting network block by key."""
        mock_session.request.return_value.json.return_value = block_data

        tenant = Tenant(tenant_data, mock_client.tenants)
        block = tenant.network_blocks.get(42)

        assert block.key == 42
        assert block.cidr == "192.168.100.0/24"

    def test_get_network_block_by_cidr(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        tenant_data: dict[str, Any],
        block_data: dict[str, Any],
    ) -> None:
        """Test getting network block by CIDR."""
        mock_session.request.return_value.json.return_value = [block_data]

        tenant = Tenant(tenant_data, mock_client.tenants)
        block = tenant.network_blocks.get(cidr="192.168.100.0/24")

        assert block.cidr == "192.168.100.0/24"

    def test_get_network_block_not_found(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        tenant_data: dict[str, Any],
    ) -> None:
        """Test NotFoundError when network block not found."""
        mock_session.request.return_value.json.return_value = []

        tenant = Tenant(tenant_data, mock_client.tenants)
        with pytest.raises(NotFoundError):
            tenant.network_blocks.get(cidr="10.99.99.0/24")

    def test_get_network_block_not_found_by_key(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        tenant_data: dict[str, Any],
    ) -> None:
        """Test NotFoundError when network block key not found."""
        mock_session.request.return_value.json.return_value = None

        tenant = Tenant(tenant_data, mock_client.tenants)
        with pytest.raises(NotFoundError):
            tenant.network_blocks.get(999)

    def test_get_network_block_requires_key_or_cidr(
        self,
        mock_client: VergeClient,
        tenant_data: dict[str, Any],
    ) -> None:
        """Test ValueError when neither key nor cidr provided."""
        tenant = Tenant(tenant_data, mock_client.tenants)
        with pytest.raises(ValueError, match="Either key or cidr must be provided"):
            tenant.network_blocks.get()

    @patch("time.sleep")
    def test_create_network_block_by_network_key(
        self,
        mock_sleep: MagicMock,
        mock_client: VergeClient,
        mock_session: MagicMock,
        tenant_data: dict[str, Any],
        block_data: dict[str, Any],
    ) -> None:
        """Test creating a network block with network key."""
        mock_session.request.return_value.json.side_effect = [
            {},  # POST response
            [block_data],  # GET to fetch created block
        ]

        tenant = Tenant(tenant_data, mock_client.tenants)
        block = tenant.network_blocks.create(
            cidr="192.168.100.0/24",
            network=3,
            description="Test block",
        )

        assert block.cidr == "192.168.100.0/24"

        # Find the POST request to vnet_cidrs
        post_call = None
        for call in mock_session.request.call_args_list:
            if (
                call.kwargs.get("method") == "POST"
                and "vnet_cidrs" in call.kwargs.get("url", "")
            ):
                post_call = call
                break

        assert post_call is not None
        body = post_call.kwargs.get("json", {})
        assert body["vnet"] == 3
        assert body["cidr"] == "192.168.100.0/24"
        assert body["owner"] == "tenants/100"
        assert body["description"] == "Test block"

    @patch("time.sleep")
    def test_create_network_block_by_network_name(
        self,
        mock_sleep: MagicMock,
        mock_client: VergeClient,
        mock_session: MagicMock,
        tenant_data: dict[str, Any],
        block_data: dict[str, Any],
    ) -> None:
        """Test creating a network block with network name."""
        mock_session.request.return_value.json.side_effect = [
            [{"$key": 3, "name": "External"}],  # GET vnets
            {},  # POST response
            [block_data],  # GET to fetch created block
        ]

        tenant = Tenant(tenant_data, mock_client.tenants)
        block = tenant.network_blocks.create(
            cidr="192.168.100.0/24",
            network_name="External",
        )

        assert block.cidr == "192.168.100.0/24"

    def test_create_network_block_requires_network(
        self,
        mock_client: VergeClient,
        tenant_data: dict[str, Any],
    ) -> None:
        """Test ValueError when neither network nor network_name provided."""
        tenant = Tenant(tenant_data, mock_client.tenants)
        with pytest.raises(ValueError, match="Either network or network_name must be provided"):
            tenant.network_blocks.create(cidr="10.0.0.0/24")

    def test_create_network_block_snapshot_raises_error(
        self,
        mock_client: VergeClient,
    ) -> None:
        """Test ValueError when creating block on snapshot."""
        tenant_data = {
            "$key": 100,
            "name": "test-tenant",
            "is_snapshot": True,
        }
        tenant = Tenant(tenant_data, mock_client.tenants)
        with pytest.raises(ValueError, match="Cannot assign network block to a tenant snapshot"):
            tenant.network_blocks.create(cidr="10.0.0.0/24", network=1)

    def test_create_network_block_network_not_found(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        tenant_data: dict[str, Any],
    ) -> None:
        """Test NotFoundError when network not found by name."""
        mock_session.request.return_value.json.return_value = []

        tenant = Tenant(tenant_data, mock_client.tenants)
        with pytest.raises(NotFoundError, match="Network 'NonExistent' not found"):
            tenant.network_blocks.create(cidr="10.0.0.0/24", network_name="NonExistent")

    def test_delete_network_block(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        tenant_data: dict[str, Any],
    ) -> None:
        """Test deleting a network block."""
        mock_session.request.return_value.json.return_value = {}

        tenant = Tenant(tenant_data, mock_client.tenants)
        tenant.network_blocks.delete(42)

        call_args = mock_session.request.call_args
        assert call_args.kwargs.get("method") == "DELETE"
        assert "vnet_cidrs/42" in call_args.kwargs.get("url", "")

    def test_delete_network_block_by_cidr(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        tenant_data: dict[str, Any],
        block_data: dict[str, Any],
    ) -> None:
        """Test deleting a network block by CIDR."""
        mock_session.request.return_value.json.side_effect = [
            [block_data],  # GET to find block
            {},  # DELETE response
        ]

        tenant = Tenant(tenant_data, mock_client.tenants)
        tenant.network_blocks.delete_by_cidr("192.168.100.0/24")

        # Find the DELETE request
        delete_call = None
        for call in mock_session.request.call_args_list:
            if call.kwargs.get("method") == "DELETE":
                delete_call = call
                break

        assert delete_call is not None
        assert "vnet_cidrs/42" in delete_call.kwargs.get("url", "")


class TestTenantNetworkBlockViaObject:
    """Test TenantNetworkBlock actions via the object itself."""

    @pytest.fixture
    def tenant_data(self) -> dict[str, Any]:
        """Sample tenant data."""
        return {
            "$key": 100,
            "name": "test-tenant",
            "running": False,
            "is_snapshot": False,
        }

    @pytest.fixture
    def block_data(self) -> dict[str, Any]:
        """Sample network block data."""
        return {
            "$key": 42,
            "vnet": 3,
            "network_name": "External",
            "cidr": "192.168.100.0/24",
            "description": "Test block",
            "owner": "tenants/100",
        }

    def test_delete_via_object(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        tenant_data: dict[str, Any],
        block_data: dict[str, Any],
    ) -> None:
        """Test deleting block via object.delete()."""
        mock_session.request.return_value.json.side_effect = [
            [block_data],  # GET to list blocks
            {},  # DELETE response
        ]

        tenant = Tenant(tenant_data, mock_client.tenants)
        blocks = tenant.network_blocks.list()
        blocks[0].delete()

        # Find the DELETE request
        delete_call = None
        for call in mock_session.request.call_args_list:
            if call.kwargs.get("method") == "DELETE":
                delete_call = call
                break

        assert delete_call is not None
        assert "vnet_cidrs/42" in delete_call.kwargs.get("url", "")


class TestTenantNetworkBlocksProperty:
    """Test Tenant.network_blocks property."""

    @pytest.fixture
    def tenant_data(self) -> dict[str, Any]:
        """Sample tenant data."""
        return {
            "$key": 100,
            "name": "test-tenant",
            "running": False,
            "is_snapshot": False,
        }

    def test_network_blocks_property_returns_manager(
        self,
        mock_client: VergeClient,
        tenant_data: dict[str, Any],
    ) -> None:
        """Test that tenant.network_blocks returns TenantNetworkBlockManager."""
        tenant = Tenant(tenant_data, mock_client.tenants)
        manager = tenant.network_blocks

        assert isinstance(manager, TenantNetworkBlockManager)

    def test_network_blocks_manager_has_correct_tenant(
        self,
        mock_client: VergeClient,
        tenant_data: dict[str, Any],
    ) -> None:
        """Test that network_blocks manager references the correct tenant."""
        tenant = Tenant(tenant_data, mock_client.tenants)
        manager = tenant.network_blocks

        assert manager._tenant.key == tenant.key


class TestTenantManagerNetworkBlocksMethod:
    """Test TenantManager.network_blocks() method."""

    @pytest.fixture
    def tenant_data(self) -> dict[str, Any]:
        """Sample tenant data."""
        return {
            "$key": 100,
            "name": "test-tenant",
            "running": False,
            "is_snapshot": False,
        }

    def test_network_blocks_method_returns_manager(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        tenant_data: dict[str, Any],
    ) -> None:
        """Test that tenants.network_blocks(key) returns TenantNetworkBlockManager."""
        mock_session.request.return_value.json.return_value = tenant_data

        manager = mock_client.tenants.network_blocks(100)

        assert isinstance(manager, TenantNetworkBlockManager)
        assert manager._tenant.key == 100
