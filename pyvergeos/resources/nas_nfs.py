"""NAS NFS share resources."""

from __future__ import annotations

import builtins
from typing import TYPE_CHECKING, Any

from pyvergeos.exceptions import NotFoundError
from pyvergeos.filters import build_filter
from pyvergeos.resources.base import ResourceManager, ResourceObject

if TYPE_CHECKING:
    from pyvergeos.client import VergeClient


class NASNFSShare(ResourceObject):
    """NAS NFS share resource object.

    Represents an NFS file share on a NAS volume.

    Note:
        Share keys are 40-character hex strings, not integers like most
        other VergeOS resources.

    Attributes:
        key: The share unique identifier ($key) - 40-char hex string.
        id: The share ID (same as $key).
        name: Share name.
        description: Share description.
        volume_key: Parent volume key.
        volume_name: Parent volume name.
        share_path: Path within the volume being shared.
        allowed_hosts: Comma-delimited list of allowed hosts.
        allow_all: Whether all hosts are allowed.
        data_access: Read-only (ro) or read-write (rw).
        squash: User/group squashing mode.
        filesystem_id: Filesystem ID for the export.
        anonymous_uid: User ID for anonymous/squashed users.
        anonymous_gid: Group ID for anonymous/squashed users.
        no_acl: Whether ACLs are disabled.
        insecure: Whether non-privileged ports are allowed.
        async_mode: Whether async mode is enabled.
        enabled: Whether the share is enabled.
        created: Creation timestamp.
        modified: Last modified timestamp.
    """

    @property
    def key(self) -> str:  # type: ignore[override]
        """Resource primary key ($key) - 40-character hex string.

        Raises:
            ValueError: If resource has no $key (not yet persisted).
        """
        k = self.get("$key") or self.get("id")
        if k is None:
            raise ValueError("Resource has no $key - may not be persisted")
        return str(k)

    def refresh(self) -> NASNFSShare:
        """Refresh resource data from API.

        Returns:
            Updated NASNFSShare object.
        """
        from typing import cast

        manager = cast("NASNFSShareManager", self._manager)
        return manager.get(self.key)

    def save(self, **kwargs: Any) -> NASNFSShare:
        """Save changes to resource.

        Args:
            **kwargs: Fields to update.

        Returns:
            Updated NASNFSShare object.
        """
        from typing import cast

        manager = cast("NASNFSShareManager", self._manager)
        return manager.update(self.key, **kwargs)

    def delete(self) -> None:
        """Delete this share."""
        from typing import cast

        manager = cast("NASNFSShareManager", self._manager)
        manager.delete(self.key)

    @property
    def volume_key(self) -> str | None:
        """Get the parent volume key (40-char hex string)."""
        vol = self.get("volume")
        return str(vol) if vol is not None else None

    @property
    def volume_name(self) -> str | None:
        """Get the parent volume name."""
        return self.get("volume_name") or self.get("volume_display")

    @property
    def is_enabled(self) -> bool:
        """Check if the share is enabled."""
        return bool(self.get("enabled", False))

    @property
    def is_read_only(self) -> bool:
        """Check if the share is read-only."""
        return self.get("data_access") == "ro"

    @property
    def allows_all_hosts(self) -> bool:
        """Check if all hosts are allowed."""
        return bool(self.get("allow_all", False))

    @property
    def squash_display(self) -> str:
        """Get human-readable squash mode."""
        squash = str(self.get("squash", "root_squash"))
        squash_map = {
            "root_squash": "Squash Root",
            "all_squash": "Squash All",
            "no_root_squash": "No Squashing",
        }
        return squash_map.get(squash, squash)

    @property
    def data_access_display(self) -> str:
        """Get human-readable data access mode."""
        access = str(self.get("data_access", "ro"))
        access_map = {
            "ro": "Read Only",
            "rw": "Read and Write",
        }
        return access_map.get(access, access)


