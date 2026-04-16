"""Unit tests for VM NIC operations."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from pyvergeos import VergeClient
from pyvergeos.exceptions import NotFoundError
from pyvergeos.resources.nics import (
    INTERFACE_DISPLAY_MAP,
    NIC,
    MachineNICManager,
    NICManager,
)
from pyvergeos.resources.nodes import Node
from pyvergeos.resources.vms import VM


class TestNICManager:
    """Unit tests for NICManager."""

    @pytest.fixture
    def vm(self, mock_client: VergeClient) -> VM:
        """Create a mock VM."""
        return VM(
            {"$key": 100, "name": "test-vm", "machine": 200},
            mock_client.vms,
        )

    def test_list_nics(self, mock_client: VergeClient, mock_session: MagicMock, vm: VM) -> None:
        """Test listing NICs."""
        mock_session.request.return_value.json.return_value = [
            {
                "$key": 1,
                "name": "eth0",
                "interface": "virtio",
                "macaddress": "aa:bb:cc:dd:ee:ff",
                "vnet_name": "Internal",
            },
            {
                "$key": 2,
                "name": "eth1",
                "interface": "e1000e",
                "macaddress": "11:22:33:44:55:66",
                "vnet_name": "External",
            },
        ]

        nics = vm.nics.list()

        assert len(nics) == 2
        assert nics[0].name == "eth0"
        assert nics[1].name == "eth1"

    def test_list_nics_filters_by_machine(
        self, mock_client: VergeClient, mock_session: MagicMock, vm: VM
    ) -> None:
        """Test that list() filters by machine key."""
        mock_session.request.return_value.json.return_value = []

        vm.nics.list()

        call_args = mock_session.request.call_args
        params = call_args.kwargs.get("params", {})
        assert "machine eq 200" in params.get("filter", "")

    def test_get_nic_by_key(
        self, mock_client: VergeClient, mock_session: MagicMock, vm: VM
    ) -> None:
        """Test getting a NIC by key."""
        mock_session.request.return_value.json.return_value = {
            "$key": 1,
            "name": "eth0",
            "interface": "virtio",
        }

        nic = vm.nics.get(1)

        assert nic.key == 1
        assert nic.name == "eth0"

    def test_get_nic_by_name(
        self, mock_client: VergeClient, mock_session: MagicMock, vm: VM
    ) -> None:
        """Test getting a NIC by name."""
        mock_session.request.return_value.json.return_value = [
            {
                "$key": 1,
                "name": "eth0",
                "interface": "virtio",
            }
        ]

        nic = vm.nics.get(name="eth0")

        assert nic.name == "eth0"

    def test_get_nic_not_found(
        self, mock_client: VergeClient, mock_session: MagicMock, vm: VM
    ) -> None:
        """Test NotFoundError when NIC not found."""
        mock_session.request.return_value.json.return_value = []

        with pytest.raises(NotFoundError):
            vm.nics.get(name="nonexistent")

    def test_create_nic_with_network_key(
        self, mock_client: VergeClient, mock_session: MagicMock, vm: VM
    ) -> None:
        """Test creating a NIC with network key."""
        # First call is POST (create), second is GET (fetch full data)
        mock_session.request.return_value.json.side_effect = [
            {"$key": 3, "name": "eth2", "interface": "virtio", "vnet": 5},
            {"$key": 3, "name": "eth2", "interface": "virtio", "vnet": 5},
        ]

        nic = vm.nics.create(network=5, name="eth2")

        assert nic.name == "eth2"
        # Find the POST call to machine_nics endpoint
        post_calls = [
            call
            for call in mock_session.request.call_args_list
            if call.kwargs.get("method") == "POST" and "machine_nics" in call.kwargs.get("url", "")
        ]
        assert len(post_calls) == 1
        body = post_calls[0].kwargs.get("json", {})
        assert body["machine"] == 200
        assert body["vnet"] == 5

    def test_create_nic_with_network_name(
        self, mock_client: VergeClient, mock_session: MagicMock, vm: VM
    ) -> None:
        """Test creating a NIC with network name lookup."""
        # First call returns network lookup, second creates NIC, third fetches full data
        mock_session.request.return_value.json.side_effect = [
            [{"$key": 10, "name": "Internal"}],  # Network lookup
            {"$key": 4, "name": "eth3", "vnet": 10},  # Created NIC (POST response)
            {"$key": 4, "name": "eth3", "vnet": 10},  # GET full NIC data
        ]

        nic = vm.nics.create(network="Internal", name="eth3")

        assert nic.name == "eth3"

    def test_create_nic_with_mac_address(
        self, mock_client: VergeClient, mock_session: MagicMock, vm: VM
    ) -> None:
        """Test creating a NIC with MAC address."""
        # Reset call history from fixture setup
        mock_session.request.reset_mock()

        # First call is POST (create), second is GET (fetch full data)
        mock_session.request.return_value.json.side_effect = [
            {"$key": 5, "name": "eth4", "macaddress": "aa:bb:cc:dd:ee:ff"},
            {"$key": 5, "name": "eth4", "macaddress": "aa:bb:cc:dd:ee:ff"},
        ]

        vm.nics.create(mac_address="AA:BB:CC:DD:EE:FF")

        # Check the first request body (the POST call)
        call_args_list = mock_session.request.call_args_list
        body = call_args_list[0].kwargs.get("json", {})
        assert body["macaddress"] == "aa:bb:cc:dd:ee:ff"

    def test_delete_nic(self, mock_client: VergeClient, mock_session: MagicMock, vm: VM) -> None:
        """Test deleting a NIC."""
        mock_session.request.return_value.status_code = 204
        mock_session.request.return_value.text = ""

        vm.nics.delete(1)

        call_args = mock_session.request.call_args
        assert call_args.kwargs["method"] == "DELETE"
        assert "machine_nics/1" in call_args.kwargs["url"]

    def test_update_nic(self, mock_client: VergeClient, mock_session: MagicMock, vm: VM) -> None:
        """Test updating a NIC."""
        mock_session.request.return_value.json.return_value = {
            "$key": 1,
            "name": "eth0",
            "description": "Updated description",
        }

        nic = vm.nics.update(1, description="Updated description")

        assert nic.get("description") == "Updated description"


class TestNIC:
    """Unit tests for NIC object."""

    @pytest.fixture
    def nic_data(self) -> dict[str, Any]:
        """Sample NIC data."""
        return {
            "$key": 1,
            "name": "eth0",
            "interface": "virtio",
            "macaddress": "aa:bb:cc:dd:ee:ff",
            "ipaddress": "192.168.1.10",
            "vnet_name": "Internal",
            "vnet_key": 5,
            "enabled": True,
            "speed": 10000,  # 10 Gbps
            "rx_bytes": 1073741824,  # 1 GB
            "tx_bytes": 536870912,  # 512 MB
        }

    @pytest.fixture
    def mock_nic_manager(self, mock_client: VergeClient) -> NICManager:
        """Create a mock NIC manager."""
        vm = VM({"$key": 100, "name": "test-vm", "machine": 200}, mock_client.vms)
        return NICManager(mock_client, vm)

    def test_interface_display(
        self, nic_data: dict[str, Any], mock_nic_manager: NICManager
    ) -> None:
        """Test interface_display property."""
        nic = NIC(nic_data, mock_nic_manager)
        assert nic.interface_display == "Virtio"

    def test_interface_display_e1000e(
        self, nic_data: dict[str, Any], mock_nic_manager: NICManager
    ) -> None:
        """Test interface_display for e1000e."""
        nic_data["interface"] = "e1000e"
        nic = NIC(nic_data, mock_nic_manager)
        assert nic.interface_display == "Intel e1000e"

    def test_is_enabled(self, nic_data: dict[str, Any], mock_nic_manager: NICManager) -> None:
        """Test is_enabled property."""
        nic = NIC(nic_data, mock_nic_manager)
        assert nic.is_enabled is True

    def test_mac_address(self, nic_data: dict[str, Any], mock_nic_manager: NICManager) -> None:
        """Test mac_address property."""
        nic = NIC(nic_data, mock_nic_manager)
        assert nic.mac_address == "aa:bb:cc:dd:ee:ff"

    def test_ip_address(self, nic_data: dict[str, Any], mock_nic_manager: NICManager) -> None:
        """Test ip_address property."""
        nic = NIC(nic_data, mock_nic_manager)
        assert nic.ip_address == "192.168.1.10"

    def test_network_name(self, nic_data: dict[str, Any], mock_nic_manager: NICManager) -> None:
        """Test network_name property."""
        nic = NIC(nic_data, mock_nic_manager)
        assert nic.network_name == "Internal"

    def test_network_key(self, nic_data: dict[str, Any], mock_nic_manager: NICManager) -> None:
        """Test network_key property."""
        nic = NIC(nic_data, mock_nic_manager)
        assert nic.network_key == 5

    def test_speed_display_gbps(
        self, nic_data: dict[str, Any], mock_nic_manager: NICManager
    ) -> None:
        """Test speed_display property for Gbps."""
        nic = NIC(nic_data, mock_nic_manager)
        assert nic.speed_display == "10.0 Gbps"

    def test_speed_display_mbps(
        self, nic_data: dict[str, Any], mock_nic_manager: NICManager
    ) -> None:
        """Test speed_display property for Mbps."""
        nic_data["speed"] = 100
        nic = NIC(nic_data, mock_nic_manager)
        assert nic.speed_display == "100 Mbps"

    def test_speed_display_none(
        self, nic_data: dict[str, Any], mock_nic_manager: NICManager
    ) -> None:
        """Test speed_display property when no speed."""
        nic_data["speed"] = None
        nic = NIC(nic_data, mock_nic_manager)
        assert nic.speed_display is None

    def test_rx_bytes(self, nic_data: dict[str, Any], mock_nic_manager: NICManager) -> None:
        """Test rx_bytes property."""
        nic = NIC(nic_data, mock_nic_manager)
        assert nic.rx_bytes == 1073741824

    def test_tx_bytes(self, nic_data: dict[str, Any], mock_nic_manager: NICManager) -> None:
        """Test tx_bytes property."""
        nic = NIC(nic_data, mock_nic_manager)
        assert nic.tx_bytes == 536870912


class TestMachineNICManager:
    """Unit tests for MachineNICManager (standalone, not VM-scoped)."""

    def test_list_all_nics(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test listing all NICs without machine scope."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "name": "enp3s0", "macaddress": "aa:bb:cc:dd:ee:01", "machine": 2},
            {"$key": 2, "name": "enp4s0", "macaddress": "aa:bb:cc:dd:ee:02", "machine": 2},
            {"$key": 3, "name": "eth0", "macaddress": "aa:bb:cc:dd:ee:03", "machine": 100},
        ]

        manager = MachineNICManager(mock_client)
        nics = manager.list()

        assert len(nics) == 3
        # Should NOT have a machine filter in params
        call_args = mock_session.request.call_args
        params = call_args.kwargs.get("params", {})
        assert "machine eq" not in params.get("filter", "")

    def test_list_scoped_to_machine(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test listing NICs scoped to a specific machine key."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "name": "enp3s0", "macaddress": "aa:bb:cc:dd:ee:01"},
            {"$key": 2, "name": "enp4s0", "macaddress": "aa:bb:cc:dd:ee:02"},
        ]

        manager = MachineNICManager(mock_client, machine_key=42)
        nics = manager.list()

        assert len(nics) == 2
        call_args = mock_session.request.call_args
        params = call_args.kwargs.get("params", {})
        assert "machine eq 42" in params.get("filter", "")

    def test_list_scoped_with_additional_filter(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test machine-scoped list with additional OData filter."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "name": "enp3s0"},
        ]

        manager = MachineNICManager(mock_client, machine_key=42)
        manager.list(filter="name eq 'enp3s0'")

        call_args = mock_session.request.call_args
        params = call_args.kwargs.get("params", {})
        assert "machine eq 42" in params["filter"]
        assert "name eq 'enp3s0'" in params["filter"]

    def test_list_empty_result(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test listing with no results."""
        mock_session.request.return_value.json.return_value = None
        mock_session.request.return_value.status_code = 204
        mock_session.request.return_value.text = ""

        manager = MachineNICManager(mock_client, machine_key=42)
        nics = manager.list()

        assert nics == []

    def test_get_by_key(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test getting a NIC by key."""
        mock_session.request.return_value.json.return_value = {
            "$key": 7,
            "name": "enp3s0",
            "macaddress": "58:47:ca:7f:d8:10",
        }

        manager = MachineNICManager(mock_client)
        nic = manager.get(7)

        assert nic.key == 7
        assert nic.name == "enp3s0"
        assert nic.mac_address == "58:47:ca:7f:d8:10"

    def test_get_by_name(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test getting a NIC by name."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 7, "name": "enp3s0", "macaddress": "58:47:ca:7f:d8:10"},
        ]

        manager = MachineNICManager(mock_client)
        nic = manager.get(name="enp3s0")

        assert nic.name == "enp3s0"

    def test_get_not_found(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test NotFoundError when NIC not found by name."""
        mock_session.request.return_value.json.return_value = []

        manager = MachineNICManager(mock_client)
        with pytest.raises(NotFoundError):
            manager.get(name="nonexistent")

    def test_get_requires_key_or_name(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test ValueError when neither key nor name provided."""
        manager = MachineNICManager(mock_client)
        with pytest.raises(ValueError, match="Either key or name"):
            manager.get()

    def test_client_machine_nics_property(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test client.machine_nics returns a MachineNICManager."""
        manager = mock_client.machine_nics
        assert isinstance(manager, MachineNICManager)

    def test_client_machine_nics_cached(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test client.machine_nics returns the same instance."""
        manager1 = mock_client.machine_nics
        manager2 = mock_client.machine_nics
        assert manager1 is manager2


class TestNodeNics:
    """Unit tests for Node.nics property."""

    @pytest.fixture
    def node(self, mock_client: VergeClient) -> Node:
        """Create a mock Node with a machine key."""
        return Node(
            {"$key": 1, "name": "node1", "machine": 42},
            mock_client.nodes,
        )

    @pytest.fixture
    def node_no_machine(self, mock_client: VergeClient) -> Node:
        """Create a mock Node without a machine key."""
        return Node(
            {"$key": 2, "name": "node2"},
            mock_client.nodes,
        )

    def test_node_nics_returns_manager(self, node: Node) -> None:
        """Test that node.nics returns a MachineNICManager."""
        manager = node.nics
        assert isinstance(manager, MachineNICManager)

    def test_node_nics_scoped_to_machine(self, node: Node, mock_session: MagicMock) -> None:
        """Test that node.nics filters by the node's machine key."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 7, "name": "enp3s0"},
        ]

        node.nics.list()

        call_args = mock_session.request.call_args
        params = call_args.kwargs.get("params", {})
        assert "machine eq 42" in params.get("filter", "")

    def test_node_nics_no_machine_raises(self, node_no_machine: Node) -> None:
        """Test that node.nics raises ValueError when no machine key."""
        with pytest.raises(ValueError, match="no associated machine"):
            _ = node_no_machine.nics

    def test_node_nics_list_with_stats(self, node: Node, mock_session: MagicMock) -> None:
        """Test listing node NICs and accessing stats via NIC objects."""
        mock_session.request.return_value.json.return_value = [
            {
                "$key": 7,
                "name": "enp3s0",
                "macaddress": "58:47:ca:7f:d8:10",
                "machine": 42,
            },
        ]

        nics = node.nics.list()
        assert len(nics) == 1
        nic = nics[0]
        assert nic.key == 7
        assert nic.mac_address == "58:47:ca:7f:d8:10"

        # Verify the NIC can produce stats/status/fabric managers
        from pyvergeos.resources.nic_stats import (
            MachineNicFabricStatusManager,
            MachineNicStatsManager,
            MachineNicStatusManager,
        )

        assert isinstance(nic.nic_stats, MachineNicStatsManager)
        assert isinstance(nic.link_status, MachineNicStatusManager)
        assert isinstance(nic.fabric_status, MachineNicFabricStatusManager)


class TestNICInterfaceMaps:
    """Test NIC interface display maps."""

    def test_interface_display_map(self) -> None:
        """Test all interface display mappings."""
        expected = {
            "virtio": "Virtio",
            "e1000": "Intel e1000",
            "e1000e": "Intel e1000e",
            "rtl8139": "Realtek 8139",
            "pcnet": "AMD PCnet",
            "igb": "Intel 82576",
            "vmxnet3": "VMware Paravirt v3",
            "direct": "Direct",
        }
        assert expected == INTERFACE_DISPLAY_MAP
