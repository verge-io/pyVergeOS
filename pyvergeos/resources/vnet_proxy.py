"""Network proxy resource managers for multi-tenant FQDN-based access."""

from __future__ import annotations

import builtins
from typing import TYPE_CHECKING, Any

from pyvergeos.exceptions import NotFoundError
from pyvergeos.resources.base import ResourceManager, ResourceObject

if TYPE_CHECKING:
    from pyvergeos.client import VergeClient
    from pyvergeos.resources.networks import Network


class VnetProxyTenant(ResourceObject):
    """Tenant FQDN mapping for proxy service.

    Maps a tenant to an FQDN for access through the network's proxy service.
    Multiple tenants can share a single IP address by using different FQDNs.
    """

    @property
    def tenant_key(self) -> int:
        """Get the tenant key."""
        return int(self.get("tenant", 0))

    @property
    def tenant_name(self) -> str:
        """Get the tenant display name."""
        return str(self.get("tenant_display", ""))

    @property
    def fqdn(self) -> str:
        """Get the FQDN for this tenant mapping."""
        return str(self.get("fqdn", ""))

    @property
    def proxy_key(self) -> int:
        """Get the parent proxy configuration key."""
        return int(self.get("proxy", 0))

    def refresh(self) -> VnetProxyTenant:
        """Refresh this tenant mapping from the API.

        Returns:
            Updated VnetProxyTenant instance.
        """
        manager = self._manager
        if not isinstance(manager, VnetProxyTenantManager):
            raise TypeError("Manager must be VnetProxyTenantManager")
        return manager.get(self.key)

    def save(self, **kwargs: Any) -> VnetProxyTenant:
        """Save changes to this tenant mapping.

        Args:
            **kwargs: Fields to update.

        Returns:
            Updated VnetProxyTenant instance.
        """
        manager = self._manager
        if not isinstance(manager, VnetProxyTenantManager):
            raise TypeError("Manager must be VnetProxyTenantManager")
        return manager.update(self.key, **kwargs)

    def delete(self) -> None:
        """Delete this tenant mapping."""
        manager = self._manager
        if not isinstance(manager, VnetProxyTenantManager):
            raise TypeError("Manager must be VnetProxyTenantManager")
        manager.delete(self.key)


