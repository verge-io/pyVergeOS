"""API Key resource manager for VergeOS user API keys."""

from __future__ import annotations

import builtins
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any

from pyvergeos.exceptions import NotFoundError
from pyvergeos.filters import build_filter
from pyvergeos.resources.base import ResourceManager, ResourceObject

if TYPE_CHECKING:
    from pyvergeos.client import VergeClient


class APIKeyCreated:
    """Response from creating an API key containing the secret.

    The secret is only available once at creation time and cannot
    be retrieved later.

    Attributes:
        key: The API key ID ($key).
        name: The API key name.
        user_key: The user's $key.
        user_name: The username.
        secret: The API key secret (only shown once).
    """

    def __init__(
        self,
        key: int,
        name: str,
        user_key: int,
        user_name: str | None,
        secret: str,
    ) -> None:
        self.key = key
        self.name = name
        self.user_key = user_key
        self.user_name = user_name
        self.secret = secret

    def __repr__(self) -> str:
        return (
            f"APIKeyCreated(key={self.key}, name={self.name!r}, "
            f"user_name={self.user_name!r}, secret=***)"
        )


class APIKey(ResourceObject):
    """API Key resource object.

    Represents an API key associated with a user account.

    Attributes:
        key: API key primary key ($key).
        name: API key name.
        description: API key description.
        user_key: The user's $key this key belongs to.
        user_name: The username this key belongs to.
        created: Creation timestamp (Unix epoch).
        expires: Expiration timestamp (Unix epoch), or None if never expires.
        last_login: Last login timestamp (Unix epoch).
        last_login_ip: IP address of last login.
        ip_allow_list: List of allowed IP addresses/CIDR ranges.
        ip_deny_list: List of denied IP addresses/CIDR ranges.
    """

    @property
    def description(self) -> str | None:
        """Get the API key description."""
        return self.get("description")

    @property
    def user_key(self) -> int:
        """Get the user $key this key belongs to."""
        return int(self.get("user", 0))

    @property
    def user_name(self) -> str | None:
        """Get the username this key belongs to."""
        return self.get("user_name")

    @property
    def created(self) -> int | None:
        """Get the creation timestamp (Unix epoch)."""
        val = self.get("created")
        return int(val) if val is not None else None

    @property
    def created_datetime(self) -> datetime | None:
        """Get the creation time as a datetime object."""
        if self.created:
            return datetime.fromtimestamp(self.created, tz=timezone.utc)
        return None

    @property
    def expires(self) -> int | None:
        """Get the expiration timestamp (Unix epoch), or None if never expires."""
        val = self.get("expires")
        return int(val) if val and val > 0 else None

    @property
    def expires_datetime(self) -> datetime | None:
        """Get the expiration time as a datetime object."""
        if self.expires:
            return datetime.fromtimestamp(self.expires, tz=timezone.utc)
        return None

    @property
    def is_expired(self) -> bool:
        """Check if the API key has expired."""
        if self.expires is None:
            return False
        now = datetime.now(tz=timezone.utc)
        expires_dt = self.expires_datetime
        return expires_dt is not None and expires_dt < now

    @property
    def last_login(self) -> int | None:
        """Get the last login timestamp (Unix epoch)."""
        val = self.get("lastlogin_stamp")
        return int(val) if val and val > 0 else None

    @property
    def last_login_datetime(self) -> datetime | None:
        """Get the last login time as a datetime object."""
        if self.last_login:
            return datetime.fromtimestamp(self.last_login, tz=timezone.utc)
        return None

    @property
    def last_login_ip(self) -> str | None:
        """Get the IP address of the last login."""
        return self.get("lastlogin_ip")

    @property
    def ip_allow_list(self) -> builtins.list[str]:
        """Get the list of allowed IP addresses/CIDR ranges."""
        val = self.get("ip_allow_list")
        if val:
            return [ip.strip() for ip in val.split(",") if ip.strip()]
        return []

    @property
    def ip_deny_list(self) -> builtins.list[str]:
        """Get the list of denied IP addresses/CIDR ranges."""
        val = self.get("ip_deny_list")
        if val:
            return [ip.strip() for ip in val.split(",") if ip.strip()]
        return []

    def delete(self) -> None:
        """Delete this API key.

        Example:
            >>> api_key.delete()
        """
        from typing import cast

        manager = cast("APIKeyManager", self._manager)
        manager.delete(self.key)


