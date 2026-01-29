"""Unit tests for Task operations."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from pyvergeos import VergeClient
from pyvergeos.exceptions import NotFoundError, TaskError, TaskTimeoutError
from pyvergeos.resources.tasks import Task

# =============================================================================
# Task Model Tests
# =============================================================================


class TestTask:
    """Unit tests for Task model."""

    def test_task_properties(self, mock_client: VergeClient) -> None:
        """Test Task property accessors."""
        data = {
            "$key": 1,
            "name": "Test Task",
            "description": "Test task description",
            "enabled": True,
            "status": "idle",
            "action": "snapshot",
            "action_display": "Create Snapshot",
            "table": "vms",
            "owner": 123,
            "owner_display": "VM: test-vm",
            "creator": 1,
            "creator_display": "admin",
            "last_run": "2024-01-15 10:30:00",
            "delete_after_run": False,
            "id": "abc123def456789012345678901234567890abcd",
        }
        task = Task(data, mock_client.tasks)

        assert task.key == 1
        assert task.name == "Test Task"
        assert task.description == "Test task description"
        assert task.is_enabled is True
        assert task.is_running is False
        assert task.is_complete is True
        assert task.has_error is False
        assert task.get("action") == "snapshot"
        assert task.get("action_display") == "Create Snapshot"
        assert task.owner_key == 123
        assert task.owner_display == "VM: test-vm"
        assert task.creator_key == 1
        assert task.creator_display == "admin"
        assert task.task_id == "abc123def456789012345678901234567890abcd"

    def test_task_is_running(self, mock_client: VergeClient) -> None:
        """Test Task.is_running returns True for running task."""
        data = {"$key": 1, "status": "running"}
        task = Task(data, mock_client.tasks)

        assert task.is_running is True
        assert task.is_complete is False

    def test_task_is_complete(self, mock_client: VergeClient) -> None:
        """Test Task.is_complete returns True for idle task."""
        data = {"$key": 1, "status": "idle"}
        task = Task(data, mock_client.tasks)

        assert task.is_complete is True
        assert task.is_running is False

    def test_task_has_error(self, mock_client: VergeClient) -> None:
        """Test Task.has_error returns True for error status."""
        data = {"$key": 1, "status": "error", "error": "Task failed"}
        task = Task(data, mock_client.tasks)

        assert task.has_error is True
        assert task.is_complete is False
        assert task.is_running is False

    def test_task_is_enabled_true(self, mock_client: VergeClient) -> None:
        """Test Task.is_enabled returns True when enabled."""
        data = {"$key": 1, "enabled": True}
        task = Task(data, mock_client.tasks)

        assert task.is_enabled is True

    def test_task_is_enabled_false(self, mock_client: VergeClient) -> None:
        """Test Task.is_enabled returns False when disabled."""
        data = {"$key": 1, "enabled": False}
        task = Task(data, mock_client.tasks)

        assert task.is_enabled is False

    def test_task_progress(self, mock_client: VergeClient) -> None:
        """Test Task.progress returns progress value."""
        data = {"$key": 1, "progress": 75}
        task = Task(data, mock_client.tasks)

        assert task.progress == 75

    def test_task_progress_default(self, mock_client: VergeClient) -> None:
        """Test Task.progress returns 0 when not set."""
        data = {"$key": 1}
        task = Task(data, mock_client.tasks)

        assert task.progress == 0

    def test_task_owner_key_none(self, mock_client: VergeClient) -> None:
        """Test Task.owner_key returns None when not set."""
        data = {"$key": 1}
        task = Task(data, mock_client.tasks)

        assert task.owner_key is None

    def test_task_creator_key_none(self, mock_client: VergeClient) -> None:
        """Test Task.creator_key returns None when not set."""
        data = {"$key": 1}
        task = Task(data, mock_client.tasks)

        assert task.creator_key is None

    def test_task_repr(self, mock_client: VergeClient) -> None:
        """Test Task string representation."""
        data = {"$key": 1, "name": "Backup VM"}
        task = Task(data, mock_client.tasks)

        repr_str = repr(task)
        assert "Task" in repr_str
        assert "key=1" in repr_str
        assert "Backup VM" in repr_str


# =============================================================================
# TaskManager Tests - List Operations
# =============================================================================


class TestTaskManagerList:
    """Unit tests for TaskManager list operations."""

    def test_list_tasks(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test listing all tasks."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "name": "Task 1", "status": "idle", "enabled": True},
            {"$key": 2, "name": "Task 2", "status": "running", "enabled": True},
            {"$key": 3, "name": "Task 3", "status": "idle", "enabled": False},
        ]

        tasks = mock_client.tasks.list()

        assert len(tasks) == 3
        assert tasks[0].name == "Task 1"
        assert tasks[1].name == "Task 2"
        assert tasks[2].name == "Task 3"

    def test_list_tasks_empty(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test listing tasks returns empty list when none exist."""
        mock_session.request.return_value.json.return_value = []

        tasks = mock_client.tasks.list()

        assert tasks == []

    def test_list_tasks_running_filter(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test listing running tasks."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 2, "name": "Running Task", "status": "running"}
        ]

        tasks = mock_client.tasks.list(running=True)

        assert len(tasks) == 1
        assert tasks[0].name == "Running Task"
        # Verify the filter was used
        call_args = mock_session.request.call_args
        assert "status eq 'running'" in str(call_args)

    def test_list_tasks_idle_filter(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test listing idle tasks (running=False)."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "name": "Idle Task", "status": "idle"}
        ]

        tasks = mock_client.tasks.list(running=False)

        assert len(tasks) == 1
        # Verify the filter was used
        call_args = mock_session.request.call_args
        assert "status eq 'idle'" in str(call_args)

    def test_list_tasks_status_filter(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test listing tasks by status string."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "name": "Task", "status": "idle"}
        ]

        tasks = mock_client.tasks.list(status="idle")

        assert len(tasks) == 1
        call_args = mock_session.request.call_args
        assert "status eq 'idle'" in str(call_args)

    def test_list_tasks_enabled_filter(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test listing enabled tasks."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "name": "Enabled Task", "enabled": True}
        ]

        tasks = mock_client.tasks.list(enabled=True)

        assert len(tasks) == 1
        call_args = mock_session.request.call_args
        assert "enabled eq true" in str(call_args)

    def test_list_tasks_disabled_filter(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test listing disabled tasks."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "name": "Disabled Task", "enabled": False}
        ]

        tasks = mock_client.tasks.list(enabled=False)

        assert len(tasks) == 1
        call_args = mock_session.request.call_args
        assert "enabled eq false" in str(call_args)

    def test_list_tasks_name_filter_exact(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test listing tasks by exact name."""
        mock_session.request.return_value.json.return_value = [{"$key": 1, "name": "Backup VM"}]

        tasks = mock_client.tasks.list(name="Backup VM")

        assert len(tasks) == 1
        call_args = mock_session.request.call_args
        assert "name eq 'Backup VM'" in str(call_args)

    def test_list_tasks_name_filter_wildcard(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test listing tasks by name with wildcard."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "name": "Backup VM 1"},
            {"$key": 2, "name": "Backup VM 2"},
        ]

        tasks = mock_client.tasks.list(name="Backup*")

        assert len(tasks) == 2
        call_args = mock_session.request.call_args
        assert "name ct 'Backup'" in str(call_args)

    def test_list_tasks_multiple_filters(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test listing tasks with multiple filters."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "name": "Backup", "status": "idle", "enabled": True}
        ]

        tasks = mock_client.tasks.list(enabled=True, running=False)

        assert len(tasks) == 1
        call_args = mock_session.request.call_args
        assert "enabled eq true" in str(call_args)
        assert "status eq 'idle'" in str(call_args)

    def test_list_running(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test list_running convenience method."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "name": "Running Task", "status": "running"}
        ]

        tasks = mock_client.tasks.list_running()

        assert len(tasks) == 1
        call_args = mock_session.request.call_args
        assert "status eq 'running'" in str(call_args)

    def test_list_idle(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test list_idle convenience method."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "name": "Idle Task", "status": "idle"}
        ]

        tasks = mock_client.tasks.list_idle()

        assert len(tasks) == 1
        call_args = mock_session.request.call_args
        assert "status eq 'idle'" in str(call_args)

    def test_list_enabled(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test list_enabled convenience method."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "name": "Enabled Task", "enabled": True}
        ]

        tasks = mock_client.tasks.list_enabled()

        assert len(tasks) == 1
        call_args = mock_session.request.call_args
        assert "enabled eq true" in str(call_args)

    def test_list_disabled(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test list_disabled convenience method."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "name": "Disabled Task", "enabled": False}
        ]

        tasks = mock_client.tasks.list_disabled()

        assert len(tasks) == 1
        call_args = mock_session.request.call_args
        assert "enabled eq false" in str(call_args)

    def test_list_with_limit(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test listing tasks with limit."""
        mock_session.request.return_value.json.return_value = [{"$key": 1, "name": "Task 1"}]

        mock_client.tasks.list(limit=1)

        call_args = mock_session.request.call_args
        assert "limit" in str(call_args) or call_args.kwargs.get("params", {}).get("limit") == 1


# =============================================================================
# TaskManager Tests - Get Operations
# =============================================================================


class TestTaskManagerGet:
    """Unit tests for TaskManager get operations."""

    def test_get_task_by_key(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test getting a task by key."""
        mock_session.request.return_value.json.return_value = {
            "$key": 1,
            "name": "Test Task",
            "status": "idle",
            "enabled": True,
        }

        task = mock_client.tasks.get(1)

        assert task.key == 1
        assert task.name == "Test Task"

    def test_get_task_by_name(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test getting a task by name."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "name": "Backup VM", "status": "idle"}
        ]

        task = mock_client.tasks.get(name="Backup VM")

        assert task.name == "Backup VM"
        call_args = mock_session.request.call_args
        assert "name eq 'Backup VM'" in str(call_args)

    def test_get_task_not_found_by_key(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test NotFoundError when task not found by key."""
        mock_session.request.return_value.json.return_value = None
        mock_session.request.return_value.text = ""

        with pytest.raises(NotFoundError):
            mock_client.tasks.get(999)

    def test_get_task_not_found_by_name(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test NotFoundError when task not found by name."""
        mock_session.request.return_value.json.return_value = []

        with pytest.raises(NotFoundError):
            mock_client.tasks.get(name="Nonexistent")

    def test_get_task_requires_key_or_name(self, mock_client: VergeClient) -> None:
        """Test that get() requires key or name parameter."""
        with pytest.raises(ValueError, match="Either key or name must be provided"):
            mock_client.tasks.get()


# =============================================================================
# TaskManager Tests - Enable/Disable Operations
# =============================================================================


class TestTaskManagerEnableDisable:
    """Unit tests for TaskManager enable/disable operations."""

    def test_enable_task(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test enabling a task."""
        # First call is the PUT to enable, second is GET to return updated task
        mock_session.request.return_value.json.side_effect = [
            None,  # PUT returns nothing
            {"$key": 1, "name": "Task", "enabled": True, "status": "idle"},
        ]

        task = mock_client.tasks.enable(1)

        assert task.is_enabled is True
        # Verify PUT was called with enabled=true
        calls = mock_session.request.call_args_list
        # Find the PUT call - it will have json={"enabled": True}
        put_calls = [c for c in calls if c.kwargs.get("json") == {"enabled": True}]
        assert len(put_calls) == 1

    def test_disable_task(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test disabling a task."""
        mock_session.request.return_value.json.side_effect = [
            None,  # PUT returns nothing
            {"$key": 1, "name": "Task", "enabled": False, "status": "idle"},
        ]

        task = mock_client.tasks.disable(1)

        assert task.is_enabled is False
        # Verify PUT was called with enabled=false
        calls = mock_session.request.call_args_list
        # Find the PUT call - it will have json={"enabled": False}
        put_calls = [c for c in calls if c.kwargs.get("json") == {"enabled": False}]
        assert len(put_calls) == 1

    def test_task_object_enable(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test enabling task via Task object method."""
        mock_session.request.return_value.json.side_effect = [
            None,
            {"$key": 1, "name": "Task", "enabled": True, "status": "idle"},
        ]

        data = {"$key": 1, "name": "Task", "enabled": False}
        task = Task(data, mock_client.tasks)
        updated = task.enable()

        assert updated.is_enabled is True

    def test_task_object_disable(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test disabling task via Task object method."""
        mock_session.request.return_value.json.side_effect = [
            None,
            {"$key": 1, "name": "Task", "enabled": False, "status": "idle"},
        ]

        data = {"$key": 1, "name": "Task", "enabled": True}
        task = Task(data, mock_client.tasks)
        updated = task.disable()

        assert updated.is_enabled is False


# =============================================================================
# TaskManager Tests - Execute Operation
# =============================================================================


class TestTaskManagerExecute:
    """Unit tests for TaskManager execute operation."""

    def test_execute_task(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test executing a task."""
        mock_session.request.return_value.json.side_effect = [
            {"task": 1},  # Action response
            {"$key": 1, "name": "Task", "status": "running"},  # GET response
        ]

        task = mock_client.tasks.execute(1)

        assert task.name == "Task"
        # Verify action was called
        calls = mock_session.request.call_args_list
        action_call = [c for c in calls if "action=execute" in str(c)][0]
        assert action_call is not None

    def test_execute_task_with_params(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test executing a task with parameters."""
        mock_session.request.return_value.json.side_effect = [
            {"task": 1},
            {"$key": 1, "name": "Task", "status": "running"},
        ]

        mock_client.tasks.execute(1, custom_param="value")

        calls = mock_session.request.call_args_list
        action_call = [c for c in calls if "action=execute" in str(c)][0]
        assert action_call.kwargs.get("json") == {"params": {"custom_param": "value"}}

    def test_task_object_execute(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test executing task via Task object method."""
        mock_session.request.return_value.json.side_effect = [
            {"task": 1},
            {"$key": 1, "name": "Task", "status": "running"},
        ]

        data = {"$key": 1, "name": "Task", "status": "idle"}
        task = Task(data, mock_client.tasks)
        updated = task.execute()

        assert updated.name == "Task"


# =============================================================================
# TaskManager Tests - Wait Operation
# =============================================================================


class TestTaskManagerWait:
    """Unit tests for TaskManager wait operation."""

    def test_wait_task_completes_immediately(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test waiting for task that is already complete."""
        mock_session.request.return_value.json.return_value = {
            "$key": 1,
            "name": "Task",
            "status": "idle",
        }

        task = mock_client.tasks.wait(1)

        assert task.is_complete is True

    def test_wait_task_completes_after_polling(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test waiting for task that completes after polling."""
        mock_session.request.return_value.json.side_effect = [
            {"$key": 1, "name": "Task", "status": "running"},
            {"$key": 1, "name": "Task", "status": "running"},
            {"$key": 1, "name": "Task", "status": "idle"},
        ]

        with patch("pyvergeos.resources.tasks.time.sleep"):
            task = mock_client.tasks.wait(1, poll_interval=1)

        assert task.is_complete is True

    def test_wait_task_timeout(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test waiting for task that times out."""
        mock_session.request.return_value.json.return_value = {
            "$key": 1,
            "name": "Task",
            "status": "running",
        }

        with (
            patch("pyvergeos.resources.tasks.time.sleep"),
            patch("pyvergeos.resources.tasks.time.time") as mock_time,
        ):
            # Simulate time passing beyond timeout
            mock_time.side_effect = [0, 0, 10]  # Start, first check, timeout check
            with pytest.raises(TaskTimeoutError) as exc_info:
                mock_client.tasks.wait(1, timeout=5)

        assert exc_info.value.task_id == 1

    def test_wait_task_error(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test waiting for task that errors."""
        mock_session.request.return_value.json.return_value = {
            "$key": 1,
            "name": "Task",
            "status": "error",
            "error": "Something went wrong",
        }

        with pytest.raises(TaskError) as exc_info:
            mock_client.tasks.wait(1)

        assert exc_info.value.task_id == 1
        assert "Something went wrong" in str(exc_info.value)

    def test_wait_task_error_no_raise(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test waiting for task that errors with raise_on_error=False."""
        mock_session.request.return_value.json.return_value = {
            "$key": 1,
            "name": "Task",
            "status": "error",
            "error": "Something went wrong",
        }

        task = mock_client.tasks.wait(1, raise_on_error=False)

        assert task.has_error is True

    def test_wait_infinite_timeout(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test waiting with infinite timeout (timeout=0)."""
        mock_session.request.return_value.json.side_effect = [
            {"$key": 1, "status": "running"},
            {"$key": 1, "status": "idle"},
        ]

        with patch("pyvergeos.resources.tasks.time.sleep"):
            task = mock_client.tasks.wait(1, timeout=0, poll_interval=1)

        assert task.is_complete is True

    def test_task_object_wait(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test waiting via Task object method."""
        mock_session.request.return_value.json.return_value = {
            "$key": 1,
            "name": "Task",
            "status": "idle",
        }

        data = {"$key": 1, "name": "Task", "status": "running"}
        task = Task(data, mock_client.tasks)
        completed = task.wait()

        assert completed.is_complete is True


# =============================================================================
# TaskManager Tests - Cancel Operation
# =============================================================================


class TestTaskManagerCancel:
    """Unit tests for TaskManager cancel operation."""

    def test_cancel_task(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test cancelling a task."""
        mock_session.request.return_value.json.side_effect = [
            {"cancelled": True},  # Action response
            {"$key": 1, "name": "Task", "status": "idle"},  # GET response
        ]

        task = mock_client.tasks.cancel(1)

        assert task.name == "Task"
        # Verify cancel action was called
        calls = mock_session.request.call_args_list
        cancel_call = [c for c in calls if "action=cancel" in str(c)][0]
        assert cancel_call is not None


# =============================================================================
# TaskManager Tests - Default Fields
# =============================================================================


class TestTaskManagerDefaultFields:
    """Unit tests for TaskManager default fields."""

    def test_list_uses_default_fields(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test that list() uses default fields."""
        mock_session.request.return_value.json.return_value = []

        mock_client.tasks.list()

        call_args = mock_session.request.call_args
        params = call_args.kwargs.get("params", {})
        fields = params.get("fields", "")

        # Check for key default fields
        assert "$key" in fields
        assert "name" in fields
        assert "enabled" in fields
        assert "status" in fields
        assert "owner_display" in fields

    def test_list_custom_fields(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test that list() can use custom fields."""
        mock_session.request.return_value.json.return_value = []

        mock_client.tasks.list(fields=["$key", "name"])

        call_args = mock_session.request.call_args
        params = call_args.kwargs.get("params", {})
        fields = params.get("fields", "")

        assert fields == "$key,name"

    def test_get_uses_default_fields(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test that get() uses default fields."""
        mock_session.request.return_value.json.return_value = {
            "$key": 1,
            "name": "Task",
        }

        mock_client.tasks.get(1)

        call_args = mock_session.request.call_args
        params = call_args.kwargs.get("params", {})
        fields = params.get("fields", "")

        assert "$key" in fields
        assert "name" in fields
