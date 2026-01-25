"""NAS service management resources."""

from __future__ import annotations

import builtins
from typing import TYPE_CHECKING, Any

from pyvergeos.exceptions import NotFoundError
from pyvergeos.filters import build_filter
from pyvergeos.resources.base import ResourceManager, ResourceObject

if TYPE_CHECKING:
    from pyvergeos.client import VergeClient


class NASService(ResourceObject):
    """NAS service resource object.

    Represents a NAS service VM that manages volumes and file shares.

    Attributes:
        key: The NAS service unique identifier ($key).
        name: NAS service name.
        vm: The underlying VM key.
        max_imports: Maximum simultaneous import jobs.
        max_syncs: Maximum simultaneous sync jobs.
        disable_swap: Whether swap is disabled.
        read_ahead_kb_default: Read-ahead buffer size in KB.
        cifs: CIFS settings key.
        nfs: NFS settings key.
    """

    @property
    def is_running(self) -> bool:
        """Check if the NAS service VM is running."""
        return self.get("vm_running", False) or self.get("vm_status") == "running"

    @property
    def vm_key(self) -> int | None:
        """Get the underlying VM key."""
        vm = self.get("vm")
        return int(vm) if vm is not None else None

    @property
    def volume_count(self) -> int:
        """Get the number of volumes managed by this service."""
        count = self.get("volume_count", 0)
        return int(count) if count is not None else 0


class CIFSSettings(ResourceObject):
    """CIFS/SMB settings resource object.

    Represents CIFS/SMB configuration for a NAS service.

    Attributes:
        key: The CIFS settings unique identifier ($key).
        service: The parent NAS service key.
        workgroup: NetBIOS workgroup name.
        realm: Kerberos realm for AD.
        server_type: Server role (default, MEMBER, BDC, PDC).
        map_to_guest: How invalid users/passwords are handled.
        server_min_protocol: Minimum SMB protocol version.
        extended_acl_support: Whether extended ACLs are enabled.
        ad_status: Active Directory join status.
    """

    pass


class NFSSettings(ResourceObject):
    """NFS settings resource object.

    Represents NFS configuration for a NAS service.

    Attributes:
        key: The NFS settings unique identifier ($key).
        service: The parent NAS service key.
        enable_nfsv4: Whether NFSv4 is enabled.
        allowed_hosts: List of allowed hosts/networks.
        allow_all: Whether all hosts are allowed.
        squash: User/group squashing mode.
        data_access: Read-only or read-write.
        anonuid: Anonymous user ID.
        anongid: Anonymous group ID.
    """

    pass


