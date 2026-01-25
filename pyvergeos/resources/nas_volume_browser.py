"""NAS volume file browser resources."""

from __future__ import annotations

import builtins
import time
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from pyvergeos.exceptions import APIError, NotFoundError, VergeTimeoutError

if TYPE_CHECKING:
    from pyvergeos.client import VergeClient


class NASVolumeFile(dict[str, Any]):
    """NAS volume file/directory entry.

    Represents a file or directory within a NAS volume.
    This is a read-only data object returned by the volume browser.

    Attributes:
        name: File or directory name.
        type: Entry type ('file' or 'directory').
        size: Size in bytes.
        date: Modification timestamp (Unix).
        n_name: Normalized name (lowercase).
    """

    def __init__(self, data: dict[str, Any]) -> None:
        """Initialize with data dict."""
        super().__init__(data)

    def __getattr__(self, name: str) -> Any:
        """Allow attribute-style access to dict items."""
        try:
            return self[name]
        except KeyError:
            raise AttributeError(
                f"'{type(self).__name__}' has no attribute '{name}'"
            ) from None

    @property
    def name(self) -> str:
        """Get the file/directory name."""
        return str(self.get("name", ""))

    @property
    def is_directory(self) -> bool:
        """Check if this entry is a directory."""
        entry_type = self.get("type", "")
        return entry_type in ("directory", "d")

    @property
    def is_file(self) -> bool:
        """Check if this entry is a file."""
        return not self.is_directory

    @property
    def size(self) -> int:
        """Get the size in bytes."""
        return int(self.get("size", 0))

    @property
    def size_display(self) -> str:
        """Get human-readable size."""
        return _format_file_size(self.size)

    @property
    def modified(self) -> datetime | None:
        """Get the modification time as datetime."""
        timestamp = self.get("date")
        if timestamp:
            return datetime.fromtimestamp(int(timestamp), tz=timezone.utc)
        return None

    @property
    def full_path(self) -> str:
        """Get the full path of this entry."""
        return str(self.get("_full_path", f"/{self.name}"))

    @property
    def volume_key(self) -> str | None:
        """Get the volume key this entry belongs to."""
        return self.get("_volume_key")


