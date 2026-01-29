"""Site resource manager for VergeOS backup/DR operations."""

from __future__ import annotations

import builtins
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from pyvergeos.exceptions import NotFoundError, ValidationError
from pyvergeos.filters import build_filter
from pyvergeos.resources.base import ResourceManager, ResourceObject

if TYPE_CHECKING:
    from pyvergeos.client import VergeClient


# Default fields for site list operations
_DEFAULT_SITE_FIELDS = [
    "$key",
    "name",
    "description",
    "enabled",
    "url",
    "domain",
    "city",
    "country",
    "timezone",
    "latitude",
    "longitude",
    "status",
    "status_info",
    "authentication_status",
    "config_cloud_snapshots",
    "config_statistics",
    "config_management",
    "config_repair_server",
    "vsan_host",
    "vsan_port",
    "is_tenant",
    "incoming_syncs_enabled",
    "outgoing_syncs_enabled",
    "statistics_interval",
    "statistics_retention",
    "created",
    "modified",
    "creator",
]


class Site(ResourceObject):
    """Site resource object representing a connection to a remote VergeOS system.

    Sites are used for disaster recovery, replication, and remote management
    between VergeOS systems.

    Properties:
        name: Site name.
        description: Site description.
        is_enabled: Whether the site is enabled.
        url: URL of the remote VergeOS system.
        domain: Domain name for the site.
        city: City where the site is located.
        country: Country code where the site is located.
        timezone: Timezone for the site.
        latitude: Geographic latitude.
        longitude: Geographic longitude.
        status: Site status (idle, authenticating, syncing, error, warning).
        status_info: Additional status information.
        authentication_status: Authentication status (unauthenticated, authenticated, legacy).
        config_cloud_snapshots: Cloud snapshot sync config (disabled, send, receive, both).
        config_statistics: Statistics sync config (disabled, send, receive, both).
        config_management: Machine management config (disabled, manage, managed, both).
        config_repair_server: Repair server config (disabled, send, receive, both).
        vsan_host: vSAN connection host.
        vsan_port: vSAN connection port.
        is_tenant: Whether site is a tenant.
        has_incoming_syncs: Whether incoming syncs are enabled.
        has_outgoing_syncs: Whether outgoing syncs are enabled.
        statistics_interval: Statistics sync interval in seconds.
        statistics_retention: Statistics retention period in seconds.
        created_at: When the site was created.
        modified_at: When the site was last modified.
        creator: Username who created the site.
    """

    @property
    def name(self) -> str:
        """Get site name."""
        return str(self.get("name", ""))

    @property
    def description(self) -> str:
        """Get site description."""
        return str(self.get("description", ""))

    @property
    def is_enabled(self) -> bool:
        """Check if site is enabled."""
        return bool(self.get("enabled", False))

    @property
    def url(self) -> str:
        """Get site URL."""
        return str(self.get("url", ""))

    @property
    def domain(self) -> str:
        """Get site domain."""
        return str(self.get("domain", ""))

    @property
    def city(self) -> str:
        """Get site city."""
        return str(self.get("city", ""))

    @property
    def country(self) -> str:
        """Get site country code."""
        return str(self.get("country", ""))

    @property
    def timezone(self) -> str:
        """Get site timezone."""
        return str(self.get("timezone", ""))

    @property
    def latitude(self) -> float | None:
        """Get site latitude."""
        val = self.get("latitude")
        return float(val) if val is not None else None

    @property
    def longitude(self) -> float | None:
        """Get site longitude."""
        val = self.get("longitude")
        return float(val) if val is not None else None

    @property
    def status(self) -> str:
        """Get site status (idle, authenticating, syncing, error, warning)."""
        return str(self.get("status", "idle"))

    @property
    def status_info(self) -> str:
        """Get additional status information."""
        return str(self.get("status_info", ""))

    @property
    def authentication_status(self) -> str:
        """Get authentication status (unauthenticated, authenticated, legacy)."""
        return str(self.get("authentication_status", "unauthenticated"))

    @property
    def is_authenticated(self) -> bool:
        """Check if site is authenticated."""
        return self.authentication_status == "authenticated"

    @property
    def config_cloud_snapshots(self) -> str:
        """Get cloud snapshot sync config (disabled, send, receive, both)."""
        return str(self.get("config_cloud_snapshots", "disabled"))

    @property
    def config_statistics(self) -> str:
        """Get statistics sync config (disabled, send, receive, both)."""
        return str(self.get("config_statistics", "disabled"))

    @property
    def config_management(self) -> str:
        """Get machine management config (disabled, manage, managed, both)."""
        return str(self.get("config_management", "disabled"))

    @property
    def config_repair_server(self) -> str:
        """Get repair server config (disabled, send, receive, both)."""
        return str(self.get("config_repair_server", "disabled"))

    @property
    def vsan_host(self) -> str:
        """Get vSAN connection host."""
        return str(self.get("vsan_host", ""))

    @property
    def vsan_port(self) -> int:
        """Get vSAN connection port."""
        return int(self.get("vsan_port", 14201))

    @property
    def is_tenant(self) -> bool:
        """Check if site is a tenant."""
        return bool(self.get("is_tenant", False))

    @property
    def has_incoming_syncs(self) -> bool:
        """Check if incoming syncs are enabled."""
        return bool(self.get("incoming_syncs_enabled", False))

    @property
    def has_outgoing_syncs(self) -> bool:
        """Check if outgoing syncs are enabled."""
        return bool(self.get("outgoing_syncs_enabled", False))

    @property
    def statistics_interval(self) -> int:
        """Get statistics sync interval in seconds."""
        return int(self.get("statistics_interval", 600))

    @property
    def statistics_retention(self) -> int:
        """Get statistics retention period in seconds."""
        return int(self.get("statistics_retention", 3888000))

    @property
    def created_at(self) -> datetime | None:
        """Get creation timestamp."""
        ts = self.get("created")
        if ts:
            return datetime.fromtimestamp(int(ts), tz=timezone.utc)
        return None

    @property
    def modified_at(self) -> datetime | None:
        """Get last modified timestamp."""
        ts = self.get("modified")
        if ts:
            return datetime.fromtimestamp(int(ts), tz=timezone.utc)
        return None

    @property
    def creator(self) -> str:
        """Get username who created the site."""
        return str(self.get("creator", ""))

    def enable(self) -> Site:
        """Enable this site.

        Returns:
            Updated Site object.
        """
        from typing import cast

        manager = cast("SiteManager", self._manager)
        return manager.enable(self.key)

    def disable(self) -> Site:
        """Disable this site.

        Returns:
            Updated Site object.
        """
        from typing import cast

        manager = cast("SiteManager", self._manager)
        return manager.disable(self.key)

    def refresh(self) -> Site:
        """Refresh site data from server.

        Returns:
            Updated Site object.
        """
        from typing import cast

        manager = cast("SiteManager", self._manager)
        return manager.get(self.key)

    def reauthenticate(self, username: str, password: str) -> Site:
        """Reauthenticate with the remote site.

        Args:
            username: Username for authentication.
            password: Password for authentication.

        Returns:
            Updated Site object.
        """
        from typing import cast

        manager = cast("SiteManager", self._manager)
        return manager.reauthenticate(self.key, username, password)

    def delete(self) -> None:
        """Delete this site."""
        from typing import cast

        manager = cast("SiteManager", self._manager)
        manager.delete(self.key)

    def __repr__(self) -> str:
        key = self.get("$key", "?")
        name = self.name
        status = self.status
        return f"<Site key={key} name={name!r} status={status!r}>"


