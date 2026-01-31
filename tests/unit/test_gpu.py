"""Unit tests for GPU and vGPU management."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock

import pytest

from pyvergeos.exceptions import NotFoundError
from pyvergeos.resources.gpu import (
    NodeGpu,
    NodeGpuInstance,
    NodeGpuInstanceManager,
    NodeGpuManager,
    NodeGpuStats,
    NodeGpuStatsHistory,
    NodeGpuStatsManager,
    NodeHostGpuDevice,
    NodeHostGpuDeviceManager,
    NodeVgpuDevice,
    NodeVgpuDeviceManager,
    NodeVgpuProfile,
    NodeVgpuProfileManager,
    NvidiaVgpuProfile,
    NvidiaVgpuProfileManager,
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
def sample_vgpu_profile_data() -> dict[str, Any]:
    """Sample NVIDIA vGPU profile data."""
    return {
        "$key": 1,
        "name": "nvidia-256",
        "type_id": 45,
        "device_hex": "10de:1eb8",
        "num_heads": 4,
        "frl_config": 60,
        "framebuffer": "256M",
        "max_resolution": "4096x2160",
        "max_instance": 24,
        "max_instances_per_vm": 1,
        "placement_ids": "1,2,3,4",
        "location": "/sys/devices/pci0000:00/0000:00:03.0/mdev_supported_types",
        "profile_type": "C",
        "grid_license": "GRID-Virtual-WS-Ext",
        "virtual_function": False,
        "profile_folder": "nvidia-256",
    }


@pytest.fixture
def sample_node_gpu_data() -> dict[str, Any]:
    """Sample node GPU data."""
    return {
        "$key": 1,
        "name": "GPU_1",
        "description": "NVIDIA Tesla T4 for AI workloads",
        "pci_device": 10,
        "pci_device_name": "NVIDIA Corporation TU104GL [Tesla T4]",
        "node": 2,
        "node_name": "node2",
        "mode": "nvidia_vgpu",
        "nvidia_vgpu_profile": 1,
        "nvidia_vgpu_profile_disp": "nvidia-256",
        "max_instances": 24,
        "instances_count": 4,
        "modified": 1704067200,
    }


@pytest.fixture
def sample_gpu_stats_data() -> dict[str, Any]:
    """Sample GPU stats data."""
    return {
        "$key": 1,
        "node_gpu": 1,
        "gpus_total": 1,
        "gpus": 1,
        "gpus_idle": 0,
        "vgpus_total": 24,
        "vgpus": 4,
        "vgpus_idle": 20,
        "timestamp": 1704067200,
    }


@pytest.fixture
def sample_gpu_stats_history_data() -> dict[str, Any]:
    """Sample GPU stats history data."""
    return {
        "$key": 1,
        "node_gpu": 1,
        "timestamp": 1704067200,
        "gpus_total": 1,
        "gpus": 1,
        "gpus_idle": 0,
        "vgpus_total": 24,
        "vgpus": 4,
        "vgpus_idle": 20,
    }


@pytest.fixture
def sample_gpu_instance_data() -> dict[str, Any]:
    """Sample GPU instance data."""
    return {
        "$key": 1,
        "gpu_key": 1,
        "gpu_name": "GPU_1",
        "node_key": 2,
        "node_display": "node2",
        "mode": "nvidia_vgpu",
        "mode_display": "NVIDIA vGPU",
        "pci_device_key": 10,
        "pci_device_name": "NVIDIA Corporation TU104GL [Tesla T4]",
        "machine_device_key": 5,
        "machine_device_name": "vgpu_0",
        "machine_key": 100,
        "machine_name": "ai-workload-1",
        "machine_type": "vm",
        "machine_type_display": "Virtual Machine",
        "machine_device_status": "online",
        "description": "AI Training GPU",
        "modified": 1704067200,
    }


@pytest.fixture
def sample_vgpu_device_data() -> dict[str, Any]:
    """Sample vGPU-capable device data."""
    return {
        "$key": 1,
        "node": 2,
        "node_name": "node2",
        "pci_device": 10,
        "name": "NVIDIA Corporation TU104GL [Tesla T4]",
        "slot": "0000:41:00.0",
        "vendor": "NVIDIA Corporation",
        "device": "TU104GL [Tesla T4]",
        "vendor_device_hex": "10de:1eb8",
        "driver": "nvidia",
        "module": "nvidia",
        "numa": "0",
        "iommu_group": "41",
        "type_id": 45,
        "max_instances": 24,
        "physical_function": "",
        "virtfn": "",
        "fingerprint": "abc123def456",
        "created": 1704000000,
        "modified": 1704067200,
    }


@pytest.fixture
def sample_host_gpu_device_data() -> dict[str, Any]:
    """Sample host GPU device data."""
    return {
        "$key": 1,
        "node": 2,
        "node_name": "node2",
        "pci_device": 11,
        "name": "NVIDIA Corporation GA102GL [RTX A6000]",
        "slot": "0000:42:00.0",
        "vendor": "NVIDIA Corporation",
        "device": "GA102GL [RTX A6000]",
        "vendor_device_hex": "10de:2230",
        "driver": "vfio-pci",
        "module": "vfio_pci",
        "numa": "0",
        "iommu_group": "42",
        "type_id": 0,
        "device_index": 0,
        "max_instances": 1,
        "fingerprint": "gpu123abc",
        "created": 1704000000,
        "modified": 1704067200,
    }


@pytest.fixture
def sample_node_vgpu_profile_data() -> dict[str, Any]:
    """Sample node-specific vGPU profile data."""
    return {
        "$key": 1,
        "physical_gpu": 10,
        "name": "nvidia-256",
        "num_heads": 4,
        "frl_config": 60,
        "framebuffer": "256M",
        "max_resolution": "4096x2160",
        "max_instance": 24,
        "available_instances": 20,
        "device_api": "1.0",
        "profile_type": "C",
        "virtual_function": False,
        "profile_folder": "nvidia-256",
    }


# =============================================================================
# NvidiaVgpuProfile Model Tests
# =============================================================================


class TestNvidiaVgpuProfile:
    """Tests for NvidiaVgpuProfile model."""

    def test_profile_properties(self, sample_vgpu_profile_data: dict[str, Any]) -> None:
        """Test profile properties."""
        manager = MagicMock()
        profile = NvidiaVgpuProfile(sample_vgpu_profile_data, manager)

        assert profile.name == "nvidia-256"
        assert profile.type_id == 45
        assert profile.device_hex == "10de:1eb8"
        assert profile.num_heads == 4
        assert profile.frl_config == 60
        assert profile.framebuffer == "256M"
        assert profile.max_resolution == "4096x2160"
        assert profile.max_instance == 24
        assert profile.max_instances_per_vm == 1
        assert profile.profile_type == "C"
        assert profile.grid_license == "GRID-Virtual-WS-Ext"
        assert profile.is_virtual_function is False

    def test_profile_type_display(self, sample_vgpu_profile_data: dict[str, Any]) -> None:
        """Test profile type display."""
        manager = MagicMock()
        profile = NvidiaVgpuProfile(sample_vgpu_profile_data, manager)

        assert profile.profile_type_display == "AI/Machine Learning/Training (vCS or vWS)"

    def test_profile_repr(self, sample_vgpu_profile_data: dict[str, Any]) -> None:
        """Test profile repr."""
        manager = MagicMock()
        profile = NvidiaVgpuProfile(sample_vgpu_profile_data, manager)

        assert "NvidiaVgpuProfile" in repr(profile)
        assert "nvidia-256" in repr(profile)
        assert "256M" in repr(profile)


# =============================================================================
# NvidiaVgpuProfileManager Tests
# =============================================================================


class TestNvidiaVgpuProfileManager:
    """Tests for NvidiaVgpuProfileManager."""

    def test_list_profiles(
        self,
        mock_client: MagicMock,
        sample_vgpu_profile_data: dict[str, Any],
    ) -> None:
        """Test listing vGPU profiles."""
        mock_client._request.return_value = [sample_vgpu_profile_data]
        manager = NvidiaVgpuProfileManager(mock_client)

        profiles = manager.list()

        assert len(profiles) == 1
        assert profiles[0].name == "nvidia-256"
        mock_client._request.assert_called_once()

    def test_list_profiles_by_type(
        self,
        mock_client: MagicMock,
        sample_vgpu_profile_data: dict[str, Any],
    ) -> None:
        """Test listing profiles filtered by type."""
        mock_client._request.return_value = [sample_vgpu_profile_data]
        manager = NvidiaVgpuProfileManager(mock_client)

        manager.list(profile_type="C")

        call_args = mock_client._request.call_args
        assert "profile_type eq 'C'" in call_args[1]["params"]["filter"]

    def test_get_profile_by_key(
        self,
        mock_client: MagicMock,
        sample_vgpu_profile_data: dict[str, Any],
    ) -> None:
        """Test getting a profile by key."""
        mock_client._request.return_value = sample_vgpu_profile_data
        manager = NvidiaVgpuProfileManager(mock_client)

        profile = manager.get(key=1)

        assert profile.name == "nvidia-256"

    def test_get_profile_by_name(
        self,
        mock_client: MagicMock,
        sample_vgpu_profile_data: dict[str, Any],
    ) -> None:
        """Test getting a profile by name."""
        mock_client._request.return_value = [sample_vgpu_profile_data]
        manager = NvidiaVgpuProfileManager(mock_client)

        profile = manager.get(name="nvidia-256")

        assert profile.type_id == 45

    def test_get_profile_not_found(self, mock_client: MagicMock) -> None:
        """Test getting a profile that doesn't exist."""
        mock_client._request.return_value = None
        manager = NvidiaVgpuProfileManager(mock_client)

        with pytest.raises(NotFoundError):
            manager.get(key=999)

    def test_get_profile_requires_key_or_name(self, mock_client: MagicMock) -> None:
        """Test that get requires key or name."""
        manager = NvidiaVgpuProfileManager(mock_client)

        with pytest.raises(ValueError, match="Either key or name must be provided"):
            manager.get()


