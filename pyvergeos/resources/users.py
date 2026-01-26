"""User resource manager for VergeOS system users."""

from __future__ import annotations

import builtins
from typing import TYPE_CHECKING, Any, Literal

from pyvergeos.exceptions import NotFoundError
from pyvergeos.filters import build_filter
from pyvergeos.resources.base import ResourceManager, ResourceObject

if TYPE_CHECKING:
    from pyvergeos.client import VergeClient

# Type aliases
UserType = Literal["normal", "api", "vdi"]
TwoFactorType = Literal["email", "authenticator"]


class User(ResourceObject):
    """User resource object.

    Represents a user account in VergeOS. Users can be normal users,
    API users, or VDI users.

    Attributes:
        key: User primary key ($key).
        name: Username (login name).
        displayname: Display name.
        email: Email address.
        user_type: User type ('normal', 'api', 'vdi').
        enabled: Whether the account is enabled.
        created: Creation timestamp (Unix epoch).
        last_login: Last login timestamp (Unix epoch).
        change_password: Whether password change is required on next login.
        physical_access: Whether console/SSH access is enabled (admin privilege).
        two_factor_enabled: Whether 2FA is enabled.
        two_factor_type: Type of 2FA ('email' or 'authenticator').
        two_factor_setup_required: Whether 2FA setup is required on next login.
        account_locked: Timestamp when account was locked (0 if not locked).
        failed_attempts: Number of failed login attempts.
        auth_source: Authentication source key.
        auth_source_name: Authentication source name.
        remote_name: Remote username (for external auth).
        identity: Identity key.
        creator: Username of the user who created this account.
        ssh_keys: SSH public keys (newline-separated).
    """

    @property
    def user_type(self) -> str:
        """Get the user type (normal, api, vdi)."""
        return str(self.get("type", "normal"))

    @property
    def user_type_display(self) -> str:
        """Get the user type as a human-readable string."""
        type_map = {
            "normal": "Normal",
            "api": "API",
            "vdi": "VDI",
            "site_sync": "Site Sync",
            "site_user": "Site User",
        }
        return type_map.get(self.user_type, self.user_type)

    @property
    def displayname(self) -> str | None:
        """Get the display name."""
        return self.get("displayname")

    @property
    def email(self) -> str | None:
        """Get the email address."""
        return self.get("email")

    @property
    def is_enabled(self) -> bool:
        """Check if user account is enabled."""
        return bool(self.get("enabled", True))

    @property
    def created(self) -> int | None:
        """Get the creation timestamp (Unix epoch)."""
        val = self.get("created")
        return int(val) if val is not None else None

    @property
    def last_login(self) -> int | None:
        """Get the last login timestamp (Unix epoch)."""
        val = self.get("last_login")
        return int(val) if val and val > 0 else None

    @property
    def change_password(self) -> bool:
        """Check if password change is required on next login."""
        return bool(self.get("change_password", False))

    @property
    def physical_access(self) -> bool:
        """Check if physical (console/SSH) access is enabled.

        Note: Users with physical access have administrator privileges.
        """
        return bool(self.get("physical_access", False))

    @property
    def two_factor_enabled(self) -> bool:
        """Check if two-factor authentication is enabled."""
        return bool(self.get("two_factor_authentication", False))

    @property
    def two_factor_type(self) -> str | None:
        """Get the 2FA type ('email' or 'authenticator')."""
        return self.get("two_factor_type")

    @property
    def two_factor_type_display(self) -> str:
        """Get the 2FA type as a human-readable string."""
        type_map = {
            "email": "Email",
            "authenticator": "Authenticator (TOTP)",
        }
        return type_map.get(self.two_factor_type or "", self.two_factor_type or "None")

    @property
    def two_factor_setup_required(self) -> bool:
        """Check if 2FA setup is required on next login.

        Note: This is a write-only field in the API, so this property
        will always return False. Use it only for setting during
        create/update operations.
        """
        return bool(self.get("two_factor_setup_next_login", False))

    @property
    def account_locked(self) -> int | None:
        """Get the account locked timestamp (Unix epoch), or None if not locked."""
        val = self.get("account_locked")
        return int(val) if val and val > 0 else None

    @property
    def is_locked(self) -> bool:
        """Check if account is currently locked."""
        return self.account_locked is not None

    @property
    def failed_attempts(self) -> int:
        """Get the number of failed login attempts."""
        return int(self.get("failed_attempts", 0))

    @property
    def auth_source(self) -> int | None:
        """Get the authentication source key."""
        val = self.get("auth_source")
        return int(val) if val is not None else None

    @property
    def auth_source_name(self) -> str | None:
        """Get the authentication source name."""
        return self.get("auth_source_name") or self.get("auth_source_display")

    @property
    def remote_name(self) -> str | None:
        """Get the remote username (for external auth)."""
        return self.get("remote_name")

    @property
    def identity(self) -> int | None:
        """Get the identity key."""
        val = self.get("identity")
        return int(val) if val is not None else None

    @property
    def creator(self) -> str | None:
        """Get the username of who created this account."""
        return self.get("creator")

    @property
    def ssh_keys(self) -> str | None:
        """Get the SSH public keys (newline-separated)."""
        return self.get("ssh_keys")

    def enable(self) -> User:
        """Enable this user account.

        Returns:
            Updated User object.
        """
        from typing import cast

        manager = cast("UserManager", self._manager)
        return manager.enable(self.key)

    def disable(self) -> User:
        """Disable this user account.

        Returns:
            Updated User object.
        """
        from typing import cast

        manager = cast("UserManager", self._manager)
        return manager.disable(self.key)


