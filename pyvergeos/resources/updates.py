"""Update management resources for VergeOS system updates.

This module provides programmatic access to VergeOS system updates, including
checking for updates, downloading, installing, and monitoring update progress.

Key concepts:
    - **Update Settings**: Main singleton configuration for update behavior
    - **Update Source**: Update server (Verge.io Updates, Trial/NFR, etc.)
    - **Update Branch**: Version branch (stable-4.13, etc.)
    - **Update Package**: Available/installed update packages
    - **Update Source Package**: Packages available from a specific source/branch
    - **Update Source Status**: Current operational status of update source
    - **Update Log**: History of update operations
    - **Update Dashboard**: Aggregated view of update status

Update workflow:
    1. Check for updates (refresh from update source)
    2. Download available packages
    3. Install downloaded packages
    4. Reboot nodes (done automatically per-node with workload migration)

Example:
    >>> # Get update settings
    >>> settings = client.update_settings.get()
    >>> print(f"Branch: {settings.branch_name}, Source: {settings.source_name}")

    >>> # Check for updates
    >>> client.update_settings.check()

    >>> # Download and install updates
    >>> client.update_settings.download()
    >>> client.update_settings.install()

    >>> # Or do everything at once
    >>> client.update_settings.update_all()

    >>> # View update logs
    >>> for log in client.update_logs.list(limit=10):
    ...     print(f"{log.level}: {log.text}")
"""

from __future__ import annotations

import builtins
from typing import TYPE_CHECKING, Any

from pyvergeos.exceptions import NotFoundError
from pyvergeos.filters import build_filter
from pyvergeos.resources.base import ResourceManager, ResourceObject

if TYPE_CHECKING:
    from pyvergeos.client import VergeClient


# =============================================================================
# Update Logs
# =============================================================================


class UpdateLog(ResourceObject):
    """Update log entry resource object.

    Represents a log entry from update operations.

    Attributes:
        key: Log entry $key (row ID).
        level: Log level (audit, message, warning, error, critical).
        text: Log message text.
        timestamp: Log timestamp (microseconds since epoch).
        user: User who triggered the operation.
        object_name: Name of the object related to the log entry.
    """

    @property
    def is_error(self) -> bool:
        """Check if this is an error log entry."""
        level = self.get("level", "")
        return level in ("error", "critical")

    @property
    def is_warning(self) -> bool:
        """Check if this is a warning log entry."""
        return self.get("level") == "warning"

    @property
    def is_audit(self) -> bool:
        """Check if this is an audit log entry."""
        return self.get("level") == "audit"


class UpdateLogManager(ResourceManager["UpdateLog"]):
    """Manager for update log operations.

    Update logs provide history of update operations including downloads,
    installs, and errors.

    Example:
        >>> # List recent update logs
        >>> for log in client.update_logs.list(limit=20):
        ...     print(f"{log.level}: {log.text}")

        >>> # List errors only
        >>> errors = client.update_logs.list_errors()

        >>> # List warnings only
        >>> warnings = client.update_logs.list_warnings()
    """

    _endpoint = "update_logs"

    _default_fields = [
        "$key",
        "level",
        "text",
        "timestamp",
        "user",
        "object_name",
    ]

    def list(  # noqa: A003
        self,
        filter: str | None = None,  # noqa: A002
        fields: builtins.list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        level: str | None = None,
        **filter_kwargs: Any,
    ) -> builtins.list[UpdateLog]:
        """List update logs with optional filtering.

        Args:
            filter: OData filter string.
            fields: List of fields to return (uses defaults if not specified).
            limit: Maximum number of results.
            offset: Skip this many results.
            level: Filter by log level (audit, message, warning, error, critical).
            **filter_kwargs: Shorthand filter arguments.

        Returns:
            List of UpdateLog objects, sorted by timestamp descending.
        """
        params: dict[str, Any] = {}

        # Build filter
        filters: builtins.list[str] = []
        if filter:
            filters.append(filter)
        if filter_kwargs:
            filters.append(build_filter(**filter_kwargs))

        # Add level filter
        if level is not None:
            filters.append(f"level eq '{level}'")

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

        # Default sort by timestamp descending
        params["sort"] = "-timestamp"

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
        fields: builtins.list[str] | None = None,
    ) -> UpdateLog:
        """Get a single log entry by key.

        Args:
            key: Log entry $key (row ID).
            fields: List of fields to return.

        Returns:
            UpdateLog object.

        Raises:
            NotFoundError: If log entry not found.
            ValueError: If key not provided.
        """
        if key is None:
            raise ValueError("Key must be provided")

        params: dict[str, Any] = {}
        if fields:
            params["fields"] = ",".join(fields)
        else:
            params["fields"] = ",".join(self._default_fields)

        response = self._client._request("GET", f"{self._endpoint}/{key}", params=params)
        if response is None:
            raise NotFoundError(f"Update log with key {key} not found")
        if not isinstance(response, dict):
            raise NotFoundError(f"Update log with key {key} returned invalid response")
        return self._to_model(response)

    def list_errors(
        self,
        limit: int | None = None,
    ) -> builtins.list[UpdateLog]:
        """List error and critical log entries.

        Args:
            limit: Maximum number of results.

        Returns:
            List of error/critical log entries.
        """
        return self.list(
            filter="(level eq 'error') or (level eq 'critical')",
            limit=limit,
        )

    def list_warnings(
        self,
        limit: int | None = None,
    ) -> builtins.list[UpdateLog]:
        """List warning log entries.

        Args:
            limit: Maximum number of results.

        Returns:
            List of warning log entries.
        """
        return self.list(level="warning", limit=limit)

    def _to_model(self, data: dict[str, Any]) -> UpdateLog:
        """Convert API response to UpdateLog object."""
        return UpdateLog(data, self)


