"""Unit tests for StorageTier operations."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from pyvergeos import VergeClient
from pyvergeos.exceptions import NotFoundError
from pyvergeos.resources.storage_tiers import StorageTier


class TestStorageTierManager:
    """Unit tests for StorageTierManager."""

    def test_list_storage_tiers(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test listing storage tiers."""
        mock_session.request.return_value.json.return_value = [
            {
                "$key": 1,
                "tier": 1,
                "description": "Tier 1 - SSD",
                "capacity": 1073741824000,  # ~1000 GB
                "used": 107374182400,  # ~100 GB
                "allocated": 214748364800,  # ~200 GB
                "dedupe_ratio": 150,  # 1.5x
                "stats": {
                    "rops": 100,
                    "wops": 50,
                    "rbps": 104857600,  # 100 MB/s
                    "wbps": 52428800,  # 50 MB/s
                },
            },
            {
                "$key": 3,
                "tier": 3,
                "description": "Tier 3 - HDD",
                "capacity": 5368709120000,  # ~5000 GB
                "used": 536870912000,  # ~500 GB
                "allocated": 1073741824000,  # ~1000 GB
                "dedupe_ratio": 120,
                "stats": {
                    "rops": 20,
                    "wops": 10,
                },
            },
        ]

        tiers = mock_client.storage_tiers.list()

        assert len(tiers) == 2
        assert tiers[0].tier == 1
        assert tiers[0].description == "Tier 1 - SSD"
        assert tiers[1].tier == 3

    def test_get_storage_tier_by_key(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test getting a storage tier by key."""
        mock_session.request.return_value.json.return_value = {
            "$key": 1,
            "tier": 1,
            "description": "Tier 1",
            "capacity": 1073741824000,
            "used": 107374182400,
        }

        tier = mock_client.storage_tiers.get(key=1)

        assert tier.tier == 1
        assert tier.description == "Tier 1"

    def test_get_storage_tier_by_tier_number(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test getting a storage tier by tier number."""
        mock_session.request.return_value.json.return_value = [
            {
                "$key": 3,
                "tier": 3,
                "description": "Tier 3",
                "capacity": 1073741824000,
                "used": 107374182400,
            }
        ]

        tier = mock_client.storage_tiers.get(tier=3)

        assert tier.tier == 3

    def test_get_storage_tier_not_found(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test that NotFoundError is raised when tier not found."""
        mock_session.request.return_value.json.return_value = []

        with pytest.raises(NotFoundError):
            mock_client.storage_tiers.get(tier=99)

    def test_get_summary(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test getting storage summary."""
        mock_session.request.return_value.json.return_value = [
            {
                "$key": 1,
                "tier": 1,
                "capacity": 1073741824000,  # ~1000 GB
                "used": 107374182400,  # ~100 GB
                "allocated": 214748364800,
            },
            {
                "$key": 3,
                "tier": 3,
                "capacity": 2147483648000,  # ~2000 GB
                "used": 214748364800,  # ~200 GB
                "allocated": 429496729600,
            },
        ]

        summary = mock_client.storage_tiers.get_summary()

        assert summary["tier_count"] == 2
        assert summary["total_capacity_gb"] == pytest.approx(3000.0, abs=1.0)
        assert summary["total_used_gb"] == pytest.approx(300.0, abs=1.0)
        assert summary["used_percent"] == pytest.approx(10.0, abs=0.5)


class TestStorageTier:
    """Unit tests for StorageTier model."""

    def test_storage_tier_properties(self, mock_client: VergeClient) -> None:
        """Test StorageTier property accessors."""
        data = {
            "$key": 1,
            "tier": 1,
            "description": "Tier 1 - Fast SSD",
            "capacity": 1073741824000,  # 1000 GB
            "used": 268435456000,  # 250 GB
            "allocated": 536870912000,  # 500 GB
            "used_inflated": 375809638400,  # 350 GB (before dedupe)
            "dedupe_ratio": 140,  # 1.4x
            "modified": 1734465618,
            "stats": {
                "rops": 100,
                "wops": 50,
                "rbps": 104857600,
                "wbps": 52428800,
                "reads": 1000000,
                "writes": 500000,
                "read_bytes": 1099511627776,
                "write_bytes": 549755813888,
            },
        }
        tier = StorageTier(data, mock_client.storage_tiers)

        assert tier.tier == 1
        assert tier.description == "Tier 1 - Fast SSD"
        assert tier.capacity_gb == pytest.approx(1000.0, abs=1.0)
        assert tier.used_gb == pytest.approx(250.0, abs=1.0)
        assert tier.free_gb == pytest.approx(750.0, abs=1.0)
        assert tier.allocated_gb == pytest.approx(500.0, abs=1.0)
        assert tier.used_inflated_gb == pytest.approx(350.0, abs=1.0)
        assert tier.used_percent == 25.0
        assert tier.dedupe_ratio == 1.4
        assert tier.dedupe_savings_percent == pytest.approx(28.6, abs=0.5)
        assert tier.modified is not None

    def test_storage_tier_stats(self, mock_client: VergeClient) -> None:
        """Test StorageTier stats properties."""
        data = {
            "$key": 1,
            "tier": 1,
            "capacity": 1073741824000,
            "used": 107374182400,
            "stats": {
                "rops": 150,
                "wops": 75,
                "rbps": 157286400,  # 150 MB/s
                "wbps": 78643200,  # 75 MB/s
                "reads": 1500000,
                "writes": 750000,
                "read_bytes": 1649267441664,
                "write_bytes": 824633720832,
            },
        }
        tier = StorageTier(data, mock_client.storage_tiers)

        assert tier.read_ops == 150
        assert tier.write_ops == 75
        assert tier.read_bytes_per_sec == 157286400
        assert tier.write_bytes_per_sec == 78643200
        assert tier.total_reads == 1500000
        assert tier.total_writes == 750000
        assert tier.total_read_bytes == 1649267441664
        assert tier.total_write_bytes == 824633720832

    def test_storage_tier_missing_fields(self, mock_client: VergeClient) -> None:
        """Test StorageTier handles missing fields gracefully."""
        data = {
            "$key": 1,
            "tier": 5,
        }
        tier = StorageTier(data, mock_client.storage_tiers)

        assert tier.tier == 5
        assert tier.description == ""
        assert tier.capacity_bytes == 0
        assert tier.capacity_gb == 0.0
        assert tier.used_bytes == 0
        assert tier.used_gb == 0.0
        assert tier.free_gb == 0.0
        assert tier.used_percent == 0.0
        assert tier.dedupe_ratio == 1.0
        assert tier.dedupe_savings_percent == 0.0
        assert tier.read_ops == 0
        assert tier.write_ops == 0

    def test_storage_tier_repr(self, mock_client: VergeClient) -> None:
        """Test StorageTier string representation."""
        data = {
            "$key": 1,
            "tier": 1,
            "capacity": 1073741824000,
            "used": 268435456000,
        }
        tier = StorageTier(data, mock_client.storage_tiers)

        repr_str = repr(tier)
        assert "StorageTier" in repr_str
        assert "1" in repr_str  # tier number
