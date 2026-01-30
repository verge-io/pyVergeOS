"""Network routing protocol resource managers (BGP, OSPF, EIGRP)."""

from __future__ import annotations

import builtins
from typing import TYPE_CHECKING, Any, Literal

from pyvergeos.exceptions import NotFoundError
from pyvergeos.resources.base import ResourceManager, ResourceObject

if TYPE_CHECKING:
    from pyvergeos.client import VergeClient
    from pyvergeos.resources.networks import Network


# BGP Router Command types
BGPRouterCommandType = Literal[
    "aggregate-address",
    "bgp",
    "bmp",
    "coalesce-time",
    "distance",
    "maximum-paths",
    "neighbor",
    "network",
    "read-quanta",
    "redistribute",
    "segment-routing",
    "table-map",
    "timers",
    "update-delay",
    "vnc",
    "vrf-policy",
    "write-quanta",
]

# BGP Interface Command types
BGPInterfaceCommandType = Literal[
    "bandwidth",
    "description",
    "ip",
    "link-detect",
    "mpls-te",
    "multicast",
    "no",
    "ospf",
]

# BGP Route Map Command types
BGPRouteMapCommandType = Literal[
    "call",
    "continue",
    "description",
    "match",
    "on",
    "set",
]

# BGP IP Command types (for prefix-list, as-path, etc.)
BGPIPCommandType = Literal[
    "as-path",
    "community-list",
    "extcommunity-list",
    "forwarding",
    "mroute",
    "multicast",
    "multicast-routing",
    "ospf",
    "prefix-list",
    "protocol",
    "route",
    "ssmpingd",
]

# OSPF Command types
OSPFCommandType = Literal[
    "advanced",
    "area",
    "auto-cost",
    "capability",
    "default-information",
    "default-metric",
    "distance",
    "distribute-list",
    "log-adjacency-changes",
    "max-metric",
    "mpls-te",
    "neighbor",
    "network",
    "no",
    "ospf",
    "passive-interface",
    "redistribute",
    "router-id",
    "timers",
]

# EIGRP Router Command types
EIGRPRouterCommandType = Literal[
    "eigrp",
    "coalesce-time",
    "maximum-paths",
    "metric",
    "neighbor",
    "network",
    "passive-interface",
    "redistribute",
    "timers",
    "variance",
]

# Layer 2 types for BGP interfaces
Layer2Type = Literal["vlan", "none"]

# Default fields for various queries
DEFAULT_BGP_ROUTER_FIELDS = ["$key", "bgp", "asn"]

DEFAULT_BGP_ROUTER_COMMAND_FIELDS = [
    "$key",
    "bgp_router",
    "orderid",
    "enabled",
    "no",
    "command",
    "params",
]

DEFAULT_BGP_INTERFACE_FIELDS = [
    "$key",
    "bgp",
    "name",
    "description",
    "ipaddress",
    "network",
    "mtu",
    "layer2_type",
    "layer2_id",
    "interface_vnet",
    "bgp_vnet",
    "nic",
]

DEFAULT_BGP_INTERFACE_COMMAND_FIELDS = [
    "$key",
    "bgp_interface",
    "orderid",
    "command",
    "params",
]

DEFAULT_BGP_ROUTEMAP_FIELDS = [
    "$key",
    "bgp",
    "tag",
    "permit",
    "sequence",
]

DEFAULT_BGP_ROUTEMAP_COMMAND_FIELDS = [
    "$key",
    "bgp_routemap",
    "orderid",
    "command",
    "params",
]

DEFAULT_BGP_IP_FIELDS = [
    "$key",
    "bgp",
    "orderid",
    "command",
    "params",
]

DEFAULT_OSPF_COMMAND_FIELDS = [
    "$key",
    "bgp",
    "orderid",
    "command",
    "params",
]

DEFAULT_EIGRP_ROUTER_FIELDS = ["$key", "bgp", "asn"]

DEFAULT_EIGRP_ROUTER_COMMAND_FIELDS = [
    "$key",
    "eigrp_router",
    "orderid",
    "enabled",
    "no",
    "command",
    "params",
]


# =============================================================================
# BGP Router Commands
# =============================================================================


class BGPRouterCommand(ResourceObject):
    """BGP router command object.

    Commands configure BGP router behavior including neighbors, networks,
    redistribution, and protocol settings.
    """

    @property
    def command_type(self) -> str:
        """Get the command type (neighbor, network, redistribute, etc.)."""
        return str(self.get("command", ""))

    @property
    def params(self) -> str:
        """Get the command parameters."""
        return str(self.get("params", ""))

    @property
    def is_enabled(self) -> bool:
        """Check if the command is enabled."""
        return bool(self.get("enabled", True))

    @property
    def is_negated(self) -> bool:
        """Check if the command is negated (no prefix)."""
        return bool(self.get("no", False))

    @property
    def order_id(self) -> int:
        """Get the command order ID."""
        return int(self.get("orderid", 0))


class BGPRouterCommandManager(ResourceManager[BGPRouterCommand]):
    """Manager for BGP router commands.

    Commands configure the BGP router including neighbors, networks,
    redistribution, and other protocol settings.

    Examples:
        List commands for a router::

            commands = router.commands.list()

        Add a neighbor::

            router.commands.create(
                command="neighbor",
                params="192.168.1.1 remote-as 65001"
            )

        Add a network advertisement::

            router.commands.create(
                command="network",
                params="10.0.0.0/24"
            )
    """

    _endpoint = "vnet_bgp_router_commands"

    def __init__(self, client: VergeClient, router: BGPRouter) -> None:
        super().__init__(client)
        self._router = router

    def _to_model(self, data: dict[str, Any]) -> BGPRouterCommand:
        data["_router_key"] = self._router.key
        return BGPRouterCommand(data, self)

    def list(
        self,
        filter: str | None = None,
        fields: builtins.list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        **filter_kwargs: Any,
    ) -> builtins.list[BGPRouterCommand]:
        """List commands for this BGP router.

        Args:
            filter: OData filter string.
            fields: List of fields to return.
            limit: Maximum number of results.
            offset: Skip this many results.
            **filter_kwargs: Shorthand filter arguments.

        Returns:
            List of BGPRouterCommand objects.
        """
        params: dict[str, Any] = {}

        # Always filter by parent router
        filters = [f"bgp_router eq {self._router.key}"]
        if filter:
            filters.append(filter)
        params["filter"] = " and ".join(filters)

        if fields is None:
            fields = DEFAULT_BGP_ROUTER_COMMAND_FIELDS.copy()
        params["fields"] = ",".join(fields)

        params["sort"] = "orderid"

        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset

        response = self._client._request("GET", self._endpoint, params=params)

        if response is None:
            return []
        if not isinstance(response, builtins.list):
            return [self._to_model(response)]
        return [self._to_model(item) for item in response]

    def get(  # type: ignore[override]
        self,
        key: int | None = None,
        *,
        fields: builtins.list[str] | None = None,
    ) -> BGPRouterCommand:
        """Get a single command by key.

        Args:
            key: Command $key (ID).
            fields: List of fields to return.

        Returns:
            BGPRouterCommand object.

        Raises:
            NotFoundError: If command not found.
            ValueError: If key not provided.
        """
        if key is None:
            raise ValueError("Key must be provided")

        if fields is None:
            fields = DEFAULT_BGP_ROUTER_COMMAND_FIELDS.copy()

        params: dict[str, Any] = {"fields": ",".join(fields)}
        response = self._client._request("GET", f"{self._endpoint}/{key}", params=params)
        if response is None:
            raise NotFoundError(f"BGP router command with key {key} not found")
        if not isinstance(response, dict):
            raise NotFoundError(f"BGP router command {key} returned invalid response")
        return self._to_model(response)

    def create(  # type: ignore[override]
        self,
        command: BGPRouterCommandType,
        params: str,
        *,
        enabled: bool = True,
        negate: bool = False,
    ) -> BGPRouterCommand:
        """Create a new BGP router command.

        Args:
            command: Command type (neighbor, network, redistribute, etc.).
            params: Command parameters.
            enabled: Whether the command is enabled.
            negate: Whether to negate the command (no prefix).

        Returns:
            Created BGPRouterCommand object.

        Examples:
            Add a BGP neighbor::

                cmd = router.commands.create(
                    command="neighbor",
                    params="192.168.1.1 remote-as 65001"
                )

            Advertise a network::

                cmd = router.commands.create(
                    command="network",
                    params="10.0.0.0/24"
                )

            Redistribute connected routes::

                cmd = router.commands.create(
                    command="redistribute",
                    params="connected"
                )
        """
        body: dict[str, Any] = {
            "bgp_router": self._router.key,
            "command": command,
            "params": params,
            "enabled": enabled,
            "no": negate,
        }

        response = self._client._request("POST", self._endpoint, json_data=body)
        if response is None or not isinstance(response, dict):
            raise ValueError("No response from create operation")

        cmd_key = response.get("$key")
        if cmd_key is None:
            raise ValueError("Create response missing $key")

        return self.get(int(cmd_key))

    def update(self, key: int, **kwargs: Any) -> BGPRouterCommand:
        """Update an existing command.

        Args:
            key: Command $key (ID).
            **kwargs: Attributes to update (command, params, enabled, negate).

        Returns:
            Updated BGPRouterCommand object.
        """
        body: dict[str, Any] = {}

        field_mapping = {
            "command": "command",
            "params": "params",
            "enabled": "enabled",
            "negate": "no",
        }

        for kwarg, api_field in field_mapping.items():
            if kwarg in kwargs:
                body[api_field] = kwargs[kwarg]

        if not body:
            raise ValueError("No update parameters provided")

        self._client._request("PUT", f"{self._endpoint}/{key}", json_data=body)
        return self.get(key)

    def delete(self, key: int) -> None:
        """Delete a command.

        Args:
            key: Command $key (ID).
        """
        self._client._request("DELETE", f"{self._endpoint}/{key}")


