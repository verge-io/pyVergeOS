"""OIDC application management for VergeOS as identity provider.

OIDC applications enable VergeOS to act as an OpenID Connect identity provider,
allowing other systems and tenants to authenticate through VergeOS.

Key concepts:
    - **OIDC Application**: Configuration for a client that authenticates via VergeOS
    - **Client Credentials**: Auto-generated client_id and client_secret for OAuth2 flow
    - **Redirect URIs**: Allowed callback URLs for the OAuth2 flow
    - **Access Control**: User/group ACLs to restrict who can use the application

Benefits:
    - Central identity management across VergeOS systems and tenants
    - Single sign-on (SSO) capabilities
    - Can chain to upstream providers (Azure, Google, etc.)
    - Reduces administrative burden for multi-system environments

Example:
    >>> # List all OIDC applications
    >>> for app in client.oidc_applications.list():
    ...     print(f"{app.name}: {app.client_id}")

    >>> # Create an OIDC application
    >>> app = client.oidc_applications.create(
    ...     name="Tenant Portal",
    ...     redirect_uri="https://tenant.example.com/callback",
    ...     description="OIDC for tenant authentication",
    ... )
    >>> print(f"Client ID: {app.client_id}")
    >>> print(f"Client Secret: {app.client_secret}")

    >>> # Get well-known configuration URL
    >>> print(f"Well-known: {app.well_known_configuration}")

    >>> # Restrict access to specific users
    >>> app = client.oidc_applications.update(app.key, restrict_access=True)
    >>> app.allowed_users.add(user_key=123)
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
# OIDC Application Users (ACL)
# =============================================================================


class OidcApplicationUser(ResourceObject):
    """OIDC application user ACL entry.

    Represents a user that is allowed to use an OIDC application
    when restrict_access is enabled.

    Attributes:
        key: Entry $key (row ID).
        oidc_application: Parent application key.
        user: Allowed user key.
    """

    @property
    def application_key(self) -> int | None:
        """Get the parent OIDC application key."""
        app = self.get("oidc_application")
        return int(app) if app is not None else None

    @property
    def user_key(self) -> int | None:
        """Get the allowed user key."""
        user = self.get("user")
        return int(user) if user is not None else None

    @property
    def user_display(self) -> str | None:
        """Get the user display name."""
        return self.get("user_display")

    def delete(self) -> None:
        """Remove this user from allowed users."""
        from typing import cast

        manager = cast("OidcApplicationUserManager", self._manager)
        manager.delete(self.key)


class OidcApplicationUserManager(ResourceManager["OidcApplicationUser"]):
    """Manager for OIDC application user ACL operations.

    Example:
        >>> # List allowed users for an application
        >>> for entry in app.allowed_users.list():
        ...     print(f"{entry.user_display}")

        >>> # Add a user
        >>> app.allowed_users.add(user_key=123)

        >>> # Remove a user
        >>> entry.delete()
    """

    _endpoint = "oidc_application_users"

    _default_fields = [
        "$key",
        "oidc_application",
        "display(oidc_application) as oidc_application_display",
        "user",
        "display(user) as user_display",
    ]

    def __init__(self, client: VergeClient, *, application_key: int | None = None) -> None:
        super().__init__(client)
        self._application_key = application_key

    def list(  # noqa: A003
        self,
        filter: str | None = None,  # noqa: A002
        fields: builtins.list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        oidc_application: int | None = None,
        **filter_kwargs: Any,
    ) -> builtins.list[OidcApplicationUser]:
        """List allowed users with optional filtering.

        Args:
            filter: OData filter string.
            fields: List of fields to return.
            limit: Maximum number of results.
            offset: Skip this many results.
            oidc_application: Filter by application key. Ignored if scoped.
            **filter_kwargs: Shorthand filter arguments.

        Returns:
            List of OidcApplicationUser objects.
        """
        params: dict[str, Any] = {}

        # Build filter
        filters: builtins.list[str] = []
        if filter:
            filters.append(filter)
        if filter_kwargs:
            filters.append(build_filter(**filter_kwargs))

        # Add application filter
        app_key = self._application_key
        if app_key is None and oidc_application is not None:
            app_key = oidc_application

        if app_key is not None:
            filters.append(f"oidc_application eq {app_key}")

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

    def get(  # type: ignore[override]
        self,
        key: int | None = None,
        *,
        fields: builtins.list[str] | None = None,
    ) -> OidcApplicationUser:
        """Get a single user ACL entry by key.

        Args:
            key: Entry $key (row ID).
            fields: List of fields to return.

        Returns:
            OidcApplicationUser object.

        Raises:
            NotFoundError: If entry not found.
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
            raise NotFoundError(f"OIDC application user with key {key} not found")
        if not isinstance(response, dict):
            raise NotFoundError(f"OIDC application user with key {key} returned invalid response")
        return self._to_model(response)

    def add(self, *, user_key: int) -> OidcApplicationUser:
        """Add a user to allowed users.

        Args:
            user_key: User $key to add.

        Returns:
            Created OidcApplicationUser object.

        Raises:
            ValueError: If manager is not scoped to an application.
        """
        if self._application_key is None:
            raise ValueError("Manager must be scoped to an application to add users")

        body: dict[str, Any] = {
            "oidc_application": self._application_key,
            "user": user_key,
        }

        response = self._client._request("POST", self._endpoint, json_data=body)

        if response and isinstance(response, dict):
            entry_key = response.get("$key")
            if entry_key:
                return self.get(key=int(entry_key))

        # Fallback: search
        results = self.list(limit=1)
        if results:
            return results[0]
        raise NotFoundError("Failed to create user ACL entry")

    def delete(self, key: int) -> None:
        """Remove a user ACL entry.

        Args:
            key: Entry $key (row ID).
        """
        self._client._request("DELETE", f"{self._endpoint}/{key}")

    def _to_model(self, data: dict[str, Any]) -> OidcApplicationUser:
        """Convert API response to OidcApplicationUser object."""
        return OidcApplicationUser(data, self)


