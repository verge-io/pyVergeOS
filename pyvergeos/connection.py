"""Connection and session management for VergeOS API."""

import warnings
from base64 import b64encode
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from pyvergeos.constants import (
    API_VERSION,
    RETRY_BACKOFF_FACTOR,
    RETRY_METHODS,
    RETRY_STATUS_CODES,
    RETRY_TOTAL,
)


class AuthMethod(Enum):
    """Authentication methods supported by VergeOS API."""

    BASIC = "basic"
    TOKEN = "token"


@dataclass
class VergeConnection:
    """Manages connection state to a VergeOS system.

    Attributes:
        host: VergeOS hostname or IP address.
        username: Username for authentication.
        api_base_url: Computed API base URL.
        token: Authentication token (Basic or Bearer).
        token_expires: Token expiration time (if applicable).
        verify_ssl: Whether to verify SSL certificates. When False, the
            InsecureRequestWarning suppression is process-global — it will
            silence warnings for all clients in the same process, even those
            with verify_ssl=True.
        retry_total: Number of retry attempts for transient failures.
        retry_backoff_factor: Backoff factor for retry delay calculation.
        retry_status_codes: HTTP status codes that trigger automatic retry.
        session: Optional caller-supplied requests session. When supplied, the
            SDK does not mount adapters, change TLS verification, or close it
            on disconnect by default. Header snapshots for VergeClient-managed
            authentication are populated by VergeClient.connect(). Do not share
            one supplied session across multiple active VergeClient instances;
            authentication is stored in session headers while connected.
        close_session: Override for disconnect lifecycle. None closes
            SDK-created sessions and leaves caller-supplied sessions open.
        connected_at: Timestamp when connection was established.
        vergeos_version: VergeOS version from system endpoint.
        is_connected: Whether connection is active.
    """

    host: str
    username: str = ""
    api_base_url: str = field(init=False)
    token: Optional[str] = None
    token_expires: Optional[datetime] = None
    verify_ssl: bool = True
    retry_total: int = RETRY_TOTAL
    retry_backoff_factor: float = RETRY_BACKOFF_FACTOR
    retry_status_codes: Iterable[int] = RETRY_STATUS_CODES
    connected_at: Optional[datetime] = None
    vergeos_version: Optional[str] = None
    os_version: Optional[str] = None
    cloud_name: Optional[str] = None
    is_connected: bool = False
    session: Optional[requests.Session] = field(default=None, repr=False)
    close_session: Optional[bool] = None

    _owns_session: bool = field(init=False, default=True, repr=False)
    _pre_connect_headers: Optional[dict[str, Optional[str]]] = field(
        init=False, default=None, repr=False
    )

    def __post_init__(self) -> None:
        self.api_base_url = f"https://{self.host}/api/{API_VERSION}"
        self._owns_session = self.session is None

        # Create session (done here so it can be mocked in tests)
        if self.session is None:
            self.session = requests.Session()

        if not self._owns_session:
            ignored_config = []
            if self.retry_total != RETRY_TOTAL:
                ignored_config.append("retry_total")
            if self.retry_backoff_factor != RETRY_BACKOFF_FACTOR:
                ignored_config.append("retry_backoff_factor")
            if set(self.retry_status_codes) != set(RETRY_STATUS_CODES):
                ignored_config.append("retry_status_codes")
            if not self.verify_ssl:
                ignored_config.append("verify_ssl")

            if ignored_config:
                warnings.warn(
                    "VergeConnection received a caller-supplied session; "
                    f"{', '.join(ignored_config)} will be ignored. Configure retry "
                    "and TLS behavior on the supplied session instead.",
                    UserWarning,
                    stacklevel=2,
                )
            return

        # Configure retry strategy with configurable parameters
        retry_strategy = Retry(
            total=self.retry_total,
            backoff_factor=self.retry_backoff_factor,
            status_forcelist=list(self.retry_status_codes),
            allowed_methods=list(RETRY_METHODS),
        )
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=1,
            pool_maxsize=10,
        )
        self.session.mount("https://", adapter)

        if not self.verify_ssl:
            self.session.verify = False
            # Suppress InsecureRequestWarning. Note: this is process-global —
            # setting verify_ssl=False on any client silences warnings for all
            # clients in the same process.
            import urllib3

            warnings.filterwarnings(
                "ignore",
                message="Unverified HTTPS request",
                category=urllib3.exceptions.InsecureRequestWarning,
            )

    def is_token_valid(self) -> bool:
        """Check if the current token/credentials are valid.

        Returns:
            True if connected and token not expired.
        """
        if not self.is_connected:
            return False
        return not (self.token_expires and datetime.now(timezone.utc) >= self.token_expires)

    def disconnect(self) -> None:
        """Clear connection state and close the HTTP session.

        Resets all authentication and connection state including token,
        expiration time, and connection timestamp. SDK-owned requests sessions
        are closed to release network resources. Caller-supplied session
        headers are restored and the session is left open by default.

        Note:
            After calling disconnect(), the connection object can be reused
            by establishing a new connection through the client.
        """
        self.token = None
        self.token_expires = None
        self.connected_at = None
        self.is_connected = False

        if self.session and not self._owns_session and self._pre_connect_headers is not None:
            for key, prior_value in self._pre_connect_headers.items():
                if prior_value is None:
                    self.session.headers.pop(key, None)
                else:
                    self.session.headers[key] = prior_value
            self._pre_connect_headers = None

        should_close = self.close_session if self.close_session is not None else self._owns_session
        if self.session and should_close:
            self.session.close()


def build_auth_header(
    method: AuthMethod,
    username: Optional[str] = None,
    password: Optional[str] = None,
    token: Optional[str] = None,
) -> dict[str, str]:
    """Build the Authorization header based on auth method.

    Args:
        method: Authentication method to use.
        username: Username for basic auth.
        password: Password for basic auth.
        token: API token for token auth.

    Returns:
        Dictionary with Authorization header.

    Raises:
        ValueError: If required credentials not provided.
    """
    if method == AuthMethod.BASIC:
        if not username or not password:
            raise ValueError("Username and password required for basic auth")
        credentials = b64encode(f"{username}:{password}".encode()).decode()
        return {"Authorization": f"Basic {credentials}"}
    elif method == AuthMethod.TOKEN:
        if not token:
            raise ValueError("Token required for token auth")
        return {"Authorization": f"Bearer {token}"}
    raise ValueError(f"Unknown auth method: {method}")
