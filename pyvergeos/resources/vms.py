"""Virtual Machine resource manager."""

from __future__ import annotations

import builtins
import logging
from typing import TYPE_CHECKING, Any

from pyvergeos.resources.base import ResourceManager, ResourceObject

if TYPE_CHECKING:
    from pyvergeos.client import VergeClient
    from pyvergeos.resources.drives import DriveManager
    from pyvergeos.resources.nics import NICManager
    from pyvergeos.resources.snapshots import VMSnapshotManager

logger = logging.getLogger(__name__)

# Default fields to request for VMs
VM_DEFAULT_FIELDS = [
    "$key",
    "name",
    "description",
    "enabled",
    "cpu_cores",
    "ram",
    "os_family",
    "guest_agent",
    "uefi",
    "secure_boot",
    "machine_type",
    "created",
    "modified",
    "is_snapshot",
    "machine",
    "machine#status#status as status",
    "machine#status#running as running",
    "machine#status#node as node_key",
    "machine#status#node#name as node_name",
    "machine#cluster as cluster_key",
    "machine#cluster#name as cluster_name",
    "machine#ha_group as ha_group",
]


class VM(ResourceObject):
    """Virtual Machine resource object."""

    _drives: DriveManager | None = None
    _nics: NICManager | None = None
    _snapshots: VMSnapshotManager | None = None

    @property
    def drives(self) -> DriveManager:
        """Access drives attached to this VM."""
        if self._drives is None:
            from pyvergeos.resources.drives import DriveManager

            self._drives = DriveManager(self._manager._client, self)
        return self._drives

    @property
    def nics(self) -> NICManager:
        """Access NICs attached to this VM."""
        if self._nics is None:
            from pyvergeos.resources.nics import NICManager

            self._nics = NICManager(self._manager._client, self)
        return self._nics

    @property
    def snapshots(self) -> VMSnapshotManager:
        """Access snapshots for this VM."""
        if self._snapshots is None:
            from pyvergeos.resources.snapshots import VMSnapshotManager

            self._snapshots = VMSnapshotManager(self._manager._client, self)
        return self._snapshots

    def power_on(self, preferred_node: int | None = None) -> VM:
        """Power on the VM.

        Args:
            preferred_node: Node $key to start VM on.

        Returns:
            Self for chaining.

        Raises:
            ValueError: If VM is a snapshot.
        """
        if self.is_snapshot:
            raise ValueError("Cannot power on a snapshot")

        body: dict[str, Any] = {"vm": self.key, "action": "poweron"}
        if preferred_node is not None:
            body["params"] = {"preferred_node": preferred_node}

        self._manager._client._request("POST", "vm_actions", json_data=body)
        return self

    def power_off(self, force: bool = False) -> VM:
        """Power off the VM.

        Args:
            force: If True, forces immediate power off (like pulling the plug).
                   If False (default), sends ACPI shutdown signal for graceful shutdown.

        Returns:
            Self for chaining.
        """
        # 'kill' = immediate termination, 'poweroff' = graceful ACPI shutdown
        action = "kill" if force else "poweroff"
        self._manager._client._request(
            "POST", "vm_actions", json_data={"vm": self.key, "action": action}
        )
        return self

    def reset(self) -> VM:
        """Reset VM (hard reboot)."""
        self._manager._client._request(
            "POST", "vm_actions", json_data={"vm": self.key, "action": "reset"}
        )
        return self

    def guest_reboot(self) -> VM:
        """Send reboot signal to guest OS (requires guest agent)."""
        self._manager._client._request(
            "POST", "vm_actions", json_data={"vm": self.key, "action": "guestreset"}
        )
        return self

    def guest_shutdown(self) -> VM:
        """Send shutdown signal to guest OS (requires guest agent)."""
        self._manager._client._request(
            "POST", "vm_actions", json_data={"vm": self.key, "action": "guestshutdown"}
        )
        return self

    def snapshot(
        self,
        name: str | None = None,
        retention: int = 86400,
        quiesce: bool = False,
    ) -> dict[str, Any] | None:
        """Take a VM snapshot.

        Args:
            name: Snapshot name (optional).
            retention: Snapshot retention in seconds (default 24h).
            quiesce: Quiesce disk activity (requires guest agent).

        Returns:
            Snapshot task information.
        """
        body: dict[str, Any] = {
            "vm": self.key,
            "action": "snapshot",
            "params": {"retention": retention, "quiesce": quiesce},
        }
        if name:
            body["params"]["name"] = name

        result = self._manager._client._request("POST", "vm_actions", json_data=body)
        return result if isinstance(result, dict) else None

    def clone(
        self,
        name: str | None = None,
        preserve_macs: bool = False,
    ) -> dict[str, Any] | None:
        """Clone this VM.

        Args:
            name: Name for the clone (default: {name}_{timestamp}).
            preserve_macs: Keep original MAC addresses.

        Returns:
            Clone task information with new VM key.
        """
        body: dict[str, Any] = {
            "vm": self.key,
            "action": "clone",
            "params": {"preserve_macs": preserve_macs},
        }
        if name:
            body["params"]["name"] = name

        result = self._manager._client._request("POST", "vm_actions", json_data=body)
        return result if isinstance(result, dict) else None

    def move(
        self,
        node: int | None = None,
        cluster: int | None = None,
    ) -> dict[str, Any] | None:
        """Move VM to a different node or cluster.

        Args:
            node: Target node $key.
            cluster: Target cluster $key.

        Returns:
            Move task information.
        """
        params: dict[str, Any] = {}
        if node is not None:
            params["node"] = node
        if cluster is not None:
            params["cluster"] = cluster

        body: dict[str, Any] = {"vm": self.key, "action": "move"}
        if params:
            body["params"] = params

        result = self._manager._client._request("POST", "vm_actions", json_data=body)
        return result if isinstance(result, dict) else None

    def get_console_info(self) -> dict[str, Any]:
        """Get console access information for this VM.

        Returns:
            Dict with console_type, host, port, url, web_url, is_available.
        """
        # Query VM with console status fields using alias syntax
        fields = "name,console,console_status#host as host,console_status#port as port"
        result = self._manager._client._request(
            "GET",
            f"vms/{self.key}",
            params={"fields": fields},
        )

        if not isinstance(result, dict):
            return {"is_available": False}

        console_type = result.get("console", "vnc")
        host = result.get("host")
        port = result.get("port")

        # Build URLs
        url = None
        if host and port:
            protocol = {"vnc": "vnc", "spice": "spice", "serial": "telnet"}.get(console_type, "vnc")
            url = f"{protocol}://{host}:{port}"

        # Web console URL (through VergeOS UI)
        web_url = f"https://{self._manager._client.host}/#/vm-console/{self.key}"

        return {
            "console_type": console_type,
            "host": host,
            "port": port,
            "url": url,
            "web_url": web_url,
            "is_available": bool(host and port),
        }

    @property
    def is_running(self) -> bool:
        """Check if VM is powered on."""
        return bool(self.get("running", False))

    @property
    def is_snapshot(self) -> bool:
        """Check if this is a snapshot (not a running VM)."""
        return bool(self.get("is_snapshot", False))

    @property
    def status(self) -> str:
        """Get VM status (running, stopped, etc.)."""
        return str(self.get("status", "unknown"))

    @property
    def node_name(self) -> str | None:
        """Get the name of the node this VM is running on."""
        return self.get("node_name")

    @property
    def cluster_name(self) -> str | None:
        """Get the name of the cluster this VM belongs to."""
        return self.get("cluster_name")


