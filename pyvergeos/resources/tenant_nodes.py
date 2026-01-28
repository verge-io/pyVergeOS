"""Tenant node (compute resource) allocation manager."""

from __future__ import annotations

import builtins
import logging
from typing import TYPE_CHECKING, Any

from pyvergeos.resources.base import ResourceManager, ResourceObject

if TYPE_CHECKING:
    from pyvergeos.client import VergeClient
    from pyvergeos.resources.tenant_manager import Tenant

logger = logging.getLogger(__name__)

# Default fields for tenant nodes
TENANT_NODE_DEFAULT_FIELDS = [
    "$key",
    "tenant",
    "name",
    "nodeid",
    "cpu_cores",
    "ram",
    "enabled",
    "description",
    "machine",
    "machine#status#running as running",
    "machine#status#status as status",
    "machine#status#node#$display as host_node",
    "machine#cluster as cluster",
    "machine#cluster#$display as cluster_name",
    "machine#preferred_node as preferred_node",
    "machine#preferred_node#$display as preferred_node_name",
    "machine#on_power_loss as on_power_loss",
]


class TenantNode(ResourceObject):
    """Tenant Node resource object.

    Represents a virtual node allocated to a tenant. Each tenant can have
    one or more nodes providing CPU and RAM resources.
    """

    @property
    def tenant_key(self) -> int:
        """Get the tenant key this node belongs to."""
        return int(self.get("tenant", 0))

    @property
    def name(self) -> str:
        """Get the node name (e.g., 'node1')."""
        return str(self.get("name", ""))

    @property
    def node_id(self) -> int:
        """Get the node ID number within the tenant."""
        return int(self.get("nodeid", 0))

    @property
    def cpu_cores(self) -> int:
        """Get the number of CPU cores allocated."""
        return int(self.get("cpu_cores", 0))

    @property
    def ram_mb(self) -> int:
        """Get RAM allocation in MB."""
        return int(self.get("ram", 0))

    @property
    def ram_gb(self) -> float:
        """Get RAM allocation in GB."""
        return round(self.ram_mb / 1024, 2)

    @property
    def is_enabled(self) -> bool:
        """Check if the node is enabled."""
        return bool(self.get("enabled", True))

    @property
    def is_running(self) -> bool:
        """Check if the node is currently running."""
        return bool(self.get("running", False))

    @property
    def status(self) -> str:
        """Get the node status."""
        return str(self.get("status", "unknown"))

    @property
    def host_node(self) -> str | None:
        """Get the physical host node name."""
        return self.get("host_node")

    @property
    def cluster_key(self) -> int | None:
        """Get the cluster key."""
        cluster = self.get("cluster")
        return int(cluster) if cluster else None

    @property
    def cluster_name(self) -> str | None:
        """Get the cluster name."""
        return self.get("cluster_name")

    @property
    def preferred_node_key(self) -> int | None:
        """Get the preferred node key."""
        node = self.get("preferred_node")
        return int(node) if node else None

    @property
    def preferred_node_name(self) -> str | None:
        """Get the preferred node name."""
        return self.get("preferred_node_name")

    @property
    def on_power_loss(self) -> str:
        """Get power loss behavior (power_on, last_state, leave_off)."""
        return str(self.get("on_power_loss", "last_state"))

    @property
    def machine_key(self) -> int | None:
        """Get the machine key for this node."""
        machine = self.get("machine")
        return int(machine) if machine else None

    def save(self, **kwargs: Any) -> TenantNode:
        """Save changes to this node.

        Args:
            **kwargs: Fields to update. Supported fields:
                - cpu_cores: Number of CPU cores
                - ram: RAM in MB
                - enabled: Enable/disable the node
                - description: Node description

        Returns:
            Updated TenantNode object.
        """
        from typing import cast

        manager = cast("TenantNodeManager", self._manager)
        return manager.update(self.key, **kwargs)

    def delete(self) -> None:
        """Delete this node from the tenant."""
        from typing import cast

        manager = cast("TenantNodeManager", self._manager)
        manager.delete(self.key)

    def __repr__(self) -> str:
        status = "running" if self.is_running else "stopped"
        return (
            f"<TenantNode {self.name}: {self.cpu_cores} cores, "
            f"{self.ram_gb:.1f} GB RAM ({status})>"
        )