# =============================================================================
# BGP Routers
# =============================================================================


class BGPRouter(ResourceObject):
    """BGP router object.

    A BGP router defines an autonomous system number (ASN) and contains
    commands for configuring neighbors, networks, and other BGP settings.
    """

    @property
    def asn(self) -> int:
        """Get the Autonomous System Number."""
        return int(self.get("asn", 0))

    @property
    def commands(self) -> BGPRouterCommandManager:
        """Access commands for this BGP router.

        Returns:
            BGPRouterCommandManager for this router.

        Examples:
            List commands::

                commands = router.commands.list()

            Add a neighbor::

                router.commands.create(
                    command="neighbor",
                    params="192.168.1.1 remote-as 65001"
                )
        """
        manager = self._manager
        if not isinstance(manager, BGPRouterManager):
            raise TypeError("Manager must be BGPRouterManager")
        return BGPRouterCommandManager(manager._client, self)


class BGPRouterManager(ResourceManager[BGPRouter]):
    """Manager for BGP routers.

    BGP routers define the local autonomous system and contain
    configuration for BGP neighbors, networks, and policies.

    Examples:
        List BGP routers::

            routers = network.routing.bgp_routers.list()

        Create a BGP router::

            router = network.routing.bgp_routers.create(asn=65000)

        Add a neighbor to the router::

            router.commands.create(
                command="neighbor",
                params="192.168.1.1 remote-as 65001"
            )
    """

    _endpoint = "vnet_bgp_routers"

    def __init__(self, client: VergeClient, routing_manager: NetworkRoutingManager) -> None:
        super().__init__(client)
        self._routing_manager = routing_manager

    def _to_model(self, data: dict[str, Any]) -> BGPRouter:
        data["_network_key"] = self._routing_manager._network.key
        return BGPRouter(data, self)

    def list(
        self,
        filter: str | None = None,
        fields: builtins.list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        **filter_kwargs: Any,
    ) -> builtins.list[BGPRouter]:
        """List BGP routers for this network.

        Args:
            filter: OData filter string.
            fields: List of fields to return.
            limit: Maximum number of results.
            offset: Skip this many results.
            **filter_kwargs: Shorthand filter arguments.

        Returns:
            List of BGPRouter objects.
        """
        bgp_key = self._routing_manager._get_bgp_config()
        if bgp_key is None:
            return []

        params: dict[str, Any] = {}

        filters = [f"bgp eq {bgp_key}"]
        if filter:
            filters.append(filter)
        params["filter"] = " and ".join(filters)

        if fields is None:
            fields = DEFAULT_BGP_ROUTER_FIELDS.copy()
        params["fields"] = ",".join(fields)

        params["sort"] = "asn"

        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset

        response = self._client._request("GET", self._endpoint, params=params)

        if response is None:
            return []
        if not isinstance(response, builtins.list):
            return [self._to_model(response)]
        return [self._to_model(item) for item in response]

    def get(  # type: ignore[override]
        self,
        key: int | None = None,
        *,
        asn: int | None = None,
        fields: builtins.list[str] | None = None,
    ) -> BGPRouter:
        """Get a single BGP router by key or ASN.

        Args:
            key: Router $key (ID).
            asn: Autonomous System Number.
            fields: List of fields to return.

        Returns:
            BGPRouter object.

        Raises:
            NotFoundError: If router not found.
            ValueError: If neither key nor asn provided.
        """
        if fields is None:
            fields = DEFAULT_BGP_ROUTER_FIELDS.copy()

        if key is not None:
            params: dict[str, Any] = {"fields": ",".join(fields)}
            response = self._client._request("GET", f"{self._endpoint}/{key}", params=params)
            if response is None:
                raise NotFoundError(f"BGP router with key {key} not found")
            if not isinstance(response, dict):
                raise NotFoundError(f"BGP router {key} returned invalid response")
            return self._to_model(response)

        if asn is not None:
            results = self.list(filter=f"asn eq {asn}", fields=fields)
            if not results:
                raise NotFoundError(f"BGP router with ASN {asn} not found")
            return results[0]

        raise ValueError("Either key or asn must be provided")

    def create(  # type: ignore[override]
        self,
        asn: int,
    ) -> BGPRouter:
        """Create a new BGP router.

        Args:
            asn: Autonomous System Number (1-4294967295).

        Returns:
            Created BGPRouter object.

        Examples:
            Create a BGP router::

                router = network.routing.bgp_routers.create(asn=65000)
        """
        bgp_key = self._routing_manager._get_or_create_bgp_config()

        body: dict[str, Any] = {
            "bgp": bgp_key,
            "asn": asn,
        }

        response = self._client._request("POST", self._endpoint, json_data=body)
        if response is None or not isinstance(response, dict):
            raise ValueError("No response from create operation")

        router_key = response.get("$key")
        if router_key is None:
            raise ValueError("Create response missing $key")

        return self.get(int(router_key))

    def update(self, key: int, **kwargs: Any) -> BGPRouter:
        """Update an existing BGP router.

        Args:
            key: Router $key (ID).
            **kwargs: Attributes to update (asn).

        Returns:
            Updated BGPRouter object.
        """
        body: dict[str, Any] = {}

        if "asn" in kwargs:
            body["asn"] = kwargs["asn"]

        if not body:
            raise ValueError("No update parameters provided")

        self._client._request("PUT", f"{self._endpoint}/{key}", json_data=body)
        return self.get(key)

    def delete(self, key: int) -> None:
        """Delete a BGP router.

        This also removes all associated commands.

        Args:
            key: Router $key (ID).
        """
        self._client._request("DELETE", f"{self._endpoint}/{key}")


# =============================================================================
# BGP Interface Commands
# =============================================================================


class BGPInterfaceCommand(ResourceObject):
    """BGP interface command object."""

    @property
    def command_type(self) -> str:
        """Get the command type."""
        return str(self.get("command", ""))

    @property
    def params(self) -> str:
        """Get the command parameters."""
        return str(self.get("params", ""))

    @property
    def order_id(self) -> int:
        """Get the command order ID."""
        return int(self.get("orderid", 0))


