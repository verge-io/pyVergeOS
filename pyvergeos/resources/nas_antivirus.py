"""NAS volume antivirus management resources."""

from __future__ import annotations

import builtins
from typing import TYPE_CHECKING, Any

from pyvergeos.exceptions import NotFoundError
from pyvergeos.filters import build_filter
from pyvergeos.resources.base import ResourceManager, ResourceObject

if TYPE_CHECKING:
    from pyvergeos.client import VergeClient


class VolumeAntivirus(ResourceObject):
    """Volume antivirus configuration resource object.

    Represents antivirus configuration for a NAS volume, including
    scanning behavior, quarantine settings, and schedule profiles.

    Attributes:
        key: The antivirus config unique identifier ($key).
        volume: Parent volume key (40-char hex string).
        enabled: Whether antivirus is enabled.
        infected_action: Action on infected files (move or delete).
        on_access: Whether real-time on-access scanning is enabled.
        scan: Scan scope (entire or specific).
        include: Directories to scan (when scan=specific).
        exclude: Directories to exclude from scan.
        quarantine_location: Quarantine directory path.
        start_time_profile: Scan schedule profile key.
        status: Linked status record key.
        stats: Linked stats record key.
    """

    @property
    def volume_key(self) -> str | None:
        """Get the parent volume key.

        Note: NAS volume keys are 40-character hex strings, not integers.
        """
        vol = self.get("volume")
        return str(vol) if vol is not None else None

    def enable(self) -> dict[str, Any] | None:
        """Enable antivirus scanning for this volume.

        Returns:
            Action response dict or None.

        Example:
            >>> av = volume.antivirus.get()
            >>> av.enable()
        """
        from typing import cast

        manager = cast("VolumeAntivirusManager", self._manager)
        return manager._action(self.key, "enable")

    def disable(self) -> dict[str, Any] | None:
        """Disable antivirus scanning for this volume.

        Returns:
            Action response dict or None.

        Example:
            >>> av = volume.antivirus.get()
            >>> av.disable()
        """
        from typing import cast

        manager = cast("VolumeAntivirusManager", self._manager)
        return manager._action(self.key, "disable")

    def start_scan(self) -> dict[str, Any] | None:
        """Start an antivirus scan on this volume.

        Returns:
            Action response dict or None.

        Example:
            >>> av = volume.antivirus.get()
            >>> av.start_scan()
        """
        from typing import cast

        manager = cast("VolumeAntivirusManager", self._manager)
        return manager._action(self.key, "start")

    def stop_scan(self) -> dict[str, Any] | None:
        """Stop the current antivirus scan on this volume.

        Returns:
            Action response dict or None.

        Example:
            >>> av = volume.antivirus.get()
            >>> av.stop_scan()
        """
        from typing import cast

        manager = cast("VolumeAntivirusManager", self._manager)
        return manager._action(self.key, "stop")

    def get_status(self) -> VolumeAntivirusStatus:
        """Get the current antivirus scan status.

        Returns:
            VolumeAntivirusStatus object.

        Example:
            >>> av = volume.antivirus.get()
            >>> status = av.get_status()
            >>> print(f"Status: {status.status}")
        """
        from typing import cast

        manager = cast("VolumeAntivirusManager", self._manager)
        return VolumeAntivirusStatusManager(manager._client, antivirus_key=self.key).get()

    def get_stats(self) -> VolumeAntivirusStats:
        """Get antivirus scan statistics.

        Returns:
            VolumeAntivirusStats object.

        Example:
            >>> av = volume.antivirus.get()
            >>> stats = av.get_stats()
            >>> print(f"Infected files: {stats.infected_files}")
        """
        from typing import cast

        manager = cast("VolumeAntivirusManager", self._manager)
        return VolumeAntivirusStatsManager(manager._client, antivirus_key=self.key).get()

    @property
    def infections(self) -> VolumeAntivirusInfectionManager:
        """Get infection records for this antivirus configuration.

        Returns:
            VolumeAntivirusInfectionManager scoped to this config.

        Example:
            >>> av = volume.antivirus.get()
            >>> for infection in av.infections.list():
            ...     print(f"{infection.filename}: {infection.virus}")
        """
        from typing import cast

        manager = cast("VolumeAntivirusManager", self._manager)
        return VolumeAntivirusInfectionManager(manager._client, antivirus_key=self.key)

    @property
    def logs(self) -> VolumeAntivirusLogManager:
        """Get scan activity logs for this antivirus configuration.

        Returns:
            VolumeAntivirusLogManager scoped to this config.

        Example:
            >>> av = volume.antivirus.get()
            >>> for log in av.logs.list():
            ...     print(f"{log.level}: {log.text}")
        """
        from typing import cast

        manager = cast("VolumeAntivirusManager", self._manager)
        return VolumeAntivirusLogManager(manager._client, antivirus_key=self.key)


