"""Unit tests for VM operations."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from pyvergeos import VergeClient
from pyvergeos.exceptions import NotFoundError
from pyvergeos.resources.vms import VM, VMManager


class TestVMManager:
    """Unit tests for VMManager."""

    def test_list_vms(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test listing VMs."""
        mock_session.request.return_value.json.return_value = [
            {
                "$key": 1,
                "name": "test-vm-1",
                "status": "running",
                "running": True,
                "is_snapshot": False,
            },
            {
                "$key": 2,
                "name": "test-vm-2",
                "status": "stopped",
                "running": False,
                "is_snapshot": False,
            },
        ]

        vms = mock_client.vms.list()

        assert len(vms) == 2
        assert vms[0].name == "test-vm-1"
        assert vms[1].name == "test-vm-2"

    def test_list_vms_excludes_snapshots_by_default(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test that list() adds filter to exclude snapshots."""
        mock_session.request.return_value.json.return_value = []

        mock_client.vms.list()

        # Check that the filter includes is_snapshot eq false
        call_args = mock_session.request.call_args
        params = call_args.kwargs.get("params", {})
        assert "is_snapshot eq false" in params.get("filter", "")

    def test_list_vms_include_snapshots(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test that include_snapshots=True doesn't add the filter."""
        mock_session.request.return_value.json.return_value = []

        mock_client.vms.list(include_snapshots=True)

        call_args = mock_session.request.call_args
        params = call_args.kwargs.get("params", {})
        # Should not have is_snapshot filter when include_snapshots=True
        filter_value = params.get("filter", "")
        assert "is_snapshot" not in filter_value or filter_value is None

    def test_get_vm_by_key(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test getting a VM by key."""
        mock_session.request.return_value.json.return_value = {
            "$key": 123,
            "name": "test-vm",
            "status": "running",
        }

        vm = mock_client.vms.get(123)

        assert vm.key == 123
        assert vm.name == "test-vm"

    def test_get_vm_by_name(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test getting a VM by name."""
        mock_session.request.return_value.json.return_value = [
            {
                "$key": 456,
                "name": "my-vm",
                "status": "stopped",
            }
        ]

        vm = mock_client.vms.get(name="my-vm")

        assert vm.name == "my-vm"
        assert vm.key == 456

    def test_get_vm_not_found(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test that NotFoundError is raised when VM not found."""
        mock_session.request.return_value.json.return_value = []

        with pytest.raises(NotFoundError):
            mock_client.vms.get(name="nonexistent")

    def test_get_vm_requires_key_or_name(self, mock_client: VergeClient) -> None:
        """Test that ValueError is raised when neither key nor name provided."""
        with pytest.raises(ValueError, match="Either key or name must be provided"):
            mock_client.vms.get()

    def test_create_vm(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test creating a VM."""
        mock_session.request.return_value.json.return_value = {
            "$key": 789,
            "name": "new-vm",
            "ram": 2048,
            "cpu_cores": 2,
        }

        vm = mock_client.vms.create(
            name="new-vm",
            ram=2048,
            cpu_cores=2,
            os_family="linux",
        )

        assert vm.name == "new-vm"
        assert vm.key == 789

    def test_create_vm_normalizes_ram(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test that RAM is normalized to 256MB increments."""
        mock_session.request.return_value.json.return_value = {
            "$key": 1,
            "name": "test",
            "ram": 2304,  # 2048 + 256
        }

        mock_client.vms.create(name="test", ram=2100)

        # Check the request body
        call_args = mock_session.request.call_args
        body = call_args.kwargs.get("json", {})
        assert body["ram"] == 2304  # Rounded up to nearest 256

    def test_update_vm(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test updating a VM."""
        mock_session.request.return_value.json.return_value = {
            "$key": 123,
            "name": "updated-vm",
            "description": "New description",
        }

        vm = mock_client.vms.update(123, description="New description")

        assert vm.get("description") == "New description"

    def test_delete_vm(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test deleting a VM."""
        mock_session.request.return_value.status_code = 204
        mock_session.request.return_value.text = ""

        mock_client.vms.delete(123)

        call_args = mock_session.request.call_args
        assert call_args.kwargs["method"] == "DELETE"
        assert "vms/123" in call_args.kwargs["url"]


class TestVM:
    """Unit tests for VM object."""

    @pytest.fixture
    def vm_data(self) -> dict[str, Any]:
        """Sample VM data."""
        return {
            "$key": 100,
            "name": "test-vm",
            "status": "running",
            "running": True,
            "is_snapshot": False,
            "node_name": "node1",
            "cluster_name": "cluster1",
            "machine": 200,
            "ram": 4096,
            "cpu_cores": 4,
        }

    @pytest.fixture
    def mock_manager(self, mock_client: VergeClient) -> VMManager:
        """Create a mock VM manager."""
        return mock_client.vms

    def test_vm_properties(self, vm_data: dict[str, Any], mock_manager: VMManager) -> None:
        """Test VM property accessors."""
        vm = VM(vm_data, mock_manager)

        assert vm.key == 100
        assert vm.name == "test-vm"
        assert vm.status == "running"
        assert vm.is_running is True
        assert vm.is_snapshot is False
        assert vm.node_name == "node1"
        assert vm.cluster_name == "cluster1"

    def test_vm_is_running_false(self, vm_data: dict[str, Any], mock_manager: VMManager) -> None:
        """Test is_running when VM is stopped."""
        vm_data["running"] = False
        vm = VM(vm_data, mock_manager)

        assert vm.is_running is False

    def test_vm_is_snapshot_true(self, vm_data: dict[str, Any], mock_manager: VMManager) -> None:
        """Test is_snapshot property."""
        vm_data["is_snapshot"] = True
        vm = VM(vm_data, mock_manager)

        assert vm.is_snapshot is True

    def test_power_on(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        vm_data: dict[str, Any],
    ) -> None:
        """Test powering on a VM."""
        vm = VM(vm_data, mock_client.vms)

        vm.power_on()

        call_args = mock_session.request.call_args
        body = call_args.kwargs.get("json", {})
        assert body["action"] == "poweron"
        assert body["vm"] == 100

    def test_power_on_with_preferred_node(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        vm_data: dict[str, Any],
    ) -> None:
        """Test powering on a VM with preferred node."""
        vm = VM(vm_data, mock_client.vms)

        vm.power_on(preferred_node=5)

        call_args = mock_session.request.call_args
        body = call_args.kwargs.get("json", {})
        assert body["params"]["preferred_node"] == 5

    def test_power_on_snapshot_raises(
        self,
        mock_client: VergeClient,
        vm_data: dict[str, Any],
    ) -> None:
        """Test that powering on a snapshot raises ValueError."""
        vm_data["is_snapshot"] = True
        vm = VM(vm_data, mock_client.vms)

        with pytest.raises(ValueError, match="Cannot power on a snapshot"):
            vm.power_on()

    def test_power_off_graceful(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        vm_data: dict[str, Any],
    ) -> None:
        """Test graceful power off."""
        vm = VM(vm_data, mock_client.vms)

        vm.power_off()

        call_args = mock_session.request.call_args
        body = call_args.kwargs.get("json", {})
        assert body["action"] == "poweroff"

    def test_power_off_force(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        vm_data: dict[str, Any],
    ) -> None:
        """Test forced power off."""
        vm = VM(vm_data, mock_client.vms)

        vm.power_off(force=True)

        call_args = mock_session.request.call_args
        body = call_args.kwargs.get("json", {})
        assert body["action"] == "kill"

    def test_reset(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        vm_data: dict[str, Any],
    ) -> None:
        """Test VM reset."""
        vm = VM(vm_data, mock_client.vms)

        vm.reset()

        call_args = mock_session.request.call_args
        body = call_args.kwargs.get("json", {})
        assert body["action"] == "reset"

    def test_guest_reboot(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        vm_data: dict[str, Any],
    ) -> None:
        """Test guest reboot."""
        vm = VM(vm_data, mock_client.vms)

        vm.guest_reboot()

        call_args = mock_session.request.call_args
        body = call_args.kwargs.get("json", {})
        assert body["action"] == "guestreset"

    def test_guest_shutdown(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        vm_data: dict[str, Any],
    ) -> None:
        """Test guest shutdown."""
        vm = VM(vm_data, mock_client.vms)

        vm.guest_shutdown()

        call_args = mock_session.request.call_args
        body = call_args.kwargs.get("json", {})
        assert body["action"] == "guestshutdown"

    def test_snapshot(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        vm_data: dict[str, Any],
    ) -> None:
        """Test taking a snapshot."""
        mock_session.request.return_value.json.return_value = {
            "$key": 999,
            "name": "my-snapshot",
        }

        vm = VM(vm_data, mock_client.vms)
        result = vm.snapshot(name="my-snapshot", retention=172800, quiesce=True)

        call_args = mock_session.request.call_args
        body = call_args.kwargs.get("json", {})
        assert body["action"] == "snapshot"
        assert body["params"]["name"] == "my-snapshot"
        assert body["params"]["retention"] == 172800
        assert body["params"]["quiesce"] is True

    def test_clone(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        vm_data: dict[str, Any],
    ) -> None:
        """Test cloning a VM."""
        mock_session.request.return_value.json.return_value = {
            "$key": 101,
            "name": "test-vm-clone",
        }

        vm = VM(vm_data, mock_client.vms)
        result = vm.clone(name="test-vm-clone", preserve_macs=True)

        call_args = mock_session.request.call_args
        body = call_args.kwargs.get("json", {})
        assert body["action"] == "clone"
        assert body["params"]["name"] == "test-vm-clone"
        assert body["params"]["preserve_macs"] is True

    def test_move(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        vm_data: dict[str, Any],
    ) -> None:
        """Test moving a VM."""
        mock_session.request.return_value.json.return_value = {"task": 123}

        vm = VM(vm_data, mock_client.vms)
        result = vm.move(node=5, cluster=2)

        call_args = mock_session.request.call_args
        body = call_args.kwargs.get("json", {})
        assert body["action"] == "move"
        assert body["params"]["node"] == 5
        assert body["params"]["cluster"] == 2

    def test_get_console_info(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        vm_data: dict[str, Any],
    ) -> None:
        """Test getting console info."""
        mock_session.request.return_value.json.return_value = {
            "name": "test-vm",
            "console": "vnc",
            "host": "192.168.1.100",
            "port": 5900,
        }

        vm = VM(vm_data, mock_client.vms)
        console = vm.get_console_info()

        assert console["console_type"] == "vnc"
        assert console["host"] == "192.168.1.100"
        assert console["port"] == 5900
        assert console["url"] == "vnc://192.168.1.100:5900"
        assert console["is_available"] is True

    def test_get_console_info_not_available(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        vm_data: dict[str, Any],
    ) -> None:
        """Test console info when not available."""
        mock_session.request.return_value.json.return_value = {
            "name": "test-vm",
            "console": "vnc",
            "host": None,
            "port": None,
        }

        vm = VM(vm_data, mock_client.vms)
        console = vm.get_console_info()

        assert console["is_available"] is False
        assert console["url"] is None

    def test_drives_property(
        self,
        mock_client: VergeClient,
        vm_data: dict[str, Any],
    ) -> None:
        """Test that drives property returns DriveManager."""
        vm = VM(vm_data, mock_client.vms)

        from pyvergeos.resources.drives import DriveManager

        assert isinstance(vm.drives, DriveManager)
        # Should be same instance on subsequent access
        assert vm.drives is vm.drives

    def test_nics_property(
        self,
        mock_client: VergeClient,
        vm_data: dict[str, Any],
    ) -> None:
        """Test that nics property returns NICManager."""
        vm = VM(vm_data, mock_client.vms)

        from pyvergeos.resources.nics import NICManager

        assert isinstance(vm.nics, NICManager)
        assert vm.nics is vm.nics

    def test_snapshots_property(
        self,
        mock_client: VergeClient,
        vm_data: dict[str, Any],
    ) -> None:
        """Test that snapshots property returns VMSnapshotManager."""
        vm = VM(vm_data, mock_client.vms)

        from pyvergeos.resources.snapshots import VMSnapshotManager

        assert isinstance(vm.snapshots, VMSnapshotManager)
        assert vm.snapshots is vm.snapshots


class TestVMListHelpers:
    """Test VM list helper methods."""

    def test_list_running(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test list_running method."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "name": "vm1", "running": True, "is_snapshot": False},
            {"$key": 2, "name": "vm2", "running": False, "is_snapshot": False},
            {"$key": 3, "name": "vm3", "running": True, "is_snapshot": False},
        ]

        running = mock_client.vms.list_running()

        assert len(running) == 2
        assert all(vm.is_running for vm in running)

    def test_list_stopped(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test list_stopped method."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "name": "vm1", "running": True, "is_snapshot": False},
            {"$key": 2, "name": "vm2", "running": False, "is_snapshot": False},
            {"$key": 3, "name": "vm3", "running": False, "is_snapshot": False},
        ]

        stopped = mock_client.vms.list_stopped()

        assert len(stopped) == 2
        assert all(not vm.is_running for vm in stopped)
