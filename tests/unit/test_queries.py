"""Unit tests for async query resource managers."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from pyvergeos.exceptions import NotFoundError, VergeTimeoutError
from pyvergeos.resources.queries import (
    NodeQueryManager,
    QueryResult,
    ServiceContainerQueryManager,
    TenantNodeQueryManager,
    VNetQueryManager,
)


@pytest.fixture
def mock_client() -> MagicMock:
    """Create a mock VergeClient."""
    client = MagicMock()
    client._request = MagicMock()
    return client


# =============================================================================
# Sample Data Fixtures
# =============================================================================


@pytest.fixture
def sample_query_data() -> dict[str, Any]:
    """Sample query result data from API."""
    return {
        "$key": 1,
        "id": "abc123def456",
        "query": "ping",
        "params": {"host": "8.8.8.8"},
        "status": "complete",
        "result": "PING 8.8.8.8: 64 bytes, time=10ms",
        "command": "ping -c 4 8.8.8.8",
        "created": 1704067200000000,
        "modified": 1704067210,
        "expires": 1704070800,
    }


@pytest.fixture
def sample_running_query() -> dict[str, Any]:
    """Sample running query data."""
    return {
        "$key": 2,
        "id": "def789ghi012",
        "query": "tcpdump",
        "params": {"interface": "eth0"},
        "status": "running",
        "result": None,
        "command": "tcpdump -i eth0",
        "created": 1704067200000000,
        "modified": 1704067200,
        "expires": 1704070800,
    }


@pytest.fixture
def sample_error_query() -> dict[str, Any]:
    """Sample error query data."""
    return {
        "$key": 3,
        "id": "err456xyz789",
        "query": "ping",
        "params": {"host": "invalid"},
        "status": "error",
        "result": "ping: unknown host invalid",
        "command": "ping -c 4 invalid",
        "created": 1704067200000000,
        "modified": 1704067205,
        "expires": 1704070800,
    }


# =============================================================================
# QueryResult Tests
# =============================================================================


class TestQueryResult:
    """Tests for QueryResult resource object."""

    def test_query_id(self, sample_query_data: dict[str, Any]) -> None:
        manager = MagicMock()
        result = QueryResult(sample_query_data, manager)
        assert result.query_id == "abc123def456"

    def test_query_type(self, sample_query_data: dict[str, Any]) -> None:
        manager = MagicMock()
        result = QueryResult(sample_query_data, manager)
        assert result.query_type == "ping"

    def test_status_complete(self, sample_query_data: dict[str, Any]) -> None:
        manager = MagicMock()
        result = QueryResult(sample_query_data, manager)
        assert result.status == "complete"
        assert result.is_complete is True
        assert result.is_error is False
        assert result.is_running is False

    def test_status_running(self, sample_running_query: dict[str, Any]) -> None:
        manager = MagicMock()
        result = QueryResult(sample_running_query, manager)
        assert result.status == "running"
        assert result.is_running is True
        assert result.is_complete is False

    def test_status_error(self, sample_error_query: dict[str, Any]) -> None:
        manager = MagicMock()
        result = QueryResult(sample_error_query, manager)
        assert result.status == "error"
        assert result.is_error is True
        assert result.is_complete is False

    def test_result_text(self, sample_query_data: dict[str, Any]) -> None:
        manager = MagicMock()
        result = QueryResult(sample_query_data, manager)
        assert result.result == "PING 8.8.8.8: 64 bytes, time=10ms"

    def test_result_none_when_running(self, sample_running_query: dict[str, Any]) -> None:
        manager = MagicMock()
        result = QueryResult(sample_running_query, manager)
        assert result.result is None

    def test_command(self, sample_query_data: dict[str, Any]) -> None:
        manager = MagicMock()
        result = QueryResult(sample_query_data, manager)
        assert result.command == "ping -c 4 8.8.8.8"

    def test_params(self, sample_query_data: dict[str, Any]) -> None:
        manager = MagicMock()
        result = QueryResult(sample_query_data, manager)
        assert result.params == {"host": "8.8.8.8"}

    def test_defaults_when_empty(self) -> None:
        manager = MagicMock()
        result = QueryResult({}, manager)
        assert result.query_id == ""
        assert result.query_type == ""
        assert result.status == "running"
        assert result.result is None
        assert result.command is None
        assert result.params is None


# =============================================================================
# VNetQueryManager Tests
# =============================================================================


class TestVNetQueryManager:
    """Tests for VNetQueryManager."""

    def test_endpoint(self, mock_client: MagicMock) -> None:
        manager = VNetQueryManager(mock_client, parent_key=10)
        assert manager._endpoint == "vnet_queries"
        assert manager._parent_field == "vnet"
        assert manager._parent_key == 10

    def test_list_filters_by_parent(self, mock_client: MagicMock) -> None:
        mock_client._request.return_value = []
        manager = VNetQueryManager(mock_client, parent_key=10)
        manager.list()
        call_args = mock_client._request.call_args
        assert "vnet eq 10" in call_args.kwargs["params"]["filter"]

    def test_list_returns_query_results(
        self,
        mock_client: MagicMock,
        sample_query_data: dict[str, Any],
    ) -> None:
        mock_client._request.return_value = [sample_query_data]
        manager = VNetQueryManager(mock_client, parent_key=10)
        results = manager.list()
        assert len(results) == 1
        assert isinstance(results[0], QueryResult)
        assert results[0].query_type == "ping"

    def test_list_with_additional_filter(self, mock_client: MagicMock) -> None:
        mock_client._request.return_value = []
        manager = VNetQueryManager(mock_client, parent_key=10)
        manager.list(filter="status eq 'running'")
        call_args = mock_client._request.call_args
        assert "vnet eq 10 and (status eq 'running')" in call_args.kwargs["params"]["filter"]

    def test_list_empty(self, mock_client: MagicMock) -> None:
        mock_client._request.return_value = None
        manager = VNetQueryManager(mock_client, parent_key=10)
        assert manager.list() == []

    def test_get_by_key(
        self,
        mock_client: MagicMock,
        sample_query_data: dict[str, Any],
    ) -> None:
        mock_client._request.return_value = sample_query_data
        manager = VNetQueryManager(mock_client, parent_key=10)
        result = manager.get(1)
        assert isinstance(result, QueryResult)
        assert result.key == 1

    def test_get_by_query_id(
        self,
        mock_client: MagicMock,
        sample_query_data: dict[str, Any],
    ) -> None:
        mock_client._request.return_value = [sample_query_data]
        manager = VNetQueryManager(mock_client, parent_key=10)
        result = manager.get(query_id="abc123def456")
        assert isinstance(result, QueryResult)

    def test_get_not_found(self, mock_client: MagicMock) -> None:
        mock_client._request.return_value = None
        manager = VNetQueryManager(mock_client, parent_key=10)
        with pytest.raises(NotFoundError):
            manager.get(999)

    def test_get_no_args(self, mock_client: MagicMock) -> None:
        manager = VNetQueryManager(mock_client, parent_key=10)
        with pytest.raises(ValueError, match="Either key or query_id"):
            manager.get()

    def test_create(
        self,
        mock_client: MagicMock,
        sample_query_data: dict[str, Any],
    ) -> None:
        mock_client._request.return_value = sample_query_data
        manager = VNetQueryManager(mock_client, parent_key=10)
        manager.create("ping", params={"host": "8.8.8.8"})

        # Verify POST was called correctly
        post_call = mock_client._request.call_args_list[0]
        assert post_call.args[0] == "POST"
        assert post_call.args[1] == "vnet_queries"
        body = post_call.kwargs["json_data"]
        assert body["vnet"] == 10
        assert body["query"] == "ping"
        assert body["params"] == {"host": "8.8.8.8"}

    def test_create_no_params(
        self,
        mock_client: MagicMock,
        sample_query_data: dict[str, Any],
    ) -> None:
        mock_client._request.return_value = sample_query_data
        manager = VNetQueryManager(mock_client, parent_key=10)
        manager.create("arp")

        post_call = mock_client._request.call_args_list[0]
        body = post_call.kwargs["json_data"]
        assert "params" not in body
        assert body["query"] == "arp"

    @patch("pyvergeos.resources.queries.time.sleep")
    def test_wait_complete(
        self,
        mock_sleep: MagicMock,
        mock_client: MagicMock,
        sample_query_data: dict[str, Any],
    ) -> None:
        mock_client._request.return_value = sample_query_data
        manager = VNetQueryManager(mock_client, parent_key=10)
        result = manager.wait(1, timeout=10)
        assert result.is_complete

    @patch("pyvergeos.resources.queries.time.sleep")
    @patch("pyvergeos.resources.queries.time.monotonic")
    def test_wait_timeout(
        self,
        mock_monotonic: MagicMock,
        mock_sleep: MagicMock,
        mock_client: MagicMock,
        sample_running_query: dict[str, Any],
    ) -> None:
        mock_client._request.return_value = sample_running_query
        mock_monotonic.side_effect = [0.0, 0.0, 11.0]
        manager = VNetQueryManager(mock_client, parent_key=10)
        with pytest.raises(VergeTimeoutError, match="did not complete"):
            manager.wait(2, timeout=10)

    @patch("pyvergeos.resources.queries.time.sleep")
    def test_wait_error_returns(
        self,
        mock_sleep: MagicMock,
        mock_client: MagicMock,
        sample_error_query: dict[str, Any],
    ) -> None:
        mock_client._request.return_value = sample_error_query
        manager = VNetQueryManager(mock_client, parent_key=10)
        result = manager.wait(3, timeout=10)
        assert result.is_error

    @patch("pyvergeos.resources.queries.time.sleep")
    def test_run_creates_and_waits(
        self,
        mock_sleep: MagicMock,
        mock_client: MagicMock,
        sample_query_data: dict[str, Any],
    ) -> None:
        mock_client._request.return_value = sample_query_data
        manager = VNetQueryManager(mock_client, parent_key=10)
        result = manager.run("ping", {"host": "8.8.8.8"})
        assert result.is_complete

    # Convenience method tests

    @patch("pyvergeos.resources.queries.time.sleep")
    def test_ping(
        self,
        mock_sleep: MagicMock,
        mock_client: MagicMock,
        sample_query_data: dict[str, Any],
    ) -> None:
        mock_client._request.return_value = sample_query_data
        manager = VNetQueryManager(mock_client, parent_key=10)
        result = manager.ping("8.8.8.8")
        assert isinstance(result, QueryResult)

    @patch("pyvergeos.resources.queries.time.sleep")
    def test_dns(
        self,
        mock_sleep: MagicMock,
        mock_client: MagicMock,
        sample_query_data: dict[str, Any],
    ) -> None:
        mock_client._request.return_value = sample_query_data
        manager = VNetQueryManager(mock_client, parent_key=10)
        result = manager.dns("example.com")
        assert isinstance(result, QueryResult)

    @patch("pyvergeos.resources.queries.time.sleep")
    def test_traceroute(
        self,
        mock_sleep: MagicMock,
        mock_client: MagicMock,
        sample_query_data: dict[str, Any],
    ) -> None:
        mock_client._request.return_value = sample_query_data
        manager = VNetQueryManager(mock_client, parent_key=10)
        result = manager.traceroute("8.8.8.8")
        assert isinstance(result, QueryResult)

    @patch("pyvergeos.resources.queries.time.sleep")
    def test_arp(
        self,
        mock_sleep: MagicMock,
        mock_client: MagicMock,
        sample_query_data: dict[str, Any],
    ) -> None:
        mock_client._request.return_value = sample_query_data
        manager = VNetQueryManager(mock_client, parent_key=10)
        result = manager.arp()
        assert isinstance(result, QueryResult)

    @patch("pyvergeos.resources.queries.time.sleep")
    def test_firewall(
        self,
        mock_sleep: MagicMock,
        mock_client: MagicMock,
        sample_query_data: dict[str, Any],
    ) -> None:
        mock_client._request.return_value = sample_query_data
        manager = VNetQueryManager(mock_client, parent_key=10)
        result = manager.firewall()
        assert isinstance(result, QueryResult)

    @patch("pyvergeos.resources.queries.time.sleep")
    def test_trace(
        self,
        mock_sleep: MagicMock,
        mock_client: MagicMock,
        sample_query_data: dict[str, Any],
    ) -> None:
        mock_client._request.return_value = sample_query_data
        manager = VNetQueryManager(mock_client, parent_key=10)
        result = manager.trace()
        assert isinstance(result, QueryResult)


# =============================================================================
# NodeQueryManager Tests
# =============================================================================


class TestNodeQueryManager:
    """Tests for NodeQueryManager."""

    def test_endpoint(self, mock_client: MagicMock) -> None:
        manager = NodeQueryManager(mock_client, parent_key=5)
        assert manager._endpoint == "node_queries"
        assert manager._parent_field == "node"

    @patch("pyvergeos.resources.queries.time.sleep")
    def test_smartctl(
        self,
        mock_sleep: MagicMock,
        mock_client: MagicMock,
        sample_query_data: dict[str, Any],
    ) -> None:
        mock_client._request.return_value = sample_query_data
        manager = NodeQueryManager(mock_client, parent_key=5)
        result = manager.smartctl("/dev/sda")
        assert isinstance(result, QueryResult)

    @patch("pyvergeos.resources.queries.time.sleep")
    def test_lsblk(
        self,
        mock_sleep: MagicMock,
        mock_client: MagicMock,
        sample_query_data: dict[str, Any],
    ) -> None:
        mock_client._request.return_value = sample_query_data
        manager = NodeQueryManager(mock_client, parent_key=5)
        result = manager.lsblk()
        assert isinstance(result, QueryResult)

    @patch("pyvergeos.resources.queries.time.sleep")
    def test_dmidecode(
        self,
        mock_sleep: MagicMock,
        mock_client: MagicMock,
        sample_query_data: dict[str, Any],
    ) -> None:
        mock_client._request.return_value = sample_query_data
        manager = NodeQueryManager(mock_client, parent_key=5)
        result = manager.dmidecode()
        assert isinstance(result, QueryResult)


# =============================================================================
# ServiceContainerQueryManager Tests
# =============================================================================


class TestServiceContainerQueryManager:
    """Tests for ServiceContainerQueryManager."""

    def test_endpoint(self, mock_client: MagicMock) -> None:
        manager = ServiceContainerQueryManager(mock_client, parent_key=3)
        assert manager._endpoint == "service_container_queries"
        assert manager._parent_field == "service_container"

    @patch("pyvergeos.resources.queries.time.sleep")
    def test_ping(
        self,
        mock_sleep: MagicMock,
        mock_client: MagicMock,
        sample_query_data: dict[str, Any],
    ) -> None:
        mock_client._request.return_value = sample_query_data
        manager = ServiceContainerQueryManager(mock_client, parent_key=3)
        result = manager.ping("8.8.8.8")
        assert isinstance(result, QueryResult)


# =============================================================================
# TenantNodeQueryManager Tests
# =============================================================================


class TestTenantNodeQueryManager:
    """Tests for TenantNodeQueryManager."""

    def test_endpoint(self, mock_client: MagicMock) -> None:
        manager = TenantNodeQueryManager(mock_client, parent_key=7)
        assert manager._endpoint == "tenant_node_queries"
        assert manager._parent_field == "tenant_node"

    @patch("pyvergeos.resources.queries.time.sleep")
    def test_dns(
        self,
        mock_sleep: MagicMock,
        mock_client: MagicMock,
        sample_query_data: dict[str, Any],
    ) -> None:
        mock_client._request.return_value = sample_query_data
        manager = TenantNodeQueryManager(mock_client, parent_key=7)
        result = manager.dns("example.com")
        assert isinstance(result, QueryResult)
