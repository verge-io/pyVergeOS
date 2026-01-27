"""Tenant resource manager."""

from __future__ import annotations

import builtins
import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from pyvergeos.resources.base import ResourceManager, ResourceObject

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

# Default fields for tenant snapshots
TENANT_SNAPSHOT_DEFAULT_FIELDS = [
    "$key",
    "tenant",
    "name",
    "description",
    "profile",
    "period",
    "min_snapshots",
    "created",
    "expires",
]

# Default fields for tenant storage allocations
TENANT_STORAGE_DEFAULT_FIELDS = [
    "$key",
    "tenant",
    "tier",
    "tier#tier as tier_number",
    "tier#description as tier_description",
    "provisioned",
    "used",
    "allocated",
    "used_pct",
    "last_update",
]

# Default fields for tenant network blocks
TENANT_NETWORK_BLOCK_DEFAULT_FIELDS = [
    "$key",
    "vnet",
    "vnet#name as network_name",
    "cidr",
    "description",
    "owner",
]

# Default fields for tenant external IPs
TENANT_EXTERNAL_IP_DEFAULT_FIELDS = [
    "$key",
    "vnet",
    "vnet#name as network_name",
    "ip",
    "type",
    "hostname",
    "description",
    "owner",
    "mac",
]


class TenantSnapshot(ResourceObject):
    """Tenant Snapshot resource object."""

    @property
    def tenant_key(self) -> int:
        """Get the tenant key this snapshot belongs to."""
        return int(self.get("tenant", 0))

    @property
    def created_at(self) -> datetime | None:
        """Get creation timestamp as datetime."""
        timestamp = self.get("created")
        if timestamp:
            return datetime.fromtimestamp(int(timestamp), tz=timezone.utc)
        return None

    @property
    def expires_at(self) -> datetime | None:
        """Get expiration timestamp as datetime."""
        timestamp = self.get("expires")
        if timestamp and int(timestamp) > 0:
            return datetime.fromtimestamp(int(timestamp), tz=timezone.utc)
        return None

    @property
    def never_expires(self) -> bool:
        """Check if snapshot never expires."""
        expires = self.get("expires")
        return expires is None or int(expires) == 0

    @property
    def profile(self) -> str | None:
        """Get the snapshot profile name (if created by a profile)."""
        return self.get("profile")

    @property
    def period(self) -> str | None:
        """Get the snapshot period (if created by a profile)."""
        return self.get("period")

    @property
    def min_snapshots(self) -> int:
        """Get minimum snapshots to keep."""
        return int(self.get("min_snapshots", 0))

    def restore(self) -> dict[str, Any] | None:
        """Restore the tenant to this snapshot.

        The tenant must be powered off before restoration.

        Returns:
            Restore task information.

        Raises:
            ValueError: If the tenant is running.
        """
        from typing import cast

        manager = cast("TenantSnapshotManager", self._manager)
        return manager.restore(self.key)