# =============================================================================
# Update Branches
# =============================================================================


class UpdateBranch(ResourceObject):
    """Update branch resource object.

    Represents an update branch (version stream) like stable-4.13.

    Attributes:
        key: Branch $key (row ID).
        name: Branch name (e.g., 'stable-4.13').
        description: Human-readable description.
        created: Creation timestamp.
    """

    pass


class UpdateBranchManager(ResourceManager["UpdateBranch"]):
    """Manager for update branch operations.

    Update branches define version streams available for updates.
    Branches are typically read-only and managed by the update source.

    Example:
        >>> # List available branches
        >>> for branch in client.update_branches.list():
        ...     print(f"{branch.name}: {branch.description}")

        >>> # Get current branch from settings
        >>> settings = client.update_settings.get()
        >>> current_branch = client.update_branches.get(settings.branch)
    """

    _endpoint = "update_branches"

    _default_fields = [
        "$key",
        "name",
        "description",
        "created",
    ]

    def list(  # noqa: A003
        self,
        filter: str | None = None,  # noqa: A002
        fields: builtins.list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        **filter_kwargs: Any,
    ) -> builtins.list[UpdateBranch]:
        """List update branches with optional filtering.

        Args:
            filter: OData filter string.
            fields: List of fields to return (uses defaults if not specified).
            limit: Maximum number of results.
            offset: Skip this many results.
            **filter_kwargs: Shorthand filter arguments.

        Returns:
            List of UpdateBranch objects.
        """
        params: dict[str, Any] = {}

        # Build filter
        filters: builtins.list[str] = []
        if filter:
            filters.append(filter)
        if filter_kwargs:
            filters.append(build_filter(**filter_kwargs))

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

    def get(
        self,
        key: int | None = None,
        *,
        name: str | None = None,
        fields: builtins.list[str] | None = None,
    ) -> UpdateBranch:
        """Get a single branch by key or name.

        Args:
            key: Branch $key (row ID).
            name: Branch name.
            fields: List of fields to return.

        Returns:
            UpdateBranch object.

        Raises:
            NotFoundError: If branch not found.
            ValueError: If no identifier provided.
        """
        if key is not None:
            params: dict[str, Any] = {}
            if fields:
                params["fields"] = ",".join(fields)
            else:
                params["fields"] = ",".join(self._default_fields)

            response = self._client._request("GET", f"{self._endpoint}/{key}", params=params)
            if response is None:
                raise NotFoundError(f"Update branch with key {key} not found")
            if not isinstance(response, dict):
                raise NotFoundError(f"Update branch with key {key} returned invalid response")
            return self._to_model(response)

        if name is not None:
            escaped_name = name.replace("'", "''")
            results = self.list(filter=f"name eq '{escaped_name}'", fields=fields, limit=1)
            if not results:
                raise NotFoundError(f"Update branch with name '{name}' not found")
            return results[0]

        raise ValueError("Either key or name must be provided")

    def _to_model(self, data: dict[str, Any]) -> UpdateBranch:
        """Convert API response to UpdateBranch object."""
        return UpdateBranch(data, self)


# =============================================================================
# Update Source Status
# =============================================================================


class UpdateSourceStatus(ResourceObject):
    """Update source status resource object.

    Represents the current operational status of an update source.

    Attributes:
        key: Status $key (row ID).
        source: Parent source key.
        status: Current status (idle, refreshing, downloading, installing, applying, error).
        info: Additional status information text.
        nodes_updated: Count of nodes that have been updated.
        last_update: Timestamp of last status change.
    """

    @property
    def source_key(self) -> int | None:
        """Get the parent source key."""
        source = self.get("source")
        return int(source) if source is not None else None

    @property
    def is_idle(self) -> bool:
        """Check if source is idle (not performing any operation)."""
        return self.get("status") == "idle"

    @property
    def is_busy(self) -> bool:
        """Check if source is currently busy with an operation."""
        status = self.get("status", "")
        return status in ("refreshing", "downloading", "installing", "applying")

    @property
    def is_error(self) -> bool:
        """Check if source is in error state."""
        return self.get("status") == "error"

    @property
    def is_refreshing(self) -> bool:
        """Check if source is currently checking for updates."""
        return self.get("status") == "refreshing"

    @property
    def is_downloading(self) -> bool:
        """Check if source is currently downloading updates."""
        return self.get("status") == "downloading"

    @property
    def is_installing(self) -> bool:
        """Check if source is currently installing updates."""
        return self.get("status") == "installing"

    @property
    def is_applying(self) -> bool:
        """Check if source is currently applying updates (rebooting nodes)."""
        return self.get("status") == "applying"


