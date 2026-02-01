"""Unit tests for TaskScheduleTrigger operations."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from pyvergeos import VergeClient
from pyvergeos.exceptions import NotFoundError
from pyvergeos.resources.task_schedule_triggers import (
    TaskScheduleTrigger,
    TaskScheduleTriggerManager,
)

# =============================================================================
# TaskScheduleTrigger Model Tests
# =============================================================================


class TestTaskScheduleTrigger:
    """Unit tests for TaskScheduleTrigger model."""

    def test_task_schedule_trigger_properties(self, mock_client: VergeClient) -> None:
        """Test TaskScheduleTrigger property accessors."""
        data = {
            "$key": 1,
            "task": 100,
            "task_display": "Backup Task",
            "schedule": 200,
            "schedule_display": "Nightly Schedule",
            "sch_enabled": True,
            "sch_repeat_every": "Day(s)",
            "sch_start_time_of_day": 7200,
            "trigger": 0,
        }
        trigger = TaskScheduleTrigger(data, mock_client.task_schedule_triggers)

        assert trigger.key == 1
        assert trigger.task_key == 100
        assert trigger.task_display == "Backup Task"
        assert trigger.schedule_key == 200
        assert trigger.schedule_display == "Nightly Schedule"
        assert trigger.is_schedule_enabled is True
        assert trigger.schedule_repeat_every == "Day(s)"
        assert trigger.schedule_start_time == 7200

    def test_task_schedule_trigger_task_key_none(self, mock_client: VergeClient) -> None:
        """Test TaskScheduleTrigger.task_key returns None when not set."""
        data = {"$key": 1}
        trigger = TaskScheduleTrigger(data, mock_client.task_schedule_triggers)

        assert trigger.task_key is None

    def test_task_schedule_trigger_schedule_key_none(self, mock_client: VergeClient) -> None:
        """Test TaskScheduleTrigger.schedule_key returns None when not set."""
        data = {"$key": 1}
        trigger = TaskScheduleTrigger(data, mock_client.task_schedule_triggers)

        assert trigger.schedule_key is None

    def test_task_schedule_trigger_display_defaults(self, mock_client: VergeClient) -> None:
        """Test TaskScheduleTrigger display properties return empty strings when not set."""
        data = {"$key": 1}
        trigger = TaskScheduleTrigger(data, mock_client.task_schedule_triggers)

        assert trigger.task_display == ""
        assert trigger.schedule_display == ""

    def test_task_schedule_trigger_schedule_enabled_default(self, mock_client: VergeClient) -> None:
        """Test TaskScheduleTrigger.is_schedule_enabled defaults to False."""
        data = {"$key": 1}
        trigger = TaskScheduleTrigger(data, mock_client.task_schedule_triggers)

        assert trigger.is_schedule_enabled is False

    def test_task_schedule_trigger_schedule_repeat_every_none(
        self, mock_client: VergeClient
    ) -> None:
        """Test TaskScheduleTrigger.schedule_repeat_every returns None when not set."""
        data = {"$key": 1}
        trigger = TaskScheduleTrigger(data, mock_client.task_schedule_triggers)

        assert trigger.schedule_repeat_every is None

    def test_task_schedule_trigger_schedule_start_time_none(self, mock_client: VergeClient) -> None:
        """Test TaskScheduleTrigger.schedule_start_time returns None when not set."""
        data = {"$key": 1}
        trigger = TaskScheduleTrigger(data, mock_client.task_schedule_triggers)

        assert trigger.schedule_start_time is None


# =============================================================================
# TaskScheduleTriggerManager Tests - List Operations
# =============================================================================


class TestTaskScheduleTriggerManagerList:
    """Unit tests for TaskScheduleTriggerManager list operations."""

    def test_list_triggers(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test listing all task schedule triggers."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "task": 100, "schedule": 200},
            {"$key": 2, "task": 101, "schedule": 200},
            {"$key": 3, "task": 100, "schedule": 201},
        ]

        triggers = mock_client.task_schedule_triggers.list()

        assert len(triggers) == 3
        assert triggers[0].task_key == 100
        assert triggers[1].task_key == 101
        assert triggers[2].task_key == 100

    def test_list_triggers_empty(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test listing triggers returns empty list when none exist."""
        mock_session.request.return_value.json.return_value = []

        triggers = mock_client.task_schedule_triggers.list()

        assert triggers == []

    def test_list_triggers_none_response(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test listing triggers handles None response."""
        mock_session.request.return_value.json.return_value = None
        mock_session.request.return_value.text = ""

        triggers = mock_client.task_schedule_triggers.list()

        assert triggers == []

    def test_list_triggers_single_dict_response(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test listing triggers handles single dict response."""
        mock_session.request.return_value.json.return_value = {
            "$key": 1,
            "task": 100,
            "schedule": 200,
        }

        triggers = mock_client.task_schedule_triggers.list()

        assert len(triggers) == 1
        assert triggers[0].task_key == 100

    def test_list_triggers_by_task(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test listing triggers filtered by task."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "task": 100, "schedule": 200}
        ]

        triggers = mock_client.task_schedule_triggers.list(task=100)

        assert len(triggers) == 1
        call_args = mock_session.request.call_args
        assert "task eq 100" in str(call_args)

    def test_list_triggers_by_schedule(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test listing triggers filtered by schedule."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "task": 100, "schedule": 200}
        ]

        triggers = mock_client.task_schedule_triggers.list(schedule=200)

        assert len(triggers) == 1
        call_args = mock_session.request.call_args
        assert "schedule eq 200" in str(call_args)

    def test_list_triggers_with_pagination(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test listing triggers with pagination."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "task": 100, "schedule": 200}
        ]

        mock_client.task_schedule_triggers.list(limit=10, offset=5)

        call_args = mock_session.request.call_args
        params = call_args.kwargs.get("params", {})
        assert params.get("limit") == 10
        assert params.get("offset") == 5

    def test_list_triggers_with_custom_filter(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test listing triggers with custom OData filter."""
        mock_session.request.return_value.json.return_value = []

        mock_client.task_schedule_triggers.list(filter="trigger gt 0")

        call_args = mock_session.request.call_args
        assert "(trigger gt 0)" in str(call_args)

    def test_list_for_task(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test list_for_task convenience method."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "task": 100, "schedule": 200}
        ]

        triggers = mock_client.task_schedule_triggers.list_for_task(100)

        assert len(triggers) == 1
        call_args = mock_session.request.call_args
        assert "task eq 100" in str(call_args)

    def test_list_for_schedule(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test list_for_schedule convenience method."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "task": 100, "schedule": 200}
        ]

        triggers = mock_client.task_schedule_triggers.list_for_schedule(200)

        assert len(triggers) == 1
        call_args = mock_session.request.call_args
        assert "schedule eq 200" in str(call_args)


# =============================================================================
# TaskScheduleTriggerManager Tests - Get Operations
# =============================================================================


class TestTaskScheduleTriggerManagerGet:
    """Unit tests for TaskScheduleTriggerManager get operations."""

    def test_get_trigger_by_key(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test getting a trigger by key."""
        mock_session.request.return_value.json.return_value = {
            "$key": 1,
            "task": 100,
            "schedule": 200,
        }

        trigger = mock_client.task_schedule_triggers.get(1)

        assert trigger.key == 1
        assert trigger.task_key == 100

    def test_get_trigger_not_found(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test NotFoundError when trigger not found."""
        mock_session.request.return_value.json.return_value = None
        mock_session.request.return_value.text = ""

        with pytest.raises(NotFoundError):
            mock_client.task_schedule_triggers.get(999)

    def test_get_trigger_invalid_response(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test NotFoundError when response is not a dict."""
        mock_session.request.return_value.json.return_value = []

        with pytest.raises(NotFoundError):
            mock_client.task_schedule_triggers.get(999)

    def test_get_trigger_requires_key(self, mock_client: VergeClient) -> None:
        """Test that get() requires key parameter."""
        with pytest.raises(ValueError, match="Key must be provided"):
            mock_client.task_schedule_triggers.get()


# =============================================================================
# TaskScheduleTriggerManager Tests - Create Operations
# =============================================================================


class TestTaskScheduleTriggerManagerCreate:
    """Unit tests for TaskScheduleTriggerManager create operations."""

    def test_create_trigger(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test creating a task schedule trigger."""
        mock_session.request.return_value.json.side_effect = [
            {"$key": 1},  # POST response
            {"$key": 1, "task": 100, "schedule": 200},  # GET response
        ]

        trigger = mock_client.task_schedule_triggers.create(task=100, schedule=200)

        assert trigger.key == 1
        assert trigger.task_key == 100
        assert trigger.schedule_key == 200

    def test_create_trigger_no_response(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test create raises error on None response."""
        mock_session.request.return_value.json.return_value = None
        mock_session.request.return_value.text = ""

        with pytest.raises(ValueError, match="No response from create operation"):
            mock_client.task_schedule_triggers.create(task=100, schedule=200)

    def test_create_trigger_invalid_response(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test create raises error on non-dict response."""
        mock_session.request.return_value.json.return_value = []

        with pytest.raises(ValueError, match="Create operation returned invalid response"):
            mock_client.task_schedule_triggers.create(task=100, schedule=200)

    def test_create_trigger_returns_model_without_key(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test create returns model when response has no $key."""
        mock_session.request.return_value.json.return_value = {
            "task": 100,
            "schedule": 200,
        }

        trigger = mock_client.task_schedule_triggers.create(task=100, schedule=200)

        assert trigger.task_key == 100
        assert trigger.schedule_key == 200


# =============================================================================
# TaskScheduleTriggerManager Tests - Delete Operations
# =============================================================================


class TestTaskScheduleTriggerManagerDelete:
    """Unit tests for TaskScheduleTriggerManager delete operations."""

    def test_delete_trigger(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test deleting a task schedule trigger."""
        mock_session.request.return_value.json.return_value = None
        mock_session.request.return_value.text = ""

        mock_client.task_schedule_triggers.delete(1)

        calls = mock_session.request.call_args_list
        delete_call = [c for c in calls if "DELETE" in str(c)][0]
        assert "task_schedule_triggers/1" in str(delete_call)


# =============================================================================
# TaskScheduleTriggerManager Tests - Trigger Operations
# =============================================================================


class TestTaskScheduleTriggerManagerTrigger:
    """Unit tests for TaskScheduleTriggerManager trigger operations."""

    def test_trigger(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test manually triggering a task schedule trigger."""
        mock_session.request.return_value.json.return_value = {"triggered": True}

        result = mock_client.task_schedule_triggers.trigger(1)

        assert result == {"triggered": True}
        calls = mock_session.request.call_args_list
        trigger_call = [c for c in calls if "action=trigger" in str(c)][0]
        assert trigger_call is not None

    def test_trigger_object_trigger_now(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test triggering via TaskScheduleTrigger object method."""
        mock_session.request.return_value.json.return_value = {"triggered": True}

        data = {"$key": 1, "task": 100, "schedule": 200}
        trigger = TaskScheduleTrigger(data, mock_client.task_schedule_triggers)
        result = trigger.trigger_now()

        assert result == {"triggered": True}


# =============================================================================
# TaskScheduleTriggerManager Tests - Scoped Manager
# =============================================================================


class TestTaskScheduleTriggerManagerScoped:
    """Unit tests for scoped TaskScheduleTriggerManager."""

    def test_scoped_by_task_key(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test manager scoped by task key."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "task": 100, "schedule": 200}
        ]

        manager = TaskScheduleTriggerManager(mock_client, task_key=100)
        triggers = manager.list()

        assert len(triggers) == 1
        call_args = mock_session.request.call_args
        assert "task eq 100" in str(call_args)

    def test_scoped_by_schedule_key(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test manager scoped by schedule key."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "task": 100, "schedule": 200}
        ]

        manager = TaskScheduleTriggerManager(mock_client, schedule_key=200)
        triggers = manager.list()

        assert len(triggers) == 1
        call_args = mock_session.request.call_args
        assert "schedule eq 200" in str(call_args)

    def test_scoped_manager_ignores_list_params(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test scoped manager uses scope over list parameters."""
        mock_session.request.return_value.json.return_value = []

        manager = TaskScheduleTriggerManager(mock_client, task_key=100)
        # Pass different task - should be ignored
        manager.list(task=200)

        call_args = mock_session.request.call_args
        assert "task eq 100" in str(call_args)
        assert "task eq 200" not in str(call_args)


# =============================================================================
# TaskScheduleTriggerManager Tests - Default Fields
# =============================================================================


class TestTaskScheduleTriggerManagerDefaultFields:
    """Unit tests for TaskScheduleTriggerManager default fields."""

    def test_list_uses_default_fields(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test that list() uses default fields."""
        mock_session.request.return_value.json.return_value = []

        mock_client.task_schedule_triggers.list()

        call_args = mock_session.request.call_args
        params = call_args.kwargs.get("params", {})
        fields = params.get("fields", "")

        assert "$key" in fields
        assert "task" in fields
        assert "schedule" in fields

    def test_list_custom_fields(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test that list() can use custom fields."""
        mock_session.request.return_value.json.return_value = []

        mock_client.task_schedule_triggers.list(fields=["$key", "task"])

        call_args = mock_session.request.call_args
        params = call_args.kwargs.get("params", {})
        fields = params.get("fields", "")

        assert fields == "$key,task"
