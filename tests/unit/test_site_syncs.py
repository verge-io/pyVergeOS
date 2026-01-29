"""Unit tests for site sync resource managers."""

from __future__ import annotations

from datetime import timedelta
from typing import Any
from unittest.mock import MagicMock

import pytest

from pyvergeos.resources.site_syncs import (
    SiteSyncIncoming,
    SiteSyncIncomingManager,
    SiteSyncOutgoing,
    SiteSyncOutgoingManager,
    SiteSyncSchedule,
    SiteSyncScheduleManager,
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_client() -> MagicMock:
    """Create a mock VergeClient."""
    client = MagicMock()
    client._request = MagicMock()
    client.sites = MagicMock()
    client.site_syncs = MagicMock()
    return client


@pytest.fixture
def outgoing_manager(mock_client: MagicMock) -> SiteSyncOutgoingManager:
    """Create an outgoing sync manager with mock client."""
    return SiteSyncOutgoingManager(mock_client)


@pytest.fixture
def incoming_manager(mock_client: MagicMock) -> SiteSyncIncomingManager:
    """Create an incoming sync manager with mock client."""
    return SiteSyncIncomingManager(mock_client)


@pytest.fixture
def schedule_manager(mock_client: MagicMock) -> SiteSyncScheduleManager:
    """Create a schedule manager with mock client."""
    return SiteSyncScheduleManager(mock_client)


@pytest.fixture
def sample_outgoing_sync_data() -> dict[str, Any]:
    """Sample outgoing sync data."""
    return {
        "$key": 1,
        "site": 2,
        "name": "Test Sync",
        "description": "Test description",
        "enabled": True,
        "status": "offline",
        "status_info": "",
        "state": "offline",
        "url": "https://remote.example.com",
        "encryption": True,
        "compression": True,
        "netinteg": True,
        "threads": 8,
        "file_threads": 4,
        "sendthrottle": 0,
        "destination_tier": "unspecified",
        "queue_retry_count": 10,
        "queue_retry_interval_seconds": 60,
        "queue_retry_interval_multiplier": True,
        "last_run": 1706500000,
        "remote_min_snapshots": 1,
        "note": "Test note",
    }


@pytest.fixture
def sample_incoming_sync_data() -> dict[str, Any]:
    """Sample incoming sync data."""
    return {
        "$key": 1,
        "site": 2,
        "name": "Incoming Sync",
        "description": "Incoming description",
        "enabled": True,
        "status": "offline",
        "status_info": "",
        "state": "offline",
        "sync_id": "abc123def456",
        "registration_code": "REG123456",
        "public_ip": "192.168.1.100",
        "force_tier": "unspecified",
        "min_snapshots": 1,
        "last_sync": 1706500000,
        "vsan_host": "vsan.example.com",
        "vsan_port": 14201,
        "request_url": "https://local.example.com",
        "system_created": False,
    }


@pytest.fixture
def sample_schedule_data() -> dict[str, Any]:
    """Sample schedule data."""
    return {
        "$key": 1,
        "site_syncs_outgoing": 2,
        "profile_period": 3,
        "retention": 604800,
        "priority": 0,
        "do_not_expire": False,
        "destination_prefix": "remote",
    }


# ============================================================================
# SiteSyncOutgoing Tests
# ============================================================================


class TestSiteSyncOutgoing:
    """Tests for SiteSyncOutgoing resource object."""

    def test_properties(
        self, outgoing_manager: SiteSyncOutgoingManager, sample_outgoing_sync_data: dict[str, Any]
    ) -> None:
        """Test all properties return correct values."""
        sync = SiteSyncOutgoing(sample_outgoing_sync_data, outgoing_manager)

        assert sync.key == 1
        assert sync.site_key == 2
        assert sync.name == "Test Sync"
        assert sync.description == "Test description"
        assert sync.is_enabled is True
        assert sync.status == "offline"
        assert sync.status_info == ""
        assert sync.state == "offline"
        assert sync.is_syncing is False
        assert sync.is_online is False
        assert sync.has_error is False
        assert sync.url == "https://remote.example.com"
        assert sync.has_encryption is True
        assert sync.has_compression is True
        assert sync.has_network_integrity is True
        assert sync.data_threads == 8
        assert sync.file_threads == 4
        assert sync.send_throttle == 0
        assert sync.destination_tier == "unspecified"
        assert sync.queue_retry_count == 10
        assert sync.queue_retry_interval == 60
        assert sync.has_retry_multiplier is True
        assert sync.remote_min_snapshots == 1
        assert sync.note == "Test note"
        assert sync.last_run_at is not None

    def test_is_syncing_true(
        self, outgoing_manager: SiteSyncOutgoingManager, sample_outgoing_sync_data: dict[str, Any]
    ) -> None:
        """Test is_syncing returns True when status is syncing."""
        data = {**sample_outgoing_sync_data, "status": "syncing"}
        sync = SiteSyncOutgoing(data, outgoing_manager)
        assert sync.is_syncing is True

    def test_is_online_true(
        self, outgoing_manager: SiteSyncOutgoingManager, sample_outgoing_sync_data: dict[str, Any]
    ) -> None:
        """Test is_online returns True when state is online."""
        data = {**sample_outgoing_sync_data, "state": "online"}
        sync = SiteSyncOutgoing(data, outgoing_manager)
        assert sync.is_online is True

    def test_has_error_status(
        self, outgoing_manager: SiteSyncOutgoingManager, sample_outgoing_sync_data: dict[str, Any]
    ) -> None:
        """Test has_error returns True when status is error."""
        data = {**sample_outgoing_sync_data, "status": "error"}
        sync = SiteSyncOutgoing(data, outgoing_manager)
        assert sync.has_error is True

    def test_has_error_state(
        self, outgoing_manager: SiteSyncOutgoingManager, sample_outgoing_sync_data: dict[str, Any]
    ) -> None:
        """Test has_error returns True when state is error."""
        data = {**sample_outgoing_sync_data, "state": "error"}
        sync = SiteSyncOutgoing(data, outgoing_manager)
        assert sync.has_error is True

    def test_last_run_at_none(
        self, outgoing_manager: SiteSyncOutgoingManager, sample_outgoing_sync_data: dict[str, Any]
    ) -> None:
        """Test last_run_at returns None when not set."""
        data = {**sample_outgoing_sync_data, "last_run": 0}
        sync = SiteSyncOutgoing(data, outgoing_manager)
        assert sync.last_run_at is None

    def test_repr(
        self, outgoing_manager: SiteSyncOutgoingManager, sample_outgoing_sync_data: dict[str, Any]
    ) -> None:
        """Test string representation."""
        sync = SiteSyncOutgoing(sample_outgoing_sync_data, outgoing_manager)
        assert "SiteSyncOutgoing" in repr(sync)
        assert "key=1" in repr(sync)
        assert "Test Sync" in repr(sync)


# ============================================================================
# SiteSyncOutgoingManager Tests
# ============================================================================


class TestSiteSyncOutgoingManager:
    """Tests for SiteSyncOutgoingManager."""

    def test_list_empty(self, outgoing_manager: SiteSyncOutgoingManager) -> None:
        """Test list returns empty list when no syncs."""
        outgoing_manager._client._request.return_value = None
        result = outgoing_manager.list()
        assert result == []

    def test_list_single(
        self,
        outgoing_manager: SiteSyncOutgoingManager,
        sample_outgoing_sync_data: dict[str, Any],
    ) -> None:
        """Test list returns single sync."""
        outgoing_manager._client._request.return_value = sample_outgoing_sync_data
        result = outgoing_manager.list()
        assert len(result) == 1
        assert isinstance(result[0], SiteSyncOutgoing)
        assert result[0].name == "Test Sync"

    def test_list_multiple(
        self,
        outgoing_manager: SiteSyncOutgoingManager,
        sample_outgoing_sync_data: dict[str, Any],
    ) -> None:
        """Test list returns multiple syncs."""
        data2 = {**sample_outgoing_sync_data, "$key": 2, "name": "Another Sync"}
        outgoing_manager._client._request.return_value = [sample_outgoing_sync_data, data2]
        result = outgoing_manager.list()
        assert len(result) == 2
        assert result[0].key == 1
        assert result[1].key == 2

    def test_list_with_site_key_filter(
        self,
        outgoing_manager: SiteSyncOutgoingManager,
        sample_outgoing_sync_data: dict[str, Any],
    ) -> None:
        """Test list with site_key filter."""
        outgoing_manager._client._request.return_value = [sample_outgoing_sync_data]
        outgoing_manager.list(site_key=2)

        call_args = outgoing_manager._client._request.call_args
        assert "site eq 2" in call_args[1]["params"]["filter"]

    def test_list_with_site_name_filter(
        self,
        outgoing_manager: SiteSyncOutgoingManager,
        sample_outgoing_sync_data: dict[str, Any],
    ) -> None:
        """Test list with site_name filter resolves to site_key."""
        mock_site = MagicMock()
        mock_site.key = 2
        outgoing_manager._client.sites.get.return_value = mock_site
        outgoing_manager._client._request.return_value = [sample_outgoing_sync_data]

        outgoing_manager.list(site_name="Test Site")

        outgoing_manager._client.sites.get.assert_called_once_with(name="Test Site")
        call_args = outgoing_manager._client._request.call_args
        assert "site eq 2" in call_args[1]["params"]["filter"]

    def test_list_with_enabled_filter(
        self,
        outgoing_manager: SiteSyncOutgoingManager,
        sample_outgoing_sync_data: dict[str, Any],
    ) -> None:
        """Test list with enabled filter."""
        outgoing_manager._client._request.return_value = [sample_outgoing_sync_data]
        outgoing_manager.list(enabled=True)

        call_args = outgoing_manager._client._request.call_args
        assert "enabled eq true" in call_args[1]["params"]["filter"]

    def test_list_enabled(
        self,
        outgoing_manager: SiteSyncOutgoingManager,
        sample_outgoing_sync_data: dict[str, Any],
    ) -> None:
        """Test list_enabled helper method."""
        outgoing_manager._client._request.return_value = [sample_outgoing_sync_data]
        outgoing_manager.list_enabled()

        call_args = outgoing_manager._client._request.call_args
        assert "enabled eq true" in call_args[1]["params"]["filter"]

    def test_list_disabled(
        self,
        outgoing_manager: SiteSyncOutgoingManager,
        sample_outgoing_sync_data: dict[str, Any],
    ) -> None:
        """Test list_disabled helper method."""
        outgoing_manager._client._request.return_value = []
        outgoing_manager.list_disabled()

        call_args = outgoing_manager._client._request.call_args
        assert "enabled eq false" in call_args[1]["params"]["filter"]

    def test_get_by_key(
        self,
        outgoing_manager: SiteSyncOutgoingManager,
        sample_outgoing_sync_data: dict[str, Any],
    ) -> None:
        """Test get by key."""
        outgoing_manager._client._request.return_value = sample_outgoing_sync_data
        result = outgoing_manager.get(1)

        assert isinstance(result, SiteSyncOutgoing)
        assert result.key == 1
        outgoing_manager._client._request.assert_called_once()

    def test_get_by_name(
        self,
        outgoing_manager: SiteSyncOutgoingManager,
        sample_outgoing_sync_data: dict[str, Any],
    ) -> None:
        """Test get by name."""
        outgoing_manager._client._request.return_value = [sample_outgoing_sync_data]
        result = outgoing_manager.get(name="Test Sync")

        assert isinstance(result, SiteSyncOutgoing)
        assert result.name == "Test Sync"

    def test_get_not_found(self, outgoing_manager: SiteSyncOutgoingManager) -> None:
        """Test get raises NotFoundError when not found."""
        from pyvergeos.exceptions import NotFoundError

        outgoing_manager._client._request.return_value = None
        with pytest.raises(NotFoundError):
            outgoing_manager.get(999)

    def test_get_no_key_or_name(self, outgoing_manager: SiteSyncOutgoingManager) -> None:
        """Test get raises ValueError when no key or name."""
        with pytest.raises(ValueError, match="Either key or name must be provided"):
            outgoing_manager.get()

    def test_enable(
        self,
        outgoing_manager: SiteSyncOutgoingManager,
        sample_outgoing_sync_data: dict[str, Any],
    ) -> None:
        """Test enable sync."""
        outgoing_manager._client._request.side_effect = [
            None,  # Action response
            sample_outgoing_sync_data,  # Get response
        ]
        result = outgoing_manager.enable(1)

        # Check action was called correctly
        action_call = outgoing_manager._client._request.call_args_list[0]
        assert action_call[0] == ("POST", "site_syncs_outgoing_actions")
        assert action_call[1]["json_data"]["action"] == "enable"
        assert action_call[1]["json_data"]["site_syncs_outgoing"] == 1

        assert isinstance(result, SiteSyncOutgoing)

    def test_disable(
        self,
        outgoing_manager: SiteSyncOutgoingManager,
        sample_outgoing_sync_data: dict[str, Any],
    ) -> None:
        """Test disable sync."""
        outgoing_manager._client._request.side_effect = [
            None,  # Action response
            sample_outgoing_sync_data,  # Get response
        ]
        result = outgoing_manager.disable(1)

        action_call = outgoing_manager._client._request.call_args_list[0]
        assert action_call[1]["json_data"]["action"] == "disable"

        assert isinstance(result, SiteSyncOutgoing)

    def test_start_alias(
        self,
        outgoing_manager: SiteSyncOutgoingManager,
        sample_outgoing_sync_data: dict[str, Any],
    ) -> None:
        """Test start is alias for enable."""
        outgoing_manager._client._request.side_effect = [
            None,
            sample_outgoing_sync_data,
        ]
        result = outgoing_manager.start(1)

        action_call = outgoing_manager._client._request.call_args_list[0]
        assert action_call[1]["json_data"]["action"] == "enable"

        assert isinstance(result, SiteSyncOutgoing)

    def test_stop_alias(
        self,
        outgoing_manager: SiteSyncOutgoingManager,
        sample_outgoing_sync_data: dict[str, Any],
    ) -> None:
        """Test stop is alias for disable."""
        outgoing_manager._client._request.side_effect = [
            None,
            sample_outgoing_sync_data,
        ]
        result = outgoing_manager.stop(1)

        action_call = outgoing_manager._client._request.call_args_list[0]
        assert action_call[1]["json_data"]["action"] == "disable"

        assert isinstance(result, SiteSyncOutgoing)

    def test_add_to_queue(self, outgoing_manager: SiteSyncOutgoingManager) -> None:
        """Test add_to_queue."""
        outgoing_manager._client._request.return_value = None
        outgoing_manager.add_to_queue(
            sync_key=1,
            snapshot_key=5,
            retention=259200,
            priority=0,
            do_not_expire=False,
            destination_prefix="test",
        )

        call_args = outgoing_manager._client._request.call_args
        assert call_args[0] == ("POST", "site_syncs_outgoing_actions")
        body = call_args[1]["json_data"]
        assert body["action"] == "add_to_queue"
        assert body["site_syncs_outgoing"] == 1
        assert body["params"]["cloud_snapshot"] == 5
        assert body["params"]["retention"] == 259200
        assert body["params"]["priority"] == 0
        assert body["params"]["do_not_expire"] is False
        assert body["params"]["destination_prefix"] == "test"

    def test_add_to_queue_with_timedelta(self, outgoing_manager: SiteSyncOutgoingManager) -> None:
        """Test add_to_queue with timedelta retention."""
        outgoing_manager._client._request.return_value = None
        outgoing_manager.add_to_queue(
            sync_key=1,
            snapshot_key=5,
            retention=timedelta(days=3),
        )

        call_args = outgoing_manager._client._request.call_args
        body = call_args[1]["json_data"]
        assert body["params"]["retention"] == 259200  # 3 days in seconds

    def test_add_to_queue_negative_retention(
        self, outgoing_manager: SiteSyncOutgoingManager
    ) -> None:
        """Test add_to_queue raises error for negative retention."""
        from pyvergeos.exceptions import ValidationError

        with pytest.raises(ValidationError, match="Retention must be positive"):
            outgoing_manager.add_to_queue(sync_key=1, snapshot_key=5, retention=-1)

    def test_invoke_alias(self, outgoing_manager: SiteSyncOutgoingManager) -> None:
        """Test invoke is alias for add_to_queue."""
        outgoing_manager._client._request.return_value = None
        outgoing_manager.invoke(sync_key=1, snapshot_key=5, retention=259200)

        call_args = outgoing_manager._client._request.call_args
        assert call_args[1]["json_data"]["action"] == "add_to_queue"

    def test_set_throttle(
        self,
        outgoing_manager: SiteSyncOutgoingManager,
        sample_outgoing_sync_data: dict[str, Any],
    ) -> None:
        """Test set_throttle."""
        outgoing_manager._client._request.side_effect = [
            None,
            sample_outgoing_sync_data,
        ]
        result = outgoing_manager.set_throttle(1, 1000000)

        action_call = outgoing_manager._client._request.call_args_list[0]
        assert action_call[1]["json_data"]["action"] == "throttle_sync"
        assert action_call[1]["json_data"]["params"]["throttle"] == 1000000

        assert isinstance(result, SiteSyncOutgoing)

    def test_disable_throttle(
        self,
        outgoing_manager: SiteSyncOutgoingManager,
        sample_outgoing_sync_data: dict[str, Any],
    ) -> None:
        """Test disable_throttle sets throttle to 0."""
        outgoing_manager._client._request.side_effect = [
            None,
            sample_outgoing_sync_data,
        ]
        result = outgoing_manager.disable_throttle(1)

        action_call = outgoing_manager._client._request.call_args_list[0]
        assert action_call[1]["json_data"]["params"]["throttle"] == 0

        assert isinstance(result, SiteSyncOutgoing)

    def test_refresh_remote_snapshots(
        self,
        outgoing_manager: SiteSyncOutgoingManager,
        sample_outgoing_sync_data: dict[str, Any],
    ) -> None:
        """Test refresh_remote_snapshots."""
        outgoing_manager._client._request.side_effect = [
            None,
            sample_outgoing_sync_data,
        ]
        result = outgoing_manager.refresh_remote_snapshots(1)

        action_call = outgoing_manager._client._request.call_args_list[0]
        assert action_call[1]["json_data"]["action"] == "refresh"

        assert isinstance(result, SiteSyncOutgoing)


# ============================================================================
# SiteSyncIncoming Tests
# ============================================================================


class TestSiteSyncIncoming:
    """Tests for SiteSyncIncoming resource object."""

    def test_properties(
        self, incoming_manager: SiteSyncIncomingManager, sample_incoming_sync_data: dict[str, Any]
    ) -> None:
        """Test all properties return correct values."""
        sync = SiteSyncIncoming(sample_incoming_sync_data, incoming_manager)

        assert sync.key == 1
        assert sync.site_key == 2
        assert sync.name == "Incoming Sync"
        assert sync.description == "Incoming description"
        assert sync.is_enabled is True
        assert sync.status == "offline"
        assert sync.status_info == ""
        assert sync.state == "offline"
        assert sync.is_syncing is False
        assert sync.is_online is False
        assert sync.has_error is False
        assert sync.sync_id == "abc123def456"
        assert sync.registration_code == "REG123456"
        assert sync.public_ip == "192.168.1.100"
        assert sync.force_tier == "unspecified"
        assert sync.min_snapshots == 1
        assert sync.vsan_host == "vsan.example.com"
        assert sync.vsan_port == 14201
        assert sync.request_url == "https://local.example.com"
        assert sync.is_system_created is False
        assert sync.last_sync_at is not None

    def test_is_syncing_true(
        self, incoming_manager: SiteSyncIncomingManager, sample_incoming_sync_data: dict[str, Any]
    ) -> None:
        """Test is_syncing returns True when status is syncing."""
        data = {**sample_incoming_sync_data, "status": "syncing"}
        sync = SiteSyncIncoming(data, incoming_manager)
        assert sync.is_syncing is True

    def test_last_sync_at_none(
        self, incoming_manager: SiteSyncIncomingManager, sample_incoming_sync_data: dict[str, Any]
    ) -> None:
        """Test last_sync_at returns None when not set."""
        data = {**sample_incoming_sync_data, "last_sync": 0}
        sync = SiteSyncIncoming(data, incoming_manager)
        assert sync.last_sync_at is None

    def test_repr(
        self, incoming_manager: SiteSyncIncomingManager, sample_incoming_sync_data: dict[str, Any]
    ) -> None:
        """Test string representation."""
        sync = SiteSyncIncoming(sample_incoming_sync_data, incoming_manager)
        assert "SiteSyncIncoming" in repr(sync)
        assert "key=1" in repr(sync)
        assert "Incoming Sync" in repr(sync)


# ============================================================================
# SiteSyncIncomingManager Tests
# ============================================================================


class TestSiteSyncIncomingManager:
    """Tests for SiteSyncIncomingManager."""

    def test_list_empty(self, incoming_manager: SiteSyncIncomingManager) -> None:
        """Test list returns empty list when no syncs."""
        incoming_manager._client._request.return_value = None
        result = incoming_manager.list()
        assert result == []

    def test_list_single(
        self,
        incoming_manager: SiteSyncIncomingManager,
        sample_incoming_sync_data: dict[str, Any],
    ) -> None:
        """Test list returns single sync."""
        incoming_manager._client._request.return_value = sample_incoming_sync_data
        result = incoming_manager.list()
        assert len(result) == 1
        assert isinstance(result[0], SiteSyncIncoming)

    def test_list_with_site_key_filter(
        self,
        incoming_manager: SiteSyncIncomingManager,
        sample_incoming_sync_data: dict[str, Any],
    ) -> None:
        """Test list with site_key filter."""
        incoming_manager._client._request.return_value = [sample_incoming_sync_data]
        incoming_manager.list(site_key=2)

        call_args = incoming_manager._client._request.call_args
        assert "site eq 2" in call_args[1]["params"]["filter"]

    def test_get_by_key(
        self,
        incoming_manager: SiteSyncIncomingManager,
        sample_incoming_sync_data: dict[str, Any],
    ) -> None:
        """Test get by key."""
        incoming_manager._client._request.return_value = sample_incoming_sync_data
        result = incoming_manager.get(1)

        assert isinstance(result, SiteSyncIncoming)
        assert result.key == 1

    def test_get_by_name(
        self,
        incoming_manager: SiteSyncIncomingManager,
        sample_incoming_sync_data: dict[str, Any],
    ) -> None:
        """Test get by name."""
        incoming_manager._client._request.return_value = [sample_incoming_sync_data]
        result = incoming_manager.get(name="Incoming Sync")

        assert isinstance(result, SiteSyncIncoming)
        assert result.name == "Incoming Sync"

    def test_enable(
        self,
        incoming_manager: SiteSyncIncomingManager,
        sample_incoming_sync_data: dict[str, Any],
    ) -> None:
        """Test enable sync."""
        incoming_manager._client._request.side_effect = [
            None,
            sample_incoming_sync_data,
        ]
        result = incoming_manager.enable(1)

        action_call = incoming_manager._client._request.call_args_list[0]
        assert action_call[0] == ("POST", "site_syncs_incoming_actions")
        assert action_call[1]["json_data"]["action"] == "enable"
        assert action_call[1]["json_data"]["site_syncs_incoming"] == 1

        assert isinstance(result, SiteSyncIncoming)

    def test_disable(
        self,
        incoming_manager: SiteSyncIncomingManager,
        sample_incoming_sync_data: dict[str, Any],
    ) -> None:
        """Test disable sync."""
        incoming_manager._client._request.side_effect = [
            None,
            sample_incoming_sync_data,
        ]
        result = incoming_manager.disable(1)

        action_call = incoming_manager._client._request.call_args_list[0]
        assert action_call[1]["json_data"]["action"] == "disable"

        assert isinstance(result, SiteSyncIncoming)


# ============================================================================
# SiteSyncSchedule Tests
# ============================================================================


class TestSiteSyncSchedule:
    """Tests for SiteSyncSchedule resource object."""

    def test_properties(
        self, schedule_manager: SiteSyncScheduleManager, sample_schedule_data: dict[str, Any]
    ) -> None:
        """Test all properties return correct values."""
        schedule = SiteSyncSchedule(sample_schedule_data, schedule_manager)

        assert schedule.key == 1
        assert schedule.sync_key == 2
        assert schedule.profile_period_key == 3
        assert schedule.retention == 604800
        assert schedule.retention_timedelta == timedelta(days=7)
        assert schedule.priority == 0
        assert schedule.do_not_expire is False
        assert schedule.destination_prefix == "remote"

    def test_repr(
        self, schedule_manager: SiteSyncScheduleManager, sample_schedule_data: dict[str, Any]
    ) -> None:
        """Test string representation."""
        schedule = SiteSyncSchedule(sample_schedule_data, schedule_manager)
        assert "SiteSyncSchedule" in repr(schedule)
        assert "key=1" in repr(schedule)
        assert "sync=2" in repr(schedule)
        assert "period=3" in repr(schedule)


# ============================================================================
# SiteSyncScheduleManager Tests
# ============================================================================


class TestSiteSyncScheduleManager:
    """Tests for SiteSyncScheduleManager."""

    def test_list_empty(self, schedule_manager: SiteSyncScheduleManager) -> None:
        """Test list returns empty list when no schedules."""
        schedule_manager._client._request.return_value = None
        result = schedule_manager.list()
        assert result == []

    def test_list_single(
        self,
        schedule_manager: SiteSyncScheduleManager,
        sample_schedule_data: dict[str, Any],
    ) -> None:
        """Test list returns single schedule."""
        schedule_manager._client._request.return_value = sample_schedule_data
        result = schedule_manager.list()
        assert len(result) == 1
        assert isinstance(result[0], SiteSyncSchedule)

    def test_list_with_sync_key_filter(
        self,
        schedule_manager: SiteSyncScheduleManager,
        sample_schedule_data: dict[str, Any],
    ) -> None:
        """Test list with sync_key filter."""
        schedule_manager._client._request.return_value = [sample_schedule_data]
        schedule_manager.list(sync_key=2)

        call_args = schedule_manager._client._request.call_args
        assert "site_syncs_outgoing eq 2" in call_args[1]["params"]["filter"]

    def test_list_with_sync_name_filter(
        self,
        schedule_manager: SiteSyncScheduleManager,
        sample_schedule_data: dict[str, Any],
    ) -> None:
        """Test list with sync_name filter resolves to sync_key."""
        mock_sync = MagicMock()
        mock_sync.key = 2
        schedule_manager._client.site_syncs.get.return_value = mock_sync
        schedule_manager._client._request.return_value = [sample_schedule_data]

        schedule_manager.list(sync_name="Test Sync")

        schedule_manager._client.site_syncs.get.assert_called_once_with(name="Test Sync")

    def test_list_for_sync(
        self,
        schedule_manager: SiteSyncScheduleManager,
        sample_schedule_data: dict[str, Any],
    ) -> None:
        """Test list_for_sync helper method."""
        schedule_manager._client._request.return_value = [sample_schedule_data]
        schedule_manager.list_for_sync(sync_key=2)

        call_args = schedule_manager._client._request.call_args
        assert "site_syncs_outgoing eq 2" in call_args[1]["params"]["filter"]

    def test_get(
        self,
        schedule_manager: SiteSyncScheduleManager,
        sample_schedule_data: dict[str, Any],
    ) -> None:
        """Test get by key."""
        schedule_manager._client._request.return_value = sample_schedule_data
        result = schedule_manager.get(1)

        assert isinstance(result, SiteSyncSchedule)
        assert result.key == 1

    def test_get_not_found(self, schedule_manager: SiteSyncScheduleManager) -> None:
        """Test get raises NotFoundError when not found."""
        from pyvergeos.exceptions import NotFoundError

        schedule_manager._client._request.return_value = None
        with pytest.raises(NotFoundError):
            schedule_manager.get(999)

    def test_create(
        self,
        schedule_manager: SiteSyncScheduleManager,
        sample_schedule_data: dict[str, Any],
    ) -> None:
        """Test create schedule."""
        schedule_manager._client._request.side_effect = [
            {"$key": 1},
            sample_schedule_data,
        ]
        result = schedule_manager.create(
            sync_key=2,
            profile_period_key=3,
            retention=604800,
            priority=0,
            do_not_expire=False,
            destination_prefix="remote",
        )

        create_call = schedule_manager._client._request.call_args_list[0]
        assert create_call[0] == ("POST", "site_syncs_outgoing_profile_periods")
        body = create_call[1]["json_data"]
        assert body["site_syncs_outgoing"] == 2
        assert body["profile_period"] == 3
        assert body["retention"] == 604800
        assert body["priority"] == 0
        assert body["do_not_expire"] is False
        assert body["destination_prefix"] == "remote"

        assert isinstance(result, SiteSyncSchedule)

    def test_create_with_timedelta(
        self,
        schedule_manager: SiteSyncScheduleManager,
        sample_schedule_data: dict[str, Any],
    ) -> None:
        """Test create schedule with timedelta retention."""
        schedule_manager._client._request.side_effect = [
            {"$key": 1},
            sample_schedule_data,
        ]
        schedule_manager.create(
            sync_key=2,
            profile_period_key=3,
            retention=timedelta(days=7),
        )

        create_call = schedule_manager._client._request.call_args_list[0]
        assert create_call[1]["json_data"]["retention"] == 604800

    def test_create_negative_retention(self, schedule_manager: SiteSyncScheduleManager) -> None:
        """Test create raises error for negative retention."""
        from pyvergeos.exceptions import ValidationError

        with pytest.raises(ValidationError, match="Retention must be positive"):
            schedule_manager.create(
                sync_key=2,
                profile_period_key=3,
                retention=-1,
            )

    def test_create_without_priority(
        self,
        schedule_manager: SiteSyncScheduleManager,
        sample_schedule_data: dict[str, Any],
    ) -> None:
        """Test create without priority (auto-assigned)."""
        schedule_manager._client._request.side_effect = [
            {"$key": 1},
            sample_schedule_data,
        ]
        schedule_manager.create(
            sync_key=2,
            profile_period_key=3,
            retention=604800,
        )

        create_call = schedule_manager._client._request.call_args_list[0]
        assert "priority" not in create_call[1]["json_data"]

    def test_delete(self, schedule_manager: SiteSyncScheduleManager) -> None:
        """Test delete schedule."""
        schedule_manager._client._request.return_value = None
        schedule_manager.delete(1)

        schedule_manager._client._request.assert_called_once_with(
            "DELETE", "site_syncs_outgoing_profile_periods/1"
        )


# ============================================================================
# Object Method Tests
# ============================================================================


class TestObjectMethods:
    """Tests for object methods on resource objects."""

    def test_outgoing_sync_enable(
        self,
        outgoing_manager: SiteSyncOutgoingManager,
        sample_outgoing_sync_data: dict[str, Any],
    ) -> None:
        """Test enable via object method."""
        sync = SiteSyncOutgoing(sample_outgoing_sync_data, outgoing_manager)
        outgoing_manager._client._request.side_effect = [
            None,
            sample_outgoing_sync_data,
        ]
        result = sync.enable()

        assert isinstance(result, SiteSyncOutgoing)

    def test_outgoing_sync_disable(
        self,
        outgoing_manager: SiteSyncOutgoingManager,
        sample_outgoing_sync_data: dict[str, Any],
    ) -> None:
        """Test disable via object method."""
        sync = SiteSyncOutgoing(sample_outgoing_sync_data, outgoing_manager)
        outgoing_manager._client._request.side_effect = [
            None,
            sample_outgoing_sync_data,
        ]
        result = sync.disable()

        assert isinstance(result, SiteSyncOutgoing)

    def test_outgoing_sync_start(
        self,
        outgoing_manager: SiteSyncOutgoingManager,
        sample_outgoing_sync_data: dict[str, Any],
    ) -> None:
        """Test start via object method."""
        sync = SiteSyncOutgoing(sample_outgoing_sync_data, outgoing_manager)
        outgoing_manager._client._request.side_effect = [
            None,
            sample_outgoing_sync_data,
        ]
        result = sync.start()

        assert isinstance(result, SiteSyncOutgoing)

    def test_outgoing_sync_stop(
        self,
        outgoing_manager: SiteSyncOutgoingManager,
        sample_outgoing_sync_data: dict[str, Any],
    ) -> None:
        """Test stop via object method."""
        sync = SiteSyncOutgoing(sample_outgoing_sync_data, outgoing_manager)
        outgoing_manager._client._request.side_effect = [
            None,
            sample_outgoing_sync_data,
        ]
        result = sync.stop()

        assert isinstance(result, SiteSyncOutgoing)

    def test_outgoing_sync_refresh(
        self,
        outgoing_manager: SiteSyncOutgoingManager,
        sample_outgoing_sync_data: dict[str, Any],
    ) -> None:
        """Test refresh via object method."""
        sync = SiteSyncOutgoing(sample_outgoing_sync_data, outgoing_manager)
        outgoing_manager._client._request.return_value = sample_outgoing_sync_data
        result = sync.refresh()

        assert isinstance(result, SiteSyncOutgoing)

    def test_outgoing_sync_add_to_queue(
        self,
        outgoing_manager: SiteSyncOutgoingManager,
        sample_outgoing_sync_data: dict[str, Any],
    ) -> None:
        """Test add_to_queue via object method."""
        sync = SiteSyncOutgoing(sample_outgoing_sync_data, outgoing_manager)
        outgoing_manager._client._request.return_value = None
        sync.add_to_queue(snapshot_key=5, retention=259200)

        call_args = outgoing_manager._client._request.call_args
        assert call_args[1]["json_data"]["site_syncs_outgoing"] == 1

    def test_incoming_sync_enable(
        self,
        incoming_manager: SiteSyncIncomingManager,
        sample_incoming_sync_data: dict[str, Any],
    ) -> None:
        """Test enable via object method."""
        sync = SiteSyncIncoming(sample_incoming_sync_data, incoming_manager)
        incoming_manager._client._request.side_effect = [
            None,
            sample_incoming_sync_data,
        ]
        result = sync.enable()

        assert isinstance(result, SiteSyncIncoming)

    def test_incoming_sync_disable(
        self,
        incoming_manager: SiteSyncIncomingManager,
        sample_incoming_sync_data: dict[str, Any],
    ) -> None:
        """Test disable via object method."""
        sync = SiteSyncIncoming(sample_incoming_sync_data, incoming_manager)
        incoming_manager._client._request.side_effect = [
            None,
            sample_incoming_sync_data,
        ]
        result = sync.disable()

        assert isinstance(result, SiteSyncIncoming)

    def test_incoming_sync_refresh(
        self,
        incoming_manager: SiteSyncIncomingManager,
        sample_incoming_sync_data: dict[str, Any],
    ) -> None:
        """Test refresh via object method."""
        sync = SiteSyncIncoming(sample_incoming_sync_data, incoming_manager)
        incoming_manager._client._request.return_value = sample_incoming_sync_data
        result = sync.refresh()

        assert isinstance(result, SiteSyncIncoming)

    def test_schedule_delete(
        self,
        schedule_manager: SiteSyncScheduleManager,
        sample_schedule_data: dict[str, Any],
    ) -> None:
        """Test delete via object method."""
        schedule = SiteSyncSchedule(sample_schedule_data, schedule_manager)
        schedule_manager._client._request.return_value = None
        schedule.delete()

        schedule_manager._client._request.assert_called_once_with(
            "DELETE", "site_syncs_outgoing_profile_periods/1"
        )
