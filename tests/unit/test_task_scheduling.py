"""Unit tests for task scheduling system.

Tests for:
- TaskScheduleManager
- TaskScheduleTriggerManager
- TaskEventManager
- TaskScriptManager
- Enhanced TaskManager CRUD
"""

from unittest.mock import MagicMock

import pytest

from pyvergeos import VergeClient
from pyvergeos.exceptions import NotFoundError
from pyvergeos.resources.task_events import TaskEvent, TaskEventManager
from pyvergeos.resources.task_schedule_triggers import (
    TaskScheduleTrigger,
    TaskScheduleTriggerManager,
)
from pyvergeos.resources.task_schedules import TaskSchedule, TaskScheduleManager
from pyvergeos.resources.task_scripts import TaskScript, TaskScriptManager
from pyvergeos.resources.tasks import Task, TaskManager

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_client():
    """Create a mock VergeClient."""
    client = MagicMock(spec=VergeClient)
    client._request = MagicMock()
    return client


@pytest.fixture
def task_manager(mock_client):
    """Create a TaskManager with mock client."""
    return TaskManager(mock_client)


@pytest.fixture
def schedule_manager(mock_client):
    """Create a TaskScheduleManager with mock client."""
    return TaskScheduleManager(mock_client)


@pytest.fixture
def trigger_manager(mock_client):
    """Create a TaskScheduleTriggerManager with mock client."""
    return TaskScheduleTriggerManager(mock_client)


@pytest.fixture
def scoped_trigger_manager(mock_client):
    """Create a scoped TaskScheduleTriggerManager."""
    return TaskScheduleTriggerManager(mock_client, task_key=1)


@pytest.fixture
def event_manager(mock_client):
    """Create a TaskEventManager with mock client."""
    return TaskEventManager(mock_client)


@pytest.fixture
def scoped_event_manager(mock_client):
    """Create a scoped TaskEventManager."""
    return TaskEventManager(mock_client, task_key=1)


@pytest.fixture
def script_manager(mock_client):
    """Create a TaskScriptManager with mock client."""
    return TaskScriptManager(mock_client)


@pytest.fixture
def sample_task():
    """Sample task data from API."""
    return {
        "$key": 1,
        "name": "Daily Backup",
        "description": "Daily backup of production VM",
        "enabled": True,
        "status": "idle",
        "action": "snapshot",
        "action_display": "Snapshot",
        "table": "vms",
        "owner": 10,
        "owner_display": "web-server",
        "creator": 1,
        "creator_display": "admin",
        "last_run": "2024-01-01 02:00:00",
        "delete_after_run": False,
        "system_created": False,
        "id": "a" * 40,
        "triggers_count": 2,
        "events_count": 1,
    }


@pytest.fixture
def sample_schedule():
    """Sample task schedule data from API."""
    return {
        "$key": 1,
        "name": "Nightly",
        "description": "Runs every night at 2 AM",
        "enabled": True,
        "task": None,
        "repeat_every": "day",
        "repeat_iteration": 1,
        "start_date": "2024-01-01",
        "start_date_epoch": 1704067200,
        "end_date": "",
        "start_time_of_day": 7200,
        "end_time_of_day": 86400,
        "all_day": False,
        "day_of_month": "start_date",
        "monday": True,
        "tuesday": True,
        "wednesday": True,
        "thursday": True,
        "friday": True,
        "saturday": True,
        "sunday": True,
        "system_created": False,
        "creator": 1,
        "creator_display": "admin",
    }


@pytest.fixture
def sample_trigger():
    """Sample task schedule trigger data from API."""
    return {
        "$key": 1,
        "task": 1,
        "task_display": "Daily Backup",
        "schedule": 1,
        "schedule_display": "Nightly",
        "trigger": 1704153600,
        "sch_enabled": True,
        "sch_repeat_every": "Day(s)",
        "sch_start_time_of_day": 7200,
    }


@pytest.fixture
def sample_event():
    """Sample task event data from API."""
    return {
        "$key": 1,
        "owner": 10,
        "owner_display": "web-server",
        "table": "vms",
        "event": "poweron",
        "event_name": "Power On",
        "task": 1,
        "task_display": "Notification Task",
        "task_name": "Notification Task",
        "table_event_filters": {"status": "running"},
        "trigger": 0,
        "context": {"notify": True},
    }


