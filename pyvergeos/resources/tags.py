"""Tag resource managers for VergeOS tags, categories, and members."""

from __future__ import annotations

import builtins
from typing import TYPE_CHECKING, Any

from pyvergeos.exceptions import NotFoundError
from pyvergeos.filters import build_filter
from pyvergeos.resources.base import ResourceManager, ResourceObject

if TYPE_CHECKING:
    from pyvergeos.client import VergeClient


# Resource type mappings for taggable resources
TAGGABLE_RESOURCE_TYPES: dict[str, str] = {
    "vms": "taggable_vms",
    "vnets": "taggable_vnets",
    "volumes": "taggable_volumes",
    "vnet_rules": "taggable_vnet_rules",
    "vmware_containers": "taggable_vmware_containers",
    "users": "taggable_users",
    "tenant_nodes": "taggable_tenant_nodes",
    "sites": "taggable_sites",
    "nodes": "taggable_nodes",
    "groups": "taggable_groups",
    "clusters": "taggable_clusters",
    "tenants": "taggable_tenants",
}

# Display names for resource types
RESOURCE_TYPE_DISPLAY: dict[str, str] = {
    "vms": "Virtual Machine",
    "vnets": "Network",
    "volumes": "Volume",
    "vnet_rules": "Network Rule",
    "vmware_containers": "VMware Container",
    "users": "User",
    "tenant_nodes": "Tenant Node",
    "sites": "Site",
    "nodes": "Node",
    "groups": "Group",
    "clusters": "Cluster",
    "tenants": "Tenant",
}


class TagMember(ResourceObject):
    """Tag member resource object.

    Represents a membership record linking a resource to a tag.

    Attributes:
        key: Membership primary key ($key).
        tag_key: Parent tag key.
        resource_type: Type of tagged resource (vms, vnets, etc.).
        resource_key: Key of the tagged resource.
        resource_ref: API reference to the resource.
    """

    @property
    def tag_key(self) -> int:
        """Get the parent tag key."""
        return int(self.get("tag", 0))

    @property
    def resource_ref(self) -> str:
        """Get the resource API reference (e.g., 'vms/123')."""
        return str(self.get("member", ""))

    @property
    def resource_type(self) -> str | None:
        """Get the resource type (vms, vnets, tenants, etc.)."""
        ref = self.resource_ref
        if "/" in ref:
            return ref.split("/")[0]
        return None

    @property
    def resource_type_display(self) -> str:
        """Get the display name for the resource type."""
        rtype = self.resource_type
        if rtype:
            return RESOURCE_TYPE_DISPLAY.get(rtype, rtype)
        return "Unknown"

    @property
    def resource_key(self) -> int | None:
        """Get the resource key (ID)."""
        ref = self.resource_ref
        if "/" in ref:
            try:
                return int(ref.split("/")[1])
            except (ValueError, IndexError):
                return None
        return None

    def remove(self) -> None:
        """Remove this tag assignment.

        Raises:
            ValueError: If membership key is not available.
        """
        from typing import cast

        manager = cast("TagMemberManager", self._manager)
        manager.remove(self.key)


