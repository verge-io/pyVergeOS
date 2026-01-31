"""Integration tests for cluster tier management.

These tests require a live VergeOS system with storage tiers configured.
Run with: pytest tests/integration/test_cluster_tiers.py -v

Prerequisites:
    - At least one cluster with storage tiers configured
    - Environment variables set (VERGE_HOST, VERGE_USERNAME, VERGE_PASSWORD)
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from pyvergeos import VergeClient
from pyvergeos.resources.cluster_tiers import (
    ClusterTier,
    ClusterTierManager,
    ClusterTierStats,
    ClusterTierStatsHistoryLong,
    ClusterTierStatsHistoryShort,
    ClusterTierStatus,
)


@pytest.fixture
def client() -> VergeClient:
    """Create a connected VergeClient from environment variables."""
    import os

    host = os.environ.get("VERGE_HOST")
    username = os.environ.get("VERGE_USERNAME")
    password = os.environ.get("VERGE_PASSWORD")

    if not all([host, username, password]):
        pytest.skip("Live VergeOS credentials not configured")

    return VergeClient(
        host=host,
        username=username,
        password=password,
        verify_ssl=False,  # Required for self-signed certs
    )


@pytest.fixture
def cluster_with_tiers(client: VergeClient) -> int | None:
    """Get a cluster key that has storage tiers."""
    clusters = client.clusters.list(storage=True)
    if clusters:
        return clusters[0].key
    return None


# =============================================================================
# Cluster Tier List and Get Tests
# =============================================================================


@pytest.mark.integration
class TestClusterTierList:
    """Integration tests for listing cluster tiers."""

    def test_list_tiers_via_cluster(self, client: VergeClient) -> None:
        """Test listing tiers via cluster.tiers property."""
        clusters = client.clusters.list(storage=True)
        if not clusters:
            pytest.skip("No storage clusters available")

        cluster = clusters[0]
        tiers = cluster.tiers.list()

        # Should have at least one tier if storage cluster exists
        assert isinstance(tiers, list)
        for tier in tiers:
            assert isinstance(tier, ClusterTier)
            assert tier.tier >= 0
            assert tier.tier <= 5
            assert tier.cluster_key == cluster.key

    def test_list_tiers_returns_capacity_info(
        self, client: VergeClient, cluster_with_tiers: int | None
    ) -> None:
        """Test that tier list includes capacity information."""
        if cluster_with_tiers is None:
            pytest.skip("No storage clusters available")

        cluster = client.clusters.get(key=cluster_with_tiers)
        tiers = cluster.tiers.list()

        if not tiers:
            pytest.skip("No tiers in cluster")

        tier = tiers[0]
        assert tier.capacity_bytes >= 0
        assert tier.used_bytes >= 0
        assert tier.capacity_gb >= 0
        assert tier.used_percent >= 0
        assert tier.used_percent <= 100

    def test_list_tiers_by_tier_number(
        self, client: VergeClient, cluster_with_tiers: int | None
    ) -> None:
        """Test filtering tiers by tier number."""
        if cluster_with_tiers is None:
            pytest.skip("No storage clusters available")

        cluster = client.clusters.get(key=cluster_with_tiers)
        all_tiers = cluster.tiers.list()

        if not all_tiers:
            pytest.skip("No tiers in cluster")

        tier_num = all_tiers[0].tier
        filtered = cluster.tiers.list(tier=tier_num)

        assert len(filtered) == 1
        assert filtered[0].tier == tier_num


@pytest.mark.integration
class TestClusterTierGet:
    """Integration tests for getting specific tiers."""

    def test_get_tier_by_key(self, client: VergeClient, cluster_with_tiers: int | None) -> None:
        """Test getting tier by key."""
        if cluster_with_tiers is None:
            pytest.skip("No storage clusters available")

        cluster = client.clusters.get(key=cluster_with_tiers)
        tiers = cluster.tiers.list()

        if not tiers:
            pytest.skip("No tiers in cluster")

        tier = cluster.tiers.get(key=tiers[0].key)

        assert isinstance(tier, ClusterTier)
        assert tier.key == tiers[0].key

    def test_get_tier_by_tier_number(
        self, client: VergeClient, cluster_with_tiers: int | None
    ) -> None:
        """Test getting tier by tier number."""
        if cluster_with_tiers is None:
            pytest.skip("No storage clusters available")

        cluster = client.clusters.get(key=cluster_with_tiers)
        tiers = cluster.tiers.list()

        if not tiers:
            pytest.skip("No tiers in cluster")

        tier_num = tiers[0].tier
        tier = cluster.tiers.get(tier=tier_num)

        assert tier.tier == tier_num


# =============================================================================
# Cluster Tier Status Tests
# =============================================================================


@pytest.mark.integration
class TestClusterTierStatus:
    """Integration tests for tier status."""

    def test_get_tier_status(self, client: VergeClient, cluster_with_tiers: int | None) -> None:
        """Test getting tier status."""
        if cluster_with_tiers is None:
            pytest.skip("No storage clusters available")

        cluster = client.clusters.get(key=cluster_with_tiers)
        tiers = cluster.tiers.list()

        if not tiers:
            pytest.skip("No tiers in cluster")

        status = tiers[0].get_status()

        assert isinstance(status, ClusterTierStatus)
        assert status.tier_key == tiers[0].key
        assert status.status_raw in [
            "online",
            "offline",
            "repairing",
            "initializing",
            "verifying",
            "noredundant",
            "outofspace",
        ]
        assert status.state_raw in ["online", "offline", "warning", "error"]

    def test_tier_status_capacity(
        self, client: VergeClient, cluster_with_tiers: int | None
    ) -> None:
        """Test tier status includes capacity info."""
        if cluster_with_tiers is None:
            pytest.skip("No storage clusters available")

        cluster = client.clusters.get(key=cluster_with_tiers)
        tiers = cluster.tiers.list()

        if not tiers:
            pytest.skip("No tiers in cluster")

        status = tiers[0].get_status()

        assert status.capacity_bytes >= 0
        assert status.used_bytes >= 0
        assert status.used_percent >= 0

    def test_tier_status_health_flags(
        self, client: VergeClient, cluster_with_tiers: int | None
    ) -> None:
        """Test tier status health flags."""
        if cluster_with_tiers is None:
            pytest.skip("No storage clusters available")

        cluster = client.clusters.get(key=cluster_with_tiers)
        tiers = cluster.tiers.list()

        if not tiers:
            pytest.skip("No tiers in cluster")

        status = tiers[0].get_status()

        # These should be boolean
        assert isinstance(status.is_redundant, bool)
        assert isinstance(status.is_encrypted, bool)
        assert isinstance(status.is_working, bool)
        assert isinstance(status.is_fullwalk, bool)
        assert isinstance(status.is_throttled, bool)


# =============================================================================
# Cluster Tier Stats Tests
# =============================================================================


@pytest.mark.integration
class TestClusterTierStats:
    """Integration tests for tier stats."""

    def test_get_tier_stats(self, client: VergeClient, cluster_with_tiers: int | None) -> None:
        """Test getting tier stats."""
        if cluster_with_tiers is None:
            pytest.skip("No storage clusters available")

        cluster = client.clusters.get(key=cluster_with_tiers)
        tiers = cluster.tiers.list()

        if not tiers:
            pytest.skip("No tiers in cluster")

        stats = tiers[0].get_stats()

        assert isinstance(stats, ClusterTierStats)
        assert stats.tier_key == tiers[0].key
        assert stats.read_ops >= 0
        assert stats.write_ops >= 0
        assert stats.read_bps >= 0
        assert stats.write_bps >= 0

    def test_tier_stats_totals(self, client: VergeClient, cluster_with_tiers: int | None) -> None:
        """Test tier stats includes total counters."""
        if cluster_with_tiers is None:
            pytest.skip("No storage clusters available")

        cluster = client.clusters.get(key=cluster_with_tiers)
        tiers = cluster.tiers.list()

        if not tiers:
            pytest.skip("No tiers in cluster")

        stats = tiers[0].get_stats()

        assert stats.total_reads >= 0
        assert stats.total_writes >= 0
        assert stats.total_read_bytes >= 0
        assert stats.total_write_bytes >= 0


# =============================================================================
# Cluster Tier Stats History Tests
# =============================================================================


@pytest.mark.integration
class TestClusterTierStatsHistory:
    """Integration tests for tier stats history."""

    def test_get_stats_history_short(
        self, client: VergeClient, cluster_with_tiers: int | None
    ) -> None:
        """Test getting short-term stats history."""
        if cluster_with_tiers is None:
            pytest.skip("No storage clusters available")

        cluster = client.clusters.get(key=cluster_with_tiers)
        tiers = cluster.tiers.list()

        if not tiers:
            pytest.skip("No tiers in cluster")

        history = tiers[0].stats_history_short(limit=10)

        assert isinstance(history, list)
        for point in history:
            assert isinstance(point, ClusterTierStatsHistoryShort)
            assert point.tier_key == tiers[0].key
            assert point.timestamp is not None

    def test_get_stats_history_long(
        self, client: VergeClient, cluster_with_tiers: int | None
    ) -> None:
        """Test getting long-term stats history."""
        if cluster_with_tiers is None:
            pytest.skip("No storage clusters available")

        cluster = client.clusters.get(key=cluster_with_tiers)
        tiers = cluster.tiers.list()

        if not tiers:
            pytest.skip("No tiers in cluster")

        history = tiers[0].stats_history_long(limit=10)

        assert isinstance(history, list)
        for point in history:
            assert isinstance(point, ClusterTierStatsHistoryLong)
            assert point.tier_key == tiers[0].key

    def test_stats_history_with_time_filter(
        self, client: VergeClient, cluster_with_tiers: int | None
    ) -> None:
        """Test getting history with time range filter."""
        if cluster_with_tiers is None:
            pytest.skip("No storage clusters available")

        cluster = client.clusters.get(key=cluster_with_tiers)
        tiers = cluster.tiers.list()

        if not tiers:
            pytest.skip("No tiers in cluster")

        now = datetime.now(timezone.utc)
        since = now - timedelta(hours=24)

        history = tiers[0].stats_history_short(since=since, limit=100)

        assert isinstance(history, list)
        # All returned points should be after 'since'
        for point in history:
            if point.timestamp:
                assert point.timestamp >= since


# =============================================================================
# Cluster Tier Summary Tests
# =============================================================================


@pytest.mark.integration
class TestClusterTierSummary:
    """Integration tests for tier summary."""

    def test_get_tier_summary(self, client: VergeClient, cluster_with_tiers: int | None) -> None:
        """Test getting tier summary for a cluster."""
        if cluster_with_tiers is None:
            pytest.skip("No storage clusters available")

        cluster = client.clusters.get(key=cluster_with_tiers)
        summary = cluster.tiers.get_summary()

        assert "cluster_key" in summary
        assert summary["cluster_key"] == cluster.key
        assert "tier_count" in summary
        assert summary["tier_count"] >= 0
        assert "total_capacity_gb" in summary
        assert "total_used_gb" in summary
        assert "used_percent" in summary
        assert "tiers" in summary


# =============================================================================
# Cluster.tiers Property Tests
# =============================================================================


@pytest.mark.integration
class TestClusterTiersProperty:
    """Integration tests for Cluster.tiers property."""

    def test_tiers_property_returns_manager(self, client: VergeClient) -> None:
        """Test that cluster.tiers returns a ClusterTierManager."""
        clusters = client.clusters.list(storage=True)
        if not clusters:
            pytest.skip("No storage clusters available")

        cluster = clusters[0]
        tier_manager = cluster.tiers

        assert isinstance(tier_manager, ClusterTierManager)
        assert tier_manager._cluster_key == cluster.key

    def test_tiers_scoped_to_cluster(self, client: VergeClient) -> None:
        """Test that tier manager is properly scoped to its cluster."""
        clusters = client.clusters.list(storage=True)
        if len(clusters) < 1:
            pytest.skip("Need at least one storage cluster")

        cluster = clusters[0]
        tiers = cluster.tiers.list()

        # All tiers should belong to this cluster
        for tier in tiers:
            assert tier.cluster_key == cluster.key
