"""DNS View resource manager."""

from __future__ import annotations

import builtins
from typing import TYPE_CHECKING, Any

from pyvergeos.exceptions import NotFoundError
from pyvergeos.resources.base import ResourceManager, ResourceObject

if TYPE_CHECKING:
    from pyvergeos.client import VergeClient
    from pyvergeos.resources.dns import DNSZoneManager
    from pyvergeos.resources.networks import Network

# Default fields for DNS view data
DNS_VIEW_DEFAULT_FIELDS = [
    "$key",
    "name",
    "recursion",
    "match_clients",
    "match_destinations",
    "max_cache_size",
    "query_source",
    "vnet",
]


class DNSView(ResourceObject):
    """DNS View resource object."""

    @property
    def name(self) -> str:
        """Get the view name."""
        return self.get("name") or ""

    @property
    def recursion(self) -> bool:
        """Get whether recursive DNS queries are enabled."""
        return bool(self.get("recursion", False))

    @property
    def match_clients(self) -> str | None:
        """Get client IP networks to match (semicolon-delimited)."""
        return self.get("match_clients")

    @property
    def match_destinations(self) -> str | None:
        """Get destination networks to match (semicolon-delimited)."""
        return self.get("match_destinations")

    @property
    def max_cache_size(self) -> int:
        """Get maximum RAM for DNS cache in bytes (0 = unlimited)."""
        return self.get("max_cache_size") or 0

    @property
    def query_source(self) -> int | None:
        """Get the query source address reference."""
        val = self.get("query_source")
        return int(val) if val is not None else None

    @property
    def network_key(self) -> int:
        """Get the network key this view belongs to."""
        vnet = self.get("vnet")
        if vnet is None:
            raise ValueError("View has no network key")
        return int(vnet)

    @property
    def zones(self) -> DNSZoneManager:
        """Access DNS zones in this view.

        Returns:
            DNSZoneManager scoped to this view.

        Examples:
            List zones in this view::

                zones = view.zones.list()

            Create a zone::

                zone = view.zones.create(domain="example.com")
        """
        from pyvergeos.resources.dns import DNSZoneManager

        return DNSZoneManager(self._manager._client, view=self)


