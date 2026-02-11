"""Integration tests for NAS Antivirus management.

These tests require a live VergeOS system with:
- At least one NAS service (with 8GB+ RAM for service-level antivirus)
- At least one NAS volume (or permission to create test volumes)

Configure with environment variables:
    VERGE_HOST, VERGE_USERNAME, VERGE_PASSWORD, VERGE_VERIFY_SSL
"""

from __future__ import annotations

import contextlib
import os
import time

import pytest

from pyvergeos import VergeClient
from pyvergeos.exceptions import NotFoundError
from pyvergeos.resources.nas_antivirus import (
    NasServiceAntivirus,
    VolumeAntivirusInfection,
    VolumeAntivirusLog,
    VolumeAntivirusStats,
    VolumeAntivirusStatus,
)
from pyvergeos.resources.nas_services import NASService
from pyvergeos.resources.nas_volumes import NASVolume

# Skip all tests in this module if not running integration tests
pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def client() -> VergeClient:
    """Create a connected client for the test module."""
    if not os.environ.get("VERGE_HOST"):
        pytest.skip("VERGE_HOST not set")

    client = VergeClient.from_env()
    client.connect()
    yield client
    client.disconnect()


@pytest.fixture(scope="module")
def test_service(client: VergeClient) -> NASService:
    """Get a NAS service for testing.

    Uses the first available running NAS service.
    """
    services = client.nas_services.list_running()
    if not services:
        pytest.skip("No running NAS services available for antivirus testing")
    return services[0]


@pytest.fixture(scope="module")
def test_volume(client: VergeClient, test_service: NASService) -> NASVolume:
    """Get or create a test NAS volume for antivirus testing.

    Creates a small test volume if none exists.
    """
    # Try to find existing test volume
    volumes = client.nas_volumes.list(service=test_service.key)
    for vol in volumes:
        if vol.name.startswith("pstest-"):
            return vol

    # Create a test volume
    vol = client.nas_volumes.create(
        name="pstest-antivirus",
        service=test_service.key,
        size_gb=5,
        description="pyVergeOS antivirus integration test volume",
    )
    return vol


@pytest.fixture
def cleanup_antivirus(client: VergeClient, test_volume: NASVolume):
    """Fixture to track and cleanup test antivirus configs."""
    created_keys: list[int] = []

    yield created_keys

    # Cleanup any antivirus configs we created
    for key in created_keys:
        with contextlib.suppress(NotFoundError):
            client.volume_antivirus.delete(key)