class TagMemberManager(ResourceManager[TagMember]):
    """Manager for tag membership operations.

    This manager handles adding and removing resources from a tag.
    It can be accessed via tag.members or directly via client.tags.members().

    Example:
        >>> # List members of a tag
        >>> for member in client.tags.members(tag_key).list():
        ...     print(f"{member.resource_type}: {member.resource_key}")

        >>> # Add a VM to a tag
        >>> client.tags.members(tag_key).add_vm(vm_key)

        >>> # Remove a member
        >>> client.tags.members(tag_key).remove(membership_key)
    """

    _endpoint = "tag_members"

    def __init__(self, client: VergeClient, tag_key: int) -> None:
        super().__init__(client)
        self._tag_key = tag_key

    def _to_model(self, data: dict[str, Any]) -> TagMember:
        """Convert API response to TagMember object."""
        return TagMember(data, self)

    def list(
        self,
        filter: str | None = None,
        fields: builtins.list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        resource_type: str | None = None,
        **filter_kwargs: Any,
    ) -> builtins.list[TagMember]:
        """List members of this tag.

        Args:
            filter: OData filter string.
            fields: List of fields to return.
            limit: Maximum number of results.
            offset: Skip this many results.
            resource_type: Filter by resource type (vms, vnets, tenants, etc.).
            **filter_kwargs: Additional filter arguments.

        Returns:
            List of TagMember objects.

        Example:
            >>> members = client.tags.members(tag_key).list()
            >>> for m in members:
            ...     print(f"{m.resource_type}: {m.resource_key}")

            >>> # List only VMs
            >>> vm_members = client.tags.members(tag_key).list(resource_type="vms")
        """
        params: dict[str, Any] = {}

        # Build filter - always filter by parent tag
        filters: builtins.list[str] = [f"tag eq {self._tag_key}"]

        if filter:
            filters.append(filter)
        if filter_kwargs:
            filters.append(build_filter(**filter_kwargs))

        params["filter"] = " and ".join(filters)

        # Default fields
        if fields:
            params["fields"] = ",".join(fields)
        else:
            params["fields"] = "$key,tag,member"

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

        result = [self._to_model(item) for item in response if item]

        # Filter by resource type if specified
        if resource_type:
            result = [m for m in result if m.resource_type == resource_type]

        return result

    def add(
        self,
        resource_type: str,
        resource_key: int,
    ) -> TagMember:
        """Add a resource to this tag.

        Args:
            resource_type: Type of resource (vms, vnets, tenants, etc.).
            resource_key: Resource $key (ID) to add.

        Returns:
            Created TagMember object.

        Raises:
            ConflictError: If resource is already tagged.

        Example:
            >>> member = client.tags.members(tag_key).add("vms", vm.key)
        """
        body = {
            "tag": self._tag_key,
            "member": f"{resource_type}/{resource_key}",
        }

        response = self._client._request("POST", self._endpoint, json_data=body)

        # Return the created membership
        if response and isinstance(response, dict):
            member_key = response.get("$key")
            if member_key:
                return TagMember(
                    {
                        "$key": member_key,
                        "tag": self._tag_key,
                        "member": f"{resource_type}/{resource_key}",
                    },
                    self,
                )

        # Fallback: fetch from list
        members = self.list(resource_type=resource_type)
        for m in members:
            if m.resource_key == resource_key:
                return m

        raise ValueError("Failed to add resource to tag")

    def add_vm(self, vm_key: int) -> TagMember:
        """Add a VM to this tag.

        Args:
            vm_key: VM $key (ID) to add.

        Returns:
            Created TagMember object.

        Example:
            >>> member = client.tags.members(tag_key).add_vm(vm.key)
        """
        return self.add("vms", vm_key)

    def add_network(self, network_key: int) -> TagMember:
        """Add a network to this tag.

        Args:
            network_key: Network $key (ID) to add.

        Returns:
            Created TagMember object.

        Example:
            >>> member = client.tags.members(tag_key).add_network(network.key)
        """
        return self.add("vnets", network_key)

    def add_tenant(self, tenant_key: int) -> TagMember:
        """Add a tenant to this tag.

        Args:
            tenant_key: Tenant $key (ID) to add.

        Returns:
            Created TagMember object.

        Example:
            >>> member = client.tags.members(tag_key).add_tenant(tenant.key)
        """
        return self.add("tenants", tenant_key)

    def add_user(self, user_key: int) -> TagMember:
        """Add a user to this tag.

        Args:
            user_key: User $key (ID) to add.

        Returns:
            Created TagMember object.

        Example:
            >>> member = client.tags.members(tag_key).add_user(user.key)
        """
        return self.add("users", user_key)

    def add_node(self, node_key: int) -> TagMember:
        """Add a node to this tag.

        Args:
            node_key: Node $key (ID) to add.

        Returns:
            Created TagMember object.

        Example:
            >>> member = client.tags.members(tag_key).add_node(node.key)
        """
        return self.add("nodes", node_key)

    def add_cluster(self, cluster_key: int) -> TagMember:
        """Add a cluster to this tag.

        Args:
            cluster_key: Cluster $key (ID) to add.

        Returns:
            Created TagMember object.

        Example:
            >>> member = client.tags.members(tag_key).add_cluster(cluster.key)
        """
        return self.add("clusters", cluster_key)

    def add_site(self, site_key: int) -> TagMember:
        """Add a site to this tag.

        Args:
            site_key: Site $key (ID) to add.

        Returns:
            Created TagMember object.

        Example:
            >>> member = client.tags.members(tag_key).add_site(site.key)
        """
        return self.add("sites", site_key)

    def add_group(self, group_key: int) -> TagMember:
        """Add a group to this tag.

        Args:
            group_key: Group $key (ID) to add.

        Returns:
            Created TagMember object.

        Example:
            >>> member = client.tags.members(tag_key).add_group(group.key)
        """
        return self.add("groups", group_key)

    def remove(self, membership_key: int) -> None:
        """Remove a membership by its key.

        Args:
            membership_key: Membership $key (ID) to remove.

        Example:
            >>> client.tags.members(tag_key).remove(membership.key)
        """
        self._client._request("DELETE", f"{self._endpoint}/{membership_key}")

    def remove_resource(self, resource_type: str, resource_key: int) -> None:
        """Remove a resource from this tag.

        Args:
            resource_type: Type of resource (vms, vnets, tenants, etc.).
            resource_key: Resource $key (ID) to remove.

        Raises:
            NotFoundError: If resource is not tagged with this tag.

        Example:
            >>> client.tags.members(tag_key).remove_resource("vms", vm.key)
        """
        members = self.list(resource_type=resource_type)
        for m in members:
            if m.resource_key == resource_key:
                self.remove(m.key)
                return

        raise NotFoundError(
            f"Resource {resource_type}/{resource_key} is not tagged with tag {self._tag_key}"
        )

    def remove_vm(self, vm_key: int) -> None:
        """Remove a VM from this tag.

        Args:
            vm_key: VM $key (ID) to remove.

        Raises:
            NotFoundError: If VM is not tagged.

        Example:
            >>> client.tags.members(tag_key).remove_vm(vm.key)
        """
        self.remove_resource("vms", vm_key)

    def remove_network(self, network_key: int) -> None:
        """Remove a network from this tag.

        Args:
            network_key: Network $key (ID) to remove.

        Raises:
            NotFoundError: If network is not tagged.

        Example:
            >>> client.tags.members(tag_key).remove_network(network.key)
        """
        self.remove_resource("vnets", network_key)

    def remove_tenant(self, tenant_key: int) -> None:
        """Remove a tenant from this tag.

        Args:
            tenant_key: Tenant $key (ID) to remove.

        Raises:
            NotFoundError: If tenant is not tagged.

        Example:
            >>> client.tags.members(tag_key).remove_tenant(tenant.key)
        """
        self.remove_resource("tenants", tenant_key)


