"""Group resource manager for VergeOS groups."""

from __future__ import annotations

import builtins
from typing import TYPE_CHECKING, Any

from pyvergeos.exceptions import NotFoundError
from pyvergeos.filters import build_filter
from pyvergeos.resources.base import ResourceManager, ResourceObject

if TYPE_CHECKING:
    from pyvergeos.client import VergeClient


class GroupMember(ResourceObject):
    """Group member resource object.

    Represents a membership record linking a user or group to a parent group.

    Attributes:
        key: Membership primary key ($key).
        group_key: Parent group key.
        member_type: Type of member ('User' or 'Group').
        member_key: Key of the member (user or group).
        member_name: Display name of the member.
        member_ref: API reference to the member.
        creator: Username of who created this membership.
    """

    @property
    def group_key(self) -> int:
        """Get the parent group key."""
        return int(self.get("parent_group", 0))

    @property
    def member_ref(self) -> str:
        """Get the member API reference (e.g., '/v4/users/1')."""
        return str(self.get("member", ""))

    @property
    def member_type(self) -> str:
        """Get the member type ('User' or 'Group')."""
        ref = self.member_ref
        if "/users/" in ref:
            return "User"
        elif "/groups/" in ref:
            return "Group"
        return "Unknown"

    @property
    def member_key(self) -> int | None:
        """Get the member key (user or group ID)."""
        ref = self.member_ref
        # Parse reference like "/v4/users/1" or "/v4/groups/2"
        if "/users/" in ref:
            try:
                return int(ref.split("/users/")[1])
            except (ValueError, IndexError):
                return None
        elif "/groups/" in ref:
            try:
                return int(ref.split("/groups/")[1])
            except (ValueError, IndexError):
                return None
        return None

    @property
    def member_name(self) -> str | None:
        """Get the member display name."""
        return self.get("member_display")

    @property
    def creator(self) -> str | None:
        """Get the username of who created this membership."""
        return self.get("creator")

    def remove(self) -> None:
        """Remove this member from the group.

        Raises:
            ValueError: If membership key is not available.
        """
        from typing import cast

        manager = cast("GroupMemberManager", self._manager)
        manager.remove(self.key)


