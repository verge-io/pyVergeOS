"""GPU and vGPU management for VergeOS.

This module provides access to GPU passthrough and NVIDIA vGPU functionality,
enabling AI/ML workloads and graphics-intensive applications.

Example:
    >>> # List all vGPU profiles available in the system
    >>> for profile in client.vgpu_profiles.list():
    ...     print(f"{profile.name}: {profile.framebuffer} RAM")

    >>> # List GPUs configured on a node
    >>> node = client.nodes.get(name="node2")
    >>> for gpu in node.gpus.list():
    ...     print(f"{gpu.name}: {gpu.mode_display}")

    >>> # Configure a GPU for passthrough
    >>> gpu = node.gpus.get(name="GPU_1")
    >>> gpu = node.gpus.update(gpu.key, mode="gpu")

    >>> # Get GPU stats
    >>> stats = gpu.stats.get()
    >>> print(f"vGPUs in use: {stats.vgpus}/{stats.vgpus_total}")
"""

from __future__ import annotations

import builtins
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Literal

from pyvergeos.exceptions import NotFoundError
from pyvergeos.filters import build_filter
from pyvergeos.resources.base import ResourceManager, ResourceObject

if TYPE_CHECKING:
    from pyvergeos.client import VergeClient


# GPU mode display mappings
GPU_MODE_DISPLAY = {
    "none": "None",
    "gpu": "PCI Passthrough",
    "nvidia_vgpu": "NVIDIA vGPU",
}

# vGPU profile type mappings
PROFILE_TYPE_DISPLAY = {
    "A": "Virtual Applications (vApps)",
    "B": "Virtual Desktops (vPC)",
    "C": "AI/Machine Learning/Training (vCS or vWS)",
    "Q": "Virtual Workstations (vWS)",
}


# =============================================================================
# NVIDIA vGPU Profiles (Global)
# =============================================================================


class NvidiaVgpuProfile(ResourceObject):
    """NVIDIA vGPU profile resource object.

    Represents a vGPU profile available in the system. Profiles define
    the characteristics of virtual GPUs that can be created.

    These are read-only and determined by NVIDIA drivers.
    """

    @property
    def name(self) -> str:
        """Profile name (e.g., 'nvidia-256', 'grid_p40-1q')."""
        return str(self.get("name", ""))

    @property
    def type_id(self) -> int:
        """NVIDIA type ID for this profile."""
        return int(self.get("type_id", 0))

    @property
    def device_hex(self) -> str:
        """Vendor:device ID in hexadecimal (e.g., '10de:1eb8')."""
        return str(self.get("device_hex", ""))

    @property
    def num_heads(self) -> int:
        """Number of display heads supported."""
        return int(self.get("num_heads", 0))

    @property
    def frl_config(self) -> int:
        """Frame rate limiter configuration."""
        return int(self.get("frl_config", 0))

    @property
    def framebuffer(self) -> str:
        """Framebuffer (VRAM) size (e.g., '256M', '1G')."""
        return str(self.get("framebuffer", ""))

    @property
    def max_resolution(self) -> str:
        """Maximum supported resolution (e.g., '4096x2160')."""
        return str(self.get("max_resolution", ""))

    @property
    def max_instance(self) -> int:
        """Maximum instances per physical GPU."""
        return int(self.get("max_instance", 0))

    @property
    def max_instances_per_vm(self) -> int:
        """Maximum vGPU instances per VM."""
        return int(self.get("max_instances_per_vm", 0))

    @property
    def placement_ids(self) -> str:
        """Placement IDs for this profile."""
        return str(self.get("placement_ids", ""))

    @property
    def location(self) -> str:
        """Profile location/path."""
        return str(self.get("location", ""))

    @property
    def profile_type(self) -> str:
        """Profile type code (A, B, C, Q)."""
        return str(self.get("profile_type", ""))

    @property
    def profile_type_display(self) -> str:
        """Human-readable profile type."""
        return PROFILE_TYPE_DISPLAY.get(self.profile_type, self.profile_type)

    @property
    def grid_license(self) -> str:
        """Required GRID license type."""
        return str(self.get("grid_license", ""))

    @property
    def is_virtual_function(self) -> bool:
        """Whether this is a virtual function profile."""
        return bool(self.get("virtual_function", False))

    @property
    def profile_folder(self) -> str:
        """Profile folder path."""
        return str(self.get("profile_folder", ""))

    def __repr__(self) -> str:
        return (
            f"<NvidiaVgpuProfile key={self.get('$key', '?')} "
            f"name={self.name!r} fb={self.framebuffer}>"
        )