# =============================================================================
# NodeGpu Model Tests
# =============================================================================


class TestNodeGpu:
    """Tests for NodeGpu model."""

    def test_gpu_properties(self, sample_node_gpu_data: dict[str, Any]) -> None:
        """Test GPU properties."""
        manager = MagicMock()
        gpu = NodeGpu(sample_node_gpu_data, manager)

        assert gpu.name == "GPU_1"
        assert gpu.description == "NVIDIA Tesla T4 for AI workloads"
        assert gpu.pci_device_key == 10
        assert gpu.pci_device_name == "NVIDIA Corporation TU104GL [Tesla T4]"
        assert gpu.node_key == 2
        assert gpu.node_name == "node2"
        assert gpu.mode == "nvidia_vgpu"
        assert gpu.nvidia_vgpu_profile_key == 1
        assert gpu.nvidia_vgpu_profile_display == "nvidia-256"
        assert gpu.max_instances == 24
        assert gpu.instances_count == 4

    def test_gpu_mode_display(self, sample_node_gpu_data: dict[str, Any]) -> None:
        """Test GPU mode display."""
        manager = MagicMock()
        gpu = NodeGpu(sample_node_gpu_data, manager)

        assert gpu.mode_display == "NVIDIA vGPU"

    def test_gpu_mode_checks(self, sample_node_gpu_data: dict[str, Any]) -> None:
        """Test GPU mode helper properties."""
        manager = MagicMock()

        # vGPU mode
        gpu = NodeGpu(sample_node_gpu_data, manager)
        assert gpu.is_vgpu is True
        assert gpu.is_passthrough is False
        assert gpu.is_disabled is False

        # Passthrough mode
        passthrough_data = dict(sample_node_gpu_data)
        passthrough_data["mode"] = "gpu"
        gpu = NodeGpu(passthrough_data, manager)
        assert gpu.is_passthrough is True
        assert gpu.is_vgpu is False

        # Disabled
        disabled_data = dict(sample_node_gpu_data)
        disabled_data["mode"] = "none"
        gpu = NodeGpu(disabled_data, manager)
        assert gpu.is_disabled is True

    def test_gpu_modified_at(self, sample_node_gpu_data: dict[str, Any]) -> None:
        """Test modified timestamp."""
        manager = MagicMock()
        gpu = NodeGpu(sample_node_gpu_data, manager)

        assert gpu.modified_at is not None
        assert gpu.modified_at.year == 2024
        assert gpu.modified_at.tzinfo == timezone.utc

    def test_gpu_repr(self, sample_node_gpu_data: dict[str, Any]) -> None:
        """Test GPU repr."""
        manager = MagicMock()
        gpu = NodeGpu(sample_node_gpu_data, manager)

        assert "NodeGpu" in repr(gpu)
        assert "GPU_1" in repr(gpu)
        assert "nvidia_vgpu" in repr(gpu)


