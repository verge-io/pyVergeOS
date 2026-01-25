"""DNS Zone and Record resource managers."""

from __future__ import annotations

import builtins
from typing import TYPE_CHECKING, Any, Literal

from pyvergeos.exceptions import NotFoundError
from pyvergeos.resources.base import ResourceManager, ResourceObject

if TYPE_CHECKING:
    from pyvergeos.client import VergeClient
    from pyvergeos.resources.networks import Network

# Default fields for DNS zone data
DNS_ZONE_DEFAULT_FIELDS = [
    "$key",
    "view",
    "domain",
    "type",
    "nameserver",
    "email",
    "default_ttl",
    "serial_number",
]

# Default fields for DNS record data
DNS_RECORD_DEFAULT_FIELDS = [
    "$key",
    "zone",
    "host",
    "type",
    "value",
    "ttl",
    "mx_preference",
    "weight",
    "port",
    "description",
]

# Type mappings for zone types
ZONE_TYPE_DISPLAY = {
    "master": "Primary",
    "slave": "Secondary",
    "redirect": "Redirect",
    "forward": "Forward",
    "static-stub": "Static Stub",
    "stub": "Stub",
}

# Type alias for record types
RecordType = Literal["A", "AAAA", "CNAME", "MX", "NS", "PTR", "SRV", "TXT", "CAA"]

# Type alias for zone types
ZoneType = Literal["master", "slave", "redirect", "forward", "static-stub", "stub"]


class DNSRecord(ResourceObject):
    """DNS Record resource object."""

    @property
    def zone_key(self) -> int:
        """Get the zone key this record belongs to."""
        zone = self.get("zone")
        if zone is None:
            raise ValueError("Record has no zone key")
        return int(zone)

    @property
    def host(self) -> str:
        """Get the hostname of this record."""
        return self.get("host") or ""

    @property
    def record_type(self) -> str:
        """Get the record type (A, AAAA, CNAME, MX, etc.)."""
        return self.get("type") or "A"

    @property
    def value(self) -> str:
        """Get the record value (IP address, hostname, or text)."""
        return self.get("value") or ""

    @property
    def ttl(self) -> str | None:
        """Get the TTL for this record."""
        return self.get("ttl")

    @property
    def mx_preference(self) -> int:
        """Get the MX preference (for MX records)."""
        return self.get("mx_preference") or 0

    @property
    def weight(self) -> int:
        """Get the weight (for SRV records)."""
        return self.get("weight") or 0

    @property
    def port(self) -> int:
        """Get the port (for SRV records)."""
        return self.get("port") or 0

    @property
    def description(self) -> str | None:
        """Get the record description."""
        return self.get("description")


