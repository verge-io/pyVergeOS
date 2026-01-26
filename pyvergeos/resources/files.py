"""File management for VergeOS media catalog."""

from __future__ import annotations

import builtins
import contextlib
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from pyvergeos.exceptions import NotFoundError, ValidationError
from pyvergeos.resources.base import ResourceManager, ResourceObject

logger = logging.getLogger(__name__)

# File type constants
FILE_TYPES = {
    "iso": "ISO",
    "img": "IMG (Raw Disk Image)",
    "qcow": "QCOW (Legacy QEMU)",
    "qcow2": "QCOW2 (QEMU, Xen)",
    "qed": "QED (KVM)",
    "raw": "Raw (Binary Disc Image)",
    "vdi": "VDI (VirtualBox)",
    "vhd": "VHD/VPC (Legacy Hyper-V)",
    "vhdx": "VHDX (Hyper-V)",
    "vmdk": "VMDK (VMware)",
    "ova": "OVA (VMware, VirtualBox)",
    "ovf": "OVF (VMware, VirtualBox)",
    "vmx": "VMX (VMware)",
    "ybvm": "Verge.io Virtual Machine",
    "nvram": "NVRAM",
    "zip": "ZIP",
}

# Chunk size for uploads (256 KB - matches verge-cli)
UPLOAD_CHUNK_SIZE = 262144


class File(ResourceObject):
    """Represents a file in the VergeOS media catalog.

    Files can be ISO images for mounting to VM drives, disk images for import,
    OVA/OVF packages, or other media types.
    """

    @property
    def name(self) -> str:
        """File name."""
        return str(self.get("name", ""))

    @property
    def file_type(self) -> str:
        """File type (iso, qcow2, vmdk, etc.)."""
        return str(self.get("type", "unknown"))

    @property
    def type_display(self) -> str:
        """Human-readable file type."""
        file_type = self.file_type
        return FILE_TYPES.get(file_type, file_type)

    @property
    def description(self) -> str:
        """File description."""
        return str(self.get("description", ""))

    @property
    def size_bytes(self) -> int:
        """File size in bytes."""
        return int(self.get("filesize") or 0)

    @property
    def size_gb(self) -> float:
        """File size in GB."""
        return round(self.size_bytes / 1073741824, 3) if self.size_bytes else 0.0

    @property
    def allocated_bytes(self) -> int:
        """Allocated storage in bytes."""
        return int(self.get("allocated_bytes") or 0)

    @property
    def allocated_gb(self) -> float:
        """Allocated storage in GB."""
        return round(self.allocated_bytes / 1073741824, 3) if self.allocated_bytes else 0.0

    @property
    def used_bytes(self) -> int:
        """Used storage in bytes (actual on-disk size)."""
        return int(self.get("used_bytes") or 0)

    @property
    def used_gb(self) -> float:
        """Used storage in GB."""
        return round(self.used_bytes / 1073741824, 3) if self.used_bytes else 0.0

    @property
    def preferred_tier(self) -> int | None:
        """Preferred storage tier (1-5)."""
        tier = self.get("preferred_tier")
        if tier is not None:
            return int(tier)
        return None

    @property
    def modified(self) -> datetime | None:
        """Last modification timestamp."""
        ts = self.get("modified")
        if ts:
            return datetime.fromtimestamp(int(ts), tz=timezone.utc)
        return None

    @property
    def creator(self) -> str:
        """Username who created the file."""
        return str(self.get("creator", ""))

    def __repr__(self) -> str:
        return f"<File key={self.get('$key', '?')} name={self.name!r} type={self.file_type}>"


