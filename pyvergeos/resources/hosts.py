"""Network DHCP/DNS host override resource manager."""

from __future__ import annotations

import builtins
from typing import TYPE_CHECKING, Any, Literal

from pyvergeos.exceptions import NotFoundError
from pyvergeos.resources.base import ResourceManager, ResourceObject

if TYPE_CHECKING:
    from pyvergeos.client import VergeClient
    from pyvergeos.resources.networks import Network

# Default fields for host data
HOST_DEFAULT_FIELDS = [
    "$key",
    "vnet",
    "vnet#name as vnet_name",
    "type",
    "host",
    "ip",
]

# Type alias for host types
HostType = Literal["host", "domain"]


class NetworkHost(ResourceObject):
    """Network DHCP/DNS host override resource object.

    Host overrides map hostnames to IP addresses for DHCP and DNS resolution.
    """

    @property
    def network_key(self) -> int:
        """Get the network key this host belongs to."""
        vnet = self.get("vnet")
        if vnet is None:
            raise ValueError("Host has no network (vnet) key")
        return int(vnet)

    @property
    def network_name(self) -> str | None:
        """Get the network name this host belongs to."""
        return self.get("vnet_name")

    @property
    def hostname(self) -> str:
        """Get the hostname of this override."""
        host = self.get("host")
        if host is None:
            raise ValueError("Host has no hostname")
        return str(host)

    @property
    def ip(self) -> str:
        """Get the IP address of this host override."""
        ip = self.get("ip")
        if ip is None:
            raise ValueError("Host has no IP address")
        return str(ip)

    @property
    def host_type(self) -> str:
        """Get the type of this host override ('host' or 'domain')."""
        return self.get("type") or "host"

    @property
    def is_domain(self) -> bool:
        """Check if this is a domain override."""
        return self.host_type == "domain"

    @property
    def is_host(self) -> bool:
        """Check if this is a host override."""
        return self.host_type == "host"


