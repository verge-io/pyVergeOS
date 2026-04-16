"""Machine NIC statistics, status, and fabric status resource managers."""

from __future__ import annotations

import builtins
from typing import TYPE_CHECKING, Any, Literal

from pyvergeos.exceptions import NotFoundError
from pyvergeos.resources.base import ResourceManager, ResourceObject

if TYPE_CHECKING:
    from pyvergeos.client import VergeClient

# NIC link status values
NicLinkStatus = Literal["up", "down", "unknown", "lowerlayerdown"]

# NIC fabric status values
NicFabricStatus = Literal["confirmed", "degraded", "no_path"]

# State display mapping
NIC_STATE_DISPLAY = {
    "online": "Online",
    "offline": "Offline",
    "warning": "Warning",
    "error": "Error",
}

# Link status display mapping
NIC_LINK_STATUS_DISPLAY = {
    "up": "Up",
    "down": "Down",
    "unknown": "Unknown",
    "lowerlayerdown": "Lower Layer Down",
}

# Fabric status display mapping
NIC_FABRIC_STATUS_DISPLAY = {
    "confirmed": "Confirmed",
    "degraded": "Degraded",
    "no_path": "No Path",
}

# Default fields
NIC_STATS_DEFAULT_FIELDS = [
    "$key",
    "parent_nic",
    "txpps",
    "rxpps",
    "txbps",
    "rxbps",
    "totalxbps",
    "tx_pckts",
    "rx_pckts",
    "tx_bytes",
    "rx_bytes",
    "tx_pckts_cur",
    "rx_pckts_cur",
    "tx_bytes_cur",
    "rx_bytes_cur",
    "last_update",
]

NIC_STATUS_DEFAULT_FIELDS = [
    "$key",
    "parent_nic",
    "status",
    "state",
    "speed",
    "last_update",
]

NIC_FABRIC_STATUS_DEFAULT_FIELDS = [
    "$key",
    "parent_nic",
    "status",
    "state",
    "max_score",
    "min_score",
    "paths",
    "created",
    "modified",
]


def _format_bps(bps: int | float) -> str:
    """Format bits per second to human-readable string.

    Args:
        bps: Bits per second value.

    Returns:
        Formatted string like "1.23 Gbps".
    """
    if not bps:
        return "0 bps"
    units = ["bps", "Kbps", "Mbps", "Gbps", "Tbps"]
    unit_index = 0
    value = float(bps)
    while value >= 1000 and unit_index < len(units) - 1:
        value /= 1000
        unit_index += 1
    return f"{value:.2f} {units[unit_index]}"


class MachineNicStats(ResourceObject):
    """Machine NIC statistics resource object.

    Provides real-time and cumulative traffic counters for a NIC.
    """

    @property
    def nic_key(self) -> int:
        """Parent NIC key."""
        return int(self.get("parent_nic", 0))

    @property
    def tx_pps(self) -> int:
        """Transmit packets per second."""
        return int(self.get("txpps") or 0)

    @property
    def rx_pps(self) -> int:
        """Receive packets per second."""
        return int(self.get("rxpps") or 0)

    @property
    def tx_bps(self) -> int:
        """Transmit bits per second."""
        return int(self.get("txbps") or 0)

    @property
    def rx_bps(self) -> int:
        """Receive bits per second."""
        return int(self.get("rxbps") or 0)

    @property
    def total_bps(self) -> int:
        """Total (TX + RX) bits per second."""
        return int(self.get("totalxbps") or 0)

    @property
    def tx_packets(self) -> int:
        """Total transmitted packets."""
        return int(self.get("tx_pckts") or 0)

    @property
    def rx_packets(self) -> int:
        """Total received packets."""
        return int(self.get("rx_pckts") or 0)

    @property
    def tx_bytes(self) -> int:
        """Total transmitted bytes."""
        return int(self.get("tx_bytes") or 0)

    @property
    def rx_bytes(self) -> int:
        """Total received bytes."""
        return int(self.get("rx_bytes") or 0)

    @property
    def tx_packets_current(self) -> int:
        """Current period transmitted packets."""
        return int(self.get("tx_pckts_cur") or 0)

    @property
    def rx_packets_current(self) -> int:
        """Current period received packets."""
        return int(self.get("rx_pckts_cur") or 0)

    @property
    def tx_bytes_current(self) -> int:
        """Current period transmitted bytes."""
        return int(self.get("tx_bytes_cur") or 0)

    @property
    def rx_bytes_current(self) -> int:
        """Current period received bytes."""
        return int(self.get("rx_bytes_cur") or 0)

    @property
    def tx_bps_display(self) -> str:
        """Formatted transmit rate."""
        return _format_bps(self.tx_bps)

    @property
    def rx_bps_display(self) -> str:
        """Formatted receive rate."""
        return _format_bps(self.rx_bps)

    @property
    def total_bps_display(self) -> str:
        """Formatted total rate."""
        return _format_bps(self.total_bps)


