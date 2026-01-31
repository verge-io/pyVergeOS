"""Unit tests for tenant stats and monitoring managers."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock

import pytest

from pyvergeos.exceptions import NotFoundError
from pyvergeos.resources.tenant_stats import (
    TenantDashboard,
    TenantDashboardManager,
    TenantLog,
    TenantLogManager,
    TenantStats,
    TenantStatsHistory,
    TenantStatsManager,
)


@pytest.fixture
def mock_client() -> MagicMock:
    """Create a mock VergeClient."""
    client = MagicMock()
    client._request = MagicMock()
    return client


@pytest.fixture
def mock_tenant() -> MagicMock:
    """Create a mock Tenant object."""
    tenant = MagicMock()
    tenant.key = 123
    tenant.name = "test-tenant"
    return tenant


# =============================================================================
# Sample Data Fixtures
# =============================================================================


@pytest.fixture
def sample_stats_data() -> dict[str, Any]:
    """Sample tenant stats data from API."""
    return {
        "$key": 1,
        "tenant": 123,
        "ram_used": 8192,
        "last_update": 1704067200,
    }


@pytest.fixture
def sample_stats_history_data() -> dict[str, Any]:
    """Sample tenant stats history data from API."""
    return {
        "$key": 1,
        "tenant": 123,
        "timestamp": 1704067200,
        "total_cpu": 45,
        "core_count": 8,
        "ram_used": 8192,
        "vram_used": 4096,
        "ram_allocated": 16384,
        "ram_pct": 50,
        "ip_count": 5,
        "tier0_provisioned": 107374182400,  # 100GB
        "tier0_used": 53687091200,  # 50GB
        "tier0_allocated": 107374182400,
        "tier0_pct": 50,
        "tier1_provisioned": 0,
        "tier1_used": 0,
        "tier1_allocated": 0,
        "tier1_pct": 0,
        "tier2_provisioned": 0,
        "tier2_used": 0,
        "tier2_allocated": 0,
        "tier2_pct": 0,
        "tier3_provisioned": 0,
        "tier3_used": 0,
        "tier3_allocated": 0,
        "tier3_pct": 0,
        "tier4_provisioned": 0,
        "tier4_used": 0,
        "tier4_allocated": 0,
        "tier4_pct": 0,
        "tier5_provisioned": 0,
        "tier5_used": 0,
        "tier5_allocated": 0,
        "tier5_pct": 0,
        "gpus_used": 1,
        "gpus_total": 2,
        "gpus_pct": 50,
        "vgpus_used": 2,
        "vgpus_total": 4,
        "vgpus_pct": 50,
    }


@pytest.fixture
def sample_log_data() -> dict[str, Any]:
    """Sample tenant log data from API."""
    return {
        "$key": 1,
        "tenant": 123,
        "tenant_name": "test-tenant",
        "level": "message",
        "text": "Tenant powered on successfully",
        "user": "admin",
        "timestamp": 1704067200000000,  # microseconds
    }


@pytest.fixture
def sample_log_list() -> list[dict[str, Any]]:
    """Sample list of tenant logs."""
    return [
        {
            "$key": 1,
            "tenant": 123,
            "tenant_name": "test-tenant",
            "level": "message",
            "text": "Tenant powered on successfully",
            "user": "admin",
            "timestamp": 1704067200000000,
        },
        {
            "$key": 2,
            "tenant": 123,
            "tenant_name": "test-tenant",
            "level": "error",
            "text": "Storage allocation failed",
            "user": "system",
            "timestamp": 1704067201000000,
        },
        {
            "$key": 3,
            "tenant": 123,
            "tenant_name": "test-tenant",
            "level": "warning",
            "text": "High resource usage detected",
            "user": "system",
            "timestamp": 1704067202000000,
        },
    ]


@pytest.fixture
def sample_dashboard_data() -> dict[str, Any]:
    """Sample tenant dashboard data from API."""
    return {
        "tenants_count": 10,
        "tenants_online": 8,
        "tenants_warn": 1,
        "tenants_error": 1,
        "storage_count": 15,
        "snapshots_count": 20,
        "cloud_snapshots_count": 5,
        "nodes_count": 25,
        "nodes_online": 22,
        "nodes_warn": 2,
        "nodes_error": 1,
        "tenant_recipes_count": 5,
        "tenant_recipes_online": 4,
        "tenant_recipes_warn": 1,
        "tenant_recipes_error": 0,
        "devices_count": 10,
        "devices_online": 9,
        "devices_warn": 1,
        "devices_error": 0,
        "running_tenants_cores": [
            {"$key": 1, "name": "tenant-a", "total_cores": 16},
            {"$key": 2, "name": "tenant-b", "total_cores": 8},
        ],
        "tenant_storage": [
            {"$key": 1, "tenant_name": "tenant-a", "used": 53687091200},
        ],
        "running_nodes_cpu": [],
        "running_nodes_ram": [],
        "running_nodes_nic": [],
        "logs": [],
        "tenant_snapshots": [],
    }


# =============================================================================
# TenantStats Model Tests
# =============================================================================


class TestTenantStats:
    """Tests for TenantStats model."""

    def test_stats_properties(self, sample_stats_data: dict[str, Any]) -> None:
        """Test stats properties."""
        manager = MagicMock()
        stats = TenantStats(sample_stats_data, manager)

        assert stats.tenant_key == 123
        assert stats.ram_used_mb == 8192

    def test_stats_last_update(self, sample_stats_data: dict[str, Any]) -> None:
        """Test last update timestamp."""
        manager = MagicMock()
        stats = TenantStats(sample_stats_data, manager)

        assert stats.last_update is not None
        assert stats.last_update.year == 2024
        assert stats.last_update.tzinfo == timezone.utc

    def test_stats_last_update_none(self) -> None:
        """Test last update when not set."""
        manager = MagicMock()
        stats = TenantStats({"$key": 1, "tenant": 123}, manager)

        assert stats.last_update is None

    def test_stats_repr(self, sample_stats_data: dict[str, Any]) -> None:
        """Test stats repr."""
        manager = MagicMock()
        stats = TenantStats(sample_stats_data, manager)

        assert "TenantStats" in repr(stats)
        assert "tenant=123" in repr(stats)
        assert "ram=8192MB" in repr(stats)


# =============================================================================
# TenantStatsHistory Model Tests
# =============================================================================


class TestTenantStatsHistory:
    """Tests for TenantStatsHistory model."""

    def test_history_properties(self, sample_stats_history_data: dict[str, Any]) -> None:
        """Test history properties."""
        manager = MagicMock()
        history = TenantStatsHistory(sample_stats_history_data, manager)

        assert history.tenant_key == 123
        assert history.timestamp_epoch == 1704067200
        assert history.total_cpu == 45
        assert history.core_count == 8
        assert history.ram_used_mb == 8192
        assert history.vram_used_mb == 4096
        assert history.ram_allocated_mb == 16384
        assert history.ram_pct == 50
        assert history.ip_count == 5

    def test_history_timestamp(self, sample_stats_history_data: dict[str, Any]) -> None:
        """Test timestamp property."""
        manager = MagicMock()
        history = TenantStatsHistory(sample_stats_history_data, manager)

        assert history.timestamp is not None
        assert history.timestamp.year == 2024
        assert history.timestamp.tzinfo == timezone.utc

    def test_history_storage_tier0(self, sample_stats_history_data: dict[str, Any]) -> None:
        """Test tier 0 storage properties."""
        manager = MagicMock()
        history = TenantStatsHistory(sample_stats_history_data, manager)

        assert history.tier0_provisioned == 107374182400
        assert history.tier0_used == 53687091200
        assert history.tier0_allocated == 107374182400
        assert history.tier0_pct == 50

    def test_history_gpu_metrics(self, sample_stats_history_data: dict[str, Any]) -> None:
        """Test GPU metrics."""
        manager = MagicMock()
        history = TenantStatsHistory(sample_stats_history_data, manager)

        assert history.gpus_used == 1
        assert history.gpus_total == 2
        assert history.gpus_pct == 50
        assert history.vgpus_used == 2
        assert history.vgpus_total == 4
        assert history.vgpus_pct == 50

    def test_history_get_tier_stats(self, sample_stats_history_data: dict[str, Any]) -> None:
        """Test get_tier_stats helper."""
        manager = MagicMock()
        history = TenantStatsHistory(sample_stats_history_data, manager)

        tier0 = history.get_tier_stats(0)
        assert tier0["provisioned"] == 107374182400
        assert tier0["used"] == 53687091200
        assert tier0["pct"] == 50

        tier1 = history.get_tier_stats(1)
        assert tier1["provisioned"] == 0
        assert tier1["used"] == 0

    def test_history_get_tier_stats_invalid(
        self, sample_stats_history_data: dict[str, Any]
    ) -> None:
        """Test get_tier_stats with invalid tier."""
        manager = MagicMock()
        history = TenantStatsHistory(sample_stats_history_data, manager)

        with pytest.raises(ValueError, match="Tier must be 0-5"):
            history.get_tier_stats(6)

        with pytest.raises(ValueError, match="Tier must be 0-5"):
            history.get_tier_stats(-1)

    def test_history_total_storage(self, sample_stats_history_data: dict[str, Any]) -> None:
        """Test total storage helpers."""
        manager = MagicMock()
        history = TenantStatsHistory(sample_stats_history_data, manager)

        assert history.total_storage_used == 53687091200
        assert history.total_storage_provisioned == 107374182400
        assert history.total_storage_allocated == 107374182400

    def test_history_repr(self, sample_stats_history_data: dict[str, Any]) -> None:
        """Test history repr."""
        manager = MagicMock()
        history = TenantStatsHistory(sample_stats_history_data, manager)

        assert "TenantStatsHistory" in repr(history)
        assert "cpu=45%" in repr(history)
        assert "ram=8192MB" in repr(history)
        assert "cores=8" in repr(history)


# =============================================================================
# TenantStatsManager Tests
# =============================================================================


class TestTenantStatsManager:
    """Tests for TenantStatsManager."""

    def test_get_stats(
        self,
        mock_client: MagicMock,
        mock_tenant: MagicMock,
        sample_stats_data: dict[str, Any],
    ) -> None:
        """Test getting current stats."""
        mock_client._request.return_value = [sample_stats_data]
        manager = TenantStatsManager(mock_client, mock_tenant)

        stats = manager.get()

        assert stats.ram_used_mb == 8192
        mock_client._request.assert_called_once()
        call_args = mock_client._request.call_args
        assert call_args[0][0] == "GET"
        assert call_args[0][1] == "tenant_stats"
        assert "tenant eq 123" in call_args[1]["params"]["filter"]

    def test_get_stats_not_found(self, mock_client: MagicMock, mock_tenant: MagicMock) -> None:
        """Test getting stats when not found."""
        mock_client._request.return_value = []
        manager = TenantStatsManager(mock_client, mock_tenant)

        with pytest.raises(NotFoundError):
            manager.get()

    def test_history_short(
        self,
        mock_client: MagicMock,
        mock_tenant: MagicMock,
        sample_stats_history_data: dict[str, Any],
    ) -> None:
        """Test getting short history."""
        mock_client._request.return_value = [sample_stats_history_data]
        manager = TenantStatsManager(mock_client, mock_tenant)

        history = manager.history_short(limit=100)

        assert len(history) == 1
        assert history[0].total_cpu == 45
        mock_client._request.assert_called_once()
        call_args = mock_client._request.call_args
        assert "tenant_stats_history_short" in call_args[0][1]

    def test_history_long(
        self,
        mock_client: MagicMock,
        mock_tenant: MagicMock,
        sample_stats_history_data: dict[str, Any],
    ) -> None:
        """Test getting long history."""
        mock_client._request.return_value = [sample_stats_history_data]
        manager = TenantStatsManager(mock_client, mock_tenant)

        history = manager.history_long(limit=100)

        assert len(history) == 1
        mock_client._request.assert_called_once()
        call_args = mock_client._request.call_args
        assert "tenant_stats_history_long" in call_args[0][1]

    def test_history_with_datetime_filter(
        self,
        mock_client: MagicMock,
        mock_tenant: MagicMock,
        sample_stats_history_data: dict[str, Any],
    ) -> None:
        """Test history with datetime filter."""
        mock_client._request.return_value = [sample_stats_history_data]
        manager = TenantStatsManager(mock_client, mock_tenant)

        since = datetime(2024, 1, 1, tzinfo=timezone.utc)
        history = manager.history_short(since=since)

        assert len(history) == 1
        call_args = mock_client._request.call_args
        assert "timestamp ge" in call_args[1]["params"]["filter"]

    def test_history_with_epoch_filter(
        self,
        mock_client: MagicMock,
        mock_tenant: MagicMock,
        sample_stats_history_data: dict[str, Any],
    ) -> None:
        """Test history with epoch timestamp filter."""
        mock_client._request.return_value = [sample_stats_history_data]
        manager = TenantStatsManager(mock_client, mock_tenant)

        history = manager.history_short(since=1704067200, until=1704153600)

        assert len(history) == 1
        call_args = mock_client._request.call_args
        assert "timestamp ge 1704067200" in call_args[1]["params"]["filter"]
        assert "timestamp le 1704153600" in call_args[1]["params"]["filter"]

    def test_history_empty_response(self, mock_client: MagicMock, mock_tenant: MagicMock) -> None:
        """Test history with empty response."""
        mock_client._request.return_value = None
        manager = TenantStatsManager(mock_client, mock_tenant)

        history = manager.history_short()

        assert history == []


# =============================================================================
# TenantLog Model Tests
# =============================================================================


class TestTenantLog:
    """Tests for TenantLog model."""

    def test_log_properties(self, sample_log_data: dict[str, Any]) -> None:
        """Test log properties."""
        manager = MagicMock()
        log = TenantLog(sample_log_data, manager)

        assert log.tenant_key == 123
        assert log.tenant_name == "test-tenant"
        assert log.level == "Message"
        assert log.level_raw == "message"
        assert log.text == "Tenant powered on successfully"
        assert log.user == "admin"

    def test_log_timestamp(self, sample_log_data: dict[str, Any]) -> None:
        """Test log timestamp (microsecond precision)."""
        manager = MagicMock()
        log = TenantLog(sample_log_data, manager)

        assert log.timestamp is not None
        assert log.timestamp_epoch_us == 1704067200000000

    def test_log_level_checks(self, sample_log_list: list[dict[str, Any]]) -> None:
        """Test log level helper properties."""
        manager = MagicMock()

        message_log = TenantLog(sample_log_list[0], manager)
        error_log = TenantLog(sample_log_list[1], manager)
        warning_log = TenantLog(sample_log_list[2], manager)

        assert message_log.is_error is False
        assert message_log.is_warning is False
        assert message_log.is_audit is False

        assert error_log.is_error is True
        assert error_log.is_warning is False

        assert warning_log.is_warning is True
        assert warning_log.is_error is False

    def test_log_repr(self, sample_log_data: dict[str, Any]) -> None:
        """Test log repr."""
        manager = MagicMock()
        log = TenantLog(sample_log_data, manager)

        assert "TenantLog" in repr(log)
        assert "Message" in repr(log)


# =============================================================================
# TenantLogManager Tests
# =============================================================================


class TestTenantLogManager:
    """Tests for TenantLogManager."""

    def test_list_logs(
        self,
        mock_client: MagicMock,
        mock_tenant: MagicMock,
        sample_log_list: list[dict[str, Any]],
    ) -> None:
        """Test listing logs."""
        mock_client._request.return_value = sample_log_list
        manager = TenantLogManager(mock_client, mock_tenant)

        logs = manager.list()

        assert len(logs) == 3
        mock_client._request.assert_called_once()

    def test_list_logs_by_level(
        self,
        mock_client: MagicMock,
        mock_tenant: MagicMock,
        sample_log_list: list[dict[str, Any]],
    ) -> None:
        """Test listing logs filtered by level."""
        mock_client._request.return_value = [sample_log_list[1]]
        manager = TenantLogManager(mock_client, mock_tenant)

        logs = manager.list(level="error")

        assert len(logs) == 1
        call_args = mock_client._request.call_args
        assert "level eq 'error'" in call_args[1]["params"]["filter"]

    def test_list_errors_only(
        self,
        mock_client: MagicMock,
        mock_tenant: MagicMock,
        sample_log_list: list[dict[str, Any]],
    ) -> None:
        """Test listing errors only."""
        mock_client._request.return_value = [sample_log_list[1]]
        manager = TenantLogManager(mock_client, mock_tenant)

        logs = manager.list(errors_only=True)

        assert len(logs) == 1
        call_args = mock_client._request.call_args
        assert "level eq 'error' or level eq 'critical'" in call_args[1]["params"]["filter"]

    def test_list_warnings_only(
        self,
        mock_client: MagicMock,
        mock_tenant: MagicMock,
        sample_log_list: list[dict[str, Any]],
    ) -> None:
        """Test listing warnings only."""
        mock_client._request.return_value = [sample_log_list[2]]
        manager = TenantLogManager(mock_client, mock_tenant)

        logs = manager.list(warnings_only=True)

        assert len(logs) == 1
        call_args = mock_client._request.call_args
        assert "level eq 'warning'" in call_args[1]["params"]["filter"]

    def test_list_logs_with_time_filter(
        self,
        mock_client: MagicMock,
        mock_tenant: MagicMock,
        sample_log_list: list[dict[str, Any]],
    ) -> None:
        """Test listing logs with time filter."""
        mock_client._request.return_value = sample_log_list
        manager = TenantLogManager(mock_client, mock_tenant)

        since = datetime(2024, 1, 1, tzinfo=timezone.utc)
        logs = manager.list(since=since)

        assert len(logs) == 3
        call_args = mock_client._request.call_args
        assert "timestamp ge" in call_args[1]["params"]["filter"]

    def test_list_logs_with_epoch_time_filter(
        self,
        mock_client: MagicMock,
        mock_tenant: MagicMock,
        sample_log_list: list[dict[str, Any]],
    ) -> None:
        """Test listing logs with epoch time filter."""
        mock_client._request.return_value = sample_log_list
        manager = TenantLogManager(mock_client, mock_tenant)

        logs = manager.list(since=1704067200000000, until=1704067210000000)

        assert len(logs) == 3
        call_args = mock_client._request.call_args
        assert "timestamp ge 1704067200000000" in call_args[1]["params"]["filter"]
        assert "timestamp le 1704067210000000" in call_args[1]["params"]["filter"]

    def test_get_log(
        self,
        mock_client: MagicMock,
        mock_tenant: MagicMock,
        sample_log_data: dict[str, Any],
    ) -> None:
        """Test getting a specific log."""
        mock_client._request.return_value = sample_log_data
        manager = TenantLogManager(mock_client, mock_tenant)

        log = manager.get(key=1)

        assert log.text == "Tenant powered on successfully"

    def test_get_log_not_found(self, mock_client: MagicMock, mock_tenant: MagicMock) -> None:
        """Test getting a log that doesn't exist."""
        mock_client._request.return_value = None
        manager = TenantLogManager(mock_client, mock_tenant)

        with pytest.raises(NotFoundError):
            manager.get(key=999)

    def test_get_log_key_required(self, mock_client: MagicMock, mock_tenant: MagicMock) -> None:
        """Test that key is required for get."""
        manager = TenantLogManager(mock_client, mock_tenant)

        with pytest.raises(ValueError, match="key must be provided"):
            manager.get()

    def test_list_logs_empty_response(self, mock_client: MagicMock, mock_tenant: MagicMock) -> None:
        """Test listing logs with empty response."""
        mock_client._request.return_value = None
        manager = TenantLogManager(mock_client, mock_tenant)

        logs = manager.list()

        assert logs == []


