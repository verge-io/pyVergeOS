"""Machine drive IO statistics resource manager (issue #128).

Per-drive IO counters. These distinguish a guest that has actually *booted*
from one that is merely powered on: a VM stuck at "no bootable device" reports
``running``, has correctly-sized drives and attached NICs, and passes every
ordinary check -- but it never issues guest disk **writes**. Read counters and
NIC transmit counters both move on a VM that never boots (firmware reads the
boot sector and sends DHCP), so only writes are a reliable boot signal.

The access pattern is the point of this module. The stats row must be found by
a filter on ``parent_drive``, never by path key: ``machine_drive_stats/<n>``
resolves to the row whose *own* ``$key`` is ``n``, which belongs to a
different drive. Measured on VergeOS 26.1.8, a ``$key`` of 34 carried a
``parent_drive`` of 39, so path-key access reported another drive's counters --
809 MB of writes on a VM that had never been powered on. Scope this manager to
a drive (``drive.drive_stats``) and it filters on ``parent_drive`` for you.
"""

from __future__ import annotations

import builtins
from typing import TYPE_CHECKING, Any

from pyvergeos.exceptions import NotFoundError
from pyvergeos.resources.base import ResourceManager, ResourceObject

if TYPE_CHECKING:
    from pyvergeos.client import VergeClient

#: Default projection for drive IO statistics.
DRIVE_STATS_DEFAULT_FIELDS = [
    "$key",
    "parent_drive",
    "reads",
    "writes",
    "read_bytes",
    "write_bytes",
    "rops",
    "wops",
    "rbps",
    "wbps",
    "totalbps",
    "used_bytes",
    "max_bytes",
    "util",
    "service_time",
    "physical",
    "up_since",
    "last_update",
]


class MachineDriveStats(ResourceObject):
    """Per-drive IO statistics.

    Read-only; the counters are maintained by the system. ``write_bytes`` is
    the field that distinguishes a booted guest from one stuck at the firmware
    prompt (see the module docstring).
    """

    @property
    def drive_key(self) -> int:
        """Parent drive ``$key`` -- the drive these counters belong to.

        This is ``parent_drive``, not the stats row's own ``$key``; the two
        are not interchangeable (issue #128).
        """
        return int(self.get("parent_drive", 0))

    @property
    def reads(self) -> int:
        """Total read operations since the drive came up."""
        return int(self.get("reads") or 0)

    @property
    def writes(self) -> int:
        """Total write operations since the drive came up.

        The reliable signal that a guest has booted: firmware does not write.
        """
        return int(self.get("writes") or 0)

    @property
    def read_bytes(self) -> int:
        """Total bytes read since the drive came up."""
        return int(self.get("read_bytes") or 0)

    @property
    def write_bytes(self) -> int:
        """Total bytes written since the drive came up.

        Nonzero writes are how you tell a booted guest from one that merely
        reports ``running`` (issue #128).
        """
        return int(self.get("write_bytes") or 0)

    @property
    def read_ops_per_sec(self) -> int:
        """Current read operations per second."""
        return int(self.get("rops") or 0)

    @property
    def write_ops_per_sec(self) -> int:
        """Current write operations per second."""
        return int(self.get("wops") or 0)

    @property
    def read_bps(self) -> int:
        """Current read bytes per second."""
        return int(self.get("rbps") or 0)

    @property
    def write_bps(self) -> int:
        """Current write bytes per second."""
        return int(self.get("wbps") or 0)

    @property
    def total_bps(self) -> int:
        """Current total (read + write) bytes per second."""
        return int(self.get("totalbps") or 0)

    @property
    def used_bytes(self) -> int:
        """Bytes currently used on the drive."""
        return int(self.get("used_bytes") or 0)

    @property
    def max_bytes(self) -> int:
        """Drive capacity in bytes."""
        return int(self.get("max_bytes") or 0)

    @property
    def utilization(self) -> float:
        """Drive busy time as a fraction reported by the platform."""
        return float(self.get("util") or 0)

    @property
    def service_time(self) -> float:
        """Average IO service time reported by the platform."""
        return float(self.get("service_time") or 0)

    @property
    def has_booted(self) -> bool:
        """Whether the guest has issued disk writes -- i.e. actually booted.

        A VM at "no bootable device" reports ``running`` but never writes to
        its guest disks, so this stays False for it (issue #128). Read
        counters are not usable for this: firmware reads the boot sector.
        """
        return self.writes > 0


