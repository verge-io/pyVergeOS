"""Network Stats & Monitoring resource managers.

This module provides access to network performance metrics, dashboard,
and VPN connection tracking for monitoring and troubleshooting.

Example:
    >>> # Access network monitor stats
    >>> network = client.networks.get(name="External")
    >>> stats = network.stats.get()
    >>> print(f"Quality: {stats.quality}%, Latency: {stats.latency_avg_ms}ms")

    >>> # Access stats history
    >>> history = network.stats.history_short(limit=100)
    >>> for point in history:
    ...     print(f"{point.timestamp}: Quality {point.quality}%")

    >>> # Access network dashboard
    >>> dashboard = client.network_dashboard.get()
    >>> print(f"Online: {dashboard.vnets_online}/{dashboard.vnets_count}")

    >>> # Access active IPSec connections
    >>> for conn in network.ipsec_connections.list():
    ...     print(f"{conn.local} <-> {conn.remote}: {conn.protocol}")

    >>> # Access WireGuard peer status
    >>> for wg in network.wireguard.list():
    ...     for status in wg.peer_status.list():
    ...         print(f"{status.peer_key}: TX {status.tx_bytes_formatted}")
"""

from __future__ import annotations

import builtins
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from pyvergeos.exceptions import NotFoundError
from pyvergeos.resources.base import ResourceManager, ResourceObject

if TYPE_CHECKING:
    from pyvergeos.client import VergeClient
    from pyvergeos.resources.networks import Network
    from pyvergeos.resources.wireguard import WireGuardInterface


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


# =============================================================================
# Network Monitor Stats
# =============================================================================


class NetworkMonitorStats(ResourceObject):
    """Network monitor statistics resource object.

    Provides current network quality and performance metrics from the
    most recent monitoring sample.
    """

    @property
    def vnet_key(self) -> int:
        """Parent network key."""
        return int(self.get("vnet", 0))

    @property
    def timestamp(self) -> datetime | None:
        """Timestamp for this stats sample."""
        ts = self.get("timestamp")
        if ts:
            return datetime.fromtimestamp(int(ts), tz=timezone.utc)
        return None

    @property
    def timestamp_epoch(self) -> int:
        """Timestamp as Unix epoch."""
        return int(self.get("timestamp", 0))

    @property
    def sent(self) -> int:
        """Number of monitoring packets sent."""
        return int(self.get("sent", 0))

    @property
    def dropped(self) -> int:
        """Number of monitoring packets dropped."""
        return int(self.get("dropped", 0))

    @property
    def quality(self) -> int:
        """Network quality percentage (0-100, higher is better)."""
        return int(self.get("quality", 0))

    @property
    def dropped_pct(self) -> int:
        """Packet drop percentage (0-100)."""
        return int(self.get("dropped_pct", 0))

    @property
    def latency_usec_avg(self) -> int:
        """Average latency in microseconds."""
        return int(self.get("latency_usec_avg", 0))

    @property
    def latency_usec_peak(self) -> int:
        """Peak latency in microseconds."""
        return int(self.get("latency_usec_peak", 0))

    @property
    def latency_avg_ms(self) -> float:
        """Average latency in milliseconds."""
        return round(self.latency_usec_avg / 1000, 2) if self.latency_usec_avg else 0.0

    @property
    def latency_peak_ms(self) -> float:
        """Peak latency in milliseconds."""
        return round(self.latency_usec_peak / 1000, 2) if self.latency_usec_peak else 0.0

    @property
    def duplicates(self) -> int:
        """Number of duplicate packets received."""
        return int(self.get("duplicates", 0))

    @property
    def truncated(self) -> int:
        """Number of truncated packets received."""
        return int(self.get("truncated", 0))

    @property
    def bad_checksums(self) -> int:
        """Number of packets with bad checksums."""
        return int(self.get("bad_checksums", 0))

    @property
    def bad_data(self) -> int:
        """Number of packets with bad data."""
        return int(self.get("bad_data", 0))

    @property
    def has_issues(self) -> bool:
        """Check if there are any packet quality issues."""
        return (
            self.dropped > 0
            or self.duplicates > 0
            or self.truncated > 0
            or self.bad_checksums > 0
            or self.bad_data > 0
        )

    @property
    def is_healthy(self) -> bool:
        """Check if network quality is good (>= 95%)."""
        return self.quality >= 95

    def __repr__(self) -> str:
        ts = self.timestamp.isoformat() if self.timestamp else "?"
        return (
            f"<NetworkMonitorStats vnet={self.vnet_key} ts={ts} "
            f"quality={self.quality}% latency={self.latency_avg_ms}ms>"
        )