@pytest.fixture
def sample_script():
    """Sample task script data from API."""
    return {
        "$key": 1,
        "name": "Cleanup Script",
        "description": "Removes old temporary files",
        "script": "log('Cleanup started')\n// cleanup code here",
        "task_settings": {"questions": []},
        "task_count": 2,
    }


# =============================================================================
# TaskSchedule Tests
# =============================================================================


class TestTaskSchedule:
    """Tests for TaskSchedule model."""

    def test_is_enabled(self, schedule_manager, sample_schedule):
        """Test is_enabled property."""
        schedule = TaskSchedule(sample_schedule, schedule_manager)
        assert schedule.is_enabled is True

        sample_schedule["enabled"] = False
        schedule = TaskSchedule(sample_schedule, schedule_manager)
        assert schedule.is_enabled is False

    def test_repeat_every_display(self, schedule_manager, sample_schedule):
        """Test repeat_every_display property."""
        schedule = TaskSchedule(sample_schedule, schedule_manager)
        assert schedule.repeat_every_display == "Day(s)"

    def test_repeat_count(self, schedule_manager, sample_schedule):
        """Test repeat_count property."""
        schedule = TaskSchedule(sample_schedule, schedule_manager)
        assert schedule.repeat_count == 1

    def test_active_days(self, schedule_manager, sample_schedule):
        """Test active_days property returns all days."""
        schedule = TaskSchedule(sample_schedule, schedule_manager)
        assert len(schedule.active_days) == 7
        assert "Monday" in schedule.active_days
        assert "Sunday" in schedule.active_days

    def test_active_days_weekdays_only(self, schedule_manager, sample_schedule):
        """Test active_days with weekdays only."""
        sample_schedule["saturday"] = False
        sample_schedule["sunday"] = False
        schedule = TaskSchedule(sample_schedule, schedule_manager)
        assert len(schedule.active_days) == 5
        assert "Saturday" not in schedule.active_days
        assert "Sunday" not in schedule.active_days


class TestTaskScheduleManager:
    """Tests for TaskScheduleManager."""

    def test_list_returns_schedules(self, schedule_manager, mock_client, sample_schedule):
        """Test listing schedules."""
        mock_client._request.return_value = [sample_schedule]

        schedules = schedule_manager.list()

        assert len(schedules) == 1
        assert isinstance(schedules[0], TaskSchedule)
        assert schedules[0].name == "Nightly"
        mock_client._request.assert_called_once()

    def test_list_empty(self, schedule_manager, mock_client):
        """Test listing returns empty list when no results."""
        mock_client._request.return_value = None

        schedules = schedule_manager.list()

        assert schedules == []

    def test_list_with_enabled_filter(self, schedule_manager, mock_client, sample_schedule):
        """Test listing with enabled filter."""
        mock_client._request.return_value = [sample_schedule]

        schedules = schedule_manager.list(enabled=True)

        assert len(schedules) == 1
        call_args = mock_client._request.call_args
        assert "enabled eq true" in call_args.kwargs.get("params", {}).get("filter", "")

    def test_get_by_key(self, schedule_manager, mock_client, sample_schedule):
        """Test getting schedule by key."""
        mock_client._request.return_value = sample_schedule

        schedule = schedule_manager.get(key=1)

        assert isinstance(schedule, TaskSchedule)
        assert schedule.name == "Nightly"

    def test_get_by_name(self, schedule_manager, mock_client, sample_schedule):
        """Test getting schedule by name."""
        mock_client._request.return_value = [sample_schedule]

        schedule = schedule_manager.get(name="Nightly")

        assert schedule.name == "Nightly"

    def test_get_not_found(self, schedule_manager, mock_client):
        """Test get raises NotFoundError when not found."""
        mock_client._request.return_value = None

        with pytest.raises(NotFoundError):
            schedule_manager.get(key=999)

    def test_create_schedule(self, schedule_manager, mock_client, sample_schedule):
        """Test creating a schedule."""
        mock_client._request.side_effect = [{"$key": 1}, sample_schedule]

        schedule = schedule_manager.create(
            name="Nightly",
            repeat_every="day",
            start_time_of_day=7200,
        )

        assert schedule.name == "Nightly"
        assert mock_client._request.call_count == 2

    def test_update_schedule(self, schedule_manager, mock_client, sample_schedule):
        """Test updating a schedule."""
        mock_client._request.side_effect = [None, sample_schedule]

        schedule = schedule_manager.update(1, name="Updated Name")

        assert schedule.name == "Nightly"  # Returns original from get
        assert mock_client._request.call_count == 2

    def test_delete_schedule(self, schedule_manager, mock_client):
        """Test deleting a schedule."""
        mock_client._request.return_value = None

        schedule_manager.delete(1)

        mock_client._request.assert_called_with("DELETE", "task_schedules/1")

    def test_enable_schedule(self, schedule_manager, mock_client, sample_schedule):
        """Test enabling a schedule."""
        mock_client._request.side_effect = [None, sample_schedule]

        schedule = schedule_manager.enable(1)

        assert schedule.is_enabled

    def test_disable_schedule(self, schedule_manager, mock_client, sample_schedule):
        """Test disabling a schedule."""
        sample_schedule["enabled"] = False
        mock_client._request.side_effect = [None, sample_schedule]

        schedule_manager.disable(1)

        call_args = mock_client._request.call_args_list[0]
        assert call_args.kwargs.get("json_data", {}).get("enabled") is False


