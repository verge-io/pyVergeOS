"""Cloud (system) snapshot resource manager for VergeOS backup/DR."""

from __future__ import annotations

import builtins
import time
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any

from pyvergeos.exceptions import NotFoundError, ValidationError
from pyvergeos.filters import build_filter
from pyvergeos.resources.base import ResourceManager, ResourceObject

if TYPE_CHECKING:
    from pyvergeos.client import VergeClient


# Default fields for cloud snapshot list operations
_DEFAULT_SNAPSHOT_FIELDS = [
    "$key",
    "name",
    "description",
    "created",
    "expires",
    "expires_type",
    "snapshot_profile",
    "private",
    "remote_sync",
    "immutable",
    "immutable_status",
    "immutable_lock_expires",
    "status",
    "status_info",
]

# Default fields for snapshot VM list operations
_DEFAULT_VM_FIELDS = [
    "$key",
    "name",
    "description",
    "uuid",
    "machine_uuid",
    "cpu_cores",
    "ram",
    "os_family",
    "is_snapshot",
    "status",
    "status_info",
    "original_key",
    "cloud_snapshot",
]

# Default fields for snapshot tenant list operations
_DEFAULT_TENANT_FIELDS = [
    "$key",
    "name",
    "description",
    "uuid",
    "nodes",
    "cpu_cores",
    "ram",
    "is_snapshot",
    "status",
    "status_info",
    "original_key",
    "cloud_snapshot",
]


class CloudSnapshotVM(ResourceObject):
    """VM within a cloud snapshot.

    Represents a VM captured in a cloud (system) snapshot. Can be used
    to restore the VM to its state at snapshot time.

    Properties:
        name: VM name at snapshot time.
        description: VM description.
        uuid: VM UUID.
        machine_uuid: VM machine UUID.
        cpu_cores: Number of CPU cores.
        ram_mb: RAM in megabytes.
        os_family: Operating system family.
        is_snapshot: Whether this is a snapshot VM.
        status: Recovery status (idle, importing, complete, error).
        status_info: Additional status information.
        original_key: Original VM key at snapshot time.
        cloud_snapshot_key: Key of the parent cloud snapshot.
    """

    @property
    def name(self) -> str:
        """Get VM name."""
        return str(self.get("name", ""))

    @property
    def description(self) -> str:
        """Get VM description."""
        return str(self.get("description", ""))

    @property
    def uuid(self) -> str | None:
        """Get VM UUID."""
        val = self.get("uuid")
        return str(val) if val else None

    @property
    def machine_uuid(self) -> str | None:
        """Get VM machine UUID."""
        val = self.get("machine_uuid")
        return str(val) if val else None

    @property
    def cpu_cores(self) -> int:
        """Get number of CPU cores."""
        return int(self.get("cpu_cores", 0))

    @property
    def ram_mb(self) -> int:
        """Get RAM in megabytes."""
        return int(self.get("ram", 0))

    @property
    def os_family(self) -> str:
        """Get OS family."""
        return str(self.get("os_family", ""))

    @property
    def is_snapshot(self) -> bool:
        """Check if this is a snapshot VM."""
        return bool(self.get("is_snapshot", False))

    @property
    def status(self) -> str:
        """Get recovery status."""
        return str(self.get("status", "idle"))

    @property
    def status_info(self) -> str:
        """Get status info."""
        return str(self.get("status_info", ""))

    @property
    def original_key(self) -> int | None:
        """Get original VM key at snapshot time."""
        val = self.get("original_key")
        return int(val) if val is not None else None

    @property
    def cloud_snapshot_key(self) -> int | None:
        """Get parent cloud snapshot key."""
        val = self.get("cloud_snapshot")
        return int(val) if val is not None else None

    def __repr__(self) -> str:
        key = self.get("$key", "?")
        name = self.name
        return f"<CloudSnapshotVM key={key} name={name!r}>"