class TenantSnapshotManager(ResourceManager[TenantSnapshot]):
    """Manager for Tenant Snapshot operations.

    This manager is accessed through a Tenant object's snapshots property
    or via client.tenants.snapshots(tenant_key).
    """

    _endpoint = "tenant_snapshots"
    _default_fields = TENANT_SNAPSHOT_DEFAULT_FIELDS

    def __init__(self, client: VergeClient, tenant: Tenant) -> None:
        super().__init__(client)
        self._tenant = tenant

    def _to_model(self, data: dict[str, Any]) -> TenantSnapshot:
        return TenantSnapshot(data, self)

    def list(  # type: ignore[override]
        self,
        filter: str | None = None,  # noqa: A002
        fields: builtins.list[str] | None = None,
        **kwargs: Any,
    ) -> builtins.list[TenantSnapshot]:
        """List snapshots for this tenant.

        Args:
            filter: Additional OData filter string.
            fields: List of fields to return.
            **kwargs: Additional filter arguments.

        Returns:
            List of TenantSnapshot objects.
        """
        if fields is None:
            fields = self._default_fields

        # Build filter for this tenant
        tenant_filter = f"tenant eq {self._tenant.key}"
        if filter:
            tenant_filter = f"{tenant_filter} and ({filter})"

        params: dict[str, Any] = {
            "filter": tenant_filter,
            "fields": ",".join(fields),
            "sort": "-created",  # Most recent first
        }

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
    ) -> TenantSnapshot:
        """Get a snapshot by key or name.

        Args:
            key: Snapshot $key (ID).
            name: Snapshot name.
            fields: List of fields to return.

        Returns:
            TenantSnapshot object.

        Raises:
            NotFoundError: If snapshot not found.
            ValueError: If neither key nor name provided.
        """
        if fields is None:
            fields = self._default_fields

        if key is not None:
            params: dict[str, Any] = {"fields": ",".join(fields)}
            response = self._client._request("GET", f"{self._endpoint}/{key}", params=params)
            if response is None:
                from pyvergeos.exceptions import NotFoundError

                raise NotFoundError(f"Tenant snapshot {key} not found")
            if not isinstance(response, dict):
                from pyvergeos.exceptions import NotFoundError

                raise NotFoundError(f"Tenant snapshot {key} returned invalid response")
            return self._to_model(response)

        if name is not None:
            snapshots = self.list(filter=f"name eq '{name}'", fields=fields)
            if not snapshots:
                from pyvergeos.exceptions import NotFoundError

                raise NotFoundError(f"Tenant snapshot with name '{name}' not found")
            return snapshots[0]

        raise ValueError("Either key or name must be provided")

    def create(  # type: ignore[override]
        self,
        name: str,
        description: str = "",
        expires_in_days: int = 0,
        expires_at: datetime | None = None,
    ) -> TenantSnapshot:
        """Create a new snapshot for this tenant.

        Args:
            name: Snapshot name (required).
            description: Snapshot description.
            expires_in_days: Days until snapshot expires. Use 0 for never expires.
            expires_at: Specific expiration datetime (overrides expires_in_days).

        Returns:
            Created TenantSnapshot object.

        Raises:
            ValueError: If tenant is a snapshot.
            ConflictError: If a snapshot with this name already exists.
        """
        if self._tenant.is_snapshot:
            raise ValueError("Cannot create snapshot of a tenant snapshot")

        body: dict[str, Any] = {
            "tenant": self._tenant.key,
            "name": name,
        }

        if description:
            body["description"] = description

        # Calculate expiration timestamp
        if expires_at is not None:
            body["expires"] = int(expires_at.timestamp())
        elif expires_in_days > 0:
            import time

            body["expires"] = int(time.time()) + (expires_in_days * 86400)

        logger.debug(f"Creating tenant snapshot '{name}' for tenant '{self._tenant.name}'")
        self._client._request("POST", self._endpoint, json_data=body)

        # Fetch the created snapshot
        import time

        time.sleep(0.5)  # Brief wait for API consistency
        return self.get(name=name)

    def delete(self, key: int) -> None:
        """Delete a snapshot.

        Args:
            key: Snapshot $key (ID).
        """
        logger.debug(f"Deleting tenant snapshot {key}")
        self._client._request("DELETE", f"{self._endpoint}/{key}")

    def restore(self, key: int) -> dict[str, Any] | None:
        """Restore the tenant to a snapshot.

        The tenant must be powered off before restoration.
        WARNING: All changes made after the snapshot was created will be lost.

        Args:
            key: Snapshot $key (ID).

        Returns:
            Restore task information.

        Raises:
            ValueError: If tenant is running.
        """
        # Refresh tenant state to check if running
        tenant = self._tenant.refresh()
        if tenant.is_running:
            raise ValueError(
                f"Cannot restore tenant '{tenant.name}': Tenant must be powered off first"
            )

        body: dict[str, Any] = {
            "tenant": self._tenant.key,
            "action": "restore",
            "params": {"snapshot": key},
        }

        logger.debug(f"Restoring tenant '{self._tenant.name}' from snapshot {key}")
        result = self._client._request("POST", "tenant_actions", json_data=body)
        return result if isinstance(result, dict) else None