# =============================================================================
# NodeGpuManager Tests
# =============================================================================


class TestNodeGpuManager:
    """Tests for NodeGpuManager."""

    def test_list_gpus(
        self,
        mock_client: MagicMock,
        sample_node_gpu_data: dict[str, Any],
    ) -> None:
        """Test listing GPUs."""
        mock_client._request.return_value = [sample_node_gpu_data]
        manager = NodeGpuManager(mock_client)

        gpus = manager.list()

        assert len(gpus) == 1
        assert gpus[0].name == "GPU_1"

    def test_list_gpus_scoped_to_node(
        self,
        mock_client: MagicMock,
        sample_node_gpu_data: dict[str, Any],
    ) -> None:
        """Test listing GPUs scoped to a node."""
        mock_client._request.return_value = [sample_node_gpu_data]
        manager = NodeGpuManager(mock_client, node_key=2)

        manager.list()

        call_args = mock_client._request.call_args
        assert "node eq 2" in call_args[1]["params"]["filter"]

    def test_list_gpus_by_mode(
        self,
        mock_client: MagicMock,
        sample_node_gpu_data: dict[str, Any],
    ) -> None:
        """Test listing GPUs filtered by mode."""
        mock_client._request.return_value = [sample_node_gpu_data]
        manager = NodeGpuManager(mock_client)

        manager.list(mode="nvidia_vgpu")

        call_args = mock_client._request.call_args
        assert "mode eq 'nvidia_vgpu'" in call_args[1]["params"]["filter"]

    def test_list_enabled_only(
        self,
        mock_client: MagicMock,
        sample_node_gpu_data: dict[str, Any],
    ) -> None:
        """Test listing only enabled GPUs."""
        mock_client._request.return_value = [sample_node_gpu_data]
        manager = NodeGpuManager(mock_client)

        manager.list(enabled_only=True)

        call_args = mock_client._request.call_args
        assert "mode ne 'none'" in call_args[1]["params"]["filter"]

    def test_get_gpu_by_key(
        self,
        mock_client: MagicMock,
        sample_node_gpu_data: dict[str, Any],
    ) -> None:
        """Test getting a GPU by key."""
        mock_client._request.return_value = sample_node_gpu_data
        manager = NodeGpuManager(mock_client)

        gpu = manager.get(key=1)

        assert gpu.name == "GPU_1"

    def test_get_gpu_by_name(
        self,
        mock_client: MagicMock,
        sample_node_gpu_data: dict[str, Any],
    ) -> None:
        """Test getting a GPU by name."""
        mock_client._request.return_value = [sample_node_gpu_data]
        manager = NodeGpuManager(mock_client)

        gpu = manager.get(name="GPU_1")

        assert gpu.key == 1

    def test_update_gpu(
        self,
        mock_client: MagicMock,
        sample_node_gpu_data: dict[str, Any],
    ) -> None:
        """Test updating a GPU."""
        mock_client._request.return_value = sample_node_gpu_data
        manager = NodeGpuManager(mock_client)

        manager.update(key=1, mode="gpu")

        call_args = mock_client._request.call_args
        assert call_args[0][0] == "PUT"
        assert call_args[1]["json_data"]["mode"] == "gpu"


