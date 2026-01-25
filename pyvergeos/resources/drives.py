"""VM Drive resource manager."""

from __future__ import annotations

import builtins
import logging
from typing import TYPE_CHECKING, Any

from pyvergeos.resources.base import ResourceManager, ResourceObject

if TYPE_CHECKING:
    from pyvergeos.client import VergeClient
    from pyvergeos.resources.vms import VM

logger = logging.getLogger(__name__)

# Default fields for drives
DRIVE_DEFAULT_FIELDS = [
    "$key",
    "name",
    "orderid",
    "interface",
    "media",
    "description",
    "enabled",
    "serial",
    "preferred_tier",
    "readonly",
    "disksize",
    "used_bytes",
    "media_source",
    "machine",
    "status#status as status",
    "status#display(status) as status_display",
    "media_source#name as media_file",
    "media_source#allocated_bytes as allocated_bytes",
]

# Interface display names
INTERFACE_DISPLAY_MAP = {
    "virtio": "Virtio (Legacy)",
    "ide": "IDE",
    "ahci": "SATA (AHCI)",
    "nvme": "NVMe",
    "virtio-scsi": "Virtio-SCSI",
    "virtio-scsi-dedicated": "Virtio-SCSI (Dedicated)",
    "lsi53c895a": "LSI SCSI",
    "megasas": "LSI MegaRAID SAS",
    "megasas-gen2": "LSI MegaRAID SAS 2",
    "usb": "USB",
}

# Media display names
MEDIA_DISPLAY_MAP = {
    "cdrom": "CD-ROM",
    "disk": "Disk",
    "efidisk": "EFI Disk",
    "import": "Import Disk",
    "9p": "Pass-Through (9P)",
    "dir": "Pass-Through (Directory)",
    "clone": "Clone Disk",
    "nonpersistent": "Non-Persistent",
}


class Drive(ResourceObject):
    """VM Drive resource object."""

    @property
    def size_gb(self) -> float:
        """Get disk size in GB."""
        size_bytes = self.get("disksize") or self.get("allocated_bytes") or 0
        return round(size_bytes / (1024**3), 2)

    @property
    def used_gb(self) -> float:
        """Get used space in GB."""
        used_bytes = self.get("used_bytes") or 0
        return round(used_bytes / (1024**3), 2)

    @property
    def interface_display(self) -> str:
        """Get friendly interface name."""
        interface = self.get("interface", "")
        return INTERFACE_DISPLAY_MAP.get(interface, str(interface))

    @property
    def media_display(self) -> str:
        """Get friendly media type name."""
        media = self.get("media", "")
        return MEDIA_DISPLAY_MAP.get(media, str(media))

    @property
    def is_enabled(self) -> bool:
        """Check if drive is enabled."""
        return bool(self.get("enabled", True))

    @property
    def is_readonly(self) -> bool:
        """Check if drive is read-only."""
        return bool(self.get("readonly", False))


