"""Unit tests for cluster tier management."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock

import pytest

from pyvergeos.exceptions import NotFoundError
from pyvergeos.resources.cluster_tiers import (
    ClusterTier,
    ClusterTierManager,
    ClusterTierStats,
    ClusterTierStatsHistoryLong,
    ClusterTierStatsHistoryShort,
    ClusterTierStatus,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_client() -> MagicMock:
    """Create a mock VergeClient."""
    client = MagicMock()
    client._request = MagicMock()
    return client


@pytest.fixture
def tier_manager(mock_client: MagicMock) -> ClusterTierManager:
    """Create a ClusterTierManager scoped to cluster 1."""
    return ClusterTierManager(mock_client, cluster_key=1)


@pytest.fixture
def sample_tier_data() -> dict[str, Any]:
    """Sample tier data as returned from API."""
    return {
        "$key": 1,
        "tier": 1,
        "cluster": 1,
        "description": "High Performance SSD",
        "cost_per_gb": 0.10,
        "price_per_gb": 0.15,
        "display_status": "online",
        "display_state": "online",
        "capacity": 1099511627776,  # 1 TB
        "used": 549755813888,  # 512 GB
        "used_pct": 50,
        "redundant": True,
        "encrypted": True,
        "working": False,
        "rops": 5000,
        "wops": 3000,
        "rbps": 524288000,  # 500 MB/s
        "wbps": 262144000,  # 250 MB/s
    }


@pytest.fixture
def sample_status_data() -> dict[str, Any]:
    """Sample tier status data."""
    return {
        "$key": 1,
        "tier": 1,
        "status": "online",
        "state": "online",
        "capacity": 1099511627776,
        "used": 549755813888,
        "used_pct": 50,
        "redundant": True,
        "encrypted": True,
        "working": False,
        "last_walk_time_ms": 150,
        "last_fullwalk_time_ms": 5000,
        "transaction": 12345,
        "repairs": 2,
        "bad_drives": 0,
        "fullwalk": False,
        "progress": 0,
        "index_unique": 987654,
        "state_timestamp": 1706745600,
        "cur_space_throttle_ms": 0,
        "transaction_start_stamp": 1706745000,
    }


@pytest.fixture
def sample_stats_data() -> dict[str, Any]:
    """Sample tier stats data."""
    return {
        "$key": 1,
        "tier": 1,
        "rops": 5000,
        "wops": 3000,
        "rbps": 524288000,
        "wbps": 262144000,
        "reads": 1000000,
        "writes": 500000,
        "read_bytes": 1099511627776,
        "write_bytes": 549755813888,
        "last_update": 1706745600,
    }


@pytest.fixture
def sample_history_short_data() -> dict[str, Any]:
    """Sample short-term history data."""
    return {
        "$key": 1,
        "tier": 1,
        "timestamp": 1706745600,
        "rops": 5000,
        "wops": 3000,
        "rbps": 524288000,
        "wbps": 262144000,
        "reads": 100000,
        "writes": 50000,
        "read_bytes": 107374182400,
        "write_bytes": 53687091200,
        "capacity": 1099511627776,
        "used": 549755813888,
    }


@pytest.fixture
def sample_history_long_data() -> dict[str, Any]:
    """Sample long-term history data."""
    return {
        "$key": 1,
        "tier": 1,
        "timestamp": 1706745600,
        "rops_peak": 10000,
        "wops_peak": 6000,
        "rbps_peak": 1048576000,
        "wbps_peak": 524288000,
        "rops_avg": 4000,
        "wops_avg": 2000,
        "rbps_avg": 419430400,
        "wbps_avg": 209715200,
        "reads": 1000000,
        "writes": 500000,
        "read_bytes": 1099511627776,
        "write_bytes": 549755813888,
        "capacity": 1099511627776,
        "used": 549755813888,
    }


# =============================================================================
# ClusterTier Tests
# =============================================================================


class TestClusterTier:
    """Tests for ClusterTier resource object."""

    def test_tier_properties(
        self, tier_manager: ClusterTierManager, sample_tier_data: dict[str, Any]
    ) -> None:
        """Test basic tier properties."""
        tier = ClusterTier(sample_tier_data, tier_manager)

        assert tier.tier == 1
        assert tier.cluster_key == 1
        assert tier.description == "High Performance SSD"
        assert tier.cost_per_gb == 0.10
        assert tier.price_per_gb == 0.15

    def test_tier_status_properties(
        self, tier_manager: ClusterTierManager, sample_tier_data: dict[str, Any]
    ) -> None:
        """Test tier status properties."""
        tier = ClusterTier(sample_tier_data, tier_manager)

        assert tier.status == "Online"
        assert tier.status_raw == "online"

    def test_tier_capacity_properties(
        self, tier_manager: ClusterTierManager, sample_tier_data: dict[str, Any]
    ) -> None:
        """Test tier capacity properties."""
        tier = ClusterTier(sample_tier_data, tier_manager)

        assert tier.capacity_bytes == 1099511627776
        assert tier.capacity_gb == 1024.0
        assert tier.capacity_tb == 1.0
        assert tier.used_bytes == 549755813888
        assert tier.used_gb == 512.0
        assert tier.used_tb == 0.5
        assert tier.used_percent == 50.0
        assert tier.free_bytes == 549755813888
        assert tier.free_gb == 512.0

    def test_tier_redundancy_properties(
        self, tier_manager: ClusterTierManager, sample_tier_data: dict[str, Any]
    ) -> None:
        """Test tier redundancy and encryption properties."""
        tier = ClusterTier(sample_tier_data, tier_manager)

        assert tier.is_redundant is True
        assert tier.is_encrypted is True
        assert tier.is_working is False

    def test_tier_io_properties(
        self, tier_manager: ClusterTierManager, sample_tier_data: dict[str, Any]
    ) -> None:
        """Test tier I/O properties."""
        tier = ClusterTier(sample_tier_data, tier_manager)

        assert tier.read_ops == 5000
        assert tier.write_ops == 3000
        assert tier.read_bps == 524288000
        assert tier.write_bps == 262144000

    def test_tier_repr(
        self, tier_manager: ClusterTierManager, sample_tier_data: dict[str, Any]
    ) -> None:
        """Test tier string representation."""
        tier = ClusterTier(sample_tier_data, tier_manager)
        repr_str = repr(tier)

        assert "ClusterTier" in repr_str
        assert "tier=1" in repr_str
        assert "cluster=1" in repr_str


# =============================================================================
# ClusterTierStatus Tests
# =============================================================================


class TestClusterTierStatus:
    """Tests for ClusterTierStatus resource object."""

    def test_status_properties(
        self, tier_manager: ClusterTierManager, sample_status_data: dict[str, Any]
    ) -> None:
        """Test status properties."""
        status = ClusterTierStatus(sample_status_data, tier_manager)

        assert status.tier_key == 1
        assert status.status == "Online"
        assert status.status_raw == "online"
        assert status.state == "Online"
        assert status.state_raw == "online"

    def test_status_boolean_properties(
        self, tier_manager: ClusterTierManager, sample_status_data: dict[str, Any]
    ) -> None:
        """Test status boolean helpers."""
        status = ClusterTierStatus(sample_status_data, tier_manager)

        assert status.is_online is True
        assert status.is_healthy is True
        assert status.is_warning is False
        assert status.is_error is False

    def test_status_capacity_properties(
        self, tier_manager: ClusterTierManager, sample_status_data: dict[str, Any]
    ) -> None:
        """Test status capacity properties."""
        status = ClusterTierStatus(sample_status_data, tier_manager)

        assert status.capacity_bytes == 1099511627776
        assert status.capacity_gb == 1024.0
        assert status.capacity_tb == 1.0
        assert status.used_bytes == 549755813888
        assert status.used_percent == 50.0
        assert status.free_gb == 512.0

    def test_status_health_properties(
        self, tier_manager: ClusterTierManager, sample_status_data: dict[str, Any]
    ) -> None:
        """Test status health properties."""
        status = ClusterTierStatus(sample_status_data, tier_manager)

        assert status.is_redundant is True
        assert status.is_encrypted is True
        assert status.is_working is False
        assert status.repairs == 2
        assert status.bad_drives == 0

    def test_status_walk_properties(
        self, tier_manager: ClusterTierManager, sample_status_data: dict[str, Any]
    ) -> None:
        """Test status walk properties."""
        status = ClusterTierStatus(sample_status_data, tier_manager)

        assert status.last_walk_time_ms == 150
        assert status.last_fullwalk_time_ms == 5000
        assert status.is_fullwalk is False
        assert status.walk_progress == 0

    def test_status_throttle_properties(
        self, tier_manager: ClusterTierManager, sample_status_data: dict[str, Any]
    ) -> None:
        """Test status throttle properties."""
        status = ClusterTierStatus(sample_status_data, tier_manager)

        assert status.throttle_ms == 0
        assert status.is_throttled is False

    def test_status_timestamps(
        self, tier_manager: ClusterTierManager, sample_status_data: dict[str, Any]
    ) -> None:
        """Test status timestamp properties."""
        status = ClusterTierStatus(sample_status_data, tier_manager)

        assert status.state_timestamp is not None
        assert isinstance(status.state_timestamp, datetime)
        assert status.transaction_start is not None


# =============================================================================
# ClusterTierStats Tests
# =============================================================================


class TestClusterTierStats:
    """Tests for ClusterTierStats resource object."""

    def test_stats_io_properties(
        self, tier_manager: ClusterTierManager, sample_stats_data: dict[str, Any]
    ) -> None:
        """Test stats I/O properties."""
        stats = ClusterTierStats(sample_stats_data, tier_manager)

        assert stats.tier_key == 1
        assert stats.read_ops == 5000
        assert stats.write_ops == 3000
        assert stats.read_bps == 524288000
        assert stats.write_bps == 262144000
        assert stats.read_mbps == 500.0
        assert stats.write_mbps == 250.0

    def test_stats_totals(
        self, tier_manager: ClusterTierManager, sample_stats_data: dict[str, Any]
    ) -> None:
        """Test stats total counters."""
        stats = ClusterTierStats(sample_stats_data, tier_manager)

        assert stats.total_reads == 1000000
        assert stats.total_writes == 500000
        assert stats.total_read_bytes == 1099511627776
        assert stats.total_write_bytes == 549755813888

    def test_stats_last_update(
        self, tier_manager: ClusterTierManager, sample_stats_data: dict[str, Any]
    ) -> None:
        """Test stats last update timestamp."""
        stats = ClusterTierStats(sample_stats_data, tier_manager)

        assert stats.last_update is not None
        assert isinstance(stats.last_update, datetime)


# =============================================================================
# ClusterTierStatsHistoryShort Tests
# =============================================================================


class TestClusterTierStatsHistoryShort:
    """Tests for ClusterTierStatsHistoryShort resource object."""

    def test_history_short_properties(
        self, tier_manager: ClusterTierManager, sample_history_short_data: dict[str, Any]
    ) -> None:
        """Test short history properties."""
        history = ClusterTierStatsHistoryShort(sample_history_short_data, tier_manager)

        assert history.tier_key == 1
        assert history.timestamp is not None
        assert history.timestamp_epoch == 1706745600
        assert history.read_ops == 5000
        assert history.write_ops == 3000
        assert history.read_bps == 524288000
        assert history.write_bps == 262144000

    def test_history_short_capacity(
        self, tier_manager: ClusterTierManager, sample_history_short_data: dict[str, Any]
    ) -> None:
        """Test short history capacity properties."""
        history = ClusterTierStatsHistoryShort(sample_history_short_data, tier_manager)

        assert history.capacity_bytes == 1099511627776
        assert history.capacity_gb == 1024.0
        assert history.used_bytes == 549755813888
        assert history.used_percent == 50.0


# =============================================================================
# ClusterTierStatsHistoryLong Tests
# =============================================================================


class TestClusterTierStatsHistoryLong:
    """Tests for ClusterTierStatsHistoryLong resource object."""

    def test_history_long_peak_properties(
        self, tier_manager: ClusterTierManager, sample_history_long_data: dict[str, Any]
    ) -> None:
        """Test long history peak properties."""
        history = ClusterTierStatsHistoryLong(sample_history_long_data, tier_manager)

        assert history.read_ops_peak == 10000
        assert history.write_ops_peak == 6000
        assert history.read_bps_peak == 1048576000
        assert history.write_bps_peak == 524288000

    def test_history_long_avg_properties(
        self, tier_manager: ClusterTierManager, sample_history_long_data: dict[str, Any]
    ) -> None:
        """Test long history average properties."""
        history = ClusterTierStatsHistoryLong(sample_history_long_data, tier_manager)

        assert history.read_ops_avg == 4000
        assert history.write_ops_avg == 2000
        assert history.read_bps_avg == 419430400
        assert history.write_bps_avg == 209715200

    def test_history_long_totals(
        self, tier_manager: ClusterTierManager, sample_history_long_data: dict[str, Any]
    ) -> None:
        """Test long history total counters."""
        history = ClusterTierStatsHistoryLong(sample_history_long_data, tier_manager)

        assert history.total_reads == 1000000
        assert history.total_writes == 500000


# =============================================================================
# ClusterTierManager Tests
# =============================================================================


class TestClusterTierManager:
    """Tests for ClusterTierManager."""

    def test_manager_initialization(self, mock_client: MagicMock) -> None:
        """Test manager initialization with cluster scope."""
        manager = ClusterTierManager(mock_client, cluster_key=1)

        assert manager._cluster_key == 1
        assert manager._endpoint == "cluster_tiers"

    def test_list_tiers(
        self,
        tier_manager: ClusterTierManager,
        mock_client: MagicMock,
        sample_tier_data: dict[str, Any],
    ) -> None:
        """Test listing tiers."""
        mock_client._request.return_value = [sample_tier_data]

        tiers = tier_manager.list()

        assert len(tiers) == 1
        assert isinstance(tiers[0], ClusterTier)
        assert tiers[0].tier == 1

        # Verify filter includes cluster scope
        call_args = mock_client._request.call_args
        assert "cluster eq 1" in call_args[1]["params"]["filter"]

    def test_list_tiers_by_tier_number(
        self,
        tier_manager: ClusterTierManager,
        mock_client: MagicMock,
        sample_tier_data: dict[str, Any],
    ) -> None:
        """Test listing tiers filtered by tier number."""
        mock_client._request.return_value = [sample_tier_data]

        tiers = tier_manager.list(tier=1)

        assert len(tiers) == 1

        # Verify filter includes tier number
        call_args = mock_client._request.call_args
        assert "tier eq 1" in call_args[1]["params"]["filter"]

    def test_list_tiers_empty(
        self, tier_manager: ClusterTierManager, mock_client: MagicMock
    ) -> None:
        """Test listing tiers returns empty list when none exist."""
        mock_client._request.return_value = None

        tiers = tier_manager.list()

        assert tiers == []

    def test_get_tier_by_key(
        self,
        tier_manager: ClusterTierManager,
        mock_client: MagicMock,
        sample_tier_data: dict[str, Any],
    ) -> None:
        """Test getting tier by key."""
        mock_client._request.return_value = sample_tier_data

        tier = tier_manager.get(key=1)

        assert isinstance(tier, ClusterTier)
        assert tier.key == 1
        mock_client._request.assert_called_once()

    def test_get_tier_by_tier_number(
        self,
        tier_manager: ClusterTierManager,
        mock_client: MagicMock,
        sample_tier_data: dict[str, Any],
    ) -> None:
        """Test getting tier by tier number."""
        mock_client._request.return_value = [sample_tier_data]

        tier = tier_manager.get(tier=1)

        assert isinstance(tier, ClusterTier)
        assert tier.tier == 1

    def test_get_tier_not_found(
        self, tier_manager: ClusterTierManager, mock_client: MagicMock
    ) -> None:
        """Test getting tier that doesn't exist."""
        mock_client._request.return_value = None

        with pytest.raises(NotFoundError):
            tier_manager.get(key=999)

    def test_get_tier_no_args(self, tier_manager: ClusterTierManager) -> None:
        """Test getting tier without key or tier raises ValueError."""
        with pytest.raises(ValueError, match="Either key or tier must be provided"):
            tier_manager.get()

    def test_get_tier_status(
        self,
        tier_manager: ClusterTierManager,
        mock_client: MagicMock,
        sample_status_data: dict[str, Any],
    ) -> None:
        """Test getting tier status."""
        mock_client._request.return_value = [sample_status_data]

        status = tier_manager.get_tier_status(tier_key=1)

        assert isinstance(status, ClusterTierStatus)
        assert status.status == "Online"

        # Verify correct endpoint called
        call_args = mock_client._request.call_args
        assert call_args[0][1] == "cluster_tier_status"

    def test_get_tier_stats(
        self,
        tier_manager: ClusterTierManager,
        mock_client: MagicMock,
        sample_stats_data: dict[str, Any],
    ) -> None:
        """Test getting tier stats."""
        mock_client._request.return_value = [sample_stats_data]

        stats = tier_manager.get_tier_stats(tier_key=1)

        assert isinstance(stats, ClusterTierStats)
        assert stats.read_ops == 5000

        # Verify correct endpoint called
        call_args = mock_client._request.call_args
        assert call_args[0][1] == "cluster_tier_stats"

    def test_get_stats_history_short(
        self,
        tier_manager: ClusterTierManager,
        mock_client: MagicMock,
        sample_history_short_data: dict[str, Any],
    ) -> None:
        """Test getting short-term stats history."""
        mock_client._request.return_value = [sample_history_short_data]

        history = tier_manager.get_stats_history_short(tier_key=1, limit=10)

        assert len(history) == 1
        assert isinstance(history[0], ClusterTierStatsHistoryShort)

        # Verify correct endpoint called
        call_args = mock_client._request.call_args
        assert call_args[0][1] == "cluster_tier_stats_history_short"

    def test_get_stats_history_short_with_time_range(
        self,
        tier_manager: ClusterTierManager,
        mock_client: MagicMock,
        sample_history_short_data: dict[str, Any],
    ) -> None:
        """Test getting short-term stats history with time range."""
        mock_client._request.return_value = [sample_history_short_data]

        since = datetime(2024, 1, 1, tzinfo=timezone.utc)
        until = datetime(2024, 1, 31, tzinfo=timezone.utc)

        tier_manager.get_stats_history_short(tier_key=1, since=since, until=until)

        call_args = mock_client._request.call_args
        filter_str = call_args[1]["params"]["filter"]
        assert "timestamp ge" in filter_str
        assert "timestamp le" in filter_str

    def test_get_stats_history_long(
        self,
        tier_manager: ClusterTierManager,
        mock_client: MagicMock,
        sample_history_long_data: dict[str, Any],
    ) -> None:
        """Test getting long-term stats history."""
        mock_client._request.return_value = [sample_history_long_data]

        history = tier_manager.get_stats_history_long(tier_key=1, limit=10)

        assert len(history) == 1
        assert isinstance(history[0], ClusterTierStatsHistoryLong)

        # Verify correct endpoint called
        call_args = mock_client._request.call_args
        assert call_args[0][1] == "cluster_tier_stats_history_long"

    def test_get_summary(
        self,
        tier_manager: ClusterTierManager,
        mock_client: MagicMock,
        sample_tier_data: dict[str, Any],
    ) -> None:
        """Test getting tier summary."""
        mock_client._request.return_value = [sample_tier_data]

        summary = tier_manager.get_summary()

        assert summary["cluster_key"] == 1
        assert summary["tier_count"] == 1
        assert summary["total_capacity_gb"] == 1024.0
        assert summary["total_used_gb"] == 512.0
        assert summary["used_percent"] == 50.0
        assert 1 in summary["tiers"]


