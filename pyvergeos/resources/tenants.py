"""Tenant resource manager."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional

from pyvergeos.resources.base import ResourceManager, ResourceObject

if TYPE_CHECKING:
    from pyvergeos.client import VergeClient


class Tenant(ResourceObject):
    """Tenant resource object."""

    def power_on(self) -> Tenant:
        """Power on the tenant."""
        self._manager.action(self.key, "poweron")
        return self  # type: ignore[return-value]

    def power_off(self) -> Tenant:
        """Power off the tenant."""
        self._manager.action(self.key, "poweroff")
        return self  # type: ignore[return-value]

    def reset(self) -> Tenant:
        """Reset the tenant."""
        self._manager.action(self.key, "reset")
        return self  # type: ignore[return-value]

    def clone(self, name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Clone this tenant.

        Args:
            name: Name for the clone.

        Returns:
            Clone task information.
        """
        kwargs: Dict[str, Any] = {}
        if name:
            kwargs["name"] = name
        return self._manager.action(self.key, "clone", **kwargs)

    @property
    def is_running(self) -> bool:
        """Check if tenant is powered on."""
        return bool(self.get("powerstate", False))


class TenantManager(ResourceManager[Tenant]):
    """Manager for Tenant operations."""

    _endpoint = "tenants"

    def __init__(self, client: VergeClient) -> None:
        super().__init__(client)

    def _to_model(self, data: Dict[str, Any]) -> Tenant:
        return Tenant(data, self)

    def list_running(self) -> List[Tenant]:
        """List all running tenants."""
        return self.list(filter="powerstate eq true")

    def create(
        self,
        name: str,
        description: str = "",
        **kwargs: Any,
    ) -> Tenant:
        """Create a new tenant.

        Args:
            name: Tenant name.
            description: Tenant description.
            **kwargs: Additional tenant properties.

        Returns:
            Created tenant object.
        """
        data = {
            "name": name,
            "description": description,
            **kwargs,
        }
        return super().create(**data)