class MachineNicStatus(ResourceObject):
    """Machine NIC link status resource object."""

    @property
    def nic_key(self) -> int:
        """Parent NIC key."""
        return int(self.get("parent_nic", 0))

    @property
    def link_status(self) -> str:
        """Link status (up/down/unknown/lowerlayerdown)."""
        return str(self.get("status", "unknown"))

    @property
    def link_status_display(self) -> str:
        """Human-readable link status."""
        return NIC_LINK_STATUS_DISPLAY.get(self.link_status, self.link_status)

    @property
    def state(self) -> str:
        """Derived state (online/offline/warning/error)."""
        return str(self.get("state", "offline"))

    @property
    def state_display(self) -> str:
        """Human-readable state."""
        return NIC_STATE_DISPLAY.get(self.state, self.state)

    @property
    def is_up(self) -> bool:
        """Check if NIC link is up."""
        return self.link_status == "up"

    @property
    def speed(self) -> int:
        """Link speed in Mbps."""
        return int(self.get("speed") or 0)

    @property
    def speed_display(self) -> str:
        """Formatted link speed."""
        speed = self.speed
        if not speed:
            return "Unknown"
        if speed >= 1000:
            return f"{speed // 1000} Gbps"
        return f"{speed} Mbps"


class MachineNicFabricStatus(ResourceObject):
    """Machine NIC fabric status resource object.

    Fabric status tracks the health of the VergeOS storage fabric
    path through a NIC.
    """

    @property
    def nic_key(self) -> int:
        """Parent NIC key."""
        return int(self.get("parent_nic", 0))

    @property
    def fabric_status(self) -> str:
        """Fabric status (confirmed/degraded/no_path)."""
        return str(self.get("status", "no_path"))

    @property
    def fabric_status_display(self) -> str:
        """Human-readable fabric status."""
        return NIC_FABRIC_STATUS_DISPLAY.get(self.fabric_status, self.fabric_status)

    @property
    def state(self) -> str:
        """Derived state (online/offline/warning/error)."""
        return str(self.get("state", "offline"))

    @property
    def state_display(self) -> str:
        """Human-readable state."""
        return NIC_STATE_DISPLAY.get(self.state, self.state)

    @property
    def is_healthy(self) -> bool:
        """Check if fabric path is fully confirmed."""
        return self.fabric_status == "confirmed"

    @property
    def is_degraded(self) -> bool:
        """Check if fabric path is degraded."""
        return self.fabric_status == "degraded"

    @property
    def max_score(self) -> float:
        """Maximum fabric score."""
        return float(self.get("max_score") or 0)

    @property
    def min_score(self) -> float:
        """Minimum fabric score."""
        return float(self.get("min_score") or 0)

    @property
    def paths(self) -> dict[str, Any] | builtins.list[Any] | None:
        """Fabric path information (JSON)."""
        return self.get("paths")


class MachineNicStatsManager(ResourceManager[MachineNicStats]):
    """Manager for machine NIC traffic statistics.

    Read-only — stats are updated by the system.

    Examples:
        Get current stats for a NIC::

            stats = nic.stats.get()
            print(f"TX: {stats.tx_bps_display}, RX: {stats.rx_bps_display}")

        Access from client directly::

            stats_list = client.machine_nic_stats.list(
                filter="parent_nic eq 42"
            )
    """

    _endpoint = "machine_nic_stats"
    _default_fields = NIC_STATS_DEFAULT_FIELDS

    def __init__(self, client: VergeClient, nic_key: int | None = None) -> None:
        super().__init__(client)
        self._nic_key = nic_key

    def _to_model(self, data: dict[str, Any]) -> MachineNicStats:
        return MachineNicStats(data, self)

    def get(  # type: ignore[override]
        self,
        key: int | None = None,
        *,
        fields: builtins.list[str] | None = None,
    ) -> MachineNicStats:
        """Get NIC statistics.

        When scoped to a NIC (via nic_key), returns stats for that NIC.
        When called with a key, fetches by $key directly.

        Args:
            key: Stats record $key (optional if scoped to a NIC).
            fields: List of fields to return.

        Returns:
            MachineNicStats object.

        Raises:
            NotFoundError: If stats not found.
        """
        if fields is None:
            fields = self._default_fields

        if key is not None:
            params: dict[str, Any] = {"fields": ",".join(fields)}
            response = self._client._request("GET", f"{self._endpoint}/{key}", params=params)
            if response is None:
                raise NotFoundError(f"NIC stats {key} not found")
            if not isinstance(response, dict):
                raise NotFoundError(f"NIC stats {key} returned invalid response")
            return self._to_model(response)

        if self._nic_key is not None:
            params = {
                "filter": f"parent_nic eq {self._nic_key}",
                "fields": ",".join(fields),
                "limit": 1,
            }
            response = self._client._request("GET", self._endpoint, params=params)
            if response is None:
                raise NotFoundError(f"Stats not found for NIC {self._nic_key}")
            if isinstance(response, list):
                if not response:
                    raise NotFoundError(f"Stats not found for NIC {self._nic_key}")
                return self._to_model(response[0])
            return self._to_model(response)

        raise ValueError("Either key or scoped nic_key required")