class Tag(ResourceObject):
    """Tag resource object.

    Represents a tag within a category in VergeOS.

    Attributes:
        key: Tag primary key ($key).
        name: Tag name.
        description: Tag description.
        category_key: Parent category key.
        category_name: Parent category name (if fetched with category info).
        created: Creation timestamp (Unix epoch).
        modified: Last modified timestamp (Unix epoch).
    """

    @property
    def description(self) -> str | None:
        """Get the tag description."""
        return self.get("description")

    @property
    def category_key(self) -> int:
        """Get the parent category key."""
        return int(self.get("category", 0))

    @property
    def category_name(self) -> str | None:
        """Get the parent category name (if fetched)."""
        return self.get("category_name")

    @property
    def created(self) -> int | None:
        """Get the creation timestamp (Unix epoch)."""
        val = self.get("created")
        return int(val) if val is not None else None

    @property
    def modified(self) -> int | None:
        """Get the last modified timestamp (Unix epoch)."""
        val = self.get("modified")
        return int(val) if val is not None else None

    @property
    def members(self) -> TagMemberManager:
        """Access tag member operations for this tag.

        Returns:
            TagMemberManager for this tag.

        Example:
            >>> # List members
            >>> for member in tag.members.list():
            ...     print(member.resource_ref)

            >>> # Add a VM
            >>> tag.members.add_vm(vm.key)
        """
        from typing import cast

        manager = cast("TagManager", self._manager)
        return manager.members(self.key)

    def refresh(self) -> Tag:
        """Refresh tag data from the server.

        Returns:
            Updated Tag object.
        """
        from typing import cast

        manager = cast("TagManager", self._manager)
        return manager.get(self.key)

    def save(self, **kwargs: Any) -> Tag:
        """Save changes to this tag.

        Args:
            **kwargs: Fields to update (name, description).

        Returns:
            Updated Tag object.
        """
        from typing import cast

        manager = cast("TagManager", self._manager)
        return manager.update(self.key, **kwargs)

    def delete(self) -> None:
        """Delete this tag."""
        from typing import cast

        manager = cast("TagManager", self._manager)
        manager.delete(self.key)


