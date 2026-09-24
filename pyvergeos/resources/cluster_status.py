"""Cluster status resource manager (issue #127).

Live per-cluster capacity figures -- node, RAM and core totals, and how much
is currently online and used. This is the input to an **N-1 capacity
pre-check**: can the cluster still run everything if one node goes away?
Draining or rebooting a node the remaining cluster cannot absorb takes
workloads down, so consumers such as ``node_drain`` and ``rolling_update`` in
the ``vergeio.vergeos`` collection gate on these numbers.

``clusters.vsan_status()`` already surfaces the same figures by traversing
``status#...`` on the ``clusters`` endpoint. This manager instead exposes the
underlying ``cluster_status`` table directly, so a caller can filter it by
``cluster`` without a private ``client._request()`` -- which is what those
consumers were reduced to.
"""

from __future__ import annotations

import builtins
from typing import TYPE_CHECKING, Any

from pyvergeos.exceptions import NotFoundError
from pyvergeos.resources.base import ResourceManager, ResourceObject

if TYPE_CHECKING:
    from pyvergeos.client import VergeClient

#: Default projection for cluster status.
CLUSTER_STATUS_DEFAULT_FIELDS = [
    "$key",
    "cluster",
    "status",
    "status_info",
    "state",
    "total_nodes",
    "online_nodes",
    "total_ram",
    "online_ram",
    "used_ram",
    "phys_ram_used",
    "phys_vram_used",
    "total_cores",
    "online_cores",
    "used_cores",
    "phys_total_cpu",
    "running_machines",
    "last_update",
]


class ClusterStatus(ResourceObject):
    """Live capacity and health for a single cluster.

    Read-only; maintained by the system. The ``online_*`` figures are the ones
    an N-1 check compares against the ``used_*`` figures (issue #127).
    """

    @property
    def cluster_key(self) -> int:
        """``$key`` of the cluster these figures belong to."""
        return int(self.get("cluster", 0))

    @property
    def status(self) -> str:
        """Raw status string (e.g. ``online``)."""
        return str(self.get("status", "unknown"))

    @property
    def state(self) -> str:
        """Derived state string."""
        return str(self.get("state", "unknown"))

    @property
    def is_online(self) -> bool:
        """Whether the cluster reports itself online."""
        return self.get("status") == "online" or self.get("state") == "online"

    @property
    def total_nodes(self) -> int:
        """Nodes configured in the cluster."""
        return int(self.get("total_nodes") or 0)

    @property
    def online_nodes(self) -> int:
        """Nodes currently online."""
        return int(self.get("online_nodes") or 0)

    @property
    def total_ram(self) -> int:
        """Configured RAM in MB across the cluster."""
        return int(self.get("total_ram") or 0)

    @property
    def online_ram(self) -> int:
        """RAM in MB currently online -- the N-1 ceiling for RAM."""
        return int(self.get("online_ram") or 0)

    @property
    def used_ram(self) -> int:
        """RAM in MB currently allocated to running workloads."""
        return int(self.get("used_ram") or 0)

    @property
    def total_cores(self) -> int:
        """Configured cores across the cluster."""
        return int(self.get("total_cores") or 0)

    @property
    def online_cores(self) -> int:
        """Cores currently online -- the N-1 ceiling for cores."""
        return int(self.get("online_cores") or 0)

    @property
    def used_cores(self) -> int:
        """Cores currently allocated to running workloads."""
        return int(self.get("used_cores") or 0)

    @property
    def running_machines(self) -> int:
        """Machines currently running on the cluster."""
        return int(self.get("running_machines") or 0)

    def can_lose_one_node(self) -> bool:
        """Whether the cluster could still run its workloads down a node.

        An **optimistic, even-spread approximation**, not a guarantee. It
        treats one node's share of the online capacity as
        ``online / online_nodes`` and asks whether the remaining share still
        covers what is used. Returns False when there are fewer than two
        online nodes, since there is no redundancy to check.

        On a cluster of equal nodes this is exact. On a cluster of unequal
        nodes it errs toward True, in the unsafe direction, because the real
        worst case is losing the *largest* node rather than an average one.
        Two nodes of 68352 and 69120 MB give an even-spread ceiling of 68736
        MB, but only 68352 MB survives losing the larger one, so any
        ``used_ram`` in between reports True while the survivor could not in
        fact hold the load (issue #135).

        Do not use a True as a drain or maintenance gate on a cluster whose
        nodes differ in size. ``cluster_status`` carries only aggregates, so
        this method cannot see per-node sizes; a true N-1 check needs the
        ``nodes`` table, where ``Node.vm_ram_mb`` gives each node's figure::

            nodes = [n.vm_ram_mb for n in client.nodes.list() if n.is_online]
            survives = sum(nodes) - max(nodes)
            safe = status.used_ram <= survives

        A helper, not a scheduler: placement rules can make the real answer
        stricter still (issues #127, #135).
        """
        if self.online_nodes < 2:
            return False
        surviving = self.online_nodes - 1
        ram_ceiling = (self.online_ram / self.online_nodes) * surviving
        core_ceiling = (self.online_cores / self.online_nodes) * surviving
        return self.used_ram <= ram_ceiling and self.used_cores <= core_ceiling


