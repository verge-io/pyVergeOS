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


# ============================================================================
# SiteSyncStats Tests
# ============================================================================


@pytest.fixture
def sample_stats_data() -> dict[str, Any]:
    """Sample sync stats data."""
    return {
        "$key": 1,
        "parent": 2,
        "checked_bytes": 1073741824,
        "scanned_bytes": 536870912,
        "sent_bytes": 104857600,
        "sent_net_bytes": 52428800,
        "checked": "1.0 GB",
        "scanned": "512 MB",
        "sent": "100 MB",
        "sent_net": "50 MB",
        "dirs_checked": 100,
        "files_checked": 1500,
        "files_updated": 50,
        "last_run_time": 120000,
        "start_time": 1706500000,
        "stop_time": 1706500120,
        "error_time": 0,
        "last_error": "",
        "sendthrottle": 0,
        "retry_count": 0,
        "snapshot_name": "cloud-snap-2024-01-29",
        "last_retry_attempt": 0,
        "timestamp": 1706500120000000,
    }


class TestSiteSyncStats:
    """Tests for SiteSyncStats resource object."""

    def test_properties(self, sample_stats_data: dict[str, Any]) -> None:
        """Test all properties return correct values."""
        from pyvergeos.resources.site_syncs import SiteSyncStats

        stats = SiteSyncStats(sample_stats_data, None)

        assert stats.parent_key == 2
        assert stats.checked_bytes == 1073741824
        assert stats.scanned_bytes == 536870912
        assert stats.sent_bytes == 104857600
        assert stats.sent_net_bytes == 52428800
        assert stats.checked_display == "1.0 GB"
        assert stats.scanned_display == "512 MB"
        assert stats.sent_display == "100 MB"
        assert stats.sent_net_display == "50 MB"
        assert stats.dirs_checked == 100
        assert stats.files_checked == 1500
        assert stats.files_updated == 50
        assert stats.last_run_time_ms == 120000
        assert stats.last_run_time_seconds == 120.0
        assert stats.started_at is not None
        assert stats.stopped_at is not None
        assert stats.error_at is None
        assert stats.last_error == ""
        assert stats.has_error is False
        assert stats.send_throttle == 0
        assert stats.retry_count == 0
        assert stats.snapshot_name == "cloud-snap-2024-01-29"
        assert stats.last_retry_at is None

    def test_compression_ratio(self, sample_stats_data: dict[str, Any]) -> None:
        """Test compression ratio calculation."""
        from pyvergeos.resources.site_syncs import SiteSyncStats

        stats = SiteSyncStats(sample_stats_data, None)
        assert stats.compression_ratio == 2.0  # 100MB / 50MB

    def test_dedup_ratio(self, sample_stats_data: dict[str, Any]) -> None:
        """Test deduplication ratio calculation."""
        from pyvergeos.resources.site_syncs import SiteSyncStats

        stats = SiteSyncStats(sample_stats_data, None)
        # 1GB checked / 100MB sent = 10.24
        assert stats.dedup_ratio == pytest.approx(10.24, rel=0.01)

    def test_compression_ratio_zero_sent(self) -> None:
        """Test compression ratio returns 0 when no data sent."""
        from pyvergeos.resources.site_syncs import SiteSyncStats

        data = {"sent_bytes": 0, "sent_net_bytes": 0}
        stats = SiteSyncStats(data, None)
        assert stats.compression_ratio == 0.0

    def test_repr(self, sample_stats_data: dict[str, Any]) -> None:
        """Test string representation."""
        from pyvergeos.resources.site_syncs import SiteSyncStats

        stats = SiteSyncStats(sample_stats_data, None)
        assert "SiteSyncStats" in repr(stats)
        assert "1.0 GB" in repr(stats)