# =============================================================================
# TaskScheduleTrigger Tests
# =============================================================================


class TestTaskScheduleTrigger:
    """Tests for TaskScheduleTrigger model."""

    def test_task_key(self, trigger_manager, sample_trigger):
        """Test task_key property."""
        trigger = TaskScheduleTrigger(sample_trigger, trigger_manager)
        assert trigger.task_key == 1

    def test_schedule_key(self, trigger_manager, sample_trigger):
        """Test schedule_key property."""
        trigger = TaskScheduleTrigger(sample_trigger, trigger_manager)
        assert trigger.schedule_key == 1

    def test_is_schedule_enabled(self, trigger_manager, sample_trigger):
        """Test is_schedule_enabled property."""
        trigger = TaskScheduleTrigger(sample_trigger, trigger_manager)
        assert trigger.is_schedule_enabled is True


class TestTaskScheduleTriggerManager:
    """Tests for TaskScheduleTriggerManager."""

    def test_list_returns_triggers(self, trigger_manager, mock_client, sample_trigger):
        """Test listing triggers."""
        mock_client._request.return_value = [sample_trigger]

        triggers = trigger_manager.list()

        assert len(triggers) == 1
        assert isinstance(triggers[0], TaskScheduleTrigger)

    def test_list_scoped_to_task(self, scoped_trigger_manager, mock_client, sample_trigger):
        """Test scoped trigger manager filters by task."""
        mock_client._request.return_value = [sample_trigger]

        scoped_trigger_manager.list()

        call_args = mock_client._request.call_args
        assert "task eq 1" in call_args.kwargs.get("params", {}).get("filter", "")

    def test_create_trigger(self, trigger_manager, mock_client, sample_trigger):
        """Test creating a trigger."""
        mock_client._request.side_effect = [{"$key": 1}, sample_trigger]

        trigger = trigger_manager.create(task=1, schedule=1)

        assert trigger.task_key == 1
        assert trigger.schedule_key == 1

    def test_delete_trigger(self, trigger_manager, mock_client):
        """Test deleting a trigger."""
        mock_client._request.return_value = None

        trigger_manager.delete(1)

        mock_client._request.assert_called_with("DELETE", "task_schedule_triggers/1")

    def test_trigger_action(self, trigger_manager, mock_client):
        """Test trigger action."""
        mock_client._request.return_value = {"task": "started"}

        trigger_manager.trigger(1)

        mock_client._request.assert_called_with(
            "PUT", "task_schedule_triggers/1?action=trigger", json_data={}
        )


# =============================================================================
# TaskEvent Tests
# =============================================================================


class TestTaskEvent:
    """Tests for TaskEvent model."""

    def test_owner_key(self, event_manager, sample_event):
        """Test owner_key property."""
        event = TaskEvent(sample_event, event_manager)
        assert event.owner_key == 10

    def test_event_type(self, event_manager, sample_event):
        """Test event_type property."""
        event = TaskEvent(sample_event, event_manager)
        assert event.event_type == "poweron"

    def test_task_key(self, event_manager, sample_event):
        """Test task_key property."""
        event = TaskEvent(sample_event, event_manager)
        assert event.task_key == 1

    def test_event_filters(self, event_manager, sample_event):
        """Test event_filters property."""
        event = TaskEvent(sample_event, event_manager)
        assert event.event_filters == {"status": "running"}

    def test_event_context(self, event_manager, sample_event):
        """Test event_context property."""
        event = TaskEvent(sample_event, event_manager)
        assert event.event_context == {"notify": True}


