"""Unit tests for TaskScript operations."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from pyvergeos import VergeClient
from pyvergeos.exceptions import NotFoundError
from pyvergeos.resources.task_scripts import TaskScript

# =============================================================================
# TaskScript Model Tests
# =============================================================================


class TestTaskScript:
    """Unit tests for TaskScript model."""

    def test_task_script_properties(self, mock_client: VergeClient) -> None:
        """Test TaskScript property accessors."""
        data = {
            "$key": 1,
            "name": "Cleanup Script",
            "description": "Removes old temporary files",
            "script": "log('Cleanup started')\n# Do cleanup",
            "task_settings": {"questions": [{"name": "target", "type": "string"}]},
            "task_count": 3,
        }
        script = TaskScript(data, mock_client.task_scripts)

        assert script.key == 1
        assert script.name == "Cleanup Script"
        assert script.description == "Removes old temporary files"
        assert script.script_code == "log('Cleanup started')\n# Do cleanup"
        assert script.settings == {"questions": [{"name": "target", "type": "string"}]}
        assert script.task_count == 3

    def test_task_script_script_code_none(self, mock_client: VergeClient) -> None:
        """Test TaskScript.script_code returns None when not set."""
        data = {"$key": 1}
        script = TaskScript(data, mock_client.task_scripts)

        assert script.script_code is None

    def test_task_script_settings_none(self, mock_client: VergeClient) -> None:
        """Test TaskScript.settings returns None when not a dict."""
        data = {"$key": 1, "task_settings": "not a dict"}
        script = TaskScript(data, mock_client.task_scripts)

        assert script.settings is None

    def test_task_script_settings_missing(self, mock_client: VergeClient) -> None:
        """Test TaskScript.settings returns None when not set."""
        data = {"$key": 1}
        script = TaskScript(data, mock_client.task_scripts)

        assert script.settings is None

    def test_task_script_task_count_default(self, mock_client: VergeClient) -> None:
        """Test TaskScript.task_count returns 0 when not set."""
        data = {"$key": 1}
        script = TaskScript(data, mock_client.task_scripts)

        assert script.task_count == 0


# =============================================================================
# TaskScriptManager Tests - List Operations
# =============================================================================


class TestTaskScriptManagerList:
    """Unit tests for TaskScriptManager list operations."""

    def test_list_scripts(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test listing all task scripts."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "name": "Script 1", "task_count": 2},
            {"$key": 2, "name": "Script 2", "task_count": 1},
            {"$key": 3, "name": "Script 3", "task_count": 0},
        ]

        scripts = mock_client.task_scripts.list()

        assert len(scripts) == 3
        assert scripts[0].name == "Script 1"
        assert scripts[1].name == "Script 2"
        assert scripts[2].name == "Script 3"

    def test_list_scripts_empty(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test listing scripts returns empty list when none exist."""
        mock_session.request.return_value.json.return_value = []

        scripts = mock_client.task_scripts.list()

        assert scripts == []

    def test_list_scripts_none_response(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test listing scripts handles None response."""
        mock_session.request.return_value.json.return_value = None
        mock_session.request.return_value.text = ""

        scripts = mock_client.task_scripts.list()

        assert scripts == []

    def test_list_scripts_single_dict_response(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test listing scripts handles single dict response."""
        mock_session.request.return_value.json.return_value = {
            "$key": 1,
            "name": "Single Script",
        }

        scripts = mock_client.task_scripts.list()

        assert len(scripts) == 1
        assert scripts[0].name == "Single Script"

    def test_list_scripts_by_name_exact(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test listing scripts by exact name."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "name": "Cleanup Script"}
        ]

        scripts = mock_client.task_scripts.list(name="Cleanup Script")

        assert len(scripts) == 1
        call_args = mock_session.request.call_args
        assert "name eq 'Cleanup Script'" in str(call_args)

    def test_list_scripts_by_name_wildcard(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test listing scripts by name with wildcard."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "name": "Backup Script 1"},
            {"$key": 2, "name": "Backup Script 2"},
        ]

        scripts = mock_client.task_scripts.list(name="Backup*")

        assert len(scripts) == 2
        call_args = mock_session.request.call_args
        assert "name ct 'Backup'" in str(call_args)

    def test_list_scripts_with_pagination(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test listing scripts with pagination."""
        mock_session.request.return_value.json.return_value = [{"$key": 1, "name": "Script"}]

        mock_client.task_scripts.list(limit=10, offset=5)

        call_args = mock_session.request.call_args
        params = call_args.kwargs.get("params", {})
        assert params.get("limit") == 10
        assert params.get("offset") == 5

    def test_list_scripts_with_custom_filter(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test listing scripts with custom OData filter."""
        mock_session.request.return_value.json.return_value = []

        mock_client.task_scripts.list(filter="task_count gt 0")

        call_args = mock_session.request.call_args
        assert "(task_count gt 0)" in str(call_args)


# =============================================================================
# TaskScriptManager Tests - Get Operations
# =============================================================================


class TestTaskScriptManagerGet:
    """Unit tests for TaskScriptManager get operations."""

    def test_get_script_by_key(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test getting a script by key."""
        mock_session.request.return_value.json.return_value = {
            "$key": 1,
            "name": "Test Script",
            "script": "log('Hello')",
        }

        script = mock_client.task_scripts.get(1)

        assert script.key == 1
        assert script.name == "Test Script"

    def test_get_script_by_name(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test getting a script by name."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "name": "Cleanup Script", "script": "log('Cleanup')"}
        ]

        script = mock_client.task_scripts.get(name="Cleanup Script")

        assert script.name == "Cleanup Script"
        call_args = mock_session.request.call_args
        assert "name eq 'Cleanup Script'" in str(call_args)

    def test_get_script_not_found_by_key(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test NotFoundError when script not found by key."""
        mock_session.request.return_value.json.return_value = None
        mock_session.request.return_value.text = ""

        with pytest.raises(NotFoundError):
            mock_client.task_scripts.get(999)

    def test_get_script_not_found_by_name(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test NotFoundError when script not found by name."""
        mock_session.request.return_value.json.return_value = []

        with pytest.raises(NotFoundError):
            mock_client.task_scripts.get(name="Nonexistent")

    def test_get_script_invalid_response(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test NotFoundError when response is not a dict."""
        mock_session.request.return_value.json.return_value = []

        with pytest.raises(NotFoundError):
            mock_client.task_scripts.get(999)

    def test_get_script_requires_key_or_name(self, mock_client: VergeClient) -> None:
        """Test that get() requires key or name parameter."""
        with pytest.raises(ValueError, match="Either key or name must be provided"):
            mock_client.task_scripts.get()


# =============================================================================
# TaskScriptManager Tests - Create Operations
# =============================================================================


class TestTaskScriptManagerCreate:
    """Unit tests for TaskScriptManager create operations."""

    def test_create_script(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test creating a task script."""
        mock_session.request.return_value.json.side_effect = [
            {"$key": 1},  # POST response
            {"$key": 1, "name": "New Script", "script": "log('Hello')"},  # GET response
        ]

        script = mock_client.task_scripts.create(name="New Script", script="log('Hello')")

        assert script.key == 1
        assert script.name == "New Script"

    def test_create_script_with_all_options(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test creating a script with all options."""
        mock_session.request.return_value.json.side_effect = [
            {"$key": 1},
            {"$key": 1, "name": "Full Script", "description": "Test script"},
        ]

        script = mock_client.task_scripts.create(
            name="Full Script",
            script="log('Hello World')",
            description="Test script with all options",
            task_settings={"questions": [{"name": "target", "type": "string"}]},
        )

        assert script.key == 1
        # Verify POST body
        post_calls = [
            c
            for c in mock_session.request.call_args_list
            if c.kwargs.get("method") == "POST" and "task_scripts" in c.kwargs.get("url", "")
        ]
        assert len(post_calls) == 1
        body = post_calls[0].kwargs.get("json", {})
        assert body.get("name") == "Full Script"
        assert body.get("script") == "log('Hello World')"
        assert body.get("description") == "Test script with all options"
        assert body.get("task_settings") == {"questions": [{"name": "target", "type": "string"}]}

    def test_create_script_default_settings(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test creating a script adds default empty settings."""
        mock_session.request.return_value.json.side_effect = [
            {"$key": 1},
            {"$key": 1, "name": "Script"},
        ]

        mock_client.task_scripts.create(name="Script", script="log('test')")

        # Verify POST body contains default settings
        post_calls = [
            c
            for c in mock_session.request.call_args_list
            if c.kwargs.get("method") == "POST" and "task_scripts" in c.kwargs.get("url", "")
        ]
        assert len(post_calls) == 1
        body = post_calls[0].kwargs.get("json", {})
        assert body.get("task_settings") == {"questions": []}

    def test_create_script_no_response(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test create raises error on None response."""
        mock_session.request.return_value.json.return_value = None
        mock_session.request.return_value.text = ""

        with pytest.raises(ValueError, match="No response from create operation"):
            mock_client.task_scripts.create(name="Test", script="log('test')")

    def test_create_script_invalid_response(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test create raises error on non-dict response."""
        mock_session.request.return_value.json.return_value = []

        with pytest.raises(ValueError, match="Create operation returned invalid response"):
            mock_client.task_scripts.create(name="Test", script="log('test')")


# =============================================================================
# TaskScriptManager Tests - Update Operations
# =============================================================================


class TestTaskScriptManagerUpdate:
    """Unit tests for TaskScriptManager update operations."""

    def test_update_script(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test updating a task script."""
        mock_session.request.return_value.json.side_effect = [
            None,  # PUT response
            {"$key": 1, "name": "Updated Script", "script": "log('Updated')"},  # GET response
        ]

        script = mock_client.task_scripts.update(1, name="Updated Script")

        assert script.name == "Updated Script"

    def test_update_script_code(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test updating script code."""
        mock_session.request.return_value.json.side_effect = [
            None,
            {"$key": 1, "script": "log('New code')"},
        ]

        script = mock_client.task_scripts.update(1, script="log('New code')")

        assert script.script_code == "log('New code')"

    def test_update_script_settings(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test updating script settings."""
        mock_session.request.return_value.json.side_effect = [
            None,
            {"$key": 1, "task_settings": {"questions": []}},
        ]

        script = mock_client.task_scripts.update(1, task_settings={"questions": []})

        assert script.settings == {"questions": []}

    def test_update_script_no_changes(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test update with no changes returns current script."""
        mock_session.request.return_value.json.return_value = {
            "$key": 1,
            "name": "Script",
        }

        script = mock_client.task_scripts.update(1)

        assert script.key == 1


# =============================================================================
# TaskScriptManager Tests - Delete Operations
# =============================================================================


class TestTaskScriptManagerDelete:
    """Unit tests for TaskScriptManager delete operations."""

    def test_delete_script(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test deleting a task script."""
        mock_session.request.return_value.json.return_value = None
        mock_session.request.return_value.text = ""

        mock_client.task_scripts.delete(1)

        calls = mock_session.request.call_args_list
        delete_call = [c for c in calls if "DELETE" in str(c)][0]
        assert "task_scripts/1" in str(delete_call)


# =============================================================================
# TaskScriptManager Tests - Run Operations
# =============================================================================


class TestTaskScriptManagerRun:
    """Unit tests for TaskScriptManager run operations."""

    def test_run_script(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test running a task script."""
        mock_session.request.return_value.json.return_value = {"task": 123, "status": "running"}

        result = mock_client.task_scripts.run(1)

        assert result == {"task": 123, "status": "running"}
        calls = mock_session.request.call_args_list
        run_call = [c for c in calls if "action=run" in str(c)][0]
        assert run_call is not None

    def test_run_script_with_params(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test running a script with parameters."""
        mock_session.request.return_value.json.return_value = {"task": 123}

        result = mock_client.task_scripts.run(1, target_vm=100, cleanup=True)

        assert result is not None
        calls = mock_session.request.call_args_list
        run_call = [c for c in calls if "action=run" in str(c)][0]
        body = run_call.kwargs.get("json", {})
        assert body.get("target_vm") == 100
        assert body.get("cleanup") is True

    def test_script_object_run(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test running script via TaskScript object method."""
        mock_session.request.return_value.json.return_value = {"task": 123}

        data = {"$key": 1, "name": "Script", "script": "log('test')"}
        script = TaskScript(data, mock_client.task_scripts)
        result = script.run(target=456)

        assert result == {"task": 123}


# =============================================================================
# TaskScriptManager Tests - Default Fields
# =============================================================================


class TestTaskScriptManagerDefaultFields:
    """Unit tests for TaskScriptManager default fields."""

    def test_list_uses_default_fields(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test that list() uses default fields."""
        mock_session.request.return_value.json.return_value = []

        mock_client.task_scripts.list()

        call_args = mock_session.request.call_args
        params = call_args.kwargs.get("params", {})
        fields = params.get("fields", "")

        assert "$key" in fields
        assert "name" in fields
        assert "script" in fields
        assert "task_settings" in fields

    def test_list_custom_fields(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test that list() can use custom fields."""
        mock_session.request.return_value.json.return_value = []

        mock_client.task_scripts.list(fields=["$key", "name"])

        call_args = mock_session.request.call_args
        params = call_args.kwargs.get("params", {})
        fields = params.get("fields", "")

        assert fields == "$key,name"
