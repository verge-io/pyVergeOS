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

    @property
    def queue(self) -> SiteSyncQueueManager:
        """Access the sync queue for this outgoing sync.

        Returns:
            SiteSyncQueueManager scoped to this sync.

        Example:
            >>> sync = client.site_syncs.get(1)
            >>> items = sync.queue.list()
            >>> syncing = sync.queue.list_syncing()
        """
        from typing import cast

        manager = cast("SiteSyncOutgoingManager", self._manager)
        return SiteSyncQueueManager(manager._client, self.key)

    @property
    def remote_snapshots(self) -> SiteSyncRemoteSnapManager:
        """Access remote snapshots for this outgoing sync.

        Returns:
            SiteSyncRemoteSnapManager scoped to this sync.

        Example:
            >>> sync = client.site_syncs.get(1)
            >>> snaps = sync.remote_snapshots.list()
            >>> snap = snaps[0]
            >>> snap.request_sync_back()
        """
        from typing import cast

        manager = cast("SiteSyncOutgoingManager", self._manager)
        return SiteSyncRemoteSnapManager(manager._client, self.key)

    @property
    def stats(self) -> SiteSyncStatsManager:
        """Access stats for this outgoing sync.

        Returns:
            SiteSyncStatsManager scoped to this sync.

        Example:
            >>> sync = client.site_syncs.get(1)
            >>> stats = sync.stats.get()
            >>> print(f"Sent: {stats.sent_display}")
        """
        from typing import cast

        manager = cast("SiteSyncOutgoingManager", self._manager)
        return SiteSyncStatsManager(manager._client, self.key)

    @property
    def logs(self) -> SiteSyncOutgoingLogManager:
        """Access logs for this outgoing sync.

        Returns:
            SiteSyncOutgoingLogManager scoped to this sync.

        Example:
            >>> sync = client.site_syncs.get(1)
            >>> logs = sync.logs.list(limit=20)
            >>> errors = sync.logs.list_errors()
        """
        from typing import cast

        manager = cast("SiteSyncOutgoingManager", self._manager)
        return SiteSyncOutgoingLogManager(manager._client, self.key)

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

    @property
    def verified(self) -> SiteSyncIncomingVerifiedManager:
        """Access verified sync info for this incoming sync.

        Returns:
            SiteSyncIncomingVerifiedManager scoped to this sync.

        Example:
            >>> incoming = client.site_syncs_incoming.get(1)
            >>> verified = incoming.verified.get()
            >>> snaps = verified.list_remote_snapshots()
        """
        from typing import cast

        manager = cast("SiteSyncIncomingManager", self._manager)
        return SiteSyncIncomingVerifiedManager(manager._client, self.key)

    @property
    def logs(self) -> SiteSyncIncomingLogManager:
        """Access logs for this incoming sync.

        Returns:
            SiteSyncIncomingLogManager scoped to this sync.

        Example:
            >>> incoming = client.site_syncs_incoming.get(1)
            >>> logs = incoming.logs.list(limit=20)
            >>> errors = incoming.logs.list_errors()
        """
        from typing import cast

        manager = cast("SiteSyncIncomingManager", self._manager)
        return SiteSyncIncomingLogManager(manager._client, self.key)

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


# ============================================================================
# Site Sync Stats
# ============================================================================

# Default fields for stats
_DEFAULT_STATS_FIELDS = [
    "$key",
    "parent",
    "checked_bytes",
    "scanned_bytes",
    "sent_bytes",
    "sent_net_bytes",
    "checked",
    "scanned",
    "sent",
    "sent_net",
    "dirs_checked",
    "files_checked",
    "files_updated",
    "last_run_time",
    "start_time",
    "stop_time",
    "error_time",
    "last_error",
    "sendthrottle",
    "retry_count",
    "snapshot_name",
    "last_retry_attempt",
    "timestamp",
]

# Default fields for stats history
_DEFAULT_STATS_HISTORY_FIELDS = [
    "$key",
    "parent",
    "checked_bytes",
    "scanned_bytes",
    "sent_bytes",
    "sent_net_bytes",
    "dirs_checked",
    "files_checked",
    "files_updated",
    "last_run_time",
    "snapshot_name",
    "timestamp",
]


