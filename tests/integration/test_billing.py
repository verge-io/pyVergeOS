"""Integration tests for billing resource manager."""

from datetime import datetime, timedelta, timezone

import pytest

from pyvergeos import VergeClient
from pyvergeos.resources.billing import BillingManager, BillingRecord


@pytest.mark.integration
class TestBillingRecords:
    """Integration tests for BillingRecord and BillingManager."""

    def test_list_billing_records(self, live_client: VergeClient) -> None:
        """Test listing billing records."""
        records = live_client.billing.list(limit=10)

        assert isinstance(records, list)
        # Billing records may not exist on all systems
        if records:
            assert all(isinstance(r, BillingRecord) for r in records)

    def test_list_billing_records_with_limit(self, live_client: VergeClient) -> None:
        """Test listing billing records with limit."""
        records = live_client.billing.list(limit=5)

        assert isinstance(records, list)
        assert len(records) <= 5

    def test_list_billing_records_sorted_by_created(self, live_client: VergeClient) -> None:
        """Test that billing records are sorted by created descending."""
        records = live_client.billing.list(limit=10)

        if len(records) >= 2:
            # Check that records are in descending order
            for i in range(len(records) - 1):
                if records[i].created and records[i + 1].created:
                    assert records[i].created >= records[i + 1].created

    def test_get_billing_record_by_key(self, live_client: VergeClient) -> None:
        """Test getting a specific billing record by key."""
        records = live_client.billing.list(limit=1)
        if not records:
            pytest.skip("No billing records available")

        record = live_client.billing.get(key=records[0].key)

        assert isinstance(record, BillingRecord)
        assert record.key == records[0].key

    def test_get_latest_billing_record(self, live_client: VergeClient) -> None:
        """Test getting the latest billing record."""
        records = live_client.billing.list(limit=1)
        if not records:
            pytest.skip("No billing records available")

        latest = live_client.billing.get_latest()

        assert isinstance(latest, BillingRecord)
        # Should be the same as the first record from list
        assert latest.key == records[0].key

    def test_billing_record_timestamp_properties(self, live_client: VergeClient) -> None:
        """Test billing record timestamp properties."""
        records = live_client.billing.list(limit=1)
        if not records:
            pytest.skip("No billing records available")

        record = records[0]

        # Check created timestamp
        if record.created:
            assert isinstance(record.created, datetime)
            assert record.created.tzinfo == timezone.utc
            assert record.created_epoch > 0

        # Check from/to timestamps if present
        if record.from_time:
            assert isinstance(record.from_time, datetime)
            assert record.from_epoch > 0

        if record.to_time:
            assert isinstance(record.to_time, datetime)
            assert record.to_epoch > 0

    def test_billing_record_cpu_metrics(self, live_client: VergeClient) -> None:
        """Test billing record CPU metrics."""
        records = live_client.billing.list(limit=1)
        if not records:
            pytest.skip("No billing records available")

        record = records[0]

        # CPU metrics should be non-negative
        assert record.used_cores >= 0
        assert record.total_cores >= 0
        assert record.online_cores >= 0

        # Used should not exceed total
        assert record.used_cores <= record.total_cores

        # Utilization should be between 0 and 100
        assert 0.0 <= record.cpu_utilization_pct <= 100.0

    def test_billing_record_ram_metrics(self, live_client: VergeClient) -> None:
        """Test billing record RAM metrics."""
        records = live_client.billing.list(limit=1)
        if not records:
            pytest.skip("No billing records available")

        record = records[0]

        # RAM metrics should be non-negative
        assert record.used_ram >= 0
        assert record.total_ram >= 0
        assert record.online_ram >= 0

        # GB conversion should be positive
        assert record.used_ram_gb >= 0.0
        assert record.total_ram_gb >= 0.0
        assert record.online_ram_gb >= 0.0

        # Used should not exceed total
        assert record.used_ram <= record.total_ram

        # Utilization should be between 0 and 100
        assert 0.0 <= record.ram_utilization_pct <= 100.0

    def test_billing_record_storage_metrics(self, live_client: VergeClient) -> None:
        """Test billing record storage tier metrics."""
        records = live_client.billing.list(limit=1)
        if not records:
            pytest.skip("No billing records available")

        record = records[0]

        # Test each tier (0-5)
        for tier in range(6):
            tier_stats = record.get_tier_stats(tier)
            assert "used" in tier_stats
            assert "used_gb" in tier_stats
            assert "total" in tier_stats
            assert "total_gb" in tier_stats

            assert tier_stats["used"] >= 0
            assert tier_stats["total"] >= 0

    def test_billing_record_total_storage(self, live_client: VergeClient) -> None:
        """Test billing record total storage calculation."""
        records = live_client.billing.list(limit=1)
        if not records:
            pytest.skip("No billing records available")

        record = records[0]

        # Total storage should be sum of all tiers
        expected_used = sum(getattr(record, f"tier{i}_used") for i in range(6))
        assert record.total_storage_used == expected_used

        expected_total = sum(getattr(record, f"tier{i}_total") for i in range(6))
        assert record.total_storage_total == expected_total

    def test_billing_record_gpu_metrics(self, live_client: VergeClient) -> None:
        """Test billing record GPU metrics."""
        records = live_client.billing.list(limit=1)
        if not records:
            pytest.skip("No billing records available")

        record = records[0]

        # GPU metrics should be non-negative
        assert record.gpus_total >= 0
        assert record.gpus_used >= 0
        assert record.gpus_idle >= 0
        assert record.vgpus_total >= 0
        assert record.vgpus_used >= 0
        assert record.vgpus_idle >= 0

        # Utilization should be between 0 and 100
        assert 0.0 <= record.gpu_utilization_pct <= 100.0
        assert 0.0 <= record.vgpu_utilization_pct <= 100.0

    def test_billing_record_node_metrics(self, live_client: VergeClient) -> None:
        """Test billing record node metrics."""
        records = live_client.billing.list(limit=1)
        if not records:
            pytest.skip("No billing records available")

        record = records[0]

        # Node metrics should be non-negative
        assert record.total_nodes >= 0
        assert record.online_nodes >= 0
        assert record.running_machines >= 0

        # Online should not exceed total
        assert record.online_nodes <= record.total_nodes