class UpdateSourceStatusManager(ResourceManager["UpdateSourceStatus"]):
    """Manager for update source status operations.

    Status objects are read-only and automatically created/updated for
    each update source.

    Example:
        >>> # Get status for the active update source
        >>> settings = client.update_settings.get()
        >>> status = client.update_source_status.get_for_source(settings.source)
        >>> print(f"Status: {status.status}, Nodes updated: {status.nodes_updated}")

        >>> # Check if update is in progress
        >>> if status.is_busy:
        ...     print("Update in progress...")
    """

    _endpoint = "update_source_status"

    _default_fields = [
        "$key",
        "source",
        "source#name as source_display",
        "status",
        "info",
        "nodes_updated",
        "last_update",
    ]

    def __init__(self, client: VergeClient, *, source_key: int | None = None) -> None:
        super().__init__(client)
        self._source_key = source_key

    def list(  # noqa: A003
        self,
        filter: str | None = None,  # noqa: A002
        fields: builtins.list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        source: int | None = None,
        **filter_kwargs: Any,
    ) -> builtins.list[UpdateSourceStatus]:
        """List source status records with optional filtering.

        Args:
            filter: OData filter string.
            fields: List of fields to return (uses defaults if not specified).
            limit: Maximum number of results.
            offset: Skip this many results.
            source: Filter by source key. Ignored if manager is scoped.
            **filter_kwargs: Shorthand filter arguments.

        Returns:
            List of UpdateSourceStatus objects.
        """
        params: dict[str, Any] = {}

        # Build filter
        filters: builtins.list[str] = []
        if filter:
            filters.append(filter)
        if filter_kwargs:
            filters.append(build_filter(**filter_kwargs))

        # Add source filter (from scope or parameter)
        src_key = self._source_key
        if src_key is None and source is not None:
            src_key = source

        if src_key is not None:
            filters.append(f"source eq {src_key}")

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
        fields: builtins.list[str] | None = None,
    ) -> UpdateSourceStatus:
        """Get a single status record by key.

        Args:
            key: Status $key (row ID).
            fields: List of fields to return.

        Returns:
            UpdateSourceStatus object.

        Raises:
            NotFoundError: If status not found.
            ValueError: If key not provided.
        """
        if key is None:
            raise ValueError("Key must be provided")

        params: dict[str, Any] = {}
        if fields:
            params["fields"] = ",".join(fields)
        else:
            params["fields"] = ",".join(self._default_fields)

        response = self._client._request("GET", f"{self._endpoint}/{key}", params=params)
        if response is None:
            raise NotFoundError(f"Update source status with key {key} not found")
        if not isinstance(response, dict):
            raise NotFoundError(f"Update source status with key {key} returned invalid response")
        return self._to_model(response)

    def get_for_source(self, source_key: int) -> UpdateSourceStatus:
        """Get status for a specific update source.

        Args:
            source_key: Update source $key.

        Returns:
            UpdateSourceStatus object.

        Raises:
            NotFoundError: If status not found.
        """
        results = self.list(source=source_key, limit=1)
        if not results:
            raise NotFoundError(f"Status for source {source_key} not found")
        return results[0]

    def _to_model(self, data: dict[str, Any]) -> UpdateSourceStatus:
        """Convert API response to UpdateSourceStatus object."""
        return UpdateSourceStatus(data, self)


# =============================================================================
# Update Source Packages
# =============================================================================


class UpdateSourcePackage(ResourceObject):
    """Update source package resource object.

    Represents a package available from an update source for a specific branch.

    Attributes:
        key: Package $key (row ID).
        name: Package name.
        description: Package description.
        version: Package version.
        branch: Branch key.
        source: Source key.
        downloaded: Whether the package has been downloaded.
        optional: Whether the package is optional.
        require_license_feature: License feature required for this package.
        created: Creation timestamp.
    """

    @property
    def branch_key(self) -> int | None:
        """Get the branch key."""
        branch = self.get("branch")
        return int(branch) if branch is not None else None

    @property
    def source_key(self) -> int | None:
        """Get the source key."""
        source = self.get("source")
        return int(source) if source is not None else None

    @property
    def is_downloaded(self) -> bool:
        """Check if the package has been downloaded."""
        return bool(self.get("downloaded", False))

    @property
    def is_optional(self) -> bool:
        """Check if the package is optional."""
        return bool(self.get("optional", False))


class UpdateSourcePackageManager(ResourceManager["UpdateSourcePackage"]):
    """Manager for update source package operations.

    Source packages represent what's available from an update source
    for a specific branch.

    Example:
        >>> # List all available packages
        >>> for pkg in client.update_source_packages.list():
        ...     status = "Downloaded" if pkg.is_downloaded else "Available"
        ...     print(f"{pkg.name} ({pkg.version}): {status}")

        >>> # List packages for a specific source
        >>> packages = client.update_source_packages.list(source=1)

        >>> # List packages not yet downloaded
        >>> pending = client.update_source_packages.list(downloaded=False)
    """

    _endpoint = "update_source_packages"

    _default_fields = [
        "$key",
        "name",
        "description",
        "version",
        "branch",
        "branch#name as branch_display",
        "source",
        "source#name as source_display",
        "downloaded",
        "optional",
        "require_license_feature",
        "created",
    ]

    def __init__(
        self,
        client: VergeClient,
        *,
        source_key: int | None = None,
        branch_key: int | None = None,
    ) -> None:
        super().__init__(client)
        self._source_key = source_key
        self._branch_key = branch_key

    def list(  # noqa: A003
        self,
        filter: str | None = None,  # noqa: A002
        fields: builtins.list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        source: int | None = None,
        branch: int | None = None,
        downloaded: bool | None = None,
        **filter_kwargs: Any,
    ) -> builtins.list[UpdateSourcePackage]:
        """List source packages with optional filtering.

        Args:
            filter: OData filter string.
            fields: List of fields to return (uses defaults if not specified).
            limit: Maximum number of results.
            offset: Skip this many results.
            source: Filter by source key. Ignored if manager is scoped.
            branch: Filter by branch key. Ignored if manager is scoped.
            downloaded: Filter by download status.
            **filter_kwargs: Shorthand filter arguments.

        Returns:
            List of UpdateSourcePackage objects.
        """
        params: dict[str, Any] = {}

        # Build filter
        filters: builtins.list[str] = []
        if filter:
            filters.append(filter)
        if filter_kwargs:
            filters.append(build_filter(**filter_kwargs))

        # Add source filter (from scope or parameter)
        src_key = self._source_key
        if src_key is None and source is not None:
            src_key = source

        if src_key is not None:
            filters.append(f"source eq {src_key}")

        # Add branch filter (from scope or parameter)
        br_key = self._branch_key
        if br_key is None and branch is not None:
            br_key = branch

        if br_key is not None:
            filters.append(f"branch eq {br_key}")

        # Add downloaded filter
        if downloaded is not None:
            filters.append(f"downloaded eq {1 if downloaded else 0}")

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

    def get(
        self,
        key: int | None = None,
        *,
        name: str | None = None,
        fields: builtins.list[str] | None = None,
    ) -> UpdateSourcePackage:
        """Get a single source package by key or name.

        Args:
            key: Package $key (row ID).
            name: Package name (may return multiple, takes first).
            fields: List of fields to return.

        Returns:
            UpdateSourcePackage object.

        Raises:
            NotFoundError: If package not found.
            ValueError: If no identifier provided.
        """
        if key is not None:
            params: dict[str, Any] = {}
            if fields:
                params["fields"] = ",".join(fields)
            else:
                params["fields"] = ",".join(self._default_fields)

            response = self._client._request("GET", f"{self._endpoint}/{key}", params=params)
            if response is None:
                raise NotFoundError(f"Update source package with key {key} not found")
            if not isinstance(response, dict):
                raise NotFoundError(
                    f"Update source package with key {key} returned invalid response"
                )
            return self._to_model(response)

        if name is not None:
            escaped_name = name.replace("'", "''")
            results = self.list(filter=f"name eq '{escaped_name}'", fields=fields, limit=1)
            if not results:
                raise NotFoundError(f"Update source package with name '{name}' not found")
            return results[0]

        raise ValueError("Either key or name must be provided")

    def list_pending(self) -> builtins.list[UpdateSourcePackage]:
        """List packages that are available but not yet downloaded.

        Returns:
            List of packages pending download.
        """
        return self.list(downloaded=False)

    def list_downloaded(self) -> builtins.list[UpdateSourcePackage]:
        """List packages that have been downloaded.

        Returns:
            List of downloaded packages.
        """
        return self.list(downloaded=True)

    def _to_model(self, data: dict[str, Any]) -> UpdateSourcePackage:
        """Convert API response to UpdateSourcePackage object."""
        return UpdateSourcePackage(data, self)


