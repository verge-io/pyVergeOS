"""Unit tests for Alarm operations."""

from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

from pyvergeos import VergeClient
from pyvergeos.exceptions import NotFoundError
from pyvergeos.resources.alarms import (
    OWNER_TYPE_DISPLAY,
    OWNER_TYPE_MAP,
    Alarm,
    AlarmHistory,
)

# =============================================================================
# Alarm Model Tests
# =============================================================================


class TestAlarm:
    """Unit tests for Alarm model."""

    def test_alarm_properties(self, mock_client: VergeClient) -> None:
        """Test Alarm property accessors."""
        now_ts = int(time.time())
        data = {
            "$key": 1,
            "owner": 123,
            "owner_name": "test-vm",
            "owner_type": "vms",
            "sub_owner": 456,
            "alarm_type": 10,
            "alarm_type_name": "VM Offline",
            "alarm_type_description": "VM is not running",
            "level": "warning",
            "status": "VM test-vm is offline",
            "alarm_id": "ABC12345",
            "resolvable": True,
            "resolve_text": "Power on the VM",
            "created": now_ts - 3600,  # 1 hour ago
            "modified": now_ts - 1800,  # 30 min ago
            "snooze": 0,
            "snoozed_by": "",
        }
        alarm = Alarm(data, mock_client.alarms)

        assert alarm.key == 1
        assert alarm.level == "warning"
        assert alarm.level_display == "Warning"
        assert alarm.status == "VM test-vm is offline"
        assert alarm.alarm_type == "VM Offline"
        assert alarm.alarm_type_key == 10
        assert alarm.description == "VM is not running"
        assert alarm.alarm_id == "ABC12345"
        assert alarm.owner_name == "test-vm"
        assert alarm.owner_key == 123
        assert alarm.owner_type == "vms"
        assert alarm.owner_type_display == "VM"
        assert alarm.sub_owner == 456
        assert alarm.is_resolvable is True
        assert alarm.resolve_text == "Power on the VM"
        assert alarm.is_snoozed is False
        assert alarm.snoozed_by == ""
        assert alarm.snooze_until is None
        assert alarm.created_at is not None
        assert alarm.modified_at is not None

    def test_alarm_level_display_critical(self, mock_client: VergeClient) -> None:
        """Test level_display for critical alarm."""
        data = {"$key": 1, "level": "critical"}
        alarm = Alarm(data, mock_client.alarms)
        assert alarm.level_display == "Critical"

    def test_alarm_level_display_error(self, mock_client: VergeClient) -> None:
        """Test level_display for error alarm."""
        data = {"$key": 1, "level": "error"}
        alarm = Alarm(data, mock_client.alarms)
        assert alarm.level_display == "Error"

    def test_alarm_owner_type_display_network(self, mock_client: VergeClient) -> None:
        """Test owner_type_display for network alarm."""
        data = {"$key": 1, "owner_type": "vnets"}
        alarm = Alarm(data, mock_client.alarms)
        assert alarm.owner_type_display == "Network"

    def test_alarm_owner_type_display_node(self, mock_client: VergeClient) -> None:
        """Test owner_type_display for node alarm."""
        data = {"$key": 1, "owner_type": "nodes"}
        alarm = Alarm(data, mock_client.alarms)
        assert alarm.owner_type_display == "Node"

    def test_alarm_owner_type_display_tenant(self, mock_client: VergeClient) -> None:
        """Test owner_type_display for tenant alarm."""
        data = {"$key": 1, "owner_type": "tenant_nodes"}
        alarm = Alarm(data, mock_client.alarms)
        assert alarm.owner_type_display == "Tenant"

    def test_alarm_owner_type_display_system(self, mock_client: VergeClient) -> None:
        """Test owner_type_display for system alarm."""
        data = {"$key": 1, "owner_type": "system"}
        alarm = Alarm(data, mock_client.alarms)
        assert alarm.owner_type_display == "System"

    def test_alarm_is_snoozed_true(self, mock_client: VergeClient) -> None:
        """Test is_snoozed returns True when alarm is snoozed."""
        future_ts = int(time.time()) + 3600  # 1 hour from now
        data = {"$key": 1, "snooze": future_ts, "snoozed_by": "admin"}
        alarm = Alarm(data, mock_client.alarms)

        assert alarm.is_snoozed is True
        assert alarm.snooze_until is not None
        assert alarm.snoozed_by == "admin"

    def test_alarm_is_snoozed_false_past(self, mock_client: VergeClient) -> None:
        """Test is_snoozed returns False when snooze time has passed."""
        past_ts = int(time.time()) - 3600  # 1 hour ago
        data = {"$key": 1, "snooze": past_ts}
        alarm = Alarm(data, mock_client.alarms)

        assert alarm.is_snoozed is False

    def test_alarm_is_snoozed_false_zero(self, mock_client: VergeClient) -> None:
        """Test is_snoozed returns False when snooze is 0."""
        data = {"$key": 1, "snooze": 0}
        alarm = Alarm(data, mock_client.alarms)

        assert alarm.is_snoozed is False

    def test_alarm_is_resolvable_true(self, mock_client: VergeClient) -> None:
        """Test is_resolvable returns True when resolvable."""
        data = {"$key": 1, "resolvable": True}
        alarm = Alarm(data, mock_client.alarms)
        assert alarm.is_resolvable is True

    def test_alarm_is_resolvable_false(self, mock_client: VergeClient) -> None:
        """Test is_resolvable returns False when not resolvable."""
        data = {"$key": 1, "resolvable": False}
        alarm = Alarm(data, mock_client.alarms)
        assert alarm.is_resolvable is False

    def test_alarm_is_resolvable_default(self, mock_client: VergeClient) -> None:
        """Test is_resolvable defaults to False."""
        data = {"$key": 1}
        alarm = Alarm(data, mock_client.alarms)
        assert alarm.is_resolvable is False

    def test_alarm_owner_key_none(self, mock_client: VergeClient) -> None:
        """Test owner_key returns None when not set."""
        data = {"$key": 1}
        alarm = Alarm(data, mock_client.alarms)
        assert alarm.owner_key is None

    def test_alarm_sub_owner_none(self, mock_client: VergeClient) -> None:
        """Test sub_owner returns None when not set."""
        data = {"$key": 1}
        alarm = Alarm(data, mock_client.alarms)
        assert alarm.sub_owner is None

    def test_alarm_created_at_none(self, mock_client: VergeClient) -> None:
        """Test created_at returns None when not set."""
        data = {"$key": 1}
        alarm = Alarm(data, mock_client.alarms)
        assert alarm.created_at is None

    def test_alarm_repr(self, mock_client: VergeClient) -> None:
        """Test Alarm string representation."""
        data = {"$key": 1, "level": "warning", "status": "Test alarm status"}
        alarm = Alarm(data, mock_client.alarms)

        repr_str = repr(alarm)
        assert "Alarm" in repr_str
        assert "key=1" in repr_str
        assert "Warning" in repr_str

    def test_alarm_repr_long_status(self, mock_client: VergeClient) -> None:
        """Test Alarm repr truncates long status."""
        data = {"$key": 1, "level": "error", "status": "A" * 50}
        alarm = Alarm(data, mock_client.alarms)

        repr_str = repr(alarm)
        assert "..." in repr_str


