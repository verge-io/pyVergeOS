"""Catalog management resources for VergeOS recipe repositories.

Catalogs organize recipes (VM and tenant templates) into logical groups.
Catalog repositories define where catalogs are sourced from - local, remote,
or from the Verge.io marketplace.

Key concepts:
    - **Repository**: A source of catalogs (local, remote, git, Verge.io marketplace)
    - **Catalog**: A collection of related recipes within a repository
    - **Status**: Current state of a repository (online, refreshing, error, etc.)

Repository types:
    - local: Locally created catalogs and recipes
    - provider: Service provider catalogs (inherited from parent)
    - remote: Remote HTTP/HTTPS URL
    - remote-git: Remote Git repository
    - yottabyte: Verge.io official marketplace

Example:
    >>> # List all catalog repositories
    >>> for repo in client.catalog_repositories.list():
    ...     print(f"{repo.name} ({repo.type}): {repo.status_info}")

    >>> # Get repository with catalogs
    >>> repo = client.catalog_repositories.get(name="Verge.io Recipes")
    >>> for catalog in repo.catalogs.list():
    ...     print(f"  {catalog.name}: {catalog.description}")

    >>> # Refresh a repository to get latest recipes
    >>> repo.refresh_catalogs()

    >>> # View repository logs
    >>> for log in repo.logs.list(limit=10):
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
# Catalog Repository Status
# =============================================================================


class CatalogRepositoryStatus(ResourceObject):
    """Catalog repository status resource object.

    Represents the current operational status of a catalog repository.

    Attributes:
        key: Status $key (row ID).
        repository: Parent repository key.
        status: Current status (online, refreshing, downloading, etc.).
        state: State indicator (online, offline, warning, error).
        info: Additional status information text.
        last_update: Timestamp of last status change.
    """

    @property
    def repository_key(self) -> int | None:
        """Get the parent repository key."""
        repo = self.get("repository")
        return int(repo) if repo is not None else None

    @property
    def is_online(self) -> bool:
        """Check if repository is online."""
        return self.get("state") == "online"

    @property
    def is_error(self) -> bool:
        """Check if repository is in error state."""
        return self.get("state") == "error"

    @property
    def is_busy(self) -> bool:
        """Check if repository is currently busy (refreshing, downloading, etc.)."""
        status = self.get("status", "")
        return status in ("refreshing", "downloading", "installing", "applying")


class CatalogRepositoryStatusManager(ResourceManager["CatalogRepositoryStatus"]):
    """Manager for catalog repository status operations.

    Status objects are read-only and automatically created for each repository.

    Example:
        >>> # Get status for all repositories
        >>> for status in client.catalog_repository_status.list():
        ...     print(f"{status.repository_key}: {status.status}")

        >>> # Get status for a specific repository
        >>> status = client.catalog_repository_status.get_for_repository(1)
    """

    _endpoint = "catalog_repository_status"

    _default_fields = [
        "$key",
        "repository",
        "repository#name as repository_display",
        "status",
        "state",
        "info",
        "last_update",
    ]

    def __init__(self, client: VergeClient, *, repository_key: int | None = None) -> None:
        super().__init__(client)
        self._repository_key = repository_key

    def list(
        self,
        filter: str | None = None,
        fields: builtins.list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        repository: int | None = None,
        **filter_kwargs: Any,
    ) -> builtins.list[CatalogRepositoryStatus]:
        """List repository status records with optional filtering.

        Args:
            filter: OData filter string.
            fields: List of fields to return (uses defaults if not specified).
            limit: Maximum number of results.
            offset: Skip this many results.
            repository: Filter by repository key. Ignored if manager is scoped.
            **filter_kwargs: Shorthand filter arguments.

        Returns:
            List of CatalogRepositoryStatus objects.
        """
        params: dict[str, Any] = {}

        # Build filter
        filters: builtins.list[str] = []
        if filter:
            filters.append(filter)
        if filter_kwargs:
            filters.append(build_filter(**filter_kwargs))

        # Add repository filter (from scope or parameter)
        repo_key = self._repository_key
        if repo_key is None and repository is not None:
            repo_key = repository

        if repo_key is not None:
            filters.append(f"repository eq {repo_key}")

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
    ) -> CatalogRepositoryStatus:
        """Get a single status record by key.

        Args:
            key: Status $key (row ID).
            fields: List of fields to return.

        Returns:
            CatalogRepositoryStatus object.

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
            raise NotFoundError(f"Repository status with key {key} not found")
        if not isinstance(response, dict):
            raise NotFoundError(f"Repository status with key {key} returned invalid response")
        return self._to_model(response)

    def get_for_repository(self, repository_key: int) -> CatalogRepositoryStatus:
        """Get status for a specific repository.

        Args:
            repository_key: Repository $key.

        Returns:
            CatalogRepositoryStatus object.

        Raises:
            NotFoundError: If status not found.
        """
        results = self.list(repository=repository_key, limit=1)
        if not results:
            raise NotFoundError(f"Status for repository {repository_key} not found")
        return results[0]

    def _to_model(self, data: dict[str, Any]) -> CatalogRepositoryStatus:
        """Convert API response to CatalogRepositoryStatus object."""
        return CatalogRepositoryStatus(data, self)


