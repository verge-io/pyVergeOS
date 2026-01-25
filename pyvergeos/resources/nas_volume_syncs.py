"""NAS volume sync resources."""

from __future__ import annotations

import builtins
from typing import TYPE_CHECKING, Any

from pyvergeos.exceptions import NotFoundError
from pyvergeos.filters import build_filter
from pyvergeos.resources.base import ResourceManager, ResourceObject

if TYPE_CHECKING:
    from pyvergeos.client import VergeClient


class NASVolumeSync(ResourceObject):
    """NAS volume sync resource object.

    Represents a volume synchronization job that copies data between NAS volumes.

    Attributes:
        key: The sync job unique identifier ($key).
        id: The sync job ID (same as key).
        name: Sync job name.
        description: Sync job description.
        enabled: Whether the sync is enabled.
        service: Parent NAS service key.
        source_volume: Source volume key.
        source_path: Starting directory in source volume.
        destination_volume: Destination volume key.
        destination_path: Destination directory path.
        include: File/directory patterns to include.
        exclude: File/directory patterns to exclude.
        sync_method: Sync method (rsync or ysync).
        destination_delete: How to handle deleted files.
        workers: Number of simultaneous workers.
        preserve_ACLs: Preserve access control lists.
        preserve_permissions: Preserve file permissions.
        preserve_owner: Preserve file owner.
        preserve_groups: Preserve file groups.
        preserve_mod_time: Preserve modification time.
        preserve_xattrs: Preserve extended attributes.
        copy_symlinks: Copy symbolic links.
        fsfreeze: Freeze filesystem before snapshot.
        status: Current sync status.
        syncing: Whether sync is currently running.
        files_transferred: Number of files transferred.
        bytes_transferred: Number of bytes transferred.
        transfer_rate: Current transfer rate.
        sync_errors: Number of sync errors.
        start_time: Sync start time.
        stop_time: Sync stop time.
        created: Creation timestamp.
        modified: Last modified timestamp.
    """

    @property
    def key(self) -> str:  # type: ignore[override]
        """Resource primary key ($key).

        Note:
            Volume sync keys are typically strings.

        Raises:
            ValueError: If resource has no $key (not yet persisted).
        """
        k = self.get("$key") or self.get("id")
        if k is None:
            raise ValueError("Resource has no $key - may not be persisted")
        return str(k)

    def refresh(self) -> NASVolumeSync:
        """Refresh resource data from API.

        Returns:
            Updated NASVolumeSync object.
        """
        from typing import cast

        manager = cast("NASVolumeSyncManager", self._manager)
        return manager.get(self.key)

    def save(self, **kwargs: Any) -> NASVolumeSync:
        """Save changes to resource.

        Args:
            **kwargs: Fields to update.

        Returns:
            Updated NASVolumeSync object.
        """
        from typing import cast

        manager = cast("NASVolumeSyncManager", self._manager)
        return manager.update(self.key, **kwargs)

    def delete(self) -> None:
        """Delete this sync job."""
        from typing import cast

        manager = cast("NASVolumeSyncManager", self._manager)
        manager.delete(self.key)

    def start(self) -> None:
        """Start this sync job."""
        from typing import cast

        manager = cast("NASVolumeSyncManager", self._manager)
        manager.start(self.key)

    def stop(self) -> None:
        """Stop this sync job."""
        from typing import cast

        manager = cast("NASVolumeSyncManager", self._manager)
        manager.stop(self.key)

    @property
    def is_syncing(self) -> bool:
        """Check if the sync is currently running."""
        return bool(self.get("syncing", False))

    @property
    def service_key(self) -> int | None:
        """Get the parent NAS service key."""
        service = self.get("service")
        return int(service) if service is not None else None

    @property
    def source_volume_key(self) -> str | None:
        """Get the source volume key."""
        vol = self.get("source_volume")
        return str(vol) if vol is not None else None

    @property
    def destination_volume_key(self) -> str | None:
        """Get the destination volume key."""
        vol = self.get("destination_volume")
        return str(vol) if vol is not None else None

    @property
    def sync_method_display(self) -> str:
        """Get human-readable sync method."""
        method = str(self.get("sync_method", ""))
        method_map = {
            "rsync": "rsync",
            "ysync": "Verge.io sync",
        }
        return method_map.get(method, method)

    @property
    def destination_delete_display(self) -> str:
        """Get human-readable destination delete mode."""
        mode = str(self.get("destination_delete", ""))
        mode_map = {
            "never": "Never delete",
            "delete": "Delete files from destination",
            "delete-before": "Delete before transfer",
            "delete-during": "Delete during transfer",
            "delete-delay": "Delete after transfer (find during)",
            "delete-after": "Delete after transfer",
        }
        return mode_map.get(mode, mode)

    @property
    def status_display(self) -> str:
        """Get human-readable status."""
        status = str(self.get("status", ""))
        status_map = {
            "complete": "Complete",
            "offline": "Offline",
            "syncing": "Syncing",
            "aborted": "Aborted",
            "error": "Error",
            "warning": "Warning",
        }
        return status_map.get(status, status)


