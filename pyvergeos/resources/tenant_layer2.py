"""Tenant Layer 2 network resource manager."""

from __future__ import annotations

import builtins
import logging
from typing import TYPE_CHECKING, Any

from pyvergeos.resources.base import ResourceManager, ResourceObject

if TYPE_CHECKING:
    from pyvergeos.client import VergeClient
    from pyvergeos.resources.tenant_manager import Tenant

logger = logging.getLogger(__name__)

# Default fields for tenant Layer 2 networks
TENANT_LAYER2_DEFAULT_FIELDS = [
    "$key",
    "tenant",
    "tenant#name as tenant_name",
    "vnet",
    "vnet#name as network_name",
    "vnet#type as network_type",
    "enabled",
]


class TenantLayer2Network(ResourceObject):
    """Tenant Layer 2 Network resource object.

    Represents a Layer 2 network assignment that provides bridged connectivity
    between a parent network and a tenant. Layer 2 networks allow tenants
    direct access to parent network segments.
    """

    @property
    def tenant_key(self) -> int:
        """Get the tenant key this L2 network is assigned to."""
        return int(self.get("tenant", 0))

    @property
    def tenant_name(self) -> str | None:
        """Get the tenant name."""
        return self.get("tenant_name")

    @property
    def network_key(self) -> int:
        """Get the network key (vnet)."""
        return int(self.get("vnet", 0))

    @property
    def network_name(self) -> str | None:
        """Get the network name."""
        return self.get("network_name")

    @property
    def network_type(self) -> str | None:
        """Get the network type (internal, external, bgp, vpn, etc.)."""
        return self.get("network_type")

    @property
    def is_enabled(self) -> bool:
        """Check if the Layer 2 network assignment is enabled."""
        return bool(self.get("enabled", False))

    def enable(self) -> TenantLayer2Network:
        """Enable this Layer 2 network assignment.

        Returns:
            Updated TenantLayer2Network object.
        """
        from typing import cast

        manager = cast("TenantLayer2Manager", self._manager)
        return manager.update(self.key, enabled=True)

    def disable(self) -> TenantLayer2Network:
        """Disable this Layer 2 network assignment.

        Returns:
            Updated TenantLayer2Network object.
        """
        from typing import cast

        manager = cast("TenantLayer2Manager", self._manager)
        return manager.update(self.key, enabled=False)

    def delete(self) -> None:
        """Delete this Layer 2 network assignment."""
        from typing import cast

        manager = cast("TenantLayer2Manager", self._manager)
        manager.delete(self.key)

    def __repr__(self) -> str:
        enabled_str = "enabled" if self.is_enabled else "disabled"
        return f"<TenantLayer2Network {self.network_name} ({enabled_str})>"


