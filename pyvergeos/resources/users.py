"""User resource manager."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List

from pyvergeos.resources.base import ResourceManager, ResourceObject

if TYPE_CHECKING:
    from pyvergeos.client import VergeClient


class User(ResourceObject):
    """User resource object."""

    @property
    def is_enabled(self) -> bool:
        """Check if user is enabled."""
        return bool(self.get("enabled", True))

    @property
    def is_admin(self) -> bool:
        """Check if user has admin privileges."""
        return bool(self.get("admin", False))


class UserManager(ResourceManager[User]):
    """Manager for User operations."""

    _endpoint = "users"

    def __init__(self, client: VergeClient) -> None:
        super().__init__(client)

    def _to_model(self, data: Dict[str, Any]) -> User:
        return User(data, self)

    def list_enabled(self) -> List[User]:
        """List all enabled users."""
        return self.list(filter="enabled eq true")

    def create(
        self,
        username: str,
        password: str,
        email: str = "",
        enabled: bool = True,
        **kwargs: Any,
    ) -> User:
        """Create a new user.

        Args:
            username: Username.
            password: User password.
            email: User email address.
            enabled: Whether user is enabled.
            **kwargs: Additional user properties.

        Returns:
            Created user object.
        """
        data = {
            "username": username,
            "password": password,
            "email": email,
            "enabled": enabled,
            **kwargs,
        }
        return super().create(**data)