class TestSiteSyncStatsManager:
    """Tests for SiteSyncStatsManager."""

    def test_get(self, mock_client: MagicMock, sample_stats_data: dict[str, Any]) -> None:
        """Test get current stats."""
        from pyvergeos.resources.site_syncs import SiteSyncStats, SiteSyncStatsManager

        mock_client._request.return_value = [sample_stats_data]
        manager = SiteSyncStatsManager(mock_client, sync_key=1)

        result = manager.get()

        assert isinstance(result, SiteSyncStats)
        assert result.checked_bytes == 1073741824

    def test_get_empty(self, mock_client: MagicMock) -> None:
        """Test get returns None when no stats."""
        from pyvergeos.resources.site_syncs import SiteSyncStatsManager

        mock_client._request.return_value = []
        manager = SiteSyncStatsManager(mock_client, sync_key=1)

        result = manager.get()

        assert result is None

    def test_list(self, mock_client: MagicMock, sample_stats_data: dict[str, Any]) -> None:
        """Test list stats entries."""
        from pyvergeos.resources.site_syncs import SiteSyncStats, SiteSyncStatsManager

        mock_client._request.return_value = [sample_stats_data]
        manager = SiteSyncStatsManager(mock_client, sync_key=1)

        result = manager.list(limit=10)

        assert len(result) == 1
        assert isinstance(result[0], SiteSyncStats)

    def test_history(self, mock_client: MagicMock) -> None:
        """Test history retrieval."""
        from pyvergeos.resources.site_syncs import SiteSyncStatsHistory, SiteSyncStatsManager

        history_data = {
            "$key": 1,
            "parent": 2,
            "checked_bytes": 1073741824,
            "scanned_bytes": 536870912,
            "sent_bytes": 104857600,
            "sent_net_bytes": 52428800,
            "dirs_checked": 100,
            "files_checked": 1500,
            "files_updated": 50,
            "last_run_time": 120000,
            "snapshot_name": "snap-1",
            "timestamp": 1706500000,
        }
        mock_client._request.return_value = [history_data]
        manager = SiteSyncStatsManager(mock_client, sync_key=1)

        result = manager.history(limit=10)

        assert len(result) == 1
        assert isinstance(result[0], SiteSyncStatsHistory)
        assert result[0].snapshot_name == "snap-1"


# ============================================================================
# SiteSyncQueueItem Tests
# ============================================================================


@pytest.fixture
def sample_queue_item_data() -> dict[str, Any]:
    """Sample queue item data."""
    return {
        "$key": 1,
        "site_syncs_outgoing": 2,
        "id": "abc123",
        "cloud_snapshot": 10,
        "priority": 0,
        "status": "queue",
        "retention": 259200,
        "remote_expiration": 1707000000,
        "stats": {
            "checked_bytes": 1073741824,
            "sent_bytes": 104857600,
        },
        "destination_prefix": "remote",
        "timestamp": 1706500000000000,
        "do_not_expire": False,
    }


class TestSiteSyncQueueItem:
    """Tests for SiteSyncQueueItem resource object."""

    def test_properties(self, sample_queue_item_data: dict[str, Any]) -> None:
        """Test all properties return correct values."""
        from pyvergeos.resources.site_syncs import SiteSyncQueueItem

        item = SiteSyncQueueItem(sample_queue_item_data, None)

        assert item.key == 1
        assert item.sync_key == 2
        assert item.queue_id == "abc123"
        assert item.cloud_snapshot_key == 10
        assert item.priority == 0
        assert item.status == "queue"
        assert item.is_queued is True
        assert item.is_syncing is False
        assert item.is_complete is False
        assert item.has_error is False
        assert item.is_paused is False
        assert item.retention == 259200
        assert item.retention_timedelta == timedelta(days=3)
        assert item.remote_expiration_at is not None
        assert item.destination_prefix == "remote"
        assert item.created_at is not None
        assert item.do_not_expire is False

    def test_status_syncing(self, sample_queue_item_data: dict[str, Any]) -> None:
        """Test is_syncing property."""
        from pyvergeos.resources.site_syncs import SiteSyncQueueItem

        data = {**sample_queue_item_data, "status": "syncing"}
        item = SiteSyncQueueItem(data, None)
        assert item.is_syncing is True

    def test_status_complete(self, sample_queue_item_data: dict[str, Any]) -> None:
        """Test is_complete property."""
        from pyvergeos.resources.site_syncs import SiteSyncQueueItem

        data = {**sample_queue_item_data, "status": "complete"}
        item = SiteSyncQueueItem(data, None)
        assert item.is_complete is True

    def test_status_error(self, sample_queue_item_data: dict[str, Any]) -> None:
        """Test has_error property."""
        from pyvergeos.resources.site_syncs import SiteSyncQueueItem

        data = {**sample_queue_item_data, "status": "error"}
        item = SiteSyncQueueItem(data, None)
        assert item.has_error is True

    def test_get_stats(self, sample_queue_item_data: dict[str, Any]) -> None:
        """Test get_stats method."""
        from pyvergeos.resources.site_syncs import SiteSyncQueueItem, SiteSyncStats

        item = SiteSyncQueueItem(sample_queue_item_data, None)
        stats = item.get_stats()

        assert isinstance(stats, SiteSyncStats)
        assert stats.checked_bytes == 1073741824

    def test_repr(self, sample_queue_item_data: dict[str, Any]) -> None:
        """Test string representation."""
        from pyvergeos.resources.site_syncs import SiteSyncQueueItem

        item = SiteSyncQueueItem(sample_queue_item_data, None)
        assert "SiteSyncQueueItem" in repr(item)
        assert "key=1" in repr(item)