class TenantStorage(ResourceObject):
    """Tenant Storage allocation resource object.

    Represents a storage tier allocation for a tenant. Each tenant can have
    allocations from different storage tiers. Values are in bytes but convenience
    properties provide GB conversions.
    """

    @property
    def tenant_key(self) -> int:
        """Get the tenant key this allocation belongs to."""
        return int(self.get("tenant", 0))

    @property
    def tier_key(self) -> int:
        """Get the storage tier key."""
        return int(self.get("tier", 0))

    @property
    def tier(self) -> int:
        """Get the tier number (1-5)."""
        return int(self.get("tier_number", 0))

    @property
    def tier_name(self) -> str:
        """Get the formatted tier name (e.g., 'Tier 1')."""
        return f"Tier {self.tier}"

    @property
    def tier_description(self) -> str | None:
        """Get the tier description."""
        return self.get("tier_description")

    @property
    def provisioned_bytes(self) -> int:
        """Get provisioned storage in bytes."""
        return int(self.get("provisioned", 0))

    @property
    def provisioned_gb(self) -> float:
        """Get provisioned storage in GB."""
        return round(self.provisioned_bytes / 1073741824, 2)

    @property
    def used_bytes(self) -> int:
        """Get used storage in bytes."""
        return int(self.get("used", 0))

    @property
    def used_gb(self) -> float:
        """Get used storage in GB."""
        return round(self.used_bytes / 1073741824, 2)

    @property
    def allocated_bytes(self) -> int:
        """Get allocated storage in bytes."""
        return int(self.get("allocated", 0))

    @property
    def allocated_gb(self) -> float:
        """Get allocated storage in GB."""
        return round(self.allocated_bytes / 1073741824, 2)

    @property
    def used_percent(self) -> int:
        """Get percentage of provisioned storage used."""
        return int(self.get("used_pct", 0))

    @property
    def free_bytes(self) -> int:
        """Get free (provisioned - used) storage in bytes."""
        return max(0, self.provisioned_bytes - self.used_bytes)

    @property
    def free_gb(self) -> float:
        """Get free storage in GB."""
        return round(self.free_bytes / 1073741824, 2)

    @property
    def last_update(self) -> datetime | None:
        """Get last update timestamp as datetime."""
        timestamp = self.get("last_update")
        if timestamp:
            return datetime.fromtimestamp(int(timestamp), tz=timezone.utc)
        return None

    def save(self, provisioned_gb: int | None = None, **kwargs: Any) -> TenantStorage:
        """Save changes to this storage allocation.

        Args:
            provisioned_gb: New provisioned size in GB (convenience parameter).
            **kwargs: Additional fields to update.

        Returns:
            Updated TenantStorage object.
        """
        from typing import cast

        manager = cast("TenantStorageManager", self._manager)
        if provisioned_gb is not None:
            kwargs["provisioned"] = provisioned_gb * 1073741824
        return manager.update(self.key, **kwargs)

    def delete(self) -> None:
        """Delete this storage allocation."""
        from typing import cast

        manager = cast("TenantStorageManager", self._manager)
        manager.delete(self.key)

    def __repr__(self) -> str:
        return (
            f"<TenantStorage {self.tier_name}: "
            f"{self.used_gb:.1f}/{self.provisioned_gb:.1f} GB ({self.used_percent}%)>"
        )