class SiteManager(ResourceManager[Site]):
    """Manager for site operations.

    Sites represent connections to other VergeOS systems for disaster recovery,
    replication, and remote management.

    Example:
        >>> # List all sites
        >>> sites = client.sites.list()

        >>> # Create a new site
        >>> site = client.sites.create(
        ...     name="DR-Site",
        ...     url="https://dr.example.com",
        ...     username="admin",
        ...     password="secret",
        ...     config_cloud_snapshots="send",
        ... )

        >>> # Get a site by name
        >>> site = client.sites.get(name="DR-Site")

        >>> # Enable/disable a site
        >>> site = client.sites.enable(site.key)
        >>> site = client.sites.disable(site.key)

        >>> # Delete a site
        >>> client.sites.delete(site.key)
    """

    _endpoint = "sites"

    def __init__(self, client: VergeClient) -> None:
        super().__init__(client)

    def _to_model(self, data: dict[str, Any]) -> Site:
        return Site(data, self)

    def list(
        self,
        filter: str | None = None,
        fields: builtins.list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        *,
        enabled: bool | None = None,
        status: str | None = None,
        **filter_kwargs: Any,
    ) -> builtins.list[Site]:
        """List sites.

        Args:
            filter: OData filter string.
            fields: List of fields to return.
            limit: Maximum number of results.
            offset: Skip this many results.
            enabled: Filter by enabled status.
            status: Filter by status (idle, authenticating, syncing, error, warning).
            **filter_kwargs: Additional filter arguments.

        Returns:
            List of Site objects sorted by name.

        Example:
            >>> # All sites
            >>> sites = client.sites.list()

            >>> # Enabled sites only
            >>> sites = client.sites.list(enabled=True)

            >>> # Sites with errors
            >>> sites = client.sites.list(status="error")
        """
        conditions: builtins.list[str] = []

        if enabled is not None:
            conditions.append(f"enabled eq {str(enabled).lower()}")

        if status is not None:
            conditions.append(f"status eq '{status}'")

        if filter:
            conditions.append(f"({filter})")

        if filter_kwargs:
            conditions.append(build_filter(**filter_kwargs))

        combined_filter = " and ".join(conditions) if conditions else None

        if fields is None:
            fields = _DEFAULT_SITE_FIELDS

        params: dict[str, Any] = {}
        if combined_filter:
            params["filter"] = combined_filter
        if fields:
            params["fields"] = ",".join(fields)
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset
        params["sort"] = "+name"

        response = self._client._request("GET", self._endpoint, params=params)

        if response is None:
            return []

        if not isinstance(response, list):
            return [self._to_model(response)]

        return [self._to_model(item) for item in response]

    def list_enabled(
        self,
        fields: builtins.list[str] | None = None,
    ) -> builtins.list[Site]:
        """List enabled sites.

        Args:
            fields: List of fields to return.

        Returns:
            List of enabled Site objects.
        """
        return self.list(enabled=True, fields=fields)

    def list_disabled(
        self,
        fields: builtins.list[str] | None = None,
    ) -> builtins.list[Site]:
        """List disabled sites.

        Args:
            fields: List of fields to return.

        Returns:
            List of disabled Site objects.
        """
        return self.list(enabled=False, fields=fields)

    def list_by_status(
        self,
        status: str,
        fields: builtins.list[str] | None = None,
    ) -> builtins.list[Site]:
        """List sites by status.

        Args:
            status: Status to filter by (idle, authenticating, syncing, error, warning).
            fields: List of fields to return.

        Returns:
            List of Site objects with the specified status.
        """
        return self.list(status=status, fields=fields)

    def get(
        self,
        key: int | None = None,
        *,
        name: str | None = None,
        fields: builtins.list[str] | None = None,
    ) -> Site:
        """Get a site by key or name.

        Args:
            key: Site $key (ID).
            name: Site name.
            fields: List of fields to return.

        Returns:
            Site object.

        Raises:
            NotFoundError: If site not found.
            ValueError: If neither key nor name provided.
        """
        if fields is None:
            fields = _DEFAULT_SITE_FIELDS

        if key is not None:
            params: dict[str, Any] = {}
            if fields:
                params["fields"] = ",".join(fields)

            response = self._client._request("GET", f"{self._endpoint}/{key}", params=params)
            if response is None:
                raise NotFoundError(f"Site {key} not found")
            if not isinstance(response, dict):
                raise NotFoundError(f"Site {key} returned invalid response")

            return self._to_model(response)

        if name is not None:
            escaped_name = name.replace("'", "''")
            results = self.list(filter=f"name eq '{escaped_name}'", fields=fields)
            if not results:
                raise NotFoundError(f"Site '{name}' not found")
            return results[0]

        raise ValueError("Either key or name must be provided")

    def create(  # type: ignore[override]
        self,
        name: str,
        url: str,
        username: str,
        password: str,
        *,
        description: str | None = None,
        allow_insecure: bool = False,
        config_cloud_snapshots: str = "disabled",
        config_statistics: str = "disabled",
        config_management: str = "disabled",
        config_repair_server: str = "disabled",
        auto_create_syncs: bool = True,
        domain: str | None = None,
        city: str | None = None,
        country: str | None = None,
        timezone: str | None = None,
        request_url: str | None = None,
    ) -> Site:
        """Create a new site connection.

        Args:
            name: Site name.
            url: URL of the remote VergeOS system.
            username: Username for authentication.
            password: Password for authentication.
            description: Optional site description.
            allow_insecure: Allow insecure SSL connections (for self-signed certs).
            config_cloud_snapshots: Cloud snapshot config (disabled, send, receive, both).
            config_statistics: Statistics config (disabled, send, receive, both).
            config_management: Management config (disabled, manage, managed, both).
            config_repair_server: Repair server config (disabled, send, receive, both).
            auto_create_syncs: Automatically create sync configurations.
            domain: Domain name for the site.
            city: City where the site is located.
            country: Country code where the site is located.
            timezone: Timezone for the site.
            request_url: URL the remote system uses to connect back.

        Returns:
            Created Site object.

        Raises:
            ValidationError: If invalid parameters.
            APIError: If creation fails.

        Example:
            >>> site = client.sites.create(
            ...     name="DR-Site",
            ...     url="https://dr.example.com",
            ...     username="admin",
            ...     password="secret",
            ...     config_cloud_snapshots="send",
            ...     allow_insecure=True,
            ... )
        """
        # Validate URL format
        if not url.startswith(("http://", "https://")):
            raise ValidationError("URL must start with http:// or https://")

        # Validate config values
        valid_sync_configs = {"disabled", "send", "receive", "both"}
        valid_management_configs = {"disabled", "manage", "managed", "both"}

        if config_cloud_snapshots not in valid_sync_configs:
            raise ValidationError(f"config_cloud_snapshots must be one of: {valid_sync_configs}")
        if config_statistics not in valid_sync_configs:
            raise ValidationError(f"config_statistics must be one of: {valid_sync_configs}")
        if config_management not in valid_management_configs:
            raise ValidationError(f"config_management must be one of: {valid_management_configs}")
        if config_repair_server not in valid_sync_configs:
            raise ValidationError(f"config_repair_server must be one of: {valid_sync_configs}")

        # Build request body
        body: dict[str, Any] = {
            "name": name,
            "url": url,
            "auth_user": username,
            "auth_password": password,
            "enabled": True,
            "allow_insecure": allow_insecure,
            "config_cloud_snapshots": config_cloud_snapshots,
            "config_statistics": config_statistics,
            "config_management": config_management,
            "config_repair_server": config_repair_server,
            "automatically_create_syncs": auto_create_syncs,
        }

        if description:
            body["description"] = description
        if domain:
            body["domain"] = domain
        if city:
            body["city"] = city
        if country:
            body["country"] = country
        if timezone:
            body["timezone"] = timezone
        if request_url:
            body["request_url"] = request_url

        response = self._client._request("POST", self._endpoint, json_data=body)
        if response is None:
            raise ValueError("No response from create operation")
        if not isinstance(response, dict):
            raise ValueError("Create operation returned invalid response")

        site_key = response.get("$key")
        if site_key:
            return self.get(int(site_key))

        return self._to_model(response)

    def update(  # type: ignore[override]
        self,
        key: int,
        *,
        name: str | None = None,
        description: str | None = None,
        enabled: bool | None = None,
        config_cloud_snapshots: str | None = None,
        config_statistics: str | None = None,
        config_management: str | None = None,
        config_repair_server: str | None = None,
        domain: str | None = None,
        city: str | None = None,
        country: str | None = None,
        timezone: str | None = None,
        statistics_interval: int | None = None,
        statistics_retention: int | None = None,
    ) -> Site:
        """Update a site's settings.

        Args:
            key: Site $key (ID).
            name: New site name.
            description: New site description.
            enabled: Enable or disable the site.
            config_cloud_snapshots: Cloud snapshot config (disabled, send, receive, both).
            config_statistics: Statistics config (disabled, send, receive, both).
            config_management: Management config (disabled, manage, managed, both).
            config_repair_server: Repair server config (disabled, send, receive, both).
            domain: Domain name for the site.
            city: City where the site is located.
            country: Country code where the site is located.
            timezone: Timezone for the site.
            statistics_interval: Statistics sync interval in seconds.
            statistics_retention: Statistics retention period in seconds.

        Returns:
            Updated Site object.
        """
        body: dict[str, Any] = {}

        if name is not None:
            body["name"] = name
        if description is not None:
            body["description"] = description
        if enabled is not None:
            body["enabled"] = enabled
        if config_cloud_snapshots is not None:
            body["config_cloud_snapshots"] = config_cloud_snapshots
        if config_statistics is not None:
            body["config_statistics"] = config_statistics
        if config_management is not None:
            body["config_management"] = config_management
        if config_repair_server is not None:
            body["config_repair_server"] = config_repair_server
        if domain is not None:
            body["domain"] = domain
        if city is not None:
            body["city"] = city
        if country is not None:
            body["country"] = country
        if timezone is not None:
            body["timezone"] = timezone
        if statistics_interval is not None:
            body["statistics_interval"] = statistics_interval
        if statistics_retention is not None:
            body["statistics_retention"] = statistics_retention

        if not body:
            return self.get(key)

        self._client._request("PUT", f"{self._endpoint}/{key}", json_data=body)
        return self.get(key)

    def delete(self, key: int) -> None:
        """Delete a site.

        This will also remove all associated sync configurations.

        Args:
            key: Site $key (ID).

        Raises:
            NotFoundError: If site not found.
        """
        self._client._request("DELETE", f"{self._endpoint}/{key}")

    def enable(self, key: int) -> Site:
        """Enable a site.

        Args:
            key: Site $key (ID).

        Returns:
            Updated Site object.
        """
        return self.update(key, enabled=True)

    def disable(self, key: int) -> Site:
        """Disable a site.

        Args:
            key: Site $key (ID).

        Returns:
            Updated Site object.
        """
        return self.update(key, enabled=False)

    def reauthenticate(self, key: int, username: str, password: str) -> Site:
        """Reauthenticate with a remote site.

        Use this to update credentials or resolve authentication issues.

        Args:
            key: Site $key (ID).
            username: Username for authentication.
            password: Password for authentication.

        Returns:
            Updated Site object.
        """
        body: dict[str, Any] = {
            "site": key,
            "action": "reauthenticate",
            "params": {
                "auth_user": username,
                "auth_password": password,
            },
        }

        self._client._request("POST", "site_actions", json_data=body)
        return self.get(key)

    def refresh_site(self, key: int) -> Site:
        """Refresh site data from the remote system.

        Args:
            key: Site $key (ID).

        Returns:
            Updated Site object.
        """
        body: dict[str, Any] = {
            "site": key,
            "action": "refresh",
        }

        self._client._request("POST", "site_actions", json_data=body)
        return self.get(key)

    def refresh_settings(self, key: int) -> Site:
        """Refresh site settings from the remote system.

        Args:
            key: Site $key (ID).

        Returns:
            Updated Site object.
        """
        body: dict[str, Any] = {
            "site": key,
            "action": "refresh_settings",
        }

        self._client._request("POST", "site_actions", json_data=body)
        return self.get(key)