class NvidiaVgpuProfileManager(ResourceManager[NvidiaVgpuProfile]):
    """Manager for NVIDIA vGPU profiles.

    Provides read-only access to vGPU profiles available in the system.
    These profiles are determined by the NVIDIA drivers and available hardware.

    Example:
        >>> # List all profiles
        >>> for profile in client.vgpu_profiles.list():
        ...     print(f"{profile.name}: {profile.framebuffer} ({profile.profile_type_display})")

        >>> # Get profiles for AI/ML workloads
        >>> ml_profiles = client.vgpu_profiles.list(profile_type="C")
    """

    _endpoint = "nvidia_vgpu_profiles"

    _default_fields = [
        "$key",
        "name",
        "type_id",
        "device_hex",
        "num_heads",
        "frl_config",
        "framebuffer",
        "max_resolution",
        "max_instance",
        "max_instances_per_vm",
        "placement_ids",
        "location",
        "profile_type",
        "grid_license",
        "virtual_function",
        "profile_folder",
    ]

    def _to_model(self, data: dict[str, Any]) -> NvidiaVgpuProfile:
        return NvidiaVgpuProfile(data, self)

    def list(
        self,
        filter: str | None = None,  # noqa: A002
        fields: builtins.list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        *,
        profile_type: Literal["A", "B", "C", "Q"] | None = None,
        **filter_kwargs: Any,
    ) -> builtins.list[NvidiaVgpuProfile]:
        """List NVIDIA vGPU profiles.

        Args:
            filter: OData filter string.
            fields: List of fields to return.
            limit: Maximum number of results.
            offset: Skip this many results.
            profile_type: Filter by profile type:
                - A: Virtual Applications (vApps)
                - B: Virtual Desktops (vPC)
                - C: AI/ML/Training (vCS or vWS)
                - Q: Virtual Workstations (vWS)
            **filter_kwargs: Additional filter arguments.

        Returns:
            List of NvidiaVgpuProfile objects.

        Example:
            >>> # List all profiles
            >>> profiles = client.vgpu_profiles.list()

            >>> # List AI/ML profiles only
            >>> ml_profiles = client.vgpu_profiles.list(profile_type="C")
        """
        if fields is None:
            fields = self._default_fields

        filters = []

        if filter:
            filters.append(filter)

        if profile_type is not None:
            filters.append(f"profile_type eq '{profile_type}'")

        if filter_kwargs:
            filters.append(build_filter(**filter_kwargs))

        params: dict[str, Any] = {"fields": ",".join(fields)}

        if filters:
            params["filter"] = " and ".join(filters)
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset

        response = self._client._request("GET", self._endpoint, params=params)

        if response is None:
            return []

        if isinstance(response, list):
            return [self._to_model(item) for item in response]

        return [self._to_model(response)]

    def get(
        self,
        key: int | None = None,
        *,
        name: str | None = None,
        fields: builtins.list[str] | None = None,
    ) -> NvidiaVgpuProfile:
        """Get a vGPU profile by key or name.

        Args:
            key: Profile $key (ID).
            name: Profile name.
            fields: List of fields to return.

        Returns:
            NvidiaVgpuProfile object.

        Raises:
            NotFoundError: If profile not found.
            ValueError: If neither key nor name provided.
        """
        if fields is None:
            fields = self._default_fields

        if key is not None:
            params: dict[str, Any] = {"fields": ",".join(fields)}
            response = self._client._request("GET", f"{self._endpoint}/{key}", params=params)
            if response is None:
                raise NotFoundError(f"vGPU profile with key {key} not found")
            if not isinstance(response, dict):
                raise NotFoundError(f"vGPU profile with key {key} returned invalid response")
            return self._to_model(response)

        if name is not None:
            escaped = name.replace("'", "''")
            results = self.list(filter=f"name eq '{escaped}'", fields=fields, limit=1)
            if not results:
                raise NotFoundError(f"vGPU profile with name '{name}' not found")
            return results[0]

        raise ValueError("Either key or name must be provided")


# =============================================================================
# Node GPUs
# =============================================================================


class NodeGpu(ResourceObject):
    """Node GPU resource object.

    Represents a physical GPU configured on a VergeOS node. A GPU can be
    configured for PCI passthrough or NVIDIA vGPU mode.

    Example:
        >>> gpu = node.gpus.get(name="GPU_1")
        >>> print(f"Mode: {gpu.mode_display}")
        >>> print(f"Instances: {gpu.instances_count}/{gpu.max_instances}")
    """

    @property
    def name(self) -> str:
        """GPU name (e.g., 'GPU_1')."""
        return str(self.get("name", ""))

    @property
    def description(self) -> str:
        """GPU description."""
        return str(self.get("description", ""))

    @property
    def pci_device_key(self) -> int | None:
        """Associated PCI device key."""
        pci = self.get("pci_device")
        return int(pci) if pci else None

    @property
    def pci_device_name(self) -> str:
        """PCI device name/description."""
        return str(self.get("pci_device_name", ""))

    @property
    def node_key(self) -> int | None:
        """Parent node key."""
        node = self.get("node")
        return int(node) if node else None

    @property
    def node_name(self) -> str:
        """Parent node name."""
        return str(self.get("node_name", ""))

    @property
    def mode(self) -> str:
        """GPU operating mode (none, gpu, nvidia_vgpu)."""
        return str(self.get("mode", "none"))

    @property
    def mode_display(self) -> str:
        """Human-readable GPU mode."""
        return GPU_MODE_DISPLAY.get(self.mode, self.mode)

    @property
    def nvidia_vgpu_profile_key(self) -> int | None:
        """Assigned vGPU profile key (for nvidia_vgpu mode)."""
        profile = self.get("nvidia_vgpu_profile")
        return int(profile) if profile else None

    @property
    def nvidia_vgpu_profile_display(self) -> str:
        """Display name of assigned vGPU profile."""
        return str(self.get("nvidia_vgpu_profile_disp", ""))

    @property
    def max_instances(self) -> int:
        """Maximum GPU/vGPU instances this GPU can provide."""
        return int(self.get("max_instances", 0))

    @property
    def instances_count(self) -> int:
        """Current number of assigned instances."""
        return int(self.get("instances_count", 0))

    @property
    def modified_at(self) -> datetime | None:
        """Timestamp when GPU was last modified."""
        ts = self.get("modified")
        if ts:
            return datetime.fromtimestamp(int(ts), tz=timezone.utc)
        return None

    @property
    def is_passthrough(self) -> bool:
        """Check if GPU is configured for PCI passthrough."""
        return self.mode == "gpu"

    @property
    def is_vgpu(self) -> bool:
        """Check if GPU is configured for NVIDIA vGPU."""
        return self.mode == "nvidia_vgpu"

    @property
    def is_disabled(self) -> bool:
        """Check if GPU is disabled (no mode set)."""
        return self.mode == "none"

    @property
    def stats(self) -> NodeGpuStatsManager:
        """Access GPU utilization stats.

        Returns:
            NodeGpuStatsManager scoped to this GPU.

        Example:
            >>> stats = gpu.stats.get()
            >>> print(f"vGPUs: {stats.vgpus}/{stats.vgpus_total}")
        """
        from typing import cast

        manager = cast("NodeGpuManager", self._manager)
        return NodeGpuStatsManager(manager._client, self.key)

    @property
    def instances(self) -> NodeGpuInstanceManager:
        """Access GPU instances assigned to VMs.

        Returns:
            NodeGpuInstanceManager scoped to this GPU.

        Example:
            >>> for inst in gpu.instances.list():
            ...     print(f"VM: {inst.machine_name}")
        """
        from typing import cast

        manager = cast("NodeGpuManager", self._manager)
        return NodeGpuInstanceManager(manager._client, self.key)

    def refresh(self) -> NodeGpu:
        """Refresh this GPU's data from the server.

        Returns:
            Updated NodeGpu object.
        """
        from typing import cast

        manager = cast("NodeGpuManager", self._manager)
        return manager.get(key=self.key)

    def save(self, **kwargs: Any) -> NodeGpu:
        """Update this GPU with the given values.

        Args:
            **kwargs: Fields to update.

        Returns:
            Updated NodeGpu object.
        """
        from typing import cast

        manager = cast("NodeGpuManager", self._manager)
        return manager.update(self.key, **kwargs)

    def __repr__(self) -> str:
        return (
            f"<NodeGpu key={self.get('$key', '?')} name={self.name!r} "
            f"mode={self.mode} instances={self.instances_count}/{self.max_instances}>"
        )