class VnetProxyTenantManager(ResourceManager[VnetProxyTenant]):
    """Manager for proxy tenant FQDN mappings.

    Scoped to a specific proxy configuration. Access via VnetProxy.tenants.

    Examples:
        List all tenant mappings::

            tenants = proxy.tenants.list()

        Get a specific mapping::

            mapping = proxy.tenants.get(key=1)
            mapping = proxy.tenants.get(fqdn="tenant1.example.com")

        Create a new mapping::

            mapping = proxy.tenants.create(
                tenant=tenant_key,
                fqdn="tenant1.example.com"
            )

        Delete a mapping::

            proxy.tenants.delete(key=1)
    """

    _endpoint = "vnet_proxy_tenants"

    def __init__(self, client: VergeClient, proxy: VnetProxy) -> None:
        """Initialize the proxy tenant manager.

        Args:
            client: VergeClient instance.
            proxy: Parent VnetProxy object.
        """
        super().__init__(client)
        self._proxy = proxy

    def _to_model(self, data: dict[str, Any]) -> VnetProxyTenant:
        return VnetProxyTenant(data, self)

    def list(
        self,
        filter: str | None = None,
        fields: builtins.list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        **filter_kwargs: Any,
    ) -> builtins.list[VnetProxyTenant]:
        """List proxy tenant mappings.

        Args:
            filter: OData filter string.
            fields: List of fields to return.
            limit: Maximum number of results.
            offset: Skip this many results.
            **filter_kwargs: Shorthand filter arguments.

        Returns:
            List of VnetProxyTenant objects.
        """
        # Scope to this proxy
        proxy_filter = f"proxy eq {self._proxy.key}"
        filter = f"({filter}) and {proxy_filter}" if filter else proxy_filter

        if fields is None:
            fields = [
                "$key",
                "proxy",
                "tenant",
                "tenant#$display as tenant_display",
                "fqdn",
                "modified",
            ]

        return super().list(
            filter=filter,
            fields=fields,
            limit=limit,
            offset=offset,
            **filter_kwargs,
        )

    def get(  # type: ignore[override]
        self,
        key: int | None = None,
        *,
        fqdn: str | None = None,
        tenant: int | None = None,
        fields: builtins.list[str] | None = None,
    ) -> VnetProxyTenant:
        """Get a proxy tenant mapping by key, FQDN, or tenant.

        Args:
            key: Mapping $key (ID).
            fqdn: FQDN to look up.
            tenant: Tenant key to look up.
            fields: List of fields to return.

        Returns:
            VnetProxyTenant object.

        Raises:
            NotFoundError: If mapping not found.
            ValueError: If no lookup parameter provided.
        """
        if fields is None:
            fields = [
                "$key",
                "proxy",
                "tenant",
                "tenant#$display as tenant_display",
                "fqdn",
                "modified",
            ]

        if key is not None:
            # Direct key lookup - verify it belongs to this proxy
            params = {
                "filter": f"$key eq {key} and proxy eq {self._proxy.key}",
                "fields": ",".join(fields),
            }
            response = self._client._request("GET", self._endpoint, params=params)
            if not response:
                raise NotFoundError(f"Proxy tenant mapping with key {key} not found")
            if isinstance(response, builtins.list):
                if not response:
                    raise NotFoundError(f"Proxy tenant mapping with key {key} not found")
                return self._to_model(response[0])
            return self._to_model(response)

        # Build filter for other lookups
        filter_parts = [f"proxy eq {self._proxy.key}"]
        if fqdn is not None:
            filter_parts.append(f"fqdn eq '{fqdn}'")
        elif tenant is not None:
            filter_parts.append(f"tenant eq {tenant}")
        else:
            raise ValueError("Must provide key, fqdn, or tenant")

        params = {
            "filter": " and ".join(filter_parts),
            "fields": ",".join(fields),
        }
        response = self._client._request("GET", self._endpoint, params=params)
        if not response:
            raise NotFoundError("Proxy tenant mapping not found")
        if isinstance(response, builtins.list):
            if not response:
                raise NotFoundError("Proxy tenant mapping not found")
            return self._to_model(response[0])
        return self._to_model(response)

    def create(  # type: ignore[override]
        self,
        tenant: int,
        fqdn: str,
        **kwargs: Any,
    ) -> VnetProxyTenant:
        """Create a new proxy tenant mapping.

        Maps a tenant to an FQDN for access through this proxy service.

        Args:
            tenant: Tenant $key (ID) to map.
            fqdn: Fully qualified domain name for the tenant.
            **kwargs: Additional fields.

        Returns:
            Created VnetProxyTenant object.

        Examples:
            Create a tenant mapping::

                mapping = proxy.tenants.create(
                    tenant=5,
                    fqdn="tenant1.example.com"
                )
        """
        data = {
            "proxy": self._proxy.key,
            "tenant": tenant,
            "fqdn": fqdn,
            **kwargs,
        }

        response = self._client._request("POST", self._endpoint, json_data=data)
        if response is None:
            raise ValueError("No response from create operation")
        if not isinstance(response, dict):
            raise ValueError("Create operation returned invalid response")

        key = response.get("$key")
        if key is None:
            raise ValueError("Create response missing $key")

        return self.get(int(key))

    def update(
        self,
        key: int,
        **kwargs: Any,
    ) -> VnetProxyTenant:
        """Update a proxy tenant mapping.

        Args:
            key: Mapping $key (ID).
            **kwargs: Fields to update (fqdn, tenant).

        Returns:
            Updated VnetProxyTenant object.
        """
        # Verify the mapping belongs to this proxy
        self.get(key)  # Raises NotFoundError if not found

        self._client._request("PUT", f"{self._endpoint}/{key}", json_data=kwargs)
        return self.get(key)

    def delete(self, key: int) -> None:
        """Delete a proxy tenant mapping.

        Args:
            key: Mapping $key (ID) to delete.
        """
        # Verify the mapping belongs to this proxy
        self.get(key)  # Raises NotFoundError if not found
        self._client._request("DELETE", f"{self._endpoint}/{key}")