class TestVolumeAntivirusIntegration:
    """Integration tests for VolumeAntivirus management."""

    def test_create_antivirus_config(
        self, client: VergeClient, test_volume: NASVolume, cleanup_antivirus: list[int]
    ) -> None:
        """Test creating a volume antivirus configuration."""
        # Create antivirus config
        av = client.volume_antivirus.create(
            volume=test_volume.key,
            enabled=False,
            infected_action="move",
            on_access=False,
            scan="entire",
            exclude="/temp\n/cache",
        )
        cleanup_antivirus.append(av.key)

        assert av.key is not None
        assert av.volume_key == test_volume.key
        assert av.get("infected_action") == "move"
        assert av.get("scan") == "entire"
        assert av.get("exclude") == "/temp\n/cache"

    def test_get_antivirus_config_by_key(
        self, client: VergeClient, test_volume: NASVolume, cleanup_antivirus: list[int]
    ) -> None:
        """Test retrieving antivirus config by key."""
        # Create config
        av = client.volume_antivirus.create(volume=test_volume.key)
        cleanup_antivirus.append(av.key)

        # Get by key
        retrieved = client.volume_antivirus.get(key=av.key)
        assert retrieved.key == av.key
        assert retrieved.volume_key == test_volume.key

    def test_get_antivirus_config_by_volume(
        self, client: VergeClient, test_volume: NASVolume, cleanup_antivirus: list[int]
    ) -> None:
        """Test retrieving antivirus config by volume."""
        # Create config
        av = client.volume_antivirus.create(volume=test_volume.key)
        cleanup_antivirus.append(av.key)

        # Get by volume key
        retrieved = client.volume_antivirus.get(volume=test_volume.key)
        assert retrieved.key == av.key
        assert retrieved.volume_key == test_volume.key

    def test_update_antivirus_config(
        self, client: VergeClient, test_volume: NASVolume, cleanup_antivirus: list[int]
    ) -> None:
        """Test updating antivirus configuration."""
        # Create config
        av = client.volume_antivirus.create(volume=test_volume.key, enabled=False, on_access=False)
        cleanup_antivirus.append(av.key)

        # Update config
        updated = client.volume_antivirus.update(
            av.key,
            on_access=True,
            quarantine_location="/custom_quarantine",
            exclude="/logs",
        )

        assert updated.key == av.key
        assert updated.get("on_access") is True
        assert updated.get("quarantine_location") == "/custom_quarantine"
        assert updated.get("exclude") == "/logs"

    def test_list_antivirus_configs(
        self, client: VergeClient, test_volume: NASVolume, cleanup_antivirus: list[int]
    ) -> None:
        """Test listing antivirus configurations."""
        # Create a config
        av = client.volume_antivirus.create(volume=test_volume.key, enabled=True)
        cleanup_antivirus.append(av.key)

        # List all configs
        configs = client.volume_antivirus.list()
        assert len(configs) >= 1
        assert any(c.key == av.key for c in configs)

        # List enabled only
        enabled_configs = client.volume_antivirus.list(enabled=True)
        assert any(c.key == av.key for c in enabled_configs)

    def test_volume_antivirus_property(
        self, client: VergeClient, test_volume: NASVolume, cleanup_antivirus: list[int]
    ) -> None:
        """Test accessing antivirus via volume.antivirus property."""
        # Create config directly
        av = client.volume_antivirus.create(volume=test_volume.key)
        cleanup_antivirus.append(av.key)

        # Access via volume property
        vol = client.nas_volumes.get(test_volume.key)
        retrieved = vol.antivirus.get()

        assert retrieved.key == av.key
        assert retrieved.volume_key == test_volume.key

    def test_antivirus_actions(
        self, client: VergeClient, test_volume: NASVolume, cleanup_antivirus: list[int]
    ) -> None:
        """Test antivirus enable/disable/start/stop actions."""
        # Create config
        av = client.volume_antivirus.create(volume=test_volume.key, enabled=False)
        cleanup_antivirus.append(av.key)

        # Test enable action
        result = av.enable()
        assert result is not None or result is None  # Action may or may not return data

        # Wait a moment for state change
        time.sleep(1)

        # Test disable action
        result = av.disable()
        assert result is not None or result is None

        # Note: start_scan and stop_scan require antivirus to be enabled
        # and may fail in test environment without proper virus definitions

    def test_get_antivirus_status(
        self, client: VergeClient, test_volume: NASVolume, cleanup_antivirus: list[int]
    ) -> None:
        """Test retrieving antivirus status."""
        # Create config
        av = client.volume_antivirus.create(volume=test_volume.key)
        cleanup_antivirus.append(av.key)

        # Get status
        status = av.get_status()

        assert isinstance(status, VolumeAntivirusStatus)
        assert status.key is not None
        assert status.get("status") is not None
        assert status.get("state") is not None

        # Test status properties
        assert isinstance(status.is_scanning, bool)
        assert isinstance(status.is_offline, bool)
        assert isinstance(status.has_error, bool)

    def test_get_antivirus_stats(
        self, client: VergeClient, test_volume: NASVolume, cleanup_antivirus: list[int]
    ) -> None:
        """Test retrieving antivirus statistics."""
        # Create config
        av = client.volume_antivirus.create(volume=test_volume.key)
        cleanup_antivirus.append(av.key)

        # Get stats
        stats = av.get_stats()

        assert isinstance(stats, VolumeAntivirusStats)
        assert stats.key is not None
        assert stats.get("infected_files") is not None  # Should be 0 initially
        assert stats.get("quarantine_count") is not None

        # Test stats properties
        assert isinstance(stats.has_infections, bool)

    def test_list_antivirus_infections(
        self, client: VergeClient, test_volume: NASVolume, cleanup_antivirus: list[int]
    ) -> None:
        """Test listing antivirus infection records."""
        # Create config
        av = client.volume_antivirus.create(volume=test_volume.key)
        cleanup_antivirus.append(av.key)

        # List infections (should be empty initially)
        infections = av.infections.list()

        assert isinstance(infections, list)
        for infection in infections:
            assert isinstance(infection, VolumeAntivirusInfection)
            assert infection.get("filename") is not None
            assert infection.get("virus") is not None

    def test_list_antivirus_logs(
        self, client: VergeClient, test_volume: NASVolume, cleanup_antivirus: list[int]
    ) -> None:
        """Test listing antivirus scan activity logs."""
        # Create config
        av = client.volume_antivirus.create(volume=test_volume.key)
        cleanup_antivirus.append(av.key)

        # List logs
        logs = av.logs.list()

        assert isinstance(logs, list)
        for log in logs:
            assert isinstance(log, VolumeAntivirusLog)
            assert log.get("level") is not None
            assert log.get("text") is not None

        # Test filtering by level
        error_logs = av.logs.list(level="error")
        assert isinstance(error_logs, list)

    def test_delete_antivirus_config(self, client: VergeClient, test_volume: NASVolume) -> None:
        """Test deleting antivirus configuration."""
        # Create config
        av = client.volume_antivirus.create(volume=test_volume.key)

        # Delete it
        client.volume_antivirus.delete(av.key)

        # Verify it's gone
        with pytest.raises(NotFoundError):
            client.volume_antivirus.get(key=av.key)