class CloudSnapshotTenant(ResourceObject):
    """Tenant within a cloud snapshot.

    Represents a tenant captured in a cloud (system) snapshot. Can be used
    to restore the tenant to its state at snapshot time.

    Properties:
        name: Tenant name at snapshot time.
        description: Tenant description.
        uuid: Tenant UUID.
        nodes: Number of nodes.
        cpu_cores: Total CPU cores.
        ram_mb: Total RAM in megabytes.
        is_snapshot: Whether this is a snapshot tenant.
        status: Recovery status (idle, importing, complete, error).
        status_info: Additional status information.
        original_key: Original tenant key at snapshot time.
        cloud_snapshot_key: Key of the parent cloud snapshot.
    """

    @property
    def name(self) -> str:
        """Get tenant name."""
        return str(self.get("name", ""))

    @property
    def description(self) -> str:
        """Get tenant description."""
        return str(self.get("description", ""))

    @property
    def uuid(self) -> str | None:
        """Get tenant UUID."""
        val = self.get("uuid")
        return str(val) if val else None

    @property
    def nodes(self) -> int:
        """Get number of nodes."""
        return int(self.get("nodes", 0))

    @property
    def cpu_cores(self) -> int:
        """Get total CPU cores."""
        return int(self.get("cpu_cores", 0))

    @property
    def ram_mb(self) -> int:
        """Get total RAM in megabytes."""
        return int(self.get("ram", 0))

    @property
    def is_snapshot(self) -> bool:
        """Check if this is a snapshot tenant."""
        return bool(self.get("is_snapshot", False))

    @property
    def status(self) -> str:
        """Get recovery status."""
        return str(self.get("status", "idle"))

    @property
    def status_info(self) -> str:
        """Get status info."""
        return str(self.get("status_info", ""))

    @property
    def original_key(self) -> int | None:
        """Get original tenant key at snapshot time."""
        val = self.get("original_key")
        return int(val) if val is not None else None

    @property
    def cloud_snapshot_key(self) -> int | None:
        """Get parent cloud snapshot key."""
        val = self.get("cloud_snapshot")
        return int(val) if val is not None else None

    def __repr__(self) -> str:
        key = self.get("$key", "?")
        name = self.name
        return f"<CloudSnapshotTenant key={key} name={name!r}>"


class CloudSnapshotVMManager(ResourceManager[CloudSnapshotVM]):
    """Manager for VMs within a cloud snapshot.

    Provides access to VMs captured in a specific cloud snapshot.

    Example:
        >>> # Get VMs in a snapshot
        >>> snapshot = client.cloud_snapshots.get(name="Daily_20260123")
        >>> vms = client.cloud_snapshots.vms(snapshot.key).list()
        >>> for vm in vms:
        ...     print(f"{vm.name}: {vm.cpu_cores} cores, {vm.ram_mb} MB RAM")
    """

    _endpoint = "cloud_snapshot_vms"

    def __init__(self, client: VergeClient, snapshot_key: int) -> None:
        super().__init__(client)
        self._snapshot_key = snapshot_key

    def _to_model(self, data: dict[str, Any]) -> CloudSnapshotVM:
        return CloudSnapshotVM(data, self)

    def list(
        self,
        filter: str | None = None,
        fields: builtins.list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        **filter_kwargs: Any,
    ) -> builtins.list[CloudSnapshotVM]:
        """List VMs in this cloud snapshot.

        Args:
            filter: OData filter string.
            fields: List of fields to return.
            limit: Maximum number of results.
            offset: Skip this many results.
            **filter_kwargs: Additional filter arguments.

        Returns:
            List of CloudSnapshotVM objects.
        """
        conditions: builtins.list[str] = [f"cloud_snapshot eq {self._snapshot_key}"]

        if filter:
            conditions.append(f"({filter})")

        if filter_kwargs:
            conditions.append(build_filter(**filter_kwargs))

        combined_filter = " and ".join(conditions)

        if fields is None:
            fields = _DEFAULT_VM_FIELDS

        params: dict[str, Any] = {"filter": combined_filter}
        if fields:
            params["fields"] = ",".join(fields)
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset
        params["sort"] = "+name"

        response = self._client._request("GET", self._endpoint, params=params)

        if response is None:
            return []

        if not isinstance(response, list):
            return [self._to_model(response)]

        return [self._to_model(item) for item in response]

    def get(
        self,
        key: int | None = None,
        *,
        name: str | None = None,
        fields: builtins.list[str] | None = None,
    ) -> CloudSnapshotVM:
        """Get a VM from this snapshot by key or name.

        Args:
            key: VM snapshot $key (ID).
            name: VM name within this snapshot.
            fields: List of fields to return.

        Returns:
            CloudSnapshotVM object.

        Raises:
            NotFoundError: If VM not found.
            ValueError: If neither key nor name provided.
        """
        if fields is None:
            fields = _DEFAULT_VM_FIELDS

        if key is not None:
            params: dict[str, Any] = {}
            if fields:
                params["fields"] = ",".join(fields)

            response = self._client._request(
                "GET", f"{self._endpoint}/{key}", params=params
            )
            if response is None:
                raise NotFoundError(f"VM {key} not found in cloud snapshot")
            if not isinstance(response, dict):
                raise NotFoundError(f"VM {key} returned invalid response")

            vm = self._to_model(response)
            if vm.cloud_snapshot_key != self._snapshot_key:
                raise NotFoundError(
                    f"VM {key} does not belong to snapshot {self._snapshot_key}"
                )
            return vm

        if name is not None:
            escaped_name = name.replace("'", "''")
            results = self.list(filter=f"name eq '{escaped_name}'", fields=fields)
            if not results:
                raise NotFoundError(
                    f"VM '{name}' not found in cloud snapshot {self._snapshot_key}"
                )
            return results[0]

        raise ValueError("Either key or name must be provided")


