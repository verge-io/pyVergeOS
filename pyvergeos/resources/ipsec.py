"""IPSec VPN resource managers."""

from __future__ import annotations

import builtins
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Literal

from pyvergeos.exceptions import NotFoundError
from pyvergeos.resources.base import ResourceManager, ResourceObject

if TYPE_CHECKING:
    from pyvergeos.client import VergeClient
    from pyvergeos.resources.networks import Network


# Key exchange version mapping
KEY_EXCHANGE_MAP = {
    "ike": "Auto",
    "ikev1": "IKEv1",
    "ikev2": "IKEv2",
}

# Reverse mapping for API
KEY_EXCHANGE_API_MAP = {
    "auto": "ike",
    "ikev1": "ikev1",
    "ikev2": "ikev2",
}

# Authentication method mapping
AUTH_METHOD_MAP = {
    "psk": "Pre-Shared Key",
    "pubkey": "RSA Certificate",
}

# Connection mode mapping
CONNECTION_MODE_MAP = {
    "add": "Responder Only",
    "route": "On-Demand",
    "start": "Always Start",
}

CONNECTION_MODE_API_MAP = {
    "responder_only": "add",
    "on_demand": "route",
    "start": "start",
}

# Negotiation mode mapping
NEGOTIATION_MAP = {
    "main": "Main",
    "aggressive": "Aggressive",
}

# DPD action mapping
DPD_ACTION_MAP = {
    "none": "Disabled",
    "clear": "Clear",
    "hold": "Hold",
    "restart": "Restart",
}

DPD_ACTION_API_MAP = {
    "disabled": "none",
    "clear": "clear",
    "hold": "hold",
    "restart": "restart",
}

# Phase 2 mode mapping
PHASE2_MODE_MAP = {
    "tunnel": "Tunnel",
    "transport": "Transport",
}

# Phase 2 protocol mapping
PHASE2_PROTOCOL_MAP = {
    "esp": "ESP (Encrypted)",
    "ah": "AH (Auth Only)",
}

# Type aliases
KeyExchangeType = Literal["auto", "ikev1", "ikev2"]
ConnectionModeType = Literal["responder_only", "on_demand", "start"]
NegotiationModeType = Literal["main", "aggressive"]
DPDActionType = Literal["disabled", "clear", "hold", "restart"]
Phase2ModeType = Literal["tunnel", "transport"]
Phase2ProtocolType = Literal["esp", "ah"]

# Default fields for IPSec connection queries
DEFAULT_CONNECTION_FIELDS = [
    "$key",
    "ipsec",
    "enabled",
    "name",
    "description",
    "keyexchange",
    "remote_gateway",
    "auth",
    "negotiation",
    "identifier",
    "peer_identifier",
    "ike",
    "ikelifetime",
    "auto",
    "mobike",
    "split_connections",
    "forceencaps",
    "keyingtries",
    "rekey",
    "reauth",
    "margintime",
    "dpdaction",
    "dpddelay",
    "dpdfailures",
    "modified",
]