class SiteSyncStats(ResourceObject):
    """Site sync statistics resource object.

    Provides performance metrics for a site sync operation.

    Properties:
        parent_key: Key of the parent sync.
        checked_bytes: Total bytes checked (file-level, pre-deduplication).
        scanned_bytes: Total bytes scanned (block comparison).
        sent_bytes: Bytes determined to need sending (pre-compression).
        sent_net_bytes: Actual bytes sent on wire (post-compression).
        dirs_checked: Number of directories checked.
        files_checked: Number of files checked.
        files_updated: Number of files updated.
        last_run_time_ms: Last run time in milliseconds.
        started_at: When sync started.
        stopped_at: When sync stopped.
        error_at: When error occurred.
        last_error: Last error message.
        send_throttle: Current throttle rate in bytes/sec.
        retry_count: Number of retry attempts.
        snapshot_name: Name of snapshot being synced.
        last_retry_at: When last retry occurred.
    """

    @property
    def parent_key(self) -> int | None:
        """Get the parent sync/queue item key."""
        val = self.get("parent")
        return int(val) if val is not None else None

    @property
    def checked_bytes(self) -> int:
        """Get total bytes checked (file-level)."""
        return int(self.get("checked_bytes", 0))

    @property
    def scanned_bytes(self) -> int:
        """Get total bytes scanned (block comparison)."""
        return int(self.get("scanned_bytes", 0))

    @property
    def sent_bytes(self) -> int:
        """Get bytes to send (pre-compression)."""
        return int(self.get("sent_bytes", 0))

    @property
    def sent_net_bytes(self) -> int:
        """Get bytes actually sent (post-compression)."""
        return int(self.get("sent_net_bytes", 0))

    @property
    def checked_display(self) -> str:
        """Get human-readable checked size."""
        return str(self.get("checked", ""))

    @property
    def scanned_display(self) -> str:
        """Get human-readable scanned size."""
        return str(self.get("scanned", ""))

    @property
    def sent_display(self) -> str:
        """Get human-readable sent size."""
        return str(self.get("sent", ""))

    @property
    def sent_net_display(self) -> str:
        """Get human-readable net sent size."""
        return str(self.get("sent_net", ""))

    @property
    def dirs_checked(self) -> int:
        """Get number of directories checked."""
        return int(self.get("dirs_checked", 0))

    @property
    def files_checked(self) -> int:
        """Get number of files checked."""
        return int(self.get("files_checked", 0))

    @property
    def files_updated(self) -> int:
        """Get number of files updated."""
        return int(self.get("files_updated", 0))

    @property
    def last_run_time_ms(self) -> int:
        """Get last run time in milliseconds."""
        return int(self.get("last_run_time", 0))

    @property
    def last_run_time_seconds(self) -> float:
        """Get last run time in seconds."""
        return self.last_run_time_ms / 1000.0

    @property
    def started_at(self) -> datetime | None:
        """Get when sync started."""
        ts = self.get("start_time")
        if ts and int(ts) > 0:
            return datetime.fromtimestamp(int(ts), tz=timezone.utc)
        return None

    @property
    def stopped_at(self) -> datetime | None:
        """Get when sync stopped."""
        ts = self.get("stop_time")
        if ts and int(ts) > 0:
            return datetime.fromtimestamp(int(ts), tz=timezone.utc)
        return None

    @property
    def error_at(self) -> datetime | None:
        """Get when error occurred."""
        ts = self.get("error_time")
        if ts and int(ts) > 0:
            return datetime.fromtimestamp(int(ts), tz=timezone.utc)
        return None

    @property
    def last_error(self) -> str:
        """Get last error message."""
        return str(self.get("last_error", ""))

    @property
    def has_error(self) -> bool:
        """Check if there was an error."""
        return bool(self.last_error)

    @property
    def send_throttle(self) -> int:
        """Get current throttle rate in bytes/sec."""
        return int(self.get("sendthrottle", 0))

    @property
    def retry_count(self) -> int:
        """Get number of retry attempts."""
        return int(self.get("retry_count", 0))

    @property
    def snapshot_name(self) -> str:
        """Get name of snapshot being synced."""
        return str(self.get("snapshot_name", ""))

    @property
    def last_retry_at(self) -> datetime | None:
        """Get when last retry occurred."""
        ts = self.get("last_retry_attempt")
        if ts and int(ts) > 0:
            return datetime.fromtimestamp(int(ts), tz=timezone.utc)
        return None

    @property
    def compression_ratio(self) -> float:
        """Calculate compression ratio (sent / sent_net).

        Returns ratio > 1 means compression is effective.
        Returns 0 if no data sent.
        """
        if self.sent_net_bytes == 0:
            return 0.0
        return self.sent_bytes / self.sent_net_bytes

    @property
    def dedup_ratio(self) -> float:
        """Calculate deduplication ratio (checked / sent).

        Returns ratio > 1 means deduplication is effective.
        Returns 0 if no data sent.
        """
        if self.sent_bytes == 0:
            return 0.0
        return self.checked_bytes / self.sent_bytes

    def __repr__(self) -> str:
        return (
            f"<SiteSyncStats checked={self.checked_display!r} "
            f"sent={self.sent_display!r} sent_net={self.sent_net_display!r}>"
        )


class SiteSyncStatsHistory(ResourceObject):
    """Site sync stats history entry.

    Long-term historical metrics for sync operations.
    """

    @property
    def parent_key(self) -> int | None:
        """Get the parent sync key."""
        val = self.get("parent")
        return int(val) if val is not None else None

    @property
    def checked_bytes(self) -> int:
        """Get total bytes checked."""
        return int(self.get("checked_bytes", 0))

    @property
    def scanned_bytes(self) -> int:
        """Get total bytes scanned."""
        return int(self.get("scanned_bytes", 0))

    @property
    def sent_bytes(self) -> int:
        """Get bytes to send."""
        return int(self.get("sent_bytes", 0))

    @property
    def sent_net_bytes(self) -> int:
        """Get bytes actually sent."""
        return int(self.get("sent_net_bytes", 0))

    @property
    def dirs_checked(self) -> int:
        """Get directories checked."""
        return int(self.get("dirs_checked", 0))

    @property
    def files_checked(self) -> int:
        """Get files checked."""
        return int(self.get("files_checked", 0))

    @property
    def files_updated(self) -> int:
        """Get files updated."""
        return int(self.get("files_updated", 0))

    @property
    def last_run_time_ms(self) -> int:
        """Get run time in milliseconds."""
        return int(self.get("last_run_time", 0))

    @property
    def snapshot_name(self) -> str:
        """Get snapshot name."""
        return str(self.get("snapshot_name", ""))

    @property
    def timestamp(self) -> datetime | None:
        """Get when record was created."""
        ts = self.get("timestamp")
        if ts and int(ts) > 0:
            return datetime.fromtimestamp(int(ts), tz=timezone.utc)
        return None

    def __repr__(self) -> str:
        return f"<SiteSyncStatsHistory snapshot={self.snapshot_name!r} sent={self.sent_bytes}>"


