"""Integration tests for machine stats and monitoring."""

from datetime import datetime, timedelta, timezone

import pytest

from pyvergeos import VergeClient
from pyvergeos.exceptions import NotFoundError
from pyvergeos.resources.devices import Device
from pyvergeos.resources.machine_stats import (
    MachineLog,
    MachineStats,
    MachineStatsHistory,
    MachineStatus,
)


@pytest.mark.integration
class TestVMMachineStats:
    """Integration tests for VM machine stats."""

    @pytest.fixture
    def test_vm(self, live_client: VergeClient):
        """Get the test VM, or skip if not available."""
        try:
            return live_client.vms.get(name="test")
        except NotFoundError:
            pytest.skip("Test VM 'test' not available")

    def test_vm_has_machine_key(self, live_client: VergeClient, test_vm) -> None:
        """Test that VM has a machine_key property."""
        assert test_vm.machine_key is not None
        assert isinstance(test_vm.machine_key, int)
        assert test_vm.machine_key > 0

    def test_get_vm_stats(self, live_client: VergeClient, test_vm) -> None:
        """Test getting current VM stats."""
        stats = test_vm.stats.get()

        assert isinstance(stats, MachineStats)
        assert stats.machine_key == test_vm.machine_key

        # Check CPU metrics
        assert isinstance(stats.total_cpu, int)
        assert stats.total_cpu >= 0
        assert stats.total_cpu <= 100

        # Check RAM metrics
        assert isinstance(stats.ram_used_mb, int)
        assert stats.ram_used_mb >= 0

        assert isinstance(stats.ram_pct, int)
        assert stats.ram_pct >= 0
        assert stats.ram_pct <= 100

    def test_get_vm_stats_fields(self, live_client: VergeClient, test_vm) -> None:
        """Test getting VM stats with specific fields."""
        stats = test_vm.stats.get(fields=["$key", "machine", "total_cpu", "ram_used"])

        assert stats.machine_key == test_vm.machine_key
        assert isinstance(stats.total_cpu, int)
        assert isinstance(stats.ram_used_mb, int)

    def test_vm_stats_history_short(self, live_client: VergeClient, test_vm) -> None:
        """Test getting short-term stats history."""
        history = test_vm.stats.history_short(limit=10)

        assert isinstance(history, list)
        # History might be empty for stopped VMs, but should work
        if history:
            assert all(isinstance(h, MachineStatsHistory) for h in history)

            # Check first record
            record = history[0]
            assert record.machine_key == test_vm.machine_key
            assert record.timestamp is not None
            assert isinstance(record.timestamp, datetime)
            assert isinstance(record.total_cpu, int)

    def test_vm_stats_history_long(self, live_client: VergeClient, test_vm) -> None:
        """Test getting long-term stats history."""
        history = test_vm.stats.history_long(limit=10)

        assert isinstance(history, list)
        if history:
            assert all(isinstance(h, MachineStatsHistory) for h in history)

            record = history[0]
            assert record.machine_key == test_vm.machine_key
            assert record.timestamp is not None

    def test_vm_stats_history_since(self, live_client: VergeClient, test_vm) -> None:
        """Test getting stats history since a specific time."""
        since = datetime.now(tz=timezone.utc) - timedelta(hours=1)
        history = test_vm.stats.history_short(limit=10, since=since)

        assert isinstance(history, list)
        # All records should be after 'since'
        for record in history:
            if record.timestamp:
                assert record.timestamp >= since


@pytest.mark.integration
class TestVMMachineStatus:
    """Integration tests for VM machine status."""

    @pytest.fixture
    def test_vm(self, live_client: VergeClient):
        """Get the test VM, or skip if not available."""
        try:
            return live_client.vms.get(name="test")
        except NotFoundError:
            pytest.skip("Test VM 'test' not available")

    def test_get_vm_status(self, live_client: VergeClient, test_vm) -> None:
        """Test getting VM machine status."""
        status = test_vm.machine_status.get()

        assert isinstance(status, MachineStatus)
        assert status.machine_key == test_vm.machine_key

        # Check status fields
        assert isinstance(status.status, str)
        assert isinstance(status.status_raw, str)
        assert isinstance(status.is_running, bool)

    def test_vm_status_display_values(self, live_client: VergeClient, test_vm) -> None:
        """Test that status has human-readable display values."""
        status = test_vm.machine_status.get()

        # status should be human-readable (e.g., "Running" not "running")
        assert status.status[0].isupper() or status.status == status.status_raw

        # state should also be human-readable
        assert isinstance(status.state, str)
        assert isinstance(status.state_raw, str)

    def test_vm_status_running_properties(self, live_client: VergeClient, test_vm) -> None:
        """Test VM status properties when running."""
        status = test_vm.machine_status.get()

        if status.is_running:
            # Running VM should have node info
            assert status.node_name is not None or status.node_key is not None
            assert status.running_cores >= 0
            assert status.running_ram_mb >= 0