# =============================================================================
# Update Sources
# =============================================================================


class UpdateSource(ResourceObject):
    """Update source resource object.

    Represents an update server (e.g., Verge.io Updates, Trial/NFR).

    Attributes:
        key: Source $key (row ID).
        name: Source name.
        description: Source description.
        url: Update server URL.
        user: Authentication username.
        last_updated: Timestamp of last successful update.
        last_refreshed: Timestamp of last refresh check.
        enabled: Whether the source is enabled.
    """

    @property
    def is_enabled(self) -> bool:
        """Check if the source is enabled."""
        return bool(self.get("enabled", True))

    @property
    def status(self) -> UpdateSourceStatusManager:
        """Get a status manager scoped to this source.

        Returns:
            UpdateSourceStatusManager for this source.
        """
        from typing import cast

        manager = cast("UpdateSourceManager", self._manager)
        return UpdateSourceStatusManager(manager._client, source_key=self.key)

    @property
    def packages(self) -> UpdateSourcePackageManager:
        """Get a package manager scoped to this source.

        Returns:
            UpdateSourcePackageManager for this source.
        """
        from typing import cast

        manager = cast("UpdateSourceManager", self._manager)
        return UpdateSourcePackageManager(manager._client, source_key=self.key)

    def get_status(self) -> UpdateSourceStatus:
        """Get the current status for this source.

        Returns:
            UpdateSourceStatus object.
        """
        from typing import cast

        manager = cast("UpdateSourceManager", self._manager)
        return manager.get_status(self.key)

    def refresh(self) -> dict[str, Any] | None:  # type: ignore[override]
        """Trigger a refresh to check for updates.

        Returns:
            Task information dict or None.
        """
        from typing import cast

        manager = cast("UpdateSourceManager", self._manager)
        return manager.action(self.key, "refresh")


