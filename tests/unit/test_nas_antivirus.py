"""Unit tests for NAS antivirus management."""

from unittest.mock import MagicMock

import pytest

from pyvergeos import VergeClient
from pyvergeos.exceptions import NotFoundError
from pyvergeos.resources.nas_antivirus import (
    NasServiceAntivirus,
    NasServiceAntivirusManager,
    VolumeAntivirus,
    VolumeAntivirusInfection,
    VolumeAntivirusInfectionManager,
    VolumeAntivirusLog,
    VolumeAntivirusLogManager,
    VolumeAntivirusManager,
    VolumeAntivirusStats,
    VolumeAntivirusStatsManager,
    VolumeAntivirusStatus,
    VolumeAntivirusStatusManager,
)


@pytest.fixture
def mock_client():
    """Create a mock VergeClient."""
    client = MagicMock(spec=VergeClient)
    client._request = MagicMock()
    return client


@pytest.fixture
def volume_av_manager(mock_client):
    """Create a VolumeAntivirusManager with mock client."""
    return VolumeAntivirusManager(mock_client)


@pytest.fixture
def sample_volume_antivirus():
    """Sample volume antivirus data from API."""
    return {
        "$key": 1,
        "volume": "8f73f8bcc9c9f1aaba32f733bfc295acaf548554",
        "volume_display": "FileShare (500 GB)",
        "volume_name": "FileShare",
        "enabled": True,
        "infected_action": "move",
        "on_access": False,
        "scan": "entire",
        "include": "",
        "exclude": "/temp\n/cache",
        "quarantine_location": ".quarantine",
        "start_time_profile": None,
        "status": 10,
        "stats": 20,
    }


@pytest.fixture
def sample_av_status():
    """Sample antivirus status data from API."""
    return {
        "$key": 10,
        "volume_antivirus": 1,
        "status": "offline",
        "status_info": "Service ready",
        "state": "online",
        "last_update": 1700000000,
    }


@pytest.fixture
def sample_av_stats():
    """Sample antivirus stats data from API."""
    return {
        "$key": 20,
        "volume_antivirus": 1,
        "infected_files": 5,
        "quarantine_count": 3,
        "last_scan": 1700000000,
        "created": 1699900000,
    }


@pytest.fixture
def sample_av_infection():
    """Sample antivirus infection data from API."""
    return {
        "$key": 100,
        "volume_antivirus": 1,
        "filename": "/documents/infected.pdf",
        "virus": "Trojan.Generic",
        "action": "move",
        "timestamp": 1700000000000000,
    }


@pytest.fixture
def sample_av_log():
    """Sample antivirus log data from API."""
    return {
        "$key": 200,
        "volume_antivirus": 1,
        "level": "message",
        "text": "Scan started",
        "user": "admin",
        "timestamp": 1700000000000000,
    }


@pytest.fixture
def sample_service_antivirus():
    """Sample service antivirus data from API."""
    return {
        "$key": 1,
        "service": 1,
        "service_display": "NAS01",
        "enabled": True,
        "max_recursion": 15,
        "database_private_mirror": "",
        "database_location": "/var/lib/clamav",
        "database_updates_enabled": True,
    }


