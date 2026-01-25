"""Tests for connection module."""

from datetime import UTC, datetime, timedelta

import pytest

from pyvergeos.connection import AuthMethod, VergeConnection, build_auth_header


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
        assert conn._session is not None

    def test_ssl_verification_disabled(self) -> None:
        conn = VergeConnection(host="test.local", verify_ssl=False)
        assert conn._session.verify is False

    def test_disconnect_clears_state(self) -> None:
        conn = VergeConnection(host="test.local")
        conn.token = "some-token"
        conn.token_expires = datetime.now(UTC)
        conn.connected_at = datetime.now(UTC)
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
        conn.token_expires = datetime.now(UTC) - timedelta(hours=1)
        assert not conn.is_token_valid()

    def test_is_token_valid_when_not_expired(self) -> None:
        conn = VergeConnection(host="test.local")
        conn.is_connected = True
        conn.token_expires = datetime.now(UTC) + timedelta(hours=1)
        assert conn.is_token_valid()