# =============================================================================
# Catalog Repository Logs
# =============================================================================


class CatalogRepositoryLog(ResourceObject):
    """Catalog repository log entry resource object.

    Represents a log entry from repository operations.

    Attributes:
        key: Log entry $key (row ID).
        catalog_repository: Repository key.
        level: Log level (message, warning, error, critical, etc.).
        text: Log message text.
        timestamp: Log timestamp (microseconds).
        user: User who triggered the log.
    """

    @property
    def repository_key(self) -> int | None:
        """Get the repository key."""
        repo = self.get("catalog_repository")
        return int(repo) if repo is not None else None

    @property
    def is_error(self) -> bool:
        """Check if this is an error log entry."""
        level = self.get("level", "")
        return level in ("error", "critical")

    @property
    def is_warning(self) -> bool:
        """Check if this is a warning log entry."""
        return self.get("level") == "warning"


class CatalogRepositoryLogManager(ResourceManager["CatalogRepositoryLog"]):
    """Manager for catalog repository log operations.

    Example:
        >>> # List all repository logs
        >>> for log in client.catalog_repository_logs.list():
        ...     print(f"{log.level}: {log.text}")

        >>> # List logs for a specific repository
        >>> for log in repo.logs.list():
        ...     print(f"{log.level}: {log.text}")
    """

    _endpoint = "catalog_repository_logs"

    _default_fields = [
        "$key",
        "catalog_repository",
        "catalog_repository#name as repository_display",
        "level",
        "text",
        "timestamp",
        "user",
    ]

    def __init__(self, client: VergeClient, *, repository_key: int | None = None) -> None:
        super().__init__(client)
        self._repository_key = repository_key

    def list(
        self,
        filter: str | None = None,
        fields: builtins.list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        catalog_repository: int | None = None,
        level: str | None = None,
        **filter_kwargs: Any,
    ) -> builtins.list[CatalogRepositoryLog]:
        """List repository logs with optional filtering.

        Args:
            filter: OData filter string.
            fields: List of fields to return (uses defaults if not specified).
            limit: Maximum number of results.
            offset: Skip this many results.
            catalog_repository: Filter by repository key. Ignored if scoped.
            level: Filter by log level.
            **filter_kwargs: Shorthand filter arguments.

        Returns:
            List of CatalogRepositoryLog objects.
        """
        params: dict[str, Any] = {}

        # Build filter
        filters: builtins.list[str] = []
        if filter:
            filters.append(filter)
        if filter_kwargs:
            filters.append(build_filter(**filter_kwargs))

        # Add repository filter (from scope or parameter)
        repo_key = self._repository_key
        if repo_key is None and catalog_repository is not None:
            repo_key = catalog_repository

        if repo_key is not None:
            filters.append(f"catalog_repository eq {repo_key}")

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
    ) -> CatalogRepositoryLog:
        """Get a single log entry by key.

        Args:
            key: Log entry $key (row ID).
            fields: List of fields to return.

        Returns:
            CatalogRepositoryLog object.

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
            raise NotFoundError(f"Repository log with key {key} not found")
        if not isinstance(response, dict):
            raise NotFoundError(f"Repository log with key {key} returned invalid response")
        return self._to_model(response)

    def list_errors(
        self,
        limit: int | None = None,
    ) -> builtins.list[CatalogRepositoryLog]:
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
    ) -> builtins.list[CatalogRepositoryLog]:
        """List warning log entries.

        Args:
            limit: Maximum number of results.

        Returns:
            List of warning log entries.
        """
        return self.list(level="warning", limit=limit)

    def _to_model(self, data: dict[str, Any]) -> CatalogRepositoryLog:
        """Convert API response to CatalogRepositoryLog object."""
        return CatalogRepositoryLog(data, self)


# =============================================================================
# Catalog Logs
# =============================================================================


class CatalogLog(ResourceObject):
    """Catalog log entry resource object.

    Represents a log entry from catalog operations.

    Attributes:
        key: Log entry $key (row ID).
        catalog: Catalog key (40-char hex string).
        level: Log level (message, warning, error, critical, etc.).
        text: Log message text.
        timestamp: Log timestamp (microseconds).
        user: User who triggered the log.
    """

    @property
    def catalog_key(self) -> str | None:
        """Get the catalog key."""
        cat = self.get("catalog")
        return str(cat) if cat is not None else None

    @property
    def is_error(self) -> bool:
        """Check if this is an error log entry."""
        level = self.get("level", "")
        return level in ("error", "critical")

    @property
    def is_warning(self) -> bool:
        """Check if this is a warning log entry."""
        return self.get("level") == "warning"


class CatalogLogManager(ResourceManager["CatalogLog"]):
    """Manager for catalog log operations.

    Example:
        >>> # List all catalog logs
        >>> for log in client.catalog_logs.list():
        ...     print(f"{log.level}: {log.text}")

        >>> # List logs for a specific catalog
        >>> for log in catalog.logs.list():
        ...     print(f"{log.level}: {log.text}")
    """

    _endpoint = "catalog_logs"

    _default_fields = [
        "$key",
        "catalog",
        "catalog#name as catalog_display",
        "level",
        "text",
        "timestamp",
        "user",
    ]

    def __init__(self, client: VergeClient, *, catalog_key: str | None = None) -> None:
        super().__init__(client)
        self._catalog_key = catalog_key

    def list(
        self,
        filter: str | None = None,
        fields: builtins.list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        catalog: str | None = None,
        level: str | None = None,
        **filter_kwargs: Any,
    ) -> builtins.list[CatalogLog]:
        """List catalog logs with optional filtering.

        Args:
            filter: OData filter string.
            fields: List of fields to return (uses defaults if not specified).
            limit: Maximum number of results.
            offset: Skip this many results.
            catalog: Filter by catalog key. Ignored if manager is scoped.
            level: Filter by log level.
            **filter_kwargs: Shorthand filter arguments.

        Returns:
            List of CatalogLog objects.
        """
        params: dict[str, Any] = {}

        # Build filter
        filters: builtins.list[str] = []
        if filter:
            filters.append(filter)
        if filter_kwargs:
            filters.append(build_filter(**filter_kwargs))

        # Add catalog filter (from scope or parameter)
        cat_key = self._catalog_key
        if cat_key is None and catalog is not None:
            cat_key = catalog

        if cat_key is not None:
            filters.append(f"catalog eq '{cat_key}'")

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
    ) -> CatalogLog:
        """Get a single log entry by key.

        Args:
            key: Log entry $key (row ID).
            fields: List of fields to return.

        Returns:
            CatalogLog object.

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
            raise NotFoundError(f"Catalog log with key {key} not found")
        if not isinstance(response, dict):
            raise NotFoundError(f"Catalog log with key {key} returned invalid response")
        return self._to_model(response)

    def list_errors(
        self,
        limit: int | None = None,
    ) -> builtins.list[CatalogLog]:
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
    ) -> builtins.list[CatalogLog]:
        """List warning log entries.

        Args:
            limit: Maximum number of results.

        Returns:
            List of warning log entries.
        """
        return self.list(level="warning", limit=limit)

    def _to_model(self, data: dict[str, Any]) -> CatalogLog:
        """Convert API response to CatalogLog object."""
        return CatalogLog(data, self)


