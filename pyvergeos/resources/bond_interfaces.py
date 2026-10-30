"""Bond member interfaces for an external network.

``primary`` is the 26.2 column that marks the primary member of a VLAN bond.
It is requested only when the connected server is 26.2 or later.
"""

from __future__ import annotations

import builtins
from typing import TYPE_CHECKING, Any

from pyvergeos.resources.base import ResourceManager, ResourceObject
from pyvergeos.versions import prepare_default_fields

if TYPE_CHECKING:
    from pyvergeos.client import VergeClient

_BOND_INTERFACE_FIELDS = [
    "$key",
    "vnet",
]

_BOND_INTERFACE_26_2_FIELDS = [
    "primary",
]


class VnetBondInterface(ResourceObject):
    """One member interface of a network bond."""

    @property
    def vnet_key(self) -> int | None:
        """Network this member belongs to."""
        value = self.get("vnet")
        return int(value) if value is not None else None

    @property
    def primary(self) -> bool:
        """Whether this member is the bond's primary interface.

        VergeOS 26.2. False when the server did not return the column.
        """
        return bool(self.get("primary", False))


class VnetBondInterfaceManager(ResourceManager[VnetBondInterface]):
    """Manager for ``vnet_bond_interfaces``.

    Pass a network key to list only that network's members. Leave it unset
    to list every bond interface the caller can see.

    Example:
        >>> for member in network.bond_interfaces.list():
        ...     print(member.key, member.primary)
    """

    _endpoint = "vnet_bond_interfaces"
    _default_fields = _BOND_INTERFACE_FIELDS

    def __init__(self, client: VergeClient, vnet_key: int | None = None) -> None:
        super().__init__(client)
        self._vnet_key = vnet_key

    def _to_model(self, data: dict[str, Any]) -> VnetBondInterface:
        return VnetBondInterface(data, self)

    def _scope_resource(self) -> str:
        return "Bond interface"

    def _scope_bindings(self) -> list[tuple[str, Any]]:
        if self._vnet_key is None:
            return []
        return [("vnet", self._vnet_key)]

    def _prepare(self) -> list[str]:
        return prepare_default_fields(self, _BOND_INTERFACE_FIELDS, _BOND_INTERFACE_26_2_FIELDS)

    def list(  # noqa: A003
        self,
        filter: str | None = None,  # noqa: A002
        fields: str | builtins.list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        **filter_kwargs: Any,
    ) -> builtins.list[VnetBondInterface]:
        """List bond member interfaces."""
        defaults = self._prepare()
        if fields is None:
            fields = defaults
        if self._vnet_key is not None:
            scope = f"vnet eq {self._vnet_key}"
            filter = f"({filter}) and {scope}" if filter else scope
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
    ) -> VnetBondInterface:
        """Get one bond member.

        ``primary`` is included on 26.2, same as ``list()``. The inherited
        get would otherwise keep the unversioned default and leave it out.
        """
        defaults = self._prepare()
        if fields is None:
            fields = defaults
        return super().get(key, name=name, fields=fields)

    def update(self, key: int, *, primary: bool | None = None, **kwargs: Any) -> VnetBondInterface:
        """Update a bond member.

        Args:
            key: Interface ``$key``.
            primary: Set or clear the primary member flag (26.2).
            **kwargs: Other columns to write.

        Returns:
            Updated bond interface.
        """
        self._prepare()
        if primary is not None:
            kwargs["primary"] = primary
        return super().update(key, **kwargs)
