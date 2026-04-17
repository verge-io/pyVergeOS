"""Physical drive (SMART health) resource manager."""

from __future__ import annotations

import builtins
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from pyvergeos.filters import build_filter
from pyvergeos.resources.base import ResourceManager, ResourceObject

if TYPE_CHECKING:
    from pyvergeos.client import VergeClient


class PhysicalDrive(ResourceObject):
    """Physical drive resource object.

    Represents a physical drive with SMART health data and vSAN status.

    Example:
        >>> for drive in client.physical_drives.list():
        ...     if drive.has_warnings:
        ...         print(f"{drive.model} ({drive.location}): SMART warning")
        ...     if drive.has_vsan_errors:
        ...         print(f"  vSAN errors: R={drive.vsan_read_errors} W={drive.vsan_write_errors}")
    """

    @property
    def model(self) -> str:
        """Drive model."""
        return str(self.get("model", ""))

    @property
    def serial(self) -> str:
        """Drive serial number."""
        return str(self.get("serial", ""))

    @property
    def firmware(self) -> str:
        """Firmware version."""
        return str(self.get("fw", ""))

    @property
    def path(self) -> str:
        """Device path (e.g. /dev/nvme0n1)."""
        return str(self.get("path", ""))

    @property
    def location(self) -> str:
        """Drive location (e.g. nvme0, sata0)."""
        return str(self.get("location", ""))

    @property
    def size_bytes(self) -> int:
        """Drive size in bytes."""
        return int(self.get("size") or 0)

    @property
    def temperature(self) -> int:
        """Current temperature in Celsius."""
        return int(self.get("temp") or 0)

    @property
    def temp_warn(self) -> bool:
        """Temperature warning flag."""
        return bool(self.get("temp_warn", False))

    @property
    def realloc_sectors(self) -> int:
        """Reallocated sector count."""
        return int(self.get("realloc_sectors") or 0)

    @property
    def realloc_sectors_warn(self) -> bool:
        """Reallocated sectors warning flag."""
        return bool(self.get("realloc_sectors_warn", False))

    @property
    def wear_level(self) -> int:
        """SSD wear level percentage."""
        return int(self.get("wear_level") or 0)

    @property
    def wear_level_warn(self) -> bool:
        """SSD wear level warning flag."""
        return bool(self.get("wear_level_warn", False))

    @property
    def current_pending_sector(self) -> int:
        """Current pending sector count."""
        return int(self.get("current_pending_sector") or 0)

    @property
    def current_pending_sector_warn(self) -> bool:
        """Current pending sector warning flag."""
        return bool(self.get("current_pending_sector_warn", False))

    @property
    def offline_uncorrectable(self) -> int:
        """Offline uncorrectable sector count."""
        return int(self.get("offline_uncorrectable") or 0)

    @property
    def offline_uncorrectable_warn(self) -> bool:
        """Offline uncorrectable sectors warning flag."""
        return bool(self.get("offline_uncorrectable_warn", False))

    @property
    def hours(self) -> int:
        """Power-on hours."""
        return int(self.get("hours") or 0)

    @property
    def hours_warn(self) -> bool:
        """Power-on hours warning flag."""
        return bool(self.get("hours_warn", False))

    @property
    def smart_enabled(self) -> bool:
        """Whether SMART monitoring is enabled."""
        return bool(self.get("smart", False))

    @property
    def vsan_read_errors(self) -> int:
        """vSAN read error count."""
        return int(self.get("vsan_read_errors") or 0)

    @property
    def vsan_write_errors(self) -> int:
        """vSAN write error count."""
        return int(self.get("vsan_write_errors") or 0)

    @property
    def vsan_last_error(self) -> str:
        """Last vSAN error message."""
        return str(self.get("vsan_last_error", ""))

    @property
    def vsan_throttle(self) -> int:
        """Write throttle in bytes/sec (0 = no throttle)."""
        return int(self.get("vsan_throttle") or 0)

    @property
    def vsan_tier(self) -> int:
        """vSAN tier number."""
        return int(self.get("vsan_tier") or 0)

    @property
    def vsan_repairing(self) -> bool:
        """Whether the drive is currently being repaired."""
        return bool(self.get("vsan_repairing", 0))

    @property
    def vsan_repair_estimate(self) -> int:
        """Estimated repair time remaining in seconds."""
        return int(self.get("vsan_repair_estimate") or 0)

    @property
    def vsan_online_since(self) -> datetime | None:
        """Timestamp when drive came online in vSAN."""
        ts = self.get("vsan_online_since")
        if ts and int(ts) > 0:
            return datetime.fromtimestamp(int(ts), tz=timezone.utc)
        return None

    @property
    def is_boot(self) -> bool:
        """Whether this is a boot drive."""
        return bool(self.get("boot", False))

    @property
    def is_spare(self) -> bool:
        """Whether this is a spare drive."""
        return bool(self.get("spare", False))

    @property
    def is_encrypted(self) -> bool:
        """Whether the drive is encrypted."""
        return bool(self.get("encrypted", False))

    @property
    def has_warnings(self) -> bool:
        """Whether any SMART warning flag is set."""
        return any([
            self.temp_warn,
            self.realloc_sectors_warn,
            self.wear_level_warn,
            self.current_pending_sector_warn,
            self.offline_uncorrectable_warn,
            self.hours_warn,
        ])

    @property
    def has_vsan_errors(self) -> bool:
        """Whether there are any vSAN read or write errors."""
        return self.vsan_read_errors > 0 or self.vsan_write_errors > 0

    def __repr__(self) -> str:
        return (
            f"<PhysicalDrive key={self.get('$key', '?')} "
            f"model={self.model!r} location={self.location!r}>"
        )


