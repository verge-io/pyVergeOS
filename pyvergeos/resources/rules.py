"""Network firewall rule resource manager."""

from __future__ import annotations

import builtins
from typing import TYPE_CHECKING, Any, Literal

from pyvergeos.exceptions import NotFoundError, ValidationError
from pyvergeos.resources.base import ResourceManager, ResourceObject

if TYPE_CHECKING:
    from pyvergeos.client import VergeClient
    from pyvergeos.resources.networks import Network

# Type aliases for rule configuration
Direction = Literal["incoming", "outgoing"]
Action = Literal["accept", "drop", "reject", "translate", "route"]
Protocol = Literal["tcp", "udp", "tcpudp", "icmp", "any"]
Interface = Literal["auto", "router", "dmz", "wireguard", "any"]
PinPosition = Literal["top", "bottom"]

# Default fields for comprehensive rule data
RULE_DEFAULT_FIELDS = [
    "$key",
    "vnet",
    "vnet#name as vnet_name",
    "name",
    "description",
    "enabled",
    "orderid",
    "pin",
    "direction",
    "action",
    "protocol",
    "interface",
    "source_ip",
    "source_ports",
    "destination_ip",
    "destination_ports",
    "target_ip",
    "target_ports",
    "ct_state",
    "statistics",
    "log",
    "trace",
    "throttle",
    "drop_throttle",
    "packets",
    "bytes",
    "system_rule",
    "modified",
]


class NetworkRule(ResourceObject):
    """Network firewall rule resource object."""

    @property
    def network_key(self) -> int:
        """Get the network key this rule belongs to."""
        vnet = self.get("vnet")
        if vnet is None:
            raise ValueError("Rule has no network (vnet) key")
        return int(vnet)

    @property
    def network_name(self) -> str | None:
        """Get the network name this rule belongs to."""
        return self.get("vnet_name")

    @property
    def is_enabled(self) -> bool:
        """Check if rule is enabled."""
        return bool(self.get("enabled", True))

    @property
    def is_system_rule(self) -> bool:
        """Check if this is a system rule (cannot be modified/deleted)."""
        return bool(self.get("system_rule", False))

    @property
    def order(self) -> int:
        """Get rule order position."""
        return int(self.get("orderid", 0))

    @property
    def direction(self) -> str:
        """Get rule direction (incoming/outgoing)."""
        return str(self.get("direction", "incoming"))

    @property
    def action(self) -> str:
        """Get rule action (accept/drop/reject/translate/route)."""
        return str(self.get("action", "accept"))

    @property
    def protocol(self) -> str:
        """Get rule protocol (tcp/udp/tcpudp/icmp/any)."""
        return str(self.get("protocol", "any"))

    @property
    def source_ip(self) -> str | None:
        """Get source IP filter."""
        return self.get("source_ip")

    @property
    def source_ports(self) -> str | None:
        """Get source ports filter."""
        return self.get("source_ports")

    @property
    def destination_ip(self) -> str | None:
        """Get destination IP filter."""
        return self.get("destination_ip")

    @property
    def destination_ports(self) -> str | None:
        """Get destination ports filter."""
        return self.get("destination_ports")

    @property
    def target_ip(self) -> str | None:
        """Get target IP for translate/route actions."""
        return self.get("target_ip")

    @property
    def target_ports(self) -> str | None:
        """Get target ports for port translation."""
        return self.get("target_ports")

    @property
    def is_logging(self) -> bool:
        """Check if logging is enabled."""
        return bool(self.get("log", False))

    @property
    def has_statistics(self) -> bool:
        """Check if statistics tracking is enabled."""
        return bool(self.get("statistics", False))

    @property
    def packet_count(self) -> int:
        """Get number of packets matched by this rule."""
        return int(self.get("packets") or 0)

    @property
    def byte_count(self) -> int:
        """Get number of bytes matched by this rule."""
        return int(self.get("bytes") or 0)

    def enable(self) -> NetworkRule:
        """Enable this rule.

        Returns:
            Self for chaining.
        """
        if self.is_system_rule:
            raise ValidationError("Cannot modify system rule")
        return self.save(enabled=True)  # type: ignore[return-value]

    def disable(self) -> NetworkRule:
        """Disable this rule.

        Returns:
            Self for chaining.
        """
        if self.is_system_rule:
            raise ValidationError("Cannot modify system rule")
        return self.save(enabled=False)  # type: ignore[return-value]


