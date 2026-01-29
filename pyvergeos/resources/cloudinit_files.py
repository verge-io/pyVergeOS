"""Cloud-init file resource manager for VM provisioning automation."""

from __future__ import annotations

import builtins
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from pyvergeos.exceptions import NotFoundError
from pyvergeos.filters import build_filter
from pyvergeos.resources.base import ResourceManager, ResourceObject

if TYPE_CHECKING:
    from pyvergeos.client import VergeClient


# Render type mappings (friendly name -> API value)
RENDER_TYPE_MAP = {
    "No": "no",
    "Variables": "variables",
    "Jinja2": "jinja2",
}

# Reverse mapping (API value -> friendly name)
RENDER_TYPE_DISPLAY = {
    "no": "No",
    "variables": "Variables",
    "jinja2": "Jinja2",
}

# Default fields for cloud-init file list operations
_DEFAULT_CLOUDINIT_FIELDS = [
    "$key",
    "name",
    "owner",
    "filesize",
    "allocated_bytes",
    "used_bytes",
    "modified",
    "render",
    "contains_variables",
    "creator",
]


class CloudInitFile(ResourceObject):
    """Cloud-init file resource object.

    Represents a cloud-init configuration file in VergeOS used for VM
    provisioning automation. Cloud-init files provide user-data, meta-data,
    network-config, and other configuration to VMs during boot.

    Properties:
        name: File name (typically /user-data, /meta-data, /network-config).
        owner: Owner reference (e.g., "vms/123").
        vm_key: Key of the VM this file belongs to.
        render: Render type (API value: no, variables, jinja2).
        render_display: Friendly render type name.
        contains_variables: Whether file contains VergeOS variables.
        filesize: Size of file contents in bytes.
        allocated_bytes: Allocated storage size.
        used_bytes: Used storage size on disk.
        creator: Username who created the file.
        modified_at: Datetime when file was last modified.
        contents: File contents (if loaded).
    """

    @property
    def name(self) -> str:
        """Get file name."""
        return str(self.get("name", ""))

    @property
    def owner(self) -> str:
        """Get owner reference (e.g., 'vms/123')."""
        return str(self.get("owner", ""))

    @property
    def vm_key(self) -> int | None:
        """Get the key of the VM this file belongs to."""
        owner = self.owner
        if owner and owner.startswith("vms/"):
            try:
                return int(owner.split("/")[1])
            except (IndexError, ValueError):
                return None
        return None

    @property
    def render(self) -> str:
        """Get render type (API value: no, variables, jinja2)."""
        return str(self.get("render", "no"))

    @property
    def render_display(self) -> str:
        """Get friendly render type name."""
        return RENDER_TYPE_DISPLAY.get(self.render, self.render)

    @property
    def contains_variables(self) -> bool:
        """Check if file contains VergeOS variables."""
        return bool(self.get("contains_variables", False))

    @property
    def filesize(self) -> int:
        """Get size of file contents in bytes."""
        return int(self.get("filesize", 0))

    @property
    def allocated_bytes(self) -> int:
        """Get allocated storage size in bytes."""
        return int(self.get("allocated_bytes", 0))

    @property
    def used_bytes(self) -> int:
        """Get used storage size on disk in bytes."""
        return int(self.get("used_bytes", 0))

    @property
    def creator(self) -> str:
        """Get username who created the file."""
        return str(self.get("creator", ""))

    @property
    def modified_at(self) -> datetime | None:
        """Get datetime when file was last modified."""
        ts = self.get("modified")
        if ts is None or ts == 0:
            return None
        return datetime.fromtimestamp(int(ts), tz=timezone.utc)

    @property
    def contents(self) -> str | None:
        """Get file contents from the raw API response.

        Note: The VergeOS API does not return file contents in standard GET
        responses. This property will typically return None. To retrieve
        actual file contents, use the get_content() method which fetches
        from the download endpoint.

        Example:
            >>> file = client.cloudinit_files.get(key=123)
            >>> file.contents  # Usually None
            >>> content = file.get_content()  # Actual content
        """
        val = self.get("contents")
        return str(val) if val is not None else None

    def get_content(self, *, as_bytes: bool = False) -> str | bytes:
        """Retrieve the full file contents.

        Args:
            as_bytes: If True, return contents as bytes instead of string.

        Returns:
            File contents as string (default) or bytes.
        """
        from typing import cast

        manager = cast("CloudInitFileManager", self._manager)
        return manager.get_content(self.key, as_bytes=as_bytes)

    def save(self, **kwargs: Any) -> CloudInitFile:
        """Update this cloud-init file.

        Args:
            **kwargs: Fields to update (name, contents, render).

        Returns:
            Updated CloudInitFile object.
        """
        from typing import cast

        manager = cast("CloudInitFileManager", self._manager)
        return manager.update(self.key, **kwargs)

    def delete(self) -> None:
        """Delete this cloud-init file."""
        from typing import cast

        manager = cast("CloudInitFileManager", self._manager)
        manager.delete(self.key)

    def __repr__(self) -> str:
        return f"<CloudInitFile key={self.get('$key', '?')} name={self.name!r} vm_key={self.vm_key}>"