class MachineNicStatusManager(ResourceManager[MachineNicStatus]):
    """Manager for machine NIC link status.

    Read-only — status is updated by the system.

    Examples:
        Get current link status for a NIC::

            status = nic.link_status.get()
            print(f"Link: {status.link_status_display} at {status.speed_display}")
    """

    _endpoint = "machine_nic_status"
    _default_fields = NIC_STATUS_DEFAULT_FIELDS

    def __init__(self, client: VergeClient, nic_key: int | None = None) -> None:
        super().__init__(client)
        self._nic_key = nic_key

    def _to_model(self, data: dict[str, Any]) -> MachineNicStatus:
        return MachineNicStatus(data, self)

    def get(  # type: ignore[override]
        self,
        key: int | None = None,
        *,
        fields: builtins.list[str] | None = None,
    ) -> MachineNicStatus:
        """Get NIC link status.

        Args:
            key: Status record $key (optional if scoped to a NIC).
            fields: List of fields to return.

        Returns:
            MachineNicStatus object.

        Raises:
            NotFoundError: If status not found.
        """
        if fields is None:
            fields = self._default_fields

        if key is not None:
            params: dict[str, Any] = {"fields": ",".join(fields)}
            response = self._client._request("GET", f"{self._endpoint}/{key}", params=params)
            if response is None:
                raise NotFoundError(f"NIC status {key} not found")
            if not isinstance(response, dict):
                raise NotFoundError(f"NIC status {key} returned invalid response")
            return self._to_model(response)

        if self._nic_key is not None:
            params = {
                "filter": f"parent_nic eq {self._nic_key}",
                "fields": ",".join(fields),
                "limit": 1,
            }
            response = self._client._request("GET", self._endpoint, params=params)
            if response is None:
                raise NotFoundError(f"Status not found for NIC {self._nic_key}")
            if isinstance(response, list):
                if not response:
                    raise NotFoundError(f"Status not found for NIC {self._nic_key}")
                return self._to_model(response[0])
            return self._to_model(response)

        raise ValueError("Either key or scoped nic_key required")


class MachineNicFabricStatusManager(ResourceManager[MachineNicFabricStatus]):
    """Manager for machine NIC fabric status.

    Read-only — fabric status is updated by the system.
    Tracks storage fabric path health through physical NICs.

    Examples:
        Get fabric status for a NIC::

            fabric = nic.fabric_status.get()
            print(f"Fabric: {fabric.fabric_status_display}")
            if not fabric.is_healthy:
                print(f"Score: {fabric.min_score}-{fabric.max_score}")
    """

    _endpoint = "machine_nic_fabric_status"
    _default_fields = NIC_FABRIC_STATUS_DEFAULT_FIELDS

    def __init__(self, client: VergeClient, nic_key: int | None = None) -> None:
        super().__init__(client)
        self._nic_key = nic_key

    def _to_model(self, data: dict[str, Any]) -> MachineNicFabricStatus:
        return MachineNicFabricStatus(data, self)

    def get(  # type: ignore[override]
        self,
        key: int | None = None,
        *,
        fields: builtins.list[str] | None = None,
    ) -> MachineNicFabricStatus:
        """Get NIC fabric status.

        Args:
            key: Fabric status record $key (optional if scoped to a NIC).
            fields: List of fields to return.

        Returns:
            MachineNicFabricStatus object.

        Raises:
            NotFoundError: If fabric status not found.
        """
        if fields is None:
            fields = self._default_fields

        if key is not None:
            params: dict[str, Any] = {"fields": ",".join(fields)}
            response = self._client._request("GET", f"{self._endpoint}/{key}", params=params)
            if response is None:
                raise NotFoundError(f"NIC fabric status {key} not found")
            if not isinstance(response, dict):
                raise NotFoundError(f"NIC fabric status {key} returned invalid response")
            return self._to_model(response)

        if self._nic_key is not None:
            params = {
                "filter": f"parent_nic eq {self._nic_key}",
                "fields": ",".join(fields),
                "limit": 1,
            }
            response = self._client._request("GET", self._endpoint, params=params)
            if response is None:
                raise NotFoundError(f"Fabric status not found for NIC {self._nic_key}")
            if isinstance(response, list):
                if not response:
                    raise NotFoundError(f"Fabric status not found for NIC {self._nic_key}")
                return self._to_model(response[0])
            return self._to_model(response)

        raise ValueError("Either key or scoped nic_key required")
