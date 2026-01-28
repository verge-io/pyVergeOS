"""Tenant snapshot resource manager."""

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