class NetworkRuleManager(ResourceManager[NetworkRule]):
    """Manager for Network firewall rule operations.

    This manager is accessed through a Network object's rules property.

    Examples:
        List all rules for a network::

            rules = network.rules.list()

        List only incoming rules::

            incoming = network.rules.list(direction="incoming")

        Create a new accept rule::

            rule = network.rules.create(
                name="Allow HTTPS",
                direction="incoming",
                action="accept",
                protocol="tcp",
                destination_ports="443"
            )

        Create a NAT rule::

            rule = network.rules.create(
                name="NAT to Web Server",
                direction="incoming",
                action="translate",
                protocol="tcp",
                destination_ports="80,443",
                target_ip="192.168.1.10"
            )

        Delete a rule::

            network.rules.delete(rule.key)
    """

    _endpoint = "vnet_rules"
    _default_fields = RULE_DEFAULT_FIELDS

    def __init__(self, client: VergeClient, network: Network) -> None:
        super().__init__(client)
        self._network = network

    @property
    def network_key(self) -> int:
        """Get the network key for this manager."""
        return self._network.key

    def _to_model(self, data: dict[str, Any]) -> NetworkRule:
        return NetworkRule(data, self)

    def list(  # type: ignore[override]
        self,
        filter: str | None = None,
        fields: builtins.list[str] | None = None,
        direction: Direction | None = None,
        action: Action | None = None,
        protocol: Protocol | None = None,
        enabled: bool | None = None,
        **kwargs: Any,
    ) -> builtins.list[NetworkRule]:
        """List firewall rules for this network.

        Args:
            filter: Additional OData filter string.
            fields: List of fields to return.
            direction: Filter by direction (incoming/outgoing).
            action: Filter by action (accept/drop/reject/translate/route).
            protocol: Filter by protocol (tcp/udp/tcpudp/icmp/any).
            enabled: Filter by enabled status.
            **kwargs: Additional filter arguments.

        Returns:
            List of NetworkRule objects sorted by order.
        """
        if fields is None:
            fields = self._default_fields.copy()

        # Build filter for this network
        filters: builtins.list[str] = [f"vnet eq {self.network_key}"]

        if direction:
            filters.append(f"direction eq '{direction}'")

        if action:
            filters.append(f"action eq '{action}'")

        if protocol:
            filters.append(f"protocol eq '{protocol}'")

        if enabled is not None:
            filters.append(f"enabled eq {str(enabled).lower()}")

        if filter:
            filters.append(f"({filter})")

        combined_filter = " and ".join(filters)

        params: dict[str, Any] = {
            "filter": combined_filter,
            "fields": ",".join(fields),
            "sort": "+orderid",
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
    ) -> NetworkRule:
        """Get a rule by key or name.

        Args:
            key: Rule $key (ID).
            name: Rule name.
            fields: List of fields to return.

        Returns:
            NetworkRule object.

        Raises:
            NotFoundError: If rule not found.
            ValueError: If neither key nor name provided.
        """
        if fields is None:
            fields = self._default_fields.copy()

        if key is not None:
            params: dict[str, Any] = {"fields": ",".join(fields)}
            response = self._client._request("GET", f"{self._endpoint}/{key}", params=params)
            if response is None:
                raise NotFoundError(f"Rule {key} not found")
            if not isinstance(response, dict):
                raise NotFoundError(f"Rule {key} returned invalid response")
            return self._to_model(response)

        if name is not None:
            escaped_name = name.replace("'", "''")
            rules = self.list(filter=f"name eq '{escaped_name}'", fields=fields)
            if not rules:
                raise NotFoundError(f"Rule with name '{name}' not found on this network")
            return rules[0]

        raise ValueError("Either key or name must be provided")

    def create(  # type: ignore[override]
        self,
        name: str,
        direction: Direction = "incoming",
        action: Action = "accept",
        protocol: Protocol = "any",
        interface: Interface = "auto",
        source_ip: str | None = None,
        source_ports: str | None = None,
        destination_ip: str | None = None,
        destination_ports: str | None = None,
        target_ip: str | None = None,
        target_ports: str | None = None,
        enabled: bool = True,
        log: bool = False,
        statistics: bool = False,
        pin: PinPosition | None = None,
        order: int | None = None,
        description: str = "",
    ) -> NetworkRule:
        """Create a new firewall rule.

        Args:
            name: Rule name (must be unique within the network).
            direction: Traffic direction (incoming or outgoing).
            action: Action to take (accept, drop, reject, translate, route).
            protocol: Protocol to match (tcp, udp, tcpudp, icmp, any).
            interface: Interface for the rule (auto, router, dmz, wireguard, any).
            source_ip: Source IP filter (IP, CIDR, or special value like "vnetself").
            source_ports: Source ports (e.g., "80", "1024-65535", "80,443").
            destination_ip: Destination IP filter.
            destination_ports: Destination ports.
            target_ip: Target IP for translate/route actions.
            target_ports: Target ports for port translation.
            enabled: Enable the rule (default True).
            log: Enable logging for this rule.
            statistics: Enable statistics tracking.
            pin: Pin position ("top" or "bottom").
            order: Specific order position (alternative to pin).
            description: Rule description.

        Returns:
            Created NetworkRule object.

        Raises:
            ValidationError: If a rule with this name already exists.
        """
        body: dict[str, Any] = {
            "vnet": self.network_key,
            "name": name,
            "direction": direction,
            "action": action,
            "protocol": protocol,
            "interface": interface,
            "enabled": enabled,
            "log": log,
            "statistics": statistics,
        }

        if source_ip:
            body["source_ip"] = source_ip
        if source_ports:
            body["source_ports"] = source_ports
        if destination_ip:
            body["destination_ip"] = destination_ip
        if destination_ports:
            body["destination_ports"] = destination_ports
        if target_ip:
            body["target_ip"] = target_ip
        if target_ports:
            body["target_ports"] = target_ports
        if description:
            body["description"] = description
        if pin:
            body["pin"] = pin
        if order is not None:
            body["orderid"] = order

        response = self._client._request("POST", self._endpoint, json_data=body)
        if response is None:
            raise ValueError("No response from create operation")
        if not isinstance(response, dict):
            raise ValueError("Create operation returned invalid response")

        # Get the created rule key and fetch full data
        key = response.get("$key")
        if key is None:
            raise ValueError("Create response missing $key")

        return self.get(int(key))

    def update(self, key: int, **kwargs: Any) -> NetworkRule:
        """Update a firewall rule.

        Args:
            key: Rule $key (ID).
            **kwargs: Fields to update. Common fields:
                - name: New rule name
                - direction: incoming/outgoing
                - action: accept/drop/reject/translate/route
                - protocol: tcp/udp/tcpudp/icmp/any
                - source_ip, source_ports: Source filters
                - destination_ip, destination_ports: Destination filters
                - target_ip, target_ports: Target for translate/route
                - enabled: Enable/disable rule
                - log: Enable/disable logging
                - statistics: Enable/disable statistics

        Returns:
            Updated NetworkRule object.

        Raises:
            ValidationError: If trying to modify a system rule.
        """
        # Check if this is a system rule
        rule = self.get(key)
        if rule.is_system_rule:
            raise ValidationError("Cannot modify system rule")

        self._client._request("PUT", f"{self._endpoint}/{key}", json_data=kwargs)
        return self.get(key)

    def delete(self, key: int) -> None:
        """Delete a firewall rule.

        Args:
            key: Rule $key (ID).

        Raises:
            ValidationError: If trying to delete a system rule.

        Note:
            Rule changes are not active until network.apply_rules() is called.
        """
        # Check if this is a system rule
        rule = self.get(key)
        if rule.is_system_rule:
            raise ValidationError("Cannot delete system rule")

        self._client._request("DELETE", f"{self._endpoint}/{key}")

    def list_incoming(self) -> builtins.list[NetworkRule]:
        """List incoming rules.

        Returns:
            List of incoming rules.
        """
        return self.list(direction="incoming")

    def list_outgoing(self) -> builtins.list[NetworkRule]:
        """List outgoing rules.

        Returns:
            List of outgoing rules.
        """
        return self.list(direction="outgoing")

    def list_enabled(self) -> builtins.list[NetworkRule]:
        """List enabled rules.

        Returns:
            List of enabled rules.
        """
        return self.list(enabled=True)

    def list_disabled(self) -> builtins.list[NetworkRule]:
        """List disabled rules.

        Returns:
            List of disabled rules.
        """
        return self.list(enabled=False)
