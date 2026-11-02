"""Snapshot profile resource manager for VergeOS backup/DR."""

from __future__ import annotations

import builtins
from collections.abc import Sequence
from datetime import timedelta
from typing import TYPE_CHECKING, Any

from pyvergeos.exceptions import NotFoundError
from pyvergeos.filters import build_filter, quote_value
from pyvergeos.resources.base import ResourceManager, ResourceObject
from pyvergeos.resources.cloud_snapshots import TagRef

if TYPE_CHECKING:
    from pyvergeos.client import VergeClient
    from pyvergeos.resources.tags import TagReference


# Frequency options
FREQUENCIES = ["custom", "hourly", "daily", "weekly", "monthly", "yearly"]

# Day of week options
DAYS_OF_WEEK = ["sun", "mon", "tue", "wed", "thu", "fri", "sat", "any"]

# Day of week display names
DAY_OF_WEEK_DISPLAY = {
    "sun": "Sunday",
    "mon": "Monday",
    "tue": "Tuesday",
    "wed": "Wednesday",
    "thu": "Thursday",
    "fri": "Friday",
    "sat": "Saturday",
    "any": "Any Day",
}

# Default fields for profile list operations
_DEFAULT_PROFILE_FIELDS = [
    "$key",
    "name",
    "description",
    "ignore_warnings",
]

# Default fields for period list operations
_DEFAULT_PERIOD_FIELDS = [
    "$key",
    "profile",
    "name",
    "frequency",
    "minute",
    "hour",
    "day_of_week",
    "day_of_month",
    "month",
    "retention",
    "max_tier",
    "quiesce",
    "min_snapshots",
    "immutable",
    "estimated_snapshot_count",
    # Tag scope and the private flag. Read off a stored period on 26.1.8.
    # site_sync_refs is also a column there; it is a rows field, so it stays
    # out of this list.
    "type",
    "partial_tags",
    "quiesce_tags",
    "private",
]

# type values stored on a period, and on a cloud snapshot. Measured with
# cloud_snapshots.create() on 26.1.8.
PERIOD_SNAPSHOT_TYPES = ("full", "partial_include", "partial_exclude")

# snapshot_profile_period_tags, from a 26.1.8 listing of 26 rows.
_DEFAULT_PERIOD_TAG_FIELDS = ["$key", "snapshot_profile_period", "refs"]


