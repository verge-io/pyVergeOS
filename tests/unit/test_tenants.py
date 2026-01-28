"""Unit tests for Tenant operations."""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from pyvergeos import VergeClient
from pyvergeos.exceptions import NotFoundError
from pyvergeos.resources.tenant_external_ips import (
    TenantExternalIP,
    TenantExternalIPManager,
)
from pyvergeos.resources.tenant_layer2 import TenantLayer2Manager, TenantLayer2Network
from pyvergeos.resources.tenant_manager import Tenant, TenantManager
from pyvergeos.resources.tenant_network_blocks import (
    TenantNetworkBlock,
    TenantNetworkBlockManager,
)
from pyvergeos.resources.tenant_nodes import TenantNode, TenantNodeManager
from pyvergeos.resources.tenant_snapshots import TenantSnapshot, TenantSnapshotManager
from pyvergeos.resources.tenant_storage import TenantStorage, TenantStorageManager


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


# =============================================================================
# TenantExternalIP Tests
# =============================================================================


class TestTenantExternalIP:
    """Unit tests for TenantExternalIP resource object."""

    @pytest.fixture
    def ip_data(self) -> dict[str, Any]:
        """Sample external IP data."""
        return {
            "$key": 42,
            "vnet": 3,
            "network_name": "External",
            "ip": "192.168.1.100",
            "type": "virtual",
            "hostname": "tenant-service",
            "description": "Test external IP",
            "owner": "tenants/100",
            "mac": None,
        }

    def test_tenant_key_from_owner(self, ip_data: dict[str, Any]) -> None:
        """Test extracting tenant key from owner field."""
        ip = TenantExternalIP(ip_data, None)  # type: ignore[arg-type]
        assert ip.tenant_key == 100

    def test_tenant_key_invalid_owner(self) -> None:
        """Test tenant_key with invalid owner."""
        ip = TenantExternalIP({"owner": "vms/123"}, None)  # type: ignore[arg-type]
        assert ip.tenant_key == 0

    def test_tenant_key_empty_owner(self) -> None:
        """Test tenant_key with empty owner."""
        ip = TenantExternalIP({}, None)  # type: ignore[arg-type]
        assert ip.tenant_key == 0

    def test_network_key(self, ip_data: dict[str, Any]) -> None:
        """Test network_key property."""
        ip = TenantExternalIP(ip_data, None)  # type: ignore[arg-type]
        assert ip.network_key == 3

    def test_network_name(self, ip_data: dict[str, Any]) -> None:
        """Test network_name property."""
        ip = TenantExternalIP(ip_data, None)  # type: ignore[arg-type]
        assert ip.network_name == "External"

    def test_ip_address(self, ip_data: dict[str, Any]) -> None:
        """Test ip_address property."""
        ip = TenantExternalIP(ip_data, None)  # type: ignore[arg-type]
        assert ip.ip_address == "192.168.1.100"

    def test_ip_address_empty(self) -> None:
        """Test ip_address with no data."""
        ip = TenantExternalIP({}, None)  # type: ignore[arg-type]
        assert ip.ip_address == ""

    def test_hostname(self, ip_data: dict[str, Any]) -> None:
        """Test hostname property."""
        ip = TenantExternalIP(ip_data, None)  # type: ignore[arg-type]
        assert ip.hostname == "tenant-service"

    def test_hostname_none(self) -> None:
        """Test hostname when not set."""
        ip = TenantExternalIP({}, None)  # type: ignore[arg-type]
        assert ip.hostname is None

    def test_ip_type(self, ip_data: dict[str, Any]) -> None:
        """Test ip_type property."""
        ip = TenantExternalIP(ip_data, None)  # type: ignore[arg-type]
        assert ip.ip_type == "virtual"

    def test_mac_address(self, ip_data: dict[str, Any]) -> None:
        """Test mac_address property."""
        ip = TenantExternalIP(ip_data, None)  # type: ignore[arg-type]
        assert ip.mac_address is None

    def test_repr_with_hostname(self, ip_data: dict[str, Any]) -> None:
        """Test __repr__ method with hostname."""
        ip = TenantExternalIP(ip_data, None)  # type: ignore[arg-type]
        repr_str = repr(ip)
        assert "192.168.1.100" in repr_str
        assert "tenant-service" in repr_str
        assert "External" in repr_str

    def test_repr_without_hostname(self) -> None:
        """Test __repr__ method without hostname."""
        ip = TenantExternalIP(
            {"ip": "10.0.0.1", "network_name": "Test"}, None  # type: ignore[arg-type]
        )
        repr_str = repr(ip)
        assert "10.0.0.1" in repr_str
        assert "Test" in repr_str


