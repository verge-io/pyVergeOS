"""Async query resource managers for network and node diagnostics."""

from __future__ import annotations

import builtins
import logging
import time
from typing import TYPE_CHECKING, Any, Literal

from pyvergeos.exceptions import NotFoundError, VergeTimeoutError
from pyvergeos.resources.base import ResourceManager, ResourceObject

if TYPE_CHECKING:
    from pyvergeos.client import VergeClient

logger = logging.getLogger(__name__)

# Query status values
QueryStatus = Literal["running", "error", "complete"]

# Query types per endpoint
VNetQueryType = Literal[
    "logs",
    "top",
    "top_if",
    "tcpdump",
    "ping",
    "dns",
    "traceroute",
    "ip",
    "ipsec",
    "whatsmyip",
    "arp",
    "arp-scan",
    "frr",
    "trace",
    "dhcp_release_renew",
    "wireguard",
    "firewall",
    "nmap",
    "tcp_connect",
]

NodeQueryType = Literal[
    "logs",
    "top",
    "top_if",
    "tcpdump",
    "ping",
    "dns",
    "traceroute",
    "ip",
    "bridge",
    "whatsmyip",
    "ipmi-sel",
    "ipmi-sensor",
    "ipmi-fru",
    "ipmi-lan",
    "ipmi-chassis",
    "ipmi-bmc",
    "ipmi-sdr",
    "ipmi-reset",
    "dmidecode",
    "lsblk",
    "arp",
    "arp-scan",
    "smartctl",
    "smartctl-test",
    "ledctl",
    "openssl-speed",
    "tcp_connect",
    "eth-tool",
    "fabric",
    "clear-pstore",
    "ras-mc-ctl",
    "bonding",
]

ServiceContainerQueryType = Literal[
    "logs",
    "top",
    "top_if",
    "tcpdump",
    "ping",
    "dns",
    "traceroute",
    "ip",
    "arp",
    "arp-scan",
    "whatsmyip",
    "dhcp_release_renew",
    "tcp_connect",
]

TenantNodeQueryType = Literal[
    "logs",
    "top",
    "top_if",
    "tcpdump",
    "ping",
    "dns",
    "traceroute",
    "ip",
    "arp",
    "arp-scan",
    "whatsmyip",
    "tcp_connect",
]

# Default fields for query results
QUERY_DEFAULT_FIELDS = [
    "$key",
    "id",
    "query",
    "params",
    "status",
    "result",
    "command",
    "created",
    "modified",
    "expires",
]


class QueryResult(ResourceObject):
    """Async query result resource object.

    Represents a query submitted to a VergeOS diagnostic endpoint.
    Queries run asynchronously — poll ``status`` until ``complete`` or ``error``.

    Note: Query resources use SHA1 string keys, not integer keys.
    Use ``query_key`` instead of the base ``key`` property.
    """

    @property
    def query_key(self) -> str:
        """Query primary key (SHA1 string).

        Query endpoints use string keys unlike most VergeOS resources.
        """
        k = self.get("$key")
        if k is None:
            raise ValueError("Query has no $key")
        return str(k)

    @property
    def query_id(self) -> str:
        """SHA1 query identifier."""
        return str(self.get("id", ""))

    @property
    def query_type(self) -> str:
        """Query type (e.g. ping, tcpdump, arp)."""
        return str(self.get("query", ""))

    @property
    def status(self) -> str:  # noqa: A003
        """Query status: running, error, or complete."""
        return str(self.get("status", "running"))

    @property
    def is_complete(self) -> bool:
        """Check if query has finished successfully."""
        return self.status == "complete"

    @property
    def is_error(self) -> bool:
        """Check if query ended in error."""
        return self.status == "error"

    @property
    def is_running(self) -> bool:
        """Check if query is still running."""
        return self.status == "running"

    @property
    def result(self) -> str | None:
        """Query result text (max 262KB)."""
        return self.get("result")

    @property
    def command(self) -> str | None:
        """Command that was executed (read-only)."""
        return self.get("command")

    @property
    def params(self) -> dict[str, Any] | None:
        """Query parameters."""
        return self.get("params")


