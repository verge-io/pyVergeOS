"""Shared object management for tenant VM sharing."""

from __future__ import annotations

import builtins
import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from pyvergeos.exceptions import NotFoundError

if TYPE_CHECKING:
    from pyvergeos.client import VergeClient
    from pyvergeos.resources.tenant_manager import Tenant

logger = logging.getLogger(__name__)

# Default fields to request for shared objects
SHARED_OBJECT_DEFAULT_FIELDS = [
    "$key",
    "recipient",
    "recipient#name as recipient_name",
    "type",
    "name",
    "description",
    "created",
    "inbox",
    "snapshot",
    "id",
]


class SharedObject(dict[str, Any]):
    """Shared object resource representing a VM shared with a tenant."""

    def __init__(self, data: dict[str, Any], manager: SharedObjectManager) -> None:
        super().__init__(data)
        self._manager = manager

    @property
    def key(self) -> int:
        """Get the shared object's primary key."""
        return int(self.get("$key", 0))

    @property
    def name(self) -> str:
        """Get the shared object name."""
        return str(self.get("name", ""))

    @property
    def description(self) -> str | None:
        """Get the shared object description."""
        return self.get("description")

    @property
    def tenant_key(self) -> int:
        """Get the recipient tenant's key."""
        return int(self.get("recipient", 0))

    @property
    def tenant_name(self) -> str | None:
        """Get the recipient tenant's name."""
        return self.get("recipient_name")

    @property
    def object_type(self) -> str:
        """Get the type of shared object (e.g., 'vm')."""
        return str(self.get("type", "vm"))

    @property
    def object_id(self) -> str | None:
        """Get the object ID (e.g., 'vms/123')."""
        return self.get("id")

    @property
    def snapshot_path(self) -> str | None:
        """Get the snapshot path."""
        return self.get("snapshot")

    @property
    def snapshot_key(self) -> int | None:
        """Get the snapshot key from the snapshot path."""
        snapshot = self.snapshot_path
        if snapshot:
            # Parse snapshot path like "machine_snapshots/14"
            parts = snapshot.rsplit("/", 1)
            if len(parts) == 2 and parts[1].isdigit():
                return int(parts[1])
        return None

    @property
    def is_inbox(self) -> bool:
        """Check if this is an inbox item (pending import)."""
        return bool(self.get("inbox", False))

    @property
    def created_at(self) -> datetime | None:
        """Get the creation timestamp."""
        created = self.get("created")
        if created:
            return datetime.fromtimestamp(created, tz=timezone.utc)
        return None

    def import_object(self) -> dict[str, Any] | None:
        """Import this shared object into the tenant.

        This triggers the import process which creates a copy of the
        shared VM within the tenant's environment.

        Returns:
            Action response (may include task information).

        Example:
            >>> shared_obj = client.shared_objects.get(key=42)
            >>> shared_obj.import_object()
        """
        return self._manager.import_object(self.key)

    def refresh(self) -> SharedObject:
        """Refresh shared object data from API.

        Returns:
            Updated SharedObject.
        """
        return self._manager.get(self.key)

    def delete(self) -> None:
        """Delete this shared object.

        This removes the share from the tenant. It does not affect
        VMs that have already been imported.
        """
        self._manager.delete(self.key)