class SnapshotProfilePeriod(ResourceObject):
    """Snapshot profile period (schedule) resource object.

    Represents a snapshot schedule period within a profile. Defines when
    snapshots are taken and how long they are retained.

    Properties:
        profile_key: Key of the parent snapshot profile.
        name: Period name (e.g., "Hourly", "Daily").
        frequency: Schedule frequency (custom, hourly, daily, weekly, monthly, yearly).
        frequency_display: Capitalized frequency display name.
        minute: Minute of the hour (0-59).
        hour: Hour of the day (0-23).
        day_of_week: Day of week (sun, mon, tue, wed, thu, fri, sat, any).
        day_of_week_display: Full day name.
        day_of_month: Day of month (0-31, 0 = any).
        month: Month (0-12, 0 = any).
        retention_seconds: Retention period in seconds.
        retention: Retention as timedelta.
        retention_display: Human-readable retention string.
        max_tier: Maximum storage tier for snapshots (1-5).
        quiesce: Whether to quiesce disks during snapshot.
        min_snapshots: Minimum snapshots to retain.
        is_immutable: Whether snapshots are immutable (system snapshots only).
        estimated_snapshot_count: Estimated number of snapshots.
        snapshot_type: full, partial_include, or partial_exclude.
        partial_tags: Comma-separated tag keys for a partial snapshot.
        partial_tag_keys: Those keys as ints.
        quiesce_tags: Comma-separated tag keys that quiesce during a partial snapshot.
        quiesce_tag_keys: Those keys as ints.
        is_private: Whether snapshots from this period are hidden from tenants.
        is_partial: Whether the period is include-scoped or exclude-scoped.
    """

    @property
    def profile_key(self) -> int | None:
        """Get parent profile key."""
        val = self.get("profile")
        return int(val) if val is not None else None

    @property
    def name(self) -> str:
        """Get period name."""
        return str(self.get("name", ""))

    @property
    def frequency(self) -> str:
        """Get schedule frequency."""
        return str(self.get("frequency", ""))

    @property
    def frequency_display(self) -> str:
        """Get capitalized frequency display name."""
        freq = self.frequency
        return freq.capitalize() if freq else ""

    @property
    def minute(self) -> int:
        """Get minute of the hour (0-59)."""
        return int(self.get("minute", 0))

    @property
    def hour(self) -> int:
        """Get hour of the day (0-23)."""
        return int(self.get("hour", 0))

    @property
    def day_of_week(self) -> str:
        """Get day of week."""
        return str(self.get("day_of_week", "any"))

    @property
    def day_of_week_display(self) -> str:
        """Get full day name."""
        return DAY_OF_WEEK_DISPLAY.get(self.day_of_week, self.day_of_week)

    @property
    def day_of_month(self) -> int:
        """Get day of month (0 = any)."""
        return int(self.get("day_of_month", 0))

    @property
    def month(self) -> int:
        """Get month (0 = any)."""
        return int(self.get("month", 0))

    @property
    def retention_seconds(self) -> int:
        """Get retention in seconds."""
        return int(self.get("retention", 0))

    @property
    def retention(self) -> timedelta:
        """Get retention as timedelta."""
        return timedelta(seconds=self.retention_seconds)

    @property
    def retention_display(self) -> str:
        """Get human-readable retention string."""
        seconds = self.retention_seconds
        if seconds <= 0:
            return "None"

        days = seconds // 86400
        hours = (seconds % 86400) // 3600

        if days > 0:
            if hours > 0:
                return f"{days}d {hours}h"
            return f"{days}d"
        return f"{hours}h"

    @property
    def max_tier(self) -> int:
        """Get maximum storage tier (1-5)."""
        val = self.get("max_tier", "1")
        return int(val) if val else 1

    @property
    def quiesce(self) -> bool:
        """Check if disk quiescing is enabled."""
        return bool(self.get("quiesce", False))

    @property
    def min_snapshots(self) -> int:
        """Get minimum snapshots to retain."""
        return int(self.get("min_snapshots", 1))

    @property
    def is_immutable(self) -> bool:
        """Check if snapshots are immutable."""
        return bool(self.get("immutable", False))

    @property
    def estimated_snapshot_count(self) -> int | None:
        """Get estimated snapshot count."""
        val = self.get("estimated_snapshot_count")
        return int(val) if val is not None else None

    @property
    def snapshot_type(self) -> str:
        """Snapshot scope stored in ``type``.

        ``full`` when the row has no type. A partial period is
        ``partial_include`` or ``partial_exclude``.
        """
        raw = self.get("type")
        return str(raw) if raw else "full"

    @property
    def is_partial(self) -> bool:
        """Whether this period captures a tag-scoped subset."""
        return self.snapshot_type in ("partial_include", "partial_exclude")

    @property
    def partial_tags(self) -> str:
        """Comma-separated tag keys for the partial snapshot."""
        raw = self.get("partial_tags")
        return str(raw) if raw else ""

    @property
    def partial_tag_keys(self) -> builtins.list[int]:
        """Tag keys parsed from ``partial_tags``."""
        return _split_tag_keys(self.get("partial_tags"))

    @property
    def quiesce_tags(self) -> str:
        """Comma-separated tag keys that quiesce during the snapshot."""
        raw = self.get("quiesce_tags")
        return str(raw) if raw else ""

    @property
    def quiesce_tag_keys(self) -> builtins.list[int]:
        """Tag keys parsed from ``quiesce_tags``."""
        return _split_tag_keys(self.get("quiesce_tags"))

    @property
    def is_private(self) -> bool:
        """Whether snapshots from this period are hidden from tenants."""
        return bool(self.get("private", False))

    def save(self, **kwargs: Any) -> SnapshotProfilePeriod:
        """Save changes to period.

        Args:
            **kwargs: Fields to update.

        Returns:
            Updated period object.
        """
        from typing import cast

        return cast("SnapshotProfilePeriod", self._save(**kwargs))

    def delete(self) -> None:
        """Delete this period."""
        from typing import cast

        manager = cast("SnapshotProfilePeriodManager", self._manager)
        manager.delete(self.key)

    def period_tags(self) -> SnapshotProfilePeriodTagManager:
        """Join rows that link this period to ``tag_references``."""
        from typing import cast

        manager = cast("SnapshotProfilePeriodManager", self._manager)
        return manager.period_tags(self.key)

    def __repr__(self) -> str:
        key = self.get("$key", "?")
        name = self.name
        freq = self.frequency_display
        return f"<SnapshotProfilePeriod key={key} name={name!r} frequency={freq!r}>"


class SnapshotProfile(ResourceObject):
    """Snapshot profile resource object.

    Represents a snapshot profile that defines automated snapshot schedules
    for VMs, NAS volumes, and cloud/system snapshots.

    Properties:
        name: Profile name.
        description: Profile description.
        ignore_warnings: Whether to ignore snapshot count warnings.
        periods: List of schedule periods (if loaded with include_periods=True).
    """

    def __init__(
        self,
        data: dict[str, Any],
        manager: ResourceManager[Any],
        periods: builtins.list[SnapshotProfilePeriod] | None = None,
    ) -> None:
        super().__init__(data, manager)
        self._periods = periods

    @property
    def name(self) -> str:
        """Get profile name."""
        return str(self.get("name", ""))

    @property
    def description(self) -> str:
        """Get profile description."""
        return str(self.get("description", ""))

    @property
    def ignore_warnings(self) -> bool:
        """Check if snapshot count warnings are ignored."""
        return bool(self.get("ignore_warnings", False))

    @property
    def periods(self) -> builtins.list[SnapshotProfilePeriod] | None:
        """Get schedule periods (if loaded)."""
        return self._periods

    def save(self, **kwargs: Any) -> SnapshotProfile:
        """Save changes to profile.

        Args:
            **kwargs: Fields to update.

        Returns:
            Updated profile object.
        """
        from typing import cast

        return cast("SnapshotProfile", self._save(**kwargs))

    def delete(self) -> None:
        """Delete this profile."""
        from typing import cast

        manager = cast("SnapshotProfileManager", self._manager)
        manager.delete(self.key)

    def get_periods(self) -> builtins.list[SnapshotProfilePeriod]:
        """Get all schedule periods for this profile.

        Returns:
            List of SnapshotProfilePeriod objects.
        """
        from typing import cast

        manager = cast("SnapshotProfileManager", self._manager)
        return manager.periods(self.key).list()

    def add_period(
        self,
        name: str,
        frequency: str,
        retention_seconds: int,
        *,
        minute: int = 0,
        hour: int = 0,
        day_of_week: str = "any",
        day_of_month: int = 0,
        month: int = 0,
        max_tier: int = 1,
        quiesce: bool = False,
        min_snapshots: int = 1,
        immutable: bool = False,
        include_tags: TagRef | Sequence[TagRef] | None = None,
        exclude_tags: TagRef | Sequence[TagRef] | None = None,
        quiesce_tags: TagRef | Sequence[TagRef] | None = None,
    ) -> SnapshotProfilePeriod:
        """Add a schedule period to this profile.

        Args:
            name: Period name.
            frequency: Schedule frequency (hourly, daily, weekly, monthly, yearly, custom).
            retention_seconds: Retention period in seconds.
            minute: Minute of the hour (0-59).
            hour: Hour of the day (0-23).
            day_of_week: Day of week (sun, mon, tue, wed, thu, fri, sat, any).
            day_of_month: Day of month (0-31, 0 = any).
            month: Month (0-12, 0 = any).
            max_tier: Maximum storage tier (1-5).
            quiesce: Enable disk quiescing.
            min_snapshots: Minimum snapshots to retain.
            immutable: Make snapshots immutable (system snapshots only).
            include_tags: Capture only resources carrying these tags.
            exclude_tags: Capture everything except resources carrying these tags.
            quiesce_tags: Quiesce resources carrying these tags. Partial periods only.

        Returns:
            Created SnapshotProfilePeriod object.
        """
        from typing import cast

        manager = cast("SnapshotProfileManager", self._manager)
        return manager.periods(self.key).create(
            name=name,
            frequency=frequency,
            retention=retention_seconds,
            minute=minute,
            hour=hour,
            day_of_week=day_of_week,
            day_of_month=day_of_month,
            month=month,
            max_tier=max_tier,
            quiesce=quiesce,
            min_snapshots=min_snapshots,
            immutable=immutable,
            include_tags=include_tags,
            exclude_tags=exclude_tags,
            quiesce_tags=quiesce_tags,
        )

    def __repr__(self) -> str:
        key = self.get("$key", "?")
        name = self.name
        return f"<SnapshotProfile key={key} name={name!r}>"


