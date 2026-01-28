"""Tenant storage allocation resource manager."""

from __future__ import annotations

import builtins
import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from pyvergeos.resources.base import ResourceManager, ResourceObject

if TYPE_CHECKING:
    from pyvergeos.client import VergeClient
    from pyvergeos.resources.tenant_manager import Tenant

logger = logging.getLogger(__name__)

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
