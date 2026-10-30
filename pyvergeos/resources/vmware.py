"""Minimum VMware container coverage.

The table is addressable so ``install_vixdisklib`` can be called on a
container. Other container fields stay available through an explicit
``fields`` argument or ``fields="all"``.
"""

from __future__ import annotations

import builtins
from typing import Any

from pyvergeos.resources.base import ResourceManager, ResourceObject

VMWARE_CONTAINER_FIELDS = [
    "$key",
    "name",
]


class VmwareContainer(ResourceObject):
    """A VMware service container."""

    @property
    def name(self) -> str:
        """Container name."""
        return str(self.get("name", ""))

    def install_vixdisklib(self, filename: str) -> dict[str, Any] | None:
        """Install a VDDK / VixDiskLib build on this container.

        Args:
            filename: File name of the library build to install.

        Returns:
            Action response, which may include task information.
        """
        manager = self._manager
        if not isinstance(manager, VmwareContainerManager):
            raise TypeError("Manager must be VmwareContainerManager")
        return manager.install_vixdisklib(self.key, filename)


class VmwareContainerManager(ResourceManager[VmwareContainer]):
    """Manager for ``vmware_containers``.

    Example:
        >>> container = client.vmware_containers.get(1)
        >>> container.install_vixdisklib("VMware-vix-disklib.tar.gz")
    """

    _endpoint = "vmware_containers"
    _default_fields = VMWARE_CONTAINER_FIELDS

    def _to_model(self, data: dict[str, Any]) -> VmwareContainer:
        return VmwareContainer(data, self)

    def install_vixdisklib(self, key: int, filename: str) -> dict[str, Any] | None:
        """Install a VixDiskLib build on a VMware container.

        Args:
            key: Container ``$key``.
            filename: File name of the library build to install.

        Returns:
            Action response, which may include task information.
        """
        return self.action(key, "install_vixdisklib", filename=filename)

    def list(  # noqa: A003
        self,
        filter: str | None = None,  # noqa: A002
        fields: str | builtins.list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        **filter_kwargs: Any,
    ) -> builtins.list[VmwareContainer]:
        """List VMware containers."""
        if fields is None:
            fields = self._default_fields
        return super().list(
            filter=filter,
            fields=fields,
            limit=limit,
            offset=offset,
            **filter_kwargs,
        )

    def get(
        self,
        key: int | None = None,
        *,
        name: str | None = None,
        fields: str | builtins.list[str] | None = None,
    ) -> VmwareContainer:
        """Get a VMware container by key or name."""
        if fields is None:
            fields = self._default_fields
        return super().get(key, name=name, fields=fields)
