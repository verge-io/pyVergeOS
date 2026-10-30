"""Time settings and the time dashboard (VergeOS 26.2).

``time_settings`` is the singleton NTP/PTP configuration. ``time_dashboard``
is the read-only view of that configuration, each physical node's sync
status, and the alarms raised when a node stays out of sync.
"""

from __future__ import annotations

import builtins
from typing import TYPE_CHECKING, Any, Literal

from pyvergeos.exceptions import NotFoundError
from pyvergeos.resources.base import ResourceManager, ResourceObject

if TYPE_CHECKING:
    pass

TimeMode = Literal["ntp", "ptp"]
PtpTransport = Literal["udpv4", "udpv6", "l2"]
PtpDelayMechanism = Literal["e2e", "p2p", "auto"]

# Columns on the time_settings singleton. Names follow the Time Settings
# form: mode, the NTP server list and clock limits, and every PTP option
# from the basic and advanced panels.
TIME_SETTINGS_FIELDS = [
    "$key",
    "mode",
    "ntp_servers",
    "ntp_max_clocks",
    "ntp_min_clocks",
    "ntp_min_sane",
    "ptp_interface_network",
    "ptp_transport",
    "ptp_domain",
    "ptp_delay_mechanism",
    "ptp_hardware_timestamps",
    "ptp_priority1",
    "ptp_priority2",
    "ptp_two_step",
    "ptp_log_sync_interval",
    "ptp_log_announce_interval",
    "ptp_log_min_delay_req_interval",
    "ptp_log_min_pdelay_req_interval",
    "ptp_unicast",
    "ptp_dscp_event",
    "ptp_dscp_general",
    "ptp_master_only",
    "ptp_inhibit_announce",
    "ptp_inhibit_delay_req",
    "ptp_follow_up_info",
    "ptp_transport_specific",
    "ptp_neighbor_prop_delay",
    "ptp_sync_receipt_timeout",
    "ptp_announce_receipt_timeout",
]

_TIME_SETTINGS_WRITABLE = [name for name in TIME_SETTINGS_FIELDS if name != "$key"]