class VnetProxy(ResourceObject):
    """Network proxy configuration.

    Enables multi-tenant access through a single IP address using FQDN mapping.
    Each tenant is assigned a unique FQDN that routes to their UI through the
    proxy service.
    """

    @property
    def network_key(self) -> int:
        """Get the parent network key."""
        return int(self.get("vnet", 0))

    @property
    def network_name(self) -> str:
        """Get the parent network display name."""
        return str(self.get("vnet_display", ""))

    @property
    def listen_address(self) -> str:
        """Get the proxy listen address.

        Returns:
            Listen address (default "0.0.0.0" for all addresses).
        """
        return str(self.get("listen_address", "0.0.0.0"))

    @property
    def default_self(self) -> bool:
        """Check if proxy defaults to self when no tenant matches.

        When True, requests with no matching FQDN will show this system's UI.
        """
        return bool(self.get("default_self", True))

    @property
    def tenants(self) -> VnetProxyTenantManager:
        """Access tenant FQDN mappings for this proxy.

        Returns:
            VnetProxyTenantManager for this proxy.

        Examples:
            List all tenant mappings::

                for mapping in proxy.tenants.list():
                    print(f"{mapping.fqdn} -> Tenant {mapping.tenant_name}")

            Create a new mapping::

                mapping = proxy.tenants.create(
                    tenant=tenant_key,
                    fqdn="newtenant.example.com"
                )
        """
        return VnetProxyTenantManager(self._manager._client, self)

    def refresh(self) -> VnetProxy:
        """Refresh this proxy configuration from the API.

        Returns:
            Updated VnetProxy instance.
        """
        manager = self._manager
        if not isinstance(manager, VnetProxyManager):
            raise TypeError("Manager must be VnetProxyManager")
        return manager.get(self.key)

    def save(
        self,
        listen_address: str | None = None,
        default_self: bool | None = None,
        **kwargs: Any,
    ) -> VnetProxy:
        """Save changes to this proxy configuration.

        Args:
            listen_address: New listen address.
            default_self: Whether to default to self UI when no match.
            **kwargs: Additional fields.

        Returns:
            Updated VnetProxy instance.
        """
        manager = self._manager
        if not isinstance(manager, VnetProxyManager):
            raise TypeError("Manager must be VnetProxyManager")

        update_data: dict[str, Any] = {**kwargs}
        if listen_address is not None:
            update_data["listen_address"] = listen_address
        if default_self is not None:
            update_data["default_self"] = default_self

        return manager.update(self.key, **update_data)

    def delete(self) -> None:
        """Delete this proxy configuration.

        Note:
            This will also delete all associated tenant mappings.
        """
        manager = self._manager
        if not isinstance(manager, VnetProxyManager):
            raise TypeError("Manager must be VnetProxyManager")
        manager.delete(self.key)


