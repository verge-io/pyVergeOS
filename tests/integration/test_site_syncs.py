"""Integration tests for Site Sync operations.

These tests require a live VergeOS system and will be skipped
if the environment variables are not set.

Note: Site sync tests are limited because creating/modifying syncs
requires remote site connectivity and specific infrastructure.
These tests focus on read operations.
"""

from __future__ import annotations

import pytest

from pyvergeos import VergeClient
from pyvergeos.exceptions import NotFoundError


@pytest.mark.integration
class TestSiteSyncOutgoingListIntegration:
    """Integration tests for SiteSyncOutgoingManager.list()."""

    def test_list_outgoing_syncs(self, live_client: VergeClient) -> None:
        """Test listing outgoing syncs from live system."""
        syncs = live_client.site_syncs.list()

        assert isinstance(syncs, list)
        # May or may not have syncs configured

    def test_list_outgoing_syncs_with_limit(self, live_client: VergeClient) -> None:
        """Test listing outgoing syncs with limit."""
        syncs = live_client.site_syncs.list(limit=1)

        assert isinstance(syncs, list)
        assert len(syncs) <= 1

    def test_list_enabled_syncs(self, live_client: VergeClient) -> None:
        """Test listing only enabled syncs."""
        syncs = live_client.site_syncs.list_enabled()

        assert isinstance(syncs, list)
        for sync in syncs:
            assert sync.is_enabled is True

    def test_list_disabled_syncs(self, live_client: VergeClient) -> None:
        """Test listing only disabled syncs."""
        syncs = live_client.site_syncs.list_disabled()

        assert isinstance(syncs, list)
        for sync in syncs:
            assert sync.is_enabled is False


@pytest.mark.integration
class TestSiteSyncOutgoingGetIntegration:
    """Integration tests for SiteSyncOutgoingManager.get()."""

    def test_get_outgoing_sync_by_key(self, live_client: VergeClient) -> None:
        """Test getting an outgoing sync by key."""
        syncs = live_client.site_syncs.list()
        if not syncs:
            pytest.skip("No outgoing syncs found on system")

        sync = live_client.site_syncs.get(syncs[0].key)

        assert sync.key == syncs[0].key
        assert sync.name == syncs[0].name

    def test_get_outgoing_sync_by_name(self, live_client: VergeClient) -> None:
        """Test getting an outgoing sync by name."""
        syncs = live_client.site_syncs.list()
        if not syncs:
            pytest.skip("No outgoing syncs found on system")

        sync = live_client.site_syncs.get(name=syncs[0].name)

        assert sync.name == syncs[0].name
        assert sync.key == syncs[0].key

    def test_get_nonexistent_sync(self, live_client: VergeClient) -> None:
        """Test that NotFoundError is raised for nonexistent sync."""
        with pytest.raises(NotFoundError):
            live_client.site_syncs.get(999999)


@pytest.mark.integration
class TestSiteSyncOutgoingPropertiesIntegration:
    """Integration tests for SiteSyncOutgoing property accessors."""

    def test_outgoing_sync_properties(self, live_client: VergeClient) -> None:
        """Test outgoing sync property accessors on live data."""
        syncs = live_client.site_syncs.list()
        if not syncs:
            pytest.skip("No outgoing syncs found on system")

        sync = syncs[0]

        # Test all properties are accessible
        _ = sync.key
        _ = sync.name
        _ = sync.description
        _ = sync.site_key
        _ = sync.is_enabled
        _ = sync.status
        _ = sync.status_info
        _ = sync.state
        _ = sync.is_syncing
        _ = sync.is_online
        _ = sync.has_error
        _ = sync.url
        _ = sync.has_encryption
        _ = sync.has_compression
        _ = sync.has_network_integrity
        _ = sync.data_threads
        _ = sync.file_threads
        _ = sync.send_throttle
        _ = sync.destination_tier
        _ = sync.queue_retry_count
        _ = sync.queue_retry_interval
        _ = sync.has_retry_multiplier
        _ = sync.last_run_at
        _ = sync.remote_min_snapshots
        _ = sync.note

    def test_outgoing_sync_repr(self, live_client: VergeClient) -> None:
        """Test outgoing sync string representation."""
        syncs = live_client.site_syncs.list()
        if not syncs:
            pytest.skip("No outgoing syncs found on system")

        sync = syncs[0]
        repr_str = repr(sync)

        assert "SiteSyncOutgoing" in repr_str
        assert sync.name in repr_str


