"""VM NIC resource manager."""

from __future__ import annotations

import builtins
import logging
from typing import TYPE_CHECKING, Any

from pyvergeos.resources.base import ResourceManager, ResourceObject

if TYPE_CHECKING:
    from pyvergeos.client import VergeClient
    from pyvergeos.resources.vms import VM

logger = logging.getLogger(__name__)

# Default fields for NICs
NIC_DEFAULT_FIELDS = [
    "$key",
    "name",
    "orderid",
    "interface",
    "description",
    "enabled",
    "macaddress",
    "ipaddress",
    "vnet",
    "machine",
    "status#status as status",
    "status#display(status) as status_display",
    "status#speed as speed",
    "vnet#$key as vnet_key",
    "vnet#name as vnet_name",
    "vnet#machine#status#status as vnet_status",
    "stats#rx_bytes as rx_bytes",
    "stats#tx_bytes as tx_bytes",
    "stats#rxbps as rxbps",
    "stats#txbps as txbps",
]

# Interface display names
INTERFACE_DISPLAY_MAP = {
    "virtio": "Virtio",
    "e1000": "Intel e1000",
    "e1000e": "Intel e1000e",
    "rtl8139": "Realtek 8139",
    "pcnet": "AMD PCnet",
    "igb": "Intel 82576",
    "vmxnet3": "VMware Paravirt v3",
    "direct": "Direct",
}


class NIC(ResourceObject):
    """VM NIC resource object."""

    @property
    def interface_display(self) -> str:
        """Get friendly interface name."""
        interface = self.get("interface", "")
        return INTERFACE_DISPLAY_MAP.get(interface, str(interface))

    @property
    def is_enabled(self) -> bool:
        """Check if NIC is enabled."""
        return bool(self.get("enabled", True))

    @property
    def mac_address(self) -> str | None:
        """Get MAC address."""
        return self.get("macaddress")

    @property
    def ip_address(self) -> str | None:
        """Get IP address."""
        return self.get("ipaddress")

    @property
    def network_name(self) -> str | None:
        """Get connected network name."""
        return self.get("vnet_name")

    @property
    def network_key(self) -> int | None:
        """Get connected network key."""
        key = self.get("vnet_key")
        return int(key) if key is not None else None

    @property
    def speed_display(self) -> str | None:
        """Get formatted speed string."""
        speed = self.get("speed")
        if not speed:
            return None
        if speed >= 1000:
            return f"{round(speed / 1000, 1)} Gbps"
        return f"{speed} Mbps"

    @property
    def rx_bytes(self) -> int:
        """Get received bytes."""
        return int(self.get("rx_bytes") or 0)

    @property
    def tx_bytes(self) -> int:
        """Get transmitted bytes."""
        return int(self.get("tx_bytes") or 0)