class PhysicalDriveManager(ResourceManager[PhysicalDrive]):
    """Manager for physical drive SMART health data.

    Provides fleet-wide view of drive health. Can be scoped to a
    specific node or used globally.

    Example:
        >>> # List all drives
        >>> drives = client.physical_drives.list()

        >>> # Find drives with warnings
        >>> for drive in drives:
        ...     if drive.has_warnings or drive.has_vsan_errors:
        ...         print(f"ALERT: {drive.model} @ {drive.location}")
    """

    _endpoint = "machine_drive_phys"

    _default_fields = [
        "$key",
        "model",
        "serial",
        "fw",
        "path",
        "location",
        "size",
        "temp",
        "temp_warn",
        "realloc_sectors",
        "realloc_sectors_warn",
        "wear_level",
        "wear_level_warn",
        "current_pending_sector",
        "current_pending_sector_warn",
        "offline_uncorrectable",
        "offline_uncorrectable_warn",
        "hours",
        "hours_warn",
        "smart",
        "vsan_read_errors",
        "vsan_write_errors",
        "vsan_last_error",
        "vsan_throttle",
        "vsan_tier",
        "vsan_repairing",
        "vsan_repair_estimate",
        "vsan_online_since",
        "boot",
        "swap",
        "spare",
        "encrypted",
        "parent_drive",
        "modified",
    ]

    def __init__(
        self, client: VergeClient, node_key: int | None = None
    ) -> None:
        super().__init__(client)
        self._node_key = node_key

    def _to_model(self, data: dict[str, Any]) -> PhysicalDrive:
        return PhysicalDrive(data, self)

    def list(  # noqa: A003
        self,
        filter: str | None = None,  # noqa: A002
        fields: builtins.list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        *,
        warnings_only: bool = False,
        **filter_kwargs: Any,
    ) -> builtins.list[PhysicalDrive]:
        """List physical drives with optional filtering.

        Args:
            filter: OData filter string.
            fields: List of fields to return.
            limit: Maximum number of results.
            offset: Skip this many results.
            warnings_only: If True, only return drives with SMART warnings.
            **filter_kwargs: Additional filter arguments.

        Returns:
            List of PhysicalDrive objects.
        """
        params: dict[str, Any] = {}
        filters = []

        if filter:
            filters.append(filter)

        if self._node_key is not None:
            filters.append(f"node eq {self._node_key}")

        if warnings_only:
            warn_conditions = [
                "temp_warn eq true",
                "realloc_sectors_warn eq true",
                "wear_level_warn eq true",
                "current_pending_sector_warn eq true",
                "offline_uncorrectable_warn eq true",
                "hours_warn eq true",
            ]
            filters.append(f"({' or '.join(warn_conditions)})")

        if filter_kwargs:
            filters.append(build_filter(**filter_kwargs))

        if filters:
            params["filter"] = " and ".join(filters)

        if fields:
            params["fields"] = ",".join(fields)
        else:
            params["fields"] = ",".join(self._default_fields)

        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset

        response = self._client._request("GET", self._endpoint, params=params)

        if response is None:
            return []

        if not isinstance(response, list):
            return [self._to_model(response)]

        return [self._to_model(item) for item in response]

    def get(  # type: ignore[override]
        self,
        key: int | None = None,
        *,
        fields: builtins.list[str] | None = None,
    ) -> PhysicalDrive:
        """Get a physical drive by key.

        Args:
            key: Drive $key (ID).
            fields: List of fields to return.

        Returns:
            PhysicalDrive object.

        Raises:
            NotFoundError: If drive not found.
            ValueError: If key not provided.
        """
        if key is None:
            raise ValueError("key must be provided")

        params: dict[str, Any] = {}
        if fields:
            params["fields"] = ",".join(fields)

        response = self._client._request(
            "GET", f"{self._endpoint}/{key}", params=params
        )

        if response is None or not isinstance(response, dict):
            from pyvergeos.exceptions import NotFoundError

            raise NotFoundError(f"Physical drive {key} not found")

        return self._to_model(response)
