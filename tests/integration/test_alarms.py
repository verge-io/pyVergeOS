"""Integration tests for Alarm operations.

These tests require a live VergeOS system and will be skipped
if the environment variables are not set.
"""

from __future__ import annotations

import pytest

from pyvergeos import VergeClient
from pyvergeos.exceptions import NotFoundError


@pytest.mark.integration
class TestAlarmListIntegration:
    """Integration tests for AlarmManager list operations."""

    def test_list_alarms(self, live_client: VergeClient) -> None:
        """Test listing alarms from live system."""
        alarms = live_client.alarms.list()

        # Should return a list (may be empty)
        assert isinstance(alarms, list)

        # Each alarm should have expected properties
        for alarm in alarms:
            assert hasattr(alarm, "key")
            assert hasattr(alarm, "level")
            assert hasattr(alarm, "status")
            assert hasattr(alarm, "is_snoozed")
            assert hasattr(alarm, "is_resolvable")

    def test_list_alarms_include_snoozed(self, live_client: VergeClient) -> None:
        """Test listing alarms including snoozed."""
        alarms = live_client.alarms.list(include_snoozed=True)

        assert isinstance(alarms, list)

    def test_list_critical_alarms(self, live_client: VergeClient) -> None:
        """Test listing critical alarms."""
        alarms = live_client.alarms.list_critical()

        assert isinstance(alarms, list)
        for alarm in alarms:
            assert alarm.level == "critical"

    def test_list_error_alarms(self, live_client: VergeClient) -> None:
        """Test listing error alarms."""
        alarms = live_client.alarms.list_errors()

        assert isinstance(alarms, list)
        for alarm in alarms:
            assert alarm.level == "error"

    def test_list_warning_alarms(self, live_client: VergeClient) -> None:
        """Test listing warning alarms."""
        alarms = live_client.alarms.list_warnings()

        assert isinstance(alarms, list)
        for alarm in alarms:
            assert alarm.level == "warning"

    def test_list_alarms_by_level_filter(self, live_client: VergeClient) -> None:
        """Test listing alarms with level filter."""
        # Test single level
        alarms = live_client.alarms.list(level="warning")
        for alarm in alarms:
            assert alarm.level == "warning"

        # Test multiple levels
        alarms = live_client.alarms.list(level=["critical", "error"])
        for alarm in alarms:
            assert alarm.level in ["critical", "error"]

    def test_list_alarms_by_owner_type(self, live_client: VergeClient) -> None:
        """Test listing alarms by owner type."""
        # Test VM alarms
        vm_alarms = live_client.alarms.list_by_owner_type("VM")
        for alarm in vm_alarms:
            assert alarm.owner_type == "vms"

        # Test Network alarms
        network_alarms = live_client.alarms.list_by_owner_type("Network")
        for alarm in network_alarms:
            assert alarm.owner_type == "vnets"

    def test_list_alarms_with_limit(self, live_client: VergeClient) -> None:
        """Test listing alarms with limit."""
        all_alarms = live_client.alarms.list(include_snoozed=True)
        if len(all_alarms) < 2:
            pytest.skip("Need at least 2 alarms to test limit")

        limited_alarms = live_client.alarms.list(limit=1, include_snoozed=True)
        assert len(limited_alarms) == 1


@pytest.mark.integration
class TestAlarmGetIntegration:
    """Integration tests for AlarmManager get operations."""

    def test_get_alarm_by_key(self, live_client: VergeClient) -> None:
        """Test getting an alarm by key."""
        alarms = live_client.alarms.list(include_snoozed=True)
        if not alarms:
            pytest.skip("No alarms available")

        alarm = live_client.alarms.get(alarms[0].key)

        assert alarm.key == alarms[0].key
        assert alarm.level == alarms[0].level

    def test_get_nonexistent_alarm(self, live_client: VergeClient) -> None:
        """Test that NotFoundError is raised for nonexistent alarm."""
        with pytest.raises(NotFoundError):
            live_client.alarms.get(999999)