class TestSiteSyncQueueManager:
    """Tests for SiteSyncQueueManager."""

    def test_list(self, mock_client: MagicMock, sample_queue_item_data: dict[str, Any]) -> None:
        """Test list queue items."""
        from pyvergeos.resources.site_syncs import SiteSyncQueueItem, SiteSyncQueueManager

        mock_client._request.return_value = [sample_queue_item_data]
        manager = SiteSyncQueueManager(mock_client, sync_key=1)

        result = manager.list()

        assert len(result) == 1
        assert isinstance(result[0], SiteSyncQueueItem)
        call_args = mock_client._request.call_args
        assert "site_syncs_outgoing eq 1" in call_args[1]["params"]["filter"]

    def test_list_queued(
        self, mock_client: MagicMock, sample_queue_item_data: dict[str, Any]
    ) -> None:
        """Test list_queued helper."""
        from pyvergeos.resources.site_syncs import SiteSyncQueueManager

        mock_client._request.return_value = [sample_queue_item_data]
        manager = SiteSyncQueueManager(mock_client, sync_key=1)

        manager.list_queued()

        call_args = mock_client._request.call_args
        assert "status eq 'queue'" in call_args[1]["params"]["filter"]

    def test_list_syncing(
        self, mock_client: MagicMock, sample_queue_item_data: dict[str, Any]
    ) -> None:
        """Test list_syncing helper."""
        from pyvergeos.resources.site_syncs import SiteSyncQueueManager

        mock_client._request.return_value = []
        manager = SiteSyncQueueManager(mock_client, sync_key=1)

        manager.list_syncing()

        call_args = mock_client._request.call_args
        assert "status eq 'syncing'" in call_args[1]["params"]["filter"]

    def test_list_errors(
        self, mock_client: MagicMock, sample_queue_item_data: dict[str, Any]
    ) -> None:
        """Test list_errors helper."""
        from pyvergeos.resources.site_syncs import SiteSyncQueueManager

        mock_client._request.return_value = []
        manager = SiteSyncQueueManager(mock_client, sync_key=1)

        manager.list_errors()

        call_args = mock_client._request.call_args
        assert "error" in call_args[1]["params"]["filter"]

    def test_get(self, mock_client: MagicMock, sample_queue_item_data: dict[str, Any]) -> None:
        """Test get queue item by key."""
        from pyvergeos.resources.site_syncs import SiteSyncQueueItem, SiteSyncQueueManager

        mock_client._request.return_value = sample_queue_item_data
        manager = SiteSyncQueueManager(mock_client, sync_key=1)

        result = manager.get(1)

        assert isinstance(result, SiteSyncQueueItem)

    def test_get_not_found(self, mock_client: MagicMock) -> None:
        """Test get raises NotFoundError."""
        from pyvergeos.exceptions import NotFoundError
        from pyvergeos.resources.site_syncs import SiteSyncQueueManager

        mock_client._request.return_value = None
        manager = SiteSyncQueueManager(mock_client, sync_key=1)

        with pytest.raises(NotFoundError):
            manager.get(999)

    def test_delete(self, mock_client: MagicMock) -> None:
        """Test delete queue item."""
        from pyvergeos.resources.site_syncs import SiteSyncQueueManager

        mock_client._request.return_value = None
        manager = SiteSyncQueueManager(mock_client, sync_key=1)

        manager.delete(1)

        mock_client._request.assert_called_once_with("DELETE", "site_syncs_outgoing_queue/1")

    def test_count(self, mock_client: MagicMock, sample_queue_item_data: dict[str, Any]) -> None:
        """Test count method."""
        from pyvergeos.resources.site_syncs import SiteSyncQueueManager

        mock_client._request.return_value = [sample_queue_item_data, sample_queue_item_data]
        manager = SiteSyncQueueManager(mock_client, sync_key=1)

        count = manager.count()

        assert count == 2


