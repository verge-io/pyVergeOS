"""Node memory (DIMM health) resource manager."""

from __future__ import annotations

import builtins
from typing import TYPE_CHECKING, Any

from pyvergeos.filters import build_filter
from pyvergeos.resources.base import ResourceManager, ResourceObject

if TYPE_CHECKING:
    from pyvergeos.client import VergeClient


class NodeMemory(ResourceObject):
    """Node memory (DIMM) resource object.

    Represents a physical memory module with health status.

    Example:
        >>> for dimm in client.node_memory.list():
        ...     if not dimm.is_healthy:
        ...         print(f"DIMM {dimm.locator} on node {dimm.node_key}: {dimm.status}")
        ...         print(f"  {dimm.status_info}")
    """

    @property
    def node_key(self) -> int | None:
        """Parent node key."""
        node = self.get("node")
        if node is not None:
            return int(node)
        return None

    @property
    def status(self) -> str:
        """DIMM status (online, error, warning, offline)."""
        return str(self.get("status", ""))

    @property
    def status_info(self) -> str:
        """Status details."""
        return str(self.get("status_info", ""))

    @property
    def label(self) -> str:
        """DIMM label."""
        return str(self.get("label", ""))

    @property
    def locator(self) -> str:
        """Slot locator (e.g. DIMM 0)."""
        return str(self.get("locator", ""))

    @property
    def bank_locator(self) -> str:
        """Bank locator (e.g. P0 CHANNEL A)."""
        return str(self.get("bank_locator", ""))

    @property
    def memory_type(self) -> str:
        """Memory type (DDR4, DDR5, etc.)."""
        return str(self.get("type", ""))

    @property
    def type_detail(self) -> str:
        """Memory type detail."""
        return str(self.get("type_detail", ""))

    @property
    def size(self) -> str:
        """DIMM size (e.g. '48 GB')."""
        return str(self.get("size", ""))

    @property
    def speed(self) -> str:
        """Memory speed (e.g. '5600 MT/s')."""
        return str(self.get("speed", ""))

    @property
    def configured_memory_speed(self) -> str:
        """Configured memory speed."""
        return str(self.get("configured_memory_speed", ""))

    @property
    def form_factor(self) -> str:
        """Form factor (DIMM, SODIMM, etc.)."""
        return str(self.get("form_factor", ""))

    @property
    def manufacturer(self) -> str:
        """DIMM manufacturer."""
        return str(self.get("manufacturer", ""))

    @property
    def serial_number(self) -> str:
        """DIMM serial number."""
        return str(self.get("serial_number", ""))

    @property
    def part_number(self) -> str:
        """Part number."""
        return str(self.get("part_number", ""))

    @property
    def asset_tag(self) -> str:
        """Asset tag."""
        return str(self.get("asset_tag", ""))

    @property
    def rank(self) -> str:
        """Memory rank."""
        return str(self.get("rank", ""))

    @property
    def data_width(self) -> str:
        """Data width."""
        return str(self.get("data_width", ""))

    @property
    def total_width(self) -> str:
        """Total width (includes ECC bits if present)."""
        return str(self.get("total_width", ""))

    @property
    def memory_technology(self) -> str:
        """Memory technology (DRAM, etc.)."""
        return str(self.get("memory_technology", ""))

    @property
    def is_healthy(self) -> bool:
        """Whether the DIMM is in a healthy state."""
        return self.status == "online"

    def __repr__(self) -> str:
        return (
            f"<NodeMemory key={self.get('$key', '?')} "
            f"locator={self.locator!r} status={self.status!r} "
            f"size={self.size!r}>"
        )


class NodeMemoryManager(ResourceManager[NodeMemory]):
    """Manager for node memory (DIMM) health data.

    Provides access to DIMM status across the cluster. Can be
    scoped to a specific node or used globally.

    Example:
        >>> # List all DIMMs
        >>> dimms = client.node_memory.list()

        >>> # Find unhealthy DIMMs
        >>> for dimm in dimms:
        ...     if not dimm.is_healthy:
        ...         print(f"ALERT: {dimm.locator} is {dimm.status}")
    """

    _endpoint = "node_memory"

    _default_fields = [
        "$key",
        "node",
        "status",
        "status_info",
        "label",
        "locator",
        "bank_locator",
        "type",
        "type_detail",
        "size",
        "speed",
        "configured_memory_speed",
        "form_factor",
        "manufacturer",
        "serial_number",
        "part_number",
        "asset_tag",
        "rank",
        "data_width",
        "total_width",
        "memory_technology",
        "modified",
    ]

    def __init__(
        self, client: VergeClient, node_key: int | None = None
    ) -> None:
        super().__init__(client)
        self._node_key = node_key

    def _to_model(self, data: dict[str, Any]) -> NodeMemory:
        return NodeMemory(data, self)

    def list(  # noqa: A003
        self,
        filter: str | None = None,  # noqa: A002
        fields: builtins.list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        **filter_kwargs: Any,
    ) -> builtins.list[NodeMemory]:
        """List node memory DIMMs with optional filtering.

        Args:
            filter: OData filter string.
            fields: List of fields to return.
            limit: Maximum number of results.
            offset: Skip this many results.
            **filter_kwargs: Additional filter arguments.

        Returns:
            List of NodeMemory objects.
        """
        params: dict[str, Any] = {}
        filters = []

        if filter:
            filters.append(filter)

        if self._node_key is not None:
            filters.append(f"node eq {self._node_key}")

        if filter_kwargs:
            filters.append(build_filter(**filter_kwargs))

        if filters:
            params["filter"] = " and ".join(filters)

        if fields:
            params["fields"] = ",".join(fields)
        else:
            params["fields"] = ",".join(self._default_fields)

        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset

        response = self._client._request("GET", self._endpoint, params=params)

        if response is None:
            return []

        if not isinstance(response, list):
            return [self._to_model(response)]

        return [self._to_model(item) for item in response]

    def get(  # type: ignore[override]
        self,
        key: int | None = None,
        *,
        fields: builtins.list[str] | None = None,
    ) -> NodeMemory:
        """Get a DIMM by key.

        Args:
            key: DIMM $key (ID).
            fields: List of fields to return.

        Returns:
            NodeMemory object.

        Raises:
            NotFoundError: If DIMM not found.
            ValueError: If key not provided.
        """
        if key is None:
            raise ValueError("key must be provided")

        params: dict[str, Any] = {}
        if fields:
            params["fields"] = ",".join(fields)

        response = self._client._request(
            "GET", f"{self._endpoint}/{key}", params=params
        )

        if response is None or not isinstance(response, dict):
            from pyvergeos.exceptions import NotFoundError

            raise NotFoundError(f"Node memory {key} not found")

        return self._to_model(response)
