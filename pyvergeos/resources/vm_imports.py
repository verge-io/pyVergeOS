"""VM import resources for importing VMs from files."""

from __future__ import annotations

import builtins
from typing import TYPE_CHECKING, Any

from pyvergeos.exceptions import NotFoundError
from pyvergeos.filters import build_filter
from pyvergeos.resources.base import ResourceManager, ResourceObject

if TYPE_CHECKING:
    from pyvergeos.client import VergeClient


class VmImport(ResourceObject):
    """VM import resource object.

    Represents a VM import operation for importing VMs from files
    (VMDK, QCOW2, OVA, OVF) or other sources.

    Note:
        Import keys are 40-character hex strings, not integers like most
        other VergeOS resources.

    Attributes:
        key: The import unique identifier ($key) - 40-char hex string.
        id: The import ID (same as $key).
        name: VM name for the imported VM.
        vm: Created VM key (after import completes).
        uuid: UUID from the source VM.
        file: Source file key from media catalog.
        volume: Source NAS volume key.
        volume_path: Path within the source volume.
        status: Import status (initializing, importing, complete, aborted, error, warning).
        status_info: Detailed status information.
        importing: Whether import is in progress.
        aborted: Whether import was aborted.
        preserve_macs: Whether to preserve MAC addresses from source.
        preserve_drive_format: Whether to preserve original drive format.
        preferred_tier: Preferred storage tier (1-5).
        timestamp: Creation timestamp.
        modified: Last modified timestamp.
    """

    @property
    def key(self) -> str:  # type: ignore[override]
        """Resource primary key ($key) - 40-character hex string.

        Raises:
            ValueError: If resource has no $key (not yet persisted).
        """
        k = self.get("$key")
        if k is None:
            raise ValueError("Resource has no $key - may not be persisted")
        return str(k)

    def refresh(self) -> VmImport:
        """Refresh resource data from API.

        Returns:
            Updated VmImport object.
        """
        from typing import cast

        manager = cast("VmImportManager", self._manager)
        return manager.get(self.key)

    def save(self, **kwargs: Any) -> VmImport:
        """Save changes to resource.

        Args:
            **kwargs: Fields to update.

        Returns:
            Updated VmImport object.
        """
        from typing import cast

        manager = cast("VmImportManager", self._manager)
        return manager.update(self.key, **kwargs)

    def delete(self) -> None:
        """Delete this import."""
        from typing import cast

        manager = cast("VmImportManager", self._manager)
        manager.delete(self.key)

    @property
    def is_complete(self) -> bool:
        """Check if import completed successfully."""
        return self.get("status") == "complete"

    @property
    def is_importing(self) -> bool:
        """Check if import is in progress."""
        return self.get("importing", False) or self.get("status") == "importing"

    @property
    def has_error(self) -> bool:
        """Check if import has an error."""
        return self.get("status") in ("error", "aborted")

    @property
    def vm_key(self) -> int | None:
        """Get the created VM key (after import completes)."""
        vm = self.get("vm")
        return int(vm) if vm is not None else None

    @property
    def logs(self) -> VmImportLogManager:
        """Get a log manager for this import's logs.

        Returns:
            VmImportLogManager scoped to this import.

        Example:
            >>> # Browse import logs
            >>> for log in vm_import.logs.list():
            ...     print(f"{log.level}: {log.text}")
        """
        from typing import cast

        manager = cast("VmImportManager", self._manager)
        return VmImportLogManager(manager._client, import_key=self.key)

    def start(self) -> dict[str, Any] | None:
        """Start the import operation.

        Returns:
            Task information dict or None.
        """
        from typing import cast

        manager = cast("VmImportManager", self._manager)
        return manager.start_import(self.key)

    def abort(self) -> dict[str, Any] | None:
        """Abort the import operation.

        Returns:
            Task information dict or None.
        """
        from typing import cast

        manager = cast("VmImportManager", self._manager)
        return manager.abort_import(self.key)


