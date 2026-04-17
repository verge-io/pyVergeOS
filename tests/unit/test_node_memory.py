"""Unit tests for node memory (DIMM health) operations."""

from __future__ import annotations

from unittest.mock import MagicMock

from pyvergeos.resources.node_memory import (
    NodeMemory,
    NodeMemoryManager,
)

SAMPLE_DIMM = {
    "$key": 1,
    "node": 1,
    "handle": "0x0014",
    "status": "online",
    "status_info": "",
    "label": "",
    "locator": "DIMM 0",
    "bank_locator": "P0 CHANNEL A",
    "type": "DDR5",
    "type_detail": "Synchronous Unbuffered (Unregistered)",
    "size": "48 GB",
    "speed": "5600 MT/s",
    "configured_memory_speed": "5600 MT/s",
    "form_factor": "SODIMM",
    "manufacturer": "Micron Technology",
    "serial_number": "EB687597",
    "part_number": "CT48G56C46S5.M16C1",
    "asset_tag": "Not Specified",
    "rank": "2",
    "data_width": "64 bits",
    "total_width": "64 bits",
    "memory_technology": "DRAM",
    "created": 1774203413,
    "modified": 1774716042,
}

SAMPLE_ERROR_DIMM = {
    "$key": 5,
    "node": 2,
    "handle": "0x0020",
    "status": "error",
    "status_info": "Correctable ECC errors detected",
    "label": "DIMM_A1",
    "locator": "DIMM 2",
    "bank_locator": "P1 CHANNEL A",
    "type": "DDR4",
    "type_detail": "Registered (Buffered)",
    "size": "32 GB",
    "speed": "3200 MT/s",
    "configured_memory_speed": "3200 MT/s",
    "form_factor": "DIMM",
    "manufacturer": "Samsung",
    "serial_number": "ABC123",
    "part_number": "M393A4K40DB3",
    "asset_tag": "DIMM-A1-SLOT2",
    "rank": "2",
    "data_width": "64 bits",
    "total_width": "72 bits",
    "memory_technology": "DRAM",
    "created": 1774000000,
    "modified": 1774500000,
}


class TestNodeMemory:
    """Tests for NodeMemory resource object."""

    def test_key_property(self) -> None:
        dimm = NodeMemory({"$key": 1}, MagicMock())
        assert dimm.key == 1

    def test_node_key(self) -> None:
        dimm = NodeMemory(SAMPLE_DIMM, MagicMock())
        assert dimm.node_key == 1

    def test_node_key_missing(self) -> None:
        dimm = NodeMemory({"$key": 1}, MagicMock())
        assert dimm.node_key is None

    def test_status_online(self) -> None:
        dimm = NodeMemory(SAMPLE_DIMM, MagicMock())
        assert dimm.status == "online"

    def test_status_error(self) -> None:
        dimm = NodeMemory(SAMPLE_ERROR_DIMM, MagicMock())
        assert dimm.status == "error"

    def test_status_info(self) -> None:
        dimm = NodeMemory(SAMPLE_ERROR_DIMM, MagicMock())
        assert dimm.status_info == "Correctable ECC errors detected"

    def test_status_info_empty(self) -> None:
        dimm = NodeMemory(SAMPLE_DIMM, MagicMock())
        assert dimm.status_info == ""

    def test_label(self) -> None:
        dimm = NodeMemory(SAMPLE_ERROR_DIMM, MagicMock())
        assert dimm.label == "DIMM_A1"

    def test_locator(self) -> None:
        dimm = NodeMemory(SAMPLE_DIMM, MagicMock())
        assert dimm.locator == "DIMM 0"

    def test_bank_locator(self) -> None:
        dimm = NodeMemory(SAMPLE_DIMM, MagicMock())
        assert dimm.bank_locator == "P0 CHANNEL A"

    def test_memory_type(self) -> None:
        dimm = NodeMemory(SAMPLE_DIMM, MagicMock())
        assert dimm.memory_type == "DDR5"

    def test_size(self) -> None:
        dimm = NodeMemory(SAMPLE_DIMM, MagicMock())
        assert dimm.size == "48 GB"

    def test_speed(self) -> None:
        dimm = NodeMemory(SAMPLE_DIMM, MagicMock())
        assert dimm.speed == "5600 MT/s"

    def test_form_factor(self) -> None:
        dimm = NodeMemory(SAMPLE_DIMM, MagicMock())
        assert dimm.form_factor == "SODIMM"

    def test_manufacturer(self) -> None:
        dimm = NodeMemory(SAMPLE_DIMM, MagicMock())
        assert dimm.manufacturer == "Micron Technology"

    def test_serial_number(self) -> None:
        dimm = NodeMemory(SAMPLE_DIMM, MagicMock())
        assert dimm.serial_number == "EB687597"

    def test_part_number(self) -> None:
        dimm = NodeMemory(SAMPLE_DIMM, MagicMock())
        assert dimm.part_number == "CT48G56C46S5.M16C1"

    def test_is_healthy_true(self) -> None:
        dimm = NodeMemory(SAMPLE_DIMM, MagicMock())
        assert dimm.is_healthy is True

    def test_is_healthy_false_error(self) -> None:
        dimm = NodeMemory(SAMPLE_ERROR_DIMM, MagicMock())
        assert dimm.is_healthy is False

    def test_is_healthy_false_warning(self) -> None:
        data = {**SAMPLE_DIMM, "status": "warning"}
        dimm = NodeMemory(data, MagicMock())
        assert dimm.is_healthy is False

    def test_repr(self) -> None:
        dimm = NodeMemory(SAMPLE_DIMM, MagicMock())
        r = repr(dimm)
        assert "NodeMemory" in r
        assert "DIMM 0" in r
        assert "online" in r


class TestNodeMemoryManager:
    """Tests for NodeMemoryManager."""

    def test_list_returns_node_memory(self) -> None:
        mock_client = MagicMock()
        mock_client._request.return_value = [SAMPLE_DIMM, SAMPLE_ERROR_DIMM]
        manager = NodeMemoryManager(mock_client)

        dimms = manager.list()

        assert len(dimms) == 2
        assert all(isinstance(d, NodeMemory) for d in dimms)

    def test_list_empty(self) -> None:
        mock_client = MagicMock()
        mock_client._request.return_value = []
        manager = NodeMemoryManager(mock_client)

        assert manager.list() == []

    def test_list_none_response(self) -> None:
        mock_client = MagicMock()
        mock_client._request.return_value = None
        manager = NodeMemoryManager(mock_client)

        assert manager.list() == []

    def test_list_with_node_filter(self) -> None:
        mock_client = MagicMock()
        mock_client._request.return_value = [SAMPLE_DIMM]
        manager = NodeMemoryManager(mock_client, node_key=1)

        _ = manager.list()

        call_args = mock_client._request.call_args
        params = call_args[1].get("params") or call_args[0][2]
        assert "node eq 1" in params.get("filter", "")

    def test_get_by_key(self) -> None:
        mock_client = MagicMock()
        mock_client._request.return_value = SAMPLE_DIMM
        manager = NodeMemoryManager(mock_client)

        dimm = manager.get(key=1)

        assert isinstance(dimm, NodeMemory)
        assert dimm.key == 1

    def test_endpoint(self) -> None:
        mock_client = MagicMock()
        manager = NodeMemoryManager(mock_client)
        assert manager._endpoint == "node_memory"
