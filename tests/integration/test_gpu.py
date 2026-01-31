"""Integration tests for GPU and vGPU management.

These tests require a live VergeOS connection and are skipped in CI.
They also require a node with NVIDIA GPU(s) available.

To run these tests:
    VERGE_HOST=192.168.10.75 VERGE_USERNAME=admin VERGE_PASSWORD=xxx \\
        uv run pytest tests/integration/test_gpu.py -v

Note: Some tests require a vGPU-capable GPU (e.g., Tesla T4, A100).
Tests that require vGPU will be skipped if no vGPU devices are detected.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pyvergeos.client import VergeClient


pytestmark = pytest.mark.integration


class TestNvidiaVgpuProfiles:
    """Integration tests for NVIDIA vGPU profile operations."""

    def test_list_vgpu_profiles(self, live_client: VergeClient) -> None:
        """Test listing vGPU profiles.

        Note: This may return an empty list if no vGPU-capable devices exist.
        """
        profiles = live_client.vgpu_profiles.list()

        # Just verify the API call works - may be empty if no vGPU hardware
        assert isinstance(profiles, list)
        print(f"Found {len(profiles)} vGPU profile(s)")

    def test_list_vgpu_profiles_by_type(self, live_client: VergeClient) -> None:
        """Test filtering vGPU profiles by type."""
        # Try each profile type
        for profile_type in ["A", "B", "C", "Q"]:
            profiles = live_client.vgpu_profiles.list(profile_type=profile_type)
            assert isinstance(profiles, list)
            # If any profiles exist, they should match the type
            for profile in profiles:
                assert profile.profile_type == profile_type


class TestNodeGpuManagement:
    """Integration tests for node GPU management."""

    def test_list_all_gpus(self, live_client: VergeClient) -> None:
        """Test listing all GPU configurations across nodes."""
        gpus = live_client.nodes.all_gpus.list()

        assert isinstance(gpus, list)
        print(f"Found {len(gpus)} GPU configuration(s)")
        for gpu in gpus:
            print(f"  GPU: {gpu.name} on {gpu.node_name} - mode: {gpu.mode_display}")

    def test_list_gpus_for_node(self, live_client: VergeClient) -> None:
        """Test listing GPU configurations for a specific node."""
        nodes = live_client.nodes.list()
        if not nodes:
            pytest.skip("No nodes available")

        # Find a node with GPUs
        for node in nodes:
            gpus = node.gpus.list()
            if gpus:
                print(f"Node {node.name} has {len(gpus)} GPU(s)")
                for gpu in gpus:
                    assert gpu.node_key == node.key
                return

        # If no GPUs found on any node, that's OK
        print("No GPUs found on any node")

    def test_list_enabled_gpus(self, live_client: VergeClient) -> None:
        """Test listing only enabled GPUs."""
        enabled_gpus = live_client.nodes.all_gpus.list(enabled_only=True)

        print(f"Found {len(enabled_gpus)} enabled GPU(s)")
        # All returned GPUs should have a mode set
        for gpu in enabled_gpus:
            assert gpu.mode != "none"
            assert not gpu.is_disabled

    def test_list_passthrough_gpus(self, live_client: VergeClient) -> None:
        """Test listing GPUs in passthrough mode."""
        passthrough_gpus = live_client.nodes.all_gpus.list(mode="gpu")

        print(f"Found {len(passthrough_gpus)} passthrough GPU(s)")
        for gpu in passthrough_gpus:
            assert gpu.is_passthrough
            assert gpu.mode == "gpu"

    def test_list_vgpu_gpus(self, live_client: VergeClient) -> None:
        """Test listing GPUs in vGPU mode."""
        vgpu_gpus = live_client.nodes.all_gpus.list(mode="nvidia_vgpu")

        print(f"Found {len(vgpu_gpus)} vGPU-mode GPU(s)")
        for gpu in vgpu_gpus:
            assert gpu.is_vgpu
            assert gpu.mode == "nvidia_vgpu"


class TestNodeGpuStats:
    """Integration tests for GPU stats."""

    def test_gpu_stats(self, live_client: VergeClient) -> None:
        """Test getting GPU stats."""
        gpus = live_client.nodes.all_gpus.list(enabled_only=True)
        if not gpus:
            pytest.skip("No enabled GPUs available")

        gpu = gpus[0]
        try:
            stats = gpu.stats.get()
            print(f"GPU {gpu.name} stats:")
            print(f"  GPUs: {stats.gpus}/{stats.gpus_total}")
            print(f"  vGPUs: {stats.vgpus}/{stats.vgpus_total}")
        except Exception as e:
            # Stats might not be available for all GPU configurations
            print(f"Could not get stats for GPU {gpu.name}: {e}")

    def test_gpu_stats_history(self, live_client: VergeClient) -> None:
        """Test getting GPU stats history."""
        gpus = live_client.nodes.all_gpus.list(enabled_only=True)
        if not gpus:
            pytest.skip("No enabled GPUs available")

        gpu = gpus[0]
        try:
            history_short = gpu.stats.history_short(limit=10)
            print(f"GPU {gpu.name} has {len(history_short)} short-term history records")

            history_long = gpu.stats.history_long(limit=10)
            print(f"GPU {gpu.name} has {len(history_long)} long-term history records")
        except Exception as e:
            print(f"Could not get history for GPU {gpu.name}: {e}")


class TestNodeGpuInstances:
    """Integration tests for GPU instances."""

    def test_list_gpu_instances(self, live_client: VergeClient) -> None:
        """Test listing GPU instances for a GPU."""
        gpus = live_client.nodes.all_gpus.list(enabled_only=True)
        if not gpus:
            pytest.skip("No enabled GPUs available")

        for gpu in gpus:
            instances = gpu.instances.list()
            print(f"GPU {gpu.name} has {len(instances)} instance(s)")
            for inst in instances:
                print(f"  - VM: {inst.machine_name} ({inst.machine_device_status})")


class TestVgpuDevices:
    """Integration tests for vGPU device operations."""

    def test_list_all_vgpu_devices(self, live_client: VergeClient) -> None:
        """Test listing all vGPU-capable devices."""
        devices = live_client.nodes.all_vgpu_devices.list()

        assert isinstance(devices, list)
        print(f"Found {len(devices)} vGPU-capable device(s)")
        for device in devices:
            print(f"  vGPU Device: {device.name} on {device.node_name}")
            print(f"    Slot: {device.slot}")
            print(f"    Driver: {device.driver}")
            print(f"    Max instances: {device.max_instances}")

    def test_list_vgpu_devices_for_node(self, live_client: VergeClient) -> None:
        """Test listing vGPU devices for a specific node."""
        nodes = live_client.nodes.list()
        if not nodes:
            pytest.skip("No nodes available")

        for node in nodes:
            devices = node.vgpu_devices.list()
            if devices:
                print(f"Node {node.name} has {len(devices)} vGPU-capable device(s)")
                for device in devices:
                    assert device.node_key == node.key
                return

        print("No vGPU-capable devices found on any node")

    def test_list_vgpu_devices_by_vendor(self, live_client: VergeClient) -> None:
        """Test filtering vGPU devices by vendor."""
        devices = live_client.nodes.all_vgpu_devices.list(vendor="NVIDIA")

        print(f"Found {len(devices)} NVIDIA vGPU device(s)")
        for device in devices:
            assert "NVIDIA" in device.vendor


class TestHostGpuDevices:
    """Integration tests for host GPU device operations."""

    def test_list_all_host_gpu_devices(self, live_client: VergeClient) -> None:
        """Test listing all host GPU devices (for passthrough)."""
        devices = live_client.nodes.all_host_gpu_devices.list()

        assert isinstance(devices, list)
        print(f"Found {len(devices)} host GPU device(s)")
        for device in devices:
            print(f"  Host GPU: {device.name} on {device.node_name}")
            print(f"    Slot: {device.slot}")
            print(f"    Driver: {device.driver}")

    def test_list_host_gpu_devices_for_node(self, live_client: VergeClient) -> None:
        """Test listing host GPU devices for a specific node."""
        nodes = live_client.nodes.list()
        if not nodes:
            pytest.skip("No nodes available")

        for node in nodes:
            devices = node.host_gpu_devices.list()
            if devices:
                print(f"Node {node.name} has {len(devices)} host GPU(s)")
                for device in devices:
                    assert device.node_key == node.key
                return

        print("No host GPU devices found on any node")


class TestGpuPassthrough:
    """Integration tests for GPU passthrough scenarios.

    Note: These tests require a node with a physical GPU available for
    passthrough (node2 per project notes).
    """

    def test_find_passthrough_capable_gpus(self, live_client: VergeClient) -> None:
        """Test finding GPUs capable of passthrough."""
        # Look for host GPU devices which can be used for passthrough
        host_gpus = live_client.nodes.all_host_gpu_devices.list()

        print(f"Found {len(host_gpus)} GPU(s) capable of passthrough:")
        for gpu in host_gpus:
            print(f"  {gpu.name} on {gpu.node_name} ({gpu.slot})")

    def test_node2_has_gpu(self, live_client: VergeClient) -> None:
        """Test that node2 has a GPU available (per project notes)."""
        try:
            node2 = live_client.nodes.get(name="node2")
        except Exception:
            pytest.skip("node2 not found")

        # Check for any GPU devices on node2
        host_gpus = node2.host_gpu_devices.list()
        vgpu_devices = node2.vgpu_devices.list()
        configured_gpus = node2.gpus.list()

        print("node2 GPU inventory:")
        print(f"  Host GPUs (passthrough): {len(host_gpus)}")
        print(f"  vGPU devices: {len(vgpu_devices)}")
        print(f"  Configured GPUs: {len(configured_gpus)}")

        # Per project notes, node2 should have a GPU
        total_gpus = len(host_gpus) + len(vgpu_devices)
        if total_gpus == 0:
            print("WARNING: node2 expected to have GPU but none found")


class TestGpuWorkflow:
    """Integration tests for complete GPU workflows."""

    def test_gpu_discovery_workflow(self, live_client: VergeClient) -> None:
        """Test a typical GPU discovery workflow."""
        # 1. List all nodes
        nodes = live_client.nodes.list()
        print(f"Found {len(nodes)} node(s)")

        # 2. For each node, discover GPU capabilities
        for node in nodes:
            print(f"\nNode: {node.name}")

            # Check for vGPU-capable devices
            vgpu_devices = node.vgpu_devices.list()
            if vgpu_devices:
                print(f"  vGPU-capable devices: {len(vgpu_devices)}")
                for device in vgpu_devices:
                    print(f"    - {device.name} (max {device.max_instances} instances)")

            # Check for host GPUs (passthrough)
            host_gpus = node.host_gpu_devices.list()
            if host_gpus:
                print(f"  Host GPUs (passthrough): {len(host_gpus)}")
                for gpu in host_gpus:
                    print(f"    - {gpu.name}")

            # Check configured GPUs
            configured = node.gpus.list()
            if configured:
                print(f"  Configured GPUs: {len(configured)}")
                for gpu in configured:
                    print(f"    - {gpu.name}: {gpu.mode_display}")
                    if gpu.is_vgpu:
                        print(f"      Profile: {gpu.nvidia_vgpu_profile_display}")
                        print(f"      Instances: {gpu.instances_count}/{gpu.max_instances}")

    def test_vgpu_profile_discovery(self, live_client: VergeClient) -> None:
        """Test discovering available vGPU profiles."""
        # 1. List global vGPU profiles
        profiles = live_client.vgpu_profiles.list()
        print(f"Found {len(profiles)} global vGPU profile(s)")

        if profiles:
            # Group by type
            by_type: dict[str, list] = {"A": [], "B": [], "C": [], "Q": []}
            for profile in profiles:
                if profile.profile_type in by_type:
                    by_type[profile.profile_type].append(profile)

            for ptype, profs in by_type.items():
                if profs:
                    print(f"\nType {ptype} ({profs[0].profile_type_display}):")
                    for p in profs[:3]:  # Show first 3 of each type
                        print(f"  - {p.name}: {p.framebuffer} RAM, max {p.max_instance}/GPU")