# =============================================================================
# OIDC Application Groups (ACL)
# =============================================================================


class OidcApplicationGroup(ResourceObject):
    """OIDC application group ACL entry.

    Represents a group whose members are allowed to use an OIDC application
    when restrict_access is enabled.

    Attributes:
        key: Entry $key (row ID).
        oidc_application: Parent application key.
        group: Allowed group key.
    """

    @property
    def application_key(self) -> int | None:
        """Get the parent OIDC application key."""
        app = self.get("oidc_application")
        return int(app) if app is not None else None

    @property
    def group_key(self) -> int | None:
        """Get the allowed group key."""
        group = self.get("group")
        return int(group) if group is not None else None

    @property
    def group_display(self) -> str | None:
        """Get the group display name."""
        return self.get("group_display")

    def delete(self) -> None:
        """Remove this group from allowed groups."""
        from typing import cast

        manager = cast("OidcApplicationGroupManager", self._manager)
        manager.delete(self.key)


class OidcApplicationGroupManager(ResourceManager["OidcApplicationGroup"]):
    """Manager for OIDC application group ACL operations.

    Example:
        >>> # List allowed groups for an application
        >>> for entry in app.allowed_groups.list():
        ...     print(f"{entry.group_display}")

        >>> # Add a group
        >>> app.allowed_groups.add(group_key=456)

        >>> # Remove a group
        >>> entry.delete()
    """

    _endpoint = "oidc_application_groups"

    _default_fields = [
        "$key",
        "oidc_application",
        "display(oidc_application) as oidc_application_display",
        "group",
        "display(group) as group_display",
    ]

    def __init__(self, client: VergeClient, *, application_key: int | None = None) -> None:
        super().__init__(client)
        self._application_key = application_key

    def list(  # noqa: A003
        self,
        filter: str | None = None,  # noqa: A002
        fields: builtins.list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        oidc_application: int | None = None,
        **filter_kwargs: Any,
    ) -> builtins.list[OidcApplicationGroup]:
        """List allowed groups with optional filtering.

        Args:
            filter: OData filter string.
            fields: List of fields to return.
            limit: Maximum number of results.
            offset: Skip this many results.
            oidc_application: Filter by application key. Ignored if scoped.
            **filter_kwargs: Shorthand filter arguments.

        Returns:
            List of OidcApplicationGroup objects.
        """
        params: dict[str, Any] = {}

        # Build filter
        filters: builtins.list[str] = []
        if filter:
            filters.append(filter)
        if filter_kwargs:
            filters.append(build_filter(**filter_kwargs))

        # Add application filter
        app_key = self._application_key
        if app_key is None and oidc_application is not None:
            app_key = oidc_application

        if app_key is not None:
            filters.append(f"oidc_application eq {app_key}")

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

    def get(  # type: ignore[override]
        self,
        key: int | None = None,
        *,
        fields: builtins.list[str] | None = None,
    ) -> OidcApplicationGroup:
        """Get a single group ACL entry by key.

        Args:
            key: Entry $key (row ID).
            fields: List of fields to return.

        Returns:
            OidcApplicationGroup object.

        Raises:
            NotFoundError: If entry not found.
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
            raise NotFoundError(f"OIDC application group with key {key} not found")
        if not isinstance(response, dict):
            raise NotFoundError(f"OIDC application group with key {key} returned invalid response")
        return self._to_model(response)

    def add(self, *, group_key: int) -> OidcApplicationGroup:
        """Add a group to allowed groups.

        Args:
            group_key: Group $key to add.

        Returns:
            Created OidcApplicationGroup object.

        Raises:
            ValueError: If manager is not scoped to an application.
        """
        if self._application_key is None:
            raise ValueError("Manager must be scoped to an application to add groups")

        body: dict[str, Any] = {
            "oidc_application": self._application_key,
            "group": group_key,
        }

        response = self._client._request("POST", self._endpoint, json_data=body)

        if response and isinstance(response, dict):
            entry_key = response.get("$key")
            if entry_key:
                return self.get(key=int(entry_key))

        # Fallback: search
        results = self.list(limit=1)
        if results:
            return results[0]
        raise NotFoundError("Failed to create group ACL entry")

    def delete(self, key: int) -> None:
        """Remove a group ACL entry.

        Args:
            key: Entry $key (row ID).
        """
        self._client._request("DELETE", f"{self._endpoint}/{key}")

    def _to_model(self, data: dict[str, Any]) -> OidcApplicationGroup:
        """Convert API response to OidcApplicationGroup object."""
        return OidcApplicationGroup(data, self)


# =============================================================================
# OIDC Application Logs
# =============================================================================


class OidcApplicationLog(ResourceObject):
    """OIDC application log entry.

    Represents an audit log entry for OIDC application operations.

    Attributes:
        key: Log entry $key (row ID).
        oidc_application: Parent application key.
        level: Log level (audit, message, warning, error, critical).
        text: Log message text.
        timestamp: Log timestamp (microseconds).
        user: User who triggered the log.
    """

    @property
    def application_key(self) -> int | None:
        """Get the parent application key."""
        app = self.get("oidc_application")
        return int(app) if app is not None else None

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


class OidcApplicationLogManager(ResourceManager["OidcApplicationLog"]):
    """Manager for OIDC application log operations.

    Example:
        >>> # List all logs for an application
        >>> for log in app.logs.list():
        ...     print(f"{log.level}: {log.text}")

        >>> # List errors only
        >>> errors = app.logs.list_errors()
    """

    _endpoint = "oidc_application_logs"

    _default_fields = [
        "$key",
        "oidc_application",
        "oidc_application#name as oidc_application_display",
        "level",
        "text",
        "timestamp",
        "user",
    ]

    def __init__(self, client: VergeClient, *, application_key: int | None = None) -> None:
        super().__init__(client)
        self._application_key = application_key

    def list(  # noqa: A003
        self,
        filter: str | None = None,  # noqa: A002
        fields: builtins.list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        oidc_application: int | None = None,
        level: str | None = None,
        **filter_kwargs: Any,
    ) -> builtins.list[OidcApplicationLog]:
        """List logs with optional filtering.

        Args:
            filter: OData filter string.
            fields: List of fields to return.
            limit: Maximum number of results.
            offset: Skip this many results.
            oidc_application: Filter by application key. Ignored if scoped.
            level: Filter by log level.
            **filter_kwargs: Shorthand filter arguments.

        Returns:
            List of OidcApplicationLog objects.
        """
        params: dict[str, Any] = {}

        # Build filter
        filters: builtins.list[str] = []
        if filter:
            filters.append(filter)
        if filter_kwargs:
            filters.append(build_filter(**filter_kwargs))

        # Add application filter
        app_key = self._application_key
        if app_key is None and oidc_application is not None:
            app_key = oidc_application

        if app_key is not None:
            filters.append(f"oidc_application eq {app_key}")

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

        # Sort by timestamp descending
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
    ) -> OidcApplicationLog:
        """Get a single log entry by key.

        Args:
            key: Log entry $key (row ID).
            fields: List of fields to return.

        Returns:
            OidcApplicationLog object.

        Raises:
            NotFoundError: If entry not found.
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
            raise NotFoundError(f"OIDC application log with key {key} not found")
        if not isinstance(response, dict):
            raise NotFoundError(f"OIDC application log with key {key} returned invalid response")
        return self._to_model(response)

    def list_errors(
        self,
        limit: int | None = None,
    ) -> builtins.list[OidcApplicationLog]:
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
    ) -> builtins.list[OidcApplicationLog]:
        """List warning log entries.

        Args:
            limit: Maximum number of results.

        Returns:
            List of warning log entries.
        """
        return self.list(level="warning", limit=limit)

    def list_audits(
        self,
        limit: int | None = None,
    ) -> builtins.list[OidcApplicationLog]:
        """List audit log entries.

        Args:
            limit: Maximum number of results.

        Returns:
            List of audit log entries.
        """
        return self.list(level="audit", limit=limit)

    def _to_model(self, data: dict[str, Any]) -> OidcApplicationLog:
        """Convert API response to OidcApplicationLog object."""
        return OidcApplicationLog(data, self)


