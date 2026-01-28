"""Unit tests for cluster operations."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from pyvergeos.exceptions import NotFoundError, ValidationError
from pyvergeos.resources.clusters import (
    CPU_TYPES,
    Cluster,
    ClusterManager,
    VSANStatus,
)


class TestCluster:
    """Tests for Cluster resource object."""

    def test_key_property(self) -> None:
        """Test key property returns int."""
        data = {"$key": 123}
        cluster = Cluster(data, MagicMock())
        assert cluster.key == 123

    def test_key_property_missing(self) -> None:
        """Test key property raises when missing."""
        cluster = Cluster({}, MagicMock())
        with pytest.raises(ValueError, match="no \\$key"):
            _ = cluster.key

    def test_name_property(self) -> None:
        """Test name property."""
        data = {"$key": 1, "name": "Production"}
        cluster = Cluster(data, MagicMock())
        assert cluster.name == "Production"

    def test_name_empty(self) -> None:
        """Test name property when empty."""
        cluster = Cluster({"$key": 1}, MagicMock())
        assert cluster.name == ""

    def test_description_property(self) -> None:
        """Test description property."""
        data = {"$key": 1, "description": "Production cluster"}
        cluster = Cluster(data, MagicMock())
        assert cluster.description == "Production cluster"

    def test_description_empty(self) -> None:
        """Test description property when empty."""
        cluster = Cluster({"$key": 1}, MagicMock())
        assert cluster.description == ""

    def test_is_enabled_true(self) -> None:
        """Test is_enabled property when true."""
        data = {"$key": 1, "enabled": True}
        cluster = Cluster(data, MagicMock())
        assert cluster.is_enabled is True

    def test_is_enabled_false(self) -> None:
        """Test is_enabled property when false."""
        data = {"$key": 1, "enabled": False}
        cluster = Cluster(data, MagicMock())
        assert cluster.is_enabled is False

    def test_is_enabled_default(self) -> None:
        """Test is_enabled property defaults to False."""
        cluster = Cluster({"$key": 1}, MagicMock())
        assert cluster.is_enabled is False

    def test_is_compute_true(self) -> None:
        """Test is_compute property when true."""
        data = {"$key": 1, "compute": True}
        cluster = Cluster(data, MagicMock())
        assert cluster.is_compute is True

    def test_is_compute_false(self) -> None:
        """Test is_compute property when false."""
        data = {"$key": 1, "compute": False}
        cluster = Cluster(data, MagicMock())
        assert cluster.is_compute is False

    def test_is_storage_true(self) -> None:
        """Test is_storage property when true."""
        data = {"$key": 1, "storage": True}
        cluster = Cluster(data, MagicMock())
        assert cluster.is_storage is True

    def test_is_storage_false(self) -> None:
        """Test is_storage property when false."""
        data = {"$key": 1, "storage": False}
        cluster = Cluster(data, MagicMock())
        assert cluster.is_storage is False

    def test_default_cpu_property(self) -> None:
        """Test default_cpu property."""
        data = {"$key": 1, "default_cpu": "EPYC-Milan"}
        cluster = Cluster(data, MagicMock())
        assert cluster.default_cpu == "EPYC-Milan"

    def test_default_cpu_empty(self) -> None:
        """Test default_cpu property when empty."""
        cluster = Cluster({"$key": 1}, MagicMock())
        assert cluster.default_cpu == ""

    def test_recommended_cpu_type_property(self) -> None:
        """Test recommended_cpu_type property."""
        data = {"$key": 1, "recommended_cpu_type": "EPYC-Rome"}
        cluster = Cluster(data, MagicMock())
        assert cluster.recommended_cpu_type == "EPYC-Rome"

    def test_nested_virtualization_true(self) -> None:
        """Test nested_virtualization property when true."""
        data = {"$key": 1, "kvm_nested": True}
        cluster = Cluster(data, MagicMock())
        assert cluster.nested_virtualization is True

    def test_nested_virtualization_false(self) -> None:
        """Test nested_virtualization property when false."""
        data = {"$key": 1, "kvm_nested": False}
        cluster = Cluster(data, MagicMock())
        assert cluster.nested_virtualization is False

    def test_ram_per_unit_property(self) -> None:
        """Test ram_per_unit property."""
        data = {"$key": 1, "ram_per_unit": 4096}
        cluster = Cluster(data, MagicMock())
        assert cluster.ram_per_unit == 4096

    def test_cores_per_unit_property(self) -> None:
        """Test cores_per_unit property."""
        data = {"$key": 1, "cores_per_unit": 2}
        cluster = Cluster(data, MagicMock())
        assert cluster.cores_per_unit == 2

    def test_max_ram_per_vm_property(self) -> None:
        """Test max_ram_per_vm property."""
        data = {"$key": 1, "max_ram_per_vm": 65536}
        cluster = Cluster(data, MagicMock())
        assert cluster.max_ram_per_vm == 65536

    def test_max_cores_per_vm_property(self) -> None:
        """Test max_cores_per_vm property."""
        data = {"$key": 1, "max_cores_per_vm": 32}
        cluster = Cluster(data, MagicMock())
        assert cluster.max_cores_per_vm == 32

    def test_target_ram_percent_property(self) -> None:
        """Test target_ram_percent property."""
        data = {"$key": 1, "target_ram_pct": 80.0}
        cluster = Cluster(data, MagicMock())
        assert cluster.target_ram_percent == 80.0

    def test_ram_overcommit_percent_property(self) -> None:
        """Test ram_overcommit_percent property."""
        data = {"$key": 1, "ram_overcommit_pct": 10.0}
        cluster = Cluster(data, MagicMock())
        assert cluster.ram_overcommit_percent == 10.0

    def test_created_at_property(self) -> None:
        """Test created_at property."""
        data = {"$key": 1, "created": 1706486400}  # 2024-01-29 00:00:00 UTC
        cluster = Cluster(data, MagicMock())
        assert cluster.created_at == datetime(2024, 1, 29, 0, 0, 0, tzinfo=timezone.utc)

    def test_created_at_none(self) -> None:
        """Test created_at property when not set."""
        cluster = Cluster({"$key": 1}, MagicMock())
        assert cluster.created_at is None

    def test_status_property_online(self) -> None:
        """Test status property for online."""
        data = {"$key": 1, "status_state": "online"}
        cluster = Cluster(data, MagicMock())
        assert cluster.status == "Online"

    def test_status_property_warning(self) -> None:
        """Test status property for warning."""
        data = {"$key": 1, "status_state": "warning"}
        cluster = Cluster(data, MagicMock())
        assert cluster.status == "Warning"

    def test_status_property_error(self) -> None:
        """Test status property for error."""
        data = {"$key": 1, "status_state": "error"}
        cluster = Cluster(data, MagicMock())
        assert cluster.status == "Error"

    def test_status_raw_property(self) -> None:
        """Test status_raw property."""
        data = {"$key": 1, "status_state": "online"}
        cluster = Cluster(data, MagicMock())
        assert cluster.status_raw == "online"

    def test_total_nodes_property(self) -> None:
        """Test total_nodes property."""
        data = {"$key": 1, "total_nodes": 4}
        cluster = Cluster(data, MagicMock())
        assert cluster.total_nodes == 4

    def test_online_nodes_property(self) -> None:
        """Test online_nodes property."""
        data = {"$key": 1, "online_nodes": 3}
        cluster = Cluster(data, MagicMock())
        assert cluster.online_nodes == 3

    def test_total_ram_mb_property(self) -> None:
        """Test total_ram_mb property."""
        data = {"$key": 1, "total_ram": 131072}
        cluster = Cluster(data, MagicMock())
        assert cluster.total_ram_mb == 131072

    def test_total_ram_gb_property(self) -> None:
        """Test total_ram_gb property."""
        data = {"$key": 1, "total_ram": 131072}  # 128 GB
        cluster = Cluster(data, MagicMock())
        assert cluster.total_ram_gb == 128.0

    def test_online_ram_mb_property(self) -> None:
        """Test online_ram_mb property."""
        data = {"$key": 1, "online_ram": 98304}
        cluster = Cluster(data, MagicMock())
        assert cluster.online_ram_mb == 98304

    def test_online_ram_gb_property(self) -> None:
        """Test online_ram_gb property."""
        data = {"$key": 1, "online_ram": 98304}  # 96 GB
        cluster = Cluster(data, MagicMock())
        assert cluster.online_ram_gb == 96.0

    def test_used_ram_mb_property(self) -> None:
        """Test used_ram_mb property."""
        data = {"$key": 1, "used_ram": 32768}
        cluster = Cluster(data, MagicMock())
        assert cluster.used_ram_mb == 32768

    def test_used_ram_gb_property(self) -> None:
        """Test used_ram_gb property."""
        data = {"$key": 1, "used_ram": 32768}  # 32 GB
        cluster = Cluster(data, MagicMock())
        assert cluster.used_ram_gb == 32.0

    def test_ram_used_percent_property(self) -> None:
        """Test ram_used_percent property."""
        data = {"$key": 1, "online_ram": 100000, "used_ram": 25000}
        cluster = Cluster(data, MagicMock())
        assert cluster.ram_used_percent == 25.0

    def test_ram_used_percent_zero_online(self) -> None:
        """Test ram_used_percent property when online_ram is 0."""
        data = {"$key": 1, "online_ram": 0, "used_ram": 0}
        cluster = Cluster(data, MagicMock())
        assert cluster.ram_used_percent == 0.0

    def test_total_cores_property(self) -> None:
        """Test total_cores property."""
        data = {"$key": 1, "total_cores": 64}
        cluster = Cluster(data, MagicMock())
        assert cluster.total_cores == 64

    def test_online_cores_property(self) -> None:
        """Test online_cores property."""
        data = {"$key": 1, "online_cores": 48}
        cluster = Cluster(data, MagicMock())
        assert cluster.online_cores == 48

    def test_used_cores_property(self) -> None:
        """Test used_cores property."""
        data = {"$key": 1, "used_cores": 16}
        cluster = Cluster(data, MagicMock())
        assert cluster.used_cores == 16

    def test_cores_used_percent_property(self) -> None:
        """Test cores_used_percent property."""
        data = {"$key": 1, "online_cores": 48, "used_cores": 12}
        cluster = Cluster(data, MagicMock())
        assert cluster.cores_used_percent == 25.0

    def test_cores_used_percent_zero_online(self) -> None:
        """Test cores_used_percent property when online_cores is 0."""
        data = {"$key": 1, "online_cores": 0, "used_cores": 0}
        cluster = Cluster(data, MagicMock())
        assert cluster.cores_used_percent == 0.0

    def test_running_machines_property(self) -> None:
        """Test running_machines property."""
        data = {"$key": 1, "running_machines": 15}
        cluster = Cluster(data, MagicMock())
        assert cluster.running_machines == 15

    def test_repr(self) -> None:
        """Test __repr__ method."""
        data = {
            "$key": 1,
            "name": "Production",
            "status_state": "online",
            "online_nodes": 3,
            "total_nodes": 4,
        }
        cluster = Cluster(data, MagicMock())
        repr_str = repr(cluster)
        assert "Cluster" in repr_str
        assert "key=1" in repr_str
        assert "Production" in repr_str
        assert "Online" in repr_str


class TestVSANStatus:
    """Tests for VSANStatus resource object."""

    def test_cluster_name_property(self) -> None:
        """Test cluster_name property."""
        data = {"$key": 1, "name": "Production"}
        status = VSANStatus(data, MagicMock())
        assert status.cluster_name == "Production"

    def test_health_status_healthy(self) -> None:
        """Test health_status property for online."""
        data = {"$key": 1, "state": "online"}
        status = VSANStatus(data, MagicMock())
        assert status.health_status == "Healthy"

    def test_health_status_degraded(self) -> None:
        """Test health_status property for warning."""
        data = {"$key": 1, "state": "warning"}
        status = VSANStatus(data, MagicMock())
        assert status.health_status == "Degraded"

    def test_health_status_critical(self) -> None:
        """Test health_status property for error."""
        data = {"$key": 1, "state": "error"}
        status = VSANStatus(data, MagicMock())
        assert status.health_status == "Critical"

    def test_health_status_offline(self) -> None:
        """Test health_status property for offline."""
        data = {"$key": 1, "state": "offline"}
        status = VSANStatus(data, MagicMock())
        assert status.health_status == "Offline"

    def test_health_status_unknown(self) -> None:
        """Test health_status property for unknown state."""
        data = {"$key": 1, "state": "unknown_state"}
        status = VSANStatus(data, MagicMock())
        assert status.health_status == "Unknown"

    def test_tiers_property(self) -> None:
        """Test tiers property."""
        data = {
            "$key": 1,
            "tiers": [
                {
                    "tier": 1,
                    "status": "online",
                    "used": 1073741824,  # 1 GB
                    "capacity": 10737418240,  # 10 GB
                    "read_ops": 100,
                    "write_ops": 50,
                    "read_bps": 1000,
                    "write_bps": 500,
                }
            ],
        }
        status = VSANStatus(data, MagicMock())
        tiers = status.tiers
        assert len(tiers) == 1
        assert tiers[0]["tier"] == 1
        assert tiers[0]["used_gb"] == 1.0
        assert tiers[0]["capacity_gb"] == 10.0
        assert tiers[0]["used_percent"] == 10.0

    def test_repr(self) -> None:
        """Test __repr__ method."""
        data = {
            "$key": 1,
            "name": "Production",
            "state": "online",
            "online_nodes": 3,
            "total_nodes": 4,
        }
        status = VSANStatus(data, MagicMock())
        repr_str = repr(status)
        assert "VSANStatus" in repr_str
        assert "Production" in repr_str


class TestClusterManager:
    """Tests for ClusterManager."""

    def test_init(self) -> None:
        """Test ClusterManager initialization."""
        mock_client = MagicMock()
        manager = ClusterManager(mock_client)
        assert manager._client == mock_client
        assert manager._endpoint == "clusters"

    def test_to_model(self) -> None:
        """Test _to_model creates Cluster object."""
        mock_client = MagicMock()
        manager = ClusterManager(mock_client)
        data = {"$key": 1, "name": "Test"}
        cluster = manager._to_model(data)
        assert isinstance(cluster, Cluster)
        assert cluster.name == "Test"


class TestClusterManagerList:
    """Tests for ClusterManager.list() method."""

    def test_list_returns_clusters(self) -> None:
        """Test list returns Cluster objects."""
        mock_client = MagicMock()
        mock_client._request.return_value = [
            {"$key": 1, "name": "Cluster1"},
            {"$key": 2, "name": "Cluster2"},
        ]
        manager = ClusterManager(mock_client)

        clusters = manager.list()

        assert len(clusters) == 2
        assert all(isinstance(c, Cluster) for c in clusters)
        assert clusters[0].name == "Cluster1"
        assert clusters[1].name == "Cluster2"

    def test_list_empty_response(self) -> None:
        """Test list with empty response."""
        mock_client = MagicMock()
        mock_client._request.return_value = None
        manager = ClusterManager(mock_client)

        clusters = manager.list()

        assert clusters == []

    def test_list_single_object_response(self) -> None:
        """Test list with single object response."""
        mock_client = MagicMock()
        mock_client._request.return_value = {"$key": 1, "name": "Single"}
        manager = ClusterManager(mock_client)

        clusters = manager.list()

        assert len(clusters) == 1
        assert clusters[0].name == "Single"

    def test_list_with_name_filter(self) -> None:
        """Test list with name filter."""
        mock_client = MagicMock()
        mock_client._request.return_value = [{"$key": 1, "name": "Production"}]
        manager = ClusterManager(mock_client)

        manager.list(name="Production")

        call_args = mock_client._request.call_args
        assert "name eq 'Production'" in call_args[1]["params"]["filter"]

    def test_list_with_enabled_filter(self) -> None:
        """Test list with enabled filter."""
        mock_client = MagicMock()
        mock_client._request.return_value = []
        manager = ClusterManager(mock_client)

        manager.list(enabled=True)

        call_args = mock_client._request.call_args
        assert "enabled eq true" in call_args[1]["params"]["filter"]

    def test_list_with_compute_filter(self) -> None:
        """Test list with compute filter."""
        mock_client = MagicMock()
        mock_client._request.return_value = []
        manager = ClusterManager(mock_client)

        manager.list(compute=True)

        call_args = mock_client._request.call_args
        assert "compute eq true" in call_args[1]["params"]["filter"]

    def test_list_with_storage_filter(self) -> None:
        """Test list with storage filter."""
        mock_client = MagicMock()
        mock_client._request.return_value = []
        manager = ClusterManager(mock_client)

        manager.list(storage=False)

        call_args = mock_client._request.call_args
        assert "storage eq false" in call_args[1]["params"]["filter"]

    def test_list_with_pagination(self) -> None:
        """Test list with pagination parameters."""
        mock_client = MagicMock()
        mock_client._request.return_value = []
        manager = ClusterManager(mock_client)

        manager.list(limit=10, offset=20)

        call_args = mock_client._request.call_args
        assert call_args[1]["params"]["limit"] == 10
        assert call_args[1]["params"]["offset"] == 20

    def test_list_uses_default_fields(self) -> None:
        """Test list uses default fields."""
        mock_client = MagicMock()
        mock_client._request.return_value = []
        manager = ClusterManager(mock_client)

        manager.list()

        call_args = mock_client._request.call_args
        fields = call_args[1]["params"]["fields"]
        assert "$key" in fields
        assert "name" in fields
        assert "status#status as status_state" in fields


class TestClusterManagerGet:
    """Tests for ClusterManager.get() method."""

    def test_get_by_key(self) -> None:
        """Test get by key."""
        mock_client = MagicMock()
        mock_client._request.return_value = {"$key": 1, "name": "Production"}
        manager = ClusterManager(mock_client)

        cluster = manager.get(1)

        assert cluster.key == 1
        assert cluster.name == "Production"
        mock_client._request.assert_called_once()

    def test_get_by_name(self) -> None:
        """Test get by name."""
        mock_client = MagicMock()
        mock_client._request.return_value = [{"$key": 1, "name": "Production"}]
        manager = ClusterManager(mock_client)

        cluster = manager.get(name="Production")

        assert cluster.name == "Production"

    def test_get_not_found_raises(self) -> None:
        """Test get raises NotFoundError when not found."""
        mock_client = MagicMock()
        mock_client._request.return_value = None
        manager = ClusterManager(mock_client)

        with pytest.raises(NotFoundError):
            manager.get(999)

    def test_get_no_key_or_name_raises(self) -> None:
        """Test get raises ValueError when neither key nor name provided."""
        mock_client = MagicMock()
        manager = ClusterManager(mock_client)

        with pytest.raises(ValueError, match="key or name"):
            manager.get()


class TestClusterManagerCreate:
    """Tests for ClusterManager.create() method."""

    def test_create_basic(self) -> None:
        """Test create with basic parameters."""
        mock_client = MagicMock()
        mock_client._request.side_effect = [
            {"$key": 2, "name": "NewCluster"},  # POST response
            {"$key": 2, "name": "NewCluster", "enabled": True},  # GET response
        ]
        manager = ClusterManager(mock_client)

        cluster = manager.create(name="NewCluster")

        assert cluster.name == "NewCluster"
        # Verify POST was called
        post_call = mock_client._request.call_args_list[0]
        assert post_call[0][0] == "POST"
        assert post_call[0][1] == "clusters"
        assert post_call[1]["json_data"]["name"] == "NewCluster"

    def test_create_with_all_parameters(self) -> None:
        """Test create with all parameters."""
        mock_client = MagicMock()
        mock_client._request.side_effect = [
            {"$key": 2},  # POST response
            {"$key": 2, "name": "FullCluster"},  # GET response
        ]
        manager = ClusterManager(mock_client)

        manager.create(
            name="FullCluster",
            description="Full test cluster",
            enabled=True,
            compute=True,
            nested_virtualization=True,
            allow_nested_virt_migration=True,
            allow_vgpu_migration=True,
            default_cpu="EPYC-Milan",
            disable_cpu_security_mitigations=False,
            disable_smt=False,
            enable_split_lock_detection=False,
            energy_perf_policy="performance",
            scaling_governor="performance",
            ram_per_unit=4096,
            cores_per_unit=1,
            cost_per_unit=0,
            price_per_unit=0,
            max_ram_per_vm=65536,
            max_cores_per_vm=16,
            target_ram_percent=80,
            ram_overcommit_percent=0,
            storage_cache_per_node=1024,
            storage_buffer_per_node=512,
            storage_hugepages=True,
            enable_nvme_power_management=False,
            swap_tier=-1,
            swap_per_drive=1024,
            max_core_temp=85,
            critical_core_temp=95,
            max_core_temp_warn_percent=10,
            disable_sleep=False,
            log_filter="level:error",
        )

        post_call = mock_client._request.call_args_list[0]
        body = post_call[1]["json_data"]
        assert body["name"] == "FullCluster"
        assert body["description"] == "Full test cluster"
        assert body["compute"] is True
        assert body["kvm_nested"] is True
        assert body["default_cpu"] == "EPYC-Milan"
        assert body["max_ram_per_vm"] == 65536
        assert body["storage_cachesize"] == 1024
        assert body["log_filter"] == "level:error"

    def test_create_name_too_long_raises(self) -> None:
        """Test create raises ValidationError for name too long."""
        mock_client = MagicMock()
        manager = ClusterManager(mock_client)

        with pytest.raises(ValidationError, match="1-128 characters"):
            manager.create(name="x" * 129)

    def test_create_empty_name_raises(self) -> None:
        """Test create raises ValidationError for empty name."""
        mock_client = MagicMock()
        manager = ClusterManager(mock_client)

        with pytest.raises(ValidationError, match="1-128 characters"):
            manager.create(name="")

    def test_create_description_too_long_raises(self) -> None:
        """Test create raises ValidationError for description too long."""
        mock_client = MagicMock()
        manager = ClusterManager(mock_client)

        with pytest.raises(ValidationError, match="max 2048 characters"):
            manager.create(name="Test", description="x" * 2049)

    def test_create_invalid_cpu_type_raises(self) -> None:
        """Test create raises ValidationError for invalid CPU type."""
        mock_client = MagicMock()
        manager = ClusterManager(mock_client)

        with pytest.raises(ValidationError, match="Invalid CPU type"):
            manager.create(name="Test", default_cpu="invalid_cpu")


class TestClusterManagerUpdate:
    """Tests for ClusterManager.update() method."""

    def test_update_single_field(self) -> None:
        """Test update with single field."""
        mock_client = MagicMock()
        mock_client._request.side_effect = [
            None,  # PUT response
            {"$key": 1, "name": "Cluster", "max_ram_per_vm": 131072},  # GET response
        ]
        manager = ClusterManager(mock_client)

        cluster = manager.update(1, max_ram_per_vm=131072)

        assert cluster.max_ram_per_vm == 131072
        # Verify PUT was called
        put_call = mock_client._request.call_args_list[0]
        assert put_call[0][0] == "PUT"
        assert put_call[0][1] == "clusters/1"
        assert put_call[1]["json_data"]["max_ram_per_vm"] == 131072

    def test_update_multiple_fields(self) -> None:
        """Test update with multiple fields."""
        mock_client = MagicMock()
        mock_client._request.side_effect = [
            None,  # PUT response
            {"$key": 1, "name": "NewName", "description": "New desc"},  # GET response
        ]
        manager = ClusterManager(mock_client)

        manager.update(1, name="NewName", description="New desc")

        put_call = mock_client._request.call_args_list[0]
        body = put_call[1]["json_data"]
        assert body["name"] == "NewName"
        assert body["description"] == "New desc"

    def test_update_no_changes_returns_current(self) -> None:
        """Test update with no changes returns current state."""
        mock_client = MagicMock()
        mock_client._request.return_value = {"$key": 1, "name": "Cluster"}
        manager = ClusterManager(mock_client)

        cluster = manager.update(1)

        assert cluster.name == "Cluster"
        # Only GET should be called, no PUT
        mock_client._request.assert_called_once()
        call_args = mock_client._request.call_args
        assert call_args[0][0] == "GET"

    def test_update_name_too_long_raises(self) -> None:
        """Test update raises ValidationError for name too long."""
        mock_client = MagicMock()
        manager = ClusterManager(mock_client)

        with pytest.raises(ValidationError, match="max 128 characters"):
            manager.update(1, name="x" * 129)

    def test_update_invalid_cpu_type_raises(self) -> None:
        """Test update raises ValidationError for invalid CPU type."""
        mock_client = MagicMock()
        manager = ClusterManager(mock_client)

        with pytest.raises(ValidationError, match="Invalid CPU type"):
            manager.update(1, default_cpu="invalid_cpu")


class TestClusterManagerDelete:
    """Tests for ClusterManager.delete() method."""

    def test_delete_success(self) -> None:
        """Test delete succeeds for empty cluster."""
        mock_client = MagicMock()
        # First call: GET to check cluster, Second call: DELETE
        mock_client._request.side_effect = [
            {"$key": 1, "name": "Empty", "total_nodes": 0, "running_machines": 0},
            None,
        ]
        manager = ClusterManager(mock_client)

        manager.delete(1)

        # Verify DELETE was called
        delete_call = mock_client._request.call_args_list[1]
        assert delete_call[0][0] == "DELETE"
        assert delete_call[0][1] == "clusters/1"

    def test_delete_with_nodes_raises(self) -> None:
        """Test delete raises ValidationError when cluster has nodes."""
        mock_client = MagicMock()
        mock_client._request.return_value = {
            "$key": 1,
            "name": "WithNodes",
            "total_nodes": 2,
            "running_machines": 0,
        }
        manager = ClusterManager(mock_client)

        with pytest.raises(ValidationError, match="2 node\\(s\\) assigned"):
            manager.delete(1)

    def test_delete_with_running_machines_raises(self) -> None:
        """Test delete raises ValidationError when cluster has running machines."""
        mock_client = MagicMock()
        mock_client._request.return_value = {
            "$key": 1,
            "name": "WithVMs",
            "total_nodes": 0,
            "running_machines": 5,
        }
        manager = ClusterManager(mock_client)

        with pytest.raises(ValidationError, match="5 running machine\\(s\\)"):
            manager.delete(1)


class TestClusterManagerVSANStatus:
    """Tests for ClusterManager.vsan_status() method."""

    def test_vsan_status_returns_list(self) -> None:
        """Test vsan_status returns list of VSANStatus objects."""
        mock_client = MagicMock()
        mock_client._request.return_value = [
            {"$key": 1, "name": "Cluster1", "state": "online"},
            {"$key": 2, "name": "Cluster2", "state": "warning"},
        ]
        manager = ClusterManager(mock_client)

        statuses = manager.vsan_status()

        assert len(statuses) == 2
        assert all(isinstance(s, VSANStatus) for s in statuses)
        assert statuses[0].cluster_name == "Cluster1"
        assert statuses[0].health_status == "Healthy"
        assert statuses[1].health_status == "Degraded"

    def test_vsan_status_with_cluster_name_filter(self) -> None:
        """Test vsan_status with cluster name filter."""
        mock_client = MagicMock()
        mock_client._request.return_value = [{"$key": 1, "name": "Production"}]
        manager = ClusterManager(mock_client)

        manager.vsan_status(cluster_name="Production")

        call_args = mock_client._request.call_args
        assert "name eq 'Production'" in call_args[1]["params"]["filter"]

    def test_vsan_status_with_tiers(self) -> None:
        """Test vsan_status with include_tiers=True."""
        mock_client = MagicMock()
        mock_client._request.return_value = []
        manager = ClusterManager(mock_client)

        manager.vsan_status(include_tiers=True)

        call_args = mock_client._request.call_args
        fields = call_args[1]["params"]["fields"]
        assert "tiers[" in fields

    def test_vsan_status_empty_response(self) -> None:
        """Test vsan_status with empty response."""
        mock_client = MagicMock()
        mock_client._request.return_value = None
        manager = ClusterManager(mock_client)

        statuses = manager.vsan_status()

        assert statuses == []


class TestCPUTypes:
    """Tests for CPU_TYPES constant."""

    def test_cpu_types_contains_common_types(self) -> None:
        """Test CPU_TYPES contains common CPU types."""
        assert "host" in CPU_TYPES
        assert "EPYC-Milan" in CPU_TYPES
        assert "EPYC-Rome" in CPU_TYPES
        assert "Cascadelake-Server" in CPU_TYPES
        assert "qemu64" in CPU_TYPES

    def test_cpu_types_is_list(self) -> None:
        """Test CPU_TYPES is a list."""
        assert isinstance(CPU_TYPES, list)
        assert len(CPU_TYPES) > 0
