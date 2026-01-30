"""Integration tests for Task Scheduling System.

These tests require a live VergeOS system and will be skipped
if the environment variables are not set.

Tests cover:
- TaskScheduleManager
- TaskScheduleTriggerManager
- TaskEventManager
- TaskScriptManager
- Enhanced TaskManager CRUD operations
"""

from __future__ import annotations

import pytest

from pyvergeos import VergeClient
from pyvergeos.exceptions import NotFoundError

# =============================================================================
# Task Schedule Integration Tests
# =============================================================================


@pytest.mark.integration
class TestTaskScheduleListIntegration:
    """Integration tests for TaskScheduleManager list operations."""

    def test_list_schedules(self, live_client: VergeClient) -> None:
        """Test listing task schedules from live system."""
        schedules = live_client.task_schedules.list()

        assert isinstance(schedules, list)
        for schedule in schedules:
            assert hasattr(schedule, "key")
            assert hasattr(schedule, "name")
            assert hasattr(schedule, "is_enabled")

    def test_list_enabled_schedules(self, live_client: VergeClient) -> None:
        """Test listing enabled schedules."""
        schedules = live_client.task_schedules.list_enabled()

        assert isinstance(schedules, list)
        for schedule in schedules:
            assert schedule.is_enabled is True

    def test_list_disabled_schedules(self, live_client: VergeClient) -> None:
        """Test listing disabled schedules."""
        schedules = live_client.task_schedules.list_disabled()

        assert isinstance(schedules, list)
        for schedule in schedules:
            assert schedule.is_enabled is False


@pytest.mark.integration
class TestTaskScheduleGetIntegration:
    """Integration tests for TaskScheduleManager get operations."""

    def test_get_schedule_by_key(self, live_client: VergeClient) -> None:
        """Test getting a schedule by key."""
        schedules = live_client.task_schedules.list()
        if not schedules:
            pytest.skip("No schedules available")

        schedule = live_client.task_schedules.get(schedules[0].key)
        assert schedule.key == schedules[0].key
        assert schedule.name == schedules[0].name

    def test_get_schedule_by_name(self, live_client: VergeClient) -> None:
        """Test getting a schedule by name."""
        schedules = live_client.task_schedules.list()
        if not schedules:
            pytest.skip("No schedules available")

        schedule = live_client.task_schedules.get(name=schedules[0].name)
        assert schedule.name == schedules[0].name

    def test_get_nonexistent_schedule(self, live_client: VergeClient) -> None:
        """Test NotFoundError for nonexistent schedule."""
        with pytest.raises(NotFoundError):
            live_client.task_schedules.get(999999)


@pytest.mark.integration
class TestTaskSchedulePropertiesIntegration:
    """Integration tests for TaskSchedule properties."""

    def test_schedule_properties(self, live_client: VergeClient) -> None:
        """Test TaskSchedule property accessors."""
        schedules = live_client.task_schedules.list()
        if not schedules:
            pytest.skip("No schedules available")

        schedule = schedules[0]

        # Basic properties
        assert schedule.key is not None
        assert schedule.name is not None
        assert isinstance(schedule.is_enabled, bool)
        assert isinstance(schedule.repeat_every_display, str)
        assert isinstance(schedule.repeat_count, int)
        assert isinstance(schedule.active_days, list)


@pytest.mark.integration
class TestTaskScheduleCRUDIntegration:
    """Integration tests for TaskSchedule CRUD operations."""

    def test_create_update_delete_schedule(self, live_client: VergeClient) -> None:
        """Test creating, updating, and deleting a schedule."""
        # Create
        schedule = live_client.task_schedules.create(
            name="PyVergeOS Test Schedule",
            description="Integration test schedule",
            repeat_every="day",
            start_time_of_day=3600,  # 1 AM
            enabled=False,  # Keep disabled for safety
        )

        try:
            assert schedule.name == "PyVergeOS Test Schedule"
            assert schedule.is_enabled is False
            assert schedule.get("repeat_every") == "day"

            # Update
            updated = live_client.task_schedules.update(
                schedule.key,
                description="Updated description",
                repeat_iteration=2,
            )
            assert updated.get("description") == "Updated description"
            assert updated.repeat_count == 2

        finally:
            # Delete
            live_client.task_schedules.delete(schedule.key)

            # Verify deleted
            with pytest.raises(NotFoundError):
                live_client.task_schedules.get(schedule.key)