class SharedObjectManager:
    """Manager for shared object operations.

    Shared objects allow parent systems to share VMs with tenants.
    The shared VM can then be imported by the tenant to create their own copy.

    Example:
        >>> # List shared objects for a tenant
        >>> shared = client.shared_objects.list(tenant_key=123)
        >>> for obj in shared:
        ...     print(f"{obj.name}: {obj.object_type}")

        >>> # Share a VM with a tenant
        >>> shared = client.shared_objects.create(
        ...     tenant_key=123,
        ...     vm_key=456,
        ...     name="Ubuntu Template",
        ...     description="Pre-configured Ubuntu server"
        ... )

        >>> # Import a shared object in the tenant
        >>> client.shared_objects.import_object(shared.key)

        >>> # Remove a share
        >>> client.shared_objects.delete(shared.key)
    """

    _endpoint = "shared_objects"
    _default_fields = SHARED_OBJECT_DEFAULT_FIELDS

    def __init__(self, client: VergeClient) -> None:
        self._client = client

    def _to_model(self, data: dict[str, Any]) -> SharedObject:
        return SharedObject(data, self)

    def list(
        self,
        tenant_key: int | None = None,
        tenant: Tenant | None = None,
        name: str | None = None,
        inbox_only: bool = False,
        fields: builtins.list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> builtins.list[SharedObject]:
        """List shared objects with optional filtering.

        Args:
            tenant_key: Filter by recipient tenant key.
            tenant: Filter by recipient Tenant object (alternative to tenant_key).
            name: Filter by shared object name (exact match).
            inbox_only: Only return inbox items (pending imports).
            fields: List of fields to return (defaults to rich field set).
            limit: Maximum number of results.
            offset: Skip this many results.

        Returns:
            List of SharedObject objects.

        Example:
            >>> # List all shared objects for a tenant
            >>> shared = client.shared_objects.list(tenant_key=123)

            >>> # List inbox items only
            >>> inbox = client.shared_objects.list(tenant_key=123, inbox_only=True)

            >>> # List by tenant object
            >>> tenant = client.tenants.get(name="my-tenant")
            >>> shared = client.shared_objects.list(tenant=tenant)
        """
        if fields is None:
            fields = self._default_fields

        # Resolve tenant_key from tenant object if provided
        if tenant is not None:
            tenant_key = tenant.key

        # Build filter
        filters: builtins.list[str] = []
        if tenant_key is not None:
            filters.append(f"recipient eq {tenant_key}")
        if name is not None:
            filters.append(f"name eq '{name}'")
        if inbox_only:
            filters.append("inbox eq true")

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

        items = response if isinstance(response, list) else [response]
        return [self._to_model(item) for item in items if item and "$key" in item]

    def get(
        self,
        key: int | None = None,
        *,
        tenant_key: int | None = None,
        name: str | None = None,
        fields: builtins.list[str] | None = None,
    ) -> SharedObject:
        """Get a single shared object by key or by tenant/name.

        Args:
            key: Shared object $key (ID).
            tenant_key: Tenant key (required when using name).
            name: Shared object name (requires tenant_key).
            fields: List of fields to return (defaults to rich field set).

        Returns:
            SharedObject object.

        Raises:
            NotFoundError: If shared object not found.
            ValueError: If neither key nor tenant_key/name provided.

        Example:
            >>> # Get by key
            >>> shared = client.shared_objects.get(42)

            >>> # Get by tenant and name
            >>> shared = client.shared_objects.get(tenant_key=123, name="Ubuntu Template")
        """
        if fields is None:
            fields = self._default_fields

        if key is not None:
            # Get by key
            params = {"fields": ",".join(fields), "filter": f"$key eq {key}"}
            response = self._client._request("GET", self._endpoint, params=params)

            if not response:
                raise NotFoundError(f"Shared object with key {key} not found")

            items = response if isinstance(response, list) else [response]
            if not items or not items[0]:
                raise NotFoundError(f"Shared object with key {key} not found")

            return self._to_model(items[0])

        elif tenant_key is not None and name is not None:
            # Get by tenant and name
            results = self.list(tenant_key=tenant_key, name=name, fields=fields)
            if not results:
                raise NotFoundError(
                    f"Shared object '{name}' not found for tenant {tenant_key}"
                )
            return results[0]

        else:
            raise ValueError("Either key or tenant_key/name must be provided")

    def create(
        self,
        tenant_key: int | None = None,
        tenant: Tenant | None = None,
        vm_key: int | None = None,
        vm_name: str | None = None,
        name: str | None = None,
        description: str | None = None,
        snapshot_name: str | None = None,
    ) -> SharedObject:
        """Share a VM with a tenant.

        Creates a shared object that the tenant can import to create
        their own copy of the VM. This automatically creates a machine
        snapshot of the VM to share.

        Args:
            tenant_key: Recipient tenant $key (ID).
            tenant: Recipient Tenant object (alternative to tenant_key).
            vm_key: VM $key to share.
            vm_name: VM name to share (alternative to vm_key, will be looked up).
            name: Name for the shared object (defaults to VM name).
            description: Optional description.
            snapshot_name: Optional name for the machine snapshot. If not
                provided, a unique name is generated.

        Returns:
            Created SharedObject.

        Raises:
            ValueError: If tenant or VM not specified.
            NotFoundError: If VM not found by name.
            APIError: If snapshot or shared object creation fails.

        Example:
            >>> # Share by tenant key and VM key
            >>> shared = client.shared_objects.create(
            ...     tenant_key=123,
            ...     vm_key=456,
            ...     name="Ubuntu Template"
            ... )

            >>> # Share by objects
            >>> tenant = client.tenants.get(name="my-tenant")
            >>> vm = client.vms.get(name="template-vm")
            >>> shared = client.shared_objects.create(
            ...     tenant=tenant,
            ...     vm_key=vm.key,
            ...     description="Pre-configured template"
            ... )
        """
        import random
        import time

        # Resolve tenant_key
        if tenant is not None:
            tenant_key = tenant.key
        if tenant_key is None:
            raise ValueError("Either tenant_key or tenant must be provided")

        # Resolve VM and get machine key
        if vm_key is None:
            if vm_name is not None:
                vm = self._client.vms.get(name=vm_name)
                vm_key = vm.key
            else:
                raise ValueError("Either vm_key or vm_name must be provided")
        else:
            vm = self._client.vms.get(vm_key)

        machine_key = vm.get("machine")
        if not machine_key:
            raise ValueError(f"VM {vm_key} has no associated machine")

        # Determine shared object name
        if name is None:
            name = vm.name

        # Generate snapshot name if not provided
        if snapshot_name is None:
            snapshot_name = f"share-{name}-{random.randint(10000, 99999)}"

        # Step 1: Create a machine snapshot
        snapshot_body: dict[str, Any] = {
            "machine": machine_key,
            "name": snapshot_name,
            "expires_type": "never",  # Shared snapshots should not auto-expire
            "created_manually": True,
        }

        snapshot_response = self._client._request(
            "POST", "machine_snapshots", json_data=snapshot_body
        )

        if not snapshot_response or not isinstance(snapshot_response, dict):
            raise ValueError("Failed to create machine snapshot for sharing")

        snapshot_key = snapshot_response.get("$key")
        if not snapshot_key:
            raise ValueError("Machine snapshot created but no key returned")

        # Brief delay to ensure snapshot is ready
        time.sleep(1)

        try:
            # Step 2: Create the shared object with the snapshot
            shared_body: dict[str, Any] = {
                "recipient": tenant_key,
                "type": "vm",
                "name": name,
                "snapshot": f"machine_snapshots/{snapshot_key}",
            }

            if description:
                shared_body["description"] = description

            response = self._client._request(
                "POST", self._endpoint, json_data=shared_body
            )

            if response and isinstance(response, dict) and "$key" in response:
                # Fetch the full object with all fields
                return self.get(int(response["$key"]))

            # If response doesn't have key, try to find by name
            return self.get(tenant_key=tenant_key, name=name)

        except Exception:
            # If shared object creation fails, clean up the snapshot
            import contextlib

            with contextlib.suppress(Exception):
                self._client._request("DELETE", f"machine_snapshots/{snapshot_key}")
            raise

    def import_object(self, key: int) -> dict[str, Any] | None:
        """Import a shared object into the tenant.

        This triggers the import process which creates a copy of the
        shared VM within the tenant's environment. The import runs
        asynchronously.

        Args:
            key: Shared object $key to import.

        Returns:
            Action response (may include task information).

        Example:
            >>> # Import by key
            >>> client.shared_objects.import_object(42)

            >>> # Import from object
            >>> shared = client.shared_objects.get(tenant_key=123, name="Template")
            >>> shared.import_object()
        """
        body = {
            "shared_object": key,
            "action": "import",
        }

        result = self._client._request("POST", "shared_object_actions", json_data=body)
        return result if isinstance(result, dict) else None

    def refresh_object(self, key: int) -> dict[str, Any] | None:
        """Refresh a shared object.

        This updates the shared object's snapshot.

        Args:
            key: Shared object $key to refresh.

        Returns:
            Action response (may include task information).
        """
        body = {
            "shared_object": key,
            "action": "refresh",
        }

        result = self._client._request("POST", "shared_object_actions", json_data=body)
        return result if isinstance(result, dict) else None

    def delete(self, key: int) -> None:
        """Delete a shared object.

        This removes the share from the tenant. It does not affect
        VMs that have already been imported by the tenant.

        Args:
            key: Shared object $key to delete.

        Example:
            >>> client.shared_objects.delete(42)

            >>> # Or via object
            >>> shared = client.shared_objects.get(42)
            >>> shared.delete()
        """
        self._client._request("DELETE", f"{self._endpoint}/{key}")

    def list_for_tenant(
        self,
        tenant: Tenant,
        inbox_only: bool = False,
    ) -> builtins.list[SharedObject]:
        """List shared objects for a specific tenant.

        Convenience method that wraps list() with a Tenant object.

        Args:
            tenant: Tenant object to list shared objects for.
            inbox_only: Only return inbox items (pending imports).

        Returns:
            List of SharedObject objects.

        Example:
            >>> tenant = client.tenants.get(name="my-tenant")
            >>> shared = client.shared_objects.list_for_tenant(tenant)
        """
        return self.list(tenant_key=tenant.key, inbox_only=inbox_only)