class QueryManager(ResourceManager[QueryResult]):
    """Base manager for async query endpoints.

    All four query endpoints (vnet, node, service_container, tenant_node)
    share the same async pattern: POST to create, poll status for
    complete/error, read result.

    Subclasses set ``_endpoint`` and ``_parent_field``.
    """

    _endpoint: str = ""
    _parent_field: str = ""

    def __init__(self, client: VergeClient, parent_key: int) -> None:
        super().__init__(client)
        self._parent_key = parent_key

    def _to_model(self, data: dict[str, Any]) -> QueryResult:
        return QueryResult(data, self)

    def list(  # noqa: A003
        self,
        filter: str | None = None,  # noqa: A002
        fields: builtins.list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        **filter_kwargs: Any,
    ) -> builtins.list[QueryResult]:
        """List queries for this parent resource.

        Args:
            filter: Additional OData filter string.
            fields: List of fields to return.
            limit: Maximum number of results.
            offset: Skip this many results.

        Returns:
            List of QueryResult objects.
        """
        if fields is None:
            fields = QUERY_DEFAULT_FIELDS

        parent_filter = f"{self._parent_field} eq {self._parent_key}"
        if filter:
            parent_filter = f"{parent_filter} and ({filter})"

        params: dict[str, Any] = {
            "filter": parent_filter,
            "fields": ",".join(fields),
        }
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset

        response = self._client._request("GET", self._endpoint, params=params)
        if response is None:
            return []
        if not isinstance(response, list):
            return [self._to_model(response)]
        return [self._to_model(item) for item in response]

    def get(  # type: ignore[override]
        self,
        key: str | int | None = None,
        *,
        query_id: str | None = None,
        fields: builtins.list[str] | None = None,
    ) -> QueryResult:
        """Get a query by key or query ID.

        Args:
            key: Query $key (SHA1 string or integer row key).
            query_id: SHA1 query identifier string.
            fields: List of fields to return.

        Returns:
            QueryResult object.

        Raises:
            NotFoundError: If query not found.
            ValueError: If neither key nor query_id provided.
        """
        if fields is None:
            fields = QUERY_DEFAULT_FIELDS

        if key is not None:
            params: dict[str, Any] = {"fields": ",".join(fields)}
            response = self._client._request("GET", f"{self._endpoint}/{key}", params=params)
            if response is None:
                raise NotFoundError(f"Query {key} not found")
            if not isinstance(response, dict):
                raise NotFoundError(f"Query {key} returned invalid response")
            return self._to_model(response)

        if query_id is not None:
            escaped_id = query_id.replace("'", "''")
            results = self.list(filter=f"id eq '{escaped_id}'", fields=fields, limit=1)
            if not results:
                raise NotFoundError(f"Query with id '{query_id}' not found")
            return results[0]

        raise ValueError("Either key or query_id must be provided")

    def create(  # type: ignore[override]
        self,
        query: str,
        params: dict[str, Any] | None = None,
    ) -> QueryResult:
        """Submit a new async query.

        Args:
            query: Query type string (e.g. "ping", "tcpdump", "arp").
            params: Query parameters (varies by query type).

        Returns:
            QueryResult object (status will be "running").
        """
        body: dict[str, Any] = {
            self._parent_field: self._parent_key,
            "query": query,
        }
        if params:
            body["params"] = params

        response = self._client._request("POST", self._endpoint, json_data=body)
        if response is None:
            raise ValueError("No response from query creation")
        if not isinstance(response, dict):
            raise ValueError("Query creation returned invalid response")

        key = response.get("$key")
        if key is not None:
            return self.get(key)
        return self._to_model(response)

    def wait(
        self,
        key: str | int,
        timeout: float = 120,
        poll_interval: float = 1.0,
    ) -> QueryResult:
        """Poll a query until it completes or errors.

        Args:
            key: Query $key to poll (SHA1 string or integer).
            timeout: Maximum seconds to wait.
            poll_interval: Seconds between polls.

        Returns:
            Completed QueryResult.

        Raises:
            VergeTimeoutError: If query doesn't complete within timeout.
        """
        deadline = time.monotonic() + timeout
        while True:
            result = self.get(key)
            if result.status in ("complete", "error"):
                return result
            if time.monotonic() >= deadline:
                raise VergeTimeoutError(
                    f"Query {key} did not complete within {timeout}s (status: {result.status})"
                )
            time.sleep(poll_interval)

    def run(
        self,
        query: str,
        params: dict[str, Any] | None = None,
        timeout: float = 120,
        poll_interval: float = 1.0,
    ) -> QueryResult:
        """Submit a query and wait for completion.

        Convenience method combining create() + wait().

        Args:
            query: Query type string.
            params: Query parameters.
            timeout: Maximum seconds to wait.
            poll_interval: Seconds between polls.

        Returns:
            Completed QueryResult.
        """
        result = self.create(query, params)
        return self.wait(result.query_key, timeout=timeout, poll_interval=poll_interval)