class APIKeyManager(ResourceManager[APIKey]):
    """Manager for VergeOS API key operations.

    Provides CRUD operations for user API keys.

    Example:
        >>> # List all API keys
        >>> for key in client.api_keys.list():
        ...     print(f"{key.name}: user={key.user_name}")

        >>> # List API keys for a specific user
        >>> user_keys = client.api_keys.list(user=123)

        >>> # Create an API key
        >>> result = client.api_keys.create(
        ...     user=123,
        ...     name="automation-key",
        ...     description="CI/CD automation"
        ... )
        >>> print(f"Secret: {result.secret}")  # Only shown once!

        >>> # Delete an API key
        >>> client.api_keys.delete(key_id)
    """

    _endpoint = "user_api_keys"

    # Default fields for list operations (matches PowerShell module)
    _default_fields = [
        "$key",
        "user",
        "user#name as user_name",
        "name",
        "description",
        "created",
        "expires",
        "lastlogin_stamp",
        "lastlogin_ip",
        "ip_allow_list",
        "ip_deny_list",
    ]

    def __init__(self, client: VergeClient) -> None:
        super().__init__(client)

    def _to_model(self, data: dict[str, Any]) -> APIKey:
        """Convert API response to APIKey object."""
        return APIKey(data, self)

    def list(
        self,
        filter: str | None = None,
        fields: builtins.list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        user: int | str | None = None,
        **filter_kwargs: Any,
    ) -> builtins.list[APIKey]:
        """List API keys with optional filtering.

        Args:
            filter: OData filter string.
            fields: List of fields to return (uses defaults if not specified).
            limit: Maximum number of results.
            offset: Skip this many results.
            user: Filter by user - can be user $key (int) or username (str).
            **filter_kwargs: Shorthand filter arguments (name, etc.).

        Returns:
            List of APIKey objects.

        Example:
            >>> # List all API keys
            >>> keys = client.api_keys.list()

            >>> # List keys for a specific user by key
            >>> keys = client.api_keys.list(user=123)

            >>> # List keys for a specific user by name
            >>> keys = client.api_keys.list(user="admin")

            >>> # List by name
            >>> keys = client.api_keys.list(name="automation")
        """
        params: dict[str, Any] = {}

        # Build filter
        filters: builtins.list[str] = []

        if filter:
            filters.append(filter)
        if filter_kwargs:
            filters.append(build_filter(**filter_kwargs))

        # Handle user filter
        if user is not None:
            user_key = self._resolve_user_key(user)
            if user_key is not None:
                filters.append(f"user eq {user_key}")

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
        user: int | str | None = None,
        fields: builtins.list[str] | None = None,
    ) -> APIKey:
        """Get a single API key by key or name.

        Args:
            key: API key $key (ID).
            name: API key name (requires user parameter).
            user: User $key or username (required when looking up by name).
            fields: List of fields to return.

        Returns:
            APIKey object.

        Raises:
            NotFoundError: If API key not found.
            ValueError: If neither key nor name provided, or name without user.

        Example:
            >>> # Get by key
            >>> api_key = client.api_keys.get(5)

            >>> # Get by name for a user
            >>> api_key = client.api_keys.get(name="automation", user="admin")
        """
        if key is not None:
            # Direct fetch by key
            params: dict[str, Any] = {}
            if fields:
                params["fields"] = ",".join(fields)
            else:
                params["fields"] = ",".join(self._default_fields)

            response = self._client._request("GET", f"{self._endpoint}/{key}", params=params)
            if response is None:
                raise NotFoundError(f"API key with key {key} not found")
            if not isinstance(response, dict):
                raise NotFoundError(f"API key with key {key} returned invalid response")
            return self._to_model(response)

        if name is not None:
            if user is None:
                raise ValueError("user parameter is required when looking up by name")

            # Search by name and user
            user_key = self._resolve_user_key(user)
            if user_key is None:
                raise NotFoundError(f"User '{user}' not found")

            escaped_name = name.replace("'", "''")
            results = self.list(
                filter=f"name eq '{escaped_name}' and user eq {user_key}",
                fields=fields,
                limit=1,
            )
            if not results:
                raise NotFoundError(f"API key '{name}' not found for user")
            return results[0]

        raise ValueError("Either key or name (with user) must be provided")

    def create(  # type: ignore[override]
        self,
        user: int | str,
        name: str,
        *,
        description: str | None = None,
        expires_in: str | None = None,
        expires: datetime | None = None,
        ip_allow_list: builtins.list[str] | None = None,
        ip_deny_list: builtins.list[str] | None = None,
    ) -> APIKeyCreated:
        """Create a new API key.

        IMPORTANT: The API key secret is only returned once at creation time.
        Store it securely as it cannot be retrieved later.

        Args:
            user: User $key (int) or username (str) to create the key for.
            name: Name for the API key (1-128 chars, unique per user).
            description: Optional description for the API key.
            expires_in: Duration until expiration ('30d', '1w', '3m', '1y', or 'never').
                        Supported units: d (days), w (weeks), m (months), y (years).
                        Default is 'never' (no expiration).
            expires: Specific datetime when the key should expire.
            ip_allow_list: List of IP addresses or CIDR ranges allowed to use this key.
            ip_deny_list: List of IP addresses or CIDR ranges denied from using this key.

        Returns:
            APIKeyCreated object containing the key ID and secret.

        Raises:
            NotFoundError: If user not found.
            ValueError: If invalid expires_in format.

        Example:
            >>> # Create a basic API key
            >>> result = client.api_keys.create(
            ...     user="admin",
            ...     name="automation-key"
            ... )
            >>> print(f"Secret: {result.secret}")  # Store this!

            >>> # Create with expiration
            >>> result = client.api_keys.create(
            ...     user=123,
            ...     name="temp-key",
            ...     expires_in="90d",
            ...     description="Temporary CI/CD key"
            ... )

            >>> # Create with IP restrictions
            >>> result = client.api_keys.create(
            ...     user="apiuser",
            ...     name="restricted-key",
            ...     ip_allow_list=["10.0.0.0/8", "192.168.1.100"]
            ... )
        """
        # Resolve user key
        user_key = self._resolve_user_key(user)
        if user_key is None:
            raise NotFoundError(f"User '{user}' not found")

        # Get username for response
        user_name = self._get_user_name(user_key)

        # Build request body
        body: dict[str, Any] = {
            "user": user_key,
            "name": name,
        }

        if description:
            body["description"] = description

        # Handle expiration
        if expires is not None:
            body["expires"] = int(expires.timestamp())
            body["expires_type"] = "date"
        elif expires_in is not None and expires_in.lower() != "never":
            expiration_ts = self._parse_expires_in(expires_in)
            if expiration_ts:
                body["expires"] = expiration_ts
                body["expires_type"] = "date"
        else:
            body["expires_type"] = "never"

        # IP lists
        if ip_allow_list:
            body["ip_allow_list"] = ",".join(ip_allow_list)

        if ip_deny_list:
            body["ip_deny_list"] = ",".join(ip_deny_list)

        response = self._client._request("POST", self._endpoint, json_data=body)

        if response and isinstance(response, dict):
            api_key_id = response.get("$key")
            # The secret is in response.private_key
            inner_response = response.get("response", {})
            secret = inner_response.get("private_key", "")

            return APIKeyCreated(
                key=int(api_key_id) if api_key_id else 0,
                name=name,
                user_key=user_key,
                user_name=user_name,
                secret=secret,
            )

        raise RuntimeError("Failed to create API key: unexpected response")

    def delete(self, key: int) -> None:
        """Delete an API key.

        This action is permanent and the key will no longer be usable.

        Args:
            key: API key $key (ID) to delete.

        Example:
            >>> client.api_keys.delete(5)
        """
        self._client._request("DELETE", f"{self._endpoint}/{key}")

    def _resolve_user_key(self, user: int | str) -> int | None:
        """Resolve a user identifier to a user $key.

        Args:
            user: User $key (int) or username (str).

        Returns:
            User $key, or None if not found.
        """
        if isinstance(user, int):
            return user

        # Look up user by name
        try:
            user_obj = self._client.users.get(name=str(user))
            return user_obj.key
        except NotFoundError:
            return None

    def _get_user_name(self, user_key: int) -> str | None:
        """Get a username by user key.

        Args:
            user_key: User $key.

        Returns:
            Username, or None if not found.
        """
        try:
            user_obj = self._client.users.get(key=user_key)
            name = user_obj.name
            return str(name) if name is not None else None
        except NotFoundError:
            return None

    def _parse_expires_in(self, expires_in: str) -> int | None:
        """Parse an expires_in duration string to a Unix timestamp.

        Args:
            expires_in: Duration string like '30d', '1w', '3m', '1y'.

        Returns:
            Unix timestamp, or None if invalid.
        """
        import re

        match = re.match(r"^(\d+)([dwmy])$", expires_in.lower())
        if not match:
            return None

        value = int(match.group(1))
        unit = match.group(2)

        now = datetime.now(tz=timezone.utc)

        if unit == "d":
            expiration = now + timedelta(days=value)
        elif unit == "w":
            expiration = now + timedelta(weeks=value)
        elif unit == "m":
            # Approximate months as 30 days
            expiration = now + timedelta(days=value * 30)
        elif unit == "y":
            # Approximate years as 365 days
            expiration = now + timedelta(days=value * 365)
        else:
            return None

        return int(expiration.timestamp())