class SnapshotProfilePeriodManager(ResourceManager[SnapshotProfilePeriod]):
    """Manager for snapshot profile period operations.

    Manages schedule periods within a snapshot profile.

    Example:
        >>> # Get periods for a profile
        >>> profile = client.snapshot_profiles.get(name="Daily Backups")
        >>> periods = client.snapshot_profiles.periods(profile.key).list()

        >>> # Create a period
        >>> period = client.snapshot_profiles.periods(profile.key).create(
        ...     name="Daily",
        ...     frequency="daily",
        ...     retention=86400 * 7,  # 7 days
        ...     hour=2,  # 2 AM
        ...     minute=0,
        ... )

        >>> # Or use the profile object directly
        >>> period = profile.add_period(
        ...     name="Hourly",
        ...     frequency="hourly",
        ...     retention_seconds=86400,  # 1 day
        ... )
    """

    #: Default projection, so that a caller's 'all' can be expanded
    #: into a true superset of it (issue #117).
    _default_fields = _DEFAULT_PERIOD_FIELDS

    _endpoint = "snapshot_profile_periods"

    def __init__(self, client: VergeClient, profile_key: int) -> None:
        super().__init__(client)
        self._profile_key = profile_key

    def _to_model(self, data: dict[str, Any]) -> SnapshotProfilePeriod:
        return SnapshotProfilePeriod(data, self)

    def list(
        self,
        filter: str | None = None,
        fields: str | builtins.list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        **filter_kwargs: Any,
    ) -> builtins.list[SnapshotProfilePeriod]:
        """List periods for this profile.

        Args:
            filter: OData filter string.
            fields: List of fields to return.
            limit: Maximum number of results.
            offset: Skip this many results.
            **filter_kwargs: Additional filter arguments.

        Returns:
            List of SnapshotProfilePeriod objects.
        """
        conditions: builtins.list[str] = [f"profile eq {self._profile_key}"]

        if filter:
            conditions.append(f"({filter})")

        if filter_kwargs:
            conditions.append(build_filter(**filter_kwargs))

        combined_filter = " and ".join(conditions)

        if fields is None:
            fields = _DEFAULT_PERIOD_FIELDS

        params: dict[str, Any] = {"filter": combined_filter}
        if fields:
            params["fields"] = self._projection(fields)
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset
        params["sort"] = "+name"

        response = self._client._request("GET", self._endpoint, params=params)

        if response is None:
            return []

        if not isinstance(response, list):
            return [self._to_model(response)]

        return [self._to_model(item) for item in response]

    def get(
        self,
        key: int | None = None,
        *,
        name: str | None = None,
        fields: str | builtins.list[str] | None = None,
    ) -> SnapshotProfilePeriod:
        """Get a period by key or name.

        Args:
            key: Period $key (ID).
            name: Period name within this profile.
            fields: List of fields to return.

        Returns:
            SnapshotProfilePeriod object.

        Raises:
            NotFoundError: If period not found.
            ValueError: If neither key nor name provided.
        """
        if fields is None:
            fields = _DEFAULT_PERIOD_FIELDS

        if key is not None:
            params: dict[str, Any] = {}
            if fields:
                params["fields"] = self._projection(fields)

            response = self._client._request("GET", f"{self._endpoint}/{key}", params=params)
            if response is None:
                raise NotFoundError(f"Period {key} not found")
            if not isinstance(response, dict):
                raise NotFoundError(f"Period {key} returned invalid response")

            # Verify this period belongs to our profile
            period = self._to_model(response)
            if period.profile_key != self._profile_key:
                raise NotFoundError(f"Period {key} does not belong to profile {self._profile_key}")
            return period

        if name is not None:
            results = self.list(filter=f"name eq {quote_value(name)}", fields=fields)
            if not results:
                raise NotFoundError(f"Period '{name}' not found in profile {self._profile_key}")
            return results[0]

        raise ValueError("Either key or name must be provided")

    def create(  # type: ignore[override]
        self,
        name: str,
        frequency: str,
        retention: int,
        *,
        minute: int = 0,
        hour: int = 0,
        day_of_week: str = "any",
        day_of_month: int = 0,
        month: int = 0,
        max_tier: int = 1,
        quiesce: bool = False,
        min_snapshots: int = 1,
        immutable: bool = False,
        include_tags: TagRef | Sequence[TagRef] | None = None,
        exclude_tags: TagRef | Sequence[TagRef] | None = None,
        quiesce_tags: TagRef | Sequence[TagRef] | None = None,
    ) -> SnapshotProfilePeriod:
        """Create a new period in this profile.

        Args:
            name: Period name (e.g., "Daily", "Hourly").
            frequency: Schedule frequency (hourly, daily, weekly, monthly, yearly, custom).
            retention: Retention period in seconds.
            minute: Minute of the hour (0-59).
            hour: Hour of the day (0-23).
            day_of_week: Day of week (sun, mon, tue, wed, thu, fri, sat, any).
            day_of_month: Day of month (0-31, 0 = any).
            month: Month (0-12, 0 = any).
            max_tier: Maximum storage tier (1-5).
            quiesce: Enable disk quiescing.
            min_snapshots: Minimum snapshots to retain.
            immutable: Make snapshots immutable (system snapshots only).
            include_tags: Capture only resources carrying these tags. A tag is
                a ``$key``, a name, or a Tag object. Mutually exclusive with
                ``exclude_tags``.
            exclude_tags: Capture everything except resources carrying these tags.
            quiesce_tags: Quiesce resources carrying these tags during the
                snapshot. Only on a partial period.

        Returns:
            Created SnapshotProfilePeriod object.

        Raises:
            ValueError: If invalid parameters provided.
            APIError: If creation fails.
        """
        if frequency not in FREQUENCIES:
            raise ValueError(
                f"Invalid frequency '{frequency}'. Must be one of: {', '.join(FREQUENCIES)}"
            )

        if day_of_week not in DAYS_OF_WEEK:
            raise ValueError(
                f"Invalid day_of_week '{day_of_week}'. Must be one of: {', '.join(DAYS_OF_WEEK)}"
            )

        if not 0 <= minute <= 59:
            raise ValueError("minute must be between 0 and 59")
        if not 0 <= hour <= 23:
            raise ValueError("hour must be between 0 and 23")
        if not 0 <= day_of_month <= 31:
            raise ValueError("day_of_month must be between 0 and 31")
        if not 0 <= month <= 12:
            raise ValueError("month must be between 0 and 12")
        if not 1 <= max_tier <= 5:
            raise ValueError("max_tier must be between 1 and 5")
        if retention < 0:
            raise ValueError("retention must be non-negative")

        body: dict[str, Any] = {
            "profile": self._profile_key,
            "name": name,
            "frequency": frequency,
            "retention": retention,
            "minute": minute,
            "hour": hour,
            "day_of_week": day_of_week,
            "day_of_month": day_of_month,
            "month": month,
            "max_tier": str(max_tier),
            "quiesce": quiesce,
            "min_snapshots": min_snapshots,
            "immutable": immutable,
        }
        body.update(
            self._period_tag_body(
                include_tags=include_tags,
                exclude_tags=exclude_tags,
                quiesce_tags=quiesce_tags,
                snapshot_type=None,
                current_type=None,
                clear_empty_quiesce=False,
            )
        )

        response = self._client._request("POST", self._endpoint, json_data=body)
        if response is None:
            raise ValueError("No response from create operation")
        if not isinstance(response, dict):
            raise ValueError("Create operation returned invalid response")

        # Fetch the created period with full fields
        created_key = response.get("$key")
        if created_key:
            return self.get(int(created_key))
        return self._to_model_unprojected(response)

    def update(
        self,
        key: int,
        *,
        include_tags: TagRef | Sequence[TagRef] | None = None,
        exclude_tags: TagRef | Sequence[TagRef] | None = None,
        quiesce_tags: TagRef | Sequence[TagRef] | None = None,
        snapshot_type: str | None = None,
        **kwargs: Any,
    ) -> SnapshotProfilePeriod:
        """Update a period.

        Args:
            key: Period $key (ID).
            include_tags: Capture only resources carrying these tags.
            exclude_tags: Capture everything except resources carrying these tags.
            quiesce_tags: Quiesce resources carrying these tags. An empty list
                clears the column. Omit it to leave the column alone.
            snapshot_type: Pass ``"full"`` to clear tag scope. A partial scope
                is set with ``include_tags`` or ``exclude_tags``.
            **kwargs: Columns to update (name, frequency, retention, minute, hour,
                day_of_week, day_of_month, month, max_tier, quiesce,
                min_snapshots, immutable, type, partial_tags, quiesce_tags, private).

        Returns:
            Updated SnapshotProfilePeriod object.

        Raises:
            ValueError: If ``skip_missed`` or another invalid field is passed.
                ``skip_missed`` is not a period column.
        """
        needs_current = (
            quiesce_tags is not None
            and include_tags is None
            and exclude_tags is None
            and snapshot_type != "full"
        )
        current_type = self.get(key).snapshot_type if needs_current else None
        tag_body = self._period_tag_body(
            include_tags=include_tags,
            exclude_tags=exclude_tags,
            quiesce_tags=quiesce_tags,
            snapshot_type=snapshot_type,
            current_type=current_type,
            clear_empty_quiesce=True,
        )
        overlap = set(tag_body) & set(kwargs)
        if overlap:
            names = ", ".join(sorted(overlap))
            raise ValueError(
                "pass tag scope as include_tags, exclude_tags, quiesce_tags, "
                f"or snapshot_type, or as the raw columns, not both ({names})"
            )
        kwargs = self._prepare_write_fields(kwargs)
        kwargs.update(tag_body)
        self._client._request("PUT", f"{self._endpoint}/{key}", json_data=kwargs)
        return self.get(key)

    def _prepare_write_fields(self, fields: dict[str, Any]) -> dict[str, Any]:
        """Validate period fields and convert ``max_tier`` to the API string.

        Used by both ``update()`` and ``ResourceObject._save()`` so attribute
        assignment behaves the same as ``update()`` (issue #97).
        """
        fields = dict(fields)
        # Not a column on snapshot_profile_periods. VergeOS accepts the name
        # and drops it, so a write looked successful and a later read was
        # always false (issue #139). Measured absent on 26.1.8.
        if "skip_missed" in fields:
            raise ValueError(
                "skip_missed is not a snapshot profile period column; VergeOS discards it"
            )
        for convenience in ("include_tags", "exclude_tags", "quiesce_tags", "snapshot_type"):
            if convenience in fields:
                raise ValueError(
                    f"{convenience} is not a snapshot profile period column; "
                    "pass it to create(), update(), or save()"
                )
        if "frequency" in fields and fields["frequency"] not in FREQUENCIES:
            raise ValueError(f"Invalid frequency. Must be one of: {', '.join(FREQUENCIES)}")
        if "day_of_week" in fields and fields["day_of_week"] not in DAYS_OF_WEEK:
            raise ValueError(f"Invalid day_of_week. Must be one of: {', '.join(DAYS_OF_WEEK)}")
        if "type" in fields and fields["type"] not in PERIOD_SNAPSHOT_TYPES:
            raise ValueError(
                f"Invalid type {fields['type']!r}. "
                f"Must be one of: {', '.join(PERIOD_SNAPSHOT_TYPES)}"
            )
        if fields.get("type") == "full":
            fields.setdefault("partial_tags", "")
            fields.setdefault("quiesce_tags", "")
        if "max_tier" in fields:
            fields["max_tier"] = str(fields["max_tier"])
        for column in ("partial_tags", "quiesce_tags"):
            if column in fields and not isinstance(fields[column], str):
                fields[column] = self._coerce_tag_column(fields[column])
        return fields

    def period_tags(self, period_key: int) -> SnapshotProfilePeriodTagManager:
        """Join rows for one period.

        Args:
            period_key: Period ``$key``.

        Returns:
            A manager filtered to that period.
        """
        return SnapshotProfilePeriodTagManager(self._client, period_key)

    def _resolve_tag_keys(self, tags: TagRef | Sequence[TagRef] | None) -> str | None:
        """Resolve tags to the comma-separated ``$key`` string the columns store.

        ``partial_tags`` and ``quiesce_tags`` take keys. A name stored
        verbatim is ignored, same as on a cloud snapshot, so this uses that
        resolver.
        """
        from pyvergeos.resources.cloud_snapshots import CloudSnapshotManager

        return CloudSnapshotManager(self._client)._resolve_tag_keys(tags)

    def _coerce_tag_column(self, value: Any) -> str:
        """Turn a tag column value into the comma-separated key string."""
        if isinstance(value, str):
            return value
        if value is None:
            return ""
        return self._resolve_tag_keys(value) or ""

    def _period_tag_body(
        self,
        *,
        include_tags: TagRef | Sequence[TagRef] | None,
        exclude_tags: TagRef | Sequence[TagRef] | None,
        quiesce_tags: TagRef | Sequence[TagRef] | None,
        snapshot_type: str | None,
        current_type: str | None,
        clear_empty_quiesce: bool,
    ) -> dict[str, Any]:
        """Build the ``type`` / ``partial_tags`` / ``quiesce_tags`` write.

        ``snapshot_type="full"`` clears the tag columns. A partial scope is
        written by ``include_tags`` or ``exclude_tags``, which set ``type``
        to ``partial_include`` or ``partial_exclude``.
        """
        if include_tags is not None and exclude_tags is not None:
            raise ValueError(
                "include_tags and exclude_tags are mutually exclusive; a partial "
                "snapshot is either include-scoped or exclude-scoped, not both"
            )
        if snapshot_type not in (None, "full"):
            raise ValueError(
                "snapshot_type only accepts 'full', to clear tag scope. "
                "Pass include_tags or exclude_tags to set a partial period"
            )
        if snapshot_type == "full" and (include_tags is not None or exclude_tags is not None):
            raise ValueError(
                "snapshot_type='full' cannot be combined with include_tags or exclude_tags"
            )

        body: dict[str, Any] = {}
        if include_tags is not None:
            partial_keys = self._resolve_tag_keys(include_tags)
            if not partial_keys:
                raise ValueError("include_tags must name at least one tag")
            body["type"] = "partial_include"
            body["partial_tags"] = partial_keys
        elif exclude_tags is not None:
            partial_keys = self._resolve_tag_keys(exclude_tags)
            if not partial_keys:
                raise ValueError("exclude_tags must name at least one tag")
            body["type"] = "partial_exclude"
            body["partial_tags"] = partial_keys
        elif snapshot_type == "full":
            body["type"] = "full"
            body["partial_tags"] = ""
            body["quiesce_tags"] = ""

        if quiesce_tags is not None:
            quiesce_keys = self._resolve_tag_keys(quiesce_tags)
            if quiesce_keys:
                effective = body.get("type", current_type)
                if effective not in ("partial_include", "partial_exclude"):
                    raise ValueError(
                        "quiesce_tags applies only to a partial snapshot; also pass "
                        "include_tags or exclude_tags"
                    )
                body["quiesce_tags"] = quiesce_keys
            elif clear_empty_quiesce and "quiesce_tags" not in body:
                body["quiesce_tags"] = ""
        return body

    def delete(self, key: int) -> None:
        """Delete a period.

        Args:
            key: Period $key (ID).
        """
        self._client._request("DELETE", f"{self._endpoint}/{key}")