class NetworkMonitorStatsHistory(ResourceObject):
    """Network monitor statistics history record.

    Represents a single time point in the network monitoring history.
    """

    @property
    def vnet_key(self) -> int:
        """Parent network key."""
        return int(self.get("vnet", 0))

    @property
    def timestamp(self) -> datetime | None:
        """Timestamp for this history point."""
        ts = self.get("timestamp")
        if ts:
            return datetime.fromtimestamp(int(ts), tz=timezone.utc)
        return None

    @property
    def timestamp_epoch(self) -> int:
        """Timestamp as Unix epoch."""
        return int(self.get("timestamp", 0))

    @property
    def sent(self) -> int:
        """Number of monitoring packets sent."""
        return int(self.get("sent", 0))

    @property
    def dropped(self) -> int:
        """Number of monitoring packets dropped."""
        return int(self.get("dropped", 0))

    @property
    def quality(self) -> int:
        """Network quality percentage (0-100)."""
        return int(self.get("quality", 0))

    @property
    def dropped_pct(self) -> int:
        """Packet drop percentage (0-100)."""
        return int(self.get("dropped_pct", 0))

    @property
    def latency_usec_avg(self) -> int:
        """Average latency in microseconds."""
        return int(self.get("latency_usec_avg", 0))

    @property
    def latency_usec_peak(self) -> int:
        """Peak latency in microseconds."""
        return int(self.get("latency_usec_peak", 0))

    @property
    def latency_avg_ms(self) -> float:
        """Average latency in milliseconds."""
        return round(self.latency_usec_avg / 1000, 2) if self.latency_usec_avg else 0.0

    @property
    def latency_peak_ms(self) -> float:
        """Peak latency in milliseconds."""
        return round(self.latency_usec_peak / 1000, 2) if self.latency_usec_peak else 0.0

    @property
    def duplicates(self) -> int:
        """Number of duplicate packets."""
        return int(self.get("duplicates", 0))

    @property
    def truncated(self) -> int:
        """Number of truncated packets."""
        return int(self.get("truncated", 0))

    @property
    def bad_checksums(self) -> int:
        """Number of packets with bad checksums."""
        return int(self.get("bad_checksums", 0))

    @property
    def bad_data(self) -> int:
        """Number of packets with bad data."""
        return int(self.get("bad_data", 0))

    def __repr__(self) -> str:
        ts = self.timestamp.isoformat() if self.timestamp else "?"
        return f"<NetworkMonitorStatsHistory ts={ts} quality={self.quality}%>"