# =============================================================================
# OIDC Application
# =============================================================================


class OidcApplication(ResourceObject):
    """OIDC application resource object.

    Represents an OIDC client application configuration for VergeOS
    acting as an identity provider.

    Attributes:
        key: Application $key (row ID).
        name: Application name.
        enabled: Whether the application is enabled.
        created: Creation timestamp.
        description: Application description.
        redirect_uri: Allowed redirect URIs (newline-separated).
        client_id: OAuth2 client ID (auto-generated).
        client_secret: OAuth2 client secret (auto-generated).
        force_auth_source: Auth source for auto-redirect.
        restrict_access: Whether access is restricted to specific users/groups.
        map_user: User to map all logins to.
        scope_profile: Grant profile scope.
        scope_email: Grant email scope.
        scope_groups: Grant groups scope.
        well_known_configuration: Well-known configuration URL.
    """

    @property
    def client_id(self) -> str | None:
        """Get the OAuth2 client ID."""
        return self.get("client_id")

    @property
    def client_secret(self) -> str | None:
        """Get the OAuth2 client secret.

        Note: This is only available if fetched with include_secret=True.
        """
        return self.get("client_secret")

    @property
    def is_enabled(self) -> bool:
        """Check if the application is enabled."""
        return bool(self.get("enabled", True))

    @property
    def is_access_restricted(self) -> bool:
        """Check if access is restricted to specific users/groups."""
        return bool(self.get("restrict_access", False))

    @property
    def redirect_uris(self) -> builtins.list[str]:
        """Get redirect URIs as a list.

        Redirect URIs are stored as newline-separated values.
        """
        uri = self.get("redirect_uri", "")
        if not uri:
            return []
        return [u.strip() for u in str(uri).split("\n") if u.strip()]

    @property
    def well_known_configuration(self) -> str | None:
        """Get the OIDC well-known configuration URL."""
        return self.get("well_known_configuration")

    @property
    def scopes(self) -> builtins.list[str]:
        """Get enabled scopes as a list."""
        scopes = ["openid"]  # Always included
        if self.get("scope_profile", True):
            scopes.append("profile")
        if self.get("scope_email", True):
            scopes.append("email")
        if self.get("scope_groups", True):
            scopes.append("groups")
        return scopes

    @property
    def force_auth_source_key(self) -> int | None:
        """Get the forced auth source key for auto-redirect."""
        source = self.get("force_auth_source")
        return int(source) if source is not None else None

    @property
    def map_user_key(self) -> int | None:
        """Get the mapped user key."""
        user = self.get("map_user")
        return int(user) if user is not None else None

    @property
    def allowed_users(self) -> OidcApplicationUserManager:
        """Get a user ACL manager scoped to this application.

        Returns:
            OidcApplicationUserManager for this application.
        """
        from typing import cast

        manager = cast("OidcApplicationManager", self._manager)
        return OidcApplicationUserManager(manager._client, application_key=self.key)

    @property
    def allowed_groups(self) -> OidcApplicationGroupManager:
        """Get a group ACL manager scoped to this application.

        Returns:
            OidcApplicationGroupManager for this application.
        """
        from typing import cast

        manager = cast("OidcApplicationManager", self._manager)
        return OidcApplicationGroupManager(manager._client, application_key=self.key)

    @property
    def logs(self) -> OidcApplicationLogManager:
        """Get a log manager scoped to this application.

        Returns:
            OidcApplicationLogManager for this application.
        """
        from typing import cast

        manager = cast("OidcApplicationManager", self._manager)
        return OidcApplicationLogManager(manager._client, application_key=self.key)

    def enable(self) -> OidcApplication:
        """Enable this OIDC application.

        Returns:
            Updated OidcApplication object.
        """
        from typing import cast

        manager = cast("OidcApplicationManager", self._manager)
        return manager.update(self.key, enabled=True)

    def disable(self) -> OidcApplication:
        """Disable this OIDC application.

        Returns:
            Updated OidcApplication object.
        """
        from typing import cast

        manager = cast("OidcApplicationManager", self._manager)
        return manager.update(self.key, enabled=False)

    def refresh(self) -> OidcApplication:
        """Refresh resource data from API.

        Returns:
            Updated OidcApplication object.
        """
        from typing import cast

        manager = cast("OidcApplicationManager", self._manager)
        return manager.get(self.key)

    def save(self, **kwargs: Any) -> OidcApplication:
        """Save changes to resource.

        Args:
            **kwargs: Fields to update.

        Returns:
            Updated OidcApplication object.
        """
        from typing import cast

        manager = cast("OidcApplicationManager", self._manager)
        return manager.update(self.key, **kwargs)

    def delete(self) -> None:
        """Delete this OIDC application."""
        from typing import cast

        manager = cast("OidcApplicationManager", self._manager)
        manager.delete(self.key)


