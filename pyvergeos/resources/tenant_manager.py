"""Tenant resource manager."""

from __future__ import annotations

import builtins
import logging
from typing import TYPE_CHECKING, Any

from pyvergeos.resources.base import ResourceManager, ResourceObject

# Import sub-managers for use in properties
from pyvergeos.resources.tenant_external_ips import TenantExternalIPManager
from pyvergeos.resources.tenant_layer2 import TenantLayer2Manager
from pyvergeos.resources.tenant_network_blocks import TenantNetworkBlockManager
from pyvergeos.resources.tenant_snapshots import TenantSnapshotManager
from pyvergeos.resources.tenant_storage import TenantStorageManager

if TYPE_CHECKING:
    from pyvergeos.client import VergeClient

logger = logging.getLogger(__name__)

# Default fields to request for tenants (includes status info via field aliases)
TENANT_DEFAULT_FIELDS = [
    "$key",
    "name",
    "description",
    "url",
    "uuid",
    "created",
    "creator",
    "is_snapshot",
    "isolate",
    "note",
    "expose_cloud_snapshots",
    "allow_branding",
    "status#status as status",
    "status#running as running",
    "status#starting as starting",
    "status#stopping as stopping",
    "status#migrating as migrating",
    "status#started as started_ts",
    "status#stopped as stopped_ts",
    "status#state as state",
    "vnet",
    "vnet#name as network_name",
    "ui_address",
    "ui_address#ip as ui_address_ip",
]


