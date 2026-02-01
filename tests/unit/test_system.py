"""Unit tests for System operations (settings, statistics, licenses, diagnostics, inventory)."""

from __future__ import annotations

import time
from unittest.mock import MagicMock

import pytest

from pyvergeos import VergeClient
from pyvergeos.exceptions import APIError, NotFoundError, TaskTimeoutError
from pyvergeos.resources.system import (
    DIAG_STATUS_BUILDING,
    DIAG_STATUS_COMPLETE,
    DIAG_STATUS_ERROR,
    DIAG_STATUS_INITIALIZING,
    InventoryCluster,
    InventoryNetwork,
    InventoryNode,
    InventoryStorageTier,
    InventoryTenant,
    InventoryVM,
    License,
    RootCertificate,
    SystemDiagnostic,
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

    def test_get_setting_not_found(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
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

    def test_get_license_by_key(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
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

    def test_get_license_by_name(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
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

    def test_get_license_not_found(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
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

    def test_statistics_to_dict(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
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

    def test_statistics_repr(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
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
                    {
                        "$key": 1,
                        "name": "vm1",
                        "cpu_cores": 4,
                        "ram": 4096,
                        "power_state": "running",
                    },
                    {
                        "$key": 2,
                        "name": "vm2",
                        "cpu_cores": 2,
                        "ram": 2048,
                        "power_state": "stopped",
                    },
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
                response.json.return_value = [{"$key": 1, "name": "tenant1", "is_running": True}]
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
            InventoryVM(
                {"$key": 1, "name": "vm1", "cpu_cores": 4, "ram": 4096, "power_state": "running"}
            ),
            InventoryVM(
                {"$key": 2, "name": "vm2", "cpu_cores": 2, "ram": 2048, "power_state": "stopped"}
            ),
        ]
        networks = [InventoryNetwork({"$key": 1, "name": "net1", "power_state": "running"})]
        storage = [
            InventoryStorageTier({"tier": 1, "capacity": 1073741824000, "used": 107374182400})
        ]
        nodes = [InventoryNode({"$key": 1, "name": "node1", "cores": 16, "ram": 65536})]
        clusters = [InventoryCluster({"$key": 1, "name": "cluster1", "total_nodes": 2})]
        tenants = [InventoryTenant({"$key": 1, "name": "tenant1", "is_running": True})]

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

    def test_system_manager_diagnostics_lazy_loading(self, mock_client: VergeClient) -> None:
        """Test that diagnostics manager is lazily loaded."""
        system = mock_client.system

        # Access diagnostics twice - should return same instance
        diag1 = system.diagnostics
        diag2 = system.diagnostics
        assert diag1 is diag2

    def test_system_manager_root_certificates_lazy_loading(self, mock_client: VergeClient) -> None:
        """Test that root_certificates manager is lazily loaded."""
        system = mock_client.system

        # Access root_certificates twice - should return same instance
        certs1 = system.root_certificates
        certs2 = system.root_certificates
        assert certs1 is certs2


# =============================================================================
# Settings Manager Extended Tests
# =============================================================================


class TestSettingsManagerExtended:
    """Unit tests for SettingsManager extended functionality."""

    def test_update_setting(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test updating a system setting."""
        # First call is GET to find the setting, second is PUT, third is GET for refresh
        mock_session.request.return_value.json.side_effect = [
            [{"$key": 1, "key": "max_connections", "value": "500", "default_value": "500"}],
            None,  # PUT returns no content
            [{"$key": 1, "key": "max_connections", "value": "1000", "default_value": "500"}],
        ]

        setting = mock_client.system.settings.update("max_connections", "1000")

        assert setting.value == "1000"
        assert setting.is_modified is True

    def test_update_setting_not_found(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test updating a non-existent setting raises NotFoundError."""
        mock_session.request.return_value.json.return_value = []

        with pytest.raises(NotFoundError):
            mock_client.system.settings.update("nonexistent", "value")

    def test_update_setting_requires_key(self, mock_client: VergeClient) -> None:
        """Test that update requires a key."""
        with pytest.raises(ValueError, match="Setting key must be provided"):
            mock_client.system.settings.update("", "value")

    def test_reset_setting(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test resetting a setting to default value."""
        mock_session.request.return_value.json.side_effect = [
            # First call: get current setting
            [{"$key": 1, "key": "max_connections", "value": "1000", "default_value": "500"}],
            # Second call: get for update
            [{"$key": 1, "key": "max_connections", "value": "1000", "default_value": "500"}],
            # Third call: PUT
            None,
            # Fourth call: get updated setting
            [{"$key": 1, "key": "max_connections", "value": "500", "default_value": "500"}],
        ]

        setting = mock_client.system.settings.reset("max_connections")

        assert setting.value == "500"
        assert setting.is_modified is False

    def test_list_modified(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test listing only modified settings."""
        mock_session.request.return_value.json.return_value = [
            {"key": "setting1", "value": "modified_value", "default_value": "default"},
            {"key": "setting2", "value": "same", "default_value": "same"},
            {"key": "setting3", "value": "also_modified", "default_value": "other_default"},
        ]

        modified = mock_client.system.settings.list_modified()

        # Should only return settings where value != default_value
        assert len(modified) == 2
        assert all(s.is_modified for s in modified)


# =============================================================================
# License Manager Extended Tests
# =============================================================================


class TestLicenseManagerExtended:
    """Unit tests for LicenseManager extended functionality."""

    def test_generate_payload(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test generating license request payload."""
        mock_session.request.return_value.json.return_value = {
            "payload": "BASE64_ENCODED_PAYLOAD_DATA"
        }

        payload = mock_client.system.licenses.generate_payload()

        assert payload == "BASE64_ENCODED_PAYLOAD_DATA"
        # Verify correct endpoint was called
        call_args = mock_session.request.call_args
        assert "license_actions" in str(call_args)

    def test_generate_payload_json_response(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test generate_payload with full JSON response (no payload field)."""
        mock_session.request.return_value.json.return_value = {
            "system_id": "12345",
            "fingerprint": "abc123",
        }

        payload = mock_client.system.licenses.generate_payload()

        # Should return JSON-serialized response
        assert "system_id" in payload
        assert "12345" in payload

    def test_generate_payload_no_response(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test generate_payload with no response raises APIError."""
        mock_session.request.return_value.json.return_value = None

        with pytest.raises(APIError):
            mock_client.system.licenses.generate_payload()

    def test_add_license(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test adding a new license."""
        mock_session.request.return_value.json.side_effect = [
            {"$key": 5},  # POST response
            {"$key": 5, "name": "New License", "valid_from": 1700000000, "valid_until": 1900000000},
        ]

        lic = mock_client.system.licenses.add("LICENSE_KEY_TEXT")

        assert lic.name == "New License"

    def test_add_license_no_response(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test add_license with no response raises APIError."""
        mock_session.request.return_value.json.return_value = None

        with pytest.raises(APIError):
            mock_client.system.licenses.add("LICENSE_KEY")


# =============================================================================
# System Diagnostic Tests
# =============================================================================


class TestSystemDiagnostic:
    """Unit tests for SystemDiagnostic model."""

    def test_diagnostic_properties(self, mock_client: VergeClient) -> None:
        """Test SystemDiagnostic property accessors."""
        data = {
            "$key": 1,
            "name": "Support-12345",
            "description": "Network issue investigation",
            "status": DIAG_STATUS_COMPLETE,
            "status_info": "All nodes complete",
            "file": 100,
            "timestamp": 1700000000,
        }
        diag = SystemDiagnostic(data, mock_client.system.diagnostics)

        assert diag.key == 1
        assert diag.name == "Support-12345"
        assert diag.description == "Network issue investigation"
        assert diag.status == DIAG_STATUS_COMPLETE
        assert diag.status_display == "Complete"
        assert diag.status_info == "All nodes complete"
        assert diag.file_key == 100
        assert diag.is_complete is True
        assert diag.is_building is False
        assert diag.has_error is False
        assert diag.created_at is not None

    def test_diagnostic_is_building(self, mock_client: VergeClient) -> None:
        """Test is_building property."""
        for status in [DIAG_STATUS_INITIALIZING, DIAG_STATUS_BUILDING]:
            data = {"$key": 1, "status": status}
            diag = SystemDiagnostic(data, mock_client.system.diagnostics)
            assert diag.is_building is True
            assert diag.is_complete is False

    def test_diagnostic_has_error(self, mock_client: VergeClient) -> None:
        """Test has_error property."""
        data = {"$key": 1, "status": DIAG_STATUS_ERROR, "status_info": "Node timeout"}
        diag = SystemDiagnostic(data, mock_client.system.diagnostics)

        assert diag.has_error is True
        assert diag.is_complete is False
        assert diag.is_building is False

    def test_diagnostic_repr(self, mock_client: VergeClient) -> None:
        """Test SystemDiagnostic string representation."""
        data = {"$key": 1, "name": "Test Diag", "status": DIAG_STATUS_COMPLETE}
        diag = SystemDiagnostic(data, mock_client.system.diagnostics)

        repr_str = repr(diag)
        assert "SystemDiagnostic" in repr_str
        assert "Test Diag" in repr_str
        assert "Complete" in repr_str


class TestSystemDiagnosticManager:
    """Unit tests for SystemDiagnosticManager."""

    def test_list_diagnostics(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test listing system diagnostics."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "name": "Diag1", "status": DIAG_STATUS_COMPLETE},
            {"$key": 2, "name": "Diag2", "status": DIAG_STATUS_BUILDING},
        ]

        diagnostics = mock_client.system.diagnostics.list()

        assert len(diagnostics) == 2
        assert diagnostics[0].name == "Diag1"
        assert diagnostics[1].name == "Diag2"

    def test_list_diagnostics_with_status_filter(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test listing diagnostics filtered by status."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "name": "Complete Diag", "status": DIAG_STATUS_COMPLETE}
        ]

        diagnostics = mock_client.system.diagnostics.list(status=DIAG_STATUS_COMPLETE)

        assert len(diagnostics) == 1
        # Verify filter was applied
        call_args = mock_session.request.call_args
        assert "status eq 'complete'" in str(call_args)

    def test_get_diagnostic(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test getting a specific diagnostic."""
        mock_session.request.return_value.json.return_value = {
            "$key": 1,
            "name": "Support-12345",
            "status": DIAG_STATUS_COMPLETE,
            "file": 100,
        }

        diag = mock_client.system.diagnostics.get(1)

        assert diag.key == 1
        assert diag.name == "Support-12345"

    def test_build_diagnostic(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test building a new diagnostic."""
        mock_session.request.return_value.json.side_effect = [
            {"$key": 5},  # POST response
            {
                "$key": 5,
                "name": "New Diagnostic",
                "status": DIAG_STATUS_INITIALIZING,
            },  # GET response
        ]

        diag = mock_client.system.diagnostics.build(
            name="New Diagnostic",
            description="Test description",
            send_to_support=True,
        )

        assert diag.key == 5
        assert diag.status == DIAG_STATUS_INITIALIZING

        # Verify POST was called with correct body - find the POST call
        post_calls = [
            c for c in mock_session.request.call_args_list if c.kwargs.get("method") == "POST"
        ]
        assert len(post_calls) >= 1
        post_call = post_calls[0]
        assert "json" in post_call.kwargs
        json_data = post_call.kwargs["json"]
        assert json_data["name"] == "New Diagnostic"
        assert json_data["description"] == "Test description"
        assert json_data["send2support"] is True

    def test_build_diagnostic_no_response(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test build diagnostic with no response raises APIError."""
        mock_session.request.return_value.json.return_value = None

        with pytest.raises(APIError):
            mock_client.system.diagnostics.build(name="Test")

    def test_send_to_support(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test sending diagnostic to support."""
        mock_session.request.return_value.json.side_effect = [
            {"$key": 1, "name": "Diag", "status": DIAG_STATUS_COMPLETE},  # GET
            None,  # POST action
        ]

        mock_client.system.diagnostics.send_to_support(1)

        # Verify action endpoint was called
        call_args = mock_session.request.call_args_list[-1]
        assert "system_diagnostic_actions" in str(call_args)

    def test_send_to_support_not_complete(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test sending incomplete diagnostic raises ValueError."""
        mock_session.request.return_value.json.return_value = {
            "$key": 1,
            "name": "Diag",
            "status": DIAG_STATUS_BUILDING,
        }

        with pytest.raises(ValueError, match="must be complete"):
            mock_client.system.diagnostics.send_to_support(1)

    def test_delete_diagnostic(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test deleting a diagnostic."""
        mock_session.request.return_value.json.return_value = None

        mock_client.system.diagnostics.delete(1)

        call_args = mock_session.request.call_args
        assert "DELETE" in str(call_args)
        assert "system_diagnostics/1" in str(call_args)

    def test_update_diagnostic(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test updating a diagnostic's name/description."""
        mock_session.request.return_value.json.side_effect = [
            None,  # PUT response
            {"$key": 1, "name": "Updated Name", "status": DIAG_STATUS_COMPLETE},  # GET
        ]

        diag = mock_client.system.diagnostics.update(1, name="Updated Name")

        assert diag.name == "Updated Name"

    def test_get_download_url(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test getting download URL for diagnostic."""
        mock_session.request.return_value.json.side_effect = [
            {"$key": 1, "name": "Diag", "status": DIAG_STATUS_COMPLETE, "file": 100},  # GET diag
            {"$key": 100, "name": "diag.tar.gz", "path": "downloads/diag.tar.gz"},  # GET file
        ]

        url = mock_client.system.diagnostics.get_download_url(1)

        assert url is not None
        assert "downloads/diag.tar.gz" in url

    def test_get_download_url_not_complete(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test get_download_url raises for incomplete diagnostic."""
        mock_session.request.return_value.json.return_value = {
            "$key": 1,
            "name": "Diag",
            "status": DIAG_STATUS_BUILDING,
        }

        with pytest.raises(ValueError, match="must be complete"):
            mock_client.system.diagnostics.get_download_url(1)


class TestSystemDiagnosticWaitForCompletion:
    """Unit tests for SystemDiagnostic.wait_for_completion."""

    def test_wait_for_completion_success(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test waiting for diagnostic completion."""
        # Simulate building -> complete transition
        mock_session.request.return_value.json.side_effect = [
            {"$key": 1, "name": "Diag", "status": DIAG_STATUS_BUILDING},  # refresh 1
            {"$key": 1, "name": "Diag", "status": DIAG_STATUS_COMPLETE},  # refresh 2
        ]

        initial_data = {"$key": 1, "name": "Diag", "status": DIAG_STATUS_BUILDING}
        diag = SystemDiagnostic(initial_data, mock_client.system.diagnostics)

        completed = diag.wait_for_completion(timeout=10, poll_interval=0.01)

        assert completed.is_complete is True

    def test_wait_for_completion_error(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test wait_for_completion returns on error status."""
        mock_session.request.return_value.json.return_value = {
            "$key": 1,
            "name": "Diag",
            "status": DIAG_STATUS_ERROR,
            "status_info": "Node failed",
        }

        initial_data = {"$key": 1, "name": "Diag", "status": DIAG_STATUS_BUILDING}
        diag = SystemDiagnostic(initial_data, mock_client.system.diagnostics)

        result = diag.wait_for_completion(timeout=10, poll_interval=0.01)

        assert result.has_error is True

    def test_wait_for_completion_timeout(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test wait_for_completion raises TaskTimeoutError on timeout."""
        mock_session.request.return_value.json.return_value = {
            "$key": 1,
            "name": "Diag",
            "status": DIAG_STATUS_BUILDING,
        }

        initial_data = {"$key": 1, "name": "Diag", "status": DIAG_STATUS_BUILDING}
        diag = SystemDiagnostic(initial_data, mock_client.system.diagnostics)

        with pytest.raises(TaskTimeoutError):
            diag.wait_for_completion(timeout=0.05, poll_interval=0.01)


# =============================================================================
# Root Certificate Tests
# =============================================================================


class TestRootCertificate:
    """Unit tests for RootCertificate model."""

    def test_certificate_properties(self, mock_client: VergeClient) -> None:
        """Test RootCertificate property accessors."""
        data = {
            "$key": 1,
            "subject": "CN=Enterprise CA, O=Acme Corp",
            "issuer": "CN=Enterprise CA, O=Acme Corp",
            "fingerprint": "AB:CD:EF:12:34:56:78:90",
            "startdate": "2024-01-01",
            "enddate": "2034-01-01",
            "cert": "-----BEGIN CERTIFICATE-----\nMIID...\n-----END CERTIFICATE-----",
            "modified": 1700000000,
        }
        cert = RootCertificate(data, mock_client.system.root_certificates)

        assert cert.key == 1
        assert cert.subject == "CN=Enterprise CA, O=Acme Corp"
        assert cert.issuer == "CN=Enterprise CA, O=Acme Corp"
        assert cert.fingerprint == "AB:CD:EF:12:34:56:78:90"
        assert cert.start_date == "2024-01-01"
        assert cert.end_date == "2034-01-01"
        assert "BEGIN CERTIFICATE" in cert.cert_pem
        assert cert.modified_at is not None

    def test_certificate_repr(self, mock_client: VergeClient) -> None:
        """Test RootCertificate string representation."""
        data = {"$key": 1, "subject": "CN=Test CA"}
        cert = RootCertificate(data, mock_client.system.root_certificates)

        repr_str = repr(cert)
        assert "RootCertificate" in repr_str
        assert "CN=Test CA" in repr_str


class TestRootCertificateManager:
    """Unit tests for RootCertificateManager."""

    def test_list_certificates(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test listing root certificates."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "subject": "CN=CA1", "fingerprint": "AA:BB"},
            {"$key": 2, "subject": "CN=CA2", "fingerprint": "CC:DD"},
        ]

        certs = mock_client.system.root_certificates.list()

        assert len(certs) == 2
        assert certs[0].subject == "CN=CA1"
        assert certs[1].subject == "CN=CA2"

    def test_get_certificate(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test getting a root certificate by key."""
        mock_session.request.return_value.json.return_value = {
            "$key": 1,
            "subject": "CN=Enterprise CA",
            "cert": "-----BEGIN CERTIFICATE-----\n...\n-----END CERTIFICATE-----",
        }

        cert = mock_client.system.root_certificates.get(1)

        assert cert.key == 1
        assert cert.subject == "CN=Enterprise CA"

    def test_get_by_subject(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test getting a certificate by subject."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "subject": "CN=Enterprise CA, O=Acme"}
        ]

        cert = mock_client.system.root_certificates.get_by_subject("Enterprise")

        assert "Enterprise" in cert.subject

    def test_get_by_subject_not_found(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test get_by_subject raises NotFoundError when not found."""
        mock_session.request.return_value.json.return_value = []

        with pytest.raises(NotFoundError):
            mock_client.system.root_certificates.get_by_subject("Nonexistent")

    def test_get_by_fingerprint(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test getting a certificate by fingerprint."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "subject": "CN=CA", "fingerprint": "AB:CD:EF:12"}
        ]

        cert = mock_client.system.root_certificates.get_by_fingerprint("AB:CD:EF:12")

        assert cert.fingerprint == "AB:CD:EF:12"

    def test_get_by_fingerprint_not_found(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test get_by_fingerprint raises NotFoundError when not found."""
        mock_session.request.return_value.json.return_value = []

        with pytest.raises(NotFoundError):
            mock_client.system.root_certificates.get_by_fingerprint("XX:YY:ZZ")

    def test_create_certificate(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test creating a new root certificate."""
        pem_data = "-----BEGIN CERTIFICATE-----\nMIID...\n-----END CERTIFICATE-----"
        mock_session.request.return_value.json.side_effect = [
            {"$key": 5},  # POST response
            {
                "$key": 5,
                "subject": "CN=New CA",
                "cert": pem_data,
            },  # GET response
        ]

        cert = mock_client.system.root_certificates.create(cert=pem_data)

        assert cert.key == 5
        assert cert.subject == "CN=New CA"

    def test_create_certificate_no_response(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test create raises APIError on no response."""
        mock_session.request.return_value.json.return_value = None

        with pytest.raises(APIError):
            mock_client.system.root_certificates.create(cert="-----BEGIN CERTIFICATE-----")

    def test_delete_certificate(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test deleting a root certificate."""
        mock_session.request.return_value.json.return_value = None

        mock_client.system.root_certificates.delete(1)

        call_args = mock_session.request.call_args
        assert "DELETE" in str(call_args)
        assert "root_certificates/1" in str(call_args)