class TenantStorageManager(ResourceManager[TenantStorage]):
    """Manager for Tenant Storage allocation operations.

    This manager handles storage tier allocations for tenants. Each tenant
    can have storage allocated from one or more storage tiers.

    This manager is accessed through a Tenant object's storage property
    or via client.tenants.storage(tenant_key).

    Example:
        >>> tenant = client.tenants.get(name="my-tenant")
        >>> # List all storage allocations
        >>> for alloc in tenant.storage.list():
        ...     print(f"{alloc.tier_name}: {alloc.provisioned_gb} GB")
        >>> # Add storage from Tier 1
        >>> tenant.storage.create(tier=1, provisioned_gb=100)
        >>> # Update allocation
        >>> tenant.storage.update_by_tier(1, provisioned_gb=200)
    """

    _endpoint = "tenant_storage"
    _default_fields = TENANT_STORAGE_DEFAULT_FIELDS

    def __init__(self, client: VergeClient, tenant: Tenant) -> None:
        super().__init__(client)
        self._tenant = tenant

    def _to_model(self, data: dict[str, Any]) -> TenantStorage:
        return TenantStorage(data, self)

    def list(  # type: ignore[override]
        self,
        filter: str | None = None,  # noqa: A002
        fields: builtins.list[str] | None = None,
        tier: int | None = None,
        **kwargs: Any,
    ) -> builtins.list[TenantStorage]:
        """List storage allocations for this tenant.

        Args:
            filter: Additional OData filter string.
            fields: List of fields to return.
            tier: Filter by specific tier number (1-5).
            **kwargs: Additional filter arguments.

        Returns:
            List of TenantStorage objects.
        """
        if fields is None:
            fields = self._default_fields

        # Build filter for this tenant
        tenant_filter = f"tenant eq {self._tenant.key}"
        if filter:
            tenant_filter = f"{tenant_filter} and ({filter})"

        params: dict[str, Any] = {
            "filter": tenant_filter,
            "fields": ",".join(fields),
        }

        response = self._client._request("GET", self._endpoint, params=params)

        if response is None:
            return []

        if not isinstance(response, list):
            items = [self._to_model(response)]
        else:
            items = [self._to_model(item) for item in response]

        # Filter by tier number if specified
        if tier is not None:
            items = [item for item in items if item.tier == tier]

        return items

    def get(  # type: ignore[override]
        self,
        key: int | None = None,
        *,
        tier: int | None = None,
        fields: builtins.list[str] | None = None,
    ) -> TenantStorage:
        """Get a storage allocation by key or tier number.

        Args:
            key: Storage allocation $key (ID).
            tier: Tier number (1-5) - alternative to key.
            fields: List of fields to return.

        Returns:
            TenantStorage object.

        Raises:
            NotFoundError: If allocation not found.
            ValueError: If neither key nor tier provided.
        """
        if fields is None:
            fields = self._default_fields

        if key is not None:
            params: dict[str, Any] = {"fields": ",".join(fields)}
            response = self._client._request("GET", f"{self._endpoint}/{key}", params=params)
            if response is None:
                from pyvergeos.exceptions import NotFoundError

                raise NotFoundError(f"Tenant storage allocation {key} not found")
            if not isinstance(response, dict):
                from pyvergeos.exceptions import NotFoundError

                raise NotFoundError(f"Tenant storage allocation {key} returned invalid response")
            return self._to_model(response)

        if tier is not None:
            allocations = self.list(tier=tier, fields=fields)
            if not allocations:
                from pyvergeos.exceptions import NotFoundError

                raise NotFoundError(
                    f"No Tier {tier} storage allocation found for tenant '{self._tenant.name}'"
                )
            return allocations[0]

        raise ValueError("Either key or tier must be provided")

    def create(  # type: ignore[override]
        self,
        tier: int,
        provisioned_gb: int | None = None,
        provisioned_bytes: int | None = None,
    ) -> TenantStorage:
        """Create a new storage allocation for this tenant.

        Args:
            tier: Storage tier number (1-5). Tier 0 is reserved for system metadata.
            provisioned_gb: Provisioned storage in GB (use this or provisioned_bytes).
            provisioned_bytes: Provisioned storage in bytes (precise control).

        Returns:
            Created TenantStorage object.

        Raises:
            ValueError: If tenant is a snapshot, tier is invalid, or no size specified.
            ConflictError: If an allocation for this tier already exists.
        """
        if self._tenant.is_snapshot:
            raise ValueError("Cannot add storage to a tenant snapshot")

        if tier < 1 or tier > 5:
            raise ValueError(
                f"Invalid tier {tier}. Valid tiers are 1-5. "
                "Tier 0 is reserved for system metadata."
            )

        if provisioned_gb is None and provisioned_bytes is None:
            raise ValueError("Either provisioned_gb or provisioned_bytes must be provided")

        # Calculate provisioned bytes
        if provisioned_bytes is not None:
            prov_bytes = provisioned_bytes
        else:
            # provisioned_gb is guaranteed to be not None here due to earlier check
            assert provisioned_gb is not None
            prov_bytes = provisioned_gb * 1073741824

        if prov_bytes < 1073741824:  # Minimum 1 GB
            raise ValueError("Provisioned storage must be at least 1 GB")

        # Get storage tier key by tier number
        tier_response = self._client._request(
            "GET",
            "storage_tiers",
            params={"filter": f"tier eq {tier}", "fields": "$key,tier"},
        )
        if not tier_response:
            from pyvergeos.exceptions import NotFoundError

            raise NotFoundError(f"Storage tier {tier} not found")

        tier_data = tier_response[0] if isinstance(tier_response, list) else tier_response
        tier_key = tier_data["$key"]

        body: dict[str, Any] = {
            "tenant": self._tenant.key,
            "tier": tier_key,
            "provisioned": prov_bytes,
        }

        logger.debug(
            f"Creating Tier {tier} storage allocation ({prov_bytes} bytes) "
            f"for tenant '{self._tenant.name}'"
        )
        self._client._request("POST", self._endpoint, json_data=body)

        # Fetch the created allocation
        import time

        time.sleep(0.5)  # Brief wait for API consistency
        return self.get(tier=tier)

    def update(self, key: int, **kwargs: Any) -> TenantStorage:
        """Update a storage allocation.

        Args:
            key: Storage allocation $key (ID).
            **kwargs: Fields to update. Supported fields:
                - provisioned: Provisioned size in bytes

        Returns:
            Updated TenantStorage object.
        """
        logger.debug(f"Updating tenant storage allocation {key}")
        self._client._request("PUT", f"{self._endpoint}/{key}", json_data=kwargs)
        return self.get(key)

    def update_by_tier(
        self,
        tier: int,
        provisioned_gb: int | None = None,
        provisioned_bytes: int | None = None,
    ) -> TenantStorage:
        """Update a storage allocation by tier number.

        Args:
            tier: Tier number (1-5).
            provisioned_gb: New provisioned size in GB.
            provisioned_bytes: New provisioned size in bytes.

        Returns:
            Updated TenantStorage object.

        Raises:
            NotFoundError: If no allocation exists for this tier.
            ValueError: If no size specified.
        """
        if provisioned_gb is None and provisioned_bytes is None:
            raise ValueError("Either provisioned_gb or provisioned_bytes must be provided")

        allocation = self.get(tier=tier)

        if provisioned_bytes is not None:
            prov_bytes = provisioned_bytes
        else:
            # provisioned_gb is guaranteed to be not None here due to earlier check
            assert provisioned_gb is not None
            prov_bytes = provisioned_gb * 1073741824

        return self.update(allocation.key, provisioned=prov_bytes)

    def delete(self, key: int) -> None:
        """Delete a storage allocation.

        Args:
            key: Storage allocation $key (ID).

        Warning:
            Removing a storage allocation with data may cause data loss.
            Ensure the allocation is empty before removal.
        """
        logger.debug(f"Deleting tenant storage allocation {key}")
        self._client._request("DELETE", f"{self._endpoint}/{key}")

    def delete_by_tier(self, tier: int) -> None:
        """Delete a storage allocation by tier number.

        Args:
            tier: Tier number (1-5).

        Raises:
            NotFoundError: If no allocation exists for this tier.

        Warning:
            Removing a storage allocation with data may cause data loss.
            Ensure the allocation is empty before removal.
        """
        allocation = self.get(tier=tier)
        self.delete(allocation.key)