class TenantNodeManager(ResourceManager[TenantNode]):
    """Manager for Tenant Node operations.

    This manager handles compute node allocations for tenants. Each tenant
    can have one or more virtual nodes with CPU and RAM resources.

    This manager is accessed through a Tenant object's nodes property
    or via client.tenants.nodes(tenant_key).

    Example:
        >>> tenant = client.tenants.get(name="my-tenant")
        >>> # List all nodes
        >>> for node in tenant.nodes.list():
        ...     print(f"{node.name}: {node.cpu_cores} cores, {node.ram_gb} GB")
        >>> # Add a node with 4 cores and 16 GB RAM
        >>> tenant.nodes.create(cpu_cores=4, ram_gb=16, cluster=1)
    """

    _endpoint = "tenant_nodes"
    _default_fields = TENANT_NODE_DEFAULT_FIELDS

    def __init__(self, client: VergeClient, tenant: Tenant) -> None:
        super().__init__(client)
        self._tenant = tenant

    def _to_model(self, data: dict[str, Any]) -> TenantNode:
        return TenantNode(data, self)

    def list(  # type: ignore[override]
        self,
        filter: str | None = None,  # noqa: A002
        fields: builtins.list[str] | None = None,
        **kwargs: Any,
    ) -> builtins.list[TenantNode]:
        """List nodes for this tenant.

        Args:
            filter: Additional OData filter string.
            fields: List of fields to return.
            **kwargs: Additional filter arguments.

        Returns:
            List of TenantNode objects.
        """
        if fields is None:
            fields = self._default_fields

        # Build filter for this tenant
        tenant_filter = f"tenant eq {self._tenant.key}"
        if filter:
            tenant_filter = f"{tenant_filter} and ({filter})"

        params: dict[str, Any] = {
            "filter": tenant_filter,
            "fields": ",".join(fields),
        }

        response = self._client._request("GET", self._endpoint, params=params)

        if response is None:
            return []

        if not isinstance(response, list):
            return [self._to_model(response)]

        return [self._to_model(item) for item in response]

    def get(
        self,
        key: int | None = None,
        *,
        name: str | None = None,
        fields: builtins.list[str] | None = None,
    ) -> TenantNode:
        """Get a node by key or name.

        Args:
            key: Node $key (ID).
            name: Node name (e.g., 'node1').
            fields: List of fields to return.

        Returns:
            TenantNode object.

        Raises:
            NotFoundError: If node not found.
            ValueError: If neither key nor name provided.
        """
        from pyvergeos.exceptions import NotFoundError

        if fields is None:
            fields = self._default_fields

        if key is not None:
            params: dict[str, Any] = {"fields": ",".join(fields)}
            response = self._client._request("GET", f"{self._endpoint}/{key}", params=params)
            if response is None:
                raise NotFoundError(f"Tenant node {key} not found")
            if not isinstance(response, dict):
                raise NotFoundError(f"Tenant node {key} returned invalid response")
            return self._to_model(response)

        if name is not None:
            nodes = self.list(filter=f"name eq '{name}'", fields=fields)
            if not nodes:
                raise NotFoundError(
                    f"Tenant node '{name}' not found for tenant '{self._tenant.name}'"
                )
            return nodes[0]

        raise ValueError("Either key or name must be provided")

    def create(  # type: ignore[override]
        self,
        cpu_cores: int = 4,
        ram_mb: int | None = None,
        ram_gb: int | None = None,
        cluster: int = 1,
        preferred_node: int | None = None,
        name: str | None = None,
        description: str = "",
    ) -> TenantNode:
        """Create a new node for this tenant.

        Args:
            cpu_cores: Number of CPU cores (default: 4).
            ram_mb: RAM allocation in MB (use this or ram_gb).
            ram_gb: RAM allocation in GB (default: 16 GB if neither specified).
            cluster: Cluster key to run the node on (default: 1).
            preferred_node: Preferred physical node key.
            name: Node name (auto-generated if not specified).
            description: Node description.

        Returns:
            Created TenantNode object.

        Raises:
            ValueError: If tenant is a snapshot or invalid parameters.
        """
        if self._tenant.is_snapshot:
            raise ValueError("Cannot add nodes to a tenant snapshot")

        # Calculate RAM in MB
        if ram_mb is not None:
            ram = ram_mb
        elif ram_gb is not None:
            ram = ram_gb * 1024
        else:
            ram = 16384  # Default 16 GB

        if ram < 2048:
            raise ValueError("RAM must be at least 2048 MB (2 GB)")

        if cpu_cores < 1:
            raise ValueError("CPU cores must be at least 1")

        body: dict[str, Any] = {
            "tenant": self._tenant.key,
            "cpu_cores": cpu_cores,
            "ram": ram,
            "cluster": cluster,
        }

        if preferred_node is not None:
            body["preferred_node"] = preferred_node

        if name:
            body["name"] = name

        if description:
            body["description"] = description

        logger.debug(
            f"Creating node for tenant '{self._tenant.name}': "
            f"{cpu_cores} cores, {ram} MB RAM"
        )
        response = self._client._request("POST", self._endpoint, json_data=body)

        # Get the created node key
        if isinstance(response, dict):
            node_key = response.get("$key")
            if node_key:
                return self.get(int(node_key))

        # Fall back to listing and getting the latest
        import time

        time.sleep(0.5)
        nodes = self.list()
        if nodes:
            return nodes[-1]

        from pyvergeos.exceptions import APIError

        raise APIError("Failed to create tenant node")

    def update(self, key: int, **kwargs: Any) -> TenantNode:
        """Update a node.

        Args:
            key: Node $key (ID).
            **kwargs: Fields to update. Supported fields:
                - cpu_cores: Number of CPU cores
                - ram: RAM in MB
                - enabled: Enable/disable the node
                - description: Node description
                - cluster: Cluster key
                - preferred_node: Preferred node key

        Returns:
            Updated TenantNode object.
        """
        logger.debug(f"Updating tenant node {key}")
        self._client._request("PUT", f"{self._endpoint}/{key}", json_data=kwargs)
        return self.get(key)

    def delete(self, key: int) -> None:
        """Delete a node.

        Args:
            key: Node $key (ID).

        Warning:
            The node must be powered off before it can be deleted.
        """
        logger.debug(f"Deleting tenant node {key}")
        self._client._request("DELETE", f"{self._endpoint}/{key}")
