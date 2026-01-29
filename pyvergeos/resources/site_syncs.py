"""Site sync resource managers for VergeOS backup/DR operations."""

from __future__ import annotations

import builtins
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any

from pyvergeos.exceptions import NotFoundError, ValidationError
from pyvergeos.filters import build_filter
from pyvergeos.resources.base import ResourceManager, ResourceObject

if TYPE_CHECKING:
    from pyvergeos.client import VergeClient


# Default fields for outgoing sync list operations
_DEFAULT_OUTGOING_SYNC_FIELDS = [
    "$key",
    "site",
    "name",
    "description",
    "enabled",
    "status",
    "status_info",
    "state",
    "url",
    "encryption",
    "compression",
    "netinteg",
    "threads",
    "file_threads",
    "sendthrottle",
    "destination_tier",
    "queue_retry_count",
    "queue_retry_interval_seconds",
    "queue_retry_interval_multiplier",
    "last_run",
    "remote_min_snapshots",
    "note",
]

# Default fields for incoming sync list operations
_DEFAULT_INCOMING_SYNC_FIELDS = [
    "$key",
    "site",
    "name",
    "description",
    "enabled",
    "status",
    "status_info",
    "state",
    "sync_id",
    "registration_code",
    "public_ip",
    "force_tier",
    "min_snapshots",
    "last_sync",
    "vsan_host",
    "vsan_port",
    "request_url",
    "system_created",
]

# Default fields for sync schedule list operations
_DEFAULT_SCHEDULE_FIELDS = [
    "$key",
    "site_syncs_outgoing",
    "profile_period",
    "retention",
    "priority",
    "do_not_expire",
    "destination_prefix",
]