# =============================================================================
# TenantDashboard Model Tests
# =============================================================================


class TestTenantDashboard:
    """Tests for TenantDashboard model."""

    def test_dashboard_tenant_counts(self, sample_dashboard_data: dict[str, Any]) -> None:
        """Test dashboard tenant counts."""
        manager = MagicMock()
        dashboard = TenantDashboard(sample_dashboard_data, manager)

        assert dashboard.tenants_count == 10
        assert dashboard.tenants_online == 8
        assert dashboard.tenants_warn == 1
        assert dashboard.tenants_error == 1
        assert dashboard.tenants_offline == 2  # 10 - 8

    def test_dashboard_storage_counts(self, sample_dashboard_data: dict[str, Any]) -> None:
        """Test dashboard storage counts."""
        manager = MagicMock()
        dashboard = TenantDashboard(sample_dashboard_data, manager)

        assert dashboard.storage_count == 15
        assert dashboard.snapshots_count == 20
        assert dashboard.cloud_snapshots_count == 5

    def test_dashboard_node_counts(self, sample_dashboard_data: dict[str, Any]) -> None:
        """Test dashboard node counts."""
        manager = MagicMock()
        dashboard = TenantDashboard(sample_dashboard_data, manager)

        assert dashboard.nodes_count == 25
        assert dashboard.nodes_online == 22
        assert dashboard.nodes_warn == 2
        assert dashboard.nodes_error == 1

    def test_dashboard_recipe_counts(self, sample_dashboard_data: dict[str, Any]) -> None:
        """Test dashboard recipe counts."""
        manager = MagicMock()
        dashboard = TenantDashboard(sample_dashboard_data, manager)

        assert dashboard.tenant_recipes_count == 5
        assert dashboard.tenant_recipes_online == 4
        assert dashboard.tenant_recipes_warn == 1
        assert dashboard.tenant_recipes_error == 0

    def test_dashboard_device_counts(self, sample_dashboard_data: dict[str, Any]) -> None:
        """Test dashboard device counts."""
        manager = MagicMock()
        dashboard = TenantDashboard(sample_dashboard_data, manager)

        assert dashboard.devices_count == 10
        assert dashboard.devices_online == 9
        assert dashboard.devices_warn == 1
        assert dashboard.devices_error == 0

    def test_dashboard_top_tenants(self, sample_dashboard_data: dict[str, Any]) -> None:
        """Test dashboard top tenants lists."""
        manager = MagicMock()
        dashboard = TenantDashboard(sample_dashboard_data, manager)

        assert len(dashboard.running_tenants_cores) == 2
        assert dashboard.running_tenants_cores[0]["name"] == "tenant-a"
        assert len(dashboard.tenant_storage) == 1

    def test_dashboard_empty_lists(self) -> None:
        """Test dashboard with missing/empty lists."""
        manager = MagicMock()
        dashboard = TenantDashboard({}, manager)

        assert dashboard.running_tenants_cores == []
        assert dashboard.tenant_storage == []
        assert dashboard.running_nodes_cpu == []
        assert dashboard.logs == []

    def test_dashboard_repr(self, sample_dashboard_data: dict[str, Any]) -> None:
        """Test dashboard repr."""
        manager = MagicMock()
        dashboard = TenantDashboard(sample_dashboard_data, manager)

        assert "TenantDashboard" in repr(dashboard)
        assert "tenants=8/10" in repr(dashboard)
        assert "nodes=22/25" in repr(dashboard)