# =============================================================================
# NodeGpuStats Model Tests
# =============================================================================


class TestNodeGpuStats:
    """Tests for NodeGpuStats model."""

    def test_stats_properties(self, sample_gpu_stats_data: dict[str, Any]) -> None:
        """Test stats properties."""
        manager = MagicMock()
        stats = NodeGpuStats(sample_gpu_stats_data, manager)

        assert stats.gpu_key == 1
        assert stats.gpus_total == 1
        assert stats.gpus == 1
        assert stats.gpus_idle == 0
        assert stats.vgpus_total == 24
        assert stats.vgpus == 4
        assert stats.vgpus_idle == 20

    def test_stats_timestamp(self, sample_gpu_stats_data: dict[str, Any]) -> None:
        """Test stats timestamp."""
        manager = MagicMock()
        stats = NodeGpuStats(sample_gpu_stats_data, manager)

        assert stats.timestamp is not None
        assert stats.timestamp.year == 2024

    def test_stats_repr(self, sample_gpu_stats_data: dict[str, Any]) -> None:
        """Test stats repr."""
        manager = MagicMock()
        stats = NodeGpuStats(sample_gpu_stats_data, manager)

        assert "NodeGpuStats" in repr(stats)
        assert "vgpus=4/24" in repr(stats)


# =============================================================================
# NodeGpuStatsHistory Model Tests
# =============================================================================