class DNSRecordManager(ResourceManager[DNSRecord]):
    """Manager for DNS Record operations.

    This manager is accessed through a DNSZone object's records property.

    Examples:
        List all records in a zone::

            records = zone.records.list()

        Get an A record by host::

            record = zone.records.get(host="www")

        Create an A record::

            record = zone.records.create(
                host="www",
                record_type="A",
                value="10.0.0.100"
            )

        Create an MX record::

            record = zone.records.create(
                host="",  # root domain
                record_type="MX",
                value="mail.example.com",
                mx_preference=10
            )

        Delete a record::

            zone.records.delete(record.key)
    """

    _endpoint = "vnet_dns_zone_records"
    _default_fields = DNS_RECORD_DEFAULT_FIELDS

    def __init__(self, client: VergeClient, zone: DNSZone) -> None:
        super().__init__(client)
        self._zone = zone

    @property
    def zone_key(self) -> int:
        """Get the zone key for this manager."""
        return self._zone.key

    def _to_model(self, data: dict[str, Any]) -> DNSRecord:
        return DNSRecord(data, self)

    def list(  # type: ignore[override]
        self,
        filter: str | None = None,
        fields: builtins.list[str] | None = None,
        host: str | None = None,
        record_type: RecordType | None = None,
        **kwargs: Any,
    ) -> builtins.list[DNSRecord]:
        """List DNS records in this zone.

        Args:
            filter: Additional OData filter string.
            fields: List of fields to return.
            host: Filter by exact hostname.
            record_type: Filter by record type (A, CNAME, MX, etc.).
            **kwargs: Additional filter arguments.

        Returns:
            List of DNSRecord objects sorted by order.
        """
        if fields is None:
            fields = self._default_fields.copy()

        # Build filter for this zone
        filters: builtins.list[str] = [
            f"zone eq {self.zone_key}",
        ]

        if host is not None:
            escaped_host = host.replace("'", "''")
            filters.append(f"host eq '{escaped_host}'")

        if record_type:
            filters.append(f"type eq '{record_type}'")

        if filter:
            filters.append(f"({filter})")

        combined_filter = " and ".join(filters)

        params: dict[str, Any] = {
            "filter": combined_filter,
            "fields": ",".join(fields),
            "sort": "+orderid",
        }

        response = self._client._request("GET", self._endpoint, params=params)

        if response is None:
            return []

        if not isinstance(response, list):
            return [self._to_model(response)]

        return [self._to_model(item) for item in response]

    def get(  # type: ignore[override]
        self,
        key: int | None = None,
        *,
        host: str | None = None,
        record_type: RecordType | None = None,
        fields: builtins.list[str] | None = None,
    ) -> DNSRecord:
        """Get a DNS record by key, host, or type.

        Args:
            key: Record $key (ID).
            host: Hostname of the record.
            record_type: Record type to filter by.
            fields: List of fields to return.

        Returns:
            DNSRecord object.

        Raises:
            NotFoundError: If record not found.
            ValueError: If no identifier provided.
        """
        if fields is None:
            fields = self._default_fields.copy()

        if key is not None:
            params: dict[str, Any] = {"fields": ",".join(fields)}
            response = self._client._request("GET", f"{self._endpoint}/{key}", params=params)
            if response is None:
                raise NotFoundError(f"DNS record {key} not found")
            if not isinstance(response, dict):
                raise NotFoundError(f"DNS record {key} returned invalid response")
            return self._to_model(response)

        if host is not None:
            records = self.list(host=host, record_type=record_type, fields=fields)
            if not records:
                raise NotFoundError(f"DNS record with host '{host}' not found in this zone")
            return records[0]

        if record_type is not None:
            records = self.list(record_type=record_type, fields=fields)
            if not records:
                raise NotFoundError(f"DNS record with type '{record_type}' not found in this zone")
            return records[0]

        raise ValueError("Either key, host, or record_type must be provided")

    def create(  # type: ignore[override]
        self,
        record_type: RecordType,
        value: str,
        host: str = "",
        ttl: str | None = None,
        mx_preference: int = 0,
        weight: int = 0,
        port: int = 0,
        description: str | None = None,
    ) -> DNSRecord:
        """Create a new DNS record.

        Args:
            record_type: Record type (A, AAAA, CNAME, MX, NS, PTR, SRV, TXT, CAA).
            value: Record value (IP address, hostname, or text).
            host: Hostname for the record (empty string for root domain).
            ttl: Time-to-live for the record (e.g., "1h", "30m", "1d").
            mx_preference: Preference value for MX records (lower = higher priority).
            weight: Weight for SRV records.
            port: Port for SRV records.
            description: Optional description for the record.

        Returns:
            Created DNSRecord object.

        Note:
            DNS changes require DNS apply on the network to take effect.
        """
        body: dict[str, Any] = {
            "zone": self.zone_key,
            "host": host,
            "type": record_type,
            "value": value,
        }

        if ttl:
            body["ttl"] = ttl

        if mx_preference > 0:
            body["mx_preference"] = mx_preference

        if weight > 0:
            body["weight"] = weight

        if port > 0:
            body["port"] = port

        if description:
            body["description"] = description

        response = self._client._request("POST", self._endpoint, json_data=body)
        if response is None:
            raise ValueError("No response from create operation")
        if not isinstance(response, dict):
            raise ValueError("Create operation returned invalid response")

        # Get the created record key and fetch full data
        key = response.get("$key")
        if key is None:
            raise ValueError("Create response missing $key")

        return self.get(int(key))

    def delete(self, key: int) -> None:
        """Delete a DNS record.

        Args:
            key: Record $key (ID).

        Note:
            DNS changes require DNS apply on the network to take effect.
        """
        self._client._request("DELETE", f"{self._endpoint}/{key}")


class DNSZone(ResourceObject):
    """DNS Zone resource object."""

    def __init__(
        self,
        data: dict[str, Any],
        manager: DNSZoneManager,
        view_key: int | None = None,
        view_name: str | None = None,
    ) -> None:
        super().__init__(data, manager)
        self._view_key = view_key
        self._view_name = view_name

    @property
    def view_key(self) -> int:
        """Get the DNS view key this zone belongs to."""
        if self._view_key is not None:
            return self._view_key
        view = self.get("view")
        if view is None:
            raise ValueError("Zone has no view key")
        return int(view)

    @property
    def view_name(self) -> str | None:
        """Get the DNS view name this zone belongs to."""
        return self._view_name

    @property
    def domain(self) -> str:
        """Get the domain name for this zone."""
        return self.get("domain") or ""

    @property
    def zone_type(self) -> str:
        """Get the zone type (raw API value)."""
        return self.get("type") or "master"

    @property
    def zone_type_display(self) -> str:
        """Get the zone type display name."""
        return ZONE_TYPE_DISPLAY.get(self.zone_type, self.zone_type)

    @property
    def nameserver(self) -> str | None:
        """Get the primary nameserver for this zone."""
        return self.get("nameserver")

    @property
    def email(self) -> str | None:
        """Get the zone administrator email."""
        return self.get("email")

    @property
    def default_ttl(self) -> str | None:
        """Get the default TTL for records in this zone."""
        return self.get("default_ttl")

    @property
    def serial_number(self) -> int:
        """Get the zone serial number."""
        return self.get("serial_number") or 1

    @property
    def records(self) -> DNSRecordManager:
        """Access DNS records for this zone.

        Returns:
            DNSRecordManager for this zone.

        Examples:
            List all records::

                records = zone.records.list()

            Create an A record::

                record = zone.records.create(
                    host="www",
                    record_type="A",
                    value="10.0.0.100"
                )
        """
        return DNSRecordManager(self._manager._client, self)


