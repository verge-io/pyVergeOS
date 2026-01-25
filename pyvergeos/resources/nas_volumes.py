"""NAS volume and snapshot resources."""

from __future__ import annotations

import builtins
from typing import TYPE_CHECKING, Any

from pyvergeos.exceptions import NotFoundError
from pyvergeos.filters import build_filter
from pyvergeos.resources.base import ResourceManager, ResourceObject

if TYPE_CHECKING:
    from pyvergeos.client import VergeClient
    from pyvergeos.resources.nas_volume_browser import NASVolumeFileManager


class NASVolume(ResourceObject):
    """NAS volume resource object.

    Represents a NAS volume (virtual filesystem) managed by a NAS service.

    Note:
        Volume keys are 40-character hex strings, not integers like most
        other VergeOS resources.

    Attributes:
        key: The volume unique identifier ($key) - 40-char hex string.
        id: The volume ID (same as $key).
        name: Volume name.
        description: Volume description.
        enabled: Whether the volume is enabled.
        max_size: Maximum size in bytes.
        preferred_tier: Preferred storage tier (1-5).
        fs_type: Filesystem type (ext4, cifs, nfs, ybfs, verge_vm_export).
        read_only: Whether the volume is read-only.
        discard: Whether discard is enabled for deleted files.
        owner_user: Volume directory owner user.
        owner_group: Volume directory owner group.
        encrypt: Whether the volume is encrypted.
        automount_snapshots: Whether snapshots are auto-mounted.
        is_snapshot: Whether this is a snapshot volume.
        service: Parent NAS service key.
        snapshot_profile: Associated snapshot profile key.
        created: Creation timestamp.
        modified: Last modified timestamp.
    """

    @property
    def key(self) -> str:  # type: ignore[override]
        """Resource primary key ($key) - 40-character hex string.

        Raises:
            ValueError: If resource has no $key (not yet persisted).
        """
        k = self.get("$key")
        if k is None:
            raise ValueError("Resource has no $key - may not be persisted")
        return str(k)

    def refresh(self) -> NASVolume:
        """Refresh resource data from API.

        Returns:
            Updated NASVolume object.
        """
        from typing import cast

        manager = cast("NASVolumeManager", self._manager)
        return manager.get(self.key)

    def save(self, **kwargs: Any) -> NASVolume:
        """Save changes to resource.

        Args:
            **kwargs: Fields to update.

        Returns:
            Updated NASVolume object.
        """
        from typing import cast

        manager = cast("NASVolumeManager", self._manager)
        return manager.update(self.key, **kwargs)

    def delete(self) -> None:
        """Delete this volume."""
        from typing import cast

        manager = cast("NASVolumeManager", self._manager)
        manager.delete(self.key)

    @property
    def max_size_gb(self) -> float:
        """Get the maximum size in GB."""
        max_size = self.get("maxsize", 0)
        return round(max_size / 1073741824, 2) if max_size else 0

    @property
    def used_gb(self) -> float:
        """Get the used space in GB."""
        used = self.get("used_bytes", 0)
        return round(used / 1073741824, 2) if used else 0

    @property
    def allocated_gb(self) -> float:
        """Get the allocated space in GB."""
        allocated = self.get("allocated_bytes", 0)
        return round(allocated / 1073741824, 2) if allocated else 0

    @property
    def is_mounted(self) -> bool:
        """Check if the volume is mounted."""
        return self.get("mounted", False) or self.get("mount_status") == "mounted"

    @property
    def service_key(self) -> int | None:
        """Get the parent NAS service key."""
        service = self.get("service")
        return int(service) if service is not None else None

    @property
    def files(self) -> NASVolumeFileManager:
        """Get a file manager for browsing this volume's files.

        Returns:
            NASVolumeFileManager scoped to this volume.

        Example:
            >>> # Browse volume files
            >>> for f in volume.files.list():
            ...     print(f"{f.name}: {f.size_display}")

            >>> # Browse a subdirectory
            >>> for f in volume.files.list("/documents"):
            ...     print(f.name)
        """
        from typing import cast

        from pyvergeos.resources.nas_volume_browser import NASVolumeFileManager

        manager = cast("NASVolumeManager", self._manager)
        return NASVolumeFileManager(
            manager._client,
            volume_key=self.key,
            volume_name=self.get("name"),
        )