class VolumeAntivirusStatus(ResourceObject):
    """Volume antivirus status resource object.

    Represents the current operational status of antivirus scanning.

    Attributes:
        key: The status unique identifier ($key).
        volume_antivirus: Parent antivirus config key.
        status: Current status (offline, scanning, error).
        status_info: Human-readable status detail.
        state: Overall state (online, offline, warning, error).
        last_update: Last modification timestamp.
    """

    @property
    def is_scanning(self) -> bool:
        """Check if a scan is currently in progress."""
        return self.get("status") == "scanning"

    @property
    def is_offline(self) -> bool:
        """Check if antivirus is offline."""
        return self.get("status") == "offline" or self.get("state") == "offline"

    @property
    def has_error(self) -> bool:
        """Check if antivirus is in error state."""
        return self.get("status") == "error" or self.get("state") == "error"


class VolumeAntivirusStats(ResourceObject):
    """Volume antivirus statistics resource object.

    Represents scan statistics including infection counts and scan history.

    Attributes:
        key: The stats unique identifier ($key).
        volume_antivirus: Parent antivirus config key.
        infected_files: Count of infected files found.
        quarantine_count: Count of quarantined files.
        last_scan: Last scan timestamp.
        created: Record creation time.
    """

    @property
    def has_infections(self) -> bool:
        """Check if any infected files have been found."""
        infected = self.get("infected_files", 0)
        return bool(infected and infected > 0)


class VolumeAntivirusInfection(ResourceObject):
    """Volume antivirus infection record resource object.

    Represents a detected infection event.

    Attributes:
        key: The infection record unique identifier ($key).
        volume_antivirus: Parent antivirus config key.
        filename: Infected file path.
        virus: Virus/malware name.
        action: Action taken (move or delete).
        timestamp: Detection timestamp (microseconds).
    """

    pass


class VolumeAntivirusLog(ResourceObject):
    """Volume antivirus scan activity log resource object.

    Represents a logged event during antivirus operations.

    Attributes:
        key: The log record unique identifier ($key).
        volume_antivirus: Parent antivirus config key.
        level: Log level (audit, message, warning, error, critical, summary, debug).
        text: Log message.
        user: User who triggered the action.
        timestamp: Log timestamp (microseconds).
    """

    pass


class NasServiceAntivirus(ResourceObject):
    """NAS service antivirus configuration resource object.

    Represents service-level antivirus configuration for a NAS service.

    Note:
        NAS service needs 8GB+ RAM for antivirus support.

    Attributes:
        key: The service antivirus config unique identifier ($key).
        service: Parent NAS service key.
        enabled: Whether antivirus is enabled.
        max_recursion: Directory recursion depth limit.
        database_private_mirror: Private mirror URL for virus definitions.
        database_location: Virus database directory path.
        database_updates_enabled: Whether automatic database updates are enabled.
    """

    @property
    def service_key(self) -> int | None:
        """Get the parent NAS service key."""
        svc = self.get("service")
        return int(svc) if svc is not None else None