class TagManager(ResourceManager[Tag]):
    """Manager for VergeOS tag operations.

    Provides CRUD operations and management for tags.

    Example:
        >>> # List all tags
        >>> for tag in client.tags.list():
        ...     print(f"{tag.name} (Category: {tag.category_name})")

        >>> # List tags in a specific category
        >>> env_tags = client.tags.list(category_key=1)

        >>> # Create a tag
        >>> tag = client.tags.create(
        ...     name="Production",
        ...     category_key=1,
        ...     description="Production resources"
        ... )

        >>> # Manage tag members
        >>> client.tags.members(tag.key).add_vm(vm.key)
    """

    _endpoint = "tags"

    # Default fields for list operations
    _default_fields = [
        "$key",
        "name",
        "description",
        "category",
        "category#name as category_name",
        "created",
        "modified",
    ]

    def __init__(self, client: VergeClient) -> None:
        super().__init__(client)

    def _to_model(self, data: dict[str, Any]) -> Tag:
        """Convert API response to Tag object."""
        return Tag(data, self)

    def list(
        self,
        filter: str | None = None,
        fields: builtins.list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        category_key: int | None = None,
        category_name: str | None = None,
        **filter_kwargs: Any,
    ) -> builtins.list[Tag]:
        """List tags with optional filtering.

        Args:
            filter: OData filter string.
            fields: List of fields to return (uses defaults if not specified).
            limit: Maximum number of results.
            offset: Skip this many results.
            category_key: Filter by category key.
            category_name: Filter by category name (performs lookup).
            **filter_kwargs: Shorthand filter arguments (name, etc.).

        Returns:
            List of Tag objects.

        Example:
            >>> # List all tags
            >>> tags = client.tags.list()

            >>> # List tags in a category
            >>> env_tags = client.tags.list(category_key=1)

            >>> # List by name
            >>> tags = client.tags.list(name="Production")
        """
        params: dict[str, Any] = {}

        # Build filter
        filters: builtins.list[str] = []

        if filter:
            filters.append(filter)
        if filter_kwargs:
            filters.append(build_filter(**filter_kwargs))

        # Filter by category
        if category_key is not None:
            filters.append(f"category eq {category_key}")
        elif category_name is not None:
            # Look up category by name
            categories = TagCategoryManager(self._client).list(name=category_name)
            if not categories:
                return []
            filters.append(f"category eq {categories[0].key}")

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
        category_key: int | None = None,
        category_name: str | None = None,
        fields: builtins.list[str] | None = None,
    ) -> Tag:
        """Get a single tag by key or name.

        Args:
            key: Tag $key (ID).
            name: Tag name (requires category_key or category_name for uniqueness).
            category_key: Category key (used with name lookup).
            category_name: Category name (used with name lookup).
            fields: List of fields to return.

        Returns:
            Tag object.

        Raises:
            NotFoundError: If tag not found.
            ValueError: If neither key nor name provided.

        Example:
            >>> # Get by key
            >>> tag = client.tags.get(123)

            >>> # Get by name in category
            >>> tag = client.tags.get(name="Production", category_name="Environment")
        """
        if key is not None:
            # Direct fetch by key
            params: dict[str, Any] = {}
            if fields:
                params["fields"] = ",".join(fields)
            else:
                params["fields"] = ",".join(self._default_fields)

            response = self._client._request(
                "GET", f"{self._endpoint}/{key}", params=params
            )
            if response is None:
                raise NotFoundError(f"Tag with key {key} not found")
            if not isinstance(response, dict):
                raise NotFoundError(f"Tag with key {key} returned invalid response")
            return self._to_model(response)

        if name is not None:
            # Search by name
            escaped_name = name.replace("'", "''")
            results = self.list(
                filter=f"name eq '{escaped_name}'",
                category_key=category_key,
                category_name=category_name,
                fields=fields,
                limit=1,
            )
            if not results:
                raise NotFoundError(f"Tag '{name}' not found")
            return results[0]

        raise ValueError("Either key or name must be provided")

    def create(  # type: ignore[override]
        self,
        name: str,
        category_key: int,
        *,
        description: str | None = None,
    ) -> Tag:
        """Create a new tag.

        Args:
            name: Tag name (must be unique within category).
            category_key: Parent category $key (ID).
            description: Tag description (optional).

        Returns:
            Created Tag object.

        Example:
            >>> # Create a tag
            >>> tag = client.tags.create(
            ...     name="Production",
            ...     category_key=1,
            ...     description="Production resources"
            ... )
        """
        body: dict[str, Any] = {
            "name": name,
            "category": category_key,
        }

        if description:
            body["description"] = description

        response = self._client._request("POST", self._endpoint, json_data=body)

        # Get the created tag
        if response and isinstance(response, dict):
            tag_key = response.get("$key")
            if tag_key:
                return self.get(key=int(tag_key))

        # Fallback: search by name
        return self.get(name=name, category_key=category_key)

    def update(  # type: ignore[override]
        self,
        key: int,
        *,
        name: str | None = None,
        description: str | None = None,
    ) -> Tag:
        """Update a tag.

        Args:
            key: Tag $key (ID).
            name: New tag name.
            description: New description.

        Returns:
            Updated Tag object.

        Example:
            >>> # Update description
            >>> client.tags.update(tag.key, description="New description")

            >>> # Rename tag
            >>> client.tags.update(tag.key, name="NewName")
        """
        body: dict[str, Any] = {}

        if name is not None:
            body["name"] = name

        if description is not None:
            body["description"] = description

        if not body:
            return self.get(key)

        self._client._request("PUT", f"{self._endpoint}/{key}", json_data=body)
        return self.get(key)

    def delete(self, key: int) -> None:
        """Delete a tag.

        Args:
            key: Tag $key (ID).

        Note:
            Deleting a tag also removes all tag member assignments.

        Example:
            >>> client.tags.delete(tag.key)
        """
        self._client._request("DELETE", f"{self._endpoint}/{key}")

    def members(self, tag_key: int) -> TagMemberManager:
        """Get a member manager for a specific tag.

        Args:
            tag_key: Tag $key (ID).

        Returns:
            TagMemberManager for the specified tag.

        Example:
            >>> # List members
            >>> members = client.tags.members(tag.key).list()

            >>> # Add VM to tag
            >>> client.tags.members(tag.key).add_vm(vm.key)
        """
        return TagMemberManager(self._client, tag_key)


