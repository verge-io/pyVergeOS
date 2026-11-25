"""Time settings and the time dashboard (VergeOS 26.2).

``time_settings`` is the singleton NTP/PTP configuration. ``time_dashboard``
is the read-only view of that configuration, each physical node's sync
status, and the alarms raised when a node stays out of sync.
"""

from __future__ import annotations

import builtins
from typing import Any, Literal

from pyvergeos.exceptions import NotFoundError
from pyvergeos.resources.base import ResourceManager, ResourceObject, reference_key

TimeMode = Literal["ntp", "ptp"]
PtpTransport = Literal["udpv4", "udpv6", "l2"]
PtpDelayMechanism = Literal["e2e", "p2p", "auto"]

# The singleton is addressed as time_settings/self, not a numeric row.
TIME_SETTINGS_KEY = "self"

# Columns on the time_settings singleton, using the live 26.2 names.
TIME_SETTINGS_FIELDS = [
    "$key",
    "mode",
    "ntp_servers",
    "ntp_maxclock",
    "ntp_minclock",
    "ntp_minsane",
    "interface_vnet",
    "ptp_transport",
    "ptp_domain",
    "ptp_delay_mechanism",
    "ptp_use_hw_timestamps",
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
    "ptp_neighbor_prop_delay_thresh",
    "ptp_sync_receipt_timeout",
    "ptp_announce_receipt_timeout",
]

_TIME_SETTINGS_WRITABLE = [name for name in TIME_SETTINGS_FIELDS if name != "$key"]


class TimeSettings(ResourceObject):
    """NTP and PTP configuration for the system.

    There is one row, and its key is the text ``self``. Node 1 follows the
    configured servers (or the PTP grandmaster). The other nodes follow
    node 1. PTP replaces NTP while it is selected.
    """

    @property
    def key(self) -> str:  # type: ignore[override]
        """Singleton key. Always the text ``self`` once the row is loaded."""
        value = self.get("$key")
        if value is None:
            raise ValueError("Resource has no $key - may not be persisted")
        return str(value)

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
    def ntp_maxclock(self) -> int:
        """Maximum number of NTP sources. Server default is 11."""
        return int(self.get("ntp_maxclock", 0) or 0)

    @property
    def ntp_minclock(self) -> int:
        """Minimum number of NTP sources NTP tries to use. Default is 4."""
        return int(self.get("ntp_minclock", 0) or 0)

    @property
    def ntp_minsane(self) -> int:
        """Minimum number of NTP sources that must agree. Default is 1."""
        return int(self.get("ntp_minsane", 0) or 0)

    @property
    def interface_vnet(self) -> int | None:
        """Physical network that carries PTP traffic.

        A row reference to ``vnets``. None when PTP has no interface yet.
        """
        value = reference_key(self.get("interface_vnet"))
        if isinstance(value, int):
            return value
        return None

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
    def ptp_use_hw_timestamps(self) -> bool:
        """Whether ptp4l uses NIC hardware timestamps.

        On is the server default. Turn it off when the NICs cannot timestamp
        in hardware. VergeOS does not fall back on its own.
        """
        return bool(self.get("ptp_use_hw_timestamps", False))

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
    def ptp_neighbor_prop_delay_thresh(self) -> int:
        """Maximum neighbor propagation delay, in nanoseconds."""
        return int(self.get("ptp_neighbor_prop_delay_thresh", 0) or 0)

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
        key: str | None = None,
        *,
        fields: str | builtins.list[str] | None = None,
    ) -> TimeSettings:
        """Read the time settings.

        Args:
            key: Row key. The singleton is the text ``self``, which is the
                default.
            fields: Fields to return. Defaults to every time setting.

        Returns:
            TimeSettings object.
        """
        row_key = TIME_SETTINGS_KEY if key is None else key
        selected = self._default_fields if fields is None else fields
        params: dict[str, Any] = {"fields": self._projection(selected)}
        response = self._client._request("GET", f"{self._endpoint}/{row_key}", params=params)
        if response is None or not isinstance(response, dict):
            raise NotFoundError("Time settings not found")
        return self._to_model(response)

    def update(  # type: ignore[override]
        self,
        key: str | None = None,
        *,
        mode: TimeMode | None = None,
        ntp_servers: str | None = None,
        ntp_maxclock: int | None = None,
        ntp_minclock: int | None = None,
        ntp_minsane: int | None = None,
        interface_vnet: int | None = None,
        ptp_transport: PtpTransport | None = None,
        ptp_domain: int | None = None,
        ptp_delay_mechanism: PtpDelayMechanism | None = None,
        ptp_use_hw_timestamps: bool | None = None,
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
        ptp_neighbor_prop_delay_thresh: int | None = None,
        ptp_sync_receipt_timeout: int | None = None,
        ptp_announce_receipt_timeout: int | None = None,
    ) -> TimeSettings:
        """Change time settings.

        Only arguments you pass are written. Switching ``mode`` to ``ptp``
        stops NTP, so set the PTP interface and profile in the same call
        when you make that change.

        Args:
            key: Row key. Defaults to ``self``.
            mode: ``ntp`` or ``ptp``.
            ntp_servers: Space-separated NTP servers.
            ntp_maxclock: Maximum NTP sources (1-255).
            ntp_minclock: Minimum NTP sources NTP tries to use (1-255).
            ntp_minsane: Minimum agreeing NTP sources (1-255).
            interface_vnet: Physical network key that carries PTP.
            ptp_transport: ``udpv4``, ``udpv6``, or ``l2``.
            ptp_domain: PTP domain, 0-127.
            ptp_delay_mechanism: ``e2e``, ``p2p``, or ``auto``.
            ptp_use_hw_timestamps: Use NIC hardware timestamps.
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
            ptp_neighbor_prop_delay_thresh: Max neighbor delay in nanoseconds.
            ptp_sync_receipt_timeout: Sync intervals before timeout.
            ptp_announce_receipt_timeout: Announce intervals before timeout.

        Returns:
            Updated TimeSettings object.
        """
        values = {
            "mode": mode,
            "ntp_servers": ntp_servers,
            "ntp_maxclock": ntp_maxclock,
            "ntp_minclock": ntp_minclock,
            "ntp_minsane": ntp_minsane,
            "interface_vnet": interface_vnet,
            "ptp_transport": ptp_transport,
            "ptp_domain": ptp_domain,
            "ptp_delay_mechanism": ptp_delay_mechanism,
            "ptp_use_hw_timestamps": ptp_use_hw_timestamps,
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
            "ptp_neighbor_prop_delay_thresh": ptp_neighbor_prop_delay_thresh,
            "ptp_sync_receipt_timeout": ptp_sync_receipt_timeout,
            "ptp_announce_receipt_timeout": ptp_announce_receipt_timeout,
        }
        body = {name: value for name, value in values.items() if value is not None}
        row_key = TIME_SETTINGS_KEY if key is None else key
        if body:
            self._client._request("PUT", f"{self._endpoint}/{row_key}", json_data=body)
        return self.get(row_key)