# ============================================================================
# SiteSyncRemoteSnap Tests
# ============================================================================


@pytest.fixture
def sample_remote_snap_data() -> dict[str, Any]:
    """Sample remote snapshot data."""
    return {
        "$key": 1,
        "site_syncs_outgoing": 2,
        "name": "cloud-snap-2024-01-29",
        "status": "offline",
        "status_info": "",
        "remote_key": 100,
        "created": 1706500000,
        "description": "Daily backup",
        "expires": 1707000000,
    }


class TestSiteSyncRemoteSnap:
    """Tests for SiteSyncRemoteSnap resource object."""

    def test_properties(self, sample_remote_snap_data: dict[str, Any]) -> None:
        """Test all properties return correct values."""
        from pyvergeos.resources.site_syncs import SiteSyncRemoteSnap

        snap = SiteSyncRemoteSnap(sample_remote_snap_data, None)

        assert snap.key == 1
        assert snap.sync_key == 2
        assert snap.name == "cloud-snap-2024-01-29"
        assert snap.status == "offline"
        assert snap.status_info == ""
        assert snap.is_downloading is False
        assert snap.has_error is False
        assert snap.remote_key == 100
        assert snap.created_at is not None
        assert snap.description == "Daily backup"
        assert snap.expires_at is not None

    def test_is_downloading(self, sample_remote_snap_data: dict[str, Any]) -> None:
        """Test is_downloading property."""
        from pyvergeos.resources.site_syncs import SiteSyncRemoteSnap

        data = {**sample_remote_snap_data, "status": "downloading"}
        snap = SiteSyncRemoteSnap(data, None)
        assert snap.is_downloading is True

    def test_has_error(self, sample_remote_snap_data: dict[str, Any]) -> None:
        """Test has_error property."""
        from pyvergeos.resources.site_syncs import SiteSyncRemoteSnap

        data = {**sample_remote_snap_data, "status": "error"}
        snap = SiteSyncRemoteSnap(data, None)
        assert snap.has_error is True

    def test_repr(self, sample_remote_snap_data: dict[str, Any]) -> None:
        """Test string representation."""
        from pyvergeos.resources.site_syncs import SiteSyncRemoteSnap

        snap = SiteSyncRemoteSnap(sample_remote_snap_data, None)
        assert "SiteSyncRemoteSnap" in repr(snap)
        assert "cloud-snap-2024-01-29" in repr(snap)


