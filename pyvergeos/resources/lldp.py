"""Node LLDP neighbor resource manager."""

from __future__ import annotations

import builtins
from typing import TYPE_CHECKING, Any

from pyvergeos.resources.base import ResourceManager, ResourceObject

if TYPE_CHECKING:
    from pyvergeos.client import VergeClient

# Default fields for LLDP neighbors
LLDP_DEFAULT_FIELDS = [
    "$key",
    "node",
    "nic",
    "rid",
    "via",
    "age",
    "chassis",
    "port",
    "vlan",
    "other",
]


class NodeLLDPNeighbor(ResourceObject):
    """LLDP neighbor discovery result.

    Represents a neighbor device discovered via LLDP on a node's NIC.
    Non-persistent — populated by LLDP discovery.
    """

    @property
    def node_key(self) -> int:
        """Parent node key."""
        return int(self.get("node", 0))

    @property
    def nic_key(self) -> int:
        """NIC key where neighbor was discovered."""
        return int(self.get("nic", 0))

    @property
    def remote_id(self) -> str | None:
        """Remote device identifier."""
        return self.get("rid")

    @property
    def via(self) -> str | None:
        """Discovery method/protocol."""
        return self.get("via")

    @property
    def age(self) -> str | None:
        """Age of LLDP data."""
        return self.get("age")

    @property
    def chassis(self) -> dict[str, Any] | None:
        """Chassis information from LLDP (JSON)."""
        return self.get("chassis")

    @property
    def port(self) -> dict[str, Any] | None:
        """Port information from LLDP (JSON)."""
        return self.get("port")

    @property
    def vlan(self) -> dict[str, Any] | None:
        """VLAN information from LLDP (JSON)."""
        return self.get("vlan")

    @property
    def other(self) -> dict[str, Any] | None:
        """Other LLDP information (JSON)."""
        return self.get("other")

    @property
    def chassis_name(self) -> str | None:
        """Convenience: extract chassis name if available."""
        chassis = self.chassis
        if isinstance(chassis, dict):
            return chassis.get("name") or chassis.get("ChassisID")
        return None

    @property
    def port_id(self) -> str | None:
        """Convenience: extract port identifier if available."""
        port = self.port
        if isinstance(port, dict):
            return port.get("PortID") or port.get("id")
        return None


class NodeLLDPNeighborManager(ResourceManager[NodeLLDPNeighbor]):
    """Manager for node LLDP neighbor discovery results.

    Read-only — neighbors are populated by LLDP discovery on the node.

    Examples:
        List LLDP neighbors for a node::

            for neighbor in node.lldp_neighbors.list():
                print(f"NIC {neighbor.nic_key}: {neighbor.chassis_name}")

        Access globally::

            neighbors = client.node_lldp_neighbors.list(
                filter="node eq 1"
            )
    """

    _endpoint = "node_lldp_neighbors"
    _default_fields = LLDP_DEFAULT_FIELDS

    def __init__(self, client: VergeClient, node_key: int | None = None) -> None:
        super().__init__(client)
        self._node_key = node_key

    def _to_model(self, data: dict[str, Any]) -> NodeLLDPNeighbor:
        return NodeLLDPNeighbor(data, self)

    def list(  # noqa: A003
        self,
        filter: str | None = None,  # noqa: A002
        fields: builtins.list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        **filter_kwargs: Any,
    ) -> builtins.list[NodeLLDPNeighbor]:
        """List LLDP neighbors.

        When scoped to a node, automatically filters by node key.

        Args:
            filter: Additional OData filter string.
            fields: List of fields to return.
            limit: Maximum number of results.
            offset: Skip this many results.

        Returns:
            List of NodeLLDPNeighbor objects.
        """
        if fields is None:
            fields = self._default_fields

        filters: builtins.list[str] = []
        if self._node_key is not None:
            filters.append(f"node eq {self._node_key}")
        if filter:
            filters.append(f"({filter})")

        params: dict[str, Any] = {
            "fields": ",".join(fields),
        }
        if filters:
            params["filter"] = " and ".join(filters)
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

    def list_by_nic(self, nic_key: int) -> builtins.list[NodeLLDPNeighbor]:
        """List LLDP neighbors discovered on a specific NIC.

        Args:
            nic_key: NIC $key to filter by.

        Returns:
            List of NodeLLDPNeighbor objects.
        """
        return self.list(filter=f"nic eq {nic_key}")
