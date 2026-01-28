"""Tenant external IP resource manager."""

from __future__ import annotations

import builtins
import logging
from typing import TYPE_CHECKING, Any

from pyvergeos.resources.base import ResourceManager, ResourceObject

if TYPE_CHECKING:
    from pyvergeos.client import VergeClient
    from pyvergeos.resources.tenant_manager import Tenant

logger = logging.getLogger(__name__)

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

        logger.debug(f"Assigning external IP '{ip}' to tenant '{self._tenant.name}'")
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