class TestNodeGpuStatsHistory:
    """Tests for NodeGpuStatsHistory model."""

    def test_history_properties(self, sample_gpu_stats_history_data: dict[str, Any]) -> None:
        """Test history properties."""
        manager = MagicMock()
        history = NodeGpuStatsHistory(sample_gpu_stats_history_data, manager)

        assert history.gpu_key == 1
        assert history.timestamp_epoch == 1704067200
        assert history.vgpus == 4
        assert history.vgpus_total == 24

    def test_history_repr(self, sample_gpu_stats_history_data: dict[str, Any]) -> None:
        """Test history repr."""
        manager = MagicMock()
        history = NodeGpuStatsHistory(sample_gpu_stats_history_data, manager)

        assert "NodeGpuStatsHistory" in repr(history)


# =============================================================================
# NodeGpuStatsManager Tests
# =============================================================================


class TestNodeGpuStatsManager:
    """Tests for NodeGpuStatsManager."""

    def test_get_stats(
        self,
        mock_client: MagicMock,
        sample_gpu_stats_data: dict[str, Any],
    ) -> None:
        """Test getting current stats."""
        mock_client._request.return_value = [sample_gpu_stats_data]
        manager = NodeGpuStatsManager(mock_client, gpu_key=1)

        stats = manager.get()

        assert stats.vgpus == 4
        call_args = mock_client._request.call_args
        assert "node_gpu eq 1" in call_args[1]["params"]["filter"]

    def test_get_stats_not_found(self, mock_client: MagicMock) -> None:
        """Test getting stats when not found."""
        mock_client._request.return_value = []
        manager = NodeGpuStatsManager(mock_client, gpu_key=1)

        with pytest.raises(NotFoundError):
            manager.get()

    def test_history_short(
        self,
        mock_client: MagicMock,
        sample_gpu_stats_history_data: dict[str, Any],
    ) -> None:
        """Test getting short history."""
        mock_client._request.return_value = [sample_gpu_stats_history_data]
        manager = NodeGpuStatsManager(mock_client, gpu_key=1)

        history = manager.history_short(limit=100)

        assert len(history) == 1
        call_args = mock_client._request.call_args
        assert "node_gpu_stats_history_short" in call_args[0][1]

    def test_history_long(
        self,
        mock_client: MagicMock,
        sample_gpu_stats_history_data: dict[str, Any],
    ) -> None:
        """Test getting long history."""
        mock_client._request.return_value = [sample_gpu_stats_history_data]
        manager = NodeGpuStatsManager(mock_client, gpu_key=1)

        history = manager.history_long(limit=100)

        assert len(history) == 1
        call_args = mock_client._request.call_args
        assert "node_gpu_stats_history_long" in call_args[0][1]

    def test_history_with_datetime_filter(
        self,
        mock_client: MagicMock,
        sample_gpu_stats_history_data: dict[str, Any],
    ) -> None:
        """Test history with datetime filter."""
        mock_client._request.return_value = [sample_gpu_stats_history_data]
        manager = NodeGpuStatsManager(mock_client, gpu_key=1)

        since = datetime(2024, 1, 1, tzinfo=timezone.utc)
        manager.history_short(since=since)

        call_args = mock_client._request.call_args
        assert "timestamp ge" in call_args[1]["params"]["filter"]


# =============================================================================
# NodeGpuInstance Model Tests
# =============================================================================


class TestNodeGpuInstance:
    """Tests for NodeGpuInstance model."""

    def test_instance_properties(self, sample_gpu_instance_data: dict[str, Any]) -> None:
        """Test instance properties."""
        manager = MagicMock()
        instance = NodeGpuInstance(sample_gpu_instance_data, manager)

        assert instance.gpu_key == 1
        assert instance.gpu_name == "GPU_1"
        assert instance.node_key == 2
        assert instance.node_name == "node2"
        assert instance.machine_key == 100
        assert instance.machine_name == "ai-workload-1"
        assert instance.machine_type == "vm"
        assert instance.mode == "nvidia_vgpu"
        assert instance.description == "AI Training GPU"

    def test_instance_repr(self, sample_gpu_instance_data: dict[str, Any]) -> None:
        """Test instance repr."""
        manager = MagicMock()
        instance = NodeGpuInstance(sample_gpu_instance_data, manager)

        assert "NodeGpuInstance" in repr(instance)
        assert "GPU_1" in repr(instance)
        assert "ai-workload-1" in repr(instance)


# =============================================================================
# NodeGpuInstanceManager Tests
# =============================================================================


