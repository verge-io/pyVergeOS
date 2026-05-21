"""Tests for VergeClient."""

from http import HTTPStatus
from unittest.mock import MagicMock

import pytest
import requests

from pyvergeos import VergeClient
from pyvergeos.constants import RETRY_BACKOFF_FACTOR, RETRY_STATUS_CODES, RETRY_TOTAL
from pyvergeos.exceptions import AuthenticationError, NotConnectedError, VergeConnectionError


class TestVergeClient:
    """Tests for VergeClient class."""

    def test_init_with_username_password(self, mock_session: MagicMock) -> None:
        mock_session.request.return_value.json.return_value = {
            "$key": 1,
            "yb_version": "4.12.0",
        }

        client = VergeClient(
            host="test.example.com",
            username="admin",
            password="secret",
        )

        assert client.is_connected
        assert client.host == "test.example.com"
        client.disconnect()

    def test_init_with_token(self, mock_session: MagicMock) -> None:
        mock_session.request.return_value.json.return_value = {
            "$key": 1,
            "yb_version": "4.12.0",
        }

        client = VergeClient(
            host="test.example.com",
            token="api-token-here",
        )

        assert client.is_connected
        client.disconnect()

    def test_init_without_credentials_raises(self) -> None:
        with pytest.raises(ValueError, match="Either token or username/password"):
            VergeClient(host="test.example.com", auto_connect=True)

    def test_auto_connect_false(self) -> None:
        client = VergeClient(
            host="test.example.com",
            username="admin",
            password="secret",
            auto_connect=False,
        )

        assert not client.is_connected
        # No disconnect needed since never connected

    def test_context_manager(self, mock_session: MagicMock) -> None:
        mock_session.request.return_value.json.return_value = {
            "$key": 1,
            "yb_version": "4.12.0",
        }

        with VergeClient(
            host="test.example.com",
            username="admin",
            password="secret",
        ) as client:
            assert client.is_connected

        assert not client.is_connected

    def test_version_property(self, mock_client: VergeClient) -> None:
        assert mock_client.version == "4.12.0"

    def test_disconnect(self, mock_client: VergeClient) -> None:
        assert mock_client.is_connected
        mock_client.disconnect()
        assert not mock_client.is_connected

    def test_request_when_not_connected(self) -> None:
        client = VergeClient(
            host="test.example.com",
            username="admin",
            password="secret",
            auto_connect=False,
        )

        with pytest.raises(NotConnectedError):
            client._request("GET", "vms")


