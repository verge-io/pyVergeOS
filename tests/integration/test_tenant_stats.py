"""Integration tests for tenant stats and monitoring."""

from datetime import datetime, timedelta, timezone

import pytest

from pyvergeos import VergeClient
from pyvergeos.resources.tenant_stats import (
    TenantDashboard,
    TenantLog,
    TenantStats,
    TenantStatsHistory,
)


@pytest.mark.integration
class TestTenantStats:
    """Integration tests for TenantStats."""

    @pytest.fixture
    def test_tenant(self, live_client: VergeClient):
        """Get a tenant for testing, or skip if not available."""
        tenants = live_client.tenants.list(limit=1)
        if not tenants:
            pytest.skip("No tenants available")
        return tenants[0]

    def test_get_tenant_stats(self, live_client: VergeClient, test_tenant) -> None:
        """Test getting current tenant stats."""
        stats = test_tenant.stats.get()

        assert isinstance(stats, TenantStats)
        assert stats.tenant_key == test_tenant.key

        # Check RAM metrics
        assert isinstance(stats.ram_used_mb, int)
        assert stats.ram_used_mb >= 0

        # Check last update
        if stats.last_update:
            assert isinstance(stats.last_update, datetime)

    def test_get_tenant_stats_fields(self, live_client: VergeClient, test_tenant) -> None:
        """Test getting tenant stats with specific fields."""
        stats = test_tenant.stats.get(fields=["$key", "tenant", "ram_used"])

        assert stats.tenant_key == test_tenant.key
        assert isinstance(stats.ram_used_mb, int)

    def test_tenant_stats_history_short(self, live_client: VergeClient, test_tenant) -> None:
        """Test getting short-term stats history."""
        history = test_tenant.stats.history_short(limit=10)

        assert isinstance(history, list)
        # History might be empty for inactive tenants
        if history:
            assert all(isinstance(h, TenantStatsHistory) for h in history)

            # Check first record
            record = history[0]
            assert record.tenant_key == test_tenant.key
            assert record.timestamp is not None
            assert isinstance(record.timestamp, datetime)
            assert isinstance(record.total_cpu, int)
            assert isinstance(record.ram_used_mb, int)

    def test_tenant_stats_history_long(self, live_client: VergeClient, test_tenant) -> None:
        """Test getting long-term stats history."""
        history = test_tenant.stats.history_long(limit=10)

        assert isinstance(history, list)
        if history:
            assert all(isinstance(h, TenantStatsHistory) for h in history)

            record = history[0]
            assert record.tenant_key == test_tenant.key
            assert record.timestamp is not None

    def test_tenant_stats_history_since(self, live_client: VergeClient, test_tenant) -> None:
        """Test getting stats history since a specific time."""
        since = datetime.now(tz=timezone.utc) - timedelta(hours=1)
        history = test_tenant.stats.history_short(limit=10, since=since)

        assert isinstance(history, list)
        # All records should be after 'since'
        for record in history:
            if record.timestamp:
                assert record.timestamp >= since

    def test_tenant_stats_storage_tiers(self, live_client: VergeClient, test_tenant) -> None:
        """Test accessing storage tier stats."""
        history = test_tenant.stats.history_short(limit=1)

        if not history:
            pytest.skip("No stats history available for tenant")

        record = history[0]

        # Test get_tier_stats helper for all tiers
        for tier in range(6):
            tier_stats = record.get_tier_stats(tier)
            assert "provisioned" in tier_stats
            assert "used" in tier_stats
            assert "allocated" in tier_stats
            assert "pct" in tier_stats

            # All should be non-negative integers
            assert tier_stats["provisioned"] >= 0
            assert tier_stats["used"] >= 0
            assert tier_stats["allocated"] >= 0
            assert tier_stats["pct"] >= 0

    def test_tenant_stats_total_storage(self, live_client: VergeClient, test_tenant) -> None:
        """Test total storage calculation."""
        history = test_tenant.stats.history_short(limit=1)

        if not history:
            pytest.skip("No stats history available for tenant")

        record = history[0]
        total_used = record.total_storage_used

        # Should be the sum of all tier used values
        expected = sum(getattr(record, f"tier{i}_used") for i in range(6))
        assert total_used == expected