class SiteSyncOutgoing(ResourceObject):
    """Outgoing site sync resource object.

    Outgoing syncs send cloud snapshots from this system to a remote site
    for disaster recovery purposes.

    Properties:
        site_key: Key of the associated site.
        name: Sync name.
        description: Sync description.
        is_enabled: Whether the sync is enabled.
        status: Sync status (offline, initializing, syncing, error).
        status_info: Additional status information.
        state: Sync state (offline, online, warning, error).
        url: Remote URL.
        has_encryption: Whether encryption is enabled.
        has_compression: Whether compression is enabled.
        has_network_integrity: Whether network integrity checking is enabled.
        data_threads: Number of data threads.
        file_threads: Number of file threads.
        send_throttle: Send throttle in bytes/sec (0 = disabled).
        destination_tier: Override destination storage tier.
        queue_retry_count: Number of retry attempts for queued items.
        queue_retry_interval: Retry interval in seconds.
        has_retry_multiplier: Whether retry interval multiplier is enabled.
        last_run_at: When the sync last ran.
        remote_min_snapshots: Minimum snapshots to retain on remote.
        note: Optional note.
    """

    @property
    def site_key(self) -> int | None:
        """Get the associated site key."""
        val = self.get("site")
        return int(val) if val is not None else None

    @property
    def name(self) -> str:
        """Get sync name."""
        return str(self.get("name", ""))

    @property
    def description(self) -> str:
        """Get sync description."""
        return str(self.get("description", ""))

    @property
    def is_enabled(self) -> bool:
        """Check if sync is enabled."""
        return bool(self.get("enabled", False))

    @property
    def status(self) -> str:
        """Get sync status (offline, initializing, syncing, error)."""
        return str(self.get("status", "offline"))

    @property
    def status_info(self) -> str:
        """Get additional status information."""
        return str(self.get("status_info", ""))

    @property
    def state(self) -> str:
        """Get sync state (offline, online, warning, error)."""
        return str(self.get("state", "offline"))

    @property
    def is_syncing(self) -> bool:
        """Check if sync is currently syncing."""
        return self.status == "syncing"

    @property
    def is_online(self) -> bool:
        """Check if sync is online."""
        return self.state == "online"

    @property
    def has_error(self) -> bool:
        """Check if sync has an error."""
        return self.state == "error" or self.status == "error"

    @property
    def url(self) -> str:
        """Get remote URL."""
        return str(self.get("url", ""))

    @property
    def has_encryption(self) -> bool:
        """Check if encryption is enabled."""
        return bool(self.get("encryption", True))

    @property
    def has_compression(self) -> bool:
        """Check if compression is enabled."""
        return bool(self.get("compression", True))

    @property
    def has_network_integrity(self) -> bool:
        """Check if network integrity checking is enabled."""
        return bool(self.get("netinteg", True))

    @property
    def data_threads(self) -> int:
        """Get number of data threads."""
        return int(self.get("threads", 8))

    @property
    def file_threads(self) -> int:
        """Get number of file threads."""
        return int(self.get("file_threads", 4))

    @property
    def send_throttle(self) -> int:
        """Get send throttle in bytes/sec (0 = disabled)."""
        return int(self.get("sendthrottle", 0))

    @property
    def destination_tier(self) -> str:
        """Get override destination storage tier."""
        return str(self.get("destination_tier", "unspecified"))

    @property
    def queue_retry_count(self) -> int:
        """Get number of retry attempts for queued items."""
        return int(self.get("queue_retry_count", 10))

    @property
    def queue_retry_interval(self) -> int:
        """Get retry interval in seconds."""
        return int(self.get("queue_retry_interval_seconds", 60))

    @property
    def has_retry_multiplier(self) -> bool:
        """Check if retry interval multiplier is enabled."""
        return bool(self.get("queue_retry_interval_multiplier", True))

    @property
    def last_run_at(self) -> datetime | None:
        """Get when the sync last ran."""
        ts = self.get("last_run")
        if ts and int(ts) > 0:
            return datetime.fromtimestamp(int(ts), tz=timezone.utc)
        return None

    @property
    def remote_min_snapshots(self) -> int:
        """Get minimum snapshots to retain on remote."""
        return int(self.get("remote_min_snapshots", 0))

    @property
    def note(self) -> str:
        """Get optional note."""
        return str(self.get("note", ""))

    def enable(self) -> SiteSyncOutgoing:
        """Enable this sync.

        Returns:
            Updated SiteSyncOutgoing object.
        """
        from typing import cast

        manager = cast("SiteSyncOutgoingManager", self._manager)
        return manager.enable(self.key)

    def disable(self) -> SiteSyncOutgoing:
        """Disable this sync.

        Returns:
            Updated SiteSyncOutgoing object.
        """
        from typing import cast

        manager = cast("SiteSyncOutgoingManager", self._manager)
        return manager.disable(self.key)

    def start(self) -> SiteSyncOutgoing:
        """Start (enable) this sync.

        Alias for enable().

        Returns:
            Updated SiteSyncOutgoing object.
        """
        return self.enable()

    def stop(self) -> SiteSyncOutgoing:
        """Stop (disable) this sync.

        Alias for disable().

        Returns:
            Updated SiteSyncOutgoing object.
        """
        return self.disable()

    def refresh(self) -> SiteSyncOutgoing:
        """Refresh sync data from server.

        Returns:
            Updated SiteSyncOutgoing object.
        """
        from typing import cast

        manager = cast("SiteSyncOutgoingManager", self._manager)
        return manager.get(self.key)

    def add_to_queue(
        self,
        snapshot_key: int,
        retention: int | timedelta = 259200,
        priority: int = 0,
        do_not_expire: bool = False,
        destination_prefix: str | None = None,
    ) -> None:
        """Add a cloud snapshot to the transfer queue.

        Args:
            snapshot_key: Key of the cloud snapshot to queue.
            retention: Retention period in seconds or timedelta. Default 3 days.
            priority: Priority for syncing (lower = first). Default 0.
            do_not_expire: If True, snapshot won't expire until synced.
            destination_prefix: Prefix for snapshot name on destination.
        """
        from typing import cast

        manager = cast("SiteSyncOutgoingManager", self._manager)
        manager.add_to_queue(
            self.key,
            snapshot_key,
            retention=retention,
            priority=priority,
            do_not_expire=do_not_expire,
            destination_prefix=destination_prefix,
        )

    def __repr__(self) -> str:
        key = self.get("$key", "?")
        name = self.name
        status = self.status
        return f"<SiteSyncOutgoing key={key} name={name!r} status={status!r}>"


