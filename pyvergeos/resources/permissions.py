"""Permission resource manager for VergeOS permissions."""

from __future__ import annotations

import builtins
from typing import TYPE_CHECKING, Any

from pyvergeos.exceptions import NotFoundError
from pyvergeos.filters import build_filter
from pyvergeos.resources.base import ResourceManager, ResourceObject

if TYPE_CHECKING:
    from pyvergeos.client import VergeClient
    from pyvergeos.resources.groups import Group
    from pyvergeos.resources.users import User


class Permission(ResourceObject):
    """Permission resource object.

    Represents a permission grant in VergeOS that controls access to
    resources for users or groups.

    Attributes:
        key: Permission primary key ($key).
        identity_key: Identity key (links to user or group identity).
        identity_name: Display name of the identity (user/group name).
        table: Resource table name (e.g., 'vms', 'vnets', '/').
        row_key: Specific row key (0 for table-level access).
        row_display: Display name of the row (if row-specific).
        is_table_level: Whether this is table-level (all rows) permission.
        can_list: Whether list/see permission is granted.
        can_read: Whether read permission is granted.
        can_create: Whether create permission is granted.
        can_modify: Whether modify permission is granted.
        can_delete: Whether delete permission is granted.
    """

    @property
    def identity_key(self) -> int:
        """Get the identity key."""
        return int(self.get("identity", 0))

    @property
    def identity_name(self) -> str | None:
        """Get the identity display name (user/group name)."""
        return self.get("identity_display")

    @property
    def table(self) -> str:
        """Get the resource table name."""
        return str(self.get("table", ""))

    @property
    def row_key(self) -> int:
        """Get the row key (0 for table-level access)."""
        return int(self.get("row", 0))

    @property
    def row_display(self) -> str | None:
        """Get the row display name (if row-specific)."""
        return self.get("rowdisplay")

    @property
    def is_table_level(self) -> bool:
        """Check if this is a table-level permission (applies to all rows)."""
        return self.row_key == 0

    @property
    def can_list(self) -> bool:
        """Check if list permission is granted."""
        return bool(self.get("list", False))

    @property
    def can_read(self) -> bool:
        """Check if read permission is granted."""
        return bool(self.get("read", False))

    @property
    def can_create(self) -> bool:
        """Check if create permission is granted."""
        return bool(self.get("create", False))

    @property
    def can_modify(self) -> bool:
        """Check if modify permission is granted."""
        return bool(self.get("modify", False))

    @property
    def can_delete(self) -> bool:
        """Check if delete permission is granted."""
        return bool(self.get("delete", False))

    @property
    def has_full_control(self) -> bool:
        """Check if all permissions are granted (full control)."""
        return (
            self.can_list
            and self.can_read
            and self.can_create
            and self.can_modify
            and self.can_delete
        )

    def revoke(self) -> None:
        """Revoke this permission.

        Raises:
            ValueError: If permission key is not available.
        """
        from typing import cast

        manager = cast("PermissionManager", self._manager)
        manager.revoke(self.key)