@pytest.mark.integration
class TestBillingFiltering:
    """Integration tests for billing record filtering."""

    def test_filter_billing_by_time_range(self, live_client: VergeClient) -> None:
        """Test filtering billing records by time range."""
        # Get records from the last 30 days
        since = datetime.now(tz=timezone.utc) - timedelta(days=30)
        records = live_client.billing.list(since=since, limit=100)

        assert isinstance(records, list)
        # All records should be after 'since'
        for record in records:
            if record.created:
                assert record.created >= since

    def test_filter_billing_with_until(self, live_client: VergeClient) -> None:
        """Test filtering billing records with until parameter."""
        until = datetime.now(tz=timezone.utc)
        records = live_client.billing.list(until=until, limit=10)

        assert isinstance(records, list)
        for record in records:
            if record.created:
                assert record.created <= until

    def test_filter_billing_with_epoch(self, live_client: VergeClient) -> None:
        """Test filtering billing records with epoch timestamps."""
        now = datetime.now(tz=timezone.utc)
        since_epoch = int((now - timedelta(days=7)).timestamp())
        until_epoch = int(now.timestamp())

        records = live_client.billing.list(since=since_epoch, until=until_epoch, limit=100)

        assert isinstance(records, list)


@pytest.mark.integration
class TestBillingSummary:
    """Integration tests for billing summary functionality."""

    def test_get_billing_summary(self, live_client: VergeClient) -> None:
        """Test getting billing summary."""
        summary = live_client.billing.get_summary()

        assert isinstance(summary, dict)
        assert "record_count" in summary
        assert "avg_cpu_utilization" in summary
        assert "peak_cpu_cores" in summary
        assert "avg_ram_utilization" in summary
        assert "peak_ram_gb" in summary
        assert "avg_storage_used_gb" in summary
        assert "peak_storage_used_gb" in summary
        assert "total_gpus" in summary
        assert "avg_gpus_used" in summary
        assert "total_vgpus" in summary
        assert "avg_vgpus_used" in summary

    def test_get_billing_summary_with_time_range(self, live_client: VergeClient) -> None:
        """Test getting billing summary with time range."""
        since = datetime.now(tz=timezone.utc) - timedelta(days=7)
        summary = live_client.billing.get_summary(since=since)

        assert isinstance(summary, dict)
        assert summary["record_count"] >= 0

    def test_get_billing_summary_values(self, live_client: VergeClient) -> None:
        """Test that billing summary values are valid."""
        summary = live_client.billing.get_summary()

        # All numeric values should be non-negative
        assert summary["record_count"] >= 0
        assert summary["avg_cpu_utilization"] >= 0.0
        assert summary["peak_cpu_cores"] >= 0
        assert summary["avg_ram_utilization"] >= 0.0
        assert summary["peak_ram_gb"] >= 0.0
        assert summary["avg_storage_used_gb"] >= 0.0
        assert summary["peak_storage_used_gb"] >= 0.0
        assert summary["total_gpus"] >= 0
        assert summary["avg_gpus_used"] >= 0.0
        assert summary["total_vgpus"] >= 0
        assert summary["avg_vgpus_used"] >= 0.0


@pytest.mark.integration
class TestBillingGenerate:
    """Integration tests for billing report generation."""

    def test_generate_billing_report(self, live_client: VergeClient) -> None:
        """Test generating a billing report.

        Note: This actually triggers billing report generation on the system.
        Use with caution in production environments.
        """
        # This test may fail if billing generation is not enabled or
        # if the user doesn't have permission
        try:
            result = live_client.billing.generate()
            # Result might be None or a dict depending on API response
            assert result is None or isinstance(result, dict)
        except Exception:
            # Billing generation might not be available on all systems
            pytest.skip("Billing generation not available or not permitted")


@pytest.mark.integration
class TestBillingManagerAccess:
    """Integration tests for accessing billing manager via client."""

    def test_client_has_billing_property(self, live_client: VergeClient) -> None:
        """Test that client has billing property."""
        assert hasattr(live_client, "billing")
        assert isinstance(live_client.billing, BillingManager)

    def test_billing_manager_endpoint(self, live_client: VergeClient) -> None:
        """Test billing manager endpoint is correct."""
        assert live_client.billing._endpoint == "billing"
