"""Integration tests for volume VM export operations.

These tests require a live VergeOS system and will be skipped
if the environment variables are not set.
"""

from __future__ import annotations

import pytest

from pyvergeos import VergeClient
from pyvergeos.exceptions import NotFoundError


@pytest.mark.integration
class TestVolumeVmExportManagerIntegration:
    """Integration tests for VolumeVmExportManager."""

    def test_list_volume_vm_exports(self, live_client: VergeClient) -> None:
        """Test listing VM exports from live system."""
        exports = live_client.volume_vm_exports.list()

        # Should return a list (may be empty)
        assert isinstance(exports, list)

        # Each item should be a VolumeVmExport object
        for exp in exports:
            assert hasattr(exp, "status")
            assert hasattr(exp, "key")
            # Key should be an integer
            assert isinstance(exp.key, int)

    def test_list_volume_vm_exports_with_pagination(self, live_client: VergeClient) -> None:
        """Test listing VM exports with pagination."""
        # Get first page
        exports = live_client.volume_vm_exports.list(limit=5)

        # Should return a list
        assert isinstance(exports, list)
        assert len(exports) <= 5

    def test_list_volume_vm_exports_by_status(self, live_client: VergeClient) -> None:
        """Test filtering VM exports by status."""
        # Get all exports
        all_exports = live_client.volume_vm_exports.list()

        # Filter by idle status
        idle_exports = live_client.volume_vm_exports.list(status="idle")

        # Each should have idle status
        for exp in idle_exports:
            assert exp.status == "idle"

        # Should be fewer or equal to total
        assert len(idle_exports) <= len(all_exports)

    def test_get_volume_vm_export_by_key(self, live_client: VergeClient) -> None:
        """Test getting a VM export by key."""
        exports = live_client.volume_vm_exports.list(limit=1)
        if not exports:
            pytest.skip("No VM exports available")

        exp = live_client.volume_vm_exports.get(key=exports[0].key)

        assert exp.key == exports[0].key
        assert exp.status == exports[0].status

    def test_get_volume_vm_export_by_volume(self, live_client: VergeClient) -> None:
        """Test getting a VM export by volume key."""
        exports = live_client.volume_vm_exports.list(limit=1)
        if not exports:
            pytest.skip("No VM exports available")

        volume_key = exports[0].volume_key
        if volume_key is None:
            pytest.skip("Export has no volume key")

        exp = live_client.volume_vm_exports.get(volume=volume_key)

        assert exp.volume_key == volume_key

    def test_get_volume_vm_export_not_found(self, live_client: VergeClient) -> None:
        """Test that NotFoundError is raised for nonexistent export."""
        with pytest.raises(NotFoundError):
            live_client.volume_vm_exports.get(key=999999)

    def test_volume_vm_export_properties(self, live_client: VergeClient) -> None:
        """Test VM export property accessors on live data."""
        exports = live_client.volume_vm_exports.list(limit=1)
        if not exports:
            pytest.skip("No VM exports available")

        exp = exports[0]

        # Basic properties should be accessible
        assert isinstance(exp.status, str)
        assert exp.status in ["idle", "building", "error", "cleaning"]
        assert isinstance(exp.is_idle, bool)
        assert isinstance(exp.is_building, bool)
        assert isinstance(exp.has_error, bool)

    def test_volume_vm_export_stats_access(self, live_client: VergeClient) -> None:
        """Test accessing VM export stats via the export object."""
        exports = live_client.volume_vm_exports.list(limit=1)
        if not exports:
            pytest.skip("No VM exports available")

        exp = exports[0]

        # Get stats for this export
        stats = exp.stats.list()

        # Should return a list
        assert isinstance(stats, list)

        # Each stat should have expected properties
        for stat in stats:
            assert hasattr(stat, "file_name")
            assert hasattr(stat, "virtual_machines")


@pytest.mark.integration
class TestVolumeVmExportStatManagerIntegration:
    """Integration tests for VolumeVmExportStatManager."""

    def test_list_volume_vm_export_stats(self, live_client: VergeClient) -> None:
        """Test listing VM export stats from live system."""
        stats = live_client.volume_vm_export_stats.list()

        # Should return a list (may be empty)
        assert isinstance(stats, list)

        # Each item should be a VolumeVmExportStat object
        for stat in stats:
            assert hasattr(stat, "file_name")
            assert hasattr(stat, "virtual_machines")
            assert hasattr(stat, "duration")

    def test_list_volume_vm_export_stats_with_pagination(
        self, live_client: VergeClient
    ) -> None:
        """Test listing VM export stats with pagination."""
        stats = live_client.volume_vm_export_stats.list(limit=5)

        # Should return a list
        assert isinstance(stats, list)
        assert len(stats) <= 5

    def test_list_volume_vm_export_stats_for_specific_export(
        self, live_client: VergeClient
    ) -> None:
        """Test filtering stats for a specific export."""
        exports = live_client.volume_vm_exports.list(limit=1)
        if not exports:
            pytest.skip("No VM exports available")

        exp = exports[0]

        # Get stats using the manager
        stats = live_client.volume_vm_export_stats.list(volume_vm_exports=exp.key)

        # All stats should belong to this export
        for stat in stats:
            assert stat.get("volume_vm_exports") == exp.key

    def test_volume_vm_export_stat_properties(self, live_client: VergeClient) -> None:
        """Test VM export stat property accessors on live data."""
        stats = live_client.volume_vm_export_stats.list(limit=1)
        if not stats:
            pytest.skip("No VM export stats available")

        stat = stats[0]

        # Basic properties should be accessible
        assert isinstance(stat.file_name, (str, type(None)))
        assert isinstance(stat.size_gb, float)
        assert isinstance(stat.has_errors, bool)