class ClusterStatusManager(ResourceManager[ClusterStatus]):
    """Manager for the ``cluster_status`` table (issue #127).

    Read-only. Use it to read capacity figures for an N-1 pre-check without a
    private ``client._request()``.

    Examples:
        From a cluster::

            status = cluster.status.get()
            if not status.can_lose_one_node():
                raise RuntimeError("draining a node would overcommit the cluster")

        That check assumes equally sized nodes. A True is not an N-1
        guarantee on a cluster whose nodes differ in size, so gate real
        drains on per-node figures instead. See
        :meth:`ClusterStatus.can_lose_one_node` (issue #135).

        Globally, or filtered to one cluster::

            all_status = client.cluster_status.list()
            one = client.cluster_status.list(filter="cluster eq 1")
    """

    _endpoint = "cluster_status"
    _default_fields = CLUSTER_STATUS_DEFAULT_FIELDS

    def __init__(self, client: VergeClient, cluster_key: int | None = None) -> None:
        super().__init__(client)
        self._cluster_key = cluster_key

    def _to_model(self, data: dict[str, Any]) -> ClusterStatus:
        return ClusterStatus(data, self)

    def list(
        self,
        filter: str | None = None,
        fields: str | builtins.list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        **filter_kwargs: Any,
    ) -> builtins.list[ClusterStatus]:
        """List cluster status rows.

        Defaults ``fields`` to the manager's projection so a bare ``list()``
        returns populated rows; the endpoint otherwise answers with only
        ``$key``.

        Args:
            filter: OData filter string, e.g. ``"cluster eq 1"``.
            fields: Fields to return.
            limit: Maximum number of results.
            offset: Skip this many results.
            **filter_kwargs: Shorthand filter arguments.

        Returns:
            List of ClusterStatus objects.
        """
        if fields is None:
            fields = self._default_fields
        return super().list(
            filter=filter, fields=fields, limit=limit, offset=offset, **filter_kwargs
        )

    def get(  # type: ignore[override]
        self,
        key: int | None = None,
        *,
        fields: str | builtins.list[str] | None = None,
    ) -> ClusterStatus:
        """Get cluster status.

        When scoped to a cluster (``cluster.status``), returns that cluster's
        status via a ``cluster`` filter. When called with ``key``, fetches the
        status row with that own ``$key``.

        Args:
            key: Status row ``$key`` (optional if scoped to a cluster).
            fields: Fields to return.

        Returns:
            ClusterStatus.

        Raises:
            NotFoundError: If no status is found.
            ValueError: If neither ``key`` nor a scoped cluster is available.
        """
        if fields is None:
            fields = self._default_fields

        if key is not None:
            params: dict[str, Any] = {"fields": self._projection(fields)}
            response = self._client._request("GET", f"{self._endpoint}/{key}", params=params)
            if response is None:
                raise NotFoundError(f"Cluster status {key} not found")
            if not isinstance(response, dict):
                raise NotFoundError(f"Cluster status {key} returned invalid response")
            return self._to_model(response)

        if self._cluster_key is not None:
            params = {
                "filter": f"cluster eq {self._cluster_key}",
                "fields": self._projection(fields),
                "limit": 1,
            }
            response = self._client._request("GET", self._endpoint, params=params)
            if response is None:
                raise NotFoundError(f"Status not found for cluster {self._cluster_key}")
            if isinstance(response, list):
                if not response:
                    raise NotFoundError(f"Status not found for cluster {self._cluster_key}")
                return self._to_model(response[0])
            return self._to_model(response)

        raise ValueError("Either key or a scoped cluster_key is required")
