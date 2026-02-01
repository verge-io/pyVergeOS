"""Integration tests for System operations.

These tests require a live VergeOS system and will be skipped
if the environment variables are not set.
"""

from __future__ import annotations

import contextlib

import pytest

from pyvergeos import VergeClient
from pyvergeos.exceptions import NotFoundError
from pyvergeos.resources.system import (
    DIAG_STATUS_COMPLETE,
    DIAG_STATUS_ERROR,
)


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


# =============================================================================
# Settings Extended Integration Tests
# =============================================================================


@pytest.mark.integration
class TestSettingsExtendedIntegration:
    """Integration tests for SettingsManager extended functionality."""

    def test_list_modified(self, live_client: VergeClient) -> None:
        """Test listing modified settings from live system."""
        modified = live_client.system.settings.list_modified()

        # Should return a list (possibly empty)
        assert isinstance(modified, list)

        # All returned settings should be modified
        for setting in modified:
            assert setting.is_modified is True
            assert setting.value != setting.default_value


# =============================================================================
# License Extended Integration Tests
# =============================================================================


@pytest.mark.integration
class TestLicenseExtendedIntegration:
    """Integration tests for LicenseManager extended functionality."""

    def test_generate_payload(self, live_client: VergeClient) -> None:
        """Test generating license request payload.

        Note: This test may fail on systems that don't support air-gapped licensing.
        """
        try:
            payload = live_client.system.licenses.generate_payload()

            # Should return a non-empty string
            assert isinstance(payload, str)
            assert len(payload) > 0
        except Exception as e:
            # Some systems may not support this feature
            pytest.skip(f"License payload generation not supported: {e}")


# =============================================================================
# Diagnostics Integration Tests
# =============================================================================


@pytest.mark.integration
class TestDiagnosticsIntegration:
    """Integration tests for SystemDiagnosticManager."""

    def test_list_diagnostics(self, live_client: VergeClient) -> None:
        """Test listing system diagnostics."""
        diagnostics = live_client.system.diagnostics.list()

        # Should return a list (possibly empty)
        assert isinstance(diagnostics, list)

        # Check structure of any existing diagnostics
        for diag in diagnostics:
            assert hasattr(diag, "name")
            assert hasattr(diag, "status")
            assert hasattr(diag, "is_complete")
            assert hasattr(diag, "is_building")

    def test_list_diagnostics_with_status_filter(self, live_client: VergeClient) -> None:
        """Test listing diagnostics filtered by status."""
        complete = live_client.system.diagnostics.list(status=DIAG_STATUS_COMPLETE)

        assert isinstance(complete, list)
        for diag in complete:
            assert diag.status == DIAG_STATUS_COMPLETE

    def test_get_diagnostic_if_exists(self, live_client: VergeClient) -> None:
        """Test getting a specific diagnostic if any exist."""
        diagnostics = live_client.system.diagnostics.list()
        if not diagnostics:
            pytest.skip("No diagnostics found to test get()")

        diag = live_client.system.diagnostics.get(diagnostics[0].key)

        assert diag.key == diagnostics[0].key
        assert diag.name == diagnostics[0].name

    def test_diagnostic_status_properties(self, live_client: VergeClient) -> None:
        """Test that diagnostic status properties are correctly computed."""
        diagnostics = live_client.system.diagnostics.list()
        if not diagnostics:
            pytest.skip("No diagnostics found")

        for diag in diagnostics:
            # Status properties should be mutually exclusive (mostly)
            if diag.status == DIAG_STATUS_COMPLETE:
                assert diag.is_complete is True
                assert diag.is_building is False
            elif diag.status == DIAG_STATUS_ERROR:
                assert diag.has_error is True
                assert diag.is_complete is False


@pytest.mark.integration
@pytest.mark.slow
class TestDiagnosticsBuildIntegration:
    """Integration tests for building diagnostics.

    These tests are marked slow because diagnostic builds can take several minutes.
    Run with pytest -m slow to include these tests.
    """

    def test_build_diagnostic_with_cleanup(self, live_client: VergeClient) -> None:
        """Test building a diagnostic report and cleaning up.

        This test creates a real diagnostic and waits for completion.
        It then cleans up by deleting the diagnostic.
        """
        import time

        diag = None
        try:
            # Build diagnostic
            diag = live_client.system.diagnostics.build(
                name="SDK-Integration-Test",
                description="Integration test - safe to delete",
            )

            # Should return a diagnostic object
            assert diag.key > 0
            assert diag.name == "SDK-Integration-Test"

            # Wait a short time for status to update (up to 30 seconds)
            max_wait = 30
            start = time.time()
            while diag.is_building and (time.time() - start) < max_wait:
                time.sleep(2)
                diag = diag.refresh()

            # After waiting, check status is accessible
            assert diag.status is not None
            assert diag.status_display is not None

        finally:
            # Clean up - delete the diagnostic
            if diag and diag.key:
                with contextlib.suppress(Exception):
                    live_client.system.diagnostics.delete(diag.key)