class VolumeAntivirusManager(ResourceManager[VolumeAntivirus]):
    """Manager for volume antivirus configuration operations.

    Can be used standalone or scoped to a specific volume.

    Example:
        >>> # Get antivirus config for a volume
        >>> av = volume.antivirus.get()

        >>> # Update configuration
        >>> av_updated = volume.antivirus.update(
        ...     key=av.key,
        ...     enabled=True,
        ...     on_access=True
        ... )

        >>> # Enable and start scan
        >>> av.enable()
        >>> av.start_scan()

        >>> # Check status
        >>> status = av.get_status()
        >>> print(f"Status: {status.status}")
    """

    _endpoint = "volume_antivirus"

    _default_fields = [
        "$key",
        "volume",
        "volume#$display as volume_display",
        "volume#name as volume_name",
        "enabled",
        "infected_action",
        "on_access",
        "scan",
        "include",
        "exclude",
        "quarantine_location",
        "start_time_profile",
        "start_time_profile#$display as start_time_profile_display",
        "status",
        "stats",
    ]

    def __init__(self, client: VergeClient, *, volume_key: str | None = None) -> None:
        super().__init__(client)
        self._volume_key = volume_key

    def list(
        self,
        filter: str | None = None,
        fields: builtins.list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        volume: str | None = None,
        enabled: bool | None = None,
        **filter_kwargs: Any,
    ) -> builtins.list[VolumeAntivirus]:
        """List volume antivirus configurations with optional filtering.

        Args:
            filter: OData filter string.
            fields: List of fields to return (uses defaults if not specified).
            limit: Maximum number of results.
            offset: Skip this many results.
            volume: Filter by volume (key or name). Ignored if manager is scoped.
            enabled: Filter by enabled state.
            **filter_kwargs: Shorthand filter arguments.

        Returns:
            List of VolumeAntivirus objects.

        Example:
            >>> # List all antivirus configs
            >>> configs = client.volume_antivirus.list()

            >>> # List enabled configs only
            >>> enabled = client.volume_antivirus.list(enabled=True)
        """
        params: dict[str, Any] = {}

        filters: builtins.list[str] = []
        if filter:
            filters.append(filter)
        if filter_kwargs:
            filters.append(build_filter(**filter_kwargs))

        # Add volume filter (from scope or parameter)
        volume_key = self._volume_key
        if volume_key is None and volume is not None:
            # Check if it looks like a volume key (40-char hex) or a name
            if len(volume) == 40 and all(c in "0123456789abcdef" for c in volume.lower()):
                volume_key = volume
            else:
                # Look up volume by name
                vol_response = self._client._request(
                    "GET",
                    "volumes",
                    params={"filter": f"name eq '{volume}'", "fields": "$key", "limit": "1"},
                )
                if vol_response:
                    if isinstance(vol_response, list):
                        vol_response = vol_response[0] if vol_response else None
                    if vol_response:
                        volume_key = vol_response.get("$key")

        if volume_key is not None:
            # Volume keys are 40-char hex strings
            filters.append(f"volume eq '{volume_key}'")

        # Add enabled filter
        if enabled is not None:
            filters.append(f"enabled eq {1 if enabled else 0}")

        if filters:
            params["filter"] = " and ".join(filters)

        # Use default fields if not specified
        if fields:
            params["fields"] = ",".join(fields)
        else:
            params["fields"] = ",".join(self._default_fields)

        # Pagination
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset

        response = self._client._request("GET", self._endpoint, params=params)

        if response is None:
            return []

        if not isinstance(response, list):
            response = [response]

        return [self._to_model(item) for item in response if item]

    def get(  # type: ignore[override]
        self,
        key: int | None = None,
        *,
        volume: str | None = None,
        fields: builtins.list[str] | None = None,
    ) -> VolumeAntivirus:
        """Get a single volume antivirus configuration.

        Args:
            key: Antivirus config $key (ID).
            volume: Volume key or name (for scoped lookup).
            fields: List of fields to return.

        Returns:
            VolumeAntivirus object.

        Raises:
            NotFoundError: If antivirus config not found.

        Example:
            >>> # Get by key
            >>> av = client.volume_antivirus.get(1)

            >>> # Get by volume name
            >>> av = client.volume_antivirus.get(volume="FileShare")

            >>> # Get from scoped manager
            >>> av = volume.antivirus.get()
        """
        if key is not None:
            params: dict[str, Any] = {}
            if fields:
                params["fields"] = ",".join(fields)
            else:
                params["fields"] = ",".join(self._default_fields)

            response = self._client._request("GET", f"{self._endpoint}/{key}", params=params)
            if response is None:
                raise NotFoundError(f"Volume antivirus config with key {key} not found")
            if not isinstance(response, dict):
                raise NotFoundError(
                    f"Volume antivirus config with key {key} returned invalid response"
                )
            return self._to_model(response)

        # If scoped to volume or volume provided, find by unique constraint
        volume_key = self._volume_key or volume
        if volume_key is not None:
            # Resolve volume name to key if needed
            if not (
                len(volume_key) == 40 and all(c in "0123456789abcdef" for c in volume_key.lower())
            ):
                vol_response = self._client._request(
                    "GET",
                    "volumes",
                    params={"filter": f"name eq '{volume_key}'", "fields": "$key", "limit": "1"},
                )
                if vol_response:
                    if isinstance(vol_response, list):
                        vol_response = vol_response[0] if vol_response else None
                    if vol_response:
                        volume_key = vol_response.get("$key")

            results = self.list(filter=f"volume eq '{volume_key}'", fields=fields, limit=1)
            if not results:
                raise NotFoundError(f"Volume antivirus config not found for volume {volume_key}")
            return results[0]

        raise ValueError("Either key or volume must be provided")

    def create(  # type: ignore[override]
        self,
        volume: str,
        *,
        enabled: bool = False,
        infected_action: str = "move",
        on_access: bool = False,
        scan: str = "entire",
        include: str | None = None,
        exclude: str | None = None,
        quarantine_location: str = ".quarantine",
        start_time_profile: int | None = None,
    ) -> VolumeAntivirus:
        """Create a new volume antivirus configuration.

        Args:
            volume: Volume key (40-char hex string).
            enabled: Enable antivirus scanning.
            infected_action: Action on infected files (move or delete).
            on_access: Enable real-time on-access scanning.
            scan: Scan scope (entire or specific).
            include: Newline-delimited directories to scan (when scan=specific).
            exclude: Newline-delimited directories to exclude.
            quarantine_location: Quarantine directory path.
            start_time_profile: Scan schedule profile key.

        Returns:
            Created VolumeAntivirus object.

        Example:
            >>> # Create with defaults
            >>> av = client.volume_antivirus.create(vol.key)

            >>> # Create with custom settings
            >>> av = client.volume_antivirus.create(
            ...     vol.key,
            ...     enabled=True,
            ...     on_access=True,
            ...     exclude="/temp\n/cache"
            ... )
        """
        body: dict[str, Any] = {
            "volume": volume,
            "enabled": enabled,
            "infected_action": infected_action,
            "on_access": on_access,
            "scan": scan,
            "quarantine_location": quarantine_location,
        }

        if include is not None:
            body["include"] = include

        if exclude is not None:
            body["exclude"] = exclude

        if start_time_profile is not None:
            body["start_time_profile"] = start_time_profile

        response = self._client._request("POST", self._endpoint, json_data=body)

        # Get the created config
        if response and isinstance(response, dict):
            av_key = response.get("$key")
            if av_key:
                return self.get(key=av_key)

        # Fallback: search by volume
        return self.get(volume=volume)

    def update(  # type: ignore[override]
        self,
        key: int,
        *,
        enabled: bool | None = None,
        infected_action: str | None = None,
        on_access: bool | None = None,
        scan: str | None = None,
        include: str | None = None,
        exclude: str | None = None,
        quarantine_location: str | None = None,
        start_time_profile: int | None = None,
    ) -> VolumeAntivirus:
        """Update a volume antivirus configuration.

        Args:
            key: Antivirus config $key (ID).
            enabled: Enable or disable antivirus.
            infected_action: Action on infected files (move or delete).
            on_access: Enable or disable real-time scanning.
            scan: Scan scope (entire or specific).
            include: Newline-delimited directories to scan.
            exclude: Newline-delimited directories to exclude.
            quarantine_location: Quarantine directory path.
            start_time_profile: Scan schedule profile key.

        Returns:
            Updated VolumeAntivirus object.

        Example:
            >>> # Enable on-access scanning
            >>> av = client.volume_antivirus.update(1, on_access=True)

            >>> # Change quarantine location
            >>> av = client.volume_antivirus.update(1, quarantine_location="/quarantine")
        """
        body: dict[str, Any] = {}

        if enabled is not None:
            body["enabled"] = enabled

        if infected_action is not None:
            body["infected_action"] = infected_action

        if on_access is not None:
            body["on_access"] = on_access

        if scan is not None:
            body["scan"] = scan

        if include is not None:
            body["include"] = include

        if exclude is not None:
            body["exclude"] = exclude

        if quarantine_location is not None:
            body["quarantine_location"] = quarantine_location

        if start_time_profile is not None:
            body["start_time_profile"] = start_time_profile

        if not body:
            return self.get(key)

        self._client._request("PUT", f"{self._endpoint}/{key}", json_data=body)
        return self.get(key)

    def delete(self, key: int) -> None:
        """Delete a volume antivirus configuration.

        Args:
            key: Antivirus config $key (ID).

        Example:
            >>> client.volume_antivirus.delete(1)
        """
        self._client._request("DELETE", f"{self._endpoint}/{key}")

    def _action(
        self, key: int, action: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any] | None:
        """Execute an antivirus action (enable, disable, start, stop).

        Args:
            key: Antivirus config $key (ID).
            action: Action name (enable, disable, start, stop).
            params: Optional action parameters.

        Returns:
            Action response dict or None.
        """
        body: dict[str, Any] = {"volume_antivirus": key, "action": action}

        if params:
            body["params"] = params

        result = self._client._request("POST", "volume_antivirus_actions", json_data=body)
        if isinstance(result, dict):
            return result
        return None

    def _to_model(self, data: dict[str, Any]) -> VolumeAntivirus:
        """Convert API response to VolumeAntivirus object."""
        return VolumeAntivirus(data, self)