class TestTenantExternalIPManager:
    """Unit tests for TenantExternalIPManager."""

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
    def ip_data(self) -> dict[str, Any]:
        """Sample external IP data."""
        return {
            "$key": 42,
            "vnet": 3,
            "network_name": "External",
            "ip": "192.168.1.100",
            "type": "virtual",
            "hostname": "tenant-service",
            "description": "Test external IP",
            "owner": "tenants/100",
        }

    def test_list_external_ips(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        tenant_data: dict[str, Any],
    ) -> None:
        """Test listing tenant external IPs."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "ip": "10.0.0.1", "vnet": 3, "type": "virtual", "owner": "tenants/100"},
            {"$key": 2, "ip": "10.0.0.2", "vnet": 3, "type": "virtual", "owner": "tenants/100"},
        ]

        tenant = Tenant(tenant_data, mock_client.tenants)
        ips = tenant.external_ips.list()

        assert len(ips) == 2
        assert ips[0].ip_address == "10.0.0.1"
        assert ips[1].ip_address == "10.0.0.2"

    def test_list_external_ips_filters_by_owner_and_type(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        tenant_data: dict[str, Any],
    ) -> None:
        """Test that list() filters by tenant owner and type."""
        mock_session.request.return_value.json.return_value = []

        tenant = Tenant(tenant_data, mock_client.tenants)
        tenant.external_ips.list()

        call_args = mock_session.request.call_args
        params = call_args.kwargs.get("params", {})
        filter_str = params.get("filter", "")
        assert "owner eq 'tenants/100'" in filter_str
        assert "type eq 'virtual'" in filter_str

    def test_list_external_ips_with_ip_filter(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        tenant_data: dict[str, Any],
    ) -> None:
        """Test list() with IP filter."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "ip": "10.0.0.1", "vnet": 3, "type": "virtual", "owner": "tenants/100"},
        ]

        tenant = Tenant(tenant_data, mock_client.tenants)
        tenant.external_ips.list(ip="10.0.0.1")

        call_args = mock_session.request.call_args
        params = call_args.kwargs.get("params", {})
        filter_value = params.get("filter", "")
        assert "ip eq '10.0.0.1'" in filter_value

    def test_list_external_ips_empty(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        tenant_data: dict[str, Any],
    ) -> None:
        """Test list() returns empty list when no IPs."""
        mock_session.request.return_value.json.return_value = None

        tenant = Tenant(tenant_data, mock_client.tenants)
        ips = tenant.external_ips.list()

        assert ips == []

    def test_get_external_ip_by_key(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        tenant_data: dict[str, Any],
        ip_data: dict[str, Any],
    ) -> None:
        """Test getting external IP by key."""
        mock_session.request.return_value.json.return_value = ip_data

        tenant = Tenant(tenant_data, mock_client.tenants)
        ip = tenant.external_ips.get(42)

        assert ip.key == 42
        assert ip.ip_address == "192.168.1.100"

    def test_get_external_ip_by_ip(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        tenant_data: dict[str, Any],
        ip_data: dict[str, Any],
    ) -> None:
        """Test getting external IP by IP address."""
        mock_session.request.return_value.json.return_value = [ip_data]

        tenant = Tenant(tenant_data, mock_client.tenants)
        ip = tenant.external_ips.get(ip="192.168.1.100")

        assert ip.ip_address == "192.168.1.100"

    def test_get_external_ip_not_found(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        tenant_data: dict[str, Any],
    ) -> None:
        """Test NotFoundError when external IP not found."""
        mock_session.request.return_value.json.return_value = []

        tenant = Tenant(tenant_data, mock_client.tenants)
        with pytest.raises(NotFoundError):
            tenant.external_ips.get(ip="10.99.99.99")

    def test_get_external_ip_not_found_by_key(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        tenant_data: dict[str, Any],
    ) -> None:
        """Test NotFoundError when external IP key not found."""
        mock_session.request.return_value.json.return_value = None

        tenant = Tenant(tenant_data, mock_client.tenants)
        with pytest.raises(NotFoundError):
            tenant.external_ips.get(999)

    def test_get_external_ip_requires_key_or_ip(
        self,
        mock_client: VergeClient,
        tenant_data: dict[str, Any],
    ) -> None:
        """Test ValueError when neither key nor ip provided."""
        tenant = Tenant(tenant_data, mock_client.tenants)
        with pytest.raises(ValueError, match="Either key or ip must be provided"):
            tenant.external_ips.get()

    @patch("time.sleep")
    def test_create_external_ip_by_network_key(
        self,
        mock_sleep: MagicMock,
        mock_client: VergeClient,
        mock_session: MagicMock,
        tenant_data: dict[str, Any],
        ip_data: dict[str, Any],
    ) -> None:
        """Test creating an external IP with network key."""
        mock_session.request.return_value.json.side_effect = [
            {},  # POST response
            [ip_data],  # GET to fetch created IP
        ]

        tenant = Tenant(tenant_data, mock_client.tenants)
        ip = tenant.external_ips.create(
            ip="192.168.1.100",
            network=3,
            hostname="tenant-service",
            description="Test external IP",
        )

        assert ip.ip_address == "192.168.1.100"

        # Find the POST request to vnet_addresses
        post_call = None
        for call in mock_session.request.call_args_list:
            if (
                call.kwargs.get("method") == "POST"
                and "vnet_addresses" in call.kwargs.get("url", "")
            ):
                post_call = call
                break

        assert post_call is not None
        body = post_call.kwargs.get("json", {})
        assert body["vnet"] == 3
        assert body["ip"] == "192.168.1.100"
        assert body["type"] == "virtual"
        assert body["owner"] == "tenants/100"
        assert body["hostname"] == "tenant-service"
        assert body["description"] == "Test external IP"

    @patch("time.sleep")
    def test_create_external_ip_by_network_name(
        self,
        mock_sleep: MagicMock,
        mock_client: VergeClient,
        mock_session: MagicMock,
        tenant_data: dict[str, Any],
        ip_data: dict[str, Any],
    ) -> None:
        """Test creating an external IP with network name."""
        mock_session.request.return_value.json.side_effect = [
            [{"$key": 3, "name": "External"}],  # GET vnets
            {},  # POST response
            [ip_data],  # GET to fetch created IP
        ]

        tenant = Tenant(tenant_data, mock_client.tenants)
        ip = tenant.external_ips.create(
            ip="192.168.1.100",
            network_name="External",
        )

        assert ip.ip_address == "192.168.1.100"

    def test_create_external_ip_requires_network(
        self,
        mock_client: VergeClient,
        tenant_data: dict[str, Any],
    ) -> None:
        """Test ValueError when neither network nor network_name provided."""
        tenant = Tenant(tenant_data, mock_client.tenants)
        with pytest.raises(ValueError, match="Either network or network_name must be provided"):
            tenant.external_ips.create(ip="10.0.0.1")

    def test_create_external_ip_snapshot_raises_error(
        self,
        mock_client: VergeClient,
    ) -> None:
        """Test ValueError when creating external IP on snapshot."""
        tenant_data = {
            "$key": 100,
            "name": "test-tenant",
            "is_snapshot": True,
        }
        tenant = Tenant(tenant_data, mock_client.tenants)
        with pytest.raises(ValueError, match="Cannot assign external IP to a tenant snapshot"):
            tenant.external_ips.create(ip="10.0.0.1", network=1)

    def test_create_external_ip_network_not_found(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        tenant_data: dict[str, Any],
    ) -> None:
        """Test NotFoundError when network not found by name."""
        mock_session.request.return_value.json.return_value = []

        tenant = Tenant(tenant_data, mock_client.tenants)
        with pytest.raises(NotFoundError, match="Network 'NonExistent' not found"):
            tenant.external_ips.create(ip="10.0.0.1", network_name="NonExistent")

    def test_delete_external_ip(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        tenant_data: dict[str, Any],
    ) -> None:
        """Test deleting an external IP."""
        mock_session.request.return_value.json.return_value = {}

        tenant = Tenant(tenant_data, mock_client.tenants)
        tenant.external_ips.delete(42)

        call_args = mock_session.request.call_args
        assert call_args.kwargs.get("method") == "DELETE"
        assert "vnet_addresses/42" in call_args.kwargs.get("url", "")

    def test_delete_external_ip_by_ip(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        tenant_data: dict[str, Any],
        ip_data: dict[str, Any],
    ) -> None:
        """Test deleting an external IP by IP address."""
        mock_session.request.return_value.json.side_effect = [
            [ip_data],  # GET to find IP
            {},  # DELETE response
        ]

        tenant = Tenant(tenant_data, mock_client.tenants)
        tenant.external_ips.delete_by_ip("192.168.1.100")

        # Find the DELETE request
        delete_call = None
        for call in mock_session.request.call_args_list:
            if call.kwargs.get("method") == "DELETE":
                delete_call = call
                break

        assert delete_call is not None
        assert "vnet_addresses/42" in delete_call.kwargs.get("url", "")


class TestTenantExternalIPViaObject:
    """Test TenantExternalIP actions via the object itself."""

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
    def ip_data(self) -> dict[str, Any]:
        """Sample external IP data."""
        return {
            "$key": 42,
            "vnet": 3,
            "network_name": "External",
            "ip": "192.168.1.100",
            "type": "virtual",
            "hostname": "tenant-service",
            "description": "Test external IP",
            "owner": "tenants/100",
        }

    def test_delete_via_object(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        tenant_data: dict[str, Any],
        ip_data: dict[str, Any],
    ) -> None:
        """Test deleting IP via object.delete()."""
        mock_session.request.return_value.json.side_effect = [
            [ip_data],  # GET to list IPs
            {},  # DELETE response
        ]

        tenant = Tenant(tenant_data, mock_client.tenants)
        ips = tenant.external_ips.list()
        ips[0].delete()

        # Find the DELETE request
        delete_call = None
        for call in mock_session.request.call_args_list:
            if call.kwargs.get("method") == "DELETE":
                delete_call = call
                break

        assert delete_call is not None
        assert "vnet_addresses/42" in delete_call.kwargs.get("url", "")


class TestTenantExternalIPsProperty:
    """Test Tenant.external_ips property."""

    @pytest.fixture
    def tenant_data(self) -> dict[str, Any]:
        """Sample tenant data."""
        return {
            "$key": 100,
            "name": "test-tenant",
            "running": False,
            "is_snapshot": False,
        }

    def test_external_ips_property_returns_manager(
        self,
        mock_client: VergeClient,
        tenant_data: dict[str, Any],
    ) -> None:
        """Test that tenant.external_ips returns TenantExternalIPManager."""
        tenant = Tenant(tenant_data, mock_client.tenants)
        manager = tenant.external_ips

        assert isinstance(manager, TenantExternalIPManager)

    def test_external_ips_manager_has_correct_tenant(
        self,
        mock_client: VergeClient,
        tenant_data: dict[str, Any],
    ) -> None:
        """Test that external_ips manager references the correct tenant."""
        tenant = Tenant(tenant_data, mock_client.tenants)
        manager = tenant.external_ips

        assert manager._tenant.key == tenant.key


