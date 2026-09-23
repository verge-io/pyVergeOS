"""Unit tests for the cluster status manager (issue #127)."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from pyvergeos.exceptions import NotFoundError
from pyvergeos.resources.cluster_status import (
    ClusterStatus,
    ClusterStatusManager,
)


@pytest.fixture
def mock_client() -> MagicMock:
    client = MagicMock()
    client._request = MagicMock()
    return client


@pytest.fixture
def sample_status() -> dict[str, Any]:
    # A two-node cluster with headroom, modelled on live lab figures.
    return {
        "$key": 1,
        "cluster": 1,
        "status": "online",
        "state": "online",
        "total_nodes": 2,
        "online_nodes": 2,
        "total_ram": 137472,
        "online_ram": 137472,
        "used_ram": 9216,
        "total_cores": 64,
        "online_cores": 64,
        "used_cores": 5,
        "running_machines": 3,
    }


class TestClusterStatusModel:
    def test_capacity_fields(self, sample_status: dict[str, Any]) -> None:
        s = ClusterStatus(sample_status, MagicMock())
        assert s.cluster_key == 1
        assert s.online_nodes == 2
        assert s.online_ram == 137472
        assert s.used_ram == 9216
        assert s.online_cores == 64
        assert s.used_cores == 5
        assert s.is_online is True

    def test_can_lose_one_node_true_with_headroom(self, sample_status: dict[str, Any]) -> None:
        # surviving one node: 68736 MB RAM / 32 cores, vs 9216 used / 5 used
        assert ClusterStatus(sample_status, MagicMock()).can_lose_one_node() is True

    def test_can_lose_one_node_false_when_overcommitted(
        self, sample_status: dict[str, Any]
    ) -> None:
        tight = dict(sample_status, used_ram=100000)  # exceeds one surviving node
        assert ClusterStatus(tight, MagicMock()).can_lose_one_node() is False

    def test_can_lose_one_node_false_with_single_node(self, sample_status: dict[str, Any]) -> None:
        single = dict(sample_status, online_nodes=1)
        assert ClusterStatus(single, MagicMock()).can_lose_one_node() is False

    def test_can_lose_one_node_core_bound(self, sample_status: dict[str, Any]) -> None:
        # RAM fine, but used cores exceed one surviving node's share (32)
        core_tight = dict(sample_status, used_cores=40)
        assert ClusterStatus(core_tight, MagicMock()).can_lose_one_node() is False

    def test_missing_fields_default_to_zero(self) -> None:
        s = ClusterStatus({"$key": 1, "cluster": 2}, MagicMock())
        assert s.online_nodes == 0
        assert s.used_ram == 0
        assert s.can_lose_one_node() is False


class TestClusterStatusManager:
    def test_get_scoped_filters_by_cluster(
        self, mock_client: MagicMock, sample_status: dict[str, Any]
    ) -> None:
        mock_client._request.return_value = [sample_status]
        manager = ClusterStatusManager(mock_client, cluster_key=1)
        s = manager.get()
        call = mock_client._request.call_args
        assert call.args[1] == "cluster_status"
        assert "cluster eq 1" in call.kwargs["params"]["filter"]
        assert s.cluster_key == 1

    def test_get_by_key_uses_path(
        self, mock_client: MagicMock, sample_status: dict[str, Any]
    ) -> None:
        mock_client._request.return_value = sample_status
        s = ClusterStatusManager(mock_client).get(key=1)
        call = mock_client._request.call_args
        assert call.args[1] == "cluster_status/1"
        assert s.online_nodes == 2

    def test_get_scoped_not_found(self, mock_client: MagicMock) -> None:
        mock_client._request.return_value = []
        with pytest.raises(NotFoundError):
            ClusterStatusManager(mock_client, cluster_key=999).get()

    def test_get_no_scope_no_key_raises(self, mock_client: MagicMock) -> None:
        with pytest.raises(ValueError, match="Either key or a scoped cluster_key"):
            ClusterStatusManager(mock_client).get()

    def test_list_defaults_fields_so_rows_are_populated(
        self, mock_client: MagicMock, sample_status: dict[str, Any]
    ) -> None:
        mock_client._request.return_value = [sample_status]
        rows = ClusterStatusManager(mock_client).list()
        call = mock_client._request.call_args
        assert "online_nodes" in call.kwargs["params"]["fields"]
        assert rows[0].online_nodes == 2

    def test_list_filter_passthrough(
        self, mock_client: MagicMock, sample_status: dict[str, Any]
    ) -> None:
        mock_client._request.return_value = [sample_status]
        ClusterStatusManager(mock_client).list(filter="cluster eq 1")
        call = mock_client._request.call_args
        assert "cluster eq 1" in call.kwargs["params"]["filter"]


class TestClusterScopedAccessor:
    def test_cluster_exposes_scoped_cluster_status(self, mock_client: MagicMock) -> None:
        from pyvergeos.resources.clusters import Cluster

        mgr = MagicMock()
        mgr._client = mock_client
        cluster = Cluster({"$key": 1}, mgr)
        scoped = cluster.cluster_status
        assert isinstance(scoped, ClusterStatusManager)
        assert scoped._cluster_key == 1

    def test_client_exposes_cluster_status_manager(self, mock_client: MagicMock) -> None:
        # client fixture here is a MagicMock; assert the real property on the class
        from pyvergeos.client import VergeClient

        assert isinstance(getattr(VergeClient, "cluster_status", None), property)
        assert isinstance(getattr(VergeClient, "machine_drive_stats", None), property)


class TestClusterStatusCoverage:
    """Exercise the remaining accessors and get() branches."""

    def test_all_accessors_on_populated_row(self, sample_status: dict[str, Any]) -> None:
        s = ClusterStatus(sample_status, MagicMock())
        assert s.status == "online"
        assert s.state == "online"
        assert s.total_nodes == 2
        assert s.total_ram == 137472
        assert s.total_cores == 64
        assert s.running_machines == 3

    def test_get_by_key_none_response_raises(self, mock_client: MagicMock) -> None:
        mock_client._request.return_value = None
        with pytest.raises(NotFoundError, match="not found"):
            ClusterStatusManager(mock_client).get(key=1)

    def test_get_by_key_non_dict_response_raises(self, mock_client: MagicMock) -> None:
        mock_client._request.return_value = ["unexpected"]
        with pytest.raises(NotFoundError, match="invalid response"):
            ClusterStatusManager(mock_client).get(key=1)

    def test_scoped_none_response_raises(self, mock_client: MagicMock) -> None:
        mock_client._request.return_value = None
        with pytest.raises(NotFoundError):
            ClusterStatusManager(mock_client, cluster_key=1).get()

    def test_scoped_single_dict_response_is_accepted(
        self, mock_client: MagicMock, sample_status: dict[str, Any]
    ) -> None:
        # some endpoints answer a filtered query with a bare object, not a list
        mock_client._request.return_value = sample_status
        s = ClusterStatusManager(mock_client, cluster_key=1).get()
        assert s.online_nodes == 2

    def test_list_with_explicit_fields_is_passed_through(
        self, mock_client: MagicMock, sample_status: dict[str, Any]
    ) -> None:
        mock_client._request.return_value = [sample_status]
        ClusterStatusManager(mock_client).list(fields=["$key", "cluster"])
        assert "cluster" in mock_client._request.call_args.kwargs["params"]["fields"]


def test_cluster_status_get_by_key_with_explicit_fields(
    mock_client: MagicMock, sample_status: dict[str, Any]
) -> None:
    mock_client._request.return_value = sample_status
    ClusterStatusManager(mock_client).get(key=1, fields=["$key", "cluster"])
    assert "cluster" in mock_client._request.call_args.kwargs["params"]["fields"]