class VolumeAntivirusStatusManager(ResourceManager[VolumeAntivirusStatus]):
    """Manager for volume antivirus status operations (read-only).

    Scoped to a specific antivirus configuration.

    Example:
        >>> av = volume.antivirus.get()
        >>> status = av.get_status()
        >>> print(f"Status: {status.status}")
    """

    _endpoint = "volume_antivirus_status"

    _default_fields = [
        "$key",
        "volume_antivirus",
        "status",
        "status_info",
        "state",
        "last_update",
    ]

    def __init__(self, client: VergeClient, *, antivirus_key: int | None = None) -> None:
        super().__init__(client)
        self._antivirus_key = antivirus_key

    def get(self, key: int | None = None) -> VolumeAntivirusStatus:  # type: ignore[override]
        """Get antivirus status.

        Args:
            key: Status $key (ID). If not provided, looks up by antivirus_key.

        Returns:
            VolumeAntivirusStatus object.

        Raises:
            NotFoundError: If status not found.

        Example:
            >>> status = av.get_status()
        """
        if key is not None:
            params: dict[str, Any] = {"fields": ",".join(self._default_fields)}
            response = self._client._request("GET", f"{self._endpoint}/{key}", params=params)
            if response is None:
                raise NotFoundError(f"Volume antivirus status with key {key} not found")
            if not isinstance(response, dict):
                raise NotFoundError(
                    f"Volume antivirus status with key {key} returned invalid response"
                )
            return self._to_model(response)

        # Look up by antivirus_key (unique constraint)
        if self._antivirus_key is not None:
            results = self.list(
                filter=f"volume_antivirus eq {self._antivirus_key}", fields=None, limit=1
            )
            if not results:
                raise NotFoundError(
                    f"Volume antivirus status not found for config {self._antivirus_key}"
                )
            return results[0]

        raise ValueError("Either key or antivirus_key must be provided")

    def list(
        self,
        filter: str | None = None,
        fields: builtins.list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        **filter_kwargs: Any,
    ) -> builtins.list[VolumeAntivirusStatus]:
        """List volume antivirus status records.

        Args:
            filter: OData filter string.
            fields: List of fields to return.
            limit: Maximum number of results.
            offset: Skip this many results.
            **filter_kwargs: Shorthand filter arguments.

        Returns:
            List of VolumeAntivirusStatus objects.
        """
        params: dict[str, Any] = {}

        filters: builtins.list[str] = []
        if filter:
            filters.append(filter)
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
            response = [response]

        return [self._to_model(item) for item in response if item]

    def _to_model(self, data: dict[str, Any]) -> VolumeAntivirusStatus:
        """Convert API response to VolumeAntivirusStatus object."""
        return VolumeAntivirusStatus(data, self)