class NodeGpuManager(ResourceManager[NodeGpu]):
    """Manager for node GPU operations.

    Provides CRUD operations for GPU configurations on nodes.
    Can be used globally or scoped to a specific node.

    Example:
        >>> # List all GPUs on a node
        >>> for gpu in node.gpus.list():
        ...     print(f"{gpu.name}: {gpu.mode_display}")

        >>> # Configure a GPU for passthrough
        >>> gpu = node.gpus.update(gpu.key, mode="gpu")

        >>> # Configure for vGPU with a specific profile
        >>> gpu = node.gpus.update(
        ...     gpu.key,
        ...     mode="nvidia_vgpu",
        ...     nvidia_vgpu_profile=profile.key
        ... )
    """

    _endpoint = "node_gpus"

    _default_fields = [
        "$key",
        "name",
        "description",
        "pci_device",
        "pci_device#name as pci_device_name",
        "node",
        "node#name as node_name",
        "mode",
        "nvidia_vgpu_profile",
        "display(nvidia_vgpu_profile) as nvidia_vgpu_profile_disp",
        "max_instances",
        "count(instances) as instances_count",
        "modified",
    ]

    def __init__(self, client: VergeClient, node_key: int | None = None) -> None:
        super().__init__(client)
        self._node_key = node_key

    def _to_model(self, data: dict[str, Any]) -> NodeGpu:
        return NodeGpu(data, self)

    def list(
        self,
        filter: str | None = None,  # noqa: A002
        fields: builtins.list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        *,
        mode: Literal["none", "gpu", "nvidia_vgpu"] | None = None,
        enabled_only: bool = False,
        **filter_kwargs: Any,
    ) -> builtins.list[NodeGpu]:
        """List node GPUs.

        Args:
            filter: OData filter string.
            fields: List of fields to return.
            limit: Maximum number of results.
            offset: Skip this many results.
            mode: Filter by GPU mode.
            enabled_only: Only return GPUs with a mode set (not 'none').
            **filter_kwargs: Additional filter arguments.

        Returns:
            List of NodeGpu objects.

        Example:
            >>> # List all GPUs on a node
            >>> gpus = node.gpus.list()

            >>> # List only passthrough GPUs
            >>> passthrough_gpus = node.gpus.list(mode="gpu")

            >>> # List enabled GPUs
            >>> enabled = node.gpus.list(enabled_only=True)
        """
        if fields is None:
            fields = self._default_fields

        filters = []

        if filter:
            filters.append(filter)

        if self._node_key is not None:
            filters.append(f"node eq {self._node_key}")

        if mode is not None:
            filters.append(f"mode eq '{mode}'")
        elif enabled_only:
            filters.append("mode ne 'none'")

        if filter_kwargs:
            filters.append(build_filter(**filter_kwargs))

        params: dict[str, Any] = {"fields": ",".join(fields)}

        if filters:
            params["filter"] = " and ".join(filters)
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset

        response = self._client._request("GET", self._endpoint, params=params)

        if response is None:
            return []

        if isinstance(response, list):
            return [self._to_model(item) for item in response]

        return [self._to_model(response)]

    def get(
        self,
        key: int | None = None,
        *,
        name: str | None = None,
        fields: builtins.list[str] | None = None,
    ) -> NodeGpu:
        """Get a GPU by key or name.

        Args:
            key: GPU $key (ID).
            name: GPU name.
            fields: List of fields to return.

        Returns:
            NodeGpu object.

        Raises:
            NotFoundError: If GPU not found.
            ValueError: If neither key nor name provided.
        """
        if fields is None:
            fields = self._default_fields

        if key is not None:
            params: dict[str, Any] = {"fields": ",".join(fields)}
            response = self._client._request("GET", f"{self._endpoint}/{key}", params=params)
            if response is None:
                raise NotFoundError(f"GPU with key {key} not found")
            if not isinstance(response, dict):
                raise NotFoundError(f"GPU with key {key} returned invalid response")
            return self._to_model(response)

        if name is not None:
            escaped = name.replace("'", "''")
            results = self.list(filter=f"name eq '{escaped}'", fields=fields, limit=1)
            if not results:
                raise NotFoundError(f"GPU with name '{name}' not found")
            return results[0]

        raise ValueError("Either key or name must be provided")

    def update(self, key: int, **kwargs: Any) -> NodeGpu:
        """Update a GPU configuration.

        Args:
            key: GPU $key (ID).
            **kwargs: Fields to update. Common fields:
                - name: GPU name
                - description: Description
                - mode: Operating mode ('none', 'gpu', 'nvidia_vgpu')
                - nvidia_vgpu_profile: vGPU profile key (for nvidia_vgpu mode)

        Returns:
            Updated NodeGpu object.

        Example:
            >>> # Enable PCI passthrough
            >>> gpu = client.nodes.gpus(node_key).update(gpu.key, mode="gpu")

            >>> # Enable vGPU mode with a profile
            >>> gpu = client.nodes.gpus(node_key).update(
            ...     gpu.key,
            ...     mode="nvidia_vgpu",
            ...     nvidia_vgpu_profile=profile.key
            ... )

            >>> # Disable GPU
            >>> gpu = client.nodes.gpus(node_key).update(gpu.key, mode="none")
        """
        response = self._client._request("PUT", f"{self._endpoint}/{key}", json_data=kwargs)
        if response is None:
            return self.get(key)
        if not isinstance(response, dict):
            return self.get(key)
        return self._to_model(response)


# =============================================================================
# Node GPU Stats
# =============================================================================