class BGPInterfaceCommandManager(ResourceManager[BGPInterfaceCommand]):
    """Manager for BGP interface commands.

    Commands configure the BGP interface including IP settings,
    OSPF parameters, and link detection.

    Examples:
        List commands::

            commands = interface.commands.list()

        Add OSPF cost::

            interface.commands.create(
                command="ospf",
                params="cost 10"
            )
    """

    _endpoint = "vnet_bgp_interface_commands"

    def __init__(self, client: VergeClient, interface: BGPInterface) -> None:
        super().__init__(client)
        self._interface = interface

    def _to_model(self, data: dict[str, Any]) -> BGPInterfaceCommand:
        data["_interface_key"] = self._interface.key
        return BGPInterfaceCommand(data, self)

    def list(
        self,
        filter: str | None = None,
        fields: builtins.list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        **filter_kwargs: Any,
    ) -> builtins.list[BGPInterfaceCommand]:
        """List commands for this interface.

        Args:
            filter: OData filter string.
            fields: List of fields to return.
            limit: Maximum number of results.
            offset: Skip this many results.
            **filter_kwargs: Shorthand filter arguments.

        Returns:
            List of BGPInterfaceCommand objects.
        """
        params: dict[str, Any] = {}

        filters = [f"bgp_interface eq {self._interface.key}"]
        if filter:
            filters.append(filter)
        params["filter"] = " and ".join(filters)

        if fields is None:
            fields = DEFAULT_BGP_INTERFACE_COMMAND_FIELDS.copy()
        params["fields"] = ",".join(fields)

        params["sort"] = "orderid"

        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset

        response = self._client._request("GET", self._endpoint, params=params)

        if response is None:
            return []
        if not isinstance(response, builtins.list):
            return [self._to_model(response)]
        return [self._to_model(item) for item in response]

    def get(  # type: ignore[override]
        self,
        key: int | None = None,
        *,
        fields: builtins.list[str] | None = None,
    ) -> BGPInterfaceCommand:
        """Get a single command by key.

        Args:
            key: Command $key (ID).
            fields: List of fields to return.

        Returns:
            BGPInterfaceCommand object.

        Raises:
            NotFoundError: If command not found.
            ValueError: If key not provided.
        """
        if key is None:
            raise ValueError("Key must be provided")

        if fields is None:
            fields = DEFAULT_BGP_INTERFACE_COMMAND_FIELDS.copy()

        params: dict[str, Any] = {"fields": ",".join(fields)}
        response = self._client._request("GET", f"{self._endpoint}/{key}", params=params)
        if response is None:
            raise NotFoundError(f"BGP interface command with key {key} not found")
        if not isinstance(response, dict):
            raise NotFoundError(f"BGP interface command {key} returned invalid response")
        return self._to_model(response)

    def create(  # type: ignore[override]
        self,
        command: BGPInterfaceCommandType,
        params: str,
    ) -> BGPInterfaceCommand:
        """Create a new interface command.

        Args:
            command: Command type (ip, ospf, bandwidth, etc.).
            params: Command parameters.

        Returns:
            Created BGPInterfaceCommand object.

        Examples:
            Set OSPF cost::

                cmd = interface.commands.create(
                    command="ospf",
                    params="cost 10"
                )
        """
        body: dict[str, Any] = {
            "bgp_interface": self._interface.key,
            "command": command,
            "params": params,
        }

        response = self._client._request("POST", self._endpoint, json_data=body)
        if response is None or not isinstance(response, dict):
            raise ValueError("No response from create operation")

        cmd_key = response.get("$key")
        if cmd_key is None:
            raise ValueError("Create response missing $key")

        return self.get(int(cmd_key))

    def update(self, key: int, **kwargs: Any) -> BGPInterfaceCommand:
        """Update an existing command.

        Args:
            key: Command $key (ID).
            **kwargs: Attributes to update (command, params).

        Returns:
            Updated BGPInterfaceCommand object.
        """
        body: dict[str, Any] = {}

        if "command" in kwargs:
            body["command"] = kwargs["command"]
        if "params" in kwargs:
            body["params"] = kwargs["params"]

        if not body:
            raise ValueError("No update parameters provided")

        self._client._request("PUT", f"{self._endpoint}/{key}", json_data=body)
        return self.get(key)

    def delete(self, key: int) -> None:
        """Delete a command.

        Args:
            key: Command $key (ID).
        """
        self._client._request("DELETE", f"{self._endpoint}/{key}")


# =============================================================================
# BGP Interfaces
# =============================================================================


class BGPInterface(ResourceObject):
    """BGP interface object.

    A BGP interface creates a Layer 2/3 connection for routing protocols.
    It creates an associated virtual network and NIC automatically.
    """

    @property
    def ip_address(self) -> str:
        """Get the interface IP address."""
        return str(self.get("ipaddress", ""))

    @property
    def network_address(self) -> str:
        """Get the network address (CIDR)."""
        return str(self.get("network", ""))

    @property
    def mtu(self) -> int:
        """Get the MTU size."""
        return int(self.get("mtu", 9000))

    @property
    def layer2_type(self) -> str:
        """Get the Layer 2 type (vlan or none)."""
        return str(self.get("layer2_type", "vlan"))

    @property
    def layer2_id(self) -> int | None:
        """Get the Layer 2 ID (VLAN ID)."""
        val = self.get("layer2_id")
        return int(val) if val is not None else None

    @property
    def interface_vnet(self) -> int | None:
        """Get the interface (uplink) network key."""
        val = self.get("interface_vnet")
        return int(val) if val is not None else None

    @property
    def commands(self) -> BGPInterfaceCommandManager:
        """Access commands for this interface.

        Returns:
            BGPInterfaceCommandManager for this interface.

        Examples:
            List commands::

                commands = interface.commands.list()

            Add OSPF cost::

                interface.commands.create(
                    command="ospf",
                    params="cost 10"
                )
        """
        manager = self._manager
        if not isinstance(manager, BGPInterfaceManager):
            raise TypeError("Manager must be BGPInterfaceManager")
        return BGPInterfaceCommandManager(manager._client, self)


class BGPInterfaceManager(ResourceManager[BGPInterface]):
    """Manager for BGP interfaces.

    BGP interfaces create Layer 2/3 connections for routing protocols.
    Each interface automatically creates an associated virtual network and NIC.

    Examples:
        List interfaces::

            interfaces = network.routing.bgp_interfaces.list()

        Create an interface::

            interface = network.routing.bgp_interfaces.create(
                name="bgp-peer-1",
                ip_address="10.255.0.1",
                network="10.255.0.0/30",
                interface_network=external_net.key,
                layer2_id=100
            )
    """

    _endpoint = "vnet_bgp_interfaces"

    def __init__(self, client: VergeClient, routing_manager: NetworkRoutingManager) -> None:
        super().__init__(client)
        self._routing_manager = routing_manager

    def _to_model(self, data: dict[str, Any]) -> BGPInterface:
        data["_network_key"] = self._routing_manager._network.key
        return BGPInterface(data, self)

    def list(
        self,
        filter: str | None = None,
        fields: builtins.list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        **filter_kwargs: Any,
    ) -> builtins.list[BGPInterface]:
        """List BGP interfaces for this network.

        Args:
            filter: OData filter string.
            fields: List of fields to return.
            limit: Maximum number of results.
            offset: Skip this many results.
            **filter_kwargs: Shorthand filter arguments.

        Returns:
            List of BGPInterface objects.
        """
        bgp_key = self._routing_manager._get_bgp_config()
        if bgp_key is None:
            return []

        params: dict[str, Any] = {}

        filters = [f"bgp eq {bgp_key}"]
        if filter:
            filters.append(filter)
        params["filter"] = " and ".join(filters)

        if fields is None:
            fields = DEFAULT_BGP_INTERFACE_FIELDS.copy()
        params["fields"] = ",".join(fields)

        params["sort"] = "name"

        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset

        response = self._client._request("GET", self._endpoint, params=params)

        if response is None:
            return []
        if not isinstance(response, builtins.list):
            return [self._to_model(response)]
        return [self._to_model(item) for item in response]

    def get(
        self,
        key: int | None = None,
        *,
        name: str | None = None,
        fields: builtins.list[str] | None = None,
    ) -> BGPInterface:
        """Get a single BGP interface by key or name.

        Args:
            key: Interface $key (ID).
            name: Interface name.
            fields: List of fields to return.

        Returns:
            BGPInterface object.

        Raises:
            NotFoundError: If interface not found.
            ValueError: If neither key nor name provided.
        """
        if fields is None:
            fields = DEFAULT_BGP_INTERFACE_FIELDS.copy()

        if key is not None:
            params: dict[str, Any] = {"fields": ",".join(fields)}
            response = self._client._request("GET", f"{self._endpoint}/{key}", params=params)
            if response is None:
                raise NotFoundError(f"BGP interface with key {key} not found")
            if not isinstance(response, dict):
                raise NotFoundError(f"BGP interface {key} returned invalid response")
            return self._to_model(response)

        if name is not None:
            escaped_name = name.replace("'", "''")
            results = self.list(filter=f"name eq '{escaped_name}'", fields=fields)
            if not results:
                raise NotFoundError(f"BGP interface with name '{name}' not found")
            return results[0]

        raise ValueError("Either key or name must be provided")

    def create(  # type: ignore[override]
        self,
        name: str,
        ip_address: str,
        network: str,
        interface_network: int,
        *,
        layer2_type: Layer2Type = "vlan",
        layer2_id: int | None = None,
        mtu: int = 9000,
        description: str = "",
    ) -> BGPInterface:
        """Create a new BGP interface.

        Args:
            name: Interface name.
            ip_address: IP address for this interface.
            network: Network address in CIDR notation (e.g., "10.255.0.0/30").
            interface_network: Key of the interface (uplink) network.
            layer2_type: Layer 2 type (vlan or none).
            layer2_id: VLAN ID (required if layer2_type is vlan).
            mtu: MTU size (1000-65536, default 9000).
            description: Interface description.

        Returns:
            Created BGPInterface object.

        Examples:
            Create a BGP peering interface::

                interface = network.routing.bgp_interfaces.create(
                    name="bgp-peer-isp",
                    ip_address="198.51.100.2",
                    network="198.51.100.0/30",
                    interface_network=external_net.key,
                    layer2_type="vlan",
                    layer2_id=100
                )
        """
        bgp_key = self._routing_manager._get_or_create_bgp_config()

        body: dict[str, Any] = {
            "bgp": bgp_key,
            "name": name,
            "ipaddress": ip_address,
            "network": network,
            "interface_vnet": interface_network,
            "layer2_type": layer2_type,
            "mtu": mtu,
        }

        if layer2_id is not None:
            body["layer2_id"] = layer2_id
        if description:
            body["description"] = description

        response = self._client._request("POST", self._endpoint, json_data=body)
        if response is None or not isinstance(response, dict):
            raise ValueError("No response from create operation")

        interface_key = response.get("$key")
        if interface_key is None:
            raise ValueError("Create response missing $key")

        return self.get(int(interface_key))

    def update(self, key: int, **kwargs: Any) -> BGPInterface:
        """Update an existing BGP interface.

        Args:
            key: Interface $key (ID).
            **kwargs: Attributes to update.

        Returns:
            Updated BGPInterface object.
        """
        body: dict[str, Any] = {}

        field_mapping = {
            "name": "name",
            "ip_address": "ipaddress",
            "network": "network",
            "interface_network": "interface_vnet",
            "layer2_type": "layer2_type",
            "layer2_id": "layer2_id",
            "mtu": "mtu",
            "description": "description",
        }

        for kwarg, api_field in field_mapping.items():
            if kwarg in kwargs:
                body[api_field] = kwargs[kwarg]

        if not body:
            raise ValueError("No update parameters provided")

        self._client._request("PUT", f"{self._endpoint}/{key}", json_data=body)
        return self.get(key)

    def delete(self, key: int) -> None:
        """Delete a BGP interface.

        This also removes the associated virtual network and NIC.

        Args:
            key: Interface $key (ID).
        """
        self._client._request("DELETE", f"{self._endpoint}/{key}")