class GroupMemberManager(ResourceManager[GroupMember]):
    """Manager for group membership operations.

    This manager handles adding and removing users/groups from a parent group.
    It can be accessed via group.members or directly via client.groups.members().

    Example:
        >>> # List members of a group
        >>> for member in client.groups.members(group_key).list():
        ...     print(f"{member.member_name} ({member.member_type})")

        >>> # Add a user to a group
        >>> client.groups.members(group_key).add_user(user_key)

        >>> # Remove a member
        >>> client.groups.members(group_key).remove(membership_key)
    """

    _endpoint = "members"

    def __init__(self, client: VergeClient, group_key: int) -> None:
        super().__init__(client)
        self._group_key = group_key

    def _to_model(self, data: dict[str, Any]) -> GroupMember:
        """Convert API response to GroupMember object."""
        return GroupMember(data, self)

    def list(
        self,
        filter: str | None = None,
        fields: builtins.list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        **filter_kwargs: Any,
    ) -> builtins.list[GroupMember]:
        """List members of this group.

        Args:
            filter: OData filter string.
            fields: List of fields to return.
            limit: Maximum number of results.
            offset: Skip this many results.
            **filter_kwargs: Additional filter arguments.

        Returns:
            List of GroupMember objects.

        Example:
            >>> members = client.groups.members(group_key).list()
            >>> for m in members:
            ...     print(f"{m.member_name}: {m.member_type}")
        """
        params: dict[str, Any] = {}

        # Build filter - always filter by parent group
        filters: builtins.list[str] = [f"parent_group eq {self._group_key}"]

        if filter:
            filters.append(filter)
        if filter_kwargs:
            filters.append(build_filter(**filter_kwargs))

        params["filter"] = " and ".join(filters)

        # Default fields
        if fields:
            params["fields"] = ",".join(fields)
        else:
            params["fields"] = "$key,parent_group,member,member#$display as member_display,creator"

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

    def add_user(self, user_key: int) -> GroupMember:
        """Add a user to this group.

        Args:
            user_key: User $key (ID) to add.

        Returns:
            Created GroupMember object with full details.

        Raises:
            ConflictError: If user is already a member.

        Example:
            >>> member = client.groups.members(group_key).add_user(user.key)
        """
        body = {
            "parent_group": self._group_key,
            "member": f"/v4/users/{user_key}",
        }

        self._client._request("POST", self._endpoint, json_data=body)

        # Fetch the created membership with full details
        members = self.list()
        for m in members:
            if m.member_type == "User" and m.member_key == user_key:
                return m

        raise ValueError("Failed to add user to group")

    def add_group(self, member_group_key: int) -> GroupMember:
        """Add a group as a member of this group (nested group).

        Args:
            member_group_key: Group $key (ID) to add as member.

        Returns:
            Created GroupMember object with full details.

        Raises:
            ConflictError: If group is already a member.

        Example:
            >>> # Add Developers group to AllUsers group
            >>> member = client.groups.members(all_users_key).add_group(developers_key)
        """
        body = {
            "parent_group": self._group_key,
            "member": f"/v4/groups/{member_group_key}",
        }

        self._client._request("POST", self._endpoint, json_data=body)

        # Fetch the created membership with full details
        members = self.list()
        for m in members:
            if m.member_type == "Group" and m.member_key == member_group_key:
                return m

        raise ValueError("Failed to add group to group")

    def remove(self, membership_key: int) -> None:
        """Remove a membership by its key.

        Args:
            membership_key: Membership $key (ID) to remove.

        Example:
            >>> client.groups.members(group_key).remove(membership.key)
        """
        self._client._request("DELETE", f"{self._endpoint}/{membership_key}")

    def remove_user(self, user_key: int) -> None:
        """Remove a user from this group.

        Args:
            user_key: User $key (ID) to remove.

        Raises:
            NotFoundError: If user is not a member of this group.

        Example:
            >>> client.groups.members(group_key).remove_user(user.key)
        """
        members = self.list()
        for m in members:
            if m.member_type == "User" and m.member_key == user_key:
                self.remove(m.key)
                return

        raise NotFoundError(f"User {user_key} is not a member of group {self._group_key}")

    def remove_group(self, member_group_key: int) -> None:
        """Remove a group from this group.

        Args:
            member_group_key: Group $key (ID) to remove.

        Raises:
            NotFoundError: If group is not a member of this group.

        Example:
            >>> client.groups.members(parent_key).remove_group(child_key)
        """
        members = self.list()
        for m in members:
            if m.member_type == "Group" and m.member_key == member_group_key:
                self.remove(m.key)
                return

        raise NotFoundError(
            f"Group {member_group_key} is not a member of group {self._group_key}"
        )


class Group(ResourceObject):
    """Group resource object.

    Represents a group in VergeOS that can contain users and other groups.
    Groups are used for organizing users and assigning permissions.

    Attributes:
        key: Group primary key ($key).
        name: Group name.
        description: Group description.
        enabled: Whether the group is enabled.
        email: Group email address.
        identifier: Group identifier (id field).
        identity: Identity key.
        is_system_group: Whether this is a system group.
        member_count: Number of members in the group.
        created: Creation timestamp (Unix epoch).
        creator: Username of who created this group.
    """

    @property
    def description(self) -> str | None:
        """Get the group description."""
        return self.get("description")

    @property
    def is_enabled(self) -> bool:
        """Check if group is enabled."""
        return bool(self.get("enabled", True))

    @property
    def email(self) -> str | None:
        """Get the group email address."""
        return self.get("email")

    @property
    def identifier(self) -> str | None:
        """Get the group identifier."""
        return self.get("id")

    @property
    def identity(self) -> int | None:
        """Get the identity key."""
        val = self.get("identity")
        return int(val) if val is not None else None

    @property
    def is_system_group(self) -> bool:
        """Check if this is a system group."""
        return bool(self.get("system_group", False))

    @property
    def member_count(self) -> int:
        """Get the number of members in the group."""
        return int(self.get("member_count", 0))

    @property
    def created(self) -> int | None:
        """Get the creation timestamp (Unix epoch)."""
        val = self.get("created")
        return int(val) if val is not None else None

    @property
    def creator(self) -> str | None:
        """Get the username of who created this group."""
        return self.get("creator")

    @property
    def members(self) -> GroupMemberManager:
        """Access group member operations for this group.

        Returns:
            GroupMemberManager for this group.

        Example:
            >>> # List members
            >>> for member in group.members.list():
            ...     print(member.member_name)

            >>> # Add a user
            >>> group.members.add_user(user.key)
        """
        from typing import cast

        manager = cast("GroupManager", self._manager)
        return manager.members(self.key)

    def enable(self) -> Group:
        """Enable this group.

        Returns:
            Updated Group object.
        """
        from typing import cast

        manager = cast("GroupManager", self._manager)
        return manager.enable(self.key)

    def disable(self) -> Group:
        """Disable this group.

        Returns:
            Updated Group object.
        """
        from typing import cast

        manager = cast("GroupManager", self._manager)
        return manager.disable(self.key)