@pytest.mark.integration
class TestVMMachineLogs:
    """Integration tests for VM machine logs."""

    @pytest.fixture
    def test_vm(self, live_client: VergeClient):
        """Get the test VM, or skip if not available."""
        try:
            return live_client.vms.get(name="test")
        except NotFoundError:
            pytest.skip("Test VM 'test' not available")

    def test_list_vm_logs(self, live_client: VergeClient, test_vm) -> None:
        """Test listing VM logs."""
        logs = test_vm.machine_logs.list(limit=10)

        assert isinstance(logs, list)
        if logs:
            assert all(isinstance(log, MachineLog) for log in logs)

            # Check first log
            log = logs[0]
            assert log.machine_key == test_vm.machine_key
            assert isinstance(log.level, str)
            assert isinstance(log.text, str)

    def test_list_vm_logs_with_level_filter(self, live_client: VergeClient, test_vm) -> None:
        """Test listing VM logs filtered by level."""
        # Test message level
        logs = test_vm.machine_logs.list(limit=5, level="message")
        assert isinstance(logs, list)
        for log in logs:
            assert log.level_raw == "message"

    def test_list_vm_logs_errors_only(self, live_client: VergeClient, test_vm) -> None:
        """Test listing only error logs."""
        logs = test_vm.machine_logs.list(limit=10, errors_only=True)

        assert isinstance(logs, list)
        for log in logs:
            assert log.level_raw in ("error", "critical")
            assert log.is_error is True

    def test_list_vm_logs_since(self, live_client: VergeClient, test_vm) -> None:
        """Test listing logs since a specific time."""
        since = datetime.now(tz=timezone.utc) - timedelta(days=1)
        logs = test_vm.machine_logs.list(limit=10, since=since)

        assert isinstance(logs, list)
        for log in logs:
            if log.timestamp:
                assert log.timestamp >= since

    def test_vm_log_properties(self, live_client: VergeClient, test_vm) -> None:
        """Test VM log property accessors."""
        logs = test_vm.machine_logs.list(limit=1)
        if not logs:
            pytest.skip("No logs available for test VM")

        log = logs[0]

        # Test timestamp
        assert log.timestamp is not None
        assert isinstance(log.timestamp, datetime)

        # Test level display vs raw
        assert isinstance(log.level, str)
        assert isinstance(log.level_raw, str)

        # Test text
        assert isinstance(log.text, str)

        # Test boolean helpers
        assert isinstance(log.is_error, bool)
        assert isinstance(log.is_warning, bool)
        assert isinstance(log.is_audit, bool)


@pytest.mark.integration
class TestVMMachineDevices:
    """Integration tests for VM machine devices."""

    @pytest.fixture
    def test_vm(self, live_client: VergeClient):
        """Get the test VM, or skip if not available."""
        try:
            return live_client.vms.get(name="test")
        except NotFoundError:
            pytest.skip("Test VM 'test' not available")

    def test_list_vm_devices(self, live_client: VergeClient, test_vm) -> None:
        """Test listing VM devices."""
        devices = test_vm.devices.list()

        assert isinstance(devices, list)
        # Devices may be empty if none attached
        if devices:
            assert all(isinstance(d, Device) for d in devices)

            device = devices[0]
            assert device.machine_key == test_vm.machine_key
            assert isinstance(device.name, str)
            assert isinstance(device.device_type, str)

    def test_list_vm_devices_by_type(self, live_client: VergeClient, test_vm) -> None:
        """Test listing VM devices filtered by type."""
        # Try listing TPM devices (common type)
        devices = test_vm.devices.list(device_type="tpm")

        assert isinstance(devices, list)
        for device in devices:
            assert device.device_type_raw == "tpm"

    def test_create_and_delete_tpm_device(self, live_client: VergeClient, test_vm) -> None:
        """Test creating and deleting a TPM device."""
        # Check if VM already has a TPM
        existing = test_vm.devices.list(device_type="tpm")
        if existing:
            pytest.skip("Test VM already has a TPM device")

        # Check if VM is stopped (required for device changes)
        if test_vm.is_running:
            pytest.skip("Cannot add devices to running VM")

        # Create TPM device
        device = test_vm.devices.create(
            device_type="tpm",
            name="Test-TPM",
            description="Integration test TPM",
            enabled=True,
            optional=True,
        )

        try:
            assert device is not None
            assert device.name == "Test-TPM"
            assert device.device_type_raw == "tpm"
            assert device.is_enabled is True
            assert device.is_optional is True
            assert device.is_tpm is True

            # Verify it's in the list
            devices = test_vm.devices.list()
            tpm_devices = [d for d in devices if d.name == "Test-TPM"]
            assert len(tpm_devices) == 1

        finally:
            # Cleanup: delete the device
            test_vm.devices.delete(device.key)

            # Verify deletion
            devices = test_vm.devices.list()
            for d in devices:
                assert d.name != "Test-TPM"