# =============================================================================
# AlarmHistory Model Tests
# =============================================================================


class TestAlarmHistory:
    """Unit tests for AlarmHistory model."""

    def test_alarm_history_properties(self, mock_client: VergeClient) -> None:
        """Test AlarmHistory property accessors."""
        now_ts = int(time.time())
        data = {
            "$key": 100,
            "level": "error",
            "status": "VM test-vm crashed",
            "alarm_type": "vm_crash",
            "alarm_id": "XYZ98765",
            "owner": "vms/123",
            "archived_by": "auto",
            "alarm_raised": now_ts - 7200,  # 2 hours ago
            "alarm_lowered": now_ts - 3600,  # 1 hour ago
        }
        history = AlarmHistory(data, mock_client.alarms)

        assert history.key == 100
        assert history.level == "error"
        assert history.level_display == "Error"
        assert history.status == "VM test-vm crashed"
        assert history.alarm_type == "vm_crash"
        assert history.alarm_id == "XYZ98765"
        assert history.owner == "vms/123"
        assert history.archived_by == "auto"
        assert history.raised_at is not None
        assert history.lowered_at is not None

    def test_alarm_history_raised_at_none(self, mock_client: VergeClient) -> None:
        """Test raised_at returns None when not set."""
        data = {"$key": 1}
        history = AlarmHistory(data, mock_client.alarms)
        assert history.raised_at is None

    def test_alarm_history_lowered_at_none(self, mock_client: VergeClient) -> None:
        """Test lowered_at returns None when not set."""
        data = {"$key": 1}
        history = AlarmHistory(data, mock_client.alarms)
        assert history.lowered_at is None

    def test_alarm_history_repr(self, mock_client: VergeClient) -> None:
        """Test AlarmHistory string representation."""
        data = {"$key": 100, "level": "warning", "status": "Test history entry"}
        history = AlarmHistory(data, mock_client.alarms)

        repr_str = repr(history)
        assert "AlarmHistory" in repr_str
        assert "key=100" in repr_str