class CloudSnapshotTenantManager(ResourceManager[CloudSnapshotTenant]):
    """Manager for tenants within a cloud snapshot.

    Provides access to tenants captured in a specific cloud snapshot.

    Example:
        >>> # Get tenants in a snapshot
        >>> snapshot = client.cloud_snapshots.get(name="Daily_20260123")
        >>> tenants = client.cloud_snapshots.tenants(snapshot.key).list()
        >>> for tenant in tenants:
        ...     print(f"{tenant.name}: {tenant.nodes} nodes")
    """

    _endpoint = "cloud_snapshot_tenants"

    def __init__(self, client: VergeClient, snapshot_key: int) -> None:
        super().__init__(client)
        self._snapshot_key = snapshot_key

    def _to_model(self, data: dict[str, Any]) -> CloudSnapshotTenant:
        return CloudSnapshotTenant(data, self)

    def list(
        self,
        filter: str | None = None,
        fields: builtins.list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        **filter_kwargs: Any,
    ) -> builtins.list[CloudSnapshotTenant]:
        """List tenants in this cloud snapshot.

        Args:
            filter: OData filter string.
            fields: List of fields to return.
            limit: Maximum number of results.
            offset: Skip this many results.
            **filter_kwargs: Additional filter arguments.

        Returns:
            List of CloudSnapshotTenant objects.
        """
        conditions: builtins.list[str] = [f"cloud_snapshot eq {self._snapshot_key}"]

        if filter:
            conditions.append(f"({filter})")

        if filter_kwargs:
            conditions.append(build_filter(**filter_kwargs))

        combined_filter = " and ".join(conditions)

        if fields is None:
            fields = _DEFAULT_TENANT_FIELDS

        params: dict[str, Any] = {"filter": combined_filter}
        if fields:
            params["fields"] = ",".join(fields)
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset
        params["sort"] = "+name"

        response = self._client._request("GET", self._endpoint, params=params)

        if response is None:
            return []

        if not isinstance(response, list):
            return [self._to_model(response)]

        return [self._to_model(item) for item in response]

    def get(
        self,
        key: int | None = None,
        *,
        name: str | None = None,
        fields: builtins.list[str] | None = None,
    ) -> CloudSnapshotTenant:
        """Get a tenant from this snapshot by key or name.

        Args:
            key: Tenant snapshot $key (ID).
            name: Tenant name within this snapshot.
            fields: List of fields to return.

        Returns:
            CloudSnapshotTenant object.

        Raises:
            NotFoundError: If tenant not found.
            ValueError: If neither key nor name provided.
        """
        if fields is None:
            fields = _DEFAULT_TENANT_FIELDS

        if key is not None:
            params: dict[str, Any] = {}
            if fields:
                params["fields"] = ",".join(fields)

            response = self._client._request(
                "GET", f"{self._endpoint}/{key}", params=params
            )
            if response is None:
                raise NotFoundError(f"Tenant {key} not found in cloud snapshot")
            if not isinstance(response, dict):
                raise NotFoundError(f"Tenant {key} returned invalid response")

            tenant = self._to_model(response)
            if tenant.cloud_snapshot_key != self._snapshot_key:
                raise NotFoundError(
                    f"Tenant {key} does not belong to snapshot {self._snapshot_key}"
                )
            return tenant

        if name is not None:
            escaped_name = name.replace("'", "''")
            results = self.list(filter=f"name eq '{escaped_name}'", fields=fields)
            if not results:
                raise NotFoundError(
                    f"Tenant '{name}' not found in cloud snapshot {self._snapshot_key}"
                )
            return results[0]

        raise ValueError("Either key or name must be provided")