class Tenant(ResourceObject):
    """Tenant resource object."""

    def power_on(self, preferred_node: int | None = None) -> Tenant:
        """Power on the tenant.

        Args:
            preferred_node: Node $key to start tenant on.

        Returns:
            Self for chaining.

        Raises:
            ValueError: If tenant is a snapshot.
        """
        if self.is_snapshot:
            raise ValueError("Cannot power on a snapshot")

        body: dict[str, Any] = {"tenant": self.key, "action": "poweron"}
        if preferred_node is not None:
            body["params"] = {"preferred_node": preferred_node}

        self._manager._client._request("POST", "tenant_actions", json_data=body)
        return self

    def power_off(self) -> Tenant:
        """Power off the tenant gracefully.

        Returns:
            Self for chaining.

        Raises:
            ValueError: If tenant is a snapshot.
        """
        if self.is_snapshot:
            raise ValueError("Cannot power off a snapshot")

        self._manager._client._request(
            "POST", "tenant_actions", json_data={"tenant": self.key, "action": "poweroff"}
        )
        return self

    def reset(self) -> Tenant:
        """Reset the tenant (hard reboot).

        Returns:
            Self for chaining.

        Raises:
            ValueError: If tenant is a snapshot.
        """
        if self.is_snapshot:
            raise ValueError("Cannot reset a snapshot")

        self._manager._client._request(
            "POST", "tenant_actions", json_data={"tenant": self.key, "action": "reset"}
        )
        return self

    def restart(self) -> Tenant:
        """Restart the tenant (alias for reset).

        Returns:
            Self for chaining.
        """
        return self.reset()

    def clone(
        self,
        name: str | None = None,
        no_network: bool = False,
        no_storage: bool = False,
        no_nodes: bool = False,
    ) -> dict[str, Any] | None:
        """Clone this tenant.

        Args:
            name: Name for the clone. If not provided, a default name is generated.
            no_network: Do not clone the network configuration.
            no_storage: Do not clone the storage configuration.
            no_nodes: Do not clone the nodes (VMs).

        Returns:
            Clone task information.

        Raises:
            ValueError: If tenant is a snapshot.
        """
        if self.is_snapshot:
            raise ValueError("Cannot clone a snapshot. Use restore instead.")

        params: dict[str, Any] = {}
        if name:
            params["name"] = name
        if no_network:
            params["no_vnet"] = True
        if no_storage:
            params["no_storage"] = True
        if no_nodes:
            params["no_nodes"] = True

        body: dict[str, Any] = {"tenant": self.key, "action": "clone"}
        if params:
            body["params"] = params

        result = self._manager._client._request("POST", "tenant_actions", json_data=body)
        return result if isinstance(result, dict) else None

    def refresh(self) -> Tenant:
        """Refresh tenant data from API.

        Returns:
            Updated Tenant object.
        """
        from typing import cast

        manager = cast("TenantManager", self._manager)
        return manager.get(self.key)

    def save(self, **kwargs: Any) -> Tenant:
        """Save changes to tenant.

        Args:
            **kwargs: Fields to update.

        Returns:
            Updated Tenant object.
        """
        from typing import cast

        manager = cast("TenantManager", self._manager)
        return manager.update(self.key, **kwargs)

    @property
    def is_running(self) -> bool:
        """Check if tenant is powered on."""
        return bool(self.get("running", False))

    @property
    def is_starting(self) -> bool:
        """Check if tenant is starting."""
        return bool(self.get("starting", False))

    @property
    def is_stopping(self) -> bool:
        """Check if tenant is stopping."""
        return bool(self.get("stopping", False))

    @property
    def is_migrating(self) -> bool:
        """Check if tenant is migrating."""
        return bool(self.get("migrating", False))

    @property
    def is_snapshot(self) -> bool:
        """Check if this is a snapshot (not a real tenant)."""
        return bool(self.get("is_snapshot", False))

    @property
    def is_isolated(self) -> bool:
        """Check if tenant network isolation is enabled."""
        return bool(self.get("isolate", False))

    @property
    def status(self) -> str:
        """Get tenant status (online, offline, starting, etc.)."""
        return str(self.get("status", "unknown"))

    @property
    def state(self) -> str:
        """Get tenant state (online, offline, warning, error)."""
        return str(self.get("state", "unknown"))

    @property
    def network_name(self) -> str | None:
        """Get the name of the tenant's network."""
        return self.get("network_name")

    @property
    def ui_address_ip(self) -> str | None:
        """Get the UI access IP address."""
        return self.get("ui_address_ip")

    @property
    def snapshots(self) -> TenantSnapshotManager:
        """Get the snapshot manager for this tenant.

        Returns:
            TenantSnapshotManager for managing tenant snapshots.

        Example:
            >>> tenant = client.tenants.get(name="my-tenant")
            >>> snapshots = tenant.snapshots.list()
            >>> tenant.snapshots.create("pre-upgrade")
        """
        from typing import cast

        manager = cast("TenantManager", self._manager)
        return TenantSnapshotManager(manager._client, self)

    @property
    def storage(self) -> TenantStorageManager:
        """Get the storage manager for this tenant.

        Returns:
            TenantStorageManager for managing tenant storage allocations.

        Example:
            >>> tenant = client.tenants.get(name="my-tenant")
            >>> # List storage allocations
            >>> for alloc in tenant.storage.list():
            ...     print(f"{alloc.tier_name}: {alloc.provisioned_gb} GB")
            >>> # Add storage from Tier 1
            >>> tenant.storage.create(tier=1, provisioned_gb=100)
        """
        from typing import cast

        manager = cast("TenantManager", self._manager)
        return TenantStorageManager(manager._client, self)

    @property
    def network_blocks(self) -> TenantNetworkBlockManager:
        """Get the network block manager for this tenant.

        Returns:
            TenantNetworkBlockManager for managing tenant network blocks.

        Example:
            >>> tenant = client.tenants.get(name="my-tenant")
            >>> # List network blocks
            >>> for block in tenant.network_blocks.list():
            ...     print(f"{block.cidr} on {block.network_name}")
            >>> # Assign a network block
            >>> tenant.network_blocks.create(network=1, cidr="192.168.100.0/24")
        """
        from typing import cast

        manager = cast("TenantManager", self._manager)
        return TenantNetworkBlockManager(manager._client, self)

    @property
    def external_ips(self) -> TenantExternalIPManager:
        """Get the external IP manager for this tenant.

        Returns:
            TenantExternalIPManager for managing tenant external IPs.

        Example:
            >>> tenant = client.tenants.get(name="my-tenant")
            >>> # List external IPs
            >>> for ip in tenant.external_ips.list():
            ...     print(f"{ip.ip_address} on {ip.network_name}")
            >>> # Assign an external IP
            >>> tenant.external_ips.create(network=1, ip="192.168.1.100")
        """
        from typing import cast

        manager = cast("TenantManager", self._manager)
        return TenantExternalIPManager(manager._client, self)

    @property
    def l2_networks(self) -> TenantLayer2Manager:
        """Get the Layer 2 network manager for this tenant.

        Returns:
            TenantLayer2Manager for managing tenant Layer 2 networks.

        Example:
            >>> tenant = client.tenants.get(name="my-tenant")
            >>> # List Layer 2 networks
            >>> for l2 in tenant.l2_networks.list():
            ...     print(f"{l2.network_name}: {l2.is_enabled}")
            >>> # Assign a Layer 2 network
            >>> tenant.l2_networks.create(network_name="VLAN100")
        """
        from typing import cast

        manager = cast("TenantManager", self._manager)
        return TenantLayer2Manager(manager._client, self)