# =============================================================================
# BGP Route Map Commands
# =============================================================================


class BGPRouteMapCommand(ResourceObject):
    """BGP route map command object."""

    @property
    def command_type(self) -> str:
        """Get the command type (match, set, call, etc.)."""
        return str(self.get("command", ""))

    @property
    def params(self) -> str:
        """Get the command parameters."""
        return str(self.get("params", ""))

    @property
    def order_id(self) -> int:
        """Get the command order ID."""
        return int(self.get("orderid", 0))


class BGPRouteMapCommandManager(ResourceManager[BGPRouteMapCommand]):
    """Manager for BGP route map commands.

    Commands define match conditions and set actions for route maps.

    Examples:
        List commands::

            commands = routemap.commands.list()

        Add a match condition::

            routemap.commands.create(
                command="match",
                params="ip address prefix-list MY-PREFIX"
            )

        Add a set action::

            routemap.commands.create(
                command="set",
                params="local-preference 200"
            )
    """

    _endpoint = "vnet_bgp_routemap_commands"

    def __init__(self, client: VergeClient, routemap: BGPRouteMap) -> None:
        super().__init__(client)
        self._routemap = routemap

    def _to_model(self, data: dict[str, Any]) -> BGPRouteMapCommand:
        data["_routemap_key"] = self._routemap.key
        return BGPRouteMapCommand(data, self)

    def list(
        self,
        filter: str | None = None,
        fields: builtins.list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        **filter_kwargs: Any,
    ) -> builtins.list[BGPRouteMapCommand]:
        """List commands for this route map.

        Args:
            filter: OData filter string.
            fields: List of fields to return.
            limit: Maximum number of results.
            offset: Skip this many results.
            **filter_kwargs: Shorthand filter arguments.

        Returns:
            List of BGPRouteMapCommand objects.
        """
        params: dict[str, Any] = {}

        filters = [f"bgp_routemap eq {self._routemap.key}"]
        if filter:
            filters.append(filter)
        params["filter"] = " and ".join(filters)

        if fields is None:
            fields = DEFAULT_BGP_ROUTEMAP_COMMAND_FIELDS.copy()
        params["fields"] = ",".join(fields)

        params["sort"] = "orderid"

        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset

        response = self._client._request("GET", self._endpoint, params=params)

        if response is None:
            return []
        if not isinstance(response, builtins.list):
            return [self._to_model(response)]
        return [self._to_model(item) for item in response]

    def get(  # type: ignore[override]
        self,
        key: int | None = None,
        *,
        fields: builtins.list[str] | None = None,
    ) -> BGPRouteMapCommand:
        """Get a single command by key.

        Args:
            key: Command $key (ID).
            fields: List of fields to return.

        Returns:
            BGPRouteMapCommand object.

        Raises:
            NotFoundError: If command not found.
            ValueError: If key not provided.
        """
        if key is None:
            raise ValueError("Key must be provided")

        if fields is None:
            fields = DEFAULT_BGP_ROUTEMAP_COMMAND_FIELDS.copy()

        params: dict[str, Any] = {"fields": ",".join(fields)}
        response = self._client._request("GET", f"{self._endpoint}/{key}", params=params)
        if response is None:
            raise NotFoundError(f"BGP route map command with key {key} not found")
        if not isinstance(response, dict):
            raise NotFoundError(f"BGP route map command {key} returned invalid response")
        return self._to_model(response)

    def create(  # type: ignore[override]
        self,
        command: BGPRouteMapCommandType,
        params: str,
    ) -> BGPRouteMapCommand:
        """Create a new route map command.

        Args:
            command: Command type (match, set, call, etc.).
            params: Command parameters.

        Returns:
            Created BGPRouteMapCommand object.

        Examples:
            Add a match condition::

                cmd = routemap.commands.create(
                    command="match",
                    params="ip address prefix-list MY-PREFIX"
                )

            Add a set action::

                cmd = routemap.commands.create(
                    command="set",
                    params="local-preference 200"
                )
        """
        body: dict[str, Any] = {
            "bgp_routemap": self._routemap.key,
            "command": command,
            "params": params,
        }

        response = self._client._request("POST", self._endpoint, json_data=body)
        if response is None or not isinstance(response, dict):
            raise ValueError("No response from create operation")

        cmd_key = response.get("$key")
        if cmd_key is None:
            raise ValueError("Create response missing $key")

        return self.get(int(cmd_key))

    def update(self, key: int, **kwargs: Any) -> BGPRouteMapCommand:
        """Update an existing command.

        Args:
            key: Command $key (ID).
            **kwargs: Attributes to update (command, params).

        Returns:
            Updated BGPRouteMapCommand object.
        """
        body: dict[str, Any] = {}

        if "command" in kwargs:
            body["command"] = kwargs["command"]
        if "params" in kwargs:
            body["params"] = kwargs["params"]

        if not body:
            raise ValueError("No update parameters provided")

        self._client._request("PUT", f"{self._endpoint}/{key}", json_data=body)
        return self.get(key)

    def delete(self, key: int) -> None:
        """Delete a command.

        Args:
            key: Command $key (ID).
        """
        self._client._request("DELETE", f"{self._endpoint}/{key}")


# =============================================================================
# BGP Route Maps
# =============================================================================


class BGPRouteMap(ResourceObject):
    """BGP route map object.

    Route maps are used to filter and modify BGP routes.
    Each route map entry has a tag, sequence number, and permit/deny action.
    """

    @property
    def tag(self) -> str:
        """Get the route map tag (name)."""
        return str(self.get("tag", ""))

    @property
    def sequence(self) -> int:
        """Get the sequence number."""
        return int(self.get("sequence", 0))

    @property
    def is_permit(self) -> bool:
        """Check if this is a permit entry (vs deny)."""
        return bool(self.get("permit", True))

    @property
    def commands(self) -> BGPRouteMapCommandManager:
        """Access commands for this route map.

        Returns:
            BGPRouteMapCommandManager for this route map.

        Examples:
            List commands::

                commands = routemap.commands.list()

            Add a match condition::

                routemap.commands.create(
                    command="match",
                    params="ip address prefix-list MY-PREFIX"
                )
        """
        manager = self._manager
        if not isinstance(manager, BGPRouteMapManager):
            raise TypeError("Manager must be BGPRouteMapManager")
        return BGPRouteMapCommandManager(manager._client, self)