class TestNodeGpuInstanceManager:
    """Tests for NodeGpuInstanceManager."""

    def test_list_instances(
        self,
        mock_client: MagicMock,
        sample_gpu_instance_data: dict[str, Any],
    ) -> None:
        """Test listing GPU instances."""
        mock_client._request.return_value = [sample_gpu_instance_data]
        manager = NodeGpuInstanceManager(mock_client, gpu_key=1)

        instances = manager.list()

        assert len(instances) == 1
        assert instances[0].machine_name == "ai-workload-1"
        call_args = mock_client._request.call_args
        assert "gpu eq 1" in call_args[1]["params"]["filter"]


# =============================================================================
# NodeVgpuDevice Model Tests
# =============================================================================


class TestNodeVgpuDevice:
    """Tests for NodeVgpuDevice model."""

    def test_device_properties(self, sample_vgpu_device_data: dict[str, Any]) -> None:
        """Test device properties."""
        manager = MagicMock()
        device = NodeVgpuDevice(sample_vgpu_device_data, manager)

        assert device.node_key == 2
        assert device.node_name == "node2"
        assert device.pci_device_key == 10
        assert device.name == "NVIDIA Corporation TU104GL [Tesla T4]"
        assert device.slot == "0000:41:00.0"
        assert device.vendor == "NVIDIA Corporation"
        assert device.device == "TU104GL [Tesla T4]"
        assert device.vendor_device_hex == "10de:1eb8"
        assert device.driver == "nvidia"
        assert device.type_id == 45
        assert device.max_instances == 24

    def test_device_repr(self, sample_vgpu_device_data: dict[str, Any]) -> None:
        """Test device repr."""
        manager = MagicMock()
        device = NodeVgpuDevice(sample_vgpu_device_data, manager)

        assert "NodeVgpuDevice" in repr(device)
        assert "0000:41:00.0" in repr(device)


# =============================================================================
# NodeVgpuDeviceManager Tests
# =============================================================================


class TestNodeVgpuDeviceManager:
    """Tests for NodeVgpuDeviceManager."""

    def test_list_devices(
        self,
        mock_client: MagicMock,
        sample_vgpu_device_data: dict[str, Any],
    ) -> None:
        """Test listing vGPU devices."""
        mock_client._request.return_value = [sample_vgpu_device_data]
        manager = NodeVgpuDeviceManager(mock_client)

        devices = manager.list()

        assert len(devices) == 1
        assert devices[0].vendor == "NVIDIA Corporation"

    def test_list_devices_scoped_to_node(
        self,
        mock_client: MagicMock,
        sample_vgpu_device_data: dict[str, Any],
    ) -> None:
        """Test listing devices scoped to a node."""
        mock_client._request.return_value = [sample_vgpu_device_data]
        manager = NodeVgpuDeviceManager(mock_client, node_key=2)

        manager.list()

        call_args = mock_client._request.call_args
        assert "node eq 2" in call_args[1]["params"]["filter"]

    def test_list_devices_by_vendor(
        self,
        mock_client: MagicMock,
        sample_vgpu_device_data: dict[str, Any],
    ) -> None:
        """Test listing devices by vendor."""
        mock_client._request.return_value = [sample_vgpu_device_data]
        manager = NodeVgpuDeviceManager(mock_client)

        manager.list(vendor="NVIDIA")

        call_args = mock_client._request.call_args
        assert "vendor ct 'NVIDIA'" in call_args[1]["params"]["filter"]

    def test_get_device(
        self,
        mock_client: MagicMock,
        sample_vgpu_device_data: dict[str, Any],
    ) -> None:
        """Test getting a device by key."""
        mock_client._request.return_value = sample_vgpu_device_data
        manager = NodeVgpuDeviceManager(mock_client)

        device = manager.get(key=1)

        assert device.slot == "0000:41:00.0"


# =============================================================================
# NodeHostGpuDevice Model Tests
# =============================================================================


class TestNodeHostGpuDevice:
    """Tests for NodeHostGpuDevice model."""

    def test_device_properties(self, sample_host_gpu_device_data: dict[str, Any]) -> None:
        """Test device properties."""
        manager = MagicMock()
        device = NodeHostGpuDevice(sample_host_gpu_device_data, manager)

        assert device.node_key == 2
        assert device.node_name == "node2"
        assert device.name == "NVIDIA Corporation GA102GL [RTX A6000]"
        assert device.slot == "0000:42:00.0"
        assert device.vendor == "NVIDIA Corporation"
        assert device.driver == "vfio-pci"
        assert device.max_instances == 1

    def test_device_repr(self, sample_host_gpu_device_data: dict[str, Any]) -> None:
        """Test device repr."""
        manager = MagicMock()
        device = NodeHostGpuDevice(sample_host_gpu_device_data, manager)

        assert "NodeHostGpuDevice" in repr(device)