class TestVolumeAntivirus:
    """Tests for VolumeAntivirus model."""

    def test_volume_key_property(self, volume_av_manager, sample_volume_antivirus):
        """Test volume_key property returns string."""
        av = VolumeAntivirus(sample_volume_antivirus, volume_av_manager)
        assert av.volume_key == "8f73f8bcc9c9f1aaba32f733bfc295acaf548554"

    def test_enable_action(self, volume_av_manager, sample_volume_antivirus, mock_client):
        """Test enable() action method."""
        av = VolumeAntivirus(sample_volume_antivirus, volume_av_manager)
        mock_client._request.return_value = {"status": "success"}

        result = av.enable()

        mock_client._request.assert_called_once_with(
            "POST",
            "volume_antivirus_actions",
            json_data={"volume_antivirus": 1, "action": "enable"},
        )
        assert result == {"status": "success"}

    def test_disable_action(self, volume_av_manager, sample_volume_antivirus, mock_client):
        """Test disable() action method."""
        av = VolumeAntivirus(sample_volume_antivirus, volume_av_manager)
        mock_client._request.return_value = {"status": "success"}

        result = av.disable()

        mock_client._request.assert_called_once_with(
            "POST",
            "volume_antivirus_actions",
            json_data={"volume_antivirus": 1, "action": "disable"},
        )
        assert result == {"status": "success"}

    def test_start_scan_action(self, volume_av_manager, sample_volume_antivirus, mock_client):
        """Test start_scan() action method."""
        av = VolumeAntivirus(sample_volume_antivirus, volume_av_manager)
        mock_client._request.return_value = {"status": "success"}

        result = av.start_scan()

        mock_client._request.assert_called_once_with(
            "POST",
            "volume_antivirus_actions",
            json_data={"volume_antivirus": 1, "action": "start"},
        )
        assert result == {"status": "success"}

    def test_stop_scan_action(self, volume_av_manager, sample_volume_antivirus, mock_client):
        """Test stop_scan() action method."""
        av = VolumeAntivirus(sample_volume_antivirus, volume_av_manager)
        mock_client._request.return_value = {"status": "success"}

        result = av.stop_scan()

        mock_client._request.assert_called_once_with(
            "POST",
            "volume_antivirus_actions",
            json_data={"volume_antivirus": 1, "action": "stop"},
        )
        assert result == {"status": "success"}


class TestVolumeAntivirusStatus:
    """Tests for VolumeAntivirusStatus model."""

    def test_is_scanning_property(self, volume_av_manager, sample_av_status):
        """Test is_scanning property."""
        sample_av_status["status"] = "scanning"
        status = VolumeAntivirusStatus(sample_av_status, volume_av_manager)
        assert status.is_scanning is True

        sample_av_status["status"] = "offline"
        status = VolumeAntivirusStatus(sample_av_status, volume_av_manager)
        assert status.is_scanning is False

    def test_is_offline_property(self, volume_av_manager, sample_av_status):
        """Test is_offline property."""
        status = VolumeAntivirusStatus(sample_av_status, volume_av_manager)
        assert status.is_offline is True

    def test_has_error_property(self, volume_av_manager, sample_av_status):
        """Test has_error property."""
        sample_av_status["status"] = "error"
        status = VolumeAntivirusStatus(sample_av_status, volume_av_manager)
        assert status.has_error is True


class TestVolumeAntivirusStats:
    """Tests for VolumeAntivirusStats model."""

    def test_has_infections_property(self, volume_av_manager, sample_av_stats):
        """Test has_infections property."""
        stats = VolumeAntivirusStats(sample_av_stats, volume_av_manager)
        assert stats.has_infections is True

        sample_av_stats["infected_files"] = 0
        stats = VolumeAntivirusStats(sample_av_stats, volume_av_manager)
        assert stats.has_infections is False