# =============================================================================
# Task Schedule Trigger Integration Tests
# =============================================================================


@pytest.mark.integration
class TestTaskScheduleTriggerListIntegration:
    """Integration tests for TaskScheduleTriggerManager list operations."""

    def test_list_triggers(self, live_client: VergeClient) -> None:
        """Test listing task schedule triggers."""
        triggers = live_client.task_schedule_triggers.list()

        assert isinstance(triggers, list)
        for trigger in triggers:
            assert hasattr(trigger, "key")
            assert hasattr(trigger, "task_key")
            assert hasattr(trigger, "schedule_key")


@pytest.mark.integration
class TestTaskScheduleTriggerScopedIntegration:
    """Integration tests for scoped trigger managers."""

    def test_triggers_scoped_to_task(self, live_client: VergeClient) -> None:
        """Test getting triggers scoped to a task."""
        tasks = live_client.tasks.list()
        if not tasks:
            pytest.skip("No tasks available")

        task = tasks[0]
        triggers = task.triggers.list()

        assert isinstance(triggers, list)
        for trigger in triggers:
            assert trigger.task_key == task.key

    def test_triggers_scoped_to_schedule(self, live_client: VergeClient) -> None:
        """Test getting triggers scoped to a schedule."""
        schedules = live_client.task_schedules.list()
        if not schedules:
            pytest.skip("No schedules available")

        schedule = schedules[0]
        triggers = schedule.triggers.list()

        assert isinstance(triggers, list)
        for trigger in triggers:
            assert trigger.schedule_key == schedule.key


# =============================================================================
# Task Event Integration Tests
# =============================================================================


@pytest.mark.integration
class TestTaskEventListIntegration:
    """Integration tests for TaskEventManager list operations."""

    def test_list_events(self, live_client: VergeClient) -> None:
        """Test listing task events."""
        events = live_client.task_events.list()

        assert isinstance(events, list)
        for event in events:
            assert hasattr(event, "key")
            assert hasattr(event, "task_key")
            assert hasattr(event, "owner_key")

    def test_list_events_by_table(self, live_client: VergeClient) -> None:
        """Test listing events filtered by table."""
        events = live_client.task_events.list(table="vms")

        assert isinstance(events, list)
        for event in events:
            assert event.owner_table == "vms"


@pytest.mark.integration
class TestTaskEventScopedIntegration:
    """Integration tests for scoped event managers."""

    def test_events_scoped_to_task(self, live_client: VergeClient) -> None:
        """Test getting events scoped to a task."""
        tasks = live_client.tasks.list()
        if not tasks:
            pytest.skip("No tasks available")

        task = tasks[0]
        events = task.events.list()

        assert isinstance(events, list)
        for event in events:
            assert event.task_key == task.key


# =============================================================================
# Task Script Integration Tests
# =============================================================================


@pytest.mark.integration
class TestTaskScriptListIntegration:
    """Integration tests for TaskScriptManager list operations."""

    def test_list_scripts(self, live_client: VergeClient) -> None:
        """Test listing task scripts."""
        scripts = live_client.task_scripts.list()

        assert isinstance(scripts, list)
        for script in scripts:
            assert hasattr(script, "key")
            assert hasattr(script, "name")
            assert hasattr(script, "script_code")


