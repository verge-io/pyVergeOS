"""WireGuard VPN resource managers."""

from __future__ import annotations

import builtins
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Literal

from pyvergeos.exceptions import NotFoundError
from pyvergeos.resources.base import ResourceManager, ResourceObject

if TYPE_CHECKING:
    from pyvergeos.client import VergeClient
    from pyvergeos.resources.networks import Network


# Firewall configuration type mapping
FIREWALL_CONFIG_MAP = {
    "site-to-site": "Site-to-Site",
    "remote-user": "Remote User",
    "none": "None",
}

# Reverse mapping for API
FIREWALL_CONFIG_API_MAP = {
    "site_to_site": "site-to-site",
    "remote_user": "remote-user",
    "none": "none",
}

# Type aliases
FirewallConfigType = Literal["site_to_site", "remote_user", "none"]

# Default fields for WireGuard interface queries
DEFAULT_INTERFACE_FIELDS = [
    "$key",
    "vnet",
    "name",
    "description",
    "enabled",
    "ip",
    "listenport",
    "mtu",
    "public_key",
    "endpoint_ip",
    "modified",
]

# Default fields for WireGuard peer queries
DEFAULT_PEER_FIELDS = [
    "$key",
    "wireguard",
    "name",
    "description",
    "enabled",
    "endpoint",
    "port",
    "peer_ip",
    "public_key",
    "preshared_key",
    "allowed_ips",
    "keepalive",
    "configure_firewall",
    "modified",
]


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


class WireGuardInterface(ResourceObject):
    """WireGuard VPN interface object."""

    @property
    def peers(self) -> WireGuardPeerManager:
        """Access peers for this WireGuard interface.

        Returns:
            WireGuardPeerManager for this interface.

        Examples:
            List all peers::

                peers = interface.peers.list()

            Create a peer::

                peer = interface.peers.create(
                    name="remote-office",
                    peer_ip="10.100.0.2",
                    public_key="abc123...",
                    allowed_ips="192.168.1.0/24"
                )
        """
        manager = self._manager
        if not isinstance(manager, WireGuardManager):
            raise TypeError("Manager must be WireGuardManager")
        return WireGuardPeerManager(manager._client, self)

    @property
    def is_enabled(self) -> bool:
        """Check if interface is enabled."""
        return bool(self.get("enabled", False))

    @property
    def ip_address(self) -> str:
        """Get the tunnel IP address with CIDR notation."""
        return str(self.get("ip", ""))

    @property
    def ip_only(self) -> str:
        """Get the IP address without the CIDR mask."""
        ip = self.ip_address
        if "/" in ip:
            return ip.split("/")[0]
        return ip

    @property
    def subnet_mask(self) -> str:
        """Get the CIDR subnet mask."""
        ip = self.ip_address
        if "/" in ip:
            return ip.split("/")[1]
        return "32"

    @property
    def listen_port(self) -> int:
        """Get the UDP listen port."""
        return int(self.get("listenport", 51820))

    @property
    def mtu(self) -> int:
        """Get the MTU (0 = auto)."""
        return int(self.get("mtu", 0))

    @property
    def mtu_display(self) -> str:
        """Get human-readable MTU."""
        mtu = self.mtu
        return "Auto" if mtu == 0 else str(mtu)

    @property
    def public_key(self) -> str:
        """Get the interface public key."""
        return str(self.get("public_key", ""))

    @property
    def endpoint_ip(self) -> str:
        """Get the endpoint IP for peer configurations."""
        return str(self.get("endpoint_ip", ""))

    @property
    def modified_at(self) -> datetime | None:
        """Get last modified timestamp."""
        return _timestamp_to_datetime(self.get("modified"))