class TimeSettings(ResourceObject):
    """NTP and PTP configuration for the system.

    There is one row. Node 1 follows the configured servers (or the PTP
    grandmaster). The other nodes follow node 1. PTP replaces NTP while it
    is selected.
    """

    @property
    def mode(self) -> str:
        """``ntp`` or ``ptp``."""
        return str(self.get("mode", "ntp"))

    @property
    def is_ntp(self) -> bool:
        """Whether the system is using NTP."""
        return self.mode == "ntp"

    @property
    def is_ptp(self) -> bool:
        """Whether the system is using PTP."""
        return self.mode == "ptp"

    @property
    def ntp_servers(self) -> str:
        """Space-separated NTP server names or addresses."""
        return str(self.get("ntp_servers", ""))

    @property
    def ntp_max_clocks(self) -> int:
        """Maximum number of NTP sources. Server default is 11."""
        return int(self.get("ntp_max_clocks", 0) or 0)

    @property
    def ntp_min_clocks(self) -> int:
        """Minimum number of NTP sources NTP tries to use. Default is 4."""
        return int(self.get("ntp_min_clocks", 0) or 0)

    @property
    def ntp_min_sane(self) -> int:
        """Minimum number of NTP sources that must agree. Default is 1."""
        return int(self.get("ntp_min_sane", 0) or 0)

    @property
    def ptp_interface_network(self) -> int | None:
        """Physical network that carries PTP traffic."""
        value = self.get("ptp_interface_network")
        return int(value) if value else None

    @property
    def ptp_transport(self) -> str:
        """PTP transport: ``udpv4``, ``udpv6``, or ``l2``."""
        return str(self.get("ptp_transport", ""))

    @property
    def ptp_domain(self) -> int:
        """PTP domain number, 0-127."""
        return int(self.get("ptp_domain", 0) or 0)

    @property
    def ptp_delay_mechanism(self) -> str:
        """Path-delay measurement: ``e2e``, ``p2p``, or ``auto``."""
        return str(self.get("ptp_delay_mechanism", ""))

    @property
    def ptp_hardware_timestamps(self) -> bool:
        """Whether ptp4l uses NIC hardware timestamps.

        On is the server default. Turn it off when the NICs cannot timestamp
        in hardware. VergeOS does not fall back on its own.
        """
        return bool(self.get("ptp_hardware_timestamps", False))

    @property
    def ptp_priority1(self) -> int:
        """BMCA clock priority 1. Lower is more preferred. Default 128."""
        return int(self.get("ptp_priority1", 0) or 0)

    @property
    def ptp_priority2(self) -> int:
        """BMCA clock priority 2, the tie-breaker. Default 128."""
        return int(self.get("ptp_priority2", 0) or 0)

    @property
    def ptp_two_step(self) -> bool:
        """Whether the timestamp is sent in a Follow_Up message."""
        return bool(self.get("ptp_two_step", False))

    @property
    def ptp_log_sync_interval(self) -> int:
        """Sync message rate as log2 seconds. 0 is one second."""
        return int(self.get("ptp_log_sync_interval", 0) or 0)

    @property
    def ptp_log_announce_interval(self) -> int:
        """Announce message rate as log2 seconds."""
        return int(self.get("ptp_log_announce_interval", 0) or 0)

    @property
    def ptp_log_min_delay_req_interval(self) -> int:
        """Minimum delay-request rate as log2 seconds, used with E2E."""
        return int(self.get("ptp_log_min_delay_req_interval", 0) or 0)

    @property
    def ptp_log_min_pdelay_req_interval(self) -> int:
        """Minimum peer-delay rate as log2 seconds, used with P2P."""
        return int(self.get("ptp_log_min_pdelay_req_interval", 0) or 0)

    @property
    def ptp_unicast(self) -> bool:
        """Whether PTP uses unicast instead of multicast."""
        return bool(self.get("ptp_unicast", False))

    @property
    def ptp_dscp_event(self) -> int:
        """DSCP for PTP event messages on port 319."""
        return int(self.get("ptp_dscp_event", 0) or 0)

    @property
    def ptp_dscp_general(self) -> int:
        """DSCP for PTP general messages on port 320."""
        return int(self.get("ptp_dscp_general", 0) or 0)

    @property
    def ptp_master_only(self) -> bool:
        """Whether this port always acts as master and skips BMCA."""
        return bool(self.get("ptp_master_only", False))

    @property
    def ptp_inhibit_announce(self) -> bool:
        """Whether Announce messages are suppressed."""
        return bool(self.get("ptp_inhibit_announce", False))

    @property
    def ptp_inhibit_delay_req(self) -> bool:
        """Whether Delay Request messages are suppressed."""
        return bool(self.get("ptp_inhibit_delay_req", False))

    @property
    def ptp_follow_up_info(self) -> bool:
        """Whether Follow_Up messages include the follow-up information TLV."""
        return bool(self.get("ptp_follow_up_info", False))

    @property
    def ptp_transport_specific(self) -> int:
        """PTP transportSpecific field. 802.1AS typically uses 1."""
        return int(self.get("ptp_transport_specific", 0) or 0)

    @property
    def ptp_neighbor_prop_delay(self) -> int:
        """Maximum neighbor propagation delay, in nanoseconds."""
        return int(self.get("ptp_neighbor_prop_delay", 0) or 0)

    @property
    def ptp_sync_receipt_timeout(self) -> int:
        """Sync intervals before a timeout. 0 disables the timeout."""
        return int(self.get("ptp_sync_receipt_timeout", 0) or 0)

    @property
    def ptp_announce_receipt_timeout(self) -> int:
        """Announce intervals before a timeout."""
        return int(self.get("ptp_announce_receipt_timeout", 0) or 0)

    def __repr__(self) -> str:
        return f"<TimeSettings mode={self.mode!r}>"