class VolumeAntivirusStatsManager(ResourceManager[VolumeAntivirusStats]):
    """Manager for volume antivirus statistics operations (read-only).

    Scoped to a specific antivirus configuration.

    Example:
        >>> av = volume.antivirus.get()
        >>> stats = av.get_stats()
        >>> print(f"Infected files: {stats.infected_files}")
    """

    _endpoint = "volume_antivirus_stats"

    _default_fields = [
        "$key",
        "volume_antivirus",
        "infected_files",
        "quarantine_count",
        "last_scan",
        "created",
    ]

    def __init__(self, client: VergeClient, *, antivirus_key: int | None = None) -> None:
        super().__init__(client)
        self._antivirus_key = antivirus_key

    def get(self, key: int | None = None) -> VolumeAntivirusStats:  # type: ignore[override]
        """Get antivirus statistics.

        Args:
            key: Stats $key (ID). If not provided, looks up by antivirus_key.

        Returns:
            VolumeAntivirusStats object.

        Raises:
            NotFoundError: If stats not found.

        Example:
            >>> stats = av.get_stats()
        """
        if key is not None:
            params: dict[str, Any] = {"fields": ",".join(self._default_fields)}
            response = self._client._request("GET", f"{self._endpoint}/{key}", params=params)
            if response is None:
                raise NotFoundError(f"Volume antivirus stats with key {key} not found")
            if not isinstance(response, dict):
                raise NotFoundError(
                    f"Volume antivirus stats with key {key} returned invalid response"
                )
            return self._to_model(response)

        # Look up by antivirus_key (unique constraint)
        if self._antivirus_key is not None:
            results = self.list(
                filter=f"volume_antivirus eq {self._antivirus_key}", fields=None, limit=1
            )
            if not results:
                raise NotFoundError(
                    f"Volume antivirus stats not found for config {self._antivirus_key}"
                )
            return results[0]

        raise ValueError("Either key or antivirus_key must be provided")

    def list(
        self,
        filter: str | None = None,
        fields: builtins.list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        **filter_kwargs: Any,
    ) -> builtins.list[VolumeAntivirusStats]:
        """List volume antivirus statistics records.

        Args:
            filter: OData filter string.
            fields: List of fields to return.
            limit: Maximum number of results.
            offset: Skip this many results.
            **filter_kwargs: Shorthand filter arguments.

        Returns:
            List of VolumeAntivirusStats objects.
        """
        params: dict[str, Any] = {}

        filters: builtins.list[str] = []
        if filter:
            filters.append(filter)
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
            response = [response]

        return [self._to_model(item) for item in response if item]

    def _to_model(self, data: dict[str, Any]) -> VolumeAntivirusStats:
        """Convert API response to VolumeAntivirusStats object."""
        return VolumeAntivirusStats(data, self)