class SiteSyncIncoming(ResourceObject):
    """Incoming site sync resource object.

    Incoming syncs receive cloud snapshots from a remote site
    for disaster recovery purposes.

    Properties:
        site_key: Key of the associated site.
        name: Sync name.
        description: Sync description.
        is_enabled: Whether the sync is enabled.
        status: Sync status (offline, syncing, error, etc.).
        status_info: Additional status information.
        state: Sync state (offline, online, warning, error).
        sync_id: Unique sync identifier.
        registration_code: Code used by remote site to establish connection.
        public_ip: Public IP/domain of connecting system.
        force_tier: Force all synced data to this tier.
        min_snapshots: Minimum snapshots to retain.
        last_sync_at: When last sync occurred.
        vsan_host: vSAN connection host.
        vsan_port: vSAN connection port.
        request_url: URL remote system uses to connect back.
        is_system_created: Whether sync was created by system.
    """

    @property
    def site_key(self) -> int | None:
        """Get the associated site key."""
        val = self.get("site")
        return int(val) if val is not None else None

    @property
    def name(self) -> str:
        """Get sync name."""
        return str(self.get("name", ""))

    @property
    def description(self) -> str:
        """Get sync description."""
        return str(self.get("description", ""))

    @property
    def is_enabled(self) -> bool:
        """Check if sync is enabled."""
        return bool(self.get("enabled", False))

    @property
    def status(self) -> str:
        """Get sync status."""
        return str(self.get("status", "offline"))

    @property
    def status_info(self) -> str:
        """Get additional status information."""
        return str(self.get("status_info", ""))

    @property
    def state(self) -> str:
        """Get sync state (offline, online, warning, error)."""
        return str(self.get("state", "offline"))

    @property
    def is_syncing(self) -> bool:
        """Check if sync is currently syncing."""
        return self.status == "syncing"

    @property
    def is_online(self) -> bool:
        """Check if sync is online."""
        return self.state == "online"

    @property
    def has_error(self) -> bool:
        """Check if sync has an error."""
        return self.state == "error" or self.status == "error"

    @property
    def sync_id(self) -> str:
        """Get unique sync identifier."""
        return str(self.get("sync_id", ""))

    @property
    def registration_code(self) -> str:
        """Get registration code for remote site connection."""
        return str(self.get("registration_code", ""))

    @property
    def public_ip(self) -> str:
        """Get public IP/domain of connecting system."""
        return str(self.get("public_ip", ""))

    @property
    def force_tier(self) -> str:
        """Get forced storage tier (unspecified, 1-5)."""
        return str(self.get("force_tier", "unspecified"))

    @property
    def min_snapshots(self) -> int:
        """Get minimum snapshots to retain."""
        return int(self.get("min_snapshots", 1))

    @property
    def last_sync_at(self) -> datetime | None:
        """Get when last sync occurred."""
        ts = self.get("last_sync")
        if ts and int(ts) > 0:
            return datetime.fromtimestamp(int(ts), tz=timezone.utc)
        return None

    @property
    def vsan_host(self) -> str:
        """Get vSAN connection host."""
        return str(self.get("vsan_host", ""))

    @property
    def vsan_port(self) -> int:
        """Get vSAN connection port."""
        return int(self.get("vsan_port", 14201))

    @property
    def request_url(self) -> str:
        """Get URL remote system uses to connect back."""
        return str(self.get("request_url", ""))

    @property
    def is_system_created(self) -> bool:
        """Check if sync was created by system."""
        return bool(self.get("system_created", False))

    def enable(self) -> SiteSyncIncoming:
        """Enable this sync.

        Returns:
            Updated SiteSyncIncoming object.
        """
        from typing import cast

        manager = cast("SiteSyncIncomingManager", self._manager)
        return manager.enable(self.key)

    def disable(self) -> SiteSyncIncoming:
        """Disable this sync.

        Returns:
            Updated SiteSyncIncoming object.
        """
        from typing import cast

        manager = cast("SiteSyncIncomingManager", self._manager)
        return manager.disable(self.key)

    def refresh(self) -> SiteSyncIncoming:
        """Refresh sync data from server.

        Returns:
            Updated SiteSyncIncoming object.
        """
        from typing import cast

        manager = cast("SiteSyncIncomingManager", self._manager)
        return manager.get(self.key)

    def __repr__(self) -> str:
        key = self.get("$key", "?")
        name = self.name
        status = self.status
        return f"<SiteSyncIncoming key={key} name={name!r} status={status!r}>"


class SiteSyncSchedule(ResourceObject):
    """Site sync schedule resource object.

    Schedules link snapshot profile periods to outgoing site syncs,
    enabling automatic syncing of snapshots taken by those periods.

    Properties:
        sync_key: Key of the associated outgoing sync.
        profile_period_key: Key of the snapshot profile period.
        retention: Retention period in seconds.
        retention_timedelta: Retention period as timedelta.
        priority: Sync priority (lower = first).
        do_not_expire: Whether source snapshot should not expire until synced.
        destination_prefix: Prefix for snapshot name on destination.
    """

    @property
    def sync_key(self) -> int | None:
        """Get the associated outgoing sync key."""
        val = self.get("site_syncs_outgoing")
        return int(val) if val is not None else None

    @property
    def profile_period_key(self) -> int | None:
        """Get the associated snapshot profile period key."""
        val = self.get("profile_period")
        return int(val) if val is not None else None

    @property
    def retention(self) -> int:
        """Get retention period in seconds."""
        return int(self.get("retention", 0))

    @property
    def retention_timedelta(self) -> timedelta:
        """Get retention period as timedelta."""
        return timedelta(seconds=self.retention)

    @property
    def priority(self) -> int:
        """Get sync priority (lower = first)."""
        return int(self.get("priority", 0))

    @property
    def do_not_expire(self) -> bool:
        """Check if source snapshot should not expire until synced."""
        return bool(self.get("do_not_expire", False))

    @property
    def destination_prefix(self) -> str:
        """Get prefix for snapshot name on destination."""
        return str(self.get("destination_prefix", "remote"))

    def delete(self) -> None:
        """Delete this schedule."""
        from typing import cast

        manager = cast("SiteSyncScheduleManager", self._manager)
        manager.delete(self.key)

    def __repr__(self) -> str:
        key = self.get("$key", "?")
        sync_key = self.sync_key
        period_key = self.profile_period_key
        return f"<SiteSyncSchedule key={key} sync={sync_key} period={period_key}>"