class TagCategory(ResourceObject):
    """Tag category resource object.

    Represents a tag category in VergeOS that organizes tags and
    defines which resource types can be tagged.

    Attributes:
        key: Category primary key ($key).
        name: Category name.
        description: Category description.
        is_single_tag_selection: Whether only one tag from this category
            can be applied to a resource.
        taggable_*: Boolean flags for each resource type that can be tagged.
        created: Creation timestamp (Unix epoch).
        modified: Last modified timestamp (Unix epoch).
    """

    @property
    def description(self) -> str | None:
        """Get the category description."""
        return self.get("description")

    @property
    def is_single_tag_selection(self) -> bool:
        """Check if only one tag from this category can be applied."""
        return bool(self.get("single_tag_selection", False))

    @property
    def taggable_vms(self) -> bool:
        """Check if VMs can be tagged with this category."""
        return bool(self.get("taggable_vms", False))

    @property
    def taggable_networks(self) -> bool:
        """Check if networks can be tagged with this category."""
        return bool(self.get("taggable_vnets", False))

    @property
    def taggable_volumes(self) -> bool:
        """Check if volumes can be tagged with this category."""
        return bool(self.get("taggable_volumes", False))

    @property
    def taggable_network_rules(self) -> bool:
        """Check if network rules can be tagged with this category."""
        return bool(self.get("taggable_vnet_rules", False))

    @property
    def taggable_vmware_containers(self) -> bool:
        """Check if VMware containers can be tagged with this category."""
        return bool(self.get("taggable_vmware_containers", False))

    @property
    def taggable_users(self) -> bool:
        """Check if users can be tagged with this category."""
        return bool(self.get("taggable_users", False))

    @property
    def taggable_tenant_nodes(self) -> bool:
        """Check if tenant nodes can be tagged with this category."""
        return bool(self.get("taggable_tenant_nodes", False))

    @property
    def taggable_sites(self) -> bool:
        """Check if sites can be tagged with this category."""
        return bool(self.get("taggable_sites", False))

    @property
    def taggable_nodes(self) -> bool:
        """Check if nodes can be tagged with this category."""
        return bool(self.get("taggable_nodes", False))

    @property
    def taggable_groups(self) -> bool:
        """Check if groups can be tagged with this category."""
        return bool(self.get("taggable_groups", False))

    @property
    def taggable_clusters(self) -> bool:
        """Check if clusters can be tagged with this category."""
        return bool(self.get("taggable_clusters", False))

    @property
    def taggable_tenants(self) -> bool:
        """Check if tenants can be tagged with this category."""
        return bool(self.get("taggable_tenants", False))

    @property
    def created(self) -> int | None:
        """Get the creation timestamp (Unix epoch)."""
        val = self.get("created")
        return int(val) if val is not None else None

    @property
    def modified(self) -> int | None:
        """Get the last modified timestamp (Unix epoch)."""
        val = self.get("modified")
        return int(val) if val is not None else None

    def get_taggable_types(self) -> builtins.list[str]:
        """Get a list of resource types that can be tagged with this category.

        Returns:
            List of resource type names (vms, vnets, etc.).

        Example:
            >>> category.get_taggable_types()
            ['vms', 'vnets', 'tenants']
        """
        result = []
        for resource_type, field_name in TAGGABLE_RESOURCE_TYPES.items():
            if self.get(field_name, False):
                result.append(resource_type)
        return result

    @property
    def tags(self) -> builtins.list[Tag]:
        """Get all tags in this category.

        Returns:
            List of Tag objects in this category.

        Example:
            >>> for tag in category.tags:
            ...     print(tag.name)
        """
        from typing import cast

        manager = cast("TagCategoryManager", self._manager)
        return manager._client.tags.list(category_key=self.key)

    def refresh(self) -> TagCategory:
        """Refresh category data from the server.

        Returns:
            Updated TagCategory object.
        """
        from typing import cast

        manager = cast("TagCategoryManager", self._manager)
        return manager.get(self.key)

    def save(self, **kwargs: Any) -> TagCategory:
        """Save changes to this category.

        Args:
            **kwargs: Fields to update.

        Returns:
            Updated TagCategory object.
        """
        from typing import cast

        manager = cast("TagCategoryManager", self._manager)
        return manager.update(self.key, **kwargs)

    def delete(self) -> None:
        """Delete this category.

        Note:
            Category must not contain any tags. Delete tags first.
        """
        from typing import cast

        manager = cast("TagCategoryManager", self._manager)
        manager.delete(self.key)