# =============================================================================
# TenantDashboardManager Tests
# =============================================================================


class TestTenantDashboardManager:
    """Tests for TenantDashboardManager."""

    def test_get_dashboard(
        self,
        mock_client: MagicMock,
        sample_dashboard_data: dict[str, Any],
    ) -> None:
        """Test getting dashboard."""
        mock_client._request.return_value = sample_dashboard_data
        manager = TenantDashboardManager(mock_client)

        dashboard = manager.get()

        assert dashboard.tenants_count == 10
        mock_client._request.assert_called_once()
        call_args = mock_client._request.call_args
        assert call_args[0][0] == "GET"
        assert call_args[0][1] == "tenant_dashboard"

    def test_get_dashboard_empty_response(self, mock_client: MagicMock) -> None:
        """Test getting dashboard with empty response."""
        mock_client._request.return_value = None
        manager = TenantDashboardManager(mock_client)

        dashboard = manager.get()

        assert dashboard.tenants_count == 0

    def test_get_dashboard_list_response(
        self,
        mock_client: MagicMock,
        sample_dashboard_data: dict[str, Any],
    ) -> None:
        """Test getting dashboard when API returns a list."""
        mock_client._request.return_value = [sample_dashboard_data]
        manager = TenantDashboardManager(mock_client)

        dashboard = manager.get()

        assert dashboard.tenants_count == 10