class SiteSyncOutgoingManager(ResourceManager[SiteSyncOutgoing]):
    """Manager for outgoing site sync operations.

    Outgoing syncs send cloud snapshots to remote sites for disaster recovery.

    Example:
        >>> # List all outgoing syncs
        >>> syncs = client.site_syncs.list()

        >>> # Get syncs for a specific site
        >>> syncs = client.site_syncs.list(site_key=1)

        >>> # Get a sync by name
        >>> sync = client.site_syncs.get(name="DR-Sync")

        >>> # Enable/disable a sync
        >>> sync = client.site_syncs.enable(sync.key)
        >>> sync = client.site_syncs.disable(sync.key)

        >>> # Add snapshot to queue
        >>> client.site_syncs.add_to_queue(
        ...     sync_key=1,
        ...     snapshot_key=5,
        ...     retention=604800,  # 7 days
        ... )
    """

    _endpoint = "site_syncs_outgoing"

    def __init__(self, client: VergeClient) -> None:
        super().__init__(client)

    def _to_model(self, data: dict[str, Any]) -> SiteSyncOutgoing:
        return SiteSyncOutgoing(data, self)

    def list(
        self,
        filter: str | None = None,
        fields: builtins.list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        *,
        site_key: int | None = None,
        site_name: str | None = None,
        enabled: bool | None = None,
        **filter_kwargs: Any,
    ) -> builtins.list[SiteSyncOutgoing]:
        """List outgoing site syncs.

        Args:
            filter: OData filter string.
            fields: List of fields to return.
            limit: Maximum number of results.
            offset: Skip this many results.
            site_key: Filter by site key.
            site_name: Filter by site name (looks up site key).
            enabled: Filter by enabled status.
            **filter_kwargs: Additional filter arguments.

        Returns:
            List of SiteSyncOutgoing objects sorted by name.

        Example:
            >>> # All outgoing syncs
            >>> syncs = client.site_syncs.list()

            >>> # Syncs for a specific site
            >>> syncs = client.site_syncs.list(site_key=1)

            >>> # Enabled syncs only
            >>> syncs = client.site_syncs.list(enabled=True)
        """
        # Resolve site name to key if provided
        if site_name and not site_key:
            site = self._client.sites.get(name=site_name)
            site_key = site.key

        conditions: builtins.list[str] = []

        if site_key is not None:
            conditions.append(f"site eq {site_key}")

        if enabled is not None:
            conditions.append(f"enabled eq {str(enabled).lower()}")

        if filter:
            conditions.append(f"({filter})")

        if filter_kwargs:
            conditions.append(build_filter(**filter_kwargs))

        combined_filter = " and ".join(conditions) if conditions else None

        if fields is None:
            fields = _DEFAULT_OUTGOING_SYNC_FIELDS

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
            return [self._to_model(response)]

        return [self._to_model(item) for item in response]

    def list_enabled(
        self,
        fields: builtins.list[str] | None = None,
    ) -> builtins.list[SiteSyncOutgoing]:
        """List enabled outgoing syncs.

        Args:
            fields: List of fields to return.

        Returns:
            List of enabled SiteSyncOutgoing objects.
        """
        return self.list(enabled=True, fields=fields)

    def list_disabled(
        self,
        fields: builtins.list[str] | None = None,
    ) -> builtins.list[SiteSyncOutgoing]:
        """List disabled outgoing syncs.

        Args:
            fields: List of fields to return.

        Returns:
            List of disabled SiteSyncOutgoing objects.
        """
        return self.list(enabled=False, fields=fields)

    def list_for_site(
        self,
        site_key: int | None = None,
        site_name: str | None = None,
        fields: builtins.list[str] | None = None,
    ) -> builtins.list[SiteSyncOutgoing]:
        """List outgoing syncs for a specific site.

        Args:
            site_key: Site key.
            site_name: Site name.
            fields: List of fields to return.

        Returns:
            List of SiteSyncOutgoing objects for the site.
        """
        return self.list(site_key=site_key, site_name=site_name, fields=fields)

    def get(
        self,
        key: int | None = None,
        *,
        name: str | None = None,
        site_key: int | None = None,
        site_name: str | None = None,
        fields: builtins.list[str] | None = None,
    ) -> SiteSyncOutgoing:
        """Get an outgoing sync by key or name.

        Args:
            key: Sync $key (ID).
            name: Sync name (requires site_key or site_name for uniqueness).
            site_key: Site key (for name lookup).
            site_name: Site name (for name lookup).
            fields: List of fields to return.

        Returns:
            SiteSyncOutgoing object.

        Raises:
            NotFoundError: If sync not found.
            ValueError: If neither key nor name provided.
        """
        if fields is None:
            fields = _DEFAULT_OUTGOING_SYNC_FIELDS

        if key is not None:
            params: dict[str, Any] = {}
            if fields:
                params["fields"] = ",".join(fields)

            response = self._client._request("GET", f"{self._endpoint}/{key}", params=params)
            if response is None:
                raise NotFoundError(f"Outgoing sync {key} not found")
            if not isinstance(response, dict):
                raise NotFoundError(f"Outgoing sync {key} returned invalid response")

            return self._to_model(response)

        if name is not None:
            # Resolve site name to key if provided
            if site_name and not site_key:
                site = self._client.sites.get(name=site_name)
                site_key = site.key

            conditions = [f"name eq '{name.replace(chr(39), chr(39) + chr(39))}'"]
            if site_key is not None:
                conditions.append(f"site eq {site_key}")

            results = self.list(filter=" and ".join(conditions), fields=fields)
            if not results:
                raise NotFoundError(f"Outgoing sync '{name}' not found")
            return results[0]

        raise ValueError("Either key or name must be provided")

    def enable(self, key: int) -> SiteSyncOutgoing:
        """Enable an outgoing sync.

        Args:
            key: Sync $key (ID).

        Returns:
            Updated SiteSyncOutgoing object.
        """
        body: dict[str, Any] = {
            "site_syncs_outgoing": key,
            "action": "enable",
        }

        self._client._request("POST", "site_syncs_outgoing_actions", json_data=body)
        return self.get(key)

    def disable(self, key: int) -> SiteSyncOutgoing:
        """Disable an outgoing sync.

        Args:
            key: Sync $key (ID).

        Returns:
            Updated SiteSyncOutgoing object.
        """
        body: dict[str, Any] = {
            "site_syncs_outgoing": key,
            "action": "disable",
        }

        self._client._request("POST", "site_syncs_outgoing_actions", json_data=body)
        return self.get(key)

    def start(self, key: int) -> SiteSyncOutgoing:
        """Start (enable) an outgoing sync.

        Alias for enable().

        Args:
            key: Sync $key (ID).

        Returns:
            Updated SiteSyncOutgoing object.
        """
        return self.enable(key)

    def stop(self, key: int) -> SiteSyncOutgoing:
        """Stop (disable) an outgoing sync.

        Alias for disable().

        Args:
            key: Sync $key (ID).

        Returns:
            Updated SiteSyncOutgoing object.
        """
        return self.disable(key)

    def add_to_queue(
        self,
        sync_key: int,
        snapshot_key: int,
        retention: int | timedelta = 259200,
        priority: int = 0,
        do_not_expire: bool = False,
        destination_prefix: str | None = None,
    ) -> None:
        """Add a cloud snapshot to the transfer queue.

        Args:
            sync_key: Key of the outgoing sync.
            snapshot_key: Key of the cloud snapshot to queue.
            retention: Retention period in seconds or timedelta. Default 3 days.
            priority: Priority for syncing (lower = first). Default 0.
            do_not_expire: If True, snapshot won't expire until synced.
            destination_prefix: Prefix for snapshot name on destination.

        Raises:
            ValidationError: If invalid parameters.
        """
        # Convert retention to seconds if timedelta
        if isinstance(retention, timedelta):
            retention_seconds = int(retention.total_seconds())
        else:
            retention_seconds = int(retention)

        if retention_seconds < 0:
            raise ValidationError("Retention must be positive")

        params: dict[str, Any] = {
            "cloud_snapshot": snapshot_key,
            "retention": retention_seconds,
            "priority": priority,
            "do_not_expire": do_not_expire,
        }

        if destination_prefix is not None:
            params["destination_prefix"] = destination_prefix

        body: dict[str, Any] = {
            "site_syncs_outgoing": sync_key,
            "action": "add_to_queue",
            "params": params,
        }

        self._client._request("POST", "site_syncs_outgoing_actions", json_data=body)

    def invoke(
        self,
        sync_key: int,
        snapshot_key: int,
        retention: int | timedelta = 259200,
        priority: int = 0,
        do_not_expire: bool = False,
        destination_prefix: str | None = None,
    ) -> None:
        """Manually trigger a sync for a cloud snapshot.

        Alias for add_to_queue().

        Args:
            sync_key: Key of the outgoing sync.
            snapshot_key: Key of the cloud snapshot to queue.
            retention: Retention period in seconds or timedelta. Default 3 days.
            priority: Priority for syncing (lower = first). Default 0.
            do_not_expire: If True, snapshot won't expire until synced.
            destination_prefix: Prefix for snapshot name on destination.
        """
        self.add_to_queue(
            sync_key,
            snapshot_key,
            retention=retention,
            priority=priority,
            do_not_expire=do_not_expire,
            destination_prefix=destination_prefix,
        )

    def set_throttle(self, key: int, throttle: int) -> SiteSyncOutgoing:
        """Set send throttle for an outgoing sync.

        Args:
            key: Sync $key (ID).
            throttle: Throttle in bytes/sec (0 = disable).

        Returns:
            Updated SiteSyncOutgoing object.
        """
        body: dict[str, Any] = {
            "site_syncs_outgoing": key,
            "action": "throttle_sync",
            "params": {"throttle": throttle},
        }

        self._client._request("POST", "site_syncs_outgoing_actions", json_data=body)
        return self.get(key)

    def disable_throttle(self, key: int) -> SiteSyncOutgoing:
        """Disable send throttle for an outgoing sync.

        Args:
            key: Sync $key (ID).

        Returns:
            Updated SiteSyncOutgoing object.
        """
        return self.set_throttle(key, 0)

    def refresh_remote_snapshots(self, key: int) -> SiteSyncOutgoing:
        """Refresh the list of snapshots on the destination.

        Args:
            key: Sync $key (ID).

        Returns:
            Updated SiteSyncOutgoing object.
        """
        body: dict[str, Any] = {
            "site_syncs_outgoing": key,
            "action": "refresh",
        }

        self._client._request("POST", "site_syncs_outgoing_actions", json_data=body)
        return self.get(key)