class TestVolumeAntivirusManager:
    """Tests for VolumeAntivirusManager."""

    def test_list_all(self, volume_av_manager, sample_volume_antivirus, mock_client):
        """Test listing all volume antivirus configs."""
        mock_client._request.return_value = [sample_volume_antivirus]

        result = volume_av_manager.list()

        assert len(result) == 1
        assert isinstance(result[0], VolumeAntivirus)
        assert result[0].key == 1

    def test_list_with_volume_filter(self, volume_av_manager, sample_volume_antivirus, mock_client):
        """Test listing with volume filter."""
        mock_client._request.return_value = [sample_volume_antivirus]

        result = volume_av_manager.list(volume="8f73f8bcc9c9f1aaba32f733bfc295acaf548554")

        assert len(result) == 1
        mock_client._request.assert_called_once()
        call_args = mock_client._request.call_args
        assert (
            "volume eq '8f73f8bcc9c9f1aaba32f733bfc295acaf548554'"
            in call_args[1]["params"]["filter"]
        )

    def test_list_with_enabled_filter(
        self, volume_av_manager, sample_volume_antivirus, mock_client
    ):
        """Test listing with enabled filter."""
        mock_client._request.return_value = [sample_volume_antivirus]

        result = volume_av_manager.list(enabled=True)

        assert len(result) == 1
        mock_client._request.assert_called_once()
        call_args = mock_client._request.call_args
        assert "enabled eq 1" in call_args[1]["params"]["filter"]

    def test_get_by_key(self, volume_av_manager, sample_volume_antivirus, mock_client):
        """Test get by key."""
        mock_client._request.return_value = sample_volume_antivirus

        result = volume_av_manager.get(key=1)

        assert isinstance(result, VolumeAntivirus)
        assert result.key == 1
        mock_client._request.assert_called_once_with(
            "GET",
            "volume_antivirus/1",
            params={"fields": ",".join(volume_av_manager._default_fields)},
        )

    def test_get_by_volume(self, volume_av_manager, sample_volume_antivirus, mock_client):
        """Test get by volume key."""
        mock_client._request.return_value = [sample_volume_antivirus]

        result = volume_av_manager.get(volume="8f73f8bcc9c9f1aaba32f733bfc295acaf548554")

        assert isinstance(result, VolumeAntivirus)
        assert result.key == 1

    def test_get_not_found(self, volume_av_manager, mock_client):
        """Test get raises NotFoundError when not found."""
        mock_client._request.return_value = None

        with pytest.raises(NotFoundError):
            volume_av_manager.get(key=999)

    def test_create(self, volume_av_manager, sample_volume_antivirus, mock_client):
        """Test creating antivirus config."""
        mock_client._request.side_effect = [
            {"$key": 1},  # POST response
            sample_volume_antivirus,  # GET response
        ]

        result = volume_av_manager.create(
            volume="8f73f8bcc9c9f1aaba32f733bfc295acaf548554",
            enabled=True,
            on_access=True,
        )

        assert isinstance(result, VolumeAntivirus)
        assert result.key == 1
        # Verify POST call
        post_call = mock_client._request.call_args_list[0]
        assert post_call[0][0] == "POST"
        assert post_call[0][1] == "volume_antivirus"
        assert post_call[1]["json_data"]["enabled"] is True
        assert post_call[1]["json_data"]["on_access"] is True

    def test_update(self, volume_av_manager, sample_volume_antivirus, mock_client):
        """Test updating antivirus config."""
        updated_data = sample_volume_antivirus.copy()
        updated_data["on_access"] = True
        mock_client._request.side_effect = [
            None,  # PUT response
            updated_data,  # GET response
        ]

        result = volume_av_manager.update(1, on_access=True, quarantine_location="/custom")

        assert isinstance(result, VolumeAntivirus)
        # Verify PUT call
        put_call = mock_client._request.call_args_list[0]
        assert put_call[0][0] == "PUT"
        assert put_call[0][1] == "volume_antivirus/1"
        assert put_call[1]["json_data"]["on_access"] is True
        assert put_call[1]["json_data"]["quarantine_location"] == "/custom"

    def test_delete(self, volume_av_manager, mock_client):
        """Test deleting antivirus config."""
        mock_client._request.return_value = None

        volume_av_manager.delete(1)

        mock_client._request.assert_called_once_with("DELETE", "volume_antivirus/1")

    def test_action_method(self, volume_av_manager, mock_client):
        """Test _action helper method."""
        mock_client._request.return_value = {"status": "success"}

        result = volume_av_manager._action(1, "enable", {"param": "value"})

        assert result == {"status": "success"}
        mock_client._request.assert_called_once_with(
            "POST",
            "volume_antivirus_actions",
            json_data={"volume_antivirus": 1, "action": "enable", "params": {"param": "value"}},
        )


class TestVolumeAntivirusStatusManager:
    """Tests for VolumeAntivirusStatusManager."""

    def test_get_by_key(self, mock_client, sample_av_status):
        """Test get status by key."""
        manager = VolumeAntivirusStatusManager(mock_client)
        mock_client._request.return_value = sample_av_status

        result = manager.get(key=10)

        assert isinstance(result, VolumeAntivirusStatus)
        assert result.key == 10

    def test_get_by_antivirus_key(self, mock_client, sample_av_status):
        """Test get status by antivirus config key."""
        manager = VolumeAntivirusStatusManager(mock_client, antivirus_key=1)
        mock_client._request.return_value = [sample_av_status]

        result = manager.get()

        assert isinstance(result, VolumeAntivirusStatus)
        assert result.key == 10