# =============================================================================
# Catalogs
# =============================================================================


class Catalog(ResourceObject):
    """Catalog resource object.

    Represents a catalog containing recipes.

    Note:
        Catalog keys are 40-character hex strings, not integers like most
        other VergeOS resources.

    Attributes:
        key: The catalog unique identifier ($key) - 40-char hex string.
        id: The catalog ID (same as $key).
        repository: Parent repository key.
        name: Catalog name.
        description: Catalog description.
        publishing_scope: Scope (private, global, tenant, none).
        enabled: Whether the catalog is enabled.
        created: Creation timestamp.
    """

    @property
    def key(self) -> str:  # type: ignore[override]
        """Resource primary key ($key) - 40-character hex string.

        Raises:
            ValueError: If resource has no $key (not yet persisted).
        """
        k = self.get("$key")
        if k is None:
            raise ValueError("Resource has no $key - may not be persisted")
        return str(k)

    def refresh(self) -> Catalog:
        """Refresh resource data from API.

        Returns:
            Updated Catalog object.
        """
        from typing import cast

        manager = cast("CatalogManager", self._manager)
        return manager.get(self.key)

    def save(self, **kwargs: Any) -> Catalog:
        """Save changes to resource.

        Args:
            **kwargs: Fields to update.

        Returns:
            Updated Catalog object.
        """
        from typing import cast

        manager = cast("CatalogManager", self._manager)
        return manager.update(self.key, **kwargs)

    def delete(self) -> None:
        """Delete this catalog."""
        from typing import cast

        manager = cast("CatalogManager", self._manager)
        manager.delete(self.key)

    @property
    def repository_key(self) -> int | None:
        """Get the parent repository key."""
        repo = self.get("repository")
        return int(repo) if repo is not None else None

    @property
    def is_enabled(self) -> bool:
        """Check if the catalog is enabled."""
        return bool(self.get("enabled", True))

    @property
    def scope(self) -> str:
        """Get the publishing scope."""
        return str(self.get("publishing_scope", "private"))

    @property
    def logs(self) -> CatalogLogManager:
        """Get a log manager scoped to this catalog.

        Returns:
            CatalogLogManager for this catalog.
        """
        from typing import cast

        manager = cast("CatalogManager", self._manager)
        return CatalogLogManager(manager._client, catalog_key=self.key)