class NASServiceManager(ResourceManager[NASService]):
    """Manager for NAS service operations.

    NAS services are specialized VMs that manage NAS volumes and file shares
    (CIFS/SMB and NFS).

    Example:
        >>> # List all NAS services
        >>> for service in client.nas_services.list():
        ...     print(f"{service.name}: {service.volume_count} volumes")

        >>> # Get a specific NAS service
        >>> nas = client.nas_services.get(name="NAS01")

        >>> # Get CIFS settings
        >>> cifs = client.nas_services.get_cifs_settings(nas.key)
        >>> print(f"Workgroup: {cifs.workgroup}")

        >>> # Update NFS settings
        >>> client.nas_services.set_nfs_settings(nas.key, enable_nfsv4=True)
    """

    _endpoint = "vm_services"

    # Default fields for list operations
    _default_fields = [
        "$key",
        "name",
        "vm",
        "vm#name as vm_name",
        "vm#$display as vm_display",
        "vm#description as vm_description",
        "vm#machine#status#status as vm_status",
        "vm#machine#status#running as vm_running",
        "vm#machine#cores as vm_cores",
        "vm#machine#ram as vm_ram",
        "vm#created as created",
        "vm#modified as modified",
        "max_imports",
        "max_syncs",
        "disable_swap",
        "read_ahead_kb_default",
        "cifs",
        "nfs",
        "count(volumes) as volume_count",
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
    ) -> builtins.list[NASService]:
        """List NAS services with optional filtering.

        Args:
            filter: OData filter string.
            fields: List of fields to return (uses defaults if not specified).
            limit: Maximum number of results.
            offset: Skip this many results.
            status: Filter by VM status (running, stopped, etc.).
            **filter_kwargs: Shorthand filter arguments (name, etc.).

        Returns:
            List of NASService objects.

        Example:
            >>> # List all NAS services
            >>> services = client.nas_services.list()

            >>> # List running services only
            >>> running = client.nas_services.list(status="running")

            >>> # Filter by name
            >>> nas01 = client.nas_services.list(name="NAS01")
        """
        params: dict[str, Any] = {}

        # Build filter
        filters: builtins.list[str] = []
        if filter:
            filters.append(filter)
        if filter_kwargs:
            filters.append(build_filter(**filter_kwargs))

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

        results = [self._to_model(item) for item in response if item]

        # Post-filter by status if specified
        if status:
            status_lower = status.lower()
            results = [s for s in results if s.get("vm_status") == status_lower]

        return results

    def list_running(self) -> builtins.list[NASService]:
        """List all running NAS services.

        Returns:
            List of running NASService objects.
        """
        return self.list(status="running")

    def list_stopped(self) -> builtins.list[NASService]:
        """List all stopped NAS services.

        Returns:
            List of stopped NASService objects.
        """
        return self.list(status="stopped")

    def get(
        self,
        key: int | None = None,
        *,
        name: str | None = None,
        fields: builtins.list[str] | None = None,
    ) -> NASService:
        """Get a single NAS service by key or name.

        Args:
            key: NAS service $key (ID).
            name: NAS service name.
            fields: List of fields to return.

        Returns:
            NASService object.

        Raises:
            NotFoundError: If NAS service not found.
            ValueError: If neither key nor name provided.

        Example:
            >>> # Get by key
            >>> service = client.nas_services.get(1)

            >>> # Get by name
            >>> service = client.nas_services.get(name="NAS01")
        """
        if key is not None:
            # Fetch by key with default fields
            params: dict[str, Any] = {}
            if fields:
                params["fields"] = ",".join(fields)
            else:
                params["fields"] = ",".join(self._default_fields)

            response = self._client._request(
                "GET", f"{self._endpoint}/{key}", params=params
            )
            if response is None:
                raise NotFoundError(f"NAS service with key {key} not found")
            if not isinstance(response, dict):
                raise NotFoundError(f"NAS service with key {key} returned invalid response")
            return self._to_model(response)

        if name is not None:
            # Search by name
            escaped_name = name.replace("'", "''")
            results = self.list(filter=f"name eq '{escaped_name}'", fields=fields, limit=1)
            if not results:
                raise NotFoundError(f"NAS service with name '{name}' not found")
            return results[0]

        raise ValueError("Either key or name must be provided")

    def create(  # type: ignore[override]
        self,
        name: str,
        *,
        hostname: str | None = None,
        network: int | str | None = None,
        cores: int = 4,
        memory_gb: int = 8,
        auto_update: bool = False,
    ) -> NASService:
        """Create a new NAS service by deploying the Services recipe.

        Args:
            name: Name for the new NAS service.
            hostname: Hostname for the NAS VM (defaults to name with invalid chars removed).
            network: Network to connect to (key or name). Defaults to 'Internal'.
            cores: Number of CPU cores (default: 4).
            memory_gb: Amount of RAM in GB (default: 8).
            auto_update: Enable auto-update on power off.

        Returns:
            Created NASService object.

        Raises:
            ValueError: If Services recipe not found or NAS service already exists.

        Example:
            >>> # Create with defaults
            >>> nas = client.nas_services.create("NAS01")

            >>> # Create with custom settings
            >>> nas = client.nas_services.create(
            ...     "FileServer",
            ...     network="Internal",
            ...     cores=8,
            ...     memory_gb=16
            ... )
        """
        # Find the Services recipe
        recipe_response = self._client._request(
            "GET",
            "vm_recipes",
            params={"filter": "name eq 'Services'", "fields": "id,name,description,version"},
        )

        if not recipe_response:
            raise ValueError("Services recipe not found. Ensure the Services recipe is available.")

        if isinstance(recipe_response, list):
            recipe = recipe_response[0] if recipe_response else None
        else:
            recipe = recipe_response

        if not recipe:
            raise ValueError("Services recipe not found")

        recipe_id = recipe.get("id")

        # Check if NAS service with this name already exists
        try:
            existing = self.get(name=name)
            if existing:
                raise ValueError(f"A NAS service with name '{name}' already exists")
        except NotFoundError:
            pass  # Good, doesn't exist

        # Determine hostname
        if not hostname:
            import re
            hostname = re.sub(r"[^a-zA-Z0-9\-]", "", name)
            hostname = hostname.strip("-")
            if len(hostname) > 63:
                hostname = hostname[:63]
            if not hostname:
                hostname = "nas"

        # Resolve network
        network_key: int | None = None
        if network is not None:
            if isinstance(network, int):
                network_key = network
            elif isinstance(network, str):
                # Look up network by name
                net_response = self._client._request(
                    "GET",
                    "vnets",
                    params={"filter": f"name eq '{network}'", "fields": "$key,name", "limit": "1"},
                )
                if net_response:
                    if isinstance(net_response, list):
                        net_response = net_response[0] if net_response else None
                    if net_response:
                        network_key = net_response.get("$key")
                if network_key is None:
                    raise ValueError(f"Network '{network}' not found")
        else:
            # Try to find 'Internal' network
            net_response = self._client._request(
                "GET",
                "vnets",
                params={"filter": "name eq 'Internal'", "fields": "$key,name", "limit": "1"},
            )
            if net_response:
                if isinstance(net_response, list):
                    net_response = net_response[0] if net_response else None
                if net_response:
                    network_key = net_response.get("$key")

        if network_key is None:
            raise ValueError("No network specified and no 'Internal' network found")

        # Build request body for vm_recipe_instances
        body: dict[str, Any] = {
            "recipe": recipe_id,
            "name": name,
            "answers": {
                "HOSTNAME": hostname,
                "YB_HOSTNAME": hostname,
                "YB_CPU_CORES": cores,
                "YB_RAM": memory_gb * 1024,  # Convert GB to MB
                "YB_NIC_1": str(network_key),
                "YB_NIC_1_IP_TYPE": "dhcp",
                "YB_TIMEZONE": "America/New_York",
                "YB_NTP": "time.nist.gov 0.pool.ntp.org 1.pool.ntp.org",
                "YB_DOMAINNAME": "",
            },
        }

        if auto_update:
            body["auto_update"] = True

        # Deploy the recipe
        self._client._request("POST", "vm_recipe_instances", json_data=body)

        # Wait for the service to be created
        import time
        max_attempts = 15
        for _ in range(max_attempts):
            time.sleep(2)
            try:
                service = self.get(name=name)
                if service:
                    return service
            except NotFoundError:
                pass

        raise ValueError(
            f"NAS service deployment initiated but service '{name}' not found after waiting. "
            "It may still be creating."
        )

    def update(  # type: ignore[override]
        self,
        key: int,
        *,
        description: str | None = None,
        cpu_cores: int | None = None,
        memory_gb: int | None = None,
        max_imports: int | None = None,
        max_syncs: int | None = None,
        disable_swap: bool | None = None,
        read_ahead_kb: int | None = None,
    ) -> NASService:
        """Update NAS service settings.

        Updates both the underlying VM settings (CPU, RAM, description) and
        NAS-specific settings (max_imports, max_syncs, etc.).

        Args:
            key: NAS service $key (ID).
            description: New description.
            cpu_cores: Number of CPU cores (requires restart).
            memory_gb: Amount of RAM in GB (requires restart).
            max_imports: Maximum simultaneous import jobs (1-10).
            max_syncs: Maximum simultaneous sync jobs (1-10).
            disable_swap: Disable swap on the NAS service.
            read_ahead_kb: Read-ahead buffer size (0=auto, 64, 128, 256, 512, 1024, 2048, 4096).

        Returns:
            Updated NASService object.

        Example:
            >>> # Update NAS settings
            >>> client.nas_services.update(1, max_imports=5, max_syncs=3)

            >>> # Update VM resources (requires restart)
            >>> client.nas_services.update(1, cpu_cores=8, memory_gb=16)
        """
        # Get current service info
        service = self.get(key)

        # Build VM update body
        vm_body: dict[str, Any] = {}
        if description is not None:
            vm_body["description"] = description
        if cpu_cores is not None:
            vm_body["cpu_cores"] = cpu_cores
        if memory_gb is not None:
            vm_body["ram"] = memory_gb * 1024  # Convert GB to MB

        # Build service update body
        service_body: dict[str, Any] = {}
        if max_imports is not None:
            service_body["max_imports"] = max_imports
        if max_syncs is not None:
            service_body["max_syncs"] = max_syncs
        if disable_swap is not None:
            service_body["disable_swap"] = disable_swap
        if read_ahead_kb is not None:
            service_body["read_ahead_kb_default"] = read_ahead_kb

        # Update VM settings if any
        if vm_body and service.vm_key:
            self._client._request("PUT", f"vms/{service.vm_key}", json_data=vm_body)

        # Update service settings if any
        if service_body:
            self._client._request("PUT", f"{self._endpoint}/{key}", json_data=service_body)

        return self.get(key)

    def delete(self, key: int, *, force: bool = False) -> None:
        """Delete a NAS service.

        The NAS service VM must be stopped before deletion. If the service
        has volumes, they must be removed first unless force=True.

        Args:
            key: NAS service $key (ID).
            force: Remove even if service has volumes (will delete all data).

        Raises:
            ValueError: If service is running or has volumes without force.

        Example:
            >>> # Delete a stopped NAS service
            >>> client.nas_services.delete(1)

            >>> # Force delete (removes all volumes and data)
            >>> client.nas_services.delete(1, force=True)
        """
        service = self.get(key)

        if service.is_running:
            raise ValueError(
                f"Cannot delete NAS service '{service.name}': Service is running. "
                "Power off the service first."
            )

        if service.volume_count > 0 and not force:
            raise ValueError(
                f"Cannot delete NAS service '{service.name}': "
                f"Service has {service.volume_count} volume(s). "
                "Remove volumes first or use force=True."
            )

        # Delete the underlying VM (cascades to recipe instance and vm_services)
        if service.vm_key:
            self._client._request("DELETE", f"vms/{service.vm_key}")
        else:
            # Fallback: delete service directly
            self._client._request("DELETE", f"{self._endpoint}/{key}")

    def power_on(self, key: int) -> dict[str, Any] | None:
        """Power on a NAS service.

        Args:
            key: NAS service $key (ID).

        Returns:
            Task information dict or None.

        Example:
            >>> client.nas_services.power_on(1)
        """
        service = self.get(key)
        if service.vm_key:
            result = self._client._request(
                "PUT", f"vms/{service.vm_key}?action=poweron", json_data={}
            )
            if isinstance(result, dict):
                return result
        return None

    def power_off(self, key: int, *, force: bool = False) -> dict[str, Any] | None:
        """Power off a NAS service.

        Args:
            key: NAS service $key (ID).
            force: Force power off (like pulling the plug).

        Returns:
            Task information dict or None.

        Example:
            >>> # Graceful shutdown
            >>> client.nas_services.power_off(1)

            >>> # Force power off
            >>> client.nas_services.power_off(1, force=True)
        """
        service = self.get(key)
        if service.vm_key:
            action = "killpower" if force else "poweroff"
            result = self._client._request(
                "PUT", f"vms/{service.vm_key}?action={action}", json_data={}
            )
            if isinstance(result, dict):
                return result
        return None

    def restart(self, key: int) -> dict[str, Any] | None:
        """Restart a NAS service.

        Args:
            key: NAS service $key (ID).

        Returns:
            Task information dict or None.

        Example:
            >>> client.nas_services.restart(1)
        """
        service = self.get(key)
        if service.vm_key:
            result = self._client._request(
                "PUT", f"vms/{service.vm_key}?action=reset", json_data={}
            )
            if isinstance(result, dict):
                return result
        return None

    # -------------------------------------------------------------------------
    # CIFS Settings
    # -------------------------------------------------------------------------

    def get_cifs_settings(self, key: int) -> CIFSSettings:
        """Get CIFS/SMB settings for a NAS service.

        Args:
            key: NAS service $key (ID).

        Returns:
            CIFSSettings object.

        Raises:
            NotFoundError: If CIFS settings not found.

        Example:
            >>> cifs = client.nas_services.get_cifs_settings(1)
            >>> print(f"Workgroup: {cifs.workgroup}")
            >>> print(f"Min Protocol: {cifs.server_min_protocol}")
        """
        fields = [
            "$key",
            "service",
            "service#$display as service_name",
            "map_to_guest",
            "realm",
            "workgroup",
            "server_type",
            "extended_acl_support",
            "server_min_protocol",
            "ad_status",
            "ad_status_info",
            "ad_upn",
            "ad_ou",
            "ad_osname",
            "ad_osver",
            "advanced",
        ]

        response = self._client._request(
            "GET",
            "vm_service_cifs",
            params={"filter": f"service eq {key}", "fields": ",".join(fields)},
        )

        if not response:
            raise NotFoundError(f"CIFS settings not found for NAS service {key}")

        if isinstance(response, list):
            response = response[0] if response else None

        if not response:
            raise NotFoundError(f"CIFS settings not found for NAS service {key}")

        return CIFSSettings(response, self)

    def set_cifs_settings(
        self,
        key: int,
        *,
        workgroup: str | None = None,
        min_protocol: str | None = None,
        guest_mapping: str | None = None,
        extended_acl_support: bool | None = None,
    ) -> CIFSSettings:
        """Update CIFS/SMB settings for a NAS service.

        Args:
            key: NAS service $key (ID).
            workgroup: NetBIOS workgroup name.
            min_protocol: Minimum SMB protocol version.
                Valid values: none, SMB2, SMB2_02, SMB2_10, SMB3, SMB3_00, SMB3_02, SMB3_11
            guest_mapping: How to handle invalid users/passwords.
                Valid values: never, bad user, bad password, bad uid
            extended_acl_support: Enable extended ACL support.

        Returns:
            Updated CIFSSettings object.

        Example:
            >>> # Set minimum protocol to SMB3
            >>> client.nas_services.set_cifs_settings(1, min_protocol="SMB3")

            >>> # Update workgroup
            >>> client.nas_services.set_cifs_settings(1, workgroup="MYWORKGROUP")
        """
        # Get current settings to find the CIFS settings key
        current = self.get_cifs_settings(key)
        cifs_key = current.key

        body: dict[str, Any] = {}

        if workgroup is not None:
            body["workgroup"] = workgroup.lower()

        if min_protocol is not None:
            # Map user-friendly values to API values
            protocol_map = {
                "none": "none",
                "smb2": "SMB2",
                "smb2_02": "SMB2_02",
                "smb2_10": "SMB2_10",
                "smb3": "SMB3",
                "smb3_00": "SMB3_00",
                "smb3_02": "SMB3_02",
                "smb3_11": "SMB3_11",
            }
            body["server_min_protocol"] = protocol_map.get(min_protocol.lower(), min_protocol)

        if guest_mapping is not None:
            # Map user-friendly values to API values
            guest_map = {
                "never": "never",
                "baduser": "bad user",
                "bad_user": "bad user",
                "badpassword": "bad password",
                "bad_password": "bad password",
                "baduid": "bad uid",
                "bad_uid": "bad uid",
            }
            body["map_to_guest"] = guest_map.get(guest_mapping.lower(), guest_mapping)

        if extended_acl_support is not None:
            body["extended_acl_support"] = extended_acl_support

        if not body:
            return current

        self._client._request("PUT", f"vm_service_cifs/{cifs_key}", json_data=body)
        return self.get_cifs_settings(key)

    # -------------------------------------------------------------------------
    # NFS Settings
    # -------------------------------------------------------------------------

    def get_nfs_settings(self, key: int) -> NFSSettings:
        """Get NFS settings for a NAS service.

        Args:
            key: NAS service $key (ID).

        Returns:
            NFSSettings object.

        Raises:
            NotFoundError: If NFS settings not found.

        Example:
            >>> nfs = client.nas_services.get_nfs_settings(1)
            >>> print(f"NFSv4 Enabled: {nfs.enable_nfsv4}")
            >>> print(f"Allowed Hosts: {nfs.allowed_hosts}")
        """
        fields = [
            "$key",
            "service",
            "service#$display as service_name",
            "enable_nfsv4",
            "allowed_hosts",
            "fsid",
            "anonuid",
            "anongid",
            "no_acl",
            "insecure",
            "async",
            "squash",
            "data_access",
            "allow_all",
        ]

        response = self._client._request(
            "GET",
            "vm_service_nfs",
            params={"filter": f"service eq {key}", "fields": ",".join(fields)},
        )

        if not response:
            raise NotFoundError(f"NFS settings not found for NAS service {key}")

        if isinstance(response, list):
            response = response[0] if response else None

        if not response:
            raise NotFoundError(f"NFS settings not found for NAS service {key}")

        return NFSSettings(response, self)

    def set_nfs_settings(
        self,
        key: int,
        *,
        enable_nfsv4: bool | None = None,
        allowed_hosts: str | None = None,
        allow_all: bool | None = None,
        squash: str | None = None,
        data_access: str | None = None,
        anon_uid: int | None = None,
        anon_gid: int | None = None,
        no_acl: bool | None = None,
        insecure: bool | None = None,
        async_mode: bool | None = None,
    ) -> NFSSettings:
        """Update NFS settings for a NAS service.

        Args:
            key: NAS service $key (ID).
            enable_nfsv4: Enable NFSv4 protocol support.
            allowed_hosts: Comma-separated list of allowed hosts/networks.
            allow_all: Allow all hosts to access NFS exports.
            squash: User/group squashing mode.
                Valid values: root_squash, all_squash, no_root_squash
            data_access: Read-only or read-write access.
                Valid values: ro, rw
            anon_uid: Anonymous user ID for squashed users.
            anon_gid: Anonymous group ID for squashed users.
            no_acl: Disable ACL support for NFS exports.
            insecure: Allow connections from non-privileged ports.
            async_mode: Enable async mode for better performance.

        Returns:
            Updated NFSSettings object.

        Example:
            >>> # Enable NFSv4
            >>> client.nas_services.set_nfs_settings(1, enable_nfsv4=True)

            >>> # Set allowed hosts
            >>> client.nas_services.set_nfs_settings(
            ...     1, allowed_hosts="192.168.1.0/24,10.0.0.0/8"
            ... )
        """
        # Get current settings to find the NFS settings key
        current = self.get_nfs_settings(key)
        nfs_key = current.key

        body: dict[str, Any] = {}

        if enable_nfsv4 is not None:
            body["enable_nfsv4"] = enable_nfsv4

        if allowed_hosts is not None:
            body["allowed_hosts"] = allowed_hosts

        if allow_all is not None:
            body["allow_all"] = allow_all

        if squash is not None:
            # Map user-friendly values to API values
            squash_map = {
                "root_squash": "root_squash",
                "rootsquash": "root_squash",
                "all_squash": "all_squash",
                "allsquash": "all_squash",
                "no_root_squash": "no_root_squash",
                "norootsquash": "no_root_squash",
                "no_squash": "no_root_squash",
                "nosquash": "no_root_squash",
            }
            body["squash"] = squash_map.get(squash.lower(), squash)

        if data_access is not None:
            # Map user-friendly values to API values
            access_map = {
                "ro": "ro",
                "readonly": "ro",
                "read_only": "ro",
                "rw": "rw",
                "readwrite": "rw",
                "read_write": "rw",
            }
            body["data_access"] = access_map.get(data_access.lower(), data_access)

        if anon_uid is not None:
            body["anonuid"] = anon_uid

        if anon_gid is not None:
            body["anongid"] = anon_gid

        if no_acl is not None:
            body["no_acl"] = no_acl

        if insecure is not None:
            body["insecure"] = insecure

        if async_mode is not None:
            body["async"] = async_mode

        if not body:
            return current

        self._client._request("PUT", f"vm_service_nfs/{nfs_key}", json_data=body)
        return self.get_nfs_settings(key)

    def _to_model(self, data: dict[str, Any]) -> NASService:
        """Convert API response to NASService object."""
        return NASService(data, self)