# Default fields for IPSec policy queries
DEFAULT_POLICY_FIELDS = [
    "$key",
    "phase1",
    "enabled",
    "name",
    "description",
    "mode",
    "local",
    "remote",
    "lifetime",
    "protocol",
    "ciphers",
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


class IPSecConnection(ResourceObject):
    """IPSec Phase 1 (IKE) connection object."""

    @property
    def policies(self) -> IPSecPolicyManager:
        """Access Phase 2 policies for this connection.

        Returns:
            IPSecPolicyManager for this connection.

        Examples:
            List all policies::

                policies = connection.policies.list()

            Create a policy::

                policy = connection.policies.create(
                    name="LAN-to-LAN",
                    local_network="10.0.0.0/24",
                    remote_network="192.168.1.0/24"
                )
        """
        manager = self._manager
        if not isinstance(manager, IPSecConnectionManager):
            raise TypeError("Manager must be IPSecConnectionManager")
        return IPSecPolicyManager(manager._client, self)

    @property
    def key_exchange_display(self) -> str:
        """Human-readable key exchange version."""
        raw = str(self.get("keyexchange", ""))
        return KEY_EXCHANGE_MAP.get(raw, raw)

    @property
    def auth_method_display(self) -> str:
        """Human-readable authentication method."""
        raw = str(self.get("auth", ""))
        return AUTH_METHOD_MAP.get(raw, raw)

    @property
    def connection_mode_display(self) -> str:
        """Human-readable connection mode."""
        raw = str(self.get("auto", ""))
        return CONNECTION_MODE_MAP.get(raw, raw)

    @property
    def dpd_action_display(self) -> str:
        """Human-readable DPD action."""
        raw = str(self.get("dpdaction", ""))
        return DPD_ACTION_MAP.get(raw, raw)

    @property
    def is_enabled(self) -> bool:
        """Check if connection is enabled."""
        return bool(self.get("enabled", False))

    @property
    def remote_gateway(self) -> str:
        """Get remote gateway address."""
        return str(self.get("remote_gateway", ""))

    @property
    def modified_at(self) -> datetime | None:
        """Get last modified timestamp."""
        return _timestamp_to_datetime(self.get("modified"))


class IPSecPolicy(ResourceObject):
    """IPSec Phase 2 policy (traffic selector) object."""

    @property
    def mode_display(self) -> str:
        """Human-readable mode."""
        raw = str(self.get("mode", ""))
        return PHASE2_MODE_MAP.get(raw, raw)

    @property
    def protocol_display(self) -> str:
        """Human-readable protocol."""
        raw = str(self.get("protocol", ""))
        return PHASE2_PROTOCOL_MAP.get(raw, raw)

    @property
    def is_enabled(self) -> bool:
        """Check if policy is enabled."""
        return bool(self.get("enabled", False))

    @property
    def local_network(self) -> str:
        """Get local network CIDR."""
        return str(self.get("local", ""))

    @property
    def remote_network(self) -> str:
        """Get remote network CIDR."""
        return str(self.get("remote", ""))

    @property
    def modified_at(self) -> datetime | None:
        """Get last modified timestamp."""
        return _timestamp_to_datetime(self.get("modified"))


class IPSecConnectionManager(ResourceManager[IPSecConnection]):
    """Manager for IPSec Phase 1 (IKE) connections.

    IPSec connections define the IKE security association including
    remote gateway, authentication, and encryption settings.

    This is a sub-resource manager that operates on a specific network.

    Examples:
        List connections on a network::

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
    """

    _endpoint = "vnet_ipsec_phase1s"

    def __init__(self, client: VergeClient, network: Network) -> None:
        super().__init__(client)
        self._network = network
        self._ipsec_key: int | None = None

    def _to_model(self, data: dict[str, Any]) -> IPSecConnection:
        # Add network info to the data
        data["_network_key"] = self._network.key
        data["_network_name"] = self._network.name
        return IPSecConnection(data, self)

    def _get_or_create_ipsec_config(self) -> int:
        """Get or create the IPSec configuration for this network.

        Returns:
            The $key of the vnet_ipsecs record.

        Raises:
            ValueError: If unable to create IPSec configuration.
        """
        if self._ipsec_key is not None:
            return self._ipsec_key

        # Query for existing IPSec config
        params = {
            "filter": f"vnet eq {self._network.key}",
            "fields": "$key,enabled,mode",
        }
        response = self._client._request("GET", "vnet_ipsecs", params=params)

        if response:
            if isinstance(response, builtins.list) and response:
                key_val = response[0].get("$key")
                if key_val is not None:
                    self._ipsec_key = int(key_val)
            elif isinstance(response, dict) and response.get("$key"):
                key_val = response.get("$key")
                if key_val is not None:
                    self._ipsec_key = int(key_val)

        if self._ipsec_key is not None:
            return self._ipsec_key

        # Create new IPSec config
        body = {
            "vnet": self._network.key,
            "enabled": True,
            "mode": "normal",
        }
        create_response = self._client._request("POST", "vnet_ipsecs", json_data=body)

        if not create_response or not isinstance(create_response, dict):
            raise ValueError("Failed to create IPSec configuration for network")

        key_val = create_response.get("$key")
        if key_val is None:
            raise ValueError("IPSec configuration created but no $key returned")
        self._ipsec_key = int(key_val)

        return self._ipsec_key

    def _get_ipsec_config(self) -> int | None:
        """Get the IPSec configuration key if it exists.

        Returns:
            The $key of the vnet_ipsecs record, or None if not configured.
        """
        if self._ipsec_key is not None:
            return self._ipsec_key

        params = {
            "filter": f"vnet eq {self._network.key}",
            "fields": "$key",
        }
        response = self._client._request("GET", "vnet_ipsecs", params=params)

        if response:
            if isinstance(response, builtins.list) and response:
                key_val = response[0].get("$key")
                if key_val is not None:
                    self._ipsec_key = int(key_val)
            elif isinstance(response, dict) and response.get("$key"):
                key_val = response.get("$key")
                if key_val is not None:
                    self._ipsec_key = int(key_val)

        return self._ipsec_key

    def list(
        self,
        filter: str | None = None,
        fields: builtins.list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        **filter_kwargs: Any,
    ) -> builtins.list[IPSecConnection]:
        """List IPSec connections on this network.

        Args:
            filter: OData filter string.
            fields: List of fields to return.
            limit: Maximum number of results.
            offset: Skip this many results.
            **filter_kwargs: Shorthand filter arguments (e.g., name="Site-B").

        Returns:
            List of IPSecConnection objects.
        """
        ipsec_key = self._get_ipsec_config()
        if ipsec_key is None:
            return []

        # Build parameters
        params: dict[str, Any] = {}

        # Build filter - always include ipsec parent filter
        filters = [f"ipsec eq {ipsec_key}"]
        if filter:
            filters.append(filter)
        params["filter"] = " and ".join(filters)

        # Default fields
        if fields is None:
            fields = DEFAULT_CONNECTION_FIELDS.copy()
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
    ) -> IPSecConnection:
        """Get a single IPSec connection by key or name.

        Args:
            key: Connection $key (ID).
            name: Connection name.
            fields: List of fields to return.

        Returns:
            IPSecConnection object.

        Raises:
            NotFoundError: If connection not found.
            ValueError: If neither key nor name provided.
        """
        # Use default fields if not specified
        if fields is None:
            fields = DEFAULT_CONNECTION_FIELDS.copy()

        if key is not None:
            params: dict[str, Any] = {"fields": ",".join(fields)}

            response = self._client._request(
                "GET", f"{self._endpoint}/{key}", params=params
            )
            if response is None:
                raise NotFoundError(f"IPSec connection with key {key} not found")
            if not isinstance(response, dict):
                raise NotFoundError(f"IPSec connection {key} returned invalid response")
            return self._to_model(response)

        if name is not None:
            escaped_name = name.replace("'", "''")
            results = self.list(filter=f"name eq '{escaped_name}'", fields=fields)
            if not results:
                raise NotFoundError(f"IPSec connection with name '{name}' not found")
            return results[0]

        raise ValueError("Either key or name must be provided")

    def create(  # type: ignore[override]
        self,
        name: str,
        remote_gateway: str,
        pre_shared_key: str,
        *,
        key_exchange: KeyExchangeType = "auto",
        encryption: str = "aes256-sha256-modp2048",
        ike_lifetime: int = 10800,
        connection_mode: ConnectionModeType = "on_demand",
        negotiation: NegotiationModeType = "main",
        identifier: str | None = None,
        peer_identifier: str | None = None,
        dpd_action: DPDActionType = "restart",
        dpd_delay: int = 30,
        dpd_failures: int = 5,
        force_udp_encap: bool = False,
        mobike: bool = False,
        split_connections: bool = False,
        keying_tries: int = 3,
        rekey: bool = True,
        reauth: bool = True,
        margin_time: int = 540,
        description: str = "",
        enabled: bool = True,
    ) -> IPSecConnection:
        """Create a new IPSec connection.

        Args:
            name: Unique name for the connection.
            remote_gateway: IP address or hostname of the remote VPN gateway.
            pre_shared_key: Pre-shared key for authentication.
            key_exchange: IKE version (auto, ikev1, ikev2).
            encryption: IKE encryption algorithms (e.g., "aes256-sha256-modp2048").
            ike_lifetime: Lifetime of the IKE SA in seconds (60-86400).
            connection_mode: Connection behavior (responder_only, on_demand, start).
            negotiation: IKEv1 negotiation mode (main, aggressive).
            identifier: Local identifier (defaults to local IP).
            peer_identifier: Remote peer identifier (defaults to remote gateway).
            dpd_action: Dead Peer Detection action (disabled, clear, hold, restart).
            dpd_delay: DPD delay in seconds (0-3600).
            dpd_failures: Number of DPD failures before action (IKEv1 only).
            force_udp_encap: Force UDP encapsulation even without NAT.
            mobike: Enable IKEv2 MOBIKE protocol for mobility.
            split_connections: Split connection entries with multiple Phase 2 configs.
            keying_tries: Number of keying attempts (0 = unlimited).
            rekey: Whether to renegotiate on expiry.
            reauth: Whether to reauthenticate on rekey (IKEv2).
            margin_time: Time before expiry to start renegotiation.
            description: Connection description.
            enabled: Whether the connection is enabled.

        Returns:
            Created IPSecConnection object.

        Examples:
            Basic connection::

                conn = network.ipsec.create(
                    name="Site-B",
                    remote_gateway="203.0.113.1",
                    pre_shared_key="MySecretKey123"
                )

            IKEv2 with custom encryption::

                conn = network.ipsec.create(
                    name="Azure-VPN",
                    remote_gateway="azure-vpn.eastus.cloudapp.net",
                    pre_shared_key="ComplexKey!@#",
                    key_exchange="ikev2",
                    encryption="aes256gcm16-sha384-modp2048",
                    connection_mode="start"
                )
        """
        # Get or create IPSec config
        ipsec_key = self._get_or_create_ipsec_config()

        # Map friendly values to API values
        keyexchange_api = KEY_EXCHANGE_API_MAP.get(key_exchange, "ike")
        auto_api = CONNECTION_MODE_API_MAP.get(connection_mode, "route")
        dpdaction_api = DPD_ACTION_API_MAP.get(dpd_action, "restart")

        body: dict[str, Any] = {
            "ipsec": ipsec_key,
            "enabled": enabled,
            "name": name,
            "remote_gateway": remote_gateway,
            "auth": "psk",
            "psk": pre_shared_key,
            "keyexchange": keyexchange_api,
            "ike": encryption,
            "ikelifetime": ike_lifetime,
            "auto": auto_api,
            "negotiation": negotiation,
            "dpdaction": dpdaction_api,
            "dpddelay": dpd_delay,
            "dpdfailures": dpd_failures,
            "forceencaps": force_udp_encap,
            "mobike": mobike,
            "split_connections": split_connections,
            "keyingtries": keying_tries,
            "rekey": rekey,
            "reauth": reauth,
            "margintime": margin_time,
        }

        if identifier:
            body["identifier"] = identifier
        if peer_identifier:
            body["peer_identifier"] = peer_identifier
        if description:
            body["description"] = description

        response = self._client._request("POST", self._endpoint, json_data=body)
        if response is None or not isinstance(response, dict):
            raise ValueError("No response from create operation")

        # Fetch the full connection
        conn_key = response.get("$key")
        if conn_key is None:
            raise ValueError("Create response missing $key")

        return self.get(int(conn_key))

    def update(self, key: int, **kwargs: Any) -> IPSecConnection:
        """Update an existing IPSec connection.

        Args:
            key: Connection $key (ID).
            **kwargs: Attributes to update. Supports:
                - name: New name
                - remote_gateway: New remote gateway
                - pre_shared_key: New PSK
                - key_exchange: New IKE version
                - encryption: New encryption algorithms
                - ike_lifetime: New IKE SA lifetime
                - connection_mode: New connection behavior
                - negotiation: New negotiation mode
                - identifier: New local identifier
                - peer_identifier: New remote identifier
                - dpd_action: New DPD action
                - dpd_delay: New DPD delay
                - dpd_failures: New DPD failure count
                - force_udp_encap: Enable/disable forced UDP encap
                - mobike: Enable/disable MOBIKE
                - split_connections: Enable/disable split connections
                - keying_tries: New keying tries
                - rekey: Enable/disable rekey
                - reauth: Enable/disable reauth
                - margin_time: New margin time
                - description: New description
                - enabled: Enable/disable connection

        Returns:
            Updated IPSecConnection object.
        """
        body: dict[str, Any] = {}

        # Map kwargs to API field names
        field_mapping = {
            "name": "name",
            "remote_gateway": "remote_gateway",
            "pre_shared_key": "psk",
            "encryption": "ike",
            "ike_lifetime": "ikelifetime",
            "negotiation": "negotiation",
            "identifier": "identifier",
            "peer_identifier": "peer_identifier",
            "dpd_delay": "dpddelay",
            "dpd_failures": "dpdfailures",
            "force_udp_encap": "forceencaps",
            "mobike": "mobike",
            "split_connections": "split_connections",
            "keying_tries": "keyingtries",
            "rekey": "rekey",
            "reauth": "reauth",
            "margin_time": "margintime",
            "description": "description",
            "enabled": "enabled",
        }

        for kwarg, api_field in field_mapping.items():
            if kwarg in kwargs:
                body[api_field] = kwargs[kwarg]

        # Map special fields
        if "key_exchange" in kwargs:
            body["keyexchange"] = KEY_EXCHANGE_API_MAP.get(kwargs["key_exchange"], "ike")
        if "connection_mode" in kwargs:
            body["auto"] = CONNECTION_MODE_API_MAP.get(kwargs["connection_mode"], "route")
        if "dpd_action" in kwargs:
            body["dpdaction"] = DPD_ACTION_API_MAP.get(kwargs["dpd_action"], "restart")

        if not body:
            raise ValueError("No update parameters provided")

        self._client._request("PUT", f"{self._endpoint}/{key}", json_data=body)
        return self.get(key)

    def delete(self, key: int) -> None:
        """Delete an IPSec connection.

        This also removes all associated Phase 2 policies.

        Args:
            key: Connection $key (ID).
        """
        self._client._request("DELETE", f"{self._endpoint}/{key}")