def _split_tag_keys(raw: Any) -> builtins.list[int]:
    """Parse a comma-separated tag-key column. Non-numeric tokens are skipped."""
    if raw is None or raw is False:
        return []
    text = raw if isinstance(raw, str) else str(raw)
    keys: builtins.list[int] = []
    for part in text.split(","):
        part = part.strip()
        if part.isdigit():
            keys.append(int(part))
    return keys


def _rows_from_refs(refs: Any) -> builtins.list[dict[str, Any]]:
    """Turn a ``refs`` value into row dicts.

    The column links a period-tag row to ``tag_references``. Expanded, it is
    a list of rows. Unexpanded, it can be a count. A count is not a key.
    """
    if refs is None or refs == "" or refs == 0 or isinstance(refs, bool):
        return []
    if isinstance(refs, int):
        return []
    if isinstance(refs, dict):
        return [refs]
    if isinstance(refs, str):
        return [{"$key": int(part)} for part in refs.split(",") if part.strip().isdigit()]
    if isinstance(refs, list):
        rows: builtins.list[dict[str, Any]] = []
        for item in refs:
            if isinstance(item, dict):
                rows.append(item)
            elif isinstance(item, bool):
                continue
            elif isinstance(item, int) or (isinstance(item, str) and item.strip().isdigit()):
                rows.append({"$key": int(item)})
        return rows
    return []