class MachineDriveStatsManager(ResourceManager[MachineDriveStats]):
    """Manager for per-drive IO statistics (issue #128).

    Read-only. Scope it to a drive and it addresses the stats by a filter on
    ``parent_drive``; do **not** rely on path-key access, which returns the
    row whose own ``$key`` matches and therefore a different drive's counters
    (see the module docstring for the measured failure).

    Examples:
        From a drive (the recommended path)::

            stats = drive.drive_stats.get()
            if stats.has_booted:
                print(f"guest is writing: {stats.write_bytes} bytes")

        Globally, filtered on the parent drive::

            rows = client.machine_drive_stats.list(filter="parent_drive eq 39")
    """

    _endpoint = "machine_drive_stats"
    _default_fields = DRIVE_STATS_DEFAULT_FIELDS

    def __init__(self, client: VergeClient, drive_key: int | None = None) -> None:
        super().__init__(client)
        self._drive_key = drive_key

    def _to_model(self, data: dict[str, Any]) -> MachineDriveStats:
        return MachineDriveStats(data, self)

    def list(
        self,
        filter: str | None = None,
        fields: str | builtins.list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        **filter_kwargs: Any,
    ) -> builtins.list[MachineDriveStats]:
        """List drive IO statistics.

        Defaults ``fields`` to the manager's projection so a bare ``list()``
        returns populated rows; the endpoint otherwise answers with only
        ``$key``.

        Args:
            filter: OData filter string, e.g. ``"parent_drive eq 39"``.
            fields: Fields to return.
            limit: Maximum number of results.
            offset: Skip this many results.
            **filter_kwargs: Shorthand filter arguments.

        Returns:
            List of MachineDriveStats objects.
        """
        if fields is None:
            fields = self._default_fields
        return super().list(
            filter=filter, fields=fields, limit=limit, offset=offset, **filter_kwargs
        )

    def get(  # type: ignore[override]
        self,
        key: int | None = None,
        *,
        fields: str | builtins.list[str] | None = None,
    ) -> MachineDriveStats:
        """Get drive IO statistics.

        When scoped to a drive (``drive.drive_stats``), returns that drive's
        stats via a ``parent_drive`` filter. When called with ``key``, fetches
        the stats row with that own ``$key`` -- which is only what you want if
        you already hold a stats ``$key``, not a drive ``$key`` (issue #128).

        Args:
            key: Stats row ``$key`` (optional if scoped to a drive).
            fields: Fields to return.

        Returns:
            MachineDriveStats.

        Raises:
            NotFoundError: If no stats are found.
            ValueError: If neither ``key`` nor a scoped drive is available.
        """
        if fields is None:
            fields = self._default_fields

        if key is not None:
            params: dict[str, Any] = {"fields": self._projection(fields)}
            response = self._client._request("GET", f"{self._endpoint}/{key}", params=params)
            if response is None:
                raise NotFoundError(f"Drive stats {key} not found")
            if not isinstance(response, dict):
                raise NotFoundError(f"Drive stats {key} returned invalid response")
            return self._to_model(response)

        if self._drive_key is not None:
            params = {
                "filter": f"parent_drive eq {self._drive_key}",
                "fields": self._projection(fields),
                "limit": 1,
            }
            response = self._client._request("GET", self._endpoint, params=params)
            if response is None:
                raise NotFoundError(f"Stats not found for drive {self._drive_key}")
            if isinstance(response, list):
                if not response:
                    raise NotFoundError(f"Stats not found for drive {self._drive_key}")
                return self._to_model(response[0])
            return self._to_model(response)

        raise ValueError("Either key or a scoped drive_key is required")
