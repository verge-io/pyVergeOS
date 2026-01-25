"""Integration tests for VM operations."""

import time

import pytest

from pyvergeos import VergeClient
from pyvergeos.exceptions import NotFoundError


@pytest.mark.integration
class TestVMOperations:
    """Integration tests for VM operations against live VergeOS."""

    def test_list_vms(self, live_client: VergeClient) -> None:
        """Test listing VMs."""
        vms = live_client.vms.list(limit=10)
        assert isinstance(vms, list)

        # Each VM should have rich fields
        if vms:
            vm = vms[0]
            assert "$key" in vm
            assert "name" in vm
            assert "status" in vm
            assert "running" in vm
            # Check joined fields
            assert "cluster_name" in vm

    def test_list_vms_excludes_snapshots(self, live_client: VergeClient) -> None:
        """Test that list() excludes snapshots by default."""
        vms = live_client.vms.list()
        for vm in vms:
            assert not vm.is_snapshot

    def test_list_vms_include_snapshots(self, live_client: VergeClient) -> None:
        """Test that include_snapshots=True includes snapshots."""
        all_items = live_client.vms.list(include_snapshots=True, limit=50)
        # Just verify it returns without error
        assert isinstance(all_items, list)

    def test_list_running_vms(self, live_client: VergeClient) -> None:
        """Test listing running VMs."""
        running = live_client.vms.list_running()
        assert isinstance(running, list)
        for vm in running:
            assert vm.is_running is True

    def test_list_stopped_vms(self, live_client: VergeClient) -> None:
        """Test listing stopped VMs."""
        stopped = live_client.vms.list_stopped()
        assert isinstance(stopped, list)
        for vm in stopped:
            assert vm.is_running is False

    def test_get_vm_by_key(self, live_client: VergeClient) -> None:
        """Test getting a VM by key."""
        # First list to get a valid key
        vms = live_client.vms.list(limit=1)
        if not vms:
            pytest.skip("No VMs available")

        vm = live_client.vms.get(vms[0].key)
        assert vm.key == vms[0].key
        assert vm.name == vms[0].name

    def test_get_vm_by_name(self, live_client: VergeClient) -> None:
        """Test getting a VM by name."""
        vms = live_client.vms.list(limit=1)
        if not vms:
            pytest.skip("No VMs available")

        vm = live_client.vms.get(name=vms[0].name)
        assert vm.name == vms[0].name
        assert vm.key == vms[0].key

    def test_get_vm_not_found(self, live_client: VergeClient) -> None:
        """Test getting a non-existent VM."""
        with pytest.raises(NotFoundError):
            live_client.vms.get(name="nonexistent-vm-12345")

    def test_vm_properties(self, live_client: VergeClient) -> None:
        """Test VM property access."""
        vms = live_client.vms.list(limit=1)
        if not vms:
            pytest.skip("No VMs available")

        vm = vms[0]

        # Test is_running property
        assert isinstance(vm.is_running, bool)

        # Test is_snapshot property
        assert isinstance(vm.is_snapshot, bool)

        # Test status property
        assert isinstance(vm.status, str)

        # Test node_name property (may be None if not running)
        node = vm.node_name
        assert node is None or isinstance(node, str)

        # Test cluster_name property
        cluster = vm.cluster_name
        assert cluster is None or isinstance(cluster, str)


@pytest.mark.integration
class TestVMConsole:
    """Integration tests for VM console access."""

    def test_get_console_info_running_vm(self, live_client: VergeClient) -> None:
        """Test getting console info for a running VM."""
        running = live_client.vms.list_running()
        if not running:
            pytest.skip("No running VMs available")

        vm = running[0]
        console = vm.get_console_info()

        assert isinstance(console, dict)
        assert "console_type" in console
        assert "host" in console
        assert "port" in console
        assert "url" in console
        assert "web_url" in console
        assert "is_available" in console

        # Running VM should have console available
        if console["is_available"]:
            assert console["host"] is not None
            assert console["port"] is not None
            assert console["url"] is not None

    def test_get_console_info_stopped_vm(self, live_client: VergeClient) -> None:
        """Test getting console info for a stopped VM."""
        stopped = live_client.vms.list_stopped()
        if not stopped:
            pytest.skip("No stopped VMs available")

        vm = stopped[0]
        console = vm.get_console_info()

        assert isinstance(console, dict)
        # Stopped VM typically has no console available
        # (but we just verify it doesn't raise an error)


@pytest.mark.integration
class TestVMPowerOperations:
    """Integration tests for VM power operations.

    These tests require a specific test VM named 'test'.
    """

    @pytest.fixture
    def test_vm(self, live_client: VergeClient) -> None:
        """Get the test VM, or skip if not available."""
        try:
            vm = live_client.vms.get(name="test")
            return vm
        except NotFoundError:
            pytest.skip("Test VM 'test' not available")

    def test_power_cycle(self, live_client: VergeClient, test_vm) -> None:
        """Test power on/off cycle."""
        if test_vm.is_running:
            # Power off
            test_vm.power_off(force=True)
            time.sleep(2)

            vm = live_client.vms.get(test_vm.key)
            assert not vm.is_running

        # Power on
        test_vm = live_client.vms.get(test_vm.key)
        test_vm.power_on()
        time.sleep(3)

        vm = live_client.vms.get(test_vm.key)
        assert vm.is_running

        # Leave it running for other tests
