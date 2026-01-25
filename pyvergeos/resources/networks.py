"""Virtual Network resource manager."""

from __future__ import annotations

import builtins
from typing import TYPE_CHECKING, Any

from pyvergeos.resources.base import ResourceManager, ResourceObject

if TYPE_CHECKING:
    from pyvergeos.client import VergeClient
    from pyvergeos.resources.aliases import NetworkAliasManager
    from pyvergeos.resources.dns import DNSZoneManager
    from pyvergeos.resources.hosts import NetworkHostManager
    from pyvergeos.resources.rules import NetworkRuleManager


# Default fields to request for comprehensive network data
DEFAULT_NETWORK_FIELDS = [
    "$key",
    "name",
    "description",
    "enabled",
    "type",
    "layer2_type",
    "layer2_id",
    "network",
    "ipaddress",
    "gateway",
    "mtu",
    "dhcp_enabled",
    "dhcp_start",
    "dhcp_stop",
    "dns",
    "domain",
    "need_fw_apply",
    "need_dns_apply",
    "need_restart",
    "on_power_loss",
    "interface_vnet",
    "machine#status#running as running",
    "machine#status#status as status",
]


class Network(ResourceObject):
    """Virtual Network resource object."""

    def power_on(self, apply_rules: bool = True) -> Network:
        """Power on the network.

        Args:
            apply_rules: Apply firewall rules on start.

        Returns:
            Self for chaining.
        """
        manager = self._manager
        if not isinstance(manager, NetworkManager):
            raise TypeError("Manager must be NetworkManager")
        manager._power_action(self.key, "poweron", apply=apply_rules)
        return self

    def power_off(self, force: bool = False) -> Network:
        """Power off the network.

        Args:
            force: Force immediate power off (killpower) instead of graceful.

        Returns:
            Self for chaining.
        """
        manager = self._manager
        if not isinstance(manager, NetworkManager):
            raise TypeError("Manager must be NetworkManager")
        action = "killpower" if force else "poweroff"
        manager._power_action(self.key, action)
        return self

    def restart(self, apply_rules: bool = True) -> Network:
        """Restart the network.

        Args:
            apply_rules: Apply firewall rules on restart.

        Returns:
            Self for chaining.
        """
        manager = self._manager
        if not isinstance(manager, NetworkManager):
            raise TypeError("Manager must be NetworkManager")
        manager._power_action(self.key, "reset", apply=apply_rules)
        return self

    # Alias for backwards compatibility
    reset = restart

    def apply_rules(self) -> Network:
        """Apply firewall rules.

        Returns:
            Self for chaining.
        """
        self._manager._client._request("PUT", f"vnets/{self.key}/apply")
        return self

    def apply_dns(self) -> Network:
        """Apply DNS configuration.

        Returns:
            Self for chaining.
        """
        self._manager._client._request("PUT", f"vnets/{self.key}/applydns")
        return self

    @property
    def is_running(self) -> bool:
        """Check if network is powered on."""
        return bool(self.get("running", False))

    @property
    def status(self) -> str:
        """Get the network status (running, stopped, etc.)."""
        return str(self.get("status", "unknown"))

    @property
    def needs_restart(self) -> bool:
        """Check if network needs restart to apply changes."""
        return bool(self.get("need_restart", False))

    @property
    def needs_rule_apply(self) -> bool:
        """Check if firewall rules need to be applied."""
        return bool(self.get("need_fw_apply", False))

    @property
    def needs_dns_apply(self) -> bool:
        """Check if DNS configuration needs to be applied."""
        return bool(self.get("need_dns_apply", False))

    @property
    def rules(self) -> NetworkRuleManager:
        """Access firewall rules for this network.

        Returns:
            NetworkRuleManager for this network.

        Examples:
            List all rules::

                rules = network.rules.list()

            Create a rule::

                rule = network.rules.create(
                    name="Allow HTTPS",
                    direction="incoming",
                    action="accept",
                    protocol="tcp",
                    destination_ports="443"
                )
        """
        from pyvergeos.resources.rules import NetworkRuleManager

        return NetworkRuleManager(self._manager._client, self)

    @property
    def aliases(self) -> NetworkAliasManager:
        """Access IP aliases for this network.

        Returns:
            NetworkAliasManager for this network.

        Examples:
            List all aliases::

                aliases = network.aliases.list()

            Create an alias::

                alias = network.aliases.create(
                    ip="10.0.0.100",
                    name="webserver",
                    description="Main web server"
                )

            Get alias by IP::

                alias = network.aliases.get(ip="10.0.0.100")
        """
        from pyvergeos.resources.aliases import NetworkAliasManager

        return NetworkAliasManager(self._manager._client, self)

    @property
    def hosts(self) -> NetworkHostManager:
        """Access DHCP/DNS host overrides for this network.

        Returns:
            NetworkHostManager for this network.

        Examples:
            List all host overrides::

                hosts = network.hosts.list()

            Create a host override::

                host = network.hosts.create(
                    hostname="server01",
                    ip="10.0.0.50"
                )

            Get host by hostname::

                host = network.hosts.get(hostname="server01")

        Note:
            Host override changes require DNS apply to take effect.
        """
        from pyvergeos.resources.hosts import NetworkHostManager

        return NetworkHostManager(self._manager._client, self)

    @property
    def dns_zones(self) -> DNSZoneManager:
        """Access DNS zones for this network.

        Returns:
            DNSZoneManager for this network.

        Examples:
            List all DNS zones::

                zones = network.dns_zones.list()

            Get a zone by domain::

                zone = network.dns_zones.get(domain="example.com")

            List records in a zone::

                records = zone.records.list()

            Create a DNS record::

                record = zone.records.create(
                    host="www",
                    record_type="A",
                    value="10.0.0.100"
                )

        Note:
            DNS zones are typically created through the VergeOS UI.
            DNS changes require DNS apply on the network to take effect.
        """
        from pyvergeos.resources.dns import DNSZoneManager

        return DNSZoneManager(self._manager._client, self)