class CloudSnapshot(ResourceObject):
    """Cloud (system) snapshot resource object.

    Represents a cloud snapshot that captures the entire system state
    including all VMs and tenants at a point in time.

    Properties:
        name: Snapshot name.
        description: Snapshot description.
        created_at: When the snapshot was created.
        expires_at: When the snapshot expires (None if never).
        never_expires: Whether the snapshot never expires.
        snapshot_profile_key: Key of associated snapshot profile.
        is_private: Whether the snapshot is hidden from tenants.
        is_remote_sync: Whether this was synced from a remote system.
        is_immutable: Whether the snapshot is immutable.
        immutable_status: Immutable status (unlocked, unlocking, locked).
        immutable_lock_expires_at: When the immutable lock expires.
        status: Snapshot status (normal, held).
        status_info: Additional status information.
    """

    def __init__(
        self,
        data: dict[str, Any],
        manager: ResourceManager[Any],
        vms: builtins.list[CloudSnapshotVM] | None = None,
        tenants: builtins.list[CloudSnapshotTenant] | None = None,
    ) -> None:
        super().__init__(data, manager)
        self._vms = vms
        self._tenants = tenants

    @property
    def name(self) -> str:
        """Get snapshot name."""
        return str(self.get("name", ""))

    @property
    def description(self) -> str:
        """Get snapshot description."""
        return str(self.get("description", ""))

    @property
    def created_at(self) -> datetime | None:
        """Get creation timestamp."""
        ts = self.get("created")
        if ts:
            return datetime.fromtimestamp(int(ts), tz=timezone.utc)
        return None

    @property
    def expires_at(self) -> datetime | None:
        """Get expiration timestamp (None if never expires)."""
        ts = self.get("expires")
        if ts and int(ts) > 0:
            return datetime.fromtimestamp(int(ts), tz=timezone.utc)
        return None

    @property
    def never_expires(self) -> bool:
        """Check if snapshot never expires."""
        expires = self.get("expires")
        expires_type = self.get("expires_type")
        return expires_type == "never" or (expires is not None and int(expires) == 0)

    @property
    def snapshot_profile_key(self) -> int | None:
        """Get associated snapshot profile key."""
        val = self.get("snapshot_profile")
        return int(val) if val else None

    @property
    def is_private(self) -> bool:
        """Check if snapshot is hidden from tenants."""
        return bool(self.get("private", False))

    @property
    def is_remote_sync(self) -> bool:
        """Check if this was synced from a remote system."""
        return bool(self.get("remote_sync", False))

    @property
    def is_immutable(self) -> bool:
        """Check if snapshot is immutable."""
        return bool(self.get("immutable", False))

    @property
    def immutable_status(self) -> str:
        """Get immutable status (unlocked, unlocking, locked)."""
        return str(self.get("immutable_status", "unlocked"))

    @property
    def is_locked(self) -> bool:
        """Check if snapshot is currently locked."""
        return self.immutable_status == "locked"

    @property
    def immutable_lock_expires_at(self) -> datetime | None:
        """Get when the immutable lock expires."""
        ts = self.get("immutable_lock_expires")
        if ts and int(ts) > 0:
            return datetime.fromtimestamp(int(ts), tz=timezone.utc)
        return None

    @property
    def status(self) -> str:
        """Get snapshot status (normal, held)."""
        return str(self.get("status", "normal"))

    @property
    def status_info(self) -> str:
        """Get additional status information."""
        return str(self.get("status_info", ""))

    @property
    def vms(self) -> builtins.list[CloudSnapshotVM] | None:
        """Get VMs in this snapshot (if loaded with include_vms=True)."""
        return self._vms

    @property
    def tenants(self) -> builtins.list[CloudSnapshotTenant] | None:
        """Get tenants in this snapshot (if loaded with include_tenants=True)."""
        return self._tenants

    def get_vms(self) -> builtins.list[CloudSnapshotVM]:
        """Get all VMs in this snapshot.

        Returns:
            List of CloudSnapshotVM objects.
        """
        from typing import cast

        manager = cast("CloudSnapshotManager", self._manager)
        return manager.vms(self.key).list()

    def get_tenants(self) -> builtins.list[CloudSnapshotTenant]:
        """Get all tenants in this snapshot.

        Returns:
            List of CloudSnapshotTenant objects.
        """
        from typing import cast

        manager = cast("CloudSnapshotManager", self._manager)
        return manager.tenants(self.key).list()

    def delete(self) -> None:
        """Delete this snapshot.

        Raises:
            ValidationError: If snapshot is immutable and locked.
        """
        if self.is_immutable and self.is_locked:
            raise ValidationError(
                f"Cannot delete immutable snapshot '{self.name}' while locked"
            )
        from typing import cast

        manager = cast("CloudSnapshotManager", self._manager)
        manager.delete(self.key)

    def __repr__(self) -> str:
        key = self.get("$key", "?")
        name = self.name
        return f"<CloudSnapshot key={key} name={name!r}>"


