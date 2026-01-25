"""NAS CIFS/SMB share resources."""

from __future__ import annotations

import builtins
from typing import TYPE_CHECKING, Any

from pyvergeos.exceptions import NotFoundError
from pyvergeos.filters import build_filter
from pyvergeos.resources.base import ResourceManager, ResourceObject

if TYPE_CHECKING:
    from pyvergeos.client import VergeClient


class NASCIFSShare(ResourceObject):
    """NAS CIFS/SMB share resource object.

    Represents a CIFS (SMB) file share on a NAS volume.

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
        comment: Short comment (visible to clients).
        enabled: Whether the share is enabled.
        browseable: Whether the share is visible in network browsing.
        read_only: Whether the share is read-only.
        guest_ok: Whether guest access is allowed.
        guest_only: Only guest connections are permitted.
        force_user: All file operations performed as this user.
        force_group: Default primary group for connecting users.
        valid_users: List of users allowed to connect.
        valid_groups: List of groups allowed to connect.
        admin_users: List of users with admin privileges.
        admin_groups: List of groups with admin privileges.
        allowed_hosts: List of allowed hosts.
        denied_hosts: List of denied hosts.
        shadow_copy_enabled: Whether shadow copy (Previous Versions) is enabled.
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

    def refresh(self) -> NASCIFSShare:
        """Refresh resource data from API.

        Returns:
            Updated NASCIFSShare object.
        """
        from typing import cast

        manager = cast("NASCIFSShareManager", self._manager)
        return manager.get(self.key)

    def save(self, **kwargs: Any) -> NASCIFSShare:
        """Save changes to resource.

        Args:
            **kwargs: Fields to update.

        Returns:
            Updated NASCIFSShare object.
        """
        from typing import cast

        manager = cast("NASCIFSShareManager", self._manager)
        return manager.update(self.key, **kwargs)

    def delete(self) -> None:
        """Delete this share."""
        from typing import cast

        manager = cast("NASCIFSShareManager", self._manager)
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
        return bool(self.get("read_only", False))

    @property
    def allows_guests(self) -> bool:
        """Check if guest access is allowed."""
        return bool(self.get("guest_ok", False))

    @property
    def shadow_copy_enabled(self) -> bool:
        """Check if shadow copy is enabled."""
        return bool(self.get("vfs_shadow_copy2", False))


class NASCIFSShareManager(ResourceManager["NASCIFSShare"]):
    """Manager for NAS CIFS/SMB share operations.

    CIFS shares provide Windows-compatible file sharing (SMB protocol).

    Example:
        >>> # List all CIFS shares
        >>> for share in client.cifs_shares.list():
        ...     print(f"{share.name} on {share.volume_name}")

        >>> # Get shares for a specific volume
        >>> shares = client.cifs_shares.list(volume="FileShare")

        >>> # Create a share
        >>> share = client.cifs_shares.create(
        ...     name="shared",
        ...     volume="FileShare",
        ...     guest_ok=True
        ... )
    """

    _endpoint = "volume_cifs_shares"

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
        "comment",
        "browseable",
        "read_only",
        "guest_ok",
        "guest_only",
        "force_user",
        "force_group",
        "valid_users",
        "valid_groups",
        "admin_users",
        "admin_groups",
        "host_allow",
        "host_deny",
        "vfs_shadow_copy2",
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
    ) -> builtins.list[NASCIFSShare]:
        """List CIFS shares with optional filtering.

        Args:
            filter: OData filter string.
            fields: List of fields to return (uses defaults if not specified).
            limit: Maximum number of results.
            offset: Skip this many results.
            volume: Filter by volume (key or name).
            enabled: Filter by enabled state.
            **filter_kwargs: Shorthand filter arguments (name, etc.).

        Returns:
            List of NASCIFSShare objects.

        Example:
            >>> # List all CIFS shares
            >>> shares = client.cifs_shares.list()

            >>> # List shares on a specific volume
            >>> shares = client.cifs_shares.list(volume="FileShare")

            >>> # List enabled shares only
            >>> shares = client.cifs_shares.list(enabled=True)
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
                # Volume keys are integers in the API for shares
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
    ) -> NASCIFSShare:
        """Get a single CIFS share by key or name.

        Args:
            key: Share $key (40-character hex string).
            name: Share name (requires volume if not unique).
            volume: Volume key or name (helps disambiguate by name).
            fields: List of fields to return.

        Returns:
            NASCIFSShare object.

        Raises:
            NotFoundError: If share not found.
            ValueError: If no identifier provided.

        Example:
            >>> # Get by key
            >>> share = client.cifs_shares.get("abc123...")

            >>> # Get by name on a volume
            >>> share = client.cifs_shares.get(name="shared", volume="FileShare")
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
                raise NotFoundError(f"CIFS share with key {key} not found")
            if isinstance(response, list):
                if not response:
                    raise NotFoundError(f"CIFS share with key {key} not found")
                response = response[0]
            if not isinstance(response, dict):
                raise NotFoundError(f"CIFS share with key {key} returned invalid response")
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
                raise NotFoundError(f"CIFS share with name '{name}' not found")
            return results[0]

        raise ValueError("Either key or name must be provided")

    def create(  # type: ignore[override]
        self,
        name: str,
        volume: str | int,
        *,
        share_path: str | None = None,
        description: str | None = None,
        comment: str | None = None,
        browseable: bool = True,
        read_only: bool = False,
        guest_ok: bool = False,
        guest_only: bool = False,
        force_user: str | None = None,
        force_group: str | None = None,
        valid_users: builtins.list[str] | None = None,
        valid_groups: builtins.list[str] | None = None,
        admin_users: builtins.list[str] | None = None,
        admin_groups: builtins.list[str] | None = None,
        allowed_hosts: builtins.list[str] | None = None,
        denied_hosts: builtins.list[str] | None = None,
        shadow_copy: bool = False,
        enabled: bool = True,
    ) -> NASCIFSShare:
        """Create a new CIFS share.

        Args:
            name: Share name (alphanumeric with underscores/hyphens).
            volume: Volume key or name to create the share on.
            share_path: Path within the volume to share (empty = entire volume).
            description: Share description.
            comment: Short comment visible to clients.
            browseable: Make visible in network browsing (default True).
            read_only: Create as read-only share.
            guest_ok: Allow guest access.
            guest_only: Only allow guest connections.
            force_user: All operations performed as this user.
            force_group: Default primary group for connecting users.
            valid_users: List of usernames allowed to connect.
            valid_groups: List of group names allowed to connect.
            admin_users: List of users with admin privileges.
            admin_groups: List of groups with admin privileges.
            allowed_hosts: List of allowed hosts (IPs, hostnames, subnets).
            denied_hosts: List of denied hosts.
            shadow_copy: Enable Previous Versions support.
            enabled: Enable the share (default True).

        Returns:
            Created NASCIFSShare object.

        Raises:
            ValueError: If volume not found.

        Example:
            >>> # Create a basic share
            >>> share = client.cifs_shares.create("shared", "FileShare")

            >>> # Create with guest access
            >>> share = client.cifs_shares.create(
            ...     "public", "FileShare",
            ...     share_path="/public",
            ...     guest_ok=True
            ... )

            >>> # Create with restricted access
            >>> share = client.cifs_shares.create(
            ...     "secure", "FileShare",
            ...     valid_users=["admin", "manager"]
            ... )
        """
        # Resolve volume to key
        volume_key = self._resolve_volume_key(volume)
        if volume_key is None:
            raise ValueError(f"Volume '{volume}' not found")

        # Build request body
        body: dict[str, Any] = {
            "volume": volume_key,
            "name": name,
            "enabled": enabled,
            "browseable": browseable,
        }

        if share_path:
            body["share_path"] = share_path

        if description:
            body["description"] = description

        if comment:
            body["comment"] = comment

        if read_only:
            body["read_only"] = True

        if guest_ok:
            body["guest_ok"] = True

        if guest_only:
            body["guest_only"] = True

        if force_user:
            body["force_user"] = force_user

        if force_group:
            body["force_group"] = force_group

        if valid_users:
            body["valid_users"] = "\n".join(valid_users)

        if valid_groups:
            body["valid_groups"] = "\n".join(valid_groups)

        if admin_users:
            body["admin_users"] = "\n".join(admin_users)

        if admin_groups:
            body["admin_groups"] = "\n".join(admin_groups)

        if allowed_hosts:
            body["host_allow"] = "\n".join(allowed_hosts)

        if denied_hosts:
            body["host_deny"] = "\n".join(denied_hosts)

        if shadow_copy:
            body["vfs_shadow_copy2"] = True

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
        comment: str | None = None,
        enabled: bool | None = None,
        browseable: bool | None = None,
        read_only: bool | None = None,
        guest_ok: bool | None = None,
        guest_only: bool | None = None,
        force_user: str | None = None,
        force_group: str | None = None,
        valid_users: builtins.list[str] | None = None,
        valid_groups: builtins.list[str] | None = None,
        admin_users: builtins.list[str] | None = None,
        admin_groups: builtins.list[str] | None = None,
        allowed_hosts: builtins.list[str] | None = None,
        denied_hosts: builtins.list[str] | None = None,
        shadow_copy: bool | None = None,
    ) -> NASCIFSShare:
        """Update a CIFS share.

        Args:
            key: Share $key (40-character hex string).
            description: New description.
            comment: New comment.
            enabled: Enable or disable the share.
            browseable: Show or hide in network browsing.
            read_only: Set read-only or read-write.
            guest_ok: Allow or disallow guest access.
            guest_only: Restrict to guest-only access.
            force_user: Set force user (empty string to clear).
            force_group: Set force group (empty string to clear).
            valid_users: Set valid users (empty list to clear).
            valid_groups: Set valid groups (empty list to clear).
            admin_users: Set admin users (empty list to clear).
            admin_groups: Set admin groups (empty list to clear).
            allowed_hosts: Set allowed hosts (empty list to clear).
            denied_hosts: Set denied hosts (empty list to clear).
            shadow_copy: Enable or disable shadow copy.

        Returns:
            Updated NASCIFSShare object.

        Example:
            >>> # Make share read-only
            >>> client.cifs_shares.update(share.key, read_only=True)

            >>> # Update access controls
            >>> client.cifs_shares.update(
            ...     share.key,
            ...     valid_users=["admin", "manager", "backup"]
            ... )
        """
        body: dict[str, Any] = {}

        if description is not None:
            body["description"] = description

        if comment is not None:
            body["comment"] = comment

        if enabled is not None:
            body["enabled"] = enabled

        if browseable is not None:
            body["browseable"] = browseable

        if read_only is not None:
            body["read_only"] = read_only

        if guest_ok is not None:
            body["guest_ok"] = guest_ok

        if guest_only is not None:
            body["guest_only"] = guest_only

        if force_user is not None:
            body["force_user"] = force_user

        if force_group is not None:
            body["force_group"] = force_group

        if valid_users is not None:
            body["valid_users"] = "\n".join(valid_users) if valid_users else ""

        if valid_groups is not None:
            body["valid_groups"] = "\n".join(valid_groups) if valid_groups else ""

        if admin_users is not None:
            body["admin_users"] = "\n".join(admin_users) if admin_users else ""

        if admin_groups is not None:
            body["admin_groups"] = "\n".join(admin_groups) if admin_groups else ""

        if allowed_hosts is not None:
            body["host_allow"] = "\n".join(allowed_hosts) if allowed_hosts else ""

        if denied_hosts is not None:
            body["host_deny"] = "\n".join(denied_hosts) if denied_hosts else ""

        if shadow_copy is not None:
            body["vfs_shadow_copy2"] = shadow_copy

        if not body:
            return self.get(key)

        self._client._request("PUT", f"{self._endpoint}/{key}", json_data=body)
        return self.get(key)

    def delete(self, key: str) -> None:  # type: ignore[override]
        """Delete a CIFS share.

        This removes the share but does not delete the underlying data
        on the volume.

        Args:
            key: Share $key (40-character hex string).

        Example:
            >>> client.cifs_shares.delete(share.key)
        """
        self._client._request("DELETE", f"{self._endpoint}/{key}")

    def enable(self, key: str) -> NASCIFSShare:
        """Enable a CIFS share.

        Args:
            key: Share $key (40-character hex string).

        Returns:
            Updated NASCIFSShare object.
        """
        return self.update(key, enabled=True)

    def disable(self, key: str) -> NASCIFSShare:
        """Disable a CIFS share.

        Args:
            key: Share $key (40-character hex string).

        Returns:
            Updated NASCIFSShare object.
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
            # Look up to get the row key for CIFS shares
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

    def _to_model(self, data: dict[str, Any]) -> NASCIFSShare:
        """Convert API response to NASCIFSShare object."""
        return NASCIFSShare(data, self)
