"""System diagnostic resource managers."""

from __future__ import annotations

import builtins
import time
from typing import TYPE_CHECKING, Any, Literal

from pyvergeos.exceptions import NotFoundError, VergeTimeoutError
from pyvergeos.resources.base import ResourceManager, ResourceObject

if TYPE_CHECKING:
    from pyvergeos.client import VergeClient

# Diagnostic status values
DiagnosticStatus = Literal["initializing", "building", "uploading", "complete", "error"]

# Default fields
DIAGNOSTIC_DEFAULT_FIELDS = [
    "$key",
    "name",
    "description",
    "status",
    "status_info",
    "file",
    "send2support",
    "timestamp",
]


class SystemDiagnostic(ResourceObject):
    """System diagnostic bundle resource object.

    Represents a diagnostic bundle that captures system state for
    troubleshooting. Max 100 diagnostics at a time.
    """

    @property
    def name(self) -> str:
        """Diagnostic name (unique)."""
        return str(self.get("name", ""))

    @property
    def description(self) -> str:
        """Diagnostic description."""
        return str(self.get("description", ""))

    @property
    def status(self) -> str:  # noqa: A003
        """Diagnostic status."""
        return str(self.get("status", "initializing"))

    @property
    def is_complete(self) -> bool:
        """Check if diagnostic bundle is ready."""
        return self.status == "complete"

    @property
    def is_error(self) -> bool:
        """Check if diagnostic failed."""
        return self.status == "error"

    @property
    def is_building(self) -> bool:
        """Check if diagnostic is still being built."""
        return self.status in ("initializing", "building", "uploading")

    @property
    def status_info(self) -> str | None:
        """Detailed status information."""
        return self.get("status_info")

    @property
    def file_key(self) -> int | None:
        """Associated file key (available when complete)."""
        f = self.get("file")
        return int(f) if f else None

    @property
    def timestamp(self) -> int | None:
        """Creation timestamp."""
        ts = self.get("timestamp")
        return int(ts) if ts else None


class SystemDiagnosticManager(ResourceManager[SystemDiagnostic]):
    """Manager for system diagnostic bundle operations.

    System diagnostics capture comprehensive system state including
    logs, configuration, and hardware information for troubleshooting.
    Max 100 diagnostics can exist at a time.

    Examples:
        Create and wait for a diagnostic::

            diag = client.system_diagnostics.create(
                name="issue-2024-01",
                description="Network connectivity issue",
            )
            diag = client.system_diagnostics.wait(diag.key)
            print(f"Status: {diag.status}")

        Send diagnostic to support::

            client.system_diagnostics.send_to_support(diag.key)
    """

    _endpoint = "system_diagnostics"
    _default_fields = DIAGNOSTIC_DEFAULT_FIELDS

    def __init__(self, client: VergeClient) -> None:
        super().__init__(client)

    def _to_model(self, data: dict[str, Any]) -> SystemDiagnostic:
        return SystemDiagnostic(data, self)

    def list(  # noqa: A003
        self,
        filter: str | None = None,  # noqa: A002
        fields: builtins.list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        **filter_kwargs: Any,
    ) -> builtins.list[SystemDiagnostic]:
        """List system diagnostics.

        Args:
            filter: OData filter string.
            fields: List of fields to return.
            limit: Maximum number of results.
            offset: Skip this many results.

        Returns:
            List of SystemDiagnostic objects.
        """
        if fields is None:
            fields = self._default_fields
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
    ) -> SystemDiagnostic:
        """Get a diagnostic by key or name.

        Args:
            key: Diagnostic $key.
            name: Diagnostic name (unique).
            fields: List of fields to return.

        Returns:
            SystemDiagnostic object.

        Raises:
            NotFoundError: If diagnostic not found.
            ValueError: If neither key nor name provided.
        """
        if fields is None:
            fields = self._default_fields

        if key is not None:
            params: dict[str, Any] = {"fields": ",".join(fields)}
            response = self._client._request("GET", f"{self._endpoint}/{key}", params=params)
            if response is None:
                raise NotFoundError(f"Diagnostic {key} not found")
            if not isinstance(response, dict):
                raise NotFoundError(f"Diagnostic {key} returned invalid response")
            return self._to_model(response)

        if name is not None:
            escaped_name = name.replace("'", "''")
            results = self.list(filter=f"name eq '{escaped_name}'", fields=fields, limit=1)
            if not results:
                raise NotFoundError(f"Diagnostic with name '{name}' not found")
            return results[0]

        raise ValueError("Either key or name must be provided")

    def create(  # type: ignore[override]
        self,
        name: str,
        description: str = "",
        send2support: bool = False,
    ) -> SystemDiagnostic:
        """Create a new system diagnostic bundle.

        Args:
            name: Unique diagnostic name (max 128 chars).
            description: Description (max 2048 chars).
            send2support: Automatically send to Verge.io support.

        Returns:
            SystemDiagnostic object (status will be "initializing").
        """
        body: dict[str, Any] = {"name": name}
        if description:
            body["description"] = description
        if send2support:
            body["send2support"] = True

        response = self._client._request("POST", self._endpoint, json_data=body)
        if response is None:
            raise ValueError("No response from diagnostic creation")
        if not isinstance(response, dict):
            raise ValueError("Diagnostic creation returned invalid response")

        key = response.get("$key")
        if key is not None:
            return self.get(int(key))
        return self._to_model(response)

    def wait(
        self,
        key: int,
        timeout: float = 300,
        poll_interval: float = 5.0,
    ) -> SystemDiagnostic:
        """Wait for a diagnostic to complete.

        Args:
            key: Diagnostic $key.
            timeout: Maximum seconds to wait.
            poll_interval: Seconds between polls.

        Returns:
            Completed SystemDiagnostic.

        Raises:
            VergeTimeoutError: If diagnostic doesn't complete within timeout.
        """
        deadline = time.monotonic() + timeout
        while True:
            diag = self.get(key)
            if diag.status in ("complete", "error"):
                return diag
            if time.monotonic() >= deadline:
                raise VergeTimeoutError(
                    f"Diagnostic {key} did not complete within {timeout}s (status: {diag.status})"
                )
            time.sleep(poll_interval)

    def send_to_support(self, key: int) -> None:
        """Send a completed diagnostic bundle to Verge.io support.

        Args:
            key: Diagnostic $key.
        """
        self._client._request(
            "POST",
            "system_diagnostic_actions",
            json_data={
                "system_diagnostic": key,
                "action": "send2support",
            },
        )
