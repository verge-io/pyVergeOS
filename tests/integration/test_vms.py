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


@pytest.mark.integration
class TestVMDrives:
    """Integration tests for VM drive operations."""

    @pytest.fixture
    def test_vm(self, live_client: VergeClient):
        """Get the test VM, or skip if not available."""
        try:
            return live_client.vms.get(name="test")
        except NotFoundError:
            pytest.skip("Test VM 'test' not available")

    def test_list_drives(self, live_client: VergeClient, test_vm) -> None:
        """Test listing drives for a VM."""
        drives = test_vm.drives.list()

        assert isinstance(drives, list)
        if drives:
            drive = drives[0]
            assert "$key" in drive
            assert "name" in drive
            assert "interface" in drive
            assert "media" in drive

    def test_drive_properties(self, live_client: VergeClient, test_vm) -> None:
        """Test drive property accessors."""
        drives = test_vm.drives.list()
        if not drives:
            pytest.skip("No drives available on test VM")

        drive = drives[0]

        # Test size properties
        assert isinstance(drive.size_gb, float)
        assert drive.size_gb >= 0

        # Test display properties
        assert isinstance(drive.interface_display, str)
        assert isinstance(drive.media_display, str)

        # Test boolean properties
        assert isinstance(drive.is_enabled, bool)
        assert isinstance(drive.is_readonly, bool)

    def test_import_drive(self, live_client: VergeClient) -> None:
        """Test importing a drive from a disk image file."""
        # Create a test VM for import
        vm = live_client.vms.create(
            name="pstest-import-drive",
            cpu_cores=1,
            ram=1024,
            os_family="linux",
        )

        try:
            # Import the QCOW2 disk image
            drive = vm.drives.import_drive(
                file_name="debian-12-generic-amd64-fa03cff7.qcow2",
                name="ImportedDisk",
                interface="virtio-scsi",
                tier=1,
            )

            assert drive is not None
            assert drive.name == "ImportedDisk"
            # After import, media becomes "disk" (converted from import format)
            assert drive.get("media") in ("import", "disk")
            assert drive.get("interface") == "virtio-scsi"

            # Verify drive is in the VM's drive list
            drives = vm.drives.list()
            imported_drives = [d for d in drives if d.name == "ImportedDisk"]
            assert len(imported_drives) == 1

        finally:
            # Cleanup: delete the test VM
            live_client.vms.delete(vm.key)


@pytest.mark.integration
class TestVMNICs:
    """Integration tests for VM NIC operations."""

    @pytest.fixture
    def test_vm(self, live_client: VergeClient):
        """Get the test VM, or skip if not available."""
        try:
            return live_client.vms.get(name="test")
        except NotFoundError:
            pytest.skip("Test VM 'test' not available")

    def test_list_nics(self, live_client: VergeClient, test_vm) -> None:
        """Test listing NICs for a VM."""
        nics = test_vm.nics.list()

        assert isinstance(nics, list)
        if nics:
            nic = nics[0]
            assert "$key" in nic
            assert "name" in nic
            assert "interface" in nic

    def test_nic_properties(self, live_client: VergeClient, test_vm) -> None:
        """Test NIC property accessors."""
        nics = test_vm.nics.list()
        if not nics:
            pytest.skip("No NICs available on test VM")

        nic = nics[0]

        # Test display properties
        assert isinstance(nic.interface_display, str)

        # Test boolean properties
        assert isinstance(nic.is_enabled, bool)

        # Test MAC address
        mac = nic.mac_address
        assert mac is None or isinstance(mac, str)

        # Test network properties
        network = nic.network_name
        assert network is None or isinstance(network, str)


@pytest.mark.integration
class TestVMSnapshots:
    """Integration tests for VM snapshot operations."""

    @pytest.fixture
    def test_vm(self, live_client: VergeClient):
        """Get the test VM, or skip if not available."""
        try:
            return live_client.vms.get(name="test")
        except NotFoundError:
            pytest.skip("Test VM 'test' not available")

    def test_list_snapshots(self, live_client: VergeClient, test_vm) -> None:
        """Test listing snapshots for a VM."""
        snapshots = test_vm.snapshots.list()

        assert isinstance(snapshots, list)
        if snapshots:
            snapshot = snapshots[0]
            assert "$key" in snapshot
            assert "name" in snapshot
            assert "created" in snapshot

    def test_snapshot_properties(self, live_client: VergeClient, test_vm) -> None:
        """Test snapshot property accessors."""
        snapshots = test_vm.snapshots.list()
        if not snapshots:
            pytest.skip("No snapshots available on test VM")

        snapshot = snapshots[0]

        # Test datetime properties
        created = snapshot.created_at
        assert created is not None

        # Test boolean properties
        assert isinstance(snapshot.is_quiesced, bool)
        assert isinstance(snapshot.is_manual, bool)
        assert isinstance(snapshot.never_expires, bool)
        assert isinstance(snapshot.is_cloud_snapshot, bool)

        # Test snap_machine_key
        snap_key = snapshot.snap_machine_key
        assert snap_key is None or isinstance(snap_key, int)

    def test_create_and_delete_snapshot(self, live_client: VergeClient, test_vm) -> None:
        """Test creating and deleting a snapshot."""
        # Create snapshot
        result = test_vm.snapshots.create(
            name="pyvergeos-test-snapshot",
            retention=3600,  # 1 hour
            quiesce=False,
        )

        assert result is not None

        # Wait for snapshot to be created
        time.sleep(2)

        # Find the snapshot
        snapshots = test_vm.snapshots.list()
        test_snapshot = None
        for s in snapshots:
            if s.name == "pyvergeos-test-snapshot":
                test_snapshot = s
                break

        assert test_snapshot is not None

        # Delete the snapshot
        test_vm.snapshots.delete(test_snapshot.key)

        # Verify deletion
        time.sleep(1)
        snapshots = test_vm.snapshots.list()
        for s in snapshots:
            assert s.name != "pyvergeos-test-snapshot"