class TenantNetworkBlock(ResourceObject):
    """Tenant Network Block resource object.

    Represents a CIDR network block assigned to a tenant from a parent network.
    These blocks allow tenants to have entire subnets routed to them.
    """

    @property
    def tenant_key(self) -> int:
        """Get the tenant key this block is assigned to.

        Parses the owner field which is in format 'tenants/{key}'.
        """
        owner = self.get("owner", "")
        if owner and owner.startswith("tenants/"):
            return int(owner.split("/")[1])
        return 0

    @property
    def network_key(self) -> int:
        """Get the network key this block belongs to."""
        return int(self.get("vnet", 0))

    @property
    def network_name(self) -> str | None:
        """Get the network name."""
        return self.get("network_name")

    @property
    def cidr(self) -> str:
        """Get the CIDR notation (e.g., '192.168.100.0/24')."""
        return str(self.get("cidr", ""))

    @property
    def network_address(self) -> str:
        """Get the network address portion of the CIDR."""
        cidr = self.cidr
        if "/" in cidr:
            return cidr.split("/")[0]
        return cidr

    @property
    def prefix_length(self) -> int:
        """Get the prefix length (subnet mask bits)."""
        cidr = self.cidr
        if "/" in cidr:
            return int(cidr.split("/")[1])
        return 0

    @property
    def address_count(self) -> int:
        """Get the number of addresses in this block."""
        prefix = self.prefix_length
        if prefix > 0:
            return int(2 ** (32 - prefix))
        return 0

    def delete(self) -> None:
        """Delete this network block assignment."""
        from typing import cast

        manager = cast("TenantNetworkBlockManager", self._manager)
        manager.delete(self.key)

    def __repr__(self) -> str:
        return f"<TenantNetworkBlock {self.cidr} on {self.network_name}>"


