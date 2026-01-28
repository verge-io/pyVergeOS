"""Tenant network block resource manager."""

from __future__ import annotations

import builtins
import logging
from typing import TYPE_CHECKING, Any

from pyvergeos.resources.base import ResourceManager, ResourceObject

if TYPE_CHECKING:
    from pyvergeos.client import VergeClient
    from pyvergeos.resources.tenant_manager import Tenant

logger = logging.getLogger(__name__)

# Default fields for tenant network blocks
TENANT_NETWORK_BLOCK_DEFAULT_FIELDS = [
    "$key",
    "vnet",
    "vnet#name as network_name",
    "cidr",
    "description",
    "owner",
]


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

    @property
    def description(self) -> str | None:
        """Get the block description."""
        return self.get("description")

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

        logger.debug(f"Assigning network block '{cidr}' to tenant '{self._tenant.name}'")
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
