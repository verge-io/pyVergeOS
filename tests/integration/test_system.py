"""Integration tests for System operations.

These tests require a live VergeOS system and will be skipped
if the environment variables are not set.
"""

from __future__ import annotations

import pytest

from pyvergeos import VergeClient
from pyvergeos.exceptions import NotFoundError


@pytest.mark.integration
class TestSettingsIntegration:
    """Integration tests for SettingsManager."""

    def test_list_settings(self, live_client: VergeClient) -> None:
        """Test listing system settings from live system."""
        settings = live_client.system.settings.list()

        # Should have some settings
        assert isinstance(settings, list)
        assert len(settings) > 0

        # Each setting should have expected properties
        for setting in settings:
            assert hasattr(setting, "key")
            assert hasattr(setting, "value")
            assert setting.key  # Should not be empty

    def test_get_setting(self, live_client: VergeClient) -> None:
        """Test getting a specific setting."""
        # max_connections is a common setting
        setting = live_client.system.settings.get("max_connections")

        assert setting.key == "max_connections"
        assert setting.value is not None
        assert setting.description  # Should have a description

    def test_get_cloud_name_setting(self, live_client: VergeClient) -> None:
        """Test getting cloud_name setting."""
        setting = live_client.system.settings.get("cloud_name")

        assert setting.key == "cloud_name"
        assert setting.value  # Should have a value

    def test_get_nonexistent_setting(self, live_client: VergeClient) -> None:
        """Test that NotFoundError is raised for nonexistent setting."""
        with pytest.raises(NotFoundError):
            live_client.system.settings.get("definitely_nonexistent_setting_xyz123")

    def test_list_settings_with_filter(self, live_client: VergeClient) -> None:
        """Test listing settings with key filter."""
        # Filter for network-related settings
        net_settings = live_client.system.settings.list(key_contains="net_")

        # Should have at least one network setting
        # (net_macprefix, net_macoffset are common)
        for setting in net_settings:
            assert "net_" in setting.key

    def test_setting_is_modified_property(self, live_client: VergeClient) -> None:
        """Test the is_modified property on live settings."""
        settings = live_client.system.settings.list()

        # Check that is_modified is consistent
        for setting in settings:
            if setting.value == setting.default_value:
                assert setting.is_modified is False
            else:
                assert setting.is_modified is True


@pytest.mark.integration
class TestLicenseIntegration:
    """Integration tests for LicenseManager."""

    def test_list_licenses(self, live_client: VergeClient) -> None:
        """Test listing licenses from live system."""
        licenses = live_client.system.licenses.list()

        # Should have at least one license
        assert isinstance(licenses, list)
        # Most systems have at least one license
        if not licenses:
            pytest.skip("No licenses found on system")

        # Each license should have expected properties
        for lic in licenses:
            assert hasattr(lic, "name")
            assert hasattr(lic, "is_valid")

    def test_get_license_by_key(self, live_client: VergeClient) -> None:
        """Test getting a license by key."""
        licenses = live_client.system.licenses.list()
        if not licenses:
            pytest.skip("No licenses found on system")

        lic = live_client.system.licenses.get(key=licenses[0].key)

        assert lic.key == licenses[0].key
        assert lic.name == licenses[0].name

    def test_license_validity_properties(self, live_client: VergeClient) -> None:
        """Test license validity properties on live data."""
        licenses = live_client.system.licenses.list()
        if not licenses:
            pytest.skip("No licenses found on system")

        for lic in licenses:
            # Check that validity properties are accessible
            _ = lic.is_valid
            _ = lic.valid_from
            _ = lic.valid_until
            _ = lic.auto_renewal
            _ = lic.allow_branding