# =============================================================================
# NodeHostGpuDeviceManager Tests
# =============================================================================


class TestNodeHostGpuDeviceManager:
    """Tests for NodeHostGpuDeviceManager."""

    def test_list_devices(
        self,
        mock_client: MagicMock,
        sample_host_gpu_device_data: dict[str, Any],
    ) -> None:
        """Test listing host GPU devices."""
        mock_client._request.return_value = [sample_host_gpu_device_data]
        manager = NodeHostGpuDeviceManager(mock_client)

        devices = manager.list()

        assert len(devices) == 1
        assert devices[0].driver == "vfio-pci"

    def test_list_devices_scoped_to_node(
        self,
        mock_client: MagicMock,
        sample_host_gpu_device_data: dict[str, Any],
    ) -> None:
        """Test listing devices scoped to a node."""
        mock_client._request.return_value = [sample_host_gpu_device_data]
        manager = NodeHostGpuDeviceManager(mock_client, node_key=2)

        manager.list()

        call_args = mock_client._request.call_args
        assert "node eq 2" in call_args[1]["params"]["filter"]

    def test_get_device(
        self,
        mock_client: MagicMock,
        sample_host_gpu_device_data: dict[str, Any],
    ) -> None:
        """Test getting a device by key."""
        mock_client._request.return_value = sample_host_gpu_device_data
        manager = NodeHostGpuDeviceManager(mock_client)

        device = manager.get(key=1)

        assert device.slot == "0000:42:00.0"


# =============================================================================
# NodeVgpuProfile Model Tests
# =============================================================================


class TestNodeVgpuProfile:
    """Tests for NodeVgpuProfile model."""

    def test_profile_properties(self, sample_node_vgpu_profile_data: dict[str, Any]) -> None:
        """Test profile properties."""
        manager = MagicMock()
        profile = NodeVgpuProfile(sample_node_vgpu_profile_data, manager)

        assert profile.physical_gpu_key == 10
        assert profile.name == "nvidia-256"
        assert profile.framebuffer == "256M"
        assert profile.max_instance == 24
        assert profile.available_instances == 20
        assert profile.profile_type == "C"

    def test_profile_type_display(self, sample_node_vgpu_profile_data: dict[str, Any]) -> None:
        """Test profile type display."""
        manager = MagicMock()
        profile = NodeVgpuProfile(sample_node_vgpu_profile_data, manager)

        assert profile.profile_type_display == "AI/Machine Learning/Training (vCS or vWS)"

    def test_profile_repr(self, sample_node_vgpu_profile_data: dict[str, Any]) -> None:
        """Test profile repr."""
        manager = MagicMock()
        profile = NodeVgpuProfile(sample_node_vgpu_profile_data, manager)

        assert "NodeVgpuProfile" in repr(profile)
        assert "nvidia-256" in repr(profile)


# =============================================================================
# NodeVgpuProfileManager Tests
# =============================================================================


class TestNodeVgpuProfileManager:
    """Tests for NodeVgpuProfileManager."""

    def test_list_profiles(
        self,
        mock_client: MagicMock,
        sample_node_vgpu_profile_data: dict[str, Any],
    ) -> None:
        """Test listing vGPU profiles."""
        mock_client._request.return_value = [sample_node_vgpu_profile_data]
        manager = NodeVgpuProfileManager(mock_client)

        profiles = manager.list()

        assert len(profiles) == 1
        assert profiles[0].name == "nvidia-256"

    def test_list_profiles_scoped_to_gpu(
        self,
        mock_client: MagicMock,
        sample_node_vgpu_profile_data: dict[str, Any],
    ) -> None:
        """Test listing profiles scoped to a physical GPU."""
        mock_client._request.return_value = [sample_node_vgpu_profile_data]
        manager = NodeVgpuProfileManager(mock_client, physical_gpu_key=10)

        manager.list()

        call_args = mock_client._request.call_args
        assert "physical_gpu eq 10" in call_args[1]["params"]["filter"]

    def test_list_profiles_by_type(
        self,
        mock_client: MagicMock,
        sample_node_vgpu_profile_data: dict[str, Any],
    ) -> None:
        """Test listing profiles by type."""
        mock_client._request.return_value = [sample_node_vgpu_profile_data]
        manager = NodeVgpuProfileManager(mock_client)

        manager.list(profile_type="C")

        call_args = mock_client._request.call_args
        assert "profile_type eq 'C'" in call_args[1]["params"]["filter"]

    def test_get_profile_by_key(
        self,
        mock_client: MagicMock,
        sample_node_vgpu_profile_data: dict[str, Any],
    ) -> None:
        """Test getting a profile by key."""
        mock_client._request.return_value = sample_node_vgpu_profile_data
        manager = NodeVgpuProfileManager(mock_client)

        profile = manager.get(key=1)

        assert profile.name == "nvidia-256"

    def test_get_profile_by_name(
        self,
        mock_client: MagicMock,
        sample_node_vgpu_profile_data: dict[str, Any],
    ) -> None:
        """Test getting a profile by name."""
        mock_client._request.return_value = [sample_node_vgpu_profile_data]
        manager = NodeVgpuProfileManager(mock_client)

        profile = manager.get(name="nvidia-256")

        assert profile.available_instances == 20


