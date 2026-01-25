"""Network IP alias resource manager."""

from __future__ import annotations

import builtins
from typing import TYPE_CHECKING, Any

from pyvergeos.exceptions import NotFoundError
from pyvergeos.resources.base import ResourceManager, ResourceObject

if TYPE_CHECKING:
    from pyvergeos.client import VergeClient
    from pyvergeos.resources.networks import Network

# Default fields for alias data
ALIAS_DEFAULT_FIELDS = [
    "$key",
    "vnet",
    "vnet#name as vnet_name",
    "ip",
    "hostname",
    "description",
    "mac",
    "type",
]


class NetworkAlias(ResourceObject):
    """Network IP alias resource object.

    IP aliases can be referenced in firewall rules using alias:name syntax.
    """

    @property
    def network_key(self) -> int:
        """Get the network key this alias belongs to."""
        vnet = self.get("vnet")
        if vnet is None:
            raise ValueError("Alias has no network (vnet) key")
        return int(vnet)

    @property
    def network_name(self) -> str | None:
        """Get the network name this alias belongs to."""
        return self.get("vnet_name")

    @property
    def ip(self) -> str:
        """Get the IP address of this alias."""
        ip = self.get("ip")
        if ip is None:
            raise ValueError("Alias has no IP address")
        return str(ip)

    @property
    def hostname(self) -> str | None:
        """Get the hostname/name of this alias."""
        return self.get("hostname")

    # Alias for consistency with PowerShell module
    @property
    def alias_name(self) -> str | None:
        """Get the name of this alias (same as hostname)."""
        return self.hostname

    @property
    def description(self) -> str | None:
        """Get the description of this alias."""
        return self.get("description")

    @property
    def mac(self) -> str | None:
        """Get the MAC address associated with this alias."""
        return self.get("mac")


class NetworkAliasManager(ResourceManager[NetworkAlias]):
    """Manager for Network IP alias operations.

    This manager is accessed through a Network object's aliases property.
    IP aliases are used in firewall rules to reference groups of IP addresses.

    Examples:
        List all aliases for a network::

            aliases = network.aliases.list()

        Get an alias by IP::

            alias = network.aliases.get(ip="10.0.0.100")

        Create a new IP alias::

            alias = network.aliases.create(
                ip="10.0.0.100",
                name="webserver",
                description="Main web server"
            )

        Delete an alias::

            network.aliases.delete(alias.key)
    """

    _endpoint = "vnet_addresses"
    _default_fields = ALIAS_DEFAULT_FIELDS

    def __init__(self, client: VergeClient, network: Network) -> None:
        super().__init__(client)
        self._network = network

    @property
    def network_key(self) -> int:
        """Get the network key for this manager."""
        return self._network.key

    def _to_model(self, data: dict[str, Any]) -> NetworkAlias:
        return NetworkAlias(data, self)

    def list(  # type: ignore[override]
        self,
        filter: str | None = None,
        fields: builtins.list[str] | None = None,
        ip: str | None = None,
        hostname: str | None = None,
        **kwargs: Any,
    ) -> builtins.list[NetworkAlias]:
        """List IP aliases for this network.

        Args:
            filter: Additional OData filter string.
            fields: List of fields to return.
            ip: Filter by exact IP address.
            hostname: Filter by exact hostname/name.
            **kwargs: Additional filter arguments.

        Returns:
            List of NetworkAlias objects sorted by IP.
        """
        if fields is None:
            fields = self._default_fields.copy()

        # Build filter for this network and type='ipalias'
        filters: builtins.list[str] = [
            f"vnet eq {self.network_key}",
            "type eq 'ipalias'",
        ]

        if ip:
            escaped_ip = ip.replace("'", "''")
            filters.append(f"ip eq '{escaped_ip}'")

        if hostname:
            escaped_hostname = hostname.replace("'", "''")
            filters.append(f"hostname eq '{escaped_hostname}'")

        if filter:
            filters.append(f"({filter})")

        combined_filter = " and ".join(filters)

        params: dict[str, Any] = {
            "filter": combined_filter,
            "fields": ",".join(fields),
            "sort": "+ip",
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
        ip: str | None = None,
        hostname: str | None = None,
        name: str | None = None,
        fields: builtins.list[str] | None = None,
    ) -> NetworkAlias:
        """Get an alias by key, IP address, or hostname.

        Args:
            key: Alias $key (ID).
            ip: IP address.
            hostname: Hostname/name of the alias.
            name: Alias for hostname (for convenience).
            fields: List of fields to return.

        Returns:
            NetworkAlias object.

        Raises:
            NotFoundError: If alias not found.
            ValueError: If no identifier provided.
        """
        if fields is None:
            fields = self._default_fields.copy()

        # Allow 'name' as alias for 'hostname'
        if name is not None and hostname is None:
            hostname = name

        if key is not None:
            params: dict[str, Any] = {"fields": ",".join(fields)}
            response = self._client._request("GET", f"{self._endpoint}/{key}", params=params)
            if response is None:
                raise NotFoundError(f"Alias {key} not found")
            if not isinstance(response, dict):
                raise NotFoundError(f"Alias {key} returned invalid response")
            return self._to_model(response)

        if ip is not None:
            aliases = self.list(ip=ip, fields=fields)
            if not aliases:
                raise NotFoundError(f"Alias with IP '{ip}' not found on this network")
            return aliases[0]

        if hostname is not None:
            aliases = self.list(hostname=hostname, fields=fields)
            if not aliases:
                raise NotFoundError(f"Alias with hostname '{hostname}' not found on this network")
            return aliases[0]

        raise ValueError("Either key, ip, or hostname must be provided")

    def create(  # type: ignore[override]
        self,
        ip: str,
        name: str,
        description: str = "",
    ) -> NetworkAlias:
        """Create a new IP alias.

        Args:
            ip: IP address for the alias. Can be a single IP or CIDR notation.
            name: Name/hostname for the alias (used in firewall rules as alias:name).
            description: Optional description.

        Returns:
            Created NetworkAlias object.

        Raises:
            ValidationError: If an alias with this IP already exists.
        """
        body: dict[str, Any] = {
            "vnet": self.network_key,
            "ip": ip,
            "hostname": name,
            "type": "ipalias",
        }

        if description:
            body["description"] = description

        response = self._client._request("POST", self._endpoint, json_data=body)
        if response is None:
            raise ValueError("No response from create operation")
        if not isinstance(response, dict):
            raise ValueError("Create operation returned invalid response")

        # Get the created alias key and fetch full data
        key = response.get("$key")
        if key is None:
            raise ValueError("Create response missing $key")

        return self.get(int(key))

    def delete(self, key: int) -> None:
        """Delete an IP alias.

        Args:
            key: Alias $key (ID).

        Note:
            Aliases referenced by firewall rules cannot be deleted
            until the rules are removed.
        """
        self._client._request("DELETE", f"{self._endpoint}/{key}")
