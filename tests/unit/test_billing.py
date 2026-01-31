"""Unit tests for billing resource manager."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import MagicMock

import pytest

from pyvergeos.exceptions import NotFoundError
from pyvergeos.resources.billing import BillingManager, BillingRecord


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
def sample_billing_data() -> dict[str, Any]:
    """Sample billing record data from API."""
    return {
        "$key": 1,
        "created": 1704067200,
        "from": 1704063600,
        "to": 1704067200,
        "sent": 1704067201,
        "description": "Billing report for January",
        "used_cores": 32,
        "total_cores": 64,
        "online_cores": 60,
        "total_nodes": 4,
        "online_nodes": 4,
        "running_machines": 25,
        "used_ram": 65536,  # 64 GB in MB
        "total_ram": 131072,  # 128 GB in MB
        "online_ram": 131072,
        "phys_ram_used": 68719476736,  # 64 GB in bytes
        "phys_vram_used": 17179869184,  # 16 GB in bytes
        "phys_total_cpu": 75,
        "tier_0_used": 107374182400,  # 100 GB
        "tier_0_total": 1099511627776,  # 1 TB
        "tier_1_used": 536870912000,  # 500 GB
        "tier_1_total": 2199023255552,  # 2 TB
        "tier_2_used": 0,
        "tier_2_total": 0,
        "tier_3_used": 0,
        "tier_3_total": 0,
        "tier_4_used": 0,
        "tier_4_total": 0,
        "tier_5_used": 0,
        "tier_5_total": 0,
        "gpus_total": 4,
        "gpus": 2,
        "gpus_idle": 2,
        "vgpus_total": 8,
        "vgpus": 4,
        "vgpus_idle": 4,
        "workload_datapoints": 1000,
        "storage_datapoints": 500,
    }


@pytest.fixture
def sample_billing_list() -> list[dict[str, Any]]:
    """Sample list of billing records."""
    return [
        {
            "$key": 2,
            "created": 1704153600,
            "from": 1704150000,
            "to": 1704153600,
            "description": "Second billing record",
            "used_cores": 40,
            "total_cores": 64,
            "online_cores": 60,
            "total_nodes": 4,
            "online_nodes": 4,
            "running_machines": 30,
            "used_ram": 81920,
            "total_ram": 131072,
            "online_ram": 131072,
            "phys_ram_used": 85899345920,
            "phys_vram_used": 17179869184,
            "phys_total_cpu": 80,
            "tier_0_used": 128849018880,
            "tier_0_total": 1099511627776,
            "tier_1_used": 644245094400,
            "tier_1_total": 2199023255552,
            "tier_2_used": 0,
            "tier_2_total": 0,
            "tier_3_used": 0,
            "tier_3_total": 0,
            "tier_4_used": 0,
            "tier_4_total": 0,
            "tier_5_used": 0,
            "tier_5_total": 0,
            "gpus_total": 4,
            "gpus": 3,
            "gpus_idle": 1,
            "vgpus_total": 8,
            "vgpus": 6,
            "vgpus_idle": 2,
            "workload_datapoints": 1200,
            "storage_datapoints": 600,
        },
        {
            "$key": 1,
            "created": 1704067200,
            "from": 1704063600,
            "to": 1704067200,
            "description": "First billing record",
            "used_cores": 32,
            "total_cores": 64,
            "online_cores": 60,
            "total_nodes": 4,
            "online_nodes": 4,
            "running_machines": 25,
            "used_ram": 65536,
            "total_ram": 131072,
            "online_ram": 131072,
            "phys_ram_used": 68719476736,
            "phys_vram_used": 17179869184,
            "phys_total_cpu": 75,
            "tier_0_used": 107374182400,
            "tier_0_total": 1099511627776,
            "tier_1_used": 536870912000,
            "tier_1_total": 2199023255552,
            "tier_2_used": 0,
            "tier_2_total": 0,
            "tier_3_used": 0,
            "tier_3_total": 0,
            "tier_4_used": 0,
            "tier_4_total": 0,
            "tier_5_used": 0,
            "tier_5_total": 0,
            "gpus_total": 4,
            "gpus": 2,
            "gpus_idle": 2,
            "vgpus_total": 8,
            "vgpus": 4,
            "vgpus_idle": 4,
            "workload_datapoints": 1000,
            "storage_datapoints": 500,
        },
    ]


# =============================================================================
# BillingRecord Model Tests
# =============================================================================


class TestBillingRecord:
    """Tests for BillingRecord model."""

    def test_timestamp_properties(self, sample_billing_data: dict[str, Any]) -> None:
        """Test timestamp properties."""
        manager = MagicMock()
        record = BillingRecord(sample_billing_data, manager)

        assert record.created is not None
        assert record.created.year == 2024
        assert record.created.tzinfo == timezone.utc
        assert record.created_epoch == 1704067200

        assert record.from_time is not None
        assert record.from_epoch == 1704063600

        assert record.to_time is not None
        assert record.to_epoch == 1704067200

        assert record.sent is not None
        assert record.sent_epoch == 1704067201

    def test_timestamp_none(self) -> None:
        """Test timestamp properties when not set."""
        manager = MagicMock()
        record = BillingRecord({"$key": 1}, manager)

        assert record.created is None
        assert record.created_epoch == 0
        assert record.from_time is None
        assert record.to_time is None
        assert record.sent is None

    def test_description(self, sample_billing_data: dict[str, Any]) -> None:
        """Test description property."""
        manager = MagicMock()
        record = BillingRecord(sample_billing_data, manager)

        assert record.description == "Billing report for January"

    def test_cpu_metrics(self, sample_billing_data: dict[str, Any]) -> None:
        """Test CPU metrics."""
        manager = MagicMock()
        record = BillingRecord(sample_billing_data, manager)

        assert record.used_cores == 32
        assert record.total_cores == 64
        assert record.online_cores == 60
        assert record.phys_total_cpu == 75

    def test_node_metrics(self, sample_billing_data: dict[str, Any]) -> None:
        """Test node metrics."""
        manager = MagicMock()
        record = BillingRecord(sample_billing_data, manager)

        assert record.total_nodes == 4
        assert record.online_nodes == 4
        assert record.running_machines == 25

    def test_ram_metrics(self, sample_billing_data: dict[str, Any]) -> None:
        """Test RAM metrics."""
        manager = MagicMock()
        record = BillingRecord(sample_billing_data, manager)

        assert record.used_ram == 65536
        assert record.used_ram_gb == 64.0
        assert record.total_ram == 131072
        assert record.total_ram_gb == 128.0
        assert record.online_ram == 131072
        assert record.online_ram_gb == 128.0
        assert record.phys_ram_used == 68719476736
        assert record.phys_ram_used_gb == 64.0
        assert record.phys_vram_used == 17179869184
        assert record.phys_vram_used_gb == 16.0

    def test_storage_tier0_metrics(self, sample_billing_data: dict[str, Any]) -> None:
        """Test storage tier 0 metrics."""
        manager = MagicMock()
        record = BillingRecord(sample_billing_data, manager)

        assert record.tier0_used == 107374182400
        assert record.tier0_used_gb == pytest.approx(100.0, rel=0.01)
        assert record.tier0_total == 1099511627776
        assert record.tier0_total_gb == pytest.approx(1024.0, rel=0.01)

    def test_storage_tier1_metrics(self, sample_billing_data: dict[str, Any]) -> None:
        """Test storage tier 1 metrics."""
        manager = MagicMock()
        record = BillingRecord(sample_billing_data, manager)

        assert record.tier1_used == 536870912000
        assert record.tier1_used_gb == pytest.approx(500.0, rel=0.01)
        assert record.tier1_total == 2199023255552
        assert record.tier1_total_gb == pytest.approx(2048.0, rel=0.01)

    def test_storage_empty_tiers(self, sample_billing_data: dict[str, Any]) -> None:
        """Test empty storage tiers."""
        manager = MagicMock()
        record = BillingRecord(sample_billing_data, manager)

        for tier in [2, 3, 4, 5]:
            assert getattr(record, f"tier{tier}_used") == 0
            assert getattr(record, f"tier{tier}_used_gb") == 0.0
            assert getattr(record, f"tier{tier}_total") == 0
            assert getattr(record, f"tier{tier}_total_gb") == 0.0

    def test_gpu_metrics(self, sample_billing_data: dict[str, Any]) -> None:
        """Test GPU metrics."""
        manager = MagicMock()
        record = BillingRecord(sample_billing_data, manager)

        assert record.gpus_total == 4
        assert record.gpus_used == 2
        assert record.gpus_idle == 2
        assert record.vgpus_total == 8
        assert record.vgpus_used == 4
        assert record.vgpus_idle == 4

    def test_datapoint_counts(self, sample_billing_data: dict[str, Any]) -> None:
        """Test data point counts."""
        manager = MagicMock()
        record = BillingRecord(sample_billing_data, manager)

        assert record.workload_datapoints == 1000
        assert record.storage_datapoints == 500

    def test_get_tier_stats(self, sample_billing_data: dict[str, Any]) -> None:
        """Test get_tier_stats helper."""
        manager = MagicMock()
        record = BillingRecord(sample_billing_data, manager)

        tier0 = record.get_tier_stats(0)
        assert tier0["used"] == 107374182400
        assert tier0["used_gb"] == pytest.approx(100.0, rel=0.01)
        assert tier0["total"] == 1099511627776
        assert tier0["total_gb"] == pytest.approx(1024.0, rel=0.01)

        tier1 = record.get_tier_stats(1)
        assert tier1["used"] == 536870912000
        assert tier1["used_gb"] == pytest.approx(500.0, rel=0.01)

    def test_get_tier_stats_invalid(self, sample_billing_data: dict[str, Any]) -> None:
        """Test get_tier_stats with invalid tier."""
        manager = MagicMock()
        record = BillingRecord(sample_billing_data, manager)

        with pytest.raises(ValueError, match="Tier must be 0-5"):
            record.get_tier_stats(6)

        with pytest.raises(ValueError, match="Tier must be 0-5"):
            record.get_tier_stats(-1)

    def test_total_storage(self, sample_billing_data: dict[str, Any]) -> None:
        """Test total storage helpers."""
        manager = MagicMock()
        record = BillingRecord(sample_billing_data, manager)

        # Tier 0 (100 GB) + Tier 1 (500 GB) = 600 GB
        expected_used = 107374182400 + 536870912000
        assert record.total_storage_used == expected_used
        assert record.total_storage_used_gb == pytest.approx(600.0, rel=0.01)

        # Tier 0 (1 TB) + Tier 1 (2 TB) = 3 TB
        expected_total = 1099511627776 + 2199023255552
        assert record.total_storage_total == expected_total
        assert record.total_storage_total_gb == pytest.approx(3072.0, rel=0.01)

    def test_cpu_utilization(self, sample_billing_data: dict[str, Any]) -> None:
        """Test CPU utilization percentage."""
        manager = MagicMock()
        record = BillingRecord(sample_billing_data, manager)

        # 32 / 64 = 50%
        assert record.cpu_utilization_pct == 50.0

    def test_cpu_utilization_zero_total(self) -> None:
        """Test CPU utilization when total is zero."""
        manager = MagicMock()
        record = BillingRecord({"$key": 1, "used_cores": 0, "total_cores": 0}, manager)

        assert record.cpu_utilization_pct == 0.0

    def test_ram_utilization(self, sample_billing_data: dict[str, Any]) -> None:
        """Test RAM utilization percentage."""
        manager = MagicMock()
        record = BillingRecord(sample_billing_data, manager)

        # 65536 / 131072 = 50%
        assert record.ram_utilization_pct == 50.0

    def test_ram_utilization_zero_total(self) -> None:
        """Test RAM utilization when total is zero."""
        manager = MagicMock()
        record = BillingRecord({"$key": 1, "used_ram": 0, "total_ram": 0}, manager)

        assert record.ram_utilization_pct == 0.0

    def test_gpu_utilization(self, sample_billing_data: dict[str, Any]) -> None:
        """Test GPU utilization percentage."""
        manager = MagicMock()
        record = BillingRecord(sample_billing_data, manager)

        # 2 / 4 = 50%
        assert record.gpu_utilization_pct == 50.0

    def test_gpu_utilization_zero_total(self) -> None:
        """Test GPU utilization when total is zero."""
        manager = MagicMock()
        record = BillingRecord({"$key": 1, "gpus": 0, "gpus_total": 0}, manager)

        assert record.gpu_utilization_pct == 0.0

    def test_vgpu_utilization(self, sample_billing_data: dict[str, Any]) -> None:
        """Test vGPU utilization percentage."""
        manager = MagicMock()
        record = BillingRecord(sample_billing_data, manager)

        # 4 / 8 = 50%
        assert record.vgpu_utilization_pct == 50.0

    def test_vgpu_utilization_zero_total(self) -> None:
        """Test vGPU utilization when total is zero."""
        manager = MagicMock()
        record = BillingRecord({"$key": 1, "vgpus": 0, "vgpus_total": 0}, manager)

        assert record.vgpu_utilization_pct == 0.0

    def test_repr(self, sample_billing_data: dict[str, Any]) -> None:
        """Test repr."""
        manager = MagicMock()
        record = BillingRecord(sample_billing_data, manager)

        repr_str = repr(record)
        assert "BillingRecord" in repr_str
        assert "cores=32/64" in repr_str
        assert "ram=64.0/128.0GB" in repr_str


# =============================================================================
# BillingManager Tests
# =============================================================================


class TestBillingManager:
    """Tests for BillingManager."""

    def test_list_records(
        self,
        mock_client: MagicMock,
        sample_billing_list: list[dict[str, Any]],
    ) -> None:
        """Test listing billing records."""
        mock_client._request.return_value = sample_billing_list
        manager = BillingManager(mock_client)

        records = manager.list()

        assert len(records) == 2
        mock_client._request.assert_called_once()
        call_args = mock_client._request.call_args
        assert call_args[0][0] == "GET"
        assert call_args[0][1] == "billing"
        assert "-created" in call_args[1]["params"]["sort"]

    def test_list_with_limit(self, mock_client: MagicMock) -> None:
        """Test listing with limit."""
        mock_client._request.return_value = []
        manager = BillingManager(mock_client)

        manager.list(limit=10)

        call_args = mock_client._request.call_args
        assert call_args[1]["params"]["limit"] == 10

    def test_list_with_offset(self, mock_client: MagicMock) -> None:
        """Test listing with offset."""
        mock_client._request.return_value = []
        manager = BillingManager(mock_client)

        manager.list(offset=5)

        call_args = mock_client._request.call_args
        assert call_args[1]["params"]["offset"] == 5

    def test_list_with_datetime_filter(
        self,
        mock_client: MagicMock,
        sample_billing_list: list[dict[str, Any]],
    ) -> None:
        """Test listing with datetime filter."""
        mock_client._request.return_value = sample_billing_list
        manager = BillingManager(mock_client)

        since = datetime(2024, 1, 1, tzinfo=timezone.utc)
        until = datetime(2024, 1, 31, tzinfo=timezone.utc)
        manager.list(since=since, until=until)

        call_args = mock_client._request.call_args
        filter_str = call_args[1]["params"]["filter"]
        assert "created ge" in filter_str
        assert "created le" in filter_str

    def test_list_with_epoch_filter(
        self,
        mock_client: MagicMock,
        sample_billing_list: list[dict[str, Any]],
    ) -> None:
        """Test listing with epoch timestamp filter."""
        mock_client._request.return_value = sample_billing_list
        manager = BillingManager(mock_client)

        manager.list(since=1704067200, until=1704153600)

        call_args = mock_client._request.call_args
        filter_str = call_args[1]["params"]["filter"]
        assert "created ge 1704067200" in filter_str
        assert "created le 1704153600" in filter_str

    def test_list_with_custom_filter(
        self,
        mock_client: MagicMock,
        sample_billing_list: list[dict[str, Any]],
    ) -> None:
        """Test listing with custom filter string."""
        mock_client._request.return_value = sample_billing_list
        manager = BillingManager(mock_client)

        manager.list(filter="used_cores gt 30")

        call_args = mock_client._request.call_args
        filter_str = call_args[1]["params"]["filter"]
        assert "used_cores gt 30" in filter_str

    def test_list_empty_response(self, mock_client: MagicMock) -> None:
        """Test listing with empty response."""
        mock_client._request.return_value = None
        manager = BillingManager(mock_client)

        records = manager.list()

        assert records == []

    def test_list_single_response(
        self,
        mock_client: MagicMock,
        sample_billing_data: dict[str, Any],
    ) -> None:
        """Test listing when API returns single dict instead of list."""
        mock_client._request.return_value = sample_billing_data
        manager = BillingManager(mock_client)

        records = manager.list()

        assert len(records) == 1
        assert records[0].used_cores == 32

    def test_get_record(
        self,
        mock_client: MagicMock,
        sample_billing_data: dict[str, Any],
    ) -> None:
        """Test getting a specific record by key."""
        mock_client._request.return_value = sample_billing_data
        manager = BillingManager(mock_client)

        record = manager.get(key=1)

        assert record.used_cores == 32
        mock_client._request.assert_called_once()
        call_args = mock_client._request.call_args
        assert call_args[0][0] == "GET"
        assert call_args[0][1] == "billing/1"

    def test_get_record_not_found(self, mock_client: MagicMock) -> None:
        """Test getting a record that doesn't exist."""
        mock_client._request.return_value = None
        manager = BillingManager(mock_client)

        with pytest.raises(NotFoundError):
            manager.get(key=999)

    def test_get_record_invalid_response(self, mock_client: MagicMock) -> None:
        """Test getting a record with invalid response."""
        mock_client._request.return_value = "invalid"
        manager = BillingManager(mock_client)

        with pytest.raises(NotFoundError):
            manager.get(key=1)

    def test_get_record_key_required(self, mock_client: MagicMock) -> None:
        """Test that key is required for get."""
        manager = BillingManager(mock_client)

        with pytest.raises(ValueError, match="key must be provided"):
            manager.get()

    def test_get_latest(
        self,
        mock_client: MagicMock,
        sample_billing_list: list[dict[str, Any]],
    ) -> None:
        """Test getting the latest record."""
        mock_client._request.return_value = [sample_billing_list[0]]
        manager = BillingManager(mock_client)

        record = manager.get_latest()

        assert record.used_cores == 40
        call_args = mock_client._request.call_args
        assert call_args[1]["params"]["limit"] == 1

    def test_get_latest_not_found(self, mock_client: MagicMock) -> None:
        """Test getting latest when no records exist."""
        mock_client._request.return_value = []
        manager = BillingManager(mock_client)

        with pytest.raises(NotFoundError, match="No billing records found"):
            manager.get_latest()

    def test_generate(self, mock_client: MagicMock) -> None:
        """Test generating a new billing report."""
        mock_client._request.return_value = {"status": "generated"}
        manager = BillingManager(mock_client)

        result = manager.generate()

        assert result == {"status": "generated"}
        mock_client._request.assert_called_once()
        call_args = mock_client._request.call_args
        assert call_args[0][0] == "POST"
        assert call_args[0][1] == "billing_actions"
        assert call_args[1]["json_data"]["action"] == "generate"

    def test_generate_no_response(self, mock_client: MagicMock) -> None:
        """Test generating when no response body."""
        mock_client._request.return_value = None
        manager = BillingManager(mock_client)

        result = manager.generate()

        assert result is None

    def test_get_summary(
        self,
        mock_client: MagicMock,
        sample_billing_list: list[dict[str, Any]],
    ) -> None:
        """Test getting a summary of billing data."""
        mock_client._request.return_value = sample_billing_list
        manager = BillingManager(mock_client)

        summary = manager.get_summary()

        assert summary["record_count"] == 2
        assert summary["avg_cpu_utilization"] == pytest.approx(56.25, rel=0.01)
        assert summary["peak_cpu_cores"] == 40
        assert summary["avg_ram_utilization"] == pytest.approx(56.25, rel=0.01)
        assert summary["peak_ram_gb"] == 80.0
        assert summary["total_gpus"] == 4
        assert summary["avg_gpus_used"] == 2.5
        assert summary["total_vgpus"] == 8
        assert summary["avg_vgpus_used"] == 5.0

    def test_get_summary_with_time_range(
        self,
        mock_client: MagicMock,
        sample_billing_list: list[dict[str, Any]],
    ) -> None:
        """Test getting summary with time range."""
        mock_client._request.return_value = sample_billing_list
        manager = BillingManager(mock_client)

        since = datetime.now(timezone.utc) - timedelta(days=30)
        summary = manager.get_summary(since=since)

        assert summary["record_count"] == 2

    def test_get_summary_empty(self, mock_client: MagicMock) -> None:
        """Test getting summary with no records."""
        mock_client._request.return_value = []
        manager = BillingManager(mock_client)

        summary = manager.get_summary()

        assert summary["record_count"] == 0
        assert summary["avg_cpu_utilization"] == 0.0
        assert summary["peak_cpu_cores"] == 0
        assert summary["avg_ram_utilization"] == 0.0
        assert summary["peak_ram_gb"] == 0.0
        assert summary["avg_storage_used_gb"] == 0.0
        assert summary["peak_storage_used_gb"] == 0.0
        assert summary["total_gpus"] == 0
        assert summary["avg_gpus_used"] == 0.0
        assert summary["total_vgpus"] == 0
        assert summary["avg_vgpus_used"] == 0.0


# =============================================================================
# Client Integration Tests
# =============================================================================


class TestClientIntegration:
    """Tests for VergeClient integration with billing."""

    def test_manager_creation(self, mock_client: MagicMock) -> None:
        """Test creating a billing manager."""
        manager = BillingManager(mock_client)
        assert isinstance(manager, BillingManager)
        assert manager._endpoint == "billing"