class SiteSyncIncomingManager(ResourceManager[SiteSyncIncoming]):
    """Manager for incoming site sync operations.

    Incoming syncs receive cloud snapshots from remote sites for disaster recovery.

    Example:
        >>> # List all incoming syncs
        >>> syncs = client.site_syncs_incoming.list()

        >>> # Get syncs for a specific site
        >>> syncs = client.site_syncs_incoming.list(site_key=1)

        >>> # Get a sync by name
        >>> sync = client.site_syncs_incoming.get(name="DR-Sync")

        >>> # Enable/disable a sync
        >>> sync = client.site_syncs_incoming.enable(sync.key)
        >>> sync = client.site_syncs_incoming.disable(sync.key)
    """

    _endpoint = "site_syncs_incoming"

    def __init__(self, client: VergeClient) -> None:
        super().__init__(client)

    def _to_model(self, data: dict[str, Any]) -> SiteSyncIncoming:
        return SiteSyncIncoming(data, self)

    def list(
        self,
        filter: str | None = None,
        fields: builtins.list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        *,
        site_key: int | None = None,
        site_name: str | None = None,
        enabled: bool | None = None,
        **filter_kwargs: Any,
    ) -> builtins.list[SiteSyncIncoming]:
        """List incoming site syncs.

        Args:
            filter: OData filter string.
            fields: List of fields to return.
            limit: Maximum number of results.
            offset: Skip this many results.
            site_key: Filter by site key.
            site_name: Filter by site name (looks up site key).
            enabled: Filter by enabled status.
            **filter_kwargs: Additional filter arguments.

        Returns:
            List of SiteSyncIncoming objects sorted by name.

        Example:
            >>> # All incoming syncs
            >>> syncs = client.site_syncs_incoming.list()

            >>> # Syncs for a specific site
            >>> syncs = client.site_syncs_incoming.list(site_key=1)

            >>> # Enabled syncs only
            >>> syncs = client.site_syncs_incoming.list(enabled=True)
        """
        # Resolve site name to key if provided
        if site_name and not site_key:
            site = self._client.sites.get(name=site_name)
            site_key = site.key

        conditions: builtins.list[str] = []

        if site_key is not None:
            conditions.append(f"site eq {site_key}")

        if enabled is not None:
            conditions.append(f"enabled eq {str(enabled).lower()}")

        if filter:
            conditions.append(f"({filter})")

        if filter_kwargs:
            conditions.append(build_filter(**filter_kwargs))

        combined_filter = " and ".join(conditions) if conditions else None

        if fields is None:
            fields = _DEFAULT_INCOMING_SYNC_FIELDS

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
            return [self._to_model(response)]

        return [self._to_model(item) for item in response]

    def list_for_site(
        self,
        site_key: int | None = None,
        site_name: str | None = None,
        fields: builtins.list[str] | None = None,
    ) -> builtins.list[SiteSyncIncoming]:
        """List incoming syncs for a specific site.

        Args:
            site_key: Site key.
            site_name: Site name.
            fields: List of fields to return.

        Returns:
            List of SiteSyncIncoming objects for the site.
        """
        return self.list(site_key=site_key, site_name=site_name, fields=fields)

    def get(
        self,
        key: int | None = None,
        *,
        name: str | None = None,
        site_key: int | None = None,
        site_name: str | None = None,
        fields: builtins.list[str] | None = None,
    ) -> SiteSyncIncoming:
        """Get an incoming sync by key or name.

        Args:
            key: Sync $key (ID).
            name: Sync name (requires site_key or site_name for uniqueness).
            site_key: Site key (for name lookup).
            site_name: Site name (for name lookup).
            fields: List of fields to return.

        Returns:
            SiteSyncIncoming object.

        Raises:
            NotFoundError: If sync not found.
            ValueError: If neither key nor name provided.
        """
        if fields is None:
            fields = _DEFAULT_INCOMING_SYNC_FIELDS

        if key is not None:
            params: dict[str, Any] = {}
            if fields:
                params["fields"] = ",".join(fields)

            response = self._client._request("GET", f"{self._endpoint}/{key}", params=params)
            if response is None:
                raise NotFoundError(f"Incoming sync {key} not found")
            if not isinstance(response, dict):
                raise NotFoundError(f"Incoming sync {key} returned invalid response")

            return self._to_model(response)

        if name is not None:
            # Resolve site name to key if provided
            if site_name and not site_key:
                site = self._client.sites.get(name=site_name)
                site_key = site.key

            conditions = [f"name eq '{name.replace(chr(39), chr(39) + chr(39))}'"]
            if site_key is not None:
                conditions.append(f"site eq {site_key}")

            results = self.list(filter=" and ".join(conditions), fields=fields)
            if not results:
                raise NotFoundError(f"Incoming sync '{name}' not found")
            return results[0]

        raise ValueError("Either key or name must be provided")

    def enable(self, key: int) -> SiteSyncIncoming:
        """Enable an incoming sync.

        Args:
            key: Sync $key (ID).

        Returns:
            Updated SiteSyncIncoming object.
        """
        body: dict[str, Any] = {
            "site_syncs_incoming": key,
            "action": "enable",
        }

        self._client._request("POST", "site_syncs_incoming_actions", json_data=body)
        return self.get(key)

    def disable(self, key: int) -> SiteSyncIncoming:
        """Disable an incoming sync.

        Args:
            key: Sync $key (ID).

        Returns:
            Updated SiteSyncIncoming object.
        """
        body: dict[str, Any] = {
            "site_syncs_incoming": key,
            "action": "disable",
        }

        self._client._request("POST", "site_syncs_incoming_actions", json_data=body)
        return self.get(key)


