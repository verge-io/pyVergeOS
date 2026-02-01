"""Main VergeClient class for interacting with VergeOS API v4."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

import requests

from pyvergeos.connection import AuthMethod, VergeConnection, build_auth_header
from pyvergeos.constants import (
    CONTENT_TYPE_JSON,
    DEFAULT_TIMEOUT,
    HEADER_ACCEPT,
    HEADER_CONTENT_TYPE,
    HTTP_AUTH_FAILURE_CODES,
    HTTP_CONFLICT,
    HTTP_NO_CONTENT,
    HTTP_NOT_FOUND,
    HTTP_SUCCESS_CODES,
    HTTP_UNPROCESSABLE_ENTITY,
    RETRY_BACKOFF_FACTOR,
    RETRY_STATUS_CODES,
    RETRY_TOTAL,
)
from pyvergeos.exceptions import (
    APIError,
    AuthenticationError,
    ConflictError,
    NotConnectedError,
    NotFoundError,
    ValidationError,
    VergeConnectionError,
    VergeTimeoutError,
)

if TYPE_CHECKING:
    from pyvergeos.resources.alarms import AlarmManager
    from pyvergeos.resources.api_keys import APIKeyManager
    from pyvergeos.resources.billing import BillingManager
    from pyvergeos.resources.catalogs import (
        CatalogLogManager,
        CatalogManager,
        CatalogRepositoryLogManager,
        CatalogRepositoryManager,
        CatalogRepositoryStatusManager,
    )
    from pyvergeos.resources.certificates import CertificateManager
    from pyvergeos.resources.cloud_snapshots import CloudSnapshotManager
    from pyvergeos.resources.cloudinit_files import CloudInitFileManager
    from pyvergeos.resources.clusters import ClusterManager
    from pyvergeos.resources.files import FileManager
    from pyvergeos.resources.gpu import NvidiaVgpuProfileManager
    from pyvergeos.resources.groups import GroupManager
    from pyvergeos.resources.logs import LogManager
    from pyvergeos.resources.nas_cifs import NASCIFSShareManager
    from pyvergeos.resources.nas_nfs import NASNFSShareManager
    from pyvergeos.resources.nas_services import NASServiceManager
    from pyvergeos.resources.nas_users import NASUserManager
    from pyvergeos.resources.nas_volume_syncs import NASVolumeSyncManager
    from pyvergeos.resources.nas_volumes import NASVolumeManager, NASVolumeSnapshotManager
    from pyvergeos.resources.network_stats import NetworkDashboardManager
    from pyvergeos.resources.networks import NetworkManager
    from pyvergeos.resources.nodes import NodeManager
    from pyvergeos.resources.permissions import PermissionManager
    from pyvergeos.resources.recipe_common import (
        RecipeQuestionManager,
        RecipeSectionManager,
    )
    from pyvergeos.resources.resource_groups import ResourceGroupManager
    from pyvergeos.resources.shared_objects import SharedObjectManager
    from pyvergeos.resources.site_syncs import (
        SiteSyncIncomingManager,
        SiteSyncOutgoingManager,
        SiteSyncScheduleManager,
    )
    from pyvergeos.resources.sites import SiteManager
    from pyvergeos.resources.snapshot_profiles import SnapshotProfileManager
    from pyvergeos.resources.storage_tiers import StorageTierManager
    from pyvergeos.resources.system import SystemManager
    from pyvergeos.resources.tags import TagCategoryManager, TagManager
    from pyvergeos.resources.task_events import TaskEventManager
    from pyvergeos.resources.task_schedule_triggers import TaskScheduleTriggerManager
    from pyvergeos.resources.task_schedules import TaskScheduleManager
    from pyvergeos.resources.task_scripts import TaskScriptManager
    from pyvergeos.resources.tasks import TaskManager
    from pyvergeos.resources.tenant_manager import TenantManager
    from pyvergeos.resources.tenant_recipes import (
        TenantRecipeInstanceManager,
        TenantRecipeLogManager,
        TenantRecipeManager,
    )
    from pyvergeos.resources.tenant_stats import TenantDashboardManager
    from pyvergeos.resources.users import UserManager
    from pyvergeos.resources.vm_imports import VmImportLogManager, VmImportManager
    from pyvergeos.resources.vm_recipes import (
        VmRecipeInstanceManager,
        VmRecipeLogManager,
        VmRecipeManager,
    )
    from pyvergeos.resources.vms import VMManager
    from pyvergeos.resources.volume_vm_exports import (
        VolumeVmExportManager,
        VolumeVmExportStatManager,
    )
    from pyvergeos.resources.webhooks import WebhookManager

logger = logging.getLogger(__name__)


class VergeClient:
    """Main client for interacting with VergeOS API v4.

    Thread Safety:
        This client is NOT thread-safe. Each thread should use its own
        VergeClient instance, or external locking should be used.

    Example:
        >>> client = VergeClient(
        ...     host="192.168.1.100",
        ...     username="admin",
        ...     password="secret"
        ... )
        >>> vms = client.vms.list()
        >>> client.disconnect()

        # Or use as context manager
        >>> with VergeClient(host="...", ...) as client:
        ...     vms = client.vms.list()

        # Or from environment variables
        >>> client = VergeClient.from_env()
    """

    def __init__(
        self,
        host: str,
        username: str | None = None,
        password: str | None = None,
        token: str | None = None,
        verify_ssl: bool = True,
        timeout: int = DEFAULT_TIMEOUT,
        auto_connect: bool = True,
        retry_total: int = RETRY_TOTAL,
        retry_backoff_factor: float = RETRY_BACKOFF_FACTOR,
        retry_status_codes: frozenset[int] | None = None,
    ) -> None:
        """Initialize VergeClient.

        Args:
            host: VergeOS hostname or IP address.
            username: Username for basic authentication.
            password: Password for basic authentication.
            token: API token for bearer authentication.
            verify_ssl: Whether to verify SSL certificates.
            timeout: Default request timeout in seconds.
            auto_connect: Whether to connect immediately.
            retry_total: Number of retry attempts for transient failures (default: 3).
            retry_backoff_factor: Backoff factor for retry delay calculation.
                Delay = backoff_factor * (2 ** retry_count). Default: 1.
            retry_status_codes: HTTP status codes that trigger automatic retry.
                Default: 429, 500, 502, 503, 504.

        Raises:
            ValueError: If neither token nor username/password provided.
        """
        self.host = host
        self._username = username
        self._password = password
        self._token = token
        self._verify_ssl = verify_ssl
        self._timeout = timeout
        self._retry_total = retry_total
        self._retry_backoff_factor = retry_backoff_factor
        self._retry_status_codes = (
            retry_status_codes if retry_status_codes is not None else RETRY_STATUS_CODES
        )

        self._connection: VergeConnection | None = None

        # Resource managers (lazy-loaded)
        self._alarms: AlarmManager | None = None
        self._certificates: CertificateManager | None = None
        self._logs: LogManager | None = None
        self._vms: VMManager | None = None
        self._networks: NetworkManager | None = None
        self._tenants: TenantManager | None = None
        self._users: UserManager | None = None
        self._api_keys: APIKeyManager | None = None
        self._groups: GroupManager | None = None
        self._permissions: PermissionManager | None = None
        self._clusters: ClusterManager | None = None
        self._nodes: NodeManager | None = None
        self._tasks: TaskManager | None = None
        self._files: FileManager | None = None
        self._storage_tiers: StorageTierManager | None = None
        self._nas_services: NASServiceManager | None = None
        self._nas_volumes: NASVolumeManager | None = None
        self._nas_volume_snapshots: NASVolumeSnapshotManager | None = None
        self._cifs_shares: NASCIFSShareManager | None = None
        self._nfs_shares: NASNFSShareManager | None = None
        self._nas_users: NASUserManager | None = None
        self._volume_syncs: NASVolumeSyncManager | None = None
        self._shared_objects: SharedObjectManager | None = None
        self._sites: SiteManager | None = None
        self._site_syncs: SiteSyncOutgoingManager | None = None
        self._site_syncs_incoming: SiteSyncIncomingManager | None = None
        self._site_sync_schedules: SiteSyncScheduleManager | None = None
        self._snapshot_profiles: SnapshotProfileManager | None = None
        self._cloud_snapshots: CloudSnapshotManager | None = None
        self._system: SystemManager | None = None
        self._resource_groups: ResourceGroupManager | None = None
        self._webhooks: WebhookManager | None = None
        self._cloudinit_files: CloudInitFileManager | None = None
        self._tags: TagManager | None = None
        self._tag_categories: TagCategoryManager | None = None
        self._vm_imports: VmImportManager | None = None
        self._vm_import_logs: VmImportLogManager | None = None
        self._volume_vm_exports: VolumeVmExportManager | None = None
        self._volume_vm_export_stats: VolumeVmExportStatManager | None = None
        self._vm_recipes: VmRecipeManager | None = None
        self._vm_recipe_instances: VmRecipeInstanceManager | None = None
        self._vm_recipe_logs: VmRecipeLogManager | None = None
        self._tenant_recipes: TenantRecipeManager | None = None
        self._tenant_recipe_instances: TenantRecipeInstanceManager | None = None
        self._tenant_recipe_logs: TenantRecipeLogManager | None = None
        self._recipe_questions: RecipeQuestionManager | None = None
        self._recipe_sections: RecipeSectionManager | None = None
        self._task_schedules: TaskScheduleManager | None = None
        self._task_schedule_triggers: TaskScheduleTriggerManager | None = None
        self._task_events: TaskEventManager | None = None
        self._task_scripts: TaskScriptManager | None = None
        self._catalog_repositories: CatalogRepositoryManager | None = None
        self._catalogs: CatalogManager | None = None
        self._catalog_logs: CatalogLogManager | None = None
        self._catalog_repository_logs: CatalogRepositoryLogManager | None = None
        self._catalog_repository_status: CatalogRepositoryStatusManager | None = None
        self._vgpu_profiles: NvidiaVgpuProfileManager | None = None
        self._tenant_dashboard: TenantDashboardManager | None = None
        self._billing: BillingManager | None = None
        self._network_dashboard: NetworkDashboardManager | None = None

        if auto_connect:
            self.connect()

    @classmethod
    def from_env(cls) -> VergeClient:
        """Create client from environment variables.

        Environment variables:
            VERGE_HOST: VergeOS hostname or IP (required)
            VERGE_USERNAME: Username for basic auth
            VERGE_PASSWORD: Password for basic auth
            VERGE_TOKEN: API token for bearer auth
            VERGE_VERIFY_SSL: Whether to verify SSL (default: true)
            VERGE_TIMEOUT: Request timeout in seconds (default: 30)
            VERGE_RETRY_TOTAL: Number of retry attempts (default: 3)
            VERGE_RETRY_BACKOFF: Retry backoff factor (default: 1)

        Returns:
            Configured VergeClient instance.

        Raises:
            ValueError: If VERGE_HOST is not set.
        """
        import os

        host = os.environ.get("VERGE_HOST")
        if not host:
            raise ValueError("VERGE_HOST environment variable not set")

        verify_ssl_str = os.environ.get("VERGE_VERIFY_SSL", "true").lower()
        verify_ssl = verify_ssl_str in ("true", "1", "yes")

        return cls(
            host=host,
            username=os.environ.get("VERGE_USERNAME"),
            password=os.environ.get("VERGE_PASSWORD"),
            token=os.environ.get("VERGE_TOKEN"),
            verify_ssl=verify_ssl,
            timeout=int(os.environ.get("VERGE_TIMEOUT", str(DEFAULT_TIMEOUT))),
            retry_total=int(os.environ.get("VERGE_RETRY_TOTAL", str(RETRY_TOTAL))),
            retry_backoff_factor=float(
                os.environ.get("VERGE_RETRY_BACKOFF", str(RETRY_BACKOFF_FACTOR))
            ),
        )

    def connect(self) -> VergeClient:
        """Establish connection to VergeOS.

        Returns:
            Self for method chaining.

        Raises:
            ConnectionError: If connection fails.
            AuthenticationError: If authentication fails.
            ValueError: If credentials not provided.
        """
        self._connection = VergeConnection(
            host=self.host,
            username=self._username or "",
            verify_ssl=self._verify_ssl,
            retry_total=self._retry_total,
            retry_backoff_factor=self._retry_backoff_factor,
            retry_status_codes=self._retry_status_codes,
        )

        # Determine auth method and build header
        if self._token:
            auth_header = build_auth_header(AuthMethod.TOKEN, token=self._token)
            self._connection.token = self._token
        elif self._username and self._password:
            auth_header = build_auth_header(
                AuthMethod.BASIC,
                username=self._username,
                password=self._password,
            )
        else:
            raise ValueError("Either token or username/password required")

        session = self._connection._session
        if session is None:
            raise NotConnectedError("Session not initialized")

        session.headers.update(auth_header)
        session.headers.update(
            {
                HEADER_CONTENT_TYPE: CONTENT_TYPE_JSON,
                HEADER_ACCEPT: CONTENT_TYPE_JSON,
            }
        )

        # Validate connection
        self._validate_connection()

        return self

    def _validate_connection(self) -> None:
        """Validate connection by fetching system info."""
        if not self._connection:
            raise NotConnectedError("No connection object")

        try:
            # Make direct request to validate connection (can't use _request()
            # because it checks is_connected which isn't set yet)
            url = f"{self._connection.api_base_url}/system"
            params = {"fields": "$key,yb_version,os_version,cloud_name"}

            session = self._connection._session
            if session is None:
                raise NotConnectedError("Session not initialized")

            resp = session.request(
                method="GET",
                url=url,
                params=params,
                timeout=self._timeout,
            )

            if resp.status_code in HTTP_AUTH_FAILURE_CODES:
                raise AuthenticationError(
                    self._extract_error_message(resp), status_code=resp.status_code
                )

            if resp.status_code in HTTP_SUCCESS_CODES and resp.text:
                response = resp.json()
                # Response can be a dict or a list with one item
                if isinstance(response, list) and len(response) > 0:
                    response = response[0]
                if isinstance(response, dict):
                    self._connection.vergeos_version = response.get("yb_version")
                    self._connection.os_version = response.get("os_version")
                    self._connection.cloud_name = response.get("cloud_name")
                    self._connection.connected_at = datetime.now(timezone.utc)
                    self._connection.is_connected = True
                    return

            raise VergeConnectionError(f"Unexpected response: HTTP {resp.status_code}")

        except AuthenticationError:
            raise
        except VergeConnectionError:
            raise
        except Exception as e:
            raise VergeConnectionError(f"Failed to connect to {self.host}: {e}") from e

    def disconnect(self) -> None:
        """Disconnect from VergeOS and cleanup resources."""
        if self._connection:
            self._connection.disconnect()
            self._connection = None

    @property
    def is_connected(self) -> bool:
        """Check if client is connected."""
        return self._connection is not None and self._connection.is_connected

    @property
    def version(self) -> str | None:
        """Get VergeOS version (yb_version)."""
        if self._connection:
            return self._connection.vergeos_version
        return None

    @property
    def os_version(self) -> str | None:
        """Get VergeOS OS version."""
        if self._connection:
            return self._connection.os_version
        return None

    @property
    def cloud_name(self) -> str | None:
        """Get the cloud name of the connected system."""
        if self._connection:
            return self._connection.cloud_name
        return None

    def __enter__(self) -> VergeClient:
        return self

    def __exit__(
        self,
        exc_type: type | None,
        exc_val: BaseException | None,
        exc_tb: Any | None,
    ) -> None:
        self.disconnect()

    def _request(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
        json_data: dict[str, Any] | None = None,
        timeout: int | None = None,
    ) -> dict[str, Any] | list[Any] | None:
        """Make an HTTP request to the VergeOS API.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE, PATCH).
            endpoint: API endpoint (without /api/v4 prefix).
            params: Query parameters.
            json_data: JSON body for POST/PUT/PATCH.
            timeout: Request timeout in seconds.

        Returns:
            Parsed JSON response or None for empty responses.

        Raises:
            NotConnectedError: If not connected.
            AuthenticationError: For 401/403 responses.
            NotFoundError: For 404 responses.
            APIError: For other API errors.
            TimeoutError: If request times out.
            ConnectionError: If connection fails.
        """
        if not self._connection or not self._connection.is_connected:
            raise NotConnectedError("Not connected to VergeOS")

        session = self._connection._session
        if session is None:
            raise NotConnectedError("Session not initialized")

        url = f"{self._connection.api_base_url}/{endpoint}"

        logger.debug("%s %s params=%s", method, url, params)

        try:
            response = session.request(
                method=method,
                url=url,
                params=params,
                json=json_data,
                timeout=timeout or self._timeout,
            )

            return self._handle_response(response)

        except requests.exceptions.Timeout as e:
            raise VergeTimeoutError(f"Request to {url} timed out") from e
        except requests.exceptions.ConnectionError as e:
            raise VergeConnectionError(f"Connection to {self.host} failed: {e}") from e

    def _handle_response(self, response: requests.Response) -> dict[str, Any] | list[Any] | None:
        """Handle API response and raise appropriate exceptions."""
        # Success responses
        if response.status_code in HTTP_SUCCESS_CODES:
            if response.text:
                return response.json()  # type: ignore[no-any-return]
            return None

        if response.status_code == HTTP_NO_CONTENT:
            return None

        # Error responses
        error_message = self._extract_error_message(response)

        if response.status_code in HTTP_AUTH_FAILURE_CODES:
            raise AuthenticationError(error_message, status_code=response.status_code)
        elif response.status_code == HTTP_NOT_FOUND:
            raise NotFoundError(error_message, status_code=response.status_code)
        elif response.status_code == HTTP_CONFLICT:
            raise ConflictError(error_message, status_code=response.status_code)
        elif response.status_code == HTTP_UNPROCESSABLE_ENTITY:
            raise ValidationError(error_message, status_code=response.status_code)
        else:
            raise APIError(error_message, status_code=response.status_code)

    def _extract_error_message(self, response: requests.Response) -> str:
        """Extract error message from API response."""
        try:
            data = response.json()
            # VergeOS uses 'err', 'error', or 'message' fields
            for field in ("err", "error", "message"):
                if field in data:
                    msg = data[field]
                    if isinstance(msg, str):
                        return msg
                    elif isinstance(msg, dict) and "message" in msg:
                        return str(msg["message"])
            return str(data)
        except (json.JSONDecodeError, KeyError):
            return response.text or f"HTTP {response.status_code}"

    # Resource manager properties

    @property
    def alarms(self) -> AlarmManager:
        """Access alarm operations."""
        if self._alarms is None:
            from pyvergeos.resources.alarms import AlarmManager

            self._alarms = AlarmManager(self)
        return self._alarms

    @property
    def logs(self) -> LogManager:
        """Access log operations."""
        if self._logs is None:
            from pyvergeos.resources.logs import LogManager

            self._logs = LogManager(self)
        return self._logs

    @property
    def vms(self) -> VMManager:
        """Access VM operations."""
        if self._vms is None:
            from pyvergeos.resources.vms import VMManager

            self._vms = VMManager(self)
        return self._vms

    @property
    def networks(self) -> NetworkManager:
        """Access network operations."""
        if self._networks is None:
            from pyvergeos.resources.networks import NetworkManager

            self._networks = NetworkManager(self)
        return self._networks

    @property
    def tenants(self) -> TenantManager:
        """Access tenant operations."""
        if self._tenants is None:
            from pyvergeos.resources.tenant_manager import TenantManager

            self._tenants = TenantManager(self)
        return self._tenants

    @property
    def tenant_dashboard(self) -> TenantDashboardManager:
        """Access tenant dashboard with aggregated metrics.

        Provides high-level overview of all tenant status and resource
        utilization for monitoring and capacity planning.

        Example:
            >>> dashboard = client.tenant_dashboard.get()
            >>> print(f"Online: {dashboard.tenants_online}/{dashboard.tenants_count}")
            >>> print(f"Errors: {dashboard.tenants_error}")
        """
        if self._tenant_dashboard is None:
            from pyvergeos.resources.tenant_stats import TenantDashboardManager

            self._tenant_dashboard = TenantDashboardManager(self)
        return self._tenant_dashboard

    @property
    def billing(self) -> BillingManager:
        """Access billing records for resource usage tracking and chargeback.

        Provides access to system-wide resource utilization records
        for billing, chargeback, and capacity planning purposes.

        Example:
            >>> # List billing records
            >>> records = client.billing.list(limit=100)
            >>> for record in records:
            ...     print(f"{record.created}: {record.used_cores} cores")

            >>> # Get the latest billing record
            >>> latest = client.billing.get_latest()
            >>> print(f"CPU: {latest.cpu_utilization_pct:.1f}%")

            >>> # Generate a new billing report
            >>> client.billing.generate()

            >>> # Get summary over time
            >>> from datetime import datetime, timedelta
            >>> since = datetime.now() - timedelta(days=30)
            >>> summary = client.billing.get_summary(since=since)
        """
        if self._billing is None:
            from pyvergeos.resources.billing import BillingManager

            self._billing = BillingManager(self)
        return self._billing

    @property
    def network_dashboard(self) -> NetworkDashboardManager:
        """Access network dashboard with aggregated metrics.

        Provides high-level overview of all network status, counts by type
        and state, and top bandwidth consumers for monitoring.

        Example:
            >>> dashboard = client.network_dashboard.get()
            >>> print(f"Online: {dashboard.vnets_online}/{dashboard.vnets_count}")
            >>> print(f"External: {dashboard.ext_online}/{dashboard.ext_count}")
            >>> print(f"Internal: {dashboard.int_online}/{dashboard.int_count}")
            >>> if dashboard.has_errors:
            ...     print(f"WARNING: {dashboard.vnets_error} networks in error state!")

            >>> # Get health summary by type
            >>> health = dashboard.get_health_summary()
            >>> for net_type, counts in health.items():
            ...     print(f"{net_type}: {counts['online']}/{counts['count']}")
        """
        if self._network_dashboard is None:
            from pyvergeos.resources.network_stats import NetworkDashboardManager

            self._network_dashboard = NetworkDashboardManager(self)
        return self._network_dashboard

    @property
    def users(self) -> UserManager:
        """Access user operations."""
        if self._users is None:
            from pyvergeos.resources.users import UserManager

            self._users = UserManager(self)
        return self._users

    @property
    def api_keys(self) -> APIKeyManager:
        """Access API key operations."""
        if self._api_keys is None:
            from pyvergeos.resources.api_keys import APIKeyManager

            self._api_keys = APIKeyManager(self)
        return self._api_keys

    @property
    def groups(self) -> GroupManager:
        """Access group operations."""
        if self._groups is None:
            from pyvergeos.resources.groups import GroupManager

            self._groups = GroupManager(self)
        return self._groups

    @property
    def permissions(self) -> PermissionManager:
        """Access permission operations."""
        if self._permissions is None:
            from pyvergeos.resources.permissions import PermissionManager

            self._permissions = PermissionManager(self)
        return self._permissions

    @property
    def clusters(self) -> ClusterManager:
        """Access cluster operations."""
        if self._clusters is None:
            from pyvergeos.resources.clusters import ClusterManager

            self._clusters = ClusterManager(self)
        return self._clusters

    @property
    def nodes(self) -> NodeManager:
        """Access node operations."""
        if self._nodes is None:
            from pyvergeos.resources.nodes import NodeManager

            self._nodes = NodeManager(self)
        return self._nodes

    @property
    def tasks(self) -> TaskManager:
        """Access task operations."""
        if self._tasks is None:
            from pyvergeos.resources.tasks import TaskManager

            self._tasks = TaskManager(self)
        return self._tasks

    @property
    def files(self) -> FileManager:
        """Access file/media catalog operations."""
        if self._files is None:
            from pyvergeos.resources.files import FileManager

            self._files = FileManager(self)
        return self._files

    @property
    def storage_tiers(self) -> StorageTierManager:
        """Access storage tier operations."""
        if self._storage_tiers is None:
            from pyvergeos.resources.storage_tiers import StorageTierManager

            self._storage_tiers = StorageTierManager(self)
        return self._storage_tiers

    @property
    def nas_services(self) -> NASServiceManager:
        """Access NAS service operations."""
        if self._nas_services is None:
            from pyvergeos.resources.nas_services import NASServiceManager

            self._nas_services = NASServiceManager(self)
        return self._nas_services

    @property
    def nas_volumes(self) -> NASVolumeManager:
        """Access NAS volume operations."""
        if self._nas_volumes is None:
            from pyvergeos.resources.nas_volumes import NASVolumeManager

            self._nas_volumes = NASVolumeManager(self)
        return self._nas_volumes

    @property
    def nas_volume_snapshots(self) -> NASVolumeSnapshotManager:
        """Access NAS volume snapshot operations."""
        if self._nas_volume_snapshots is None:
            from pyvergeos.resources.nas_volumes import NASVolumeSnapshotManager

            self._nas_volume_snapshots = NASVolumeSnapshotManager(self)
        return self._nas_volume_snapshots

    @property
    def cifs_shares(self) -> NASCIFSShareManager:
        """Access NAS CIFS/SMB share operations."""
        if self._cifs_shares is None:
            from pyvergeos.resources.nas_cifs import NASCIFSShareManager

            self._cifs_shares = NASCIFSShareManager(self)
        return self._cifs_shares

    @property
    def nfs_shares(self) -> NASNFSShareManager:
        """Access NAS NFS share operations."""
        if self._nfs_shares is None:
            from pyvergeos.resources.nas_nfs import NASNFSShareManager

            self._nfs_shares = NASNFSShareManager(self)
        return self._nfs_shares

    @property
    def nas_users(self) -> NASUserManager:
        """Access NAS local user operations."""
        if self._nas_users is None:
            from pyvergeos.resources.nas_users import NASUserManager

            self._nas_users = NASUserManager(self)
        return self._nas_users

    @property
    def volume_syncs(self) -> NASVolumeSyncManager:
        """Access NAS volume sync operations."""
        if self._volume_syncs is None:
            from pyvergeos.resources.nas_volume_syncs import NASVolumeSyncManager

            self._volume_syncs = NASVolumeSyncManager(self)
        return self._volume_syncs

    @property
    def shared_objects(self) -> SharedObjectManager:
        """Access shared object operations for tenant VM sharing."""
        if self._shared_objects is None:
            from pyvergeos.resources.shared_objects import SharedObjectManager

            self._shared_objects = SharedObjectManager(self)
        return self._shared_objects

    @property
    def system(self) -> SystemManager:
        """Access system operations (settings, statistics, licenses, inventory)."""
        if self._system is None:
            from pyvergeos.resources.system import SystemManager

            self._system = SystemManager(self)
        return self._system

    @property
    def sites(self) -> SiteManager:
        """Access site operations for backup/DR remote site connections."""
        if self._sites is None:
            from pyvergeos.resources.sites import SiteManager

            self._sites = SiteManager(self)
        return self._sites

    @property
    def site_syncs(self) -> SiteSyncOutgoingManager:
        """Access outgoing site sync operations for backup/DR."""
        if self._site_syncs is None:
            from pyvergeos.resources.site_syncs import SiteSyncOutgoingManager

            self._site_syncs = SiteSyncOutgoingManager(self)
        return self._site_syncs

    @property
    def site_syncs_incoming(self) -> SiteSyncIncomingManager:
        """Access incoming site sync operations for backup/DR."""
        if self._site_syncs_incoming is None:
            from pyvergeos.resources.site_syncs import SiteSyncIncomingManager

            self._site_syncs_incoming = SiteSyncIncomingManager(self)
        return self._site_syncs_incoming

    @property
    def site_sync_schedules(self) -> SiteSyncScheduleManager:
        """Access site sync schedule operations for backup/DR."""
        if self._site_sync_schedules is None:
            from pyvergeos.resources.site_syncs import SiteSyncScheduleManager

            self._site_sync_schedules = SiteSyncScheduleManager(self)
        return self._site_sync_schedules

    @property
    def snapshot_profiles(self) -> SnapshotProfileManager:
        """Access snapshot profile operations for backup/DR."""
        if self._snapshot_profiles is None:
            from pyvergeos.resources.snapshot_profiles import SnapshotProfileManager

            self._snapshot_profiles = SnapshotProfileManager(self)
        return self._snapshot_profiles

    @property
    def cloud_snapshots(self) -> CloudSnapshotManager:
        """Access cloud (system) snapshot operations for backup/DR."""
        if self._cloud_snapshots is None:
            from pyvergeos.resources.cloud_snapshots import CloudSnapshotManager

            self._cloud_snapshots = CloudSnapshotManager(self)
        return self._cloud_snapshots

    @property
    def resource_groups(self) -> ResourceGroupManager:
        """Access resource group operations for hardware device passthrough.

        Resource groups define collections of hardware devices (GPU, PCI, USB,
        SR-IOV NIC, vGPU) that can be assigned to VMs.
        """
        if self._resource_groups is None:
            from pyvergeos.resources.resource_groups import ResourceGroupManager

            self._resource_groups = ResourceGroupManager(self)
        return self._resource_groups

    @property
    def webhooks(self) -> WebhookManager:
        """Access webhook operations for notification integrations.

        Webhooks allow VergeOS to send notifications to external systems when
        events occur. Configure webhook URLs and view delivery history.
        """
        if self._webhooks is None:
            from pyvergeos.resources.webhooks import WebhookManager

            self._webhooks = WebhookManager(self)
        return self._webhooks

    @property
    def cloudinit_files(self) -> CloudInitFileManager:
        """Access cloud-init file operations for VM provisioning automation.

        Cloud-init files provide user-data, meta-data, and other configuration
        to VMs during boot for automated provisioning.
        """
        if self._cloudinit_files is None:
            from pyvergeos.resources.cloudinit_files import CloudInitFileManager

            self._cloudinit_files = CloudInitFileManager(self)
        return self._cloudinit_files

    @property
    def certificates(self) -> CertificateManager:
        """Access SSL/TLS certificate operations.

        Manage SSL/TLS certificates including manual uploads, Let's Encrypt
        (ACME) certificates, and self-signed certificates.
        """
        if self._certificates is None:
            from pyvergeos.resources.certificates import CertificateManager

            self._certificates = CertificateManager(self)
        return self._certificates

    @property
    def tags(self) -> TagManager:
        """Access tag operations for resource organization.

        Tags provide a flexible way to categorize and organize resources like
        VMs, networks, and tenants. Tags are organized within categories.

        Example:
            >>> # List all tags
            >>> for tag in client.tags.list():
            ...     print(f"{tag.name} (Category: {tag.category_name})")

            >>> # Create a tag
            >>> tag = client.tags.create(
            ...     name="Production",
            ...     category_key=1,
            ...     description="Production resources"
            ... )

            >>> # Tag a VM
            >>> client.tags.members(tag.key).add_vm(vm.key)
        """
        if self._tags is None:
            from pyvergeos.resources.tags import TagManager

            self._tags = TagManager(self)
        return self._tags

    @property
    def tag_categories(self) -> TagCategoryManager:
        """Access tag category operations for organizing tags.

        Tag categories organize tags and define which resource types can be
        tagged with tags in each category.

        Example:
            >>> # List all categories
            >>> for cat in client.tag_categories.list():
            ...     print(f"{cat.name}: {cat.get_taggable_types()}")

            >>> # Create a category
            >>> category = client.tag_categories.create(
            ...     name="Environment",
            ...     description="Deployment environment",
            ...     taggable_vms=True,
            ...     taggable_networks=True,
            ...     single_tag_selection=True
            ... )
        """
        if self._tag_categories is None:
            from pyvergeos.resources.tags import TagCategoryManager

            self._tag_categories = TagCategoryManager(self)
        return self._tag_categories

    @property
    def vm_imports(self) -> VmImportManager:
        """Access VM import operations for importing VMs from files.

        VM imports allow importing virtual machines from various formats
        including VMDK, QCOW2, OVA, and OVF files.

        Example:
            >>> # List all imports
            >>> for imp in client.vm_imports.list():
            ...     print(f"{imp.name}: {imp.status}")

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
        if self._vm_imports is None:
            from pyvergeos.resources.vm_imports import VmImportManager

            self._vm_imports = VmImportManager(self)
        return self._vm_imports

    @property
    def vm_import_logs(self) -> VmImportLogManager:
        """Access VM import log operations.

        VM import logs provide detailed progress and error information
        for VM import operations.

        Example:
            >>> # List all import logs
            >>> for log in client.vm_import_logs.list():
            ...     print(f"{log.level}: {log.text}")

            >>> # List errors only
            >>> errors = client.vm_import_logs.list(level="error")
        """
        if self._vm_import_logs is None:
            from pyvergeos.resources.vm_imports import VmImportLogManager

            self._vm_import_logs = VmImportLogManager(self)
        return self._vm_import_logs

    @property
    def volume_vm_exports(self) -> VolumeVmExportManager:
        """Access volume VM export operations for exporting VMs to NAS volumes.

        Volume VM exports allow exporting VMs to NAS volumes for backup
        and migration purposes.

        Example:
            >>> # List all exports
            >>> for exp in client.volume_vm_exports.list():
            ...     print(f"{exp.volume_name}: {exp.status}")

            >>> # Create an export configuration
            >>> exp = client.volume_vm_exports.create(
            ...     volume=123,
            ...     max_exports=5,
            ...     quiesced=True
            ... )

            >>> # Start an export
            >>> exp.start(name="backup-2024")

            >>> # View export stats
            >>> for stat in exp.stats.list():
            ...     print(f"{stat.file_name}: {stat.size_gb}GB")
        """
        if self._volume_vm_exports is None:
            from pyvergeos.resources.volume_vm_exports import VolumeVmExportManager

            self._volume_vm_exports = VolumeVmExportManager(self)
        return self._volume_vm_exports

    @property
    def volume_vm_export_stats(self) -> VolumeVmExportStatManager:
        """Access volume VM export statistics.

        VM export stats provide information about completed export
        operations including size, duration, and success/error counts.

        Example:
            >>> # List all export stats
            >>> for stat in client.volume_vm_export_stats.list():
            ...     print(f"{stat.file_name}: {stat.size_gb}GB")

            >>> # List stats for a specific export
            >>> stats = client.volume_vm_export_stats.list(volume_vm_exports=1)
        """
        if self._volume_vm_export_stats is None:
            from pyvergeos.resources.volume_vm_exports import VolumeVmExportStatManager

            self._volume_vm_export_stats = VolumeVmExportStatManager(self)
        return self._volume_vm_export_stats

    @property
    def vm_recipes(self) -> VmRecipeManager:
        """Access VM recipe operations for automated VM provisioning.

        VM recipes are templates that can be deployed to create new VMs
        with pre-configured settings and software.

        Example:
            >>> # List all VM recipes
            >>> for recipe in client.vm_recipes.list():
            ...     print(f"{recipe.name}: {recipe.version}")

            >>> # Get a specific recipe
            >>> recipe = client.vm_recipes.get(name="Ubuntu Server")

            >>> # Deploy a recipe
            >>> instance = recipe.deploy("my-ubuntu", answers={"ram": 4096})
        """
        if self._vm_recipes is None:
            from pyvergeos.resources.vm_recipes import VmRecipeManager

            self._vm_recipes = VmRecipeManager(self)
        return self._vm_recipes

    @property
    def vm_recipe_instances(self) -> VmRecipeInstanceManager:
        """Access VM recipe instance operations.

        VM recipe instances represent deployed VMs created from recipes.

        Example:
            >>> # List all VM recipe instances
            >>> for inst in client.vm_recipe_instances.list():
            ...     print(f"{inst.name}: {inst.version}")

            >>> # List instances for a specific recipe
            >>> insts = client.vm_recipe_instances.list(recipe="8f73f8bcc9...")
        """
        if self._vm_recipe_instances is None:
            from pyvergeos.resources.vm_recipes import VmRecipeInstanceManager

            self._vm_recipe_instances = VmRecipeInstanceManager(self)
        return self._vm_recipe_instances

    @property
    def vm_recipe_logs(self) -> VmRecipeLogManager:
        """Access VM recipe log operations.

        VM recipe logs provide detailed progress and error information
        for recipe operations.

        Example:
            >>> # List all recipe logs
            >>> for log in client.vm_recipe_logs.list():
            ...     print(f"{log.level}: {log.text}")

            >>> # List errors only
            >>> errors = client.vm_recipe_logs.list_errors()
        """
        if self._vm_recipe_logs is None:
            from pyvergeos.resources.vm_recipes import VmRecipeLogManager

            self._vm_recipe_logs = VmRecipeLogManager(self)
        return self._vm_recipe_logs

    @property
    def tenant_recipes(self) -> TenantRecipeManager:
        """Access tenant recipe operations for automated tenant provisioning.

        Tenant recipes are templates that can be deployed to create new
        tenants with pre-configured settings and resources.

        Example:
            >>> # List all tenant recipes
            >>> for recipe in client.tenant_recipes.list():
            ...     print(f"{recipe.name}: {recipe.version}")

            >>> # Get a specific recipe
            >>> recipe = client.tenant_recipes.get(name="Standard Tenant")

            >>> # Deploy a recipe
            >>> instance = recipe.deploy("my-tenant", answers={"storage_gb": 500})
        """
        if self._tenant_recipes is None:
            from pyvergeos.resources.tenant_recipes import TenantRecipeManager

            self._tenant_recipes = TenantRecipeManager(self)
        return self._tenant_recipes

    @property
    def tenant_recipe_instances(self) -> TenantRecipeInstanceManager:
        """Access tenant recipe instance operations.

        Tenant recipe instances represent deployed tenants created from recipes.

        Example:
            >>> # List all tenant recipe instances
            >>> for inst in client.tenant_recipe_instances.list():
            ...     print(f"{inst.name}: {inst.version}")

            >>> # List instances for a specific recipe
            >>> insts = client.tenant_recipe_instances.list(recipe="8f73f8bcc9...")
        """
        if self._tenant_recipe_instances is None:
            from pyvergeos.resources.tenant_recipes import TenantRecipeInstanceManager

            self._tenant_recipe_instances = TenantRecipeInstanceManager(self)
        return self._tenant_recipe_instances

    @property
    def tenant_recipe_logs(self) -> TenantRecipeLogManager:
        """Access tenant recipe log operations.

        Tenant recipe logs provide detailed progress and error information
        for recipe operations.

        Example:
            >>> # List all recipe logs
            >>> for log in client.tenant_recipe_logs.list():
            ...     print(f"{log.level}: {log.text}")

            >>> # List errors only
            >>> errors = client.tenant_recipe_logs.list_errors()
        """
        if self._tenant_recipe_logs is None:
            from pyvergeos.resources.tenant_recipes import TenantRecipeLogManager

            self._tenant_recipe_logs = TenantRecipeLogManager(self)
        return self._tenant_recipe_logs

    @property
    def recipe_questions(self) -> RecipeQuestionManager:
        """Access recipe question operations.

        Recipe questions define the configuration options available when
        deploying a recipe. Questions are organized into sections.

        Example:
            >>> # List all questions for a VM recipe
            >>> questions = client.recipe_questions.list(
            ...     recipe_ref="vm_recipes/8f73f8bcc9..."
            ... )
            >>> for q in questions:
            ...     print(f"{q.name}: {q.question_type}")
        """
        if self._recipe_questions is None:
            from pyvergeos.resources.recipe_common import RecipeQuestionManager

            self._recipe_questions = RecipeQuestionManager(self)
        return self._recipe_questions

    @property
    def recipe_sections(self) -> RecipeSectionManager:
        """Access recipe section operations.

        Recipe sections organize questions into logical groups.

        Example:
            >>> # List all sections for a VM recipe
            >>> sections = client.recipe_sections.list(
            ...     recipe_ref="vm_recipes/8f73f8bcc9..."
            ... )
            >>> for s in sections:
            ...     print(f"{s.name}: {s.description}")
        """
        if self._recipe_sections is None:
            from pyvergeos.resources.recipe_common import RecipeSectionManager

            self._recipe_sections = RecipeSectionManager(self)
        return self._recipe_sections

    @property
    def task_schedules(self) -> TaskScheduleManager:
        """Access task schedule operations.

        Task schedules define when scheduled tasks should run. They support
        various repeat intervals (minute, hour, day, week, month, year).

        Example:
            >>> # List all schedules
            >>> for schedule in client.task_schedules.list():
            ...     print(f"{schedule.name}: {schedule.repeat_every_display}")

            >>> # Create a daily schedule
            >>> schedule = client.task_schedules.create(
            ...     name="Nightly Backup",
            ...     repeat_every="day",
            ...     start_time_of_day=7200,  # 2 AM
            ... )

            >>> # Get upcoming execution times
            >>> times = schedule.get_schedule(max_results=10)
        """
        if self._task_schedules is None:
            from pyvergeos.resources.task_schedules import TaskScheduleManager

            self._task_schedules = TaskScheduleManager(self)
        return self._task_schedules

    @property
    def task_schedule_triggers(self) -> TaskScheduleTriggerManager:
        """Access task schedule trigger operations.

        Task schedule triggers link tasks to schedules. When a schedule fires,
        all linked tasks are executed.

        Example:
            >>> # List all triggers
            >>> for trigger in client.task_schedule_triggers.list():
            ...     print(f"{trigger.task_display} -> {trigger.schedule_display}")

            >>> # Link a task to a schedule
            >>> trigger = client.task_schedule_triggers.create(
            ...     task=task.key,
            ...     schedule=schedule.key,
            ... )

            >>> # List triggers for a specific task
            >>> triggers = client.task_schedule_triggers.list(task=task.key)
        """
        if self._task_schedule_triggers is None:
            from pyvergeos.resources.task_schedule_triggers import TaskScheduleTriggerManager

            self._task_schedule_triggers = TaskScheduleTriggerManager(self)
        return self._task_schedule_triggers

    @property
    def task_events(self) -> TaskEventManager:
        """Access task event operations.

        Task events enable event-driven automation by linking tasks to system
        events. When a specific event occurs on a resource, linked tasks execute.

        Example:
            >>> # List all task events
            >>> for event in client.task_events.list():
            ...     print(f"{event.event_name_display}: {event.task_display}")

            >>> # List events for a specific task
            >>> events = client.task_events.list(task=task.key)

            >>> # List events for VMs only
            >>> events = client.task_events.list(table="vms")

            >>> # Manually trigger an event
            >>> client.task_events.trigger(event.key, context={"key": "value"})
        """
        if self._task_events is None:
            from pyvergeos.resources.task_events import TaskEventManager

            self._task_events = TaskEventManager(self)
        return self._task_events

    @property
    def task_scripts(self) -> TaskScriptManager:
        """Access task script operations.

        Task scripts are GCS (VergeOS scripting) code that can be executed
        as tasks. Scripts can define questions that are prompted when running.

        Example:
            >>> # List all scripts
            >>> for script in client.task_scripts.list():
            ...     print(f"{script.name}: {script.task_count} tasks")

            >>> # Create a script
            >>> script = client.task_scripts.create(
            ...     name="Cleanup Script",
            ...     script="log('Cleanup started')",
            ...     task_settings={"questions": []},
            ... )

            >>> # Run a script
            >>> result = script.run()
        """
        if self._task_scripts is None:
            from pyvergeos.resources.task_scripts import TaskScriptManager

            self._task_scripts = TaskScriptManager(self)
        return self._task_scripts

    @property
    def catalog_repositories(self) -> CatalogRepositoryManager:
        """Access catalog repository operations.

        Catalog repositories define where catalogs and recipes are sourced from.
        Types include local, remote, git, and Verge.io marketplace.

        Example:
            >>> # List all repositories
            >>> for repo in client.catalog_repositories.list():
            ...     print(f"{repo.name} ({repo.type})")

            >>> # Get the Verge.io marketplace
            >>> marketplace = client.catalog_repositories.get(name="Verge.io Recipes")

            >>> # Refresh a repository
            >>> repo.refresh()

            >>> # List catalogs in a repository
            >>> for catalog in repo.catalogs.list():
            ...     print(f"  {catalog.name}")
        """
        if self._catalog_repositories is None:
            from pyvergeos.resources.catalogs import CatalogRepositoryManager

            self._catalog_repositories = CatalogRepositoryManager(self)
        return self._catalog_repositories

    @property
    def catalogs(self) -> CatalogManager:
        """Access catalog operations.

        Catalogs organize recipes into logical groups within repositories.

        Example:
            >>> # List all catalogs
            >>> for catalog in client.catalogs.list():
            ...     print(f"{catalog.name}: {catalog.description}")

            >>> # List catalogs in a specific repository
            >>> for catalog in client.catalogs.list(repository=1):
            ...     print(f"{catalog.name}")

            >>> # Get a specific catalog
            >>> catalog = client.catalogs.get(name="VergeOS Recipes")
        """
        if self._catalogs is None:
            from pyvergeos.resources.catalogs import CatalogManager

            self._catalogs = CatalogManager(self)
        return self._catalogs

    @property
    def catalog_logs(self) -> CatalogLogManager:
        """Access catalog log operations.

        Catalog logs provide activity history for catalog operations.

        Example:
            >>> # List all catalog logs
            >>> for log in client.catalog_logs.list():
            ...     print(f"{log.level}: {log.text}")

            >>> # List errors only
            >>> errors = client.catalog_logs.list_errors()
        """
        if self._catalog_logs is None:
            from pyvergeos.resources.catalogs import CatalogLogManager

            self._catalog_logs = CatalogLogManager(self)
        return self._catalog_logs

    @property
    def catalog_repository_logs(self) -> CatalogRepositoryLogManager:
        """Access catalog repository log operations.

        Repository logs provide activity history for repository operations
        including refresh, download, and sync activities.

        Example:
            >>> # List all repository logs
            >>> for log in client.catalog_repository_logs.list():
            ...     print(f"{log.level}: {log.text}")

            >>> # List errors only
            >>> errors = client.catalog_repository_logs.list_errors()
        """
        if self._catalog_repository_logs is None:
            from pyvergeos.resources.catalogs import CatalogRepositoryLogManager

            self._catalog_repository_logs = CatalogRepositoryLogManager(self)
        return self._catalog_repository_logs

    @property
    def catalog_repository_status(self) -> CatalogRepositoryStatusManager:
        """Access catalog repository status operations.

        Repository status provides current operational state information.

        Example:
            >>> # List all repository statuses
            >>> for status in client.catalog_repository_status.list():
            ...     print(f"{status.repository_key}: {status.status}")

            >>> # Get status for a specific repository
            >>> status = client.catalog_repository_status.get_for_repository(1)
        """
        if self._catalog_repository_status is None:
            from pyvergeos.resources.catalogs import CatalogRepositoryStatusManager

            self._catalog_repository_status = CatalogRepositoryStatusManager(self)
        return self._catalog_repository_status

    @property
    def vgpu_profiles(self) -> NvidiaVgpuProfileManager:
        """Access NVIDIA vGPU profile operations.

        vGPU profiles define the characteristics of virtual GPUs that can be
        created. Profiles are read-only and determined by NVIDIA drivers and
        available hardware.

        Example:
            >>> # List all vGPU profiles
            >>> for profile in client.vgpu_profiles.list():
            ...     print(f"{profile.name}: {profile.framebuffer}")

            >>> # List AI/ML profiles only
            >>> ml_profiles = client.vgpu_profiles.list(profile_type="C")

            >>> # Get a specific profile
            >>> profile = client.vgpu_profiles.get(name="nvidia-256")
        """
        if self._vgpu_profiles is None:
            from pyvergeos.resources.gpu import NvidiaVgpuProfileManager

            self._vgpu_profiles = NvidiaVgpuProfileManager(self)
        return self._vgpu_profiles
