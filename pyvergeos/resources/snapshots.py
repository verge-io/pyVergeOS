"""VM Snapshot resource manager."""

from __future__ import annotations

import builtins
import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, cast

from pyvergeos.filters import combine_filters, quote_value
from pyvergeos.resources.base import ResourceManager, ResourceObject

if TYPE_CHECKING:
    from pyvergeos.client import VergeClient
    from pyvergeos.resources.vms import VM

logger = logging.getLogger(__name__)

# Default fields for snapshots
SNAPSHOT_DEFAULT_FIELDS = [
    "$key",
    "name",
    "description",
    "created",
    "expires",
    "expires_type",
    "quiesced",
    "created_manually",
    "machine",
    "snap_machine",
    "snapshot_period",
]


class VMSnapshot(ResourceObject):
    """VM Snapshot resource object."""

    @property
    def created_at(self) -> datetime | None:
        """Get creation timestamp as datetime."""
        timestamp = self.get("created")
        if timestamp:
            return datetime.fromtimestamp(int(timestamp), tz=timezone.utc)
        return None

    @property
    def expires_at(self) -> datetime | None:
        """Get expiration timestamp as datetime."""
        timestamp = self.get("expires")
        if timestamp and int(timestamp) > 0:
            return datetime.fromtimestamp(int(timestamp), tz=timezone.utc)
        return None

    @property
    def never_expires(self) -> bool:
        """Check if snapshot never expires."""
        expires_type = self.get("expires_type")
        expires = self.get("expires")
        return expires_type == "never" or (expires is not None and int(expires) == 0)

    @property
    def is_quiesced(self) -> bool:
        """Check if snapshot was quiesced."""
        return bool(self.get("quiesced", False))

    @property
    def is_manual(self) -> bool:
        """Check if snapshot was created manually."""
        return bool(self.get("created_manually", False))

    @property
    def snap_machine_key(self) -> int | None:
        """Get the snap_machine key (used for restore)."""
        key = self.get("snap_machine")
        return int(key) if key is not None else None

    @property
    def is_cloud_snapshot(self) -> bool:
        """Check if this is a cloud snapshot."""
        return bool(self.get("snapshot_period"))

    def restore(self, name: str | None = None, power_on: bool = False) -> dict[str, Any] | None:
        """Restore this snapshot to a new VM.

        Args:
            name: Name for the restored VM (default: "{snapshot_name} restored").
            power_on: Power on the VM after restoration.

        Returns:
            Clone task information.

        Raises:
            ValueError: If the snapshot has no snap_machine, or no snapshot
                VM exists for that machine.
            NotFoundError: If this snapshot key no longer exists.

        Notes:
            Delegates to ``VMSnapshotManager.restore`` so the snap_machine
            (machine key) is resolved to the snapshot VM key before posting
            to ``vm_actions``. Posting the machine key as a VM key fails
            with NotFound (or, if keys collide, can clone the wrong VM).
        """
        manager = cast("VMSnapshotManager", self._manager)
        return manager.restore(self.key, name=name, power_on=power_on)