# =============================================================================
# Cluster.tiers Integration Tests
# =============================================================================


class TestClusterTiersProperty:
    """Tests for Cluster.tiers property."""

    def test_cluster_tiers_property(self, mock_client: MagicMock) -> None:
        """Test accessing tiers via cluster object."""
        from pyvergeos.resources.clusters import Cluster, ClusterManager

        cluster_manager = ClusterManager(mock_client)
        cluster_data = {"$key": 1, "name": "Test Cluster"}
        cluster = Cluster(cluster_data, cluster_manager)

        tier_manager = cluster.tiers

        assert isinstance(tier_manager, ClusterTierManager)
        assert tier_manager._cluster_key == 1


# =============================================================================
# Status Display Mapping Tests
# =============================================================================


class TestStatusDisplayMappings:
    """Tests for status display string mappings."""

    def test_tier_status_display_online(self, tier_manager: ClusterTierManager) -> None:
        """Test online status display."""
        status = ClusterTierStatus({"status": "online", "tier": 1}, tier_manager)
        assert status.status == "Online"

    def test_tier_status_display_repairing(self, tier_manager: ClusterTierManager) -> None:
        """Test repairing status display."""
        status = ClusterTierStatus({"status": "repairing", "tier": 1}, tier_manager)
        assert status.status == "Repairing"

    def test_tier_status_display_noredundant(self, tier_manager: ClusterTierManager) -> None:
        """Test no redundancy status display."""
        status = ClusterTierStatus({"status": "noredundant", "tier": 1}, tier_manager)
        assert status.status == "Online - No Redundancy"

    def test_tier_status_display_outofspace(self, tier_manager: ClusterTierManager) -> None:
        """Test out of space status display."""
        status = ClusterTierStatus({"status": "outofspace", "tier": 1}, tier_manager)
        assert status.status == "Tier Throttled (Low Space)"

    def test_tier_state_display_warning(self, tier_manager: ClusterTierManager) -> None:
        """Test warning state display."""
        status = ClusterTierStatus({"state": "warning", "tier": 1}, tier_manager)
        assert status.state == "Warning"
        assert status.is_warning is True
        assert status.is_healthy is False