class VmImportLog(ResourceObject):
    """VM import log entry resource object.

    Represents a log entry for a VM import operation.

    Attributes:
        key: The log entry key ($key).
        vm_import: Parent import key.
        level: Log level (message, warning, error, critical, debug, summary).
        text: Log message text.
        timestamp: Log entry timestamp.
        user: User who initiated the action.
    """

    @property
    def is_error(self) -> bool:
        """Check if this is an error log entry."""
        return self.get("level") in ("error", "critical")

    @property
    def is_warning(self) -> bool:
        """Check if this is a warning log entry."""
        return self.get("level") == "warning"


class VmImportManager(ResourceManager["VmImport"]):
    """Manager for VM import operations.

    VM imports allow importing VMs from files (VMDK, QCOW2, OVA, OVF)
    or from NAS volumes.

    Example:
        >>> # List all imports
        >>> for imp in client.vm_imports.list():
        ...     print(f"{imp.name}: {imp.status}")

        >>> # Get a specific import
        >>> imp = client.vm_imports.get(key="abc123...")

        >>> # Create an import from a file
        >>> imp = client.vm_imports.create(
        ...     name="imported-vm",
        ...     file=123,  # file key from media catalog
        ...     preferred_tier="1"
        ... )

        >>> # Start the import
        >>> imp.start()

        >>> # Monitor import logs
        >>> for log in imp.logs.list():
        ...     print(f"{log.level}: {log.text}")
    """

    _endpoint = "vm_imports"

    # Default fields for list operations
    _default_fields = [
        "$key",
        "id",
        "name",
        "vm",
        "vm#$display as vm_display",
        "uuid",
        "file",
        "file#$display as file_display",
        "volume",
        "volume#$display as volume_display",
        "volume_path",
        "status",
        "status_info",
        "importing",
        "aborted",
        "preserve_macs",
        "preserve_drive_format",
        "preferred_tier",
        "timestamp",
        "modified",
    ]

    def __init__(self, client: VergeClient) -> None:
        super().__init__(client)

    def list(
        self,
        filter: str | None = None,
        fields: builtins.list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        status: str | None = None,
        **filter_kwargs: Any,
    ) -> builtins.list[VmImport]:
        """List VM imports with optional filtering.

        Args:
            filter: OData filter string.
            fields: List of fields to return (uses defaults if not specified).
            limit: Maximum number of results.
            offset: Skip this many results.
            status: Filter by status (initializing, importing, complete, aborted, error).
            **filter_kwargs: Shorthand filter arguments (name, etc.).

        Returns:
            List of VmImport objects.

        Example:
            >>> # List all imports
            >>> imports = client.vm_imports.list()

            >>> # List active imports
            >>> active = client.vm_imports.list(status="importing")

            >>> # List completed imports
            >>> done = client.vm_imports.list(status="complete")
        """
        params: dict[str, Any] = {}

        # Build filter
        filters: builtins.list[str] = []
        if filter:
            filters.append(filter)
        if filter_kwargs:
            filters.append(build_filter(**filter_kwargs))

        # Add status filter
        if status:
            filters.append(f"status eq '{status}'")

        if filters:
            params["filter"] = " and ".join(filters)

        # Use default fields if not specified
        if fields:
            params["fields"] = ",".join(fields)
        else:
            params["fields"] = ",".join(self._default_fields)

        # Pagination
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset

        response = self._client._request("GET", self._endpoint, params=params)

        if response is None:
            return []

        if not isinstance(response, list):
            response = [response]

        return [self._to_model(item) for item in response if item]

    def get(  # type: ignore[override]
        self,
        key: str | None = None,
        *,
        name: str | None = None,
        fields: builtins.list[str] | None = None,
    ) -> VmImport:
        """Get a single VM import by key or name.

        Args:
            key: Import $key (40-character hex string).
            name: Import name (VM name).
            fields: List of fields to return.

        Returns:
            VmImport object.

        Raises:
            NotFoundError: If import not found.
            ValueError: If no identifier provided.

        Example:
            >>> # Get by key
            >>> imp = client.vm_imports.get("8f73f8bcc9c9f1aaba32f733bfc295acaf548554")

            >>> # Get by name
            >>> imp = client.vm_imports.get(name="imported-vm")
        """
        if key is not None:
            # Fetch by key using id filter
            params: dict[str, Any] = {
                "filter": f"id eq '{key}'",
            }
            if fields:
                params["fields"] = ",".join(fields)
            else:
                params["fields"] = ",".join(self._default_fields)

            response = self._client._request("GET", self._endpoint, params=params)

            if response is None:
                raise NotFoundError(f"VM import with key {key} not found")
            if isinstance(response, list):
                if not response:
                    raise NotFoundError(f"VM import with key {key} not found")
                response = response[0]
            if not isinstance(response, dict):
                raise NotFoundError(f"VM import with key {key} returned invalid response")
            return self._to_model(response)

        if name is not None:
            # Search by name
            escaped_name = name.replace("'", "''")
            results = self.list(filter=f"name eq '{escaped_name}'", fields=fields, limit=1)
            if not results:
                raise NotFoundError(f"VM import with name '{name}' not found")
            return results[0]

        raise ValueError("Either key or name must be provided")

    def create(  # type: ignore[override]
        self,
        name: str,
        *,
        file: int | None = None,
        volume: str | None = None,
        volume_path: str | None = None,
        shared_object: int | None = None,
        preserve_macs: bool = True,
        preserve_drive_format: bool = False,
        preferred_tier: str | None = None,
        no_optical_drives: bool = False,
        override_drive_interface: str | None = None,
        override_nic_interface: str | None = None,
        cleanup_on_delete: bool = False,
    ) -> VmImport:
        """Create a new VM import.

        Args:
            name: Name for the imported VM.
            file: Source file key from media catalog (for file imports).
            volume: Source NAS volume key (for volume imports).
            volume_path: Path within the source volume.
            shared_object: Shared object key (for tenant imports).
            preserve_macs: Preserve MAC addresses from source (default True).
            preserve_drive_format: Preserve original drive format instead of
                converting to optimized .raw format (default False).
            preferred_tier: Preferred storage tier (1-5).
            no_optical_drives: Do not create optical drives (default False).
            override_drive_interface: Override drive interface type.
            override_nic_interface: Override NIC interface type.
            cleanup_on_delete: Clean up import file path on delete.

        Returns:
            Created VmImport object.

        Raises:
            ValueError: If no source (file, volume, or shared_object) provided.

        Example:
            >>> # Import from media catalog file
            >>> imp = client.vm_imports.create(
            ...     name="imported-vm",
            ...     file=123,
            ...     preferred_tier="1"
            ... )

            >>> # Import from NAS volume
            >>> imp = client.vm_imports.create(
            ...     name="imported-vm",
            ...     volume="abc123...",
            ...     volume_path="/exports/vm.vmdk"
            ... )
        """
        if file is None and volume is None and shared_object is None:
            raise ValueError("One of file, volume, or shared_object must be provided")

        body: dict[str, Any] = {
            "name": name,
            "preserve_macs": preserve_macs,
            "preserve_drive_format": preserve_drive_format,
        }

        if file is not None:
            body["file"] = file

        if volume is not None:
            body["volume"] = volume

        if volume_path is not None:
            body["volume_path"] = volume_path

        if shared_object is not None:
            body["shared_object"] = shared_object

        if preferred_tier is not None:
            body["preferred_tier"] = preferred_tier

        if no_optical_drives:
            body["no_optical_drives"] = True

        if override_drive_interface is not None:
            body["override_drive_interface"] = override_drive_interface

        if override_nic_interface is not None:
            body["override_nic_interface"] = override_nic_interface

        if cleanup_on_delete:
            body["cleanup_on_delete"] = True

        response = self._client._request("POST", self._endpoint, json_data=body)

        # Get the created import
        if response and isinstance(response, dict):
            imp_key = response.get("$key") or response.get("id")
            if imp_key:
                return self.get(key=imp_key)

        # Fallback: search by name
        return self.get(name=name)

    def update(  # type: ignore[override]
        self,
        key: str,
        *,
        name: str | None = None,
        vm: int | None = None,
        preserve_macs: bool | None = None,
        preserve_drive_format: bool | None = None,
        preferred_tier: str | None = None,
        no_optical_drives: bool | None = None,
        override_drive_interface: str | None = None,
        override_nic_interface: str | None = None,
    ) -> VmImport:
        """Update a VM import.

        Args:
            key: Import $key (40-character hex string).
            name: New VM name.
            vm: Associated VM key.
            preserve_macs: Preserve MAC addresses.
            preserve_drive_format: Preserve original drive format.
            preferred_tier: Preferred storage tier (1-5).
            no_optical_drives: Do not create optical drives.
            override_drive_interface: Override drive interface type.
            override_nic_interface: Override NIC interface type.

        Returns:
            Updated VmImport object.
        """
        body: dict[str, Any] = {}

        if name is not None:
            body["name"] = name

        if vm is not None:
            body["vm"] = vm

        if preserve_macs is not None:
            body["preserve_macs"] = preserve_macs

        if preserve_drive_format is not None:
            body["preserve_drive_format"] = preserve_drive_format

        if preferred_tier is not None:
            body["preferred_tier"] = preferred_tier

        if no_optical_drives is not None:
            body["no_optical_drives"] = no_optical_drives

        if override_drive_interface is not None:
            body["override_drive_interface"] = override_drive_interface

        if override_nic_interface is not None:
            body["override_nic_interface"] = override_nic_interface

        if not body:
            return self.get(key)

        self._client._request("PUT", f"{self._endpoint}/{key}", json_data=body)
        return self.get(key)

    def delete(self, key: str) -> None:  # type: ignore[override]
        """Delete a VM import.

        Args:
            key: Import $key (40-character hex string).

        Example:
            >>> client.vm_imports.delete(imp.key)
        """
        self._client._request("DELETE", f"{self._endpoint}/{key}")

    def start_import(self, key: str) -> dict[str, Any] | None:
        """Start a VM import operation.

        This initiates the actual import process for an import that has
        been created but not yet started.

        Args:
            key: Import $key (40-character hex string).

        Returns:
            Task information dict or None.

        Example:
            >>> result = client.vm_imports.start_import(imp.key)
            >>> if result and "task" in result:
            ...     client.tasks.wait(result["task"])
        """
        result = self._client._request(
            "PUT", f"{self._endpoint}/{key}?action=import", json_data={}
        )
        if isinstance(result, dict):
            return result
        return None

    def abort_import(self, key: str) -> dict[str, Any] | None:
        """Abort a VM import operation.

        This stops an in-progress import.

        Args:
            key: Import $key (40-character hex string).

        Returns:
            Task information dict or None.

        Example:
            >>> client.vm_imports.abort_import(imp.key)
        """
        result = self._client._request(
            "PUT", f"{self._endpoint}/{key}?action=abort", json_data={}
        )
        if isinstance(result, dict):
            return result
        return None

    def logs(self, key: str) -> VmImportLogManager:
        """Get a log manager for a specific import.

        Args:
            key: Import $key (40-character hex string).

        Returns:
            VmImportLogManager for the import.

        Example:
            >>> # List logs for an import
            >>> for log in client.vm_imports.logs(imp.key).list():
            ...     print(f"{log.level}: {log.text}")
        """
        return VmImportLogManager(self._client, import_key=key)

    def _to_model(self, data: dict[str, Any]) -> VmImport:
        """Convert API response to VmImport object."""
        return VmImport(data, self)