class PermissionManager(ResourceManager[Permission]):
    """Manager for VergeOS permission operations.

    Provides operations to list, grant, and revoke permissions for users
    and groups on resources.

    Example:
        >>> # List all permissions for a user
        >>> perms = client.permissions.list(user=user.key)

        >>> # List permissions for a group on VMs
        >>> perms = client.permissions.list(group=group.key, table="vms")

        >>> # Grant read-only access to VMs
        >>> client.permissions.grant(
        ...     user=user.key,
        ...     table="vms",
        ...     can_list=True,
        ...     can_read=True
        ... )

        >>> # Grant full control to a group
        >>> client.permissions.grant(
        ...     group=group.key,
        ...     table="vms",
        ...     full_control=True
        ... )

        >>> # Revoke a permission
        >>> client.permissions.revoke(permission.key)
    """

    _endpoint = "permissions"

    # Default fields for list operations (matches PowerShell module)
    _default_fields = [
        "$key",
        "identity",
        "identity#owner#$display as identity_display",
        "table",
        "rowdisplay",
        "row",
        "list",
        "read",
        "create",
        "modify",
        "delete",
    ]

    def __init__(self, client: VergeClient) -> None:
        super().__init__(client)

    def _to_model(self, data: dict[str, Any]) -> Permission:
        """Convert API response to Permission object."""
        return Permission(data, self)

    def _resolve_identity(
        self,
        user: int | User | None = None,
        group: int | Group | None = None,
        identity_key: int | None = None,
    ) -> int | None:
        """Resolve user/group to identity key.

        Args:
            user: User key or User object.
            group: Group key or Group object.
            identity_key: Direct identity key.

        Returns:
            Identity key or None if not resolved.
        """
        if identity_key is not None:
            return identity_key

        if user is not None:
            # If it's a User object, get the identity directly
            if hasattr(user, "identity"):
                return user.identity

            # If it's an int, we need to look up the user
            user_obj = self._client.users.get(int(user))
            return user_obj.identity

        if group is not None:
            # If it's a Group object, get the identity directly
            if hasattr(group, "identity"):
                return group.identity

            # If it's an int, we need to look up the group
            group_obj = self._client.groups.get(int(group))
            return group_obj.identity

        return None

    def list(
        self,
        filter: str | None = None,
        fields: builtins.list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        user: int | User | None = None,
        group: int | Group | None = None,
        identity_key: int | None = None,
        table: str | None = None,
        **filter_kwargs: Any,
    ) -> builtins.list[Permission]:
        """List permissions with optional filtering.

        Args:
            filter: OData filter string.
            fields: List of fields to return (uses defaults if not specified).
            limit: Maximum number of results.
            offset: Skip this many results.
            user: User key or User object to filter by.
            group: Group key or Group object to filter by.
            identity_key: Identity key to filter by directly.
            table: Resource table name to filter by (e.g., 'vms', 'vnets').
            **filter_kwargs: Shorthand filter arguments.

        Returns:
            List of Permission objects.

        Example:
            >>> # List all permissions
            >>> perms = client.permissions.list()

            >>> # List permissions for a user
            >>> perms = client.permissions.list(user=user.key)

            >>> # List permissions for a group on VMs
            >>> perms = client.permissions.list(group=group.key, table="vms")

            >>> # List permissions by identity key directly
            >>> perms = client.permissions.list(identity_key=123)
        """
        params: dict[str, Any] = {}

        # Build filter
        filters: builtins.list[str] = []

        if filter:
            filters.append(filter)
        if filter_kwargs:
            filters.append(build_filter(**filter_kwargs))

        # Resolve identity from user/group
        resolved_identity = self._resolve_identity(user, group, identity_key)
        if resolved_identity is not None:
            filters.append(f"identity eq {resolved_identity}")

        # Add table filter
        if table is not None:
            escaped_table = table.replace("'", "''")
            filters.append(f"table eq '{escaped_table}'")

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
        key: int,
        *,
        fields: builtins.list[str] | None = None,
    ) -> Permission:
        """Get a single permission by key.

        Args:
            key: Permission $key (ID).
            fields: List of fields to return.

        Returns:
            Permission object.

        Raises:
            NotFoundError: If permission not found.

        Example:
            >>> perm = client.permissions.get(123)
        """
        params: dict[str, Any] = {}
        if fields:
            params["fields"] = ",".join(fields)
        else:
            params["fields"] = ",".join(self._default_fields)

        response = self._client._request("GET", f"{self._endpoint}/{key}", params=params)
        if response is None:
            raise NotFoundError(f"Permission with key {key} not found")
        if not isinstance(response, dict):
            raise NotFoundError(f"Permission with key {key} returned invalid response")
        return self._to_model(response)

    def grant(
        self,
        table: str,
        *,
        user: int | User | None = None,
        group: int | Group | None = None,
        identity_key: int | None = None,
        row_key: int = 0,
        can_list: bool = True,
        can_read: bool = False,
        can_create: bool = False,
        can_modify: bool = False,
        can_delete: bool = False,
        full_control: bool = False,
    ) -> Permission:
        """Grant permission to a user or group.

        Args:
            table: Resource table to grant access to (e.g., 'vms', 'vnets', '/').
            user: User key or User object to grant to.
            group: Group key or Group object to grant to.
            identity_key: Identity key to grant to directly.
            row_key: Specific row key (0 for table-level access to all rows).
            can_list: Grant permission to list/see items. Default True.
            can_read: Grant permission to read item details. Default False.
            can_create: Grant permission to create new items. Default False.
            can_modify: Grant permission to modify existing items. Default False.
            can_delete: Grant permission to delete items. Default False.
            full_control: Grant all permissions (overrides individual flags).

        Returns:
            Created Permission object.

        Raises:
            ValueError: If no user, group, or identity_key provided.
            ConflictError: If permission already exists.

        Example:
            >>> # Grant read-only access to VMs for a user
            >>> perm = client.permissions.grant(
            ...     table="vms",
            ...     user=user.key,
            ...     can_list=True,
            ...     can_read=True
            ... )

            >>> # Grant full control to a group
            >>> perm = client.permissions.grant(
            ...     table="vms",
            ...     group=group.key,
            ...     full_control=True
            ... )

            >>> # Grant root access (all resources)
            >>> perm = client.permissions.grant(
            ...     table="/",
            ...     user=user.key,
            ...     can_list=True,
            ...     can_read=True
            ... )

            >>> # Grant access to a specific VM only
            >>> perm = client.permissions.grant(
            ...     table="vms",
            ...     user=user.key,
            ...     row_key=vm.key,
            ...     full_control=True
            ... )
        """
        # Resolve identity
        resolved_identity = self._resolve_identity(user, group, identity_key)
        if resolved_identity is None:
            raise ValueError("Either user, group, or identity_key must be provided")

        # Build request body
        body: dict[str, Any] = {
            "identity": resolved_identity,
            "table": table,
            "row": row_key,
        }

        # Set permission flags
        if full_control:
            body["list"] = True
            body["read"] = True
            body["create"] = True
            body["modify"] = True
            body["delete"] = True
        else:
            body["list"] = can_list
            body["read"] = can_read
            body["create"] = can_create
            body["modify"] = can_modify
            body["delete"] = can_delete

        response = self._client._request("POST", self._endpoint, json_data=body)

        # Get the created permission
        if response and isinstance(response, dict):
            perm_key = response.get("$key")
            if perm_key:
                return self.get(key=int(perm_key))

        # Fallback: search by identity and table
        perms = self.list(identity_key=resolved_identity, table=table)
        if perms:
            # Find the one with matching row
            for p in perms:
                if p.row_key == row_key:
                    return p
            # If no exact row match, return the first one
            return perms[0]

        raise NotFoundError("Failed to retrieve created permission")

    def revoke(self, key: int) -> None:
        """Revoke (delete) a permission.

        Args:
            key: Permission $key (ID) to revoke.

        Example:
            >>> client.permissions.revoke(perm.key)
        """
        self._client._request("DELETE", f"{self._endpoint}/{key}")

    def revoke_for_user(
        self,
        user: int | User,
        table: str | None = None,
    ) -> int:
        """Revoke all permissions for a user, optionally filtered by table.

        Args:
            user: User key or User object.
            table: Optional table name to filter by.

        Returns:
            Number of permissions revoked.

        Example:
            >>> # Revoke all permissions for user
            >>> count = client.permissions.revoke_for_user(user.key)

            >>> # Revoke only VM permissions for user
            >>> count = client.permissions.revoke_for_user(user.key, table="vms")
        """
        perms = self.list(user=user, table=table)
        count = 0
        for perm in perms:
            self.revoke(perm.key)
            count += 1
        return count

    def revoke_for_group(
        self,
        group: int | Group,
        table: str | None = None,
    ) -> int:
        """Revoke all permissions for a group, optionally filtered by table.

        Args:
            group: Group key or Group object.
            table: Optional table name to filter by.

        Returns:
            Number of permissions revoked.

        Example:
            >>> # Revoke all permissions for group
            >>> count = client.permissions.revoke_for_group(group.key)

            >>> # Revoke only network permissions for group
            >>> count = client.permissions.revoke_for_group(group.key, table="vnets")
        """
        perms = self.list(group=group, table=table)
        count = 0
        for perm in perms:
            self.revoke(perm.key)
            count += 1
        return count
