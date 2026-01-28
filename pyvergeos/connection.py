"""Connection and session management for VergeOS API."""

from base64 import b64encode
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


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
        verify_ssl: Whether to verify SSL certificates.
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
    connected_at: Optional[datetime] = None
    vergeos_version: Optional[str] = None
    os_version: Optional[str] = None
    cloud_name: Optional[str] = None
    is_connected: bool = False

    _session: Optional[requests.Session] = field(default=None, repr=False)

    def __post_init__(self) -> None:
        self.api_base_url = f"https://{self.host}/api/v4"

        # Create session (done here so it can be mocked in tests)
        if self._session is None:
            self._session = requests.Session()

        # Configure retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "PUT", "DELETE", "POST"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self._session.mount("https://", adapter)
        self._session.mount("http://", adapter)

        if not self.verify_ssl:
            self._session.verify = False
            # Suppress InsecureRequestWarning (session-scoped via filter)
            import warnings

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
        """Clear connection state and close session."""
        self.token = None
        self.token_expires = None
        self.connected_at = None
        self.is_connected = False
        if self._session:
            self._session.close()


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