class OidcApplicationManager(ResourceManager["OidcApplication"]):
    """Manager for OIDC application operations.

    OIDC applications enable VergeOS to act as an identity provider.

    Example:
        >>> # List all OIDC applications
        >>> for app in client.oidc_applications.list():
        ...     print(f"{app.name}: {app.client_id}")

        >>> # Get a specific application
        >>> app = client.oidc_applications.get(name="Tenant Portal")

        >>> # Create an application
        >>> app = client.oidc_applications.create(
        ...     name="Partner Portal",
        ...     redirect_uri="https://partner.example.com/callback",
        ...     description="OIDC for partner authentication",
        ... )
        >>> print(f"Client ID: {app.client_id}")
        >>> print(f"Client Secret: {app.client_secret}")

        >>> # Restrict access to specific users
        >>> app = client.oidc_applications.update(app.key, restrict_access=True)
        >>> app.allowed_users.add(user_key=123)

        >>> # Delete an application
        >>> client.oidc_applications.delete(app.key)
    """

    _endpoint = "oidc_applications"

    _default_fields = [
        "$key",
        "name",
        "enabled",
        "created",
        "description",
        "redirect_uri",
        "client_id",
        "force_auth_source",
        "restrict_access",
        "map_user",
        "scope_profile",
        "scope_email",
        "scope_groups",
    ]

    def __init__(self, client: VergeClient) -> None:
        super().__init__(client)

    def list(  # noqa: A003
        self,
        filter: str | None = None,  # noqa: A002
        fields: builtins.list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        enabled: bool | None = None,
        **filter_kwargs: Any,
    ) -> builtins.list[OidcApplication]:
        """List OIDC applications with optional filtering.

        Args:
            filter: OData filter string.
            fields: List of fields to return (uses defaults if not specified).
            limit: Maximum number of results.
            offset: Skip this many results.
            enabled: Filter by enabled state.
            **filter_kwargs: Shorthand filter arguments (name, etc.).

        Returns:
            List of OidcApplication objects.

        Example:
            >>> # List all applications
            >>> apps = client.oidc_applications.list()

            >>> # List enabled applications only
            >>> apps = client.oidc_applications.list(enabled=True)

            >>> # Filter by name pattern
            >>> apps = client.oidc_applications.list(name="Tenant*")
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
        include_secret: bool = False,
        include_well_known: bool = False,
    ) -> OidcApplication:
        """Get a single OIDC application by key or name.

        Args:
            key: Application $key (row ID).
            name: Application name.
            fields: List of fields to return.
            include_secret: Include client_secret in response.
            include_well_known: Include well_known_configuration in response.

        Returns:
            OidcApplication object.

        Raises:
            NotFoundError: If application not found.
            ValueError: If no identifier provided.

        Example:
            >>> # Get by key
            >>> app = client.oidc_applications.get(1)

            >>> # Get by name with secret
            >>> app = client.oidc_applications.get(
            ...     name="Tenant Portal",
            ...     include_secret=True
            ... )
            >>> print(app.client_secret)
        """
        # Determine which fields to request
        request_fields = list(fields) if fields else list(self._default_fields)
        if include_secret and "client_secret" not in request_fields:
            request_fields.append("client_secret")
        if include_well_known and "well_known_configuration" not in request_fields:
            request_fields.append("well_known_configuration")

        if key is not None:
            params: dict[str, Any] = {
                "fields": ",".join(request_fields),
            }

            response = self._client._request("GET", f"{self._endpoint}/{key}", params=params)
            if response is None:
                raise NotFoundError(f"OIDC application with key {key} not found")
            if not isinstance(response, dict):
                raise NotFoundError(f"OIDC application with key {key} returned invalid response")
            return self._to_model(response)

        if name is not None:
            escaped_name = name.replace("'", "''")
            results = self.list(filter=f"name eq '{escaped_name}'", fields=request_fields, limit=1)
            if not results:
                raise NotFoundError(f"OIDC application with name '{name}' not found")
            return results[0]

        raise ValueError("Either key or name must be provided")

    def create(  # type: ignore[override]
        self,
        name: str,
        *,
        redirect_uri: str | builtins.list[str] | None = None,
        description: str | None = None,
        enabled: bool = True,
        force_auth_source: int | None = None,
        restrict_access: bool = False,
        map_user: int | None = None,
        scope_profile: bool = True,
        scope_email: bool = True,
        scope_groups: bool = True,
    ) -> OidcApplication:
        """Create a new OIDC application.

        The client_id and client_secret are auto-generated and returned
        in the created object.

        Args:
            name: Application name.
            redirect_uri: Allowed redirect URIs (string or list of strings).
                Wildcards supported (e.g., ``https://*.example.com``).
            description: Application description.
            enabled: Whether the application is enabled.
            force_auth_source: Auth source key for auto-redirect.
            restrict_access: Restrict access to specific users/groups.
            map_user: User key to map all logins to.
            scope_profile: Grant profile scope (read user name).
            scope_email: Grant email scope (read user email).
            scope_groups: Grant groups scope (read group membership).

        Returns:
            Created OidcApplication object with client credentials.

        Example:
            >>> app = client.oidc_applications.create(
            ...     name="Partner Portal",
            ...     redirect_uri=[
            ...         "https://portal.example.com/callback",
            ...         "https://staging.example.com/callback",
            ...     ],
            ...     description="OIDC for partner authentication",
            ... )
            >>> print(f"Client ID: {app.client_id}")
            >>> print(f"Client Secret: {app.client_secret}")
        """
        body: dict[str, Any] = {
            "name": name,
            "enabled": enabled,
            "scope_profile": scope_profile,
            "scope_email": scope_email,
            "scope_groups": scope_groups,
        }

        # Handle redirect URIs
        if redirect_uri is not None:
            if isinstance(redirect_uri, list):
                body["redirect_uri"] = "\n".join(redirect_uri)
            else:
                body["redirect_uri"] = redirect_uri

        if description is not None:
            body["description"] = description

        body["force_auth_source"] = force_auth_source if force_auth_source is not None else 0

        if restrict_access:
            body["restrict_access"] = restrict_access

        body["map_user"] = map_user if map_user is not None else 0

        response = self._client._request("POST", self._endpoint, json_data=body)

        # Get the created application with secret
        if response and isinstance(response, dict):
            app_key = response.get("$key")
            if app_key:
                return self.get(key=int(app_key), include_secret=True, include_well_known=True)

        # Fallback: search by name (with secret)
        return self.get(name=name, include_secret=True, include_well_known=True)

    def update(  # type: ignore[override]
        self,
        key: int,
        *,
        name: str | None = None,
        redirect_uri: str | builtins.list[str] | None = None,
        description: str | None = None,
        enabled: bool | None = None,
        force_auth_source: int | None = None,
        restrict_access: bool | None = None,
        map_user: int | None = None,
        scope_profile: bool | None = None,
        scope_email: bool | None = None,
        scope_groups: bool | None = None,
    ) -> OidcApplication:
        """Update an OIDC application.

        Note: client_id and client_secret cannot be changed.

        Args:
            key: Application $key (row ID).
            name: New application name.
            redirect_uri: Updated redirect URIs.
            description: New description.
            enabled: Enable or disable.
            force_auth_source: Auth source for auto-redirect.
            restrict_access: Restrict to specific users/groups.
            map_user: User to map all logins to.
            scope_profile: Grant profile scope.
            scope_email: Grant email scope.
            scope_groups: Grant groups scope.

        Returns:
            Updated OidcApplication object.

        Example:
            >>> # Update redirect URIs
            >>> app = client.oidc_applications.update(
            ...     app.key,
            ...     redirect_uri="https://new.example.com/callback"
            ... )

            >>> # Enable access restriction
            >>> app = client.oidc_applications.update(
            ...     app.key,
            ...     restrict_access=True
            ... )
        """
        body: dict[str, Any] = {}

        if name is not None:
            body["name"] = name

        if redirect_uri is not None:
            if isinstance(redirect_uri, list):
                body["redirect_uri"] = "\n".join(redirect_uri)
            else:
                body["redirect_uri"] = redirect_uri

        if description is not None:
            body["description"] = description

        if enabled is not None:
            body["enabled"] = enabled

        if force_auth_source is not None:
            body["force_auth_source"] = force_auth_source

        if restrict_access is not None:
            body["restrict_access"] = restrict_access

        if map_user is not None:
            body["map_user"] = map_user

        if scope_profile is not None:
            body["scope_profile"] = scope_profile

        if scope_email is not None:
            body["scope_email"] = scope_email

        if scope_groups is not None:
            body["scope_groups"] = scope_groups

        if not body:
            return self.get(key)

        self._client._request("PUT", f"{self._endpoint}/{key}", json_data=body)
        return self.get(key)

    def delete(self, key: int) -> None:
        """Delete an OIDC application.

        Args:
            key: Application $key (row ID).

        Raises:
            NotFoundError: If application not found.

        Example:
            >>> client.oidc_applications.delete(app.key)
        """
        self._client._request("DELETE", f"{self._endpoint}/{key}")

    def allowed_users(self, key: int) -> OidcApplicationUserManager:
        """Get a user ACL manager scoped to a specific application.

        Args:
            key: Application $key (row ID).

        Returns:
            OidcApplicationUserManager for the application.
        """
        return OidcApplicationUserManager(self._client, application_key=key)

    def allowed_groups(self, key: int) -> OidcApplicationGroupManager:
        """Get a group ACL manager scoped to a specific application.

        Args:
            key: Application $key (row ID).

        Returns:
            OidcApplicationGroupManager for the application.
        """
        return OidcApplicationGroupManager(self._client, application_key=key)

    def logs(self, key: int) -> OidcApplicationLogManager:
        """Get a log manager scoped to a specific application.

        Args:
            key: Application $key (row ID).

        Returns:
            OidcApplicationLogManager for the application.
        """
        return OidcApplicationLogManager(self._client, application_key=key)

    def _to_model(self, data: dict[str, Any]) -> OidcApplication:
        """Convert API response to OidcApplication object."""
        return OidcApplication(data, self)