class TestTaskEventManager:
    """Tests for TaskEventManager."""

    def test_list_returns_events(self, event_manager, mock_client, sample_event):
        """Test listing events."""
        mock_client._request.return_value = [sample_event]

        events = event_manager.list()

        assert len(events) == 1
        assert isinstance(events[0], TaskEvent)

    def test_list_scoped_to_task(self, scoped_event_manager, mock_client, sample_event):
        """Test scoped event manager filters by task."""
        mock_client._request.return_value = [sample_event]

        scoped_event_manager.list()

        call_args = mock_client._request.call_args
        assert "task eq 1" in call_args.kwargs.get("params", {}).get("filter", "")

    def test_list_by_table(self, event_manager, mock_client, sample_event):
        """Test filtering events by table."""
        mock_client._request.return_value = [sample_event]

        event_manager.list(table="vms")

        call_args = mock_client._request.call_args
        assert "table eq 'vms'" in call_args.kwargs.get("params", {}).get("filter", "")

    def test_create_event(self, event_manager, mock_client, sample_event):
        """Test creating an event."""
        mock_client._request.side_effect = [{"$key": 1}, sample_event]

        event = event_manager.create(task=1, owner=10, event="poweron")

        assert event.task_key == 1
        assert event.owner_key == 10

    def test_delete_event(self, event_manager, mock_client):
        """Test deleting an event."""
        mock_client._request.return_value = None

        event_manager.delete(1)

        mock_client._request.assert_called_with("DELETE", "task_events/1")

    def test_trigger_event(self, event_manager, mock_client):
        """Test trigger action."""
        mock_client._request.return_value = {"task": "started"}

        event_manager.trigger(1, context={"key": "value"})

        mock_client._request.assert_called_with(
            "PUT", "task_events/1?action=trigger", json_data={"context": {"key": "value"}}
        )


# =============================================================================
# TaskScript Tests
# =============================================================================


class TestTaskScript:
    """Tests for TaskScript model."""

    def test_script_code(self, script_manager, sample_script):
        """Test script_code property."""
        script = TaskScript(sample_script, script_manager)
        assert "Cleanup started" in script.script_code

    def test_settings(self, script_manager, sample_script):
        """Test settings property."""
        script = TaskScript(sample_script, script_manager)
        assert script.settings == {"questions": []}

    def test_task_count(self, script_manager, sample_script):
        """Test task_count property."""
        script = TaskScript(sample_script, script_manager)
        assert script.task_count == 2


class TestTaskScriptManager:
    """Tests for TaskScriptManager."""

    def test_list_returns_scripts(self, script_manager, mock_client, sample_script):
        """Test listing scripts."""
        mock_client._request.return_value = [sample_script]

        scripts = script_manager.list()

        assert len(scripts) == 1
        assert isinstance(scripts[0], TaskScript)
        assert scripts[0].name == "Cleanup Script"

    def test_get_by_key(self, script_manager, mock_client, sample_script):
        """Test getting script by key."""
        mock_client._request.return_value = sample_script

        script = script_manager.get(key=1)

        assert script.name == "Cleanup Script"

    def test_get_by_name(self, script_manager, mock_client, sample_script):
        """Test getting script by name."""
        mock_client._request.return_value = [sample_script]

        script = script_manager.get(name="Cleanup Script")

        assert script.name == "Cleanup Script"

    def test_create_script(self, script_manager, mock_client, sample_script):
        """Test creating a script."""
        mock_client._request.side_effect = [{"$key": 1}, sample_script]

        script = script_manager.create(
            name="Cleanup Script",
            script="log('Cleanup started')",
            description="Removes old files",
        )

        assert script.name == "Cleanup Script"

    def test_update_script(self, script_manager, mock_client, sample_script):
        """Test updating a script."""
        mock_client._request.side_effect = [None, sample_script]

        script_manager.update(1, description="Updated description")

        assert mock_client._request.call_count == 2

    def test_delete_script(self, script_manager, mock_client):
        """Test deleting a script."""
        mock_client._request.return_value = None

        script_manager.delete(1)

        mock_client._request.assert_called_with("DELETE", "task_scripts/1")

    def test_run_script(self, script_manager, mock_client):
        """Test running a script."""
        mock_client._request.return_value = {"task": "started"}

        script_manager.run(1, target_vm=10)

        mock_client._request.assert_called_with(
            "PUT", "task_scripts/1?action=run", json_data={"target_vm": 10}
        )