class VMSnapshotManager(ResourceManager[VMSnapshot]):
    """Manager for VM Snapshot operations.

    This manager is accessed through a VM object's snapshots property.
    """

    _endpoint = "machine_snapshots"
    _default_fields = SNAPSHOT_DEFAULT_FIELDS

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

    def _to_model(self, data: dict[str, Any]) -> VMSnapshot:
        return VMSnapshot(data, self)

    def list(  # noqa: A003
        self,
        filter: str | None = None,  # noqa: A002
        fields: str | list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        **kwargs: Any,
    ) -> list[VMSnapshot]:
        """List snapshots for this VM.

        Args:
            filter: Additional OData filter string.
            fields: List of fields to return.
            **kwargs: Additional filter arguments.

        Returns:
            List of VMSnapshot objects.
        """
        if fields is None:
            fields = self._default_fields

        # Build filter for this VM's machine
        machine_filter = f"machine eq {self.machine_key}"
        if filter:
            machine_filter = f"{machine_filter} and ({filter})"
        # Merge shorthand kwargs instead of silently dropping them (issue #96)
        combined_filter = combine_filters(machine_filter, kwargs)

        params: dict[str, Any] = {
            "filter": combined_filter,
            "fields": self._projection(fields),
            "sort": "-created",  # Most recent first
        }
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
        fields: str | builtins.list[str] | None = None,
    ) -> VMSnapshot:
        """Get a snapshot by key or name.

        Args:
            key: Snapshot $key (ID).
            name: Snapshot name.
            fields: List of fields to return.

        Returns:
            VMSnapshot object.

        Raises:
            NotFoundError: If snapshot not found.
            ValueError: If neither key nor name provided.
        """
        if fields is None:
            fields = self._default_fields

        if key is not None:
            params: dict[str, Any] = {"fields": self._projection(fields)}
            response = self._client._request("GET", f"{self._endpoint}/{key}", params=params)
            if response is None:
                from pyvergeos.exceptions import NotFoundError

                raise NotFoundError(f"Snapshot {key} not found")
            if not isinstance(response, dict):
                from pyvergeos.exceptions import NotFoundError

                raise NotFoundError(f"Snapshot {key} returned invalid response")
            return self._to_model(response)

        if name is not None:
            snapshots = self.list(filter=f"name eq {quote_value(name)}", fields=fields)
            if not snapshots:
                from pyvergeos.exceptions import NotFoundError

                raise NotFoundError(f"Snapshot with name '{name}' not found")
            return snapshots[0]

        raise ValueError("Either key or name must be provided")

    def create(  # type: ignore[override]
        self,
        name: str | None = None,
        retention: int = 86400,
        quiesce: bool = False,
        description: str = "",
    ) -> dict[str, Any] | None:
        """Create a new snapshot for this VM.

        Args:
            name: Snapshot name (optional, auto-generated with timestamp if not provided).
            retention: Snapshot retention in seconds (default 24h). Use 0 for
                never expires. Omitted uses the 24h default. Negative values
                and None are rejected.
            quiesce: Quiesce disk activity (requires guest agent).
            description: Snapshot description.

        Returns:
            Created snapshot information.
        """
        import time as _time

        # None/bool must not fall through: bool is an int, and False would
        # otherwise be stored as expires:0 ("never").
        if retention is None or isinstance(retention, bool):
            raise TypeError("retention must be an int number of seconds; use 0 for never expires")
        if retention < 0:
            raise ValueError("retention must be non-negative; use 0 for never expires")

        # Generate snapshot name if not provided
        snapshot_name = name or f"Snapshot-{_time.strftime('%Y%m%d-%H%M%S')}"

        # Calculate expiration timestamp (0 means never expires)
        expires_timestamp = int(_time.time()) + retention if retention > 0 else 0

        body: dict[str, Any] = {
            "machine": self.machine_key,
            "name": snapshot_name,
            "created_manually": True,
            "quiesce": quiesce,
        }

        # Always send expires: retention=0 must be expires:0 ("never"), not
        # omitted — omitting lets the platform default to +72h (#146).
        body["expires"] = expires_timestamp

        if description:
            body["description"] = description

        result = self._client._request("POST", self._endpoint, json_data=body)
        return result if isinstance(result, dict) else None

    def delete(self, key: int) -> None:
        """Delete a snapshot.

        Args:
            key: Snapshot $key (ID).
        """
        self._client._request("DELETE", f"{self._endpoint}/{key}")

    def restore(
        self,
        key: int,
        name: str | None = None,
        replace_original: bool = False,
        power_on: bool = False,
    ) -> dict[str, Any] | None:
        """Restore a snapshot.

        Args:
            key: Snapshot $key (ID).
            name: Name for the restored VM (only for clone mode).
            replace_original: If True, revert original VM to snapshot state.
                              WARNING: All changes since snapshot will be lost.
            power_on: Power on VM after restoration.

        Returns:
            Restore task information.
        """
        snapshot = self.get(key)
        snap_machine_key = snapshot.snap_machine_key

        if snap_machine_key is None:
            raise ValueError("Snapshot does not have a valid snap_machine reference")

        # Find the snapshot VM that has this machine
        # The snap_machine is a machine key, not a VM key
        # We need to find the VM where machine = snap_machine
        response = self._client._request(
            "GET",
            "vms",
            params={
                "filter": f"machine eq {snap_machine_key}",
                "fields": "$key,name,machine,is_snapshot",
            },
        )

        snap_vm_key = None
        if response:
            vms = response if isinstance(response, list) else [response]
            for vm_data in vms:
                if not isinstance(vm_data, dict) or not vm_data.get("is_snapshot"):
                    continue
                # Trust an integer machine when the server returned one. A
                # row for a different machine must not be cloned just because
                # it is also a snapshot (key-collision case, #147).
                machine = vm_data.get("machine")
                if (
                    isinstance(machine, int)
                    and not isinstance(machine, bool)
                    and machine != snap_machine_key
                ):
                    continue
                vm_key = vm_data.get("$key")
                if vm_key is None:
                    continue
                snap_vm_key = vm_key
                break

        if snap_vm_key is None:
            raise ValueError(f"Could not find snapshot VM with machine key {snap_machine_key}")

        if replace_original:
            # In-place restore - revert original VM
            if self._vm.is_running:
                raise ValueError("VM must be powered off for in-place restore")

            body: dict[str, Any] = {
                "vm": snap_vm_key,
                "action": "restore",
            }

            result = self._client._request("POST", "vm_actions", json_data=body)

            if power_on and result:
                import time

                time.sleep(2)
                self._client._request(
                    "POST",
                    "vm_actions",
                    json_data={"vm": self._vm.key, "action": "poweron"},
                )

            return result if isinstance(result, dict) else None
        else:
            # Clone mode - create new VM from snapshot
            restored_name = name or f"{snapshot.get('name', 'snapshot')} restored"

            body = {
                "vm": snap_vm_key,
                "action": "clone",
                "params": {"name": restored_name},
            }

            result = self._client._request("POST", "vm_actions", json_data=body)

            if power_on and result and isinstance(result, dict):
                new_vm_key = result.get("$key") or result.get("key")
                if new_vm_key:
                    import time

                    time.sleep(2)
                    self._client._request(
                        "POST",
                        "vm_actions",
                        json_data={"vm": new_vm_key, "action": "poweron"},
                    )

            return result if isinstance(result, dict) else None