class WireGuardPeer(ResourceObject):
    """WireGuard VPN peer object."""

    @property
    def is_enabled(self) -> bool:
        """Check if peer is enabled."""
        return bool(self.get("enabled", False))

    @property
    def endpoint(self) -> str:
        """Get the peer endpoint (IP or hostname)."""
        return str(self.get("endpoint", ""))

    @property
    def port(self) -> int:
        """Get the peer port."""
        return int(self.get("port", 51820))

    @property
    def peer_ip(self) -> str:
        """Get the peer tunnel IP address."""
        return str(self.get("peer_ip", ""))

    @property
    def public_key(self) -> str:
        """Get the peer public key."""
        return str(self.get("public_key", ""))

    @property
    def has_preshared_key(self) -> bool:
        """Check if a preshared key is configured."""
        return bool(self.get("preshared_key"))

    @property
    def allowed_ips(self) -> str:
        """Get the allowed IPs for this peer."""
        return str(self.get("allowed_ips", ""))

    @property
    def keepalive(self) -> int:
        """Get the keepalive interval in seconds (0 = disabled)."""
        return int(self.get("keepalive", 0))

    @property
    def firewall_config(self) -> str:
        """Get the raw firewall configuration mode."""
        return str(self.get("configure_firewall", ""))

    @property
    def firewall_config_display(self) -> str:
        """Get human-readable firewall configuration mode."""
        raw = self.firewall_config
        return FIREWALL_CONFIG_MAP.get(raw, raw)

    @property
    def modified_at(self) -> datetime | None:
        """Get last modified timestamp."""
        return _timestamp_to_datetime(self.get("modified"))

    def get_config(self) -> str:
        """Get the WireGuard configuration for this peer.

        Returns the WireGuard config file content that can be used
        by the remote peer to connect to this tunnel.

        Returns:
            WireGuard configuration file content as string.

        Raises:
            ValueError: If configuration cannot be retrieved.

        Examples:
            Get and save peer config::

                config = peer.get_config()
                with open("wg0.conf", "w") as f:
                    f.write(config)
        """
        manager = self._manager
        if not isinstance(manager, WireGuardPeerManager):
            raise TypeError("Manager must be WireGuardPeerManager")
        return manager.get_config(self.key)