# =============================================================================
# AlarmManager Tests - List Operations
# =============================================================================


class TestAlarmManagerList:
    """Unit tests for AlarmManager list operations."""

    def test_list_alarms(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test listing all alarms."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "level": "critical", "status": "Critical alarm"},
            {"$key": 2, "level": "error", "status": "Error alarm"},
            {"$key": 3, "level": "warning", "status": "Warning alarm"},
        ]

        alarms = mock_client.alarms.list()

        assert len(alarms) == 3
        assert alarms[0].level == "critical"
        assert alarms[1].level == "error"
        assert alarms[2].level == "warning"

    def test_list_alarms_empty(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test listing alarms returns empty list when none exist."""
        mock_session.request.return_value.json.return_value = []

        alarms = mock_client.alarms.list()

        assert alarms == []

    def test_list_alarms_excludes_snoozed_by_default(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test that list() excludes snoozed alarms by default."""
        mock_session.request.return_value.json.return_value = []

        mock_client.alarms.list()

        call_args = mock_session.request.call_args
        params = call_args.kwargs.get("params", {})
        filter_str = params.get("filter", "")
        assert "snooze eq 0 or snooze le {$now}" in filter_str

    def test_list_alarms_include_snoozed(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test listing alarms with include_snoozed=True."""
        mock_session.request.return_value.json.return_value = []

        mock_client.alarms.list(include_snoozed=True)

        call_args = mock_session.request.call_args
        params = call_args.kwargs.get("params", {})
        filter_str = params.get("filter", "")
        assert "snooze" not in filter_str

    def test_list_alarms_level_filter_single(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test listing alarms filtered by single level."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "level": "critical"}
        ]

        alarms = mock_client.alarms.list(level="critical")

        assert len(alarms) == 1
        call_args = mock_session.request.call_args
        params = call_args.kwargs.get("params", {})
        assert "level eq 'critical'" in params.get("filter", "")

    def test_list_alarms_level_filter_multiple(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test listing alarms filtered by multiple levels."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "level": "critical"},
            {"$key": 2, "level": "error"},
        ]

        alarms = mock_client.alarms.list(level=["critical", "error"])

        assert len(alarms) == 2
        call_args = mock_session.request.call_args
        params = call_args.kwargs.get("params", {})
        filter_str = params.get("filter", "")
        assert "level eq 'critical'" in filter_str
        assert "level eq 'error'" in filter_str
        assert " or " in filter_str

    def test_list_alarms_owner_type_filter(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test listing alarms filtered by owner type."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "owner_type": "vms"}
        ]

        alarms = mock_client.alarms.list(owner_type="VM")

        assert len(alarms) == 1
        call_args = mock_session.request.call_args
        params = call_args.kwargs.get("params", {})
        assert "owner_type eq 'vms'" in params.get("filter", "")

    def test_list_alarms_sorted_by_created_desc(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test that list() sorts by created date descending."""
        mock_session.request.return_value.json.return_value = []

        mock_client.alarms.list()

        call_args = mock_session.request.call_args
        params = call_args.kwargs.get("params", {})
        assert params.get("sort") == "-created"

    def test_list_critical(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test list_critical convenience method."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "level": "critical"}
        ]

        alarms = mock_client.alarms.list_critical()

        assert len(alarms) == 1
        call_args = mock_session.request.call_args
        params = call_args.kwargs.get("params", {})
        assert "level eq 'critical'" in params.get("filter", "")

    def test_list_errors(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test list_errors convenience method."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "level": "error"}
        ]

        alarms = mock_client.alarms.list_errors()

        assert len(alarms) == 1
        call_args = mock_session.request.call_args
        params = call_args.kwargs.get("params", {})
        assert "level eq 'error'" in params.get("filter", "")

    def test_list_warnings(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test list_warnings convenience method."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "level": "warning"}
        ]

        alarms = mock_client.alarms.list_warnings()

        assert len(alarms) == 1
        call_args = mock_session.request.call_args
        params = call_args.kwargs.get("params", {})
        assert "level eq 'warning'" in params.get("filter", "")

    def test_list_by_owner_type(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test list_by_owner_type convenience method."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "owner_type": "vnets"}
        ]

        alarms = mock_client.alarms.list_by_owner_type("Network")

        assert len(alarms) == 1
        call_args = mock_session.request.call_args
        params = call_args.kwargs.get("params", {})
        assert "owner_type eq 'vnets'" in params.get("filter", "")

    def test_list_with_limit(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test listing alarms with limit."""
        mock_session.request.return_value.json.return_value = [{"$key": 1}]

        mock_client.alarms.list(limit=10)

        call_args = mock_session.request.call_args
        params = call_args.kwargs.get("params", {})
        assert params.get("limit") == 10


# =============================================================================
# AlarmManager Tests - Get Operations
# =============================================================================


class TestAlarmManagerGet:
    """Unit tests for AlarmManager get operations."""

    def test_get_alarm_by_key(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test getting an alarm by key."""
        mock_session.request.return_value.json.return_value = {
            "$key": 1,
            "level": "warning",
            "status": "Test alarm",
        }

        alarm = mock_client.alarms.get(1)

        assert alarm.key == 1
        assert alarm.status == "Test alarm"

    def test_get_alarm_not_found(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test NotFoundError when alarm not found by key."""
        mock_session.request.return_value.json.return_value = None
        mock_session.request.return_value.text = ""

        with pytest.raises(NotFoundError):
            mock_client.alarms.get(999)

    def test_get_alarm_requires_key(self, mock_client: VergeClient) -> None:
        """Test that get() requires key parameter."""
        with pytest.raises(ValueError, match="key must be provided"):
            mock_client.alarms.get()

    def test_get_alarm_name_not_supported(self, mock_client: VergeClient) -> None:
        """Test that get() does not support name parameter."""
        with pytest.raises(ValueError, match="Alarms do not have a name field"):
            mock_client.alarms.get(name="test")


# =============================================================================
# AlarmManager Tests - Snooze Operations
# =============================================================================


class TestAlarmManagerSnooze:
    """Unit tests for AlarmManager snooze operations."""

    def test_snooze_alarm(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test snoozing an alarm for default 24 hours."""
        mock_session.request.return_value.json.side_effect = [
            None,  # PUT returns nothing
            {"$key": 1, "snooze": int(time.time()) + 86400, "snoozed_by": "admin"},
        ]

        alarm = mock_client.alarms.snooze(1)

        assert alarm.is_snoozed is True
        # Verify PUT was called with snooze timestamp
        calls = mock_session.request.call_args_list
        put_calls = [c for c in calls if c.kwargs.get("json") and "snooze" in c.kwargs["json"]]
        assert len(put_calls) == 1
        snooze_ts = put_calls[0].kwargs["json"]["snooze"]
        # Should be approximately 24 hours from now
        expected = int(time.time()) + (24 * 3600)
        assert abs(snooze_ts - expected) < 5

    def test_snooze_alarm_custom_hours(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test snoozing an alarm for custom duration."""
        mock_session.request.return_value.json.side_effect = [
            None,
            {"$key": 1, "snooze": int(time.time()) + 172800},
        ]

        mock_client.alarms.snooze(1, hours=48)

        calls = mock_session.request.call_args_list
        put_calls = [c for c in calls if c.kwargs.get("json") and "snooze" in c.kwargs["json"]]
        snooze_ts = put_calls[0].kwargs["json"]["snooze"]
        expected = int(time.time()) + (48 * 3600)
        assert abs(snooze_ts - expected) < 5

    def test_snooze_alarm_invalid_hours_too_low(self, mock_client: VergeClient) -> None:
        """Test snooze with hours < 1 raises ValueError."""
        with pytest.raises(ValueError, match="hours must be at least 1"):
            mock_client.alarms.snooze(1, hours=0)

    def test_snooze_alarm_invalid_hours_too_high(self, mock_client: VergeClient) -> None:
        """Test snooze with hours > 8760 raises ValueError."""
        with pytest.raises(ValueError, match="hours cannot exceed 8760"):
            mock_client.alarms.snooze(1, hours=9000)

    def test_snooze_to_specific_time(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test snoozing until a specific datetime."""
        mock_session.request.return_value.json.side_effect = [
            None,
            {"$key": 1, "snooze": int(time.time()) + 604800},
        ]

        future_time = datetime.now(timezone.utc) + timedelta(days=7)
        mock_client.alarms.snooze_to(1, until=future_time)

        calls = mock_session.request.call_args_list
        put_calls = [c for c in calls if c.kwargs.get("json") and "snooze" in c.kwargs["json"]]
        assert len(put_calls) == 1

    def test_snooze_to_past_time_raises(self, mock_client: VergeClient) -> None:
        """Test snooze_to with past time raises ValueError."""
        past_time = datetime.now(timezone.utc) - timedelta(hours=1)

        with pytest.raises(ValueError, match="snooze time must be in the future"):
            mock_client.alarms.snooze_to(1, until=past_time)

    def test_unsnooze_alarm(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test unsnoozing an alarm."""
        mock_session.request.return_value.json.side_effect = [
            None,
            {"$key": 1, "snooze": 0},
        ]

        alarm = mock_client.alarms.unsnooze(1)

        assert alarm.is_snoozed is False
        calls = mock_session.request.call_args_list
        put_calls = [c for c in calls if c.kwargs.get("json") == {"snooze": 0}]
        assert len(put_calls) == 1

    def test_alarm_object_snooze(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test snoozing via Alarm object method."""
        mock_session.request.return_value.json.side_effect = [
            None,
            {"$key": 1, "snooze": int(time.time()) + 86400},
        ]

        data = {"$key": 1, "snooze": 0}
        alarm = Alarm(data, mock_client.alarms)
        updated = alarm.snooze()

        assert updated.is_snoozed is True

    def test_alarm_object_unsnooze(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test unsnoozing via Alarm object method."""
        mock_session.request.return_value.json.side_effect = [
            None,
            {"$key": 1, "snooze": 0},
        ]

        data = {"$key": 1, "snooze": int(time.time()) + 3600}
        alarm = Alarm(data, mock_client.alarms)
        updated = alarm.unsnooze()

        assert updated.is_snoozed is False


# =============================================================================
# AlarmManager Tests - Resolve Operations
# =============================================================================


class TestAlarmManagerResolve:
    """Unit tests for AlarmManager resolve operations."""

    def test_resolve_alarm(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test resolving a resolvable alarm."""
        # First call is GET to verify resolvable, second is POST to resolve
        mock_session.request.return_value.json.side_effect = [
            {"$key": 1, "resolvable": True, "status": "Resolvable alarm"},
            None,  # POST returns nothing
        ]

        mock_client.alarms.resolve(1)

        # Verify POST was called to resolve endpoint
        calls = mock_session.request.call_args_list
        [c for c in calls if "resolve" in str(c) and c.kwargs.get("method") == "POST"]
        # Actually let's check differently
        post_calls = [c for c in calls if "alarms/1/resolve" in str(c)]
        assert len(post_calls) == 1

    def test_resolve_non_resolvable_alarm_raises(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test resolving non-resolvable alarm raises ValueError."""
        mock_session.request.return_value.json.return_value = {
            "$key": 1,
            "resolvable": False,
        }

        with pytest.raises(ValueError, match="is not resolvable"):
            mock_client.alarms.resolve(1)

    def test_alarm_object_resolve(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test resolving via Alarm object method."""
        mock_session.request.return_value.json.side_effect = [
            {"$key": 1, "resolvable": True},
            None,
        ]

        data = {"$key": 1, "resolvable": True}
        alarm = Alarm(data, mock_client.alarms)
        alarm.resolve()

        # Verify resolve was called
        calls = mock_session.request.call_args_list
        post_calls = [c for c in calls if "alarms/1/resolve" in str(c)]
        assert len(post_calls) == 1


# =============================================================================
# AlarmManager Tests - History Operations
# =============================================================================


class TestAlarmManagerHistory:
    """Unit tests for AlarmManager history operations."""

    def test_list_history(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test listing alarm history."""
        now_ts = int(time.time())
        mock_session.request.return_value.json.return_value = [
            {
                "$key": 100,
                "level": "error",
                "status": "Old error",
                "alarm_raised": now_ts - 7200,
                "alarm_lowered": now_ts - 3600,
            },
            {
                "$key": 101,
                "level": "warning",
                "status": "Old warning",
                "alarm_raised": now_ts - 3600,
                "alarm_lowered": now_ts - 1800,
            },
        ]

        history = mock_client.alarms.list_history()

        assert len(history) == 2
        assert history[0].level == "error"
        assert history[1].level == "warning"

    def test_list_history_empty(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test listing history returns empty list when none exist."""
        mock_session.request.return_value.json.return_value = []

        history = mock_client.alarms.list_history()

        assert history == []

    def test_list_history_sorted_by_lowered_desc(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test that list_history() sorts by lowered date descending."""
        mock_session.request.return_value.json.return_value = []

        mock_client.alarms.list_history()

        call_args = mock_session.request.call_args
        params = call_args.kwargs.get("params", {})
        assert params.get("sort") == "-alarm_lowered"

    def test_list_history_level_filter(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test listing history filtered by level."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 100, "level": "critical"}
        ]

        mock_client.alarms.list_history(level="critical")

        call_args = mock_session.request.call_args
        params = call_args.kwargs.get("params", {})
        assert "level eq 'critical'" in params.get("filter", "")

    def test_list_history_with_limit(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test listing history with limit."""
        mock_session.request.return_value.json.return_value = []

        mock_client.alarms.list_history(limit=50)

        call_args = mock_session.request.call_args
        params = call_args.kwargs.get("params", {})
        assert params.get("limit") == 50

    def test_get_history_by_key(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test getting history entry by key."""
        mock_session.request.return_value.json.return_value = {
            "$key": 100,
            "level": "error",
            "status": "Old error",
        }

        history = mock_client.alarms.get_history(100)

        assert history.key == 100
        assert history.level == "error"

    def test_get_history_not_found(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test NotFoundError when history not found."""
        mock_session.request.return_value.json.return_value = None
        mock_session.request.return_value.text = ""

        with pytest.raises(NotFoundError):
            mock_client.alarms.get_history(999)


# =============================================================================
# AlarmManager Tests - Summary
# =============================================================================


class TestAlarmManagerSummary:
    """Unit tests for AlarmManager summary operations."""

    def test_get_summary(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test getting alarm summary."""
        now_ts = int(time.time())
        future_ts = now_ts + 3600
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "level": "critical", "snooze": 0, "resolvable": True},
            {"$key": 2, "level": "error", "snooze": 0, "resolvable": False},
            {"$key": 3, "level": "warning", "snooze": 0, "resolvable": True},
            {"$key": 4, "level": "warning", "snooze": future_ts, "resolvable": False},
        ]

        summary = mock_client.alarms.get_summary()

        assert summary["total"] == 4
        assert summary["active"] == 3
        assert summary["snoozed"] == 1
        assert summary["critical"] == 1
        assert summary["error"] == 1
        assert summary["warning"] == 1  # Only non-snoozed warning
        assert summary["resolvable"] == 2


# =============================================================================
# AlarmManager Tests - Default Fields
# =============================================================================


class TestAlarmManagerDefaultFields:
    """Unit tests for AlarmManager default fields."""

    def test_list_uses_default_fields(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test that list() uses default fields."""
        mock_session.request.return_value.json.return_value = []

        mock_client.alarms.list()

        call_args = mock_session.request.call_args
        params = call_args.kwargs.get("params", {})
        fields = params.get("fields", "")

        assert "$key" in fields
        assert "level" in fields
        assert "status" in fields
        assert "owner_name" in fields
        assert "snooze" in fields

    def test_get_uses_default_fields(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test that get() uses default fields."""
        mock_session.request.return_value.json.return_value = {"$key": 1}

        mock_client.alarms.get(1)

        call_args = mock_session.request.call_args
        params = call_args.kwargs.get("params", {})
        fields = params.get("fields", "")

        assert "$key" in fields
        assert "level" in fields


# =============================================================================
# Owner Type Mapping Tests
# =============================================================================


class TestOwnerTypeMappings:
    """Test owner type mapping constants."""

    def test_owner_type_map_all_entries(self) -> None:
        """Test all owner type mappings exist."""
        assert OWNER_TYPE_MAP["VM"] == "vms"
        assert OWNER_TYPE_MAP["Network"] == "vnets"
        assert OWNER_TYPE_MAP["Node"] == "nodes"
        assert OWNER_TYPE_MAP["Tenant"] == "tenant_nodes"
        assert OWNER_TYPE_MAP["User"] == "users"
        assert OWNER_TYPE_MAP["System"] == "system"
        assert OWNER_TYPE_MAP["CloudSnapshot"] == "cloud_snapshots"

    def test_owner_type_display_all_entries(self) -> None:
        """Test all reverse owner type mappings exist."""
        assert OWNER_TYPE_DISPLAY["vms"] == "VM"
        assert OWNER_TYPE_DISPLAY["vnets"] == "Network"
        assert OWNER_TYPE_DISPLAY["nodes"] == "Node"
        assert OWNER_TYPE_DISPLAY["tenant_nodes"] == "Tenant"
        assert OWNER_TYPE_DISPLAY["users"] == "User"
        assert OWNER_TYPE_DISPLAY["system"] == "System"
        assert OWNER_TYPE_DISPLAY["cloud_snapshots"] == "CloudSnapshot"