class VmImportLogManager(ResourceManager["VmImportLog"]):
    """Manager for VM import log operations.

    This manager provides access to log entries for VM imports.
    It can be used either standalone or scoped to a specific import.

    Example:
        >>> # List all import logs (standalone)
        >>> for log in client.vm_import_logs.list():
        ...     print(f"{log.level}: {log.text}")

        >>> # List logs for a specific import
        >>> for log in client.vm_imports.logs(imp.key).list():
        ...     print(f"{log.level}: {log.text}")

        >>> # Get only errors
        >>> errors = client.vm_imports.logs(imp.key).list(level="error")
    """

    _endpoint = "vm_import_logs"

    # Default fields for list operations
    _default_fields = [
        "$key",
        "vm_import",
        "level",
        "text",
        "timestamp",
        "user",
    ]

    def __init__(
        self, client: VergeClient, *, import_key: str | None = None
    ) -> None:
        super().__init__(client)
        self._import_key = import_key

    def list(
        self,
        filter: str | None = None,
        fields: builtins.list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        level: str | None = None,
        vm_import: str | None = None,
        **filter_kwargs: Any,
    ) -> builtins.list[VmImportLog]:
        """List VM import logs with optional filtering.

        Args:
            filter: OData filter string.
            fields: List of fields to return (uses defaults if not specified).
            limit: Maximum number of results.
            offset: Skip this many results.
            level: Filter by log level (message, warning, error, critical, debug).
            vm_import: Filter by import key. Ignored if manager is scoped.
            **filter_kwargs: Shorthand filter arguments.

        Returns:
            List of VmImportLog objects.

        Example:
            >>> # List all logs
            >>> logs = client.vm_import_logs.list()

            >>> # List errors only
            >>> errors = client.vm_import_logs.list(level="error")

            >>> # List logs for a specific import
            >>> logs = client.vm_imports.logs(imp.key).list()
        """
        params: dict[str, Any] = {}

        # Build filter
        filters: builtins.list[str] = []
        if filter:
            filters.append(filter)
        if filter_kwargs:
            filters.append(build_filter(**filter_kwargs))

        # Add import filter (from scope or parameter)
        import_key = self._import_key
        if import_key is None and vm_import is not None:
            import_key = vm_import

        if import_key is not None:
            filters.append(f"vm_import eq '{import_key}'")

        # Add level filter
        if level:
            filters.append(f"level eq '{level}'")

        if filters:
            params["filter"] = " and ".join(filters)

        # Use default fields if not specified
        if fields:
            params["fields"] = ",".join(fields)
        else:
            params["fields"] = ",".join(self._default_fields)

        # Pagination
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset

        response = self._client._request("GET", self._endpoint, params=params)

        if response is None:
            return []

        if not isinstance(response, list):
            response = [response]

        return [self._to_model(item) for item in response if item]

    def get(  # type: ignore[override]
        self,
        key: int | None = None,
        *,
        fields: builtins.list[str] | None = None,
    ) -> VmImportLog:
        """Get a single VM import log entry by key.

        Args:
            key: Log entry $key (row ID).
            fields: List of fields to return.

        Returns:
            VmImportLog object.

        Raises:
            NotFoundError: If log entry not found.
            ValueError: If key not provided.

        Example:
            >>> log = client.vm_import_logs.get(1)
        """
        if key is not None:
            params: dict[str, Any] = {}
            if fields:
                params["fields"] = ",".join(fields)
            else:
                params["fields"] = ",".join(self._default_fields)

            response = self._client._request(
                "GET", f"{self._endpoint}/{key}", params=params
            )
            if response is None:
                raise NotFoundError(f"VM import log with key {key} not found")
            if not isinstance(response, dict):
                raise NotFoundError(f"VM import log with key {key} returned invalid response")
            return self._to_model(response)

        raise ValueError("Key must be provided")

    def list_errors(self) -> builtins.list[VmImportLog]:
        """List only error and critical log entries.

        Returns:
            List of error VmImportLog objects.

        Example:
            >>> errors = client.vm_imports.logs(imp.key).list_errors()
        """
        return self.list(filter="(level eq 'error') or (level eq 'critical')")

    def list_warnings(self) -> builtins.list[VmImportLog]:
        """List only warning log entries.

        Returns:
            List of warning VmImportLog objects.

        Example:
            >>> warnings = client.vm_imports.logs(imp.key).list_warnings()
        """
        return self.list(level="warning")

    def _to_model(self, data: dict[str, Any]) -> VmImportLog:
        """Convert API response to VmImportLog object."""
        return VmImportLog(data, self)