class SiteSyncScheduleManager(ResourceManager[SiteSyncSchedule]):
    """Manager for site sync schedule operations.

    Schedules link snapshot profile periods to outgoing syncs, enabling
    automatic syncing of snapshots taken by those periods.

    Example:
        >>> # List all schedules
        >>> schedules = client.site_sync_schedules.list()

        >>> # Get schedules for a specific sync
        >>> schedules = client.site_sync_schedules.list(sync_key=1)

        >>> # Create a new schedule
        >>> schedule = client.site_sync_schedules.create(
        ...     sync_key=1,
        ...     profile_period_key=2,
        ...     retention=604800,  # 7 days
        ... )

        >>> # Delete a schedule
        >>> client.site_sync_schedules.delete(schedule.key)
    """

    _endpoint = "site_syncs_outgoing_profile_periods"

    def __init__(self, client: VergeClient) -> None:
        super().__init__(client)

    def _to_model(self, data: dict[str, Any]) -> SiteSyncSchedule:
        return SiteSyncSchedule(data, self)

    def list(
        self,
        filter: str | None = None,
        fields: builtins.list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        *,
        sync_key: int | None = None,
        sync_name: str | None = None,
        **filter_kwargs: Any,
    ) -> builtins.list[SiteSyncSchedule]:
        """List site sync schedules.

        Args:
            filter: OData filter string.
            fields: List of fields to return.
            limit: Maximum number of results.
            offset: Skip this many results.
            sync_key: Filter by outgoing sync key.
            sync_name: Filter by outgoing sync name.
            **filter_kwargs: Additional filter arguments.

        Returns:
            List of SiteSyncSchedule objects sorted by priority.

        Example:
            >>> # All schedules
            >>> schedules = client.site_sync_schedules.list()

            >>> # Schedules for a specific sync
            >>> schedules = client.site_sync_schedules.list(sync_key=1)
        """
        # Resolve sync name to key if provided
        if sync_name and not sync_key:
            sync = self._client.site_syncs.get(name=sync_name)
            sync_key = sync.key

        conditions: builtins.list[str] = []

        if sync_key is not None:
            conditions.append(f"site_syncs_outgoing eq {sync_key}")

        if filter:
            conditions.append(f"({filter})")

        if filter_kwargs:
            conditions.append(build_filter(**filter_kwargs))

        combined_filter = " and ".join(conditions) if conditions else None

        if fields is None:
            fields = _DEFAULT_SCHEDULE_FIELDS

        params: dict[str, Any] = {}
        if combined_filter:
            params["filter"] = combined_filter
        if fields:
            params["fields"] = ",".join(fields)
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset
        params["sort"] = "+priority"

        response = self._client._request("GET", self._endpoint, params=params)

        if response is None:
            return []

        if not isinstance(response, list):
            return [self._to_model(response)]

        return [self._to_model(item) for item in response]

    def list_for_sync(
        self,
        sync_key: int | None = None,
        sync_name: str | None = None,
        fields: builtins.list[str] | None = None,
    ) -> builtins.list[SiteSyncSchedule]:
        """List schedules for a specific outgoing sync.

        Args:
            sync_key: Outgoing sync key.
            sync_name: Outgoing sync name.
            fields: List of fields to return.

        Returns:
            List of SiteSyncSchedule objects for the sync.
        """
        return self.list(sync_key=sync_key, sync_name=sync_name, fields=fields)

    def get(  # type: ignore[override]
        self,
        key: int,
        *,
        fields: builtins.list[str] | None = None,
    ) -> SiteSyncSchedule:
        """Get a schedule by key.

        Args:
            key: Schedule $key (ID).
            fields: List of fields to return.

        Returns:
            SiteSyncSchedule object.

        Raises:
            NotFoundError: If schedule not found.
        """
        if fields is None:
            fields = _DEFAULT_SCHEDULE_FIELDS

        params: dict[str, Any] = {}
        if fields:
            params["fields"] = ",".join(fields)

        response = self._client._request("GET", f"{self._endpoint}/{key}", params=params)
        if response is None:
            raise NotFoundError(f"Site sync schedule {key} not found")
        if not isinstance(response, dict):
            raise NotFoundError(f"Site sync schedule {key} returned invalid response")

        return self._to_model(response)

    def create(  # type: ignore[override]
        self,
        sync_key: int,
        profile_period_key: int,
        retention: int | timedelta,
        *,
        priority: int | None = None,
        do_not_expire: bool = False,
        destination_prefix: str = "remote",
    ) -> SiteSyncSchedule:
        """Create a new site sync schedule.

        Links a snapshot profile period to an outgoing sync so that snapshots
        taken by that period are automatically queued for sync.

        Args:
            sync_key: Key of the outgoing sync.
            profile_period_key: Key of the snapshot profile period.
            retention: Retention period in seconds or timedelta.
            priority: Sync priority (lower = first). Auto-assigned if not specified.
            do_not_expire: If True, source snapshot won't expire until synced.
            destination_prefix: Prefix for snapshot name on destination.

        Returns:
            Created SiteSyncSchedule object.

        Raises:
            ValidationError: If invalid parameters.

        Example:
            >>> schedule = client.site_sync_schedules.create(
            ...     sync_key=1,
            ...     profile_period_key=2,
            ...     retention=timedelta(days=7),
            ...     destination_prefix="remote",
            ... )
        """
        # Convert retention to seconds if timedelta
        if isinstance(retention, timedelta):
            retention_seconds = int(retention.total_seconds())
        else:
            retention_seconds = int(retention)

        if retention_seconds < 0:
            raise ValidationError("Retention must be positive")

        body: dict[str, Any] = {
            "site_syncs_outgoing": sync_key,
            "profile_period": profile_period_key,
            "retention": retention_seconds,
            "do_not_expire": do_not_expire,
            "destination_prefix": destination_prefix,
        }

        if priority is not None:
            body["priority"] = priority

        response = self._client._request("POST", self._endpoint, json_data=body)
        if response is None:
            raise ValueError("No response from create operation")
        if not isinstance(response, dict):
            raise ValueError("Create operation returned invalid response")

        schedule_key = response.get("$key")
        if schedule_key:
            return self.get(int(schedule_key))

        return self._to_model(response)

    def delete(self, key: int) -> None:
        """Delete a site sync schedule.

        Args:
            key: Schedule $key (ID).

        Raises:
            NotFoundError: If schedule not found.
        """
        self._client._request("DELETE", f"{self._endpoint}/{key}")