class SnapshotProfilePeriodTag(ResourceObject):
    """One ``snapshot_profile_period_tags`` row.

    The row points at a period and, through ``refs``, at ``tag_references``.
    Those are the columns a 26.1.8 listing returned.
    """

    @property
    def period_key(self) -> int | None:
        """Parent period ``$key``."""
        val = self.get("snapshot_profile_period")
        if val is None or val == "":
            return None
        return int(val)

    @property
    def refs(self) -> Any:
        """Raw ``refs`` value from the row."""
        return self.get("refs")

    def references(self) -> builtins.list[TagReference]:
        """Child ``tag_references`` rows, read with ``refs[all]``."""
        from typing import cast

        manager = cast("SnapshotProfilePeriodTagManager", self._manager)
        return manager.references(self.key)

    def delete(self) -> None:
        """Delete this row."""
        from typing import cast

        manager = cast("SnapshotProfilePeriodTagManager", self._manager)
        manager.delete(self.key)


class SnapshotProfilePeriodTagManager(ResourceManager[SnapshotProfilePeriodTag]):
    """Manager for ``snapshot_profile_period_tags``.

    Pass a period key to only see that period's rows. Without one, the
    manager addresses the whole table.

    Writes accept ``snapshot_profile_period`` and ``refs`` only. Anything
    else is refused before the request, because VergeOS drops unknown
    fields and reports success.
    """

    _default_fields = _DEFAULT_PERIOD_TAG_FIELDS
    _endpoint = "snapshot_profile_period_tags"

    def __init__(self, client: VergeClient, period_key: int | None = None) -> None:
        super().__init__(client)
        self._period_key = period_key

    def _to_model(self, data: dict[str, Any]) -> SnapshotProfilePeriodTag:
        return SnapshotProfilePeriodTag(data, self)

    def _scope_bindings(self) -> builtins.list[tuple[str, Any]]:
        if self._period_key is None:
            return []
        return [("snapshot_profile_period", self._period_key)]

    def _scope_resource(self) -> str:
        return "Snapshot profile period tag"

    def list(
        self,
        filter: str | None = None,  # noqa: A002
        fields: str | builtins.list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        **filter_kwargs: Any,
    ) -> builtins.list[SnapshotProfilePeriodTag]:
        """List period-tag rows.

        A manager created for one period only returns that period's rows.
        """
        if self._period_key is not None:
            scope = f"snapshot_profile_period eq {self._period_key}"
            filter = f"({filter}) and {scope}" if filter else scope
        if fields is None:
            fields = list(_DEFAULT_PERIOD_TAG_FIELDS)
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
        fields: str | builtins.list[str] | None = None,
    ) -> SnapshotProfilePeriodTag:
        """Get one row by ``$key``.

        The table has no name column in the 26.1.8 listing, so lookup by
        name is refused.
        """
        if name is not None:
            raise ValueError("snapshot profile period tags have no name column; get by key")
        if fields is None:
            fields = list(_DEFAULT_PERIOD_TAG_FIELDS)
        return super().get(key, fields=fields)

    def create(
        self,
        *,
        snapshot_profile_period: int | None = None,
        refs: Any = None,
        **extra: Any,
    ) -> SnapshotProfilePeriodTag:
        """Create a period-tag row.

        Args:
            snapshot_profile_period: Period ``$key``. Filled in when this
                manager was opened for a period.
            refs: The ``refs`` value to store. Pass back a shape you read.
            **extra: Refused. Not a column on this table.

        Returns:
            The created row, re-read so the response is not just the POST receipt.
        """
        self._reject_unknown_fields(extra)
        period_key = self._period_key if self._period_key is not None else snapshot_profile_period
        if period_key is None:
            raise ValueError("snapshot_profile_period is required")
        if (
            self._period_key is not None
            and snapshot_profile_period is not None
            and int(snapshot_profile_period) != int(self._period_key)
        ):
            raise ValueError(
                f"this manager is scoped to period {self._period_key}, "
                f"not {snapshot_profile_period}"
            )
        body: dict[str, Any] = {"snapshot_profile_period": int(period_key)}
        if refs is not None:
            body["refs"] = refs
        response = super().create(**body)
        created = response.get("$key")
        if created is not None:
            return self.get(int(created))
        return response

    def update(
        self,
        key: int,
        *,
        snapshot_profile_period: int | None = None,
        refs: Any = None,
        **extra: Any,
    ) -> SnapshotProfilePeriodTag:
        """Update ``snapshot_profile_period`` or ``refs``."""
        self._reject_unknown_fields(extra)
        body: dict[str, Any] = {}
        if snapshot_profile_period is not None:
            if self._period_key is not None and int(snapshot_profile_period) != int(
                self._period_key
            ):
                raise ValueError(
                    f"this manager is scoped to period {self._period_key}, "
                    f"not {snapshot_profile_period}"
                )
            body["snapshot_profile_period"] = int(snapshot_profile_period)
        if refs is not None:
            body["refs"] = refs
        if not body:
            return self.get(key)
        self._ensure_in_scope(key)
        self._client._request("PUT", f"{self._endpoint}/{key}", json_data=body)
        return self.get(key)

    def references(self, key: int) -> builtins.list[TagReference]:
        """Read ``refs[all]`` for one period-tag row.

        Args:
            key: ``snapshot_profile_period_tags`` ``$key``.

        Returns:
            The nested rows. Empty when ``refs`` is a count or absent.
        """
        self._ensure_in_scope(key)
        response = self._client._request(
            "GET",
            f"{self._endpoint}/{key}",
            params={"fields": "refs[all]"},
        )
        if not isinstance(response, dict):
            raise NotFoundError(f"snapshot_profile_period_tags/{key} not found")
        from pyvergeos.resources.tags import TagReferenceManager

        manager = TagReferenceManager(self._client)
        manager._requested_aliases = None
        return [manager._to_model(row) for row in _rows_from_refs(response.get("refs"))]

    def _reject_unknown_fields(self, extra: dict[str, Any]) -> None:
        if not extra:
            return
        unknown = ", ".join(sorted(extra))
        raise ValueError(
            f"unknown snapshot_profile_period_tags field {unknown}; "
            "known columns are $key, snapshot_profile_period, and refs"
        )


