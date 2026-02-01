"""Authentication source management for external identity providers.

Authentication sources enable SSO and federated login via OAuth2/OIDC providers
such as Azure AD, Google, GitLab, Okta, and generic OpenID Connect.

Key concepts:
    - **Auth Source**: Configuration for an external identity provider
    - **Driver**: The type of provider (azure, google, gitlab, okta, openid, etc.)
    - **Settings**: Driver-specific configuration stored as JSON
    - **States**: Ephemeral OAuth state tokens during authentication flow

Supported drivers:
    - azure: Azure Active Directory
    - google: Google OAuth
    - gitlab: GitLab (OpenID)
    - okta: Okta
    - openid: Generic OpenID Connect
    - openid-well-known: OpenID with well-known configuration discovery
    - oauth2: Generic OAuth2
    - verge.io: Verge.io parent system authentication

Example:
    >>> # List all authentication sources
    >>> for source in client.auth_sources.list():
    ...     print(f"{source.name} ({source.driver})")

    >>> # Get a specific auth source
    >>> azure = client.auth_sources.get(name="Azure AD")

    >>> # Create an Azure AD auth source
    >>> source = client.auth_sources.create(
    ...     name="Corporate Azure",
    ...     driver="azure",
    ...     settings={
    ...         "tenant_id": "your-tenant-id",
    ...         "client_id": "your-client-id",
    ...         "client_secret": "your-client-secret",
    ...         "scope": "openid profile email",
    ...     }
    ... )

    >>> # Enable debug mode for troubleshooting
    >>> source.enable_debug()

    >>> # List users using this auth source
    >>> for user in client.users.list(auth_source=source.key):
    ...     print(f"  {user.name}")
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
# Auth Source State (OAuth State Tokens)
# =============================================================================


class AuthSourceState(ResourceObject):
    """OAuth state token for authentication flow.

    Auth source states are ephemeral tokens created during the OAuth
    authentication flow. They expire after 15 minutes.

    Attributes:
        key: State key (40-character hex string).
        auth_source: Parent auth source key.
        meta: State metadata (JSON).
        timestamp: Creation timestamp (microseconds).
    """

    @property
    def key(self) -> str:  # type: ignore[override]
        """State key (40-character hex string).

        Raises:
            ValueError: If state has no key.
        """
        state = self.get("state")
        if state is None:
            state = self.get("$key")
        if state is None:
            raise ValueError("State has no key")
        return str(state)

    @property
    def auth_source_key(self) -> int | None:
        """Get the parent auth source key."""
        source = self.get("auth_source")
        return int(source) if source is not None else None

    @property
    def is_expired(self) -> bool:
        """Check if state has expired (>15 minutes old).

        States expire 15 minutes (900 seconds) after creation.
        """
        import time

        timestamp = self.get("timestamp", 0)
        if not timestamp:
            return True
        # timestamp is in microseconds, convert to seconds
        created_at = int(timestamp) / 1_000_000
        return bool(time.time() - created_at > 900)


class AuthSourceStateManager(ResourceManager["AuthSourceState"]):
    """Manager for authentication source state operations.

    States are read-only and automatically created/deleted during OAuth flow.

    Example:
        >>> # List states for an auth source
        >>> for state in client.auth_source_states.list(auth_source=1):
        ...     print(f"{state.key}: expired={state.is_expired}")
    """

    _endpoint = "auth_source_states"

    _default_fields = [
        "$key",
        "state",
        "auth_source",
        "meta",
        "timestamp",
    ]

    def __init__(self, client: VergeClient, *, auth_source_key: int | None = None) -> None:
        super().__init__(client)
        self._auth_source_key = auth_source_key

    def list(  # noqa: A003
        self,
        filter: str | None = None,  # noqa: A002
        fields: builtins.list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        auth_source: int | None = None,
        **filter_kwargs: Any,
    ) -> builtins.list[AuthSourceState]:
        """List auth source states with optional filtering.

        Args:
            filter: OData filter string.
            fields: List of fields to return (uses defaults if not specified).
            limit: Maximum number of results.
            offset: Skip this many results.
            auth_source: Filter by auth source key. Ignored if manager is scoped.
            **filter_kwargs: Shorthand filter arguments.

        Returns:
            List of AuthSourceState objects.
        """
        params: dict[str, Any] = {}

        # Build filter
        filters: builtins.list[str] = []
        if filter:
            filters.append(filter)
        if filter_kwargs:
            filters.append(build_filter(**filter_kwargs))

        # Add auth_source filter (from scope or parameter)
        source_key = self._auth_source_key
        if source_key is None and auth_source is not None:
            source_key = auth_source

        if source_key is not None:
            filters.append(f"auth_source eq {source_key}")

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
        key: str | None = None,
        *,
        fields: builtins.list[str] | None = None,
    ) -> AuthSourceState:
        """Get a single state by key.

        Args:
            key: State key (40-character hex string).
            fields: List of fields to return.

        Returns:
            AuthSourceState object.

        Raises:
            NotFoundError: If state not found.
            ValueError: If key not provided.
        """
        if key is None:
            raise ValueError("Key must be provided")

        params: dict[str, Any] = {
            "filter": f"state eq '{key}'",
        }
        if fields:
            params["fields"] = ",".join(fields)
        else:
            params["fields"] = ",".join(self._default_fields)

        response = self._client._request("GET", self._endpoint, params=params)

        if response is None:
            raise NotFoundError(f"Auth source state with key {key} not found")
        if isinstance(response, list):
            if not response:
                raise NotFoundError(f"Auth source state with key {key} not found")
            response = response[0]
        if not isinstance(response, dict):
            raise NotFoundError(f"Auth source state with key {key} returned invalid response")
        return self._to_model(response)

    def _to_model(self, data: dict[str, Any]) -> AuthSourceState:
        """Convert API response to AuthSourceState object."""
        return AuthSourceState(data, self)


# =============================================================================
# Auth Source
# =============================================================================


class AuthSource(ResourceObject):
    """Authentication source resource object.

    Represents an external identity provider configuration.

    Attributes:
        key: Auth source $key (row ID).
        name: Display name shown on login button.
        driver: Provider type (azure, google, gitlab, okta, openid, etc.).
        settings: Driver-specific configuration (JSON).
        menu: Whether to show in dropdown menu.
        debug: Debug logging enabled.
        debug_ts: Debug mode timestamp.
        button_background_color: Login button background color (CSS).
        button_color: Login button text color (CSS).
        button_fa_icon: Login button Font Awesome icon class.
        icon_color: Login button icon color (CSS).
    """

    @property
    def driver(self) -> str:
        """Get the auth provider driver type."""
        return str(self.get("driver", ""))

    @property
    def is_azure(self) -> bool:
        """Check if this is an Azure AD source."""
        return self.driver == "azure"

    @property
    def is_google(self) -> bool:
        """Check if this is a Google source."""
        return self.driver == "google"

    @property
    def is_gitlab(self) -> bool:
        """Check if this is a GitLab source."""
        return self.driver == "gitlab"

    @property
    def is_okta(self) -> bool:
        """Check if this is an Okta source."""
        return self.driver == "okta"

    @property
    def is_openid(self) -> bool:
        """Check if this is an OpenID source (any variant)."""
        driver = self.driver
        return driver in ("openid", "openid-well-known")

    @property
    def is_oauth2(self) -> bool:
        """Check if this is a generic OAuth2 source."""
        return self.driver == "oauth2"

    @property
    def is_vergeos(self) -> bool:
        """Check if this is a Verge.io parent source."""
        return self.driver == "verge.io"

    @property
    def settings(self) -> dict[str, Any]:
        """Get driver-specific settings.

        Settings vary by driver but commonly include:
        - client_id: OAuth client ID
        - client_secret: OAuth client secret
        - tenant_id: Azure tenant ID (Azure only)
        - scope: OAuth scopes to request
        - redirect_uri: OAuth redirect URI
        - remote_user_fields: Fields to match users
        """
        settings = self.get("settings")
        if isinstance(settings, dict):
            return settings
        return {}

    @property
    def is_debug_enabled(self) -> bool:
        """Check if debug logging is enabled."""
        return bool(self.get("debug", False))

    @property
    def is_menu(self) -> bool:
        """Check if shown in dropdown menu."""
        return bool(self.get("menu", False))

    @property
    def button_style(self) -> dict[str, str | None]:
        """Get login button styling properties.

        Returns:
            Dict with background_color, text_color, icon, icon_color.
        """
        return {
            "background_color": self.get("button_background_color"),
            "text_color": self.get("button_color"),
            "icon": self.get("button_fa_icon"),
            "icon_color": self.get("icon_color"),
        }

    @property
    def states(self) -> AuthSourceStateManager:
        """Get a state manager scoped to this auth source.

        Returns:
            AuthSourceStateManager for this auth source.
        """
        from typing import cast

        manager = cast("AuthSourceManager", self._manager)
        return AuthSourceStateManager(manager._client, auth_source_key=self.key)

    def enable_debug(self) -> AuthSource:
        """Enable debug logging for this auth source.

        Debug mode automatically disables after 1 hour.

        Returns:
            Updated AuthSource object.
        """
        from typing import cast

        manager = cast("AuthSourceManager", self._manager)
        return manager.update(self.key, debug=True)

    def disable_debug(self) -> AuthSource:
        """Disable debug logging for this auth source.

        Returns:
            Updated AuthSource object.
        """
        from typing import cast

        manager = cast("AuthSourceManager", self._manager)
        return manager.update(self.key, debug=False)

    def refresh(self) -> AuthSource:
        """Refresh resource data from API.

        Returns:
            Updated AuthSource object.
        """
        from typing import cast

        manager = cast("AuthSourceManager", self._manager)
        return manager.get(self.key)

    def save(self, **kwargs: Any) -> AuthSource:
        """Save changes to resource.

        Args:
            **kwargs: Fields to update.

        Returns:
            Updated AuthSource object.
        """
        from typing import cast

        manager = cast("AuthSourceManager", self._manager)
        return manager.update(self.key, **kwargs)

    def delete(self) -> None:
        """Delete this auth source.

        This will fail if users or OIDC applications are using this source.
        """
        from typing import cast

        manager = cast("AuthSourceManager", self._manager)
        manager.delete(self.key)


class AuthSourceManager(ResourceManager["AuthSource"]):
    """Manager for authentication source operations.

    Authentication sources enable SSO via external identity providers.

    Example:
        >>> # List all auth sources
        >>> for source in client.auth_sources.list():
        ...     print(f"{source.name} ({source.driver})")

        >>> # Get a specific source
        >>> source = client.auth_sources.get(name="Azure AD")

        >>> # Create an auth source
        >>> source = client.auth_sources.create(
        ...     name="Google",
        ...     driver="google",
        ...     settings={
        ...         "client_id": "your-client-id",
        ...         "client_secret": "your-secret",
        ...     }
        ... )

        >>> # Update settings
        >>> source = client.auth_sources.update(
        ...     source.key,
        ...     settings={"scope": "openid profile email groups"}
        ... )

        >>> # Delete an auth source
        >>> client.auth_sources.delete(source.key)
    """

    _endpoint = "auth_sources"

    _default_fields = [
        "$key",
        "name",
        "driver",
        "menu",
        "debug",
        "debug_ts",
        "button_background_color",
        "button_color",
        "button_fa_icon",
        "icon_color",
    ]

    def __init__(self, client: VergeClient) -> None:
        super().__init__(client)

    def list(  # noqa: A003
        self,
        filter: str | None = None,  # noqa: A002
        fields: builtins.list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        driver: str | None = None,
        **filter_kwargs: Any,
    ) -> builtins.list[AuthSource]:
        """List auth sources with optional filtering.

        Args:
            filter: OData filter string.
            fields: List of fields to return (uses defaults if not specified).
            limit: Maximum number of results.
            offset: Skip this many results.
            driver: Filter by driver type (azure, google, gitlab, etc.).
            **filter_kwargs: Shorthand filter arguments (name, etc.).

        Returns:
            List of AuthSource objects.

        Example:
            >>> # List all sources
            >>> sources = client.auth_sources.list()

            >>> # List Azure sources only
            >>> sources = client.auth_sources.list(driver="azure")

            >>> # Filter by name pattern
            >>> sources = client.auth_sources.list(name="Corporate*")
        """
        params: dict[str, Any] = {}

        # Build filter
        filters: builtins.list[str] = []
        if filter:
            filters.append(filter)
        if filter_kwargs:
            filters.append(build_filter(**filter_kwargs))

        # Add driver filter
        if driver is not None:
            filters.append(f"driver eq '{driver}'")

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
        include_settings: bool = False,
    ) -> AuthSource:
        """Get a single auth source by key or name.

        Args:
            key: Auth source $key (row ID).
            name: Auth source name.
            fields: List of fields to return.
            include_settings: Include settings JSON in response.

        Returns:
            AuthSource object.

        Raises:
            NotFoundError: If source not found.
            ValueError: If no identifier provided.

        Example:
            >>> # Get by key
            >>> source = client.auth_sources.get(1)

            >>> # Get by name
            >>> source = client.auth_sources.get(name="Azure AD")

            >>> # Include settings
            >>> source = client.auth_sources.get(1, include_settings=True)
            >>> print(source.settings)
        """
        # Determine which fields to request
        request_fields = list(fields) if fields else list(self._default_fields)
        if include_settings and "settings" not in request_fields:
            request_fields.append("settings")

        if key is not None:
            params: dict[str, Any] = {
                "fields": ",".join(request_fields),
            }

            response = self._client._request("GET", f"{self._endpoint}/{key}", params=params)
            if response is None:
                raise NotFoundError(f"Auth source with key {key} not found")
            if not isinstance(response, dict):
                raise NotFoundError(f"Auth source with key {key} returned invalid response")
            return self._to_model(response)

        if name is not None:
            escaped_name = name.replace("'", "''")
            results = self.list(filter=f"name eq '{escaped_name}'", fields=request_fields, limit=1)
            if not results:
                raise NotFoundError(f"Auth source with name '{name}' not found")
            return results[0]

        raise ValueError("Either key or name must be provided")

    def create(  # type: ignore[override]
        self,
        name: str,
        *,
        driver: str,
        settings: dict[str, Any] | None = None,
        menu: bool = False,
        button_background_color: str | None = None,
        button_color: str | None = None,
        button_fa_icon: str | None = None,
        icon_color: str | None = None,
    ) -> AuthSource:
        """Create a new authentication source.

        Args:
            name: Display name for the auth source (appears on login button).
            driver: Provider type. One of:
                - azure: Azure Active Directory
                - google: Google OAuth
                - gitlab: GitLab (OpenID)
                - okta: Okta
                - openid: Generic OpenID Connect
                - openid-well-known: OpenID with well-known discovery
                - oauth2: Generic OAuth2
                - verge.io: Verge.io parent system
            settings: Driver-specific configuration. Common fields:
                - client_id: OAuth client ID
                - client_secret: OAuth client secret
                - tenant_id: Azure tenant ID (Azure only)
                - scope: OAuth scopes (default: "openid profile email")
                - remote_user_fields: Fields to match users
                - auto_create_users: Pattern for auto-creating users
                - update_remote_user: Update remote user ID after login
                - update_user_email: Update user email from provider
                - update_user_display_name: Update display name from provider
                - update_group_membership: Sync group membership
            menu: Show in dropdown menu instead of buttons.
            button_background_color: Button background color (CSS value).
            button_color: Button text color (CSS value).
            button_fa_icon: Button icon (Bootstrap Icon class, e.g. "bi-google").
            icon_color: Button icon color (CSS value).

        Returns:
            Created AuthSource object.

        Example:
            >>> # Create Azure AD source
            >>> source = client.auth_sources.create(
            ...     name="Corporate Azure",
            ...     driver="azure",
            ...     settings={
            ...         "tenant_id": "your-tenant-id",
            ...         "client_id": "your-client-id",
            ...         "client_secret": "your-client-secret",
            ...         "scope": "openid profile email",
            ...         "update_remote_user": True,
            ...         "update_user_email": True,
            ...     }
            ... )

            >>> # Create Google source with custom styling
            >>> source = client.auth_sources.create(
            ...     name="Sign in with Google",
            ...     driver="google",
            ...     settings={
            ...         "client_id": "your-client-id",
            ...         "client_secret": "your-secret",
            ...     },
            ...     button_background_color="#4285F4",
            ...     button_color="#ffffff",
            ...     button_fa_icon="bi-google",
            ... )
        """
        body: dict[str, Any] = {
            "name": name,
            "driver": driver,
        }

        if settings is not None:
            body["settings"] = settings

        if menu:
            body["menu"] = menu

        if button_background_color is not None:
            body["button_background_color"] = button_background_color

        if button_color is not None:
            body["button_color"] = button_color

        if button_fa_icon is not None:
            body["button_fa_icon"] = button_fa_icon

        if icon_color is not None:
            body["icon_color"] = icon_color

        response = self._client._request("POST", self._endpoint, json_data=body)

        # Get the created source
        if response and isinstance(response, dict):
            source_key = response.get("$key")
            if source_key:
                return self.get(key=int(source_key))

        # Fallback: search by name
        return self.get(name=name)

    def update(  # type: ignore[override]
        self,
        key: int,
        *,
        name: str | None = None,
        settings: dict[str, Any] | None = None,
        menu: bool | None = None,
        debug: bool | None = None,
        button_background_color: str | None = None,
        button_color: str | None = None,
        button_fa_icon: str | None = None,
        icon_color: str | None = None,
    ) -> AuthSource:
        """Update an authentication source.

        Note: The driver cannot be changed after creation.

        Args:
            key: Auth source $key (row ID).
            name: New display name.
            settings: Updated settings (merged with existing).
            menu: Show in dropdown menu.
            debug: Enable/disable debug logging.
            button_background_color: Button background color.
            button_color: Button text color.
            button_fa_icon: Button icon class.
            icon_color: Button icon color.

        Returns:
            Updated AuthSource object.

        Example:
            >>> # Update settings
            >>> source = client.auth_sources.update(
            ...     source.key,
            ...     settings={"scope": "openid profile email groups"}
            ... )

            >>> # Enable debug mode
            >>> source = client.auth_sources.update(source.key, debug=True)
        """
        body: dict[str, Any] = {}

        if name is not None:
            body["name"] = name

        if settings is not None:
            body["settings"] = settings

        if menu is not None:
            body["menu"] = menu

        if debug is not None:
            body["debug"] = debug

        if button_background_color is not None:
            body["button_background_color"] = button_background_color

        if button_color is not None:
            body["button_color"] = button_color

        if button_fa_icon is not None:
            body["button_fa_icon"] = button_fa_icon

        if icon_color is not None:
            body["icon_color"] = icon_color

        if not body:
            return self.get(key)

        self._client._request("PUT", f"{self._endpoint}/{key}", json_data=body)
        return self.get(key)

    def delete(self, key: int) -> None:
        """Delete an authentication source.

        This operation will fail if:
        - Users are assigned to this auth source
        - OIDC applications reference this auth source

        Args:
            key: Auth source $key (row ID).

        Raises:
            NotFoundError: If source not found.
            ConflictError: If source is in use by users or OIDC apps.

        Example:
            >>> client.auth_sources.delete(source.key)
        """
        self._client._request("DELETE", f"{self._endpoint}/{key}")

    def states(self, key: int) -> AuthSourceStateManager:
        """Get a state manager scoped to a specific auth source.

        Args:
            key: Auth source $key (row ID).

        Returns:
            AuthSourceStateManager for the auth source.
        """
        return AuthSourceStateManager(self._client, auth_source_key=key)

    def _to_model(self, data: dict[str, Any]) -> AuthSource:
        """Convert API response to AuthSource object."""
        return AuthSource(data, self)