class SiteSyncStatsManager:
    """Manager for site sync stats (scoped to a sync).

    Example:
        >>> sync = client.site_syncs.get(1)
        >>> stats = sync.stats.get()
        >>> print(f"Checked: {stats.checked_display}")

        >>> # Get historical stats
        >>> history = sync.stats.history()
        >>> for entry in history:
        ...     print(f"{entry.snapshot_name}: {entry.sent_bytes} bytes")
    """

    def __init__(self, client: VergeClient, sync_key: int) -> None:
        self._client = client
        self._sync_key = sync_key
        self._endpoint = "site_sync_stats"
        self._history_endpoint = "site_sync_stats_history_long"

    def get(
        self,
        fields: builtins.list[str] | None = None,
    ) -> SiteSyncStats | None:
        """Get current stats for this sync.

        Args:
            fields: List of fields to return.

        Returns:
            SiteSyncStats object or None if no stats available.
        """
        if fields is None:
            fields = _DEFAULT_STATS_FIELDS

        params: dict[str, Any] = {
            "filter": f"parent eq {self._sync_key}",
            "sort": "-timestamp",
            "limit": 1,
        }
        if fields:
            params["fields"] = ",".join(fields)

        response = self._client._request("GET", self._endpoint, params=params)
        if response is None:
            return None

        if isinstance(response, list):
            if not response:
                return None
            return SiteSyncStats(response[0], None)  # type: ignore[arg-type]

        return SiteSyncStats(response, None)  # type: ignore[arg-type]

    def list(  # noqa: A003
        self,
        limit: int | None = 20,
        offset: int | None = None,
        fields: builtins.list[str] | None = None,
    ) -> builtins.list[SiteSyncStats]:
        """List recent stats entries.

        Args:
            limit: Maximum entries to return.
            offset: Skip this many entries.
            fields: List of fields to return.

        Returns:
            List of SiteSyncStats objects, newest first.
        """
        if fields is None:
            fields = _DEFAULT_STATS_FIELDS

        params: dict[str, Any] = {
            "filter": f"parent eq {self._sync_key}",
            "sort": "-timestamp",
        }
        if fields:
            params["fields"] = ",".join(fields)
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset

        response = self._client._request("GET", self._endpoint, params=params)
        if response is None:
            return []

        if not isinstance(response, list):
            return [SiteSyncStats(response, None)]  # type: ignore[arg-type]

        return [SiteSyncStats(item, None) for item in response]  # type: ignore[arg-type]

    def history(
        self,
        limit: int | None = 100,
        offset: int | None = None,
        fields: builtins.list[str] | None = None,
    ) -> builtins.list[SiteSyncStatsHistory]:
        """Get historical stats (long-term).

        Args:
            limit: Maximum entries to return.
            offset: Skip this many entries.
            fields: List of fields to return.

        Returns:
            List of SiteSyncStatsHistory objects, newest first.
        """
        if fields is None:
            fields = _DEFAULT_STATS_HISTORY_FIELDS

        params: dict[str, Any] = {
            "filter": f"parent eq {self._sync_key}",
            "sort": "-timestamp",
        }
        if fields:
            params["fields"] = ",".join(fields)
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset

        response = self._client._request("GET", self._history_endpoint, params=params)
        if response is None:
            return []

        if not isinstance(response, list):
            return [SiteSyncStatsHistory(response, None)]  # type: ignore[arg-type]

        return [SiteSyncStatsHistory(item, None) for item in response]  # type: ignore[arg-type]


# ============================================================================
# Site Sync Queue
# ============================================================================

# Default fields for queue items
_DEFAULT_QUEUE_FIELDS = [
    "$key",
    "site_syncs_outgoing",
    "id",
    "cloud_snapshot",
    "priority",
    "status",
    "retention",
    "remote_expiration",
    "stats",
    "destination_prefix",
    "timestamp",
    "do_not_expire",
]


class SiteSyncQueueItem(ResourceObject):
    """Site sync queue item resource object.

    Represents a cloud snapshot queued for sync to a remote site.

    Properties:
        sync_key: Key of the parent outgoing sync.
        cloud_snapshot_key: Key of the cloud snapshot.
        priority: Sync priority (lower = first).
        status: Queue status (queue, paused, syncing, complete, error, retry).
        retention: Retention period in seconds.
        remote_expiration_at: When snapshot will expire on remote.
        destination_prefix: Prefix for snapshot name on remote.
        created_at: When item was queued.
        do_not_expire: Whether snapshot should not expire until synced.
    """

    @property
    def sync_key(self) -> int | None:
        """Get the parent outgoing sync key."""
        val = self.get("site_syncs_outgoing")
        return int(val) if val is not None else None

    @property
    def queue_id(self) -> str:
        """Get the queue item ID."""
        return str(self.get("id", ""))

    @property
    def cloud_snapshot_key(self) -> int | None:
        """Get the cloud snapshot key."""
        val = self.get("cloud_snapshot")
        return int(val) if val is not None else None

    @property
    def priority(self) -> int:
        """Get sync priority (lower = first)."""
        return int(self.get("priority", 0))

    @property
    def status(self) -> str:
        """Get queue status.

        Values: queue, paused, syncing, complete, error, retry, initializing,
        skip_retention.
        """
        return str(self.get("status", "queue"))

    @property
    def is_queued(self) -> bool:
        """Check if item is queued (waiting to sync)."""
        return self.status == "queue"

    @property
    def is_syncing(self) -> bool:
        """Check if item is currently syncing."""
        return self.status == "syncing"

    @property
    def is_complete(self) -> bool:
        """Check if sync completed successfully."""
        return self.status == "complete"

    @property
    def has_error(self) -> bool:
        """Check if item has an error."""
        return self.status in ("error", "retry")

    @property
    def is_paused(self) -> bool:
        """Check if item is paused."""
        return self.status == "paused"

    @property
    def retention(self) -> int:
        """Get retention period in seconds."""
        return int(self.get("retention", 259200))

    @property
    def retention_timedelta(self) -> timedelta:
        """Get retention period as timedelta."""
        return timedelta(seconds=self.retention)

    @property
    def remote_expiration_at(self) -> datetime | None:
        """Get when snapshot expires on remote."""
        ts = self.get("remote_expiration")
        if ts and int(ts) > 0:
            return datetime.fromtimestamp(int(ts), tz=timezone.utc)
        return None

    @property
    def destination_prefix(self) -> str:
        """Get prefix for snapshot name on remote."""
        return str(self.get("destination_prefix", ""))

    @property
    def created_at(self) -> datetime | None:
        """Get when item was queued."""
        ts = self.get("timestamp")
        if ts and int(ts) > 0:
            # timestamp is in microseconds
            return datetime.fromtimestamp(int(ts) / 1_000_000, tz=timezone.utc)
        return None

    @property
    def do_not_expire(self) -> bool:
        """Check if snapshot should not expire until synced."""
        return bool(self.get("do_not_expire", False))

    def get_stats(self) -> SiteSyncStats | None:
        """Get stats for this queue item.

        Returns:
            SiteSyncStats object or None if no stats available.
        """
        stats_data = self.get("stats")
        if stats_data and isinstance(stats_data, dict):
            return SiteSyncStats(stats_data, None)  # type: ignore[arg-type]
        return None

    def delete(self) -> None:
        """Remove this item from the queue."""
        from typing import cast

        manager = cast("SiteSyncQueueManager", self._manager)
        manager.delete(self.key)

    def __repr__(self) -> str:
        key = self.get("$key", "?")
        status = self.status
        priority = self.priority
        return f"<SiteSyncQueueItem key={key} status={status!r} priority={priority}>"


