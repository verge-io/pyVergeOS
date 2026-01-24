"""Group resource manager."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict

from pyvergeos.resources.base import ResourceManager, ResourceObject

if TYPE_CHECKING:
    from pyvergeos.client import VergeClient


class Group(ResourceObject):
    """Group resource object."""

    pass


class GroupManager(ResourceManager[Group]):
    """Manager for Group operations."""

    _endpoint = "groups"

    def __init__(self, client: VergeClient) -> None:
        super().__init__(client)

    def _to_model(self, data: Dict[str, Any]) -> Group:
        return Group(data, self)

    def create(
        self,
        name: str,
        description: str = "",
        **kwargs: Any,
    ) -> Group:
        """Create a new group.

        Args:
            name: Group name.
            description: Group description.
            **kwargs: Additional group properties.

        Returns:
            Created group object.
        """
        data = {
            "name": name,
            "description": description,
            **kwargs,
        }
        return super().create(**data)
