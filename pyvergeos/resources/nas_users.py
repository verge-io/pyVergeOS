"""NAS local user resources."""

from __future__ import annotations

import builtins
from typing import TYPE_CHECKING, Any

from pyvergeos.exceptions import NotFoundError
from pyvergeos.filters import build_filter
from pyvergeos.resources.base import ResourceManager, ResourceObject

if TYPE_CHECKING:
    from pyvergeos.client import VergeClient


class NASUser(ResourceObject):
    """NAS local user resource object.

    Represents a local user account on a NAS service for CIFS/SMB authentication.
    Local users are used when not using Active Directory integration.

    Note:
        User keys are 40-character hex strings, not integers like most
        other VergeOS resources.

    Attributes:
        key: The user unique identifier ($key) - 40-char hex string.
        name: Username.
        displayname: Display name.
        description: User description.
        enabled: Whether the account is enabled.
        service_key: Parent NAS service key.
        service_name: Parent NAS service name.
        home_share_key: Home share key.
        home_share_name: Home share name.
        home_drive: Home drive letter (e.g., "H").
        status: Account status (online=Enabled, offline=Disabled, error=Error).
        status_info: Additional status information.
        user_sid: Windows SID.
        group_sid: Group SID.
        user_id: Unix UID.
        group_id: Unix GID.
        created: Creation timestamp.
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

    def refresh(self) -> NASUser:
        """Refresh resource data from API.

        Returns:
            Updated NASUser object.
        """
        from typing import cast

        manager = cast("NASUserManager", self._manager)
        return manager.get(self.key)

    def save(self, **kwargs: Any) -> NASUser:
        """Save changes to resource.

        Args:
            **kwargs: Fields to update.

        Returns:
            Updated NASUser object.
        """
        from typing import cast

        manager = cast("NASUserManager", self._manager)
        return manager.update(self.key, **kwargs)

    def delete(self) -> None:
        """Delete this user."""
        from typing import cast

        manager = cast("NASUserManager", self._manager)
        manager.delete(self.key)

    @property
    def service_key(self) -> int | None:
        """Get the parent NAS service key."""
        svc = self.get("service")
        return int(svc) if svc is not None else None

    @property
    def service_name(self) -> str | None:
        """Get the parent NAS service name."""
        return self.get("service_name") or self.get("service_display")

    @property
    def home_share_key(self) -> int | None:
        """Get the home share key."""
        share = self.get("home_share")
        return int(share) if share is not None else None

    @property
    def home_share_name(self) -> str | None:
        """Get the home share name."""
        return self.get("home_share_display")

    @property
    def home_drive(self) -> str | None:
        """Get the home drive letter."""
        return self.get("home_drive")

    @property
    def displayname(self) -> str | None:
        """Get the display name."""
        return self.get("displayname")

    @property
    def is_enabled(self) -> bool:
        """Check if the user account is enabled."""
        return bool(self.get("enabled", False))

    @property
    def status(self) -> str | None:
        """Get the user status (online=Enabled, offline=Disabled, error=Error)."""
        return self.get("status_value") or self.get("status")

    @property
    def status_display(self) -> str:
        """Get the user status as a human-readable string."""
        status = self.status
        status_map = {
            "online": "Enabled",
            "offline": "Disabled",
            "error": "Error",
        }
        return status_map.get(status or "", status or "Unknown")

    @property
    def user_sid(self) -> str | None:
        """Get the Windows SID."""
        return self.get("user_sid")

    @property
    def group_sid(self) -> str | None:
        """Get the group SID."""
        return self.get("group_sid")

    @property
    def user_id(self) -> int | None:
        """Get the Unix UID."""
        uid = self.get("user_id")
        return int(uid) if uid is not None else None

    @property
    def group_id(self) -> int | None:
        """Get the Unix GID."""
        gid = self.get("group_id")
        return int(gid) if gid is not None else None


class NASUserManager(ResourceManager["NASUser"]):
    """Manager for NAS local user operations.

    NAS local users are used for CIFS/SMB authentication when not using
    Active Directory integration.

    Example:
        >>> # List all users on a NAS service
        >>> for user in client.nas_users.list(service=1):
        ...     print(f"{user.name}: {'Enabled' if user.is_enabled else 'Disabled'}")

        >>> # Create a user
        >>> user = client.nas_users.create(
        ...     service=1,
        ...     name="backup",
        ...     password="SecurePass123!"
        ... )

        >>> # Enable/disable users
        >>> client.nas_users.disable(user.key)
        >>> client.nas_users.enable(user.key)
    """

    _endpoint = "vm_service_users"

    # Default fields for list operations
    _default_fields = [
        "$key",
        "name",
        "enabled",
        "displayname",
        "description",
        "home_share",
        "display(home_share) as home_share_display",
        "home_drive",
        "created",
        "service",
        "service#$display as service_display",
        "service#name as service_name",
        "status#status as status_value",
        "status#status_info as status_info",
        "status#user_sid as user_sid",
        "status#group_sid as group_sid",
        "status#user_id as user_id",
        "status#group_id as group_id",
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
    ) -> builtins.list[NASUser]:
        """List NAS local users with optional filtering.

        Args:
            filter: OData filter string.
            fields: List of fields to return (uses defaults if not specified).
            limit: Maximum number of results.
            offset: Skip this many results.
            service: Filter by NAS service (key or name).
            enabled: Filter by enabled state.
            **filter_kwargs: Shorthand filter arguments (name, etc.).

        Returns:
            List of NASUser objects.

        Example:
            >>> # List all users for a NAS service
            >>> users = client.nas_users.list(service=1)

            >>> # List enabled users only
            >>> users = client.nas_users.list(service=1, enabled=True)

            >>> # List by name pattern
            >>> users = client.nas_users.list(service=1, name="backup")
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
            service_key = self._resolve_service_key(service)
            if service_key is not None:
                filters.append(f"service eq {service_key}")

        # Add enabled filter
        if enabled is not None:
            filters.append(f"enabled eq {str(enabled).lower()}")

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
    ) -> NASUser:
        """Get a single NAS user by key or name.

        Args:
            key: User $key (40-character hex string).
            name: Username (requires service if not unique).
            service: NAS service key or name (required when looking up by name).
            fields: List of fields to return.

        Returns:
            NASUser object.

        Raises:
            NotFoundError: If user not found.
            ValueError: If no identifier provided or name without service.

        Example:
            >>> # Get by key
            >>> user = client.nas_users.get("abc123...")

            >>> # Get by name on a service
            >>> user = client.nas_users.get(name="backup", service=1)
        """
        if key is not None:
            # Fetch by key using filter (keys are hex strings)
            params: dict[str, Any] = {
                "filter": f"$key eq '{key}'",
            }
            if fields:
                params["fields"] = ",".join(fields)
            else:
                params["fields"] = ",".join(self._default_fields)

            response = self._client._request("GET", self._endpoint, params=params)

            if response is None:
                raise NotFoundError(f"NAS user with key {key} not found")
            if isinstance(response, list):
                if not response:
                    raise NotFoundError(f"NAS user with key {key} not found")
                response = response[0]
            if not isinstance(response, dict):
                raise NotFoundError(f"NAS user with key {key} returned invalid response")
            return self._to_model(response)

        if name is not None:
            if service is None:
                raise ValueError("service is required when looking up by name")

            # Resolve service key
            service_key = self._resolve_service_key(service)
            if service_key is None:
                raise NotFoundError(f"NAS service '{service}' not found")

            # Search by name and service
            escaped_name = name.replace("'", "''")
            filter_str = f"service eq {service_key} and name eq '{escaped_name}'"

            results = self.list(filter=filter_str, fields=fields, limit=1)
            if not results:
                raise NotFoundError(f"NAS user '{name}' not found on service {service}")
            return results[0]

        raise ValueError("Either key or name must be provided")

    def create(  # type: ignore[override]
        self,
        service: int | str,
        name: str,
        password: str,
        *,
        displayname: str | None = None,
        description: str | None = None,
        home_share: str | int | None = None,
        home_drive: str | None = None,
        enabled: bool = True,
    ) -> NASUser:
        """Create a new NAS local user.

        Args:
            service: NAS service key or name.
            name: Username (1-32 chars, starts with letter, alphanumeric/underscore/hyphen).
            password: User password.
            displayname: Display name for the user.
            description: User description.
            home_share: Home share key or name (CIFS share on this NAS service).
            home_drive: Home drive letter (single letter A-Z, e.g., "H").
            enabled: Enable the user account (default True).

        Returns:
            Created NASUser object.

        Raises:
            ValueError: If service not found.

        Example:
            >>> # Create a basic user
            >>> user = client.nas_users.create(
            ...     service=1,
            ...     name="backup",
            ...     password="SecurePass123!"
            ... )

            >>> # Create with home share
            >>> user = client.nas_users.create(
            ...     service=1,
            ...     name="admin",
            ...     password="AdminPass!",
            ...     displayname="Administrator",
            ...     home_share="AdminDocs",
            ...     home_drive="H"
            ... )
        """
        # Resolve service to key
        service_key = self._resolve_service_key(service)
        if service_key is None:
            raise ValueError(f"NAS service '{service}' not found")

        # Build request body
        body: dict[str, Any] = {
            "service": service_key,
            "name": name,
            "password": password,
            "enabled": enabled,
        }

        if displayname:
            body["displayname"] = displayname

        if description:
            body["description"] = description

        # Resolve home share if specified
        if home_share is not None:
            home_share_key = self._resolve_cifs_share_key(home_share, service_key)
            if home_share_key is not None:
                body["home_share"] = home_share_key

        if home_drive:
            body["home_drive"] = home_drive.upper()

        response = self._client._request("POST", self._endpoint, json_data=body)

        # Get the created user
        if response and isinstance(response, dict):
            user_key = response.get("$key") or response.get("id")
            if user_key:
                return self.get(key=str(user_key))

        # Fallback: search by name and service
        return self.get(name=name, service=service_key)

    def update(  # type: ignore[override]
        self,
        key: str,
        *,
        password: str | None = None,
        displayname: str | None = None,
        description: str | None = None,
        home_share: str | int | None = None,
        home_drive: str | None = None,
        enabled: bool | None = None,
    ) -> NASUser:
        """Update a NAS user.

        Args:
            key: User $key (40-character hex string).
            password: New password.
            displayname: New display name.
            description: New description.
            home_share: New home share key or name (empty string to clear).
            home_drive: New home drive letter (empty string to clear).
            enabled: Enable or disable the user.

        Returns:
            Updated NASUser object.

        Example:
            >>> # Change password
            >>> client.nas_users.update(user.key, password="NewPass123!")

            >>> # Update display name
            >>> client.nas_users.update(user.key, displayname="Backup User")

            >>> # Disable user
            >>> client.nas_users.update(user.key, enabled=False)
        """
        body: dict[str, Any] = {}

        if password is not None:
            body["password"] = password

        if displayname is not None:
            body["displayname"] = displayname

        if description is not None:
            body["description"] = description

        if home_share is not None:
            if home_share == "" or home_share == 0:
                # Clear the home share
                body["home_share"] = None
            else:
                # Get the user's service to resolve the share
                user = self.get(key)
                if user.service_key:
                    home_share_key = self._resolve_cifs_share_key(home_share, user.service_key)
                    if home_share_key is not None:
                        body["home_share"] = home_share_key

        if home_drive is not None:
            body["home_drive"] = home_drive.upper() if home_drive else ""

        if enabled is not None:
            body["enabled"] = enabled

        if not body:
            return self.get(key)

        self._client._request("PUT", f"{self._endpoint}/{key}", json_data=body)
        return self.get(key)

    def delete(self, key: str) -> None:  # type: ignore[override]
        """Delete a NAS user.

        This permanently removes the user account.

        Args:
            key: User $key (40-character hex string).

        Example:
            >>> client.nas_users.delete(user.key)
        """
        self._client._request("DELETE", f"{self._endpoint}/{key}")

    def enable(self, key: str) -> NASUser:
        """Enable a NAS user account.

        Args:
            key: User $key (40-character hex string).

        Returns:
            Updated NASUser object.

        Example:
            >>> client.nas_users.enable(user.key)
        """
        return self.update(key, enabled=True)

    def disable(self, key: str) -> NASUser:
        """Disable a NAS user account.

        Args:
            key: User $key (40-character hex string).

        Returns:
            Updated NASUser object.

        Example:
            >>> client.nas_users.disable(user.key)
        """
        return self.update(key, enabled=False)

    def _resolve_service_key(self, service: int | str) -> int | None:
        """Resolve a NAS service identifier to its key.

        Args:
            service: Service key (int) or name (str).

        Returns:
            Service key as integer, or None if not found.
        """
        if isinstance(service, int):
            return service

        # Look up by name in vm_services endpoint (NAS services are stored there)
        response = self._client._request(
            "GET",
            "vm_services",
            params={
                "filter": f"name eq '{service}'",
                "fields": "$key,name",
                "limit": "1",
            },
        )
        if response:
            if isinstance(response, list):
                response = response[0] if response else None
            if response:
                return response.get("$key")
        return None

    def _resolve_cifs_share_key(
        self, share: int | str, service_key: int
    ) -> int | None:
        """Resolve a CIFS share identifier to its key.

        Args:
            share: Share key (int) or name (str).
            service_key: NAS service key to search within.

        Returns:
            Share key as integer, or None if not found.
        """
        if isinstance(share, int):
            return share

        # Look up by name within the service's volumes
        response = self._client._request(
            "GET",
            "volume_cifs_shares",
            params={
                "filter": f"volume#service eq {service_key} and name eq '{share}'",
                "fields": "$key,name",
                "limit": "1",
            },
        )
        if response:
            if isinstance(response, list):
                response = response[0] if response else None
            if response:
                return response.get("$key")
        return None

    def _to_model(self, data: dict[str, Any]) -> NASUser:
        """Convert API response to NASUser object."""
        return NASUser(data, self)
