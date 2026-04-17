"""Unit tests for vSAN query operations."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from pyvergeos.exceptions import VergeTimeoutError
from pyvergeos.resources.queries import QueryResult
from pyvergeos.resources.vsan_queries import VsanQueryManager


SAMPLE_QUERY_CREATED = {
    "$key": "abc123def456",
    "location": "/v4/vsan_queries/abc123def456",
    "dbpath": "vsan_queries/abc123def456",
    "$row": 1,
}

SAMPLE_QUERY_RUNNING = {
    "$key": "abc123def456",
    "id": "abc123def456",
    "query": "getjournalstatus",
    "params": [],
    "status": "running",
    "result": "",
    "command": "vcmd getjournalstatus",
    "created": 1776388317910047,
    "modified": 1776388317,
    "expires": 1776391917,
}

SAMPLE_JOURNAL_COMPLETE = {
    "$key": "abc123def456",
    "id": "abc123def456",
    "query": "getjournalstatus",
    "params": [],
    "status": "complete",
    "result": (
        '0) status = (string) "flushing open files"\r\n'
        "1) alive = (bool) true\r\n"
        "2) cur_transaction = (uint64) 270326\r\n"
        "3) redundant = (bool) true\r\n"
    ),
    "command": "vcmd getjournalstatus",
    "created": 1776388317910047,
    "modified": 1776388318,
    "expires": 1776391917,
}

SAMPLE_TIER_COMPLETE = {
    "$key": "def789",
    "id": "def789",
    "query": "gettierstatus",
    "params": [],
    "status": "complete",
    "result": (
        "0) tier_1 = (serstring)\r\n{\r\n"
        "     0) tier = (int) 1\r\n"
        "     1) redundancy = (int) 2\r\n"
        "     2) redundant = (bool) true\r\n}\r\n"
    ),
    "command": "vcmd gettierstatus",
    "created": 1776388337777135,
    "modified": 1776388337,
    "expires": 1776391937,
}

SAMPLE_REPAIR_COMPLETE = {
    "$key": "ghi012",
    "id": "ghi012",
    "query": "getrepairstatus",
    "params": {"node": 1},
    "status": "complete",
    "result": (
        "0) device_0 = (uint64) 0\r\n"
        "1) device_1 = (uint64) 0\r\n"
    ),
    "command": "vcmd getrepairstatus",
    "created": 1776388451693922,
    "modified": 1776388451,
    "expires": 1776392051,
}


class TestVsanQueryManager:
    """Tests for VsanQueryManager."""

    def test_endpoint(self) -> None:
        mock_client = MagicMock()
        manager = VsanQueryManager(mock_client)
        assert manager._endpoint == "vsan_queries"

    def test_create_journal_query(self) -> None:
        mock_client = MagicMock()
        mock_client._request.side_effect = [
            SAMPLE_QUERY_CREATED,
            SAMPLE_JOURNAL_COMPLETE,
        ]
        manager = VsanQueryManager(mock_client)

        result = manager.create("getjournalstatus")

        # Verify POST was called with correct body
        post_call = mock_client._request.call_args_list[0]
        assert post_call[0][0] == "POST"
        assert post_call[0][1] == "vsan_queries"
        body = post_call[1].get("json_data") or post_call[0][2]
        assert body["query"] == "getjournalstatus"

    def test_create_repair_query_with_params(self) -> None:
        mock_client = MagicMock()
        mock_client._request.side_effect = [
            SAMPLE_QUERY_CREATED,
            SAMPLE_REPAIR_COMPLETE,
        ]
        manager = VsanQueryManager(mock_client)

        result = manager.create("getrepairstatus", params={"node": 1})

        post_call = mock_client._request.call_args_list[0]
        body = post_call[1].get("json_data") or post_call[0][2]
        assert body["query"] == "getrepairstatus"
        assert body["params"] == {"node": 1}

    def test_wait_returns_completed(self) -> None:
        mock_client = MagicMock()
        mock_client._request.return_value = SAMPLE_JOURNAL_COMPLETE
        manager = VsanQueryManager(mock_client)

        result = manager.wait("abc123def456")

        assert isinstance(result, QueryResult)
        assert result.status == "complete"

    def test_wait_polls_until_complete(self) -> None:
        mock_client = MagicMock()
        mock_client._request.side_effect = [
            SAMPLE_QUERY_RUNNING,
            SAMPLE_QUERY_RUNNING,
            SAMPLE_JOURNAL_COMPLETE,
        ]
        manager = VsanQueryManager(mock_client)

        with patch("time.sleep"):
            result = manager.wait("abc123def456", poll_interval=0.01)

        assert result.status == "complete"
        assert mock_client._request.call_count == 3

    def test_wait_timeout(self) -> None:
        mock_client = MagicMock()
        mock_client._request.return_value = SAMPLE_QUERY_RUNNING
        manager = VsanQueryManager(mock_client)

        with patch("time.monotonic", side_effect=[0, 0.5, 1.0, 2.0, 3.0]):
            with pytest.raises(VergeTimeoutError):
                manager.wait("abc123def456", timeout=2, poll_interval=0.01)

    def test_run_creates_and_waits(self) -> None:
        mock_client = MagicMock()
        mock_client._request.side_effect = [
            SAMPLE_QUERY_CREATED,
            SAMPLE_JOURNAL_COMPLETE,  # From get() inside create()
            SAMPLE_JOURNAL_COMPLETE,  # From wait()
        ]
        manager = VsanQueryManager(mock_client)

        with patch("time.sleep"):
            result = manager.run("getjournalstatus")

        assert isinstance(result, QueryResult)
        assert result.status == "complete"

    def test_journal_status(self) -> None:
        mock_client = MagicMock()
        mock_client._request.side_effect = [
            SAMPLE_QUERY_CREATED,
            SAMPLE_JOURNAL_COMPLETE,
            SAMPLE_JOURNAL_COMPLETE,
        ]
        manager = VsanQueryManager(mock_client)

        with patch("time.sleep"):
            result = manager.journal_status()

        assert result.status == "complete"
        assert "flushing open files" in result.result

    def test_tier_status(self) -> None:
        mock_client = MagicMock()
        mock_client._request.side_effect = [
            SAMPLE_QUERY_CREATED,
            SAMPLE_TIER_COMPLETE,
            SAMPLE_TIER_COMPLETE,
        ]
        manager = VsanQueryManager(mock_client)

        with patch("time.sleep"):
            result = manager.tier_status()

        assert result.status == "complete"
        assert "tier_1" in result.result

    def test_repair_status(self) -> None:
        mock_client = MagicMock()
        mock_client._request.side_effect = [
            SAMPLE_QUERY_CREATED,
            SAMPLE_REPAIR_COMPLETE,
            SAMPLE_REPAIR_COMPLETE,
        ]
        manager = VsanQueryManager(mock_client)

        with patch("time.sleep"):
            result = manager.repair_status(node_key=1)

        assert result.status == "complete"

        # Verify node param was passed
        post_call = mock_client._request.call_args_list[0]
        body = post_call[1].get("json_data") or post_call[0][2]
        assert body["params"] == {"node": 1}

    def test_list(self) -> None:
        mock_client = MagicMock()
        mock_client._request.return_value = [
            SAMPLE_JOURNAL_COMPLETE,
            SAMPLE_TIER_COMPLETE,
        ]
        manager = VsanQueryManager(mock_client)

        results = manager.list()

        assert len(results) == 2
        assert all(isinstance(r, QueryResult) for r in results)

    def test_get_by_key(self) -> None:
        mock_client = MagicMock()
        mock_client._request.return_value = SAMPLE_JOURNAL_COMPLETE
        manager = VsanQueryManager(mock_client)

        result = manager.get(key="abc123def456")

        assert isinstance(result, QueryResult)
        assert result.key == "abc123def456"