class VolumeAntivirusInfectionManager(ResourceManager[VolumeAntivirusInfection]):
    """Manager for volume antivirus infection records (read-only).

    Scoped to a specific antivirus configuration. Infections are
    auto-expired after 7 days and limited to 1000 records per config.

    Example:
        >>> av = volume.antivirus.get()
        >>> for infection in av.infections.list():
        ...     print(f"{infection.filename}: {infection.virus}")
    """

    _endpoint = "volume_antivirus_infections"

    _default_fields = [
        "$key",
        "volume_antivirus",
        "filename",
        "virus",
        "action",
        "timestamp",
    ]

    def __init__(self, client: VergeClient, *, antivirus_key: int | None = None) -> None:
        super().__init__(client)
        self._antivirus_key = antivirus_key

    def list(  # noqa: A002
        self,
        filter: str | None = None,
        fields: builtins.list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        **filter_kwargs: Any,
    ) -> builtins.list[VolumeAntivirusInfection]:
        """List volume antivirus infection records.

        Args:
            filter: OData filter string.
            fields: List of fields to return.
            limit: Maximum number of results.
            offset: Skip this many results.
            **filter_kwargs: Shorthand filter arguments.

        Returns:
            List of VolumeAntivirusInfection objects.

        Example:
            >>> infections = av.infections.list()
            >>> recent = av.infections.list(limit=10)
        """
        params: dict[str, Any] = {}

        filters: builtins.list[str] = []
        if filter:
            filters.append(filter)
        if filter_kwargs:
            filters.append(build_filter(**filter_kwargs))

        # Add scoped antivirus filter
        if self._antivirus_key is not None:
            filters.append(f"volume_antivirus eq {self._antivirus_key}")

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
            response = [response]

        return [self._to_model(item) for item in response if item]

    def _to_model(self, data: dict[str, Any]) -> VolumeAntivirusInfection:
        """Convert API response to VolumeAntivirusInfection object."""
        return VolumeAntivirusInfection(data, self)


