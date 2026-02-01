"""Unit tests for TenantNode operations."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from pyvergeos.exceptions import APIError, NotFoundError
from pyvergeos.resources.tenant_nodes import (
    TenantNode,
    TenantNodeManager,
)


@pytest.fixture
def mock_client() -> MagicMock:
    """Create a mock VergeClient."""
    client = MagicMock()
    client._request = MagicMock()
    return client


@pytest.fixture
def mock_tenant() -> MagicMock:
    """Create a mock Tenant object."""
    tenant = MagicMock()
    tenant.key = 123
    tenant.name = "test-tenant"
    tenant.is_snapshot = False
    return tenant


@pytest.fixture
def sample_node_data() -> dict[str, Any]:
    """Sample tenant node data from API."""
    return {
        "$key": 1,
        "tenant": 123,
        "name": "node1",
        "nodeid": 1,
        "cpu_cores": 4,
        "ram": 16384,
        "enabled": True,
        "description": "Primary node",
        "machine": 456,
        "running": True,
        "status": "running",
        "host_node": "host01",
        "cluster": 1,
        "cluster_name": "default",
        "preferred_node": 2,
        "preferred_node_name": "host02",
        "on_power_loss": "last_state",
    }


@pytest.fixture
def sample_node_list() -> list[dict[str, Any]]:
    """Sample list of tenant nodes."""
    return [
        {
            "$key": 1,
            "tenant": 123,
            "name": "node1",
            "nodeid": 1,
            "cpu_cores": 4,
            "ram": 16384,
            "enabled": True,
            "running": True,
            "status": "running",
        },
        {
            "$key": 2,
            "tenant": 123,
            "name": "node2",
            "nodeid": 2,
            "cpu_cores": 8,
            "ram": 32768,
            "enabled": True,
            "running": False,
            "status": "stopped",
        },
    ]


# =============================================================================
# TenantNode Model Tests
# =============================================================================


class TestTenantNode:
    """Tests for TenantNode model."""

    def test_node_properties(self, sample_node_data: dict[str, Any]) -> None:
        """Test node properties."""
        manager = MagicMock()
        node = TenantNode(sample_node_data, manager)

        assert node.key == 1
        assert node.tenant_key == 123
        assert node.name == "node1"
        assert node.node_id == 1
        assert node.cpu_cores == 4
        assert node.description == "Primary node"

    def test_node_ram_properties(self, sample_node_data: dict[str, Any]) -> None:
        """Test RAM properties."""
        manager = MagicMock()
        node = TenantNode(sample_node_data, manager)

        assert node.ram_mb == 16384
        assert node.ram_gb == 16.0

    def test_node_ram_gb_rounding(self) -> None:
        """Test RAM GB calculation with non-even values."""
        manager = MagicMock()
        node = TenantNode({"$key": 1, "ram": 8192}, manager)

        assert node.ram_gb == 8.0

        # Test with odd value
        node2 = TenantNode({"$key": 2, "ram": 10240}, manager)  # 10 GB
        assert node2.ram_gb == 10.0

    def test_node_enabled(self, sample_node_data: dict[str, Any]) -> None:
        """Test is_enabled property."""
        manager = MagicMock()
        node = TenantNode(sample_node_data, manager)

        assert node.is_enabled is True

        # Test disabled node
        disabled_node = TenantNode({"$key": 1, "enabled": False}, manager)
        assert disabled_node.is_enabled is False

    def test_node_enabled_default(self) -> None:
        """Test is_enabled default when not set."""
        manager = MagicMock()
        node = TenantNode({"$key": 1}, manager)

        # Default should be True
        assert node.is_enabled is True

    def test_node_running(self, sample_node_data: dict[str, Any]) -> None:
        """Test is_running property."""
        manager = MagicMock()
        node = TenantNode(sample_node_data, manager)

        assert node.is_running is True

        # Test stopped node
        stopped_node = TenantNode({"$key": 1, "running": False}, manager)
        assert stopped_node.is_running is False

    def test_node_running_default(self) -> None:
        """Test is_running default when not set."""
        manager = MagicMock()
        node = TenantNode({"$key": 1}, manager)

        assert node.is_running is False

    def test_node_status(self, sample_node_data: dict[str, Any]) -> None:
        """Test status property."""
        manager = MagicMock()
        node = TenantNode(sample_node_data, manager)

        assert node.status == "running"

    def test_node_status_default(self) -> None:
        """Test status default when not set."""
        manager = MagicMock()
        node = TenantNode({"$key": 1}, manager)

        assert node.status == "unknown"

    def test_node_host_node(self, sample_node_data: dict[str, Any]) -> None:
        """Test host_node property."""
        manager = MagicMock()
        node = TenantNode(sample_node_data, manager)

        assert node.host_node == "host01"

    def test_node_host_node_none(self) -> None:
        """Test host_node when not set."""
        manager = MagicMock()
        node = TenantNode({"$key": 1}, manager)

        assert node.host_node is None

    def test_node_cluster_properties(self, sample_node_data: dict[str, Any]) -> None:
        """Test cluster properties."""
        manager = MagicMock()
        node = TenantNode(sample_node_data, manager)

        assert node.cluster_key == 1
        assert node.cluster_name == "default"

    def test_node_cluster_none(self) -> None:
        """Test cluster properties when not set."""
        manager = MagicMock()
        node = TenantNode({"$key": 1}, manager)

        assert node.cluster_key is None
        assert node.cluster_name is None

    def test_node_preferred_node_properties(self, sample_node_data: dict[str, Any]) -> None:
        """Test preferred node properties."""
        manager = MagicMock()
        node = TenantNode(sample_node_data, manager)

        assert node.preferred_node_key == 2
        assert node.preferred_node_name == "host02"

    def test_node_preferred_node_none(self) -> None:
        """Test preferred node properties when not set."""
        manager = MagicMock()
        node = TenantNode({"$key": 1}, manager)

        assert node.preferred_node_key is None
        assert node.preferred_node_name is None

    def test_node_on_power_loss(self, sample_node_data: dict[str, Any]) -> None:
        """Test on_power_loss property."""
        manager = MagicMock()
        node = TenantNode(sample_node_data, manager)

        assert node.on_power_loss == "last_state"

    def test_node_on_power_loss_default(self) -> None:
        """Test on_power_loss default when not set."""
        manager = MagicMock()
        node = TenantNode({"$key": 1}, manager)

        assert node.on_power_loss == "last_state"

    def test_node_machine_key(self, sample_node_data: dict[str, Any]) -> None:
        """Test machine_key property."""
        manager = MagicMock()
        node = TenantNode(sample_node_data, manager)

        assert node.machine_key == 456

    def test_node_machine_key_none(self) -> None:
        """Test machine_key when not set."""
        manager = MagicMock()
        node = TenantNode({"$key": 1}, manager)

        assert node.machine_key is None

    def test_node_save(self, sample_node_data: dict[str, Any]) -> None:
        """Test save method calls manager update."""
        manager = MagicMock()
        manager.update.return_value = TenantNode(sample_node_data, manager)
        node = TenantNode(sample_node_data, manager)

        result = node.save(cpu_cores=8, ram=32768)

        manager.update.assert_called_once_with(1, cpu_cores=8, ram=32768)
        assert isinstance(result, TenantNode)

    def test_node_delete(self, sample_node_data: dict[str, Any]) -> None:
        """Test delete method calls manager."""
        manager = MagicMock()
        node = TenantNode(sample_node_data, manager)

        node.delete()

        manager.delete.assert_called_once_with(1)

    def test_node_repr_running(self, sample_node_data: dict[str, Any]) -> None:
        """Test node repr when running."""
        manager = MagicMock()
        node = TenantNode(sample_node_data, manager)

        repr_str = repr(node)
        assert "TenantNode" in repr_str
        assert "node1" in repr_str
        assert "4 cores" in repr_str
        assert "16.0 GB RAM" in repr_str
        assert "running" in repr_str

    def test_node_repr_stopped(self) -> None:
        """Test node repr when stopped."""
        manager = MagicMock()
        node = TenantNode(
            {"$key": 1, "name": "node1", "cpu_cores": 2, "ram": 4096, "running": False},
            manager,
        )

        repr_str = repr(node)
        assert "stopped" in repr_str


# =============================================================================
# TenantNodeManager Tests
# =============================================================================


class TestTenantNodeManager:
    """Tests for TenantNodeManager."""

    def test_list_nodes(
        self,
        mock_client: MagicMock,
        mock_tenant: MagicMock,
        sample_node_list: list[dict[str, Any]],
    ) -> None:
        """Test listing nodes."""
        mock_client._request.return_value = sample_node_list
        manager = TenantNodeManager(mock_client, mock_tenant)

        nodes = manager.list()

        assert len(nodes) == 2
        assert nodes[0].name == "node1"
        assert nodes[1].name == "node2"
        mock_client._request.assert_called_once()

    def test_list_filters_by_tenant(
        self,
        mock_client: MagicMock,
        mock_tenant: MagicMock,
    ) -> None:
        """Test that list filters by tenant."""
        mock_client._request.return_value = []
        manager = TenantNodeManager(mock_client, mock_tenant)

        manager.list()

        call_args = mock_client._request.call_args
        params = call_args[1]["params"]
        assert "tenant eq 123" in params["filter"]

    def test_list_with_additional_filter(
        self,
        mock_client: MagicMock,
        mock_tenant: MagicMock,
    ) -> None:
        """Test listing with additional filter."""
        mock_client._request.return_value = []
        manager = TenantNodeManager(mock_client, mock_tenant)

        manager.list(filter="running eq true")

        call_args = mock_client._request.call_args
        params = call_args[1]["params"]
        assert "running eq true" in params["filter"]
        assert "tenant eq 123" in params["filter"]

    def test_list_empty_response(
        self,
        mock_client: MagicMock,
        mock_tenant: MagicMock,
    ) -> None:
        """Test list with None response."""
        mock_client._request.return_value = None
        manager = TenantNodeManager(mock_client, mock_tenant)

        nodes = manager.list()

        assert nodes == []

    def test_list_single_response(
        self,
        mock_client: MagicMock,
        mock_tenant: MagicMock,
        sample_node_data: dict[str, Any],
    ) -> None:
        """Test list when API returns single item (not list)."""
        mock_client._request.return_value = sample_node_data
        manager = TenantNodeManager(mock_client, mock_tenant)

        nodes = manager.list()

        assert len(nodes) == 1
        assert nodes[0].name == "node1"

    def test_get_by_key(
        self,
        mock_client: MagicMock,
        mock_tenant: MagicMock,
        sample_node_data: dict[str, Any],
    ) -> None:
        """Test getting a node by key."""
        mock_client._request.return_value = sample_node_data
        manager = TenantNodeManager(mock_client, mock_tenant)

        node = manager.get(1)

        assert node.key == 1
        assert node.name == "node1"
        call_args = mock_client._request.call_args
        assert call_args[0][1] == "tenant_nodes/1"

    def test_get_by_name(
        self,
        mock_client: MagicMock,
        mock_tenant: MagicMock,
        sample_node_data: dict[str, Any],
    ) -> None:
        """Test getting a node by name."""
        mock_client._request.return_value = [sample_node_data]
        manager = TenantNodeManager(mock_client, mock_tenant)

        node = manager.get(name="node1")

        assert node.name == "node1"

    def test_get_by_key_not_found(
        self,
        mock_client: MagicMock,
        mock_tenant: MagicMock,
    ) -> None:
        """Test get by key when not found."""
        mock_client._request.return_value = None
        manager = TenantNodeManager(mock_client, mock_tenant)

        with pytest.raises(NotFoundError, match="Tenant node 999 not found"):
            manager.get(999)

    def test_get_by_key_invalid_response(
        self,
        mock_client: MagicMock,
        mock_tenant: MagicMock,
    ) -> None:
        """Test get by key with invalid response type."""
        mock_client._request.return_value = "invalid"
        manager = TenantNodeManager(mock_client, mock_tenant)

        with pytest.raises(NotFoundError):
            manager.get(1)

    def test_get_by_name_not_found(
        self,
        mock_client: MagicMock,
        mock_tenant: MagicMock,
    ) -> None:
        """Test get by name when not found."""
        mock_client._request.return_value = []
        manager = TenantNodeManager(mock_client, mock_tenant)

        with pytest.raises(NotFoundError, match="Tenant node 'node1' not found"):
            manager.get(name="node1")

    def test_get_requires_key_or_name(
        self,
        mock_client: MagicMock,
        mock_tenant: MagicMock,
    ) -> None:
        """Test that get requires key or name."""
        manager = TenantNodeManager(mock_client, mock_tenant)

        with pytest.raises(ValueError, match="Either key or name must be provided"):
            manager.get()

    def test_create_node_defaults(
        self,
        mock_client: MagicMock,
        mock_tenant: MagicMock,
        sample_node_data: dict[str, Any],
    ) -> None:
        """Test creating a node with defaults."""
        mock_client._request.side_effect = [
            {"$key": 1, "name": "node1"},  # POST response
            sample_node_data,  # GET response
        ]
        manager = TenantNodeManager(mock_client, mock_tenant)

        node = manager.create()

        assert node.key == 1
        post_call = mock_client._request.call_args_list[0]
        assert post_call[0][0] == "POST"
        assert post_call[1]["json_data"]["tenant"] == 123
        assert post_call[1]["json_data"]["cpu_cores"] == 4  # Default
        assert post_call[1]["json_data"]["ram"] == 16384  # Default 16 GB
        assert post_call[1]["json_data"]["cluster"] == 1  # Default

    def test_create_node_with_ram_gb(
        self,
        mock_client: MagicMock,
        mock_tenant: MagicMock,
        sample_node_data: dict[str, Any],
    ) -> None:
        """Test creating a node with RAM in GB."""
        mock_client._request.side_effect = [
            {"$key": 1},  # POST response
            sample_node_data,  # GET response
        ]
        manager = TenantNodeManager(mock_client, mock_tenant)

        manager.create(cpu_cores=8, ram_gb=32)

        post_call = mock_client._request.call_args_list[0]
        assert post_call[1]["json_data"]["cpu_cores"] == 8
        assert post_call[1]["json_data"]["ram"] == 32768  # 32 * 1024

    def test_create_node_with_ram_mb(
        self,
        mock_client: MagicMock,
        mock_tenant: MagicMock,
        sample_node_data: dict[str, Any],
    ) -> None:
        """Test creating a node with RAM in MB."""
        mock_client._request.side_effect = [
            {"$key": 1},  # POST response
            sample_node_data,  # GET response
        ]
        manager = TenantNodeManager(mock_client, mock_tenant)

        manager.create(cpu_cores=4, ram_mb=8192)

        post_call = mock_client._request.call_args_list[0]
        assert post_call[1]["json_data"]["ram"] == 8192

    def test_create_node_with_all_options(
        self,
        mock_client: MagicMock,
        mock_tenant: MagicMock,
        sample_node_data: dict[str, Any],
    ) -> None:
        """Test creating a node with all options."""
        mock_client._request.side_effect = [
            {"$key": 1},  # POST response
            sample_node_data,  # GET response
        ]
        manager = TenantNodeManager(mock_client, mock_tenant)

        manager.create(
            cpu_cores=8,
            ram_gb=32,
            cluster=2,
            preferred_node=5,
            name="mynode",
            description="Test node",
        )

        post_call = mock_client._request.call_args_list[0]
        json_data = post_call[1]["json_data"]
        assert json_data["cluster"] == 2
        assert json_data["preferred_node"] == 5
        assert json_data["name"] == "mynode"
        assert json_data["description"] == "Test node"

    def test_create_node_ram_minimum(
        self,
        mock_client: MagicMock,
        mock_tenant: MagicMock,
    ) -> None:
        """Test that create validates minimum RAM."""
        manager = TenantNodeManager(mock_client, mock_tenant)

        with pytest.raises(ValueError, match="RAM must be at least 2048 MB"):
            manager.create(ram_mb=1024)

    def test_create_node_cpu_minimum(
        self,
        mock_client: MagicMock,
        mock_tenant: MagicMock,
    ) -> None:
        """Test that create validates minimum CPU cores."""
        manager = TenantNodeManager(mock_client, mock_tenant)

        with pytest.raises(ValueError, match="CPU cores must be at least 1"):
            manager.create(cpu_cores=0)

    def test_create_on_snapshot_raises_error(
        self,
        mock_client: MagicMock,
        mock_tenant: MagicMock,
    ) -> None:
        """Test that create raises error for snapshot tenant."""
        mock_tenant.is_snapshot = True
        manager = TenantNodeManager(mock_client, mock_tenant)

        with pytest.raises(ValueError, match="Cannot add nodes to a tenant snapshot"):
            manager.create()

    def test_create_node_fallback_list(
        self,
        mock_client: MagicMock,
        mock_tenant: MagicMock,
        sample_node_data: dict[str, Any],
    ) -> None:
        """Test create fallback when POST doesn't return key."""
        mock_client._request.side_effect = [
            {},  # POST response without key
            [sample_node_data],  # List response
        ]
        manager = TenantNodeManager(mock_client, mock_tenant)

        node = manager.create()

        assert node.name == "node1"

    def test_create_node_failure(
        self,
        mock_client: MagicMock,
        mock_tenant: MagicMock,
    ) -> None:
        """Test create when node creation fails."""
        mock_client._request.side_effect = [
            {},  # POST response without key
            [],  # Empty list response
        ]
        manager = TenantNodeManager(mock_client, mock_tenant)

        with pytest.raises(APIError, match="Failed to create tenant node"):
            manager.create()

    def test_update_node(
        self,
        mock_client: MagicMock,
        mock_tenant: MagicMock,
        sample_node_data: dict[str, Any],
    ) -> None:
        """Test updating a node."""
        mock_client._request.side_effect = [
            None,  # PUT response
            sample_node_data,  # GET response
        ]
        manager = TenantNodeManager(mock_client, mock_tenant)

        node = manager.update(1, cpu_cores=8, ram=32768)

        assert node.key == 1
        put_call = mock_client._request.call_args_list[0]
        assert put_call[0][0] == "PUT"
        assert put_call[0][1] == "tenant_nodes/1"
        assert put_call[1]["json_data"]["cpu_cores"] == 8
        assert put_call[1]["json_data"]["ram"] == 32768

    def test_delete_node(
        self,
        mock_client: MagicMock,
        mock_tenant: MagicMock,
    ) -> None:
        """Test deleting a node."""
        manager = TenantNodeManager(mock_client, mock_tenant)

        manager.delete(1)

        mock_client._request.assert_called_once()
        call_args = mock_client._request.call_args
        assert call_args[0][0] == "DELETE"
        assert call_args[0][1] == "tenant_nodes/1"