class UpdateSourceManager(ResourceManager["UpdateSource"]):
    """Manager for update source operations.

    Update sources define where updates come from (Verge.io update servers).

    Example:
        >>> # List available sources
        >>> for source in client.update_sources.list():
        ...     print(f"{source.name}: {source.url}")

        >>> # Get the active source
        >>> settings = client.update_settings.get()
        >>> source = client.update_sources.get(settings.source)

        >>> # Check source status
        >>> status = source.get_status()
        >>> print(f"Status: {status.status}")
    """

    _endpoint = "update_sources"

    _default_fields = [
        "$key",
        "name",
        "description",
        "url",
        "user",
        "last_updated",
        "last_refreshed",
        "enabled",
    ]

    def list(  # noqa: A003
        self,
        filter: str | None = None,  # noqa: A002
        fields: builtins.list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        enabled: bool | None = None,
        **filter_kwargs: Any,
    ) -> builtins.list[UpdateSource]:
        """List update sources with optional filtering.

        Args:
            filter: OData filter string.
            fields: List of fields to return (uses defaults if not specified).
            limit: Maximum number of results.
            offset: Skip this many results.
            enabled: Filter by enabled state.
            **filter_kwargs: Shorthand filter arguments.

        Returns:
            List of UpdateSource objects.
        """
        params: dict[str, Any] = {}

        # Build filter
        filters: builtins.list[str] = []
        if filter:
            filters.append(filter)
        if filter_kwargs:
            filters.append(build_filter(**filter_kwargs))

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

    def get(
        self,
        key: int | None = None,
        *,
        name: str | None = None,
        fields: builtins.list[str] | None = None,
    ) -> UpdateSource:
        """Get a single source by key or name.

        Args:
            key: Source $key (row ID).
            name: Source name.
            fields: List of fields to return.

        Returns:
            UpdateSource object.

        Raises:
            NotFoundError: If source not found.
            ValueError: If no identifier provided.
        """
        if key is not None:
            params: dict[str, Any] = {}
            if fields:
                params["fields"] = ",".join(fields)
            else:
                params["fields"] = ",".join(self._default_fields)

            response = self._client._request("GET", f"{self._endpoint}/{key}", params=params)
            if response is None:
                raise NotFoundError(f"Update source with key {key} not found")
            if not isinstance(response, dict):
                raise NotFoundError(f"Update source with key {key} returned invalid response")
            return self._to_model(response)

        if name is not None:
            escaped_name = name.replace("'", "''")
            results = self.list(filter=f"name eq '{escaped_name}'", fields=fields, limit=1)
            if not results:
                raise NotFoundError(f"Update source with name '{name}' not found")
            return results[0]

        raise ValueError("Either key or name must be provided")

    def create(  # type: ignore[override]
        self,
        name: str,
        *,
        url: str,
        description: str | None = None,
        user: str | None = None,
        password: str | None = None,
        enabled: bool = True,
    ) -> UpdateSource:
        """Create a new update source.

        Args:
            name: Source name.
            url: Update server URL.
            description: Source description.
            user: Authentication username.
            password: Authentication password.
            enabled: Whether the source is enabled.

        Returns:
            Created UpdateSource object.
        """
        body: dict[str, Any] = {
            "name": name,
            "url": url,
            "enabled": enabled,
        }

        if description is not None:
            body["description"] = description

        if user is not None:
            body["user"] = user

        if password is not None:
            body["password"] = password

        response = self._client._request("POST", self._endpoint, json_data=body)

        # Get the created source
        if response and isinstance(response, dict):
            src_key = response.get("$key")
            if src_key:
                return self.get(key=int(src_key))

        # Fallback: search by name
        return self.get(name=name)

    def update(  # type: ignore[override]
        self,
        key: int,
        *,
        name: str | None = None,
        description: str | None = None,
        url: str | None = None,
        user: str | None = None,
        password: str | None = None,
        enabled: bool | None = None,
    ) -> UpdateSource:
        """Update an update source.

        Args:
            key: Source $key (row ID).
            name: New name.
            description: New description.
            url: New URL.
            user: New username.
            password: New password.
            enabled: Enable or disable.

        Returns:
            Updated UpdateSource object.
        """
        body: dict[str, Any] = {}

        if name is not None:
            body["name"] = name

        if description is not None:
            body["description"] = description

        if url is not None:
            body["url"] = url

        if user is not None:
            body["user"] = user

        if password is not None:
            body["password"] = password

        if enabled is not None:
            body["enabled"] = enabled

        if not body:
            return self.get(key)

        self._client._request("PUT", f"{self._endpoint}/{key}", json_data=body)
        return self.get(key)

    def delete(self, key: int) -> None:
        """Delete an update source.

        Args:
            key: Source $key (row ID).

        Raises:
            NotFoundError: If source not found.
        """
        self._client._request("DELETE", f"{self._endpoint}/{key}")

    def action(self, key: int, action_name: str, **kwargs: Any) -> dict[str, Any] | None:
        """Perform an action on an update source.

        Args:
            key: Source $key (row ID).
            action_name: Action name (refresh, download, install, apply, all).
            **kwargs: Additional action parameters.

        Returns:
            Task information dict or None.
        """
        body: dict[str, Any] = {
            "source": key,
            "action": action_name,
        }
        body.update(kwargs)

        result = self._client._request("POST", "update_actions", json_data=body)
        if isinstance(result, dict):
            return result
        return None

    def get_status(self, key: int) -> UpdateSourceStatus:
        """Get the current status for an update source.

        Args:
            key: Source $key (row ID).

        Returns:
            UpdateSourceStatus object.
        """
        mgr = UpdateSourceStatusManager(self._client)
        return mgr.get_for_source(key)

    def packages(self, key: int) -> UpdateSourcePackageManager:
        """Get a package manager scoped to a specific source.

        Args:
            key: Source $key (row ID).

        Returns:
            UpdateSourcePackageManager for the source.
        """
        return UpdateSourcePackageManager(self._client, source_key=key)

    def _to_model(self, data: dict[str, Any]) -> UpdateSource:
        """Convert API response to UpdateSource object."""
        return UpdateSource(data, self)


# =============================================================================
# Update Packages
# =============================================================================


class UpdatePackage(ResourceObject):
    """Update package resource object.

    Represents an installed or available update package.

    Attributes:
        key: Package key (name string, not integer).
        name: Package name.
        description: Package description.
        version: Package version.
        branch: Branch key.
        type: Package type (ybpkg).
        optional: Whether the package is optional.
        created: Creation timestamp.
        modified: Last modified timestamp.
    """

    @property
    def key(self) -> str:  # type: ignore[override]
        """Resource primary key ($key) - package name string.

        Unlike most resources, update packages use the name as the key.

        Raises:
            ValueError: If resource has no $key.
        """
        k = self.get("$key")
        if k is None:
            k = self.get("name")
        if k is None:
            raise ValueError("Resource has no $key - may not be persisted")
        return str(k)

    @property
    def branch_key(self) -> int | None:
        """Get the branch key."""
        branch = self.get("branch")
        return int(branch) if branch is not None else None

    @property
    def is_optional(self) -> bool:
        """Check if the package is optional."""
        return bool(self.get("optional", False))


