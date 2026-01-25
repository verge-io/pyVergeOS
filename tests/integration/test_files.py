"""Integration tests for File operations.

These tests require a live VergeOS system and will be skipped
if the environment variables are not set.
"""

from __future__ import annotations

import pytest

from pyvergeos import VergeClient
from pyvergeos.exceptions import NotFoundError


@pytest.mark.integration
class TestFileManagerIntegration:
    """Integration tests for FileManager."""

    def test_list_files(self, live_client: VergeClient) -> None:
        """Test listing files from live system."""
        files = live_client.files.list()

        # Should have at least some files
        assert isinstance(files, list)
        # Each item should be a File object
        for f in files:
            assert hasattr(f, "name")
            assert hasattr(f, "file_type")
            assert hasattr(f, "size_bytes")

    def test_list_files_by_type(self, live_client: VergeClient) -> None:
        """Test filtering files by type."""
        # Get all files
        all_files = live_client.files.list()

        # Filter by type
        isos = live_client.files.list(file_type="iso")

        # Should only have ISO files
        for f in isos:
            assert f.file_type == "iso"

        # Should be fewer or equal to total
        assert len(isos) <= len(all_files)

    def test_get_file_by_key(self, live_client: VergeClient) -> None:
        """Test getting a file by key."""
        files = live_client.files.list(limit=1)
        if not files:
            pytest.skip("No files available in media catalog")

        file = live_client.files.get(key=files[0].key)

        assert file.key == files[0].key
        assert file.name == files[0].name

    def test_get_file_by_name(self, live_client: VergeClient) -> None:
        """Test getting a file by name."""
        files = live_client.files.list(limit=1)
        if not files:
            pytest.skip("No files available in media catalog")

        file = live_client.files.get(name=files[0].name)

        assert file.name == files[0].name
        assert file.key == files[0].key

    def test_get_file_not_found(self, live_client: VergeClient) -> None:
        """Test that NotFoundError is raised for nonexistent file."""
        with pytest.raises(NotFoundError):
            live_client.files.get(name="definitely-does-not-exist-abc123.iso")

    def test_file_properties(self, live_client: VergeClient) -> None:
        """Test file property accessors on live data."""
        files = live_client.files.list(limit=1)
        if not files:
            pytest.skip("No files available in media catalog")

        file = files[0]

        # Basic properties should be accessible
        assert isinstance(file.name, str)
        assert len(file.name) > 0
        assert isinstance(file.file_type, str)
        assert isinstance(file.size_bytes, int)
        assert isinstance(file.size_gb, float)
        assert file.size_bytes >= 0
        assert file.size_gb >= 0


@pytest.mark.integration
class TestStorageTierIntegration:
    """Integration tests for StorageTierManager."""

    def test_list_storage_tiers(self, live_client: VergeClient) -> None:
        """Test listing storage tiers from live system."""
        tiers = live_client.storage_tiers.list()

        # Should have at least one tier
        assert len(tiers) > 0

        # Each tier should have valid properties
        for tier in tiers:
            assert tier.tier >= 0
            assert tier.capacity_bytes >= 0
            assert tier.capacity_gb >= 0

    def test_get_storage_tier(self, live_client: VergeClient) -> None:
        """Test getting a specific storage tier."""
        tiers = live_client.storage_tiers.list()
        if not tiers:
            pytest.skip("No storage tiers available")

        # Get by tier number
        tier = live_client.storage_tiers.get(tier=tiers[0].tier)

        assert tier.tier == tiers[0].tier

    def test_storage_tier_stats(self, live_client: VergeClient) -> None:
        """Test storage tier statistics."""
        tiers = live_client.storage_tiers.list()
        if not tiers:
            pytest.skip("No storage tiers available")

        tier = tiers[0]

        # Stats should be available
        assert isinstance(tier.read_ops, int)
        assert isinstance(tier.write_ops, int)
        assert tier.read_ops >= 0
        assert tier.write_ops >= 0

    def test_storage_summary(self, live_client: VergeClient) -> None:
        """Test storage summary calculation."""
        summary = live_client.storage_tiers.get_summary()

        assert "tier_count" in summary
        assert "total_capacity_gb" in summary
        assert "total_used_gb" in summary
        assert "used_percent" in summary

        assert summary["tier_count"] > 0
        assert summary["total_capacity_gb"] > 0
        assert summary["used_percent"] >= 0
        assert summary["used_percent"] <= 100


@pytest.mark.integration
class TestVSANStatusIntegration:
    """Integration tests for vSAN status."""

    def test_vsan_status(self, live_client: VergeClient) -> None:
        """Test getting vSAN status."""
        status_list = live_client.clusters.vsan_status()

        assert len(status_list) > 0

        for status in status_list:
            assert isinstance(status.cluster_name, str)
            assert len(status.cluster_name) > 0
            assert status.health_status in ["Healthy", "Degraded", "Critical", "Offline", "Unknown"]
            assert status.total_nodes >= 0
            assert status.online_nodes >= 0
            assert status.online_nodes <= status.total_nodes

    def test_vsan_status_with_tiers(self, live_client: VergeClient) -> None:
        """Test getting vSAN status with tier information."""
        status_list = live_client.clusters.vsan_status(include_tiers=True)

        assert len(status_list) > 0

        for status in status_list:
            # Tiers should be available
            assert hasattr(status, "tiers")
            assert isinstance(status.tiers, list)

            for tier in status.tiers:
                assert "tier" in tier
                assert "used_percent" in tier
                assert tier["used_percent"] >= 0
                assert tier["used_percent"] <= 100