@pytest.mark.integration
class TestTenantLogs:
    """Integration tests for TenantLog."""

    @pytest.fixture
    def test_tenant(self, live_client: VergeClient):
        """Get a tenant for testing, or skip if not available."""
        tenants = live_client.tenants.list(limit=1)
        if not tenants:
            pytest.skip("No tenants available")
        return tenants[0]

    def test_list_tenant_logs(self, live_client: VergeClient, test_tenant) -> None:
        """Test listing tenant logs."""
        logs = test_tenant.logs.list(limit=10)

        assert isinstance(logs, list)
        if logs:
            assert all(isinstance(log, TenantLog) for log in logs)

            # Check first log
            log = logs[0]
            assert log.tenant_key == test_tenant.key
            assert isinstance(log.level, str)
            assert isinstance(log.text, str)

    def test_list_tenant_logs_with_level_filter(
        self, live_client: VergeClient, test_tenant
    ) -> None:
        """Test listing tenant logs filtered by level."""
        # Test message level
        logs = test_tenant.logs.list(limit=5, level="message")
        assert isinstance(logs, list)
        for log in logs:
            assert log.level_raw == "message"

    def test_list_tenant_logs_errors_only(self, live_client: VergeClient, test_tenant) -> None:
        """Test listing only error logs."""
        logs = test_tenant.logs.list(limit=10, errors_only=True)

        assert isinstance(logs, list)
        for log in logs:
            assert log.level_raw in ("error", "critical")
            assert log.is_error is True

    def test_list_tenant_logs_since(self, live_client: VergeClient, test_tenant) -> None:
        """Test listing logs since a specific time."""
        since = datetime.now(tz=timezone.utc) - timedelta(days=1)
        logs = test_tenant.logs.list(limit=10, since=since)

        assert isinstance(logs, list)
        for log in logs:
            if log.timestamp:
                assert log.timestamp >= since

    def test_tenant_log_properties(self, live_client: VergeClient, test_tenant) -> None:
        """Test tenant log property accessors."""
        logs = test_tenant.logs.list(limit=1)
        if not logs:
            pytest.skip("No logs available for test tenant")

        log = logs[0]

        # Test timestamp
        assert log.timestamp is not None
        assert isinstance(log.timestamp, datetime)

        # Test level display vs raw
        assert isinstance(log.level, str)
        assert isinstance(log.level_raw, str)

        # Test text
        assert isinstance(log.text, str)

        # Test boolean helpers
        assert isinstance(log.is_error, bool)
        assert isinstance(log.is_warning, bool)
        assert isinstance(log.is_audit, bool)