class NetworkMonitorStatsManager(ResourceManager[NetworkMonitorStats]):
    """Manager for network monitor statistics.

    Provides access to current and historical network quality metrics.
    Scoped to a specific network.

    Example:
        >>> # Get current stats (most recent sample)
        >>> stats = manager.get()
        >>> print(f"Quality: {stats.quality}%")

        >>> # Get short-term history (high resolution)
        >>> history = manager.history_short(limit=100)

        >>> # Get long-term history (aggregated, longer retention)
        >>> history = manager.history_long(limit=1000)
    """

    _endpoint = "vnet_monitor_stats_history_short"

    _default_fields = [
        "$key",
        "vnet",
        "timestamp",
        "sent",
        "dropped",
        "quality",
        "dropped_pct",
        "latency_usec_avg",
        "latency_usec_peak",
        "duplicates",
        "truncated",
        "bad_checksums",
        "bad_data",
    ]

    def __init__(self, client: VergeClient, network: Network) -> None:
        super().__init__(client)
        self._network = network
        self._network_key = network.key

    def _to_model(self, data: dict[str, Any]) -> NetworkMonitorStats:
        return NetworkMonitorStats(data, self)

    def _to_history_model(self, data: dict[str, Any]) -> NetworkMonitorStatsHistory:
        return NetworkMonitorStatsHistory(data, self)

    def get(self, fields: builtins.list[str] | None = None) -> NetworkMonitorStats:  # type: ignore[override]
        """Get the most recent network monitor statistics.

        Args:
            fields: List of fields to return.

        Returns:
            NetworkMonitorStats object with latest metrics.

        Raises:
            NotFoundError: If no stats found for this network.
        """
        if fields is None:
            fields = self._default_fields

        params: dict[str, Any] = {
            "filter": f"vnet eq {self._network_key}",
            "fields": ",".join(fields),
            "sort": "-timestamp",
            "limit": 1,
        }

        response = self._client._request("GET", self._endpoint, params=params)

        if response is None:
            raise NotFoundError(f"Stats not found for network {self._network_key}")

        if isinstance(response, list):
            if not response:
                raise NotFoundError(f"Stats not found for network {self._network_key}")
            return self._to_model(response[0])

        return self._to_model(response)

    def history_short(
        self,
        limit: int | None = None,
        offset: int | None = None,
        since: datetime | int | None = None,
        until: datetime | int | None = None,
        fields: builtins.list[str] | None = None,
    ) -> builtins.list[NetworkMonitorStatsHistory]:
        """Get short-term stats history (high resolution).

        Short-term history provides granular data points for recent monitoring,
        typically stored for hours to a few days.

        Args:
            limit: Maximum number of records to return.
            offset: Skip this many records.
            since: Return records after this time (datetime or epoch).
            until: Return records before this time (datetime or epoch).
            fields: List of fields to return.

        Returns:
            List of NetworkMonitorStatsHistory objects, sorted by timestamp descending.
        """
        return self._get_history(
            "vnet_monitor_stats_history_short",
            limit=limit,
            offset=offset,
            since=since,
            until=until,
            fields=fields,
        )

    def history_long(
        self,
        limit: int | None = None,
        offset: int | None = None,
        since: datetime | int | None = None,
        until: datetime | int | None = None,
        fields: builtins.list[str] | None = None,
    ) -> builtins.list[NetworkMonitorStatsHistory]:
        """Get long-term stats history (aggregated, longer retention).

        Long-term history provides aggregated data points (averages, peaks, sums)
        over longer periods, typically stored for weeks to months.

        Args:
            limit: Maximum number of records to return.
            offset: Skip this many records.
            since: Return records after this time (datetime or epoch).
            until: Return records before this time (datetime or epoch).
            fields: List of fields to return.

        Returns:
            List of NetworkMonitorStatsHistory objects, sorted by timestamp descending.
        """
        return self._get_history(
            "vnet_monitor_stats_history_long",
            limit=limit,
            offset=offset,
            since=since,
            until=until,
            fields=fields,
        )

    def _get_history(
        self,
        endpoint: str,
        limit: int | None = None,
        offset: int | None = None,
        since: datetime | int | None = None,
        until: datetime | int | None = None,
        fields: builtins.list[str] | None = None,
    ) -> builtins.list[NetworkMonitorStatsHistory]:
        """Internal helper to get history from short or long endpoint."""
        if fields is None:
            fields = self._default_fields

        filters = [f"vnet eq {self._network_key}"]

        # Convert datetime to epoch if needed
        if since is not None:
            since_epoch = int(since.timestamp()) if isinstance(since, datetime) else int(since)
            filters.append(f"timestamp ge {since_epoch}")

        if until is not None:
            until_epoch = int(until.timestamp()) if isinstance(until, datetime) else int(until)
            filters.append(f"timestamp le {until_epoch}")

        params: dict[str, Any] = {
            "filter": " and ".join(filters),
            "fields": ",".join(fields),
            "sort": "-timestamp",
        }

        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset

        response = self._client._request("GET", endpoint, params=params)

        if response is None:
            return []

        if isinstance(response, list):
            return [self._to_history_model(item) for item in response]

        return [self._to_history_model(response)]


# =============================================================================
# Network Dashboard
# =============================================================================


