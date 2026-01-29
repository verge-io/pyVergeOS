"""Integration tests for Task operations.

These tests require a live VergeOS system and will be skipped
if the environment variables are not set.
"""

from __future__ import annotations

import pytest

from pyvergeos import VergeClient
from pyvergeos.exceptions import NotFoundError


@pytest.mark.integration
class TestTaskListIntegration:
    """Integration tests for TaskManager list operations."""

    def test_list_tasks(self, live_client: VergeClient) -> None:
        """Test listing tasks from live system."""
        tasks = live_client.tasks.list()

        # Should return a list (may be empty)
        assert isinstance(tasks, list)

        # Each task should have expected properties
        for task in tasks:
            assert hasattr(task, "key")
            assert hasattr(task, "name")
            assert hasattr(task, "is_enabled")
            assert hasattr(task, "is_running")
            assert hasattr(task, "is_complete")

    def test_list_running_tasks(self, live_client: VergeClient) -> None:
        """Test listing running tasks."""
        running_tasks = live_client.tasks.list_running()

        assert isinstance(running_tasks, list)
        for task in running_tasks:
            assert task.is_running is True

    def test_list_idle_tasks(self, live_client: VergeClient) -> None:
        """Test listing idle tasks."""
        idle_tasks = live_client.tasks.list_idle()

        assert isinstance(idle_tasks, list)
        for task in idle_tasks:
            assert task.is_complete is True

    def test_list_enabled_tasks(self, live_client: VergeClient) -> None:
        """Test listing enabled tasks."""
        enabled_tasks = live_client.tasks.list_enabled()

        assert isinstance(enabled_tasks, list)
        for task in enabled_tasks:
            assert task.is_enabled is True

    def test_list_disabled_tasks(self, live_client: VergeClient) -> None:
        """Test listing disabled tasks."""
        disabled_tasks = live_client.tasks.list_disabled()

        assert isinstance(disabled_tasks, list)
        for task in disabled_tasks:
            assert task.is_enabled is False

    def test_list_with_limit(self, live_client: VergeClient) -> None:
        """Test listing tasks with limit."""
        all_tasks = live_client.tasks.list()
        if len(all_tasks) < 2:
            pytest.skip("Need at least 2 tasks to test limit")

        limited_tasks = live_client.tasks.list(limit=1)
        assert len(limited_tasks) == 1


@pytest.mark.integration
class TestTaskGetIntegration:
    """Integration tests for TaskManager get operations."""

    def test_get_task_by_key(self, live_client: VergeClient) -> None:
        """Test getting a task by key."""
        tasks = live_client.tasks.list()
        if not tasks:
            pytest.skip("No tasks available")

        task = live_client.tasks.get(tasks[0].key)

        assert task.key == tasks[0].key
        assert task.name == tasks[0].name

    def test_get_task_by_name(self, live_client: VergeClient) -> None:
        """Test getting a task by name."""
        tasks = live_client.tasks.list()
        if not tasks:
            pytest.skip("No tasks available")

        task = live_client.tasks.get(name=tasks[0].name)

        assert task.name == tasks[0].name

    def test_get_nonexistent_task_by_key(self, live_client: VergeClient) -> None:
        """Test that NotFoundError is raised for nonexistent task."""
        with pytest.raises(NotFoundError):
            live_client.tasks.get(999999)

    def test_get_nonexistent_task_by_name(self, live_client: VergeClient) -> None:
        """Test that NotFoundError is raised for nonexistent task name."""
        with pytest.raises(NotFoundError):
            live_client.tasks.get(name="definitely_nonexistent_task_xyz123")


@pytest.mark.integration
class TestTaskPropertiesIntegration:
    """Integration tests for Task properties."""

    def test_task_properties(self, live_client: VergeClient) -> None:
        """Test Task property accessors on live data."""
        tasks = live_client.tasks.list()
        if not tasks:
            pytest.skip("No tasks available")

        task = tasks[0]

        # All tasks should have these properties accessible
        assert task.key is not None
        assert task.name is not None
        assert isinstance(task.is_enabled, bool)
        assert isinstance(task.is_running, bool)
        assert isinstance(task.is_complete, bool)
        assert isinstance(task.has_error, bool)
        assert isinstance(task.progress, int)

        # owner_display and creator_display should be strings
        assert isinstance(task.owner_display, str)
        assert isinstance(task.creator_display, str)

    def test_task_status_consistency(self, live_client: VergeClient) -> None:
        """Test that task status properties are consistent."""
        tasks = live_client.tasks.list()
        if not tasks:
            pytest.skip("No tasks available")

        for task in tasks:
            # A task should be either running or complete (unless error)
            if not task.has_error:
                assert task.is_running != task.is_complete