class NASVolumeFileManager:
    """Manager for browsing NAS volume files.

    This manager provides methods to browse files and directories within
    a NAS volume. It uses the asynchronous volume_browser API.

    Note:
        The NAS service VM must be running to browse volumes.
        The volume must be mounted (enabled).

    Example:
        >>> # Browse root directory
        >>> files = client.nas_volumes.files(vol.key).list()
        >>> for f in files:
        ...     print(f"{f.name}: {f.size_display}")

        >>> # Browse a subdirectory
        >>> files = client.nas_volumes.files(vol.key).list("/documents")

        >>> # Get a specific file
        >>> file = client.nas_volumes.files(vol.key).get("/documents/report.pdf")
    """

    _endpoint = "volume_browser"

    def __init__(
        self, client: VergeClient, *, volume_key: str, volume_name: str | None = None
    ) -> None:
        """Initialize the file manager.

        Args:
            client: VergeClient instance.
            volume_key: Volume key (40-character hex string).
            volume_name: Optional volume name for display purposes.
        """
        self._client = client
        self._volume_key = volume_key
        self._volume_name = volume_name

    def list(
        self,
        path: str = "/",
        *,
        limit: int = 1000,
        offset: int | None = None,
        extensions: str = "",
        sort: str = "",
        timeout: int = 30,
    ) -> builtins.list[NASVolumeFile]:
        """List files and directories at the specified path.

        Args:
            path: Directory path to list. Use "/" for root.
            limit: Maximum number of entries to return (default 1000).
            offset: Pagination offset.
            extensions: Filter by file extensions (comma-separated).
            sort: Sort field.
            timeout: Maximum seconds to wait for results (default 30).

        Returns:
            List of NASVolumeFile objects.

        Raises:
            APIError: If the browse operation fails.
            VergeTimeoutError: If the operation times out.

        Example:
            >>> # List root directory
            >>> files = client.nas_volumes.files(vol.key).list()

            >>> # List a subdirectory
            >>> files = client.nas_volumes.files(vol.key).list("/documents")

            >>> # Filter by extension
            >>> pdfs = client.nas_volumes.files(vol.key).list("/documents", extensions="pdf")
        """
        # Normalize path - API uses empty string for root, not "/"
        dir_path = path
        if dir_path == "/":
            dir_path = ""
        elif dir_path.startswith("/"):
            dir_path = dir_path[1:]

        # Create browse request
        body = {
            "volume": self._volume_key,
            "query": "get-dir",
            "params": {
                "dir": dir_path,
                "limit": limit,
                "offset": offset,
                "filter": {"extensions": extensions},
                "volume": self._volume_key,
                "sort": sort,
            },
        }

        # POST to create browse job
        response = self._client._request("POST", self._endpoint, json_data=body)

        if not response or not isinstance(response, dict):
            raise APIError("No response from volume browser")

        job_key = response.get("$key") or response.get("id")
        if not job_key:
            raise APIError("No job key returned from volume browser")

        # Poll for results
        result = self._poll_for_result(job_key, timeout=timeout)

        # Handle empty directory (result is null/None)
        if result is None:
            return []

        # Parse result if it's a JSON string
        if isinstance(result, str):
            import json

            try:
                result = json.loads(result)
            except json.JSONDecodeError as e:
                raise APIError(f"Invalid result from volume browser: {result}") from e

        # Result can be an array directly or have an entries property
        entries: builtins.list[dict[str, Any]]
        if isinstance(result, list):
            entries = result
        elif isinstance(result, dict) and "entries" in result:
            entries = result["entries"]
        else:
            entries = [result] if result else []

        # Convert to NASVolumeFile objects
        files: builtins.list[NASVolumeFile] = []
        for entry in entries:
            if entry:
                # Add metadata
                entry["_volume_key"] = self._volume_key
                entry["_volume_name"] = self._volume_name
                # Build full path
                if path == "/" or path == "":
                    entry["_full_path"] = f"/{entry.get('name', '')}"
                else:
                    normalized_path = path if path.startswith("/") else f"/{path}"
                    entry["_full_path"] = f"{normalized_path}/{entry.get('name', '')}"
                files.append(NASVolumeFile(entry))

        return files

    def get(
        self,
        path: str,
        *,
        timeout: int = 30,
    ) -> NASVolumeFile:
        """Get information about a specific file or directory.

        Args:
            path: Full path to the file or directory.
            timeout: Maximum seconds to wait for results.

        Returns:
            NASVolumeFile object.

        Raises:
            NotFoundError: If the file/directory is not found.
            APIError: If the browse operation fails.

        Example:
            >>> file = client.nas_volumes.files(vol.key).get("/documents/report.pdf")
            >>> print(f"{file.name}: {file.size_display}")
        """
        # Split path into directory and name
        path = path.rstrip("/")
        if "/" in path:
            last_slash = path.rfind("/")
            dir_path = path[:last_slash] if last_slash > 0 else "/"
            file_name = path[last_slash + 1 :]
        else:
            dir_path = "/"
            file_name = path

        # List the directory
        files = self.list(dir_path, timeout=timeout)

        # Find the specific file/directory
        for f in files:
            if f.name == file_name:
                return f

        raise NotFoundError(f"File or directory not found: {path}")

    def _poll_for_result(
        self, job_key: str, *, timeout: int = 30, poll_interval: float = 0.5
    ) -> Any:
        """Poll for browse operation results.

        Args:
            job_key: The browse job key.
            timeout: Maximum seconds to wait.
            poll_interval: Seconds between polls.

        Returns:
            The result data (can be list, dict, or None for empty dirs).

        Raises:
            APIError: If the job fails.
            VergeTimeoutError: If timeout is exceeded.
        """
        max_attempts = int(timeout / poll_interval)
        endpoint = f"{self._endpoint}/{job_key}"

        for _attempt in range(max_attempts):
            time.sleep(poll_interval)

            # Must explicitly request the result field - it's not returned by default
            response = self._client._request(
                "GET", endpoint, params={"fields": "id,status,result"}
            )

            if not response or not isinstance(response, dict):
                continue

            status = response.get("status")

            if status == "complete":
                return response.get("result")
            elif status == "error":
                error_msg = response.get("result", "Unknown error")
                raise APIError(f"Browse operation failed: {error_msg}")

        raise VergeTimeoutError(
            f"Browse operation timed out after {timeout} seconds"
        )


def _format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format.

    Args:
        size_bytes: Size in bytes.

    Returns:
        Human-readable size string (e.g., "1.5 MB").
    """
    if size_bytes == 0:
        return "0 B"

    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    size = float(size_bytes)
    unit_index = 0

    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1

    if unit_index == 0:
        return f"{int(size)} B"
    return f"{size:.2f} {units[unit_index]}"
