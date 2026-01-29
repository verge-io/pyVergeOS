"""Snapshot profile resource manager for VergeOS backup/DR."""

from __future__ import annotations

import builtins
from datetime import timedelta
from typing import TYPE_CHECKING, Any

from pyvergeos.exceptions import NotFoundError
from pyvergeos.filters import build_filter
from pyvergeos.resources.base import ResourceManager, ResourceObject

if TYPE_CHECKING:
    from pyvergeos.client import VergeClient


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
    "skip_missed",
    "max_tier",
    "quiesce",
    "min_snapshots",
    "immutable",
    "estimated_snapshot_count",
]


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
        skip_missed: Skip if snapshot time was missed.
        max_tier: Maximum storage tier for snapshots (1-5).
        quiesce: Whether to quiesce disks during snapshot.
        min_snapshots: Minimum snapshots to retain.
        is_immutable: Whether snapshots are immutable (system snapshots only).
        estimated_snapshot_count: Estimated number of snapshots.
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
    def skip_missed(self) -> bool:
        """Check if missed snapshots should be skipped."""
        return bool(self.get("skip_missed", False))

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

    def save(self, **kwargs: Any) -> SnapshotProfilePeriod:
        """Save changes to period.

        Args:
            **kwargs: Fields to update.

        Returns:
            Updated period object.
        """
        from typing import cast

        manager = cast("SnapshotProfilePeriodManager", self._manager)
        return manager.update(self.key, **kwargs)

    def delete(self) -> None:
        """Delete this period."""
        from typing import cast

        manager = cast("SnapshotProfilePeriodManager", self._manager)
        manager.delete(self.key)

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

        manager = cast("SnapshotProfileManager", self._manager)
        return manager.update(self.key, **kwargs)

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
        skip_missed: bool = False,
        max_tier: int = 1,
        quiesce: bool = False,
        min_snapshots: int = 1,
        immutable: bool = False,
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
            skip_missed: Skip if snapshot time was missed.
            max_tier: Maximum storage tier (1-5).
            quiesce: Enable disk quiescing.
            min_snapshots: Minimum snapshots to retain.
            immutable: Make snapshots immutable (system snapshots only).

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
            skip_missed=skip_missed,
            max_tier=max_tier,
            quiesce=quiesce,
            min_snapshots=min_snapshots,
            immutable=immutable,
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

    _endpoint = "snapshot_profile_periods"

    def __init__(self, client: VergeClient, profile_key: int) -> None:
        super().__init__(client)
        self._profile_key = profile_key

    def _to_model(self, data: dict[str, Any]) -> SnapshotProfilePeriod:
        return SnapshotProfilePeriod(data, self)

    def list(
        self,
        filter: str | None = None,
        fields: builtins.list[str] | None = None,
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
            params["fields"] = ",".join(fields)
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
        fields: builtins.list[str] | None = None,
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
                params["fields"] = ",".join(fields)

            response = self._client._request(
                "GET", f"{self._endpoint}/{key}", params=params
            )
            if response is None:
                raise NotFoundError(f"Period {key} not found")
            if not isinstance(response, dict):
                raise NotFoundError(f"Period {key} returned invalid response")

            # Verify this period belongs to our profile
            period = self._to_model(response)
            if period.profile_key != self._profile_key:
                raise NotFoundError(
                    f"Period {key} does not belong to profile {self._profile_key}"
                )
            return period

        if name is not None:
            escaped_name = name.replace("'", "''")
            results = self.list(filter=f"name eq '{escaped_name}'", fields=fields)
            if not results:
                raise NotFoundError(
                    f"Period '{name}' not found in profile {self._profile_key}"
                )
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
        skip_missed: bool = False,
        max_tier: int = 1,
        quiesce: bool = False,
        min_snapshots: int = 1,
        immutable: bool = False,
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
            skip_missed: Skip if snapshot time was missed.
            max_tier: Maximum storage tier (1-5).
            quiesce: Enable disk quiescing.
            min_snapshots: Minimum snapshots to retain.
            immutable: Make snapshots immutable (system snapshots only).

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
                f"Invalid day_of_week '{day_of_week}'. "
                f"Must be one of: {', '.join(DAYS_OF_WEEK)}"
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
            "skip_missed": skip_missed,
            "max_tier": str(max_tier),
            "quiesce": quiesce,
            "min_snapshots": min_snapshots,
            "immutable": immutable,
        }

        response = self._client._request("POST", self._endpoint, json_data=body)
        if response is None:
            raise ValueError("No response from create operation")
        if not isinstance(response, dict):
            raise ValueError("Create operation returned invalid response")

        # Fetch the created period with full fields
        created_key = response.get("$key")
        if created_key:
            return self.get(int(created_key))
        return self._to_model(response)

    def update(self, key: int, **kwargs: Any) -> SnapshotProfilePeriod:
        """Update a period.

        Args:
            key: Period $key (ID).
            **kwargs: Fields to update (name, frequency, retention, minute, hour,
                     day_of_week, day_of_month, month, skip_missed, max_tier,
                     quiesce, min_snapshots, immutable).

        Returns:
            Updated SnapshotProfilePeriod object.
        """
        # Validate parameters if provided
        if "frequency" in kwargs and kwargs["frequency"] not in FREQUENCIES:
            raise ValueError(
                f"Invalid frequency. Must be one of: {', '.join(FREQUENCIES)}"
            )
        if "day_of_week" in kwargs and kwargs["day_of_week"] not in DAYS_OF_WEEK:
            raise ValueError(
                f"Invalid day_of_week. Must be one of: {', '.join(DAYS_OF_WEEK)}"
            )
        if "max_tier" in kwargs:
            kwargs["max_tier"] = str(kwargs["max_tier"])

        self._client._request("PUT", f"{self._endpoint}/{key}", json_data=kwargs)
        return self.get(key)

    def delete(self, key: int) -> None:
        """Delete a period.

        Args:
            key: Period $key (ID).
        """
        self._client._request("DELETE", f"{self._endpoint}/{key}")


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
        fields: builtins.list[str] | None = None,
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
            params["fields"] = ",".join(fields)
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
        fields: builtins.list[str] | None = None,
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
                params["fields"] = ",".join(fields)

            response = self._client._request(
                "GET", f"{self._endpoint}/{key}", params=params
            )
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
            escaped_name = name.replace("'", "''")
            results = self.list(
                filter=f"name eq '{escaped_name}'", fields=fields, limit=1
            )
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
        return self._to_model(response)

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