class NetworkDashboard(ResourceObject):
    """Network dashboard with aggregated metrics.

    Provides a high-level overview of network status, counts by type and state,
    and top resource consumers for monitoring and capacity planning.
    """

    # Total network counts
    @property
    def vnets_count(self) -> int:
        """Total number of networks."""
        return int(self.get("vnets_count", 0))

    @property
    def vnets_online(self) -> int:
        """Number of online networks."""
        return int(self.get("vnets_online", 0))

    @property
    def vnets_warn(self) -> int:
        """Number of networks in warning state."""
        return int(self.get("vnets_warn", 0))

    @property
    def vnets_error(self) -> int:
        """Number of networks in error state."""
        return int(self.get("vnets_error", 0))

    @property
    def vnets_offline(self) -> int:
        """Number of offline networks."""
        return self.vnets_count - self.vnets_online

    # External network counts
    @property
    def ext_count(self) -> int:
        """Total external networks."""
        return int(self.get("ext_count", 0))

    @property
    def ext_online(self) -> int:
        """Online external networks."""
        return int(self.get("ext_online", 0))

    @property
    def ext_warn(self) -> int:
        """External networks in warning state."""
        return int(self.get("ext_warn", 0))

    @property
    def ext_error(self) -> int:
        """External networks in error state."""
        return int(self.get("ext_error", 0))

    # Internal network counts
    @property
    def int_count(self) -> int:
        """Total internal networks."""
        return int(self.get("int_count", 0))

    @property
    def int_online(self) -> int:
        """Online internal networks."""
        return int(self.get("int_online", 0))

    @property
    def int_warn(self) -> int:
        """Internal networks in warning state."""
        return int(self.get("int_warn", 0))

    @property
    def int_error(self) -> int:
        """Internal networks in error state."""
        return int(self.get("int_error", 0))

    # Tenant network counts
    @property
    def ten_count(self) -> int:
        """Total tenant networks."""
        return int(self.get("ten_count", 0))

    @property
    def ten_online(self) -> int:
        """Online tenant networks."""
        return int(self.get("ten_online", 0))

    @property
    def ten_warn(self) -> int:
        """Tenant networks in warning state."""
        return int(self.get("ten_warn", 0))

    @property
    def ten_error(self) -> int:
        """Tenant networks in error state."""
        return int(self.get("ten_error", 0))

    # VPN network counts
    @property
    def vpn_count(self) -> int:
        """Total VPN networks."""
        return int(self.get("vpn_count", 0))

    @property
    def vpn_online(self) -> int:
        """Online VPN networks."""
        return int(self.get("vpn_online", 0))

    @property
    def vpn_warn(self) -> int:
        """VPN networks in warning state."""
        return int(self.get("vpn_warn", 0))

    @property
    def vpn_error(self) -> int:
        """VPN networks in error state."""
        return int(self.get("vpn_error", 0))

    # NIC counts
    @property
    def nics_count(self) -> int:
        """Total network interfaces."""
        return int(self.get("nics_count", 0))

    @property
    def nics_online(self) -> int:
        """Online network interfaces."""
        return int(self.get("nics_online", 0))

    @property
    def nics_warn(self) -> int:
        """Network interfaces in warning state."""
        return int(self.get("nics_warn", 0))

    @property
    def nics_error(self) -> int:
        """Network interfaces in error state."""
        return int(self.get("nics_error", 0))

    # WireGuard counts
    @property
    def wireguards_count(self) -> int:
        """Total WireGuard interfaces."""
        return int(self.get("wireguards_count", 0))

    # Top consumers (raw data access)
    @property
    def running_ext_vnets(self) -> builtins.list[dict[str, Any]]:
        """Top running external networks by throughput."""
        data = self.get("running_ext_vnets")
        return data if isinstance(data, list) else []

    @property
    def running_int_vnets(self) -> builtins.list[dict[str, Any]]:
        """Top running internal networks by throughput."""
        data = self.get("running_int_vnets")
        return data if isinstance(data, list) else []

    @property
    def running_tenant_vnets(self) -> builtins.list[dict[str, Any]]:
        """Top running tenant networks by throughput."""
        data = self.get("running_tenant_vnets")
        return data if isinstance(data, list) else []

    @property
    def nics_rate(self) -> builtins.list[dict[str, Any]]:
        """Top network interfaces by throughput rate."""
        data = self.get("nics_rate")
        return data if isinstance(data, list) else []

    @property
    def logs(self) -> builtins.list[dict[str, Any]]:
        """Recent network-related logs."""
        data = self.get("logs")
        return data if isinstance(data, list) else []

    # Helper methods
    def get_health_summary(self) -> dict[str, Any]:
        """Get a summary of network health across all types.

        Returns:
            Dictionary with health counts by network type.
        """
        return {
            "total": {
                "count": self.vnets_count,
                "online": self.vnets_online,
                "warning": self.vnets_warn,
                "error": self.vnets_error,
            },
            "external": {
                "count": self.ext_count,
                "online": self.ext_online,
                "warning": self.ext_warn,
                "error": self.ext_error,
            },
            "internal": {
                "count": self.int_count,
                "online": self.int_online,
                "warning": self.int_warn,
                "error": self.int_error,
            },
            "tenant": {
                "count": self.ten_count,
                "online": self.ten_online,
                "warning": self.ten_warn,
                "error": self.ten_error,
            },
            "vpn": {
                "count": self.vpn_count,
                "online": self.vpn_online,
                "warning": self.vpn_warn,
                "error": self.vpn_error,
            },
        }

    @property
    def has_errors(self) -> bool:
        """Check if any networks are in error state."""
        return self.vnets_error > 0

    @property
    def has_warnings(self) -> bool:
        """Check if any networks are in warning state."""
        return self.vnets_warn > 0

    def __repr__(self) -> str:
        return (
            f"<NetworkDashboard vnets={self.vnets_online}/{self.vnets_count} "
            f"ext={self.ext_online}/{self.ext_count} int={self.int_online}/{self.int_count}>"
        )