class WireGuardManager(ResourceManager[WireGuardInterface]):
    """Manager for WireGuard VPN interfaces.

    WireGuard interfaces define the local VPN tunnel endpoint including
    IP address, listen port, and cryptographic keys.

    This is a sub-resource manager that operates on a specific network.

    Examples:
        List interfaces on a network::

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
    """

    _endpoint = "vnet_wireguards"

    def __init__(self, client: VergeClient, network: Network) -> None:
        super().__init__(client)
        self._network = network

    def _to_model(self, data: dict[str, Any]) -> WireGuardInterface:
        # Add network info to the data
        data["_network_key"] = self._network.key
        data["_network_name"] = self._network.name
        return WireGuardInterface(data, self)

    def list(
        self,
        filter: str | None = None,
        fields: builtins.list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        **filter_kwargs: Any,
    ) -> builtins.list[WireGuardInterface]:
        """List WireGuard interfaces on this network.

        Args:
            filter: OData filter string.
            fields: List of fields to return.
            limit: Maximum number of results.
            offset: Skip this many results.
            **filter_kwargs: Shorthand filter arguments (e.g., name="wg0").

        Returns:
            List of WireGuardInterface objects.
        """
        # Build parameters
        params: dict[str, Any] = {}

        # Build filter - always include vnet parent filter
        filters = [f"vnet eq {self._network.key}"]
        if filter:
            filters.append(filter)
        params["filter"] = " and ".join(filters)

        # Default fields
        if fields is None:
            fields = DEFAULT_INTERFACE_FIELDS.copy()
        params["fields"] = ",".join(fields)

        # Sort by name
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
    ) -> WireGuardInterface:
        """Get a single WireGuard interface by key or name.

        Args:
            key: Interface $key (ID).
            name: Interface name.
            fields: List of fields to return.

        Returns:
            WireGuardInterface object.

        Raises:
            NotFoundError: If interface not found.
            ValueError: If neither key nor name provided.
        """
        # Use default fields if not specified
        if fields is None:
            fields = DEFAULT_INTERFACE_FIELDS.copy()

        if key is not None:
            params: dict[str, Any] = {"fields": ",".join(fields)}

            response = self._client._request(
                "GET", f"{self._endpoint}/{key}", params=params
            )
            if response is None:
                raise NotFoundError(f"WireGuard interface with key {key} not found")
            if not isinstance(response, dict):
                raise NotFoundError(f"WireGuard interface {key} returned invalid response")
            return self._to_model(response)

        if name is not None:
            escaped_name = name.replace("'", "''")
            results = self.list(filter=f"name eq '{escaped_name}'", fields=fields)
            if not results:
                raise NotFoundError(f"WireGuard interface with name '{name}' not found")
            return results[0]

        raise ValueError("Either key or name must be provided")

    def create(  # type: ignore[override]
        self,
        name: str,
        ip_address: str,
        *,
        listen_port: int = 51820,
        mtu: int = 0,
        endpoint_ip: str | None = None,
        description: str = "",
        enabled: bool = True,
    ) -> WireGuardInterface:
        """Create a new WireGuard interface.

        Args:
            name: Unique name for the interface.
            ip_address: Tunnel IP address in CIDR notation (e.g., "10.100.0.1/24").
            listen_port: UDP port to listen on (default: 51820).
            mtu: MTU for the interface (0 = auto, default).
            endpoint_ip: Public IP for peer configurations (auto-detected if not set).
            description: Interface description.
            enabled: Whether the interface is enabled.

        Returns:
            Created WireGuardInterface object.

        Examples:
            Basic interface::

                wg = network.wireguard.create(
                    name="wg0",
                    ip_address="10.100.0.1/24"
                )

            Interface with custom port::

                wg = network.wireguard.create(
                    name="wg-remote",
                    ip_address="10.100.0.1/24",
                    listen_port=51821,
                    endpoint_ip="203.0.113.50"
                )
        """
        body: dict[str, Any] = {
            "vnet": self._network.key,
            "name": name,
            "enabled": enabled,
            "ip": ip_address,
            "listenport": listen_port,
            "mtu": mtu,
        }

        if endpoint_ip:
            body["endpoint_ip"] = endpoint_ip
        if description:
            body["description"] = description

        response = self._client._request("POST", self._endpoint, json_data=body)
        if response is None or not isinstance(response, dict):
            raise ValueError("No response from create operation")

        # Fetch the full interface
        iface_key = response.get("$key")
        if iface_key is None:
            raise ValueError("Create response missing $key")

        return self.get(int(iface_key))

    def update(self, key: int, **kwargs: Any) -> WireGuardInterface:
        """Update an existing WireGuard interface.

        Args:
            key: Interface $key (ID).
            **kwargs: Attributes to update. Supports:
                - name: New name
                - ip_address: New tunnel IP in CIDR notation
                - listen_port: New listen port
                - mtu: New MTU (0 = auto)
                - endpoint_ip: New endpoint IP
                - description: New description
                - enabled: Enable/disable interface

        Returns:
            Updated WireGuardInterface object.
        """
        body: dict[str, Any] = {}

        # Map kwargs to API field names
        field_mapping = {
            "name": "name",
            "ip_address": "ip",
            "listen_port": "listenport",
            "mtu": "mtu",
            "endpoint_ip": "endpoint_ip",
            "description": "description",
            "enabled": "enabled",
        }

        for kwarg, api_field in field_mapping.items():
            if kwarg in kwargs:
                body[api_field] = kwargs[kwarg]

        if not body:
            raise ValueError("No update parameters provided")

        self._client._request("PUT", f"{self._endpoint}/{key}", json_data=body)
        return self.get(key)

    def delete(self, key: int) -> None:
        """Delete a WireGuard interface.

        This also removes all associated peers.

        Args:
            key: Interface $key (ID).
        """
        self._client._request("DELETE", f"{self._endpoint}/{key}")