class VNetQueryManager(QueryManager):
    """Manager for virtual network diagnostic queries.

    Supports 19 query types including ping, dns, tcpdump, traceroute,
    arp, firewall trace, and more.

    Examples:
        Run a ping query::

            result = network.queries.run("ping", {"host": "8.8.8.8"})
            print(result.result)

        Run a tcpdump capture::

            query = network.queries.create("tcpdump", {"interface": "eth0"})
            # ... wait or poll ...
            result = network.queries.get(query.key)
    """

    _endpoint = "vnet_queries"
    _parent_field = "vnet"

    def ping(
        self,
        target: str,
        timeout: float = 30,
        **params: Any,
    ) -> QueryResult:
        """Run a ping query.

        Args:
            target: Target host or IP address.
            timeout: Max seconds to wait for result.
            **params: Additional ping parameters.

        Returns:
            Completed QueryResult with ping output.
        """
        return self.run("ping", {"host": target, **params}, timeout=timeout)

    def dns(
        self,
        name: str,
        timeout: float = 30,
        **params: Any,
    ) -> QueryResult:
        """Run a DNS lookup query.

        Args:
            name: Hostname to resolve.
            timeout: Max seconds to wait for result.
            **params: Additional DNS parameters.

        Returns:
            Completed QueryResult with DNS output.
        """
        return self.run("dns", {"name": name, **params}, timeout=timeout)

    def traceroute(
        self,
        target: str,
        timeout: float = 60,
        **params: Any,
    ) -> QueryResult:
        """Run a traceroute query.

        Args:
            target: Target host or IP address.
            timeout: Max seconds to wait for result.
            **params: Additional traceroute parameters.

        Returns:
            Completed QueryResult with traceroute output.
        """
        return self.run("traceroute", {"host": target, **params}, timeout=timeout)

    def tcpdump(
        self,
        timeout: float = 120,
        **params: Any,
    ) -> QueryResult:
        """Run a packet capture query.

        Args:
            timeout: Max seconds to wait for result.
            **params: tcpdump parameters (interface, count, filter, etc.).

        Returns:
            Completed QueryResult with capture output.
        """
        return self.run("tcpdump", params if params else None, timeout=timeout)

    def arp(self, timeout: float = 30) -> QueryResult:
        """Get ARP table.

        Args:
            timeout: Max seconds to wait for result.

        Returns:
            Completed QueryResult with ARP table output.
        """
        return self.run("arp", timeout=timeout)

    def firewall(self, timeout: float = 30, **params: Any) -> QueryResult:
        """Get firewall rule listing.

        Args:
            timeout: Max seconds to wait for result.
            **params: Additional firewall query parameters.

        Returns:
            Completed QueryResult with nftables output.
        """
        return self.run("firewall", params if params else None, timeout=timeout)

    def trace(self, timeout: float = 30, **params: Any) -> QueryResult:
        """Run nftables packet trace.

        Args:
            timeout: Max seconds to wait for result.
            **params: Trace parameters.

        Returns:
            Completed QueryResult with trace output.
        """
        return self.run("trace", params if params else None, timeout=timeout)