class NodeGpuStats(ResourceObject):
    """Node GPU stats resource object.

    Provides current GPU utilization metrics.
    """

    @property
    def gpu_key(self) -> int:
        """Parent GPU key."""
        return int(self.get("node_gpu", 0))

    @property
    def gpus_total(self) -> int:
        """Total GPU slots available."""
        return int(self.get("gpus_total", 0))

    @property
    def gpus(self) -> int:
        """GPUs in use."""
        return int(self.get("gpus", 0))

    @property
    def gpus_idle(self) -> int:
        """Idle GPU slots."""
        return int(self.get("gpus_idle", 0))

    @property
    def vgpus_total(self) -> int:
        """Total vGPU slots available."""
        return int(self.get("vgpus_total", 0))

    @property
    def vgpus(self) -> int:
        """vGPUs in use."""
        return int(self.get("vgpus", 0))

    @property
    def vgpus_idle(self) -> int:
        """Idle vGPU slots."""
        return int(self.get("vgpus_idle", 0))

    @property
    def timestamp(self) -> datetime | None:
        """Stats timestamp."""
        ts = self.get("timestamp")
        if ts:
            return datetime.fromtimestamp(int(ts), tz=timezone.utc)
        return None

    def __repr__(self) -> str:
        return (
            f"<NodeGpuStats gpu={self.gpu_key} "
            f"gpus={self.gpus}/{self.gpus_total} vgpus={self.vgpus}/{self.vgpus_total}>"
        )


class NodeGpuStatsHistory(ResourceObject):
    """Node GPU stats history record.

    Represents a single time point in the GPU stats history.
    """

    @property
    def gpu_key(self) -> int:
        """Parent GPU key."""
        return int(self.get("node_gpu", 0))

    @property
    def timestamp(self) -> datetime | None:
        """Timestamp for this history point."""
        ts = self.get("timestamp")
        if ts:
            return datetime.fromtimestamp(int(ts), tz=timezone.utc)
        return None

    @property
    def timestamp_epoch(self) -> int:
        """Timestamp as Unix epoch."""
        return int(self.get("timestamp", 0))

    @property
    def gpus_total(self) -> int:
        """Total GPU slots available."""
        return int(self.get("gpus_total", 0))

    @property
    def gpus(self) -> int:
        """GPUs in use."""
        return int(self.get("gpus", 0))

    @property
    def gpus_idle(self) -> int:
        """Idle GPU slots."""
        return int(self.get("gpus_idle", 0))

    @property
    def vgpus_total(self) -> int:
        """Total vGPU slots available."""
        return int(self.get("vgpus_total", 0))

    @property
    def vgpus(self) -> int:
        """vGPUs in use."""
        return int(self.get("vgpus", 0))

    @property
    def vgpus_idle(self) -> int:
        """Idle vGPU slots."""
        return int(self.get("vgpus_idle", 0))

    def __repr__(self) -> str:
        ts = self.timestamp.isoformat() if self.timestamp else "?"
        return f"<NodeGpuStatsHistory ts={ts} vgpus={self.vgpus}/{self.vgpus_total}>"


class NodeGpuStatsManager(ResourceManager[NodeGpuStats]):
    """Manager for node GPU stats.

    Provides access to current and historical GPU utilization metrics.
    Scoped to a specific GPU.

    Example:
        >>> # Get current stats
        >>> stats = gpu.stats.get()
        >>> print(f"vGPUs: {stats.vgpus}/{stats.vgpus_total}")

        >>> # Get stats history
        >>> history = gpu.stats.history_short(limit=100)
    """

    _endpoint = "node_gpu_stats"

    _default_fields = [
        "$key",
        "node_gpu",
        "gpus_total",
        "gpus",
        "gpus_idle",
        "vgpus_total",
        "vgpus",
        "vgpus_idle",
        "timestamp",
    ]

    _history_fields = [
        "$key",
        "node_gpu",
        "timestamp",
        "gpus_total",
        "gpus",
        "gpus_idle",
        "vgpus_total",
        "vgpus",
        "vgpus_idle",
    ]

    def __init__(self, client: VergeClient, gpu_key: int) -> None:
        super().__init__(client)
        self._gpu_key = gpu_key

    def _to_model(self, data: dict[str, Any]) -> NodeGpuStats:
        return NodeGpuStats(data, self)

    def _to_history_model(self, data: dict[str, Any]) -> NodeGpuStatsHistory:
        return NodeGpuStatsHistory(data, self)

    def get(self, fields: builtins.list[str] | None = None) -> NodeGpuStats:  # type: ignore[override]
        """Get current GPU stats.

        Args:
            fields: List of fields to return.

        Returns:
            NodeGpuStats object.

        Raises:
            NotFoundError: If stats not found for this GPU.
        """
        if fields is None:
            fields = self._default_fields

        params: dict[str, Any] = {
            "filter": f"node_gpu eq {self._gpu_key}",
            "fields": ",".join(fields),
            "limit": 1,
        }

        response = self._client._request("GET", self._endpoint, params=params)

        if response is None:
            raise NotFoundError(f"Stats not found for GPU {self._gpu_key}")

        if isinstance(response, list):
            if not response:
                raise NotFoundError(f"Stats not found for GPU {self._gpu_key}")
            return self._to_model(response[0])

        return self._to_model(response)

    def history_short(
        self,
        limit: int | None = None,
        offset: int | None = None,
        since: datetime | int | None = None,
        until: datetime | int | None = None,
        fields: builtins.list[str] | None = None,
    ) -> builtins.list[NodeGpuStatsHistory]:
        """Get short-term GPU stats history (high resolution).

        Args:
            limit: Maximum number of records to return.
            offset: Skip this many records.
            since: Return records after this time (datetime or epoch).
            until: Return records before this time (datetime or epoch).
            fields: List of fields to return.

        Returns:
            List of NodeGpuStatsHistory objects, sorted by timestamp descending.
        """
        return self._get_history(
            "node_gpu_stats_history_short",
            limit=limit,
            offset=offset,
            since=since,
            until=until,
            fields=fields,
        )

    def history_long(
        self,
        limit: int | None = None,
        offset: int | None = None,
        since: datetime | int | None = None,
        until: datetime | int | None = None,
        fields: builtins.list[str] | None = None,
    ) -> builtins.list[NodeGpuStatsHistory]:
        """Get long-term GPU stats history (lower resolution, longer retention).

        Args:
            limit: Maximum number of records to return.
            offset: Skip this many records.
            since: Return records after this time (datetime or epoch).
            until: Return records before this time (datetime or epoch).
            fields: List of fields to return.

        Returns:
            List of NodeGpuStatsHistory objects, sorted by timestamp descending.
        """
        return self._get_history(
            "node_gpu_stats_history_long",
            limit=limit,
            offset=offset,
            since=since,
            until=until,
            fields=fields,
        )

    def _get_history(
        self,
        endpoint: str,
        limit: int | None = None,
        offset: int | None = None,
        since: datetime | int | None = None,
        until: datetime | int | None = None,
        fields: builtins.list[str] | None = None,
    ) -> builtins.list[NodeGpuStatsHistory]:
        """Internal helper to get history from short or long endpoint."""
        if fields is None:
            fields = self._history_fields

        filters = [f"node_gpu eq {self._gpu_key}"]

        if since is not None:
            since_epoch = int(since.timestamp()) if isinstance(since, datetime) else int(since)
            filters.append(f"timestamp ge {since_epoch}")

        if until is not None:
            until_epoch = int(until.timestamp()) if isinstance(until, datetime) else int(until)
            filters.append(f"timestamp le {until_epoch}")

        params: dict[str, Any] = {
            "filter": " and ".join(filters),
            "fields": ",".join(fields),
            "sort": "-timestamp",
        }

        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset

        response = self._client._request("GET", endpoint, params=params)

        if response is None:
            return []

        if isinstance(response, list):
            return [self._to_history_model(item) for item in response]

        return [self._to_history_model(response)]


