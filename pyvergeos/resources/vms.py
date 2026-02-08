"""Virtual Machine resource manager."""

from __future__ import annotations

import builtins
import logging
from typing import TYPE_CHECKING, Any

from pyvergeos.resources.base import ResourceManager, ResourceObject

if TYPE_CHECKING:
    from pyvergeos.client import VergeClient
    from pyvergeos.resources.cloudinit_files import VMCloudInitFileManager
    from pyvergeos.resources.devices import DeviceManager
    from pyvergeos.resources.drives import DriveManager
    from pyvergeos.resources.machine_stats import (
        MachineLogManager,
        MachineStatsManager,
        MachineStatusManager,
    )
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
    "cloudinit_datasource",
]


class VM(ResourceObject):
    """Virtual Machine resource object."""

    _drives: DriveManager | None = None
    _nics: NICManager | None = None
    _snapshots: VMSnapshotManager | None = None
    _cloudinit_files: VMCloudInitFileManager | None = None
    _stats: MachineStatsManager | None = None
    _machine_status: MachineStatusManager | None = None
    _machine_logs: MachineLogManager | None = None
    _devices: DeviceManager | None = None

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

    @property
    def cloudinit_files(self) -> VMCloudInitFileManager:
        """Access cloud-init files for this VM."""
        if self._cloudinit_files is None:
            from pyvergeos.resources.cloudinit_files import VMCloudInitFileManager

            self._cloudinit_files = VMCloudInitFileManager(self._manager._client, self)
        return self._cloudinit_files

    def set_cloudinit_datasource(self, datasource: str) -> None:
        """Set the cloud-init datasource for this VM.

        The datasource controls whether VergeOS attaches a virtual CD-ROM
        with cloud-init files to the VM. This is required for cloud-init
        files (Linux) or unattend.xml (Windows) to be delivered to the guest.

        Args:
            datasource: Datasource type. Valid values:
                - "nocloud" or "NoCloud": Enable NoCloud datasource
                - "config_drive_v2" or "ConfigDrive": Enable Config Drive v2
                - "none" or "": Disable cloud-init datasource

        Example:
            >>> vm = client.vms.get(name="my-vm")
            >>> # Enable cloud-init delivery
            >>> vm.set_cloudinit_datasource("nocloud")
            >>> # Create cloud-init files
            >>> vm.cloudinit_files.create(name="/user-data", contents="...")
            >>> # Disable cloud-init delivery
            >>> vm.set_cloudinit_datasource("none")
        """
        # Normalize datasource value to API format
        datasource_map = {
            "nocloud": "nocloud",
            "config_drive_v2": "config_drive_v2",
            "configdrive": "config_drive_v2",
            "none": "none",
            "": "none",
        }
        api_value = datasource_map.get(datasource.lower(), datasource.lower())

        # Update VM via API
        self._manager._client._request(
            "PUT",
            f"vms/{self.key}",
            json_data={"cloudinit_datasource": api_value},
        )

        # Update local cache (VM is a dict subclass)
        self["cloudinit_datasource"] = api_value

    @property
    def machine_key(self) -> int:
        """Get the underlying machine key for this VM."""
        machine = self.get("machine")
        if machine is None:
            raise ValueError("VM has no machine key")
        return int(machine)

    @property
    def stats(self) -> MachineStatsManager:
        """Access performance stats for this VM.

        Example:
            >>> stats = vm.stats.get()
            >>> print(f"CPU: {stats.total_cpu}%, RAM: {stats.ram_used_mb}MB")

            >>> # Get stats history
            >>> history = vm.stats.history_short(limit=100)
        """
        if self._stats is None:
            from pyvergeos.resources.machine_stats import MachineStatsManager

            self._stats = MachineStatsManager(self._manager._client, self.machine_key)
        return self._stats

    @property
    def machine_status(self) -> MachineStatusManager:
        """Access detailed operational status for this VM.

        Example:
            >>> status = vm.machine_status.get()
            >>> print(f"Status: {status.status}, Node: {status.node_name}")
        """
        if self._machine_status is None:
            from pyvergeos.resources.machine_stats import MachineStatusManager

            self._machine_status = MachineStatusManager(self._manager._client, self.machine_key)
        return self._machine_status

    @property
    def machine_logs(self) -> MachineLogManager:
        """Access log entries for this VM.

        Example:
            >>> logs = vm.machine_logs.list(limit=20)
            >>> errors = vm.machine_logs.list(errors_only=True)
        """
        if self._machine_logs is None:
            from pyvergeos.resources.machine_stats import MachineLogManager

            self._machine_logs = MachineLogManager(self._manager._client, self.machine_key)
        return self._machine_logs

    @property
    def devices(self) -> DeviceManager:
        """Access devices (GPU, TPM, USB, PCI, SR-IOV) attached to this VM.

        Returns:
            DeviceManager scoped to this VM.

        Example:
            >>> # List all devices
            >>> devices = vm.devices.list()

            >>> # List vGPUs only
            >>> vgpus = vm.devices.list(device_type="node_nvidia_vgpu_devices")

            >>> # Attach a vGPU
            >>> device = vm.devices.create_vgpu(
            ...     resource_group=vgpu_pool.key,
            ...     frame_rate_limit=60,
            ... )
        """
        if self._devices is None:
            from pyvergeos.resources.devices import DeviceManager

            self._devices = DeviceManager(self._manager._client, self.machine_key)
        return self._devices

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

    def migrate(self, preferred_node: int | None = None) -> dict[str, Any] | None:
        """Live migrate VM to another node while keeping it running.

        Args:
            preferred_node: Target node $key. If None, auto-selects based on
                resource balancing.

        Returns:
            Migration task information.

        Note:
            The VM must be running for live migration. Migration progress can be
            monitored via the VM status field.
        """
        body: dict[str, Any] = {"vm": self.key, "action": "migrate"}
        if preferred_node is not None:
            body["params"] = {"preferred_node": preferred_node}

        result = self._manager._client._request("POST", "vm_actions", json_data=body)
        return result if isinstance(result, dict) else None

    def hibernate(self) -> dict[str, Any] | None:
        """Hibernate the VM to disk.

        Saves the VM's memory state to disk and powers off. The VM can be resumed
        later by powering it on, which will restore the memory state.

        Returns:
            Hibernate task information.
        """
        result = self._manager._client._request(
            "POST", "vm_actions", json_data={"vm": self.key, "action": "hibernate"}
        )
        return result if isinstance(result, dict) else None

    def restore(
        self,
        snapshot: int,
        preserve_macs: bool = False,
        name: str | None = None,
    ) -> dict[str, Any] | None:
        """Restore VM from a snapshot.

        Args:
            snapshot: Snapshot $key to restore from.
            preserve_macs: Keep original MAC addresses (default False).
            name: Name for restored VM if creating a clone. If None, overwrites
                the current VM.

        Returns:
            Restore task information.

        Warning:
            If name is not provided, this will overwrite the current VM. The VM
            should be powered off before restoring.
        """
        params: dict[str, Any] = {"snapshot": snapshot, "preserve_macs": preserve_macs}
        if name is not None:
            params["name"] = name

        result = self._manager._client._request(
            "POST",
            "vm_actions",
            json_data={"vm": self.key, "action": "restore", "params": params},
        )
        return result if isinstance(result, dict) else None

    def hotplug_drive(
        self,
        name: str,
        size: int,
        interface: str = "virtio-scsi",
        media: str = "disk",
        tier: int = 1,
    ) -> dict[str, Any] | None:
        """Hot-add a drive to a running VM.

        Args:
            name: Drive name.
            size: Disk size in bytes.
            interface: Drive interface type (default "virtio-scsi").
                Options: virtio, virtio-scsi, ide, ahci, nvme, etc.
            media: Media type (default "disk").
            tier: Preferred storage tier (1-5, default 1).

        Returns:
            Hotplug task information.

        Note:
            The VM must be running and have allow_hotplug enabled.
        """
        params: dict[str, Any] = {
            "name": name,
            "disksize": size,
            "interface": interface,
            "media": media,
            "preferred_tier": str(tier),
        }

        result = self._manager._client._request(
            "POST",
            "vm_actions",
            json_data={"vm": self.key, "action": "hotplugdrive", "params": params},
        )
        return result if isinstance(result, dict) else None

    def hotplug_nic(
        self,
        name: str,
        network: int,
        interface: str = "virtio",
    ) -> dict[str, Any] | None:
        """Hot-add a NIC to a running VM.

        Args:
            name: NIC name.
            network: Network $key to connect to.
            interface: NIC interface type (default "virtio").
                Options: virtio, e1000, e1000e, rtl8139, vmxnet3, etc.

        Returns:
            Hotplug task information.

        Note:
            The VM must be running and have allow_hotplug enabled.
        """
        params: dict[str, Any] = {
            "name": name,
            "vnet": network,
            "interface": interface,
        }

        result = self._manager._client._request(
            "POST",
            "vm_actions",
            json_data={"vm": self.key, "action": "hotplugnic", "params": params},
        )
        return result if isinstance(result, dict) else None

    def tag(self, tag_key: int) -> None:
        """Add a tag to this VM.

        Args:
            tag_key: Tag $key to add.

        Example:
            >>> # Get a tag by name and add it
            >>> tag = client.tags.get(name="Production", category_name="Environment")
            >>> vm.tag(tag.key)
        """
        self._manager._client.tags.members(tag_key).add_vm(self.key)

    def untag(self, tag_key: int) -> None:
        """Remove a tag from this VM.

        Args:
            tag_key: Tag $key to remove.

        Example:
            >>> vm.untag(tag.key)
        """
        self._manager._client.tags.members(tag_key).remove_vm(self.key)

    def get_tags(self) -> list[dict[str, Any]]:
        """Get all tags assigned to this VM.

        Returns:
            List of tag info dictionaries with tag_key, tag_name, category_name.

        Example:
            >>> for tag_info in vm.get_tags():
            ...     print(f"{tag_info['category_name']}: {tag_info['tag_name']}")
        """
        # Query tag_members for this VM
        members = self._manager._client._request(
            "GET",
            "tag_members",
            params={
                "filter": f"member eq 'vms/{self.key}'",
                "fields": "$key,tag,tag#name as tag_name,tag#category#name as category_name",
            },
        )
        if not isinstance(members, list):
            return []
        return [
            {
                "tag_key": m.get("tag"),
                "tag_name": m.get("tag_name"),
                "category_name": m.get("category_name"),
            }
            for m in members
        ]

    def _get_current_user_key(self) -> int:
        """Get the current user's key by looking up the username.

        Returns:
            User $key.

        Raises:
            ValueError: If user cannot be found.
        """
        connection = self._manager._client._connection
        if connection is None:
            raise ValueError("Client not connected")
        username = connection.username
        if not username:
            raise ValueError("Could not determine current username")

        # Look up user by name
        users = self._manager._client._request(
            "GET",
            "users",
            params={"filter": f"name eq '{username}'", "fields": "$key,name", "limit": 1},
        )
        if not isinstance(users, list) or not users:
            raise ValueError(f"Could not find user '{username}'")

        user_key = users[0].get("$key")
        if user_key is None:
            raise ValueError(f"User '{username}' has no key")

        return int(user_key)

    def favorite(self) -> None:
        """Add this VM to the current user's favorites.

        Example:
            >>> vm = client.vms.get(name="web-server")
            >>> vm.favorite()
        """
        user_key = self._get_current_user_key()

        # Create favorite entry
        self._manager._client._request(
            "POST",
            "vm_favorites",
            json_data={"vm": self.key, "user": user_key},
        )

    def unfavorite(self) -> None:
        """Remove this VM from the current user's favorites.

        Example:
            >>> vm = client.vms.get(name="web-server")
            >>> vm.unfavorite()
        """
        user_key = self._get_current_user_key()

        # Find and delete the favorite entry
        favorites = self._manager._client._request(
            "GET",
            "vm_favorites",
            params={"filter": f"vm eq {self.key} and user eq {user_key}"},
        )
        if isinstance(favorites, list) and favorites:
            fav_key = favorites[0].get("$key")
            if fav_key:
                self._manager._client._request("DELETE", f"vm_favorites/{fav_key}")

    def is_favorite(self) -> bool:
        """Check if this VM is in the current user's favorites.

        Returns:
            True if the VM is a favorite, False otherwise.
        """
        try:
            user_key = self._get_current_user_key()
        except ValueError:
            return False

        # Check for favorite entry
        favorites = self._manager._client._request(
            "GET",
            "vm_favorites",
            params={"filter": f"vm eq {self.key} and user eq {user_key}"},
        )
        return isinstance(favorites, list) and len(favorites) > 0

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
            cloudinit_datasource: Cloud-init datasource type. Valid values are
                "ConfigDrive" (Config Drive v2), "NoCloud", or None (disabled, default).
                Automatically set to "ConfigDrive" if cloud_init files are provided.
            cloud_init: Cloud-init file configuration for VM provisioning.
                Can be a string (content for /user-data), a dict mapping file names
                to contents (e.g., {"/user-data": "...", "/meta-data": "..."}), or
                a list of file specs with full control. When provided,
                cloudinit_datasource defaults to "ConfigDrive" if not set.
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
            file_specs.append(
                {
                    "name": "/user-data",
                    "contents": cloud_init,
                }
            )
        elif isinstance(cloud_init, dict):
            # Dict mapping file names to contents
            for file_name, contents in cloud_init.items():
                file_specs.append(
                    {
                        "name": file_name,
                        "contents": contents,
                    }
                )
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