class UserManager(ResourceManager[User]):
    """Manager for VergeOS user operations.

    Provides CRUD operations and management for user accounts.

    Example:
        >>> # List all users
        >>> for user in client.users.list():
        ...     print(f"{user.name}: {user.user_type_display}")

        >>> # List only API users
        >>> api_users = client.users.list(user_type="api")

        >>> # Create a user
        >>> user = client.users.create(
        ...     name="jsmith",
        ...     password="SecurePass123!",
        ...     displayname="John Smith",
        ...     email="jsmith@company.com"
        ... )

        >>> # Enable/disable users
        >>> client.users.disable(user.key)
        >>> client.users.enable(user.key)
    """

    _endpoint = "users"

    # Default fields for list operations (matches PowerShell module)
    # Note: two_factor_setup_next_login is a write-only argument field
    _default_fields = [
        "$key",
        "name",
        "displayname",
        "email",
        "type",
        "enabled",
        "created",
        "last_login",
        "change_password",
        "physical_access",
        "two_factor_authentication",
        "two_factor_type",
        "account_locked",
        "failed_attempts",
        "auth_source",
        "auth_source#name as auth_source_name",
        "remote_name",
        "identity",
        "creator",
    ]

    def __init__(self, client: VergeClient) -> None:
        super().__init__(client)

    def _to_model(self, data: dict[str, Any]) -> User:
        """Convert API response to User object."""
        return User(data, self)

    def list(
        self,
        filter: str | None = None,
        fields: builtins.list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        user_type: UserType | None = None,
        enabled: bool | None = None,
        include_system: bool = False,
        **filter_kwargs: Any,
    ) -> builtins.list[User]:
        """List users with optional filtering.

        By default, excludes system user types (site_sync, site_user).

        Args:
            filter: OData filter string.
            fields: List of fields to return (uses defaults if not specified).
            limit: Maximum number of results.
            offset: Skip this many results.
            user_type: Filter by user type ('normal', 'api', 'vdi').
            enabled: Filter by enabled status.
            include_system: Include system user types (site_sync, site_user).
            **filter_kwargs: Shorthand filter arguments (name, etc.).

        Returns:
            List of User objects.

        Example:
            >>> # List all users
            >>> users = client.users.list()

            >>> # List only API users
            >>> api_users = client.users.list(user_type="api")

            >>> # List disabled users
            >>> disabled = client.users.list(enabled=False)

            >>> # List by name pattern (exact match)
            >>> users = client.users.list(name="admin")
        """
        params: dict[str, Any] = {}

        # Build filter
        filters: builtins.list[str] = []

        # Exclude system user types by default
        if not include_system:
            filters.append("type ne 'site_sync'")
            filters.append("type ne 'site_user'")

        if filter:
            filters.append(filter)
        if filter_kwargs:
            filters.append(build_filter(**filter_kwargs))

        # Add user_type filter
        if user_type is not None:
            filters.append(f"type eq '{user_type}'")

        # Add enabled filter
        if enabled is not None:
            filters.append(f"enabled eq {str(enabled).lower()}")

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

    def list_enabled(self) -> builtins.list[User]:
        """List all enabled users.

        Returns:
            List of enabled User objects.
        """
        return self.list(enabled=True)

    def list_disabled(self) -> builtins.list[User]:
        """List all disabled users.

        Returns:
            List of disabled User objects.
        """
        return self.list(enabled=False)

    def list_api_users(self) -> builtins.list[User]:
        """List all API users.

        Returns:
            List of API User objects.
        """
        return self.list(user_type="api")

    def list_vdi_users(self) -> builtins.list[User]:
        """List all VDI users.

        Returns:
            List of VDI User objects.
        """
        return self.list(user_type="vdi")

    def get(
        self,
        key: int | None = None,
        *,
        name: str | None = None,
        fields: builtins.list[str] | None = None,
    ) -> User:
        """Get a single user by key or name.

        Args:
            key: User $key (ID).
            name: Username.
            fields: List of fields to return.

        Returns:
            User object.

        Raises:
            NotFoundError: If user not found.
            ValueError: If neither key nor name provided.

        Example:
            >>> # Get by key
            >>> user = client.users.get(123)

            >>> # Get by name
            >>> user = client.users.get(name="admin")
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
                raise NotFoundError(f"User with key {key} not found")
            if not isinstance(response, dict):
                raise NotFoundError(f"User with key {key} returned invalid response")
            return self._to_model(response)

        if name is not None:
            # Search by name
            escaped_name = name.replace("'", "''")
            results = self.list(filter=f"name eq '{escaped_name}'", fields=fields, limit=1)
            if not results:
                raise NotFoundError(f"User '{name}' not found")
            return results[0]

        raise ValueError("Either key or name must be provided")

    def create(  # type: ignore[override]
        self,
        name: str,
        password: str,
        *,
        displayname: str | None = None,
        email: str | None = None,
        user_type: UserType = "normal",
        enabled: bool = True,
        change_password: bool = False,
        physical_access: bool = False,
        two_factor_enabled: bool = False,
        two_factor_type: TwoFactorType = "email",
        two_factor_setup_required: bool = False,
        ssh_keys: builtins.list[str] | str | None = None,
    ) -> User:
        """Create a new user.

        Args:
            name: Username (1-128 chars, no forward slashes, will be lowercased).
            password: User password.
            displayname: Display name for the user.
            email: Email address (required if enabling 2FA).
            user_type: User type ('normal', 'api', 'vdi'). Default 'normal'.
            enabled: Enable the account. Default True.
            change_password: Require password change on next login. Default False.
            physical_access: Enable console/SSH access (grants admin). Default False.
            two_factor_enabled: Enable two-factor authentication. Default False.
            two_factor_type: Type of 2FA ('email' or 'authenticator'). Default 'email'.
            two_factor_setup_required: Require 2FA setup on next login. Default False.
            ssh_keys: SSH public keys (list or newline-separated string).

        Returns:
            Created User object.

        Raises:
            ValueError: If email not provided when enabling 2FA.

        Example:
            >>> # Create a basic user
            >>> user = client.users.create(
            ...     name="jsmith",
            ...     password="SecurePass123!",
            ...     displayname="John Smith",
            ...     email="jsmith@company.com"
            ... )

            >>> # Create an API user
            >>> api_user = client.users.create(
            ...     name="api_service",
            ...     password="ApiSecret!",
            ...     user_type="api"
            ... )

            >>> # Create with 2FA enabled
            >>> user = client.users.create(
            ...     name="secure_user",
            ...     password="Pass123!",
            ...     email="secure@company.com",
            ...     two_factor_enabled=True,
            ...     two_factor_type="authenticator"
            ... )
        """
        # Validate 2FA requirements
        if two_factor_enabled and not email:
            raise ValueError("Email address is required when enabling two-factor authentication")

        # Build request body
        body: dict[str, Any] = {
            "name": name.lower(),  # API requires lowercase
            "password": password,
            "type": user_type,
            "enabled": enabled,
        }

        if displayname:
            body["displayname"] = displayname

        if email:
            body["email"] = email.lower()

        if change_password:
            body["change_password"] = True

        if physical_access:
            body["physical_access"] = True

        # Handle 2FA settings
        if two_factor_enabled:
            if two_factor_type == "authenticator":
                # Authenticator requires TOTP setup - user must set up at next login
                body["two_factor_setup_next_login"] = True
                body["two_factor_type"] = two_factor_type
            else:
                # Email-based 2FA can be enabled immediately
                body["two_factor_authentication"] = True
                body["two_factor_type"] = two_factor_type

        if two_factor_setup_required:
            body["two_factor_setup_next_login"] = True

        # Handle SSH keys
        if ssh_keys:
            if isinstance(ssh_keys, list):
                body["ssh_keys"] = "\n".join(ssh_keys)
            else:
                body["ssh_keys"] = ssh_keys

        response = self._client._request("POST", self._endpoint, json_data=body)

        # Get the created user
        if response and isinstance(response, dict):
            user_key = response.get("$key")
            if user_key:
                return self.get(key=int(user_key))

        # Fallback: search by name
        return self.get(name=name.lower())

    def update(  # type: ignore[override]
        self,
        key: int,
        *,
        password: str | None = None,
        displayname: str | None = None,
        email: str | None = None,
        enabled: bool | None = None,
        change_password: bool | None = None,
        physical_access: bool | None = None,
        two_factor_enabled: bool | None = None,
        two_factor_type: TwoFactorType | None = None,
        two_factor_setup_required: bool | None = None,
        ssh_keys: builtins.list[str] | str | None = None,
    ) -> User:
        """Update a user.

        Args:
            key: User $key (ID).
            password: New password.
            displayname: New display name.
            email: New email address.
            enabled: Enable or disable the account.
            change_password: Require password change on next login.
            physical_access: Enable or disable console/SSH access.
            two_factor_enabled: Enable or disable 2FA.
            two_factor_type: Type of 2FA ('email' or 'authenticator').
            two_factor_setup_required: Require 2FA setup on next login.
            ssh_keys: SSH public keys (list, string, or empty string to clear).

        Returns:
            Updated User object.

        Example:
            >>> # Change password
            >>> client.users.update(user.key, password="NewPass123!")

            >>> # Update display name and email
            >>> client.users.update(
            ...     user.key,
            ...     displayname="John Q. Smith",
            ...     email="john.smith@company.com"
            ... )

            >>> # Enable 2FA
            >>> client.users.update(
            ...     user.key,
            ...     two_factor_enabled=True,
            ...     two_factor_type="authenticator"
            ... )
        """
        body: dict[str, Any] = {}

        if password is not None:
            body["password"] = password

        if displayname is not None:
            body["displayname"] = displayname

        if email is not None:
            body["email"] = email.lower() if email else ""

        if enabled is not None:
            body["enabled"] = enabled

        if change_password is not None:
            body["change_password"] = change_password

        if physical_access is not None:
            body["physical_access"] = physical_access

        if two_factor_enabled is not None:
            body["two_factor_authentication"] = two_factor_enabled

        if two_factor_type is not None:
            body["two_factor_type"] = two_factor_type

        if two_factor_setup_required is not None:
            body["two_factor_setup_next_login"] = two_factor_setup_required

        if ssh_keys is not None:
            if isinstance(ssh_keys, list):
                body["ssh_keys"] = "\n".join(ssh_keys) if ssh_keys else ""
            else:
                body["ssh_keys"] = ssh_keys

        if not body:
            return self.get(key)

        self._client._request("PUT", f"{self._endpoint}/{key}", json_data=body)
        return self.get(key)

    def enable(self, key: int) -> User:
        """Enable a user account.

        Args:
            key: User $key (ID).

        Returns:
            Updated User object.

        Example:
            >>> client.users.enable(user.key)
        """
        return self.update(key, enabled=True)

    def disable(self, key: int) -> User:
        """Disable a user account.

        The account is not deleted and can be re-enabled later.

        Args:
            key: User $key (ID).

        Returns:
            Updated User object.

        Example:
            >>> client.users.disable(user.key)
        """
        return self.update(key, enabled=False)
