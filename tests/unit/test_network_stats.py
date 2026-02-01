"""Unit tests for network stats and monitoring managers."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock

import pytest

from pyvergeos.exceptions import NotFoundError
from pyvergeos.resources.network_stats import (
    IPSecActiveConnection,
    IPSecActiveConnectionManager,
    NetworkDashboard,
    NetworkDashboardManager,
    NetworkMonitorStats,
    NetworkMonitorStatsHistory,
    NetworkMonitorStatsManager,
    WireGuardPeerStatus,
    WireGuardPeerStatusManager,
)


@pytest.fixture
def mock_client() -> MagicMock:
    """Create a mock VergeClient."""
    client = MagicMock()
    client._request = MagicMock()
    return client


@pytest.fixture
def mock_network() -> MagicMock:
    """Create a mock Network object."""
    network = MagicMock()
    network.key = 1
    network.name = "External"
    return network


@pytest.fixture
def mock_wireguard() -> MagicMock:
    """Create a mock WireGuardInterface object."""
    wg = MagicMock()
    wg.key = 10
    wg.name = "wg0"
    return wg


# =============================================================================
# Sample Data Fixtures
# =============================================================================


@pytest.fixture
def sample_monitor_stats_data() -> dict[str, Any]:
    """Sample network monitor stats data from API."""
    return {
        "$key": 1,
        "vnet": 1,
        "timestamp": 1704067200,
        "sent": 100,
        "dropped": 2,
        "quality": 98,
        "dropped_pct": 2,
        "latency_usec_avg": 5500,
        "latency_usec_peak": 12000,
        "duplicates": 0,
        "truncated": 0,
        "bad_checksums": 0,
        "bad_data": 0,
    }


@pytest.fixture
def sample_monitor_stats_with_issues() -> dict[str, Any]:
    """Sample network monitor stats with issues."""
    return {
        "$key": 2,
        "vnet": 1,
        "timestamp": 1704067200,
        "sent": 100,
        "dropped": 15,
        "quality": 85,
        "dropped_pct": 15,
        "latency_usec_avg": 25000,
        "latency_usec_peak": 50000,
        "duplicates": 3,
        "truncated": 1,
        "bad_checksums": 2,
        "bad_data": 1,
    }


@pytest.fixture
def sample_monitor_stats_history() -> list[dict[str, Any]]:
    """Sample network monitor stats history."""
    return [
        {
            "$key": 1,
            "vnet": 1,
            "timestamp": 1704067200,
            "sent": 100,
            "dropped": 2,
            "quality": 98,
            "latency_usec_avg": 5500,
            "latency_usec_peak": 12000,
        },
        {
            "$key": 2,
            "vnet": 1,
            "timestamp": 1704067140,
            "sent": 100,
            "dropped": 3,
            "quality": 97,
            "latency_usec_avg": 6000,
            "latency_usec_peak": 15000,
        },
    ]


@pytest.fixture
def sample_dashboard_data() -> dict[str, Any]:
    """Sample network dashboard data from API."""
    return {
        "vnets_count": 10,
        "vnets_online": 8,
        "vnets_warn": 1,
        "vnets_error": 1,
        "ext_count": 2,
        "ext_online": 2,
        "ext_warn": 0,
        "ext_error": 0,
        "int_count": 5,
        "int_online": 4,
        "int_warn": 1,
        "int_error": 0,
        "ten_count": 2,
        "ten_online": 1,
        "ten_warn": 0,
        "ten_error": 1,
        "vpn_count": 1,
        "vpn_online": 1,
        "vpn_warn": 0,
        "vpn_error": 0,
        "nics_count": 25,
        "nics_online": 20,
        "nics_warn": 3,
        "nics_error": 2,
        "wireguards_count": 2,
        "running_ext_vnets": [{"$key": 1, "name": "External", "rxbps": 1000000}],
        "running_int_vnets": [{"$key": 2, "name": "Internal", "rxbps": 500000}],
        "running_tenant_vnets": [],
        "nics_rate": [{"$key": 1, "name": "eth0", "totalxbps": 1500000}],
        "logs": [{"level": "message", "text": "Network started"}],
    }


@pytest.fixture
def sample_ipsec_connection_data() -> dict[str, Any]:
    """Sample IPSec active connection data."""
    return {
        "$key": 1,
        "vnet": 1,
        "phase1": 10,
        "phase2": 20,
        "uniqueid": 12345,
        "local": "192.168.1.1",
        "remote": "10.0.0.1",
        "local_network": "192.168.1.0/24",
        "remote_network": "10.0.0.0/24",
        "connection": "site-b-vpn",
        "reqid": "1",
        "interface": "ipsec0",
        "protocol": "ESP",
        "created": 1704067200,
    }


@pytest.fixture
def sample_wireguard_peer_status() -> dict[str, Any]:
    """Sample WireGuard peer status data."""
    return {
        "$key": 1,
        "peer": 100,
        "last_handshake": 1704153600,
        "tx_bytes": 1073741824,  # 1 GB
        "rx_bytes": 536870912,  # 512 MB
        "last_update": 1704153660,
    }


@pytest.fixture
def sample_wireguard_peer_status_disconnected() -> dict[str, Any]:
    """Sample WireGuard peer status for disconnected peer."""
    return {
        "$key": 2,
        "peer": 101,
        "last_handshake": 1704067200,  # Old timestamp
        "tx_bytes": 1024,
        "rx_bytes": 512,
        "last_update": 1704067200,
    }


# =============================================================================
# NetworkMonitorStats Model Tests
# =============================================================================


class TestNetworkMonitorStats:
    """Tests for NetworkMonitorStats model."""

    def test_stats_properties(self, sample_monitor_stats_data: dict[str, Any]) -> None:
        """Test basic stats properties."""
        manager = MagicMock()
        stats = NetworkMonitorStats(sample_monitor_stats_data, manager)

        assert stats.vnet_key == 1
        assert stats.timestamp_epoch == 1704067200
        assert stats.sent == 100
        assert stats.dropped == 2
        assert stats.quality == 98
        assert stats.dropped_pct == 2
        assert stats.latency_usec_avg == 5500
        assert stats.latency_usec_peak == 12000
        assert stats.duplicates == 0
        assert stats.truncated == 0
        assert stats.bad_checksums == 0
        assert stats.bad_data == 0

    def test_latency_ms_conversion(self, sample_monitor_stats_data: dict[str, Any]) -> None:
        """Test latency conversion to milliseconds."""
        manager = MagicMock()
        stats = NetworkMonitorStats(sample_monitor_stats_data, manager)

        assert stats.latency_avg_ms == 5.5
        assert stats.latency_peak_ms == 12.0

    def test_timestamp_property(self, sample_monitor_stats_data: dict[str, Any]) -> None:
        """Test timestamp conversion."""
        manager = MagicMock()
        stats = NetworkMonitorStats(sample_monitor_stats_data, manager)

        assert stats.timestamp is not None
        assert stats.timestamp.year == 2024
        assert stats.timestamp.tzinfo == timezone.utc

    def test_has_issues_false(self) -> None:
        """Test has_issues is False when no issues."""
        manager = MagicMock()
        # Create data with no issues (dropped=0, no duplicates, etc.)
        data_no_issues = {
            "$key": 1,
            "vnet": 1,
            "timestamp": 1704067200,
            "sent": 100,
            "dropped": 0,
            "quality": 100,
            "dropped_pct": 0,
            "latency_usec_avg": 5500,
            "latency_usec_peak": 12000,
            "duplicates": 0,
            "truncated": 0,
            "bad_checksums": 0,
            "bad_data": 0,
        }
        stats = NetworkMonitorStats(data_no_issues, manager)

        assert stats.has_issues is False
        assert stats.is_healthy is True

    def test_has_issues_true(self, sample_monitor_stats_with_issues: dict[str, Any]) -> None:
        """Test has_issues is True when issues present."""
        manager = MagicMock()
        stats = NetworkMonitorStats(sample_monitor_stats_with_issues, manager)

        assert stats.has_issues is True
        assert stats.is_healthy is False

    def test_repr(self, sample_monitor_stats_data: dict[str, Any]) -> None:
        """Test stats repr."""
        manager = MagicMock()
        stats = NetworkMonitorStats(sample_monitor_stats_data, manager)

        repr_str = repr(stats)
        assert "NetworkMonitorStats" in repr_str
        assert "vnet=1" in repr_str
        assert "quality=98%" in repr_str
        assert "latency=5.5ms" in repr_str


# =============================================================================
# NetworkMonitorStatsHistory Model Tests
# =============================================================================


class TestNetworkMonitorStatsHistory:
    """Tests for NetworkMonitorStatsHistory model."""

    def test_history_properties(self, sample_monitor_stats_history: list[dict[str, Any]]) -> None:
        """Test history properties."""
        manager = MagicMock()
        history = NetworkMonitorStatsHistory(sample_monitor_stats_history[0], manager)

        assert history.vnet_key == 1
        assert history.timestamp_epoch == 1704067200
        assert history.quality == 98
        assert history.latency_avg_ms == 5.5

    def test_repr(self, sample_monitor_stats_history: list[dict[str, Any]]) -> None:
        """Test history repr."""
        manager = MagicMock()
        history = NetworkMonitorStatsHistory(sample_monitor_stats_history[0], manager)

        assert "NetworkMonitorStatsHistory" in repr(history)
        assert "quality=98%" in repr(history)


# =============================================================================
# NetworkMonitorStatsManager Tests
# =============================================================================


class TestNetworkMonitorStatsManager:
    """Tests for NetworkMonitorStatsManager."""

    def test_get_stats(
        self,
        mock_client: MagicMock,
        mock_network: MagicMock,
        sample_monitor_stats_data: dict[str, Any],
    ) -> None:
        """Test getting current stats."""
        mock_client._request.return_value = [sample_monitor_stats_data]
        manager = NetworkMonitorStatsManager(mock_client, mock_network)

        stats = manager.get()

        assert stats.quality == 98
        mock_client._request.assert_called_once()
        call_args = mock_client._request.call_args
        assert call_args[0][0] == "GET"
        assert "vnet_monitor_stats_history_short" in call_args[0][1]
        assert "vnet eq 1" in call_args[1]["params"]["filter"]

    def test_get_stats_not_found(
        self,
        mock_client: MagicMock,
        mock_network: MagicMock,
    ) -> None:
        """Test getting stats when not found."""
        mock_client._request.return_value = []
        manager = NetworkMonitorStatsManager(mock_client, mock_network)

        with pytest.raises(NotFoundError):
            manager.get()

    def test_history_short(
        self,
        mock_client: MagicMock,
        mock_network: MagicMock,
        sample_monitor_stats_history: list[dict[str, Any]],
    ) -> None:
        """Test getting short history."""
        mock_client._request.return_value = sample_monitor_stats_history
        manager = NetworkMonitorStatsManager(mock_client, mock_network)

        history = manager.history_short(limit=100)

        assert len(history) == 2
        assert history[0].quality == 98
        mock_client._request.assert_called_once()
        call_args = mock_client._request.call_args
        assert "vnet_monitor_stats_history_short" in call_args[0][1]

    def test_history_long(
        self,
        mock_client: MagicMock,
        mock_network: MagicMock,
        sample_monitor_stats_history: list[dict[str, Any]],
    ) -> None:
        """Test getting long history."""
        mock_client._request.return_value = sample_monitor_stats_history
        manager = NetworkMonitorStatsManager(mock_client, mock_network)

        history = manager.history_long(limit=100)

        assert len(history) == 2
        mock_client._request.assert_called_once()
        call_args = mock_client._request.call_args
        assert "vnet_monitor_stats_history_long" in call_args[0][1]

    def test_history_with_datetime_filter(
        self,
        mock_client: MagicMock,
        mock_network: MagicMock,
        sample_monitor_stats_history: list[dict[str, Any]],
    ) -> None:
        """Test history with datetime filter."""
        mock_client._request.return_value = sample_monitor_stats_history
        manager = NetworkMonitorStatsManager(mock_client, mock_network)

        since = datetime(2024, 1, 1, tzinfo=timezone.utc)
        history = manager.history_short(since=since)

        assert len(history) == 2
        call_args = mock_client._request.call_args
        assert "timestamp ge" in call_args[1]["params"]["filter"]

    def test_history_with_epoch_filter(
        self,
        mock_client: MagicMock,
        mock_network: MagicMock,
        sample_monitor_stats_history: list[dict[str, Any]],
    ) -> None:
        """Test history with epoch timestamp filter."""
        mock_client._request.return_value = sample_monitor_stats_history
        manager = NetworkMonitorStatsManager(mock_client, mock_network)

        history = manager.history_short(since=1704067200, until=1704153600)

        assert len(history) == 2
        call_args = mock_client._request.call_args
        assert "timestamp ge 1704067200" in call_args[1]["params"]["filter"]
        assert "timestamp le 1704153600" in call_args[1]["params"]["filter"]

    def test_history_empty_response(
        self,
        mock_client: MagicMock,
        mock_network: MagicMock,
    ) -> None:
        """Test empty history response."""
        mock_client._request.return_value = None
        manager = NetworkMonitorStatsManager(mock_client, mock_network)

        history = manager.history_short()

        assert history == []


# =============================================================================
# NetworkDashboard Model Tests
# =============================================================================


class TestNetworkDashboard:
    """Tests for NetworkDashboard model."""

    def test_dashboard_total_counts(self, sample_dashboard_data: dict[str, Any]) -> None:
        """Test dashboard total network counts."""
        manager = MagicMock()
        dashboard = NetworkDashboard(sample_dashboard_data, manager)

        assert dashboard.vnets_count == 10
        assert dashboard.vnets_online == 8
        assert dashboard.vnets_warn == 1
        assert dashboard.vnets_error == 1
        assert dashboard.vnets_offline == 2

    def test_dashboard_external_counts(self, sample_dashboard_data: dict[str, Any]) -> None:
        """Test dashboard external network counts."""
        manager = MagicMock()
        dashboard = NetworkDashboard(sample_dashboard_data, manager)

        assert dashboard.ext_count == 2
        assert dashboard.ext_online == 2
        assert dashboard.ext_warn == 0
        assert dashboard.ext_error == 0

    def test_dashboard_internal_counts(self, sample_dashboard_data: dict[str, Any]) -> None:
        """Test dashboard internal network counts."""
        manager = MagicMock()
        dashboard = NetworkDashboard(sample_dashboard_data, manager)

        assert dashboard.int_count == 5
        assert dashboard.int_online == 4
        assert dashboard.int_warn == 1
        assert dashboard.int_error == 0

    def test_dashboard_tenant_counts(self, sample_dashboard_data: dict[str, Any]) -> None:
        """Test dashboard tenant network counts."""
        manager = MagicMock()
        dashboard = NetworkDashboard(sample_dashboard_data, manager)

        assert dashboard.ten_count == 2
        assert dashboard.ten_online == 1
        assert dashboard.ten_error == 1

    def test_dashboard_vpn_counts(self, sample_dashboard_data: dict[str, Any]) -> None:
        """Test dashboard VPN network counts."""
        manager = MagicMock()
        dashboard = NetworkDashboard(sample_dashboard_data, manager)

        assert dashboard.vpn_count == 1
        assert dashboard.vpn_online == 1

    def test_dashboard_nic_counts(self, sample_dashboard_data: dict[str, Any]) -> None:
        """Test dashboard NIC counts."""
        manager = MagicMock()
        dashboard = NetworkDashboard(sample_dashboard_data, manager)

        assert dashboard.nics_count == 25
        assert dashboard.nics_online == 20
        assert dashboard.nics_warn == 3
        assert dashboard.nics_error == 2

    def test_dashboard_wireguard_count(self, sample_dashboard_data: dict[str, Any]) -> None:
        """Test dashboard WireGuard count."""
        manager = MagicMock()
        dashboard = NetworkDashboard(sample_dashboard_data, manager)

        assert dashboard.wireguards_count == 2

    def test_dashboard_top_consumers(self, sample_dashboard_data: dict[str, Any]) -> None:
        """Test dashboard top consumer lists."""
        manager = MagicMock()
        dashboard = NetworkDashboard(sample_dashboard_data, manager)

        assert len(dashboard.running_ext_vnets) == 1
        assert dashboard.running_ext_vnets[0]["name"] == "External"
        assert len(dashboard.running_int_vnets) == 1
        assert len(dashboard.running_tenant_vnets) == 0
        assert len(dashboard.nics_rate) == 1
        assert len(dashboard.logs) == 1

    def test_dashboard_has_errors(self, sample_dashboard_data: dict[str, Any]) -> None:
        """Test has_errors property."""
        manager = MagicMock()
        dashboard = NetworkDashboard(sample_dashboard_data, manager)

        assert dashboard.has_errors is True

    def test_dashboard_has_warnings(self, sample_dashboard_data: dict[str, Any]) -> None:
        """Test has_warnings property."""
        manager = MagicMock()
        dashboard = NetworkDashboard(sample_dashboard_data, manager)

        assert dashboard.has_warnings is True

    def test_dashboard_no_errors(self) -> None:
        """Test no errors."""
        manager = MagicMock()
        dashboard = NetworkDashboard({"vnets_error": 0, "vnets_warn": 0}, manager)

        assert dashboard.has_errors is False
        assert dashboard.has_warnings is False

    def test_get_health_summary(self, sample_dashboard_data: dict[str, Any]) -> None:
        """Test get_health_summary method."""
        manager = MagicMock()
        dashboard = NetworkDashboard(sample_dashboard_data, manager)

        summary = dashboard.get_health_summary()

        assert "total" in summary
        assert summary["total"]["count"] == 10
        assert summary["total"]["online"] == 8
        assert "external" in summary
        assert "internal" in summary
        assert "tenant" in summary
        assert "vpn" in summary

    def test_repr(self, sample_dashboard_data: dict[str, Any]) -> None:
        """Test dashboard repr."""
        manager = MagicMock()
        dashboard = NetworkDashboard(sample_dashboard_data, manager)

        repr_str = repr(dashboard)
        assert "NetworkDashboard" in repr_str
        assert "vnets=8/10" in repr_str


# =============================================================================
# NetworkDashboardManager Tests
# =============================================================================


class TestNetworkDashboardManager:
    """Tests for NetworkDashboardManager."""

    def test_get_dashboard(
        self,
        mock_client: MagicMock,
        sample_dashboard_data: dict[str, Any],
    ) -> None:
        """Test getting dashboard."""
        mock_client._request.return_value = sample_dashboard_data
        manager = NetworkDashboardManager(mock_client)

        dashboard = manager.get()

        assert dashboard.vnets_count == 10
        mock_client._request.assert_called_once_with("GET", "vnet_dashboard")

    def test_get_dashboard_list_response(
        self,
        mock_client: MagicMock,
        sample_dashboard_data: dict[str, Any],
    ) -> None:
        """Test getting dashboard when API returns list."""
        mock_client._request.return_value = [sample_dashboard_data]
        manager = NetworkDashboardManager(mock_client)

        dashboard = manager.get()

        assert dashboard.vnets_count == 10

    def test_get_dashboard_empty_response(self, mock_client: MagicMock) -> None:
        """Test getting dashboard with empty response."""
        mock_client._request.return_value = None
        manager = NetworkDashboardManager(mock_client)

        dashboard = manager.get()

        assert dashboard.vnets_count == 0


# =============================================================================
# IPSecActiveConnection Model Tests
# =============================================================================


class TestIPSecActiveConnection:
    """Tests for IPSecActiveConnection model."""

    def test_connection_properties(self, sample_ipsec_connection_data: dict[str, Any]) -> None:
        """Test connection properties."""
        manager = MagicMock()
        conn = IPSecActiveConnection(sample_ipsec_connection_data, manager)

        assert conn.vnet_key == 1
        assert conn.phase1_key == 10
        assert conn.phase2_key == 20
        assert conn.uniqueid == 12345
        assert conn.local == "192.168.1.1"
        assert conn.remote == "10.0.0.1"
        assert conn.local_network == "192.168.1.0/24"
        assert conn.remote_network == "10.0.0.0/24"
        assert conn.connection == "site-b-vpn"
        assert conn.reqid == "1"
        assert conn.interface == "ipsec0"
        assert conn.protocol == "ESP"

    def test_connection_created_at(self, sample_ipsec_connection_data: dict[str, Any]) -> None:
        """Test connection created timestamp."""
        manager = MagicMock()
        conn = IPSecActiveConnection(sample_ipsec_connection_data, manager)

        assert conn.created_at is not None
        assert conn.created_at.year == 2024
        assert conn.created_at.tzinfo == timezone.utc

    def test_connection_repr(self, sample_ipsec_connection_data: dict[str, Any]) -> None:
        """Test connection repr."""
        manager = MagicMock()
        conn = IPSecActiveConnection(sample_ipsec_connection_data, manager)

        repr_str = repr(conn)
        assert "IPSecActiveConnection" in repr_str
        assert "site-b-vpn" in repr_str


# =============================================================================
# IPSecActiveConnectionManager Tests
# =============================================================================


class TestIPSecActiveConnectionManager:
    """Tests for IPSecActiveConnectionManager."""

    def test_list_connections(
        self,
        mock_client: MagicMock,
        mock_network: MagicMock,
        sample_ipsec_connection_data: dict[str, Any],
    ) -> None:
        """Test listing connections."""
        mock_client._request.return_value = [sample_ipsec_connection_data]
        manager = IPSecActiveConnectionManager(mock_client, mock_network)

        connections = manager.list()

        assert len(connections) == 1
        assert connections[0].connection == "site-b-vpn"
        mock_client._request.assert_called_once()
        call_args = mock_client._request.call_args
        assert "vnet_ipsec_connections" in call_args[0][1]
        assert "vnet eq 1" in call_args[1]["params"]["filter"]

    def test_list_connections_empty(
        self,
        mock_client: MagicMock,
        mock_network: MagicMock,
    ) -> None:
        """Test listing connections when none exist."""
        mock_client._request.return_value = []
        manager = IPSecActiveConnectionManager(mock_client, mock_network)

        connections = manager.list()

        assert connections == []

    def test_count_connections(
        self,
        mock_client: MagicMock,
        mock_network: MagicMock,
        sample_ipsec_connection_data: dict[str, Any],
    ) -> None:
        """Test counting connections."""
        mock_client._request.return_value = [
            sample_ipsec_connection_data,
            {**sample_ipsec_connection_data, "$key": 2},
        ]
        manager = IPSecActiveConnectionManager(mock_client, mock_network)

        count = manager.count()

        assert count == 2


# =============================================================================
# WireGuardPeerStatus Model Tests
# =============================================================================


class TestWireGuardPeerStatus:
    """Tests for WireGuardPeerStatus model."""

    def test_status_properties(self, sample_wireguard_peer_status: dict[str, Any]) -> None:
        """Test status properties."""
        manager = MagicMock()
        status = WireGuardPeerStatus(sample_wireguard_peer_status, manager)

        assert status.peer_key == 100
        assert status.tx_bytes == 1073741824
        assert status.rx_bytes == 536870912
        assert status.last_handshake_epoch == 1704153600

    def test_formatted_bytes(self, sample_wireguard_peer_status: dict[str, Any]) -> None:
        """Test formatted byte strings."""
        manager = MagicMock()
        status = WireGuardPeerStatus(sample_wireguard_peer_status, manager)

        assert "GB" in status.tx_bytes_formatted
        assert "MB" in status.rx_bytes_formatted

    def test_last_handshake(self, sample_wireguard_peer_status: dict[str, Any]) -> None:
        """Test last handshake timestamp."""
        manager = MagicMock()
        status = WireGuardPeerStatus(sample_wireguard_peer_status, manager)

        assert status.last_handshake is not None
        assert status.last_handshake.tzinfo == timezone.utc

    def test_last_update(self, sample_wireguard_peer_status: dict[str, Any]) -> None:
        """Test last update timestamp."""
        manager = MagicMock()
        status = WireGuardPeerStatus(sample_wireguard_peer_status, manager)

        assert status.last_update is not None

    def test_is_connected_no_handshake(self) -> None:
        """Test is_connected when no handshake."""
        manager = MagicMock()
        status = WireGuardPeerStatus({"peer": 1}, manager)

        assert status.is_connected is False

    def test_repr(self, sample_wireguard_peer_status: dict[str, Any]) -> None:
        """Test status repr."""
        manager = MagicMock()
        status = WireGuardPeerStatus(sample_wireguard_peer_status, manager)

        repr_str = repr(status)
        assert "WireGuardPeerStatus" in repr_str
        assert "peer=100" in repr_str


# =============================================================================
# WireGuardPeerStatusManager Tests
# =============================================================================


class TestWireGuardPeerStatusManager:
    """Tests for WireGuardPeerStatusManager."""

    def test_list_status(
        self,
        mock_client: MagicMock,
        mock_wireguard: MagicMock,
        sample_wireguard_peer_status: dict[str, Any],
    ) -> None:
        """Test listing peer status."""
        # First call returns peers, second returns status
        mock_client._request.side_effect = [
            [{"$key": 100}],  # vnet_wireguard_peers query
            [sample_wireguard_peer_status],  # vnet_wireguard_peer_status query
        ]
        manager = WireGuardPeerStatusManager(mock_client, mock_wireguard)

        statuses = manager.list()

        assert len(statuses) == 1
        assert statuses[0].peer_key == 100

    def test_list_status_no_peers(
        self,
        mock_client: MagicMock,
        mock_wireguard: MagicMock,
    ) -> None:
        """Test listing status when no peers."""
        mock_client._request.return_value = []
        manager = WireGuardPeerStatusManager(mock_client, mock_wireguard)

        statuses = manager.list()

        assert statuses == []

    def test_get_for_peer(
        self,
        mock_client: MagicMock,
        mock_wireguard: MagicMock,
        sample_wireguard_peer_status: dict[str, Any],
    ) -> None:
        """Test getting status for specific peer."""
        mock_client._request.return_value = [sample_wireguard_peer_status]
        manager = WireGuardPeerStatusManager(mock_client, mock_wireguard)

        status = manager.get_for_peer(100)

        assert status.peer_key == 100
        call_args = mock_client._request.call_args
        assert "peer eq 100" in call_args[1]["params"]["filter"]

    def test_get_for_peer_not_found(
        self,
        mock_client: MagicMock,
        mock_wireguard: MagicMock,
    ) -> None:
        """Test getting status for non-existent peer."""
        mock_client._request.return_value = []
        manager = WireGuardPeerStatusManager(mock_client, mock_wireguard)

        with pytest.raises(NotFoundError):
            manager.get_for_peer(999)


# =============================================================================
# Integration Tests
# =============================================================================


class TestNetworkIntegration:
    """Tests for Network integration with stats."""

    def test_network_has_stats_property(self, mock_client: MagicMock) -> None:
        """Test that Network has stats property."""
        from pyvergeos.resources.networks import Network

        network_data = {
            "$key": 1,
            "name": "External",
        }
        manager = MagicMock()
        manager._client = mock_client
        network = Network(network_data, manager)

        stats_manager = network.stats
        assert isinstance(stats_manager, NetworkMonitorStatsManager)
        assert stats_manager._network_key == 1

    def test_network_has_ipsec_connections_property(self, mock_client: MagicMock) -> None:
        """Test that Network has ipsec_connections property."""
        from pyvergeos.resources.networks import Network

        network_data = {
            "$key": 1,
            "name": "External",
        }
        manager = MagicMock()
        manager._client = mock_client
        network = Network(network_data, manager)

        conn_manager = network.ipsec_connections
        assert isinstance(conn_manager, IPSecActiveConnectionManager)


class TestWireGuardIntegration:
    """Tests for WireGuard integration with peer status."""

    def test_wireguard_has_peer_status_property(self, mock_client: MagicMock) -> None:
        """Test that WireGuardInterface has peer_status property."""
        from pyvergeos.resources.wireguard import WireGuardInterface, WireGuardManager

        wg_data = {
            "$key": 10,
            "name": "wg0",
            "vnet": 1,
        }
        network = MagicMock()
        network.key = 1
        wg_manager = WireGuardManager(mock_client, network)
        wg = WireGuardInterface(wg_data, wg_manager)

        status_manager = wg.peer_status
        assert isinstance(status_manager, WireGuardPeerStatusManager)
        assert status_manager._wireguard_key == 10


class TestClientIntegration:
    """Tests for VergeClient integration with network dashboard."""

    def test_client_has_network_dashboard_property(self, mock_client: MagicMock) -> None:
        """Test that client has network_dashboard property."""
        from pyvergeos.client import VergeClient

        # Create a minimal client instance without auto-connect
        client = VergeClient.__new__(VergeClient)
        client._network_dashboard = None
        client._connection = None

        # Access property triggers lazy loading
        dashboard_manager = client.network_dashboard
        assert isinstance(dashboard_manager, NetworkDashboardManager)