class TestTenantManagerExternalIPsMethod:
    """Test TenantManager.external_ips() method."""

    @pytest.fixture
    def tenant_data(self) -> dict[str, Any]:
        """Sample tenant data."""
        return {
            "$key": 100,
            "name": "test-tenant",
            "running": False,
            "is_snapshot": False,
        }

    def test_external_ips_method_returns_manager(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        tenant_data: dict[str, Any],
    ) -> None:
        """Test that tenants.external_ips(key) returns TenantExternalIPManager."""
        mock_session.request.return_value.json.return_value = tenant_data

        manager = mock_client.tenants.external_ips(100)

        assert isinstance(manager, TenantExternalIPManager)
        assert manager._tenant.key == 100


class TestTenantLayer2Network:
    """Unit tests for TenantLayer2Network object."""

    @pytest.fixture
    def l2_data(self) -> dict[str, Any]:
        """Sample Layer 2 network data."""
        return {
            "$key": 42,
            "tenant": 100,
            "tenant_name": "test-tenant",
            "vnet": 10,
            "network_name": "VLAN100",
            "network_type": "internal",
            "enabled": True,
        }

    def test_tenant_key(self, l2_data: dict[str, Any]) -> None:
        """Test tenant_key property."""
        l2 = TenantLayer2Network(l2_data, None)  # type: ignore[arg-type]
        assert l2.tenant_key == 100

    def test_tenant_name(self, l2_data: dict[str, Any]) -> None:
        """Test tenant_name property."""
        l2 = TenantLayer2Network(l2_data, None)  # type: ignore[arg-type]
        assert l2.tenant_name == "test-tenant"

    def test_network_key(self, l2_data: dict[str, Any]) -> None:
        """Test network_key property."""
        l2 = TenantLayer2Network(l2_data, None)  # type: ignore[arg-type]
        assert l2.network_key == 10

    def test_network_name(self, l2_data: dict[str, Any]) -> None:
        """Test network_name property."""
        l2 = TenantLayer2Network(l2_data, None)  # type: ignore[arg-type]
        assert l2.network_name == "VLAN100"

    def test_network_type(self, l2_data: dict[str, Any]) -> None:
        """Test network_type property."""
        l2 = TenantLayer2Network(l2_data, None)  # type: ignore[arg-type]
        assert l2.network_type == "internal"

    def test_is_enabled_true(self, l2_data: dict[str, Any]) -> None:
        """Test is_enabled property when True."""
        l2 = TenantLayer2Network(l2_data, None)  # type: ignore[arg-type]
        assert l2.is_enabled is True

    def test_is_enabled_false(self, l2_data: dict[str, Any]) -> None:
        """Test is_enabled property when False."""
        l2_data["enabled"] = False
        l2 = TenantLayer2Network(l2_data, None)  # type: ignore[arg-type]
        assert l2.is_enabled is False

    def test_is_enabled_missing(self) -> None:
        """Test is_enabled when field is missing."""
        l2 = TenantLayer2Network({"$key": 1}, None)  # type: ignore[arg-type]
        assert l2.is_enabled is False

    def test_repr_enabled(self, l2_data: dict[str, Any]) -> None:
        """Test __repr__ when enabled."""
        l2 = TenantLayer2Network(l2_data, None)  # type: ignore[arg-type]
        repr_str = repr(l2)
        assert "VLAN100" in repr_str
        assert "enabled" in repr_str

    def test_repr_disabled(self, l2_data: dict[str, Any]) -> None:
        """Test __repr__ when disabled."""
        l2_data["enabled"] = False
        l2 = TenantLayer2Network(l2_data, None)  # type: ignore[arg-type]
        repr_str = repr(l2)
        assert "VLAN100" in repr_str
        assert "disabled" in repr_str


