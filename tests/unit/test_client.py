"""Tests for VergeClient."""

from unittest.mock import MagicMock

import pytest

from pyvergeos import VergeClient
from pyvergeos.exceptions import NotConnectedError


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