class BGPRouteMapManager(ResourceManager[BGPRouteMap]):
    """Manager for BGP route maps.

    Route maps filter and modify BGP routes. Multiple entries with the
    same tag form a route map; entries are evaluated by sequence number.

    Examples:
        List route maps::

            routemaps = network.routing.bgp_route_maps.list()

        Create a route map entry::

            routemap = network.routing.bgp_route_maps.create(
                tag="IMPORT-FROM-ISP",
                sequence=10,
                permit=True
            )

        Add match/set commands::

            routemap.commands.create(command="match", params="as-path 1")
            routemap.commands.create(command="set", params="local-preference 200")
    """

    _endpoint = "vnet_bgp_routemaps"

    def __init__(self, client: VergeClient, routing_manager: NetworkRoutingManager) -> None:
        super().__init__(client)
        self._routing_manager = routing_manager

    def _to_model(self, data: dict[str, Any]) -> BGPRouteMap:
        data["_network_key"] = self._routing_manager._network.key
        return BGPRouteMap(data, self)

    def list(
        self,
        filter: str | None = None,
        fields: builtins.list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        **filter_kwargs: Any,
    ) -> builtins.list[BGPRouteMap]:
        """List route maps for this network.

        Args:
            filter: OData filter string.
            fields: List of fields to return.
            limit: Maximum number of results.
            offset: Skip this many results.
            **filter_kwargs: Shorthand filter arguments.

        Returns:
            List of BGPRouteMap objects.
        """
        bgp_key = self._routing_manager._get_bgp_config()
        if bgp_key is None:
            return []

        params: dict[str, Any] = {}

        filters = [f"bgp eq {bgp_key}"]
        if filter:
            filters.append(filter)
        params["filter"] = " and ".join(filters)

        if fields is None:
            fields = DEFAULT_BGP_ROUTEMAP_FIELDS.copy()
        params["fields"] = ",".join(fields)

        params["sort"] = "tag,sequence"

        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset

        response = self._client._request("GET", self._endpoint, params=params)

        if response is None:
            return []
        if not isinstance(response, builtins.list):
            return [self._to_model(response)]
        return [self._to_model(item) for item in response]

    def get(  # type: ignore[override]
        self,
        key: int | None = None,
        *,
        tag: str | None = None,
        sequence: int | None = None,
        fields: builtins.list[str] | None = None,
    ) -> BGPRouteMap:
        """Get a single route map by key or tag+sequence.

        Args:
            key: Route map $key (ID).
            tag: Route map tag (use with sequence).
            sequence: Sequence number (use with tag).
            fields: List of fields to return.

        Returns:
            BGPRouteMap object.

        Raises:
            NotFoundError: If route map not found.
            ValueError: If invalid parameters.
        """
        if fields is None:
            fields = DEFAULT_BGP_ROUTEMAP_FIELDS.copy()

        if key is not None:
            params: dict[str, Any] = {"fields": ",".join(fields)}
            response = self._client._request("GET", f"{self._endpoint}/{key}", params=params)
            if response is None:
                raise NotFoundError(f"BGP route map with key {key} not found")
            if not isinstance(response, dict):
                raise NotFoundError(f"BGP route map {key} returned invalid response")
            return self._to_model(response)

        if tag is not None and sequence is not None:
            escaped_tag = tag.replace("'", "''")
            results = self.list(
                filter=f"tag eq '{escaped_tag}' and sequence eq {sequence}",
                fields=fields,
            )
            if not results:
                raise NotFoundError(
                    f"BGP route map with tag '{tag}' and sequence {sequence} not found"
                )
            return results[0]

        raise ValueError("Either key or (tag and sequence) must be provided")

    def create(  # type: ignore[override]
        self,
        tag: str,
        sequence: int,
        *,
        permit: bool = True,
    ) -> BGPRouteMap:
        """Create a new route map entry.

        Args:
            tag: Route map tag/name.
            sequence: Sequence number (1-65535).
            permit: Whether this is a permit (True) or deny (False) entry.

        Returns:
            Created BGPRouteMap object.

        Examples:
            Create a permit entry::

                routemap = network.routing.bgp_route_maps.create(
                    tag="IMPORT-FROM-ISP",
                    sequence=10,
                    permit=True
                )

            Create a deny entry::

                routemap = network.routing.bgp_route_maps.create(
                    tag="BLOCK-PRIVATE",
                    sequence=10,
                    permit=False
                )
        """
        bgp_key = self._routing_manager._get_or_create_bgp_config()

        body: dict[str, Any] = {
            "bgp": bgp_key,
            "tag": tag,
            "sequence": sequence,
            "permit": permit,
        }

        response = self._client._request("POST", self._endpoint, json_data=body)
        if response is None or not isinstance(response, dict):
            raise ValueError("No response from create operation")

        routemap_key = response.get("$key")
        if routemap_key is None:
            raise ValueError("Create response missing $key")

        return self.get(int(routemap_key))

    def update(self, key: int, **kwargs: Any) -> BGPRouteMap:
        """Update an existing route map.

        Args:
            key: Route map $key (ID).
            **kwargs: Attributes to update (tag, sequence, permit).

        Returns:
            Updated BGPRouteMap object.
        """
        body: dict[str, Any] = {}

        if "tag" in kwargs:
            body["tag"] = kwargs["tag"]
        if "sequence" in kwargs:
            body["sequence"] = kwargs["sequence"]
        if "permit" in kwargs:
            body["permit"] = kwargs["permit"]

        if not body:
            raise ValueError("No update parameters provided")

        self._client._request("PUT", f"{self._endpoint}/{key}", json_data=body)
        return self.get(key)

    def delete(self, key: int) -> None:
        """Delete a route map entry.

        This also removes all associated commands.

        Args:
            key: Route map $key (ID).
        """
        self._client._request("DELETE", f"{self._endpoint}/{key}")


# =============================================================================
# BGP IP Commands (prefix-list, as-path, etc.)
# =============================================================================


class BGPIPCommand(ResourceObject):
    """BGP IP command object.

    IP commands configure prefix lists, AS path lists, community lists,
    and other IP-level BGP settings.
    """

    @property
    def command_type(self) -> str:
        """Get the command type (prefix-list, as-path, etc.)."""
        return str(self.get("command", ""))

    @property
    def params(self) -> str:
        """Get the command parameters."""
        return str(self.get("params", ""))

    @property
    def order_id(self) -> int:
        """Get the command order ID."""
        return int(self.get("orderid", 0))


class BGPIPCommandManager(ResourceManager[BGPIPCommand]):
    """Manager for BGP IP commands.

    IP commands configure prefix lists, AS path access lists, community lists,
    and other IP-level BGP configuration.

    Examples:
        List IP commands::

            commands = network.routing.bgp_ip_commands.list()

        Create a prefix list::

            network.routing.bgp_ip_commands.create(
                command="prefix-list",
                params="MY-PREFIXES seq 10 permit 10.0.0.0/8 le 24"
            )

        Create an AS path access list::

            network.routing.bgp_ip_commands.create(
                command="as-path",
                params="access-list 1 permit ^65001$"
            )
    """

    _endpoint = "vnet_bgp_ip"

    def __init__(self, client: VergeClient, routing_manager: NetworkRoutingManager) -> None:
        super().__init__(client)
        self._routing_manager = routing_manager

    def _to_model(self, data: dict[str, Any]) -> BGPIPCommand:
        data["_network_key"] = self._routing_manager._network.key
        return BGPIPCommand(data, self)

    def list(
        self,
        filter: str | None = None,
        fields: builtins.list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        **filter_kwargs: Any,
    ) -> builtins.list[BGPIPCommand]:
        """List IP commands for this network.

        Args:
            filter: OData filter string.
            fields: List of fields to return.
            limit: Maximum number of results.
            offset: Skip this many results.
            **filter_kwargs: Shorthand filter arguments.

        Returns:
            List of BGPIPCommand objects.
        """
        bgp_key = self._routing_manager._get_bgp_config()
        if bgp_key is None:
            return []

        params: dict[str, Any] = {}

        filters = [f"bgp eq {bgp_key}"]
        if filter:
            filters.append(filter)
        params["filter"] = " and ".join(filters)

        if fields is None:
            fields = DEFAULT_BGP_IP_FIELDS.copy()
        params["fields"] = ",".join(fields)

        params["sort"] = "orderid"

        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset

        response = self._client._request("GET", self._endpoint, params=params)

        if response is None:
            return []
        if not isinstance(response, builtins.list):
            return [self._to_model(response)]
        return [self._to_model(item) for item in response]

    def get(  # type: ignore[override]
        self,
        key: int | None = None,
        *,
        fields: builtins.list[str] | None = None,
    ) -> BGPIPCommand:
        """Get a single IP command by key.

        Args:
            key: Command $key (ID).
            fields: List of fields to return.

        Returns:
            BGPIPCommand object.

        Raises:
            NotFoundError: If command not found.
            ValueError: If key not provided.
        """
        if key is None:
            raise ValueError("Key must be provided")

        if fields is None:
            fields = DEFAULT_BGP_IP_FIELDS.copy()

        params: dict[str, Any] = {"fields": ",".join(fields)}
        response = self._client._request("GET", f"{self._endpoint}/{key}", params=params)
        if response is None:
            raise NotFoundError(f"BGP IP command with key {key} not found")
        if not isinstance(response, dict):
            raise NotFoundError(f"BGP IP command {key} returned invalid response")
        return self._to_model(response)

    def create(  # type: ignore[override]
        self,
        command: BGPIPCommandType,
        params: str,
    ) -> BGPIPCommand:
        """Create a new IP command.

        Args:
            command: Command type (prefix-list, as-path, community-list, etc.).
            params: Command parameters.

        Returns:
            Created BGPIPCommand object.

        Examples:
            Create a prefix list::

                cmd = network.routing.bgp_ip_commands.create(
                    command="prefix-list",
                    params="MY-PREFIXES seq 10 permit 10.0.0.0/8 le 24"
                )

            Create an AS path access list::

                cmd = network.routing.bgp_ip_commands.create(
                    command="as-path",
                    params="access-list 1 permit ^65001$"
                )

            Create a community list::

                cmd = network.routing.bgp_ip_commands.create(
                    command="community-list",
                    params="standard COMMUNITY-1 permit 65000:100"
                )
        """
        bgp_key = self._routing_manager._get_or_create_bgp_config()

        body: dict[str, Any] = {
            "bgp": bgp_key,
            "command": command,
            "params": params,
        }

        response = self._client._request("POST", self._endpoint, json_data=body)
        if response is None or not isinstance(response, dict):
            raise ValueError("No response from create operation")

        cmd_key = response.get("$key")
        if cmd_key is None:
            raise ValueError("Create response missing $key")

        return self.get(int(cmd_key))

    def update(self, key: int, **kwargs: Any) -> BGPIPCommand:
        """Update an existing IP command.

        Args:
            key: Command $key (ID).
            **kwargs: Attributes to update (command, params).

        Returns:
            Updated BGPIPCommand object.
        """
        body: dict[str, Any] = {}

        if "command" in kwargs:
            body["command"] = kwargs["command"]
        if "params" in kwargs:
            body["params"] = kwargs["params"]

        if not body:
            raise ValueError("No update parameters provided")

        self._client._request("PUT", f"{self._endpoint}/{key}", json_data=body)
        return self.get(key)

    def delete(self, key: int) -> None:
        """Delete an IP command.

        Args:
            key: Command $key (ID).
        """
        self._client._request("DELETE", f"{self._endpoint}/{key}")


