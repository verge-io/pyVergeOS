"""Tests for connection module."""

from datetime import datetime, timedelta, timezone
from http import HTTPStatus
from unittest.mock import MagicMock, patch

import pytest
import requests
from requests.structures import CaseInsensitiveDict

from pyvergeos.connection import AuthMethod, VergeConnection, build_auth_header
from pyvergeos.constants import RETRY_BACKOFF_FACTOR, RETRY_STATUS_CODES, RETRY_TOTAL


class TestAuthMethod:
    """Tests for AuthMethod enum."""

    def test_basic_auth(self) -> None:
        assert AuthMethod.BASIC.value == "basic"

    def test_token_auth(self) -> None:
        assert AuthMethod.TOKEN.value == "token"


class TestBuildAuthHeader:
    """Tests for build_auth_header function."""

    def test_basic_auth_header(self) -> None:
        header = build_auth_header(AuthMethod.BASIC, username="admin", password="secret")
        # Base64 of "admin:secret" is "YWRtaW46c2VjcmV0"
        assert header == {"Authorization": "Basic YWRtaW46c2VjcmV0"}

    def test_token_auth_header(self) -> None:
        header = build_auth_header(AuthMethod.TOKEN, token="my-api-token")
        assert header == {"Authorization": "Bearer my-api-token"}

    def test_basic_auth_requires_username(self) -> None:
        with pytest.raises(ValueError, match="Username and password required"):
            build_auth_header(AuthMethod.BASIC, password="secret")

    def test_basic_auth_requires_password(self) -> None:
        with pytest.raises(ValueError, match="Username and password required"):
            build_auth_header(AuthMethod.BASIC, username="admin")

    def test_token_auth_requires_token(self) -> None:
        with pytest.raises(ValueError, match="Token required"):
            build_auth_header(AuthMethod.TOKEN)

    def test_special_characters_in_password(self) -> None:
        # Test with special characters that need proper encoding
        header = build_auth_header(AuthMethod.BASIC, username="admin", password="p@ss:word!")
        assert "Authorization" in header
        assert header["Authorization"].startswith("Basic ")


class TestVergeConnection:
    """Tests for VergeConnection dataclass."""

    def test_api_base_url_construction(self) -> None:
        conn = VergeConnection(host="192.168.1.100")
        assert conn.api_base_url == "https://192.168.1.100/api/v4"

    def test_api_base_url_with_hostname(self) -> None:
        conn = VergeConnection(host="verge.example.com")
        assert conn.api_base_url == "https://verge.example.com/api/v4"

    def test_default_values(self) -> None:
        conn = VergeConnection(host="test.local")
        assert conn.username == ""
        assert conn.token is None
        assert conn.token_expires is None
        assert conn.verify_ssl is True
        assert conn.connected_at is None
        assert conn.vergeos_version is None
        assert conn.is_connected is False

    def test_session_created(self) -> None:
        conn = VergeConnection(host="test.local")
        assert conn.session is not None

    def test_ssl_verification_disabled(self) -> None:
        conn = VergeConnection(host="test.local", verify_ssl=False)
        assert conn.session is not None
        assert conn.session.verify is False

    def test_disconnect_clears_state(self) -> None:
        conn = VergeConnection(host="test.local")
        conn.token = "some-token"
        conn.token_expires = datetime.now(timezone.utc)
        conn.connected_at = datetime.now(timezone.utc)
        conn.is_connected = True

        conn.disconnect()

        assert conn.token is None
        assert conn.token_expires is None
        assert conn.connected_at is None
        assert conn.is_connected is False

    def test_is_token_valid_when_not_connected(self) -> None:
        conn = VergeConnection(host="test.local")
        assert not conn.is_token_valid()

    def test_is_token_valid_when_connected(self) -> None:
        conn = VergeConnection(host="test.local")
        conn.is_connected = True
        assert conn.is_token_valid()

    def test_is_token_valid_when_expired(self) -> None:
        conn = VergeConnection(host="test.local")
        conn.is_connected = True
        conn.token_expires = datetime.now(timezone.utc) - timedelta(hours=1)
        assert not conn.is_token_valid()

    def test_is_token_valid_when_not_expired(self) -> None:
        conn = VergeConnection(host="test.local")
        conn.is_connected = True
        conn.token_expires = datetime.now(timezone.utc) + timedelta(hours=1)
        assert conn.is_token_valid()


