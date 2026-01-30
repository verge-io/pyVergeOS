"""Volume VM export resources for exporting VMs to NAS volumes."""

from __future__ import annotations

import builtins
from typing import TYPE_CHECKING, Any

from pyvergeos.exceptions import NotFoundError
from pyvergeos.filters import build_filter
from pyvergeos.resources.base import ResourceManager, ResourceObject

if TYPE_CHECKING:
    from pyvergeos.client import VergeClient


class VolumeVmExport(ResourceObject):
    """Volume VM export resource object.

    Represents a VM export configuration for a NAS volume.
    VM exports allow exporting VMs to NAS volumes for backup/migration.

    Attributes:
        key: The export unique identifier ($key).
        volume: Parent NAS volume key.
        name: Volume name (derived from volume).
        quiesced: Whether exports are quiesced.
        status: Export status (idle, building, error, cleaning).
        status_info: Detailed status information.
        create_current: Whether to create 'current' folder with latest export.
        max_exports: Maximum exports to store (1-100).
    """

    @property
    def is_idle(self) -> bool:
        """Check if export is idle."""
        return self.get("status") == "idle"

    @property
    def is_building(self) -> bool:
        """Check if export is building."""
        return self.get("status") == "building"

    @property
    def has_error(self) -> bool:
        """Check if export has an error."""
        return self.get("status") == "error"

    @property
    def volume_key(self) -> int | None:
        """Get the parent volume key."""
        vol = self.get("volume")
        return int(vol) if vol is not None else None

    @property
    def stats(self) -> VolumeVmExportStatManager:
        """Get a stats manager for this export's statistics.

        Returns:
            VolumeVmExportStatManager scoped to this export.

        Example:
            >>> # Browse export stats
            >>> for stat in export.stats.list():
            ...     print(f"{stat.file_name}: {stat.virtual_machines} VMs")
        """
        from typing import cast

        manager = cast("VolumeVmExportManager", self._manager)
        return VolumeVmExportStatManager(manager._client, export_key=self.key)

    def start(
        self,
        name: str | None = None,
        vms: builtins.list[int] | None = None,
    ) -> dict[str, Any] | None:
        """Start an export operation.

        Args:
            name: Optional export name/folder name.
            vms: Optional list of VM keys to export. If not provided, exports all.

        Returns:
            Action result dict or None.
        """
        from typing import cast

        manager = cast("VolumeVmExportManager", self._manager)
        return manager.start_export(self.key, name=name, vms=vms)

    def stop(self) -> dict[str, Any] | None:
        """Stop an in-progress export operation.

        Returns:
            Action result dict or None.
        """
        from typing import cast

        manager = cast("VolumeVmExportManager", self._manager)
        return manager.stop_export(self.key)

    def cleanup(self) -> dict[str, Any] | None:
        """Clean up old export folders.

        Returns:
            Action result dict or None.
        """
        from typing import cast

        manager = cast("VolumeVmExportManager", self._manager)
        return manager.cleanup_exports(self.key)


class VolumeVmExportStat(ResourceObject):
    """Volume VM export statistics resource object.

    Represents statistics for a completed VM export.

    Attributes:
        key: The stat entry key ($key).
        volume_vm_exports: Parent export key.
        duration: Export duration in seconds.
        virtual_machines: Number of VMs exported.
        export_success: Number of successful exports.
        errors: Number of errors.
        quiesced: Whether the export was quiesced.
        size_bytes: Total size in bytes.
        file_name: Export folder name.
        timestamp: Export timestamp.
    """

    @property
    def size_gb(self) -> float:
        """Get the export size in GB."""
        size = self.get("size_bytes", 0)
        return round(size / 1073741824, 2) if size else 0

    @property
    def has_errors(self) -> bool:
        """Check if the export had errors."""
        errors = self.get("errors", 0)
        return int(errors) > 0 if errors else False