class TimeSettingsManager(ResourceManager[TimeSettings]):
    """Manager for the ``time_settings`` singleton.

    VergeOS 26.2 and later. ``get()`` reads the row. ``update()`` changes
    the fields you pass and leaves the rest alone.

    Example:
        >>> settings = client.time_settings.get()
        >>> print(settings.mode, settings.ntp_servers)
        >>> client.time_settings.update(ntp_servers="ntp1.example.com ntp2.example.com")
    """

    _endpoint = "time_settings"
    _default_fields = TIME_SETTINGS_FIELDS

    def _to_model(self, data: dict[str, Any]) -> TimeSettings:
        return TimeSettings(data, self)

    def get(  # type: ignore[override]
        self,
        key: int | None = None,
        *,
        fields: str | builtins.list[str] | None = None,
    ) -> TimeSettings:
        """Read the time settings.

        Args:
            key: Row key. The singleton is key 1, which is the default.
            fields: Fields to return. Defaults to every time setting.

        Returns:
            TimeSettings object.
        """
        row_key = 1 if key is None else key
        selected = self._default_fields if fields is None else fields
        params: dict[str, Any] = {"fields": self._projection(selected)}
        response = self._client._request("GET", f"{self._endpoint}/{row_key}", params=params)
        if response is None or not isinstance(response, dict):
            raise NotFoundError("Time settings not found")
        return self._to_model(response)

    def update(  # type: ignore[override]
        self,
        key: int | None = None,
        *,
        mode: TimeMode | None = None,
        ntp_servers: str | None = None,
        ntp_max_clocks: int | None = None,
        ntp_min_clocks: int | None = None,
        ntp_min_sane: int | None = None,
        ptp_interface_network: int | None = None,
        ptp_transport: PtpTransport | None = None,
        ptp_domain: int | None = None,
        ptp_delay_mechanism: PtpDelayMechanism | None = None,
        ptp_hardware_timestamps: bool | None = None,
        ptp_priority1: int | None = None,
        ptp_priority2: int | None = None,
        ptp_two_step: bool | None = None,
        ptp_log_sync_interval: int | None = None,
        ptp_log_announce_interval: int | None = None,
        ptp_log_min_delay_req_interval: int | None = None,
        ptp_log_min_pdelay_req_interval: int | None = None,
        ptp_unicast: bool | None = None,
        ptp_dscp_event: int | None = None,
        ptp_dscp_general: int | None = None,
        ptp_master_only: bool | None = None,
        ptp_inhibit_announce: bool | None = None,
        ptp_inhibit_delay_req: bool | None = None,
        ptp_follow_up_info: bool | None = None,
        ptp_transport_specific: int | None = None,
        ptp_neighbor_prop_delay: int | None = None,
        ptp_sync_receipt_timeout: int | None = None,
        ptp_announce_receipt_timeout: int | None = None,
    ) -> TimeSettings:
        """Change time settings.

        Only arguments you pass are written. Switching ``mode`` to ``ptp``
        stops NTP, so set the PTP interface and profile in the same call
        when you make that change.

        Args:
            key: Row key. Defaults to the singleton key 1.
            mode: ``ntp`` or ``ptp``.
            ntp_servers: Space-separated NTP servers.
            ntp_max_clocks: Maximum NTP sources (1-255).
            ntp_min_clocks: Minimum NTP sources NTP tries to use (1-255).
            ntp_min_sane: Minimum agreeing NTP sources (1-255).
            ptp_interface_network: Physical network key that carries PTP.
            ptp_transport: ``udpv4``, ``udpv6``, or ``l2``.
            ptp_domain: PTP domain, 0-127.
            ptp_delay_mechanism: ``e2e``, ``p2p``, or ``auto``.
            ptp_hardware_timestamps: Use NIC hardware timestamps.
            ptp_priority1: BMCA priority 1 (0-255, lower wins).
            ptp_priority2: BMCA priority 2 (0-255).
            ptp_two_step: Send the timestamp in a Follow_Up message.
            ptp_log_sync_interval: Sync rate as log2 seconds.
            ptp_log_announce_interval: Announce rate as log2 seconds.
            ptp_log_min_delay_req_interval: E2E delay-request rate.
            ptp_log_min_pdelay_req_interval: P2P peer-delay rate.
            ptp_unicast: Use unicast PTP.
            ptp_dscp_event: DSCP for event messages (0-63).
            ptp_dscp_general: DSCP for general messages (0-63).
            ptp_master_only: Always act as master and disable BMCA.
            ptp_inhibit_announce: Stop Announce messages.
            ptp_inhibit_delay_req: Stop Delay Request messages.
            ptp_follow_up_info: Add the follow-up information TLV.
            ptp_transport_specific: transportSpecific field (0-255).
            ptp_neighbor_prop_delay: Max neighbor delay in nanoseconds.
            ptp_sync_receipt_timeout: Sync intervals before timeout.
            ptp_announce_receipt_timeout: Announce intervals before timeout.

        Returns:
            Updated TimeSettings object.
        """
        values = {
            "mode": mode,
            "ntp_servers": ntp_servers,
            "ntp_max_clocks": ntp_max_clocks,
            "ntp_min_clocks": ntp_min_clocks,
            "ntp_min_sane": ntp_min_sane,
            "ptp_interface_network": ptp_interface_network,
            "ptp_transport": ptp_transport,
            "ptp_domain": ptp_domain,
            "ptp_delay_mechanism": ptp_delay_mechanism,
            "ptp_hardware_timestamps": ptp_hardware_timestamps,
            "ptp_priority1": ptp_priority1,
            "ptp_priority2": ptp_priority2,
            "ptp_two_step": ptp_two_step,
            "ptp_log_sync_interval": ptp_log_sync_interval,
            "ptp_log_announce_interval": ptp_log_announce_interval,
            "ptp_log_min_delay_req_interval": ptp_log_min_delay_req_interval,
            "ptp_log_min_pdelay_req_interval": ptp_log_min_pdelay_req_interval,
            "ptp_unicast": ptp_unicast,
            "ptp_dscp_event": ptp_dscp_event,
            "ptp_dscp_general": ptp_dscp_general,
            "ptp_master_only": ptp_master_only,
            "ptp_inhibit_announce": ptp_inhibit_announce,
            "ptp_inhibit_delay_req": ptp_inhibit_delay_req,
            "ptp_follow_up_info": ptp_follow_up_info,
            "ptp_transport_specific": ptp_transport_specific,
            "ptp_neighbor_prop_delay": ptp_neighbor_prop_delay,
            "ptp_sync_receipt_timeout": ptp_sync_receipt_timeout,
            "ptp_announce_receipt_timeout": ptp_announce_receipt_timeout,
        }
        body = {name: value for name, value in values.items() if value is not None}
        row_key = 1 if key is None else key
        if body:
            self._client._request("PUT", f"{self._endpoint}/{row_key}", json_data=body)
        return self.get(row_key)