class IPSecPolicyManager(ResourceManager[IPSecPolicy]):
    """Manager for IPSec Phase 2 policies (traffic selectors).

    Phase 2 policies define which traffic should be encrypted through
    the IPSec tunnel. They specify local and remote networks.

    This is a sub-resource manager that operates on a specific connection.

    Examples:
        List policies for a connection::

            policies = connection.policies.list()

        Create a policy::

            policy = connection.policies.create(
                name="LAN-to-LAN",
                local_network="10.0.0.0/24",
                remote_network="192.168.1.0/24"
            )

        Delete a policy::

            connection.policies.delete(policy.key)
    """

    _endpoint = "vnet_ipsec_phase2s"

    def __init__(self, client: VergeClient, connection: IPSecConnection) -> None:
        super().__init__(client)
        self._connection = connection

    def _to_model(self, data: dict[str, Any]) -> IPSecPolicy:
        # Add connection info to the data
        data["_connection_key"] = self._connection.key
        data["_connection_name"] = self._connection.name
        return IPSecPolicy(data, self)

    def list(
        self,
        filter: str | None = None,
        fields: builtins.list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        **filter_kwargs: Any,
    ) -> builtins.list[IPSecPolicy]:
        """List Phase 2 policies for this connection.

        Args:
            filter: OData filter string.
            fields: List of fields to return.
            limit: Maximum number of results.
            offset: Skip this many results.
            **filter_kwargs: Shorthand filter arguments (e.g., name="LAN").

        Returns:
            List of IPSecPolicy objects.
        """
        params: dict[str, Any] = {}

        # Build filter - always include phase1 parent filter
        filters = [f"phase1 eq {self._connection.key}"]
        if filter:
            filters.append(filter)
        params["filter"] = " and ".join(filters)

        # Default fields
        if fields is None:
            fields = DEFAULT_POLICY_FIELDS.copy()
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
    ) -> IPSecPolicy:
        """Get a single Phase 2 policy by key or name.

        Args:
            key: Policy $key (ID).
            name: Policy name.
            fields: List of fields to return.

        Returns:
            IPSecPolicy object.

        Raises:
            NotFoundError: If policy not found.
            ValueError: If neither key nor name provided.
        """
        # Use default fields if not specified
        if fields is None:
            fields = DEFAULT_POLICY_FIELDS.copy()

        if key is not None:
            params: dict[str, Any] = {"fields": ",".join(fields)}

            response = self._client._request(
                "GET", f"{self._endpoint}/{key}", params=params
            )
            if response is None:
                raise NotFoundError(f"IPSec policy with key {key} not found")
            if not isinstance(response, dict):
                raise NotFoundError(f"IPSec policy {key} returned invalid response")
            return self._to_model(response)

        if name is not None:
            escaped_name = name.replace("'", "''")
            results = self.list(filter=f"name eq '{escaped_name}'", fields=fields)
            if not results:
                raise NotFoundError(f"IPSec policy with name '{name}' not found")
            return results[0]

        raise ValueError("Either key or name must be provided")

    def create(  # type: ignore[override]
        self,
        name: str,
        local_network: str,
        remote_network: str | None = None,
        *,
        mode: Phase2ModeType = "tunnel",
        protocol: Phase2ProtocolType = "esp",
        ciphers: str = "aes128-sha256-modp2048,aes128gcm128-sha256-modp2048",
        lifetime: int = 3600,
        description: str = "",
        enabled: bool = True,
    ) -> IPSecPolicy:
        """Create a new Phase 2 policy.

        Args:
            name: Unique name for the policy.
            local_network: Local network/subnet in CIDR notation (e.g., "10.0.0.0/24").
            remote_network: Remote network/subnet in CIDR notation.
            mode: IPSec mode (tunnel or transport).
            protocol: Security protocol (esp for encrypted, ah for auth only).
            ciphers: Phase 2 cipher suites.
            lifetime: SA lifetime in seconds (60-86400).
            description: Policy description.
            enabled: Whether the policy is enabled.

        Returns:
            Created IPSecPolicy object.

        Examples:
            Basic LAN-to-LAN policy::

                policy = connection.policies.create(
                    name="LAN-to-LAN",
                    local_network="10.0.0.0/24",
                    remote_network="192.168.1.0/24"
                )

            All traffic through tunnel::

                policy = connection.policies.create(
                    name="All-Traffic",
                    local_network="0.0.0.0/0",
                    remote_network="0.0.0.0/0"
                )
        """
        body: dict[str, Any] = {
            "phase1": self._connection.key,
            "enabled": enabled,
            "name": name,
            "local": local_network,
            "mode": mode,
            "protocol": protocol,
            "ciphers": ciphers,
            "lifetime": lifetime,
        }

        if remote_network:
            body["remote"] = remote_network
        if description:
            body["description"] = description

        response = self._client._request("POST", self._endpoint, json_data=body)
        if response is None or not isinstance(response, dict):
            raise ValueError("No response from create operation")

        # Fetch the full policy
        policy_key = response.get("$key")
        if policy_key is None:
            raise ValueError("Create response missing $key")

        return self.get(int(policy_key))

    def update(self, key: int, **kwargs: Any) -> IPSecPolicy:
        """Update an existing Phase 2 policy.

        Args:
            key: Policy $key (ID).
            **kwargs: Attributes to update. Supports:
                - name: New name
                - local_network: New local network
                - remote_network: New remote network
                - mode: New mode (tunnel/transport)
                - protocol: New protocol (esp/ah)
                - ciphers: New cipher suites
                - lifetime: New lifetime
                - description: New description
                - enabled: Enable/disable policy

        Returns:
            Updated IPSecPolicy object.
        """
        body: dict[str, Any] = {}

        # Map kwargs to API field names
        field_mapping = {
            "name": "name",
            "local_network": "local",
            "remote_network": "remote",
            "mode": "mode",
            "protocol": "protocol",
            "ciphers": "ciphers",
            "lifetime": "lifetime",
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
        """Delete a Phase 2 policy.

        Args:
            key: Policy $key (ID).
        """
        self._client._request("DELETE", f"{self._endpoint}/{key}")