class TestVolumeAntivirusStatsManager:
    """Tests for VolumeAntivirusStatsManager."""

    def test_get_by_key(self, mock_client, sample_av_stats):
        """Test get stats by key."""
        manager = VolumeAntivirusStatsManager(mock_client)
        mock_client._request.return_value = sample_av_stats

        result = manager.get(key=20)

        assert isinstance(result, VolumeAntivirusStats)
        assert result.key == 20

    def test_get_by_antivirus_key(self, mock_client, sample_av_stats):
        """Test get stats by antivirus config key."""
        manager = VolumeAntivirusStatsManager(mock_client, antivirus_key=1)
        mock_client._request.return_value = [sample_av_stats]

        result = manager.get()

        assert isinstance(result, VolumeAntivirusStats)
        assert result.key == 20


class TestVolumeAntivirusInfectionManager:
    """Tests for VolumeAntivirusInfectionManager."""

    def test_list_all(self, mock_client, sample_av_infection):
        """Test listing all infections."""
        manager = VolumeAntivirusInfectionManager(mock_client, antivirus_key=1)
        mock_client._request.return_value = [sample_av_infection]

        result = manager.list()

        assert len(result) == 1
        assert isinstance(result[0], VolumeAntivirusInfection)
        assert result[0].get("filename") == "/documents/infected.pdf"

    def test_list_scoped_to_antivirus(self, mock_client, sample_av_infection):
        """Test listing infections scoped to antivirus config."""
        manager = VolumeAntivirusInfectionManager(mock_client, antivirus_key=1)
        mock_client._request.return_value = [sample_av_infection]

        result = manager.list()

        assert len(result) == 1
        mock_client._request.assert_called_once()
        call_args = mock_client._request.call_args
        assert "volume_antivirus eq 1" in call_args[1]["params"]["filter"]


class TestVolumeAntivirusLogManager:
    """Tests for VolumeAntivirusLogManager."""

    def test_list_all(self, mock_client, sample_av_log):
        """Test listing all logs."""
        manager = VolumeAntivirusLogManager(mock_client, antivirus_key=1)
        mock_client._request.return_value = [sample_av_log]

        result = manager.list()

        assert len(result) == 1
        assert isinstance(result[0], VolumeAntivirusLog)
        assert result[0].get("text") == "Scan started"

    def test_list_with_level_filter(self, mock_client, sample_av_log):
        """Test listing logs with level filter."""
        manager = VolumeAntivirusLogManager(mock_client, antivirus_key=1)
        mock_client._request.return_value = [sample_av_log]

        result = manager.list(level="error")

        assert len(result) == 1
        mock_client._request.assert_called_once()
        call_args = mock_client._request.call_args
        assert "level eq 'error'" in call_args[1]["params"]["filter"]


class TestNasServiceAntivirus:
    """Tests for NasServiceAntivirus model."""

    def test_service_key_property(self, mock_client, sample_service_antivirus):
        """Test service_key property returns int."""
        manager = NasServiceAntivirusManager(mock_client)
        svc_av = NasServiceAntivirus(sample_service_antivirus, manager)
        assert svc_av.service_key == 1


class TestNasServiceAntivirusManager:
    """Tests for NasServiceAntivirusManager."""

    def test_get_by_key(self, mock_client, sample_service_antivirus):
        """Test get service antivirus by key."""
        manager = NasServiceAntivirusManager(mock_client)
        mock_client._request.return_value = sample_service_antivirus

        result = manager.get(key=1)

        assert isinstance(result, NasServiceAntivirus)
        assert result.key == 1

    def test_get_by_service_key(self, mock_client, sample_service_antivirus):
        """Test get service antivirus by service key."""
        manager = NasServiceAntivirusManager(mock_client, service_key=1)
        mock_client._request.return_value = [sample_service_antivirus]

        result = manager.get()

        assert isinstance(result, NasServiceAntivirus)
        assert result.key == 1

    def test_update(self, mock_client, sample_service_antivirus):
        """Test updating service antivirus config."""
        manager = NasServiceAntivirusManager(mock_client)
        updated_data = sample_service_antivirus.copy()
        updated_data["max_recursion"] = 20
        mock_client._request.side_effect = [
            None,  # PUT response
            updated_data,  # GET response
        ]

        result = manager.update(1, max_recursion=20, enabled=False)

        assert isinstance(result, NasServiceAntivirus)
        # Verify PUT call
        put_call = mock_client._request.call_args_list[0]
        assert put_call[0][0] == "PUT"
        assert put_call[0][1] == "vm_service_antivirus/1"
        assert put_call[1]["json_data"]["max_recursion"] == 20
        assert put_call[1]["json_data"]["enabled"] is False