class FileManager(ResourceManager[File]):
    """Manages files in the VergeOS media catalog.

    Files in the media catalog can be used as:
    - ISO images for VM CD-ROM drives
    - Disk images for VM drive import
    - OVA/OVF packages for VM import

    Example:
        >>> files = client.files.list(file_type="iso")
        >>> for f in files:
        ...     print(f"{f.name}: {f.size_gb} GB")

        >>> # Upload a file
        >>> uploaded = client.files.upload("/path/to/image.iso", tier=1)

        >>> # Download a file
        >>> client.files.download(name="ubuntu.iso", destination="/tmp/")
    """

    _endpoint = "files"

    def _to_model(self, data: dict[str, Any]) -> File:
        return File(data, self)

    def list(  # noqa: A003
        self,
        filter: str | None = None,  # noqa: A002
        fields: builtins.list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        file_type: str | builtins.list[str] | None = None,
        **filter_kwargs: Any,
    ) -> builtins.list[File]:
        """List files in the media catalog.

        Args:
            filter: OData filter string.
            fields: List of fields to return.
            limit: Maximum number of results.
            offset: Skip this many results.
            file_type: Filter by file type(s) - "iso", "qcow2", "vmdk", etc.
            **filter_kwargs: Additional filter arguments.

        Returns:
            List of File objects.

        Example:
            >>> # List all ISO files
            >>> isos = client.files.list(file_type="iso")

            >>> # List importable disk images
            >>> images = client.files.list(file_type=["ova", "ovf", "vmdk", "qcow2"])
        """
        # Default fields for useful file information
        if fields is None:
            fields = [
                "$key",
                "name",
                "type",
                "description",
                "filesize",
                "allocated_bytes",
                "used_bytes",
                "preferred_tier",
                "modified",
                "creator",
            ]

        results = super().list(
            filter=filter, fields=fields, limit=limit, offset=offset, **filter_kwargs
        )

        # Apply file_type filter client-side (more flexible)
        if file_type:
            if isinstance(file_type, str):
                file_type = [file_type]
            results = [f for f in results if f.file_type in file_type]

        return results

    def get(
        self,
        key: int | None = None,
        *,
        name: str | None = None,
        fields: builtins.list[str] | None = None,
    ) -> File:
        """Get a file by key or name.

        Args:
            key: File $key (ID).
            name: File name.
            fields: List of fields to return.

        Returns:
            File object.

        Raises:
            NotFoundError: If file not found.
            ValueError: If neither key nor name provided.
        """
        return super().get(key, name=name, fields=fields)

    def upload(
        self,
        path: str | Path,
        name: str | None = None,
        description: str | None = None,
        tier: int | None = None,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> File:
        """Upload a file to the media catalog.

        Args:
            path: Local path to the file to upload.
            name: Name for the file in VergeOS (defaults to local filename).
            description: Optional description.
            tier: Preferred storage tier (1-5).
            progress_callback: Optional callback(bytes_uploaded, total_bytes).

        Returns:
            Uploaded File object.

        Raises:
            FileNotFoundError: If local file doesn't exist.
            ValidationError: If upload fails.

        Example:
            >>> def show_progress(uploaded, total):
            ...     pct = (uploaded / total) * 100
            ...     print(f"\\rUploading: {pct:.1f}%", end="")
            >>> client.files.upload("/path/to/image.iso", tier=1, progress_callback=show_progress)
        """
        file_path = Path(path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        if not file_path.is_file():
            raise ValidationError(f"Not a file: {path}")

        upload_name = name or file_path.name
        file_size = file_path.stat().st_size

        logger.info("Uploading '%s' (%d bytes) as '%s'", file_path.name, file_size, upload_name)

        # Get connection details
        connection = self._client._connection
        if connection is None:
            from pyvergeos.exceptions import NotConnectedError

            raise NotConnectedError("Not connected to VergeOS")

        session = connection._session
        if session is None:
            from pyvergeos.exceptions import NotConnectedError

            raise NotConnectedError("Session not initialized")

        # Step 1: Create file entry with POST
        create_body: dict[str, Any] = {
            "allocated_bytes": str(file_size),
            "name": upload_name,
        }
        if description:
            create_body["description"] = description
        if tier:
            create_body["preferred_tier"] = str(tier)

        url = f"{connection.api_base_url}/files"
        response = session.post(url, json=create_body, timeout=30)

        if response.status_code not in (200, 201):
            raise ValidationError(f"Failed to create file entry: {response.text}")

        response_data = response.json()
        file_id = response_data.get("$key")
        if not file_id:
            # Try extracting from location
            location = response_data.get("location", "")
            if location:
                file_id = location.rstrip("/").split("/")[-1]

        if not file_id:
            raise ValidationError("Could not determine file ID from upload response")

        logger.debug("File entry created with ID: %s", file_id)

        # Step 2: Upload file in chunks using PUT
        try:
            with open(file_path, "rb") as f:
                offset = 0
                while offset < file_size:
                    chunk = f.read(UPLOAD_CHUNK_SIZE)
                    if not chunk:
                        break

                    chunk_url = f"{url}/{file_id}?filepos={offset}"
                    chunk_response = session.put(
                        chunk_url,
                        data=chunk,
                        headers={"Content-Type": "application/octet-stream"},
                        timeout=120,
                    )

                    if chunk_response.status_code not in (200, 201, 204):
                        raise ValidationError(f"Chunk upload failed: {chunk_response.text}")

                    offset += len(chunk)

                    if progress_callback:
                        progress_callback(offset, file_size)

            logger.info("Upload completed: %s", upload_name)

            # Return the uploaded file
            return self.get(key=int(file_id))

        except Exception as e:
            # Try to clean up the partial upload
            logger.error("Upload failed, attempting cleanup: %s", e)
            with contextlib.suppress(Exception):
                self.delete(int(file_id))
            raise

    def download(
        self,
        key: int | None = None,
        *,
        name: str | None = None,
        destination: str | Path = ".",
        filename: str | None = None,
        overwrite: bool = False,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> Path:
        """Download a file from the media catalog.

        Args:
            key: File $key (ID).
            name: File name (alternative to key).
            destination: Directory or full path for downloaded file.
            filename: Override the filename (defaults to file's name).
            overwrite: Whether to overwrite existing files.
            progress_callback: Optional callback(bytes_downloaded, total_bytes).

        Returns:
            Path to the downloaded file.

        Raises:
            NotFoundError: If file not found.
            FileExistsError: If destination exists and overwrite=False.
            ValueError: If neither key nor name provided.

        Example:
            >>> path = client.files.download(name="ubuntu.iso", destination="/tmp/")
            >>> print(f"Downloaded to: {path}")
        """
        # Resolve file info
        file_obj = self.get(key=key, name=name)
        file_key = file_obj.key
        download_name = filename or file_obj.name

        # Determine output path
        dest_path = Path(destination)
        output_path = dest_path / download_name if dest_path.is_dir() else dest_path

        # Check if exists
        if output_path.exists() and not overwrite:
            raise FileExistsError(f"File already exists: {output_path}")

        # Ensure parent directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Get connection details
        connection = self._client._connection
        if connection is None:
            from pyvergeos.exceptions import NotConnectedError

            raise NotConnectedError("Not connected to VergeOS")

        session = connection._session
        if session is None:
            from pyvergeos.exceptions import NotConnectedError

            raise NotConnectedError("Session not initialized")

        # Build download URL
        encoded_name = download_name.replace(" ", "%20")
        download_url = f"{connection.api_base_url}/files/{file_key}?download=1&asname={encoded_name}"

        logger.info("Downloading '%s' to '%s'", download_name, output_path)

        # Stream download
        response = session.get(download_url, stream=True, timeout=30)
        if response.status_code != 200:
            raise NotFoundError(f"Download failed: {response.text}")

        total_size = file_obj.size_bytes
        downloaded = 0

        with open(output_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=UPLOAD_CHUNK_SIZE):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if progress_callback and total_size:
                        progress_callback(downloaded, total_size)

        logger.info("Download completed: %s", output_path)
        return output_path

    def delete(self, key: int) -> None:
        """Delete a file from the media catalog.

        Args:
            key: File $key (ID).

        Raises:
            NotFoundError: If file not found.
            ValidationError: If file is in use by VM drives.

        Note:
            Files that are referenced by VM drives cannot be deleted
            until the references are removed.
        """
        super().delete(key)
        logger.info("Deleted file with key %d", key)