class TestVergeConnectionRetryConfig:
    """Tests for VergeConnection retry configuration."""

    def test_default_retry_values(self) -> None:
        conn = VergeConnection(host="test.local")
        assert conn.retry_total == RETRY_TOTAL
        assert conn.retry_backoff_factor == RETRY_BACKOFF_FACTOR
        assert conn.retry_status_codes == RETRY_STATUS_CODES

    def test_custom_retry_total(self) -> None:
        conn = VergeConnection(host="test.local", retry_total=5)
        assert conn.retry_total == 5

    def test_custom_retry_backoff_factor(self) -> None:
        conn = VergeConnection(host="test.local", retry_backoff_factor=2.0)
        assert conn.retry_backoff_factor == 2.0

    def test_custom_retry_status_codes(self) -> None:
        custom_codes = frozenset({HTTPStatus.BAD_GATEWAY, HTTPStatus.GATEWAY_TIMEOUT})
        conn = VergeConnection(host="test.local", retry_status_codes=custom_codes)
        assert conn.retry_status_codes == custom_codes

    def test_retry_status_codes_generator_is_normalized(self) -> None:
        retry_status_codes = (
            status for status in (HTTPStatus.BAD_GATEWAY, HTTPStatus.GATEWAY_TIMEOUT)
        )

        conn = VergeConnection(host="test.local", retry_status_codes=retry_status_codes)

        assert conn.retry_status_codes == frozenset(
            {HTTPStatus.BAD_GATEWAY, HTTPStatus.GATEWAY_TIMEOUT}
        )

    def test_retry_disabled_with_zero_total(self) -> None:
        conn = VergeConnection(host="test.local", retry_total=0)
        assert conn.retry_total == 0

    def test_all_retry_params_together(self) -> None:
        custom_codes = frozenset({HTTPStatus.SERVICE_UNAVAILABLE})
        conn = VergeConnection(
            host="test.local",
            retry_total=10,
            retry_backoff_factor=0.5,
            retry_status_codes=custom_codes,
        )
        assert conn.retry_total == 10
        assert conn.retry_backoff_factor == 0.5
        assert conn.retry_status_codes == custom_codes