class TenantNetworkBlockManager(ResourceManager[TenantNetworkBlock]):
    """Manager for Tenant Network Block operations.

    This manager handles CIDR network blocks assigned to tenants. Network blocks
    allow routing entire subnets from a parent network to a tenant.

    This manager is accessed through a Tenant object's network_blocks property
    or via client.tenants.network_blocks(tenant_key).

    Example:
        >>> tenant = client.tenants.get(name="my-tenant")
        >>> # List network blocks
        >>> for block in tenant.network_blocks.list():
        ...     print(f"{block.cidr} on {block.network_name}")
        >>> # Assign a network block
        >>> tenant.network_blocks.create(network=1, cidr="192.168.100.0/24")
    """

    _endpoint = "vnet_cidrs"
    _default_fields = TENANT_NETWORK_BLOCK_DEFAULT_FIELDS

    def __init__(self, client: VergeClient, tenant: Tenant) -> None:
        super().__init__(client)
        self._tenant = tenant

    def _to_model(self, data: dict[str, Any]) -> TenantNetworkBlock:
        return TenantNetworkBlock(data, self)

    def list(  # type: ignore[override]
        self,
        filter: str | None = None,  # noqa: A002
        fields: builtins.list[str] | None = None,
        cidr: str | None = None,
        **kwargs: Any,
    ) -> builtins.list[TenantNetworkBlock]:
        """List network blocks assigned to this tenant.

        Args:
            filter: Additional OData filter string.
            fields: List of fields to return.
            cidr: Filter by specific CIDR block.
            **kwargs: Additional filter arguments.

        Returns:
            List of TenantNetworkBlock objects.
        """
        if fields is None:
            fields = self._default_fields

        # Build filter for this tenant's blocks
        owner_filter = f"owner eq 'tenants/{self._tenant.key}'"
        if cidr:
            owner_filter = f"{owner_filter} and cidr eq '{cidr}'"
        if filter:
            owner_filter = f"{owner_filter} and ({filter})"

        params: dict[str, Any] = {
            "filter": owner_filter,
            "fields": ",".join(fields),
        }

        response = self._client._request("GET", self._endpoint, params=params)

        if response is None:
            return []

        if not isinstance(response, list):
            return [self._to_model(response)]

        return [self._to_model(item) for item in response]

    def get(  # type: ignore[override]
        self,
        key: int | None = None,
        *,
        cidr: str | None = None,
        fields: builtins.list[str] | None = None,
    ) -> TenantNetworkBlock:
        """Get a network block by key or CIDR.

        Args:
            key: Network block $key (ID).
            cidr: CIDR notation to find.
            fields: List of fields to return.

        Returns:
            TenantNetworkBlock object.

        Raises:
            NotFoundError: If network block not found.
            ValueError: If neither key nor cidr provided.
        """
        if fields is None:
            fields = self._default_fields

        if key is not None:
            params: dict[str, Any] = {"fields": ",".join(fields)}
            response = self._client._request("GET", f"{self._endpoint}/{key}", params=params)
            if response is None:
                from pyvergeos.exceptions import NotFoundError

                raise NotFoundError(f"Tenant network block {key} not found")
            if not isinstance(response, dict):
                from pyvergeos.exceptions import NotFoundError

                raise NotFoundError(f"Tenant network block {key} returned invalid response")
            return self._to_model(response)

        if cidr is not None:
            blocks = self.list(cidr=cidr, fields=fields)
            if not blocks:
                from pyvergeos.exceptions import NotFoundError

                raise NotFoundError(
                    f"Network block '{cidr}' not found for tenant '{self._tenant.name}'"
                )
            return blocks[0]

        raise ValueError("Either key or cidr must be provided")

    def create(  # type: ignore[override]
        self,
        cidr: str,
        network: int | None = None,
        network_name: str | None = None,
        description: str = "",
    ) -> TenantNetworkBlock:
        """Assign a network block to this tenant.

        Args:
            cidr: Network block in CIDR notation (e.g., "192.168.100.0/24").
            network: Network $key (ID) to assign block from.
            network_name: Network name (alternative to network key).
            description: Optional description for the block.

        Returns:
            Created TenantNetworkBlock object.

        Raises:
            ValueError: If tenant is a snapshot or neither network nor network_name provided.
            NotFoundError: If network not found.
            ConflictError: If CIDR already exists or overlaps.
        """
        if self._tenant.is_snapshot:
            raise ValueError("Cannot assign network block to a tenant snapshot")

        # Resolve network key
        if network is None and network_name is None:
            raise ValueError("Either network or network_name must be provided")

        net_key: int
        if network is not None:
            net_key = network
        else:
            # Look up network by name
            response = self._client._request(
                "GET",
                "vnets",
                params={"filter": f"name eq '{network_name}'", "fields": "$key,name"},
            )
            if not response:
                from pyvergeos.exceptions import NotFoundError

                raise NotFoundError(f"Network '{network_name}' not found")
            net_data = response[0] if isinstance(response, list) else response
            net_key = int(net_data["$key"])

        body: dict[str, Any] = {
            "vnet": net_key,
            "cidr": cidr,
            "owner": f"tenants/{self._tenant.key}",
        }

        if description:
            body["description"] = description

        logger.debug(
            f"Assigning network block '{cidr}' to tenant '{self._tenant.name}'"
        )
        self._client._request("POST", self._endpoint, json_data=body)

        # Fetch the created block
        import time

        time.sleep(0.5)  # Brief wait for API consistency
        return self.get(cidr=cidr)

    def delete(self, key: int) -> None:
        """Remove a network block assignment.

        Args:
            key: Network block $key (ID).

        Warning:
            Removing a network block may disrupt connectivity for services
            using addresses in that range. Firewall rules referencing the
            block must be removed first.
        """
        logger.debug(f"Removing tenant network block {key}")
        self._client._request("DELETE", f"{self._endpoint}/{key}")

    def delete_by_cidr(self, cidr: str) -> None:
        """Remove a network block by CIDR.

        Args:
            cidr: CIDR notation of the block to remove.

        Raises:
            NotFoundError: If no block with this CIDR exists.
        """
        block = self.get(cidr=cidr)
        self.delete(block.key)