class SiteSyncQueueManager:
    """Manager for site sync queue (scoped to an outgoing sync).

    Example:
        >>> sync = client.site_syncs.get(1)
        >>> # List queued items
        >>> items = sync.queue.list()
        >>> for item in items:
        ...     print(f"{item.key}: {item.status} (priority {item.priority})")

        >>> # Get items currently syncing
        >>> syncing = sync.queue.list_syncing()

        >>> # Get items with errors
        >>> errors = sync.queue.list_errors()
    """

    def __init__(self, client: VergeClient, sync_key: int) -> None:
        self._client = client
        self._sync_key = sync_key
        self._endpoint = "site_syncs_outgoing_queue"

    def _to_model(self, data: dict[str, Any]) -> SiteSyncQueueItem:
        return SiteSyncQueueItem(data, self)  # type: ignore[arg-type]

    def list(  # noqa: A003
        self,
        filter: str | None = None,  # noqa: A002
        fields: builtins.list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        *,
        status: str | None = None,
        **filter_kwargs: Any,
    ) -> builtins.list[SiteSyncQueueItem]:
        """List queue items for this sync.

        Args:
            filter: OData filter string.
            fields: List of fields to return.
            limit: Maximum results to return.
            offset: Skip this many results.
            status: Filter by status (queue, syncing, complete, error, etc.).
            **filter_kwargs: Additional filter arguments.

        Returns:
            List of SiteSyncQueueItem objects sorted by priority.
        """
        conditions: builtins.list[str] = [f"site_syncs_outgoing eq {self._sync_key}"]

        if status is not None:
            conditions.append(f"status eq '{status}'")

        if filter:
            conditions.append(f"({filter})")

        if filter_kwargs:
            conditions.append(build_filter(**filter_kwargs))

        combined_filter = " and ".join(conditions)

        if fields is None:
            fields = _DEFAULT_QUEUE_FIELDS

        params: dict[str, Any] = {
            "filter": combined_filter,
            "sort": "+priority",
        }
        if fields:
            params["fields"] = ",".join(fields)
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

    def list_queued(
        self,
        fields: builtins.list[str] | None = None,
    ) -> builtins.list[SiteSyncQueueItem]:
        """List items waiting to sync.

        Args:
            fields: List of fields to return.

        Returns:
            List of queued SiteSyncQueueItem objects.
        """
        return self.list(status="queue", fields=fields)

    def list_syncing(
        self,
        fields: builtins.list[str] | None = None,
    ) -> builtins.list[SiteSyncQueueItem]:
        """List items currently syncing.

        Args:
            fields: List of fields to return.

        Returns:
            List of syncing SiteSyncQueueItem objects.
        """
        return self.list(status="syncing", fields=fields)

    def list_complete(
        self,
        limit: int | None = 20,
        fields: builtins.list[str] | None = None,
    ) -> builtins.list[SiteSyncQueueItem]:
        """List completed items.

        Args:
            limit: Maximum results (default 20).
            fields: List of fields to return.

        Returns:
            List of completed SiteSyncQueueItem objects.
        """
        return self.list(status="complete", limit=limit, fields=fields)

    def list_errors(
        self,
        fields: builtins.list[str] | None = None,
    ) -> builtins.list[SiteSyncQueueItem]:
        """List items with errors.

        Args:
            fields: List of fields to return.

        Returns:
            List of error/retry SiteSyncQueueItem objects.
        """
        return self.list(filter="status eq 'error' or status eq 'retry'", fields=fields)

    def get(
        self,
        key: int,
        fields: builtins.list[str] | None = None,
    ) -> SiteSyncQueueItem:
        """Get a queue item by key.

        Args:
            key: Queue item $key (ID).
            fields: List of fields to return.

        Returns:
            SiteSyncQueueItem object.

        Raises:
            NotFoundError: If item not found.
        """
        if fields is None:
            fields = _DEFAULT_QUEUE_FIELDS

        params: dict[str, Any] = {}
        if fields:
            params["fields"] = ",".join(fields)

        response = self._client._request("GET", f"{self._endpoint}/{key}", params=params)
        if response is None:
            raise NotFoundError(f"Queue item {key} not found")
        if not isinstance(response, dict):
            raise NotFoundError(f"Queue item {key} returned invalid response")

        return self._to_model(response)

    def delete(self, key: int) -> None:
        """Remove an item from the queue.

        Args:
            key: Queue item $key (ID).
        """
        self._client._request("DELETE", f"{self._endpoint}/{key}")

    def count(self) -> int:
        """Get total count of items in queue.

        Returns:
            Number of queue items.
        """
        items = self.list(fields=["$key"], limit=1000)
        return len(items)

    def count_pending(self) -> int:
        """Get count of items waiting to sync.

        Returns:
            Number of queued items.
        """
        items = self.list_queued(fields=["$key"])
        return len(items)


