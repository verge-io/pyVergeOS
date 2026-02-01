"""Integration tests for network stats and monitoring.

These tests require a live VergeOS system.
Configure with environment variables:
    VERGE_HOST, VERGE_USERNAME, VERGE_PASSWORD, VERGE_VERIFY_SSL
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from pyvergeos import VergeClient
from pyvergeos.exceptions import NotFoundError
from pyvergeos.resources.network_stats import (
    IPSecActiveConnection,
    NetworkDashboard,
    NetworkMonitorStats,
    NetworkMonitorStatsHistory,
    WireGuardPeerStatus,
)
from pyvergeos.resources.networks import Network

# Skip all tests in this module if not running integration tests
pytestmark = pytest.mark.integration


# =============================================================================
# Network Dashboard Tests
# =============================================================================


class TestNetworkDashboard:
    """Integration tests for NetworkDashboard."""

    def test_get_network_dashboard(self, live_client: VergeClient) -> None:
        """Test getting the network dashboard."""
        dashboard = live_client.network_dashboard.get()

        assert isinstance(dashboard, NetworkDashboard)

        # Check total network counts
        assert isinstance(dashboard.vnets_count, int)
        assert dashboard.vnets_count >= 0

        assert isinstance(dashboard.vnets_online, int)
        assert dashboard.vnets_online >= 0
        assert dashboard.vnets_online <= dashboard.vnets_count

    def test_dashboard_has_network_type_counts(self, live_client: VergeClient) -> None:
        """Test dashboard has counts for different network types."""
        dashboard = live_client.network_dashboard.get()

        # External networks
        assert isinstance(dashboard.ext_count, int)
        assert isinstance(dashboard.ext_online, int)

        # Internal networks
        assert isinstance(dashboard.int_count, int)
        assert isinstance(dashboard.int_online, int)

        # Tenant networks
        assert isinstance(dashboard.ten_count, int)
        assert isinstance(dashboard.ten_online, int)

    def test_dashboard_has_nic_counts(self, live_client: VergeClient) -> None:
        """Test dashboard has NIC counts."""
        dashboard = live_client.network_dashboard.get()

        assert isinstance(dashboard.nics_count, int)
        assert isinstance(dashboard.nics_online, int)
        assert dashboard.nics_count >= 0

    def test_dashboard_health_summary(self, live_client: VergeClient) -> None:
        """Test getting health summary from dashboard."""
        dashboard = live_client.network_dashboard.get()

        summary = dashboard.get_health_summary()

        assert "total" in summary
        assert "external" in summary
        assert "internal" in summary
        assert "tenant" in summary
        assert "vpn" in summary

        # Each category should have count and online
        assert "count" in summary["total"]
        assert "online" in summary["total"]

    def test_dashboard_error_warning_properties(self, live_client: VergeClient) -> None:
        """Test dashboard has_errors and has_warnings properties."""
        dashboard = live_client.network_dashboard.get()

        assert isinstance(dashboard.has_errors, bool)
        assert isinstance(dashboard.has_warnings, bool)

    def test_dashboard_top_consumers(self, live_client: VergeClient) -> None:
        """Test dashboard top consumer lists."""
        dashboard = live_client.network_dashboard.get()

        assert isinstance(dashboard.running_ext_vnets, list)
        assert isinstance(dashboard.running_int_vnets, list)
        assert isinstance(dashboard.running_tenant_vnets, list)
        assert isinstance(dashboard.nics_rate, list)

    def test_dashboard_repr(self, live_client: VergeClient) -> None:
        """Test dashboard string representation."""
        dashboard = live_client.network_dashboard.get()

        repr_str = repr(dashboard)
        assert "NetworkDashboard" in repr_str
        assert "vnets=" in repr_str


# =============================================================================
# Network Monitor Stats Tests
# =============================================================================


class TestNetworkMonitorStats:
    """Integration tests for NetworkMonitorStats via Network.stats."""

    @pytest.fixture
    def running_network(self, live_client: VergeClient) -> Network:
        """Get a running network for stats testing."""
        networks = live_client.networks.list_running()
        if not networks:
            pytest.skip("No running networks available for stats testing")
        return networks[0]

    def test_network_has_stats_property(
        self, live_client: VergeClient, running_network: Network
    ) -> None:
        """Test that Network has stats property."""
        stats_manager = running_network.stats

        assert stats_manager is not None
        assert stats_manager._network_key == running_network.key

    def test_get_current_stats(self, live_client: VergeClient, running_network: Network) -> None:
        """Test getting current network stats."""
        try:
            stats = running_network.stats.get()

            assert isinstance(stats, NetworkMonitorStats)
            assert stats.vnet_key == running_network.key

            # Check quality metric
            assert isinstance(stats.quality, int)
            assert 0 <= stats.quality <= 100

            # Check latency metrics
            assert isinstance(stats.latency_avg_ms, float)
            assert stats.latency_avg_ms >= 0

        except NotFoundError:
            # Some networks may not have stats yet
            pytest.skip("No stats available for this network")

    def test_stats_health_properties(
        self, live_client: VergeClient, running_network: Network
    ) -> None:
        """Test stats health properties."""
        try:
            stats = running_network.stats.get()

            assert isinstance(stats.has_issues, bool)
            assert isinstance(stats.is_healthy, bool)
            # They should be opposites
            assert stats.has_issues != stats.is_healthy

        except NotFoundError:
            pytest.skip("No stats available for this network")

    def test_stats_history_short(self, live_client: VergeClient, running_network: Network) -> None:
        """Test getting short-term stats history."""
        history = running_network.stats.history_short(limit=10)

        assert isinstance(history, list)
        if history:
            assert all(isinstance(h, NetworkMonitorStatsHistory) for h in history)

            record = history[0]
            assert record.vnet_key == running_network.key
            assert record.timestamp is not None

    def test_stats_history_long(self, live_client: VergeClient, running_network: Network) -> None:
        """Test getting long-term stats history."""
        history = running_network.stats.history_long(limit=10)

        assert isinstance(history, list)
        if history:
            assert all(isinstance(h, NetworkMonitorStatsHistory) for h in history)

    def test_stats_history_since(self, live_client: VergeClient, running_network: Network) -> None:
        """Test getting stats history since a specific time."""
        since = datetime.now(tz=timezone.utc) - timedelta(hours=1)
        history = running_network.stats.history_short(limit=10, since=since)

        assert isinstance(history, list)
        for record in history:
            if record.timestamp:
                assert record.timestamp >= since

    def test_stats_manager_caching(
        self, live_client: VergeClient, running_network: Network
    ) -> None:
        """Test that stats manager is cached on the Network object."""
        stats_manager1 = running_network.stats
        stats_manager2 = running_network.stats

        # Should be the same instance (cached)
        assert stats_manager1 is stats_manager2


# =============================================================================
# IPSec Active Connection Tests
# =============================================================================


class TestIPSecActiveConnections:
    """Integration tests for IPSecActiveConnection tracking."""

    @pytest.fixture
    def test_network(self, live_client: VergeClient) -> Network:
        """Get a network that might have IPSec configured."""
        # Try to get External network first (most likely to have IPSec)
        try:
            return live_client.networks.get(name="External")
        except NotFoundError:
            pass

        # Fall back to first external network
        networks = live_client.networks.list_external()
        if not networks:
            pytest.skip("No external networks available for IPSec testing")
        return networks[0]

    def test_network_has_ipsec_connections_property(
        self, live_client: VergeClient, test_network: Network
    ) -> None:
        """Test that Network has ipsec_connections property."""
        conn_manager = test_network.ipsec_connections

        assert conn_manager is not None
        assert conn_manager._network_key == test_network.key

    def test_list_ipsec_connections(self, live_client: VergeClient, test_network: Network) -> None:
        """Test listing IPSec active connections."""
        connections = test_network.ipsec_connections.list()

        assert isinstance(connections, list)
        # May be empty if no active tunnels
        for conn in connections:
            assert isinstance(conn, IPSecActiveConnection)
            assert conn.vnet_key == test_network.key

    def test_count_ipsec_connections(self, live_client: VergeClient, test_network: Network) -> None:
        """Test counting IPSec connections."""
        count = test_network.ipsec_connections.count()

        assert isinstance(count, int)
        assert count >= 0

        # Verify count matches list length
        connections = test_network.ipsec_connections.list()
        assert count == len(connections)

    def test_ipsec_connection_properties(
        self, live_client: VergeClient, test_network: Network
    ) -> None:
        """Test IPSec connection properties when connections exist."""
        connections = test_network.ipsec_connections.list()

        if not connections:
            pytest.skip("No active IPSec connections")

        conn = connections[0]

        # Test required properties
        assert isinstance(conn.local, str)
        assert isinstance(conn.remote, str)
        assert isinstance(conn.connection, str)

        # Test optional timestamp
        if conn.created_at:
            assert isinstance(conn.created_at, datetime)

    def test_ipsec_connections_manager_caching(
        self, live_client: VergeClient, test_network: Network
    ) -> None:
        """Test that ipsec_connections manager is cached."""
        manager1 = test_network.ipsec_connections
        manager2 = test_network.ipsec_connections

        assert manager1 is manager2


# =============================================================================
# WireGuard Peer Status Tests
# =============================================================================


class TestWireGuardPeerStatus:
    """Integration tests for WireGuardPeerStatus."""

    @pytest.fixture
    def wireguard_interface(self, live_client: VergeClient):
        """Get a WireGuard interface for testing."""
        # Try to find a network with WireGuard
        try:
            external = live_client.networks.get(name="External")
            interfaces = external.wireguard.list()
            if interfaces:
                return interfaces[0]
        except NotFoundError:
            pass

        # Try other external networks
        networks = live_client.networks.list_external()
        for network in networks:
            interfaces = network.wireguard.list()
            if interfaces:
                return interfaces[0]

        pytest.skip("No WireGuard interfaces available for peer status testing")

    def test_wireguard_has_peer_status_property(
        self, live_client: VergeClient, wireguard_interface
    ) -> None:
        """Test that WireGuardInterface has peer_status property."""
        status_manager = wireguard_interface.peer_status

        assert status_manager is not None
        assert status_manager._wireguard_key == wireguard_interface.key

    def test_list_peer_status(self, live_client: VergeClient, wireguard_interface) -> None:
        """Test listing WireGuard peer status."""
        statuses = wireguard_interface.peer_status.list()

        assert isinstance(statuses, list)
        # May be empty if no peers
        for status in statuses:
            assert isinstance(status, WireGuardPeerStatus)

    def test_peer_status_properties(self, live_client: VergeClient, wireguard_interface) -> None:
        """Test WireGuard peer status properties."""
        statuses = wireguard_interface.peer_status.list()

        if not statuses:
            pytest.skip("No WireGuard peers with status")

        status = statuses[0]

        assert isinstance(status.peer_key, int)
        assert isinstance(status.tx_bytes, int)
        assert isinstance(status.rx_bytes, int)
        assert status.tx_bytes >= 0
        assert status.rx_bytes >= 0

    def test_peer_status_formatted_bytes(
        self, live_client: VergeClient, wireguard_interface
    ) -> None:
        """Test peer status formatted byte strings."""
        statuses = wireguard_interface.peer_status.list()

        if not statuses:
            pytest.skip("No WireGuard peers with status")

        status = statuses[0]

        # Formatted strings should include units
        assert isinstance(status.tx_bytes_formatted, str)
        assert isinstance(status.rx_bytes_formatted, str)
        # Should have some unit indicator
        assert any(unit in status.tx_bytes_formatted for unit in ["B", "KB", "MB", "GB", "TB"])

    def test_peer_status_is_connected(self, live_client: VergeClient, wireguard_interface) -> None:
        """Test peer is_connected property."""
        statuses = wireguard_interface.peer_status.list()

        if not statuses:
            pytest.skip("No WireGuard peers with status")

        status = statuses[0]
        assert isinstance(status.is_connected, bool)

    def test_peer_status_manager_caching(
        self, live_client: VergeClient, wireguard_interface
    ) -> None:
        """Test that peer_status manager is cached."""
        manager1 = wireguard_interface.peer_status
        manager2 = wireguard_interface.peer_status

        assert manager1 is manager2


# =============================================================================
# Cross-Resource Integration Tests
# =============================================================================


class TestNetworkStatsIntegration:
    """Integration tests for cross-resource network stats access."""

    def test_multiple_networks_have_independent_stats(self, live_client: VergeClient) -> None:
        """Test that different networks have independent stats managers."""
        networks = live_client.networks.list_running()
        if len(networks) < 2:
            pytest.skip("Need at least 2 running networks for this test")

        net1, net2 = networks[0], networks[1]

        # Get stats managers for each network
        stats1 = net1.stats
        stats2 = net2.stats

        # Should be different managers for different networks
        assert stats1._network_key != stats2._network_key
        assert stats1 is not stats2

    def test_dashboard_reflects_network_count(self, live_client: VergeClient) -> None:
        """Test that dashboard counts reflect actual network list."""
        dashboard = live_client.network_dashboard.get()
        networks = live_client.networks.list()

        # Total count should match or be close (timing differences possible)
        assert abs(dashboard.vnets_count - len(networks)) <= 2

    def test_dashboard_running_count_reflects_running_networks(
        self, live_client: VergeClient
    ) -> None:
        """Test that dashboard running count reflects running network list."""
        dashboard = live_client.network_dashboard.get()
        running_networks = live_client.networks.list_running()

        # Running count should match or be close
        assert abs(dashboard.vnets_online - len(running_networks)) <= 2