class NetworkManager(ResourceManager[Network]):
    """Manager for Virtual Network operations.

    Provides CRUD operations and power management for virtual networks.

    Examples:
        List all networks::

            networks = client.networks.list()

        Get a network by name::

            external = client.networks.get(name="External")

        Create an internal network::

            net = client.networks.create(
                name="Dev-Network",
                network_address="10.10.10.0/24",
                ip_address="10.10.10.1",
                dhcp_enabled=True,
                dhcp_start="10.10.10.100",
                dhcp_stop="10.10.10.200"
            )

        Power operations::

            net.power_on()
            net.restart()
            net.power_off()
    """

    _endpoint = "vnets"

    def __init__(self, client: VergeClient) -> None:
        super().__init__(client)

    def _to_model(self, data: dict[str, Any]) -> Network:
        return Network(data, self)

    def _power_action(
        self, key: int, action: str, **params: Any
    ) -> dict[str, Any] | None:
        """Execute a power action on a network.

        Uses the vnet_actions endpoint for power operations.

        Args:
            key: Network $key (ID).
            action: Power action (poweron, poweroff, killpower, reset).
            **params: Action parameters (e.g., apply=True).

        Returns:
            Action response.
        """
        body: dict[str, Any] = {"vnet": key, "action": action}
        if params:
            body["params"] = params
        response = self._client._request("POST", "vnet_actions", json_data=body)
        if isinstance(response, dict):
            return response
        return None

    def list(
        self,
        filter: str | None = None,
        fields: builtins.list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        **filter_kwargs: Any,
    ) -> builtins.list[Network]:
        """List networks with optional filtering.

        By default, requests common fields including running status.
        Override with the `fields` parameter for custom field selection.

        Args:
            filter: OData filter string.
            fields: List of fields to return (defaults to common fields).
            limit: Maximum number of results.
            offset: Skip this many results.
            **filter_kwargs: Shorthand filter arguments.

        Returns:
            List of Network objects.
        """
        # Use default fields if none specified
        if fields is None:
            fields = DEFAULT_NETWORK_FIELDS.copy()
        return super().list(
            filter=filter,
            fields=fields,
            limit=limit,
            offset=offset,
            **filter_kwargs,
        )

    def get(
        self,
        key: int | None = None,
        *,
        name: str | None = None,
        fields: builtins.list[str] | None = None,
    ) -> Network:
        """Get a single network by key or name.

        Args:
            key: Network $key (ID).
            name: Network name.
            fields: List of fields to return (defaults to common fields).

        Returns:
            Network object.

        Raises:
            NotFoundError: If network not found.
        """
        if fields is None:
            fields = DEFAULT_NETWORK_FIELDS.copy()
        return super().get(key, name=name, fields=fields)

    def list_internal(self) -> builtins.list[Network]:
        """List internal networks.

        Returns:
            List of internal networks.
        """
        return self.list(filter="type eq 'internal'")

    def list_external(self) -> builtins.list[Network]:
        """List external networks.

        Returns:
            List of external networks.
        """
        return self.list(filter="type eq 'external'")

    def list_running(self) -> builtins.list[Network]:
        """List all running networks.

        Returns:
            List of running networks.
        """
        return self.list(filter="running eq true")

    def list_stopped(self) -> builtins.list[Network]:
        """List all stopped networks.

        Returns:
            List of stopped networks.
        """
        return self.list(filter="running eq false")

    def create(  # type: ignore[override]
        self,
        name: str,
        network_type: str = "internal",
        network_address: str | None = None,
        ip_address: str | None = None,
        gateway: str | None = None,
        dhcp_enabled: bool = False,
        dhcp_start: str | None = None,
        dhcp_stop: str | None = None,
        dns: str = "simple",
        dns_servers: builtins.list[str] | None = None,
        domain: str | None = None,
        mtu: int | None = None,
        layer2_type: str = "vxlan",
        layer2_id: int | None = None,
        interface_network: int | None = None,
        on_power_loss: str = "last_state",
        description: str = "",
        **kwargs: Any,
    ) -> Network:
        """Create a new virtual network.

        Args:
            name: Network name.
            network_type: Network type (internal, external, dmz).
            network_address: CIDR notation (e.g., "192.168.1.0/24").
            ip_address: Router IP address within the network.
            gateway: Default gateway IP (for DHCP clients).
            dhcp_enabled: Enable DHCP server.
            dhcp_start: DHCP range start IP.
            dhcp_stop: DHCP range end IP.
            dns: DNS mode (disabled, simple, bind, network).
            dns_servers: List of DNS server IPs for DHCP.
            domain: Domain name for the network.
            mtu: MTU size (1000-65536).
            layer2_type: Layer 2 type (vlan, vxlan, none).
            layer2_id: VLAN or VXLAN ID.
            interface_network: Key of interface (uplink) network.
            on_power_loss: Behavior on power restore (power_on, last_state, leave_off).
            description: Network description.
            **kwargs: Additional network properties.

        Returns:
            Created network object.
        """
        data: dict[str, Any] = {
            "name": name,
            "type": network_type,
            "dhcp_enabled": dhcp_enabled,
            "dns": dns,
            "layer2_type": layer2_type,
            "on_power_loss": on_power_loss,
            "description": description,
            **kwargs,
        }

        if network_address:
            data["network"] = network_address
        if ip_address:
            data["ipaddress"] = ip_address
        if gateway:
            data["gateway"] = gateway
        if dhcp_start:
            data["dhcp_start"] = dhcp_start
        if dhcp_stop:
            data["dhcp_stop"] = dhcp_stop
        if dns_servers:
            data["dnslist"] = ",".join(dns_servers)
        if domain:
            data["domain"] = domain
        if mtu:
            data["mtu"] = mtu
        if layer2_id:
            data["layer2_id"] = layer2_id
        if interface_network:
            data["interface_vnet"] = interface_network

        # Create the network
        response = self._client._request("POST", self._endpoint, json_data=data)
        if response is None:
            raise ValueError("No response from create operation")
        if not isinstance(response, dict):
            raise ValueError("Create operation returned invalid response")

        # API returns {$key, location, dbpath} - fetch full network
        key = response.get("$key")
        if key is None:
            raise ValueError("Create response missing $key")

        return self.get(int(key))