class WireGuardPeerManager(ResourceManager[WireGuardPeer]):
    """Manager for WireGuard VPN peers.

    Peers define remote endpoints that can connect to the WireGuard tunnel.

    This is a sub-resource manager that operates on a specific WireGuard interface.

    Examples:
        List peers for an interface::

            peers = interface.peers.list()

        Create a site-to-site peer::

            peer = interface.peers.create(
                name="remote-office",
                peer_ip="10.100.0.2",
                public_key="abc123...",
                allowed_ips="192.168.1.0/24"
            )

        Create a remote user peer::

            peer = interface.peers.create(
                name="laptop",
                peer_ip="10.100.0.10",
                public_key="xyz789...",
                allowed_ips="10.100.0.10/32",
                firewall_config="remote_user",
                keepalive=25
            )

        Get peer configuration::

            config = peer.get_config()
    """

    _endpoint = "vnet_wireguard_peers"

    def __init__(self, client: VergeClient, interface: WireGuardInterface) -> None:
        super().__init__(client)
        self._interface = interface

    def _to_model(self, data: dict[str, Any]) -> WireGuardPeer:
        # Add interface info to the data
        data["_interface_key"] = self._interface.key
        data["_interface_name"] = self._interface.name
        return WireGuardPeer(data, self)

    def list(
        self,
        filter: str | None = None,
        fields: builtins.list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        **filter_kwargs: Any,
    ) -> builtins.list[WireGuardPeer]:
        """List peers for this WireGuard interface.

        Args:
            filter: OData filter string.
            fields: List of fields to return.
            limit: Maximum number of results.
            offset: Skip this many results.
            **filter_kwargs: Shorthand filter arguments (e.g., name="laptop").

        Returns:
            List of WireGuardPeer objects.
        """
        params: dict[str, Any] = {}

        # Build filter - always include wireguard parent filter
        filters = [f"wireguard eq {self._interface.key}"]
        if filter:
            filters.append(filter)
        params["filter"] = " and ".join(filters)

        # Default fields
        if fields is None:
            fields = DEFAULT_PEER_FIELDS.copy()
        params["fields"] = ",".join(fields)

        # Sort by name
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
    ) -> WireGuardPeer:
        """Get a single peer by key or name.

        Args:
            key: Peer $key (ID).
            name: Peer name.
            fields: List of fields to return.

        Returns:
            WireGuardPeer object.

        Raises:
            NotFoundError: If peer not found.
            ValueError: If neither key nor name provided.
        """
        # Use default fields if not specified
        if fields is None:
            fields = DEFAULT_PEER_FIELDS.copy()

        if key is not None:
            params: dict[str, Any] = {"fields": ",".join(fields)}

            response = self._client._request(
                "GET", f"{self._endpoint}/{key}", params=params
            )
            if response is None:
                raise NotFoundError(f"WireGuard peer with key {key} not found")
            if not isinstance(response, dict):
                raise NotFoundError(f"WireGuard peer {key} returned invalid response")
            return self._to_model(response)

        if name is not None:
            escaped_name = name.replace("'", "''")
            results = self.list(filter=f"name eq '{escaped_name}'", fields=fields)
            if not results:
                raise NotFoundError(f"WireGuard peer with name '{name}' not found")
            return results[0]

        raise ValueError("Either key or name must be provided")

    def create(  # type: ignore[override]
        self,
        name: str,
        peer_ip: str,
        public_key: str,
        allowed_ips: str,
        *,
        endpoint: str | None = None,
        port: int = 51820,
        preshared_key: str | None = None,
        keepalive: int = 0,
        firewall_config: FirewallConfigType = "site_to_site",
        description: str = "",
        enabled: bool = True,
    ) -> WireGuardPeer:
        """Create a new WireGuard peer.

        Args:
            name: Unique name for the peer.
            peer_ip: Tunnel IP address for the peer (e.g., "10.100.0.2").
            public_key: Public key of the remote peer (base64 encoded).
            allowed_ips: Comma-separated allowed IP ranges (e.g., "192.168.1.0/24").
            endpoint: Remote peer IP/hostname (empty for roaming clients).
            port: Remote peer port (default: 51820).
            preshared_key: Optional preshared key for post-quantum resistance.
            keepalive: Keepalive interval in seconds (0 = disabled).
            firewall_config: Firewall rule configuration:
                - "site_to_site": Create routes and accept rules for allowed IPs
                - "remote_user": Same as site-to-site plus SNAT for outbound traffic
                - "none": Don't create any firewall rules
            description: Peer description.
            enabled: Whether the peer is enabled.

        Returns:
            Created WireGuardPeer object.

        Examples:
            Site-to-site peer::

                peer = interface.peers.create(
                    name="remote-office",
                    peer_ip="10.100.0.2",
                    public_key="abc123...",
                    allowed_ips="192.168.1.0/24",
                    endpoint="vpn.remote-office.com"
                )

            Remote user (roaming client)::

                peer = interface.peers.create(
                    name="laptop",
                    peer_ip="10.100.0.10",
                    public_key="xyz789...",
                    allowed_ips="10.100.0.10/32",
                    firewall_config="remote_user",
                    keepalive=25
                )
        """
        # Map friendly value to API value
        firewall_api = FIREWALL_CONFIG_API_MAP.get(firewall_config, "site-to-site")

        body: dict[str, Any] = {
            "wireguard": self._interface.key,
            "name": name,
            "enabled": enabled,
            "peer_ip": peer_ip,
            "public_key": public_key,
            "allowed_ips": allowed_ips,
            "port": port,
            "keepalive": keepalive,
            "configure_firewall": firewall_api,
        }

        if endpoint:
            body["endpoint"] = endpoint
        if preshared_key:
            body["preshared_key"] = preshared_key
        if description:
            body["description"] = description

        response = self._client._request("POST", self._endpoint, json_data=body)
        if response is None or not isinstance(response, dict):
            raise ValueError("No response from create operation")

        # Fetch the full peer
        peer_key = response.get("$key")
        if peer_key is None:
            raise ValueError("Create response missing $key")

        return self.get(int(peer_key))

    def update(self, key: int, **kwargs: Any) -> WireGuardPeer:
        """Update an existing WireGuard peer.

        Args:
            key: Peer $key (ID).
            **kwargs: Attributes to update. Supports:
                - name: New name
                - peer_ip: New peer tunnel IP
                - public_key: New public key
                - allowed_ips: New allowed IPs
                - endpoint: New endpoint
                - port: New port
                - preshared_key: New preshared key
                - keepalive: New keepalive interval
                - firewall_config: New firewall configuration
                - description: New description
                - enabled: Enable/disable peer

        Returns:
            Updated WireGuardPeer object.
        """
        body: dict[str, Any] = {}

        # Map kwargs to API field names
        field_mapping = {
            "name": "name",
            "peer_ip": "peer_ip",
            "public_key": "public_key",
            "allowed_ips": "allowed_ips",
            "endpoint": "endpoint",
            "port": "port",
            "preshared_key": "preshared_key",
            "keepalive": "keepalive",
            "description": "description",
            "enabled": "enabled",
        }

        for kwarg, api_field in field_mapping.items():
            if kwarg in kwargs:
                body[api_field] = kwargs[kwarg]

        # Map firewall_config to API value
        if "firewall_config" in kwargs:
            body["configure_firewall"] = FIREWALL_CONFIG_API_MAP.get(
                kwargs["firewall_config"], "site-to-site"
            )

        if not body:
            raise ValueError("No update parameters provided")

        self._client._request("PUT", f"{self._endpoint}/{key}", json_data=body)
        return self.get(key)

    def delete(self, key: int) -> None:
        """Delete a WireGuard peer.

        Args:
            key: Peer $key (ID).
        """
        self._client._request("DELETE", f"{self._endpoint}/{key}")

    def get_config(self, key: int) -> str:
        """Get the WireGuard configuration for a peer.

        Retrieves the WireGuard config file content that can be used
        by the remote peer to connect to this tunnel.

        Args:
            key: Peer $key (ID).

        Returns:
            WireGuard configuration file content as string.

        Raises:
            NotFoundError: If peer not found.
            ValueError: If configuration cannot be retrieved.

        Examples:
            Get and save peer config::

                config = interface.peers.get_config(peer.key)
                with open("wg0.conf", "w") as f:
                    f.write(config)

        Note:
            Configuration is only available for peers that were created with
            the autogenerate_peer option enabled in the VergeOS UI.
        """
        try:
            params = {"fields": "wg_config"}
            response = self._client._request(
                "GET", f"{self._endpoint}/{key}", params=params
            )
        except NotFoundError:
            # The wg_config field may not be available if peer wasn't auto-generated
            raise ValueError(
                "Configuration not available. This peer may not have been created "
                "with auto-generate enabled, or the configuration has not been "
                "generated yet."
            ) from None

        if response is None:
            raise NotFoundError(f"WireGuard peer with key {key} not found")
        if not isinstance(response, dict):
            raise ValueError("Invalid response from API")

        config = response.get("wg_config", "")
        if not config:
            raise ValueError(
                "No configuration available. Ensure peer was created with "
                "auto-generate enabled or has proper key configuration."
            )

        return str(config)