class TestSiteSyncRemoteSnapManager:
    """Tests for SiteSyncRemoteSnapManager."""

    def test_list(self, mock_client: MagicMock, sample_remote_snap_data: dict[str, Any]) -> None:
        """Test list remote snapshots."""
        from pyvergeos.resources.site_syncs import SiteSyncRemoteSnap, SiteSyncRemoteSnapManager

        mock_client._request.return_value = [sample_remote_snap_data]
        manager = SiteSyncRemoteSnapManager(mock_client, sync_key=1)

        result = manager.list()

        assert len(result) == 1
        assert isinstance(result[0], SiteSyncRemoteSnap)

    def test_get_by_key(
        self, mock_client: MagicMock, sample_remote_snap_data: dict[str, Any]
    ) -> None:
        """Test get by key."""
        from pyvergeos.resources.site_syncs import SiteSyncRemoteSnap, SiteSyncRemoteSnapManager

        mock_client._request.return_value = sample_remote_snap_data
        manager = SiteSyncRemoteSnapManager(mock_client, sync_key=1)

        result = manager.get(key=1)

        assert isinstance(result, SiteSyncRemoteSnap)

    def test_get_by_name(
        self, mock_client: MagicMock, sample_remote_snap_data: dict[str, Any]
    ) -> None:
        """Test get by name."""
        from pyvergeos.resources.site_syncs import SiteSyncRemoteSnap, SiteSyncRemoteSnapManager

        mock_client._request.return_value = [sample_remote_snap_data]
        manager = SiteSyncRemoteSnapManager(mock_client, sync_key=1)

        result = manager.get(name="cloud-snap-2024-01-29")

        assert isinstance(result, SiteSyncRemoteSnap)

    def test_get_not_found(self, mock_client: MagicMock) -> None:
        """Test get raises NotFoundError."""
        from pyvergeos.exceptions import NotFoundError
        from pyvergeos.resources.site_syncs import SiteSyncRemoteSnapManager

        mock_client._request.return_value = None
        manager = SiteSyncRemoteSnapManager(mock_client, sync_key=1)

        with pytest.raises(NotFoundError):
            manager.get(key=999)

    def test_get_no_key_or_name(self, mock_client: MagicMock) -> None:
        """Test get raises ValueError when no key or name."""
        from pyvergeos.resources.site_syncs import SiteSyncRemoteSnapManager

        manager = SiteSyncRemoteSnapManager(mock_client, sync_key=1)

        with pytest.raises(ValueError, match="Either key or name"):
            manager.get()

    def test_request_sync_back(self, mock_client: MagicMock) -> None:
        """Test request_sync_back action."""
        from pyvergeos.resources.site_syncs import SiteSyncRemoteSnapManager

        mock_client._request.return_value = None
        manager = SiteSyncRemoteSnapManager(mock_client, sync_key=1)

        manager.request_sync_back(1)

        call_args = mock_client._request.call_args
        assert call_args[0] == ("POST", "site_syncs_outgoing_remote_snap_actions")
        assert call_args[1]["json_data"]["action"] == "request"

    def test_set_retention(self, mock_client: MagicMock) -> None:
        """Test set_retention action."""
        from datetime import datetime, timezone

        from pyvergeos.resources.site_syncs import SiteSyncRemoteSnapManager

        mock_client._request.return_value = None
        manager = SiteSyncRemoteSnapManager(mock_client, sync_key=1)

        expires = datetime(2024, 2, 1, tzinfo=timezone.utc)
        manager.set_retention(1, expires)

        call_args = mock_client._request.call_args
        assert call_args[1]["json_data"]["action"] == "set_retention"
        assert "expires" in call_args[1]["json_data"]["params"]


# ============================================================================
# SiteSyncIncomingVerified Tests
# ============================================================================


@pytest.fixture
def sample_verified_data() -> dict[str, Any]:
    """Sample verified sync data."""
    return {
        "$key": 1,
        "site_syncs_incoming": 2,
        "name": "Incoming Sync",
        "registered": True,
        "registered_on": 1706500000,
    }


