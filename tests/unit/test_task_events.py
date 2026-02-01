"""Unit tests for TaskEvent operations."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from pyvergeos import VergeClient
from pyvergeos.exceptions import NotFoundError
from pyvergeos.resources.task_events import TaskEvent, TaskEventManager

# =============================================================================
# TaskEvent Model Tests
# =============================================================================


class TestTaskEvent:
    """Unit tests for TaskEvent model."""

    def test_task_event_properties(self, mock_client: VergeClient) -> None:
        """Test TaskEvent property accessors."""
        data = {
            "$key": 1,
            "owner": 123,
            "table": "vms",
            "event": "poweron",
            "event_name": "Power On",
            "task": 456,
            "task_display": "Notify Admin",
            "table_event_filters": {"severity": "critical"},
            "context": {"custom": "value"},
            "trigger": 0,
        }
        event = TaskEvent(data, mock_client.task_events)

        assert event.key == 1
        assert event.owner_key == 123
        assert event.owner_table == "vms"
        assert event.event_type == "poweron"
        assert event.event_name_display == "Power On"
        assert event.task_key == 456
        assert event.task_display == "Notify Admin"
        assert event.event_filters == {"severity": "critical"}
        assert event.event_context == {"custom": "value"}

    def test_task_event_owner_key_none(self, mock_client: VergeClient) -> None:
        """Test TaskEvent.owner_key returns None when not set."""
        data = {"$key": 1}
        event = TaskEvent(data, mock_client.task_events)

        assert event.owner_key is None

    def test_task_event_owner_key_empty_string(self, mock_client: VergeClient) -> None:
        """Test TaskEvent.owner_key returns None for empty string."""
        data = {"$key": 1, "owner": ""}
        event = TaskEvent(data, mock_client.task_events)

        assert event.owner_key is None

    def test_task_event_owner_key_path_value(self, mock_client: VergeClient) -> None:
        """Test TaskEvent.owner_key returns None for path-like values."""
        data = {"$key": 1, "owner": "update_settings/1"}
        event = TaskEvent(data, mock_client.task_events)

        assert event.owner_key is None

    def test_task_event_task_key_none(self, mock_client: VergeClient) -> None:
        """Test TaskEvent.task_key returns None when not set."""
        data = {"$key": 1}
        event = TaskEvent(data, mock_client.task_events)

        assert event.task_key is None

    def test_task_event_event_filters_none(self, mock_client: VergeClient) -> None:
        """Test TaskEvent.event_filters returns None when not a dict."""
        data = {"$key": 1, "table_event_filters": "not a dict"}
        event = TaskEvent(data, mock_client.task_events)

        assert event.event_filters is None

    def test_task_event_event_context_none(self, mock_client: VergeClient) -> None:
        """Test TaskEvent.event_context returns None when not a dict."""
        data = {"$key": 1, "context": "not a dict"}
        event = TaskEvent(data, mock_client.task_events)

        assert event.event_context is None

    def test_task_event_task_display_default(self, mock_client: VergeClient) -> None:
        """Test TaskEvent.task_display returns empty string when not set."""
        data = {"$key": 1}
        event = TaskEvent(data, mock_client.task_events)

        assert event.task_display == ""


# =============================================================================
# TaskEventManager Tests - List Operations
# =============================================================================


class TestTaskEventManagerList:
    """Unit tests for TaskEventManager list operations."""

    def test_list_task_events(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test listing all task events."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "event": "poweron", "task": 100},
            {"$key": 2, "event": "poweroff", "task": 100},
            {"$key": 3, "event": "login", "task": 200},
        ]

        events = mock_client.task_events.list()

        assert len(events) == 3
        assert events[0].event_type == "poweron"
        assert events[1].event_type == "poweroff"
        assert events[2].event_type == "login"

    def test_list_task_events_empty(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test listing task events returns empty list when none exist."""
        mock_session.request.return_value.json.return_value = []

        events = mock_client.task_events.list()

        assert events == []

    def test_list_task_events_none_response(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test listing task events handles None response."""
        mock_session.request.return_value.json.return_value = None
        mock_session.request.return_value.text = ""

        events = mock_client.task_events.list()

        assert events == []

    def test_list_task_events_single_dict_response(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test listing task events handles single dict response."""
        mock_session.request.return_value.json.return_value = {"$key": 1, "event": "poweron"}

        events = mock_client.task_events.list()

        assert len(events) == 1
        assert events[0].event_type == "poweron"

    def test_list_task_events_by_task(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test listing task events filtered by task."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "event": "poweron", "task": 100}
        ]

        events = mock_client.task_events.list(task=100)

        assert len(events) == 1
        call_args = mock_session.request.call_args
        assert "task eq 100" in str(call_args)

    def test_list_task_events_by_owner(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test listing task events filtered by owner."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "owner": 123, "event": "poweron"}
        ]

        events = mock_client.task_events.list(owner=123)

        assert len(events) == 1
        call_args = mock_session.request.call_args
        assert "owner eq 123" in str(call_args)

    def test_list_task_events_by_table(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test listing task events filtered by table."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "table": "vms", "event": "poweron"}
        ]

        events = mock_client.task_events.list(table="vms")

        assert len(events) == 1
        call_args = mock_session.request.call_args
        assert "table eq 'vms'" in str(call_args)

    def test_list_task_events_by_event(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test listing task events filtered by event type."""
        mock_session.request.return_value.json.return_value = [{"$key": 1, "event": "poweron"}]

        events = mock_client.task_events.list(event="poweron")

        assert len(events) == 1
        call_args = mock_session.request.call_args
        assert "event eq 'poweron'" in str(call_args)

    def test_list_task_events_with_pagination(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test listing task events with pagination."""
        mock_session.request.return_value.json.return_value = [{"$key": 1, "event": "poweron"}]

        mock_client.task_events.list(limit=10, offset=5)

        call_args = mock_session.request.call_args
        params = call_args.kwargs.get("params", {})
        assert params.get("limit") == 10
        assert params.get("offset") == 5

    def test_list_task_events_with_custom_filter(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test listing task events with custom OData filter."""
        mock_session.request.return_value.json.return_value = []

        mock_client.task_events.list(filter="trigger gt 0")

        call_args = mock_session.request.call_args
        assert "(trigger gt 0)" in str(call_args)

    def test_list_for_task(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test list_for_task convenience method."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "event": "poweron", "task": 100}
        ]

        events = mock_client.task_events.list_for_task(100)

        assert len(events) == 1
        call_args = mock_session.request.call_args
        assert "task eq 100" in str(call_args)

    def test_list_for_owner(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test list_for_owner convenience method."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "owner": 123, "event": "poweron"}
        ]

        events = mock_client.task_events.list_for_owner(123)

        assert len(events) == 1
        call_args = mock_session.request.call_args
        assert "owner eq 123" in str(call_args)

    def test_list_by_table(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test list_by_table convenience method."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "table": "vnets", "event": "poweron"}
        ]

        events = mock_client.task_events.list_by_table("vnets")

        assert len(events) == 1
        call_args = mock_session.request.call_args
        assert "table eq 'vnets'" in str(call_args)


# =============================================================================
# TaskEventManager Tests - Get Operations
# =============================================================================


class TestTaskEventManagerGet:
    """Unit tests for TaskEventManager get operations."""

    def test_get_task_event_by_key(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test getting a task event by key."""
        mock_session.request.return_value.json.return_value = {
            "$key": 1,
            "event": "poweron",
            "task": 100,
        }

        event = mock_client.task_events.get(1)

        assert event.key == 1
        assert event.event_type == "poweron"

    def test_get_task_event_not_found(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test NotFoundError when task event not found."""
        mock_session.request.return_value.json.return_value = None
        mock_session.request.return_value.text = ""

        with pytest.raises(NotFoundError):
            mock_client.task_events.get(999)

    def test_get_task_event_invalid_response(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test NotFoundError when response is not a dict."""
        mock_session.request.return_value.json.return_value = []

        with pytest.raises(NotFoundError):
            mock_client.task_events.get(999)

    def test_get_task_event_requires_key(self, mock_client: VergeClient) -> None:
        """Test that get() requires key parameter."""
        with pytest.raises(ValueError, match="Key must be provided"):
            mock_client.task_events.get()


# =============================================================================
# TaskEventManager Tests - Create Operations
# =============================================================================


class TestTaskEventManagerCreate:
    """Unit tests for TaskEventManager create operations."""

    def test_create_task_event(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test creating a task event."""
        mock_session.request.return_value.json.side_effect = [
            {"$key": 1},  # POST response
            {"$key": 1, "event": "poweron", "task": 100, "owner": 123},  # GET response
        ]

        event = mock_client.task_events.create(task=100, owner=123, event="poweron")

        assert event.key == 1
        assert event.event_type == "poweron"

    def test_create_task_event_with_optional_fields(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test creating a task event with optional fields."""
        mock_session.request.return_value.json.side_effect = [
            {"$key": 1},
            {"$key": 1, "event": "poweron", "task": 100, "owner": 123, "table": "vms"},
        ]

        event = mock_client.task_events.create(
            task=100,
            owner=123,
            event="poweron",
            table="vms",
            event_name="Power On VM",
            table_event_filters={"severity": "warning"},
            context={"notify": True},
        )

        assert event.key == 1
        # Verify POST body contained optional fields
        post_calls = [
            c
            for c in mock_session.request.call_args_list
            if c.kwargs.get("method") == "POST" and "task_events" in c.kwargs.get("url", "")
        ]
        assert len(post_calls) == 1
        body = post_calls[0].kwargs.get("json", {})
        assert body.get("table") == "vms"
        assert body.get("event_name") == "Power On VM"
        assert body.get("table_event_filters") == {"severity": "warning"}
        assert body.get("context") == {"notify": True}

    def test_create_task_event_no_response(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test create raises error on None response."""
        mock_session.request.return_value.json.return_value = None
        mock_session.request.return_value.text = ""

        with pytest.raises(ValueError, match="No response from create operation"):
            mock_client.task_events.create(task=100, owner=123, event="poweron")

    def test_create_task_event_invalid_response(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test create raises error on non-dict response."""
        mock_session.request.return_value.json.return_value = []

        with pytest.raises(ValueError, match="Create operation returned invalid response"):
            mock_client.task_events.create(task=100, owner=123, event="poweron")


# =============================================================================
# TaskEventManager Tests - Update Operations
# =============================================================================


class TestTaskEventManagerUpdate:
    """Unit tests for TaskEventManager update operations."""

    def test_update_task_event(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test updating a task event."""
        mock_session.request.return_value.json.side_effect = [
            None,  # PUT response
            {"$key": 1, "event": "poweron", "context": {"updated": True}},  # GET response
        ]

        event = mock_client.task_events.update(1, context={"updated": True})

        assert event.key == 1
        assert event.event_context == {"updated": True}

    def test_update_task_event_filters(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test updating task event filters."""
        mock_session.request.return_value.json.side_effect = [
            None,
            {"$key": 1, "table_event_filters": {"severity": "critical"}},
        ]

        event = mock_client.task_events.update(1, table_event_filters={"severity": "critical"})

        assert event.event_filters == {"severity": "critical"}

    def test_update_task_event_no_changes(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test update with no changes returns current event."""
        mock_session.request.return_value.json.return_value = {
            "$key": 1,
            "event": "poweron",
        }

        event = mock_client.task_events.update(1)

        assert event.key == 1


# =============================================================================
# TaskEventManager Tests - Delete Operations
# =============================================================================


class TestTaskEventManagerDelete:
    """Unit tests for TaskEventManager delete operations."""

    def test_delete_task_event(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test deleting a task event."""
        mock_session.request.return_value.json.return_value = None
        mock_session.request.return_value.text = ""

        mock_client.task_events.delete(1)

        calls = mock_session.request.call_args_list
        delete_call = [c for c in calls if "DELETE" in str(c)][0]
        assert "task_events/1" in str(delete_call)


# =============================================================================
# TaskEventManager Tests - Trigger Operations
# =============================================================================


class TestTaskEventManagerTrigger:
    """Unit tests for TaskEventManager trigger operations."""

    def test_trigger_task_event(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test manually triggering a task event."""
        mock_session.request.return_value.json.return_value = {"triggered": True}

        result = mock_client.task_events.trigger(1)

        assert result == {"triggered": True}
        calls = mock_session.request.call_args_list
        trigger_call = [c for c in calls if "action=trigger" in str(c)][0]
        assert trigger_call is not None

    def test_trigger_task_event_with_context(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test triggering a task event with context."""
        mock_session.request.return_value.json.return_value = {"triggered": True}

        result = mock_client.task_events.trigger(1, context={"custom": "data"})

        assert result is not None
        calls = mock_session.request.call_args_list
        trigger_call = [c for c in calls if "action=trigger" in str(c)][0]
        # Context should be passed as parameter
        assert "context" in str(trigger_call)

    def test_task_event_object_trigger_now(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test triggering via TaskEvent object method."""
        mock_session.request.return_value.json.return_value = {"triggered": True}

        data = {"$key": 1, "event": "poweron"}
        event = TaskEvent(data, mock_client.task_events)
        result = event.trigger_now(context={"test": "value"})

        assert result == {"triggered": True}


# =============================================================================
# TaskEventManager Tests - Scoped Manager
# =============================================================================


class TestTaskEventManagerScoped:
    """Unit tests for scoped TaskEventManager."""

    def test_scoped_by_task_key(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test manager scoped by task key."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "event": "poweron", "task": 100}
        ]

        manager = TaskEventManager(mock_client, task_key=100)
        events = manager.list()

        assert len(events) == 1
        call_args = mock_session.request.call_args
        assert "task eq 100" in str(call_args)

    def test_scoped_by_owner_key(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test manager scoped by owner key."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "owner": 123, "event": "poweron"}
        ]

        manager = TaskEventManager(mock_client, owner_key=123)
        events = manager.list()

        assert len(events) == 1
        call_args = mock_session.request.call_args
        assert "owner eq 123" in str(call_args)

    def test_scoped_manager_ignores_list_params(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test scoped manager uses scope over list parameters."""
        mock_session.request.return_value.json.return_value = []

        manager = TaskEventManager(mock_client, task_key=100)
        # Pass different task - should be ignored
        manager.list(task=200)

        call_args = mock_session.request.call_args
        assert "task eq 100" in str(call_args)
        assert "task eq 200" not in str(call_args)


# =============================================================================
# TaskEventManager Tests - Default Fields
# =============================================================================


class TestTaskEventManagerDefaultFields:
    """Unit tests for TaskEventManager default fields."""

    def test_list_uses_default_fields(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test that list() uses default fields."""
        mock_session.request.return_value.json.return_value = []

        mock_client.task_events.list()

        call_args = mock_session.request.call_args
        params = call_args.kwargs.get("params", {})
        fields = params.get("fields", "")

        assert "$key" in fields
        assert "event" in fields
        assert "task" in fields
        assert "owner" in fields

    def test_list_custom_fields(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test that list() can use custom fields."""
        mock_session.request.return_value.json.return_value = []

        mock_client.task_events.list(fields=["$key", "event"])

        call_args = mock_session.request.call_args
        params = call_args.kwargs.get("params", {})
        fields = params.get("fields", "")

        assert fields == "$key,event"