class NASVolumeSyncManager(ResourceManager["NASVolumeSync"]):
    """Manager for NAS volume sync operations.

    Volume syncs copy data between NAS volumes on a schedule or on-demand.

    Example:
        >>> # List all volume syncs
        >>> for sync in client.volume_syncs.list():
        ...     print(f"{sync.name}: {sync.status_display}")

        >>> # Get a specific sync
        >>> sync = client.volume_syncs.get(name="DailyBackup")

        >>> # Create a sync job
        >>> sync = client.volume_syncs.create(
        ...     name="DailyBackup",
        ...     service=1,
        ...     source_volume="8f73...",
        ...     destination_volume="9a84...",
        ... )

        >>> # Start a sync
        >>> client.volume_syncs.start(sync.key)

        >>> # Stop a running sync
        >>> client.volume_syncs.stop(sync.key)
    """

    _endpoint = "volume_syncs"
    _actions_endpoint = "volume_sync_actions"

    # Default fields for list operations
    _default_fields = [
        "$key",
        "id",
        "name",
        "description",
        "enabled",
        "created",
        "modified",
        "service",
        "service#name as service_name",
        "service#vm#$display as service_vm",
        "source_volume",
        "source_volume#name as source_volume_name",
        "source_path",
        "destination_volume",
        "destination_volume#name as destination_volume_name",
        "destination_path",
        "include",
        "exclude",
        "sync_method",
        "destination_delete",
        "workers",
        "preserve_ACLs",
        "preserve_permissions",
        "preserve_owner",
        "preserve_groups",
        "preserve_mod_time",
        "preserve_xattrs",
        "copy_symlinks",
        "fsfreeze",
        "progress#status as status",
        "progress#syncing as syncing",
        "progress#files_transferred as files_transferred",
        "progress#bytes_transferred as bytes_transferred",
        "progress#transfer_rate as transfer_rate",
        "progress#sync_errors as sync_errors",
        "progress#start_time as start_time",
        "progress#stop_time as stop_time",
    ]

    def __init__(self, client: VergeClient) -> None:
        super().__init__(client)

    def list(
        self,
        filter: str | None = None,
        fields: builtins.list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        service: int | str | None = None,
        enabled: bool | None = None,
        **filter_kwargs: Any,
    ) -> builtins.list[NASVolumeSync]:
        """List volume sync jobs with optional filtering.

        Args:
            filter: OData filter string.
            fields: List of fields to return (uses defaults if not specified).
            limit: Maximum number of results.
            offset: Skip this many results.
            service: Filter by NAS service (key or name).
            enabled: Filter by enabled state.
            **filter_kwargs: Shorthand filter arguments (name, etc.).

        Returns:
            List of NASVolumeSync objects.

        Example:
            >>> # List all syncs
            >>> syncs = client.volume_syncs.list()

            >>> # List syncs for a specific NAS service
            >>> syncs = client.volume_syncs.list(service="NAS01")

            >>> # List enabled syncs only
            >>> syncs = client.volume_syncs.list(enabled=True)

            >>> # Filter by name
            >>> syncs = client.volume_syncs.list(name="DailyBackup")
        """
        params: dict[str, Any] = {}

        # Build filter
        filters: builtins.list[str] = []
        if filter:
            filters.append(filter)
        if filter_kwargs:
            filters.append(build_filter(**filter_kwargs))

        # Add service filter
        if service is not None:
            if isinstance(service, int):
                filters.append(f"service eq {service}")
            elif isinstance(service, str):
                # Look up service by name
                svc_response = self._client._request(
                    "GET",
                    "vm_services",
                    params={"filter": f"name eq '{service}'", "fields": "$key", "limit": "1"},
                )
                if svc_response:
                    if isinstance(svc_response, list):
                        svc_response = svc_response[0] if svc_response else None
                    if svc_response:
                        filters.append(f"service eq {svc_response.get('$key')}")

        # Add enabled filter
        if enabled is not None:
            filters.append(f"enabled eq {1 if enabled else 0}")

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
        key: str | None = None,
        *,
        name: str | None = None,
        service: int | str | None = None,
        fields: builtins.list[str] | None = None,
    ) -> NASVolumeSync:
        """Get a single volume sync by key or name.

        Args:
            key: Sync job key (ID).
            name: Sync job name.
            service: NAS service (key or name) to narrow name search.
            fields: List of fields to return.

        Returns:
            NASVolumeSync object.

        Raises:
            NotFoundError: If sync not found.
            ValueError: If no identifier provided.

        Example:
            >>> # Get by key
            >>> sync = client.volume_syncs.get("abc123")

            >>> # Get by name
            >>> sync = client.volume_syncs.get(name="DailyBackup")

            >>> # Get by name within specific NAS service
            >>> sync = client.volume_syncs.get(name="DailyBackup", service="NAS01")
        """
        if key is not None:
            # Fetch by key using id filter
            params: dict[str, Any] = {
                "filter": f"id eq '{key}'",
            }
            if fields:
                params["fields"] = ",".join(fields)
            else:
                params["fields"] = ",".join(self._default_fields)

            response = self._client._request("GET", self._endpoint, params=params)

            if response is None:
                raise NotFoundError(f"Volume sync with key {key} not found")
            if isinstance(response, list):
                if not response:
                    raise NotFoundError(f"Volume sync with key {key} not found")
                response = response[0]
            if not isinstance(response, dict):
                raise NotFoundError(f"Volume sync with key {key} returned invalid response")
            return self._to_model(response)

        if name is not None:
            # Search by name
            escaped_name = name.replace("'", "''")
            results = self.list(
                filter=f"name eq '{escaped_name}'",
                service=service,
                fields=fields,
                limit=1,
            )
            if not results:
                raise NotFoundError(f"Volume sync with name '{name}' not found")
            return results[0]

        raise ValueError("Either key or name must be provided")

    def create(  # type: ignore[override]
        self,
        name: str,
        service: int | str,
        source_volume: str,
        destination_volume: str,
        *,
        source_path: str | None = None,
        destination_path: str | None = None,
        description: str | None = None,
        include: builtins.list[str] | None = None,
        exclude: builtins.list[str] | None = None,
        sync_method: str = "ysync",
        destination_delete: str = "never",
        workers: int = 4,
        preserve_acls: bool = True,
        preserve_permissions: bool = True,
        preserve_owner: bool = True,
        preserve_groups: bool = True,
        preserve_mod_time: bool = True,
        preserve_xattrs: bool = True,
        copy_symlinks: bool = True,
        freeze_filesystem: bool = False,
        enabled: bool = True,
    ) -> NASVolumeSync:
        """Create a new volume sync job.

        Args:
            name: Name for the sync job.
            service: NAS service (key or name) to create the sync on.
            source_volume: Source volume key (40-char hex string).
            destination_volume: Destination volume key (40-char hex string).
            source_path: Starting directory in source volume.
            destination_path: Destination directory path.
            description: Sync job description.
            include: List of file/directory patterns to include.
            exclude: List of file/directory patterns to exclude.
            sync_method: Sync method - "rsync" or "ysync" (default: "ysync").
            destination_delete: How to handle deleted files.
                Valid values: "never", "delete", "delete-before",
                "delete-during", "delete-delay", "delete-after"
            workers: Number of simultaneous workers (1-128, default: 4).
            preserve_acls: Preserve access control lists (default: True).
            preserve_permissions: Preserve file permissions (default: True).
            preserve_owner: Preserve file owner (default: True).
            preserve_groups: Preserve file groups (default: True).
            preserve_mod_time: Preserve modification time (default: True).
            preserve_xattrs: Preserve extended attributes (default: True).
            copy_symlinks: Copy symbolic links (default: True).
            freeze_filesystem: Freeze filesystem before snapshot (default: False).
            enabled: Enable the sync job (default: True).

        Returns:
            Created NASVolumeSync object.

        Raises:
            ValueError: If NAS service not found.

        Example:
            >>> # Create a basic sync job
            >>> sync = client.volume_syncs.create(
            ...     name="DailyBackup",
            ...     service="NAS01",
            ...     source_volume="8f73f8bcc9c9f1aaba32f733bfc295acaf548554",
            ...     destination_volume="9a84e7add1d2c3b4a5e6f7890123456789abcdef",
            ... )

            >>> # Create with options
            >>> sync = client.volume_syncs.create(
            ...     name="SelectiveSync",
            ...     service=1,
            ...     source_volume=source_vol.key,
            ...     destination_volume=dest_vol.key,
            ...     include=["*.docx", "*.xlsx"],
            ...     exclude=["temp/*"],
            ...     workers=8,
            ... )
        """
        # Resolve NAS service to key
        service_key: int | None = None
        if isinstance(service, int):
            service_key = service
        elif isinstance(service, str):
            svc_response = self._client._request(
                "GET",
                "vm_services",
                params={"filter": f"name eq '{service}'", "fields": "$key,name", "limit": "1"},
            )
            if not svc_response:
                raise ValueError(f"NAS service '{service}' not found")
            if isinstance(svc_response, list):
                svc_response = svc_response[0] if svc_response else None
            if not svc_response:
                raise ValueError(f"NAS service '{service}' not found")
            service_key = svc_response.get("$key")

        if service_key is None:
            raise ValueError("Could not resolve NAS service key")

        # Map sync_method friendly names
        sync_method_map = {
            "rsync": "rsync",
            "ysync": "ysync",
            "vergesync": "ysync",
            "verge_sync": "ysync",
        }
        api_sync_method = sync_method_map.get(sync_method.lower(), sync_method)

        # Map destination_delete friendly names
        delete_map = {
            "never": "never",
            "delete": "delete",
            "delete-before": "delete-before",
            "delete_before": "delete-before",
            "deletebefore": "delete-before",
            "delete-during": "delete-during",
            "delete_during": "delete-during",
            "deleteduring": "delete-during",
            "delete-delay": "delete-delay",
            "delete_delay": "delete-delay",
            "deletedelay": "delete-delay",
            "delete-after": "delete-after",
            "delete_after": "delete-after",
            "deleteafter": "delete-after",
        }
        api_delete = delete_map.get(destination_delete.lower(), destination_delete)

        # Build request body
        body: dict[str, Any] = {
            "service": service_key,
            "name": name,
            "type": "volsync",
            "source_volume": source_volume,
            "destination_volume": destination_volume,
            "enabled": enabled,
            "sync_method": api_sync_method,
            "destination_delete": api_delete,
            "workers": workers,
            "preserve_ACLs": preserve_acls,
            "preserve_permissions": preserve_permissions,
            "preserve_owner": preserve_owner,
            "preserve_groups": preserve_groups,
            "preserve_mod_time": preserve_mod_time,
            "preserve_xattrs": preserve_xattrs,
            "copy_symlinks": copy_symlinks,
            "fsfreeze": freeze_filesystem,
        }

        if source_path is not None:
            body["source_path"] = source_path

        if destination_path is not None:
            body["destination_path"] = destination_path

        if description is not None:
            body["description"] = description

        if include:
            body["include"] = "\n".join(include)

        if exclude:
            body["exclude"] = "\n".join(exclude)

        response = self._client._request("POST", self._endpoint, json_data=body)

        # Get the created sync
        if response and isinstance(response, dict):
            sync_key = response.get("$key") or response.get("id")
            if sync_key:
                return self.get(key=sync_key)

        # Fallback: search by name
        return self.get(name=name, service=service_key)

    def update(  # type: ignore[override]
        self,
        key: str,
        *,
        description: str | None = None,
        source_path: str | None = None,
        destination_path: str | None = None,
        include: builtins.list[str] | None = None,
        exclude: builtins.list[str] | None = None,
        sync_method: str | None = None,
        destination_delete: str | None = None,
        workers: int | None = None,
        preserve_acls: bool | None = None,
        preserve_permissions: bool | None = None,
        preserve_owner: bool | None = None,
        preserve_groups: bool | None = None,
        preserve_mod_time: bool | None = None,
        preserve_xattrs: bool | None = None,
        copy_symlinks: bool | None = None,
        freeze_filesystem: bool | None = None,
        enabled: bool | None = None,
    ) -> NASVolumeSync:
        """Update a volume sync job.

        Args:
            key: Sync job key (ID).
            description: New description.
            source_path: New source path.
            destination_path: New destination path.
            include: New list of include patterns.
            exclude: New list of exclude patterns.
            sync_method: New sync method ("rsync" or "ysync").
            destination_delete: New delete mode.
            workers: New number of workers (1-128).
            preserve_acls: Preserve access control lists.
            preserve_permissions: Preserve file permissions.
            preserve_owner: Preserve file owner.
            preserve_groups: Preserve file groups.
            preserve_mod_time: Preserve modification time.
            preserve_xattrs: Preserve extended attributes.
            copy_symlinks: Copy symbolic links.
            freeze_filesystem: Freeze filesystem before snapshot.
            enabled: Enable or disable the sync job.

        Returns:
            Updated NASVolumeSync object.

        Example:
            >>> # Update workers
            >>> client.volume_syncs.update(sync.key, workers=8)

            >>> # Disable a sync
            >>> client.volume_syncs.update(sync.key, enabled=False)
        """
        body: dict[str, Any] = {}

        if description is not None:
            body["description"] = description

        if source_path is not None:
            body["source_path"] = source_path

        if destination_path is not None:
            body["destination_path"] = destination_path

        if include is not None:
            body["include"] = "\n".join(include) if include else ""

        if exclude is not None:
            body["exclude"] = "\n".join(exclude) if exclude else ""

        if sync_method is not None:
            sync_method_map = {
                "rsync": "rsync",
                "ysync": "ysync",
                "vergesync": "ysync",
                "verge_sync": "ysync",
            }
            body["sync_method"] = sync_method_map.get(sync_method.lower(), sync_method)

        if destination_delete is not None:
            delete_map = {
                "never": "never",
                "delete": "delete",
                "delete-before": "delete-before",
                "delete_before": "delete-before",
                "deletebefore": "delete-before",
                "delete-during": "delete-during",
                "delete_during": "delete-during",
                "deleteduring": "delete-during",
                "delete-delay": "delete-delay",
                "delete_delay": "delete-delay",
                "deletedelay": "delete-delay",
                "delete-after": "delete-after",
                "delete_after": "delete-after",
                "deleteafter": "delete-after",
            }
            body["destination_delete"] = delete_map.get(
                destination_delete.lower(), destination_delete
            )

        if workers is not None:
            body["workers"] = workers

        if preserve_acls is not None:
            body["preserve_ACLs"] = preserve_acls

        if preserve_permissions is not None:
            body["preserve_permissions"] = preserve_permissions

        if preserve_owner is not None:
            body["preserve_owner"] = preserve_owner

        if preserve_groups is not None:
            body["preserve_groups"] = preserve_groups

        if preserve_mod_time is not None:
            body["preserve_mod_time"] = preserve_mod_time

        if preserve_xattrs is not None:
            body["preserve_xattrs"] = preserve_xattrs

        if copy_symlinks is not None:
            body["copy_symlinks"] = copy_symlinks

        if freeze_filesystem is not None:
            body["fsfreeze"] = freeze_filesystem

        if enabled is not None:
            body["enabled"] = enabled

        if not body:
            return self.get(key)

        self._client._request("PUT", f"{self._endpoint}/{key}", json_data=body)
        return self.get(key)

    def delete(self, key: str) -> None:  # type: ignore[override]
        """Delete a volume sync job.

        This operation cannot be undone. Running syncs should be stopped first.

        Args:
            key: Sync job key (ID).

        Example:
            >>> client.volume_syncs.delete(sync.key)
        """
        self._client._request("DELETE", f"{self._endpoint}/{key}")

    def enable(self, key: str) -> NASVolumeSync:
        """Enable a volume sync job.

        Args:
            key: Sync job key (ID).

        Returns:
            Updated NASVolumeSync object.

        Example:
            >>> client.volume_syncs.enable(sync.key)
        """
        return self.update(key, enabled=True)

    def disable(self, key: str) -> NASVolumeSync:
        """Disable a volume sync job.

        Args:
            key: Sync job key (ID).

        Returns:
            Updated NASVolumeSync object.

        Example:
            >>> client.volume_syncs.disable(sync.key)
        """
        return self.update(key, enabled=False)

    def start(self, key: str) -> None:
        """Start a volume sync job.

        Initiates the synchronization process to copy data from source
        to destination volume.

        Args:
            key: Sync job key (ID).

        Example:
            >>> client.volume_syncs.start(sync.key)
        """
        body: dict[str, Any] = {
            "sync": key,
            "action": "start_sync",
        }
        self._client._request("POST", self._actions_endpoint, json_data=body)

    def stop(self, key: str) -> None:
        """Stop a running volume sync job.

        Aborts the synchronization process at its current progress point.

        Args:
            key: Sync job key (ID).

        Example:
            >>> client.volume_syncs.stop(sync.key)
        """
        body: dict[str, Any] = {
            "sync": key,
            "action": "stop_sync",
        }
        self._client._request("POST", self._actions_endpoint, json_data=body)

    def _to_model(self, data: dict[str, Any]) -> NASVolumeSync:
        """Convert API response to NASVolumeSync object."""
        return NASVolumeSync(data, self)
