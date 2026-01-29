"""Integration tests for Log operations.

These tests require a live VergeOS system and will be skipped
if the environment variables are not set.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from pyvergeos import VergeClient
from pyvergeos.exceptions import NotFoundError


@pytest.mark.integration
class TestLogListIntegration:
    """Integration tests for LogManager list operations."""

    def test_list_logs(self, live_client: VergeClient) -> None:
        """Test listing logs from live system."""
        logs = live_client.logs.list()

        # Should return a list (may be empty but usually has logs)
        assert isinstance(logs, list)
        assert len(logs) > 0  # System should have some logs

        # Each log should have expected properties
        for log in logs:
            assert hasattr(log, "key")
            assert hasattr(log, "level")
            assert hasattr(log, "text")
            assert hasattr(log, "user")
            assert hasattr(log, "object_type")
            assert hasattr(log, "created_at")

    def test_list_logs_with_limit(self, live_client: VergeClient) -> None:
        """Test listing logs with limit."""
        logs = live_client.logs.list(limit=5)

        assert isinstance(logs, list)
        assert len(logs) <= 5

    def test_list_logs_level_filter_single(self, live_client: VergeClient) -> None:
        """Test listing logs filtered by single level."""
        logs = live_client.logs.list(level="message", limit=20)

        for log in logs:
            assert log.level == "message"

    def test_list_logs_level_filter_multiple(self, live_client: VergeClient) -> None:
        """Test listing logs filtered by multiple levels."""
        logs = live_client.logs.list(level=["error", "critical"], limit=20)

        for log in logs:
            assert log.level in ["error", "critical"]

    def test_list_errors(self, live_client: VergeClient) -> None:
        """Test list_errors convenience method."""
        logs = live_client.logs.list_errors(limit=20)

        for log in logs:
            assert log.level in ["error", "critical"]

    def test_list_by_level(self, live_client: VergeClient) -> None:
        """Test list_by_level convenience method."""
        logs = live_client.logs.list_by_level("warning", limit=10)

        for log in logs:
            assert log.level == "warning"


@pytest.mark.integration
class TestLogObjectTypeFilterIntegration:
    """Integration tests for LogManager object type filtering."""

    def test_list_logs_object_type_vm(self, live_client: VergeClient) -> None:
        """Test listing VM logs."""
        logs = live_client.logs.list(object_type="VM", limit=10)

        for log in logs:
            assert log.object_type == "vm"
            assert log.object_type_display == "VM"

    def test_list_logs_object_type_network(self, live_client: VergeClient) -> None:
        """Test listing Network logs."""
        logs = live_client.logs.list(object_type="Network", limit=10)

        for log in logs:
            assert log.object_type == "vnet"
            assert log.object_type_display == "Network"

    def test_list_by_object_type(self, live_client: VergeClient) -> None:
        """Test list_by_object_type convenience method."""
        logs = live_client.logs.list_by_object_type("VM", limit=10)

        for log in logs:
            assert log.object_type == "vm"

    def test_list_logs_object_type_task(self, live_client: VergeClient) -> None:
        """Test listing Task logs."""
        logs = live_client.logs.list(object_type="Task", limit=10)

        for log in logs:
            assert log.object_type == "task"


@pytest.mark.integration
class TestLogUserFilterIntegration:
    """Integration tests for LogManager user filtering."""

    def test_list_logs_by_user(self, live_client: VergeClient) -> None:
        """Test listing logs filtered by user."""
        # First get some logs to find a valid user
        logs = live_client.logs.list(limit=50)
        users = {log.user for log in logs if log.user}
        if not users:
            pytest.skip("No logs with user information available")

        user = list(users)[0]
        user_logs = live_client.logs.list(user=user, limit=20)

        for log in user_logs:
            assert user.lower() in log.user.lower()

    def test_list_by_user(self, live_client: VergeClient) -> None:
        """Test list_by_user convenience method."""
        logs = live_client.logs.list(limit=50)
        users = {log.user for log in logs if log.user}
        if not users:
            pytest.skip("No logs with user information available")

        user = list(users)[0]
        user_logs = live_client.logs.list_by_user(user, limit=10)

        for log in user_logs:
            assert user.lower() in log.user.lower()


@pytest.mark.integration
class TestLogTextSearchIntegration:
    """Integration tests for LogManager text search."""

    def test_list_logs_text_filter(self, live_client: VergeClient) -> None:
        """Test listing logs filtered by text content."""
        # Search for common terms that should exist in most systems
        logs = live_client.logs.search("power", limit=10)

        # Should return a list
        assert isinstance(logs, list)

        # Each log should contain the search term
        for log in logs:
            assert "power" in log.text.lower()

    def test_search_convenience_method(self, live_client: VergeClient) -> None:
        """Test search convenience method with filters."""
        logs = live_client.logs.search("snapshot", limit=10)

        assert isinstance(logs, list)
        for log in logs:
            assert "snapshot" in log.text.lower()


@pytest.mark.integration
class TestLogTimeFilterIntegration:
    """Integration tests for LogManager time-based filtering."""

    def test_list_logs_since(self, live_client: VergeClient) -> None:
        """Test listing logs since a datetime."""
        # Get logs from the last 24 hours
        since = datetime.now(timezone.utc) - timedelta(hours=24)
        logs = live_client.logs.list(since=since, limit=50)

        # Should return a list (may be empty if no recent logs)
        assert isinstance(logs, list)

        # All logs should be after the since time
        for log in logs:
            if log.created_at:
                assert log.created_at >= since

    def test_list_logs_before(self, live_client: VergeClient) -> None:
        """Test listing logs before a datetime."""
        before = datetime.now(timezone.utc)
        logs = live_client.logs.list(before=before, limit=50)

        # Should return a list
        assert isinstance(logs, list)

        # All logs should be before the time
        for log in logs:
            if log.created_at:
                assert log.created_at <= before

    def test_list_logs_time_range(self, live_client: VergeClient) -> None:
        """Test listing logs within a time range."""
        now = datetime.now(timezone.utc)
        since = now - timedelta(hours=48)
        before = now - timedelta(hours=24)

        logs = live_client.logs.list(since=since, before=before, limit=50)

        assert isinstance(logs, list)

        for log in logs:
            if log.created_at:
                assert since <= log.created_at <= before


@pytest.mark.integration
class TestLogGetIntegration:
    """Integration tests for LogManager get operations."""

    def test_get_log_by_key(self, live_client: VergeClient) -> None:
        """Test getting a log by key."""
        logs = live_client.logs.list(limit=10)
        if not logs:
            pytest.skip("No logs available")

        log = live_client.logs.get(logs[0].key)

        assert log.key == logs[0].key
        assert log.level == logs[0].level
        assert log.text == logs[0].text

    def test_get_nonexistent_log(self, live_client: VergeClient) -> None:
        """Test that NotFoundError is raised for nonexistent log."""
        with pytest.raises(NotFoundError):
            live_client.logs.get(999999999)

    def test_get_log_name_not_supported(self, live_client: VergeClient) -> None:
        """Test that name parameter raises ValueError."""
        with pytest.raises(ValueError, match="Logs do not have a name field"):
            live_client.logs.get(name="test")


@pytest.mark.integration
class TestLogPropertiesIntegration:
    """Integration tests for Log properties."""

    def test_log_properties(self, live_client: VergeClient) -> None:
        """Test Log property accessors on live data."""
        logs = live_client.logs.list(limit=10)
        if not logs:
            pytest.skip("No logs available")

        log = logs[0]

        # All logs should have these properties accessible
        assert log.key is not None
        assert log.level is not None
        assert log.level_display is not None
        assert log.text is not None
        # user may be empty for system-generated logs
        assert log.object_type is not None
        assert log.object_type_display is not None

    def test_log_level_display_mapping(self, live_client: VergeClient) -> None:
        """Test that level_display is properly capitalized."""
        logs = live_client.logs.list(limit=50)
        if not logs:
            pytest.skip("No logs available")

        for log in logs:
            # level_display should be capitalized version of level
            assert log.level_display == log.level.capitalize()

    def test_log_created_at_datetime(self, live_client: VergeClient) -> None:
        """Test that created_at is a proper datetime."""
        logs = live_client.logs.list(limit=10)
        if not logs:
            pytest.skip("No logs available")

        for log in logs:
            if log.created_at:
                assert isinstance(log.created_at, datetime)
                # Should have timezone info
                assert log.created_at.tzinfo is not None

    def test_log_timestamp_us(self, live_client: VergeClient) -> None:
        """Test that timestamp_us returns microseconds."""
        logs = live_client.logs.list(limit=10)
        if not logs:
            pytest.skip("No logs available")

        for log in logs:
            ts = log.timestamp_us
            # Timestamp should be a large number (microseconds since epoch)
            # For 2024+, should be > 1700000000000000
            assert ts > 1700000000000000


@pytest.mark.integration
class TestLogSortingIntegration:
    """Integration tests for Log sorting."""

    def test_logs_sorted_by_timestamp_desc(self, live_client: VergeClient) -> None:
        """Test that logs are sorted by timestamp descending."""
        logs = live_client.logs.list(limit=20)
        if len(logs) < 2:
            pytest.skip("Need at least 2 logs to test sorting")

        # Each log should have timestamp >= next log's timestamp
        for i in range(len(logs) - 1):
            if logs[i].timestamp_us and logs[i + 1].timestamp_us:
                assert logs[i].timestamp_us >= logs[i + 1].timestamp_us


@pytest.mark.integration
class TestLogCombinedFiltersIntegration:
    """Integration tests for combined log filters."""

    def test_combined_level_and_object_type(self, live_client: VergeClient) -> None:
        """Test combining level and object type filters."""
        logs = live_client.logs.list(
            level=["message", "audit"],
            object_type="VM",
            limit=20
        )

        for log in logs:
            assert log.level in ["message", "audit"]
            assert log.object_type == "vm"

    def test_combined_time_and_level(self, live_client: VergeClient) -> None:
        """Test combining time and level filters."""
        since = datetime.now(timezone.utc) - timedelta(hours=48)
        logs = live_client.logs.list(
            since=since,
            level="message",
            limit=20
        )

        for log in logs:
            assert log.level == "message"
            if log.created_at:
                assert log.created_at >= since

    def test_search_with_level_and_object_type(self, live_client: VergeClient) -> None:
        """Test search with additional filters."""
        logs = live_client.logs.search(
            "power",
            level="audit",
            object_type="VM",
            limit=10
        )

        for log in logs:
            assert "power" in log.text.lower()
            assert log.level == "audit"
            assert log.object_type == "vm"