class TestVergeClientByoSession:
    """Tests for caller-supplied session wiring."""

    def _session(self, status_code: int = 200) -> MagicMock:
        response = MagicMock()
        response.status_code = status_code
        response.text = "{}"
        response.json.return_value = {
            "$key": 1,
            "yb_version": "4.12.0",
            "os_version": "26.0",
            "cloud_name": "test-cloud",
        }

        session = MagicMock(spec=requests.Session)
        session.headers = {}
        session.request.return_value = response
        return session

    def test_constructor_stores_session_config(self) -> None:
        session = self._session()

        client = VergeClient(
            host="test.example.com",
            username="admin",
            password="secret",
            session=session,
            close_session=True,
            auto_connect=False,
        )

        assert client._session is session
        assert client._close_session is True

    def test_connect_forwards_session_to_connection(self) -> None:
        session = self._session()
        client = VergeClient(
            host="test.example.com",
            username="admin",
            password="secret",
            session=session,
            auto_connect=False,
        )

        client.connect()

        assert client._connection is not None
        assert client._connection.session is session
        client.disconnect()

    def test_reconnect_uses_same_byo_session(self) -> None:
        session = self._session()
        client = VergeClient(
            host="test.example.com",
            username="admin",
            password="secret",
            session=session,
            auto_connect=False,
        )

        client.connect()
        client.disconnect()
        client.connect()

        assert client._connection is not None
        assert client._connection.session is session
        client.disconnect()

    def test_connect_twice_restores_byo_headers_before_reconnecting(self) -> None:
        session = self._session()
        session.headers = {
            "Authorization": "Bearer caller-token",
            "Content-Type": "text/plain",
            "Accept": "text/plain",
        }
        client = VergeClient(
            host="test.example.com",
            token="verge-token",
            session=session,
            auto_connect=False,
        )

        client.connect()
        assert session.headers["Authorization"] == "Bearer verge-token"

        client.connect()
        assert session.headers["Authorization"] == "Bearer verge-token"

        client.disconnect()

        assert session.headers["Authorization"] == "Bearer caller-token"
        assert session.headers["Content-Type"] == "text/plain"
        assert session.headers["Accept"] == "text/plain"
        session.close.assert_not_called()

    def test_byo_disconnect_does_not_close_session(self) -> None:
        session = self._session()
        client = VergeClient(
            host="test.example.com",
            username="admin",
            password="secret",
            session=session,
        )

        client.disconnect()

        session.close.assert_not_called()

    def test_byo_disconnect_restores_absent_headers(self) -> None:
        session = self._session()
        client = VergeClient(
            host="test.example.com",
            username="admin",
            password="secret",
            session=session,
        )

        assert "Authorization" in session.headers
        assert "Content-Type" in session.headers
        assert "Accept" in session.headers

        client.disconnect()

        assert "Authorization" not in session.headers
        assert "Content-Type" not in session.headers
        assert "Accept" not in session.headers

    def test_byo_disconnect_restores_present_headers(self) -> None:
        session = self._session()
        session.headers = {
            "Authorization": "Bearer caller-token",
            "Content-Type": "text/plain",
            "Accept": "text/plain",
        }
        client = VergeClient(
            host="test.example.com",
            token="verge-token",
            session=session,
        )

        assert session.headers["Authorization"] == "Bearer verge-token"
        assert session.headers["Content-Type"] == "application/json"
        assert session.headers["Accept"] == "application/json"

        client.disconnect()

        assert session.headers["Authorization"] == "Bearer caller-token"
        assert session.headers["Content-Type"] == "text/plain"
        assert session.headers["Accept"] == "text/plain"

    def test_failed_connect_cleans_up_byo_headers_and_state(self) -> None:
        session = self._session(status_code=HTTPStatus.UNAUTHORIZED)
        session.request.return_value.json.return_value = {"err": "invalid credentials"}
        client = VergeClient(
            host="test.example.com",
            username="admin",
            password="secret",
            session=session,
            auto_connect=False,
        )

        with pytest.raises(AuthenticationError):
            client.connect()

        assert client._connection is None
        assert "Authorization" not in session.headers
        assert "Content-Type" not in session.headers
        assert "Accept" not in session.headers
        session.close.assert_not_called()

    def test_failed_connect_closes_owned_session_and_clears_state(
        self, mock_session: MagicMock
    ) -> None:
        mock_session.request.return_value.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
        mock_session.request.return_value.text = "server error"
        client = VergeClient(
            host="test.example.com",
            username="admin",
            password="secret",
            auto_connect=False,
        )

        with pytest.raises(VergeConnectionError):
            client.connect()

        assert client._connection is None
        mock_session.close.assert_called_once_with()

    def test_default_session_config_is_legacy_owned_path(self, mock_session: MagicMock) -> None:
        mock_session.request.return_value.json.return_value = {
            "$key": 1,
            "yb_version": "4.12.0",
        }
        client = VergeClient(
            host="test.example.com",
            username="admin",
            password="secret",
            auto_connect=False,
        )

        assert client._session is None
        client.connect()

        assert client._connection is not None
        assert client._connection._pre_connect_headers is None
        client.disconnect()
        mock_session.close.assert_called_once_with()


class TestVergeClientResourceManagers:
    """Tests for resource manager properties."""

    def test_vms_property(self, mock_client: VergeClient) -> None:
        vms = mock_client.vms
        assert vms is not None
        # Same instance returned on second access
        assert mock_client.vms is vms

    def test_networks_property(self, mock_client: VergeClient) -> None:
        networks = mock_client.networks
        assert networks is not None
        assert mock_client.networks is networks

    def test_tenants_property(self, mock_client: VergeClient) -> None:
        tenants = mock_client.tenants
        assert tenants is not None

    def test_users_property(self, mock_client: VergeClient) -> None:
        users = mock_client.users
        assert users is not None

    def test_tasks_property(self, mock_client: VergeClient) -> None:
        tasks = mock_client.tasks
        assert tasks is not None