class TestTenantLayer2Manager:
    """Unit tests for TenantLayer2Manager."""

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
    def l2_data(self) -> dict[str, Any]:
        """Sample Layer 2 network data."""
        return {
            "$key": 42,
            "tenant": 100,
            "tenant_name": "test-tenant",
            "vnet": 10,
            "network_name": "VLAN100",
            "network_type": "internal",
            "enabled": True,
        }

    def test_list_l2_networks(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        tenant_data: dict[str, Any],
    ) -> None:
        """Test listing tenant Layer 2 networks."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "tenant": 100, "vnet": 10, "network_name": "VLAN100", "enabled": True},
            {"$key": 2, "tenant": 100, "vnet": 11, "network_name": "VLAN200", "enabled": False},
        ]

        tenant = Tenant(tenant_data, mock_client.tenants)
        l2_networks = tenant.l2_networks.list()

        assert len(l2_networks) == 2
        assert l2_networks[0].network_name == "VLAN100"
        assert l2_networks[1].network_name == "VLAN200"

    def test_list_l2_networks_filters_by_tenant(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        tenant_data: dict[str, Any],
    ) -> None:
        """Test that list() filters by tenant."""
        mock_session.request.return_value.json.return_value = []

        tenant = Tenant(tenant_data, mock_client.tenants)
        tenant.l2_networks.list()

        call_args = mock_session.request.call_args
        params = call_args.kwargs.get("params", {})
        assert "tenant eq 100" in params.get("filter", "")

    def test_list_l2_networks_with_additional_filter(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        tenant_data: dict[str, Any],
    ) -> None:
        """Test list() with additional filter."""
        mock_session.request.return_value.json.return_value = []

        tenant = Tenant(tenant_data, mock_client.tenants)
        tenant.l2_networks.list(filter="enabled eq true")

        call_args = mock_session.request.call_args
        params = call_args.kwargs.get("params", {})
        filter_value = params.get("filter", "")
        assert "tenant eq 100" in filter_value
        assert "enabled eq true" in filter_value

    def test_list_l2_networks_empty(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        tenant_data: dict[str, Any],
    ) -> None:
        """Test list() returns empty list when no L2 networks."""
        mock_session.request.return_value.json.return_value = None

        tenant = Tenant(tenant_data, mock_client.tenants)
        l2_networks = tenant.l2_networks.list()

        assert l2_networks == []

    def test_get_l2_network_by_key(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        tenant_data: dict[str, Any],
        l2_data: dict[str, Any],
    ) -> None:
        """Test getting Layer 2 network by key."""
        mock_session.request.return_value.json.return_value = [l2_data]

        tenant = Tenant(tenant_data, mock_client.tenants)
        l2 = tenant.l2_networks.get(42)

        assert l2.key == 42
        assert l2.network_name == "VLAN100"

    def test_get_l2_network_by_network_name(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        tenant_data: dict[str, Any],
        l2_data: dict[str, Any],
    ) -> None:
        """Test getting Layer 2 network by network name."""
        mock_session.request.return_value.json.return_value = [l2_data]

        tenant = Tenant(tenant_data, mock_client.tenants)
        l2 = tenant.l2_networks.get(network_name="VLAN100")

        assert l2.network_name == "VLAN100"

    def test_get_l2_network_not_found_by_key(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        tenant_data: dict[str, Any],
    ) -> None:
        """Test NotFoundError when Layer 2 network key not found."""
        mock_session.request.return_value.json.return_value = []

        tenant = Tenant(tenant_data, mock_client.tenants)
        with pytest.raises(NotFoundError):
            tenant.l2_networks.get(999)

    def test_get_l2_network_not_found_by_name(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        tenant_data: dict[str, Any],
    ) -> None:
        """Test NotFoundError when Layer 2 network not found by name."""
        mock_session.request.return_value.json.return_value = []

        tenant = Tenant(tenant_data, mock_client.tenants)
        with pytest.raises(NotFoundError):
            tenant.l2_networks.get(network_name="NonExistent")

    def test_get_l2_network_requires_key_or_name(
        self,
        mock_client: VergeClient,
        tenant_data: dict[str, Any],
    ) -> None:
        """Test ValueError when neither key nor network_name provided."""
        tenant = Tenant(tenant_data, mock_client.tenants)
        with pytest.raises(ValueError, match="Either key or network_name must be provided"):
            tenant.l2_networks.get()

    @patch("time.sleep")
    def test_create_l2_network_by_network_key(
        self,
        mock_sleep: MagicMock,
        mock_client: VergeClient,
        mock_session: MagicMock,
        tenant_data: dict[str, Any],
        l2_data: dict[str, Any],
    ) -> None:
        """Test creating Layer 2 network with network key."""
        mock_session.request.return_value.json.side_effect = [
            {"$key": 42},  # POST response
            [l2_data],  # GET to fetch created L2 network
        ]

        tenant = Tenant(tenant_data, mock_client.tenants)
        l2 = tenant.l2_networks.create(network=10, enabled=True)

        assert l2.network_name == "VLAN100"

        # Find the POST request to tenant_layer2_vnets
        post_call = None
        for call in mock_session.request.call_args_list:
            if (
                call.kwargs.get("method") == "POST"
                and "tenant_layer2_vnets" in call.kwargs.get("url", "")
            ):
                post_call = call
                break

        assert post_call is not None
        body = post_call.kwargs.get("json", {})
        assert body["tenant"] == 100
        assert body["vnet"] == 10
        assert body["enabled"] is True

    @patch("time.sleep")
    def test_create_l2_network_by_network_name(
        self,
        mock_sleep: MagicMock,
        mock_client: VergeClient,
        mock_session: MagicMock,
        tenant_data: dict[str, Any],
        l2_data: dict[str, Any],
    ) -> None:
        """Test creating Layer 2 network with network name."""
        mock_session.request.return_value.json.side_effect = [
            [{"$key": 10, "name": "VLAN100"}],  # GET vnets
            {"$key": 42},  # POST response
            [l2_data],  # GET to fetch created L2 network
        ]

        tenant = Tenant(tenant_data, mock_client.tenants)
        l2 = tenant.l2_networks.create(network_name="VLAN100", enabled=True)

        assert l2.network_name == "VLAN100"

    @patch("time.sleep")
    def test_create_l2_network_disabled(
        self,
        mock_sleep: MagicMock,
        mock_client: VergeClient,
        mock_session: MagicMock,
        tenant_data: dict[str, Any],
        l2_data: dict[str, Any],
    ) -> None:
        """Test creating Layer 2 network in disabled state."""
        l2_data["enabled"] = False
        mock_session.request.return_value.json.side_effect = [
            {"$key": 42},  # POST response
            [l2_data],  # GET to fetch created L2 network
        ]

        tenant = Tenant(tenant_data, mock_client.tenants)
        tenant.l2_networks.create(network=10, enabled=False)

        # Find the POST request
        post_call = None
        for call in mock_session.request.call_args_list:
            if (
                call.kwargs.get("method") == "POST"
                and "tenant_layer2_vnets" in call.kwargs.get("url", "")
            ):
                post_call = call
                break

        assert post_call is not None
        body = post_call.kwargs.get("json", {})
        assert body["enabled"] is False

    def test_create_l2_network_requires_network(
        self,
        mock_client: VergeClient,
        tenant_data: dict[str, Any],
    ) -> None:
        """Test ValueError when neither network nor network_name provided."""
        tenant = Tenant(tenant_data, mock_client.tenants)
        with pytest.raises(ValueError, match="Either network or network_name must be provided"):
            tenant.l2_networks.create()

    def test_create_l2_network_snapshot_raises_error(
        self,
        mock_client: VergeClient,
    ) -> None:
        """Test ValueError when creating L2 network on snapshot."""
        tenant_data = {
            "$key": 100,
            "name": "test-tenant",
            "is_snapshot": True,
        }
        tenant = Tenant(tenant_data, mock_client.tenants)
        with pytest.raises(ValueError, match="Cannot assign Layer 2 network to a tenant snapshot"):
            tenant.l2_networks.create(network=10)

    def test_create_l2_network_not_found(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        tenant_data: dict[str, Any],
    ) -> None:
        """Test NotFoundError when network not found by name."""
        mock_session.request.return_value.json.return_value = []

        tenant = Tenant(tenant_data, mock_client.tenants)
        with pytest.raises(NotFoundError, match="Network 'NonExistent' not found"):
            tenant.l2_networks.create(network_name="NonExistent")

    def test_update_l2_network_enable(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        tenant_data: dict[str, Any],
        l2_data: dict[str, Any],
    ) -> None:
        """Test updating Layer 2 network to enabled."""
        mock_session.request.return_value.json.side_effect = [
            {},  # PUT response
            [l2_data],  # GET to fetch updated L2 network
        ]

        tenant = Tenant(tenant_data, mock_client.tenants)
        l2 = tenant.l2_networks.update(42, enabled=True)

        assert l2.is_enabled is True

        # Find the PUT request
        put_call = None
        for call in mock_session.request.call_args_list:
            if call.kwargs.get("method") == "PUT":
                put_call = call
                break

        assert put_call is not None
        assert "tenant_layer2_vnets/42" in put_call.kwargs.get("url", "")
        body = put_call.kwargs.get("json", {})
        assert body["enabled"] is True

    def test_update_l2_network_disable(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        tenant_data: dict[str, Any],
        l2_data: dict[str, Any],
    ) -> None:
        """Test updating Layer 2 network to disabled."""
        l2_data["enabled"] = False
        mock_session.request.return_value.json.side_effect = [
            {},  # PUT response
            [l2_data],  # GET to fetch updated L2 network
        ]

        tenant = Tenant(tenant_data, mock_client.tenants)
        l2 = tenant.l2_networks.update(42, enabled=False)

        assert l2.is_enabled is False

    def test_delete_l2_network(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        tenant_data: dict[str, Any],
    ) -> None:
        """Test deleting a Layer 2 network."""
        mock_session.request.return_value.json.return_value = {}

        tenant = Tenant(tenant_data, mock_client.tenants)
        tenant.l2_networks.delete(42)

        call_args = mock_session.request.call_args
        assert call_args.kwargs.get("method") == "DELETE"
        assert "tenant_layer2_vnets/42" in call_args.kwargs.get("url", "")

    def test_delete_l2_network_by_network(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        tenant_data: dict[str, Any],
        l2_data: dict[str, Any],
    ) -> None:
        """Test deleting Layer 2 network by network name."""
        mock_session.request.return_value.json.side_effect = [
            [l2_data],  # GET to find L2 network
            {},  # DELETE response
        ]

        tenant = Tenant(tenant_data, mock_client.tenants)
        tenant.l2_networks.delete_by_network("VLAN100")

        # Find the DELETE request
        delete_call = None
        for call in mock_session.request.call_args_list:
            if call.kwargs.get("method") == "DELETE":
                delete_call = call
                break

        assert delete_call is not None
        assert "tenant_layer2_vnets/42" in delete_call.kwargs.get("url", "")


class TestTenantLayer2ViaObject:
    """Test TenantLayer2Network actions via the object itself."""

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
    def l2_data(self) -> dict[str, Any]:
        """Sample Layer 2 network data."""
        return {
            "$key": 42,
            "tenant": 100,
            "tenant_name": "test-tenant",
            "vnet": 10,
            "network_name": "VLAN100",
            "network_type": "internal",
            "enabled": True,
        }

    def test_enable_via_object(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        tenant_data: dict[str, Any],
        l2_data: dict[str, Any],
    ) -> None:
        """Test enabling L2 network via object.enable()."""
        mock_session.request.return_value.json.side_effect = [
            [l2_data],  # GET to list L2 networks
            {},  # PUT response
            [l2_data],  # GET to fetch updated L2 network
        ]

        tenant = Tenant(tenant_data, mock_client.tenants)
        l2_networks = tenant.l2_networks.list()
        result = l2_networks[0].enable()

        assert result.is_enabled is True

        # Find the PUT request
        put_call = None
        for call in mock_session.request.call_args_list:
            if call.kwargs.get("method") == "PUT":
                put_call = call
                break

        assert put_call is not None
        body = put_call.kwargs.get("json", {})
        assert body["enabled"] is True

    def test_disable_via_object(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        tenant_data: dict[str, Any],
        l2_data: dict[str, Any],
    ) -> None:
        """Test disabling L2 network via object.disable()."""
        l2_data_disabled = l2_data.copy()
        l2_data_disabled["enabled"] = False
        mock_session.request.return_value.json.side_effect = [
            [l2_data],  # GET to list L2 networks
            {},  # PUT response
            [l2_data_disabled],  # GET to fetch updated L2 network
        ]

        tenant = Tenant(tenant_data, mock_client.tenants)
        l2_networks = tenant.l2_networks.list()
        result = l2_networks[0].disable()

        assert result.is_enabled is False

        # Find the PUT request
        put_call = None
        for call in mock_session.request.call_args_list:
            if call.kwargs.get("method") == "PUT":
                put_call = call
                break

        assert put_call is not None
        body = put_call.kwargs.get("json", {})
        assert body["enabled"] is False

    def test_delete_via_object(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        tenant_data: dict[str, Any],
        l2_data: dict[str, Any],
    ) -> None:
        """Test deleting L2 network via object.delete()."""
        mock_session.request.return_value.json.side_effect = [
            [l2_data],  # GET to list L2 networks
            {},  # DELETE response
        ]

        tenant = Tenant(tenant_data, mock_client.tenants)
        l2_networks = tenant.l2_networks.list()
        l2_networks[0].delete()

        # Find the DELETE request
        delete_call = None
        for call in mock_session.request.call_args_list:
            if call.kwargs.get("method") == "DELETE":
                delete_call = call
                break

        assert delete_call is not None
        assert "tenant_layer2_vnets/42" in delete_call.kwargs.get("url", "")


class TestTenantL2NetworksProperty:
    """Test Tenant.l2_networks property."""

    @pytest.fixture
    def tenant_data(self) -> dict[str, Any]:
        """Sample tenant data."""
        return {
            "$key": 100,
            "name": "test-tenant",
            "running": False,
            "is_snapshot": False,
        }

    def test_l2_networks_property_returns_manager(
        self,
        mock_client: VergeClient,
        tenant_data: dict[str, Any],
    ) -> None:
        """Test that tenant.l2_networks returns TenantLayer2Manager."""
        tenant = Tenant(tenant_data, mock_client.tenants)
        manager = tenant.l2_networks

        assert isinstance(manager, TenantLayer2Manager)

    def test_l2_networks_manager_has_correct_tenant(
        self,
        mock_client: VergeClient,
        tenant_data: dict[str, Any],
    ) -> None:
        """Test that l2_networks manager references the correct tenant."""
        tenant = Tenant(tenant_data, mock_client.tenants)
        manager = tenant.l2_networks

        assert manager._tenant.key == tenant.key


class TestTenantManagerL2NetworksMethod:
    """Test TenantManager.l2_networks() method."""

    @pytest.fixture
    def tenant_data(self) -> dict[str, Any]:
        """Sample tenant data."""
        return {
            "$key": 100,
            "name": "test-tenant",
            "running": False,
            "is_snapshot": False,
        }

    def test_l2_networks_method_returns_manager(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        tenant_data: dict[str, Any],
    ) -> None:
        """Test that tenants.l2_networks(key) returns TenantLayer2Manager."""
        mock_session.request.return_value.json.return_value = tenant_data

        manager = mock_client.tenants.l2_networks(100)

        assert isinstance(manager, TenantLayer2Manager)
        assert manager._tenant.key == 100


class TestTenantUtilities:
    """Unit tests for Tenant utility methods (send_file, crash cart, isolation)."""

    @pytest.fixture
    def tenant_data(self) -> dict[str, Any]:
        """Sample tenant data."""
        return {
            "$key": 100,
            "name": "test-tenant",
            "running": True,
            "is_snapshot": False,
            "isolate": False,
        }

    @pytest.fixture
    def tenant_isolated_data(self) -> dict[str, Any]:
        """Sample isolated tenant data."""
        return {
            "$key": 101,
            "name": "isolated-tenant",
            "running": True,
            "is_snapshot": False,
            "isolate": True,
        }

    @pytest.fixture
    def tenant_snapshot_data(self) -> dict[str, Any]:
        """Sample tenant snapshot data."""
        return {
            "$key": 102,
            "name": "tenant-snapshot",
            "running": False,
            "is_snapshot": True,
            "isolate": False,
        }

    # Tests for send_file()

    def test_send_file(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        tenant_data: dict[str, Any],
    ) -> None:
        """Test sending a file to a tenant."""
        mock_session.request.return_value.json.return_value = {"$key": 1}
        tenant = Tenant(tenant_data, mock_client.tenants)

        result = tenant.send_file(file_key=42)

        call_args = mock_session.request.call_args
        body = call_args.kwargs.get("json", {})
        assert body["tenant"] == 100
        assert body["action"] == "give_file"
        assert body["params"]["file"] == 42
        assert result == {"$key": 1}

    def test_send_file_snapshot_raises(
        self,
        mock_client: VergeClient,
        tenant_snapshot_data: dict[str, Any],
    ) -> None:
        """Test that sending file to snapshot raises ValueError."""
        tenant = Tenant(tenant_snapshot_data, mock_client.tenants)

        with pytest.raises(ValueError, match="Cannot send file to a tenant snapshot"):
            tenant.send_file(file_key=42)

    def test_send_file_via_manager(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
    ) -> None:
        """Test sending a file via manager."""
        mock_session.request.return_value.json.return_value = {"$key": 1}

        result = mock_client.tenants.send_file(key=100, file_key=42)

        call_args = mock_session.request.call_args
        body = call_args.kwargs.get("json", {})
        assert body["tenant"] == 100
        assert body["action"] == "give_file"
        assert body["params"]["file"] == 42
        assert result == {"$key": 1}

    # Tests for enable_isolation()

    def test_enable_isolation(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        tenant_data: dict[str, Any],
    ) -> None:
        """Test enabling isolation for a tenant."""
        mock_session.request.return_value.json.return_value = {}
        tenant = Tenant(tenant_data, mock_client.tenants)

        result = tenant.enable_isolation()

        call_args = mock_session.request.call_args
        body = call_args.kwargs.get("json", {})
        assert body["tenant"] == 100
        assert body["action"] == "isolateon"
        assert result is tenant  # Returns self for chaining

    def test_enable_isolation_snapshot_raises(
        self,
        mock_client: VergeClient,
        tenant_snapshot_data: dict[str, Any],
    ) -> None:
        """Test that enabling isolation on snapshot raises ValueError."""
        tenant = Tenant(tenant_snapshot_data, mock_client.tenants)

        with pytest.raises(
            ValueError, match="Cannot enable isolation for a tenant snapshot"
        ):
            tenant.enable_isolation()

    def test_enable_isolation_already_isolated_raises(
        self,
        mock_client: VergeClient,
        tenant_isolated_data: dict[str, Any],
    ) -> None:
        """Test that enabling isolation when already isolated raises ValueError."""
        tenant = Tenant(tenant_isolated_data, mock_client.tenants)

        with pytest.raises(ValueError, match="already in isolation mode"):
            tenant.enable_isolation()

    def test_enable_isolation_via_manager(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
    ) -> None:
        """Test enabling isolation via manager."""
        mock_session.request.return_value.json.return_value = {}

        mock_client.tenants.enable_isolation(key=100)

        call_args = mock_session.request.call_args
        body = call_args.kwargs.get("json", {})
        assert body["tenant"] == 100
        assert body["action"] == "isolateon"

    # Tests for disable_isolation()

    def test_disable_isolation(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        tenant_isolated_data: dict[str, Any],
    ) -> None:
        """Test disabling isolation for a tenant."""
        mock_session.request.return_value.json.return_value = {}
        tenant = Tenant(tenant_isolated_data, mock_client.tenants)

        result = tenant.disable_isolation()

        call_args = mock_session.request.call_args
        body = call_args.kwargs.get("json", {})
        assert body["tenant"] == 101
        assert body["action"] == "isolateoff"
        assert result is tenant  # Returns self for chaining

    def test_disable_isolation_snapshot_raises(
        self,
        mock_client: VergeClient,
        tenant_snapshot_data: dict[str, Any],
    ) -> None:
        """Test that disabling isolation on snapshot raises ValueError."""
        tenant = Tenant(tenant_snapshot_data, mock_client.tenants)

        with pytest.raises(
            ValueError, match="Cannot disable isolation for a tenant snapshot"
        ):
            tenant.disable_isolation()

    def test_disable_isolation_not_isolated_raises(
        self,
        mock_client: VergeClient,
        tenant_data: dict[str, Any],
    ) -> None:
        """Test that disabling isolation when not isolated raises ValueError."""
        tenant = Tenant(tenant_data, mock_client.tenants)

        with pytest.raises(ValueError, match="not in isolation mode"):
            tenant.disable_isolation()

    def test_disable_isolation_via_manager(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
    ) -> None:
        """Test disabling isolation via manager."""
        mock_session.request.return_value.json.return_value = {}

        mock_client.tenants.disable_isolation(key=100)

        call_args = mock_session.request.call_args
        body = call_args.kwargs.get("json", {})
        assert body["tenant"] == 100
        assert body["action"] == "isolateoff"

    # Tests for create_crash_cart()

    def test_create_crash_cart(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        tenant_data: dict[str, Any],
    ) -> None:
        """Test creating a crash cart for a tenant."""
        # First call gets the recipe, second creates the VM
        mock_session.request.return_value.json.side_effect = [
            [{"id": 5, "name": "Crash Cart"}],  # vm_recipes response
            {"$key": 99},  # vm_recipe_instances response
        ]
        tenant = Tenant(tenant_data, mock_client.tenants)

        result = tenant.create_crash_cart()

        # Check the vm_recipe_instances call
        calls = mock_session.request.call_args_list
        recipe_instance_call = calls[-1]
        body = recipe_instance_call.kwargs.get("json", {})
        assert body["recipe"] == 5
        assert body["name"] == "Crash Cart - test-tenant"
        assert body["answers"]["tenant"] == 100
        assert result == {"$key": 99}

    def test_create_crash_cart_custom_name(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        tenant_data: dict[str, Any],
    ) -> None:
        """Test creating a crash cart with a custom name."""
        mock_session.request.return_value.json.side_effect = [
            [{"id": 5, "name": "Crash Cart"}],
            {"$key": 99},
        ]
        tenant = Tenant(tenant_data, mock_client.tenants)

        tenant.create_crash_cart(name="Emergency Access")

        calls = mock_session.request.call_args_list
        recipe_instance_call = calls[-1]
        body = recipe_instance_call.kwargs.get("json", {})
        assert body["name"] == "Emergency Access"

    def test_create_crash_cart_snapshot_raises(
        self,
        mock_client: VergeClient,
        tenant_snapshot_data: dict[str, Any],
    ) -> None:
        """Test that creating crash cart for snapshot raises ValueError."""
        tenant = Tenant(tenant_snapshot_data, mock_client.tenants)

        with pytest.raises(
            ValueError, match="Cannot deploy Crash Cart for a tenant snapshot"
        ):
            tenant.create_crash_cart()

    def test_create_crash_cart_recipe_not_found(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        tenant_data: dict[str, Any],
    ) -> None:
        """Test that NotFoundError is raised when Crash Cart recipe not found."""
        mock_session.request.return_value.json.return_value = []
        tenant = Tenant(tenant_data, mock_client.tenants)

        with pytest.raises(NotFoundError, match="Crash Cart recipe not found"):
            tenant.create_crash_cart()

    def test_create_crash_cart_via_manager(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        tenant_data: dict[str, Any],
    ) -> None:
        """Test creating crash cart via manager."""
        mock_session.request.return_value.json.side_effect = [
            tenant_data,  # get tenant
            [{"id": 5, "name": "Crash Cart"}],
            {"$key": 99},
        ]

        result = mock_client.tenants.create_crash_cart(key=100)

        calls = mock_session.request.call_args_list
        recipe_instance_call = calls[-1]
        body = recipe_instance_call.kwargs.get("json", {})
        assert body["name"] == "Crash Cart - test-tenant"
        assert result == {"$key": 99}

    # Tests for delete_crash_cart()

    def test_delete_crash_cart(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        tenant_data: dict[str, Any],
    ) -> None:
        """Test deleting a crash cart for a tenant."""
        tenant = Tenant(tenant_data, mock_client.tenants)

        # Mock vms.get to return a VM object
        vm_mock = MagicMock(key=200, name="Crash Cart - test-tenant")
        with patch.object(mock_client.vms, "get", return_value=vm_mock):
            tenant.delete_crash_cart()

        # Verify DELETE was called with the VM key
        call_args = mock_session.request.call_args
        assert call_args.kwargs["method"] == "DELETE"
        assert "vms/200" in call_args.kwargs["url"]

    def test_delete_crash_cart_custom_name(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        tenant_data: dict[str, Any],
    ) -> None:
        """Test deleting a crash cart with a custom name."""
        tenant = Tenant(tenant_data, mock_client.tenants)

        # Mock vms.get to return a VM object
        vm_mock = MagicMock(key=201, name="Emergency Access")
        with patch.object(mock_client.vms, "get", return_value=vm_mock):
            tenant.delete_crash_cart(name="Emergency Access")

        call_args = mock_session.request.call_args
        assert "vms/201" in call_args.kwargs["url"]

    def test_delete_crash_cart_snapshot_raises(
        self,
        mock_client: VergeClient,
        tenant_snapshot_data: dict[str, Any],
    ) -> None:
        """Test that deleting crash cart for snapshot raises ValueError."""
        tenant = Tenant(tenant_snapshot_data, mock_client.tenants)

        with pytest.raises(
            ValueError, match="Cannot delete Crash Cart for a tenant snapshot"
        ):
            tenant.delete_crash_cart()

    def test_delete_crash_cart_not_found(
        self,
        mock_client: VergeClient,
        tenant_data: dict[str, Any],
    ) -> None:
        """Test that NotFoundError is raised when crash cart VM not found."""
        tenant = Tenant(tenant_data, mock_client.tenants)

        # Mock vms.get to raise NotFoundError
        with patch.object(
            mock_client.vms, "get", side_effect=NotFoundError("VM not found")
        ), pytest.raises(NotFoundError, match="not found"):
            tenant.delete_crash_cart()

    def test_delete_crash_cart_via_manager(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        tenant_data: dict[str, Any],
    ) -> None:
        """Test deleting crash cart via manager."""
        # Mock get tenant
        mock_session.request.return_value.json.return_value = tenant_data

        # Mock vms.get to return a VM object
        vm_mock = MagicMock(key=200, name="Crash Cart - test-tenant")
        with patch.object(mock_client.vms, "get", return_value=vm_mock):
            mock_client.tenants.delete_crash_cart(key=100)

        # Verify DELETE was called - get the last call which should be DELETE
        calls = [
            c for c in mock_session.request.call_args_list
            if c.kwargs.get("method") == "DELETE"
        ]
        assert len(calls) == 1
        assert "vms/200" in calls[0].kwargs["url"]


class TestTenantNode:
    """Unit tests for TenantNode object."""

    @pytest.fixture
    def node_data(self) -> dict[str, Any]:
        """Sample tenant node data."""
        return {
            "$key": 42,
            "tenant": 100,
            "name": "node1",
            "nodeid": 1,
            "cpu_cores": 4,
            "ram": 16384,
            "enabled": True,
            "running": True,
            "status": "online",
            "host_node": "verge-node1",
            "cluster": 1,
            "cluster_name": "default",
            "preferred_node": 2,
            "preferred_node_name": "verge-node2",
            "on_power_loss": "last_state",
            "machine": 500,
        }

    def test_tenant_key(self, node_data: dict[str, Any]) -> None:
        """Test tenant_key property."""
        node = TenantNode(node_data, None)  # type: ignore[arg-type]
        assert node.tenant_key == 100

    def test_name(self, node_data: dict[str, Any]) -> None:
        """Test name property."""
        node = TenantNode(node_data, None)  # type: ignore[arg-type]
        assert node.name == "node1"

    def test_node_id(self, node_data: dict[str, Any]) -> None:
        """Test node_id property."""
        node = TenantNode(node_data, None)  # type: ignore[arg-type]
        assert node.node_id == 1

    def test_cpu_cores(self, node_data: dict[str, Any]) -> None:
        """Test cpu_cores property."""
        node = TenantNode(node_data, None)  # type: ignore[arg-type]
        assert node.cpu_cores == 4

    def test_ram_mb(self, node_data: dict[str, Any]) -> None:
        """Test ram_mb property."""
        node = TenantNode(node_data, None)  # type: ignore[arg-type]
        assert node.ram_mb == 16384

    def test_ram_gb(self, node_data: dict[str, Any]) -> None:
        """Test ram_gb property."""
        node = TenantNode(node_data, None)  # type: ignore[arg-type]
        assert node.ram_gb == 16.0

    def test_is_enabled(self, node_data: dict[str, Any]) -> None:
        """Test is_enabled property."""
        node = TenantNode(node_data, None)  # type: ignore[arg-type]
        assert node.is_enabled is True

    def test_is_enabled_false(self, node_data: dict[str, Any]) -> None:
        """Test is_enabled property when disabled."""
        node_data["enabled"] = False
        node = TenantNode(node_data, None)  # type: ignore[arg-type]
        assert node.is_enabled is False

    def test_is_running(self, node_data: dict[str, Any]) -> None:
        """Test is_running property."""
        node = TenantNode(node_data, None)  # type: ignore[arg-type]
        assert node.is_running is True

    def test_is_running_false(self, node_data: dict[str, Any]) -> None:
        """Test is_running property when stopped."""
        node_data["running"] = False
        node = TenantNode(node_data, None)  # type: ignore[arg-type]
        assert node.is_running is False

    def test_status(self, node_data: dict[str, Any]) -> None:
        """Test status property."""
        node = TenantNode(node_data, None)  # type: ignore[arg-type]
        assert node.status == "online"

    def test_host_node(self, node_data: dict[str, Any]) -> None:
        """Test host_node property."""
        node = TenantNode(node_data, None)  # type: ignore[arg-type]
        assert node.host_node == "verge-node1"

    def test_cluster_key(self, node_data: dict[str, Any]) -> None:
        """Test cluster_key property."""
        node = TenantNode(node_data, None)  # type: ignore[arg-type]
        assert node.cluster_key == 1

    def test_cluster_name(self, node_data: dict[str, Any]) -> None:
        """Test cluster_name property."""
        node = TenantNode(node_data, None)  # type: ignore[arg-type]
        assert node.cluster_name == "default"

    def test_preferred_node_key(self, node_data: dict[str, Any]) -> None:
        """Test preferred_node_key property."""
        node = TenantNode(node_data, None)  # type: ignore[arg-type]
        assert node.preferred_node_key == 2

    def test_preferred_node_name(self, node_data: dict[str, Any]) -> None:
        """Test preferred_node_name property."""
        node = TenantNode(node_data, None)  # type: ignore[arg-type]
        assert node.preferred_node_name == "verge-node2"

    def test_on_power_loss(self, node_data: dict[str, Any]) -> None:
        """Test on_power_loss property."""
        node = TenantNode(node_data, None)  # type: ignore[arg-type]
        assert node.on_power_loss == "last_state"

    def test_machine_key(self, node_data: dict[str, Any]) -> None:
        """Test machine_key property."""
        node = TenantNode(node_data, None)  # type: ignore[arg-type]
        assert node.machine_key == 500

    def test_repr(self, node_data: dict[str, Any]) -> None:
        """Test __repr__ for running node."""
        node = TenantNode(node_data, None)  # type: ignore[arg-type]
        repr_str = repr(node)
        assert "node1" in repr_str
        assert "4 cores" in repr_str
        assert "16.0 GB RAM" in repr_str
        assert "running" in repr_str

    def test_repr_stopped(self, node_data: dict[str, Any]) -> None:
        """Test __repr__ for stopped node."""
        node_data["running"] = False
        node = TenantNode(node_data, None)  # type: ignore[arg-type]
        repr_str = repr(node)
        assert "stopped" in repr_str


class TestTenantNodeManager:
    """Unit tests for TenantNodeManager."""

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
    def node_data(self) -> dict[str, Any]:
        """Sample tenant node data."""
        return {
            "$key": 42,
            "tenant": 100,
            "name": "node1",
            "nodeid": 1,
            "cpu_cores": 4,
            "ram": 16384,
            "enabled": True,
            "running": True,
            "status": "online",
        }

    def test_list_nodes(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        tenant_data: dict[str, Any],
        node_data: dict[str, Any],
    ) -> None:
        """Test listing nodes for a tenant."""
        mock_session.request.return_value.json.return_value = [node_data]
        tenant = Tenant(tenant_data, mock_client.tenants)

        nodes = tenant.nodes.list()

        assert len(nodes) == 1
        assert isinstance(nodes[0], TenantNode)
        assert nodes[0].name == "node1"

    def test_list_nodes_filters_by_tenant(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        tenant_data: dict[str, Any],
        node_data: dict[str, Any],
    ) -> None:
        """Test that list filters by tenant key."""
        mock_session.request.return_value.json.return_value = [node_data]
        tenant = Tenant(tenant_data, mock_client.tenants)

        tenant.nodes.list()

        call_args = mock_session.request.call_args
        params = call_args.kwargs.get("params", {})
        assert "tenant eq 100" in params.get("filter", "")

    def test_list_nodes_empty(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        tenant_data: dict[str, Any],
    ) -> None:
        """Test listing nodes when tenant has none."""
        mock_session.request.return_value.json.return_value = []
        tenant = Tenant(tenant_data, mock_client.tenants)

        nodes = tenant.nodes.list()

        assert nodes == []

    def test_get_node_by_key(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        tenant_data: dict[str, Any],
        node_data: dict[str, Any],
    ) -> None:
        """Test getting a node by key."""
        mock_session.request.return_value.json.return_value = node_data
        tenant = Tenant(tenant_data, mock_client.tenants)

        node = tenant.nodes.get(42)

        assert isinstance(node, TenantNode)
        assert node.key == 42
        call_args = mock_session.request.call_args
        assert "tenant_nodes/42" in call_args.kwargs.get("url", "")

    def test_get_node_by_name(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        tenant_data: dict[str, Any],
        node_data: dict[str, Any],
    ) -> None:
        """Test getting a node by name."""
        mock_session.request.return_value.json.return_value = [node_data]
        tenant = Tenant(tenant_data, mock_client.tenants)

        node = tenant.nodes.get(name="node1")

        assert node.name == "node1"
        call_args = mock_session.request.call_args
        params = call_args.kwargs.get("params", {})
        assert "name eq 'node1'" in params.get("filter", "")

    def test_get_node_not_found(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        tenant_data: dict[str, Any],
    ) -> None:
        """Test that NotFoundError is raised when node not found."""
        mock_session.request.return_value.json.return_value = []
        tenant = Tenant(tenant_data, mock_client.tenants)

        with pytest.raises(NotFoundError):
            tenant.nodes.get(name="nonexistent")

    def test_get_node_not_found_by_key(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        tenant_data: dict[str, Any],
    ) -> None:
        """Test NotFoundError when fetching node by key that doesn't exist."""
        mock_session.request.return_value.json.return_value = None
        tenant = Tenant(tenant_data, mock_client.tenants)

        with pytest.raises(NotFoundError):
            tenant.nodes.get(999)

    def test_get_node_requires_key_or_name(
        self,
        mock_client: VergeClient,
        tenant_data: dict[str, Any],
    ) -> None:
        """Test that ValueError is raised when neither key nor name provided."""
        tenant = Tenant(tenant_data, mock_client.tenants)

        with pytest.raises(ValueError, match="Either key or name must be provided"):
            tenant.nodes.get()

    def test_create_node(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        tenant_data: dict[str, Any],
        node_data: dict[str, Any],
    ) -> None:
        """Test creating a node."""
        mock_session.request.return_value.json.side_effect = [
            {"$key": 42},  # POST response
            node_data,  # GET to fetch created node
        ]
        tenant = Tenant(tenant_data, mock_client.tenants)

        node = tenant.nodes.create(cpu_cores=4, ram_gb=16, cluster=1)

        assert isinstance(node, TenantNode)
        # Check the POST request body
        calls = mock_session.request.call_args_list
        post_call = [c for c in calls if c.kwargs.get("method") == "POST"][0]
        body = post_call.kwargs.get("json", {})
        assert body["tenant"] == 100
        assert body["cpu_cores"] == 4
        assert body["ram"] == 16384  # 16 GB = 16384 MB
        assert body["cluster"] == 1

    def test_create_node_with_ram_mb(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        tenant_data: dict[str, Any],
        node_data: dict[str, Any],
    ) -> None:
        """Test creating a node with RAM specified in MB."""
        mock_session.request.return_value.json.side_effect = [
            {"$key": 42},
            node_data,
        ]
        tenant = Tenant(tenant_data, mock_client.tenants)

        tenant.nodes.create(cpu_cores=4, ram_mb=8192)

        calls = mock_session.request.call_args_list
        post_call = [c for c in calls if c.kwargs.get("method") == "POST"][0]
        body = post_call.kwargs.get("json", {})
        assert body["ram"] == 8192

    def test_create_node_with_preferred_node(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        tenant_data: dict[str, Any],
        node_data: dict[str, Any],
    ) -> None:
        """Test creating a node with preferred node."""
        mock_session.request.return_value.json.side_effect = [
            {"$key": 42},
            node_data,
        ]
        tenant = Tenant(tenant_data, mock_client.tenants)

        tenant.nodes.create(cpu_cores=4, ram_gb=16, cluster=1, preferred_node=2)

        calls = mock_session.request.call_args_list
        post_call = [c for c in calls if c.kwargs.get("method") == "POST"][0]
        body = post_call.kwargs.get("json", {})
        assert body["preferred_node"] == 2

    def test_create_node_on_snapshot_raises(
        self,
        mock_client: VergeClient,
        tenant_data: dict[str, Any],
    ) -> None:
        """Test that creating node on snapshot raises ValueError."""
        tenant_data["is_snapshot"] = True
        tenant = Tenant(tenant_data, mock_client.tenants)

        with pytest.raises(ValueError, match="Cannot add nodes to a tenant snapshot"):
            tenant.nodes.create(cpu_cores=4, ram_gb=16)

    def test_create_node_invalid_ram_raises(
        self,
        mock_client: VergeClient,
        tenant_data: dict[str, Any],
    ) -> None:
        """Test that creating node with too little RAM raises ValueError."""
        tenant = Tenant(tenant_data, mock_client.tenants)

        with pytest.raises(ValueError, match="RAM must be at least 2048 MB"):
            tenant.nodes.create(cpu_cores=4, ram_mb=1024)

    def test_create_node_invalid_cpu_raises(
        self,
        mock_client: VergeClient,
        tenant_data: dict[str, Any],
    ) -> None:
        """Test that creating node with 0 CPU cores raises ValueError."""
        tenant = Tenant(tenant_data, mock_client.tenants)

        with pytest.raises(ValueError, match="CPU cores must be at least 1"):
            tenant.nodes.create(cpu_cores=0, ram_gb=16)

    def test_update_node(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        tenant_data: dict[str, Any],
        node_data: dict[str, Any],
    ) -> None:
        """Test updating a node."""
        mock_session.request.return_value.json.side_effect = [
            {},  # PUT response
            node_data,  # GET to fetch updated node
        ]
        tenant = Tenant(tenant_data, mock_client.tenants)

        node = tenant.nodes.update(42, cpu_cores=8)

        assert isinstance(node, TenantNode)
        calls = mock_session.request.call_args_list
        put_call = [c for c in calls if c.kwargs.get("method") == "PUT"][0]
        body = put_call.kwargs.get("json", {})
        assert body["cpu_cores"] == 8

    def test_delete_node(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        tenant_data: dict[str, Any],
    ) -> None:
        """Test deleting a node."""
        mock_session.request.return_value.json.return_value = {}
        tenant = Tenant(tenant_data, mock_client.tenants)

        tenant.nodes.delete(42)

        call_args = mock_session.request.call_args
        assert call_args.kwargs.get("method") == "DELETE"
        assert "tenant_nodes/42" in call_args.kwargs.get("url", "")


