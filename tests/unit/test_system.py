"""Unit tests for System operations (settings, statistics, licenses, inventory)."""

from __future__ import annotations

import time
from unittest.mock import MagicMock

import pytest

from pyvergeos import VergeClient
from pyvergeos.exceptions import NotFoundError
from pyvergeos.resources.system import (
    InventoryCluster,
    InventoryNetwork,
    InventoryNode,
    InventoryStorageTier,
    InventoryTenant,
    InventoryVM,
    License,
    SystemInventory,
    SystemSetting,
)

# =============================================================================
# SystemSetting Tests
# =============================================================================


class TestSettingsManager:
    """Unit tests for SettingsManager."""

    def test_list_settings(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test listing system settings."""
        mock_session.request.return_value.json.return_value = [
            {
                "key": "max_connections",
                "value": "500",
                "default_value": "500",
                "description": "Max webserver connections",
            },
            {
                "key": "cloud_name",
                "value": "test-cloud",
                "default_value": "test-cloud",
                "description": "Cloud name",
            },
        ]

        settings = mock_client.system.settings.list()

        assert len(settings) == 2
        assert settings[0].key == "max_connections"
        assert settings[0].value == "500"
        assert settings[1].key == "cloud_name"

    def test_list_settings_with_key_filter(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test listing settings filtered by key contains."""
        mock_session.request.return_value.json.return_value = [
            {
                "key": "net_macprefix",
                "value": "F0:DB:30",
                "default_value": "F0:DB:30",
                "description": "MAC prefix",
            },
            {
                "key": "net_macoffset",
                "value": "12345",
                "default_value": "10000",
                "description": "MAC offset",
            },
        ]

        settings = mock_client.system.settings.list(key_contains="net_")

        assert len(settings) == 2
        # Verify the filter was used in the request
        call_args = mock_session.request.call_args
        assert "net_" in str(call_args)

    def test_get_setting(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test getting a specific setting."""
        mock_session.request.return_value.json.return_value = [
            {
                "key": "max_connections",
                "value": "750",
                "default_value": "500",
                "description": "Max webserver connections",
            }
        ]

        setting = mock_client.system.settings.get("max_connections")

        assert setting.key == "max_connections"
        assert setting.value == "750"
        assert setting.default_value == "500"
        assert setting.is_modified is True

    def test_get_setting_not_found(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test that NotFoundError is raised when setting not found."""
        mock_session.request.return_value.json.return_value = []

        with pytest.raises(NotFoundError):
            mock_client.system.settings.get("nonexistent_setting")

    def test_get_setting_requires_key(self, mock_client: VergeClient) -> None:
        """Test that get() requires a key parameter."""
        with pytest.raises(ValueError, match="Setting key must be provided"):
            mock_client.system.settings.get(None)


class TestSystemSetting:
    """Unit tests for SystemSetting model."""

    def test_setting_properties(self, mock_client: VergeClient) -> None:
        """Test SystemSetting property accessors."""
        data = {
            "key": "test_setting",
            "value": "new_value",
            "default_value": "default_value",
            "description": "Test setting description",
        }
        setting = SystemSetting(data, mock_client.system.settings)

        assert setting.key == "test_setting"
        assert setting.value == "new_value"
        assert setting.default_value == "default_value"
        assert setting.description == "Test setting description"
        assert setting.is_modified is True

    def test_setting_not_modified(self, mock_client: VergeClient) -> None:
        """Test SystemSetting.is_modified when value matches default."""
        data = {
            "key": "unchanged_setting",
            "value": "same_value",
            "default_value": "same_value",
            "description": "Unchanged setting",
        }
        setting = SystemSetting(data, mock_client.system.settings)

        assert setting.is_modified is False

    def test_setting_repr(self, mock_client: VergeClient) -> None:
        """Test SystemSetting string representation."""
        data = {
            "key": "test_key",
            "value": "test_value",
            "default_value": "default",
        }
        setting = SystemSetting(data, mock_client.system.settings)

        repr_str = repr(setting)
        assert "SystemSetting" in repr_str
        assert "test_key" in repr_str
        assert "modified" in repr_str


# =============================================================================
# License Tests
# =============================================================================


class TestLicenseManager:
    """Unit tests for LicenseManager."""

    def test_list_licenses(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test listing licenses."""
        mock_session.request.return_value.json.return_value = [
            {
                "$key": 1,
                "name": "Standard License",
                "description": "Standard features",
                "valid_from": 1700000000,
                "valid_until": 1800000000,
                "auto_renewal": True,
                "allow_branding": False,
            },
            {
                "$key": 2,
                "name": "Enterprise License",
                "description": "Enterprise features",
                "valid_from": 1700000000,
                "valid_until": 0,  # Never expires
                "auto_renewal": False,
                "allow_branding": True,
            },
        ]

        licenses = mock_client.system.licenses.list()

        assert len(licenses) == 2
        assert licenses[0].name == "Standard License"
        assert licenses[1].name == "Enterprise License"

    def test_get_license_by_key(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test getting a license by key."""
        mock_session.request.return_value.json.return_value = {
            "$key": 1,
            "name": "Standard License",
            "description": "Standard features",
            "valid_from": 1700000000,
            "valid_until": 1800000000,
        }

        lic = mock_client.system.licenses.get(key=1)

        assert lic.name == "Standard License"

    def test_get_license_by_name(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test getting a license by name."""
        mock_session.request.return_value.json.return_value = [
            {
                "$key": 1,
                "name": "Production",
                "description": "Production license",
                "valid_from": 1700000000,
                "valid_until": 1900000000,
            }
        ]

        lic = mock_client.system.licenses.get(name="Production")

        assert lic.name == "Production"

    def test_get_license_not_found(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test that NotFoundError is raised when license not found."""
        mock_session.request.return_value.json.return_value = []

        with pytest.raises(NotFoundError):
            mock_client.system.licenses.get(name="Nonexistent")

    def test_get_license_requires_key_or_name(self, mock_client: VergeClient) -> None:
        """Test that get() requires key or name parameter."""
        with pytest.raises(ValueError, match="Either key or name must be provided"):
            mock_client.system.licenses.get()


class TestLicense:
    """Unit tests for License model."""

    def test_license_properties(self, mock_client: VergeClient) -> None:
        """Test License property accessors."""
        data = {
            "$key": 1,
            "name": "Test License",
            "description": "Test description",
            "valid_from": 1700000000,
            "valid_until": 2000000000,  # Far future
            "issued": 1699000000,
            "added": 1699500000,
            "added_by": "admin",
            "auto_renewal": True,
            "allow_branding": False,
            "note": "Test note",
            "features": {"feature1": True, "feature2": False},
        }
        lic = License(data, mock_client.system.licenses)

        assert lic.name == "Test License"
        assert lic.description == "Test description"
        assert lic.added_by == "admin"
        assert lic.auto_renewal is True
        assert lic.allow_branding is False
        assert lic.note == "Test note"
        assert lic.features == {"feature1": True, "feature2": False}
        assert lic.valid_from is not None
        assert lic.valid_until is not None
        assert lic.issued is not None
        assert lic.added is not None

    def test_license_is_valid_true(self, mock_client: VergeClient) -> None:
        """Test License.is_valid returns True for valid license."""
        now = int(time.time())
        data = {
            "$key": 1,
            "name": "Valid License",
            "valid_from": now - 86400,  # Yesterday
            "valid_until": now + 86400 * 365,  # Next year
        }
        lic = License(data, mock_client.system.licenses)

        assert lic.is_valid is True

    def test_license_is_valid_expired(self, mock_client: VergeClient) -> None:
        """Test License.is_valid returns False for expired license."""
        now = int(time.time())
        data = {
            "$key": 1,
            "name": "Expired License",
            "valid_from": now - 86400 * 365,  # Last year
            "valid_until": now - 86400,  # Yesterday
        }
        lic = License(data, mock_client.system.licenses)

        assert lic.is_valid is False

    def test_license_is_valid_not_yet_valid(self, mock_client: VergeClient) -> None:
        """Test License.is_valid returns False for future license."""
        now = int(time.time())
        data = {
            "$key": 1,
            "name": "Future License",
            "valid_from": now + 86400 * 30,  # Next month
            "valid_until": now + 86400 * 365,
        }
        lic = License(data, mock_client.system.licenses)

        assert lic.is_valid is False

    def test_license_features_json_string(self, mock_client: VergeClient) -> None:
        """Test License.features parses JSON string."""
        data = {
            "$key": 1,
            "name": "Test",
            "features": '{"key": "value"}',
        }
        lic = License(data, mock_client.system.licenses)

        assert lic.features == {"key": "value"}

    def test_license_features_invalid_json(self, mock_client: VergeClient) -> None:
        """Test License.features handles invalid JSON gracefully."""
        data = {
            "$key": 1,
            "name": "Test",
            "features": "not valid json",
        }
        lic = License(data, mock_client.system.licenses)

        assert lic.features is None

    def test_license_repr(self, mock_client: VergeClient) -> None:
        """Test License string representation."""
        now = int(time.time())
        data = {
            "$key": 1,
            "name": "Test License",
            "valid_from": now - 86400,
            "valid_until": now + 86400 * 365,
        }
        lic = License(data, mock_client.system.licenses)

        repr_str = repr(lic)
        assert "License" in repr_str
        assert "Test License" in repr_str
        assert "valid" in repr_str


# =============================================================================
# SystemStatistics Tests
# =============================================================================


class TestSystemStatistics:
    """Unit tests for SystemStatistics."""

    def test_get_statistics(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test getting system statistics."""
        mock_session.request.return_value.json.return_value = {
            "machines_count": 10,
            "machines_online": 8,
            "machines_warn": 1,
            "machines_error": 1,
            "tenants_count": 5,
            "tenants_online": 4,
            "vnets_count": 15,
            "vnets_online": 12,
            "nodes_count": 3,
            "nodes_online": 3,
            "clusters_count": 1,
            "clusters_online": 1,
            "storage_tiers_count": 4,
            "users_count": 10,
            "users_online": 8,
            "groups_count": 5,
            "groups_online": 5,
            "alarms_count": 2,
            "alarms_warning": 2,
            "alarms_error": 0,
        }

        stats = mock_client.system.statistics()

        assert stats.vms_total == 10
        assert stats.vms_online == 8
        assert stats.vms_warning == 1
        assert stats.vms_error == 1
        assert stats.tenants_total == 5
        assert stats.tenants_online == 4
        assert stats.networks_total == 15
        assert stats.networks_online == 12
        assert stats.nodes_total == 3
        assert stats.nodes_online == 3
        assert stats.clusters_total == 1
        assert stats.clusters_online == 1
        assert stats.storage_tiers_total == 4
        assert stats.users_total == 10
        assert stats.users_enabled == 8
        assert stats.groups_total == 5
        assert stats.groups_enabled == 5
        assert stats.alarms_total == 2
        assert stats.alarms_warning == 2
        assert stats.alarms_error == 0

    def test_statistics_handles_empty_response(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test statistics handles empty response gracefully."""
        mock_session.request.return_value.json.return_value = None
        mock_session.request.return_value.text = ""

        stats = mock_client.system.statistics()

        assert stats.vms_total == 0
        assert stats.nodes_total == 0

    def test_statistics_handles_object_counts(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test statistics handles object-wrapped counts."""
        mock_session.request.return_value.json.return_value = {
            "machines_count": {"$count": 5},
            "resource_instance_count": {"$count": 10},
            "resource_instance_max": {"instances_total": 100},
        }

        stats = mock_client.system.statistics()

        assert stats.vms_total == 5
        assert stats.resource_instance_count == 10
        assert stats.resource_instance_max == 100

    def test_statistics_to_dict(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test statistics to_dict method."""
        mock_session.request.return_value.json.return_value = {
            "machines_count": 10,
            "machines_online": 8,
            "machines_warn": 1,
            "machines_error": 1,
        }

        stats = mock_client.system.statistics()
        d = stats.to_dict()

        assert "vms" in d
        assert d["vms"]["total"] == 10
        assert d["vms"]["online"] == 8

    def test_statistics_repr(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test statistics string representation."""
        mock_session.request.return_value.json.return_value = {
            "machines_count": 10,
            "machines_online": 8,
            "nodes_count": 3,
            "nodes_online": 3,
            "alarms_count": 2,
        }

        stats = mock_client.system.statistics()
        repr_str = repr(stats)

        assert "SystemStatistics" in repr_str
        assert "VMs=8/10" in repr_str
        assert "Nodes=3/3" in repr_str
        assert "Alarms=2" in repr_str


# =============================================================================
# Inventory Tests
# =============================================================================


class TestInventoryVM:
    """Unit tests for InventoryVM."""

    def test_inventory_vm_properties(self) -> None:
        """Test InventoryVM property accessors."""
        data = {
            "$key": 123,
            "name": "test-vm",
            "description": "Test VM",
            "power_state": "running",
            "cpu_cores": 4,
            "ram": 4096,
            "os_family": "linux",
            "cluster_name": "main",
            "node_name": "node1",
        }
        vm = InventoryVM(data)

        assert vm.key == 123
        assert vm.name == "test-vm"
        assert vm.description == "Test VM"
        assert vm.power_state == "running"
        assert vm.cpu_cores == 4
        assert vm.ram_mb == 4096
        assert vm.ram_gb == 4.0
        assert vm.os_family == "linux"
        assert vm.cluster == "main"
        assert vm.node == "node1"


class TestInventoryNetwork:
    """Unit tests for InventoryNetwork."""

    def test_inventory_network_properties(self) -> None:
        """Test InventoryNetwork property accessors."""
        data = {
            "$key": 100,
            "name": "test-network",
            "description": "Test network",
            "type": "internal",
            "power_state": "running",
            "network": "192.168.1.0/24",
            "ip": "192.168.1.1",
        }
        net = InventoryNetwork(data)

        assert net.key == 100
        assert net.name == "test-network"
        assert net.description == "Test network"
        assert net.network_type == "internal"
        assert net.power_state == "running"
        assert net.network_address == "192.168.1.0/24"
        assert net.ip_address == "192.168.1.1"


class TestInventoryStorageTier:
    """Unit tests for InventoryStorageTier."""

    def test_inventory_storage_tier_properties(self) -> None:
        """Test InventoryStorageTier property accessors."""
        data = {
            "tier": 1,
            "description": "SSD",
            "capacity": 1073741824000,  # ~1000 GB
            "used": 268435456000,  # ~250 GB
        }
        tier = InventoryStorageTier(data)

        assert tier.tier == 1
        assert tier.description == "SSD"
        assert tier.capacity_gb == pytest.approx(1000.0, abs=1.0)
        assert tier.used_gb == pytest.approx(250.0, abs=1.0)
        assert tier.used_percent == 25.0


class TestInventoryNode:
    """Unit tests for InventoryNode."""

    def test_inventory_node_properties(self) -> None:
        """Test InventoryNode property accessors."""
        data = {
            "$key": 1,
            "name": "node1",
            "status_display": "Online",
            "cluster_name": "main",
            "cores": 16,
            "ram": 65536,
        }
        node = InventoryNode(data)

        assert node.key == 1
        assert node.name == "node1"
        assert node.status == "Online"
        assert node.cluster == "main"
        assert node.cores == 16
        assert node.ram_mb == 65536
        assert node.ram_gb == 64.0


class TestInventoryCluster:
    """Unit tests for InventoryCluster."""

    def test_inventory_cluster_properties(self) -> None:
        """Test InventoryCluster property accessors."""
        data = {
            "$key": 1,
            "name": "main-cluster",
            "description": "Main cluster",
            "status_display": "Online",
            "total_nodes": 3,
            "online_nodes": 3,
        }
        cluster = InventoryCluster(data)

        assert cluster.key == 1
        assert cluster.name == "main-cluster"
        assert cluster.description == "Main cluster"
        assert cluster.status == "Online"
        assert cluster.total_nodes == 3
        assert cluster.online_nodes == 3


class TestInventoryTenant:
    """Unit tests for InventoryTenant."""

    def test_inventory_tenant_properties(self) -> None:
        """Test InventoryTenant property accessors."""
        data = {
            "$key": 10,
            "name": "customer-a",
            "description": "Customer A tenant",
            "status_display": "Running",
            "is_running": True,
        }
        tenant = InventoryTenant(data)

        assert tenant.key == 10
        assert tenant.name == "customer-a"
        assert tenant.description == "Customer A tenant"
        assert tenant.status == "Running"
        assert tenant.is_running is True


class TestSystemInventory:
    """Unit tests for SystemInventory."""

    def test_get_inventory(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test getting system inventory."""
        # Setup mock responses for each resource type
        def mock_request(method: str, url: str, **kwargs: object) -> MagicMock:
            response = MagicMock()
            response.status_code = 200

            if "vms" in url:
                response.json.return_value = [
                    {"$key": 1, "name": "vm1", "cpu_cores": 4, "ram": 4096, "power_state": "running"},
                    {"$key": 2, "name": "vm2", "cpu_cores": 2, "ram": 2048, "power_state": "stopped"},
                ]
            elif "vnets" in url:
                response.json.return_value = [
                    {"$key": 1, "name": "net1", "type": "internal", "power_state": "running"}
                ]
            elif "storage_tiers" in url:
                response.json.return_value = [
                    {"tier": 1, "capacity": 1073741824000, "used": 107374182400}
                ]
            elif "nodes" in url:
                response.json.return_value = [
                    {"$key": 1, "name": "node1", "cores": 16, "ram": 65536}
                ]
            elif "clusters" in url:
                response.json.return_value = [
                    {"$key": 1, "name": "cluster1", "total_nodes": 2, "online_nodes": 2}
                ]
            elif "tenants" in url:
                response.json.return_value = [
                    {"$key": 1, "name": "tenant1", "is_running": True}
                ]
            else:
                response.json.return_value = {}

            return response

        mock_session.request.side_effect = mock_request

        inventory = mock_client.system.inventory()

        assert len(inventory.vms) == 2
        assert len(inventory.networks) == 1
        assert len(inventory.storage) == 1
        assert len(inventory.nodes) == 1
        assert len(inventory.clusters) == 1
        assert len(inventory.tenants) == 1

    def test_inventory_summary(self) -> None:
        """Test SystemInventory summary generation."""
        from datetime import datetime, timezone

        vms = [
            InventoryVM({"$key": 1, "name": "vm1", "cpu_cores": 4, "ram": 4096, "power_state": "running"}),
            InventoryVM({"$key": 2, "name": "vm2", "cpu_cores": 2, "ram": 2048, "power_state": "stopped"}),
        ]
        networks = [
            InventoryNetwork({"$key": 1, "name": "net1", "power_state": "running"})
        ]
        storage = [
            InventoryStorageTier({"tier": 1, "capacity": 1073741824000, "used": 107374182400})
        ]
        nodes = [
            InventoryNode({"$key": 1, "name": "node1", "cores": 16, "ram": 65536})
        ]
        clusters = [
            InventoryCluster({"$key": 1, "name": "cluster1", "total_nodes": 2})
        ]
        tenants = [
            InventoryTenant({"$key": 1, "name": "tenant1", "is_running": True})
        ]

        inventory = SystemInventory(
            vms=vms,
            networks=networks,
            storage=storage,
            nodes=nodes,
            clusters=clusters,
            tenants=tenants,
            generated_at=datetime.now(timezone.utc),
        )

        summary = inventory.summary

        assert summary["vms_total"] == 2
        assert summary["vms_running"] == 1
        assert summary["vms_stopped"] == 1
        assert summary["total_cpu_cores"] == 6
        assert summary["total_ram_gb"] == 6.0
        assert summary["networks_total"] == 1
        assert summary["networks_running"] == 1
        assert summary["storage_tiers"] == 1
        assert summary["nodes_total"] == 1
        assert summary["clusters_total"] == 1
        assert summary["tenants_total"] == 1
        assert summary["tenants_running"] == 1

    def test_inventory_repr(self) -> None:
        """Test SystemInventory string representation."""
        from datetime import datetime, timezone

        inventory = SystemInventory(
            vms=[InventoryVM({"$key": 1, "name": "vm1"})],
            networks=[InventoryNetwork({"$key": 1, "name": "net1"})],
            storage=[InventoryStorageTier({"tier": 1})],
            nodes=[InventoryNode({"$key": 1, "name": "node1"})],
            clusters=[InventoryCluster({"$key": 1, "name": "cluster1"})],
            tenants=[InventoryTenant({"$key": 1, "name": "tenant1"})],
            generated_at=datetime.now(timezone.utc),
        )

        repr_str = repr(inventory)

        assert "SystemInventory" in repr_str
        assert "VMs=1" in repr_str
        assert "Networks=1" in repr_str
        assert "Nodes=1" in repr_str

    def test_inventory_partial_collection(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test getting inventory with selective resource types."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "name": "vm1", "cpu_cores": 4, "ram": 4096}
        ]

        inventory = mock_client.system.inventory(
            include_vms=True,
            include_networks=False,
            include_storage=False,
            include_nodes=False,
            include_clusters=False,
            include_tenants=False,
        )

        assert len(inventory.vms) == 1
        assert len(inventory.networks) == 0
        assert len(inventory.storage) == 0
        assert len(inventory.nodes) == 0
        assert len(inventory.clusters) == 0
        assert len(inventory.tenants) == 0


# =============================================================================
# SystemManager Tests
# =============================================================================


class TestSystemManager:
    """Unit tests for SystemManager."""

    def test_system_manager_access(self, mock_client: VergeClient) -> None:
        """Test accessing system manager from client."""
        system = mock_client.system

        assert system is not None
        assert system.settings is not None
        assert system.licenses is not None

    def test_system_manager_lazy_loading(self, mock_client: VergeClient) -> None:
        """Test that sub-managers are lazily loaded."""
        system = mock_client.system

        # Access settings twice - should return same instance
        settings1 = system.settings
        settings2 = system.settings
        assert settings1 is settings2

        # Access licenses twice - should return same instance
        licenses1 = system.licenses
        licenses2 = system.licenses
        assert licenses1 is licenses2