class TenantExternalIP(ResourceObject):
    """Tenant External IP resource object.

    Represents a virtual IP address assigned to a tenant from a parent network.
    These external IPs can be used for NAT rules, services, or other networking
    purposes within the tenant's environment.
    """

    @property
    def tenant_key(self) -> int:
        """Get the tenant key this IP is assigned to.

        Parses the owner field which is in format 'tenants/{key}'.
        """
        owner = self.get("owner", "")
        if owner and owner.startswith("tenants/"):
            try:
                return int(owner.split("/")[1])
            except (IndexError, ValueError):
                return 0
        return 0

    @property
    def network_key(self) -> int:
        """Get the network key this IP belongs to."""
        return int(self.get("vnet", 0))

    @property
    def network_name(self) -> str | None:
        """Get the network name."""
        return self.get("network_name")

    @property
    def ip_address(self) -> str:
        """Get the IP address."""
        return str(self.get("ip", ""))

    @property
    def hostname(self) -> str | None:
        """Get the hostname associated with this IP."""
        return self.get("hostname")

    @property
    def mac_address(self) -> str | None:
        """Get the MAC address (if any)."""
        return self.get("mac")

    @property
    def ip_type(self) -> str:
        """Get the IP type (should be 'virtual' for external IPs)."""
        return str(self.get("type", ""))

    def delete(self) -> None:
        """Delete this external IP assignment."""
        from typing import cast

        manager = cast("TenantExternalIPManager", self._manager)
        manager.delete(self.key)

    def __repr__(self) -> str:
        hostname = self.hostname
        if hostname:
            return f"<TenantExternalIP {self.ip_address} ({hostname}) on {self.network_name}>"
        return f"<TenantExternalIP {self.ip_address} on {self.network_name}>"


