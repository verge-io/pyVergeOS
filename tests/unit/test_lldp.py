"""Unit tests for LLDP neighbor resource manager."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from pyvergeos.resources.lldp import NodeLLDPNeighbor, NodeLLDPNeighborManager


@pytest.fixture
def mock_client() -> MagicMock:
    """Create a mock VergeClient."""
    client = MagicMock()
    client._request = MagicMock()
    return client


@pytest.fixture
def sample_lldp_data() -> dict[str, Any]:
    """Sample LLDP neighbor data from API."""
    return {
        "$key": 1,
        "node": 5,
        "nic": 42,
        "rid": "1",
        "via": "LLDP",
        "age": "0 day, 00:05:30",
        "chassis": {
            "name": "switch01.example.com",
            "ChassisID": "aa:bb:cc:dd:ee:ff",
            "descr": "Arista Networks EOS",
        },
        "port": {
            "PortID": "Ethernet1/1",
            "descr": "Server Port 1",
        },
        "vlan": {"vlan-id": 100, "pvid": "yes"},
        "other": {"mfs": 9216},
    }


# =============================================================================
# NodeLLDPNeighbor Tests
# =============================================================================


class TestNodeLLDPNeighbor:
    """Tests for NodeLLDPNeighbor resource object."""

    def test_node_key(self, sample_lldp_data: dict[str, Any]) -> None:
        neighbor = NodeLLDPNeighbor(sample_lldp_data, MagicMock())
        assert neighbor.node_key == 5

    def test_nic_key(self, sample_lldp_data: dict[str, Any]) -> None:
        neighbor = NodeLLDPNeighbor(sample_lldp_data, MagicMock())
        assert neighbor.nic_key == 42

    def test_remote_id(self, sample_lldp_data: dict[str, Any]) -> None:
        neighbor = NodeLLDPNeighbor(sample_lldp_data, MagicMock())
        assert neighbor.remote_id == "1"

    def test_via(self, sample_lldp_data: dict[str, Any]) -> None:
        neighbor = NodeLLDPNeighbor(sample_lldp_data, MagicMock())
        assert neighbor.via == "LLDP"

    def test_age(self, sample_lldp_data: dict[str, Any]) -> None:
        neighbor = NodeLLDPNeighbor(sample_lldp_data, MagicMock())
        assert neighbor.age == "0 day, 00:05:30"

    def test_chassis(self, sample_lldp_data: dict[str, Any]) -> None:
        neighbor = NodeLLDPNeighbor(sample_lldp_data, MagicMock())
        assert isinstance(neighbor.chassis, dict)
        assert neighbor.chassis["name"] == "switch01.example.com"

    def test_port(self, sample_lldp_data: dict[str, Any]) -> None:
        neighbor = NodeLLDPNeighbor(sample_lldp_data, MagicMock())
        assert isinstance(neighbor.port, dict)
        assert neighbor.port["PortID"] == "Ethernet1/1"

    def test_vlan(self, sample_lldp_data: dict[str, Any]) -> None:
        neighbor = NodeLLDPNeighbor(sample_lldp_data, MagicMock())
        assert isinstance(neighbor.vlan, dict)
        assert neighbor.vlan["vlan-id"] == 100

    def test_other(self, sample_lldp_data: dict[str, Any]) -> None:
        neighbor = NodeLLDPNeighbor(sample_lldp_data, MagicMock())
        assert isinstance(neighbor.other, dict)

    def test_chassis_name(self, sample_lldp_data: dict[str, Any]) -> None:
        neighbor = NodeLLDPNeighbor(sample_lldp_data, MagicMock())
        assert neighbor.chassis_name == "switch01.example.com"

    def test_chassis_name_fallback(self) -> None:
        neighbor = NodeLLDPNeighbor(
            {"$key": 1, "chassis": {"ChassisID": "aa:bb:cc:dd:ee:ff"}},
            MagicMock(),
        )
        assert neighbor.chassis_name == "aa:bb:cc:dd:ee:ff"

    def test_chassis_name_none(self) -> None:
        neighbor = NodeLLDPNeighbor({"$key": 1}, MagicMock())
        assert neighbor.chassis_name is None

    def test_port_id(self, sample_lldp_data: dict[str, Any]) -> None:
        neighbor = NodeLLDPNeighbor(sample_lldp_data, MagicMock())
        assert neighbor.port_id == "Ethernet1/1"

    def test_port_id_none(self) -> None:
        neighbor = NodeLLDPNeighbor({"$key": 1}, MagicMock())
        assert neighbor.port_id is None

    def test_defaults_when_empty(self) -> None:
        neighbor = NodeLLDPNeighbor({}, MagicMock())
        assert neighbor.node_key == 0
        assert neighbor.nic_key == 0
        assert neighbor.remote_id is None
        assert neighbor.via is None
        assert neighbor.age is None
        assert neighbor.chassis is None
        assert neighbor.port is None
        assert neighbor.vlan is None


# =============================================================================
# NodeLLDPNeighborManager Tests
# =============================================================================


class TestNodeLLDPNeighborManager:
    """Tests for NodeLLDPNeighborManager."""

    def test_endpoint(self, mock_client: MagicMock) -> None:
        manager = NodeLLDPNeighborManager(mock_client, node_key=5)
        assert manager._endpoint == "node_lldp_neighbors"

    def test_list_scoped(
        self,
        mock_client: MagicMock,
        sample_lldp_data: dict[str, Any],
    ) -> None:
        mock_client._request.return_value = [sample_lldp_data]
        manager = NodeLLDPNeighborManager(mock_client, node_key=5)
        results = manager.list()
        assert len(results) == 1
        assert isinstance(results[0], NodeLLDPNeighbor)

    def test_list_filters_by_node(self, mock_client: MagicMock) -> None:
        mock_client._request.return_value = []
        manager = NodeLLDPNeighborManager(mock_client, node_key=5)
        manager.list()
        call_args = mock_client._request.call_args
        assert "node eq 5" in call_args.kwargs["params"]["filter"]

    def test_list_global(
        self,
        mock_client: MagicMock,
        sample_lldp_data: dict[str, Any],
    ) -> None:
        mock_client._request.return_value = [sample_lldp_data]
        manager = NodeLLDPNeighborManager(mock_client)
        results = manager.list()
        assert len(results) == 1
        # No filter should be set for global
        call_args = mock_client._request.call_args
        assert "filter" not in call_args.kwargs["params"]

    def test_list_empty(self, mock_client: MagicMock) -> None:
        mock_client._request.return_value = None
        manager = NodeLLDPNeighborManager(mock_client, node_key=5)
        assert manager.list() == []

    def test_list_by_nic(self, mock_client: MagicMock) -> None:
        mock_client._request.return_value = []
        manager = NodeLLDPNeighborManager(mock_client, node_key=5)
        manager.list_by_nic(42)
        call_args = mock_client._request.call_args
        assert "nic eq 42" in call_args.kwargs["params"]["filter"]

    def test_list_with_additional_filter(self, mock_client: MagicMock) -> None:
        mock_client._request.return_value = []
        manager = NodeLLDPNeighborManager(mock_client, node_key=5)
        manager.list(filter="nic eq 42")
        call_args = mock_client._request.call_args
        filter_str = call_args.kwargs["params"]["filter"]
        assert "node eq 5" in filter_str
        assert "nic eq 42" in filter_str