class NodeQueryManager(QueryManager):
    """Manager for node diagnostic queries.

    Supports 30+ query types including system diagnostics, IPMI,
    storage (smartctl, lsblk), network, and hardware queries.

    Examples:
        Check IPMI sensors::

            result = node.queries.run("ipmi-sensor")
            print(result.result)

        Run a SMART check::

            result = node.queries.run("smartctl", {"device": "/dev/sda"})
    """

    _endpoint = "node_queries"
    _parent_field = "node"

    def ping(
        self,
        target: str,
        timeout: float = 30,
        **params: Any,
    ) -> QueryResult:
        """Run a ping query.

        Args:
            target: Target host or IP address.
            timeout: Max seconds to wait for result.
            **params: Additional ping parameters.

        Returns:
            Completed QueryResult with ping output.
        """
        return self.run("ping", {"host": target, **params}, timeout=timeout)

    def dns(
        self,
        name: str,
        timeout: float = 30,
        **params: Any,
    ) -> QueryResult:
        """Run a DNS lookup query.

        Args:
            name: Hostname to resolve.
            timeout: Max seconds to wait for result.
            **params: Additional DNS parameters.

        Returns:
            Completed QueryResult with DNS output.
        """
        return self.run("dns", {"name": name, **params}, timeout=timeout)

    def traceroute(
        self,
        target: str,
        timeout: float = 60,
        **params: Any,
    ) -> QueryResult:
        """Run a traceroute query.

        Args:
            target: Target host or IP address.
            timeout: Max seconds to wait for result.
            **params: Additional traceroute parameters.

        Returns:
            Completed QueryResult with traceroute output.
        """
        return self.run("traceroute", {"host": target, **params}, timeout=timeout)

    def tcpdump(
        self,
        timeout: float = 120,
        **params: Any,
    ) -> QueryResult:
        """Run a packet capture query.

        Args:
            timeout: Max seconds to wait for result.
            **params: tcpdump parameters.

        Returns:
            Completed QueryResult with capture output.
        """
        return self.run("tcpdump", params if params else None, timeout=timeout)

    def arp(self, timeout: float = 30) -> QueryResult:
        """Get ARP table.

        Args:
            timeout: Max seconds to wait for result.

        Returns:
            Completed QueryResult with ARP table output.
        """
        return self.run("arp", timeout=timeout)

    def smartctl(
        self,
        device: str,
        timeout: float = 60,
        **params: Any,
    ) -> QueryResult:
        """Run SMART diagnostics on a drive.

        Args:
            device: Device path (e.g. /dev/sda).
            timeout: Max seconds to wait for result.
            **params: Additional smartctl parameters.

        Returns:
            Completed QueryResult with SMART output.
        """
        return self.run("smartctl", {"device": device, **params}, timeout=timeout)

    def lsblk(self, timeout: float = 30) -> QueryResult:
        """List block devices.

        Args:
            timeout: Max seconds to wait for result.

        Returns:
            Completed QueryResult with block device listing.
        """
        return self.run("lsblk", timeout=timeout)

    def dmidecode(self, timeout: float = 30) -> QueryResult:
        """Get DMI/SMBIOS hardware information.

        Args:
            timeout: Max seconds to wait for result.

        Returns:
            Completed QueryResult with hardware info.
        """
        return self.run("dmidecode", timeout=timeout)


class ServiceContainerQueryManager(QueryManager):
    """Manager for service container diagnostic queries.

    Supports 13 query types for diagnosing network issues
    within service containers.
    """

    _endpoint = "service_container_queries"
    _parent_field = "service_container"

    def ping(
        self,
        target: str,
        timeout: float = 30,
        **params: Any,
    ) -> QueryResult:
        """Run a ping query.

        Args:
            target: Target host or IP address.
            timeout: Max seconds to wait for result.

        Returns:
            Completed QueryResult with ping output.
        """
        return self.run("ping", {"host": target, **params}, timeout=timeout)

    def dns(
        self,
        name: str,
        timeout: float = 30,
        **params: Any,
    ) -> QueryResult:
        """Run a DNS lookup query.

        Args:
            name: Hostname to resolve.
            timeout: Max seconds to wait for result.

        Returns:
            Completed QueryResult with DNS output.
        """
        return self.run("dns", {"name": name, **params}, timeout=timeout)

    def traceroute(
        self,
        target: str,
        timeout: float = 60,
        **params: Any,
    ) -> QueryResult:
        """Run a traceroute query.

        Args:
            target: Target host or IP address.
            timeout: Max seconds to wait for result.

        Returns:
            Completed QueryResult with traceroute output.
        """
        return self.run("traceroute", {"host": target, **params}, timeout=timeout)


class TenantNodeQueryManager(QueryManager):
    """Manager for tenant node diagnostic queries.

    Supports 12 query types for diagnosing network and system
    issues within tenant nodes.
    """

    _endpoint = "tenant_node_queries"
    _parent_field = "tenant_node"

    def ping(
        self,
        target: str,
        timeout: float = 30,
        **params: Any,
    ) -> QueryResult:
        """Run a ping query.

        Args:
            target: Target host or IP address.
            timeout: Max seconds to wait for result.

        Returns:
            Completed QueryResult with ping output.
        """
        return self.run("ping", {"host": target, **params}, timeout=timeout)

    def dns(
        self,
        name: str,
        timeout: float = 30,
        **params: Any,
    ) -> QueryResult:
        """Run a DNS lookup query.

        Args:
            name: Hostname to resolve.
            timeout: Max seconds to wait for result.

        Returns:
            Completed QueryResult with DNS output.
        """
        return self.run("dns", {"name": name, **params}, timeout=timeout)

    def traceroute(
        self,
        target: str,
        timeout: float = 60,
        **params: Any,
    ) -> QueryResult:
        """Run a traceroute query.

        Args:
            target: Target host or IP address.
            timeout: Max seconds to wait for result.

        Returns:
            Completed QueryResult with traceroute output.
        """
        return self.run("traceroute", {"host": target, **params}, timeout=timeout)