class TestVergeConnectionByoSession:
    """Tests for caller-supplied session behavior."""

    def _session(self) -> MagicMock:
        session = MagicMock(spec=requests.Session)
        session.headers = CaseInsensitiveDict()
        return session

    def test_byo_session_is_public_field_and_not_reconfigured(self) -> None:
        session = self._session()

        conn = VergeConnection(host="test.local", session=session)

        assert conn.session is session
        session.mount.assert_not_called()
        assert "verify" not in session.__dict__

    def test_byo_verify_ssl_false_warns_without_mutating_session(self) -> None:
        session = self._session()

        with (
            patch("pyvergeos.connection.warnings.filterwarnings") as filterwarnings,
            pytest.warns(UserWarning, match="verify_ssl"),
        ):
            VergeConnection(host="test.local", session=session, verify_ssl=False)

        filterwarnings.assert_not_called()
        assert "verify" not in session.__dict__

    @pytest.mark.parametrize(
        ("kwargs", "expected"),
        [
            ({"retry_total": RETRY_TOTAL + 1}, "retry_total"),
            ({"retry_backoff_factor": RETRY_BACKOFF_FACTOR + 1}, "retry_backoff_factor"),
            ({"retry_status_codes": frozenset({HTTPStatus.BAD_GATEWAY})}, "retry_status_codes"),
        ],
    )
    def test_byo_ignored_config_warns(self, kwargs: dict[str, object], expected: str) -> None:
        session = self._session()

        with pytest.warns(UserWarning, match=expected):
            VergeConnection(host="test.local", session=session, **kwargs)

    def test_byo_ignored_config_warns_with_joined_config_names(self) -> None:
        session = self._session()

        with pytest.warns(
            UserWarning,
            match="retry_total, retry_backoff_factor, retry_status_codes, verify_ssl",
        ):
            VergeConnection(
                host="test.local",
                session=session,
                retry_total=RETRY_TOTAL + 1,
                retry_backoff_factor=RETRY_BACKOFF_FACTOR + 1,
                retry_status_codes=frozenset({HTTPStatus.BAD_GATEWAY}),
                verify_ssl=False,
            )

    def test_byo_disconnect_does_not_close_by_default(self) -> None:
        session = self._session()
        conn = VergeConnection(host="test.local", session=session)

        conn.disconnect()

        session.close.assert_not_called()

    def test_byo_disconnect_closes_when_requested(self) -> None:
        session = self._session()
        conn = VergeConnection(host="test.local", session=session, close_session=True)

        conn.disconnect()

        session.close.assert_called_once_with()

    def test_owned_close_session_false_requires_byo_session(self) -> None:
        with pytest.raises(ValueError, match="close_session=False"):
            VergeConnection(host="test.local", close_session=False)

    def test_apply_auth_headers_snapshots_byo_headers(self) -> None:
        session = self._session()
        session.headers = CaseInsensitiveDict(
            {
                "Authorization": "Bearer caller-token",
                "Accept": "text/plain",
            }
        )
        conn = VergeConnection(host="test.local", session=session)

        conn.apply_auth_headers(
            {
                "Authorization": "Bearer verge-token",
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
        )

        assert session.headers["Authorization"] == "Bearer verge-token"
        assert session.headers["Content-Type"] == "application/json"
        assert session.headers["Accept"] == "application/json"

        conn.disconnect()

        assert session.headers["Authorization"] == "Bearer caller-token"
        assert "Content-Type" not in session.headers
        assert session.headers["Accept"] == "text/plain"
        assert conn._pre_connect_headers is None

    def test_apply_auth_headers_preserves_original_snapshot(self) -> None:
        session = self._session()
        session.headers = CaseInsensitiveDict({"Authorization": "Bearer caller-token"})
        conn = VergeConnection(host="test.local", session=session)

        conn.apply_auth_headers({"Authorization": "Bearer verge-token-1"})
        conn.apply_auth_headers({"Authorization": "Bearer verge-token-2"})

        assert session.headers["Authorization"] == "Bearer verge-token-2"

        conn.disconnect()

        assert session.headers["Authorization"] == "Bearer caller-token"
        assert conn._pre_connect_headers is None

    def test_apply_auth_headers_resets_snapshot_between_byo_cycles(self) -> None:
        session = self._session()
        session.headers = CaseInsensitiveDict({"aUtHoRiZaTiOn": "Bearer caller-token"})
        conn = VergeConnection(host="test.local", session=session)

        conn.apply_auth_headers({"Authorization": "Bearer verge-token-1"})
        conn.disconnect()

        assert conn._pre_connect_headers is None
        assert dict(session.headers.items()) == {"aUtHoRiZaTiOn": "Bearer caller-token"}

        session.headers["aUtHoRiZaTiOn"] = "Bearer caller-token-2"
        conn.apply_auth_headers({"Authorization": "Bearer verge-token-2"})
        conn.disconnect()

        assert conn._pre_connect_headers is None
        assert dict(session.headers.items()) == {"aUtHoRiZaTiOn": "Bearer caller-token-2"}

    def test_disconnect_restores_byo_headers(self) -> None:
        session = self._session()
        session.headers = CaseInsensitiveDict(
            {
                "Authorization": "Bearer caller-token",
                "Accept": "text/plain",
                "Content-Type": "text/plain",
            }
        )
        conn = VergeConnection(host="test.local", session=session)
        conn._pre_connect_headers = {
            "Authorization": ("Authorization", "Bearer caller-token"),
            "Accept": ("Accept", "text/plain"),
            "Content-Type": ("Content-Type", None),
        }
        session.headers.update(
            {
                "Authorization": "Basic verge-token",
                "Accept": "application/json",
                "Content-Type": "application/json",
            }
        )

        conn.disconnect()

        assert session.headers["Authorization"] == "Bearer caller-token"
        assert session.headers["Accept"] == "text/plain"
        assert "Content-Type" not in session.headers
        assert conn._pre_connect_headers is None

    def test_disconnect_header_restore_missing_key_is_idempotent(self) -> None:
        session = self._session()
        conn = VergeConnection(host="test.local", session=session)
        conn._pre_connect_headers = {"Authorization": ("Authorization", None)}

        conn.disconnect()

        assert "Authorization" not in session.headers
        assert conn._pre_connect_headers is None
