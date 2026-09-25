"""Integration tests for NAS Antivirus management.

These tests require a live VergeOS system with:
- At least one NAS service (with 8GB+ RAM for service-level antivirus)
- At least one NAS volume (or permission to create test volumes)

Configure with environment variables:
    VERGE_HOST, VERGE_USERNAME, VERGE_PASSWORD

TLS verification matches the shared live_client fixture (disabled).
Antivirus configuration is reached through volume.antivirus and
service.antivirus.

VergeOS creates the volume antivirus row with the volume. These tests
read that row, update it, and restore the original settings. They do
not delete the platform row. The disposable volume is deleted afterwards
so a shared ``pstest-antivirus`` volume is not left on the lab.
"""

from __future__ import annotations

import contextlib
import secrets
import time
from collections.abc import Generator
from typing import Any

import pytest

from pyvergeos import VergeClient
from pyvergeos.exceptions import NotFoundError
from pyvergeos.resources.nas_antivirus import (
    NasServiceAntivirus,
    NasServiceAntivirusManager,
    VolumeAntivirus,
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
def client(live_client_module: VergeClient) -> VergeClient:
    """Live client with the same TLS settings as the shared live_client fixture."""
    return live_client_module


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
def test_volume(client: VergeClient, test_service: NASService) -> Generator[NASVolume, None, None]:
    """Create a disposable NAS volume and delete it afterwards.

    VergeOS creates the antivirus row with the volume. Reusing a shared
    ``pstest-antivirus`` volume left that volume on the lab.
    """
    vol = client.nas_volumes.create(
        name=f"pstest-av-{secrets.token_hex(4)}",
        service=test_service.key,
        size_gb=5,
        description="pyVergeOS antivirus integration test volume",
    )
    try:
        yield vol
    finally:
        with contextlib.suppress(NotFoundError):
            client.nas_volumes.delete(vol.key)


def _wait_for_volume_antivirus(volume: NASVolume, timeout: float = 15) -> VolumeAntivirus:
    """Return the antivirus row the platform creates with the volume."""
    deadline = time.monotonic() + timeout
    while True:
        try:
            return volume.antivirus.get()
        except NotFoundError:
            if time.monotonic() >= deadline:
                raise
            time.sleep(1)


def _antivirus_settings(av: VolumeAntivirus) -> dict[str, Any]:
    """Settings to write back so a test leaves the platform defaults."""
    include = av.get("include")
    exclude = av.get("exclude")
    quarantine = av.get("quarantine_location")
    action = av.get("infected_action")
    scan = av.get("scan")
    return {
        "enabled": bool(av.get("enabled")),
        "infected_action": action if action else "move",
        "on_access": bool(av.get("on_access")),
        "scan": scan if scan else "entire",
        "include": "" if include is None else include,
        "exclude": "" if exclude is None else exclude,
        "quarantine_location": quarantine if quarantine else ".quarantine",
    }


def _restore_antivirus(volume: NASVolume, settings: dict[str, Any]) -> VolumeAntivirus:
    """Write ``settings`` back onto the volume's antivirus row."""
    current = volume.antivirus.get()
    return volume.antivirus.update(current.key, **settings)


@pytest.fixture
def volume_av(test_volume: NASVolume) -> Generator[VolumeAntivirus, None, None]:
    """The volume's existing antivirus row, restored after the test."""
    av = _wait_for_volume_antivirus(test_volume)
    original = _antivirus_settings(av)
    try:
        yield av
    finally:
        _restore_antivirus(test_volume, original)


class TestVolumeAntivirusIntegration:
    """Integration tests for VolumeAntivirus management.

    The platform creates the antivirus row with the volume. Tests read that
    row, update it, and the ``volume_av`` fixture restores the original
    settings. They do not POST a second row or delete the platform row.
    """

    def test_create_updates_precreated_row(
        self, test_volume: NASVolume, volume_av: VolumeAntivirus
    ) -> None:
        """create() updates the row VergeOS made with the volume (no 409)."""
        updated = test_volume.antivirus.create(
            volume=test_volume.key,
            enabled=False,
            infected_action="move",
            on_access=True,
            scan="entire",
            exclude="/temp\n/cache",
        )

        assert updated.key == volume_av.key
        assert updated.volume_key == test_volume.key
        assert updated.get("infected_action") == "move"
        assert updated.get("scan") == "entire"
        assert updated.get("on_access") is True
        assert updated.get("exclude") == "/temp\n/cache"

    def test_update_existing_antivirus_config(
        self, test_volume: NASVolume, volume_av: VolumeAntivirus
    ) -> None:
        """The row exists as soon as the volume does; update it in place."""
        assert volume_av.key is not None
        assert volume_av.volume_key == test_volume.key

        updated = test_volume.antivirus.update(
            volume_av.key,
            enabled=False,
            infected_action="move",
            on_access=False,
            scan="entire",
            exclude="/temp\n/cache",
        )

        assert updated.key == volume_av.key
        assert updated.volume_key == test_volume.key
        assert updated.get("infected_action") == "move"
        assert updated.get("scan") == "entire"
        assert updated.get("exclude") == "/temp\n/cache"

    def test_get_antivirus_config_by_key(
        self, test_volume: NASVolume, volume_av: VolumeAntivirus
    ) -> None:
        """Test retrieving antivirus config by key."""
        retrieved = test_volume.antivirus.get(key=volume_av.key)
        assert retrieved.key == volume_av.key
        assert retrieved.volume_key == test_volume.key

    def test_get_antivirus_config_by_volume(
        self, test_volume: NASVolume, volume_av: VolumeAntivirus
    ) -> None:
        """Test retrieving antivirus config by volume."""
        retrieved = test_volume.antivirus.get(volume=test_volume.key)
        assert retrieved.key == volume_av.key
        assert retrieved.volume_key == test_volume.key

    def test_update_antivirus_config(
        self, test_volume: NASVolume, volume_av: VolumeAntivirus
    ) -> None:
        """Test updating antivirus configuration."""
        updated = test_volume.antivirus.update(
            volume_av.key,
            on_access=True,
            quarantine_location="/custom_quarantine",
            exclude="/logs",
        )

        assert updated.key == volume_av.key
        assert updated.get("on_access") is True
        assert updated.get("quarantine_location") == "/custom_quarantine"
        assert updated.get("exclude") == "/logs"

    def test_list_antivirus_configs(
        self, test_volume: NASVolume, volume_av: VolumeAntivirus
    ) -> None:
        """Test listing antivirus configurations."""
        test_volume.antivirus.update(volume_av.key, enabled=True)

        configs = test_volume.antivirus.list()
        assert len(configs) >= 1
        assert any(c.key == volume_av.key for c in configs)

        enabled_configs = test_volume.antivirus.list(enabled=True)
        assert any(c.key == volume_av.key for c in enabled_configs)

    def test_volume_antivirus_property(
        self, client: VergeClient, test_volume: NASVolume, volume_av: VolumeAntivirus
    ) -> None:
        """Test accessing antivirus via volume.antivirus property."""
        vol = client.nas_volumes.get(test_volume.key)
        retrieved = vol.antivirus.get()

        assert retrieved.key == volume_av.key
        assert retrieved.volume_key == test_volume.key

    def test_antivirus_actions(self, volume_av: VolumeAntivirus) -> None:
        """Test antivirus enable/disable actions."""
        result = volume_av.enable()
        assert result is None or isinstance(result, dict)

        time.sleep(1)

        result = volume_av.disable()
        assert result is None or isinstance(result, dict)

        # start_scan and stop_scan require antivirus to be enabled and may
        # fail without virus definitions.

    def test_get_antivirus_status(self, volume_av: VolumeAntivirus) -> None:
        """Test retrieving antivirus status."""
        status = volume_av.get_status()

        assert isinstance(status, VolumeAntivirusStatus)
        assert status.key is not None
        assert status.get("status") is not None
        assert status.get("state") is not None

        assert isinstance(status.is_scanning, bool)
        assert isinstance(status.is_offline, bool)
        assert isinstance(status.has_error, bool)

    def test_get_antivirus_stats(self, volume_av: VolumeAntivirus) -> None:
        """Test retrieving antivirus statistics."""
        stats = volume_av.get_stats()

        assert isinstance(stats, VolumeAntivirusStats)
        assert stats.key is not None
        assert stats.get("infected_files") is not None
        assert stats.get("quarantine_count") is not None

        assert isinstance(stats.has_infections, bool)

    def test_list_antivirus_infections(self, volume_av: VolumeAntivirus) -> None:
        """Test listing antivirus infection records."""
        infections = volume_av.infections.list()

        assert isinstance(infections, list)
        for infection in infections:
            assert isinstance(infection, VolumeAntivirusInfection)
            assert infection.get("filename") is not None
            assert infection.get("virus") is not None

    def test_list_antivirus_logs(self, volume_av: VolumeAntivirus) -> None:
        """Test listing antivirus scan activity logs."""
        logs = volume_av.logs.list()

        assert isinstance(logs, list)
        for log in logs:
            assert isinstance(log, VolumeAntivirusLog)
            assert log.get("level") is not None
            assert log.get("text") is not None

        error_logs = volume_av.logs.list(level="error")
        assert isinstance(error_logs, list)

    def test_restore_antivirus_defaults(
        self, test_volume: NASVolume, volume_av: VolumeAntivirus
    ) -> None:
        """Updates are written back to the settings captured before the test."""
        original = _antivirus_settings(volume_av)
        test_volume.antivirus.update(
            volume_av.key,
            enabled=True,
            on_access=True,
            quarantine_location="/custom_quarantine",
            exclude="/logs",
        )

        restored = _restore_antivirus(test_volume, original)
        assert restored.get("exclude") in (original["exclude"], None, "")
        assert restored.get("quarantine_location") == original["quarantine_location"]
        assert bool(restored.get("enabled")) is original["enabled"]
        assert bool(restored.get("on_access")) is original["on_access"]


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

    def test_list_service_antivirus_configs(
        self, client: VergeClient, test_service: NASService
    ) -> None:
        """Unscoped list returns every service; scoped list stays on one."""
        configs = NasServiceAntivirusManager(client).list()

        assert isinstance(configs, list)
        for config in configs:
            assert isinstance(config, NasServiceAntivirus)
            assert config.key is not None
            assert config.service_key is not None

        scoped = test_service.antivirus.list()
        assert scoped
        assert all(config.service_key == test_service.key for config in scoped)


class TestAntivirusIntegrationWorkflow:
    """Integration tests for complete antivirus workflow."""

    def test_complete_antivirus_workflow(
        self, test_volume: NASVolume, volume_av: VolumeAntivirus
    ) -> None:
        """Test a complete antivirus configuration and monitoring workflow."""
        av_updated = test_volume.antivirus.update(
            volume_av.key,
            enabled=True,
            infected_action="move",
            on_access=False,
            scan="entire",
            exclude="/temp",
            quarantine_location=".quarantine",
        )
        assert av_updated.get("enabled") is True

        status = av_updated.get_status()
        assert status.key is not None
        assert status.get("status") is not None

        stats = av_updated.get_stats()
        assert stats.key is not None
        assert stats.get("infected_files") is not None

        logs = av_updated.logs.list(limit=10)
        assert isinstance(logs, list)

        infections = av_updated.infections.list()
        assert isinstance(infections, list)

        av_updated.disable()
