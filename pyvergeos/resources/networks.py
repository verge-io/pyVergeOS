"""Virtual Network resource manager."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pyvergeos.resources.base import ResourceManager, ResourceObject

if TYPE_CHECKING:
    from pyvergeos.client import VergeClient


class Network(ResourceObject):
    """Virtual Network resource object."""

    def power_on(self, apply_rules: bool = True) -> Network:
        """Power on the network.

        Args:
            apply_rules: Apply firewall rules on start.

        Returns:
            Self for chaining.
        """
        self._manager.action(self.key, "poweron", apply=apply_rules)
        return self

    def power_off(self) -> Network:
        """Power off the network."""
        self._manager.action(self.key, "poweroff")
        return self

    def reset(self, apply_rules: bool = True) -> Network:
        """Reset the network.

        Args:
            apply_rules: Apply firewall rules on restart.

        Returns:
            Self for chaining.
        """
        self._manager.action(self.key, "reset", apply=apply_rules)
        return self

    def apply_rules(self) -> Network:
        """Apply firewall rules."""
        self._manager.action(self.key, "apply")
        return self

    def apply_dns(self) -> Network:
        """Apply DNS configuration."""
        self._manager.action(self.key, "applydns")
        return self

    @property
    def is_running(self) -> bool:
        """Check if network is powered on."""
        return bool(self.get("powerstate", False))

    @property
    def needs_restart(self) -> bool:
        """Check if network needs restart to apply changes."""
        return bool(self.get("need_restart", False))

    @property
    def needs_rule_apply(self) -> bool:
        """Check if firewall rules need to be applied."""
        return bool(self.get("need_fw_apply", False))


class NetworkManager(ResourceManager[Network]):
    """Manager for Virtual Network operations."""

    _endpoint = "vnets"

    def __init__(self, client: VergeClient) -> None:
        super().__init__(client)

    def _to_model(self, data: dict[str, Any]) -> Network:
        return Network(data, self)

    def list_internal(self) -> list[Network]:
        """List internal networks."""
        return self.list(filter="type eq 'internal'")

    def list_external(self) -> list[Network]:
        """List external networks."""
        return self.list(filter="type eq 'external'")

    def list_running(self) -> list[Network]:
        """List all running networks."""
        return self.list(filter="powerstate eq true")

    def create(  # type: ignore[override]
        self,
        name: str,
        network_type: str = "internal",
        network_address: str | None = None,
        ip_address: str | None = None,
        dhcp_enabled: bool = False,
        description: str = "",
        **kwargs: Any,
    ) -> Network:
        """Create a new virtual network.

        Args:
            name: Network name.
            network_type: Network type (internal, external, dmz, etc.).
            network_address: CIDR notation (e.g., "192.168.1.0/24").
            ip_address: Router IP address.
            dhcp_enabled: Enable DHCP server.
            description: Network description.
            **kwargs: Additional network properties.

        Returns:
            Created network object.
        """
        data: dict[str, Any] = {
            "name": name,
            "type": network_type,
            "dhcp_enabled": dhcp_enabled,
            "description": description,
            **kwargs,
        }

        if network_address:
            data["network"] = network_address
        if ip_address:
            data["ipaddress"] = ip_address

        return super().create(**data)
