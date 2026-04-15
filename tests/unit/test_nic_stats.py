"""Unit tests for machine NIC stats, status, and fabric status managers."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from pyvergeos.exceptions import NotFoundError
from pyvergeos.resources.nic_stats import (
    MachineNicFabricStatus,
    MachineNicFabricStatusManager,
    MachineNicStats,
    MachineNicStatsManager,
    MachineNicStatus,
    MachineNicStatusManager,
    _format_bps,
)


@pytest.fixture
def mock_client() -> MagicMock:
    """Create a mock VergeClient."""
    client = MagicMock()
    client._request = MagicMock()
    return client


# =============================================================================
# Sample Data Fixtures
# =============================================================================


@pytest.fixture
def sample_nic_stats_data() -> dict[str, Any]:
    """Sample NIC stats data from API."""
    return {
        "$key": 1,
        "parent_nic": 42,
        "txpps": 1000,
        "rxpps": 2000,
        "txbps": 8000000,
        "rxbps": 16000000,
        "totalxbps": 24000000,
        "tx_pckts": 50000,
        "rx_pckts": 100000,
        "tx_bytes": 40000000,
        "rx_bytes": 80000000,
        "tx_pckts_cur": 500,
        "rx_pckts_cur": 1000,
        "tx_bytes_cur": 400000,
        "rx_bytes_cur": 800000,
        "last_update": 1704067200,
    }


@pytest.fixture
def sample_nic_status_data() -> dict[str, Any]:
    """Sample NIC status data from API."""
    return {
        "$key": 1,
        "parent_nic": 42,
        "status": "up",
        "state": "online",
        "speed": 10000,
        "last_update": 1704067200,
    }


@pytest.fixture
def sample_nic_fabric_data() -> dict[str, Any]:
    """Sample NIC fabric status data from API."""
    return {
        "$key": 1,
        "parent_nic": 42,
        "status": "confirmed",
        "state": "online",
        "max_score": 100.0,
        "min_score": 95.0,
        "paths": [{"node": 1, "score": 100}, {"node": 2, "score": 95}],
        "created": 1704000000,
        "modified": 1704067200,
    }


# =============================================================================
# MachineNicStats Tests
# =============================================================================


class TestMachineNicStats:
    """Tests for MachineNicStats resource object."""

    def test_nic_key(self, sample_nic_stats_data: dict[str, Any]) -> None:
        stats = MachineNicStats(sample_nic_stats_data, MagicMock())
        assert stats.nic_key == 42

    def test_tx_pps(self, sample_nic_stats_data: dict[str, Any]) -> None:
        stats = MachineNicStats(sample_nic_stats_data, MagicMock())
        assert stats.tx_pps == 1000

    def test_rx_pps(self, sample_nic_stats_data: dict[str, Any]) -> None:
        stats = MachineNicStats(sample_nic_stats_data, MagicMock())
        assert stats.rx_pps == 2000

    def test_tx_bps(self, sample_nic_stats_data: dict[str, Any]) -> None:
        stats = MachineNicStats(sample_nic_stats_data, MagicMock())
        assert stats.tx_bps == 8000000

    def test_rx_bps(self, sample_nic_stats_data: dict[str, Any]) -> None:
        stats = MachineNicStats(sample_nic_stats_data, MagicMock())
        assert stats.rx_bps == 16000000

    def test_total_bps(self, sample_nic_stats_data: dict[str, Any]) -> None:
        stats = MachineNicStats(sample_nic_stats_data, MagicMock())
        assert stats.total_bps == 24000000

    def test_tx_packets(self, sample_nic_stats_data: dict[str, Any]) -> None:
        stats = MachineNicStats(sample_nic_stats_data, MagicMock())
        assert stats.tx_packets == 50000

    def test_rx_packets(self, sample_nic_stats_data: dict[str, Any]) -> None:
        stats = MachineNicStats(sample_nic_stats_data, MagicMock())
        assert stats.rx_packets == 100000

    def test_tx_bytes(self, sample_nic_stats_data: dict[str, Any]) -> None:
        stats = MachineNicStats(sample_nic_stats_data, MagicMock())
        assert stats.tx_bytes == 40000000

    def test_rx_bytes(self, sample_nic_stats_data: dict[str, Any]) -> None:
        stats = MachineNicStats(sample_nic_stats_data, MagicMock())
        assert stats.rx_bytes == 80000000

    def test_current_counters(self, sample_nic_stats_data: dict[str, Any]) -> None:
        stats = MachineNicStats(sample_nic_stats_data, MagicMock())
        assert stats.tx_packets_current == 500
        assert stats.rx_packets_current == 1000
        assert stats.tx_bytes_current == 400000
        assert stats.rx_bytes_current == 800000

    def test_display_properties(self, sample_nic_stats_data: dict[str, Any]) -> None:
        stats = MachineNicStats(sample_nic_stats_data, MagicMock())
        assert "Mbps" in stats.tx_bps_display
        assert "Mbps" in stats.rx_bps_display
        assert "Mbps" in stats.total_bps_display

    def test_defaults_when_empty(self) -> None:
        stats = MachineNicStats({}, MagicMock())
        assert stats.nic_key == 0
        assert stats.tx_pps == 0
        assert stats.rx_pps == 0
        assert stats.tx_bps == 0
        assert stats.tx_bps_display == "0 bps"


# =============================================================================
# MachineNicStatus Tests
# =============================================================================


class TestMachineNicStatus:
    """Tests for MachineNicStatus resource object."""

    def test_nic_key(self, sample_nic_status_data: dict[str, Any]) -> None:
        status = MachineNicStatus(sample_nic_status_data, MagicMock())
        assert status.nic_key == 42

    def test_link_status(self, sample_nic_status_data: dict[str, Any]) -> None:
        status = MachineNicStatus(sample_nic_status_data, MagicMock())
        assert status.link_status == "up"
        assert status.link_status_display == "Up"

    def test_state(self, sample_nic_status_data: dict[str, Any]) -> None:
        status = MachineNicStatus(sample_nic_status_data, MagicMock())
        assert status.state == "online"
        assert status.state_display == "Online"

    def test_is_up(self, sample_nic_status_data: dict[str, Any]) -> None:
        status = MachineNicStatus(sample_nic_status_data, MagicMock())
        assert status.is_up is True

    def test_is_not_up(self) -> None:
        status = MachineNicStatus(
            {"$key": 1, "parent_nic": 42, "status": "down", "state": "offline"},
            MagicMock(),
        )
        assert status.is_up is False

    def test_speed(self, sample_nic_status_data: dict[str, Any]) -> None:
        status = MachineNicStatus(sample_nic_status_data, MagicMock())
        assert status.speed == 10000
        assert status.speed_display == "10 Gbps"

    def test_speed_mbps(self) -> None:
        status = MachineNicStatus({"$key": 1, "parent_nic": 42, "speed": 100}, MagicMock())
        assert status.speed_display == "100 Mbps"

    def test_speed_unknown(self) -> None:
        status = MachineNicStatus({"$key": 1, "parent_nic": 42, "speed": 0}, MagicMock())
        assert status.speed_display == "Unknown"

    def test_lowerlayerdown(self) -> None:
        status = MachineNicStatus(
            {
                "$key": 1,
                "parent_nic": 42,
                "status": "lowerlayerdown",
                "state": "error",
            },
            MagicMock(),
        )
        assert status.link_status_display == "Lower Layer Down"
        assert status.state_display == "Error"


# =============================================================================
# MachineNicFabricStatus Tests
# =============================================================================


class TestMachineNicFabricStatus:
    """Tests for MachineNicFabricStatus resource object."""

    def test_nic_key(self, sample_nic_fabric_data: dict[str, Any]) -> None:
        fabric = MachineNicFabricStatus(sample_nic_fabric_data, MagicMock())
        assert fabric.nic_key == 42

    def test_fabric_status_confirmed(self, sample_nic_fabric_data: dict[str, Any]) -> None:
        fabric = MachineNicFabricStatus(sample_nic_fabric_data, MagicMock())
        assert fabric.fabric_status == "confirmed"
        assert fabric.fabric_status_display == "Confirmed"
        assert fabric.is_healthy is True
        assert fabric.is_degraded is False

    def test_fabric_status_degraded(self) -> None:
        fabric = MachineNicFabricStatus(
            {"$key": 1, "parent_nic": 42, "status": "degraded", "state": "warning"},
            MagicMock(),
        )
        assert fabric.is_healthy is False
        assert fabric.is_degraded is True
        assert fabric.fabric_status_display == "Degraded"

    def test_scores(self, sample_nic_fabric_data: dict[str, Any]) -> None:
        fabric = MachineNicFabricStatus(sample_nic_fabric_data, MagicMock())
        assert fabric.max_score == 100.0
        assert fabric.min_score == 95.0

    def test_paths(self, sample_nic_fabric_data: dict[str, Any]) -> None:
        fabric = MachineNicFabricStatus(sample_nic_fabric_data, MagicMock())
        assert isinstance(fabric.paths, list)
        assert len(fabric.paths) == 2


# =============================================================================
# MachineNicStatsManager Tests
# =============================================================================


class TestMachineNicStatsManager:
    """Tests for MachineNicStatsManager."""

    def test_endpoint(self, mock_client: MagicMock) -> None:
        manager = MachineNicStatsManager(mock_client, nic_key=42)
        assert manager._endpoint == "machine_nic_stats"

    def test_get_scoped(
        self,
        mock_client: MagicMock,
        sample_nic_stats_data: dict[str, Any],
    ) -> None:
        mock_client._request.return_value = [sample_nic_stats_data]
        manager = MachineNicStatsManager(mock_client, nic_key=42)
        stats = manager.get()
        assert isinstance(stats, MachineNicStats)
        assert stats.nic_key == 42

    def test_get_scoped_filters_by_nic(
        self,
        mock_client: MagicMock,
        sample_nic_stats_data: dict[str, Any],
    ) -> None:
        mock_client._request.return_value = [sample_nic_stats_data]
        manager = MachineNicStatsManager(mock_client, nic_key=42)
        manager.get()
        call_args = mock_client._request.call_args
        assert "parent_nic eq 42" in call_args.kwargs["params"]["filter"]

    def test_get_by_key(
        self,
        mock_client: MagicMock,
        sample_nic_stats_data: dict[str, Any],
    ) -> None:
        mock_client._request.return_value = sample_nic_stats_data
        manager = MachineNicStatsManager(mock_client, nic_key=42)
        stats = manager.get(key=1)
        assert stats.key == 1

    def test_get_scoped_not_found(self, mock_client: MagicMock) -> None:
        mock_client._request.return_value = []
        manager = MachineNicStatsManager(mock_client, nic_key=999)
        with pytest.raises(NotFoundError):
            manager.get()

    def test_get_no_scope_no_key(self, mock_client: MagicMock) -> None:
        manager = MachineNicStatsManager(mock_client)
        with pytest.raises(ValueError, match="Either key or scoped nic_key"):
            manager.get()

    def test_global_list(
        self,
        mock_client: MagicMock,
        sample_nic_stats_data: dict[str, Any],
    ) -> None:
        mock_client._request.return_value = [sample_nic_stats_data]
        manager = MachineNicStatsManager(mock_client)
        results = manager.list(filter="parent_nic eq 42")
        assert len(results) == 1


# =============================================================================
# MachineNicStatusManager Tests
# =============================================================================


class TestMachineNicStatusManager:
    """Tests for MachineNicStatusManager."""

    def test_endpoint(self, mock_client: MagicMock) -> None:
        manager = MachineNicStatusManager(mock_client, nic_key=42)
        assert manager._endpoint == "machine_nic_status"

    def test_get_scoped(
        self,
        mock_client: MagicMock,
        sample_nic_status_data: dict[str, Any],
    ) -> None:
        mock_client._request.return_value = [sample_nic_status_data]
        manager = MachineNicStatusManager(mock_client, nic_key=42)
        status = manager.get()
        assert isinstance(status, MachineNicStatus)
        assert status.is_up is True

    def test_get_not_found(self, mock_client: MagicMock) -> None:
        mock_client._request.return_value = []
        manager = MachineNicStatusManager(mock_client, nic_key=999)
        with pytest.raises(NotFoundError):
            manager.get()


# =============================================================================
# MachineNicFabricStatusManager Tests
# =============================================================================


class TestMachineNicFabricStatusManager:
    """Tests for MachineNicFabricStatusManager."""

    def test_endpoint(self, mock_client: MagicMock) -> None:
        manager = MachineNicFabricStatusManager(mock_client, nic_key=42)
        assert manager._endpoint == "machine_nic_fabric_status"

    def test_get_scoped(
        self,
        mock_client: MagicMock,
        sample_nic_fabric_data: dict[str, Any],
    ) -> None:
        mock_client._request.return_value = [sample_nic_fabric_data]
        manager = MachineNicFabricStatusManager(mock_client, nic_key=42)
        fabric = manager.get()
        assert isinstance(fabric, MachineNicFabricStatus)
        assert fabric.is_healthy is True

    def test_get_not_found(self, mock_client: MagicMock) -> None:
        mock_client._request.return_value = []
        manager = MachineNicFabricStatusManager(mock_client, nic_key=999)
        with pytest.raises(NotFoundError):
            manager.get()


# =============================================================================
# Helper Function Tests
# =============================================================================


class TestFormatBps:
    """Tests for _format_bps helper."""

    def test_zero(self) -> None:
        assert _format_bps(0) == "0 bps"

    def test_bps(self) -> None:
        assert _format_bps(500) == "500.00 bps"

    def test_kbps(self) -> None:
        assert _format_bps(5000) == "5.00 Kbps"

    def test_mbps(self) -> None:
        assert _format_bps(8000000) == "8.00 Mbps"

    def test_gbps(self) -> None:
        assert _format_bps(10000000000) == "10.00 Gbps"