class NASVolumeSnapshot(ResourceObject):
    """NAS volume snapshot resource object.

    Represents a point-in-time snapshot of a NAS volume.

    Attributes:
        key: The snapshot unique identifier ($key).
        name: Snapshot name.
        description: Snapshot description.
        volume: Parent volume key.
        snap_volume: Mounted snapshot volume key (if mounted).
        created: Creation timestamp.
        expires: Expiration timestamp (0 for never expires).
        expires_type: Expiration type (never, date).
        enabled: Whether the snapshot is enabled.
        created_manually: Whether created manually.
        quiesce: Whether I/O was quiesced during creation.
    """

    @property
    def volume_key(self) -> str | None:
        """Get the parent volume key.

        Note: NAS volume keys are 40-character hex strings, not integers.
        """
        vol = self.get("volume")
        return str(vol) if vol is not None else None

    @property
    def never_expires(self) -> bool:
        """Check if the snapshot never expires."""
        return self.get("expires_type") == "never" or self.get("expires", 0) == 0


class NASVolumeManager(ResourceManager["NASVolume"]):
    """Manager for NAS volume operations.

    NAS volumes are virtual filesystems that can be shared via CIFS/SMB or NFS.

    Example:
        >>> # List all volumes
        >>> for volume in client.nas_volumes.list():
        ...     print(f"{volume.name}: {volume.max_size_gb}GB")

        >>> # Get a specific volume
        >>> vol = client.nas_volumes.get(name="FileShare")

        >>> # Create a volume
        >>> vol = client.nas_volumes.create(
        ...     name="DataShare",
        ...     service=1,
        ...     size_gb=500,
        ...     tier=1
        ... )

        >>> # Create a snapshot
        >>> snap = vol.snapshots.create("pre-update")
    """

    _endpoint = "volumes"

    # Default fields for list operations
    _default_fields = [
        "$key",
        "id",
        "name",
        "description",
        "enabled",
        "created",
        "modified",
        "maxsize",
        "preferred_tier",
        "fs_type",
        "read_only",
        "discard",
        "owner_user",
        "owner_group",
        "encrypt",
        "automount_snapshots",
        "is_snapshot",
        "note",
        "creator",
        "service",
        "service#$display as service_display",
        "service#vm#$display as nas_vm_display",
        "service#vm#machine#status#status as nas_status",
        "snapshot_profile",
        "snapshot_profile#$display as snapshot_profile_display",
        "status#status as mount_status",
        "status#mounted as mounted",
        "drive",
        "drive#media_source#used_bytes as used_bytes",
        "drive#media_source#filesize as allocated_bytes",
    ]

    def __init__(self, client: VergeClient) -> None:
        super().__init__(client)

    def list(
        self,
        filter: str | None = None,
        fields: builtins.list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        enabled: bool | None = None,
        fs_type: str | None = None,
        service: int | str | None = None,
        **filter_kwargs: Any,
    ) -> builtins.list[NASVolume]:
        """List NAS volumes with optional filtering.

        Args:
            filter: OData filter string.
            fields: List of fields to return (uses defaults if not specified).
            limit: Maximum number of results.
            offset: Skip this many results.
            enabled: Filter by enabled state.
            fs_type: Filter by filesystem type (ext4, cifs, nfs, ybfs, verge_vm_export).
            service: Filter by NAS service (key or name).
            **filter_kwargs: Shorthand filter arguments (name, etc.).

        Returns:
            List of NASVolume objects.

        Example:
            >>> # List all volumes
            >>> volumes = client.nas_volumes.list()

            >>> # List enabled volumes only
            >>> enabled = client.nas_volumes.list(enabled=True)

            >>> # Filter by filesystem type
            >>> ext4_vols = client.nas_volumes.list(fs_type="ext4")

            >>> # Filter by NAS service
            >>> nas01_vols = client.nas_volumes.list(service="NAS01")
        """
        params: dict[str, Any] = {}

        # Build filter
        filters: builtins.list[str] = []
        if filter:
            filters.append(filter)
        if filter_kwargs:
            filters.append(build_filter(**filter_kwargs))

        # Add enabled filter
        if enabled is not None:
            filters.append(f"enabled eq {1 if enabled else 0}")

        # Add fs_type filter
        if fs_type:
            filters.append(f"fs_type eq '{fs_type}'")

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
        fields: builtins.list[str] | None = None,
    ) -> NASVolume:
        """Get a single NAS volume by key or name.

        Args:
            key: Volume $key (40-character hex string).
            name: Volume name.
            fields: List of fields to return.

        Returns:
            NASVolume object.

        Raises:
            NotFoundError: If volume not found.
            ValueError: If no identifier provided.

        Example:
            >>> # Get by key
            >>> vol = client.nas_volumes.get("8f73f8bcc9c9f1aaba32f733bfc295acaf548554")

            >>> # Get by name
            >>> vol = client.nas_volumes.get(name="FileShare")
        """
        if key is not None:
            # Fetch by key using id filter (PowerShell pattern: id eq '$Key')
            params: dict[str, Any] = {
                "filter": f"id eq '{key}'",
            }
            if fields:
                params["fields"] = ",".join(fields)
            else:
                params["fields"] = ",".join(self._default_fields)

            response = self._client._request("GET", self._endpoint, params=params)

            if response is None:
                raise NotFoundError(f"NAS volume with key {key} not found")
            if isinstance(response, list):
                if not response:
                    raise NotFoundError(f"NAS volume with key {key} not found")
                response = response[0]
            if not isinstance(response, dict):
                raise NotFoundError(f"NAS volume with key {key} returned invalid response")
            return self._to_model(response)

        if name is not None:
            # Search by name
            escaped_name = name.replace("'", "''")
            results = self.list(filter=f"name eq '{escaped_name}'", fields=fields, limit=1)
            if not results:
                raise NotFoundError(f"NAS volume with name '{name}' not found")
            return results[0]

        raise ValueError("Either key or name must be provided")

    def create(  # type: ignore[override]
        self,
        name: str,
        service: int | str,
        size_gb: int,
        *,
        tier: int | None = None,
        description: str | None = None,
        read_only: bool = False,
        discard: bool = True,
        owner_user: str | None = None,
        owner_group: str | None = None,
        snapshot_profile: int | None = None,
        enabled: bool = True,
    ) -> NASVolume:
        """Create a new NAS volume.

        Args:
            name: Volume name (alphanumeric with underscores/hyphens only).
            service: NAS service (key or name) to create the volume on.
            size_gb: Maximum size in gigabytes (1-524288).
            tier: Preferred storage tier (1-5).
            description: Volume description.
            read_only: Create as read-only volume.
            discard: Enable automatic discard of deleted files (default True).
            owner_user: Volume directory owner user.
            owner_group: Volume directory owner group.
            snapshot_profile: Snapshot profile key.
            enabled: Enable the volume (default True).

        Returns:
            Created NASVolume object.

        Raises:
            ValueError: If NAS service not found.

        Example:
            >>> # Create a basic volume
            >>> vol = client.nas_volumes.create("FileShare", "NAS01", 500)

            >>> # Create with options
            >>> vol = client.nas_volumes.create(
            ...     "Archive",
            ...     service="NAS01",
            ...     size_gb=2000,
            ...     tier=3,
            ...     description="Archive storage"
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

        # Build request body
        body: dict[str, Any] = {
            "name": name,
            "service": service_key,
            "maxsize": size_gb * 1073741824,  # Convert GB to bytes
            "enabled": enabled,
            "discard": discard,
        }

        if tier is not None:
            body["preferred_tier"] = str(tier)

        if description is not None:
            body["description"] = description

        if read_only:
            body["read_only"] = True

        if owner_user is not None:
            body["owner_user"] = owner_user

        if owner_group is not None:
            body["owner_group"] = owner_group

        if snapshot_profile is not None:
            body["snapshot_profile"] = snapshot_profile

        response = self._client._request("POST", self._endpoint, json_data=body)

        # Get the created volume
        if response and isinstance(response, dict):
            vol_key = response.get("$key") or response.get("id")
            if vol_key:
                return self.get(key=vol_key)

        # Fallback: search by name
        return self.get(name=name)

    def update(  # type: ignore[override]
        self,
        key: str,
        *,
        description: str | None = None,
        size_gb: int | None = None,
        tier: int | None = None,
        enabled: bool | None = None,
        read_only: bool | None = None,
        discard: bool | None = None,
        owner_user: str | None = None,
        owner_group: str | None = None,
        snapshot_profile: int | None = None,
        automount_snapshots: bool | None = None,
    ) -> NASVolume:
        """Update a NAS volume.

        Args:
            key: Volume $key (40-character hex string).
            description: New description.
            size_gb: New maximum size in gigabytes.
            tier: New preferred storage tier (1-5).
            enabled: Enable or disable the volume.
            read_only: Set read-only or read-write.
            discard: Enable or disable automatic discard.
            owner_user: New owner user.
            owner_group: New owner group.
            snapshot_profile: New snapshot profile key (or None to remove).
            automount_snapshots: Enable or disable auto-mount of snapshots.

        Returns:
            Updated NASVolume object.

        Example:
            >>> # Increase size
            >>> client.nas_volumes.update(vol.key, size_gb=1000)

            >>> # Change tier
            >>> client.nas_volumes.update(vol.key, tier=3)

            >>> # Disable volume
            >>> client.nas_volumes.update(vol.key, enabled=False)
        """
        body: dict[str, Any] = {}

        if description is not None:
            body["description"] = description

        if size_gb is not None:
            body["maxsize"] = size_gb * 1073741824

        if tier is not None:
            body["preferred_tier"] = str(tier)

        if enabled is not None:
            body["enabled"] = enabled

        if read_only is not None:
            body["read_only"] = read_only

        if discard is not None:
            body["discard"] = discard

        if owner_user is not None:
            body["owner_user"] = owner_user

        if owner_group is not None:
            body["owner_group"] = owner_group

        if snapshot_profile is not None:
            body["snapshot_profile"] = snapshot_profile

        if automount_snapshots is not None:
            body["automount_snapshots"] = automount_snapshots

        if not body:
            return self.get(key)

        self._client._request("PUT", f"{self._endpoint}/{key}", json_data=body)
        return self.get(key)

    def delete(self, key: str) -> None:  # type: ignore[override]
        """Delete a NAS volume.

        This operation is destructive and cannot be undone. All data on
        the volume will be permanently deleted.

        Args:
            key: Volume $key (40-character hex string).

        Raises:
            NotFoundError: If volume not found.

        Example:
            >>> client.nas_volumes.delete(vol.key)
        """
        self._client._request("DELETE", f"{self._endpoint}/{key}")

    def enable(self, key: str) -> NASVolume:
        """Enable a NAS volume.

        Args:
            key: Volume $key (40-character hex string).

        Returns:
            Updated NASVolume object.

        Example:
            >>> client.nas_volumes.enable(vol.key)
        """
        return self.update(key, enabled=True)

    def disable(self, key: str) -> NASVolume:
        """Disable a NAS volume.

        Args:
            key: Volume $key (40-character hex string).

        Returns:
            Updated NASVolume object.

        Example:
            >>> client.nas_volumes.disable(vol.key)
        """
        return self.update(key, enabled=False)

    def reset(self, key: str) -> dict[str, Any] | None:
        """Reset a NAS volume.

        Resets the volume, which can help recover from error states.

        Args:
            key: Volume $key (40-character hex string).

        Returns:
            Task information dict or None.

        Example:
            >>> client.nas_volumes.reset(vol.key)
        """
        result = self._client._request(
            "PUT", f"{self._endpoint}/{key}?action=reset", json_data={}
        )
        if isinstance(result, dict):
            return result
        return None

    def snapshots(self, key: str) -> NASVolumeSnapshotManager:
        """Get a snapshot manager for a specific volume.

        Args:
            key: Volume $key (40-character hex string).

        Returns:
            NASVolumeSnapshotManager for the volume.

        Example:
            >>> # List snapshots for a volume
            >>> for snap in client.nas_volumes.snapshots(vol.key).list():
            ...     print(snap.name)

            >>> # Create a snapshot
            >>> snap = client.nas_volumes.snapshots(vol.key).create("pre-update")
        """
        return NASVolumeSnapshotManager(self._client, volume_key=key)

    def files(self, key: str, *, name: str | None = None) -> NASVolumeFileManager:
        """Get a file manager for browsing a volume's files.

        Args:
            key: Volume $key (40-character hex string).
            name: Optional volume name for display purposes.

        Returns:
            NASVolumeFileManager for browsing the volume.

        Example:
            >>> # Browse root directory
            >>> for f in client.nas_volumes.files(vol.key).list():
            ...     print(f"{f.name}: {f.size_display}")

            >>> # Browse a subdirectory
            >>> files = client.nas_volumes.files(vol.key).list("/documents")

            >>> # Get a specific file
            >>> file = client.nas_volumes.files(vol.key).get("/report.pdf")
        """
        from pyvergeos.resources.nas_volume_browser import NASVolumeFileManager

        return NASVolumeFileManager(self._client, volume_key=key, volume_name=name)

    def _to_model(self, data: dict[str, Any]) -> NASVolume:
        """Convert API response to NASVolume object."""
        return NASVolume(data, self)


class NASVolumeSnapshotManager(ResourceManager["NASVolumeSnapshot"]):
    """Manager for NAS volume snapshot operations.

    This manager can be used either standalone or scoped to a specific volume.

    Example:
        >>> # List all snapshots (standalone)
        >>> for snap in client.nas_volume_snapshots.list():
        ...     print(f"{snap.name} ({snap.volume_name})")

        >>> # List snapshots for a specific volume
        >>> for snap in client.nas_volumes.snapshots(vol.key).list():
        ...     print(snap.name)

        >>> # Create a snapshot
        >>> snap = client.nas_volumes.snapshots(vol.key).create("pre-update")
    """

    _endpoint = "volume_snapshots"

    # Default fields for list operations
    _default_fields = [
        "$key",
        "name",
        "description",
        "created",
        "expires",
        "expires_type",
        "enabled",
        "created_manually",
        "quiesce",
        "volume",
        "volume#$display as volume_display",
        "volume#name as volume_name",
        "snap_volume",
    ]

    def __init__(
        self, client: VergeClient, *, volume_key: str | None = None
    ) -> None:
        super().__init__(client)
        self._volume_key = volume_key

    def list(
        self,
        filter: str | None = None,
        fields: builtins.list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        volume: str | None = None,
        **filter_kwargs: Any,
    ) -> builtins.list[NASVolumeSnapshot]:
        """List volume snapshots with optional filtering.

        Args:
            filter: OData filter string.
            fields: List of fields to return (uses defaults if not specified).
            limit: Maximum number of results.
            offset: Skip this many results.
            volume: Filter by volume (key or name). Ignored if manager is scoped.
            **filter_kwargs: Shorthand filter arguments (name, etc.).

        Returns:
            List of NASVolumeSnapshot objects.

        Example:
            >>> # List all snapshots
            >>> snapshots = client.nas_volume_snapshots.list()

            >>> # List snapshots for a specific volume by name
            >>> snapshots = client.nas_volume_snapshots.list(volume="FileShare")

            >>> # List snapshots by name pattern
            >>> snapshots = client.nas_volume_snapshots.list(name="Daily-*")
        """
        params: dict[str, Any] = {}

        # Build filter
        filters: builtins.list[str] = []
        if filter:
            filters.append(filter)
        if filter_kwargs:
            filters.append(build_filter(**filter_kwargs))

        # Add volume filter (from scope or parameter)
        volume_key = self._volume_key
        if volume_key is None and volume is not None:
            # Check if it looks like a volume key (40-char hex) or a name
            if len(volume) == 40 and all(c in "0123456789abcdef" for c in volume.lower()):
                volume_key = volume
            else:
                # Look up volume by name
                vol_response = self._client._request(
                    "GET",
                    "volumes",
                    params={"filter": f"name eq '{volume}'", "fields": "$key", "limit": "1"},
                )
                if vol_response:
                    if isinstance(vol_response, list):
                        vol_response = vol_response[0] if vol_response else None
                    if vol_response:
                        volume_key = vol_response.get("$key")

        if volume_key is not None:
            # Volume keys are strings (40-char hex)
            filters.append(f"volume eq '{volume_key}'")

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

    def get(
        self,
        key: int | None = None,
        *,
        name: str | None = None,
        fields: builtins.list[str] | None = None,
    ) -> NASVolumeSnapshot:
        """Get a single volume snapshot by key or name.

        Args:
            key: Snapshot $key (row ID).
            name: Snapshot name (requires scoped manager or unique name).
            fields: List of fields to return.

        Returns:
            NASVolumeSnapshot object.

        Raises:
            NotFoundError: If snapshot not found.
            ValueError: If no identifier provided.

        Example:
            >>> # Get by key
            >>> snap = client.nas_volume_snapshots.get(1)

            >>> # Get by name (scoped to volume)
            >>> snap = client.nas_volumes.snapshots(1).get(name="pre-update")
        """
        if key is not None:
            # Fetch by key with default fields
            params: dict[str, Any] = {}
            if fields:
                params["fields"] = ",".join(fields)
            else:
                params["fields"] = ",".join(self._default_fields)

            response = self._client._request(
                "GET", f"{self._endpoint}/{key}", params=params
            )
            if response is None:
                raise NotFoundError(f"Volume snapshot with key {key} not found")
            if not isinstance(response, dict):
                raise NotFoundError(f"Volume snapshot with key {key} returned invalid response")
            return self._to_model(response)

        if name is not None:
            # Search by name
            escaped_name = name.replace("'", "''")
            results = self.list(filter=f"name eq '{escaped_name}'", fields=fields, limit=1)
            if not results:
                raise NotFoundError(f"Volume snapshot with name '{name}' not found")
            return results[0]

        raise ValueError("Either key or name must be provided")

    def create(  # type: ignore[override]
        self,
        name: str,
        *,
        volume: str | None = None,
        description: str | None = None,
        expires_days: int = 3,
        never_expires: bool = False,
        quiesce: bool = False,
    ) -> NASVolumeSnapshot:
        """Create a new volume snapshot.

        Args:
            name: Snapshot name.
            volume: Volume key (40-char hex string, required if manager is not scoped).
            description: Snapshot description.
            expires_days: Days until expiration (default 3).
            never_expires: If True, snapshot never expires.
            quiesce: If True, freeze I/O during snapshot for consistency.

        Returns:
            Created NASVolumeSnapshot object.

        Raises:
            ValueError: If volume not specified and manager not scoped.

        Example:
            >>> # Create with scoped manager
            >>> snap = client.nas_volumes.snapshots(vol.key).create("pre-update")

            >>> # Create with standalone manager
            >>> snap = client.nas_volume_snapshots.create("backup", volume=vol.key)

            >>> # Create a permanent quiesced snapshot
            >>> snap = client.nas_volumes.snapshots(vol.key).create(
            ...     "before-migration",
            ...     never_expires=True,
            ...     quiesce=True
            ... )
        """
        volume_key = volume or self._volume_key
        if volume_key is None:
            raise ValueError("Volume key is required (use scoped manager or provide volume)")

        import time as _time

        body: dict[str, Any] = {
            "volume": volume_key,
            "name": name,
            "created_manually": True,
        }

        if description is not None:
            body["description"] = description

        if never_expires:
            body["expires_type"] = "never"
            body["expires"] = 0
        else:
            body["expires_type"] = "date"
            # Calculate expiration as Unix timestamp
            body["expires"] = int(_time.time()) + (expires_days * 86400)

        if quiesce:
            body["quiesce"] = True

        response = self._client._request("POST", self._endpoint, json_data=body)

        # Get the created snapshot
        if response and isinstance(response, dict):
            snap_key = response.get("$key")
            if snap_key:
                return self.get(key=snap_key)

        # Fallback: search by name
        return self.get(name=name)

    def delete(self, key: int) -> None:
        """Delete a volume snapshot.

        This operation cannot be undone.

        Args:
            key: Snapshot $key (ID).

        Example:
            >>> client.nas_volume_snapshots.delete(1)
        """
        self._client._request("DELETE", f"{self._endpoint}/{key}")

    def _to_model(self, data: dict[str, Any]) -> NASVolumeSnapshot:
        """Convert API response to NASVolumeSnapshot object."""
        return NASVolumeSnapshot(data, self)