# =============================================================================
# OSPF Commands
# =============================================================================


class OSPFCommand(ResourceObject):
    """OSPF command object.

    OSPF commands configure the OSPF routing protocol including
    areas, networks, redistribution, and timers.
    """

    @property
    def command_type(self) -> str:
        """Get the command type (area, network, redistribute, etc.)."""
        return str(self.get("command", ""))

    @property
    def params(self) -> str:
        """Get the command parameters."""
        return str(self.get("params", ""))

    @property
    def order_id(self) -> int:
        """Get the command order ID."""
        return int(self.get("orderid", 0))


class OSPFCommandManager(ResourceManager[OSPFCommand]):
    """Manager for OSPF commands.

    OSPF commands configure the OSPF routing protocol including
    areas, networks, redistribution, router ID, and timers.

    Examples:
        List OSPF commands::

            commands = network.routing.ospf_commands.list()

        Set router ID::

            network.routing.ospf_commands.create(
                command="router-id",
                params="1.1.1.1"
            )

        Add network to OSPF::

            network.routing.ospf_commands.create(
                command="network",
                params="10.0.0.0/24 area 0"
            )

        Configure an area::

            network.routing.ospf_commands.create(
                command="area",
                params="0 authentication message-digest"
            )
    """

    _endpoint = "vnet_ospf_commands"

    def __init__(self, client: VergeClient, routing_manager: NetworkRoutingManager) -> None:
        super().__init__(client)
        self._routing_manager = routing_manager

    def _to_model(self, data: dict[str, Any]) -> OSPFCommand:
        data["_network_key"] = self._routing_manager._network.key
        return OSPFCommand(data, self)

    def list(
        self,
        filter: str | None = None,
        fields: builtins.list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        **filter_kwargs: Any,
    ) -> builtins.list[OSPFCommand]:
        """List OSPF commands for this network.

        Args:
            filter: OData filter string.
            fields: List of fields to return.
            limit: Maximum number of results.
            offset: Skip this many results.
            **filter_kwargs: Shorthand filter arguments.

        Returns:
            List of OSPFCommand objects.
        """
        bgp_key = self._routing_manager._get_bgp_config()
        if bgp_key is None:
            return []

        params: dict[str, Any] = {}

        filters = [f"bgp eq {bgp_key}"]
        if filter:
            filters.append(filter)
        params["filter"] = " and ".join(filters)

        if fields is None:
            fields = DEFAULT_OSPF_COMMAND_FIELDS.copy()
        params["fields"] = ",".join(fields)

        params["sort"] = "orderid"

        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset

        response = self._client._request("GET", self._endpoint, params=params)

        if response is None:
            return []
        if not isinstance(response, builtins.list):
            return [self._to_model(response)]
        return [self._to_model(item) for item in response]

    def get(  # type: ignore[override]
        self,
        key: int | None = None,
        *,
        fields: builtins.list[str] | None = None,
    ) -> OSPFCommand:
        """Get a single OSPF command by key.

        Args:
            key: Command $key (ID).
            fields: List of fields to return.

        Returns:
            OSPFCommand object.

        Raises:
            NotFoundError: If command not found.
            ValueError: If key not provided.
        """
        if key is None:
            raise ValueError("Key must be provided")

        if fields is None:
            fields = DEFAULT_OSPF_COMMAND_FIELDS.copy()

        params: dict[str, Any] = {"fields": ",".join(fields)}
        response = self._client._request("GET", f"{self._endpoint}/{key}", params=params)
        if response is None:
            raise NotFoundError(f"OSPF command with key {key} not found")
        if not isinstance(response, dict):
            raise NotFoundError(f"OSPF command {key} returned invalid response")
        return self._to_model(response)

    def create(  # type: ignore[override]
        self,
        command: OSPFCommandType,
        params: str,
    ) -> OSPFCommand:
        """Create a new OSPF command.

        Args:
            command: Command type (area, network, redistribute, etc.).
            params: Command parameters.

        Returns:
            Created OSPFCommand object.

        Examples:
            Set router ID::

                cmd = network.routing.ospf_commands.create(
                    command="router-id",
                    params="1.1.1.1"
                )

            Add network to OSPF area 0::

                cmd = network.routing.ospf_commands.create(
                    command="network",
                    params="10.0.0.0/24 area 0"
                )

            Configure area authentication::

                cmd = network.routing.ospf_commands.create(
                    command="area",
                    params="0 authentication message-digest"
                )

            Redistribute BGP routes::

                cmd = network.routing.ospf_commands.create(
                    command="redistribute",
                    params="bgp metric 100"
                )

            Set passive interface::

                cmd = network.routing.ospf_commands.create(
                    command="passive-interface",
                    params="default"
                )
        """
        bgp_key = self._routing_manager._get_or_create_bgp_config()

        body: dict[str, Any] = {
            "bgp": bgp_key,
            "command": command,
            "params": params,
        }

        response = self._client._request("POST", self._endpoint, json_data=body)
        if response is None or not isinstance(response, dict):
            raise ValueError("No response from create operation")

        cmd_key = response.get("$key")
        if cmd_key is None:
            raise ValueError("Create response missing $key")

        return self.get(int(cmd_key))

    def update(self, key: int, **kwargs: Any) -> OSPFCommand:
        """Update an existing OSPF command.

        Args:
            key: Command $key (ID).
            **kwargs: Attributes to update (command, params).

        Returns:
            Updated OSPFCommand object.
        """
        body: dict[str, Any] = {}

        if "command" in kwargs:
            body["command"] = kwargs["command"]
        if "params" in kwargs:
            body["params"] = kwargs["params"]

        if not body:
            raise ValueError("No update parameters provided")

        self._client._request("PUT", f"{self._endpoint}/{key}", json_data=body)
        return self.get(key)

    def delete(self, key: int) -> None:
        """Delete an OSPF command.

        Args:
            key: Command $key (ID).
        """
        self._client._request("DELETE", f"{self._endpoint}/{key}")


# =============================================================================
# EIGRP Router Commands
# =============================================================================


class EIGRPRouterCommand(ResourceObject):
    """EIGRP router command object."""

    @property
    def command_type(self) -> str:
        """Get the command type (network, redistribute, etc.)."""
        return str(self.get("command", ""))

    @property
    def params(self) -> str:
        """Get the command parameters."""
        return str(self.get("params", ""))

    @property
    def is_enabled(self) -> bool:
        """Check if the command is enabled."""
        return bool(self.get("enabled", True))

    @property
    def is_negated(self) -> bool:
        """Check if the command is negated (no prefix)."""
        return bool(self.get("no", False))

    @property
    def order_id(self) -> int:
        """Get the command order ID."""
        return int(self.get("orderid", 0))


