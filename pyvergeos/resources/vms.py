"""Virtual Machine resource manager."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from pyvergeos.resources.base import ResourceManager, ResourceObject

if TYPE_CHECKING:
    from pyvergeos.client import VergeClient

logger = logging.getLogger(__name__)


class VM(ResourceObject):
    """Virtual Machine resource object."""

    def power_on(self, preferred_node: int | None = None) -> VM:
        """Power on the VM.

        Args:
            preferred_node: Node $key to start VM on.

        Returns:
            Self for chaining.
        """
        kwargs: dict[str, Any] = {}
        if preferred_node is not None:
            kwargs["preferred_node"] = preferred_node
        self._manager.action(self.key, "poweron", **kwargs)
        return self  # type: ignore[return-value]

    def power_off(self) -> VM:
        """Graceful power off (ACPI shutdown)."""
        self._manager.action(self.key, "poweroff")
        return self  # type: ignore[return-value]

    def kill_power(self) -> VM:
        """Force power off (like pulling the plug)."""
        self._manager.action(self.key, "killpower")
        return self  # type: ignore[return-value]

    def reset(self) -> VM:
        """Reset VM."""
        self._manager.action(self.key, "reset")
        return self  # type: ignore[return-value]

    def guest_reboot(self) -> VM:
        """Send reboot signal to guest OS (requires guest agent)."""
        self._manager.action(self.key, "guestreset")
        return self  # type: ignore[return-value]

    def snapshot(
        self,
        retention: int = 86400,
        quiesce: bool = False,
    ) -> dict[str, Any] | None:
        """Take a VM snapshot.

        Args:
            retention: Snapshot retention in seconds (default 24h).
            quiesce: Quiesce disk activity (requires guest agent).

        Returns:
            Snapshot task information.
        """
        return self._manager.action(
            self.key,
            "snapshot",
            retention=retention,
            quiesce=quiesce,
        )

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
        kwargs: dict[str, Any] = {"preserve_macs": preserve_macs}
        if name:
            kwargs["name"] = name
        return self._manager.action(self.key, "clone", **kwargs)

    @property
    def is_running(self) -> bool:
        """Check if VM is powered on."""
        return bool(self.get("powerstate", False))

    @property
    def is_snapshot(self) -> bool:
        """Check if this is a snapshot (not a running VM)."""
        return bool(self.get("is_snapshot", False))


class VMManager(ResourceManager[VM]):
    """Manager for Virtual Machine operations."""

    _endpoint = "vms"

    def __init__(self, client: VergeClient) -> None:
        super().__init__(client)

    def _to_model(self, data: dict[str, Any]) -> VM:
        return VM(data, self)

    def list_running(self) -> list[VM]:
        """List all running VMs."""
        return self.list(filter="powerstate eq true and is_snapshot eq false")

    def list_stopped(self) -> list[VM]:
        """List all stopped VMs."""
        return self.list(filter="powerstate eq false and is_snapshot eq false")

    def create(
        self,
        name: str,
        ram: int = 1024,
        cpu_cores: int = 1,
        description: str = "",
        os_family: str = "linux",
        machine_type: str = "pc-q35-10.0",
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
            **kwargs: Additional VM properties.

        Returns:
            Created VM object.
        """
        # Normalize RAM to 256 MB increments
        normalized_ram = ((ram + 255) // 256) * 256
        if normalized_ram != ram:
            logger.info("RAM normalized from %dMB to %dMB", ram, normalized_ram)

        data = {
            "name": name,
            "ram": normalized_ram,
            "cpu_cores": cpu_cores,
            "description": description,
            "os_family": os_family,
            "machine_type": machine_type,
            **kwargs,
        }

        return super().create(**data)