class CatalogManager(ResourceManager["Catalog"]):
    """Manager for catalog operations.

    Catalogs organize recipes into logical groups within repositories.

    Example:
        >>> # List all catalogs
        >>> for catalog in client.catalogs.list():
        ...     print(f"{catalog.name}: {catalog.description}")

        >>> # List catalogs in a specific repository
        >>> for catalog in client.catalogs.list(repository=1):
        ...     print(f"{catalog.name}")

        >>> # Get a specific catalog
        >>> catalog = client.catalogs.get(name="VergeOS Recipes")
    """

    _endpoint = "catalogs"

    _default_fields = [
        "$key",
        "id",
        "repository",
        "repository#name as repository_display",
        "name",
        "description",
        "publishing_scope",
        "enabled",
        "created",
    ]

    def __init__(self, client: VergeClient, *, repository_key: int | None = None) -> None:
        super().__init__(client)
        self._repository_key = repository_key

    def list(
        self,
        filter: str | None = None,
        fields: builtins.list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        repository: int | None = None,
        enabled: bool | None = None,
        **filter_kwargs: Any,
    ) -> builtins.list[Catalog]:
        """List catalogs with optional filtering.

        Args:
            filter: OData filter string.
            fields: List of fields to return (uses defaults if not specified).
            limit: Maximum number of results.
            offset: Skip this many results.
            repository: Filter by repository key. Ignored if manager is scoped.
            enabled: Filter by enabled state.
            **filter_kwargs: Shorthand filter arguments (name, etc.).

        Returns:
            List of Catalog objects.

        Example:
            >>> # List all catalogs
            >>> catalogs = client.catalogs.list()

            >>> # List enabled catalogs only
            >>> catalogs = client.catalogs.list(enabled=True)

            >>> # Filter by name
            >>> catalogs = client.catalogs.list(name="VergeOS*")
        """
        params: dict[str, Any] = {}

        # Build filter
        filters: builtins.list[str] = []
        if filter:
            filters.append(filter)
        if filter_kwargs:
            filters.append(build_filter(**filter_kwargs))

        # Add repository filter (from scope or parameter)
        repo_key = self._repository_key
        if repo_key is None and repository is not None:
            repo_key = repository

        if repo_key is not None:
            filters.append(f"repository eq {repo_key}")

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
        key: str | None = None,
        *,
        name: str | None = None,
        fields: builtins.list[str] | None = None,
    ) -> Catalog:
        """Get a single catalog by key or name.

        Args:
            key: Catalog $key (40-character hex string).
            name: Catalog name.
            fields: List of fields to return.

        Returns:
            Catalog object.

        Raises:
            NotFoundError: If catalog not found.
            ValueError: If no identifier provided.

        Example:
            >>> # Get by key
            >>> catalog = client.catalogs.get("8f73f8bcc9c9f1aaba32f733bfc295acaf548554")

            >>> # Get by name
            >>> catalog = client.catalogs.get(name="VergeOS Recipes")
        """
        if key is not None:
            # Fetch by key using id filter
            params: dict[str, Any] = {
                "filter": f"id eq '{key}'",
            }
            if fields:
                params["fields"] = ",".join(fields)
            else:
                params["fields"] = ",".join(self._default_fields)

            response = self._client._request("GET", self._endpoint, params=params)

            if response is None:
                raise NotFoundError(f"Catalog with key {key} not found")
            if isinstance(response, list):
                if not response:
                    raise NotFoundError(f"Catalog with key {key} not found")
                response = response[0]
            if not isinstance(response, dict):
                raise NotFoundError(f"Catalog with key {key} returned invalid response")
            return self._to_model(response)

        if name is not None:
            # Search by name
            escaped_name = name.replace("'", "''")
            results = self.list(filter=f"name eq '{escaped_name}'", fields=fields, limit=1)
            if not results:
                raise NotFoundError(f"Catalog with name '{name}' not found")
            return results[0]

        raise ValueError("Either key or name must be provided")

    def create(  # type: ignore[override]
        self,
        name: str,
        *,
        repository: int,
        description: str | None = None,
        publishing_scope: str = "private",
        enabled: bool = True,
    ) -> Catalog:
        """Create a new catalog.

        Args:
            name: Catalog name.
            repository: Parent repository key.
            description: Catalog description.
            publishing_scope: Scope (private, global, tenant, none).
            enabled: Whether the catalog is enabled.

        Returns:
            Created Catalog object.

        Example:
            >>> catalog = client.catalogs.create(
            ...     name="My Recipes",
            ...     repository=1,
            ...     description="Custom VM recipes",
            ...     publishing_scope="private"
            ... )
        """
        body: dict[str, Any] = {
            "name": name,
            "repository": repository,
            "enabled": enabled,
        }

        if description is not None:
            body["description"] = description

        if publishing_scope:
            body["publishing_scope"] = publishing_scope

        response = self._client._request("POST", self._endpoint, json_data=body)

        # Get the created catalog
        if response and isinstance(response, dict):
            cat_key = response.get("$key")
            if cat_key:
                return self.get(key=str(cat_key))

        # Fallback: search by name
        return self.get(name=name)

    def update(  # type: ignore[override]
        self,
        key: str,
        *,
        name: str | None = None,
        description: str | None = None,
        publishing_scope: str | None = None,
        enabled: bool | None = None,
    ) -> Catalog:
        """Update a catalog.

        Args:
            key: Catalog $key (40-character hex string).
            name: New name.
            description: New description.
            publishing_scope: New scope.
            enabled: Enable or disable.

        Returns:
            Updated Catalog object.

        Example:
            >>> client.catalogs.update(catalog.key, description="Updated description")
        """
        body: dict[str, Any] = {}

        if name is not None:
            body["name"] = name

        if description is not None:
            body["description"] = description

        if publishing_scope is not None:
            body["publishing_scope"] = publishing_scope

        if enabled is not None:
            body["enabled"] = enabled

        if not body:
            return self.get(key)

        self._client._request("PUT", f"{self._endpoint}/{key}", json_data=body)
        return self.get(key)

    def delete(self, key: str) -> None:  # type: ignore[override]
        """Delete a catalog.

        This operation is destructive and cannot be undone.
        All recipes in the catalog will be deleted.

        Args:
            key: Catalog $key (40-character hex string).

        Raises:
            NotFoundError: If catalog not found.

        Example:
            >>> client.catalogs.delete(catalog.key)
        """
        self._client._request("DELETE", f"{self._endpoint}/{key}")

    def logs(self, key: str) -> CatalogLogManager:
        """Get a log manager scoped to a specific catalog.

        Args:
            key: Catalog $key (40-character hex string).

        Returns:
            CatalogLogManager for the catalog.
        """
        return CatalogLogManager(self._client, catalog_key=key)

    def _to_model(self, data: dict[str, Any]) -> Catalog:
        """Convert API response to Catalog object."""
        return Catalog(data, self)