class VolumeAntivirusLogManager(ResourceManager[VolumeAntivirusLog]):
    """Manager for volume antivirus scan activity logs (read-only).

    Scoped to a specific antivirus configuration. Logs are
    auto-expired after 7 days and limited to 1000 records per config.

    Example:
        >>> av = volume.antivirus.get()
        >>> for log in av.logs.list():
        ...     print(f"{log.level}: {log.text}")
    """

    _endpoint = "volume_antivirus_logs"

    _default_fields = [
        "$key",
        "volume_antivirus",
        "level",
        "text",
        "user",
        "timestamp",
    ]

    def __init__(self, client: VergeClient, *, antivirus_key: int | None = None) -> None:
        super().__init__(client)
        self._antivirus_key = antivirus_key

    def list(  # noqa: A002
        self,
        filter: str | None = None,
        fields: builtins.list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        level: str | None = None,
        **filter_kwargs: Any,
    ) -> builtins.list[VolumeAntivirusLog]:
        """List volume antivirus scan activity logs.

        Args:
            filter: OData filter string.
            fields: List of fields to return.
            limit: Maximum number of results.
            offset: Skip this many results.
            level: Filter by log level (audit, message, warning, error, critical, summary, debug).
            **filter_kwargs: Shorthand filter arguments.

        Returns:
            List of VolumeAntivirusLog objects.

        Example:
            >>> logs = av.logs.list()
            >>> errors = av.logs.list(level="error")
        """
        params: dict[str, Any] = {}

        filters: builtins.list[str] = []
        if filter:
            filters.append(filter)
        if filter_kwargs:
            filters.append(build_filter(**filter_kwargs))

        # Add scoped antivirus filter
        if self._antivirus_key is not None:
            filters.append(f"volume_antivirus eq {self._antivirus_key}")

        # Add level filter
        if level is not None:
            filters.append(f"level eq '{level}'")

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
            response = [response]

        return [self._to_model(item) for item in response if item]

    def _to_model(self, data: dict[str, Any]) -> VolumeAntivirusLog:
        """Convert API response to VolumeAntivirusLog object."""
        return VolumeAntivirusLog(data, self)