class CloudInitFileManager(ResourceManager[CloudInitFile]):
    """Manager for cloud-init file operations.

    Provides CRUD operations for cloud-init files used in VM provisioning.
    Cloud-init files are associated with specific VMs and provide configuration
    for automated VM setup during boot.

    Example:
        >>> # List cloud-init files for a VM
        >>> files = client.cloudinit_files.list(vm_key=123)
        >>>
        >>> # Create a user-data file
        >>> user_data = '''#cloud-config
        ... users:
        ...   - name: admin
        ...     sudo: ALL=(ALL) NOPASSWD:ALL
        ... '''
        >>> file = client.cloudinit_files.create(
        ...     vm_key=123,
        ...     name="/user-data",
        ...     contents=user_data,
        ...     render="No"
        ... )
        >>>
        >>> # Get file contents
        >>> content = file.get_content()
        >>>
        >>> # Update file
        >>> file = client.cloudinit_files.update(file.key, render="Variables")
        >>>
        >>> # Delete file
        >>> client.cloudinit_files.delete(file.key)
    """

    _endpoint = "cloudinit_files"

    def __init__(self, client: VergeClient) -> None:
        super().__init__(client)

    def _to_model(self, data: dict[str, Any]) -> CloudInitFile:
        """Convert API response to CloudInitFile object."""
        return CloudInitFile(data, self)

    def list(
        self,
        filter: str | None = None,
        fields: builtins.list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        *,
        vm_key: int | None = None,
        name: str | None = None,
        render: str | None = None,
        **filter_kwargs: Any,
    ) -> builtins.list[CloudInitFile]:
        """List cloud-init files with optional filtering.

        Note: File contents are not returned in list operations. Use
        get_content() to retrieve actual file contents.

        Args:
            filter: OData filter string.
            fields: List of fields to return.
            limit: Maximum number of results.
            offset: Skip this many results.
            vm_key: Filter by VM $key.
            name: Filter by file name (exact match or wildcard with *).
            render: Filter by render type (No, Variables, Jinja2).
            **filter_kwargs: Additional filter arguments.

        Returns:
            List of CloudInitFile objects.
        """
        params: dict[str, Any] = {}
        filters: builtins.list[str] = []

        # Build filter from string
        if filter:
            filters.append(filter)

        # Filter by VM
        if vm_key is not None:
            filters.append(f"owner eq 'vms/{vm_key}'")

        # Filter by name
        if name is not None:
            if "*" in name or "?" in name:
                # Wildcard search - use contains
                search_term = name.replace("*", "").replace("?", "")
                if search_term:
                    escaped = search_term.replace("'", "''")
                    filters.append(f"name ct '{escaped}'")
            else:
                escaped = name.replace("'", "''")
                filters.append(f"name eq '{escaped}'")

        # Filter by render type
        if render:
            api_render = RENDER_TYPE_MAP.get(render, render.lower())
            filters.append(f"render eq '{api_render}'")

        # Add filter kwargs
        if filter_kwargs:
            filters.append(build_filter(**filter_kwargs))

        if filters:
            params["filter"] = " and ".join(filters)

        # Field selection
        field_list = list(fields) if fields else list(_DEFAULT_CLOUDINIT_FIELDS)
        params["fields"] = ",".join(field_list)

        # Pagination
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

    def get(
        self,
        key: int | None = None,
        *,
        name: str | None = None,
        vm_key: int | None = None,
        fields: builtins.list[str] | None = None,
    ) -> CloudInitFile:
        """Get a cloud-init file by key or name.

        Note: File contents are not returned in GET operations. Use
        get_content() to retrieve actual file contents.

        Args:
            key: CloudInitFile $key (ID).
            name: File name (exact match). Requires vm_key if using name.
            vm_key: VM $key (required when searching by name).
            fields: List of fields to return.

        Returns:
            CloudInitFile object.

        Raises:
            NotFoundError: If file not found.
            ValueError: If neither key nor (name + vm_key) provided.
        """
        field_list = list(fields) if fields else list(_DEFAULT_CLOUDINIT_FIELDS)

        if key is not None:
            params: dict[str, Any] = {"fields": ",".join(field_list)}
            response = self._client._request("GET", f"{self._endpoint}/{key}", params=params)
            if response is None:
                raise NotFoundError(f"Cloud-init file with key {key} not found")
            if not isinstance(response, dict):
                raise NotFoundError(f"Cloud-init file with key {key} returned invalid response")
            return self._to_model(response)

        if name is not None:
            if vm_key is None:
                raise ValueError("vm_key is required when searching by name")

            results = self.list(
                vm_key=vm_key,
                name=name,
                fields=field_list,
                limit=1,
            )
            if not results:
                raise NotFoundError(f"Cloud-init file '{name}' not found for VM {vm_key}")
            return results[0]

        raise ValueError("Either key or (name + vm_key) must be provided")

    def create(  # type: ignore[override]
        self,
        vm_key: int,
        name: str,
        *,
        contents: str | None = None,
        render: str = "No",
    ) -> CloudInitFile:
        """Create a new cloud-init file.

        Args:
            vm_key: VM $key (ID) to attach the file to.
            name: File name (typically /user-data, /meta-data, /network-config).
                  Maximum 256 characters.
            contents: File contents. Maximum 65536 bytes (64KB).
            render: Render type for variable processing:
                - No: File is used as-is without processing (default).
                - Variables: File supports VergeOS variable substitution.
                - Jinja2: File is processed as a Jinja2 template.

        Returns:
            Created CloudInitFile object.

        Raises:
            ValidationError: If parameters invalid or contents too large.
            ConflictError: If file with same name already exists for VM.
        """
        # Validate contents size
        if contents and len(contents) > 65536:
            raise ValueError(
                f"Contents exceed maximum size of 65536 bytes (64KB). "
                f"Current size: {len(contents)} bytes."
            )

        body: dict[str, Any] = {
            "name": name,
            "owner": f"vms/{vm_key}",
            "render": RENDER_TYPE_MAP.get(render, render.lower()),
        }

        if contents is not None:
            body["contents"] = contents

        response = self._client._request("POST", self._endpoint, json_data=body)
        if response is None:
            raise ValueError("No response from create operation")
        if not isinstance(response, dict):
            raise ValueError("Create operation returned invalid response")

        # Fetch full object since POST response may not include all fields
        key = response.get("$key")
        if key is not None:
            return self.get(int(key))

        return self._to_model(response)

    def update(  # type: ignore[override]
        self,
        key: int,
        *,
        name: str | None = None,
        contents: str | None = None,
        render: str | None = None,
    ) -> CloudInitFile:
        """Update a cloud-init file.

        Args:
            key: CloudInitFile $key (ID).
            name: New file name.
            contents: New file contents. Maximum 65536 bytes (64KB).
            render: New render type (No, Variables, Jinja2).

        Returns:
            Updated CloudInitFile object.

        Raises:
            NotFoundError: If file not found.
            ValidationError: If parameters invalid.
        """
        body: dict[str, Any] = {}

        if name is not None:
            body["name"] = name

        if contents is not None:
            if len(contents) > 65536:
                raise ValueError(
                    f"Contents exceed maximum size of 65536 bytes (64KB). "
                    f"Current size: {len(contents)} bytes."
                )
            body["contents"] = contents

        if render is not None:
            body["render"] = RENDER_TYPE_MAP.get(render, render.lower())

        if not body:
            # No changes, just fetch current
            return self.get(key)

        response = self._client._request("PUT", f"{self._endpoint}/{key}", json_data=body)
        if response is None or not isinstance(response, dict):
            return self.get(key)
        return self._to_model(response)

    def delete(self, key: int) -> None:
        """Delete a cloud-init file.

        Args:
            key: CloudInitFile $key (ID).

        Raises:
            NotFoundError: If file not found.
        """
        self._client._request("DELETE", f"{self._endpoint}/{key}")

    def get_content(
        self,
        key: int,
        *,
        as_bytes: bool = False,
    ) -> str | bytes:
        """Retrieve the raw contents of a cloud-init file.

        This method downloads the file contents directly from the API,
        which is useful when you need the exact file content without
        any metadata.

        Args:
            key: CloudInitFile $key (ID).
            as_bytes: If True, return contents as bytes instead of string.

        Returns:
            File contents as string (default) or bytes.

        Raises:
            NotFoundError: If file not found.
        """
        # Use the download endpoint
        endpoint = f"{self._endpoint}/{key}"
        params = {"download": 1}

        # Make request through connection to get raw response
        if not self._client._connection or not self._client._connection.is_connected:
            from pyvergeos.exceptions import NotConnectedError

            raise NotConnectedError("Not connected to VergeOS")

        session = self._client._connection._session
        if session is None:
            from pyvergeos.exceptions import NotConnectedError

            raise NotConnectedError("Session not initialized")

        url = f"{self._client._connection.api_base_url}/{endpoint}"

        response = session.request(
            method="GET",
            url=url,
            params=params,
            timeout=self._client._timeout,
        )

        if response.status_code == 404:
            raise NotFoundError(f"Cloud-init file with key {key} not found")
        elif response.status_code != 200:
            from pyvergeos.exceptions import APIError

            raise APIError(
                f"Failed to download cloud-init file: HTTP {response.status_code}",
                status_code=response.status_code,
            )

        if as_bytes:
            return response.content

        # Return as string (UTF-8)
        return response.content.decode("utf-8")

    def list_for_vm(self, vm_key: int) -> builtins.list[CloudInitFile]:
        """List all cloud-init files for a specific VM.

        Convenience method that filters by VM key.

        Note: File contents are not returned. Use get_content() to retrieve
        actual file contents for individual files.

        Args:
            vm_key: VM $key (ID).

        Returns:
            List of CloudInitFile objects for the VM.
        """
        return self.list(vm_key=vm_key)
