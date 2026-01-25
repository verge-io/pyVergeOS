"""Node resource manager."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pyvergeos.resources.base import ResourceManager, ResourceObject

if TYPE_CHECKING:
    from pyvergeos.client import VergeClient


class Node(ResourceObject):
    """Node resource object."""

    @property
    def is_online(self) -> bool:
        """Check if node is online."""
        return self.get("status") == "online"

    @property
    def is_maintenance(self) -> bool:
        """Check if node is in maintenance mode."""
        return bool(self.get("maintenance", False))


class NodeManager(ResourceManager[Node]):
    """Manager for Node operations."""

    _endpoint = "nodes"

    def __init__(self, client: VergeClient) -> None:
        super().__init__(client)

    def _to_model(self, data: dict[str, Any]) -> Node:
        return Node(data, self)
