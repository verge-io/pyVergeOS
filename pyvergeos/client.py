"""Main VergeClient class for interacting with VergeOS API v4."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

import requests

from pyvergeos.connection import AuthMethod, VergeConnection, build_auth_header
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
    from pyvergeos.resources.clusters import ClusterManager
    from pyvergeos.resources.files import FileManager
    from pyvergeos.resources.groups import GroupManager
    from pyvergeos.resources.networks import NetworkManager
    from pyvergeos.resources.nodes import NodeManager
    from pyvergeos.resources.storage_tiers import StorageTierManager
    from pyvergeos.resources.tasks import TaskManager
    from pyvergeos.resources.tenants import TenantManager
    from pyvergeos.resources.users import UserManager
    from pyvergeos.resources.vms import VMManager

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
        timeout: int = 30,
        auto_connect: bool = True,
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

        Raises:
            ValueError: If neither token nor username/password provided.
        """
        self.host = host
        self._username = username
        self._password = password
        self._token = token
        self._verify_ssl = verify_ssl
        self._timeout = timeout

        self._connection: VergeConnection | None = None

        # Resource managers (lazy-loaded)
        self._vms: VMManager | None = None
        self._networks: NetworkManager | None = None
        self._tenants: TenantManager | None = None
        self._users: UserManager | None = None
        self._groups: GroupManager | None = None
        self._clusters: ClusterManager | None = None
        self._nodes: NodeManager | None = None
        self._tasks: TaskManager | None = None
        self._files: FileManager | None = None
        self._storage_tiers: StorageTierManager | None = None

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
            timeout=int(os.environ.get("VERGE_TIMEOUT", "30")),
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
                "Content-Type": "application/json",
                "Accept": "application/json",
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

            if resp.status_code in (401, 403):
                raise AuthenticationError(
                    self._extract_error_message(resp), status_code=resp.status_code
                )

            if resp.status_code == 200 and resp.text:
                response = resp.json()
                # Response can be a dict or a list with one item
                if isinstance(response, list) and len(response) > 0:
                    response = response[0]
                if isinstance(response, dict):
                    self._connection.vergeos_version = response.get("yb_version")
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
        """Get VergeOS version."""
        if self._connection:
            return self._connection.vergeos_version
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
        if response.status_code in (200, 201):
            if response.text:
                return response.json()  # type: ignore[no-any-return]
            return None

        if response.status_code == 204:
            return None

        # Error responses
        error_message = self._extract_error_message(response)

        if response.status_code in (401, 403):
            raise AuthenticationError(error_message, status_code=response.status_code)
        elif response.status_code == 404:
            raise NotFoundError(error_message, status_code=response.status_code)
        elif response.status_code == 409:
            raise ConflictError(error_message, status_code=response.status_code)
        elif response.status_code == 422:
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
            from pyvergeos.resources.tenants import TenantManager

            self._tenants = TenantManager(self)
        return self._tenants

    @property
    def users(self) -> UserManager:
        """Access user operations."""
        if self._users is None:
            from pyvergeos.resources.users import UserManager

            self._users = UserManager(self)
        return self._users

    @property
    def groups(self) -> GroupManager:
        """Access group operations."""
        if self._groups is None:
            from pyvergeos.resources.groups import GroupManager

            self._groups = GroupManager(self)
        return self._groups

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