class SnapshotProfileManager(ResourceManager[SnapshotProfile]):
    """Manager for snapshot profile operations.

    Snapshot profiles define automated snapshot schedules for VMs, NAS volumes,
    and cloud/system snapshots.

    Example:
        >>> # List all profiles
        >>> profiles = client.snapshot_profiles.list()

        >>> # Get a profile by name
        >>> profile = client.snapshot_profiles.get(name="Daily Backups")

        >>> # Create a new profile
        >>> profile = client.snapshot_profiles.create(
        ...     name="Production VMs",
        ...     description="Snapshot profile for production workloads",
        ... )

        >>> # Add schedule periods
        >>> profile.add_period(
        ...     name="Hourly",
        ...     frequency="hourly",
        ...     retention_seconds=86400,  # 1 day
        ... )
        >>> profile.add_period(
        ...     name="Daily",
        ...     frequency="daily",
        ...     retention_seconds=604800,  # 7 days
        ...     hour=2,
        ...     minute=0,
        ... )

        >>> # Delete a profile
        >>> client.snapshot_profiles.delete(profile.key)
    """

    #: Default projection, so that a caller's 'all' can be expanded
    #: into a true superset of it (issue #117).
    _default_fields = _DEFAULT_PROFILE_FIELDS

    _endpoint = "snapshot_profiles"

    def __init__(self, client: VergeClient) -> None:
        super().__init__(client)
        self._period_managers: dict[int, SnapshotProfilePeriodManager] = {}

    def _to_model(
        self,
        data: dict[str, Any],
        periods: builtins.list[SnapshotProfilePeriod] | None = None,
    ) -> SnapshotProfile:
        return SnapshotProfile(data, self, periods=periods)

    def periods(self, profile_key: int) -> SnapshotProfilePeriodManager:
        """Get the period manager for a profile.

        Args:
            profile_key: Profile $key (ID).

        Returns:
            SnapshotProfilePeriodManager for the profile.
        """
        if profile_key not in self._period_managers:
            self._period_managers[profile_key] = SnapshotProfilePeriodManager(
                self._client, profile_key
            )
        return self._period_managers[profile_key]

    def list(
        self,
        filter: str | None = None,
        fields: str | builtins.list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        *,
        include_periods: bool = False,
        **filter_kwargs: Any,
    ) -> builtins.list[SnapshotProfile]:
        """List snapshot profiles.

        Args:
            filter: OData filter string.
            fields: List of fields to return.
            limit: Maximum number of results.
            offset: Skip this many results.
            include_periods: If True, include schedule periods for each profile.
            **filter_kwargs: Additional filter arguments.

        Returns:
            List of SnapshotProfile objects sorted by name.

        Example:
            >>> # All profiles
            >>> profiles = client.snapshot_profiles.list()

            >>> # Profiles with periods
            >>> profiles = client.snapshot_profiles.list(include_periods=True)
            >>> for profile in profiles:
            ...     print(f"{profile.name}: {len(profile.periods or [])} periods")
        """
        conditions: builtins.list[str] = []

        if filter:
            conditions.append(f"({filter})")

        if filter_kwargs:
            conditions.append(build_filter(**filter_kwargs))

        combined_filter = " and ".join(conditions) if conditions else None

        if fields is None:
            fields = _DEFAULT_PROFILE_FIELDS

        params: dict[str, Any] = {}
        if combined_filter:
            params["filter"] = combined_filter
        if fields:
            params["fields"] = self._projection(fields)
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset
        params["sort"] = "+name"

        response = self._client._request("GET", self._endpoint, params=params)

        if response is None:
            return []

        if not isinstance(response, list):
            response = [response]

        profiles: builtins.list[SnapshotProfile] = []
        for item in response:
            profile_periods = None
            if include_periods:
                profile_key = item.get("$key")
                if profile_key:
                    try:
                        profile_periods = self.periods(int(profile_key)).list()
                    except Exception:
                        profile_periods = []
            profiles.append(self._to_model(item, periods=profile_periods))

        return profiles

    def get(
        self,
        key: int | None = None,
        *,
        name: str | None = None,
        fields: str | builtins.list[str] | None = None,
        include_periods: bool = False,
    ) -> SnapshotProfile:
        """Get a snapshot profile by key or name.

        Args:
            key: Profile $key (ID).
            name: Profile name.
            fields: List of fields to return.
            include_periods: If True, include schedule periods.

        Returns:
            SnapshotProfile object.

        Raises:
            NotFoundError: If profile not found.
            ValueError: If neither key nor name provided.
        """
        if fields is None:
            fields = _DEFAULT_PROFILE_FIELDS

        if key is not None:
            params: dict[str, Any] = {}
            if fields:
                params["fields"] = self._projection(fields)

            response = self._client._request("GET", f"{self._endpoint}/{key}", params=params)
            if response is None:
                raise NotFoundError(f"Snapshot profile {key} not found")
            if not isinstance(response, dict):
                raise NotFoundError(f"Snapshot profile {key} returned invalid response")

            profile_periods = None
            if include_periods:
                try:
                    profile_periods = self.periods(key).list()
                except Exception:
                    profile_periods = []

            return self._to_model(response, periods=profile_periods)

        if name is not None:
            results = self.list(filter=f"name eq {quote_value(name)}", fields=fields, limit=1)
            if not results:
                raise NotFoundError(f"Snapshot profile '{name}' not found")

            profile = results[0]
            if include_periods:
                profile._periods = self.periods(profile.key).list()
            return profile

        raise ValueError("Either key or name must be provided")

    def create(  # type: ignore[override]
        self,
        name: str,
        *,
        description: str | None = None,
        ignore_warnings: bool = False,
    ) -> SnapshotProfile:
        """Create a new snapshot profile.

        Args:
            name: Profile name (must be unique).
            description: Optional profile description.
            ignore_warnings: Ignore snapshot count estimate warnings.

        Returns:
            Created SnapshotProfile object.

        Raises:
            ValueError: If name is empty.
            APIError: If creation fails (e.g., duplicate name).

        Example:
            >>> profile = client.snapshot_profiles.create(
            ...     name="Production VMs",
            ...     description="Snapshot profile for production workloads",
            ... )
        """
        if not name:
            raise ValueError("name is required")

        body: dict[str, Any] = {"name": name}
        if description is not None:
            body["description"] = description
        if ignore_warnings:
            body["ignore_warnings"] = True

        response = self._client._request("POST", self._endpoint, json_data=body)
        if response is None:
            raise ValueError("No response from create operation")
        if not isinstance(response, dict):
            raise ValueError("Create operation returned invalid response")

        # Fetch the created profile with full fields
        created_key = response.get("$key")
        if created_key:
            return self.get(int(created_key))
        return self._to_model_unprojected(response)

    def update(self, key: int, **kwargs: Any) -> SnapshotProfile:
        """Update a snapshot profile.

        Args:
            key: Profile $key (ID).
            **kwargs: Fields to update (name, description, ignore_warnings).

        Returns:
            Updated SnapshotProfile object.

        Example:
            >>> profile = client.snapshot_profiles.update(
            ...     profile.key,
            ...     description="Updated description",
            ... )
        """
        self._client._request("PUT", f"{self._endpoint}/{key}", json_data=kwargs)
        return self.get(key)

    def delete(self, key: int) -> None:
        """Delete a snapshot profile.

        Uses the snapshot_profile_actions endpoint with delete action.
        The profile must not be in use by any VMs, volumes, or cloud snapshots.

        Args:
            key: Profile $key (ID).

        Raises:
            APIError: If deletion fails (e.g., profile in use).

        Example:
            >>> client.snapshot_profiles.delete(profile.key)
        """
        # Use the action endpoint for deletion
        body = {"snapshot_profile": key, "action": "delete"}
        self._client._request("POST", "snapshot_profile_actions", json_data=body)