class DNSViewManager(ResourceManager[DNSView]):
    """Manager for DNS View operations.

    This manager is accessed through a Network object's dns_views property.

    Examples:
        List all views for a network::

            views = network.dns_views.list()

        Get a view by name::

            view = network.dns_views.get(name="internal")

        Create a view::

            view = network.dns_views.create(
                name="internal",
                recursion=True,
                match_clients="10/8;172.16/16;",
            )

        Access zones through a view::

            zones = view.zones.list()
            zone = view.zones.create(domain="example.com")
    """

    _endpoint = "vnet_dns_views"
    _default_fields = DNS_VIEW_DEFAULT_FIELDS

    def __init__(self, client: VergeClient, network: Network) -> None:
        super().__init__(client)
        self._network = network

    @property
    def network_key(self) -> int:
        """Get the network key for this manager."""
        return self._network.key

    def _to_model(self, data: dict[str, Any]) -> DNSView:
        return DNSView(data, self)

    def list(  # type: ignore[override]
        self,
        filter: str | None = None,  # noqa: A002
        fields: builtins.list[str] | None = None,
        **kwargs: Any,
    ) -> builtins.list[DNSView]:
        """List DNS views for this network.

        Args:
            filter: Additional OData filter string.
            fields: List of fields to return.
            **kwargs: Additional filter arguments.

        Returns:
            List of DNSView objects.
        """
        if fields is None:
            fields = self._default_fields.copy()

        filters: builtins.list[str] = [f"vnet eq {self.network_key}"]

        if filter:
            filters.append(f"({filter})")

        combined_filter = " and ".join(filters)

        params: dict[str, Any] = {
            "filter": combined_filter,
            "fields": ",".join(fields),
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
    ) -> DNSView:
        """Get a DNS view by key or name.

        Args:
            key: View $key (ID).
            name: View name.
            fields: List of fields to return.

        Returns:
            DNSView object.

        Raises:
            NotFoundError: If view not found.
            ValueError: If neither key nor name provided.
        """
        if fields is None:
            fields = self._default_fields.copy()

        if key is not None:
            params: dict[str, Any] = {"fields": ",".join(fields)}
            response = self._client._request("GET", f"{self._endpoint}/{key}", params=params)
            if response is None:
                raise NotFoundError(f"DNS view {key} not found")
            if not isinstance(response, dict):
                raise NotFoundError(f"DNS view {key} returned invalid response")
            return self._to_model(response)

        if name is not None:
            escaped_name = name.replace("'", "''")
            views = self.list(filter=f"name eq '{escaped_name}'")
            if not views:
                raise NotFoundError(f"DNS view '{name}' not found on this network")
            return views[0]

        raise ValueError("Either key or name must be provided")

    def create(  # type: ignore[override]
        self,
        name: str,
        recursion: bool = False,
        match_clients: str | None = None,
        match_destinations: str | None = None,
        max_cache_size: int = 33554432,
        query_source: int | None = None,
    ) -> DNSView:
        """Create a new DNS view.

        Args:
            name: View name (must be unique per network).
            recursion: Enable recursive DNS queries (default False).
            match_clients: Client IP networks to match (semicolon-delimited,
                e.g., "10/8;172.16/16;").
            match_destinations: Destination networks to match
                (semicolon-delimited).
            max_cache_size: Maximum RAM for DNS cache in bytes
                (default 33554432 / 32MB, 0 = unlimited).
            query_source: Reference to vnet_addresses for query source IP.

        Returns:
            Created DNSView object.

        Note:
            DNS changes require DNS apply on the network to take effect.
        """
        body: dict[str, Any] = {
            "vnet": self.network_key,
            "name": name,
            "recursion": recursion,
            "max_cache_size": max_cache_size,
        }

        if match_clients is not None:
            body["match_clients"] = match_clients

        if match_destinations is not None:
            body["match_destinations"] = match_destinations

        if query_source is not None:
            body["query_source"] = query_source

        response = self._client._request("POST", self._endpoint, json_data=body)
        if response is None:
            raise ValueError("No response from create operation")
        if not isinstance(response, dict):
            raise ValueError("Create operation returned invalid response")

        key = response.get("$key")
        if key is None:
            raise ValueError("Create response missing $key")

        return self.get(int(key))

    def update(  # type: ignore[override]
        self,
        key: int,
        name: str | None = None,
        recursion: bool | None = None,
        match_clients: str | None = None,
        match_destinations: str | None = None,
        max_cache_size: int | None = None,
        query_source: int | None = None,
    ) -> DNSView:
        """Update a DNS view.

        Args:
            key: View $key (ID).
            name: New view name.
            recursion: Enable/disable recursive DNS queries.
            match_clients: Client IP networks to match.
            match_destinations: Destination networks to match.
            max_cache_size: Maximum RAM for DNS cache in bytes.
            query_source: Reference to vnet_addresses for query source IP.

        Returns:
            Updated DNSView object.

        Note:
            DNS changes require DNS apply on the network to take effect.
        """
        body: dict[str, Any] = {}

        if name is not None:
            body["name"] = name
        if recursion is not None:
            body["recursion"] = recursion
        if match_clients is not None:
            body["match_clients"] = match_clients
        if match_destinations is not None:
            body["match_destinations"] = match_destinations
        if max_cache_size is not None:
            body["max_cache_size"] = max_cache_size
        if query_source is not None:
            body["query_source"] = query_source

        if not body:
            return self.get(key)

        self._client._request("PUT", f"{self._endpoint}/{key}", json_data=body)

        return self.get(key)

    def delete(self, key: int) -> None:
        """Delete a DNS view.

        Args:
            key: View $key (ID).

        Note:
            Deleting a view also deletes all zones and records within it.
            DNS changes require DNS apply on the network to take effect.
        """
        self._client._request("DELETE", f"{self._endpoint}/{key}")
