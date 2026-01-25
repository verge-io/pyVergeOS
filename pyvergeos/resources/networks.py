"""Virtual Network resource manager."""

from __future__ import annotations

import builtins
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Literal

from pyvergeos.resources.base import ResourceManager, ResourceObject

if TYPE_CHECKING:
    from pyvergeos.client import VergeClient
    from pyvergeos.resources.aliases import NetworkAliasManager
    from pyvergeos.resources.dns import DNSZoneManager
    from pyvergeos.resources.hosts import NetworkHostManager
    from pyvergeos.resources.ipsec import IPSecConnectionManager
    from pyvergeos.resources.rules import NetworkRuleManager
    from pyvergeos.resources.wireguard import WireGuardManager


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

# Type aliases for diagnostics
DiagnosticType = Literal["dhcp_leases", "addresses", "all"]

# Address type mapping for human-readable display
ADDRESS_TYPE_MAP = {
    "dynamic": "DHCP Lease",
    "static": "Static",
    "ipalias": "IP Alias",
    "proxy": "Proxy ARP",
    "virtual": "Virtual IP",
}

# Statistics fields to request from vnets endpoint
STATISTICS_FIELDS = [
    "$key",
    "name",
    "nic#stats#txbps as tx_bps",
    "nic#stats#rxbps as rx_bps",
    "nic#stats#tx_pckts as tx_packets",
    "nic#stats#rx_pckts as rx_packets",
    "nic#stats#tx_bytes as tx_bytes",
    "nic#stats#rx_bytes as rx_bytes",
    "nic_dmz#stats#txbps as dmz_tx_bps",
    "nic_dmz#stats#rxbps as dmz_rx_bps",
    "nic_dmz#stats#tx_pckts as dmz_tx_packets",
    "nic_dmz#stats#rx_pckts as dmz_rx_packets",
    "nic_dmz#stats#tx_bytes as dmz_tx_bytes",
    "nic_dmz#stats#rx_bytes as dmz_rx_bytes",
]


def _format_bytes(size: int | float | None) -> str:
    """Format bytes to human-readable string.

    Args:
        size: Size in bytes.

    Returns:
        Formatted string like "1.23 MB".
    """
    if size is None or size == 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    unit_index = 0
    size_float = float(size)
    while size_float >= 1024 and unit_index < len(units) - 1:
        size_float /= 1024
        unit_index += 1
    return f"{size_float:.2f} {units[unit_index]}"


