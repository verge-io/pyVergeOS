"""Cluster resource manager."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pyvergeos.resources.base import ResourceManager, ResourceObject

if TYPE_CHECKING:
    from pyvergeos.client import VergeClient


class Cluster(ResourceObject):
    """Cluster resource object."""

    @property
    def is_compute(self) -> bool:
        """Check if cluster is a compute cluster."""
        return bool(self.get("compute", False))


class ClusterManager(ResourceManager[Cluster]):
    """Manager for Cluster operations."""

    _endpoint = "clusters"

    def __init__(self, client: VergeClient) -> None:
        super().__init__(client)

    def _to_model(self, data: dict[str, Any]) -> Cluster:
        return Cluster(data, self)