class DNSZoneManager(ResourceManager[DNSZone]):
    """Manager for DNS Zone operations.

    This manager is accessed through a Network object's dns_zones property.

    Examples:
        List all zones for a network::

            zones = network.dns_zones.list()

        Get a zone by domain::

            zone = network.dns_zones.get(domain="example.com")

        List records in a zone::

            records = zone.records.list()

        Create a record::

            record = zone.records.create(
                host="www",
                record_type="A",
                value="10.0.0.100"
            )

    Note:
        DNS zones are typically created through the VergeOS UI.
        This manager provides read access to zones and full CRUD
        for records within zones.
    """

    _endpoint = "vnet_dns_zones"
    _views_endpoint = "vnet_dns_views"
    _default_fields = DNS_ZONE_DEFAULT_FIELDS

    def __init__(self, client: VergeClient, network: Network) -> None:
        super().__init__(client)
        self._network = network

    @property
    def network_key(self) -> int:
        """Get the network key for this manager."""
        return self._network.key

    def _to_model(
        self,
        data: dict[str, Any],
        view_key: int | None = None,
        view_name: str | None = None,
    ) -> DNSZone:
        return DNSZone(data, self, view_key=view_key, view_name=view_name)

    def _get_views(self) -> builtins.list[dict[str, Any]]:
        """Get DNS views for this network.

        Returns:
            List of DNS view dictionaries with $key and name.
        """
        params: dict[str, Any] = {
            "filter": f"vnet eq {self.network_key}",
            "fields": "$key,name",
        }

        response = self._client._request("GET", self._views_endpoint, params=params)

        if response is None:
            return []

        if not isinstance(response, list):
            return [response]

        return response

    def list(  # type: ignore[override]
        self,
        filter: str | None = None,
        fields: builtins.list[str] | None = None,
        domain: str | None = None,
        zone_type: ZoneType | None = None,
        include_records: bool = False,
        **kwargs: Any,
    ) -> builtins.list[DNSZone]:
        """List DNS zones for this network.

        Args:
            filter: Additional OData filter string.
            fields: List of fields to return.
            domain: Filter by exact domain name.
            zone_type: Filter by zone type.
            include_records: Include records in each zone (not yet implemented).
            **kwargs: Additional filter arguments.

        Returns:
            List of DNSZone objects sorted by domain.
        """
        if fields is None:
            fields = self._default_fields.copy()

        # First get all views for this network
        views = self._get_views()
        if not views:
            return []

        all_zones: builtins.list[DNSZone] = []

        for view in views:
            view_key = view.get("$key")
            view_name = view.get("name")

            if view_key is None:
                continue

            # Build filter for zones in this view
            filters: builtins.list[str] = [f"view eq {view_key}"]

            if domain:
                escaped_domain = domain.replace("'", "''")
                filters.append(f"domain eq '{escaped_domain}'")

            if zone_type:
                filters.append(f"type eq '{zone_type}'")

            if filter:
                filters.append(f"({filter})")

            combined_filter = " and ".join(filters)

            params: dict[str, Any] = {
                "filter": combined_filter,
                "fields": ",".join(fields),
                "sort": "+domain",
            }

            response = self._client._request("GET", self._endpoint, params=params)

            if response is None:
                continue

            if not isinstance(response, list):
                all_zones.append(self._to_model(response, view_key=view_key, view_name=view_name))
            else:
                for item in response:
                    all_zones.append(self._to_model(item, view_key=view_key, view_name=view_name))

        return all_zones

    def get(  # type: ignore[override]
        self,
        key: int | None = None,
        *,
        domain: str | None = None,
        fields: builtins.list[str] | None = None,
    ) -> DNSZone:
        """Get a DNS zone by key or domain.

        Args:
            key: Zone $key (ID).
            domain: Domain name of the zone.
            fields: List of fields to return.

        Returns:
            DNSZone object.

        Raises:
            NotFoundError: If zone not found.
            ValueError: If no identifier provided.
        """
        if fields is None:
            fields = self._default_fields.copy()

        if key is not None:
            params: dict[str, Any] = {"fields": ",".join(fields)}
            response = self._client._request("GET", f"{self._endpoint}/{key}", params=params)
            if response is None:
                raise NotFoundError(f"DNS zone {key} not found")
            if not isinstance(response, dict):
                raise NotFoundError(f"DNS zone {key} returned invalid response")
            return self._to_model(response)

        if domain is not None:
            zones = self.list(domain=domain, fields=fields)
            if not zones:
                raise NotFoundError(f"DNS zone '{domain}' not found on this network")
            return zones[0]

        raise ValueError("Either key or domain must be provided")