# =============================================================================
# Edge Cases
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_zero_capacity_tier(self, tier_manager: ClusterTierManager) -> None:
        """Test tier with zero capacity doesn't cause division by zero."""
        tier = ClusterTier({"$key": 1, "tier": 1, "capacity": 0, "used": 0}, tier_manager)

        assert tier.used_percent == 0.0
        assert tier.free_bytes == 0

    def test_missing_optional_fields(self, tier_manager: ClusterTierManager) -> None:
        """Test tier with missing optional fields uses defaults."""
        tier = ClusterTier({"$key": 1, "tier": 1}, tier_manager)

        assert tier.description == ""
        assert tier.cost_per_gb == 0.0
        assert tier.is_redundant is False
        assert tier.read_ops == 0

    def test_status_not_found(
        self, tier_manager: ClusterTierManager, mock_client: MagicMock
    ) -> None:
        """Test getting status when none exists raises NotFoundError."""
        mock_client._request.return_value = []

        with pytest.raises(NotFoundError):
            tier_manager.get_tier_status(tier_key=999)

    def test_stats_not_found(
        self, tier_manager: ClusterTierManager, mock_client: MagicMock
    ) -> None:
        """Test getting stats when none exist raises NotFoundError."""
        mock_client._request.return_value = []

        with pytest.raises(NotFoundError):
            tier_manager.get_tier_stats(tier_key=999)

    def test_history_empty(self, tier_manager: ClusterTierManager, mock_client: MagicMock) -> None:
        """Test getting history when none exists returns empty list."""
        mock_client._request.return_value = None

        history = tier_manager.get_stats_history_short(tier_key=1)

        assert history == []