class TenantExternalIPManager(ResourceManager[TenantExternalIP]):
    """Manager for Tenant External IP operations.

    This manager handles virtual IP addresses assigned to tenants. External IPs
    allow tenants to have public or routable addresses from a parent network
    that can be used for NAT rules, services, or external connectivity.

    This manager is accessed through a Tenant object's external_ips property
    or via client.tenants.external_ips(tenant_key).

    Example:
        >>> tenant = client.tenants.get(name="my-tenant")
        >>> # List external IPs
        >>> for ip in tenant.external_ips.list():
        ...     print(f"{ip.ip_address} on {ip.network_name}")
        >>> # Assign an external IP
        >>> tenant.external_ips.create(network=1, ip="192.168.1.100")
    """

    _endpoint = "vnet_addresses"
    _default_fields = TENANT_EXTERNAL_IP_DEFAULT_FIELDS

    def __init__(self, client: VergeClient, tenant: Tenant) -> None:
        super().__init__(client)
        self._tenant = tenant

    def _to_model(self, data: dict[str, Any]) -> TenantExternalIP:
        return TenantExternalIP(data, self)

    def list(  # type: ignore[override]
        self,
        filter: str | None = None,  # noqa: A002
        fields: builtins.list[str] | None = None,
        ip: str | None = None,
        **kwargs: Any,
    ) -> builtins.list[TenantExternalIP]:
        """List external IPs assigned to this tenant.

        Args:
            filter: Additional OData filter string.
            fields: List of fields to return.
            ip: Filter by specific IP address.
            **kwargs: Additional filter arguments.

        Returns:
            List of TenantExternalIP objects.
        """
        if fields is None:
            fields = self._default_fields

        # Build filter for this tenant's virtual IPs
        owner_filter = f"owner eq 'tenants/{self._tenant.key}' and type eq 'virtual'"
        if ip:
            owner_filter = f"{owner_filter} and ip eq '{ip}'"
        if filter:
            owner_filter = f"{owner_filter} and ({filter})"

        params: dict[str, Any] = {
            "filter": owner_filter,
            "fields": ",".join(fields),
        }

        response = self._client._request("GET", self._endpoint, params=params)

        if response is None:
            return []

        if not isinstance(response, list):
            return [self._to_model(response)]

        return [self._to_model(item) for item in response]

    def get(  # type: ignore[override]
        self,
        key: int | None = None,
        *,
        ip: str | None = None,
        fields: builtins.list[str] | None = None,
    ) -> TenantExternalIP:
        """Get an external IP by key or IP address.

        Args:
            key: IP address $key (ID).
            ip: IP address to find.
            fields: List of fields to return.

        Returns:
            TenantExternalIP object.

        Raises:
            NotFoundError: If external IP not found.
            ValueError: If neither key nor ip provided.
        """
        if fields is None:
            fields = self._default_fields

        if key is not None:
            params: dict[str, Any] = {"fields": ",".join(fields)}
            response = self._client._request("GET", f"{self._endpoint}/{key}", params=params)
            if response is None:
                from pyvergeos.exceptions import NotFoundError

                raise NotFoundError(f"Tenant external IP {key} not found")
            if not isinstance(response, dict):
                from pyvergeos.exceptions import NotFoundError

                raise NotFoundError(f"Tenant external IP {key} returned invalid response")
            return self._to_model(response)

        if ip is not None:
            ips = self.list(ip=ip, fields=fields)
            if not ips:
                from pyvergeos.exceptions import NotFoundError

                raise NotFoundError(
                    f"External IP '{ip}' not found for tenant '{self._tenant.name}'"
                )
            return ips[0]

        raise ValueError("Either key or ip must be provided")

    def create(  # type: ignore[override]
        self,
        ip: str,
        network: int | None = None,
        network_name: str | None = None,
        hostname: str | None = None,
        description: str = "",
    ) -> TenantExternalIP:
        """Assign an external IP to this tenant.

        Args:
            ip: IP address to assign (e.g., "192.168.1.100").
            network: Network $key (ID) to assign IP from.
            network_name: Network name (alternative to network key).
            hostname: Optional hostname for DNS.
            description: Optional description for the IP.

        Returns:
            Created TenantExternalIP object.

        Raises:
            ValueError: If tenant is a snapshot or neither network nor network_name provided.
            NotFoundError: If network not found.
            ConflictError: If IP already exists.
        """
        if self._tenant.is_snapshot:
            raise ValueError("Cannot assign external IP to a tenant snapshot")

        # Resolve network key
        if network is None and network_name is None:
            raise ValueError("Either network or network_name must be provided")

        net_key: int
        if network is not None:
            net_key = network
        else:
            # Look up network by name
            response = self._client._request(
                "GET",
                "vnets",
                params={"filter": f"name eq '{network_name}'", "fields": "$key,name"},
            )
            if not response:
                from pyvergeos.exceptions import NotFoundError

                raise NotFoundError(f"Network '{network_name}' not found")
            net_data = response[0] if isinstance(response, list) else response
            net_key = int(net_data["$key"])

        body: dict[str, Any] = {
            "vnet": net_key,
            "ip": ip,
            "type": "virtual",
            "owner": f"tenants/{self._tenant.key}",
        }

        if hostname:
            body["hostname"] = hostname
        if description:
            body["description"] = description

        logger.debug(
            f"Assigning external IP '{ip}' to tenant '{self._tenant.name}'"
        )
        self._client._request("POST", self._endpoint, json_data=body)

        # Fetch the created IP
        import time

        time.sleep(0.5)  # Brief wait for API consistency
        return self.get(ip=ip)

    def delete(self, key: int) -> None:
        """Remove an external IP assignment.

        Args:
            key: IP address $key (ID).

        Warning:
            Removing an external IP may disrupt connectivity for services
            using that address. Firewall rules referencing the IP must be
            removed first.
        """
        logger.debug(f"Removing tenant external IP {key}")
        self._client._request("DELETE", f"{self._endpoint}/{key}")

    def delete_by_ip(self, ip: str) -> None:
        """Remove an external IP by IP address.

        Args:
            ip: IP address to remove.

        Raises:
            NotFoundError: If no IP with this address exists.
        """
        external_ip = self.get(ip=ip)
        self.delete(external_ip.key)


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