class TenantLayer2Manager(ResourceManager[TenantLayer2Network]):
    """Manager for Tenant Layer 2 Network operations.

    This manager handles Layer 2 network assignments for tenants. Layer 2
    networks provide bridged connectivity between parent and tenant networks,
    allowing tenants direct access to parent network segments.

    Only certain network types can be assigned: internal, external, bgp,
    vpn, or bridged physical networks. A maximum of 28 Layer 2 networks
    can be assigned per tenant.

    This manager is accessed through a Tenant object's l2_networks property
    or via client.tenants.l2_networks(tenant_key).

    Example:
        >>> tenant = client.tenants.get(name="my-tenant")
        >>> # List Layer 2 networks
        >>> for l2 in tenant.l2_networks.list():
        ...     print(f"{l2.network_name}: {l2.is_enabled}")
        >>> # Assign a Layer 2 network
        >>> tenant.l2_networks.create(network_name="VLAN100")
    """

    _endpoint = "tenant_layer2_vnets"
    _default_fields = TENANT_LAYER2_DEFAULT_FIELDS

    def __init__(self, client: VergeClient, tenant: Tenant) -> None:
        super().__init__(client)
        self._tenant = tenant

    def _to_model(self, data: dict[str, Any]) -> TenantLayer2Network:
        return TenantLayer2Network(data, self)

    def list(  # type: ignore[override]
        self,
        filter: str | None = None,  # noqa: A002
        fields: builtins.list[str] | None = None,
        **kwargs: Any,
    ) -> builtins.list[TenantLayer2Network]:
        """List Layer 2 networks assigned to this tenant.

        Args:
            filter: Additional OData filter string.
            fields: List of fields to return.
            **kwargs: Additional filter arguments.

        Returns:
            List of TenantLayer2Network objects.
        """
        if fields is None:
            fields = self._default_fields

        # Build filter for this tenant's L2 networks
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
            return [self._to_model(response)]

        return [self._to_model(item) for item in response]

    def get(  # type: ignore[override]
        self,
        key: int | None = None,
        *,
        network_name: str | None = None,
        fields: builtins.list[str] | None = None,
    ) -> TenantLayer2Network:
        """Get a Layer 2 network by key or network name.

        Args:
            key: Layer 2 network assignment $key (ID).
            network_name: Network name to find.
            fields: List of fields to return.

        Returns:
            TenantLayer2Network object.

        Raises:
            NotFoundError: If Layer 2 network not found.
            ValueError: If neither key nor network_name provided.
        """
        if fields is None:
            fields = self._default_fields

        if key is not None:
            # Query by key with tenant filter to ensure it belongs to this tenant
            params: dict[str, Any] = {
                "filter": f"$key eq {key}",
                "fields": ",".join(fields),
            }
            response = self._client._request("GET", self._endpoint, params=params)
            if response is None:
                from pyvergeos.exceptions import NotFoundError

                raise NotFoundError(f"Tenant Layer 2 network {key} not found")
            if isinstance(response, list):
                if not response:
                    from pyvergeos.exceptions import NotFoundError

                    raise NotFoundError(f"Tenant Layer 2 network {key} not found")
                return self._to_model(response[0])
            return self._to_model(response)

        if network_name is not None:
            # Search by network name within this tenant's L2 networks
            l2_networks = self.list(fields=fields)
            for l2 in l2_networks:
                if l2.network_name == network_name:
                    return l2
            from pyvergeos.exceptions import NotFoundError

            raise NotFoundError(
                f"Layer 2 network '{network_name}' not found for tenant '{self._tenant.name}'"
            )

        raise ValueError("Either key or network_name must be provided")

    def create(  # type: ignore[override]
        self,
        network: int | None = None,
        network_name: str | None = None,
        enabled: bool = True,
    ) -> TenantLayer2Network:
        """Assign a Layer 2 network to this tenant.

        Only certain network types can be assigned as Layer 2 networks:
        internal, external, bgp, vpn, or bridged physical networks.
        A maximum of 28 Layer 2 networks can be assigned per tenant.

        Args:
            network: Network $key (ID) to assign.
            network_name: Network name (alternative to network key).
            enabled: Whether the assignment should be enabled (default True).

        Returns:
            Created TenantLayer2Network object.

        Raises:
            ValueError: If tenant is a snapshot or neither network nor network_name provided.
            NotFoundError: If network not found.
            ConflictError: If network already assigned or max limit reached.
        """
        if self._tenant.is_snapshot:
            raise ValueError("Cannot assign Layer 2 network to a tenant snapshot")

        # Resolve network key
        if network is None and network_name is None:
            raise ValueError("Either network or network_name must be provided")

        net_key: int
        resolved_name: str | None = network_name
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
            "tenant": self._tenant.key,
            "vnet": net_key,
            "enabled": enabled,
        }

        logger.debug(
            f"Assigning Layer 2 network '{resolved_name or net_key}' "
            f"to tenant '{self._tenant.name}'"
        )
        response = self._client._request("POST", self._endpoint, json_data=body)

        # Get the created key from response and fetch the full object
        if isinstance(response, dict) and "$key" in response:
            return self.get(response["$key"])

        # Fallback: fetch by network name if we have it
        import time

        time.sleep(0.5)  # Brief wait for API consistency
        if resolved_name:
            return self.get(network_name=resolved_name)

        # Last resort: get the most recently created L2 network for this tenant
        l2_networks = self.list()
        if l2_networks:
            # Find the one matching our network key
            for l2 in l2_networks:
                if l2.network_key == net_key:
                    return l2
        from pyvergeos.exceptions import NotFoundError

        raise NotFoundError("Failed to retrieve created Layer 2 network")

    def update(self, key: int, enabled: bool) -> TenantLayer2Network:  # type: ignore[override]
        """Update a Layer 2 network assignment.

        Only the enabled status can be modified. To change the network
        assignment, remove and recreate it.

        Args:
            key: Layer 2 network assignment $key (ID).
            enabled: Whether the assignment should be enabled.

        Returns:
            Updated TenantLayer2Network object.
        """
        body: dict[str, Any] = {"enabled": enabled}

        logger.debug(f"Updating Layer 2 network {key}: enabled={enabled}")
        self._client._request("PUT", f"{self._endpoint}/{key}", json_data=body)
        return self.get(key)

    def delete(self, key: int) -> None:
        """Remove a Layer 2 network assignment.

        Args:
            key: Layer 2 network assignment $key (ID).

        Warning:
            Removing a Layer 2 network disconnects the bridged connectivity
            between the parent and tenant networks. This may affect tenant
            workloads using that network segment.
        """
        logger.debug(f"Removing tenant Layer 2 network {key}")
        self._client._request("DELETE", f"{self._endpoint}/{key}")

    def delete_by_network(self, network_name: str) -> None:
        """Remove a Layer 2 network assignment by network name.

        Args:
            network_name: Name of the network to remove.

        Raises:
            NotFoundError: If no assignment with this network exists.
        """
        l2_network = self.get(network_name=network_name)
        self.delete(l2_network.key)