class EIGRPRouterCommandManager(ResourceManager[EIGRPRouterCommand]):
    """Manager for EIGRP router commands.

    Commands configure EIGRP router behavior including networks,
    redistribution, metrics, and neighbors.

    Examples:
        List commands::

            commands = router.commands.list()

        Add a network::

            router.commands.create(
                command="network",
                params="10.0.0.0/24"
            )

        Redistribute OSPF::

            router.commands.create(
                command="redistribute",
                params="ospf"
            )
    """

    _endpoint = "vnet_eigrp_router_commands"

    def __init__(self, client: VergeClient, router: EIGRPRouter) -> None:
        super().__init__(client)
        self._router = router

    def _to_model(self, data: dict[str, Any]) -> EIGRPRouterCommand:
        data["_router_key"] = self._router.key
        return EIGRPRouterCommand(data, self)

    def list(
        self,
        filter: str | None = None,
        fields: builtins.list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        **filter_kwargs: Any,
    ) -> builtins.list[EIGRPRouterCommand]:
        """List commands for this EIGRP router.

        Args:
            filter: OData filter string.
            fields: List of fields to return.
            limit: Maximum number of results.
            offset: Skip this many results.
            **filter_kwargs: Shorthand filter arguments.

        Returns:
            List of EIGRPRouterCommand objects.
        """
        params: dict[str, Any] = {}

        filters = [f"eigrp_router eq {self._router.key}"]
        if filter:
            filters.append(filter)
        params["filter"] = " and ".join(filters)

        if fields is None:
            fields = DEFAULT_EIGRP_ROUTER_COMMAND_FIELDS.copy()
        params["fields"] = ",".join(fields)

        params["sort"] = "orderid"

        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset

        response = self._client._request("GET", self._endpoint, params=params)

        if response is None:
            return []
        if not isinstance(response, builtins.list):
            return [self._to_model(response)]
        return [self._to_model(item) for item in response]

    def get(  # type: ignore[override]
        self,
        key: int | None = None,
        *,
        fields: builtins.list[str] | None = None,
    ) -> EIGRPRouterCommand:
        """Get a single command by key.

        Args:
            key: Command $key (ID).
            fields: List of fields to return.

        Returns:
            EIGRPRouterCommand object.

        Raises:
            NotFoundError: If command not found.
            ValueError: If key not provided.
        """
        if key is None:
            raise ValueError("Key must be provided")

        if fields is None:
            fields = DEFAULT_EIGRP_ROUTER_COMMAND_FIELDS.copy()

        params: dict[str, Any] = {"fields": ",".join(fields)}
        response = self._client._request("GET", f"{self._endpoint}/{key}", params=params)
        if response is None:
            raise NotFoundError(f"EIGRP router command with key {key} not found")
        if not isinstance(response, dict):
            raise NotFoundError(f"EIGRP router command {key} returned invalid response")
        return self._to_model(response)

    def create(  # type: ignore[override]
        self,
        command: EIGRPRouterCommandType,
        params: str,
        *,
        enabled: bool = True,
        negate: bool = False,
    ) -> EIGRPRouterCommand:
        """Create a new EIGRP router command.

        Args:
            command: Command type (network, redistribute, metric, etc.).
            params: Command parameters.
            enabled: Whether the command is enabled.
            negate: Whether to negate the command (no prefix).

        Returns:
            Created EIGRPRouterCommand object.

        Examples:
            Add a network::

                cmd = router.commands.create(
                    command="network",
                    params="10.0.0.0/24"
                )

            Redistribute OSPF::

                cmd = router.commands.create(
                    command="redistribute",
                    params="ospf"
                )

            Set variance::

                cmd = router.commands.create(
                    command="variance",
                    params="2"
                )
        """
        body: dict[str, Any] = {
            "eigrp_router": self._router.key,
            "command": command,
            "params": params,
            "enabled": enabled,
            "no": negate,
        }

        response = self._client._request("POST", self._endpoint, json_data=body)
        if response is None or not isinstance(response, dict):
            raise ValueError("No response from create operation")

        cmd_key = response.get("$key")
        if cmd_key is None:
            raise ValueError("Create response missing $key")

        return self.get(int(cmd_key))

    def update(self, key: int, **kwargs: Any) -> EIGRPRouterCommand:
        """Update an existing command.

        Args:
            key: Command $key (ID).
            **kwargs: Attributes to update (command, params, enabled, negate).

        Returns:
            Updated EIGRPRouterCommand object.
        """
        body: dict[str, Any] = {}

        field_mapping = {
            "command": "command",
            "params": "params",
            "enabled": "enabled",
            "negate": "no",
        }

        for kwarg, api_field in field_mapping.items():
            if kwarg in kwargs:
                body[api_field] = kwargs[kwarg]

        if not body:
            raise ValueError("No update parameters provided")

        self._client._request("PUT", f"{self._endpoint}/{key}", json_data=body)
        return self.get(key)

    def delete(self, key: int) -> None:
        """Delete a command.

        Args:
            key: Command $key (ID).
        """
        self._client._request("DELETE", f"{self._endpoint}/{key}")


# =============================================================================
# EIGRP Routers
# =============================================================================


class EIGRPRouter(ResourceObject):
    """EIGRP router object.

    An EIGRP router defines an autonomous system number (ASN) and contains
    commands for configuring networks, redistribution, and other settings.
    """

    @property
    def asn(self) -> int:
        """Get the Autonomous System Number."""
        return int(self.get("asn", 0))

    @property
    def commands(self) -> EIGRPRouterCommandManager:
        """Access commands for this EIGRP router.

        Returns:
            EIGRPRouterCommandManager for this router.

        Examples:
            List commands::

                commands = router.commands.list()

            Add a network::

                router.commands.create(
                    command="network",
                    params="10.0.0.0/24"
                )
        """
        manager = self._manager
        if not isinstance(manager, EIGRPRouterManager):
            raise TypeError("Manager must be EIGRPRouterManager")
        return EIGRPRouterCommandManager(manager._client, self)


class EIGRPRouterManager(ResourceManager[EIGRPRouter]):
    """Manager for EIGRP routers.

    EIGRP (Enhanced Interior Gateway Routing Protocol) is a Cisco-developed
    routing protocol. EIGRP routers define the AS number and contain
    configuration for networks, redistribution, and metrics.

    Examples:
        List EIGRP routers::

            routers = network.routing.eigrp_routers.list()

        Create an EIGRP router::

            router = network.routing.eigrp_routers.create(asn=100)

        Add a network::

            router.commands.create(
                command="network",
                params="10.0.0.0/24"
            )
    """

    _endpoint = "vnet_eigrp_routers"

    def __init__(self, client: VergeClient, routing_manager: NetworkRoutingManager) -> None:
        super().__init__(client)
        self._routing_manager = routing_manager

    def _to_model(self, data: dict[str, Any]) -> EIGRPRouter:
        data["_network_key"] = self._routing_manager._network.key
        return EIGRPRouter(data, self)

    def list(
        self,
        filter: str | None = None,
        fields: builtins.list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        **filter_kwargs: Any,
    ) -> builtins.list[EIGRPRouter]:
        """List EIGRP routers for this network.

        Args:
            filter: OData filter string.
            fields: List of fields to return.
            limit: Maximum number of results.
            offset: Skip this many results.
            **filter_kwargs: Shorthand filter arguments.

        Returns:
            List of EIGRPRouter objects.
        """
        bgp_key = self._routing_manager._get_bgp_config()
        if bgp_key is None:
            return []

        params: dict[str, Any] = {}

        filters = [f"bgp eq {bgp_key}"]
        if filter:
            filters.append(filter)
        params["filter"] = " and ".join(filters)

        if fields is None:
            fields = DEFAULT_EIGRP_ROUTER_FIELDS.copy()
        params["fields"] = ",".join(fields)

        params["sort"] = "asn"

        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset

        response = self._client._request("GET", self._endpoint, params=params)

        if response is None:
            return []
        if not isinstance(response, builtins.list):
            return [self._to_model(response)]
        return [self._to_model(item) for item in response]

    def get(  # type: ignore[override]
        self,
        key: int | None = None,
        *,
        asn: int | None = None,
        fields: builtins.list[str] | None = None,
    ) -> EIGRPRouter:
        """Get a single EIGRP router by key or ASN.

        Args:
            key: Router $key (ID).
            asn: Autonomous System Number.
            fields: List of fields to return.

        Returns:
            EIGRPRouter object.

        Raises:
            NotFoundError: If router not found.
            ValueError: If neither key nor asn provided.
        """
        if fields is None:
            fields = DEFAULT_EIGRP_ROUTER_FIELDS.copy()

        if key is not None:
            params: dict[str, Any] = {"fields": ",".join(fields)}
            response = self._client._request("GET", f"{self._endpoint}/{key}", params=params)
            if response is None:
                raise NotFoundError(f"EIGRP router with key {key} not found")
            if not isinstance(response, dict):
                raise NotFoundError(f"EIGRP router {key} returned invalid response")
            return self._to_model(response)

        if asn is not None:
            results = self.list(filter=f"asn eq {asn}", fields=fields)
            if not results:
                raise NotFoundError(f"EIGRP router with ASN {asn} not found")
            return results[0]

        raise ValueError("Either key or asn must be provided")

    def create(  # type: ignore[override]
        self,
        asn: int,
    ) -> EIGRPRouter:
        """Create a new EIGRP router.

        Args:
            asn: Autonomous System Number (1-65535).

        Returns:
            Created EIGRPRouter object.

        Examples:
            Create an EIGRP router::

                router = network.routing.eigrp_routers.create(asn=100)
        """
        bgp_key = self._routing_manager._get_or_create_bgp_config()

        body: dict[str, Any] = {
            "bgp": bgp_key,
            "asn": asn,
        }

        response = self._client._request("POST", self._endpoint, json_data=body)
        if response is None or not isinstance(response, dict):
            raise ValueError("No response from create operation")

        router_key = response.get("$key")
        if router_key is None:
            raise ValueError("Create response missing $key")

        return self.get(int(router_key))

    def update(self, key: int, **kwargs: Any) -> EIGRPRouter:
        """Update an existing EIGRP router.

        Args:
            key: Router $key (ID).
            **kwargs: Attributes to update (asn).

        Returns:
            Updated EIGRPRouter object.
        """
        body: dict[str, Any] = {}

        if "asn" in kwargs:
            body["asn"] = kwargs["asn"]

        if not body:
            raise ValueError("No update parameters provided")

        self._client._request("PUT", f"{self._endpoint}/{key}", json_data=body)
        return self.get(key)

    def delete(self, key: int) -> None:
        """Delete an EIGRP router.

        This also removes all associated commands.

        Args:
            key: Router $key (ID).
        """
        self._client._request("DELETE", f"{self._endpoint}/{key}")