class UpdatePackageManager(ResourceManager["UpdatePackage"]):
    """Manager for update package operations.

    Update packages represent the actual software packages that make up
    a VergeOS system.

    Example:
        >>> # List all packages
        >>> for pkg in client.update_packages.list():
        ...     print(f"{pkg.name}: {pkg.version}")

        >>> # Get a specific package
        >>> pkg = client.update_packages.get("yb-system")
    """

    _endpoint = "update_packages"

    _default_fields = [
        "$key",
        "name",
        "description",
        "version",
        "branch",
        "branch#name as branch_display",
        "type",
        "optional",
        "created",
        "modified",
    ]

    def list(  # noqa: A003
        self,
        filter: str | None = None,  # noqa: A002
        fields: builtins.list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        branch: int | None = None,
        **filter_kwargs: Any,
    ) -> builtins.list[UpdatePackage]:
        """List update packages with optional filtering.

        Args:
            filter: OData filter string.
            fields: List of fields to return (uses defaults if not specified).
            limit: Maximum number of results.
            offset: Skip this many results.
            branch: Filter by branch key.
            **filter_kwargs: Shorthand filter arguments.

        Returns:
            List of UpdatePackage objects.
        """
        params: dict[str, Any] = {}

        # Build filter
        filters: builtins.list[str] = []
        if filter:
            filters.append(filter)
        if filter_kwargs:
            filters.append(build_filter(**filter_kwargs))

        # Add branch filter
        if branch is not None:
            filters.append(f"branch eq {branch}")

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
        key: str | None = None,
        *,
        name: str | None = None,
        fields: builtins.list[str] | None = None,
    ) -> UpdatePackage:
        """Get a single package by key (name).

        Args:
            key: Package key (name string).
            name: Package name (alias for key).
            fields: List of fields to return.

        Returns:
            UpdatePackage object.

        Raises:
            NotFoundError: If package not found.
            ValueError: If no identifier provided.
        """
        # Key and name are the same for packages
        pkg_name = key or name
        if pkg_name is None:
            raise ValueError("Either key or name must be provided")

        params: dict[str, Any] = {}
        if fields:
            params["fields"] = ",".join(fields)
        else:
            params["fields"] = ",".join(self._default_fields)

        response = self._client._request("GET", f"{self._endpoint}/{pkg_name}", params=params)
        if response is None:
            raise NotFoundError(f"Update package '{pkg_name}' not found")
        if not isinstance(response, dict):
            raise NotFoundError(f"Update package '{pkg_name}' returned invalid response")
        return self._to_model(response)

    def _to_model(self, data: dict[str, Any]) -> UpdatePackage:
        """Convert API response to UpdatePackage object."""
        return UpdatePackage(data, self)


# =============================================================================
# Update Settings
# =============================================================================


class UpdateSettings(ResourceObject):
    """Update settings resource object.

    Singleton configuration for system update behavior. There is only
    one update settings record (key=1).

    Attributes:
        key: Settings $key (always 1).
        name: Settings name.
        source: Active update source key.
        branch: Selected update branch key.
        auto_refresh: Automatically check for updates.
        auto_update: Automatically install updates.
        auto_reboot: Automatically reboot after updates.
        update_time: Scheduled update time (HH:MM format).
        max_vsan_usage: Maximum vSAN usage percentage for automatic updates.
        warm_reboot: Use kexec for faster reboots.
        multi_cluster_update: Allow multiple clusters to update simultaneously.
        snapshot_cloud_on_update: Take system snapshot before updates.
        snapshot_cloud_expire_seconds: Snapshot expiration period.
        installed: Whether updates are installed and pending reboot.
        reboot_required: Whether a reboot is required.
        applying_updates: Whether updates are currently being applied.
        release_notes_url: URL to release notes.
        anonymize_statistics: Anonymize statistics sent to update server.
    """

    @property
    def source_key(self) -> int | None:
        """Get the active source key."""
        source = self.get("source")
        return int(source) if source is not None else None

    @property
    def source_name(self) -> str | None:
        """Get the active source name if available."""
        source = self.get("source")
        if isinstance(source, dict):
            return source.get("name")
        return self.get("source_display")

    @property
    def branch_key(self) -> int | None:
        """Get the selected branch key."""
        branch = self.get("branch")
        return int(branch) if branch is not None else None

    @property
    def branch_name(self) -> str | None:
        """Get the selected branch name if available."""
        branch = self.get("branch")
        if isinstance(branch, dict):
            return branch.get("name")
        return self.get("branch_display")

    @property
    def is_auto_refresh(self) -> bool:
        """Check if auto-refresh is enabled."""
        return bool(self.get("auto_refresh", True))

    @property
    def is_auto_update(self) -> bool:
        """Check if auto-update is enabled."""
        return bool(self.get("auto_update", False))

    @property
    def is_installed(self) -> bool:
        """Check if updates are installed and pending reboot."""
        return bool(self.get("installed", False))

    @property
    def is_reboot_required(self) -> bool:
        """Check if a reboot is required."""
        return bool(self.get("reboot_required", False))

    @property
    def is_applying_updates(self) -> bool:
        """Check if updates are currently being applied."""
        return bool(self.get("applying_updates", False))

    def check(self) -> dict[str, Any] | None:
        """Check for available updates.

        Returns:
            Task information dict or None.
        """
        from typing import cast

        manager = cast("UpdateSettingsManager", self._manager)
        return manager.check()

    def download(self) -> dict[str, Any] | None:
        """Download available updates.

        Returns:
            Task information dict or None.
        """
        from typing import cast

        manager = cast("UpdateSettingsManager", self._manager)
        return manager.download()

    def install(self) -> dict[str, Any] | None:
        """Install downloaded updates.

        Returns:
            Task information dict or None.
        """
        from typing import cast

        manager = cast("UpdateSettingsManager", self._manager)
        return manager.install()

    def update_all(self, force: bool = False) -> dict[str, Any] | None:
        """Download, install, and reboot in one operation.

        Args:
            force: Allow unmigratable workloads to be temporarily rebooted.

        Returns:
            Task information dict or None.
        """
        from typing import cast

        manager = cast("UpdateSettingsManager", self._manager)
        return manager.update_all(force=force)


