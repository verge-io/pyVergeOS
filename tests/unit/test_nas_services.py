"""Unit tests for NAS service operations."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from pyvergeos import VergeClient
from pyvergeos.exceptions import NotFoundError
from pyvergeos.resources.nas_services import (
    CIFSSettings,
    NASService,
    NASServiceManager,
    NFSSettings,
)


class TestNASServiceManager:
    """Unit tests for NASServiceManager."""

    def test_list_services(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test listing NAS services."""
        mock_session.request.return_value.json.return_value = [
            {
                "$key": 1,
                "name": "NAS01",
                "vm": 100,
                "vm_status": "running",
                "vm_running": True,
                "volume_count": 5,
            },
            {
                "$key": 2,
                "name": "NAS02",
                "vm": 101,
                "vm_status": "stopped",
                "vm_running": False,
                "volume_count": 3,
            },
        ]

        services = mock_client.nas_services.list()

        assert len(services) == 2
        assert services[0].name == "NAS01"
        assert services[1].name == "NAS02"

    def test_list_services_empty(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test listing when no NAS services exist."""
        mock_session.request.return_value.json.return_value = None

        services = mock_client.nas_services.list()

        assert services == []

    def test_list_services_by_status(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test filtering services by status."""
        mock_session.request.return_value.json.return_value = [
            {
                "$key": 1,
                "name": "NAS01",
                "vm_status": "running",
                "vm_running": True,
            },
            {
                "$key": 2,
                "name": "NAS02",
                "vm_status": "stopped",
                "vm_running": False,
            },
        ]

        running = mock_client.nas_services.list(status="running")

        assert len(running) == 1
        assert running[0].name == "NAS01"

    def test_list_running(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test list_running helper method."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "name": "NAS01", "vm_status": "running", "vm_running": True},
        ]

        running = mock_client.nas_services.list_running()

        assert len(running) == 1
        assert running[0].is_running is True

    def test_list_stopped(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test list_stopped helper method."""
        mock_session.request.return_value.json.return_value = [
            {"$key": 1, "name": "NAS01", "vm_status": "stopped", "vm_running": False},
        ]

        stopped = mock_client.nas_services.list_stopped()

        assert len(stopped) == 1
        assert stopped[0].is_running is False

    def test_get_service_by_key(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test getting a NAS service by key."""
        mock_session.request.return_value.json.return_value = {
            "$key": 1,
            "name": "NAS01",
            "vm": 100,
            "vm_status": "running",
        }

        service = mock_client.nas_services.get(1)

        assert service.key == 1
        assert service.name == "NAS01"

    def test_get_service_by_name(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test getting a NAS service by name."""
        mock_session.request.return_value.json.return_value = [
            {
                "$key": 2,
                "name": "FileServer",
                "vm": 101,
            }
        ]

        service = mock_client.nas_services.get(name="FileServer")

        assert service.name == "FileServer"
        assert service.key == 2

    def test_get_service_not_found_by_key(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test NotFoundError when service not found by key."""
        mock_session.request.return_value.json.return_value = None

        with pytest.raises(NotFoundError):
            mock_client.nas_services.get(999)

    def test_get_service_not_found_by_name(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test NotFoundError when service not found by name."""
        mock_session.request.return_value.json.return_value = []

        with pytest.raises(NotFoundError):
            mock_client.nas_services.get(name="nonexistent")

    def test_get_service_requires_key_or_name(self, mock_client: VergeClient) -> None:
        """Test ValueError when neither key nor name provided."""
        with pytest.raises(ValueError, match="Either key or name must be provided"):
            mock_client.nas_services.get()

    def test_update_service(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test updating a NAS service."""
        # Calls: get current service, update service, get updated service
        # (no VM update since we're only updating service settings)
        mock_session.request.return_value.json.side_effect = [
            {"$key": 1, "name": "NAS01", "vm": 100, "max_imports": 3},  # GET service
            {},  # PUT service update response
            {"$key": 1, "name": "NAS01", "vm": 100, "max_imports": 5},  # GET updated
        ]

        _ = mock_client.nas_services.update(1, max_imports=5, max_syncs=3)

        # Verify PUT was called with correct body
        put_calls = [
            call
            for call in mock_session.request.call_args_list
            if call.kwargs.get("method") == "PUT"
        ]
        assert len(put_calls) == 1
        body = put_calls[0].kwargs.get("json", {})
        assert body.get("max_imports") == 5
        assert body.get("max_syncs") == 3

    def test_delete_service_running_raises(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test that deleting a running service raises ValueError."""
        mock_session.request.return_value.json.return_value = {
            "$key": 1,
            "name": "NAS01",
            "vm": 100,
            "vm_status": "running",
            "vm_running": True,
            "volume_count": 0,
        }

        with pytest.raises(ValueError, match="Service is running"):
            mock_client.nas_services.delete(1)

    def test_delete_service_with_volumes_raises(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test that deleting service with volumes raises ValueError without force."""
        mock_session.request.return_value.json.return_value = {
            "$key": 1,
            "name": "NAS01",
            "vm": 100,
            "vm_status": "stopped",
            "vm_running": False,
            "volume_count": 5,
        }

        with pytest.raises(ValueError, match="has 5 volume"):
            mock_client.nas_services.delete(1)

    def test_delete_service_force(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test force deleting a service with volumes."""
        mock_session.request.return_value.json.return_value = {
            "$key": 1,
            "name": "NAS01",
            "vm": 100,
            "vm_status": "stopped",
            "vm_running": False,
            "volume_count": 5,
        }

        # Should not raise with force=True
        mock_client.nas_services.delete(1, force=True)

        delete_calls = [
            call
            for call in mock_session.request.call_args_list
            if call.kwargs.get("method") == "DELETE"
        ]
        assert len(delete_calls) == 1

    def test_power_on(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test powering on a NAS service."""
        mock_session.request.return_value.json.side_effect = [
            {"$key": 1, "name": "NAS01", "vm": 100},
            {"task": 123},
        ]

        result = mock_client.nas_services.power_on(1)

        assert result == {"task": 123}
        post_calls = [
            call
            for call in mock_session.request.call_args_list
            if call.kwargs.get("method") == "POST"
        ]
        assert any(call.kwargs.get("url", "").endswith("vm_actions") for call in post_calls)

    def test_power_off(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test powering off a NAS service."""
        mock_session.request.return_value.json.side_effect = [
            {"$key": 1, "name": "NAS01", "vm": 100},
            {"task": 124},
        ]

        result = mock_client.nas_services.power_off(1)

        assert result == {"task": 124}
        post_calls = [
            call
            for call in mock_session.request.call_args_list
            if call.kwargs.get("method") == "POST"
        ]
        assert any(call.kwargs.get("url", "").endswith("vm_actions") for call in post_calls)

    def test_power_off_force(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test force powering off a NAS service."""
        mock_session.request.return_value.json.side_effect = [
            {"$key": 1, "name": "NAS01", "vm": 100},
            {"task": 125},
        ]

        mock_client.nas_services.power_off(1, force=True)

        post_calls = [
            call
            for call in mock_session.request.call_args_list
            if call.kwargs.get("method") == "POST"
        ]
        assert any(call.kwargs.get("url", "").endswith("vm_actions") for call in post_calls)

    def test_restart(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test restarting a NAS service."""
        mock_session.request.return_value.json.side_effect = [
            {"$key": 1, "name": "NAS01", "vm": 100},
            {"task": 126},
        ]

        result = mock_client.nas_services.restart(1)

        assert result == {"task": 126}


class TestNASServiceCIFSSettings:
    """Tests for CIFS settings operations."""

    def test_get_cifs_settings(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test getting CIFS settings."""
        mock_session.request.return_value.json.return_value = [
            {
                "$key": 10,
                "service": 1,
                "workgroup": "WORKGROUP",
                "server_min_protocol": "SMB2",
                "map_to_guest": "never",
                "extended_acl_support": True,
            }
        ]

        cifs = mock_client.nas_services.get_cifs_settings(1)

        assert isinstance(cifs, CIFSSettings)
        assert cifs.get("workgroup") == "WORKGROUP"
        assert cifs.get("server_min_protocol") == "SMB2"

    def test_get_cifs_settings_not_found(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test NotFoundError when CIFS settings not found."""
        mock_session.request.return_value.json.return_value = []

        with pytest.raises(NotFoundError):
            mock_client.nas_services.get_cifs_settings(999)

    def test_set_cifs_settings(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test updating CIFS settings."""
        mock_session.request.return_value.json.side_effect = [
            [{"$key": 10, "service": 1, "workgroup": "WORKGROUP"}],
            {},  # PUT response
            [{"$key": 10, "service": 1, "workgroup": "newgroup"}],
        ]

        _ = mock_client.nas_services.set_cifs_settings(1, workgroup="NEWGROUP", min_protocol="SMB3")

        put_calls = [
            call
            for call in mock_session.request.call_args_list
            if call.kwargs.get("method") == "PUT"
        ]
        assert len(put_calls) == 1
        body = put_calls[0].kwargs.get("json", {})
        assert body["workgroup"] == "newgroup"
        assert body["server_min_protocol"] == "SMB3"


class TestNASServiceNFSSettings:
    """Tests for NFS settings operations."""

    def test_get_nfs_settings(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test getting NFS settings."""
        mock_session.request.return_value.json.return_value = [
            {
                "$key": 20,
                "service": 1,
                "enable_nfsv4": True,
                "allowed_hosts": "192.168.1.0/24",
                "squash": "root_squash",
                "data_access": "rw",
            }
        ]

        nfs = mock_client.nas_services.get_nfs_settings(1)

        assert isinstance(nfs, NFSSettings)
        assert nfs.get("enable_nfsv4") is True
        assert nfs.get("allowed_hosts") == "192.168.1.0/24"

    def test_get_nfs_settings_not_found(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test NotFoundError when NFS settings not found."""
        mock_session.request.return_value.json.return_value = []

        with pytest.raises(NotFoundError):
            mock_client.nas_services.get_nfs_settings(999)

    def test_set_nfs_settings(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """Test updating NFS settings."""
        mock_session.request.return_value.json.side_effect = [
            [{"$key": 20, "service": 1, "enable_nfsv4": False}],
            {},  # PUT response
            [{"$key": 20, "service": 1, "enable_nfsv4": True}],
        ]

        _ = mock_client.nas_services.set_nfs_settings(
            1, enable_nfsv4=True, allowed_hosts="10.0.0.0/8"
        )

        put_calls = [
            call
            for call in mock_session.request.call_args_list
            if call.kwargs.get("method") == "PUT"
        ]
        assert len(put_calls) == 1
        body = put_calls[0].kwargs.get("json", {})
        assert body["enable_nfsv4"] is True
        assert body["allowed_hosts"] == "10.0.0.0/8"

    def test_set_nfs_settings_squash_mapping(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Test that squash values are mapped correctly."""
        mock_session.request.return_value.json.side_effect = [
            [{"$key": 20, "service": 1}],
            {},
            [{"$key": 20, "service": 1, "squash": "no_root_squash"}],
        ]

        mock_client.nas_services.set_nfs_settings(1, squash="no_squash")

        put_calls = [
            call
            for call in mock_session.request.call_args_list
            if call.kwargs.get("method") == "PUT"
        ]
        body = put_calls[0].kwargs.get("json", {})
        assert body["squash"] == "no_root_squash"


class TestNASService:
    """Unit tests for NASService object."""

    @pytest.fixture
    def service_data(self) -> dict[str, Any]:
        """Sample NAS service data."""
        return {
            "$key": 1,
            "name": "NAS01",
            "vm": 100,
            "vm_name": "NAS01-VM",
            "vm_status": "running",
            "vm_running": True,
            "vm_cores": 4,
            "vm_ram": 8192,
            "max_imports": 5,
            "max_syncs": 3,
            "disable_swap": False,
            "read_ahead_kb_default": 256,
            "cifs": 10,
            "nfs": 20,
            "volume_count": 5,
        }

    @pytest.fixture
    def mock_manager(self, mock_client: VergeClient) -> NASServiceManager:
        """Create a mock NAS service manager."""
        return mock_client.nas_services

    def test_service_properties(
        self, service_data: dict[str, Any], mock_manager: NASServiceManager
    ) -> None:
        """Test NASService property accessors."""
        service = NASService(service_data, mock_manager)

        assert service.key == 1
        assert service.name == "NAS01"
        assert service.vm_key == 100
        assert service.volume_count == 5
        assert service.is_running is True

    def test_service_is_running_false(
        self, service_data: dict[str, Any], mock_manager: NASServiceManager
    ) -> None:
        """Test is_running when service is stopped."""
        service_data["vm_running"] = False
        service_data["vm_status"] = "stopped"
        service = NASService(service_data, mock_manager)

        assert service.is_running is False

    def test_service_vm_key_none(self, mock_manager: NASServiceManager) -> None:
        """Test vm_key when no VM is associated."""
        service = NASService({"$key": 1, "name": "NAS01"}, mock_manager)

        assert service.vm_key is None

    def test_service_volume_count_default(self, mock_manager: NASServiceManager) -> None:
        """Test volume_count default value."""
        service = NASService({"$key": 1, "name": "NAS01"}, mock_manager)

        assert service.volume_count == 0