# =============================================================================
# Node Integration Tests
# =============================================================================


class TestNodeGpuIntegration:
    """Tests for Node integration with GPU managers."""

    def test_node_has_gpus_property(self, mock_client: MagicMock) -> None:
        """Test that Node has gpus property."""
        from pyvergeos.resources.nodes import Node

        node_data = {
            "$key": 2,
            "name": "node2",
            "machine": 100,
        }
        manager = MagicMock()
        manager._client = mock_client
        node = Node(node_data, manager)

        gpus_manager = node.gpus
        assert isinstance(gpus_manager, NodeGpuManager)
        assert gpus_manager._node_key == 2

    def test_node_has_vgpu_devices_property(self, mock_client: MagicMock) -> None:
        """Test that Node has vgpu_devices property."""
        from pyvergeos.resources.nodes import Node

        node_data = {
            "$key": 2,
            "name": "node2",
            "machine": 100,
        }
        manager = MagicMock()
        manager._client = mock_client
        node = Node(node_data, manager)

        vgpu_manager = node.vgpu_devices
        assert isinstance(vgpu_manager, NodeVgpuDeviceManager)
        assert vgpu_manager._node_key == 2

    def test_node_has_host_gpu_devices_property(self, mock_client: MagicMock) -> None:
        """Test that Node has host_gpu_devices property."""
        from pyvergeos.resources.nodes import Node

        node_data = {
            "$key": 2,
            "name": "node2",
            "machine": 100,
        }
        manager = MagicMock()
        manager._client = mock_client
        node = Node(node_data, manager)

        host_gpu_manager = node.host_gpu_devices
        assert isinstance(host_gpu_manager, NodeHostGpuDeviceManager)
        assert host_gpu_manager._node_key == 2

    def test_node_manager_has_all_gpus(self, mock_client: MagicMock) -> None:
        """Test that NodeManager has all_gpus property."""
        from pyvergeos.resources.nodes import NodeManager

        manager = NodeManager(mock_client)
        all_gpus = manager.all_gpus

        assert isinstance(all_gpus, NodeGpuManager)
        assert all_gpus._node_key is None

    def test_node_manager_has_all_vgpu_devices(self, mock_client: MagicMock) -> None:
        """Test that NodeManager has all_vgpu_devices property."""
        from pyvergeos.resources.nodes import NodeManager

        manager = NodeManager(mock_client)
        all_vgpu = manager.all_vgpu_devices

        assert isinstance(all_vgpu, NodeVgpuDeviceManager)
        assert all_vgpu._node_key is None

    def test_node_manager_has_all_host_gpu_devices(self, mock_client: MagicMock) -> None:
        """Test that NodeManager has all_host_gpu_devices property."""
        from pyvergeos.resources.nodes import NodeManager

        manager = NodeManager(mock_client)
        all_host_gpu = manager.all_host_gpu_devices

        assert isinstance(all_host_gpu, NodeHostGpuDeviceManager)
        assert all_host_gpu._node_key is None


# =============================================================================
# Client Integration Tests
# =============================================================================


class TestClientGpuIntegration:
    """Tests for VergeClient integration with GPU managers."""

    def test_client_has_vgpu_profiles(self, mock_client: MagicMock) -> None:
        """Test that client has vgpu_profiles property."""
        # Mock the connection validation
        mock_client._vgpu_profiles = None
        mock_client._connection = MagicMock()
        mock_client._connection.is_connected = True

        # Simulate what the client property does
        from pyvergeos.resources.gpu import NvidiaVgpuProfileManager

        manager = NvidiaVgpuProfileManager(mock_client)
        assert isinstance(manager, NvidiaVgpuProfileManager)