class GroupManager(ResourceManager[Group]):
    """Manager for VergeOS group operations.

    Provides CRUD operations and management for groups.

    Example:
        >>> # List all groups
        >>> for group in client.groups.list():
        ...     print(f"{group.name}: {group.member_count} members")

        >>> # List only enabled groups
        >>> enabled_groups = client.groups.list(enabled=True)

        >>> # Create a group
        >>> group = client.groups.create(
        ...     name="Developers",
        ...     description="Development team",
        ...     email="dev@company.com"
        ... )

        >>> # Enable/disable groups
        >>> client.groups.disable(group.key)
        >>> client.groups.enable(group.key)

        >>> # Manage members
        >>> client.groups.members(group.key).add_user(user.key)
    """

    _endpoint = "groups"

    # Default fields for list operations (matches PowerShell module)
    _default_fields = [
        "$key",
        "name",
        "description",
        "enabled",
        "created",
        "email",
        "id",
        "identity",
        "system_group",
        "creator",
        "count(members) as member_count",
    ]

    def __init__(self, client: VergeClient) -> None:
        super().__init__(client)

    def _to_model(self, data: dict[str, Any]) -> Group:
        """Convert API response to Group object."""
        return Group(data, self)

    def list(
        self,
        filter: str | None = None,
        fields: builtins.list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        enabled: bool | None = None,
        include_system: bool = True,
        **filter_kwargs: Any,
    ) -> builtins.list[Group]:
        """List groups with optional filtering.

        Args:
            filter: OData filter string.
            fields: List of fields to return (uses defaults if not specified).
            limit: Maximum number of results.
            offset: Skip this many results.
            enabled: Filter by enabled status.
            include_system: Include system groups (default True).
            **filter_kwargs: Shorthand filter arguments (name, etc.).

        Returns:
            List of Group objects.

        Example:
            >>> # List all groups
            >>> groups = client.groups.list()

            >>> # List only enabled groups
            >>> enabled = client.groups.list(enabled=True)

            >>> # List non-system groups only
            >>> user_groups = client.groups.list(include_system=False)

            >>> # List by name pattern (exact match)
            >>> groups = client.groups.list(name="Administrators")
        """
        params: dict[str, Any] = {}

        # Build filter
        filters: builtins.list[str] = []

        # Exclude system groups if requested
        if not include_system:
            filters.append("system_group eq false")

        if filter:
            filters.append(filter)
        if filter_kwargs:
            filters.append(build_filter(**filter_kwargs))

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

    def list_enabled(self) -> builtins.list[Group]:
        """List all enabled groups.

        Returns:
            List of enabled Group objects.
        """
        return self.list(enabled=True)

    def list_disabled(self) -> builtins.list[Group]:
        """List all disabled groups.

        Returns:
            List of disabled Group objects.
        """
        return self.list(enabled=False)

    def get(
        self,
        key: int | None = None,
        *,
        name: str | None = None,
        fields: builtins.list[str] | None = None,
    ) -> Group:
        """Get a single group by key or name.

        Args:
            key: Group $key (ID).
            name: Group name.
            fields: List of fields to return.

        Returns:
            Group object.

        Raises:
            NotFoundError: If group not found.
            ValueError: If neither key nor name provided.

        Example:
            >>> # Get by key
            >>> group = client.groups.get(123)

            >>> # Get by name
            >>> group = client.groups.get(name="Administrators")
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
                raise NotFoundError(f"Group with key {key} not found")
            if not isinstance(response, dict):
                raise NotFoundError(f"Group with key {key} returned invalid response")
            return self._to_model(response)

        if name is not None:
            # Search by name
            escaped_name = name.replace("'", "''")
            results = self.list(filter=f"name eq '{escaped_name}'", fields=fields, limit=1)
            if not results:
                raise NotFoundError(f"Group '{name}' not found")
            return results[0]

        raise ValueError("Either key or name must be provided")

    def create(  # type: ignore[override]
        self,
        name: str,
        *,
        description: str | None = None,
        email: str | None = None,
        enabled: bool = True,
    ) -> Group:
        """Create a new group.

        Args:
            name: Group name (1-128 characters, must be unique).
            description: Group description (optional).
            email: Group email address (optional).
            enabled: Whether the group is enabled (default True).

        Returns:
            Created Group object.

        Example:
            >>> # Create a basic group
            >>> group = client.groups.create(name="Developers")

            >>> # Create with all options
            >>> group = client.groups.create(
            ...     name="QA Team",
            ...     description="Quality Assurance team",
            ...     email="qa@company.com"
            ... )
        """
        body: dict[str, Any] = {
            "name": name,
            "enabled": enabled,
        }

        if description:
            body["description"] = description

        if email:
            body["email"] = email.lower()

        response = self._client._request("POST", self._endpoint, json_data=body)

        # Get the created group
        if response and isinstance(response, dict):
            group_key = response.get("$key")
            if group_key:
                return self.get(key=int(group_key))

        # Fallback: search by name
        return self.get(name=name)

    def update(  # type: ignore[override]
        self,
        key: int,
        *,
        name: str | None = None,
        description: str | None = None,
        email: str | None = None,
        enabled: bool | None = None,
    ) -> Group:
        """Update a group.

        Args:
            key: Group $key (ID).
            name: New group name.
            description: New description.
            email: New email address.
            enabled: Enable or disable the group.

        Returns:
            Updated Group object.

        Example:
            >>> # Update description
            >>> client.groups.update(group.key, description="New description")

            >>> # Rename group
            >>> client.groups.update(group.key, name="NewName")
        """
        body: dict[str, Any] = {}

        if name is not None:
            body["name"] = name

        if description is not None:
            body["description"] = description

        if email is not None:
            body["email"] = email.lower() if email else ""

        if enabled is not None:
            body["enabled"] = enabled

        if not body:
            return self.get(key)

        self._client._request("PUT", f"{self._endpoint}/{key}", json_data=body)
        return self.get(key)

    def enable(self, key: int) -> Group:
        """Enable a group.

        Args:
            key: Group $key (ID).

        Returns:
            Updated Group object.

        Example:
            >>> client.groups.enable(group.key)
        """
        return self.update(key, enabled=True)

    def disable(self, key: int) -> Group:
        """Disable a group.

        The group is not deleted and can be re-enabled later.

        Args:
            key: Group $key (ID).

        Returns:
            Updated Group object.

        Example:
            >>> client.groups.disable(group.key)
        """
        return self.update(key, enabled=False)

    def members(self, group_key: int) -> GroupMemberManager:
        """Get a member manager for a specific group.

        Args:
            group_key: Group $key (ID).

        Returns:
            GroupMemberManager for the specified group.

        Example:
            >>> # List members
            >>> members = client.groups.members(group.key).list()

            >>> # Add user to group
            >>> client.groups.members(group.key).add_user(user.key)
        """
        return GroupMemberManager(self._client, group_key)