# =============================================================================
# Enhanced Task Tests (CRUD)
# =============================================================================


class TestTaskEnhanced:
    """Tests for enhanced Task model with triggers/events."""

    def test_owner_table(self, task_manager, sample_task):
        """Test owner_table property."""
        task = Task(sample_task, task_manager)
        assert task.owner_table == "vms"

    def test_action_type(self, task_manager, sample_task):
        """Test action_type property."""
        task = Task(sample_task, task_manager)
        assert task.action_type == "snapshot"

    def test_is_delete_after_run(self, task_manager, sample_task):
        """Test is_delete_after_run property."""
        task = Task(sample_task, task_manager)
        assert task.is_delete_after_run is False

    def test_trigger_count(self, task_manager, sample_task):
        """Test trigger_count property."""
        task = Task(sample_task, task_manager)
        assert task.trigger_count == 2

    def test_event_count(self, task_manager, sample_task):
        """Test event_count property."""
        task = Task(sample_task, task_manager)
        assert task.event_count == 1

    def test_triggers_property(self, task_manager, mock_client, sample_task):
        """Test triggers property returns scoped manager."""
        task = Task(sample_task, task_manager)
        triggers = task.triggers
        assert isinstance(triggers, TaskScheduleTriggerManager)

    def test_events_property(self, task_manager, mock_client, sample_task):
        """Test events property returns scoped manager."""
        task = Task(sample_task, task_manager)
        events = task.events
        assert isinstance(events, TaskEventManager)


class TestTaskManagerCRUD:
    """Tests for TaskManager CRUD operations."""

    def test_create_task(self, task_manager, mock_client, sample_task):
        """Test creating a task."""
        mock_client._request.side_effect = [{"$key": 1}, sample_task]

        task = task_manager.create(
            name="Daily Backup",
            owner=10,
            action="snapshot",
            description="Daily backup",
        )

        assert task.name == "Daily Backup"
        # Verify POST was called first
        first_call = mock_client._request.call_args_list[0]
        assert first_call.args[0] == "POST"
        assert first_call.args[1] == "tasks"

    def test_update_task(self, task_manager, mock_client, sample_task):
        """Test updating a task."""
        mock_client._request.side_effect = [None, sample_task]

        task_manager.update(1, description="Updated description", enabled=False)

        first_call = mock_client._request.call_args_list[0]
        assert first_call.args[0] == "PUT"
        json_data = first_call.kwargs.get("json_data", {})
        assert json_data.get("description") == "Updated description"
        assert json_data.get("enabled") is False

    def test_delete_task(self, task_manager, mock_client):
        """Test deleting a task."""
        mock_client._request.return_value = None

        task_manager.delete(1)

        mock_client._request.assert_called_with("DELETE", "tasks/1")

    def test_triggers_method(self, task_manager, mock_client):
        """Test triggers method returns scoped manager."""
        manager = task_manager.triggers(1)
        assert isinstance(manager, TaskScheduleTriggerManager)

    def test_events_method(self, task_manager, mock_client):
        """Test events method returns scoped manager."""
        manager = task_manager.events(1)
        assert isinstance(manager, TaskEventManager)

    def test_list_by_owner(self, task_manager, mock_client, sample_task):
        """Test listing tasks by owner."""
        mock_client._request.return_value = [sample_task]

        task_manager.list_by_owner(10)

        call_args = mock_client._request.call_args
        assert "owner eq 10" in call_args.kwargs.get("params", {}).get("filter", "")

    def test_list_by_action(self, task_manager, mock_client, sample_task):
        """Test listing tasks by action."""
        mock_client._request.return_value = [sample_task]

        task_manager.list_by_action("snapshot")

        call_args = mock_client._request.call_args
        assert "action eq 'snapshot'" in call_args.kwargs.get("params", {}).get("filter", "")