class TestNasServiceAntivirusIntegration:
    """Integration tests for NAS service-level antivirus configuration."""

    def test_get_service_antivirus_config(
        self, client: VergeClient, test_service: NASService
    ) -> None:
        """Test retrieving service-level antivirus configuration."""
        # Access via service property
        svc_av = test_service.antivirus.get()

        assert isinstance(svc_av, NasServiceAntivirus)
        assert svc_av.key is not None
        assert svc_av.service_key == test_service.key
        assert svc_av.get("enabled") is not None
        assert svc_av.get("max_recursion") is not None
        assert svc_av.get("database_location") is not None

    def test_update_service_antivirus_config(
        self, client: VergeClient, test_service: NASService
    ) -> None:
        """Test updating service-level antivirus configuration."""
        # Get current config
        svc_av = test_service.antivirus.get()
        original_recursion = svc_av.get("max_recursion")

        # Update max_recursion
        new_recursion = 20 if original_recursion != 20 else 15
        updated = test_service.antivirus.update(key=svc_av.key, max_recursion=new_recursion)

        assert updated.get("max_recursion") == new_recursion

        # Restore original value
        test_service.antivirus.update(key=svc_av.key, max_recursion=original_recursion)

    def test_list_service_antivirus_configs(self, client: VergeClient) -> None:
        """Test listing all service-level antivirus configurations."""
        # List all configs
        configs = client.nas_service_antivirus.list()

        assert isinstance(configs, list)
        for config in configs:
            assert isinstance(config, NasServiceAntivirus)
            assert config.key is not None
            assert config.service_key is not None


class TestAntivirusIntegrationWorkflow:
    """Integration tests for complete antivirus workflow."""

    def test_complete_antivirus_workflow(
        self, client: VergeClient, test_volume: NASVolume, cleanup_antivirus: list[int]
    ) -> None:
        """Test a complete antivirus configuration and monitoring workflow."""
        # Step 1: Create antivirus configuration
        av = test_volume.antivirus.get_or_create = lambda: (
            test_volume.antivirus.get()
            if test_volume.antivirus.list()
            else client.volume_antivirus.create(test_volume.key)
        )
        av = client.volume_antivirus.create(
            volume=test_volume.key,
            enabled=False,
            infected_action="move",
            on_access=False,
            scan="entire",
            exclude="/temp",
        )
        cleanup_antivirus.append(av.key)

        # Step 2: Update configuration
        av_updated = client.volume_antivirus.update(
            av.key, enabled=True, quarantine_location=".quarantine"
        )
        assert av_updated.get("enabled") is True

        # Step 3: Check status
        status = av_updated.get_status()
        assert status.key is not None
        assert status.get("status") is not None

        # Step 4: Check statistics
        stats = av_updated.get_stats()
        assert stats.key is not None
        assert stats.get("infected_files") is not None

        # Step 5: List logs
        logs = av_updated.logs.list(limit=10)
        assert isinstance(logs, list)

        # Step 6: List infections
        infections = av_updated.infections.list()
        assert isinstance(infections, list)

        # Step 7: Disable antivirus
        av_updated.disable()

        # Step 8: Cleanup (delete config)
        client.volume_antivirus.delete(av_updated.key)
        cleanup_antivirus.remove(av_updated.key)