class VnetProxyManager(ResourceManager[VnetProxy]):
    """Manager for network proxy configuration.

    Scoped to a specific network. Access via Network.proxy.

    The proxy service allows multiple tenants to share a single external IP
    address by using FQDN-based routing. Each tenant is assigned a unique
    hostname that routes to their UI through the proxy.

    Examples:
        Get proxy configuration for a network::

            proxy = network.proxy.get()
            print(f"Listen address: {proxy.listen_address}")

        Create/enable proxy on a network::

            proxy = network.proxy.create(
                listen_address="0.0.0.0",
                default_self=True
            )

        List tenant mappings::

            for mapping in proxy.tenants.list():
                print(f"{mapping.fqdn} -> {mapping.tenant_name}")

        Add a tenant mapping::

            mapping = proxy.tenants.create(
                tenant=tenant_key,
                fqdn="tenant1.example.com"
            )

    Note:
        Only one proxy configuration can exist per network.
        The proxy service is typically used on external networks.
    """

    _endpoint = "vnet_proxy"

    def __init__(self, client: VergeClient, network: Network) -> None:
        """Initialize the proxy manager.

        Args:
            client: VergeClient instance.
            network: Parent Network object.
        """
        super().__init__(client)
        self._network = network

    def _to_model(self, data: dict[str, Any]) -> VnetProxy:
        return VnetProxy(data, self)

    def exists(self) -> bool:
        """Check if proxy is configured for this network.

        Returns:
            True if proxy configuration exists.
        """
        try:
            self.get()
            return True
        except NotFoundError:
            return False

    def get(  # type: ignore[override]
        self,
        key: int | None = None,
        *,
        fields: builtins.list[str] | None = None,
    ) -> VnetProxy:
        """Get the proxy configuration for this network.

        Args:
            key: Optional proxy $key (ID). If not provided, gets the
                proxy for this network (there's only one per network).
            fields: List of fields to return.

        Returns:
            VnetProxy object.

        Raises:
            NotFoundError: If proxy not configured for this network.
        """
        if fields is None:
            fields = [
                "$key",
                "vnet",
                "vnet#$display as vnet_display",
                "name",
                "listen_address",
                "default_self",
                "modified",
            ]

        if key is not None:
            # Verify it belongs to this network
            params = {
                "filter": f"$key eq {key} and vnet eq {self._network.key}",
                "fields": ",".join(fields),
            }
        else:
            # Get by network
            params = {
                "filter": f"vnet eq {self._network.key}",
                "fields": ",".join(fields),
            }

        response = self._client._request("GET", self._endpoint, params=params)
        if not response:
            raise NotFoundError(f"Proxy not configured for network {self._network.name}")
        if isinstance(response, builtins.list):
            if not response:
                raise NotFoundError(f"Proxy not configured for network {self._network.name}")
            return self._to_model(response[0])
        return self._to_model(response)

    def create(
        self,
        listen_address: str = "0.0.0.0",
        default_self: bool = True,
        **kwargs: Any,
    ) -> VnetProxy:
        """Create/enable proxy configuration for this network.

        Args:
            listen_address: Address to listen on (default "0.0.0.0" for all).
            default_self: Default to this system's UI when no FQDN matches.
            **kwargs: Additional fields.

        Returns:
            Created VnetProxy object.

        Note:
            Only one proxy configuration can exist per network.
            Creating a proxy when one already exists will raise an error.

        Examples:
            Enable proxy with defaults::

                proxy = network.proxy.create()

            Enable proxy with custom listen address::

                proxy = network.proxy.create(listen_address="192.168.1.1")
        """
        # Check if proxy already exists
        if self.exists():
            raise ValueError(
                f"Proxy already configured for network {self._network.name}. "
                "Use update() to modify or delete() first."
            )

        data = {
            "vnet": self._network.key,
            "listen_address": listen_address,
            "default_self": default_self,
            **kwargs,
        }

        response = self._client._request("POST", self._endpoint, json_data=data)
        if response is None:
            raise ValueError("No response from create operation")
        if not isinstance(response, dict):
            raise ValueError("Create operation returned invalid response")

        key = response.get("$key")
        if key is None:
            raise ValueError("Create response missing $key")

        return self.get(int(key))

    def update(
        self,
        key: int,
        **kwargs: Any,
    ) -> VnetProxy:
        """Update proxy configuration.

        Args:
            key: Proxy $key (ID).
            **kwargs: Fields to update (listen_address, default_self).

        Returns:
            Updated VnetProxy object.
        """
        # Verify it belongs to this network
        self.get(key)  # Raises NotFoundError if not found

        self._client._request("PUT", f"{self._endpoint}/{key}", json_data=kwargs)
        return self.get(key)

    def delete(self, key: int | None = None) -> None:
        """Delete proxy configuration for this network.

        Args:
            key: Proxy $key (ID). If not provided, deletes the proxy
                for this network.

        Note:
            This will also delete all associated tenant mappings.
        """
        if key is None:
            proxy = self.get()  # Raises NotFoundError if not found
            key = proxy.key

        # Verify it belongs to this network
        self.get(key)  # Raises NotFoundError if not found
        self._client._request("DELETE", f"{self._endpoint}/{key}")

    def get_or_create(
        self,
        listen_address: str = "0.0.0.0",
        default_self: bool = True,
        **kwargs: Any,
    ) -> VnetProxy:
        """Get existing proxy or create new one.

        Convenience method that returns existing proxy configuration
        or creates a new one with the provided settings.

        Args:
            listen_address: Listen address for new proxy.
            default_self: Default self setting for new proxy.
            **kwargs: Additional fields for new proxy.

        Returns:
            VnetProxy object (existing or newly created).

        Examples:
            Ensure proxy is configured::

                proxy = network.proxy.get_or_create()
        """
        try:
            return self.get()
        except NotFoundError:
            return self.create(
                listen_address=listen_address,
                default_self=default_self,
                **kwargs,
            )