class TestTenantNodeViaObject:
    """Test TenantNode actions via the object itself."""

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
    def node_data(self) -> dict[str, Any]:
        """Sample tenant node data."""
        return {
            "$key": 42,
            "tenant": 100,
            "name": "node1",
            "nodeid": 1,
            "cpu_cores": 4,
            "ram": 16384,
            "enabled": True,
            "running": True,
            "status": "online",
        }

    def test_save_via_object(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        tenant_data: dict[str, Any],
        node_data: dict[str, Any],
    ) -> None:
        """Test saving node changes via object.save()."""
        mock_session.request.return_value.json.side_effect = [
            [node_data],  # GET to list nodes
            {},  # PUT response
            node_data,  # GET to fetch updated node
        ]

        tenant = Tenant(tenant_data, mock_client.tenants)
        nodes = tenant.nodes.list()
        result = nodes[0].save(cpu_cores=8)

        assert isinstance(result, TenantNode)

        # Find the PUT request
        put_call = None
        for call in mock_session.request.call_args_list:
            if call.kwargs.get("method") == "PUT":
                put_call = call
                break

        assert put_call is not None
        body = put_call.kwargs.get("json", {})
        assert body["cpu_cores"] == 8

    def test_delete_via_object(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        tenant_data: dict[str, Any],
        node_data: dict[str, Any],
    ) -> None:
        """Test deleting node via object.delete()."""
        mock_session.request.return_value.json.side_effect = [
            [node_data],  # GET to list nodes
            {},  # DELETE response
        ]

        tenant = Tenant(tenant_data, mock_client.tenants)
        nodes = tenant.nodes.list()
        nodes[0].delete()

        # Find the DELETE request
        delete_call = None
        for call in mock_session.request.call_args_list:
            if call.kwargs.get("method") == "DELETE":
                delete_call = call
                break

        assert delete_call is not None
        assert "tenant_nodes/42" in delete_call.kwargs.get("url", "")