# ============================================================================
# Site Sync Remote Snapshots
# ============================================================================

# Default fields for remote snapshots
_DEFAULT_REMOTE_SNAP_FIELDS = [
    "$key",
    "site_syncs_outgoing",
    "name",
    "status",
    "status_info",
    "remote_key",
    "created",
    "description",
    "expires",
]


class SiteSyncRemoteSnap(ResourceObject):
    """Remote snapshot on destination site.

    Represents a cloud snapshot that has been synced to the remote site.

    Properties:
        sync_key: Key of the parent outgoing sync.
        name: Snapshot name on remote.
        status: Status (offline, requesting, downloading, error).
        status_info: Additional status information.
        remote_key: Key of snapshot on remote system.
        created_at: When snapshot was created.
        description: Snapshot description.
        expires_at: When snapshot expires on remote.
    """

    @property
    def sync_key(self) -> int | None:
        """Get the parent outgoing sync key."""
        val = self.get("site_syncs_outgoing")
        return int(val) if val is not None else None

    @property
    def name(self) -> str:
        """Get snapshot name."""
        return str(self.get("name", ""))

    @property
    def status(self) -> str:
        """Get status (offline, request, downloading, error, unsupported)."""
        return str(self.get("status", "offline"))

    @property
    def status_info(self) -> str:
        """Get additional status information."""
        return str(self.get("status_info", ""))

    @property
    def is_downloading(self) -> bool:
        """Check if snapshot is being downloaded (sync back)."""
        return self.status == "downloading"

    @property
    def has_error(self) -> bool:
        """Check if there's an error."""
        return self.status == "error"

    @property
    def remote_key(self) -> int | None:
        """Get the snapshot key on remote system."""
        val = self.get("remote_key")
        return int(val) if val is not None else None

    @property
    def created_at(self) -> datetime | None:
        """Get when snapshot was created."""
        ts = self.get("created")
        if ts and int(ts) > 0:
            return datetime.fromtimestamp(int(ts), tz=timezone.utc)
        return None

    @property
    def description(self) -> str:
        """Get snapshot description."""
        return str(self.get("description", ""))

    @property
    def expires_at(self) -> datetime | None:
        """Get when snapshot expires on remote."""
        ts = self.get("expires")
        if ts and int(ts) > 0:
            return datetime.fromtimestamp(int(ts), tz=timezone.utc)
        return None

    def request_sync_back(self) -> None:
        """Request this snapshot be synced back to local system.

        This initiates a "sync back" operation to restore this
        snapshot from the remote site to the local system.
        """
        from typing import cast

        manager = cast("SiteSyncRemoteSnapManager", self._manager)
        manager.request_sync_back(self.key)

    def set_retention(self, expires: datetime | int) -> None:
        """Set the retention/expiration for this remote snapshot.

        Args:
            expires: New expiration as datetime or Unix timestamp.
        """
        from typing import cast

        manager = cast("SiteSyncRemoteSnapManager", self._manager)
        manager.set_retention(self.key, expires)

    def __repr__(self) -> str:
        key = self.get("$key", "?")
        name = self.name
        status = self.status
        return f"<SiteSyncRemoteSnap key={key} name={name!r} status={status!r}>"