@pytest.mark.integration
class TestNodeMachineStats:
    """Integration tests for Node machine stats."""

    @pytest.fixture
    def test_node(self, live_client: VergeClient):
        """Get a node for testing."""
        nodes = live_client.nodes.list(limit=1)
        if not nodes:
            pytest.skip("No nodes available")
        return nodes[0]

    def test_node_has_machine_key(self, live_client: VergeClient, test_node) -> None:
        """Test that Node has a machine_key property."""
        assert test_node.machine_key is not None
        assert isinstance(test_node.machine_key, int)
        assert test_node.machine_key > 0

    def test_get_node_stats(self, live_client: VergeClient, test_node) -> None:
        """Test getting current node stats."""
        stats = test_node.stats.get()

        assert isinstance(stats, MachineStats)
        assert stats.machine_key == test_node.machine_key

        # Nodes should have CPU and RAM metrics
        assert isinstance(stats.total_cpu, int)
        assert isinstance(stats.ram_used_mb, int)
        assert isinstance(stats.ram_pct, int)

    def test_node_stats_history_short(self, live_client: VergeClient, test_node) -> None:
        """Test getting short-term node stats history."""
        history = test_node.stats.history_short(limit=5)

        assert isinstance(history, list)
        if history:
            record = history[0]
            assert isinstance(record, MachineStatsHistory)
            assert record.machine_key == test_node.machine_key

    def test_node_stats_history_long(self, live_client: VergeClient, test_node) -> None:
        """Test getting long-term node stats history."""
        history = test_node.stats.history_long(limit=5)

        assert isinstance(history, list)
        if history:
            record = history[0]
            assert isinstance(record, MachineStatsHistory)

    def test_get_node_status(self, live_client: VergeClient, test_node) -> None:
        """Test getting node machine status."""
        status = test_node.machine_status.get()

        assert isinstance(status, MachineStatus)
        assert status.machine_key == test_node.machine_key
        assert isinstance(status.status, str)
        assert isinstance(status.is_running, bool)

    def test_list_node_logs(self, live_client: VergeClient, test_node) -> None:
        """Test listing node logs."""
        logs = test_node.machine_logs.list(limit=5)

        assert isinstance(logs, list)
        if logs:
            log = logs[0]
            assert isinstance(log, MachineLog)
            assert log.machine_key == test_node.machine_key


@pytest.mark.integration
class TestMachineStatsManager:
    """Integration tests for direct MachineStatsManager access."""

    def test_stats_manager_scoping(self, live_client: VergeClient) -> None:
        """Test that stats managers are properly scoped to their machine."""
        vms = live_client.vms.list(limit=2)
        if len(vms) < 2:
            pytest.skip("Need at least 2 VMs for this test")

        vm1, vm2 = vms[0], vms[1]

        # Get stats for each VM
        stats1 = vm1.stats.get()
        stats2 = vm2.stats.get()

        # Verify they are for different machines
        assert stats1.machine_key == vm1.machine_key
        assert stats2.machine_key == vm2.machine_key

        if vm1.machine_key != vm2.machine_key:
            # The stats should be for different machines
            assert stats1.machine_key != stats2.machine_key

    def test_stats_manager_caching(self, live_client: VergeClient) -> None:
        """Test that stats manager is cached on the VM object."""
        try:
            vm = live_client.vms.get(name="test")
        except NotFoundError:
            pytest.skip("Test VM 'test' not available")

        # Access stats property twice
        stats_manager1 = vm.stats
        stats_manager2 = vm.stats

        # Should be the same instance (cached)
        assert stats_manager1 is stats_manager2