class NICManager(ResourceManager[NIC]):
    """Manager for VM NIC operations.

    This manager is accessed through a VM object's nics property.
    """

    _endpoint = "machine_nics"
    _default_fields = NIC_DEFAULT_FIELDS

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

    def _to_model(self, data: dict[str, Any]) -> NIC:
        return NIC(data, self)

    def list(  # type: ignore[override]  # noqa: A003
        self,
        filter: str | None = None,  # noqa: A002
        fields: list[str] | None = None,
        **kwargs: Any,
    ) -> list[NIC]:
        """List NICs for this VM.

        Args:
            filter: Additional OData filter string.
            fields: List of fields to return.
            **kwargs: Additional filter arguments.

        Returns:
            List of NIC objects.
        """
        if fields is None:
            fields = self._default_fields

        # Build filter for this VM's machine
        machine_filter = f"machine eq {self.machine_key}"
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
    ) -> NIC:
        """Get a NIC by key or name.

        Args:
            key: NIC $key (ID).
            name: NIC name.
            fields: List of fields to return.

        Returns:
            NIC object.

        Raises:
            NotFoundError: If NIC not found.
            ValueError: If neither key nor name provided.
        """
        if fields is None:
            fields = self._default_fields

        if key is not None:
            params: dict[str, Any] = {"fields": ",".join(fields)}
            response = self._client._request("GET", f"{self._endpoint}/{key}", params=params)
            if response is None:
                from pyvergeos.exceptions import NotFoundError

                raise NotFoundError(f"NIC {key} not found")
            if not isinstance(response, dict):
                from pyvergeos.exceptions import NotFoundError

                raise NotFoundError(f"NIC {key} returned invalid response")
            return self._to_model(response)

        if name is not None:
            nics = self.list(filter=f"name eq '{name}'", fields=fields)
            if not nics:
                from pyvergeos.exceptions import NotFoundError

                raise NotFoundError(f"NIC with name '{name}' not found")
            return nics[0]

        raise ValueError("Either key or name must be provided")

    def create(  # type: ignore[override]
        self,
        network: int | str | None = None,
        name: str | None = None,
        interface: str = "virtio",
        mac_address: str | None = None,
        ip_address: str | None = None,
        description: str = "",
        enabled: bool = True,
    ) -> NIC:
        """Create a new NIC for this VM.

        Args:
            network: Network key (int) or name (str) to connect to.
            name: NIC name (optional, auto-generated if not provided).
            interface: NIC interface type (virtio, e1000, e1000e, etc.).
            mac_address: MAC address (format: xx:xx:xx:xx:xx:xx).
            ip_address: Static IP address.
            description: NIC description.
            enabled: Enable NIC (default True).

        Returns:
            Created NIC object.
        """
        body: dict[str, Any] = {
            "machine": self.machine_key,
            "interface": interface,
            "enabled": enabled,
        }

        if name:
            body["name"] = name

        # Resolve network by name if string provided
        if network is not None:
            if isinstance(network, str):
                # Look up network by name
                response = self._client._request(
                    "GET",
                    "vnets",
                    params={"filter": f"name eq '{network}'", "fields": "$key,name"},
                )
                if not response:
                    raise ValueError(f"Network '{network}' not found")
                if isinstance(response, list):
                    if not response:
                        raise ValueError(f"Network '{network}' not found")
                    network = response[0].get("$key")
                else:
                    network = response.get("$key")
            body["vnet"] = int(network)  # type: ignore[arg-type]

        if mac_address:
            body["macaddress"] = mac_address.lower()

        if ip_address:
            body["ipaddress"] = ip_address

        if description:
            body["description"] = description

        response = self._client._request("POST", self._endpoint, json_data=body)
        if response is None:
            raise ValueError("No response from create operation")
        if not isinstance(response, dict):
            raise ValueError("Create operation returned invalid response")
        # Fetch the full NIC data with all fields
        nic = self._to_model(response)
        return self.get(nic.key)

    def delete(self, key: int) -> None:
        """Delete a NIC.

        Args:
            key: NIC $key (ID).

        Note:
            VM should typically be powered off before removing NICs.
        """
        self._client._request("DELETE", f"{self._endpoint}/{key}")

    def update(self, key: int, **kwargs: Any) -> NIC:
        """Update a NIC.

        Args:
            key: NIC $key (ID).
            **kwargs: Fields to update.

        Returns:
            Updated NIC object.
        """
        # Handle network name -> key resolution
        if "network" in kwargs:
            network = kwargs.pop("network")
            if isinstance(network, str):
                response = self._client._request(
                    "GET",
                    "vnets",
                    params={"filter": f"name eq '{network}'", "fields": "$key,name"},
                )
                if not response:
                    raise ValueError(f"Network '{network}' not found")
                if isinstance(response, list):
                    if not response:
                        raise ValueError(f"Network '{network}' not found")
                    network = response[0].get("$key")
                else:
                    network = response.get("$key")
            kwargs["vnet"] = int(network)

        response = self._client._request("PUT", f"{self._endpoint}/{key}", json_data=kwargs)
        if response is None:
            return self.get(key)
        if not isinstance(response, dict):
            return self.get(key)
        return self._to_model(response)