class VMManager(ResourceManager[VM]):
    """Manager for Virtual Machine operations."""

    _endpoint = "vms"
    _default_fields = VM_DEFAULT_FIELDS

    def __init__(self, client: VergeClient) -> None:
        super().__init__(client)

    def _to_model(self, data: dict[str, Any]) -> VM:
        return VM(data, self)

    def list(
        self,
        filter: str | None = None,  # noqa: A002
        fields: list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        include_snapshots: bool = False,
        **filter_kwargs: Any,
    ) -> list[VM]:
        """List VMs with optional filtering.

        Args:
            filter: OData filter string.
            fields: List of fields to return (defaults to rich field set).
            limit: Maximum number of results.
            offset: Skip this many results.
            include_snapshots: Include VM snapshots (default False).
            **filter_kwargs: Shorthand filter arguments.

        Returns:
            List of VM objects.
        """
        # Use default fields if not specified
        if fields is None:
            fields = self._default_fields

        # Add snapshot filter unless explicitly including snapshots
        if not include_snapshots:
            snapshot_filter = "is_snapshot eq false"
            filter = f"({filter}) and {snapshot_filter}" if filter else snapshot_filter

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
        fields: builtins.list[str] | None = None,
    ) -> VM:
        """Get a single VM by key or name.

        Args:
            key: VM $key (ID).
            name: VM name (will search if key not provided).
            fields: List of fields to return (defaults to rich field set).

        Returns:
            VM object.

        Raises:
            NotFoundError: If VM not found.
            ValueError: If neither key nor name provided.
        """
        if fields is None:
            fields = self._default_fields
        return super().get(key, name=name, fields=fields)

    def list_running(self) -> builtins.list[VM]:
        """List all running VMs."""
        # Filter post-query since API doesn't support filtering on joined fields
        return [vm for vm in self.list() if vm.is_running]

    def list_stopped(self) -> builtins.list[VM]:
        """List all stopped VMs."""
        # Filter post-query since API doesn't support filtering on joined fields
        return [vm for vm in self.list() if not vm.is_running]

    def create(  # type: ignore[override]
        self,
        name: str,
        ram: int = 1024,
        cpu_cores: int = 1,
        description: str = "",
        os_family: str = "linux",
        machine_type: str = "pc-q35-10.0",
        cloudinit_datasource: str | None = None,
        cloud_init: str | dict[str, str] | builtins.list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> VM:
        """Create a new VM.

        Args:
            name: VM name (required).
            ram: RAM in MB (default 1024). Will be rounded UP to nearest 256MB.
            cpu_cores: Number of CPU cores (default 1).
            description: VM description.
            os_family: OS family (linux, windows, freebsd, other).
            machine_type: QEMU machine type.
            cloudinit_datasource: Cloud-init datasource type. Valid values:
                - "ConfigDrive": Config Drive v2 (standard cloud-init config drive).
                - "NoCloud": NoCloud datasource.
                - None: Disabled (default).
                Note: Automatically set to "ConfigDrive" if cloud_init files provided.
            cloud_init: Cloud-init file configuration for VM provisioning. Supports:
                - str: Content for /user-data file (most common case).
                - dict: Mapping of file names to contents,
                    e.g., {"/user-data": "...", "/meta-data": "..."}.
                - list: List of file specs with full control,
                    e.g., [{"name": "/user-data", "contents": "...", "render": "Variables"}].
                When provided, cloudinit_datasource defaults to "ConfigDrive" if not set.
            **kwargs: Additional VM properties.

        Returns:
            Created VM object.

        Example:
            >>> # Simple user-data string (auto-enables ConfigDrive)
            >>> vm = client.vms.create(
            ...     name="web-server",
            ...     cloud_init="#cloud-config\\npackages:\\n  - nginx"
            ... )
            >>>
            >>> # Multiple files as dict
            >>> vm = client.vms.create(
            ...     name="web-server",
            ...     cloud_init={
            ...         "/user-data": "#cloud-config\\npackages:\\n  - nginx",
            ...         "/meta-data": "instance-id: web-1\\nlocal-hostname: web-server"
            ...     }
            ... )
            >>>
            >>> # Full control with render options
            >>> vm = client.vms.create(
            ...     name="web-server",
            ...     cloud_init=[
            ...         {"name": "/user-data", "contents": "...", "render": "Jinja2"},
            ...         {"name": "/meta-data", "contents": "..."}
            ...     ]
            ... )
            >>>
            >>> # Enable cloud-init datasource without files (files added later)
            >>> vm = client.vms.create(
            ...     name="web-server",
            ...     cloudinit_datasource="ConfigDrive"
            ... )
        """
        # Normalize RAM to 256 MB increments
        normalized_ram = ((ram + 255) // 256) * 256
        if normalized_ram != ram:
            logger.info("RAM normalized from %dMB to %dMB", ram, normalized_ram)

        # Map friendly datasource names to API values
        datasource_map = {
            "ConfigDrive": "config_drive_v2",
            "config_drive_v2": "config_drive_v2",
            "NoCloud": "nocloud",
            "nocloud": "nocloud",
            "None": "none",
            "none": "none",
            None: None,
        }

        # Determine cloud-init datasource
        # If cloud_init files provided, default to ConfigDrive
        effective_datasource = cloudinit_datasource
        if cloud_init is not None and cloudinit_datasource is None:
            effective_datasource = "ConfigDrive"
            logger.info("Enabling ConfigDrive datasource for cloud-init files")

        data: dict[str, Any] = {
            "name": name,
            "ram": normalized_ram,
            "cpu_cores": cpu_cores,
            "description": description,
            "os_family": os_family,
            "machine_type": machine_type,
            **kwargs,
        }

        # Add cloudinit_datasource if specified
        if effective_datasource is not None:
            api_datasource = datasource_map.get(effective_datasource)
            if api_datasource is None and effective_datasource not in datasource_map:
                raise ValueError(
                    f"Invalid cloudinit_datasource: {effective_datasource!r}. "
                    "Valid values: 'ConfigDrive', 'NoCloud', or None."
                )
            if api_datasource and api_datasource != "none":
                data["cloudinit_datasource"] = api_datasource

        # Create VM and fetch full data with all fields
        vm = super().create(**data)
        # The API only returns limited fields on create, so fetch the full VM
        vm = self.get(vm.key)

        # Create cloud-init files if provided
        if cloud_init is not None:
            self._create_cloud_init_files(vm.key, cloud_init)

        return vm

    def _create_cloud_init_files(
        self,
        vm_key: int,
        cloud_init: str | dict[str, str] | builtins.list[dict[str, Any]],
    ) -> None:
        """Create cloud-init files for a VM.

        Args:
            vm_key: VM $key (ID).
            cloud_init: Cloud-init configuration (str, dict, or list).
        """
        from pyvergeos.resources.cloudinit_files import CloudInitFileManager

        # Get or create the cloud-init file manager
        cloudinit_mgr = CloudInitFileManager(self._client)

        # Normalize input to list of file specs
        file_specs: builtins.list[dict[str, Any]] = []

        if isinstance(cloud_init, str):
            # Simple string -> /user-data file
            file_specs.append({
                "name": "/user-data",
                "contents": cloud_init,
            })
        elif isinstance(cloud_init, dict):
            # Dict mapping file names to contents
            for file_name, contents in cloud_init.items():
                file_specs.append({
                    "name": file_name,
                    "contents": contents,
                })
        elif isinstance(cloud_init, builtins.list):
            # List of file specs (already in correct format)
            file_specs = cloud_init
        else:
            raise ValueError(
                f"cloud_init must be str, dict, or list, got {type(cloud_init).__name__}"
            )

        # Create each file
        for spec in file_specs:
            if "name" not in spec:
                raise ValueError("Each cloud_init file spec must have a 'name' key")

            cloudinit_mgr.create(
                vm_key=vm_key,
                name=spec["name"],
                contents=spec.get("contents"),
                render=spec.get("render", "No"),
            )