class TimeNodeSync:
    """One physical node from the time dashboard.

    The dashboard nests each node's sync payload at
    ``machine.status.time_sync_status``. That value is a JSON object while
    the node is reporting, and ``[]`` when it has nothing to report.
    """

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
    def time_sync_status(self) -> dict[str, Any] | list[Any]:
        """Sync payload from ``machine.status.time_sync_status``.

        A dict while the node is reporting, or an empty list when it is not.
        """
        machine = self._data.get("machine")
        if not isinstance(machine, dict):
            return []
        status = machine.get("status")
        if not isinstance(status, dict):
            return []
        value = status.get("time_sync_status", [])
        if isinstance(value, dict):
            return value
        if isinstance(value, list):
            return value
        return []

    @property
    def source(self) -> str:
        """Time source this node is following, when the payload names one."""
        status = self.time_sync_status
        if not isinstance(status, dict):
            return ""
        value = status.get("source", status.get("time_source", ""))
        return str(value or "")

    @property
    def synced(self) -> bool:
        """Whether the sync payload says this node is synchronized.

        An empty list means there is no report. A payload without an explicit
        synced flag is not treated as synchronized.
        """
        status = self.time_sync_status
        if not isinstance(status, dict):
            return False
        for name in ("synced", "synchronized", "in_sync"):
            if name in status:
                return bool(status[name])
        state = str(status.get("status", status.get("state", ""))).lower()
        return state in ("synced", "sync", "ok", "online")

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
        """Current mode. The dashboard keeps it on ``settings``, not the top level."""
        if self.settings.get("mode"):
            return str(self.settings.get("mode"))
        return str(self.get("mode", "") or "")

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

        The live document is ``{settings, nodes, alarms}``. ``settings.mode``
        is the current mode, and each node's sync state is
        ``machine.status.time_sync_status``.
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