class UpdateSettingsManager(ResourceManager["UpdateSettings"]):
    """Manager for update settings operations.

    Update settings is a singleton - there is only one record with key=1.

    Example:
        >>> # Get current settings
        >>> settings = client.update_settings.get()
        >>> print(f"Branch: {settings.branch_name}")
        >>> print(f"Auto-refresh: {settings.is_auto_refresh}")

        >>> # Check for updates
        >>> client.update_settings.check()

        >>> # Download available updates
        >>> client.update_settings.download()

        >>> # Install updates
        >>> client.update_settings.install()

        >>> # Or do everything at once
        >>> client.update_settings.update_all()

        >>> # Update settings
        >>> client.update_settings.update(
        ...     auto_refresh=True,
        ...     update_time="02:00",
        ...     snapshot_cloud_on_update=True,
        ... )
    """

    _endpoint = "update_settings"

    _default_fields = [
        "$key",
        "name",
        "source",
        "source#name as source_display",
        "branch",
        "branch#name as branch_display",
        "branch#description as branch_description",
        "auto_refresh",
        "auto_update",
        "auto_reboot",
        "update_time",
        "max_vsan_usage",
        "warm_reboot",
        "multi_cluster_update",
        "snapshot_cloud_on_update",
        "snapshot_cloud_expire_seconds",
        "installed",
        "reboot_required",
        "applying_updates",
        "applying_updates_force",
        "release_notes_url",
        "anonymize_statistics",
    ]

    def get(  # type: ignore[override]
        self,
        key: int | None = None,
        *,
        fields: builtins.list[str] | None = None,
    ) -> UpdateSettings:
        """Get update settings.

        Update settings is a singleton (key=1), so the key parameter
        is optional and ignored.

        Args:
            key: Ignored (settings is always key=1).
            fields: List of fields to return.

        Returns:
            UpdateSettings object.
        """
        params: dict[str, Any] = {}
        if fields:
            params["fields"] = ",".join(fields)
        else:
            params["fields"] = ",".join(self._default_fields)

        response = self._client._request("GET", f"{self._endpoint}/1", params=params)
        if response is None:
            raise NotFoundError("Update settings not found")
        if not isinstance(response, dict):
            raise NotFoundError("Update settings returned invalid response")
        return self._to_model(response)

    def update(  # type: ignore[override]
        self,
        key: int | None = None,
        *,
        source: int | None = None,
        branch: int | None = None,
        user: str | None = None,
        password: str | None = None,
        auto_refresh: bool | None = None,
        auto_update: bool | None = None,
        auto_reboot: bool | None = None,
        update_time: str | None = None,
        max_vsan_usage: int | None = None,
        warm_reboot: bool | None = None,
        multi_cluster_update: bool | None = None,
        snapshot_cloud_on_update: bool | None = None,
        snapshot_cloud_expire_seconds: int | None = None,
        anonymize_statistics: bool | None = None,
    ) -> UpdateSettings:
        """Update the update settings.

        Args:
            key: Ignored (settings is always key=1).
            source: Update source key.
            branch: Update branch key.
            user: Update server username.
            password: Update server password.
            auto_refresh: Automatically check for updates.
            auto_update: Automatically install updates.
            auto_reboot: Automatically reboot after updates.
            update_time: Scheduled update time (HH:MM format).
            max_vsan_usage: Maximum vSAN usage percentage (10-100).
            warm_reboot: Use kexec for faster reboots.
            multi_cluster_update: Allow multiple clusters to update simultaneously.
            snapshot_cloud_on_update: Take system snapshot before updates.
            snapshot_cloud_expire_seconds: Snapshot expiration period in seconds.
            anonymize_statistics: Anonymize statistics sent to update server.

        Returns:
            Updated UpdateSettings object.
        """
        body: dict[str, Any] = {}

        if source is not None:
            body["source"] = source

        if branch is not None:
            body["branch"] = branch

        if user is not None:
            body["user"] = user

        if password is not None:
            body["password"] = password

        if auto_refresh is not None:
            body["auto_refresh"] = auto_refresh

        if auto_update is not None:
            body["auto_update"] = auto_update

        if auto_reboot is not None:
            body["auto_reboot"] = auto_reboot

        if update_time is not None:
            body["update_time"] = update_time

        if max_vsan_usage is not None:
            body["max_vsan_usage"] = max_vsan_usage

        if warm_reboot is not None:
            body["warm_reboot"] = warm_reboot

        if multi_cluster_update is not None:
            body["multi_cluster_update"] = multi_cluster_update

        if snapshot_cloud_on_update is not None:
            body["snapshot_cloud_on_update"] = snapshot_cloud_on_update

        if snapshot_cloud_expire_seconds is not None:
            body["snapshot_cloud_expire_seconds"] = snapshot_cloud_expire_seconds

        if anonymize_statistics is not None:
            body["anonymize_statistics"] = anonymize_statistics

        if not body:
            return self.get()

        self._client._request("PUT", f"{self._endpoint}/1", json_data=body)
        return self.get()

    def check(self) -> dict[str, Any] | None:
        """Check for available updates.

        Triggers a refresh to check the update source for new packages.

        Returns:
            Task information dict or None.

        Example:
            >>> result = client.update_settings.check()
            >>> if result:
            ...     task = client.tasks.wait(result.get("task"))
        """
        return self._action("check")

    def download(self) -> dict[str, Any] | None:
        """Download available updates.

        Downloads packages that are available from the update source.

        Returns:
            Task information dict or None.

        Example:
            >>> result = client.update_settings.download()
            >>> if result:
            ...     task = client.tasks.wait(result.get("task"))
        """
        return self._action("download")

    def install(self) -> dict[str, Any] | None:
        """Install downloaded updates.

        Installs packages that have been downloaded. This prepares them
        for application during node reboots.

        Returns:
            Task information dict or None.

        Example:
            >>> result = client.update_settings.install()
            >>> if result:
            ...     task = client.tasks.wait(result.get("task"))
        """
        return self._action("install")

    def update_all(self, force: bool = False) -> dict[str, Any] | None:
        """Download, install, and reboot in one operation.

        This is the recommended way to apply updates. It will:
        1. Download available packages
        2. Install packages
        3. Reboot nodes one at a time with workload migration

        Args:
            force: Allow unmigratable workloads to be temporarily rebooted.
                Use this if there are VMs that cannot be migrated (e.g.,
                VMs with GPU passthrough).

        Returns:
            Task information dict or None.

        Example:
            >>> # Normal update
            >>> result = client.update_settings.update_all()

            >>> # Force update (allows non-migratable workloads to reboot)
            >>> result = client.update_settings.update_all(force=True)
        """
        return self._action("all", force=force)

    def _action(self, action: str, **kwargs: Any) -> dict[str, Any] | None:
        """Perform an action on update settings.

        Delegates to the update_actions endpoint with the configured source.

        Args:
            action: Action name (check, download, install, all).
            **kwargs: Additional action parameters.

        Returns:
            Task/action response dict or None.
        """
        # Map settings-level action names to API action names
        action_map: dict[str, str] = {"check": "refresh"}
        api_action = action_map.get(action, action)

        # Get the configured source key from settings
        settings = self.get()
        source_key = settings.source_key
        if source_key is None:
            raise ValueError("No update source configured in settings")

        body: dict[str, Any] = {"source": source_key, "action": api_action}
        body.update(kwargs)

        result = self._client._request("POST", "update_actions", json_data=body)
        if isinstance(result, dict):
            return result
        return None

    def _to_model(self, data: dict[str, Any]) -> UpdateSettings:
        """Convert API response to UpdateSettings object."""
        return UpdateSettings(data, self)