class TestSiteSyncIncomingVerified:
    """Tests for SiteSyncIncomingVerified resource object."""

    def test_properties(self, sample_verified_data: dict[str, Any]) -> None:
        """Test all properties return correct values."""
        from pyvergeos.resources.site_syncs import SiteSyncIncomingVerified

        verified = SiteSyncIncomingVerified(sample_verified_data, None)

        assert verified.key == 1
        assert verified.incoming_sync_key == 2
        assert verified.name == "Incoming Sync"
        assert verified.is_registered is True
        assert verified.registered_at is not None

    def test_not_registered(self) -> None:
        """Test when not registered."""
        from pyvergeos.resources.site_syncs import SiteSyncIncomingVerified

        data = {
            "$key": 1,
            "site_syncs_incoming": 2,
            "registered": False,
            "registered_on": 0,
        }
        verified = SiteSyncIncomingVerified(data, None)

        assert verified.is_registered is False
        assert verified.registered_at is None

    def test_repr(self, sample_verified_data: dict[str, Any]) -> None:
        """Test string representation."""
        from pyvergeos.resources.site_syncs import SiteSyncIncomingVerified

        verified = SiteSyncIncomingVerified(sample_verified_data, None)
        assert "SiteSyncIncomingVerified" in repr(verified)
        assert "registered=True" in repr(verified)


class TestSiteSyncIncomingVerifiedManager:
    """Tests for SiteSyncIncomingVerifiedManager."""

    def test_get(self, mock_client: MagicMock, sample_verified_data: dict[str, Any]) -> None:
        """Test get verified entry."""
        from pyvergeos.resources.site_syncs import (
            SiteSyncIncomingVerified,
            SiteSyncIncomingVerifiedManager,
        )

        mock_client._request.return_value = [sample_verified_data]
        manager = SiteSyncIncomingVerifiedManager(mock_client, incoming_sync_key=1)

        result = manager.get()

        assert isinstance(result, SiteSyncIncomingVerified)

    def test_get_empty(self, mock_client: MagicMock) -> None:
        """Test get returns None when no entry."""
        from pyvergeos.resources.site_syncs import SiteSyncIncomingVerifiedManager

        mock_client._request.return_value = []
        manager = SiteSyncIncomingVerifiedManager(mock_client, incoming_sync_key=1)

        result = manager.get()

        assert result is None

    def test_list_remote_snapshots(self, mock_client: MagicMock) -> None:
        """Test list_remote_snapshots action."""
        from pyvergeos.resources.site_syncs import SiteSyncIncomingVerifiedManager

        mock_client._request.return_value = {"snapshots": [{"name": "snap1"}, {"name": "snap2"}]}
        manager = SiteSyncIncomingVerifiedManager(mock_client, incoming_sync_key=1)

        result = manager.list_remote_snapshots(1)

        assert len(result) == 2
        call_args = mock_client._request.call_args
        assert call_args[1]["json_data"]["action"] == "list_snaps"

    def test_request_snapshot(self, mock_client: MagicMock) -> None:
        """Test request_snapshot action."""
        from pyvergeos.resources.site_syncs import SiteSyncIncomingVerifiedManager

        mock_client._request.return_value = None
        manager = SiteSyncIncomingVerifiedManager(mock_client, incoming_sync_key=1)

        manager.request_snapshot(1, "snap-name", retention=604800)

        call_args = mock_client._request.call_args
        assert call_args[1]["json_data"]["action"] == "request"
        assert call_args[1]["json_data"]["params"]["snapshot"] == "snap-name"

    def test_request_snapshot_with_timedelta(self, mock_client: MagicMock) -> None:
        """Test request_snapshot with timedelta."""
        from pyvergeos.resources.site_syncs import SiteSyncIncomingVerifiedManager

        mock_client._request.return_value = None
        manager = SiteSyncIncomingVerifiedManager(mock_client, incoming_sync_key=1)

        manager.request_snapshot(1, "snap-name", retention=timedelta(days=7))

        call_args = mock_client._request.call_args
        assert call_args[1]["json_data"]["params"]["retention"] == 604800

    def test_set_retention(self, mock_client: MagicMock) -> None:
        """Test set_retention action."""
        from pyvergeos.resources.site_syncs import SiteSyncIncomingVerifiedManager

        mock_client._request.return_value = None
        manager = SiteSyncIncomingVerifiedManager(mock_client, incoming_sync_key=1)

        manager.set_retention(1, "snap-name", 604800)

        call_args = mock_client._request.call_args
        assert call_args[1]["json_data"]["action"] == "set_retention"