class NASNFSShareManager(ResourceManager["NASNFSShare"]):
    """Manager for NAS NFS share operations.

    NFS shares provide Unix/Linux-compatible file sharing.

    Example:
        >>> # List all NFS shares
        >>> for share in client.nfs_shares.list():
        ...     print(f"{share.name} on {share.volume_name}")

        >>> # Get shares for a specific volume
        >>> shares = client.nfs_shares.list(volume="FileShare")

        >>> # Create a share
        >>> share = client.nfs_shares.create(
        ...     name="exports",
        ...     volume="FileShare",
        ...     allowed_hosts="192.168.1.0/24"
        ... )
    """

    _endpoint = "volume_nfs_shares"

    # Default fields for list operations
    _default_fields = [
        "$key",
        "id",
        "name",
        "description",
        "enabled",
        "created",
        "modified",
        "share_path",
        "allowed_hosts",
        "fsid",
        "anonuid",
        "anongid",
        "no_acl",
        "insecure",
        "async",
        "squash",
        "data_access",
        "allow_all",
        "volume",
        "volume#$display as volume_display",
        "volume#name as volume_name",
        "status#status as status",
        "status#state as state",
    ]

    def __init__(self, client: VergeClient) -> None:
        super().__init__(client)

    def list(
        self,
        filter: str | None = None,
        fields: builtins.list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        volume: str | int | None = None,
        enabled: bool | None = None,
        **filter_kwargs: Any,
    ) -> builtins.list[NASNFSShare]:
        """List NFS shares with optional filtering.

        Args:
            filter: OData filter string.
            fields: List of fields to return (uses defaults if not specified).
            limit: Maximum number of results.
            offset: Skip this many results.
            volume: Filter by volume (key or name).
            enabled: Filter by enabled state.
            **filter_kwargs: Shorthand filter arguments (name, etc.).

        Returns:
            List of NASNFSShare objects.

        Example:
            >>> # List all NFS shares
            >>> shares = client.nfs_shares.list()

            >>> # List shares on a specific volume
            >>> shares = client.nfs_shares.list(volume="FileShare")

            >>> # List enabled shares only
            >>> shares = client.nfs_shares.list(enabled=True)
        """
        params: dict[str, Any] = {}

        # Build filter
        filters: builtins.list[str] = []
        if filter:
            filters.append(filter)
        if filter_kwargs:
            filters.append(build_filter(**filter_kwargs))

        # Add volume filter
        if volume is not None:
            volume_key = self._resolve_volume_key(volume)
            if volume_key:
                filters.append(f"volume eq {volume_key}")

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
        volume: str | int | None = None,
        fields: builtins.list[str] | None = None,
    ) -> NASNFSShare:
        """Get a single NFS share by key or name.

        Args:
            key: Share $key (40-character hex string).
            name: Share name (requires volume if not unique).
            volume: Volume key or name (helps disambiguate by name).
            fields: List of fields to return.

        Returns:
            NASNFSShare object.

        Raises:
            NotFoundError: If share not found.
            ValueError: If no identifier provided.

        Example:
            >>> # Get by key
            >>> share = client.nfs_shares.get("abc123...")

            >>> # Get by name on a volume
            >>> share = client.nfs_shares.get(name="exports", volume="FileShare")
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
                raise NotFoundError(f"NFS share with key {key} not found")
            if isinstance(response, list):
                if not response:
                    raise NotFoundError(f"NFS share with key {key} not found")
                response = response[0]
            if not isinstance(response, dict):
                raise NotFoundError(f"NFS share with key {key} returned invalid response")
            return self._to_model(response)

        if name is not None:
            # Search by name
            escaped_name = name.replace("'", "''")
            filter_str = f"name eq '{escaped_name}'"

            # Add volume filter if specified
            if volume is not None:
                volume_key = self._resolve_volume_key(volume)
                if volume_key:
                    filter_str += f" and volume eq {volume_key}"

            results = self.list(filter=filter_str, fields=fields, limit=1)
            if not results:
                raise NotFoundError(f"NFS share with name '{name}' not found")
            return results[0]

        raise ValueError("Either key or name must be provided")

    def create(  # type: ignore[override]
        self,
        name: str,
        volume: str | int,
        *,
        share_path: str | None = None,
        description: str | None = None,
        allowed_hosts: str | None = None,
        allow_all: bool = False,
        data_access: str = "ro",
        squash: str = "root_squash",
        anonymous_uid: str | None = None,
        anonymous_gid: str | None = None,
        async_mode: bool = False,
        insecure: bool = False,
        no_acl: bool = False,
        filesystem_id: str | None = None,
        enabled: bool = True,
    ) -> NASNFSShare:
        """Create a new NFS share.

        Args:
            name: Share name (alphanumeric with underscores/hyphens).
            volume: Volume key or name to create the share on.
            share_path: Path within the volume to share (empty = entire volume).
            description: Share description.
            allowed_hosts: Comma-delimited list of allowed hosts (FQDNs, IPs,
                networks, NIS netgroups). Required unless allow_all is True.
            allow_all: Allow connections from any host.
            data_access: Data access mode - "ro" (read-only) or "rw" (read-write).
            squash: User/group squashing - "root_squash", "all_squash", "no_root_squash".
            anonymous_uid: User ID for anonymous/squashed users (default 65534).
            anonymous_gid: Group ID for anonymous/squashed users (default 65534).
            async_mode: Enable async mode for better performance (risk of data loss).
            insecure: Allow connections from non-privileged ports.
            no_acl: Disable access control lists.
            filesystem_id: Filesystem ID for the export (must be unique per volume).
            enabled: Enable the share (default True).

        Returns:
            Created NASNFSShare object.

        Raises:
            ValueError: If volume not found or if neither allowed_hosts nor
                allow_all is specified.

        Example:
            >>> # Create a share for a subnet
            >>> share = client.nfs_shares.create(
            ...     "exports", "FileShare",
            ...     allowed_hosts="192.168.1.0/24"
            ... )

            >>> # Create a read-write share for specific hosts
            >>> share = client.nfs_shares.create(
            ...     "data", "FileShare",
            ...     allowed_hosts="10.0.0.5,10.0.0.6",
            ...     data_access="rw",
            ...     squash="no_root_squash"
            ... )

            >>> # Create a share accessible from anywhere
            >>> share = client.nfs_shares.create(
            ...     "public", "FileShare",
            ...     allow_all=True,
            ...     data_access="ro"
            ... )
        """
        # Validate hosts requirement
        if not allow_all and not allowed_hosts:
            raise ValueError("Either allowed_hosts or allow_all must be specified")

        # Resolve volume to key
        volume_key = self._resolve_volume_key(volume)
        if volume_key is None:
            raise ValueError(f"Volume '{volume}' not found")

        # Map friendly values to API values
        data_access_map = {
            "readonly": "ro",
            "read_only": "ro",
            "ro": "ro",
            "readwrite": "rw",
            "read_write": "rw",
            "rw": "rw",
        }
        squash_map = {
            "squashroot": "root_squash",
            "squash_root": "root_squash",
            "root_squash": "root_squash",
            "squashall": "all_squash",
            "squash_all": "all_squash",
            "all_squash": "all_squash",
            "nosquash": "no_root_squash",
            "no_squash": "no_root_squash",
            "no_root_squash": "no_root_squash",
        }

        # Build request body
        body: dict[str, Any] = {
            "volume": volume_key,
            "name": name,
            "enabled": enabled,
            "data_access": data_access_map.get(data_access.lower(), data_access),
            "squash": squash_map.get(squash.lower(), squash),
        }

        if share_path:
            body["share_path"] = share_path

        if description:
            body["description"] = description

        if allow_all:
            body["allow_all"] = True

        if allowed_hosts:
            body["allowed_hosts"] = allowed_hosts

        if anonymous_uid:
            body["anonuid"] = anonymous_uid

        if anonymous_gid:
            body["anongid"] = anonymous_gid

        if async_mode:
            body["async"] = True

        if insecure:
            body["insecure"] = True

        if no_acl:
            body["no_acl"] = True

        if filesystem_id:
            body["fsid"] = filesystem_id

        response = self._client._request("POST", self._endpoint, json_data=body)

        # Get the created share
        if response and isinstance(response, dict):
            share_key = response.get("$key") or response.get("id")
            if share_key:
                return self.get(key=share_key)

        # Fallback: search by name and volume
        return self.get(name=name, volume=volume_key)

    def update(  # type: ignore[override]
        self,
        key: str,
        *,
        description: str | None = None,
        allowed_hosts: str | None = None,
        allow_all: bool | None = None,
        data_access: str | None = None,
        squash: str | None = None,
        anonymous_uid: str | None = None,
        anonymous_gid: str | None = None,
        async_mode: bool | None = None,
        insecure: bool | None = None,
        no_acl: bool | None = None,
        filesystem_id: str | None = None,
        enabled: bool | None = None,
    ) -> NASNFSShare:
        """Update an NFS share.

        Args:
            key: Share $key (40-character hex string).
            description: New description.
            allowed_hosts: New allowed hosts list.
            allow_all: Allow all hosts.
            data_access: Data access mode - "ro" or "rw".
            squash: Squash mode - "root_squash", "all_squash", "no_root_squash".
            anonymous_uid: Anonymous user ID.
            anonymous_gid: Anonymous group ID.
            async_mode: Enable or disable async mode.
            insecure: Allow or disallow non-privileged ports.
            no_acl: Enable or disable ACL support.
            filesystem_id: New filesystem ID.
            enabled: Enable or disable the share.

        Returns:
            Updated NASNFSShare object.

        Example:
            >>> # Change to read-write
            >>> client.nfs_shares.update(share.key, data_access="rw")

            >>> # Update allowed hosts
            >>> client.nfs_shares.update(
            ...     share.key,
            ...     allowed_hosts="192.168.1.0/24,10.0.0.0/8"
            ... )
        """
        body: dict[str, Any] = {}

        if description is not None:
            body["description"] = description

        if allowed_hosts is not None:
            body["allowed_hosts"] = allowed_hosts

        if allow_all is not None:
            body["allow_all"] = allow_all

        if data_access is not None:
            data_access_map = {
                "readonly": "ro",
                "read_only": "ro",
                "ro": "ro",
                "readwrite": "rw",
                "read_write": "rw",
                "rw": "rw",
            }
            body["data_access"] = data_access_map.get(data_access.lower(), data_access)

        if squash is not None:
            squash_map = {
                "squashroot": "root_squash",
                "squash_root": "root_squash",
                "root_squash": "root_squash",
                "squashall": "all_squash",
                "squash_all": "all_squash",
                "all_squash": "all_squash",
                "nosquash": "no_root_squash",
                "no_squash": "no_root_squash",
                "no_root_squash": "no_root_squash",
            }
            body["squash"] = squash_map.get(squash.lower(), squash)

        if anonymous_uid is not None:
            body["anonuid"] = anonymous_uid

        if anonymous_gid is not None:
            body["anongid"] = anonymous_gid

        if async_mode is not None:
            body["async"] = async_mode

        if insecure is not None:
            body["insecure"] = insecure

        if no_acl is not None:
            body["no_acl"] = no_acl

        if filesystem_id is not None:
            body["fsid"] = filesystem_id

        if enabled is not None:
            body["enabled"] = enabled

        if not body:
            return self.get(key)

        self._client._request("PUT", f"{self._endpoint}/{key}", json_data=body)
        return self.get(key)

    def delete(self, key: str) -> None:  # type: ignore[override]
        """Delete an NFS share.

        This removes the share but does not delete the underlying data
        on the volume.

        Args:
            key: Share $key (40-character hex string).

        Example:
            >>> client.nfs_shares.delete(share.key)
        """
        self._client._request("DELETE", f"{self._endpoint}/{key}")

    def enable(self, key: str) -> NASNFSShare:
        """Enable an NFS share.

        Args:
            key: Share $key (40-character hex string).

        Returns:
            Updated NASNFSShare object.
        """
        return self.update(key, enabled=True)

    def disable(self, key: str) -> NASNFSShare:
        """Disable an NFS share.

        Args:
            key: Share $key (40-character hex string).

        Returns:
            Updated NASNFSShare object.
        """
        return self.update(key, enabled=False)

    def _resolve_volume_key(self, volume: str | int) -> int | None:
        """Resolve a volume identifier to its integer key.

        Args:
            volume: Volume key (hex string or int) or name.

        Returns:
            Volume key as integer, or None if not found.
        """
        if isinstance(volume, int):
            return volume

        # Check if it looks like a volume key (40-char hex)
        if len(volume) == 40 and all(c in "0123456789abcdef" for c in volume.lower()):
            # Look up to get the row key for NFS shares
            vol_response = self._client._request(
                "GET",
                "volumes",
                params={"filter": f"id eq '{volume}'", "fields": "$key,id,name", "limit": "1"},
            )
            if vol_response:
                if isinstance(vol_response, list):
                    vol_response = vol_response[0] if vol_response else None
                if vol_response:
                    return vol_response.get("$key")
            return None

        # Look up by name
        vol_response = self._client._request(
            "GET",
            "volumes",
            params={"filter": f"name eq '{volume}'", "fields": "$key,id,name", "limit": "1"},
        )
        if vol_response:
            if isinstance(vol_response, list):
                vol_response = vol_response[0] if vol_response else None
            if vol_response:
                return vol_response.get("$key")
        return None

    def _to_model(self, data: dict[str, Any]) -> NASNFSShare:
        """Convert API response to NASNFSShare object."""
        return NASNFSShare(data, self)