class NetworkHostManager(ResourceManager[NetworkHost]):
    """Manager for Network DHCP/DNS host override operations.

    This manager is accessed through a Network object's hosts property.
    Host overrides provide static DNS entries and DHCP hostname assignment.

    Examples:
        List all hosts for a network::

            hosts = network.hosts.list()

        Get a host by hostname::

            host = network.hosts.get(hostname="server01")

        Create a new host override::

            host = network.hosts.create(
                hostname="server01",
                ip="10.0.0.50",
                host_type="host"
            )

        Update a host override::

            network.hosts.update(host.key, ip="10.0.0.51")

        Delete a host override::

            network.hosts.delete(host.key)
    """

    _endpoint = "vnet_hosts"
    _default_fields = HOST_DEFAULT_FIELDS

    def __init__(self, client: VergeClient, network: Network) -> None:
        super().__init__(client)
        self._network = network

    @property
    def network_key(self) -> int:
        """Get the network key for this manager."""
        return self._network.key

    def _to_model(self, data: dict[str, Any]) -> NetworkHost:
        return NetworkHost(data, self)

    def list(  # type: ignore[override]
        self,
        filter: str | None = None,
        fields: builtins.list[str] | None = None,
        hostname: str | None = None,
        ip: str | None = None,
        host_type: HostType | None = None,
        **kwargs: Any,
    ) -> builtins.list[NetworkHost]:
        """List DHCP/DNS host overrides for this network.

        Args:
            filter: Additional OData filter string.
            fields: List of fields to return.
            hostname: Filter by exact hostname.
            ip: Filter by exact IP address.
            host_type: Filter by type ('host' or 'domain').
            **kwargs: Additional filter arguments.

        Returns:
            List of NetworkHost objects sorted by hostname.
        """
        if fields is None:
            fields = self._default_fields.copy()

        # Build filter for this network
        filters: builtins.list[str] = [
            f"vnet eq {self.network_key}",
        ]

        if hostname:
            escaped_hostname = hostname.replace("'", "''")
            filters.append(f"host eq '{escaped_hostname}'")

        if ip:
            escaped_ip = ip.replace("'", "''")
            filters.append(f"ip eq '{escaped_ip}'")

        if host_type:
            filters.append(f"type eq '{host_type}'")

        if filter:
            filters.append(f"({filter})")

        combined_filter = " and ".join(filters)

        params: dict[str, Any] = {
            "filter": combined_filter,
            "fields": ",".join(fields),
            "sort": "+host",
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
        hostname: str | None = None,
        ip: str | None = None,
        fields: builtins.list[str] | None = None,
    ) -> NetworkHost:
        """Get a host override by key, hostname, or IP address.

        Args:
            key: Host $key (ID).
            hostname: Hostname of the override.
            ip: IP address of the override.
            fields: List of fields to return.

        Returns:
            NetworkHost object.

        Raises:
            NotFoundError: If host not found.
            ValueError: If no identifier provided.
        """
        if fields is None:
            fields = self._default_fields.copy()

        if key is not None:
            params: dict[str, Any] = {"fields": ",".join(fields)}
            response = self._client._request("GET", f"{self._endpoint}/{key}", params=params)
            if response is None:
                raise NotFoundError(f"Host {key} not found")
            if not isinstance(response, dict):
                raise NotFoundError(f"Host {key} returned invalid response")
            return self._to_model(response)

        if hostname is not None:
            hosts = self.list(hostname=hostname, fields=fields)
            if not hosts:
                raise NotFoundError(f"Host with hostname '{hostname}' not found on this network")
            return hosts[0]

        if ip is not None:
            hosts = self.list(ip=ip, fields=fields)
            if not hosts:
                raise NotFoundError(f"Host with IP '{ip}' not found on this network")
            return hosts[0]

        raise ValueError("Either key, hostname, or ip must be provided")

    def create(  # type: ignore[override]
        self,
        hostname: str,
        ip: str,
        host_type: HostType = "host",
    ) -> NetworkHost:
        """Create a new DHCP/DNS host override.

        Args:
            hostname: Hostname or domain name for the override.
            ip: IP address to map to the hostname.
            host_type: Type of override - 'host' (default) or 'domain'.

        Returns:
            Created NetworkHost object.

        Raises:
            ValidationError: If a host with this hostname already exists.

        Note:
            Host override changes require DNS apply to take effect.
        """
        body: dict[str, Any] = {
            "vnet": self.network_key,
            "host": hostname,
            "ip": ip,
            "type": host_type,
        }

        response = self._client._request("POST", self._endpoint, json_data=body)
        if response is None:
            raise ValueError("No response from create operation")
        if not isinstance(response, dict):
            raise ValueError("Create operation returned invalid response")

        # Get the created host key and fetch full data
        key = response.get("$key")
        if key is None:
            raise ValueError("Create response missing $key")

        return self.get(int(key))

    def update(  # type: ignore[override]
        self,
        key: int,
        *,
        hostname: str | None = None,
        ip: str | None = None,
        host_type: HostType | None = None,
    ) -> NetworkHost:
        """Update an existing host override.

        Args:
            key: Host $key (ID).
            hostname: New hostname for the override.
            ip: New IP address for the override.
            host_type: New type ('host' or 'domain').

        Returns:
            Updated NetworkHost object.

        Raises:
            NotFoundError: If host not found.
            ValueError: If no update fields provided.

        Note:
            Host override changes require DNS apply to take effect.
        """
        body: dict[str, Any] = {}

        if hostname is not None:
            body["host"] = hostname
        if ip is not None:
            body["ip"] = ip
        if host_type is not None:
            body["type"] = host_type

        if not body:
            raise ValueError("At least one field must be provided to update")

        self._client._request("PUT", f"{self._endpoint}/{key}", json_data=body)

        return self.get(key)

    def delete(self, key: int) -> None:
        """Delete a host override.

        Args:
            key: Host $key (ID).

        Note:
            Host override changes require DNS apply to take effect.
        """
        self._client._request("DELETE", f"{self._endpoint}/{key}")