class TestVergeClientRetryConfig:
    """Tests for VergeClient retry configuration."""

    def test_default_retry_values(self, mock_session: MagicMock) -> None:
        mock_session.request.return_value.json.return_value = {
            "$key": 1,
            "yb_version": "4.12.0",
        }

        client = VergeClient(
            host="test.example.com",
            username="admin",
            password="secret",
        )

        assert client._retry_total == RETRY_TOTAL
        assert client._retry_backoff_factor == RETRY_BACKOFF_FACTOR
        assert client._retry_status_codes == RETRY_STATUS_CODES
        client.disconnect()

    def test_custom_retry_total(self, mock_session: MagicMock) -> None:
        mock_session.request.return_value.json.return_value = {
            "$key": 1,
            "yb_version": "4.12.0",
        }

        client = VergeClient(
            host="test.example.com",
            username="admin",
            password="secret",
            retry_total=5,
        )

        assert client._retry_total == 5
        assert client._connection is not None
        assert client._connection.retry_total == 5
        client.disconnect()

    def test_custom_retry_backoff_factor(self, mock_session: MagicMock) -> None:
        mock_session.request.return_value.json.return_value = {
            "$key": 1,
            "yb_version": "4.12.0",
        }

        client = VergeClient(
            host="test.example.com",
            username="admin",
            password="secret",
            retry_backoff_factor=2.0,
        )

        assert client._retry_backoff_factor == 2.0
        assert client._connection is not None
        assert client._connection.retry_backoff_factor == 2.0
        client.disconnect()

    def test_custom_retry_status_codes(self, mock_session: MagicMock) -> None:
        mock_session.request.return_value.json.return_value = {
            "$key": 1,
            "yb_version": "4.12.0",
        }

        custom_codes = frozenset({HTTPStatus.BAD_GATEWAY, HTTPStatus.GATEWAY_TIMEOUT})
        client = VergeClient(
            host="test.example.com",
            username="admin",
            password="secret",
            retry_status_codes=custom_codes,
        )

        assert client._retry_status_codes == custom_codes
        assert client._connection is not None
        assert set(client._connection.retry_status_codes) == set(custom_codes)
        client.disconnect()

    def test_retry_disabled(self, mock_session: MagicMock) -> None:
        mock_session.request.return_value.json.return_value = {
            "$key": 1,
            "yb_version": "4.12.0",
        }

        client = VergeClient(
            host="test.example.com",
            username="admin",
            password="secret",
            retry_total=0,
        )

        assert client._retry_total == 0
        assert client._connection is not None
        assert client._connection.retry_total == 0
        client.disconnect()

    def test_all_retry_params_together(self, mock_session: MagicMock) -> None:
        mock_session.request.return_value.json.return_value = {
            "$key": 1,
            "yb_version": "4.12.0",
        }

        custom_codes = frozenset({HTTPStatus.SERVICE_UNAVAILABLE})
        client = VergeClient(
            host="test.example.com",
            username="admin",
            password="secret",
            retry_total=10,
            retry_backoff_factor=0.5,
            retry_status_codes=custom_codes,
        )

        assert client._retry_total == 10
        assert client._retry_backoff_factor == 0.5
        assert client._retry_status_codes == custom_codes
        assert client._connection is not None
        assert client._connection.retry_total == 10
        assert client._connection.retry_backoff_factor == 0.5
        client.disconnect()

    def test_retry_params_preserved_on_reconnect(self, mock_session: MagicMock) -> None:
        mock_session.request.return_value.json.return_value = {
            "$key": 1,
            "yb_version": "4.12.0",
        }

        client = VergeClient(
            host="test.example.com",
            username="admin",
            password="secret",
            retry_total=7,
            auto_connect=False,
        )

        # First connect
        client.connect()
        assert client._connection is not None
        assert client._connection.retry_total == 7

        # Disconnect and reconnect
        client.disconnect()
        client.connect()
        assert client._connection is not None
        assert client._connection.retry_total == 7
        client.disconnect()