class TimeNodeSync:
    """One physical node's time sync status from the dashboard."""

    def __init__(self, data: dict[str, Any]) -> None:
        self._data = data

    @property
    def node_key(self) -> int | None:
        """Node ``$key``, when the row carries one."""
        value = self._data.get("node", self._data.get("$key"))
        return int(value) if value else None

    @property
    def name(self) -> str:
        """Node name."""
        return str(self._data.get("name", ""))

    @property
    def source(self) -> str:
        """Time source this node is following."""
        value = self._data.get("source", self._data.get("time_source", ""))
        return str(value or "")

    @property
    def synced(self) -> bool:
        """Whether the node is currently synchronized."""
        if "synced" in self._data:
            return bool(self._data.get("synced"))
        status = str(self._data.get("status", "")).lower()
        return status in ("synced", "sync", "ok", "online")

    @property
    def status(self) -> str:
        """Raw status string from the dashboard."""
        return str(self._data.get("status", ""))

    @property
    def last_check(self) -> int | None:
        """Unix time of the last check, when present."""
        value = self._data.get("last_check", self._data.get("last_update"))
        return int(value) if value else None

    def __repr__(self) -> str:
        return f"<TimeNodeSync node={self.node_key} synced={self.synced}>"


class TimeDashboard(ResourceObject):
    """Read-only time view: settings, per-node sync, and related alarms."""

    @property
    def settings(self) -> dict[str, Any]:
        """Embedded time settings, or an empty dict."""
        value = self.get("settings")
        return value if isinstance(value, dict) else {}

    @property
    def mode(self) -> str:
        """Current mode, from the dashboard or its embedded settings."""
        if self.get("mode"):
            return str(self.get("mode"))
        return str(self.settings.get("mode", ""))

    @property
    def nodes(self) -> list[TimeNodeSync]:
        """Physical-node synchronization rows."""
        value = self.get("nodes")
        if value is None:
            value = self.get("node_status")
        if not isinstance(value, list):
            return []
        return [TimeNodeSync(item) for item in value if isinstance(item, dict)]

    @property
    def alarms(self) -> list[dict[str, Any]]:
        """Alarms included on the time dashboard."""
        value = self.get("alarms")
        if not isinstance(value, list):
            return []
        return [item for item in value if isinstance(item, dict)]

    def __repr__(self) -> str:
        return f"<TimeDashboard mode={self.mode!r} nodes={len(self.nodes)}>"


class TimeDashboardManager(ResourceManager[TimeDashboard]):
    """Manager for the read-only ``time_dashboard`` view.

    Example:
        >>> dashboard = client.time_dashboard.get()
        >>> for node in dashboard.nodes:
        ...     print(node.name, "synced" if node.synced else "out of sync")
    """

    _endpoint = "time_dashboard"

    def _to_model(self, data: dict[str, Any]) -> TimeDashboard:
        return TimeDashboard(data, self)

    def get(self) -> TimeDashboard:  # type: ignore[override]
        """Read the time dashboard.

        A single document is used as-is. A list of node rows, which is how
        some status views answer, is wrapped so ``nodes`` still works.
        """
        response = self._client._request("GET", self._endpoint)
        if response is None:
            return self._to_model({})
        if isinstance(response, list):
            if (
                len(response) == 1
                and isinstance(response[0], dict)
                and any(name in response[0] for name in ("settings", "nodes", "alarms", "mode"))
            ):
                return self._to_model(response[0])
            rows = [item for item in response if isinstance(item, dict)]
            return self._to_model({"nodes": rows})
        if isinstance(response, dict):
            return self._to_model(response)
        return self._to_model({})


# Kept so a typo in the writable set fails a test instead of a request.
assert set(_TIME_SETTINGS_WRITABLE) <= set(TIME_SETTINGS_FIELDS)