class NetworkDashboardManager(ResourceManager[NetworkDashboard]):
    """Manager for network dashboard.

    Provides aggregated network metrics and status counts for monitoring.

    Example:
        >>> dashboard = client.network_dashboard.get()
        >>> print(f"Online: {dashboard.vnets_online}/{dashboard.vnets_count}")
        >>> print(f"Errors: {dashboard.vnets_error}")
        >>> if dashboard.has_errors:
        ...     print("WARNING: Networks in error state!")
    """

    _endpoint = "vnet_dashboard"

    def __init__(self, client: VergeClient) -> None:
        super().__init__(client)

    def _to_model(self, data: dict[str, Any]) -> NetworkDashboard:
        return NetworkDashboard(data, self)

    def get(self) -> NetworkDashboard:  # type: ignore[override]
        """Get network dashboard.

        Returns:
            NetworkDashboard object with aggregated metrics.
        """
        response = self._client._request("GET", self._endpoint)

        if response is None:
            return self._to_model({})

        if isinstance(response, list) and response:
            return self._to_model(response[0])

        if isinstance(response, dict):
            return self._to_model(response)

        return self._to_model({})


# =============================================================================
# IPSec Active Connections
# =============================================================================


class IPSecActiveConnection(ResourceObject):
    """Active IPSec VPN connection (non-persistent/computed).

    Represents a currently established IPSec tunnel with connection details.
    This data is computed from strongSwan status and is not stored in the database.
    """

    @property
    def vnet_key(self) -> int:
        """Parent network key."""
        return int(self.get("vnet", 0))

    @property
    def phase1_key(self) -> int | None:
        """Phase 1 (IKE SA) configuration key."""
        p1 = self.get("phase1")
        return int(p1) if p1 else None

    @property
    def phase2_key(self) -> int | None:
        """Phase 2 (Child SA) configuration key."""
        p2 = self.get("phase2")
        return int(p2) if p2 else None

    @property
    def uniqueid(self) -> int:
        """Unique identifier for this connection instance."""
        return int(self.get("uniqueid", 0))

    @property
    def local(self) -> str:
        """Local endpoint address."""
        return str(self.get("local", ""))

    @property
    def remote(self) -> str:
        """Remote endpoint address."""
        return str(self.get("remote", ""))

    @property
    def local_network(self) -> str:
        """Local network/subnet (CIDR)."""
        return str(self.get("local_network", ""))

    @property
    def remote_network(self) -> str:
        """Remote network/subnet (CIDR)."""
        return str(self.get("remote_network", ""))

    @property
    def connection(self) -> str:
        """Connection name."""
        return str(self.get("connection", ""))

    @property
    def reqid(self) -> str:
        """Request ID."""
        return str(self.get("reqid", ""))

    @property
    def interface(self) -> str:
        """Interface name."""
        return str(self.get("interface", ""))

    @property
    def protocol(self) -> str:
        """Protocol (ESP, AH, etc.)."""
        return str(self.get("protocol", ""))

    @property
    def created_at(self) -> datetime | None:
        """Timestamp when connection was established."""
        ts = self.get("created")
        if ts:
            return datetime.fromtimestamp(int(ts), tz=timezone.utc)
        return None

    def __repr__(self) -> str:
        return (
            f"<IPSecActiveConnection {self.connection} "
            f"{self.local_network} <-> {self.remote_network}>"
        )