# =============================================================================
# Node GPU Instances
# =============================================================================


class NodeGpuInstance(ResourceObject):
    """Node GPU instance resource object.

    Represents a GPU or vGPU instance assigned to a VM.
    """

    @property
    def gpu_key(self) -> int:
        """Parent GPU key."""
        return int(self.get("gpu_key", 0))

    @property
    def gpu_name(self) -> str:
        """Parent GPU name."""
        return str(self.get("gpu_name", ""))

    @property
    def node_key(self) -> int | None:
        """Node key."""
        node = self.get("node_key")
        return int(node) if node else None

    @property
    def node_name(self) -> str:
        """Node name."""
        return str(self.get("node_display", ""))

    @property
    def machine_key(self) -> int | None:
        """Machine (VM) key."""
        machine = self.get("machine_key")
        return int(machine) if machine else None

    @property
    def machine_name(self) -> str:
        """Machine (VM) name."""
        return str(self.get("machine_name", ""))

    @property
    def machine_type(self) -> str:
        """Machine type (e.g., 'vm')."""
        return str(self.get("machine_type", ""))

    @property
    def machine_type_display(self) -> str:
        """Machine type display name."""
        return str(self.get("machine_type_display", ""))

    @property
    def machine_device_key(self) -> int | None:
        """Machine device key."""
        device = self.get("machine_device_key")
        return int(device) if device else None

    @property
    def machine_device_name(self) -> str:
        """Machine device name."""
        return str(self.get("machine_device_name", ""))

    @property
    def machine_device_status(self) -> str:
        """Machine device status."""
        return str(self.get("machine_device_status", ""))

    @property
    def pci_device_key(self) -> int | None:
        """PCI device key."""
        pci = self.get("pci_device_key")
        return int(pci) if pci else None

    @property
    def pci_device_name(self) -> str:
        """PCI device name."""
        return str(self.get("pci_device_name", ""))

    @property
    def mode(self) -> str:
        """GPU mode (gpu, nvidia_vgpu)."""
        return str(self.get("mode", ""))

    @property
    def mode_display(self) -> str:
        """GPU mode display name."""
        return str(self.get("mode_display", ""))

    @property
    def description(self) -> str:
        """Instance description."""
        return str(self.get("description", ""))

    @property
    def modified_at(self) -> datetime | None:
        """Timestamp when instance was last modified."""
        ts = self.get("modified")
        if ts:
            return datetime.fromtimestamp(int(ts), tz=timezone.utc)
        return None

    def __repr__(self) -> str:
        return (
            f"<NodeGpuInstance key={self.get('$key', '?')} "
            f"gpu={self.gpu_name!r} machine={self.machine_name!r}>"
        )


class NodeGpuInstanceManager(ResourceManager[NodeGpuInstance]):
    """Manager for node GPU instances.

    Provides read-only access to GPU instances assigned to VMs.
    Scoped to a specific GPU.

    Example:
        >>> # List instances for a GPU
        >>> for inst in gpu.instances.list():
        ...     print(f"VM: {inst.machine_name} ({inst.machine_device_status})")
    """

    _endpoint = "node_gpu_instances"

    _default_fields = [
        "$key",
        "gpu#$key as gpu_key",
        "gpu#name as gpu_name",
        "gpu#node#$key as node_key",
        "gpu#node#$display as node_display",
        "gpu#mode as mode",
        "gpu#display(mode) as mode_display",
        "gpu#pci_device#$key as pci_device_key",
        "gpu#pci_device#name as pci_device_name",
        "machine_device#$key as machine_device_key",
        "machine_device#name as machine_device_name",
        "machine_device#machine#$key as machine_key",
        "machine_device#machine#name as machine_name",
        "machine_device#machine#type as machine_type",
        "machine_device#machine#display(type) as machine_type_display",
        "machine_device#status#status as machine_device_status",
        "description",
        "modified",
    ]

    def __init__(self, client: VergeClient, gpu_key: int) -> None:
        super().__init__(client)
        self._gpu_key = gpu_key

    def _to_model(self, data: dict[str, Any]) -> NodeGpuInstance:
        return NodeGpuInstance(data, self)

    def list(
        self,
        filter: str | None = None,  # noqa: A002
        fields: builtins.list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        **filter_kwargs: Any,
    ) -> builtins.list[NodeGpuInstance]:
        """List GPU instances.

        Args:
            filter: OData filter string.
            fields: List of fields to return.
            limit: Maximum number of results.
            offset: Skip this many results.
            **filter_kwargs: Additional filter arguments.

        Returns:
            List of NodeGpuInstance objects.
        """
        if fields is None:
            fields = self._default_fields

        filters = [f"gpu eq {self._gpu_key}"]

        if filter:
            filters.append(filter)

        if filter_kwargs:
            filters.append(build_filter(**filter_kwargs))

        params: dict[str, Any] = {
            "filter": " and ".join(filters),
            "fields": ",".join(fields),
        }

        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset

        response = self._client._request("GET", self._endpoint, params=params)

        if response is None:
            return []

        if isinstance(response, list):
            return [self._to_model(item) for item in response]

        return [self._to_model(response)]