class TestTenantNodesProperty:
    """Test Tenant.nodes property."""

    @pytest.fixture
    def tenant_data(self) -> dict[str, Any]:
        """Sample tenant data."""
        return {
            "$key": 100,
            "name": "test-tenant",
            "running": False,
            "is_snapshot": False,
        }

    def test_nodes_property_returns_manager(
        self,
        mock_client: VergeClient,
        tenant_data: dict[str, Any],
    ) -> None:
        """Test that tenant.nodes returns TenantNodeManager."""
        tenant = Tenant(tenant_data, mock_client.tenants)
        manager = tenant.nodes

        assert isinstance(manager, TenantNodeManager)

    def test_nodes_manager_has_correct_tenant(
        self,
        mock_client: VergeClient,
        tenant_data: dict[str, Any],
    ) -> None:
        """Test that nodes manager references the correct tenant."""
        tenant = Tenant(tenant_data, mock_client.tenants)
        manager = tenant.nodes

        assert manager._tenant.key == tenant.key


class TestTenantManagerNodesMethod:
    """Test TenantManager.nodes() method."""

    @pytest.fixture
    def tenant_data(self) -> dict[str, Any]:
        """Sample tenant data."""
        return {
            "$key": 100,
            "name": "test-tenant",
            "running": False,
            "is_snapshot": False,
        }

    def test_nodes_method_returns_manager(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        tenant_data: dict[str, Any],
    ) -> None:
        """Test that tenants.nodes(key) returns TenantNodeManager."""
        mock_session.request.return_value.json.return_value = tenant_data

        manager = mock_client.tenants.nodes(100)

        assert isinstance(manager, TenantNodeManager)
        assert manager._tenant.key == 100