@pytest.mark.integration
class TestSiteSyncIncomingListIntegration:
    """Integration tests for SiteSyncIncomingManager.list()."""

    def test_list_incoming_syncs(self, live_client: VergeClient) -> None:
        """Test listing incoming syncs from live system."""
        syncs = live_client.site_syncs_incoming.list()

        assert isinstance(syncs, list)
        # May or may not have syncs configured

    def test_list_incoming_syncs_with_limit(self, live_client: VergeClient) -> None:
        """Test listing incoming syncs with limit."""
        syncs = live_client.site_syncs_incoming.list(limit=1)

        assert isinstance(syncs, list)
        assert len(syncs) <= 1


@pytest.mark.integration
class TestSiteSyncIncomingGetIntegration:
    """Integration tests for SiteSyncIncomingManager.get()."""

    def test_get_incoming_sync_by_key(self, live_client: VergeClient) -> None:
        """Test getting an incoming sync by key."""
        syncs = live_client.site_syncs_incoming.list()
        if not syncs:
            pytest.skip("No incoming syncs found on system")

        sync = live_client.site_syncs_incoming.get(syncs[0].key)

        assert sync.key == syncs[0].key
        assert sync.name == syncs[0].name

    def test_get_incoming_sync_by_name(self, live_client: VergeClient) -> None:
        """Test getting an incoming sync by name."""
        syncs = live_client.site_syncs_incoming.list()
        if not syncs:
            pytest.skip("No incoming syncs found on system")

        sync = live_client.site_syncs_incoming.get(name=syncs[0].name)

        assert sync.name == syncs[0].name
        assert sync.key == syncs[0].key


@pytest.mark.integration
class TestSiteSyncIncomingPropertiesIntegration:
    """Integration tests for SiteSyncIncoming property accessors."""

    def test_incoming_sync_properties(self, live_client: VergeClient) -> None:
        """Test incoming sync property accessors on live data."""
        syncs = live_client.site_syncs_incoming.list()
        if not syncs:
            pytest.skip("No incoming syncs found on system")

        sync = syncs[0]

        # Test all properties are accessible
        _ = sync.key
        _ = sync.name
        _ = sync.description
        _ = sync.site_key
        _ = sync.is_enabled
        _ = sync.status
        _ = sync.status_info
        _ = sync.state
        _ = sync.is_syncing
        _ = sync.is_online
        _ = sync.has_error
        _ = sync.sync_id
        _ = sync.registration_code
        _ = sync.public_ip
        _ = sync.force_tier
        _ = sync.min_snapshots
        _ = sync.last_sync_at
        _ = sync.vsan_host
        _ = sync.vsan_port
        _ = sync.request_url
        _ = sync.is_system_created

    def test_incoming_sync_repr(self, live_client: VergeClient) -> None:
        """Test incoming sync string representation."""
        syncs = live_client.site_syncs_incoming.list()
        if not syncs:
            pytest.skip("No incoming syncs found on system")

        sync = syncs[0]
        repr_str = repr(sync)

        assert "SiteSyncIncoming" in repr_str
        assert sync.name in repr_str


@pytest.mark.integration
class TestSiteSyncScheduleListIntegration:
    """Integration tests for SiteSyncScheduleManager.list()."""

    def test_list_schedules(self, live_client: VergeClient) -> None:
        """Test listing sync schedules from live system."""
        schedules = live_client.site_sync_schedules.list()

        assert isinstance(schedules, list)
        # May or may not have schedules configured

    def test_list_schedules_for_sync(self, live_client: VergeClient) -> None:
        """Test listing schedules for a specific sync."""
        syncs = live_client.site_syncs.list()
        if not syncs:
            pytest.skip("No outgoing syncs found on system")

        schedules = live_client.site_sync_schedules.list_for_sync(sync_key=syncs[0].key)

        assert isinstance(schedules, list)
        for schedule in schedules:
            assert schedule.sync_key == syncs[0].key


@pytest.mark.integration
class TestSiteSyncSchedulePropertiesIntegration:
    """Integration tests for SiteSyncSchedule property accessors."""

    def test_schedule_properties(self, live_client: VergeClient) -> None:
        """Test schedule property accessors on live data."""
        schedules = live_client.site_sync_schedules.list()
        if not schedules:
            pytest.skip("No sync schedules found on system")

        schedule = schedules[0]

        # Test all properties are accessible
        _ = schedule.key
        _ = schedule.sync_key
        _ = schedule.profile_period_key
        _ = schedule.retention
        _ = schedule.retention_timedelta
        _ = schedule.priority
        _ = schedule.do_not_expire
        _ = schedule.destination_prefix

    def test_schedule_repr(self, live_client: VergeClient) -> None:
        """Test schedule string representation."""
        schedules = live_client.site_sync_schedules.list()
        if not schedules:
            pytest.skip("No sync schedules found on system")

        schedule = schedules[0]
        repr_str = repr(schedule)

        assert "SiteSyncSchedule" in repr_str