# =============================================================================
# Catalog Repositories
# =============================================================================


class CatalogRepository(ResourceObject):
    """Catalog repository resource object.

    Represents a source of catalogs and recipes.

    Attributes:
        key: Repository $key (row ID).
        name: Repository name.
        description: Repository description.
        type: Repository type (local, provider, remote, remote-git, yottabyte).
        url: URL for remote repositories.
        user: Username for authentication.
        allow_insecure: Allow insecure SSL certificates.
        auto_refresh: Automatically refresh repository.
        max_tier: Maximum storage tier for downloaded recipes.
        override_default_scope: Override default publishing scope.
        enabled: Whether the repository is enabled.
        last_refreshed: Timestamp of last refresh.
    """

    @property
    def is_enabled(self) -> bool:
        """Check if the repository is enabled."""
        return bool(self.get("enabled", True))

    @property
    def is_local(self) -> bool:
        """Check if this is a local repository."""
        return self.get("type") == "local"

    @property
    def is_remote(self) -> bool:
        """Check if this is a remote repository."""
        repo_type = self.get("type", "")
        return repo_type in ("remote", "remote-git", "yottabyte", "provider")

    @property
    def repository_type(self) -> str:
        """Get the repository type."""
        return str(self.get("type", "local"))

    @property
    def status_info(self) -> str | None:
        """Get the current status from the status object.

        Note: This may require fetching status separately for full details.
        """
        status = self.get("status")
        if isinstance(status, dict):
            return status.get("status")
        return None

    @property
    def status(self) -> CatalogRepositoryStatusManager:
        """Get a status manager scoped to this repository.

        Returns:
            CatalogRepositoryStatusManager for this repository.
        """
        from typing import cast

        manager = cast("CatalogRepositoryManager", self._manager)
        return CatalogRepositoryStatusManager(manager._client, repository_key=self.key)

    @property
    def catalogs(self) -> CatalogManager:
        """Get a catalog manager scoped to this repository.

        Returns:
            CatalogManager for this repository.
        """
        from typing import cast

        manager = cast("CatalogRepositoryManager", self._manager)
        return CatalogManager(manager._client, repository_key=self.key)

    @property
    def logs(self) -> CatalogRepositoryLogManager:
        """Get a log manager scoped to this repository.

        Returns:
            CatalogRepositoryLogManager for this repository.
        """
        from typing import cast

        manager = cast("CatalogRepositoryManager", self._manager)
        return CatalogRepositoryLogManager(manager._client, repository_key=self.key)

    def refresh_catalogs(self) -> dict[str, Any] | None:
        """Refresh this repository to fetch latest catalogs/recipes.

        Returns:
            Task information dict or None.
        """
        from typing import cast

        manager = cast("CatalogRepositoryManager", self._manager)
        return manager.refresh(self.key)

    def get_status(self) -> CatalogRepositoryStatus:
        """Get the current status for this repository.

        Returns:
            CatalogRepositoryStatus object.
        """
        from typing import cast

        manager = cast("CatalogRepositoryManager", self._manager)
        return manager.get_status(self.key)


