"""Unit tests for Log operations."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from pyvergeos import VergeClient
from pyvergeos.exceptions import NotFoundError
from pyvergeos.resources.logs import (
    LOG_LEVELS,
    OBJECT_TYPE_DISPLAY,
    OBJECT_TYPE_MAP,
    Log,
)

# =============================================================================
# Log Model Tests
# =============================================================================


class TestLog:
    """Unit tests for Log model."""

    def test_log_properties(self, mock_client: VergeClient) -> None:
        """Test Log property accessors."""
        # Timestamp in microseconds (Jan 29, 2026 12:00:00 UTC)
        timestamp_us = 1769688000000000
        data = {
            "$key": 1,
            "level": "warning",
            "text": "VM test-vm powered on",
            "timestamp": timestamp_us,
            "user": "admin",
            "object_type": "vm",
            "object_name": "test-vm",
        }
        log = Log(data, mock_client.logs)

        assert log.key == 1
        assert log.level == "warning"
        assert log.level_display == "Warning"
        assert log.text == "VM test-vm powered on"
        assert log.user == "admin"
        assert log.object_type == "vm"
        assert log.object_type_display == "VM"
        assert log.object_name == "test-vm"
        assert log.timestamp_us == timestamp_us
        assert log.created_at is not None

    def test_log_level_display_critical(self, mock_client: VergeClient) -> None:
        """Test level_display for critical log."""
        data = {"$key": 1, "level": "critical"}
        log = Log(data, mock_client.logs)
        assert log.level_display == "Critical"

    def test_log_level_display_error(self, mock_client: VergeClient) -> None:
        """Test level_display for error log."""
        data = {"$key": 1, "level": "error"}
        log = Log(data, mock_client.logs)
        assert log.level_display == "Error"

    def test_log_level_display_message(self, mock_client: VergeClient) -> None:
        """Test level_display for message log."""
        data = {"$key": 1, "level": "message"}
        log = Log(data, mock_client.logs)
        assert log.level_display == "Message"

    def test_log_level_display_audit(self, mock_client: VergeClient) -> None:
        """Test level_display for audit log."""
        data = {"$key": 1, "level": "audit"}
        log = Log(data, mock_client.logs)
        assert log.level_display == "Audit"

    def test_log_object_type_display_network(self, mock_client: VergeClient) -> None:
        """Test object_type_display for network log."""
        data = {"$key": 1, "object_type": "vnet"}
        log = Log(data, mock_client.logs)
        assert log.object_type_display == "Network"

    def test_log_object_type_display_tenant(self, mock_client: VergeClient) -> None:
        """Test object_type_display for tenant log."""
        data = {"$key": 1, "object_type": "tenant"}
        log = Log(data, mock_client.logs)
        assert log.object_type_display == "Tenant"

    def test_log_object_type_display_node(self, mock_client: VergeClient) -> None:
        """Test object_type_display for node log."""
        data = {"$key": 1, "object_type": "node"}
        log = Log(data, mock_client.logs)
        assert log.object_type_display == "Node"

    def test_log_object_type_display_system(self, mock_client: VergeClient) -> None:
        """Test object_type_display for system log."""
        data = {"$key": 1, "object_type": "system"}
        log = Log(data, mock_client.logs)
        assert log.object_type_display == "System"

    def test_log_object_type_display_nas_service(self, mock_client: VergeClient) -> None:
        """Test object_type_display for NAS service log."""
        data = {"$key": 1, "object_type": "vm_service"}
        log = Log(data, mock_client.logs)
        assert log.object_type_display == "NASService"

    def test_log_object_type_display_unknown(self, mock_client: VergeClient) -> None:
        """Test object_type_display for unknown type."""
        data = {"$key": 1, "object_type": "custom_type"}
        log = Log(data, mock_client.logs)
        assert log.object_type_display == "custom_type"

    def test_log_created_at_conversion(self, mock_client: VergeClient) -> None:
        """Test timestamp to datetime conversion."""
        # Timestamp for 2026-01-29 12:00:00 UTC in microseconds
        timestamp_us = 1769688000000000
        data = {"$key": 1, "timestamp": timestamp_us}
        log = Log(data, mock_client.logs)

        created_at = log.created_at
        assert created_at is not None
        assert created_at.year == 2026
        assert created_at.month == 1
        assert created_at.day == 29
        assert created_at.hour == 12
        assert created_at.tzinfo == timezone.utc

    def test_log_created_at_none(self, mock_client: VergeClient) -> None:
        """Test created_at returns None when timestamp not set."""
        data = {"$key": 1}
        log = Log(data, mock_client.logs)
        assert log.created_at is None

    def test_log_created_at_zero(self, mock_client: VergeClient) -> None:
        """Test created_at returns None when timestamp is zero."""
        data = {"$key": 1, "timestamp": 0}
        log = Log(data, mock_client.logs)
        assert log.created_at is None

    def test_log_timestamp_us_default(self, mock_client: VergeClient) -> None:
        """Test timestamp_us returns 0 when not set."""
        data = {"$key": 1}
        log = Log(data, mock_client.logs)
        assert log.timestamp_us == 0

    def test_log_user_empty(self, mock_client: VergeClient) -> None:
        """Test user returns empty string when not set."""
        data = {"$key": 1}
        log = Log(data, mock_client.logs)
        assert log.user == ""

    def test_log_object_name_empty(self, mock_client: VergeClient) -> None:
        """Test object_name returns empty string when not set."""
        data = {"$key": 1}
        log = Log(data, mock_client.logs)
        assert log.object_name == ""

    def test_log_repr(self, mock_client: VergeClient) -> None:
        """Test Log string representation."""
        data = {"$key": 1, "level": "warning", "text": "Test log message"}
        log = Log(data, mock_client.logs)

        repr_str = repr(log)
        assert "Log" in repr_str
        assert "key=1" in repr_str
        assert "Warning" in repr_str

    def test_log_repr_long_text(self, mock_client: VergeClient) -> None:
        """Test Log repr truncates long text."""
        data = {"$key": 1, "level": "error", "text": "A" * 50}
        log = Log(data, mock_client.logs)

        repr_str = repr(log)
        assert "..." in repr_str


# =============================================================================
# LogManager Tests - List Operations
# =============================================================================


class TestLogManagerList:
    """Unit tests for LogManager list operations."""

    def test_list_logs(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test listing all logs."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "level": "critical", "text": "Critical log"},
            {"$key": 2, "level": "error", "text": "Error log"},
            {"$key": 3, "level": "warning", "text": "Warning log"},
        ]

        logs = mock_client.logs.list()

        assert len(logs) == 3
        assert logs[0].level == "critical"
        assert logs[1].level == "error"
        assert logs[2].level == "warning"

    def test_list_logs_empty(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test listing logs returns empty list when none exist."""
        mock_session.request.return_value.json.return_value = []

        logs = mock_client.logs.list()

        assert logs == []

    def test_list_logs_level_filter_single(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test listing logs filtered by single level."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "level": "critical"}
        ]

        logs = mock_client.logs.list(level="critical")

        assert len(logs) == 1
        call_args = mock_session.request.call_args
        params = call_args.kwargs.get("params", {})
        assert "level eq 'critical'" in params.get("filter", "")

    def test_list_logs_level_filter_multiple(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test listing logs filtered by multiple levels."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "level": "critical"},
            {"$key": 2, "level": "error"},
        ]

        logs = mock_client.logs.list(level=["critical", "error"])

        assert len(logs) == 2
        call_args = mock_session.request.call_args
        params = call_args.kwargs.get("params", {})
        filter_str = params.get("filter", "")
        assert "level eq 'critical'" in filter_str
        assert "level eq 'error'" in filter_str
        assert " or " in filter_str

    def test_list_logs_object_type_filter(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test listing logs filtered by object type."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "object_type": "vm"}
        ]

        logs = mock_client.logs.list(object_type="VM")

        assert len(logs) == 1
        call_args = mock_session.request.call_args
        params = call_args.kwargs.get("params", {})
        assert "object_type eq 'vm'" in params.get("filter", "")

    def test_list_logs_user_filter(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test listing logs filtered by user."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "user": "admin"}
        ]

        logs = mock_client.logs.list(user="admin")

        assert len(logs) == 1
        call_args = mock_session.request.call_args
        params = call_args.kwargs.get("params", {})
        assert "user ct 'admin'" in params.get("filter", "")

    def test_list_logs_text_filter(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test listing logs filtered by text content."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "text": "powered on"}
        ]

        logs = mock_client.logs.list(text="power")

        assert len(logs) == 1
        call_args = mock_session.request.call_args
        params = call_args.kwargs.get("params", {})
        assert "text ct 'power'" in params.get("filter", "")

    def test_list_logs_since_filter(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test listing logs filtered by since datetime."""
        mock_session.request.return_value.json.return_value = []

        since = datetime(2026, 1, 29, 12, 0, 0, tzinfo=timezone.utc)
        mock_client.logs.list(since=since)

        call_args = mock_session.request.call_args
        params = call_args.kwargs.get("params", {})
        filter_str = params.get("filter", "")
        assert "timestamp ge" in filter_str

    def test_list_logs_before_filter(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test listing logs filtered by before datetime."""
        mock_session.request.return_value.json.return_value = []

        before = datetime(2026, 1, 29, 12, 0, 0, tzinfo=timezone.utc)
        mock_client.logs.list(before=before)

        call_args = mock_session.request.call_args
        params = call_args.kwargs.get("params", {})
        filter_str = params.get("filter", "")
        assert "timestamp lt" in filter_str

    def test_list_logs_time_range(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test listing logs with time range."""
        mock_session.request.return_value.json.return_value = []

        since = datetime(2026, 1, 29, 10, 0, 0, tzinfo=timezone.utc)
        before = datetime(2026, 1, 29, 12, 0, 0, tzinfo=timezone.utc)
        mock_client.logs.list(since=since, before=before)

        call_args = mock_session.request.call_args
        params = call_args.kwargs.get("params", {})
        filter_str = params.get("filter", "")
        assert "timestamp ge" in filter_str
        assert "timestamp lt" in filter_str

    def test_list_logs_errors_only(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test errors_only shortcut."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "level": "error"},
            {"$key": 2, "level": "critical"},
        ]

        logs = mock_client.logs.list(errors_only=True)

        assert len(logs) == 2
        call_args = mock_session.request.call_args
        params = call_args.kwargs.get("params", {})
        filter_str = params.get("filter", "")
        assert "level eq 'error'" in filter_str
        assert "level eq 'critical'" in filter_str

    def test_list_logs_sorted_by_timestamp_desc(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test that list() sorts by timestamp descending."""
        mock_session.request.return_value.json.return_value = []

        mock_client.logs.list()

        call_args = mock_session.request.call_args
        params = call_args.kwargs.get("params", {})
        assert params.get("sort") == "-timestamp"

    def test_list_logs_default_limit(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test that list() uses default limit of 100."""
        mock_session.request.return_value.json.return_value = []

        mock_client.logs.list()

        call_args = mock_session.request.call_args
        params = call_args.kwargs.get("params", {})
        assert params.get("limit") == 100

    def test_list_logs_custom_limit(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test listing logs with custom limit."""
        mock_session.request.return_value.json.return_value = []

        mock_client.logs.list(limit=50)

        call_args = mock_session.request.call_args
        params = call_args.kwargs.get("params", {})
        assert params.get("limit") == 50

    def test_list_logs_user_escape_quotes(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test that user filter escapes single quotes."""
        mock_session.request.return_value.json.return_value = []

        mock_client.logs.list(user="user'name")

        call_args = mock_session.request.call_args
        params = call_args.kwargs.get("params", {})
        assert "user ct 'user''name'" in params.get("filter", "")

    def test_list_logs_text_escape_quotes(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test that text filter escapes single quotes."""
        mock_session.request.return_value.json.return_value = []

        mock_client.logs.list(text="it's")

        call_args = mock_session.request.call_args
        params = call_args.kwargs.get("params", {})
        assert "text ct 'it''s'" in params.get("filter", "")


# =============================================================================
# LogManager Tests - Convenience Methods
# =============================================================================


class TestLogManagerConvenienceMethods:
    """Unit tests for LogManager convenience methods."""

    def test_list_errors(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test list_errors convenience method."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "level": "error"}
        ]

        logs = mock_client.logs.list_errors()

        assert len(logs) == 1
        call_args = mock_session.request.call_args
        params = call_args.kwargs.get("params", {})
        filter_str = params.get("filter", "")
        assert "level eq 'error'" in filter_str
        assert "level eq 'critical'" in filter_str

    def test_list_errors_with_since(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test list_errors with since parameter."""
        mock_session.request.return_value.json.return_value = []

        since = datetime(2026, 1, 29, 12, 0, 0, tzinfo=timezone.utc)
        mock_client.logs.list_errors(since=since)

        call_args = mock_session.request.call_args
        params = call_args.kwargs.get("params", {})
        filter_str = params.get("filter", "")
        assert "timestamp ge" in filter_str

    def test_list_by_level(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test list_by_level convenience method."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "level": "warning"}
        ]

        logs = mock_client.logs.list_by_level("warning")

        assert len(logs) == 1
        call_args = mock_session.request.call_args
        params = call_args.kwargs.get("params", {})
        assert "level eq 'warning'" in params.get("filter", "")

    def test_list_by_object_type(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test list_by_object_type convenience method."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "object_type": "vnet"}
        ]

        logs = mock_client.logs.list_by_object_type("Network")

        assert len(logs) == 1
        call_args = mock_session.request.call_args
        params = call_args.kwargs.get("params", {})
        assert "object_type eq 'vnet'" in params.get("filter", "")

    def test_list_by_user(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test list_by_user convenience method."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "user": "admin"}
        ]

        logs = mock_client.logs.list_by_user("admin")

        assert len(logs) == 1
        call_args = mock_session.request.call_args
        params = call_args.kwargs.get("params", {})
        assert "user ct 'admin'" in params.get("filter", "")

    def test_search(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test search convenience method."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "text": "snapshot created"}
        ]

        logs = mock_client.logs.search("snapshot")

        assert len(logs) == 1
        call_args = mock_session.request.call_args
        params = call_args.kwargs.get("params", {})
        assert "text ct 'snapshot'" in params.get("filter", "")

    def test_search_with_filters(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test search with additional filters."""
        mock_session.request.return_value.json.return_value = []

        mock_client.logs.search("error", level="critical", object_type="VM")

        call_args = mock_session.request.call_args
        params = call_args.kwargs.get("params", {})
        filter_str = params.get("filter", "")
        assert "text ct 'error'" in filter_str
        assert "level eq 'critical'" in filter_str
        assert "object_type eq 'vm'" in filter_str


# =============================================================================
# LogManager Tests - Get Operations
# =============================================================================


class TestLogManagerGet:
    """Unit tests for LogManager get operations."""

    def test_get_log_by_key(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test getting a log by key."""
        mock_session.request.return_value.json.return_value = {
            "$key": 123,
            "level": "warning",
            "text": "Test log",
        }

        log = mock_client.logs.get(123)

        assert log.key == 123
        assert log.text == "Test log"

    def test_get_log_not_found(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test NotFoundError when log not found by key."""
        mock_session.request.return_value.json.return_value = None
        mock_session.request.return_value.text = ""

        with pytest.raises(NotFoundError):
            mock_client.logs.get(999)

    def test_get_log_requires_key(self, mock_client: VergeClient) -> None:
        """Test that get() requires key parameter."""
        with pytest.raises(ValueError, match="key must be provided"):
            mock_client.logs.get()

    def test_get_log_name_not_supported(self, mock_client: VergeClient) -> None:
        """Test that get() does not support name parameter."""
        with pytest.raises(ValueError, match="Logs do not have a name field"):
            mock_client.logs.get(name="test")


# =============================================================================
# LogManager Tests - Default Fields
# =============================================================================


class TestLogManagerDefaultFields:
    """Unit tests for LogManager default fields."""

    def test_list_uses_default_fields(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test that list() uses default fields."""
        mock_session.request.return_value.json.return_value = []

        mock_client.logs.list()

        call_args = mock_session.request.call_args
        params = call_args.kwargs.get("params", {})
        fields = params.get("fields", "")

        assert "$key" in fields
        assert "level" in fields
        assert "text" in fields
        assert "timestamp" in fields
        assert "user" in fields
        assert "object_type" in fields
        assert "object_name" in fields

    def test_get_uses_default_fields(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test that get() uses default fields."""
        mock_session.request.return_value.json.return_value = {"$key": 1}

        mock_client.logs.get(1)

        call_args = mock_session.request.call_args
        params = call_args.kwargs.get("params", {})
        fields = params.get("fields", "")

        assert "$key" in fields
        assert "level" in fields


# =============================================================================
# Object Type Mapping Tests
# =============================================================================


class TestObjectTypeMappings:
    """Test object type mapping constants."""

    def test_object_type_map_entries(self) -> None:
        """Test key object type mappings exist."""
        assert OBJECT_TYPE_MAP["VM"] == "vm"
        assert OBJECT_TYPE_MAP["Network"] == "vnet"
        assert OBJECT_TYPE_MAP["Tenant"] == "tenant"
        assert OBJECT_TYPE_MAP["User"] == "user"
        assert OBJECT_TYPE_MAP["System"] == "system"
        assert OBJECT_TYPE_MAP["Node"] == "node"
        assert OBJECT_TYPE_MAP["Cluster"] == "cluster"
        assert OBJECT_TYPE_MAP["Task"] == "task"
        assert OBJECT_TYPE_MAP["NASService"] == "vm_service"

    def test_object_type_display_entries(self) -> None:
        """Test reverse object type mappings exist."""
        assert OBJECT_TYPE_DISPLAY["vm"] == "VM"
        assert OBJECT_TYPE_DISPLAY["vnet"] == "Network"
        assert OBJECT_TYPE_DISPLAY["tenant"] == "Tenant"
        assert OBJECT_TYPE_DISPLAY["user"] == "User"
        assert OBJECT_TYPE_DISPLAY["system"] == "System"
        assert OBJECT_TYPE_DISPLAY["node"] == "Node"
        assert OBJECT_TYPE_DISPLAY["cluster"] == "Cluster"
        assert OBJECT_TYPE_DISPLAY["task"] == "Task"
        assert OBJECT_TYPE_DISPLAY["vm_service"] == "NASService"


# =============================================================================
# Log Level Tests
# =============================================================================


class TestLogLevels:
    """Test log level constants."""

    def test_all_levels_defined(self) -> None:
        """Test all log levels are defined."""
        assert "critical" in LOG_LEVELS
        assert "error" in LOG_LEVELS
        assert "warning" in LOG_LEVELS
        assert "message" in LOG_LEVELS
        assert "audit" in LOG_LEVELS
        assert "summary" in LOG_LEVELS
        assert "debug" in LOG_LEVELS

    def test_level_count(self) -> None:
        """Test correct number of levels."""
        assert len(LOG_LEVELS) == 7