class SiteSyncRemoteSnapManager:
    """Manager for remote snapshots (scoped to an outgoing sync).

    Example:
        >>> sync = client.site_syncs.get(1)
        >>> # Refresh list of remote snapshots
        >>> sync.refresh_remote_snapshots()

        >>> # List remote snapshots
        >>> snaps = sync.remote_snapshots.list()
        >>> for snap in snaps:
        ...     print(f"{snap.name}: expires {snap.expires_at}")

        >>> # Request a snapshot to be synced back
        >>> snap = snaps[0]
        >>> snap.request_sync_back()
    """

    def __init__(self, client: VergeClient, sync_key: int) -> None:
        self._client = client
        self._sync_key = sync_key
        self._endpoint = "site_syncs_outgoing_remote_snaps"
        self._actions_endpoint = "site_syncs_outgoing_remote_snap_actions"

    def _to_model(self, data: dict[str, Any]) -> SiteSyncRemoteSnap:
        return SiteSyncRemoteSnap(data, self)  # type: ignore[arg-type]

    def list(  # noqa: A003
        self,
        filter: str | None = None,  # noqa: A002
        fields: builtins.list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        **filter_kwargs: Any,
    ) -> builtins.list[SiteSyncRemoteSnap]:
        """List remote snapshots.

        Args:
            filter: OData filter string.
            fields: List of fields to return.
            limit: Maximum results to return.
            offset: Skip this many results.
            **filter_kwargs: Additional filter arguments.

        Returns:
            List of SiteSyncRemoteSnap objects sorted by expiration.
        """
        conditions: builtins.list[str] = [f"site_syncs_outgoing eq {self._sync_key}"]

        if filter:
            conditions.append(f"({filter})")

        if filter_kwargs:
            conditions.append(build_filter(**filter_kwargs))

        combined_filter = " and ".join(conditions)

        if fields is None:
            fields = _DEFAULT_REMOTE_SNAP_FIELDS

        params: dict[str, Any] = {
            "filter": combined_filter,
            "sort": "+expires",
        }
        if fields:
            params["fields"] = ",".join(fields)
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

    def get(
        self,
        key: int | None = None,
        *,
        name: str | None = None,
        fields: builtins.list[str] | None = None,
    ) -> SiteSyncRemoteSnap:
        """Get a remote snapshot by key or name.

        Args:
            key: Snapshot $key (ID).
            name: Snapshot name.
            fields: List of fields to return.

        Returns:
            SiteSyncRemoteSnap object.

        Raises:
            NotFoundError: If not found.
            ValueError: If neither key nor name provided.
        """
        if fields is None:
            fields = _DEFAULT_REMOTE_SNAP_FIELDS

        if key is not None:
            params: dict[str, Any] = {}
            if fields:
                params["fields"] = ",".join(fields)

            response = self._client._request("GET", f"{self._endpoint}/{key}", params=params)
            if response is None:
                raise NotFoundError(f"Remote snapshot {key} not found")
            if not isinstance(response, dict):
                raise NotFoundError(f"Remote snapshot {key} returned invalid response")

            return self._to_model(response)

        if name is not None:
            escaped_name = name.replace("'", "''")
            results = self.list(filter=f"name eq '{escaped_name}'", fields=fields)
            if not results:
                raise NotFoundError(f"Remote snapshot '{name}' not found")
            return results[0]

        raise ValueError("Either key or name must be provided")

    def request_sync_back(self, key: int) -> None:
        """Request a remote snapshot to be synced back.

        Args:
            key: Remote snapshot $key (ID).
        """
        body: dict[str, Any] = {
            "site_syncs_outgoing_remote_snap": key,
            "action": "request",
        }
        self._client._request("POST", self._actions_endpoint, json_data=body)

    def set_retention(self, key: int, expires: datetime | int) -> None:
        """Set retention for a remote snapshot.

        Args:
            key: Remote snapshot $key (ID).
            expires: New expiration as datetime or Unix timestamp.
        """
        expires_ts = int(expires.timestamp()) if isinstance(expires, datetime) else int(expires)

        body: dict[str, Any] = {
            "site_syncs_outgoing_remote_snap": key,
            "action": "set_retention",
            "params": {"expires": expires_ts},
        }
        self._client._request("POST", self._actions_endpoint, json_data=body)

    def count(self) -> int:
        """Get count of remote snapshots.

        Returns:
            Number of remote snapshots.
        """
        snaps = self.list(fields=["$key"], limit=1000)
        return len(snaps)


# ============================================================================
# Site Sync Incoming Verified
# ============================================================================

# Default fields for verified syncs
_DEFAULT_VERIFIED_FIELDS = [
    "$key",
    "site_syncs_incoming",
    "name",
    "registered",
    "registered_on",
]


class SiteSyncIncomingVerified(ResourceObject):
    """Verified incoming sync resource object.

    Represents a verified/registered incoming sync connection.

    Properties:
        incoming_sync_key: Key of the parent incoming sync.
        name: Name (from parent sync).
        is_registered: Whether sync is registered.
        registered_at: When sync was registered.
    """

    @property
    def incoming_sync_key(self) -> int | None:
        """Get the parent incoming sync key."""
        val = self.get("site_syncs_incoming")
        return int(val) if val is not None else None

    @property
    def name(self) -> str:
        """Get name (from parent sync)."""
        return str(self.get("name", ""))

    @property
    def is_registered(self) -> bool:
        """Check if sync is registered."""
        return bool(self.get("registered", False))

    @property
    def registered_at(self) -> datetime | None:
        """Get when sync was registered."""
        ts = self.get("registered_on")
        if ts and int(ts) > 0:
            return datetime.fromtimestamp(int(ts), tz=timezone.utc)
        return None

    def list_remote_snapshots(self) -> builtins.list[dict[str, Any]]:
        """Request list of snapshots available on the remote sender.

        Returns:
            List of snapshot information dicts.
        """
        from typing import cast

        manager = cast("SiteSyncIncomingVerifiedManager", self._manager)
        return manager.list_remote_snapshots(self.key)

    def request_snapshot(
        self,
        snapshot_name: str,
        retention: int | timedelta = 259200,
    ) -> None:
        """Request a snapshot to be synced from the remote sender.

        Args:
            snapshot_name: Name of snapshot on remote system.
            retention: Retention period in seconds or timedelta.
        """
        from typing import cast

        manager = cast("SiteSyncIncomingVerifiedManager", self._manager)
        manager.request_snapshot(self.key, snapshot_name, retention)

    def set_retention(
        self,
        snapshot_name: str,
        retention: int | timedelta,
    ) -> None:
        """Set retention for a synced snapshot.

        Args:
            snapshot_name: Name of the snapshot.
            retention: New retention period in seconds or timedelta.
        """
        from typing import cast

        manager = cast("SiteSyncIncomingVerifiedManager", self._manager)
        manager.set_retention(self.key, snapshot_name, retention)

    def __repr__(self) -> str:
        key = self.get("$key", "?")
        name = self.name
        registered = self.is_registered
        return f"<SiteSyncIncomingVerified key={key} name={name!r} registered={registered}>"