class TagCategoryManager(ResourceManager[TagCategory]):
    """Manager for VergeOS tag category operations.

    Provides CRUD operations and management for tag categories.

    Example:
        >>> # List all categories
        >>> for category in client.tag_categories.list():
        ...     print(f"{category.name}: {category.get_taggable_types()}")

        >>> # Create a category
        >>> category = client.tag_categories.create(
        ...     name="Environment",
        ...     description="Deployment environment",
        ...     taggable_vms=True,
        ...     taggable_networks=True,
        ...     single_tag_selection=True
        ... )
    """

    _endpoint = "tag_categories"

    # Default fields for list operations
    _default_fields = [
        "$key",
        "name",
        "description",
        "single_tag_selection",
        "taggable_vms",
        "taggable_vnets",
        "taggable_volumes",
        "taggable_vnet_rules",
        "taggable_vmware_containers",
        "taggable_users",
        "taggable_tenant_nodes",
        "taggable_sites",
        "taggable_nodes",
        "taggable_groups",
        "taggable_clusters",
        "taggable_tenants",
        "created",
        "modified",
    ]

    def __init__(self, client: VergeClient) -> None:
        super().__init__(client)

    def _to_model(self, data: dict[str, Any]) -> TagCategory:
        """Convert API response to TagCategory object."""
        return TagCategory(data, self)

    def list(
        self,
        filter: str | None = None,
        fields: builtins.list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        **filter_kwargs: Any,
    ) -> builtins.list[TagCategory]:
        """List tag categories with optional filtering.

        Args:
            filter: OData filter string.
            fields: List of fields to return (uses defaults if not specified).
            limit: Maximum number of results.
            offset: Skip this many results.
            **filter_kwargs: Shorthand filter arguments (name, etc.).

        Returns:
            List of TagCategory objects.

        Example:
            >>> # List all categories
            >>> categories = client.tag_categories.list()

            >>> # List by name
            >>> categories = client.tag_categories.list(name="Environment")
        """
        params: dict[str, Any] = {}

        # Build filter
        filters: builtins.list[str] = []

        if filter:
            filters.append(filter)
        if filter_kwargs:
            filters.append(build_filter(**filter_kwargs))

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
    ) -> TagCategory:
        """Get a single tag category by key or name.

        Args:
            key: Category $key (ID).
            name: Category name.
            fields: List of fields to return.

        Returns:
            TagCategory object.

        Raises:
            NotFoundError: If category not found.
            ValueError: If neither key nor name provided.

        Example:
            >>> # Get by key
            >>> category = client.tag_categories.get(123)

            >>> # Get by name
            >>> category = client.tag_categories.get(name="Environment")
        """
        if key is not None:
            # Direct fetch by key
            params: dict[str, Any] = {}
            if fields:
                params["fields"] = ",".join(fields)
            else:
                params["fields"] = ",".join(self._default_fields)

            response = self._client._request(
                "GET", f"{self._endpoint}/{key}", params=params
            )
            if response is None:
                raise NotFoundError(f"Tag category with key {key} not found")
            if not isinstance(response, dict):
                raise NotFoundError(
                    f"Tag category with key {key} returned invalid response"
                )
            return self._to_model(response)

        if name is not None:
            # Search by name
            escaped_name = name.replace("'", "''")
            results = self.list(filter=f"name eq '{escaped_name}'", fields=fields, limit=1)
            if not results:
                raise NotFoundError(f"Tag category '{name}' not found")
            return results[0]

        raise ValueError("Either key or name must be provided")

    def create(  # type: ignore[override]
        self,
        name: str,
        *,
        description: str | None = None,
        single_tag_selection: bool = False,
        taggable_vms: bool = False,
        taggable_networks: bool = False,
        taggable_volumes: bool = False,
        taggable_network_rules: bool = False,
        taggable_vmware_containers: bool = False,
        taggable_users: bool = False,
        taggable_tenant_nodes: bool = False,
        taggable_sites: bool = False,
        taggable_nodes: bool = False,
        taggable_groups: bool = False,
        taggable_clusters: bool = False,
        taggable_tenants: bool = False,
    ) -> TagCategory:
        """Create a new tag category.

        Args:
            name: Category name (must be unique).
            description: Category description (optional).
            single_tag_selection: If True, only one tag from this category
                can be applied to a resource.
            taggable_vms: Allow tagging VMs.
            taggable_networks: Allow tagging networks.
            taggable_volumes: Allow tagging volumes.
            taggable_network_rules: Allow tagging network rules.
            taggable_vmware_containers: Allow tagging VMware containers.
            taggable_users: Allow tagging users.
            taggable_tenant_nodes: Allow tagging tenant nodes.
            taggable_sites: Allow tagging sites.
            taggable_nodes: Allow tagging nodes.
            taggable_groups: Allow tagging groups.
            taggable_clusters: Allow tagging clusters.
            taggable_tenants: Allow tagging tenants.

        Returns:
            Created TagCategory object.

        Example:
            >>> # Create an environment category
            >>> category = client.tag_categories.create(
            ...     name="Environment",
            ...     description="Deployment environment",
            ...     taggable_vms=True,
            ...     taggable_networks=True,
            ...     taggable_tenants=True,
            ...     single_tag_selection=True
            ... )
        """
        body: dict[str, Any] = {
            "name": name,
        }

        if description:
            body["description"] = description

        if single_tag_selection:
            body["single_tag_selection"] = True

        if taggable_vms:
            body["taggable_vms"] = True

        if taggable_networks:
            body["taggable_vnets"] = True

        if taggable_volumes:
            body["taggable_volumes"] = True

        if taggable_network_rules:
            body["taggable_vnet_rules"] = True

        if taggable_vmware_containers:
            body["taggable_vmware_containers"] = True

        if taggable_users:
            body["taggable_users"] = True

        if taggable_tenant_nodes:
            body["taggable_tenant_nodes"] = True

        if taggable_sites:
            body["taggable_sites"] = True

        if taggable_nodes:
            body["taggable_nodes"] = True

        if taggable_groups:
            body["taggable_groups"] = True

        if taggable_clusters:
            body["taggable_clusters"] = True

        if taggable_tenants:
            body["taggable_tenants"] = True

        response = self._client._request("POST", self._endpoint, json_data=body)

        # Get the created category
        if response and isinstance(response, dict):
            category_key = response.get("$key")
            if category_key:
                return self.get(key=int(category_key))

        # Fallback: search by name
        return self.get(name=name)

    def update(  # type: ignore[override]
        self,
        key: int,
        *,
        name: str | None = None,
        description: str | None = None,
        single_tag_selection: bool | None = None,
        taggable_vms: bool | None = None,
        taggable_networks: bool | None = None,
        taggable_volumes: bool | None = None,
        taggable_network_rules: bool | None = None,
        taggable_vmware_containers: bool | None = None,
        taggable_users: bool | None = None,
        taggable_tenant_nodes: bool | None = None,
        taggable_sites: bool | None = None,
        taggable_nodes: bool | None = None,
        taggable_groups: bool | None = None,
        taggable_clusters: bool | None = None,
        taggable_tenants: bool | None = None,
    ) -> TagCategory:
        """Update a tag category.

        Args:
            key: Category $key (ID).
            name: New category name.
            description: New description.
            single_tag_selection: Update single tag selection mode.
            taggable_*: Update taggable resource types.

        Returns:
            Updated TagCategory object.

        Example:
            >>> # Update description
            >>> client.tag_categories.update(
            ...     category.key,
            ...     description="New description"
            ... )

            >>> # Enable additional resource types
            >>> client.tag_categories.update(
            ...     category.key,
            ...     taggable_nodes=True,
            ...     taggable_clusters=True
            ... )
        """
        body: dict[str, Any] = {}

        if name is not None:
            body["name"] = name

        if description is not None:
            body["description"] = description

        if single_tag_selection is not None:
            body["single_tag_selection"] = single_tag_selection

        if taggable_vms is not None:
            body["taggable_vms"] = taggable_vms

        if taggable_networks is not None:
            body["taggable_vnets"] = taggable_networks

        if taggable_volumes is not None:
            body["taggable_volumes"] = taggable_volumes

        if taggable_network_rules is not None:
            body["taggable_vnet_rules"] = taggable_network_rules

        if taggable_vmware_containers is not None:
            body["taggable_vmware_containers"] = taggable_vmware_containers

        if taggable_users is not None:
            body["taggable_users"] = taggable_users

        if taggable_tenant_nodes is not None:
            body["taggable_tenant_nodes"] = taggable_tenant_nodes

        if taggable_sites is not None:
            body["taggable_sites"] = taggable_sites

        if taggable_nodes is not None:
            body["taggable_nodes"] = taggable_nodes

        if taggable_groups is not None:
            body["taggable_groups"] = taggable_groups

        if taggable_clusters is not None:
            body["taggable_clusters"] = taggable_clusters

        if taggable_tenants is not None:
            body["taggable_tenants"] = taggable_tenants

        if not body:
            return self.get(key)

        self._client._request("PUT", f"{self._endpoint}/{key}", json_data=body)
        return self.get(key)

    def delete(self, key: int) -> None:
        """Delete a tag category.

        Args:
            key: Category $key (ID).

        Note:
            The category must not contain any tags. Delete all tags first.

        Example:
            >>> client.tag_categories.delete(category.key)
        """
        self._client._request("DELETE", f"{self._endpoint}/{key}")