def _timestamp_to_datetime(timestamp: int | None) -> datetime | None:
    """Convert Unix timestamp to datetime.

    Args:
        timestamp: Unix timestamp in seconds.

    Returns:
        Datetime object or None if timestamp is 0 or None.
    """
    if not timestamp or timestamp == 0:
        return None
    return datetime.fromtimestamp(timestamp, tz=timezone.utc)


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

    @property
    def ipsec(self) -> IPSecConnectionManager:
        """Access IPSec VPN connections for this network.

        Returns:
            IPSecConnectionManager for this network.

        Examples:
            List all IPSec connections::

                connections = network.ipsec.list()

            Get a connection by name::

                conn = network.ipsec.get(name="Site-B")

            Create a connection::

                conn = network.ipsec.create(
                    name="Site-B",
                    remote_gateway="203.0.113.1",
                    pre_shared_key="MySecretKey123"
                )

            Access Phase 2 policies::

                policies = conn.policies.list()

            Create a Phase 2 policy::

                policy = conn.policies.create(
                    name="LAN-to-LAN",
                    local_network="10.0.0.0/24",
                    remote_network="192.168.1.0/24"
                )

        Note:
            IPSec configuration changes may require applying firewall rules
            on the network for changes to take effect.
        """
        from pyvergeos.resources.ipsec import IPSecConnectionManager

        return IPSecConnectionManager(self._manager._client, self)

    @property
    def wireguard(self) -> WireGuardManager:
        """Access WireGuard VPN interfaces for this network.

        Returns:
            WireGuardManager for this network.

        Examples:
            List all WireGuard interfaces::

                interfaces = network.wireguard.list()

            Get an interface by name::

                wg = network.wireguard.get(name="wg0")

            Create an interface::

                wg = network.wireguard.create(
                    name="wg0",
                    ip_address="10.100.0.1/24",
                    listen_port=51820
                )

            Access peers::

                peers = wg.peers.list()

            Create a peer::

                peer = wg.peers.create(
                    name="remote-office",
                    peer_ip="10.100.0.2",
                    public_key="abc123...",
                    allowed_ips="192.168.1.0/24"
                )

            Get peer configuration::

                config = peer.get_config()

        Note:
            WireGuard configuration changes may require applying firewall rules
            on the network for changes to take effect.
        """
        from pyvergeos.resources.wireguard import WireGuardManager

        return WireGuardManager(self._manager._client, self)

    def diagnostics(
        self,
        diagnostic_type: DiagnosticType = "all",
    ) -> dict[str, Any]:
        """Get network diagnostic information.

        Returns DHCP leases and/or address table entries for this network.

        Args:
            diagnostic_type: Type of diagnostics to retrieve:
                - "dhcp_leases": Only DHCP lease information (dynamic addresses)
                - "addresses": All address table entries
                - "all": Both DHCP leases and addresses (default)

        Returns:
            Dictionary containing:
                - network_key: Network key
                - network_name: Network name
                - is_running: Whether network is running
                - dhcp_enabled: Whether DHCP is enabled
                - dhcp_leases: List of DHCP leases (if requested)
                - dhcp_lease_count: Number of DHCP leases
                - addresses: List of all addresses (if requested)
                - address_count: Number of addresses

        Examples:
            Get all diagnostics::

                diag = network.diagnostics()
                print(f"DHCP Leases: {diag['dhcp_lease_count']}")
                for lease in diag['dhcp_leases']:
                    print(f"  {lease['ip']} -> {lease['hostname']}")

            Get only DHCP leases::

                diag = network.diagnostics(diagnostic_type="dhcp_leases")

            Get only address table::

                diag = network.diagnostics(diagnostic_type="addresses")
        """
        manager = self._manager
        if not isinstance(manager, NetworkManager):
            raise TypeError("Manager must be NetworkManager")
        return manager.diagnostics(self.key, diagnostic_type=diagnostic_type)

    def statistics(
        self,
        include_history: bool = False,
        history_limit: int = 60,
    ) -> dict[str, Any]:
        """Get network traffic statistics.

        Returns current traffic statistics and optionally historical data.

        Args:
            include_history: Include historical monitoring data.
            history_limit: Maximum number of history entries to return (default 60).

        Returns:
            Dictionary containing:
                - network_key: Network key
                - network_name: Network name
                - is_running: Whether network is running
                - tx_bytes_per_sec: Transmit rate in bytes/second
                - rx_bytes_per_sec: Receive rate in bytes/second
                - tx_packets_per_sec: Transmit packets/second
                - rx_packets_per_sec: Receive packets/second
                - tx_bytes_total: Total bytes transmitted
                - rx_bytes_total: Total bytes received
                - tx_total_formatted: Human-readable total transmitted
                - rx_total_formatted: Human-readable total received
                - dmz_tx_bytes_per_sec: DMZ transmit rate (if applicable)
                - dmz_rx_bytes_per_sec: DMZ receive rate (if applicable)
                - ... (similar DMZ stats)
                - history: List of historical stats (if requested)

        Examples:
            Get current statistics::

                stats = network.statistics()
                print(f"TX: {stats['tx_total_formatted']}")
                print(f"RX: {stats['rx_total_formatted']}")

            Get statistics with history::

                stats = network.statistics(include_history=True)
                for entry in stats.get('history', []):
                    print(f"{entry['timestamp']}: {entry['quality']}% quality")

        Note:
            Statistics are only available for running networks.
        """
        manager = self._manager
        if not isinstance(manager, NetworkManager):
            raise TypeError("Manager must be NetworkManager")
        return manager.statistics(
            self.key, include_history=include_history, history_limit=history_limit
        )


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

    def diagnostics(
        self,
        key: int,
        diagnostic_type: DiagnosticType = "all",
    ) -> dict[str, Any]:
        """Get network diagnostic information.

        Returns DHCP leases and/or address table entries for a network.

        Args:
            key: Network $key (ID).
            diagnostic_type: Type of diagnostics to retrieve:
                - "dhcp_leases": Only DHCP lease information (dynamic addresses)
                - "addresses": All address table entries
                - "all": Both DHCP leases and addresses (default)

        Returns:
            Dictionary containing diagnostic information.

        Examples:
            Get all diagnostics::

                diag = client.networks.diagnostics(network_key)
                print(f"DHCP Leases: {diag['dhcp_lease_count']}")

            Get via network object::

                network = client.networks.get(name="Internal")
                diag = network.diagnostics()
        """
        # Get the network to include metadata
        network = self.get(key)

        result: dict[str, Any] = {
            "network_key": network.key,
            "network_name": network.name,
            "is_running": network.is_running,
            "dhcp_enabled": network.get("dhcp_enabled", False),
        }

        # Get DHCP leases (dynamic addresses)
        if diagnostic_type in ("dhcp_leases", "all"):
            lease_params = {
                "filter": f"vnet eq {key} and type eq 'dynamic'",
                "fields": "$key,ip,mac,hostname,expiration,vendor",
                "sort": "ip",
            }
            lease_response = self._client._request(
                "GET", "vnet_addresses", params=lease_params
            )

            leases: builtins.list[dict[str, Any]] = []
            if lease_response:
                raw_leases = (
                    lease_response
                    if isinstance(lease_response, builtins.list)
                    else [lease_response]
                )
                for lease in raw_leases:
                    if isinstance(lease, dict) and lease.get("$key"):
                        leases.append(
                            {
                                "key": lease.get("$key"),
                                "ip": lease.get("ip"),
                                "mac": lease.get("mac"),
                                "hostname": lease.get("hostname"),
                                "vendor": lease.get("vendor"),
                                "expiration": _timestamp_to_datetime(
                                    lease.get("expiration")
                                ),
                            }
                        )

            result["dhcp_leases"] = leases
            result["dhcp_lease_count"] = len(leases)

        # Get all addresses
        if diagnostic_type in ("addresses", "all"):
            address_params = {
                "filter": f"vnet eq {key}",
                "fields": "$key,ip,mac,hostname,type,expiration,vendor,description",
                "sort": "ip",
            }
            address_response = self._client._request(
                "GET", "vnet_addresses", params=address_params
            )

            addresses: builtins.list[dict[str, Any]] = []
            if address_response:
                raw_addresses = (
                    address_response
                    if isinstance(address_response, builtins.list)
                    else [address_response]
                )
                for addr in raw_addresses:
                    if isinstance(addr, dict) and addr.get("$key"):
                        addr_type = addr.get("type", "")
                        addresses.append(
                            {
                                "key": addr.get("$key"),
                                "ip": addr.get("ip"),
                                "mac": addr.get("mac"),
                                "hostname": addr.get("hostname"),
                                "type": ADDRESS_TYPE_MAP.get(addr_type, addr_type),
                                "type_raw": addr_type,
                                "vendor": addr.get("vendor"),
                                "description": addr.get("description"),
                                "expiration": _timestamp_to_datetime(
                                    addr.get("expiration")
                                ),
                            }
                        )

            result["addresses"] = addresses
            result["address_count"] = len(addresses)

        return result

    def statistics(
        self,
        key: int,
        include_history: bool = False,
        history_limit: int = 60,
    ) -> dict[str, Any]:
        """Get network traffic statistics.

        Returns current traffic statistics and optionally historical data.

        Args:
            key: Network $key (ID).
            include_history: Include historical monitoring data.
            history_limit: Maximum number of history entries (default 60).

        Returns:
            Dictionary containing traffic statistics.

        Examples:
            Get current statistics::

                stats = client.networks.statistics(network_key)
                print(f"TX: {stats['tx_total_formatted']}")

            Get via network object::

                network = client.networks.get(name="External")
                stats = network.statistics(include_history=True)

        Note:
            Statistics are only available for running networks.
        """
        # Get the network first to get name and running status
        network = self.get(key)

        # Query stats fields
        stats_params = {
            "filter": f"$key eq {key}",
            "fields": ",".join(STATISTICS_FIELDS),
        }
        stats_response = self._client._request("GET", "vnets", params=stats_params)

        # Extract stats data
        stats_data: dict[str, Any] = {}
        if stats_response:
            if isinstance(stats_response, builtins.list) and stats_response:
                stats_data = stats_response[0]
            elif isinstance(stats_response, dict):
                stats_data = stats_response

        result: dict[str, Any] = {
            "network_key": network.key,
            "network_name": network.name,
            "is_running": network.is_running,
            # Router interface stats
            "tx_bytes_per_sec": stats_data.get("tx_bps"),
            "rx_bytes_per_sec": stats_data.get("rx_bps"),
            "tx_packets_per_sec": stats_data.get("tx_packets"),
            "rx_packets_per_sec": stats_data.get("rx_packets"),
            "tx_bytes_total": stats_data.get("tx_bytes"),
            "rx_bytes_total": stats_data.get("rx_bytes"),
            "tx_total_formatted": _format_bytes(stats_data.get("tx_bytes")),
            "rx_total_formatted": _format_bytes(stats_data.get("rx_bytes")),
            # DMZ interface stats
            "dmz_tx_bytes_per_sec": stats_data.get("dmz_tx_bps"),
            "dmz_rx_bytes_per_sec": stats_data.get("dmz_rx_bps"),
            "dmz_tx_packets_per_sec": stats_data.get("dmz_tx_packets"),
            "dmz_rx_packets_per_sec": stats_data.get("dmz_rx_packets"),
            "dmz_tx_bytes_total": stats_data.get("dmz_tx_bytes"),
            "dmz_rx_bytes_total": stats_data.get("dmz_rx_bytes"),
        }

        # Get historical data if requested
        if include_history:
            history_params = {
                "filter": f"vnet eq {key}",
                "fields": "timestamp,sent,dropped,quality,latency_usec_avg,latency_usec_peak",
                "sort": "-timestamp",
                "limit": str(history_limit),
            }
            history_response = self._client._request(
                "GET", "vnet_monitor_stats_history_short", params=history_params
            )

            history: builtins.list[dict[str, Any]] = []
            if history_response:
                raw_history = (
                    history_response
                    if isinstance(history_response, builtins.list)
                    else [history_response]
                )
                for entry in raw_history:
                    if isinstance(entry, dict):
                        latency_avg = entry.get("latency_usec_avg", 0)
                        latency_peak = entry.get("latency_usec_peak", 0)
                        history.append(
                            {
                                "timestamp": _timestamp_to_datetime(
                                    entry.get("timestamp")
                                ),
                                "sent": entry.get("sent"),
                                "dropped": entry.get("dropped"),
                                "quality": entry.get("quality"),
                                "latency_avg_ms": round(latency_avg / 1000, 2)
                                if latency_avg
                                else 0,
                                "latency_peak_ms": round(latency_peak / 1000, 2)
                                if latency_peak
                                else 0,
                            }
                        )

            result["history"] = history

        return result