@pytest.mark.integration
class TestTaskScriptGetIntegration:
    """Integration tests for TaskScriptManager get operations."""

    def test_get_script_by_key(self, live_client: VergeClient) -> None:
        """Test getting a script by key."""
        scripts = live_client.task_scripts.list()
        if not scripts:
            pytest.skip("No scripts available")

        script = live_client.task_scripts.get(scripts[0].key)
        assert script.key == scripts[0].key
        assert script.name == scripts[0].name

    def test_get_script_by_name(self, live_client: VergeClient) -> None:
        """Test getting a script by name."""
        scripts = live_client.task_scripts.list()
        if not scripts:
            pytest.skip("No scripts available")

        script = live_client.task_scripts.get(name=scripts[0].name)
        assert script.name == scripts[0].name


@pytest.mark.integration
class TestTaskScriptCRUDIntegration:
    """Integration tests for TaskScript CRUD operations."""

    def test_create_update_delete_script(self, live_client: VergeClient) -> None:
        """Test creating, updating, and deleting a script."""
        # Create - use valid GCS script syntax (simple return statement)
        script = live_client.task_scripts.create(
            name="PyVergeOS Test Script",
            description="Integration test script",
            script="return_success();",
            task_settings={"questions": []},
        )

        try:
            assert script.name == "PyVergeOS Test Script"
            assert "return_success" in script.script_code

            # Update
            updated = live_client.task_scripts.update(
                script.key,
                description="Updated description",
            )
            assert updated.get("description") == "Updated description"

        finally:
            # Delete
            live_client.task_scripts.delete(script.key)

            # Verify deleted
            with pytest.raises(NotFoundError):
                live_client.task_scripts.get(script.key)


# =============================================================================
# Enhanced Task Manager Integration Tests
# =============================================================================


@pytest.mark.integration
class TestTaskEnhancedIntegration:
    """Integration tests for enhanced Task properties."""

    def test_task_trigger_count(self, live_client: VergeClient) -> None:
        """Test trigger_count property."""
        tasks = live_client.tasks.list()
        if not tasks:
            pytest.skip("No tasks available")

        for task in tasks:
            assert isinstance(task.trigger_count, int)
            assert task.trigger_count >= 0

    def test_task_event_count(self, live_client: VergeClient) -> None:
        """Test event_count property."""
        tasks = live_client.tasks.list()
        if not tasks:
            pytest.skip("No tasks available")

        for task in tasks:
            assert isinstance(task.event_count, int)
            assert task.event_count >= 0

    def test_task_owner_table(self, live_client: VergeClient) -> None:
        """Test owner_table property."""
        tasks = live_client.tasks.list()
        if not tasks:
            pytest.skip("No tasks available")

        for task in tasks:
            # owner_table might be None for some tasks
            if task.owner_table is not None:
                assert isinstance(task.owner_table, str)


@pytest.mark.integration
class TestTaskManagerHelperMethods:
    """Integration tests for TaskManager helper methods."""

    def test_triggers_method(self, live_client: VergeClient) -> None:
        """Test triggers() method returns scoped manager."""
        tasks = live_client.tasks.list()
        if not tasks:
            pytest.skip("No tasks available")

        task = tasks[0]
        triggers_manager = live_client.tasks.triggers(task.key)
        triggers = triggers_manager.list()

        assert isinstance(triggers, list)
        for trigger in triggers:
            assert trigger.task_key == task.key

    def test_events_method(self, live_client: VergeClient) -> None:
        """Test events() method returns scoped manager."""
        tasks = live_client.tasks.list()
        if not tasks:
            pytest.skip("No tasks available")

        task = tasks[0]
        events_manager = live_client.tasks.events(task.key)
        events = events_manager.list()

        assert isinstance(events, list)
        for event in events:
            assert event.task_key == task.key

    def test_list_by_action(self, live_client: VergeClient) -> None:
        """Test list_by_action method."""
        # Get all tasks to find an action type
        tasks = live_client.tasks.list()
        if not tasks:
            pytest.skip("No tasks available")

        # Get first task's action
        action = tasks[0].action_type
        if not action:
            pytest.skip("No action type available")

        # Filter by that action
        filtered = live_client.tasks.list_by_action(action)

        assert isinstance(filtered, list)
        for task in filtered:
            assert task.action_type == action