class CatalogRepositoryManager(ResourceManager["CatalogRepository"]):
    """Manager for catalog repository operations.

    Catalog repositories define where catalogs and recipes are sourced from.

    Example:
        >>> # List all repositories
        >>> for repo in client.catalog_repositories.list():
        ...     print(f"{repo.name} ({repo.type})")

        >>> # Get the local repository
        >>> local = client.catalog_repositories.get(name="Local")

        >>> # Get the Verge.io marketplace
        >>> marketplace = client.catalog_repositories.get(name="Verge.io Recipes")

        >>> # Refresh a repository
        >>> repo.refresh()
    """

    _endpoint = "catalog_repositories"

    _default_fields = [
        "$key",
        "name",
        "description",
        "type",
        "url",
        "user",
        "allow_insecure",
        "auto_refresh",
        "max_tier",
        "override_default_scope",
        "enabled",
        "last_refreshed",
        "status#status as status_value",
        "status#state as status_state",
    ]

    def __init__(self, client: VergeClient) -> None:
        super().__init__(client)

    def list(
        self,
        filter: str | None = None,
        fields: builtins.list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        type: str | None = None,
        enabled: bool | None = None,
        **filter_kwargs: Any,
    ) -> builtins.list[CatalogRepository]:
        """List repositories with optional filtering.

        Args:
            filter: OData filter string.
            fields: List of fields to return (uses defaults if not specified).
            limit: Maximum number of results.
            offset: Skip this many results.
            type: Filter by repository type.
            enabled: Filter by enabled state.
            **filter_kwargs: Shorthand filter arguments (name, etc.).

        Returns:
            List of CatalogRepository objects.

        Example:
            >>> # List all repositories
            >>> repos = client.catalog_repositories.list()

            >>> # List enabled repositories only
            >>> repos = client.catalog_repositories.list(enabled=True)

            >>> # List remote repositories
            >>> repos = client.catalog_repositories.list(type="remote")
        """
        params: dict[str, Any] = {}

        # Build filter
        filters: builtins.list[str] = []
        if filter:
            filters.append(filter)
        if filter_kwargs:
            filters.append(build_filter(**filter_kwargs))

        # Add type filter
        if type is not None:
            filters.append(f"type eq '{type}'")

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
    ) -> CatalogRepository:
        """Get a single repository by key or name.

        Args:
            key: Repository $key (row ID).
            name: Repository name.
            fields: List of fields to return.

        Returns:
            CatalogRepository object.

        Raises:
            NotFoundError: If repository not found.
            ValueError: If no identifier provided.

        Example:
            >>> # Get by key
            >>> repo = client.catalog_repositories.get(1)

            >>> # Get by name
            >>> repo = client.catalog_repositories.get(name="Local")
        """
        if key is not None:
            params: dict[str, Any] = {}
            if fields:
                params["fields"] = ",".join(fields)
            else:
                params["fields"] = ",".join(self._default_fields)

            response = self._client._request("GET", f"{self._endpoint}/{key}", params=params)
            if response is None:
                raise NotFoundError(f"Catalog repository with key {key} not found")
            if not isinstance(response, dict):
                raise NotFoundError(f"Catalog repository with key {key} returned invalid response")
            return self._to_model(response)

        if name is not None:
            escaped_name = name.replace("'", "''")
            results = self.list(filter=f"name eq '{escaped_name}'", fields=fields, limit=1)
            if not results:
                raise NotFoundError(f"Catalog repository with name '{name}' not found")
            return results[0]

        raise ValueError("Either key or name must be provided")

    def create(  # type: ignore[override]
        self,
        name: str,
        *,
        type: str = "local",
        description: str | None = None,
        url: str | None = None,
        user: str | None = None,
        password: str | None = None,
        allow_insecure: bool = False,
        auto_refresh: bool = True,
        max_tier: str = "1",
        override_default_scope: str = "none",
        enabled: bool = True,
    ) -> CatalogRepository:
        """Create a new catalog repository.

        Args:
            name: Repository name.
            type: Repository type (local, remote, remote-git, yottabyte).
            description: Repository description.
            url: URL for remote repositories.
            user: Username for authentication.
            password: Password for authentication.
            allow_insecure: Allow insecure SSL certificates.
            auto_refresh: Automatically refresh repository.
            max_tier: Maximum storage tier for downloads (1-5).
            override_default_scope: Override default publishing scope.
            enabled: Whether the repository is enabled.

        Returns:
            Created CatalogRepository object.

        Example:
            >>> # Create a local repository
            >>> repo = client.catalog_repositories.create(
            ...     name="My Recipes",
            ...     type="local",
            ...     description="Custom local recipes"
            ... )

            >>> # Create a remote repository
            >>> repo = client.catalog_repositories.create(
            ...     name="Partner Recipes",
            ...     type="remote",
            ...     url="https://recipes.example.com/api/v4",
            ...     user="api-user",
            ...     password="api-key"
            ... )
        """
        body: dict[str, Any] = {
            "name": name,
            "type": type,
            "auto_refresh": auto_refresh,
            "max_tier": max_tier,
            "override_default_scope": override_default_scope,
            "enabled": enabled,
        }

        if description is not None:
            body["description"] = description

        if url is not None:
            body["url"] = url

        if user is not None:
            body["user"] = user

        if password is not None:
            body["password"] = password

        if allow_insecure:
            body["allow_insecure"] = allow_insecure

        response = self._client._request("POST", self._endpoint, json_data=body)

        # Get the created repository
        if response and isinstance(response, dict):
            repo_key = response.get("$key")
            if repo_key:
                return self.get(key=int(repo_key))

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
        allow_insecure: bool | None = None,
        auto_refresh: bool | None = None,
        max_tier: str | None = None,
        override_default_scope: str | None = None,
        enabled: bool | None = None,
    ) -> CatalogRepository:
        """Update a catalog repository.

        Args:
            key: Repository $key (row ID).
            name: New name.
            description: New description.
            url: New URL.
            user: New username.
            password: New password.
            allow_insecure: Allow insecure SSL certificates.
            auto_refresh: Automatically refresh repository.
            max_tier: Maximum storage tier.
            override_default_scope: Override default scope.
            enabled: Enable or disable.

        Returns:
            Updated CatalogRepository object.

        Example:
            >>> client.catalog_repositories.update(
            ...     repo.key,
            ...     description="Updated description",
            ...     auto_refresh=False
            ... )
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

        if allow_insecure is not None:
            body["allow_insecure"] = allow_insecure

        if auto_refresh is not None:
            body["auto_refresh"] = auto_refresh

        if max_tier is not None:
            body["max_tier"] = max_tier

        if override_default_scope is not None:
            body["override_default_scope"] = override_default_scope

        if enabled is not None:
            body["enabled"] = enabled

        if not body:
            return self.get(key)

        self._client._request("PUT", f"{self._endpoint}/{key}", json_data=body)
        return self.get(key)

    def delete(self, key: int) -> None:
        """Delete a catalog repository.

        This operation is destructive and cannot be undone.
        All catalogs and recipes in the repository will be deleted.

        Note: The default "Local" repository (key=1) cannot be deleted.

        Args:
            key: Repository $key (row ID).

        Raises:
            NotFoundError: If repository not found.
            APIError: If repository cannot be deleted.

        Example:
            >>> client.catalog_repositories.delete(repo.key)
        """
        self._client._request("DELETE", f"{self._endpoint}/{key}")

    def refresh(self, key: int) -> dict[str, Any] | None:
        """Refresh a repository to fetch latest catalogs/recipes.

        This triggers a refresh operation that connects to the remote
        source and downloads any new or updated catalogs and recipes.

        Args:
            key: Repository $key (row ID).

        Returns:
            Task information dict or None.

        Example:
            >>> result = client.catalog_repositories.refresh(repo.key)
        """
        # The refresh action uses the catalog_repository_actions endpoint
        body: dict[str, Any] = {
            "repository": key,
            "action": "refresh",
        }
        result = self._client._request("POST", "catalog_repository_actions", json_data=body)
        if isinstance(result, dict):
            return result
        return None

    def get_status(self, key: int) -> CatalogRepositoryStatus:
        """Get the current status for a repository.

        Args:
            key: Repository $key (row ID).

        Returns:
            CatalogRepositoryStatus object.
        """
        mgr = CatalogRepositoryStatusManager(self._client)
        return mgr.get_for_repository(key)

    def catalogs(self, key: int) -> CatalogManager:
        """Get a catalog manager scoped to a specific repository.

        Args:
            key: Repository $key (row ID).

        Returns:
            CatalogManager for the repository.
        """
        return CatalogManager(self._client, repository_key=key)

    def logs(self, key: int) -> CatalogRepositoryLogManager:
        """Get a log manager scoped to a specific repository.

        Args:
            key: Repository $key (row ID).

        Returns:
            CatalogRepositoryLogManager for the repository.
        """
        return CatalogRepositoryLogManager(self._client, repository_key=key)

    def _to_model(self, data: dict[str, Any]) -> CatalogRepository:
        """Convert API response to CatalogRepository object."""
        return CatalogRepository(data, self)