class SiteSyncIncomingVerifiedManager:
    """Manager for verified incoming syncs (scoped to an incoming sync).

    Example:
        >>> incoming = client.site_syncs_incoming.get(1)
        >>> verified = incoming.verified.get()
        >>> print(f"Registered: {verified.is_registered}")

        >>> # List snapshots available on sender
        >>> snaps = verified.list_remote_snapshots()

        >>> # Request a snapshot to sync back
        >>> verified.request_snapshot("cloud-snap-2024-01-01", retention=604800)
    """

    def __init__(self, client: VergeClient, incoming_sync_key: int) -> None:
        self._client = client
        self._incoming_sync_key = incoming_sync_key
        self._endpoint = "site_syncs_incoming_verified"
        self._actions_endpoint = "site_syncs_incoming_verified_actions"

    def _to_model(self, data: dict[str, Any]) -> SiteSyncIncomingVerified:
        return SiteSyncIncomingVerified(data, self)  # type: ignore[arg-type]

    def get(
        self,
        fields: builtins.list[str] | None = None,
    ) -> SiteSyncIncomingVerified | None:
        """Get the verified sync entry for this incoming sync.

        Args:
            fields: List of fields to return.

        Returns:
            SiteSyncIncomingVerified object or None.
        """
        if fields is None:
            fields = _DEFAULT_VERIFIED_FIELDS

        params: dict[str, Any] = {
            "filter": f"site_syncs_incoming eq {self._incoming_sync_key}",
            "limit": 1,
        }
        if fields:
            params["fields"] = ",".join(fields)

        response = self._client._request("GET", self._endpoint, params=params)
        if response is None:
            return None

        if isinstance(response, list):
            if not response:
                return None
            return self._to_model(response[0])

        return self._to_model(response)

    def list_remote_snapshots(self, verified_key: int) -> builtins.list[dict[str, Any]]:
        """Request list of snapshots available on the remote sender.

        Args:
            verified_key: Verified sync $key (ID).

        Returns:
            List of snapshot information dicts.
        """
        body: dict[str, Any] = {
            "site_syncs_incoming_verified": verified_key,
            "action": "list_snaps",
        }
        response = self._client._request("POST", self._actions_endpoint, json_data=body)
        if response and isinstance(response, dict):
            snaps = response.get("snapshots", [])
            if isinstance(snaps, list):
                return snaps
        return []

    def request_snapshot(
        self,
        verified_key: int,
        snapshot_name: str,
        retention: int | timedelta = 259200,
    ) -> None:
        """Request a snapshot to be synced from the remote sender.

        Args:
            verified_key: Verified sync $key (ID).
            snapshot_name: Name of snapshot on remote system.
            retention: Retention period in seconds or timedelta.
        """
        if isinstance(retention, timedelta):
            retention_seconds = int(retention.total_seconds())
        else:
            retention_seconds = int(retention)

        body: dict[str, Any] = {
            "site_syncs_incoming_verified": verified_key,
            "action": "request",
            "params": {
                "snapshot": snapshot_name,
                "retention": retention_seconds,
            },
        }
        self._client._request("POST", self._actions_endpoint, json_data=body)

    def set_retention(
        self,
        verified_key: int,
        snapshot_name: str,
        retention: int | timedelta,
    ) -> None:
        """Set retention for a synced snapshot.

        Args:
            verified_key: Verified sync $key (ID).
            snapshot_name: Name of the snapshot.
            retention: New retention period in seconds or timedelta.
        """
        if isinstance(retention, timedelta):
            retention_seconds = int(retention.total_seconds())
        else:
            retention_seconds = int(retention)

        body: dict[str, Any] = {
            "site_syncs_incoming_verified": verified_key,
            "action": "set_retention",
            "params": {
                "snapshot": snapshot_name,
                "retention": retention_seconds,
            },
        }
        self._client._request("POST", self._actions_endpoint, json_data=body)


# ============================================================================
# Site Sync Logs
# ============================================================================

# Default fields for logs
_DEFAULT_LOG_FIELDS = [
    "$key",
    "level",
    "text",
    "timestamp",
    "user",
]

# Log level display mappings
LOG_LEVEL_DISPLAY = {
    "audit": "Audit",
    "message": "Message",
    "warning": "Warning",
    "error": "Error",
    "critical": "Critical",
    "summary": "Summary",
    "debug": "Debug",
}


class SiteSyncLog(ResourceObject):
    """Site sync log entry.

    Properties:
        level: Log level (audit, message, warning, error, critical).
        level_display: Human-readable level name.
        text: Log message text.
        timestamp_us: Timestamp in microseconds.
        logged_at: Datetime when logged.
        user: User who triggered the log (if applicable).
    """

    @property
    def level(self) -> str:
        """Get log level."""
        return str(self.get("level", "message"))

    @property
    def level_display(self) -> str:
        """Get human-readable level name."""
        return LOG_LEVEL_DISPLAY.get(self.level, self.level.title())

    @property
    def is_error(self) -> bool:
        """Check if this is an error or critical log."""
        return self.level in ("error", "critical")

    @property
    def is_warning(self) -> bool:
        """Check if this is a warning log."""
        return self.level == "warning"

    @property
    def text(self) -> str:
        """Get log message text."""
        return str(self.get("text", ""))

    @property
    def timestamp_us(self) -> int:
        """Get timestamp in microseconds."""
        return int(self.get("timestamp", 0))

    @property
    def logged_at(self) -> datetime | None:
        """Get datetime when logged."""
        ts = self.timestamp_us
        if ts > 0:
            return datetime.fromtimestamp(ts / 1_000_000, tz=timezone.utc)
        return None

    @property
    def user(self) -> str:
        """Get user who triggered the log."""
        return str(self.get("user", ""))

    def __repr__(self) -> str:
        level = self.level
        text = self.text[:50] + "..." if len(self.text) > 50 else self.text
        return f"<SiteSyncLog [{level}] {text!r}>"