# ============================================================================
# SiteSyncLog Tests
# ============================================================================


@pytest.fixture
def sample_log_data() -> dict[str, Any]:
    """Sample log entry data."""
    return {
        "$key": 1,
        "level": "message",
        "text": "Sync started for cloud-snap-2024-01-29",
        "timestamp": 1706500000000000,
        "user": "admin",
    }


class TestSiteSyncLog:
    """Tests for SiteSyncLog resource object."""

    def test_properties(self, sample_log_data: dict[str, Any]) -> None:
        """Test all properties return correct values."""
        from pyvergeos.resources.site_syncs import SiteSyncLog

        log = SiteSyncLog(sample_log_data, None)

        assert log.level == "message"
        assert log.level_display == "Message"
        assert log.is_error is False
        assert log.is_warning is False
        assert log.text == "Sync started for cloud-snap-2024-01-29"
        assert log.timestamp_us == 1706500000000000
        assert log.logged_at is not None
        assert log.user == "admin"

    def test_is_error(self, sample_log_data: dict[str, Any]) -> None:
        """Test is_error property."""
        from pyvergeos.resources.site_syncs import SiteSyncLog

        data = {**sample_log_data, "level": "error"}
        log = SiteSyncLog(data, None)
        assert log.is_error is True

    def test_is_warning(self, sample_log_data: dict[str, Any]) -> None:
        """Test is_warning property."""
        from pyvergeos.resources.site_syncs import SiteSyncLog

        data = {**sample_log_data, "level": "warning"}
        log = SiteSyncLog(data, None)
        assert log.is_warning is True

    def test_repr(self, sample_log_data: dict[str, Any]) -> None:
        """Test string representation."""
        from pyvergeos.resources.site_syncs import SiteSyncLog

        log = SiteSyncLog(sample_log_data, None)
        assert "SiteSyncLog" in repr(log)
        assert "[message]" in repr(log)


class TestSiteSyncOutgoingLogManager:
    """Tests for SiteSyncOutgoingLogManager."""

    def test_list(self, mock_client: MagicMock, sample_log_data: dict[str, Any]) -> None:
        """Test list logs."""
        from pyvergeos.resources.site_syncs import SiteSyncLog, SiteSyncOutgoingLogManager

        mock_client._request.return_value = [sample_log_data]
        manager = SiteSyncOutgoingLogManager(mock_client, sync_key=1)

        result = manager.list()

        assert len(result) == 1
        assert isinstance(result[0], SiteSyncLog)
        call_args = mock_client._request.call_args
        assert "site_syncs_outgoing eq 1" in call_args[1]["params"]["filter"]

    def test_list_with_level(self, mock_client: MagicMock, sample_log_data: dict[str, Any]) -> None:
        """Test list with level filter."""
        from pyvergeos.resources.site_syncs import SiteSyncOutgoingLogManager

        mock_client._request.return_value = [sample_log_data]
        manager = SiteSyncOutgoingLogManager(mock_client, sync_key=1)

        manager.list(level="error")

        call_args = mock_client._request.call_args
        assert "level eq 'error'" in call_args[1]["params"]["filter"]

    def test_list_errors(self, mock_client: MagicMock, sample_log_data: dict[str, Any]) -> None:
        """Test list_errors helper."""
        from pyvergeos.resources.site_syncs import SiteSyncOutgoingLogManager

        mock_client._request.return_value = []
        manager = SiteSyncOutgoingLogManager(mock_client, sync_key=1)

        manager.list_errors()

        call_args = mock_client._request.call_args
        assert "error" in call_args[1]["params"]["filter"]
        assert "critical" in call_args[1]["params"]["filter"]

    def test_list_warnings(self, mock_client: MagicMock, sample_log_data: dict[str, Any]) -> None:
        """Test list_warnings helper."""
        from pyvergeos.resources.site_syncs import SiteSyncOutgoingLogManager

        mock_client._request.return_value = []
        manager = SiteSyncOutgoingLogManager(mock_client, sync_key=1)

        manager.list_warnings()

        call_args = mock_client._request.call_args
        assert "level eq 'warning'" in call_args[1]["params"]["filter"]