# =============================================================================
# Node vGPU Devices (Physical vGPU-capable devices)
# =============================================================================


class NodeVgpuDevice(ResourceObject):
    """Node vGPU device resource object.

    Represents a physical NVIDIA vGPU-capable device on a node.
    These are detected automatically by the system.
    """

    @property
    def node_key(self) -> int | None:
        """Parent node key."""
        node = self.get("node")
        return int(node) if node else None

    @property
    def node_name(self) -> str:
        """Parent node name."""
        return str(self.get("node_name", ""))

    @property
    def pci_device_key(self) -> int | None:
        """Associated PCI device key."""
        pci = self.get("pci_device")
        return int(pci) if pci else None

    @property
    def name(self) -> str:
        """Device name."""
        return str(self.get("name", ""))

    @property
    def slot(self) -> str:
        """PCI slot."""
        return str(self.get("slot", ""))

    @property
    def vendor(self) -> str:
        """Vendor name."""
        return str(self.get("vendor", ""))

    @property
    def device(self) -> str:
        """Device description."""
        return str(self.get("device", ""))

    @property
    def vendor_device_hex(self) -> str:
        """Vendor:device ID in hexadecimal."""
        return str(self.get("vendor_device_hex", ""))

    @property
    def driver(self) -> str:
        """Current driver."""
        return str(self.get("driver", ""))

    @property
    def module(self) -> str:
        """Kernel module."""
        return str(self.get("module", ""))

    @property
    def numa_node(self) -> str:
        """NUMA node."""
        return str(self.get("numa", ""))

    @property
    def iommu_group(self) -> str:
        """IOMMU group."""
        return str(self.get("iommu_group", ""))

    @property
    def type_id(self) -> int:
        """Device type ID."""
        return int(self.get("type_id", 0))

    @property
    def max_instances(self) -> int:
        """Maximum vGPU instances."""
        return int(self.get("max_instances", 1))

    @property
    def physical_function(self) -> str:
        """Physical function (for SR-IOV)."""
        return str(self.get("physical_function", ""))

    @property
    def virtual_function(self) -> str:
        """Virtual function identifier."""
        return str(self.get("virtfn", ""))

    @property
    def fingerprint(self) -> str:
        """Device fingerprint for live migration."""
        return str(self.get("fingerprint", ""))

    @property
    def created_at(self) -> datetime | None:
        """Timestamp when device was detected."""
        ts = self.get("created")
        if ts:
            return datetime.fromtimestamp(int(ts), tz=timezone.utc)
        return None

    @property
    def modified_at(self) -> datetime | None:
        """Timestamp when device was last updated."""
        ts = self.get("modified")
        if ts:
            return datetime.fromtimestamp(int(ts), tz=timezone.utc)
        return None

    def __repr__(self) -> str:
        return f"<NodeVgpuDevice key={self.get('$key', '?')} name={self.name!r} slot={self.slot!r}>"


class NodeVgpuDeviceManager(ResourceManager[NodeVgpuDevice]):
    """Manager for node vGPU device operations.

    Provides read-only access to NVIDIA vGPU-capable devices on nodes.
    Can be used globally or scoped to a specific node.

    Example:
        >>> # List all vGPU devices on a node
        >>> for device in node.vgpu_devices.list():
        ...     print(f"{device.name}: {device.vendor} {device.device}")

        >>> # List all vGPU devices across all nodes
        >>> for device in client.nodes.all_vgpu_devices.list():
        ...     print(f"{device.node_name}: {device.name}")
    """

    _endpoint = "node_nvidia_vgpu_devices"

    _default_fields = [
        "$key",
        "node",
        "node#name as node_name",
        "pci_device",
        "name",
        "slot",
        "vendor",
        "device",
        "vendor_device_hex",
        "driver",
        "module",
        "numa",
        "iommu_group",
        "type_id",
        "max_instances",
        "physical_function",
        "virtfn",
        "fingerprint",
        "created",
        "modified",
    ]

    def __init__(self, client: VergeClient, node_key: int | None = None) -> None:
        super().__init__(client)
        self._node_key = node_key

    def _to_model(self, data: dict[str, Any]) -> NodeVgpuDevice:
        return NodeVgpuDevice(data, self)

    def list(
        self,
        filter: str | None = None,  # noqa: A002
        fields: builtins.list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        *,
        vendor: str | None = None,
        **filter_kwargs: Any,
    ) -> builtins.list[NodeVgpuDevice]:
        """List vGPU-capable devices.

        Args:
            filter: OData filter string.
            fields: List of fields to return.
            limit: Maximum number of results.
            offset: Skip this many results.
            vendor: Filter by vendor name (contains).
            **filter_kwargs: Additional filter arguments.

        Returns:
            List of NodeVgpuDevice objects.
        """
        if fields is None:
            fields = self._default_fields

        filters = []

        if filter:
            filters.append(filter)

        if self._node_key is not None:
            filters.append(f"node eq {self._node_key}")

        if vendor is not None:
            escaped = vendor.replace("'", "''")
            filters.append(f"vendor ct '{escaped}'")

        if filter_kwargs:
            filters.append(build_filter(**filter_kwargs))

        params: dict[str, Any] = {"fields": ",".join(fields)}

        if filters:
            params["filter"] = " and ".join(filters)
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset

        response = self._client._request("GET", self._endpoint, params=params)

        if response is None:
            return []

        if isinstance(response, list):
            return [self._to_model(item) for item in response]

        return [self._to_model(response)]

    def get(  # type: ignore[override]
        self,
        key: int,
        *,
        fields: builtins.list[str] | None = None,
    ) -> NodeVgpuDevice:
        """Get a vGPU device by key.

        Args:
            key: Device $key (ID).
            fields: List of fields to return.

        Returns:
            NodeVgpuDevice object.

        Raises:
            NotFoundError: If device not found.
        """
        if fields is None:
            fields = self._default_fields

        params: dict[str, Any] = {"fields": ",".join(fields)}
        response = self._client._request("GET", f"{self._endpoint}/{key}", params=params)
        if response is None:
            raise NotFoundError(f"vGPU device with key {key} not found")
        if not isinstance(response, dict):
            raise NotFoundError(f"vGPU device with key {key} returned invalid response")
        return self._to_model(response)