class IPSecActiveConnectionManager(ResourceManager[IPSecActiveConnection]):
    """Manager for active IPSec connections.

    Provides access to currently established IPSec VPN tunnels.
    This is a read-only, non-persistent view of active connection state.
    Scoped to a specific network.

    Example:
        >>> # List all active IPSec connections
        >>> for conn in network.ipsec_connections.list():
        ...     print(f"{conn.local} <-> {conn.remote}")
        ...     print(f"  Protocol: {conn.protocol}")
        ...     print(f"  Local Network: {conn.local_network}")
        ...     print(f"  Remote Network: {conn.remote_network}")
    """

    _endpoint = "vnet_ipsec_connections"

    _default_fields = [
        "$key",
        "vnet",
        "phase1",
        "phase2",
        "uniqueid",
        "local",
        "remote",
        "local_network",
        "remote_network",
        "connection",
        "reqid",
        "interface",
        "protocol",
        "created",
    ]

    def __init__(self, client: VergeClient, network: Network) -> None:
        super().__init__(client)
        self._network = network
        self._network_key = network.key

    def _to_model(self, data: dict[str, Any]) -> IPSecActiveConnection:
        return IPSecActiveConnection(data, self)

    def list(  # noqa: A002
        self,
        filter: str | None = None,  # noqa: A002
        fields: builtins.list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        **filter_kwargs: Any,
    ) -> builtins.list[IPSecActiveConnection]:
        """List active IPSec connections for this network.

        Args:
            filter: OData filter string.
            fields: List of fields to return.
            limit: Maximum number of results.
            offset: Skip this many results.
            **filter_kwargs: Additional filter parameters (ignored for scoped manager).

        Returns:
            List of IPSecActiveConnection objects.
        """
        # Note: filter_kwargs ignored - this is a network-scoped manager
        _ = filter_kwargs

        if fields is None:
            fields = self._default_fields

        filters = [f"vnet eq {self._network_key}"]
        if filter:
            filters.append(filter)

        params: dict[str, Any] = {
            "filter": " and ".join(filters),
            "fields": ",".join(fields),
        }

        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset

        response = self._client._request("GET", self._endpoint, params=params)

        if response is None:
            return []

        if isinstance(response, list):
            return [self._to_model(item) for item in response]

        return [self._to_model(response)]

    def count(self) -> int:
        """Get count of active IPSec connections.

        Returns:
            Number of active connections.
        """
        return len(self.list())


# =============================================================================
# WireGuard Peer Status
# =============================================================================


class WireGuardPeerStatus(ResourceObject):
    """WireGuard peer connection status.

    Provides real-time status information for a WireGuard peer including
    handshake time and transfer statistics.
    """

    @property
    def peer_key(self) -> int:
        """Peer configuration key."""
        return int(self.get("peer", 0))

    @property
    def last_handshake(self) -> datetime | None:
        """Timestamp of last successful handshake."""
        ts = self.get("last_handshake")
        if ts:
            return datetime.fromtimestamp(int(ts), tz=timezone.utc)
        return None

    @property
    def last_handshake_epoch(self) -> int:
        """Last handshake as Unix epoch."""
        return int(self.get("last_handshake", 0))

    @property
    def tx_bytes(self) -> int:
        """Total bytes transmitted to peer."""
        return int(self.get("tx_bytes", 0))

    @property
    def rx_bytes(self) -> int:
        """Total bytes received from peer."""
        return int(self.get("rx_bytes", 0))

    @property
    def tx_bytes_formatted(self) -> str:
        """Human-readable bytes transmitted."""
        return _format_bytes(self.tx_bytes)

    @property
    def rx_bytes_formatted(self) -> str:
        """Human-readable bytes received."""
        return _format_bytes(self.rx_bytes)

    @property
    def last_update(self) -> datetime | None:
        """Timestamp of last status update."""
        ts = self.get("last_update")
        if ts:
            return datetime.fromtimestamp(int(ts), tz=timezone.utc)
        return None

    @property
    def is_connected(self) -> bool:
        """Check if peer has had a recent handshake (within 3 minutes)."""
        if self.last_handshake is None:
            return False
        now = datetime.now(timezone.utc)
        age = (now - self.last_handshake).total_seconds()
        return age < 180  # 3 minutes

    def __repr__(self) -> str:
        connected = "connected" if self.is_connected else "disconnected"
        return (
            f"<WireGuardPeerStatus peer={self.peer_key} {connected} "
            f"tx={self.tx_bytes_formatted} rx={self.rx_bytes_formatted}>"
        )