# =============================================================================
# Update Dashboard
# =============================================================================


class UpdateDashboard(ResourceObject):
    """Update dashboard resource object.

    Provides an aggregated view of update status including packages,
    branches, settings, and logs.

    Attributes:
        logs: Recent update logs.
        packages: Available packages with status.
        branches: Available branches.
        settings: Current update settings.
        node_count: Number of physical nodes.
        counts: Event and task counts.
    """

    @property
    def node_count(self) -> int:
        """Get the number of physical nodes."""
        nc = self.get("node_count")
        if isinstance(nc, dict):
            return int(nc.get("$count", 0))
        return int(nc) if nc is not None else 0

    @property
    def event_count(self) -> int:
        """Get the number of update-related events."""
        counts = self.get("counts", {})
        if isinstance(counts, dict):
            return int(counts.get("event_count", 0))
        return 0

    @property
    def task_count(self) -> int:
        """Get the number of active update tasks."""
        counts = self.get("counts", {})
        if isinstance(counts, dict):
            return int(counts.get("task_count", 0))
        return 0

    def get_settings(self) -> dict[str, Any]:
        """Get the settings portion of the dashboard.

        Returns:
            Settings dict with source, branch, and status info.
        """
        settings = self.get("settings", {})
        return settings if isinstance(settings, dict) else {}

    def get_packages(self) -> builtins.list[dict[str, Any]]:
        """Get the packages list from the dashboard.

        Returns:
            List of package dicts with version and status info.
        """
        packages = self.get("packages", [])
        return packages if isinstance(packages, list) else []

    def get_branches(self) -> builtins.list[dict[str, Any]]:
        """Get the available branches from the dashboard.

        Returns:
            List of branch dicts.
        """
        branches = self.get("branches", [])
        return branches if isinstance(branches, list) else []

    def get_logs(self) -> builtins.list[dict[str, Any]]:
        """Get recent logs from the dashboard.

        Returns:
            List of log entry dicts.
        """
        logs = self.get("logs", [])
        return logs if isinstance(logs, list) else []


class UpdateDashboardManager(ResourceManager["UpdateDashboard"]):
    """Manager for update dashboard operations.

    The update dashboard provides an aggregated view of the update system
    including packages, branches, settings, and logs.

    Example:
        >>> # Get the dashboard
        >>> dashboard = client.update_dashboard.get()

        >>> # Check node count
        >>> print(f"Nodes: {dashboard.node_count}")

        >>> # Get settings summary
        >>> settings = dashboard.get_settings()
        >>> print(f"Branch: {settings.get('branch#name')}")

        >>> # List packages
        >>> for pkg in dashboard.get_packages():
        ...     print(f"{pkg.get('name')}: {pkg.get('version')}")
    """

    _endpoint = "update_dashboard"

    def get(  # type: ignore[override]
        self,
        *,
        fields: builtins.list[str] | None = None,
    ) -> UpdateDashboard:
        """Get the update dashboard.

        Args:
            fields: List of fields to return (optional).

        Returns:
            UpdateDashboard object with aggregated update information.
        """
        params: dict[str, Any] = {}
        if fields:
            params["fields"] = ",".join(fields)

        response = self._client._request("GET", self._endpoint, params=params)
        if response is None:
            raise NotFoundError("Update dashboard not found")
        if not isinstance(response, dict):
            raise NotFoundError("Update dashboard returned invalid response")
        return self._to_model(response)

    def _to_model(self, data: dict[str, Any]) -> UpdateDashboard:
        """Convert API response to UpdateDashboard object."""
        return UpdateDashboard(data, self)