class TenantManager(ResourceManager[Tenant]):
    """Manager for Tenant operations."""

    _endpoint = "tenants"
    _default_fields = TENANT_DEFAULT_FIELDS

    def __init__(self, client: VergeClient) -> None:
        super().__init__(client)

    def _to_model(self, data: dict[str, Any]) -> Tenant:
        return Tenant(data, self)

    def list(
        self,
        filter: str | None = None,  # noqa: A002
        fields: builtins.list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        include_snapshots: bool = False,
        **filter_kwargs: Any,
    ) -> builtins.list[Tenant]:
        """List tenants with optional filtering.

        Args:
            filter: OData filter string.
            fields: List of fields to return (defaults to rich field set).
            limit: Maximum number of results.
            offset: Skip this many results.
            include_snapshots: Include tenant snapshots (default False).
            **filter_kwargs: Shorthand filter arguments.

        Returns:
            List of Tenant objects.
        """
        # Use default fields if not specified
        if fields is None:
            fields = self._default_fields

        # Add snapshot filter unless explicitly including snapshots
        if not include_snapshots:
            snapshot_filter = "is_snapshot eq false"
            filter = f"({filter}) and {snapshot_filter}" if filter else snapshot_filter

        return super().list(
            filter=filter,
            fields=fields,
            limit=limit,
            offset=offset,
            **filter_kwargs,
        )

    def get(
        self,
        key: int | None = None,
        *,
        name: str | None = None,
        fields: builtins.list[str] | None = None,
    ) -> Tenant:
        """Get a single tenant by key or name.

        Args:
            key: Tenant $key (ID).
            name: Tenant name (will search if key not provided).
            fields: List of fields to return (defaults to rich field set).

        Returns:
            Tenant object.

        Raises:
            NotFoundError: If tenant not found.
            ValueError: If neither key nor name provided.
        """
        if fields is None:
            fields = self._default_fields
        return super().get(key, name=name, fields=fields)

    def list_running(self) -> builtins.list[Tenant]:
        """List all running tenants."""
        return [tenant for tenant in self.list() if tenant.is_running]

    def list_stopped(self) -> builtins.list[Tenant]:
        """List all stopped tenants."""
        return [
            tenant for tenant in self.list() if not tenant.is_running and not tenant.is_starting
        ]

    def list_by_status(self, status: str) -> builtins.list[Tenant]:
        """List tenants by status.

        Args:
            status: Status to filter by (online, offline, starting, stopping,
                    migrating, error, reduced, provisioning, restarting).

        Returns:
            List of Tenant objects matching the status.
        """
        return [tenant for tenant in self.list() if tenant.status == status]

    def create(  # type: ignore[override]
        self,
        name: str,
        password: str | None = None,
        description: str = "",
        url: str | None = None,
        note: str | None = None,
        expose_cloud_snapshots: bool = True,
        allow_branding: bool = False,
        require_password_change: bool = False,
        **kwargs: Any,
    ) -> Tenant:
        """Create a new tenant.

        The tenant is created in a stopped state by default.

        Args:
            name: Tenant name (required, 1-120 characters).
            password: Password for the auto-created admin user.
                     If not specified, a random password is generated.
            description: Tenant description.
            url: URL associated with the tenant.
            note: Note for the tenant.
            expose_cloud_snapshots: Allow tenant to request cloud snapshots (default True).
            allow_branding: Allow tenant to customize branding (default False).
            require_password_change: Require password change on first login (default False).
            **kwargs: Additional tenant properties.

        Returns:
            Created Tenant object.
        """
        data: dict[str, Any] = {
            "name": name,
            "expose_cloud_snapshots": expose_cloud_snapshots,
        }

        if password:
            data["password"] = password
        if description:
            data["description"] = description
        if url:
            data["url"] = url
        if note:
            data["note"] = note
        if allow_branding:
            data["allow_branding"] = True
        if require_password_change:
            data["change_password"] = True

        # Add any additional kwargs
        data.update(kwargs)

        # Create tenant and fetch full data with all fields
        tenant = super().create(**data)
        # The API only returns limited fields on create, so fetch the full tenant
        return self.get(tenant.key)

    def update(self, key: int, **kwargs: Any) -> Tenant:
        """Update an existing tenant.

        Args:
            key: Tenant $key (ID).
            **kwargs: Attributes to update. Supported fields include:
                - name: New name for the tenant
                - description: Tenant description
                - url: URL associated with the tenant
                - note: Note for the tenant
                - expose_cloud_snapshots: Allow cloud snapshots
                - allow_branding: Allow branding customization

        Returns:
            Updated Tenant object.
        """
        # Perform the update
        self._client._request("PUT", f"{self._endpoint}/{key}", json_data=kwargs)
        # Fetch the updated tenant with full fields
        return self.get(key)

    def power_on(self, key: int, preferred_node: int | None = None) -> dict[str, Any] | None:
        """Power on a tenant.

        Args:
            key: Tenant $key (ID).
            preferred_node: Node $key to start tenant on.

        Returns:
            Action response (may include task information).
        """
        body: dict[str, Any] = {"tenant": key, "action": "poweron"}
        if preferred_node is not None:
            body["params"] = {"preferred_node": preferred_node}

        result = self._client._request("POST", "tenant_actions", json_data=body)
        return result if isinstance(result, dict) else None

    def power_off(self, key: int) -> dict[str, Any] | None:
        """Power off a tenant gracefully.

        Args:
            key: Tenant $key (ID).

        Returns:
            Action response (may include task information).
        """
        result = self._client._request(
            "POST", "tenant_actions", json_data={"tenant": key, "action": "poweroff"}
        )
        return result if isinstance(result, dict) else None

    def reset(self, key: int) -> dict[str, Any] | None:
        """Reset a tenant (hard reboot).

        Args:
            key: Tenant $key (ID).

        Returns:
            Action response (may include task information).
        """
        result = self._client._request(
            "POST", "tenant_actions", json_data={"tenant": key, "action": "reset"}
        )
        return result if isinstance(result, dict) else None

    def restart(self, key: int) -> dict[str, Any] | None:
        """Restart a tenant (alias for reset).

        Args:
            key: Tenant $key (ID).

        Returns:
            Action response (may include task information).
        """
        return self.reset(key)

    def clone(
        self,
        key: int,
        name: str | None = None,
        no_network: bool = False,
        no_storage: bool = False,
        no_nodes: bool = False,
    ) -> dict[str, Any] | None:
        """Clone a tenant.

        Args:
            key: Tenant $key (ID) of the source tenant.
            name: Name for the clone. If not provided, a default name is generated.
            no_network: Do not clone the network configuration.
            no_storage: Do not clone the storage configuration.
            no_nodes: Do not clone the nodes (VMs).

        Returns:
            Clone task information.
        """
        params: dict[str, Any] = {}
        if name:
            params["name"] = name
        if no_network:
            params["no_vnet"] = True
        if no_storage:
            params["no_storage"] = True
        if no_nodes:
            params["no_nodes"] = True

        body: dict[str, Any] = {"tenant": key, "action": "clone"}
        if params:
            body["params"] = params

        result = self._client._request("POST", "tenant_actions", json_data=body)
        return result if isinstance(result, dict) else None

    def snapshots(self, tenant_key: int) -> TenantSnapshotManager:
        """Get the snapshot manager for a specific tenant.

        Args:
            tenant_key: Tenant $key (ID).

        Returns:
            TenantSnapshotManager for managing tenant snapshots.

        Example:
            >>> # Access snapshot manager directly by tenant key
            >>> snapshot_manager = client.tenants.snapshots(123)
            >>> snapshots = snapshot_manager.list()
        """
        tenant = self.get(tenant_key)
        return TenantSnapshotManager(self._client, tenant)

    def storage(self, tenant_key: int) -> TenantStorageManager:
        """Get the storage manager for a specific tenant.

        Args:
            tenant_key: Tenant $key (ID).

        Returns:
            TenantStorageManager for managing tenant storage allocations.

        Example:
            >>> # Access storage manager directly by tenant key
            >>> storage_manager = client.tenants.storage(123)
            >>> allocations = storage_manager.list()
        """
        tenant = self.get(tenant_key)
        return TenantStorageManager(self._client, tenant)

    def network_blocks(self, tenant_key: int) -> TenantNetworkBlockManager:
        """Get the network block manager for a specific tenant.

        Args:
            tenant_key: Tenant $key (ID).

        Returns:
            TenantNetworkBlockManager for managing tenant network blocks.

        Example:
            >>> # Access network block manager directly by tenant key
            >>> block_manager = client.tenants.network_blocks(123)
            >>> blocks = block_manager.list()
        """
        tenant = self.get(tenant_key)
        return TenantNetworkBlockManager(self._client, tenant)

    def external_ips(self, tenant_key: int) -> TenantExternalIPManager:
        """Get the external IP manager for a specific tenant.

        Args:
            tenant_key: Tenant $key (ID).

        Returns:
            TenantExternalIPManager for managing tenant external IPs.

        Example:
            >>> # Access external IP manager directly by tenant key
            >>> ip_manager = client.tenants.external_ips(123)
            >>> ips = ip_manager.list()
        """
        tenant = self.get(tenant_key)
        return TenantExternalIPManager(self._client, tenant)

    def l2_networks(self, tenant_key: int) -> TenantLayer2Manager:
        """Get the Layer 2 network manager for a specific tenant.

        Args:
            tenant_key: Tenant $key (ID).

        Returns:
            TenantLayer2Manager for managing tenant Layer 2 networks.

        Example:
            >>> # Access Layer 2 network manager directly by tenant key
            >>> l2_manager = client.tenants.l2_networks(123)
            >>> l2_networks = l2_manager.list()
        """
        tenant = self.get(tenant_key)
        return TenantLayer2Manager(self._client, tenant)