@pytest.mark.integration
class TestAlarmPropertiesIntegration:
    """Integration tests for Alarm properties."""

    def test_alarm_properties(self, live_client: VergeClient) -> None:
        """Test Alarm property accessors on live data."""
        alarms = live_client.alarms.list(include_snoozed=True)
        if not alarms:
            pytest.skip("No alarms available")

        alarm = alarms[0]

        # All alarms should have these properties accessible
        assert alarm.key is not None
        assert alarm.level is not None
        assert alarm.level_display is not None
        assert alarm.status is not None
        assert isinstance(alarm.is_snoozed, bool)
        assert isinstance(alarm.is_resolvable, bool)

        # Owner type display should be mapped
        if alarm.owner_type:
            assert alarm.owner_type_display is not None

    def test_alarm_level_display_mapping(self, live_client: VergeClient) -> None:
        """Test that level_display is properly capitalized."""
        alarms = live_client.alarms.list(include_snoozed=True)
        if not alarms:
            pytest.skip("No alarms available")

        for alarm in alarms:
            # level_display should be capitalized version of level
            assert alarm.level_display == alarm.level.capitalize()


@pytest.mark.integration
class TestAlarmSnoozeIntegration:
    """Integration tests for alarm snooze operations."""

    def test_snooze_and_unsnooze_alarm(self, live_client: VergeClient) -> None:
        """Test snoozing and unsnoozing an alarm."""
        alarms = live_client.alarms.list(include_snoozed=True)
        if not alarms:
            pytest.skip("No alarms available")

        # Find an alarm that isn't snoozed or use any available
        alarm = alarms[0]
        original_snoozed = alarm.is_snoozed

        try:
            # Snooze the alarm for 1 hour
            snoozed_alarm = live_client.alarms.snooze(alarm.key, hours=1)
            assert snoozed_alarm.is_snoozed is True
            assert snoozed_alarm.snooze_until is not None

            # Verify via fresh get
            alarm_after_snooze = live_client.alarms.get(alarm.key)
            assert alarm_after_snooze.is_snoozed is True

            # Unsnooze the alarm
            unsnoozed_alarm = live_client.alarms.unsnooze(alarm.key)
            assert unsnoozed_alarm.is_snoozed is False

            # Verify via fresh get
            alarm_after_unsnooze = live_client.alarms.get(alarm.key)
            assert alarm_after_unsnooze.is_snoozed is False

        finally:
            # Restore original state if it was snoozed
            if original_snoozed:
                live_client.alarms.snooze(alarm.key, hours=1)
            else:
                live_client.alarms.unsnooze(alarm.key)

    def test_alarm_object_snooze_unsnooze(self, live_client: VergeClient) -> None:
        """Test snooze/unsnooze via Alarm object methods."""
        alarms = live_client.alarms.list(include_snoozed=True)
        if not alarms:
            pytest.skip("No alarms available")

        alarm = alarms[0]
        original_snoozed = alarm.is_snoozed

        try:
            # Snooze via object method
            snoozed = alarm.snooze(hours=1)
            assert snoozed.is_snoozed is True

            # Unsnooze via object method
            unsnoozed = snoozed.unsnooze()
            assert unsnoozed.is_snoozed is False

        finally:
            # Restore original state
            if original_snoozed:
                live_client.alarms.snooze(alarm.key, hours=1)
            else:
                live_client.alarms.unsnooze(alarm.key)


@pytest.mark.integration
class TestAlarmHistoryIntegration:
    """Integration tests for alarm history operations."""

    def test_list_history(self, live_client: VergeClient) -> None:
        """Test listing alarm history from live system."""
        history = live_client.alarms.list_history()

        # Should return a list (may be empty)
        assert isinstance(history, list)

        # Each history entry should have expected properties
        for entry in history:
            assert hasattr(entry, "key")
            assert hasattr(entry, "level")
            assert hasattr(entry, "status")
            assert hasattr(entry, "raised_at")
            assert hasattr(entry, "lowered_at")

    def test_list_history_with_level_filter(self, live_client: VergeClient) -> None:
        """Test listing history filtered by level."""
        history = live_client.alarms.list_history(level="error")

        for entry in history:
            assert entry.level == "error"

    def test_list_history_with_limit(self, live_client: VergeClient) -> None:
        """Test listing history with limit."""
        all_history = live_client.alarms.list_history()
        if len(all_history) < 2:
            pytest.skip("Need at least 2 history entries to test limit")

        limited_history = live_client.alarms.list_history(limit=1)
        assert len(limited_history) == 1

    def test_get_history_by_key(self, live_client: VergeClient) -> None:
        """Test getting history entry by key."""
        history = live_client.alarms.list_history()
        if not history:
            pytest.skip("No alarm history available")

        entry = live_client.alarms.get_history(history[0].key)

        assert entry.key == history[0].key