class VolumeVmExportManager(ResourceManager["VolumeVmExport"]):
    """Manager for volume VM export operations.

    Volume VM exports allow exporting VMs to NAS volumes for backup
    and migration purposes.

    Example:
        >>> # List all exports
        >>> for exp in client.volume_vm_exports.list():
        ...     print(f"{exp.name}: {exp.status}")

        >>> # Get export for a volume
        >>> exp = client.volume_vm_exports.get(volume=123)

        >>> # Start an export
        >>> exp.start(name="backup-2024")

        >>> # View export stats
        >>> for stat in exp.stats.list():
        ...     print(f"{stat.file_name}: {stat.size_gb}GB")
    """

    _endpoint = "volume_vm_exports"

    # Default fields for list operations
    _default_fields = [
        "$key",
        "volume",
        "volume#$display as volume_display",
        "volume#name as volume_name",
        "quiesced",
        "status",
        "status_info",
        "create_current",
        "max_exports",
    ]

    def __init__(self, client: VergeClient) -> None:
        super().__init__(client)

    def list(
        self,
        filter: str | None = None,
        fields: builtins.list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        status: str | None = None,
        volume: int | None = None,
        **filter_kwargs: Any,
    ) -> builtins.list[VolumeVmExport]:
        """List volume VM exports with optional filtering.

        Args:
            filter: OData filter string.
            fields: List of fields to return (uses defaults if not specified).
            limit: Maximum number of results.
            offset: Skip this many results.
            status: Filter by status (idle, building, error, cleaning).
            volume: Filter by volume key.
            **filter_kwargs: Shorthand filter arguments.

        Returns:
            List of VolumeVmExport objects.

        Example:
            >>> # List all exports
            >>> exports = client.volume_vm_exports.list()

            >>> # List active exports
            >>> active = client.volume_vm_exports.list(status="building")
        """
        params: dict[str, Any] = {}

        # Build filter
        filters: builtins.list[str] = []
        if filter:
            filters.append(filter)
        if filter_kwargs:
            filters.append(build_filter(**filter_kwargs))

        # Add status filter
        if status:
            filters.append(f"status eq '{status}'")

        # Add volume filter
        if volume is not None:
            filters.append(f"volume eq {volume}")

        if filters:
            params["filter"] = " and ".join(filters)

        # Use default fields if not specified
        if fields:
            params["fields"] = ",".join(fields)
        else:
            params["fields"] = ",".join(self._default_fields)

        # Pagination
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset

        response = self._client._request("GET", self._endpoint, params=params)

        if response is None:
            return []

        if not isinstance(response, list):
            response = [response]

        return [self._to_model(item) for item in response if item]

    def get(  # type: ignore[override]
        self,
        key: int | None = None,
        *,
        volume: int | None = None,
        fields: builtins.list[str] | None = None,
    ) -> VolumeVmExport:
        """Get a single volume VM export by key or volume.

        Args:
            key: Export $key (row ID).
            volume: Parent volume key (since there's one export per volume).
            fields: List of fields to return.

        Returns:
            VolumeVmExport object.

        Raises:
            NotFoundError: If export not found.
            ValueError: If no identifier provided.

        Example:
            >>> # Get by key
            >>> exp = client.volume_vm_exports.get(key=1)

            >>> # Get by volume
            >>> exp = client.volume_vm_exports.get(volume=123)
        """
        if key is not None:
            # Direct fetch by key
            params: dict[str, Any] = {}
            if fields:
                params["fields"] = ",".join(fields)
            else:
                params["fields"] = ",".join(self._default_fields)

            response = self._client._request("GET", f"{self._endpoint}/{key}", params=params)
            if response is None:
                raise NotFoundError(f"Volume VM export with key {key} not found")
            if not isinstance(response, dict):
                raise NotFoundError(f"Volume VM export with key {key} returned invalid response")
            return self._to_model(response)

        if volume is not None:
            # Search by volume
            results = self.list(filter=f"volume eq {volume}", fields=fields, limit=1)
            if not results:
                raise NotFoundError(f"Volume VM export for volume {volume} not found")
            return results[0]

        raise ValueError("Either key or volume must be provided")

    def create(  # type: ignore[override]
        self,
        volume: int,
        *,
        quiesced: bool = True,
        create_current: bool = True,
        max_exports: int = 3,
    ) -> VolumeVmExport:
        """Create a new volume VM export configuration.

        Args:
            volume: NAS volume key to export VMs to.
            quiesced: Whether to quiesce VMs during export (default True).
            create_current: Create 'current' folder with latest export (default True).
            max_exports: Maximum exports to store (1-100, default 3).

        Returns:
            Created VolumeVmExport object.

        Example:
            >>> exp = client.volume_vm_exports.create(
            ...     volume=123,
            ...     max_exports=5,
            ...     quiesced=True
            ... )
        """
        body: dict[str, Any] = {
            "volume": volume,
            "quiesced": quiesced,
            "create_current": create_current,
            "max_exports": max_exports,
        }

        response = self._client._request("POST", self._endpoint, json_data=body)

        # Get the created export
        if response and isinstance(response, dict):
            exp_key = response.get("$key")
            if exp_key:
                return self.get(key=exp_key)

        # Fallback: search by volume
        return self.get(volume=volume)

    def update(  # type: ignore[override]
        self,
        key: int,
        *,
        quiesced: bool | None = None,
        create_current: bool | None = None,
        max_exports: int | None = None,
    ) -> VolumeVmExport:
        """Update a volume VM export configuration.

        Args:
            key: Export $key (row ID).
            quiesced: Whether to quiesce VMs during export.
            create_current: Create 'current' folder with latest export.
            max_exports: Maximum exports to store (1-100).

        Returns:
            Updated VolumeVmExport object.
        """
        body: dict[str, Any] = {}

        if quiesced is not None:
            body["quiesced"] = quiesced

        if create_current is not None:
            body["create_current"] = create_current

        if max_exports is not None:
            body["max_exports"] = max_exports

        if not body:
            return self.get(key)

        self._client._request("PUT", f"{self._endpoint}/{key}", json_data=body)
        return self.get(key)

    def delete(self, key: int) -> None:
        """Delete a volume VM export configuration.

        Args:
            key: Export $key (row ID).

        Example:
            >>> client.volume_vm_exports.delete(1)
        """
        self._client._request("DELETE", f"{self._endpoint}/{key}")

    def start_export(
        self,
        key: int,
        name: str | None = None,
        vms: builtins.list[int] | None = None,
    ) -> dict[str, Any] | None:
        """Start a VM export operation.

        Args:
            key: Export $key (row ID).
            name: Optional export name/folder name.
            vms: Optional list of VM keys to export. If not provided, exports all.

        Returns:
            Action result dict or None.

        Example:
            >>> result = client.volume_vm_exports.start_export(1, name="backup-2024")
        """
        # Use the actions endpoint
        body: dict[str, Any] = {
            "volume_vm_export": key,
            "action": "start_export",
        }

        params: dict[str, Any] = {}
        if name is not None:
            params["name"] = name
        if vms is not None:
            params["vms"] = vms

        if params:
            body["params"] = params

        result = self._client._request("POST", "volume_vm_export_actions", json_data=body)
        if isinstance(result, dict):
            return result
        return None

    def stop_export(self, key: int) -> dict[str, Any] | None:
        """Stop an in-progress VM export operation.

        Args:
            key: Export $key (row ID).

        Returns:
            Action result dict or None.

        Example:
            >>> client.volume_vm_exports.stop_export(1)
        """
        body: dict[str, Any] = {
            "volume_vm_export": key,
            "action": "stop_export",
        }

        result = self._client._request("POST", "volume_vm_export_actions", json_data=body)
        if isinstance(result, dict):
            return result
        return None

    def cleanup_exports(self, key: int) -> dict[str, Any] | None:
        """Clean up old export folders.

        Args:
            key: Export $key (row ID).

        Returns:
            Action result dict or None.

        Example:
            >>> client.volume_vm_exports.cleanup_exports(1)
        """
        body: dict[str, Any] = {
            "volume_vm_export": key,
            "action": "cleanup",
        }

        result = self._client._request("POST", "volume_vm_export_actions", json_data=body)
        if isinstance(result, dict):
            return result
        return None

    def stats(self, key: int) -> VolumeVmExportStatManager:
        """Get a stats manager for a specific export.

        Args:
            key: Export $key (row ID).

        Returns:
            VolumeVmExportStatManager for the export.

        Example:
            >>> for stat in client.volume_vm_exports.stats(1).list():
            ...     print(f"{stat.file_name}: {stat.size_gb}GB")
        """
        return VolumeVmExportStatManager(self._client, export_key=key)

    def _to_model(self, data: dict[str, Any]) -> VolumeVmExport:
        """Convert API response to VolumeVmExport object."""
        return VolumeVmExport(data, self)