@pytest.mark.integration
class TestTaskEnableDisableIntegration:
    """Integration tests for task enable/disable operations."""

    def test_disable_and_enable_task(self, live_client: VergeClient) -> None:
        """Test disabling and re-enabling a task."""
        tasks = live_client.tasks.list()
        if not tasks:
            pytest.skip("No tasks available")

        # Find a task to test with
        task = tasks[0]
        original_enabled = task.is_enabled

        try:
            # Disable the task
            disabled_task = live_client.tasks.disable(task.key)
            assert disabled_task.is_enabled is False

            # Verify via fresh get
            task_after_disable = live_client.tasks.get(task.key)
            assert task_after_disable.is_enabled is False

            # Re-enable the task
            enabled_task = live_client.tasks.enable(task.key)
            assert enabled_task.is_enabled is True

            # Verify via fresh get
            task_after_enable = live_client.tasks.get(task.key)
            assert task_after_enable.is_enabled is True

        finally:
            # Restore original state
            if original_enabled:
                live_client.tasks.enable(task.key)
            else:
                live_client.tasks.disable(task.key)

    def test_task_object_enable_disable(self, live_client: VergeClient) -> None:
        """Test enable/disable via Task object methods."""
        tasks = live_client.tasks.list()
        if not tasks:
            pytest.skip("No tasks available")

        task = tasks[0]
        original_enabled = task.is_enabled

        try:
            # Disable via object method
            disabled = task.disable()
            assert disabled.is_enabled is False

            # Enable via object method
            enabled = disabled.enable()
            assert enabled.is_enabled is True

        finally:
            # Restore original state
            if original_enabled:
                live_client.tasks.enable(task.key)
            else:
                live_client.tasks.disable(task.key)


@pytest.mark.integration
class TestTaskFilteringIntegration:
    """Integration tests for task filtering."""

    def test_filter_by_status(self, live_client: VergeClient) -> None:
        """Test filtering tasks by status."""
        # Get idle tasks via filter
        idle_tasks = live_client.tasks.list(status="idle")

        for task in idle_tasks:
            assert task.get("status") == "idle"

    def test_filter_by_enabled(self, live_client: VergeClient) -> None:
        """Test filtering tasks by enabled status."""
        # Get enabled tasks
        enabled_tasks = live_client.tasks.list(enabled=True)

        for task in enabled_tasks:
            assert task.is_enabled is True

        # Get disabled tasks
        disabled_tasks = live_client.tasks.list(enabled=False)

        for task in disabled_tasks:
            assert task.is_enabled is False

    def test_multiple_filters(self, live_client: VergeClient) -> None:
        """Test combining multiple filters."""
        # Get enabled idle tasks
        tasks = live_client.tasks.list(enabled=True, running=False)

        for task in tasks:
            assert task.is_enabled is True
            assert task.is_complete is True


@pytest.mark.integration
class TestTaskWaitIntegration:
    """Integration tests for task wait functionality."""

    def test_wait_already_complete(self, live_client: VergeClient) -> None:
        """Test waiting for a task that is already complete."""
        tasks = live_client.tasks.list_idle()
        if not tasks:
            pytest.skip("No idle tasks available")

        task = tasks[0]

        # Wait should return immediately for idle task
        completed = live_client.tasks.wait(task.key, timeout=5)
        assert completed.is_complete is True

    def test_task_object_wait(self, live_client: VergeClient) -> None:
        """Test waiting via Task object method."""
        tasks = live_client.tasks.list_idle()
        if not tasks:
            pytest.skip("No idle tasks available")

        task = tasks[0]

        # Wait should return immediately
        completed = task.wait(timeout=5)
        assert completed.is_complete is True