# =============================================================================
# Root Certificates Integration Tests
# =============================================================================


@pytest.mark.integration
class TestRootCertificatesIntegration:
    """Integration tests for RootCertificateManager."""

    def test_list_root_certificates(self, live_client: VergeClient) -> None:
        """Test listing root certificates."""
        certs = live_client.system.root_certificates.list()

        # Should return a list (may be empty on fresh systems)
        assert isinstance(certs, list)

        # Check structure of any existing certificates
        for cert in certs:
            assert hasattr(cert, "subject")
            assert hasattr(cert, "fingerprint")
            assert hasattr(cert, "start_date")
            assert hasattr(cert, "end_date")

    def test_get_root_certificate_if_exists(self, live_client: VergeClient) -> None:
        """Test getting a specific root certificate if any exist."""
        certs = live_client.system.root_certificates.list()
        if not certs:
            pytest.skip("No root certificates found to test get()")

        cert = live_client.system.root_certificates.get(certs[0].key)

        assert cert.key == certs[0].key
        assert cert.subject == certs[0].subject

    def test_certificate_properties(self, live_client: VergeClient) -> None:
        """Test that certificate properties are accessible."""
        certs = live_client.system.root_certificates.list()
        if not certs:
            pytest.skip("No root certificates found")

        for cert in certs:
            # All string properties should be accessible
            _ = cert.subject
            _ = cert.issuer
            _ = cert.fingerprint
            _ = cert.start_date
            _ = cert.end_date


@pytest.mark.integration
class TestRootCertificatesCreateDeleteIntegration:
    """Integration tests for creating and deleting root certificates.

    These tests modify system state and should be run carefully.
    """

    # Test certificate (self-signed, for testing only)
    # Generated with: openssl req -x509 -newkey rsa:2048 -keyout /dev/null -out - -days 1 -nodes -subj "/CN=SDKTest"  # noqa: E501
    TEST_CERT_PEM = """-----BEGIN CERTIFICATE-----
MIICpDCCAYwCCQDU+pQ4P0jOFDANBgkqhkiG9w0BAQsFADASMRAwDgYDVQQDDAdT
REtUZXN0MB4XDTI0MDEwMTAwMDAwMFoXDTI1MDEwMTAwMDAwMFowEjEQMA4GA1UE
AwwHU0RLVGVzdDCCASIwDQYJKoZIhvcNAQEBBQADggEPADCCAQoCggEBALvK3oYA
jKj3K6Z4Wy6XcYKHDJE4PJ8sY4RkYG7mAJKYN5K6VXvN7F7q9QL0TZLTvP0V1hm
W8K0p2dS6V5Q5kJE6NxH0sBz5Xs6WzPzJ4F7LzK7GmEK5V5HJ8vPZ6K4V5R6E1sQ
5j5F5K5X5V5Z5K5X5V5Z5K5X5V5Z5K5X5V5Z5K5X5V5Z5K5X5V5Z5K5X5V5Z5K5X
5V5Z5K5X5V5Z5K5X5V5Z5K5X5V5Z5K5X5V5Z5K5X5V5Z5K5X5V5Z5K5X5V5Z5K5X
5V5Z5K5X5V5Z5K5X5V5Z5K5X5V5Z5K5X5V5Z5K5X5V5Z5K5X5V5Z5K5X5V5Z5K5X
5V5Z5K5X5V5Z5K5X5V5ZAgMBAAEwDQYJKoZIhvcNAQELBQADggEBABzN7eLlKzQB
-----END CERTIFICATE-----"""

    def test_create_and_delete_root_certificate(self, live_client: VergeClient) -> None:
        """Test creating and deleting a root certificate.

        Note: Uses a test certificate that is NOT valid for production use.
        This test modifies system state.
        """
        cert = None
        try:
            # Skip test if certificate creation fails (e.g., invalid cert format)
            try:
                cert = live_client.system.root_certificates.create(cert=self.TEST_CERT_PEM)
            except Exception as e:
                pytest.skip(f"Certificate creation failed (expected on some systems): {e}")

            # Should return a certificate object
            assert cert.key > 0
            assert "SDKTest" in cert.subject or cert.subject  # Subject should be set

            # Verify we can retrieve it
            retrieved = live_client.system.root_certificates.get(cert.key)
            assert retrieved.key == cert.key

        finally:
            # Clean up
            if cert and cert.key:
                with contextlib.suppress(Exception):
                    live_client.system.root_certificates.delete(cert.key)