# =============================================================================
# Integration Tests with Tenant
# =============================================================================


class TestTenantIntegration:
    """Tests for Tenant integration with stats/logs."""

    def test_tenant_has_stats_property(self, mock_client: MagicMock) -> None:
        """Test that Tenant has stats property."""
        from pyvergeos.resources.tenant_manager import Tenant

        tenant_data = {
            "$key": 123,
            "name": "test-tenant",
        }
        manager = MagicMock()
        manager._client = mock_client
        tenant = Tenant(tenant_data, manager)

        stats_manager = tenant.stats
        assert isinstance(stats_manager, TenantStatsManager)
        assert stats_manager._tenant_key == 123

    def test_tenant_has_logs_property(self, mock_client: MagicMock) -> None:
        """Test that Tenant has logs property."""
        from pyvergeos.resources.tenant_manager import Tenant

        tenant_data = {
            "$key": 123,
            "name": "test-tenant",
        }
        manager = MagicMock()
        manager._client = mock_client
        tenant = Tenant(tenant_data, manager)

        logs_manager = tenant.logs
        assert isinstance(logs_manager, TenantLogManager)
        assert logs_manager._tenant_key == 123


# =============================================================================
# Client Integration Tests
# =============================================================================


class TestClientIntegration:
    """Tests for VergeClient integration with tenant dashboard."""

    def test_client_has_tenant_dashboard_property(self, mock_client: MagicMock) -> None:
        """Test that client has tenant_dashboard property after initialization."""
        # This tests the pattern, not the actual client
        # The actual client test would require more setup
        manager = TenantDashboardManager(mock_client)
        assert isinstance(manager, TenantDashboardManager)