@pytest.mark.integration
class TestTenantDashboard:
    """Integration tests for TenantDashboard."""

    def test_get_tenant_dashboard(self, live_client: VergeClient) -> None:
        """Test getting tenant dashboard."""
        dashboard = live_client.tenant_dashboard.get()

        assert isinstance(dashboard, TenantDashboard)

        # Check tenant counts
        assert isinstance(dashboard.tenants_count, int)
        assert dashboard.tenants_count >= 0
        assert isinstance(dashboard.tenants_online, int)
        assert dashboard.tenants_online >= 0
        assert isinstance(dashboard.tenants_offline, int)
        assert dashboard.tenants_offline >= 0

        # Online + offline should not exceed total
        assert dashboard.tenants_online + dashboard.tenants_offline <= dashboard.tenants_count

    def test_tenant_dashboard_resource_counts(self, live_client: VergeClient) -> None:
        """Test tenant dashboard resource counts."""
        dashboard = live_client.tenant_dashboard.get()

        # Check node and storage counts
        assert isinstance(dashboard.nodes_count, int)
        assert dashboard.nodes_count >= 0
        assert isinstance(dashboard.storage_count, int)
        assert dashboard.storage_count >= 0
        assert isinstance(dashboard.snapshots_count, int)
        assert dashboard.snapshots_count >= 0

    def test_tenant_dashboard_top_consumers(self, live_client: VergeClient) -> None:
        """Test tenant dashboard top consumers."""
        dashboard = live_client.tenant_dashboard.get()

        # running_tenants_cores should be a list
        top_tenants = dashboard.running_tenants_cores
        assert isinstance(top_tenants, list)

        # running_nodes_cpu should be a list
        top_cpu = dashboard.running_nodes_cpu
        assert isinstance(top_cpu, list)

        # running_nodes_ram should be a list
        top_ram = dashboard.running_nodes_ram
        assert isinstance(top_ram, list)

        # tenant_storage should be a list
        top_storage = dashboard.tenant_storage
        assert isinstance(top_storage, list)

    def test_tenant_dashboard_repr(self, live_client: VergeClient) -> None:
        """Test dashboard repr."""
        dashboard = live_client.tenant_dashboard.get()

        # Repr should include tenant and node counts
        repr_str = repr(dashboard)
        assert "TenantDashboard" in repr_str
        assert "tenants=" in repr_str
        assert "nodes=" in repr_str


@pytest.mark.integration
class TestTenantStatsManagerScoping:
    """Integration tests for TenantStatsManager scoping."""

    def test_stats_manager_scoping(self, live_client: VergeClient) -> None:
        """Test that stats managers are properly scoped to their tenant."""
        tenants = live_client.tenants.list(limit=2)
        if len(tenants) < 2:
            pytest.skip("Need at least 2 tenants for this test")

        tenant1, tenant2 = tenants[0], tenants[1]

        # Get stats for each tenant
        stats1 = tenant1.stats.get()
        stats2 = tenant2.stats.get()

        # Verify they are for different tenants
        assert stats1.tenant_key == tenant1.key
        assert stats2.tenant_key == tenant2.key

        if tenant1.key != tenant2.key:
            # The stats should be for different tenants
            assert stats1.tenant_key != stats2.tenant_key

    def test_logs_manager_scoping(self, live_client: VergeClient) -> None:
        """Test that log managers are properly scoped to their tenant."""
        tenants = live_client.tenants.list(limit=2)
        if len(tenants) < 2:
            pytest.skip("Need at least 2 tenants for this test")

        tenant1, tenant2 = tenants[0], tenants[1]

        # Get logs for each tenant
        logs1 = tenant1.logs.list(limit=5)
        logs2 = tenant2.logs.list(limit=5)

        # Logs should be scoped to their respective tenants
        for log in logs1:
            assert log.tenant_key == tenant1.key

        for log in logs2:
            assert log.tenant_key == tenant2.key

    def test_stats_manager_from_tenant_property(self, live_client: VergeClient) -> None:
        """Test accessing stats manager via tenant.stats property."""
        tenants = live_client.tenants.list(limit=1)
        if not tenants:
            pytest.skip("No tenants available")

        tenant = tenants[0]

        # Access stats property
        stats_manager = tenant.stats

        # Get stats using the manager
        stats = stats_manager.get()
        assert stats.tenant_key == tenant.key

        # Get history
        history = stats_manager.history_short(limit=5)
        assert isinstance(history, list)
        for record in history:
            assert record.tenant_key == tenant.key

    def test_logs_manager_from_tenant_property(self, live_client: VergeClient) -> None:
        """Test accessing logs manager via tenant.logs property."""
        tenants = live_client.tenants.list(limit=1)
        if not tenants:
            pytest.skip("No tenants available")

        tenant = tenants[0]

        # Access logs property
        logs_manager = tenant.logs

        # Get logs using the manager
        logs = logs_manager.list(limit=5)
        assert isinstance(logs, list)
        for log in logs:
            assert log.tenant_key == tenant.key