class WireGuardPeerStatusManager(ResourceManager[WireGuardPeerStatus]):
    """Manager for WireGuard peer status.

    Provides access to real-time connection status for WireGuard peers.
    Scoped to a specific WireGuard interface.

    Example:
        >>> # List peer status for a WireGuard interface
        >>> for wg in network.wireguard.list():
        ...     for status in wg.peer_status.list():
        ...         if status.is_connected:
        ...             print(f"Peer {status.peer_key}: {status.tx_bytes_formatted} TX")
    """

    _endpoint = "vnet_wireguard_peer_status"

    _default_fields = [
        "$key",
        "peer",
        "last_handshake",
        "tx_bytes",
        "rx_bytes",
        "last_update",
    ]

    def __init__(self, client: VergeClient, wireguard: WireGuardInterface) -> None:
        super().__init__(client)
        self._wireguard = wireguard
        self._wireguard_key = wireguard.key

    def _to_model(self, data: dict[str, Any]) -> WireGuardPeerStatus:
        return WireGuardPeerStatus(data, self)

    def list(  # noqa: A002
        self,
        filter: str | None = None,  # noqa: A002
        fields: builtins.list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        **filter_kwargs: Any,
    ) -> builtins.list[WireGuardPeerStatus]:
        """List peer status for this WireGuard interface.

        Args:
            filter: OData filter string.
            fields: List of fields to return.
            limit: Maximum number of results.
            offset: Skip this many results.
            **filter_kwargs: Additional filter parameters (ignored for scoped manager).

        Returns:
            List of WireGuardPeerStatus objects.
        """
        # Note: filter_kwargs ignored - this is a wireguard-scoped manager
        _ = filter_kwargs

        if fields is None:
            fields = self._default_fields

        # Get peer IDs for this WireGuard interface
        peer_params: dict[str, Any] = {
            "filter": f"wireguard eq {self._wireguard_key}",
            "fields": "$key",
        }
        peer_response = self._client._request("GET", "vnet_wireguard_peers", params=peer_params)

        if not peer_response:
            return []

        peer_keys = []
        if isinstance(peer_response, list):
            peer_keys = [p.get("$key") for p in peer_response if p.get("$key")]
        elif isinstance(peer_response, dict) and peer_response.get("$key"):
            peer_keys = [peer_response["$key"]]

        if not peer_keys:
            return []

        # Query status for these peers
        peer_filter = " or ".join([f"peer eq {pk}" for pk in peer_keys])
        filters = [f"({peer_filter})"]
        if filter:
            filters.append(filter)

        params: dict[str, Any] = {
            "filter": " and ".join(filters),
            "fields": ",".join(fields),
        }

        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset

        response = self._client._request("GET", self._endpoint, params=params)

        if response is None:
            return []

        if isinstance(response, list):
            return [self._to_model(item) for item in response]

        return [self._to_model(response)]

    def get_for_peer(self, peer_key: int) -> WireGuardPeerStatus:
        """Get status for a specific peer.

        Args:
            peer_key: Peer $key (ID).

        Returns:
            WireGuardPeerStatus object.

        Raises:
            NotFoundError: If status not found for this peer.
        """
        params: dict[str, Any] = {
            "filter": f"peer eq {peer_key}",
            "fields": ",".join(self._default_fields),
            "limit": 1,
        }

        response = self._client._request("GET", self._endpoint, params=params)

        if response is None:
            raise NotFoundError(f"Status not found for peer {peer_key}")

        if isinstance(response, list):
            if not response:
                raise NotFoundError(f"Status not found for peer {peer_key}")
            return self._to_model(response[0])

        return self._to_model(response)