# =============================================================================
# Network Routing Manager (main entry point)
# =============================================================================


class NetworkRoutingManager:
    """Manager for network routing protocols (BGP, OSPF, EIGRP).

    This is the main entry point for configuring dynamic routing protocols
    on a VergeOS virtual network.

    Examples:
        Access routing configuration::

            routing = network.routing

        Configure BGP::

            # Create a BGP router
            bgp = routing.bgp_routers.create(asn=65000)

            # Add a neighbor
            bgp.commands.create(
                command="neighbor",
                params="192.168.1.1 remote-as 65001"
            )

            # Advertise networks
            bgp.commands.create(
                command="network",
                params="10.0.0.0/24"
            )

        Configure OSPF::

            # Set router ID
            routing.ospf_commands.create(
                command="router-id",
                params="1.1.1.1"
            )

            # Add network to area 0
            routing.ospf_commands.create(
                command="network",
                params="10.0.0.0/24 area 0"
            )

        Configure EIGRP::

            # Create an EIGRP router
            eigrp = routing.eigrp_routers.create(asn=100)

            # Add network
            eigrp.commands.create(
                command="network",
                params="10.0.0.0/24"
            )

    Note:
        Routing configuration changes require restarting the network
        for changes to take effect.
    """

    def __init__(self, client: VergeClient, network: Network) -> None:
        self._client = client
        self._network = network
        self._bgp_key: int | None = None

    def _get_or_create_bgp_config(self) -> int:
        """Get or create the BGP configuration for this network.

        Returns:
            The $key of the vnet_bgp record.

        Raises:
            ValueError: If unable to create BGP configuration.
        """
        if self._bgp_key is not None:
            return self._bgp_key

        # Query for existing BGP config
        params = {
            "filter": f"vnet eq {self._network.key}",
            "fields": "$key",
        }
        response = self._client._request("GET", "vnet_bgp", params=params)

        if response:
            if isinstance(response, builtins.list) and response:
                key_val = response[0].get("$key")
                if key_val is not None:
                    self._bgp_key = int(key_val)
            elif isinstance(response, dict) and response.get("$key"):
                key_val = response.get("$key")
                if key_val is not None:
                    self._bgp_key = int(key_val)

        if self._bgp_key is not None:
            return self._bgp_key

        # Create new BGP config
        body = {
            "vnet": self._network.key,
        }
        create_response = self._client._request("POST", "vnet_bgp", json_data=body)

        if not create_response or not isinstance(create_response, dict):
            raise ValueError("Failed to create BGP configuration for network")

        key_val = create_response.get("$key")
        if key_val is None:
            raise ValueError("BGP configuration created but no $key returned")
        self._bgp_key = int(key_val)

        return self._bgp_key

    def _get_bgp_config(self) -> int | None:
        """Get the BGP configuration key if it exists.

        Returns:
            The $key of the vnet_bgp record, or None if not configured.
        """
        if self._bgp_key is not None:
            return self._bgp_key

        params = {
            "filter": f"vnet eq {self._network.key}",
            "fields": "$key",
        }
        response = self._client._request("GET", "vnet_bgp", params=params)

        if response:
            if isinstance(response, builtins.list) and response:
                key_val = response[0].get("$key")
                if key_val is not None:
                    self._bgp_key = int(key_val)
            elif isinstance(response, dict) and response.get("$key"):
                key_val = response.get("$key")
                if key_val is not None:
                    self._bgp_key = int(key_val)

        return self._bgp_key

    @property
    def bgp_routers(self) -> BGPRouterManager:
        """Access BGP routers for this network.

        Returns:
            BGPRouterManager for this network.

        Examples:
            List BGP routers::

                routers = network.routing.bgp_routers.list()

            Create a router::

                router = network.routing.bgp_routers.create(asn=65000)
        """
        return BGPRouterManager(self._client, self)

    @property
    def bgp_interfaces(self) -> BGPInterfaceManager:
        """Access BGP interfaces for this network.

        Returns:
            BGPInterfaceManager for this network.

        Examples:
            List interfaces::

                interfaces = network.routing.bgp_interfaces.list()

            Create an interface::

                interface = network.routing.bgp_interfaces.create(
                    name="peer-1",
                    ip_address="10.255.0.1",
                    network="10.255.0.0/30",
                    interface_network=external.key
                )
        """
        return BGPInterfaceManager(self._client, self)

    @property
    def bgp_route_maps(self) -> BGPRouteMapManager:
        """Access BGP route maps for this network.

        Returns:
            BGPRouteMapManager for this network.

        Examples:
            List route maps::

                maps = network.routing.bgp_route_maps.list()

            Create a route map::

                rmap = network.routing.bgp_route_maps.create(
                    tag="IMPORT",
                    sequence=10,
                    permit=True
                )
        """
        return BGPRouteMapManager(self._client, self)

    @property
    def bgp_ip_commands(self) -> BGPIPCommandManager:
        """Access BGP IP commands (prefix-lists, as-path lists, etc.).

        Returns:
            BGPIPCommandManager for this network.

        Examples:
            Create a prefix list::

                network.routing.bgp_ip_commands.create(
                    command="prefix-list",
                    params="MY-PREFIX seq 10 permit 10.0.0.0/8 le 24"
                )
        """
        return BGPIPCommandManager(self._client, self)

    @property
    def ospf_commands(self) -> OSPFCommandManager:
        """Access OSPF commands for this network.

        Returns:
            OSPFCommandManager for this network.

        Examples:
            Set router ID::

                network.routing.ospf_commands.create(
                    command="router-id",
                    params="1.1.1.1"
                )

            Add network to OSPF::

                network.routing.ospf_commands.create(
                    command="network",
                    params="10.0.0.0/24 area 0"
                )
        """
        return OSPFCommandManager(self._client, self)

    @property
    def eigrp_routers(self) -> EIGRPRouterManager:
        """Access EIGRP routers for this network.

        Returns:
            EIGRPRouterManager for this network.

        Examples:
            List EIGRP routers::

                routers = network.routing.eigrp_routers.list()

            Create a router::

                router = network.routing.eigrp_routers.create(asn=100)
        """
        return EIGRPRouterManager(self._client, self)

    @property
    def is_configured(self) -> bool:
        """Check if routing is configured for this network.

        Returns:
            True if a vnet_bgp record exists for this network.
        """
        return self._get_bgp_config() is not None

    def delete_config(self) -> None:
        """Delete all routing configuration for this network.

        This removes the vnet_bgp record and all associated resources
        (BGP routers, interfaces, route maps, OSPF commands, EIGRP routers).

        Warning:
            This is a destructive operation that removes all routing
            configuration for the network.
        """
        bgp_key = self._get_bgp_config()
        if bgp_key is not None:
            self._client._request("DELETE", f"vnet_bgp/{bgp_key}")
            self._bgp_key = None