@pytest.mark.integration
class TestStatisticsIntegration:
    """Integration tests for system statistics."""

    def test_get_statistics(self, live_client: VergeClient) -> None:
        """Test getting system statistics from live system."""
        stats = live_client.system.statistics()

        # Should have basic statistics
        assert stats.vms_total >= 0
        assert stats.vms_online >= 0
        assert stats.vms_online <= stats.vms_total

        assert stats.nodes_total >= 0
        assert stats.nodes_online >= 0

        assert stats.clusters_total >= 0

    def test_statistics_consistency(self, live_client: VergeClient) -> None:
        """Test that statistics are internally consistent."""
        stats = live_client.system.statistics()

        # Online should be <= total for each resource
        assert stats.vms_online <= stats.vms_total
        assert stats.nodes_online <= stats.nodes_total
        assert stats.clusters_online <= stats.clusters_total
        assert stats.networks_online <= stats.networks_total
        assert stats.tenants_online <= stats.tenants_total

    def test_statistics_to_dict(self, live_client: VergeClient) -> None:
        """Test converting statistics to dictionary."""
        stats = live_client.system.statistics()
        d = stats.to_dict()

        # Should have expected keys
        assert "vms" in d
        assert "nodes" in d
        assert "clusters" in d
        assert "networks" in d
        assert "tenants" in d
        assert "alarms" in d

        # Nested structure should work
        assert "total" in d["vms"]
        assert "online" in d["vms"]


@pytest.mark.integration
class TestInventoryIntegration:
    """Integration tests for system inventory."""

    def test_get_full_inventory(self, live_client: VergeClient) -> None:
        """Test getting full system inventory."""
        inventory = live_client.system.inventory()

        # Should have all resource lists
        assert isinstance(inventory.vms, list)
        assert isinstance(inventory.networks, list)
        assert isinstance(inventory.storage, list)
        assert isinstance(inventory.nodes, list)
        assert isinstance(inventory.clusters, list)
        assert isinstance(inventory.tenants, list)

        # Should have timestamp
        assert inventory.generated_at is not None

    def test_inventory_vm_details(self, live_client: VergeClient) -> None:
        """Test VM details in inventory."""
        inventory = live_client.system.inventory()

        if not inventory.vms:
            pytest.skip("No VMs found in inventory")

        vm = inventory.vms[0]
        assert vm.key > 0
        assert vm.name
        # CPU and RAM should be non-negative
        assert vm.cpu_cores >= 0
        assert vm.ram_mb >= 0
        assert vm.ram_gb >= 0

    def test_inventory_storage_details(self, live_client: VergeClient) -> None:
        """Test storage tier details in inventory."""
        inventory = live_client.system.inventory()

        if not inventory.storage:
            pytest.skip("No storage tiers found in inventory")

        tier = inventory.storage[0]
        assert tier.tier >= 0
        assert tier.capacity_bytes >= 0
        assert tier.capacity_gb >= 0
        assert tier.used_bytes >= 0
        assert tier.used_percent >= 0

    def test_inventory_summary(self, live_client: VergeClient) -> None:
        """Test inventory summary generation."""
        inventory = live_client.system.inventory()
        summary = inventory.summary

        # Summary should have expected keys
        assert "vms_total" in summary
        assert "vms_running" in summary
        assert "total_cpu_cores" in summary
        assert "total_ram_gb" in summary
        assert "networks_total" in summary
        assert "storage_tiers" in summary
        assert "nodes_total" in summary
        assert "clusters_total" in summary
        assert "tenants_total" in summary

    def test_inventory_partial(self, live_client: VergeClient) -> None:
        """Test getting partial inventory."""
        inventory = live_client.system.inventory(
            include_vms=True,
            include_networks=False,
            include_storage=True,
            include_nodes=False,
            include_clusters=False,
            include_tenants=False,
        )

        # Should have VMs and storage
        assert isinstance(inventory.vms, list)
        assert isinstance(inventory.storage, list)

        # Should be empty for excluded types
        assert inventory.networks == []
        assert inventory.nodes == []
        assert inventory.clusters == []
        assert inventory.tenants == []


@pytest.mark.integration
class TestSystemManagerIntegration:
    """Integration tests for SystemManager access."""

    def test_system_manager_access(self, live_client: VergeClient) -> None:
        """Test accessing system manager from client."""
        system = live_client.system

        assert system is not None
        assert system.settings is not None
        assert system.licenses is not None

    def test_system_statistics_method(self, live_client: VergeClient) -> None:
        """Test calling statistics method."""
        stats = live_client.system.statistics()

        assert stats is not None
        # Should return a SystemStatistics object
        assert hasattr(stats, "vms_total")
        assert hasattr(stats, "to_dict")

    def test_system_inventory_method(self, live_client: VergeClient) -> None:
        """Test calling inventory method."""
        inventory = live_client.system.inventory()

        assert inventory is not None
        # Should return a SystemInventory object
        assert hasattr(inventory, "vms")
        assert hasattr(inventory, "summary")