@pytest.mark.integration
class TestAlarmSummaryIntegration:
    """Integration tests for alarm summary."""

    def test_get_summary(self, live_client: VergeClient) -> None:
        """Test getting alarm summary."""
        summary = live_client.alarms.get_summary()

        # Summary should have expected keys
        assert "total" in summary
        assert "active" in summary
        assert "snoozed" in summary
        assert "critical" in summary
        assert "error" in summary
        assert "warning" in summary
        assert "message" in summary
        assert "resolvable" in summary

        # Values should be non-negative integers
        assert summary["total"] >= 0
        assert summary["active"] >= 0
        assert summary["snoozed"] >= 0
        assert summary["critical"] >= 0
        assert summary["error"] >= 0
        assert summary["warning"] >= 0

        # Total should equal active + snoozed
        assert summary["total"] == summary["active"] + summary["snoozed"]

    def test_summary_counts_match_list(self, live_client: VergeClient) -> None:
        """Test that summary counts match list results."""
        summary = live_client.alarms.get_summary()

        # Get all alarms including snoozed
        all_alarms = live_client.alarms.list(include_snoozed=True)
        assert summary["total"] == len(all_alarms)

        # Get active alarms (default excludes snoozed)
        active_alarms = live_client.alarms.list()
        # Note: active count may differ slightly if alarms come/go during test
        assert abs(summary["active"] - len(active_alarms)) <= 1


@pytest.mark.integration
class TestAlarmResolveIntegration:
    """Integration tests for alarm resolve operations."""

    def test_find_resolvable_alarms(self, live_client: VergeClient) -> None:
        """Test finding resolvable alarms."""
        alarms = live_client.alarms.list(include_snoozed=True)
        resolvable = [a for a in alarms if a.is_resolvable]

        # Just verify we can identify resolvable alarms
        # Don't actually resolve them as they may be important
        for alarm in resolvable:
            assert alarm.is_resolvable is True
            # resolve_text should be non-empty for resolvable alarms
            # (though this is not always guaranteed)

    def test_resolve_non_resolvable_raises(self, live_client: VergeClient) -> None:
        """Test that resolving non-resolvable alarm raises ValueError."""
        alarms = live_client.alarms.list(include_snoozed=True)
        non_resolvable = [a for a in alarms if not a.is_resolvable]

        if not non_resolvable:
            pytest.skip("No non-resolvable alarms available")

        with pytest.raises(ValueError, match="is not resolvable"):
            live_client.alarms.resolve(non_resolvable[0].key)


@pytest.mark.integration
class TestAlarmOwnerTypeIntegration:
    """Integration tests for alarm owner type filtering."""

    def test_all_owner_types(self, live_client: VergeClient) -> None:
        """Test listing alarms by all owner types."""
        owner_types = ["VM", "Network", "Node", "Tenant", "User", "System", "CloudSnapshot"]

        for owner_type in owner_types:
            alarms = live_client.alarms.list_by_owner_type(owner_type)

            # Should return a list (may be empty)
            assert isinstance(alarms, list)

            # Each should have correct owner type
            expected_api_type = {
                "VM": "vms",
                "Network": "vnets",
                "Node": "nodes",
                "Tenant": "tenant_nodes",
                "User": "users",
                "System": "system",
                "CloudSnapshot": "cloud_snapshots",
            }[owner_type]

            for alarm in alarms:
                assert alarm.owner_type == expected_api_type