# =============================================================================
# Node Host GPU Devices (Physical GPUs for passthrough)
# =============================================================================


class NodeHostGpuDevice(ResourceObject):
    """Node host GPU device resource object.

    Represents a physical GPU device available for host GPU passthrough.
    These are detected automatically by the system.
    """

    @property
    def node_key(self) -> int | None:
        """Parent node key."""
        node = self.get("node")
        return int(node) if node else None

    @property
    def node_name(self) -> str:
        """Parent node name."""
        return str(self.get("node_name", ""))

    @property
    def pci_device_key(self) -> int | None:
        """Associated PCI device key."""
        pci = self.get("pci_device")
        return int(pci) if pci else None

    @property
    def name(self) -> str:
        """Device name."""
        return str(self.get("name", ""))

    @property
    def slot(self) -> str:
        """PCI slot."""
        return str(self.get("slot", ""))

    @property
    def vendor(self) -> str:
        """Vendor name."""
        return str(self.get("vendor", ""))

    @property
    def device(self) -> str:
        """Device description."""
        return str(self.get("device", ""))

    @property
    def vendor_device_hex(self) -> str:
        """Vendor:device ID in hexadecimal."""
        return str(self.get("vendor_device_hex", ""))

    @property
    def driver(self) -> str:
        """Current driver."""
        return str(self.get("driver", ""))

    @property
    def module(self) -> str:
        """Kernel module."""
        return str(self.get("module", ""))

    @property
    def numa_node(self) -> str:
        """NUMA node."""
        return str(self.get("numa", ""))

    @property
    def iommu_group(self) -> str:
        """IOMMU group."""
        return str(self.get("iommu_group", ""))

    @property
    def type_id(self) -> int:
        """Device type ID."""
        return int(self.get("type_id", 0))

    @property
    def device_index(self) -> int:
        """Device index."""
        return int(self.get("device_index", 0))

    @property
    def max_instances(self) -> int:
        """Maximum instances (typically 1 for passthrough)."""
        return int(self.get("max_instances", 1))

    @property
    def fingerprint(self) -> str:
        """Device fingerprint for live migration."""
        return str(self.get("fingerprint", ""))

    @property
    def created_at(self) -> datetime | None:
        """Timestamp when device was detected."""
        ts = self.get("created")
        if ts:
            return datetime.fromtimestamp(int(ts), tz=timezone.utc)
        return None

    @property
    def modified_at(self) -> datetime | None:
        """Timestamp when device was last updated."""
        ts = self.get("modified")
        if ts:
            return datetime.fromtimestamp(int(ts), tz=timezone.utc)
        return None

    def __repr__(self) -> str:
        return (
            f"<NodeHostGpuDevice key={self.get('$key', '?')} name={self.name!r} slot={self.slot!r}>"
        )


class NodeHostGpuDeviceManager(ResourceManager[NodeHostGpuDevice]):
    """Manager for node host GPU device operations.

    Provides read-only access to GPUs available for host passthrough on nodes.
    Can be used globally or scoped to a specific node.

    Example:
        >>> # List all host GPUs on a node
        >>> for device in node.host_gpu_devices.list():
        ...     print(f"{device.name}: {device.vendor} {device.device}")

        >>> # List all host GPUs across all nodes
        >>> for device in client.nodes.all_host_gpu_devices.list():
        ...     print(f"{device.node_name}: {device.name}")
    """

    _endpoint = "node_host_gpu_devices"

    _default_fields = [
        "$key",
        "node",
        "node#name as node_name",
        "pci_device",
        "name",
        "slot",
        "vendor",
        "device",
        "vendor_device_hex",
        "driver",
        "module",
        "numa",
        "iommu_group",
        "type_id",
        "device_index",
        "max_instances",
        "fingerprint",
        "created",
        "modified",
    ]

    def __init__(self, client: VergeClient, node_key: int | None = None) -> None:
        super().__init__(client)
        self._node_key = node_key

    def _to_model(self, data: dict[str, Any]) -> NodeHostGpuDevice:
        return NodeHostGpuDevice(data, self)

    def list(
        self,
        filter: str | None = None,  # noqa: A002
        fields: builtins.list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        *,
        vendor: str | None = None,
        **filter_kwargs: Any,
    ) -> builtins.list[NodeHostGpuDevice]:
        """List host GPU devices.

        Args:
            filter: OData filter string.
            fields: List of fields to return.
            limit: Maximum number of results.
            offset: Skip this many results.
            vendor: Filter by vendor name (contains).
            **filter_kwargs: Additional filter arguments.

        Returns:
            List of NodeHostGpuDevice objects.
        """
        if fields is None:
            fields = self._default_fields

        filters = []

        if filter:
            filters.append(filter)

        if self._node_key is not None:
            filters.append(f"node eq {self._node_key}")

        if vendor is not None:
            escaped = vendor.replace("'", "''")
            filters.append(f"vendor ct '{escaped}'")

        if filter_kwargs:
            filters.append(build_filter(**filter_kwargs))

        params: dict[str, Any] = {"fields": ",".join(fields)}

        if filters:
            params["filter"] = " and ".join(filters)
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset

        response = self._client._request("GET", self._endpoint, params=params)

        if response is None:
            return []

        if isinstance(response, list):
            return [self._to_model(item) for item in response]

        return [self._to_model(response)]

    def get(  # type: ignore[override]
        self,
        key: int,
        *,
        fields: builtins.list[str] | None = None,
    ) -> NodeHostGpuDevice:
        """Get a host GPU device by key.

        Args:
            key: Device $key (ID).
            fields: List of fields to return.

        Returns:
            NodeHostGpuDevice object.

        Raises:
            NotFoundError: If device not found.
        """
        if fields is None:
            fields = self._default_fields

        params: dict[str, Any] = {"fields": ",".join(fields)}
        response = self._client._request("GET", f"{self._endpoint}/{key}", params=params)
        if response is None:
            raise NotFoundError(f"Host GPU device with key {key} not found")
        if not isinstance(response, dict):
            raise NotFoundError(f"Host GPU device with key {key} returned invalid response")
        return self._to_model(response)