class CloudSnapshotManager(ResourceManager[CloudSnapshot]):
    """Manager for cloud (system) snapshot operations.

    Cloud snapshots capture the entire system state including all VMs and
    tenants at a point in time. They are used for disaster recovery and
    point-in-time restoration.

    Example:
        >>> # List all snapshots
        >>> snapshots = client.cloud_snapshots.list()

        >>> # Create a new snapshot
        >>> snapshot = client.cloud_snapshots.create(
        ...     name="Pre-Upgrade",
        ...     retention_seconds=604800,  # 7 days
        ... )

        >>> # Get a snapshot by name with VMs
        >>> snapshot = client.cloud_snapshots.get(
        ...     name="Daily_20260123",
        ...     include_vms=True,
        ... )
        >>> for vm in snapshot.vms:
        ...     print(vm.name)

        >>> # Restore a VM from snapshot
        >>> client.cloud_snapshots.restore_vm(
        ...     snapshot_key=snapshot.key,
        ...     vm_name="WebServer01",
        ...     new_name="WebServer01-Restored",
        ... )

        >>> # Delete a snapshot
        >>> client.cloud_snapshots.delete(snapshot.key)
    """

    _endpoint = "cloud_snapshots"

    def __init__(self, client: VergeClient) -> None:
        super().__init__(client)
        self._vm_managers: dict[int, CloudSnapshotVMManager] = {}
        self._tenant_managers: dict[int, CloudSnapshotTenantManager] = {}

    def _to_model(
        self,
        data: dict[str, Any],
        vms: builtins.list[CloudSnapshotVM] | None = None,
        tenants: builtins.list[CloudSnapshotTenant] | None = None,
    ) -> CloudSnapshot:
        return CloudSnapshot(data, self, vms=vms, tenants=tenants)

    def vms(self, snapshot_key: int) -> CloudSnapshotVMManager:
        """Get the VM manager for a snapshot.

        Args:
            snapshot_key: Snapshot $key (ID).

        Returns:
            CloudSnapshotVMManager for the snapshot.
        """
        if snapshot_key not in self._vm_managers:
            self._vm_managers[snapshot_key] = CloudSnapshotVMManager(
                self._client, snapshot_key
            )
        return self._vm_managers[snapshot_key]

    def tenants(self, snapshot_key: int) -> CloudSnapshotTenantManager:
        """Get the tenant manager for a snapshot.

        Args:
            snapshot_key: Snapshot $key (ID).

        Returns:
            CloudSnapshotTenantManager for the snapshot.
        """
        if snapshot_key not in self._tenant_managers:
            self._tenant_managers[snapshot_key] = CloudSnapshotTenantManager(
                self._client, snapshot_key
            )
        return self._tenant_managers[snapshot_key]

    def list(
        self,
        filter: str | None = None,
        fields: builtins.list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        *,
        include_expired: bool = False,
        include_vms: bool = False,
        include_tenants: bool = False,
        **filter_kwargs: Any,
    ) -> builtins.list[CloudSnapshot]:
        """List cloud snapshots.

        Args:
            filter: OData filter string.
            fields: List of fields to return.
            limit: Maximum number of results.
            offset: Skip this many results.
            include_expired: Include expired snapshots.
            include_vms: Include VMs for each snapshot.
            include_tenants: Include tenants for each snapshot.
            **filter_kwargs: Additional filter arguments.

        Returns:
            List of CloudSnapshot objects sorted by creation time (newest first).

        Example:
            >>> # All active snapshots
            >>> snapshots = client.cloud_snapshots.list()

            >>> # All snapshots including expired
            >>> snapshots = client.cloud_snapshots.list(include_expired=True)

            >>> # Snapshots with VMs and tenants
            >>> snapshots = client.cloud_snapshots.list(
            ...     include_vms=True,
            ...     include_tenants=True,
            ... )
        """
        conditions: builtins.list[str] = []

        # Exclude expired snapshots by default
        if not include_expired:
            now = int(time.time())
            conditions.append(f"(expires eq 0 or expires gt {now})")

        if filter:
            conditions.append(f"({filter})")

        if filter_kwargs:
            conditions.append(build_filter(**filter_kwargs))

        combined_filter = " and ".join(conditions) if conditions else None

        if fields is None:
            fields = _DEFAULT_SNAPSHOT_FIELDS

        params: dict[str, Any] = {}
        if combined_filter:
            params["filter"] = combined_filter
        if fields:
            params["fields"] = ",".join(fields)
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset
        params["sort"] = "-created"

        response = self._client._request("GET", self._endpoint, params=params)

        if response is None:
            return []

        if not isinstance(response, list):
            response = [response]

        snapshots: builtins.list[CloudSnapshot] = []
        for item in response:
            snapshot_vms = None
            snapshot_tenants = None
            snapshot_key = item.get("$key")

            if snapshot_key:
                if include_vms:
                    try:
                        snapshot_vms = self.vms(int(snapshot_key)).list()
                    except Exception:
                        snapshot_vms = []
                if include_tenants:
                    try:
                        snapshot_tenants = self.tenants(int(snapshot_key)).list()
                    except Exception:
                        snapshot_tenants = []

            snapshots.append(
                self._to_model(item, vms=snapshot_vms, tenants=snapshot_tenants)
            )

        return snapshots

    def get(
        self,
        key: int | None = None,
        *,
        name: str | None = None,
        fields: builtins.list[str] | None = None,
        include_vms: bool = False,
        include_tenants: bool = False,
        include_expired: bool = True,
    ) -> CloudSnapshot:
        """Get a cloud snapshot by key or name.

        Args:
            key: Snapshot $key (ID).
            name: Snapshot name.
            fields: List of fields to return.
            include_vms: Include VMs in the snapshot.
            include_tenants: Include tenants in the snapshot.
            include_expired: Include expired snapshots when searching by name.

        Returns:
            CloudSnapshot object.

        Raises:
            NotFoundError: If snapshot not found.
            ValueError: If neither key nor name provided.
        """
        if fields is None:
            fields = _DEFAULT_SNAPSHOT_FIELDS

        if key is not None:
            params: dict[str, Any] = {}
            if fields:
                params["fields"] = ",".join(fields)

            response = self._client._request(
                "GET", f"{self._endpoint}/{key}", params=params
            )
            if response is None:
                raise NotFoundError(f"Cloud snapshot {key} not found")
            if not isinstance(response, dict):
                raise NotFoundError(f"Cloud snapshot {key} returned invalid response")

            snapshot_vms = None
            snapshot_tenants = None
            if include_vms:
                try:
                    snapshot_vms = self.vms(key).list()
                except Exception:
                    snapshot_vms = []
            if include_tenants:
                try:
                    snapshot_tenants = self.tenants(key).list()
                except Exception:
                    snapshot_tenants = []

            return self._to_model(response, vms=snapshot_vms, tenants=snapshot_tenants)

        if name is not None:
            escaped_name = name.replace("'", "''")
            results = self.list(
                filter=f"name eq '{escaped_name}'",
                fields=fields,
                limit=1,
                include_expired=include_expired,
                include_vms=include_vms,
                include_tenants=include_tenants,
            )
            if not results:
                raise NotFoundError(f"Cloud snapshot '{name}' not found")
            return results[0]

        raise ValueError("Either key or name must be provided")

    def create(  # type: ignore[override]
        self,
        name: str | None = None,
        *,
        retention_seconds: int | None = None,
        retention: timedelta | None = None,
        never_expire: bool = False,
        min_snapshots: int = 1,
        immutable: bool = False,
        private: bool = False,
        wait: bool = False,
        wait_timeout: int = 300,
    ) -> CloudSnapshot:
        """Create a new cloud snapshot.

        Args:
            name: Snapshot name. If not provided, a timestamped name is generated.
            retention_seconds: Retention period in seconds (default: 259200 = 3 days).
            retention: Retention period as timedelta (alternative to retention_seconds).
            never_expire: If True, snapshot never expires.
            min_snapshots: Minimum snapshots to retain (default: 1).
            immutable: Make snapshot immutable (locked, read-only).
            private: Hide snapshot from tenants.
            wait: Wait for snapshot creation to complete.
            wait_timeout: Maximum seconds to wait (default: 300).

        Returns:
            Created CloudSnapshot object.

        Raises:
            ValueError: If invalid parameters.
            APIError: If creation fails.

        Example:
            >>> # Create with default settings (3-day retention)
            >>> snapshot = client.cloud_snapshots.create()

            >>> # Create with custom name and retention
            >>> snapshot = client.cloud_snapshots.create(
            ...     name="Pre-Upgrade",
            ...     retention=timedelta(days=7),
            ... )

            >>> # Create immutable snapshot that never expires
            >>> snapshot = client.cloud_snapshots.create(
            ...     name="Permanent-Backup",
            ...     never_expire=True,
            ...     immutable=True,
            ... )
        """
        # Generate default name if not provided
        if name is None:
            name = datetime.now().strftime("Snapshot_%Y%m%d_%H%M")

        # Build request body
        body: dict[str, Any] = {
            "name": name,
            "min_snapshots": min_snapshots,
        }

        # Handle retention
        if never_expire:
            body["retention"] = 0
        elif retention is not None:
            body["retention"] = int(retention.total_seconds())
        elif retention_seconds is not None:
            body["retention"] = retention_seconds
        else:
            # Default: 3 days
            body["retention"] = 259200

        if immutable:
            body["immutable"] = True

        if private:
            body["private"] = True

        response = self._client._request("POST", self._endpoint, json_data=body)
        if response is None:
            raise ValueError("No response from create operation")
        if not isinstance(response, dict):
            raise ValueError("Create operation returned invalid response")

        snapshot_key = response.get("$key")
        task_key = response.get("task")

        if wait and task_key:
            # Wait for task to complete
            from pyvergeos.resources.tasks import TaskManager

            task_manager = TaskManager(self._client)
            task = task_manager.wait(int(task_key), timeout=wait_timeout)
            if task.has_error:
                raise ValidationError(f"Snapshot creation failed: {task.status_info}")

        if snapshot_key:
            return self.get(int(snapshot_key))

        return self._to_model(response)

    def delete(self, key: int) -> None:
        """Delete a cloud snapshot.

        Args:
            key: Snapshot $key (ID).

        Raises:
            ValidationError: If snapshot is immutable and locked.
            NotFoundError: If snapshot not found.
        """
        self._client._request("DELETE", f"{self._endpoint}/{key}")

    def restore_vm(
        self,
        snapshot_key: int | None = None,
        snapshot_name: str | None = None,
        *,
        vm_key: int | None = None,
        vm_name: str | None = None,
        new_name: str | None = None,
    ) -> dict[str, Any]:
        """Restore a VM from a cloud snapshot.

        Creates a new VM from the snapshot data. Does not overwrite any existing VM.

        Args:
            snapshot_key: Cloud snapshot $key (ID).
            snapshot_name: Cloud snapshot name (alternative to snapshot_key).
            vm_key: VM snapshot key within the cloud snapshot.
            vm_name: VM name within the cloud snapshot (alternative to vm_key).
            new_name: Optional new name for the restored VM.

        Returns:
            Dict with restore operation details (task key if available).

        Raises:
            ValueError: If required parameters not provided.
            NotFoundError: If snapshot or VM not found.

        Example:
            >>> # Restore VM by name
            >>> result = client.cloud_snapshots.restore_vm(
            ...     snapshot_name="Daily_20260123",
            ...     vm_name="WebServer01",
            ...     new_name="WebServer01-Restored",
            ... )

            >>> # Restore by keys
            >>> result = client.cloud_snapshots.restore_vm(
            ...     snapshot_key=5,
            ...     vm_key=123,
            ... )
        """
        # Resolve snapshot
        if snapshot_key is None and snapshot_name is None:
            raise ValueError("Either snapshot_key or snapshot_name must be provided")

        if snapshot_key is None:
            snapshot = self.get(name=snapshot_name, include_expired=True)
            snapshot_key = snapshot.key

        # Resolve VM
        if vm_key is None and vm_name is None:
            raise ValueError("Either vm_key or vm_name must be provided")

        if vm_key is None:
            vm = self.vms(snapshot_key).get(name=vm_name)
            vm_key = vm.key

        # Build recover action
        body: dict[str, Any] = {
            "action": "recover",
            "params": {
                "rows": [vm_key],
            },
        }

        if new_name:
            body["params"]["name"] = new_name

        response = self._client._request(
            "POST", "cloud_snapshot_vm_actions", json_data=body
        )

        result: dict[str, Any] = {
            "snapshot_key": snapshot_key,
            "vm_key": vm_key,
            "status": "initiated",
        }

        if response and isinstance(response, dict):
            if "task" in response:
                result["task_key"] = response["task"]
            result["response"] = response

        return result

    def restore_tenant(
        self,
        snapshot_key: int | None = None,
        snapshot_name: str | None = None,
        *,
        tenant_key: int | None = None,
        tenant_name: str | None = None,
        new_name: str | None = None,
    ) -> dict[str, Any]:
        """Restore a tenant from a cloud snapshot.

        Creates a new tenant from the snapshot data. Does not overwrite any existing tenant.

        Args:
            snapshot_key: Cloud snapshot $key (ID).
            snapshot_name: Cloud snapshot name (alternative to snapshot_key).
            tenant_key: Tenant snapshot key within the cloud snapshot.
            tenant_name: Tenant name within the cloud snapshot (alternative to tenant_key).
            new_name: Optional new name for the restored tenant.

        Returns:
            Dict with restore operation details (task key if available).

        Raises:
            ValueError: If required parameters not provided.
            NotFoundError: If snapshot or tenant not found.

        Example:
            >>> # Restore tenant by name
            >>> result = client.cloud_snapshots.restore_tenant(
            ...     snapshot_name="Daily_20260123",
            ...     tenant_name="CustomerA",
            ...     new_name="CustomerA-DR",
            ... )
        """
        # Resolve snapshot
        if snapshot_key is None and snapshot_name is None:
            raise ValueError("Either snapshot_key or snapshot_name must be provided")

        if snapshot_key is None:
            snapshot = self.get(name=snapshot_name, include_expired=True)
            snapshot_key = snapshot.key

        # Resolve tenant
        if tenant_key is None and tenant_name is None:
            raise ValueError("Either tenant_key or tenant_name must be provided")

        if tenant_key is None:
            tenant = self.tenants(snapshot_key).get(name=tenant_name)
            tenant_key = tenant.key

        # Build recover action
        body: dict[str, Any] = {
            "action": "recover",
            "params": {
                "rows": [tenant_key],
            },
        }

        if new_name:
            body["params"]["name"] = new_name

        response = self._client._request(
            "POST", "cloud_snapshot_tenant_actions", json_data=body
        )

        result: dict[str, Any] = {
            "snapshot_key": snapshot_key,
            "tenant_key": tenant_key,
            "status": "initiated",
        }

        if response and isinstance(response, dict):
            if "task" in response:
                result["task_key"] = response["task"]
            result["response"] = response

        return result