class VolumeVmExportStatManager(ResourceManager["VolumeVmExportStat"]):
    """Manager for volume VM export statistics.

    This manager provides access to export statistics.
    It can be used either standalone or scoped to a specific export.

    Example:
        >>> # List all export stats (standalone)
        >>> for stat in client.volume_vm_export_stats.list():
        ...     print(f"{stat.file_name}: {stat.size_gb}GB")

        >>> # List stats for a specific export
        >>> for stat in client.volume_vm_exports.stats(1).list():
        ...     print(f"{stat.file_name}: {stat.virtual_machines} VMs")
    """

    _endpoint = "volume_vm_export_stats"

    # Default fields for list operations
    _default_fields = [
        "$key",
        "volume_vm_exports",
        "duration",
        "virtual_machines",
        "export_success",
        "errors",
        "quiesced",
        "size_bytes",
        "file_name",
        "timestamp",
    ]

    def __init__(self, client: VergeClient, *, export_key: int | None = None) -> None:
        super().__init__(client)
        self._export_key = export_key

    def list(
        self,
        filter: str | None = None,
        fields: builtins.list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        volume_vm_exports: int | None = None,
        **filter_kwargs: Any,
    ) -> builtins.list[VolumeVmExportStat]:
        """List volume VM export statistics with optional filtering.

        Args:
            filter: OData filter string.
            fields: List of fields to return (uses defaults if not specified).
            limit: Maximum number of results.
            offset: Skip this many results.
            volume_vm_exports: Filter by export key. Ignored if manager is scoped.
            **filter_kwargs: Shorthand filter arguments.

        Returns:
            List of VolumeVmExportStat objects.

        Example:
            >>> # List all stats
            >>> stats = client.volume_vm_export_stats.list()

            >>> # List stats for a specific export
            >>> stats = client.volume_vm_exports.stats(1).list()
        """
        params: dict[str, Any] = {}

        # Build filter
        filters: builtins.list[str] = []
        if filter:
            filters.append(filter)
        if filter_kwargs:
            filters.append(build_filter(**filter_kwargs))

        # Add export filter (from scope or parameter)
        export_key = self._export_key
        if export_key is None and volume_vm_exports is not None:
            export_key = volume_vm_exports

        if export_key is not None:
            filters.append(f"volume_vm_exports eq {export_key}")

        if filters:
            params["filter"] = " and ".join(filters)

        # Use default fields if not specified
        if fields:
            params["fields"] = ",".join(fields)
        else:
            params["fields"] = ",".join(self._default_fields)

        # Pagination
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset

        response = self._client._request("GET", self._endpoint, params=params)

        if response is None:
            return []

        if not isinstance(response, list):
            response = [response]

        return [self._to_model(item) for item in response if item]

    def get(  # type: ignore[override]
        self,
        key: int | None = None,
        *,
        fields: builtins.list[str] | None = None,
    ) -> VolumeVmExportStat:
        """Get a single VM export stat by key.

        Args:
            key: Stat $key (row ID).
            fields: List of fields to return.

        Returns:
            VolumeVmExportStat object.

        Raises:
            NotFoundError: If stat not found.
            ValueError: If key not provided.

        Example:
            >>> stat = client.volume_vm_export_stats.get(1)
        """
        if key is not None:
            params: dict[str, Any] = {}
            if fields:
                params["fields"] = ",".join(fields)
            else:
                params["fields"] = ",".join(self._default_fields)

            response = self._client._request("GET", f"{self._endpoint}/{key}", params=params)
            if response is None:
                raise NotFoundError(f"Volume VM export stat with key {key} not found")
            if not isinstance(response, dict):
                raise NotFoundError(
                    f"Volume VM export stat with key {key} returned invalid response"
                )
            return self._to_model(response)

        raise ValueError("Key must be provided")

    def delete(self, key: int) -> None:
        """Delete a VM export stat entry.

        Args:
            key: Stat $key (row ID).

        Example:
            >>> client.volume_vm_export_stats.delete(1)
        """
        self._client._request("DELETE", f"{self._endpoint}/{key}")

    def _to_model(self, data: dict[str, Any]) -> VolumeVmExportStat:
        """Convert API response to VolumeVmExportStat object."""
        return VolumeVmExportStat(data, self)