# =============================================================================
# Node vGPU Profiles (Per-node available profiles)
# =============================================================================


class NodeVgpuProfile(ResourceObject):
    """Node vGPU profile resource object.

    Represents a vGPU profile available on a specific node's physical GPU.
    These are determined by the physical hardware and NVIDIA drivers.
    """

    @property
    def physical_gpu_key(self) -> int | None:
        """Associated physical GPU (PCI device) key."""
        pci = self.get("physical_gpu")
        return int(pci) if pci else None

    @property
    def name(self) -> str:
        """Profile name (e.g., 'nvidia-256')."""
        return str(self.get("name", ""))

    @property
    def num_heads(self) -> int:
        """Number of display heads."""
        return int(self.get("num_heads", 0))

    @property
    def frl_config(self) -> int:
        """Frame rate limiter configuration."""
        return int(self.get("frl_config", 0))

    @property
    def framebuffer(self) -> str:
        """Framebuffer (VRAM) size."""
        return str(self.get("framebuffer", ""))

    @property
    def max_resolution(self) -> str:
        """Maximum resolution."""
        return str(self.get("max_resolution", ""))

    @property
    def max_instance(self) -> int:
        """Maximum instances per GPU."""
        return int(self.get("max_instance", 0))

    @property
    def available_instances(self) -> int:
        """Currently available instances."""
        return int(self.get("available_instances", 0))

    @property
    def device_api(self) -> str:
        """Device API version."""
        return str(self.get("device_api", ""))

    @property
    def profile_type(self) -> str:
        """Profile type code (A, B, C, Q)."""
        return str(self.get("profile_type", ""))

    @property
    def profile_type_display(self) -> str:
        """Human-readable profile type."""
        return PROFILE_TYPE_DISPLAY.get(self.profile_type, self.profile_type)

    @property
    def is_virtual_function(self) -> bool:
        """Whether this is a virtual function profile."""
        return bool(self.get("virtual_function", False))

    @property
    def profile_folder(self) -> str:
        """Profile folder path."""
        return str(self.get("profile_folder", ""))

    def __repr__(self) -> str:
        return (
            f"<NodeVgpuProfile key={self.get('$key', '?')} "
            f"name={self.name!r} avail={self.available_instances}/{self.max_instance}>"
        )


class NodeVgpuProfileManager(ResourceManager[NodeVgpuProfile]):
    """Manager for node vGPU profile operations.

    Provides read-only access to vGPU profiles available on a specific node.
    These are determined by the physical hardware.

    Example:
        >>> # List profiles available on a node's GPU
        >>> for profile in node.vgpu_profiles.list():
        ...     print(f"{profile.name}: {profile.available_instances} available")
    """

    _endpoint = "node_nvidia_vgpu_profiles"

    _default_fields = [
        "$key",
        "physical_gpu",
        "name",
        "num_heads",
        "frl_config",
        "framebuffer",
        "max_resolution",
        "max_instance",
        "available_instances",
        "device_api",
        "profile_type",
        "virtual_function",
        "profile_folder",
    ]

    def __init__(self, client: VergeClient, physical_gpu_key: int | None = None) -> None:
        super().__init__(client)
        self._physical_gpu_key = physical_gpu_key

    def _to_model(self, data: dict[str, Any]) -> NodeVgpuProfile:
        return NodeVgpuProfile(data, self)

    def list(
        self,
        filter: str | None = None,  # noqa: A002
        fields: builtins.list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        *,
        profile_type: Literal["A", "B", "C", "Q"] | None = None,
        **filter_kwargs: Any,
    ) -> builtins.list[NodeVgpuProfile]:
        """List vGPU profiles.

        Args:
            filter: OData filter string.
            fields: List of fields to return.
            limit: Maximum number of results.
            offset: Skip this many results.
            profile_type: Filter by profile type.
            **filter_kwargs: Additional filter arguments.

        Returns:
            List of NodeVgpuProfile objects.
        """
        if fields is None:
            fields = self._default_fields

        filters = []

        if filter:
            filters.append(filter)

        if self._physical_gpu_key is not None:
            filters.append(f"physical_gpu eq {self._physical_gpu_key}")

        if profile_type is not None:
            filters.append(f"profile_type eq '{profile_type}'")

        if filter_kwargs:
            filters.append(build_filter(**filter_kwargs))

        params: dict[str, Any] = {"fields": ",".join(fields)}

        if filters:
            params["filter"] = " and ".join(filters)
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset

        response = self._client._request("GET", self._endpoint, params=params)

        if response is None:
            return []

        if isinstance(response, list):
            return [self._to_model(item) for item in response]

        return [self._to_model(response)]

    def get(
        self,
        key: int | None = None,
        *,
        name: str | None = None,
        fields: builtins.list[str] | None = None,
    ) -> NodeVgpuProfile:
        """Get a vGPU profile by key or name.

        Args:
            key: Profile $key (ID).
            name: Profile name.
            fields: List of fields to return.

        Returns:
            NodeVgpuProfile object.

        Raises:
            NotFoundError: If profile not found.
            ValueError: If neither key nor name provided.
        """
        if fields is None:
            fields = self._default_fields

        if key is not None:
            params: dict[str, Any] = {"fields": ",".join(fields)}
            response = self._client._request("GET", f"{self._endpoint}/{key}", params=params)
            if response is None:
                raise NotFoundError(f"vGPU profile with key {key} not found")
            if not isinstance(response, dict):
                raise NotFoundError(f"vGPU profile with key {key} returned invalid response")
            return self._to_model(response)

        if name is not None:
            escaped = name.replace("'", "''")
            results = self.list(filter=f"name eq '{escaped}'", fields=fields, limit=1)
            if not results:
                raise NotFoundError(f"vGPU profile with name '{name}' not found")
            return results[0]

        raise ValueError("Either key or name must be provided")