class DriveManager(ResourceManager[Drive]):
    """Manager for VM Drive operations.

    This manager is accessed through a VM object's drives property.
    """

    _endpoint = "machine_drives"
    _default_fields = DRIVE_DEFAULT_FIELDS

    def __init__(self, client: VergeClient, vm: VM) -> None:
        super().__init__(client)
        self._vm = vm

    @property
    def machine_key(self) -> int:
        """Get the machine key for this VM."""
        machine = self._vm.get("machine")
        if machine is None:
            raise ValueError("VM has no machine key")
        return int(machine)

    def _to_model(self, data: dict[str, Any]) -> Drive:
        return Drive(data, self)

    def list(  # type: ignore[override]  # noqa: A003
        self,
        filter: str | None = None,  # noqa: A002
        fields: list[str] | None = None,
        media: str | None = None,
        **kwargs: Any,
    ) -> list[Drive]:
        """List drives for this VM.

        Args:
            filter: Additional OData filter string.
            fields: List of fields to return.
            media: Filter by media type (disk, cdrom, efidisk).
            **kwargs: Additional filter arguments.

        Returns:
            List of Drive objects.
        """
        # Use default fields if not specified
        if fields is None:
            fields = self._default_fields

        # Build filter for this VM's machine
        machine_filter = f"machine eq {self.machine_key}"
        if media:
            machine_filter = f"{machine_filter} and media eq '{media}'"
        if filter:
            machine_filter = f"{machine_filter} and ({filter})"

        params: dict[str, Any] = {
            "filter": machine_filter,
            "fields": ",".join(fields),
            "sort": "+orderid",
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
    ) -> Drive:
        """Get a drive by key or name.

        Args:
            key: Drive $key (ID).
            name: Drive name.
            fields: List of fields to return.

        Returns:
            Drive object.

        Raises:
            NotFoundError: If drive not found.
            ValueError: If neither key nor name provided.
        """
        if fields is None:
            fields = self._default_fields

        if key is not None:
            params: dict[str, Any] = {"fields": ",".join(fields)}
            response = self._client._request("GET", f"{self._endpoint}/{key}", params=params)
            if response is None:
                from pyvergeos.exceptions import NotFoundError

                raise NotFoundError(f"Drive {key} not found")
            if not isinstance(response, dict):
                from pyvergeos.exceptions import NotFoundError

                raise NotFoundError(f"Drive {key} returned invalid response")
            return self._to_model(response)

        if name is not None:
            drives = self.list(filter=f"name eq '{name}'", fields=fields)
            if not drives:
                from pyvergeos.exceptions import NotFoundError

                raise NotFoundError(f"Drive with name '{name}' not found")
            return drives[0]

        raise ValueError("Either key or name must be provided")

    def create(  # type: ignore[override]
        self,
        size_gb: int | None = None,
        name: str | None = None,
        interface: str = "virtio-scsi",
        media: str = "disk",
        tier: int | None = None,
        description: str = "",
        readonly: bool = False,
        enabled: bool = True,
        media_source: int | str | None = None,
    ) -> Drive:
        """Create a new drive for this VM.

        Args:
            size_gb: Disk size in GB (required for disk media).
            name: Drive name (optional, auto-generated if not provided).
            interface: Drive interface type (virtio-scsi, nvme, ahci, ide, etc.).
            media: Media type (disk, cdrom, efidisk).
            tier: Preferred storage tier (1-5).
            description: Drive description.
            readonly: Make drive read-only.
            enabled: Enable drive (default True).
            media_source: File key (int) or name (str) for CD-ROM media source.
                Used to attach ISO or other media files.

        Returns:
            Created Drive object.

        Raises:
            ValueError: If size_gb not provided for disk media.
            ValueError: If media_source file not found (when passed as string).
        """
        if media == "disk" and size_gb is None:
            raise ValueError("size_gb is required for disk media")

        body: dict[str, Any] = {
            "machine": self.machine_key,
            "interface": interface,
            "media": media,
            "enabled": enabled,
        }

        if name:
            body["name"] = name
        if size_gb is not None:
            body["disksize"] = int(size_gb) * (1024**3)  # Convert to bytes
        if tier is not None:
            body["preferred_tier"] = str(tier)
        if description:
            body["description"] = description
        if readonly:
            body["readonly"] = True

        # Resolve media_source by name if string provided
        if media_source is not None:
            if isinstance(media_source, str):
                # Look up file by name
                response = self._client._request(
                    "GET",
                    "files",
                    params={"filter": f"name eq '{media_source}'", "fields": "$key,name"},
                )
                if not response:
                    raise ValueError(f"Media file '{media_source}' not found")
                if isinstance(response, list):
                    if not response:
                        raise ValueError(f"Media file '{media_source}' not found")
                    media_source = response[0].get("$key")
                else:
                    media_source = response.get("$key")
            body["media_source"] = int(media_source)  # type: ignore[arg-type]

        response = self._client._request("POST", self._endpoint, json_data=body)
        if response is None:
            raise ValueError("No response from create operation")
        if not isinstance(response, dict):
            raise ValueError("Create operation returned invalid response")
        # Fetch the full drive data with all fields
        drive = self._to_model(response)
        return self.get(drive.key)

    def delete(self, key: int) -> None:
        """Delete a drive.

        Args:
            key: Drive $key (ID).

        Note:
            VM should typically be powered off before removing drives.
        """
        self._client._request("DELETE", f"{self._endpoint}/{key}")

    def update(self, key: int, **kwargs: Any) -> Drive:
        """Update a drive.

        Args:
            key: Drive $key (ID).
            **kwargs: Fields to update.

        Returns:
            Updated Drive object.
        """
        response = self._client._request("PUT", f"{self._endpoint}/{key}", json_data=kwargs)
        if response is None:
            return self.get(key)
        if not isinstance(response, dict):
            return self.get(key)
        return self._to_model(response)

    def import_drive(
        self,
        file_key: int | None = None,
        file_name: str | None = None,
        name: str | None = None,
        interface: str = "virtio-scsi",
        tier: int | None = None,
        preserve_drive_format: bool = False,
        enabled: bool = True,
    ) -> Drive:
        """Import a disk image file as a new drive.

        Creates a new drive by importing from a disk image file (VMDK, QCOW2,
        VHD, VHDX, OVA, OVF, etc.). The file must already be uploaded to the
        VergeOS media catalog.

        This is the recommended way to import VMs from OVA/OVF/VMDK files:
        1. Create a new VM with client.vms.create()
        2. Import the disk(s) with vm.drives.import_drive()

        Args:
            file_key: The $key (ID) of the disk image file to import.
            file_name: The name of the disk image file to import.
                One of file_key or file_name is required.
            name: Name for the new drive. If not specified, auto-generated.
            interface: Drive interface type. Default is 'virtio-scsi'.
                Valid values: virtio, ide, ahci, nvme, virtio-scsi,
                virtio-scsi-dedicated.
            tier: Preferred storage tier (1-5).
            preserve_drive_format: Keep the original drive format instead of
                converting to raw. Default is False.
            enabled: Enable the drive. Default is True.

        Returns:
            Created Drive object.

        Raises:
            ValueError: If neither file_key nor file_name is provided.
            ValueError: If file not found (when looking up by name).

        Example:
            >>> # Import a QCOW2 disk image
            >>> vm = client.vms.get(name="NewServer")
            >>> drive = vm.drives.import_drive(
            ...     file_name="debian-12-generic-amd64.qcow2",
            ...     interface="virtio-scsi",
            ...     tier=1,
            ... )

            >>> # Import from an OVA file's disk
            >>> vm = client.vms.create(name="ImportedVM", cpu_cores=2, ram=4096)
            >>> drive = vm.drives.import_drive(file_name="server-disk.vmdk")

        Note:
            Supported import formats: VMDK, QCOW2, VHD, VHDX, VDI, RAW, OVA, OVF.
            The import process converts the disk to VergeOS format unless
            preserve_drive_format is True.
        """
        if file_key is None and file_name is None:
            raise ValueError("Either file_key or file_name must be provided")

        # Resolve file by name if needed
        resolved_file_key = file_key
        if file_key is None and file_name is not None:
            response = self._client._request(
                "GET",
                "files",
                params={"filter": f"name eq '{file_name}'", "fields": "$key,name"},
            )
            if not response:
                raise ValueError(f"File '{file_name}' not found in media catalog")
            if isinstance(response, list):
                if not response:
                    raise ValueError(f"File '{file_name}' not found in media catalog")
                resolved_file_key = response[0].get("$key")
            else:
                resolved_file_key = response.get("$key")

        # Build request body for import drive
        body: dict[str, Any] = {
            "machine": self.machine_key,
            "interface": interface,
            "media": "import",
            "media_source": int(resolved_file_key) if resolved_file_key else 0,
            "enabled": enabled,
            "preserve_drive_format": preserve_drive_format,
        }

        if name:
            body["name"] = name

        if tier is not None:
            body["preferred_tier"] = str(tier)

        response = self._client._request("POST", self._endpoint, json_data=body)
        if response is None:
            raise ValueError("No response from import operation")
        if not isinstance(response, dict):
            raise ValueError("Import operation returned invalid response")

        # Fetch the full drive data with all fields
        drive = self._to_model(response)
        return self.get(drive.key)