class TestSiteSyncIncomingLogManager:
    """Tests for SiteSyncIncomingLogManager."""

    def test_list(self, mock_client: MagicMock, sample_log_data: dict[str, Any]) -> None:
        """Test list logs."""
        from pyvergeos.resources.site_syncs import SiteSyncIncomingLogManager, SiteSyncLog

        mock_client._request.return_value = [sample_log_data]
        manager = SiteSyncIncomingLogManager(mock_client, sync_key=1)

        result = manager.list()

        assert len(result) == 1
        assert isinstance(result[0], SiteSyncLog)
        call_args = mock_client._request.call_args
        assert "site_syncs_incoming eq 1" in call_args[1]["params"]["filter"]


# ============================================================================
# Scoped Manager Access Tests
# ============================================================================


class TestScopedManagerAccess:
    """Tests for accessing scoped managers via object properties."""

    def test_outgoing_sync_queue_property(
        self, outgoing_manager: SiteSyncOutgoingManager, sample_outgoing_sync_data: dict[str, Any]
    ) -> None:
        """Test queue property on SiteSyncOutgoing."""
        from pyvergeos.resources.site_syncs import SiteSyncQueueManager

        sync = SiteSyncOutgoing(sample_outgoing_sync_data, outgoing_manager)
        queue = sync.queue

        assert isinstance(queue, SiteSyncQueueManager)

    def test_outgoing_sync_remote_snapshots_property(
        self, outgoing_manager: SiteSyncOutgoingManager, sample_outgoing_sync_data: dict[str, Any]
    ) -> None:
        """Test remote_snapshots property on SiteSyncOutgoing."""
        from pyvergeos.resources.site_syncs import SiteSyncRemoteSnapManager

        sync = SiteSyncOutgoing(sample_outgoing_sync_data, outgoing_manager)
        remote_snaps = sync.remote_snapshots

        assert isinstance(remote_snaps, SiteSyncRemoteSnapManager)

    def test_outgoing_sync_stats_property(
        self, outgoing_manager: SiteSyncOutgoingManager, sample_outgoing_sync_data: dict[str, Any]
    ) -> None:
        """Test stats property on SiteSyncOutgoing."""
        from pyvergeos.resources.site_syncs import SiteSyncStatsManager

        sync = SiteSyncOutgoing(sample_outgoing_sync_data, outgoing_manager)
        stats = sync.stats

        assert isinstance(stats, SiteSyncStatsManager)

    def test_outgoing_sync_logs_property(
        self, outgoing_manager: SiteSyncOutgoingManager, sample_outgoing_sync_data: dict[str, Any]
    ) -> None:
        """Test logs property on SiteSyncOutgoing."""
        from pyvergeos.resources.site_syncs import SiteSyncOutgoingLogManager

        sync = SiteSyncOutgoing(sample_outgoing_sync_data, outgoing_manager)
        logs = sync.logs

        assert isinstance(logs, SiteSyncOutgoingLogManager)

    def test_incoming_sync_verified_property(
        self, incoming_manager: SiteSyncIncomingManager, sample_incoming_sync_data: dict[str, Any]
    ) -> None:
        """Test verified property on SiteSyncIncoming."""
        from pyvergeos.resources.site_syncs import SiteSyncIncomingVerifiedManager

        sync = SiteSyncIncoming(sample_incoming_sync_data, incoming_manager)
        verified = sync.verified

        assert isinstance(verified, SiteSyncIncomingVerifiedManager)

    def test_incoming_sync_logs_property(
        self, incoming_manager: SiteSyncIncomingManager, sample_incoming_sync_data: dict[str, Any]
    ) -> None:
        """Test logs property on SiteSyncIncoming."""
        from pyvergeos.resources.site_syncs import SiteSyncIncomingLogManager

        sync = SiteSyncIncoming(sample_incoming_sync_data, incoming_manager)
        logs = sync.logs

        assert isinstance(logs, SiteSyncIncomingLogManager)
