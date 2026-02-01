"""Unit tests for TaskSchedule operations."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from pyvergeos import VergeClient
from pyvergeos.exceptions import NotFoundError
from pyvergeos.resources.task_schedules import (
    DAY_OF_MONTH_OPTIONS,
    REPEAT_INTERVALS,
    TaskSchedule,
)

# =============================================================================
# TaskSchedule Model Tests
# =============================================================================


class TestTaskSchedule:
    """Unit tests for TaskSchedule model."""

    def test_task_schedule_properties(self, mock_client: VergeClient) -> None:
        """Test TaskSchedule property accessors."""
        data = {
            "$key": 1,
            "name": "Nightly Backup",
            "description": "Runs every night at 2 AM",
            "enabled": True,
            "repeat_every": "day",
            "repeat_iteration": 1,
            "start_date": "2024-01-01",
            "start_time_of_day": 7200,
            "end_time_of_day": 86400,
            "task": 100,
            "system_created": False,
            "creator": 1,
            "monday": True,
            "tuesday": True,
            "wednesday": True,
            "thursday": True,
            "friday": True,
            "saturday": False,
            "sunday": False,
        }
        schedule = TaskSchedule(data, mock_client.task_schedules)

        assert schedule.key == 1
        assert schedule.name == "Nightly Backup"
        assert schedule.description == "Runs every night at 2 AM"
        assert schedule.is_enabled is True
        assert schedule.repeat_every_display == "Day(s)"
        assert schedule.repeat_count == 1
        assert schedule.task_key == 100
        assert schedule.is_system_created is False
        assert schedule.creator_key == 1

    def test_task_schedule_day_properties(self, mock_client: VergeClient) -> None:
        """Test TaskSchedule day-of-week properties."""
        data = {
            "$key": 1,
            "monday": True,
            "tuesday": True,
            "wednesday": True,
            "thursday": True,
            "friday": True,
            "saturday": False,
            "sunday": False,
        }
        schedule = TaskSchedule(data, mock_client.task_schedules)

        assert schedule.runs_on_monday is True
        assert schedule.runs_on_tuesday is True
        assert schedule.runs_on_wednesday is True
        assert schedule.runs_on_thursday is True
        assert schedule.runs_on_friday is True
        assert schedule.runs_on_saturday is False
        assert schedule.runs_on_sunday is False

    def test_task_schedule_active_days(self, mock_client: VergeClient) -> None:
        """Test TaskSchedule.active_days returns correct list."""
        data = {
            "$key": 1,
            "monday": True,
            "tuesday": False,
            "wednesday": True,
            "thursday": False,
            "friday": True,
            "saturday": False,
            "sunday": False,
        }
        schedule = TaskSchedule(data, mock_client.task_schedules)

        assert schedule.active_days == ["Monday", "Wednesday", "Friday"]

    def test_task_schedule_active_days_all(self, mock_client: VergeClient) -> None:
        """Test TaskSchedule.active_days with all days enabled."""
        data = {
            "$key": 1,
            "monday": True,
            "tuesday": True,
            "wednesday": True,
            "thursday": True,
            "friday": True,
            "saturday": True,
            "sunday": True,
        }
        schedule = TaskSchedule(data, mock_client.task_schedules)

        assert len(schedule.active_days) == 7
        assert "Monday" in schedule.active_days
        assert "Sunday" in schedule.active_days

    def test_task_schedule_active_days_defaults(self, mock_client: VergeClient) -> None:
        """Test TaskSchedule.active_days defaults to all days when not set."""
        data = {"$key": 1}
        schedule = TaskSchedule(data, mock_client.task_schedules)

        # All days default to True
        assert len(schedule.active_days) == 7

    def test_task_schedule_is_enabled_default(self, mock_client: VergeClient) -> None:
        """Test TaskSchedule.is_enabled defaults to True."""
        data = {"$key": 1}
        schedule = TaskSchedule(data, mock_client.task_schedules)

        assert schedule.is_enabled is True

    def test_task_schedule_repeat_count_default(self, mock_client: VergeClient) -> None:
        """Test TaskSchedule.repeat_count defaults to 1."""
        data = {"$key": 1}
        schedule = TaskSchedule(data, mock_client.task_schedules)

        assert schedule.repeat_count == 1

    def test_task_schedule_task_key_none(self, mock_client: VergeClient) -> None:
        """Test TaskSchedule.task_key returns None when not set."""
        data = {"$key": 1}
        schedule = TaskSchedule(data, mock_client.task_schedules)

        assert schedule.task_key is None

    def test_task_schedule_creator_key_none(self, mock_client: VergeClient) -> None:
        """Test TaskSchedule.creator_key returns None when not set."""
        data = {"$key": 1}
        schedule = TaskSchedule(data, mock_client.task_schedules)

        assert schedule.creator_key is None

    def test_task_schedule_is_system_created_default(self, mock_client: VergeClient) -> None:
        """Test TaskSchedule.is_system_created defaults to False."""
        data = {"$key": 1}
        schedule = TaskSchedule(data, mock_client.task_schedules)

        assert schedule.is_system_created is False

    def test_task_schedule_repeat_every_display_unknown(self, mock_client: VergeClient) -> None:
        """Test TaskSchedule.repeat_every_display returns raw value for unknown intervals."""
        data = {"$key": 1, "repeat_every": "custom_interval"}
        schedule = TaskSchedule(data, mock_client.task_schedules)

        assert schedule.repeat_every_display == "custom_interval"


# =============================================================================
# Constants Tests
# =============================================================================


class TestConstants:
    """Unit tests for module constants."""

    def test_repeat_intervals(self) -> None:
        """Test REPEAT_INTERVALS constant."""
        assert "minute" in REPEAT_INTERVALS
        assert "hour" in REPEAT_INTERVALS
        assert "day" in REPEAT_INTERVALS
        assert "week" in REPEAT_INTERVALS
        assert "month" in REPEAT_INTERVALS
        assert "year" in REPEAT_INTERVALS
        assert "never" in REPEAT_INTERVALS
        assert REPEAT_INTERVALS["day"] == "Day(s)"

    def test_day_of_month_options(self) -> None:
        """Test DAY_OF_MONTH_OPTIONS constant."""
        assert "first" in DAY_OF_MONTH_OPTIONS
        assert "last" in DAY_OF_MONTH_OPTIONS
        assert "15th" in DAY_OF_MONTH_OPTIONS
        assert "start_date" in DAY_OF_MONTH_OPTIONS


# =============================================================================
# TaskScheduleManager Tests - List Operations
# =============================================================================


class TestTaskScheduleManagerList:
    """Unit tests for TaskScheduleManager list operations."""

    def test_list_schedules(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test listing all task schedules."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "name": "Hourly", "repeat_every": "hour", "enabled": True},
            {"$key": 2, "name": "Daily", "repeat_every": "day", "enabled": True},
            {"$key": 3, "name": "Weekly", "repeat_every": "week", "enabled": False},
        ]

        schedules = mock_client.task_schedules.list()

        assert len(schedules) == 3
        assert schedules[0].name == "Hourly"
        assert schedules[1].name == "Daily"
        assert schedules[2].name == "Weekly"

    def test_list_schedules_empty(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test listing schedules returns empty list when none exist."""
        mock_session.request.return_value.json.return_value = []

        schedules = mock_client.task_schedules.list()

        assert schedules == []

    def test_list_schedules_none_response(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test listing schedules handles None response."""
        mock_session.request.return_value.json.return_value = None
        mock_session.request.return_value.text = ""

        schedules = mock_client.task_schedules.list()

        assert schedules == []

    def test_list_schedules_single_dict_response(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test listing schedules handles single dict response."""
        mock_session.request.return_value.json.return_value = {
            "$key": 1,
            "name": "Single",
            "repeat_every": "day",
        }

        schedules = mock_client.task_schedules.list()

        assert len(schedules) == 1
        assert schedules[0].name == "Single"

    def test_list_schedules_by_enabled(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test listing schedules filtered by enabled state."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "name": "Active", "enabled": True}
        ]

        schedules = mock_client.task_schedules.list(enabled=True)

        assert len(schedules) == 1
        call_args = mock_session.request.call_args
        assert "enabled eq true" in str(call_args)

    def test_list_schedules_by_disabled(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test listing disabled schedules."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "name": "Inactive", "enabled": False}
        ]

        schedules = mock_client.task_schedules.list(enabled=False)

        assert len(schedules) == 1
        call_args = mock_session.request.call_args
        assert "enabled eq false" in str(call_args)

    def test_list_schedules_by_repeat_every(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test listing schedules filtered by repeat interval."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "name": "Daily", "repeat_every": "day"}
        ]

        schedules = mock_client.task_schedules.list(repeat_every="day")

        assert len(schedules) == 1
        call_args = mock_session.request.call_args
        assert "repeat_every eq 'day'" in str(call_args)

    def test_list_schedules_by_name_exact(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test listing schedules by exact name."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "name": "Nightly Backup"}
        ]

        schedules = mock_client.task_schedules.list(name="Nightly Backup")

        assert len(schedules) == 1
        call_args = mock_session.request.call_args
        assert "name eq 'Nightly Backup'" in str(call_args)

    def test_list_schedules_by_name_wildcard(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test listing schedules by name with wildcard."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "name": "Backup Daily"},
            {"$key": 2, "name": "Backup Weekly"},
        ]

        schedules = mock_client.task_schedules.list(name="Backup*")

        assert len(schedules) == 2
        call_args = mock_session.request.call_args
        assert "name ct 'Backup'" in str(call_args)

    def test_list_schedules_with_pagination(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test listing schedules with pagination."""
        mock_session.request.return_value.json.return_value = [{"$key": 1, "name": "Schedule"}]

        mock_client.task_schedules.list(limit=10, offset=5)

        call_args = mock_session.request.call_args
        params = call_args.kwargs.get("params", {})
        assert params.get("limit") == 10
        assert params.get("offset") == 5

    def test_list_enabled(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test list_enabled convenience method."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "name": "Active", "enabled": True}
        ]

        schedules = mock_client.task_schedules.list_enabled()

        assert len(schedules) == 1
        call_args = mock_session.request.call_args
        assert "enabled eq true" in str(call_args)

    def test_list_disabled(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test list_disabled convenience method."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "name": "Inactive", "enabled": False}
        ]

        schedules = mock_client.task_schedules.list_disabled()

        assert len(schedules) == 1
        call_args = mock_session.request.call_args
        assert "enabled eq false" in str(call_args)


# =============================================================================
# TaskScheduleManager Tests - Get Operations
# =============================================================================


class TestTaskScheduleManagerGet:
    """Unit tests for TaskScheduleManager get operations."""

    def test_get_schedule_by_key(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test getting a schedule by key."""
        mock_session.request.return_value.json.return_value = {
            "$key": 1,
            "name": "Daily",
            "repeat_every": "day",
            "enabled": True,
        }

        schedule = mock_client.task_schedules.get(1)

        assert schedule.key == 1
        assert schedule.name == "Daily"

    def test_get_schedule_by_name(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test getting a schedule by name."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "name": "Nightly Backup", "repeat_every": "day"}
        ]

        schedule = mock_client.task_schedules.get(name="Nightly Backup")

        assert schedule.name == "Nightly Backup"
        call_args = mock_session.request.call_args
        assert "name eq 'Nightly Backup'" in str(call_args)

    def test_get_schedule_not_found_by_key(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test NotFoundError when schedule not found by key."""
        mock_session.request.return_value.json.return_value = None
        mock_session.request.return_value.text = ""

        with pytest.raises(NotFoundError):
            mock_client.task_schedules.get(999)

    def test_get_schedule_not_found_by_name(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test NotFoundError when schedule not found by name."""
        mock_session.request.return_value.json.return_value = []

        with pytest.raises(NotFoundError):
            mock_client.task_schedules.get(name="Nonexistent")

    def test_get_schedule_invalid_response(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test NotFoundError when response is not a dict."""
        mock_session.request.return_value.json.return_value = []

        with pytest.raises(NotFoundError):
            mock_client.task_schedules.get(999)

    def test_get_schedule_requires_key_or_name(self, mock_client: VergeClient) -> None:
        """Test that get() requires key or name parameter."""
        with pytest.raises(ValueError, match="Either key or name must be provided"):
            mock_client.task_schedules.get()


# =============================================================================
# TaskScheduleManager Tests - Create Operations
# =============================================================================


class TestTaskScheduleManagerCreate:
    """Unit tests for TaskScheduleManager create operations."""

    def test_create_schedule(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test creating a task schedule."""
        mock_session.request.return_value.json.side_effect = [
            {"$key": 1},  # POST response
            {"$key": 1, "name": "Daily Backup", "repeat_every": "day"},  # GET response
        ]

        schedule = mock_client.task_schedules.create(name="Daily Backup", repeat_every="day")

        assert schedule.key == 1
        assert schedule.name == "Daily Backup"

    def test_create_schedule_with_all_options(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test creating a schedule with all options."""
        mock_session.request.return_value.json.side_effect = [
            {"$key": 1},
            {"$key": 1, "name": "Weekly Report", "repeat_every": "week"},
        ]

        schedule = mock_client.task_schedules.create(
            name="Weekly Report",
            description="Generate weekly reports",
            enabled=True,
            repeat_every="week",
            repeat_iteration=1,
            start_date="2024-01-01",
            end_date="2024-12-31 23:59:59",
            start_time_of_day=32400,  # 9 AM
            end_time_of_day=64800,  # 6 PM
            day_of_month="first",
            monday=True,
            tuesday=True,
            wednesday=True,
            thursday=True,
            friday=True,
            saturday=False,
            sunday=False,
            task=100,
        )

        assert schedule.key == 1
        # Verify POST body
        post_calls = [
            c
            for c in mock_session.request.call_args_list
            if c.kwargs.get("method") == "POST" and "task_schedules" in c.kwargs.get("url", "")
        ]
        assert len(post_calls) == 1
        body = post_calls[0].kwargs.get("json", {})
        assert body.get("name") == "Weekly Report"
        assert body.get("description") == "Generate weekly reports"
        assert body.get("repeat_every") == "week"
        assert body.get("saturday") is False
        assert body.get("sunday") is False
        assert body.get("task") == 100

    def test_create_schedule_no_response(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test create raises error on None response."""
        mock_session.request.return_value.json.return_value = None
        mock_session.request.return_value.text = ""

        with pytest.raises(ValueError, match="No response from create operation"):
            mock_client.task_schedules.create(name="Test")

    def test_create_schedule_invalid_response(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test create raises error on non-dict response."""
        mock_session.request.return_value.json.return_value = []

        with pytest.raises(ValueError, match="Create operation returned invalid response"):
            mock_client.task_schedules.create(name="Test")


# =============================================================================
# TaskScheduleManager Tests - Update Operations
# =============================================================================


class TestTaskScheduleManagerUpdate:
    """Unit tests for TaskScheduleManager update operations."""

    def test_update_schedule(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test updating a task schedule."""
        mock_session.request.return_value.json.side_effect = [
            None,  # PUT response
            {"$key": 1, "name": "Updated Schedule", "enabled": True},  # GET response
        ]

        schedule = mock_client.task_schedules.update(1, name="Updated Schedule")

        assert schedule.name == "Updated Schedule"

    def test_update_schedule_enabled(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test updating schedule enabled state."""
        mock_session.request.return_value.json.side_effect = [
            None,
            {"$key": 1, "name": "Schedule", "enabled": False},
        ]

        schedule = mock_client.task_schedules.update(1, enabled=False)

        assert schedule.is_enabled is False

    def test_update_schedule_days(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test updating schedule day flags."""
        mock_session.request.return_value.json.side_effect = [
            None,
            {"$key": 1, "monday": True, "saturday": False, "sunday": False},
        ]

        schedule = mock_client.task_schedules.update(1, monday=True, saturday=False, sunday=False)

        assert schedule.runs_on_monday is True
        assert schedule.runs_on_saturday is False

    def test_update_schedule_no_changes(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test update with no changes returns current schedule."""
        mock_session.request.return_value.json.return_value = {
            "$key": 1,
            "name": "Schedule",
        }

        schedule = mock_client.task_schedules.update(1)

        assert schedule.key == 1


# =============================================================================
# TaskScheduleManager Tests - Delete Operations
# =============================================================================


class TestTaskScheduleManagerDelete:
    """Unit tests for TaskScheduleManager delete operations."""

    def test_delete_schedule(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test deleting a task schedule."""
        mock_session.request.return_value.json.return_value = None
        mock_session.request.return_value.text = ""

        mock_client.task_schedules.delete(1)

        calls = mock_session.request.call_args_list
        delete_call = [c for c in calls if "DELETE" in str(c)][0]
        assert "task_schedules/1" in str(delete_call)


# =============================================================================
# TaskScheduleManager Tests - Enable/Disable Operations
# =============================================================================


class TestTaskScheduleManagerEnableDisable:
    """Unit tests for TaskScheduleManager enable/disable operations."""

    def test_enable_schedule(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test enabling a schedule."""
        mock_session.request.return_value.json.side_effect = [
            None,  # PUT response
            {"$key": 1, "name": "Schedule", "enabled": True},  # GET response
        ]

        schedule = mock_client.task_schedules.enable(1)

        assert schedule.is_enabled is True
        # Verify PUT was called with enabled=True
        calls = mock_session.request.call_args_list
        put_calls = [c for c in calls if c.kwargs.get("json") == {"enabled": True}]
        assert len(put_calls) == 1

    def test_disable_schedule(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test disabling a schedule."""
        mock_session.request.return_value.json.side_effect = [
            None,
            {"$key": 1, "name": "Schedule", "enabled": False},
        ]

        schedule = mock_client.task_schedules.disable(1)

        assert schedule.is_enabled is False
        # Verify PUT was called with enabled=False
        calls = mock_session.request.call_args_list
        put_calls = [c for c in calls if c.kwargs.get("json") == {"enabled": False}]
        assert len(put_calls) == 1

    def test_schedule_object_enable(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test enabling schedule via TaskSchedule object method."""
        mock_session.request.return_value.json.side_effect = [
            None,
            {"$key": 1, "name": "Schedule", "enabled": True},
        ]

        data = {"$key": 1, "name": "Schedule", "enabled": False}
        schedule = TaskSchedule(data, mock_client.task_schedules)
        updated = schedule.enable()

        assert updated.is_enabled is True

    def test_schedule_object_disable(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test disabling schedule via TaskSchedule object method."""
        mock_session.request.return_value.json.side_effect = [
            None,
            {"$key": 1, "name": "Schedule", "enabled": False},
        ]

        data = {"$key": 1, "name": "Schedule", "enabled": True}
        schedule = TaskSchedule(data, mock_client.task_schedules)
        updated = schedule.disable()

        assert updated.is_enabled is False


# =============================================================================
# TaskScheduleManager Tests - Get Schedule Operations
# =============================================================================


class TestTaskScheduleManagerGetSchedule:
    """Unit tests for TaskScheduleManager get_schedule operation."""

    def test_get_schedule_times(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test getting upcoming scheduled execution times."""
        # Action method only returns dict responses, so mock returns times in a dict
        mock_session.request.return_value.json.return_value = {
            "times": [{"time": 1704067200}, {"time": 1704153600}]
        }

        times = mock_client.task_schedules.get_schedule(1, max_results=10)

        assert len(times) == 2
        call_args = mock_session.request.call_args
        assert "action=get_schedule" in str(call_args)

    def test_get_schedule_times_with_range(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test getting scheduled times with time range."""
        mock_session.request.return_value.json.return_value = []

        mock_client.task_schedules.get_schedule(
            1, max_results=100, start_time=1704067200, end_time=1704153600
        )

        call_args = mock_session.request.call_args
        params = call_args.kwargs.get("json", {})
        assert params.get("start_time") == 1704067200
        assert params.get("end_time") == 1704153600

    def test_get_schedule_times_none_response(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test get_schedule handles None response."""
        mock_session.request.return_value.json.return_value = None
        mock_session.request.return_value.text = ""

        times = mock_client.task_schedules.get_schedule(1)

        assert times == []

    def test_get_schedule_times_dict_response(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test get_schedule handles dict response with times key."""
        mock_session.request.return_value.json.return_value = {
            "times": [{"time": 1704067200}, {"time": 1704153600}]
        }

        times = mock_client.task_schedules.get_schedule(1)

        assert len(times) == 2

    def test_get_schedule_times_dict_response_no_times(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test get_schedule handles dict response without times key.

        When the response dict has no 'times' or 'schedule' key, the method
        returns an empty list as the fallback.
        """
        mock_session.request.return_value.json.return_value = {"result": "ok"}

        times = mock_client.task_schedules.get_schedule(1)

        # No times/schedule key means empty list fallback
        assert times == []

    def test_get_schedule_max_results_bounds(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test get_schedule clamps max_results to valid range."""
        mock_session.request.return_value.json.return_value = []

        # Test lower bound
        mock_client.task_schedules.get_schedule(1, max_results=0)
        call_args = mock_session.request.call_args
        params = call_args.kwargs.get("json", {})
        assert params.get("max") == 1

    def test_schedule_object_get_schedule(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test getting schedule times via TaskSchedule object method."""
        # Action method only returns dict responses, so mock returns times in a dict
        mock_session.request.return_value.json.return_value = {"times": [{"time": 1704067200}]}

        data = {"$key": 1, "name": "Schedule"}
        schedule = TaskSchedule(data, mock_client.task_schedules)
        times = schedule.get_schedule(max_results=10)

        assert len(times) == 1


# =============================================================================
# TaskScheduleManager Tests - Triggers Access
# =============================================================================


class TestTaskScheduleManagerTriggers:
    """Unit tests for TaskScheduleManager triggers access."""

    def test_triggers_returns_scoped_manager(self, mock_client: VergeClient) -> None:
        """Test triggers() returns a scoped TaskScheduleTriggerManager."""
        manager = mock_client.task_schedules.triggers(1)

        # Manager should be scoped to the schedule
        from pyvergeos.resources.task_schedule_triggers import TaskScheduleTriggerManager

        assert isinstance(manager, TaskScheduleTriggerManager)

    def test_schedule_object_triggers(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test accessing triggers via TaskSchedule object."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "task": 100, "schedule": 200}
        ]

        data = {"$key": 200, "name": "Schedule"}
        schedule = TaskSchedule(data, mock_client.task_schedules)
        triggers = schedule.triggers.list()

        assert len(triggers) == 1
        call_args = mock_session.request.call_args
        assert "schedule eq 200" in str(call_args)


# =============================================================================
# TaskScheduleManager Tests - Default Fields
# =============================================================================


class TestTaskScheduleManagerDefaultFields:
    """Unit tests for TaskScheduleManager default fields."""

    def test_list_uses_default_fields(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test that list() uses default fields."""
        mock_session.request.return_value.json.return_value = []

        mock_client.task_schedules.list()

        call_args = mock_session.request.call_args
        params = call_args.kwargs.get("params", {})
        fields = params.get("fields", "")

        assert "$key" in fields
        assert "name" in fields
        assert "enabled" in fields
        assert "repeat_every" in fields

    def test_list_custom_fields(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test that list() can use custom fields."""
        mock_session.request.return_value.json.return_value = []

        mock_client.task_schedules.list(fields=["$key", "name"])

        call_args = mock_session.request.call_args
        params = call_args.kwargs.get("params", {})
        fields = params.get("fields", "")

        assert fields == "$key,name"