class NasServiceAntivirusManager(ResourceManager[NasServiceAntivirus]):
    """Manager for NAS service antivirus configuration operations.

    Scoped to a specific NAS service.

    Note:
        NAS service requires 8GB+ RAM for antivirus support.

    Example:
        >>> # Get service antivirus config
        >>> svc_av = nas.antivirus.get()

        >>> # Update settings
        >>> svc_av = nas.antivirus.update(
        ...     key=svc_av.key,
        ...     max_recursion=20
        ... )
    """

    _endpoint = "vm_service_antivirus"

    _default_fields = [
        "$key",
        "service",
        "service#$display as service_display",
        "enabled",
        "max_recursion",
        "database_private_mirror",
        "database_location",
        "database_updates_enabled",
    ]

    def __init__(self, client: VergeClient, *, service_key: int | None = None) -> None:
        super().__init__(client)
        self._service_key = service_key

    def get(self, key: int | None = None) -> NasServiceAntivirus:  # type: ignore[override]
        """Get NAS service antivirus configuration.

        Args:
            key: Service antivirus config $key (ID). If not provided, looks up by service_key.

        Returns:
            NasServiceAntivirus object.

        Raises:
            NotFoundError: If service antivirus config not found.

        Example:
            >>> svc_av = nas.antivirus.get()
        """
        if key is not None:
            params: dict[str, Any] = {"fields": ",".join(self._default_fields)}
            response = self._client._request("GET", f"{self._endpoint}/{key}", params=params)
            if response is None:
                raise NotFoundError(f"NAS service antivirus config with key {key} not found")
            if not isinstance(response, dict):
                raise NotFoundError(
                    f"NAS service antivirus config with key {key} returned invalid response"
                )
            return self._to_model(response)

        # Look up by service_key (unique constraint)
        if self._service_key is not None:
            results = self.list(filter=f"service eq {self._service_key}", fields=None, limit=1)
            if not results:
                raise NotFoundError(
                    f"NAS service antivirus config not found for service {self._service_key}"
                )
            return results[0]

        raise ValueError("Either key or service_key must be provided")

    def list(
        self,
        filter: str | None = None,
        fields: builtins.list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        **filter_kwargs: Any,
    ) -> builtins.list[NasServiceAntivirus]:
        """List NAS service antivirus configurations.

        Args:
            filter: OData filter string.
            fields: List of fields to return.
            limit: Maximum number of results.
            offset: Skip this many results.
            **filter_kwargs: Shorthand filter arguments.

        Returns:
            List of NasServiceAntivirus objects.
        """
        params: dict[str, Any] = {}

        filters: builtins.list[str] = []
        if filter:
            filters.append(filter)
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
            response = [response]

        return [self._to_model(item) for item in response if item]

    def update(  # type: ignore[override]
        self,
        key: int,
        *,
        enabled: bool | None = None,
        max_recursion: int | None = None,
        database_private_mirror: str | None = None,
        database_location: str | None = None,
        database_updates_enabled: bool | None = None,
    ) -> NasServiceAntivirus:
        """Update NAS service antivirus configuration.

        Args:
            key: Service antivirus config $key (ID).
            enabled: Enable or disable antivirus support (requires 8GB+ RAM).
            max_recursion: Directory recursion depth limit (0-100).
            database_private_mirror: Private mirror URL for virus definitions.
            database_location: Virus database directory path.
            database_updates_enabled: Enable or disable automatic database updates.

        Returns:
            Updated NasServiceAntivirus object.

        Example:
            >>> svc_av = client.nas_service_antivirus.update(1, max_recursion=20)
        """
        body: dict[str, Any] = {}

        if enabled is not None:
            body["enabled"] = enabled

        if max_recursion is not None:
            body["max_recursion"] = max_recursion

        if database_private_mirror is not None:
            body["database_private_mirror"] = database_private_mirror

        if database_location is not None:
            body["database_location"] = database_location

        if database_updates_enabled is not None:
            body["database_updates_enabled"] = database_updates_enabled

        if not body:
            return self.get(key)

        self._client._request("PUT", f"{self._endpoint}/{key}", json_data=body)
        return self.get(key)

    def _to_model(self, data: dict[str, Any]) -> NasServiceAntivirus:
        """Convert API response to NasServiceAntivirus object."""
        return NasServiceAntivirus(data, self)