class SiteSyncOutgoingLogManager:
    """Manager for outgoing sync logs (scoped to an outgoing sync).

    Example:
        >>> sync = client.site_syncs.get(1)
        >>> logs = sync.logs.list(limit=20)
        >>> for log in logs:
        ...     print(f"[{log.level}] {log.text}")

        >>> # Get only errors
        >>> errors = sync.logs.list_errors()
    """

    def __init__(self, client: VergeClient, sync_key: int) -> None:
        self._client = client
        self._sync_key = sync_key
        self._endpoint = "site_syncs_outgoing_logs"

    def _to_model(self, data: dict[str, Any]) -> SiteSyncLog:
        return SiteSyncLog(data, None)  # type: ignore[arg-type]

    def list(  # noqa: A003
        self,
        filter: str | None = None,  # noqa: A002
        fields: builtins.list[str] | None = None,
        limit: int | None = 100,
        offset: int | None = None,
        *,
        level: str | None = None,
        **filter_kwargs: Any,
    ) -> builtins.list[SiteSyncLog]:
        """List logs for this sync.

        Args:
            filter: OData filter string.
            fields: List of fields to return.
            limit: Maximum entries (default 100).
            offset: Skip this many entries.
            level: Filter by level (audit, message, warning, error, critical).
            **filter_kwargs: Additional filter arguments.

        Returns:
            List of SiteSyncLog objects, newest first.
        """
        conditions: builtins.list[str] = [f"site_syncs_outgoing eq {self._sync_key}"]

        if level is not None:
            conditions.append(f"level eq '{level}'")

        if filter:
            conditions.append(f"({filter})")

        if filter_kwargs:
            conditions.append(build_filter(**filter_kwargs))

        combined_filter = " and ".join(conditions)

        if fields is None:
            fields = _DEFAULT_LOG_FIELDS

        params: dict[str, Any] = {
            "filter": combined_filter,
            "sort": "-timestamp",
        }
        if fields:
            params["fields"] = ",".join(fields)
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

    def list_errors(
        self,
        limit: int | None = 100,
        fields: builtins.list[str] | None = None,
    ) -> builtins.list[SiteSyncLog]:
        """List error and critical logs.

        Args:
            limit: Maximum entries.
            fields: List of fields to return.

        Returns:
            List of error/critical SiteSyncLog objects.
        """
        return self.list(
            filter="level eq 'error' or level eq 'critical'",
            limit=limit,
            fields=fields,
        )

    def list_warnings(
        self,
        limit: int | None = 100,
        fields: builtins.list[str] | None = None,
    ) -> builtins.list[SiteSyncLog]:
        """List warning logs.

        Args:
            limit: Maximum entries.
            fields: List of fields to return.

        Returns:
            List of warning SiteSyncLog objects.
        """
        return self.list(level="warning", limit=limit, fields=fields)


class SiteSyncIncomingLogManager:
    """Manager for incoming sync logs (scoped to an incoming sync).

    Example:
        >>> incoming = client.site_syncs_incoming.get(1)
        >>> logs = incoming.logs.list(limit=20)
        >>> for log in logs:
        ...     print(f"[{log.level}] {log.text}")

        >>> # Get only errors
        >>> errors = incoming.logs.list_errors()
    """

    def __init__(self, client: VergeClient, sync_key: int) -> None:
        self._client = client
        self._sync_key = sync_key
        self._endpoint = "site_syncs_incoming_logs"

    def _to_model(self, data: dict[str, Any]) -> SiteSyncLog:
        return SiteSyncLog(data, None)  # type: ignore[arg-type]

    def list(  # noqa: A003
        self,
        filter: str | None = None,  # noqa: A002
        fields: builtins.list[str] | None = None,
        limit: int | None = 100,
        offset: int | None = None,
        *,
        level: str | None = None,
        **filter_kwargs: Any,
    ) -> builtins.list[SiteSyncLog]:
        """List logs for this sync.

        Args:
            filter: OData filter string.
            fields: List of fields to return.
            limit: Maximum entries (default 100).
            offset: Skip this many entries.
            level: Filter by level (audit, message, warning, error, critical).
            **filter_kwargs: Additional filter arguments.

        Returns:
            List of SiteSyncLog objects, newest first.
        """
        conditions: builtins.list[str] = [f"site_syncs_incoming eq {self._sync_key}"]

        if level is not None:
            conditions.append(f"level eq '{level}'")

        if filter:
            conditions.append(f"({filter})")

        if filter_kwargs:
            conditions.append(build_filter(**filter_kwargs))

        combined_filter = " and ".join(conditions)

        if fields is None:
            fields = _DEFAULT_LOG_FIELDS

        params: dict[str, Any] = {
            "filter": combined_filter,
            "sort": "-timestamp",
        }
        if fields:
            params["fields"] = ",".join(fields)
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

    def list_errors(
        self,
        limit: int | None = 100,
        fields: builtins.list[str] | None = None,
    ) -> builtins.list[SiteSyncLog]:
        """List error and critical logs.

        Args:
            limit: Maximum entries.
            fields: List of fields to return.

        Returns:
            List of error/critical SiteSyncLog objects.
        """
        return self.list(
            filter="level eq 'error' or level eq 'critical'",
            limit=limit,
            fields=fields,
        )

    def list_warnings(
        self,
        limit: int | None = 100,
        fields: builtins.list[str] | None = None,
    ) -> builtins.list[SiteSyncLog]:
        """List warning logs.

        Args:
            limit: Maximum entries.
            fields: List of fields to return.

        Returns:
            List of warning SiteSyncLog objects.
        """
        return self.list(level="warning", limit=limit, fields=fields)
