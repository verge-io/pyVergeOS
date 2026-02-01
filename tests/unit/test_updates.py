"""Unit tests for update management resources."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from pyvergeos.client import VergeClient
from pyvergeos.exceptions import NotFoundError
from pyvergeos.resources.updates import (
    UpdateBranch,
    UpdateBranchManager,
    UpdateDashboard,
    UpdateDashboardManager,
    UpdateLog,
    UpdateLogManager,
    UpdatePackage,
    UpdatePackageManager,
    UpdateSettings,
    UpdateSettingsManager,
    UpdateSource,
    UpdateSourceManager,
    UpdateSourcePackage,
    UpdateSourcePackageManager,
    UpdateSourceStatus,
    UpdateSourceStatusManager,
)


@pytest.fixture
def mock_client() -> MagicMock:
    """Create a mock VergeClient."""
    client = MagicMock(spec=VergeClient)
    client.is_connected = True
    return client


# =============================================================================
# UpdateLogManager Tests
# =============================================================================


class TestUpdateLogManager:
    """Tests for UpdateLogManager."""

    def test_init(self, mock_client: MagicMock) -> None:
        """Test manager initialization."""
        manager = UpdateLogManager(mock_client)
        assert manager._client == mock_client
        assert manager._endpoint == "update_logs"

    def test_list_returns_logs(self, mock_client: MagicMock) -> None:
        """Test listing logs."""
        mock_client._request.return_value = [
            {"$key": 1, "level": "message", "text": "Update started"},
            {"$key": 2, "level": "message", "text": "Download complete"},
        ]

        manager = UpdateLogManager(mock_client)
        logs = manager.list()

        assert len(logs) == 2
        assert isinstance(logs[0], UpdateLog)
        assert logs[0]["text"] == "Update started"

    def test_list_with_level_filter(self, mock_client: MagicMock) -> None:
        """Test listing with level filter."""
        mock_client._request.return_value = []

        manager = UpdateLogManager(mock_client)
        manager.list(level="error")

        call_args = mock_client._request.call_args
        assert "level eq 'error'" in call_args[1]["params"]["filter"]

    def test_list_returns_empty_on_none(self, mock_client: MagicMock) -> None:
        """Test listing returns empty list on None response."""
        mock_client._request.return_value = None

        manager = UpdateLogManager(mock_client)
        logs = manager.list()

        assert logs == []

    def test_list_default_sort(self, mock_client: MagicMock) -> None:
        """Test listing uses timestamp descending sort."""
        mock_client._request.return_value = []

        manager = UpdateLogManager(mock_client)
        manager.list()

        call_args = mock_client._request.call_args
        assert call_args[1]["params"]["sort"] == "-timestamp"

    def test_get_by_key(self, mock_client: MagicMock) -> None:
        """Test getting log by key."""
        mock_client._request.return_value = {
            "$key": 1,
            "level": "message",
            "text": "Update started",
        }

        manager = UpdateLogManager(mock_client)
        log = manager.get(key=1)

        assert isinstance(log, UpdateLog)
        assert log.key == 1
        assert log["text"] == "Update started"

    def test_get_not_found(self, mock_client: MagicMock) -> None:
        """Test get raises NotFoundError when not found."""
        mock_client._request.return_value = None

        manager = UpdateLogManager(mock_client)
        with pytest.raises(NotFoundError):
            manager.get(key=999)

    def test_get_requires_key(self, mock_client: MagicMock) -> None:
        """Test get raises ValueError without key."""
        manager = UpdateLogManager(mock_client)
        with pytest.raises(ValueError, match="Key must be provided"):
            manager.get()

    def test_list_errors(self, mock_client: MagicMock) -> None:
        """Test list_errors convenience method."""
        mock_client._request.return_value = [
            {"$key": 1, "level": "error", "text": "Download failed"},
        ]

        manager = UpdateLogManager(mock_client)
        _ = manager.list_errors()

        call_args = mock_client._request.call_args
        assert "level eq 'error'" in call_args[1]["params"]["filter"]
        assert "level eq 'critical'" in call_args[1]["params"]["filter"]

    def test_list_warnings(self, mock_client: MagicMock) -> None:
        """Test list_warnings convenience method."""
        mock_client._request.return_value = []

        manager = UpdateLogManager(mock_client)
        manager.list_warnings()

        call_args = mock_client._request.call_args
        assert "level eq 'warning'" in call_args[1]["params"]["filter"]


class TestUpdateLog:
    """Tests for UpdateLog resource object."""

    def test_is_error_true(self, mock_client: MagicMock) -> None:
        """Test is_error returns True for error level."""
        manager = UpdateLogManager(mock_client)
        log = UpdateLog({"$key": 1, "level": "error"}, manager)
        assert log.is_error is True

    def test_is_error_true_critical(self, mock_client: MagicMock) -> None:
        """Test is_error returns True for critical level."""
        manager = UpdateLogManager(mock_client)
        log = UpdateLog({"$key": 1, "level": "critical"}, manager)
        assert log.is_error is True

    def test_is_error_false(self, mock_client: MagicMock) -> None:
        """Test is_error returns False for message level."""
        manager = UpdateLogManager(mock_client)
        log = UpdateLog({"$key": 1, "level": "message"}, manager)
        assert log.is_error is False

    def test_is_warning(self, mock_client: MagicMock) -> None:
        """Test is_warning property."""
        manager = UpdateLogManager(mock_client)
        log = UpdateLog({"$key": 1, "level": "warning"}, manager)
        assert log.is_warning is True

    def test_is_audit(self, mock_client: MagicMock) -> None:
        """Test is_audit property."""
        manager = UpdateLogManager(mock_client)
        log = UpdateLog({"$key": 1, "level": "audit"}, manager)
        assert log.is_audit is True


# =============================================================================
# UpdateBranchManager Tests
# =============================================================================


class TestUpdateBranchManager:
    """Tests for UpdateBranchManager."""

    def test_init(self, mock_client: MagicMock) -> None:
        """Test manager initialization."""
        manager = UpdateBranchManager(mock_client)
        assert manager._client == mock_client
        assert manager._endpoint == "update_branches"

    def test_list_returns_branches(self, mock_client: MagicMock) -> None:
        """Test listing branches."""
        mock_client._request.return_value = [
            {"$key": 1, "name": "stable-4.12", "description": "4.12 Release"},
            {"$key": 2, "name": "stable-4.13", "description": "4.13 Release"},
        ]

        manager = UpdateBranchManager(mock_client)
        branches = manager.list()

        assert len(branches) == 2
        assert isinstance(branches[0], UpdateBranch)
        assert branches[1]["name"] == "stable-4.13"

    def test_get_by_key(self, mock_client: MagicMock) -> None:
        """Test getting branch by key."""
        mock_client._request.return_value = {
            "$key": 1,
            "name": "stable-4.13",
            "description": "4.13 Release",
        }

        manager = UpdateBranchManager(mock_client)
        branch = manager.get(key=1)

        assert isinstance(branch, UpdateBranch)
        assert branch["name"] == "stable-4.13"

    def test_get_by_name(self, mock_client: MagicMock) -> None:
        """Test getting branch by name."""
        mock_client._request.return_value = [
            {"$key": 2, "name": "stable-4.13", "description": "4.13 Release"},
        ]

        manager = UpdateBranchManager(mock_client)
        branch = manager.get(name="stable-4.13")

        assert branch["name"] == "stable-4.13"

    def test_get_not_found(self, mock_client: MagicMock) -> None:
        """Test get raises NotFoundError when not found."""
        mock_client._request.return_value = None

        manager = UpdateBranchManager(mock_client)
        with pytest.raises(NotFoundError):
            manager.get(key=999)

    def test_get_requires_identifier(self, mock_client: MagicMock) -> None:
        """Test get raises ValueError without identifier."""
        manager = UpdateBranchManager(mock_client)
        with pytest.raises(ValueError, match="Either key or name"):
            manager.get()


# =============================================================================
# UpdateSourceStatusManager Tests
# =============================================================================


class TestUpdateSourceStatusManager:
    """Tests for UpdateSourceStatusManager."""

    def test_init(self, mock_client: MagicMock) -> None:
        """Test manager initialization."""
        manager = UpdateSourceStatusManager(mock_client)
        assert manager._client == mock_client
        assert manager._endpoint == "update_source_status"

    def test_init_with_scope(self, mock_client: MagicMock) -> None:
        """Test manager initialization with source scope."""
        manager = UpdateSourceStatusManager(mock_client, source_key=1)
        assert manager._source_key == 1

    def test_list_returns_statuses(self, mock_client: MagicMock) -> None:
        """Test listing statuses."""
        mock_client._request.return_value = [
            {"$key": 1, "source": 1, "status": "idle"},
        ]

        manager = UpdateSourceStatusManager(mock_client)
        statuses = manager.list()

        assert len(statuses) == 1
        assert isinstance(statuses[0], UpdateSourceStatus)
        assert statuses[0]["status"] == "idle"

    def test_list_with_source_filter(self, mock_client: MagicMock) -> None:
        """Test listing with source filter."""
        mock_client._request.return_value = []

        manager = UpdateSourceStatusManager(mock_client)
        manager.list(source=1)

        call_args = mock_client._request.call_args
        assert "source eq 1" in call_args[1]["params"]["filter"]

    def test_list_scoped_applies_filter(self, mock_client: MagicMock) -> None:
        """Test scoped manager applies source filter."""
        mock_client._request.return_value = []

        manager = UpdateSourceStatusManager(mock_client, source_key=1)
        manager.list()

        call_args = mock_client._request.call_args
        assert "source eq 1" in call_args[1]["params"]["filter"]

    def test_get_for_source(self, mock_client: MagicMock) -> None:
        """Test get_for_source convenience method."""
        mock_client._request.return_value = [
            {"$key": 1, "source": 1, "status": "idle"},
        ]

        manager = UpdateSourceStatusManager(mock_client)
        status = manager.get_for_source(1)

        assert isinstance(status, UpdateSourceStatus)
        assert status["status"] == "idle"

    def test_get_for_source_not_found(self, mock_client: MagicMock) -> None:
        """Test get_for_source raises NotFoundError."""
        mock_client._request.return_value = []

        manager = UpdateSourceStatusManager(mock_client)
        with pytest.raises(NotFoundError):
            manager.get_for_source(999)


class TestUpdateSourceStatus:
    """Tests for UpdateSourceStatus resource object."""

    def test_source_key(self, mock_client: MagicMock) -> None:
        """Test source_key property."""
        manager = UpdateSourceStatusManager(mock_client)
        status = UpdateSourceStatus({"$key": 1, "source": 2}, manager)
        assert status.source_key == 2

    def test_is_idle(self, mock_client: MagicMock) -> None:
        """Test is_idle property."""
        manager = UpdateSourceStatusManager(mock_client)
        status = UpdateSourceStatus({"$key": 1, "status": "idle"}, manager)
        assert status.is_idle is True

    def test_is_busy(self, mock_client: MagicMock) -> None:
        """Test is_busy property."""
        manager = UpdateSourceStatusManager(mock_client)

        for busy_status in ["refreshing", "downloading", "installing", "applying"]:
            status = UpdateSourceStatus({"$key": 1, "status": busy_status}, manager)
            assert status.is_busy is True, f"{busy_status} should be busy"

    def test_is_not_busy_when_idle(self, mock_client: MagicMock) -> None:
        """Test is_busy returns False when idle."""
        manager = UpdateSourceStatusManager(mock_client)
        status = UpdateSourceStatus({"$key": 1, "status": "idle"}, manager)
        assert status.is_busy is False

    def test_is_error(self, mock_client: MagicMock) -> None:
        """Test is_error property."""
        manager = UpdateSourceStatusManager(mock_client)
        status = UpdateSourceStatus({"$key": 1, "status": "error"}, manager)
        assert status.is_error is True

    def test_is_refreshing(self, mock_client: MagicMock) -> None:
        """Test is_refreshing property."""
        manager = UpdateSourceStatusManager(mock_client)
        status = UpdateSourceStatus({"$key": 1, "status": "refreshing"}, manager)
        assert status.is_refreshing is True

    def test_is_downloading(self, mock_client: MagicMock) -> None:
        """Test is_downloading property."""
        manager = UpdateSourceStatusManager(mock_client)
        status = UpdateSourceStatus({"$key": 1, "status": "downloading"}, manager)
        assert status.is_downloading is True

    def test_is_installing(self, mock_client: MagicMock) -> None:
        """Test is_installing property."""
        manager = UpdateSourceStatusManager(mock_client)
        status = UpdateSourceStatus({"$key": 1, "status": "installing"}, manager)
        assert status.is_installing is True

    def test_is_applying(self, mock_client: MagicMock) -> None:
        """Test is_applying property."""
        manager = UpdateSourceStatusManager(mock_client)
        status = UpdateSourceStatus({"$key": 1, "status": "applying"}, manager)
        assert status.is_applying is True


# =============================================================================
# UpdateSourcePackageManager Tests
# =============================================================================


class TestUpdateSourcePackageManager:
    """Tests for UpdateSourcePackageManager."""

    def test_init(self, mock_client: MagicMock) -> None:
        """Test manager initialization."""
        manager = UpdateSourcePackageManager(mock_client)
        assert manager._client == mock_client
        assert manager._endpoint == "update_source_packages"

    def test_init_with_scope(self, mock_client: MagicMock) -> None:
        """Test manager initialization with scopes."""
        manager = UpdateSourcePackageManager(mock_client, source_key=1, branch_key=2)
        assert manager._source_key == 1
        assert manager._branch_key == 2

    def test_list_returns_packages(self, mock_client: MagicMock) -> None:
        """Test listing packages."""
        mock_client._request.return_value = [
            {"$key": 1, "name": "yb-system", "version": "26.0.1.2", "downloaded": True},
            {"$key": 2, "name": "yb-cloud", "version": "26.0.1.2", "downloaded": False},
        ]

        manager = UpdateSourcePackageManager(mock_client)
        packages = manager.list()

        assert len(packages) == 2
        assert isinstance(packages[0], UpdateSourcePackage)

    def test_list_with_downloaded_filter(self, mock_client: MagicMock) -> None:
        """Test listing with downloaded filter."""
        mock_client._request.return_value = []

        manager = UpdateSourcePackageManager(mock_client)
        manager.list(downloaded=True)

        call_args = mock_client._request.call_args
        assert "downloaded eq 1" in call_args[1]["params"]["filter"]

    def test_list_with_downloaded_false_filter(self, mock_client: MagicMock) -> None:
        """Test listing with downloaded=False filter."""
        mock_client._request.return_value = []

        manager = UpdateSourcePackageManager(mock_client)
        manager.list(downloaded=False)

        call_args = mock_client._request.call_args
        assert "downloaded eq 0" in call_args[1]["params"]["filter"]

    def test_list_pending(self, mock_client: MagicMock) -> None:
        """Test list_pending convenience method."""
        mock_client._request.return_value = []

        manager = UpdateSourcePackageManager(mock_client)
        manager.list_pending()

        call_args = mock_client._request.call_args
        assert "downloaded eq 0" in call_args[1]["params"]["filter"]

    def test_list_downloaded(self, mock_client: MagicMock) -> None:
        """Test list_downloaded convenience method."""
        mock_client._request.return_value = []

        manager = UpdateSourcePackageManager(mock_client)
        manager.list_downloaded()

        call_args = mock_client._request.call_args
        assert "downloaded eq 1" in call_args[1]["params"]["filter"]

    def test_get_by_key(self, mock_client: MagicMock) -> None:
        """Test getting package by key."""
        mock_client._request.return_value = {
            "$key": 1,
            "name": "yb-system",
            "version": "26.0.1.2",
        }

        manager = UpdateSourcePackageManager(mock_client)
        pkg = manager.get(key=1)

        assert isinstance(pkg, UpdateSourcePackage)
        assert pkg["name"] == "yb-system"


class TestUpdateSourcePackage:
    """Tests for UpdateSourcePackage resource object."""

    def test_branch_key(self, mock_client: MagicMock) -> None:
        """Test branch_key property."""
        manager = UpdateSourcePackageManager(mock_client)
        pkg = UpdateSourcePackage({"$key": 1, "branch": 2}, manager)
        assert pkg.branch_key == 2

    def test_source_key(self, mock_client: MagicMock) -> None:
        """Test source_key property."""
        manager = UpdateSourcePackageManager(mock_client)
        pkg = UpdateSourcePackage({"$key": 1, "source": 3}, manager)
        assert pkg.source_key == 3

    def test_is_downloaded(self, mock_client: MagicMock) -> None:
        """Test is_downloaded property."""
        manager = UpdateSourcePackageManager(mock_client)
        pkg = UpdateSourcePackage({"$key": 1, "downloaded": True}, manager)
        assert pkg.is_downloaded is True

    def test_is_not_downloaded(self, mock_client: MagicMock) -> None:
        """Test is_downloaded returns False."""
        manager = UpdateSourcePackageManager(mock_client)
        pkg = UpdateSourcePackage({"$key": 1, "downloaded": False}, manager)
        assert pkg.is_downloaded is False

    def test_is_optional(self, mock_client: MagicMock) -> None:
        """Test is_optional property."""
        manager = UpdateSourcePackageManager(mock_client)
        pkg = UpdateSourcePackage({"$key": 1, "optional": True}, manager)
        assert pkg.is_optional is True


# =============================================================================
# UpdateSourceManager Tests
# =============================================================================


class TestUpdateSourceManager:
    """Tests for UpdateSourceManager."""

    def test_init(self, mock_client: MagicMock) -> None:
        """Test manager initialization."""
        manager = UpdateSourceManager(mock_client)
        assert manager._client == mock_client
        assert manager._endpoint == "update_sources"

    def test_list_returns_sources(self, mock_client: MagicMock) -> None:
        """Test listing sources."""
        mock_client._request.return_value = [
            {"$key": 1, "name": "Verge.io Updates", "url": "https://updates.verge.io"},
            {"$key": 2, "name": "Trial/NFR", "url": "https://trial.verge.io"},
        ]

        manager = UpdateSourceManager(mock_client)
        sources = manager.list()

        assert len(sources) == 2
        assert isinstance(sources[0], UpdateSource)
        assert sources[0]["name"] == "Verge.io Updates"

    def test_list_with_enabled_filter(self, mock_client: MagicMock) -> None:
        """Test listing with enabled filter."""
        mock_client._request.return_value = []

        manager = UpdateSourceManager(mock_client)
        manager.list(enabled=True)

        call_args = mock_client._request.call_args
        assert "enabled eq 1" in call_args[1]["params"]["filter"]

    def test_get_by_key(self, mock_client: MagicMock) -> None:
        """Test getting source by key."""
        mock_client._request.return_value = {
            "$key": 1,
            "name": "Verge.io Updates",
            "url": "https://updates.verge.io",
        }

        manager = UpdateSourceManager(mock_client)
        source = manager.get(key=1)

        assert isinstance(source, UpdateSource)
        assert source["name"] == "Verge.io Updates"

    def test_get_by_name(self, mock_client: MagicMock) -> None:
        """Test getting source by name."""
        mock_client._request.return_value = [
            {"$key": 1, "name": "Verge.io Updates"},
        ]

        manager = UpdateSourceManager(mock_client)
        source = manager.get(name="Verge.io Updates")

        assert source["name"] == "Verge.io Updates"

    def test_create_source(self, mock_client: MagicMock) -> None:
        """Test creating a source."""
        mock_client._request.side_effect = [
            {"$key": 3},  # POST response
            {"$key": 3, "name": "Test Source", "url": "https://test.example.com"},
        ]

        manager = UpdateSourceManager(mock_client)
        source = manager.create(
            name="Test Source",
            url="https://test.example.com",
            description="Test update source",
        )

        assert source.key == 3
        post_call = mock_client._request.call_args_list[0]
        assert post_call[0] == ("POST", "update_sources")

    def test_update_source(self, mock_client: MagicMock) -> None:
        """Test updating a source."""
        mock_client._request.side_effect = [
            None,  # PUT response
            {"$key": 1, "name": "Updated Source"},  # GET response
        ]

        manager = UpdateSourceManager(mock_client)
        source = manager.update(1, name="Updated Source")

        assert source["name"] == "Updated Source"
        put_call = mock_client._request.call_args_list[0]
        assert put_call[0] == ("PUT", "update_sources/1")

    def test_delete_source(self, mock_client: MagicMock) -> None:
        """Test deleting a source."""
        mock_client._request.return_value = None

        manager = UpdateSourceManager(mock_client)
        manager.delete(1)

        mock_client._request.assert_called_with("DELETE", "update_sources/1")

    def test_action(self, mock_client: MagicMock) -> None:
        """Test performing an action on a source."""
        mock_client._request.return_value = {"task": 123}

        manager = UpdateSourceManager(mock_client)
        result = manager.action(1, "refresh")

        assert result == {"task": 123}
        mock_client._request.assert_called_with(
            "POST", "update_actions", json_data={"source": 1, "action": "refresh"}
        )

    def test_get_status(self, mock_client: MagicMock) -> None:
        """Test getting status for a source."""
        mock_client._request.return_value = [
            {"$key": 1, "source": 1, "status": "idle"},
        ]

        manager = UpdateSourceManager(mock_client)
        status = manager.get_status(1)

        assert isinstance(status, UpdateSourceStatus)
        assert status["status"] == "idle"

    def test_packages_returns_scoped_manager(self, mock_client: MagicMock) -> None:
        """Test packages method returns scoped manager."""
        manager = UpdateSourceManager(mock_client)
        pkg_manager = manager.packages(1)

        assert isinstance(pkg_manager, UpdateSourcePackageManager)
        assert pkg_manager._source_key == 1


class TestUpdateSource:
    """Tests for UpdateSource resource object."""

    def test_is_enabled(self, mock_client: MagicMock) -> None:
        """Test is_enabled property."""
        manager = UpdateSourceManager(mock_client)
        source = UpdateSource({"$key": 1, "enabled": True}, manager)
        assert source.is_enabled is True

    def test_is_not_enabled(self, mock_client: MagicMock) -> None:
        """Test is_enabled returns False."""
        manager = UpdateSourceManager(mock_client)
        source = UpdateSource({"$key": 1, "enabled": False}, manager)
        assert source.is_enabled is False

    def test_status_returns_scoped_manager(self, mock_client: MagicMock) -> None:
        """Test status property returns scoped manager."""
        manager = UpdateSourceManager(mock_client)
        source = UpdateSource({"$key": 1}, manager)
        status_manager = source.status

        assert isinstance(status_manager, UpdateSourceStatusManager)
        assert status_manager._source_key == 1

    def test_packages_returns_scoped_manager(self, mock_client: MagicMock) -> None:
        """Test packages property returns scoped manager."""
        manager = UpdateSourceManager(mock_client)
        source = UpdateSource({"$key": 1}, manager)
        pkg_manager = source.packages

        assert isinstance(pkg_manager, UpdateSourcePackageManager)
        assert pkg_manager._source_key == 1

    def test_get_status(self, mock_client: MagicMock) -> None:
        """Test get_status method."""
        mock_client._request.return_value = [
            {"$key": 1, "source": 1, "status": "idle"},
        ]

        manager = UpdateSourceManager(mock_client)
        source = UpdateSource({"$key": 1}, manager)
        status = source.get_status()

        assert isinstance(status, UpdateSourceStatus)

    def test_refresh(self, mock_client: MagicMock) -> None:
        """Test refresh method."""
        mock_client._request.return_value = {"task": 123}

        manager = UpdateSourceManager(mock_client)
        source = UpdateSource({"$key": 1}, manager)
        result = source.refresh()

        assert result == {"task": 123}


# =============================================================================
# UpdatePackageManager Tests
# =============================================================================


class TestUpdatePackageManager:
    """Tests for UpdatePackageManager."""

    def test_init(self, mock_client: MagicMock) -> None:
        """Test manager initialization."""
        manager = UpdatePackageManager(mock_client)
        assert manager._client == mock_client
        assert manager._endpoint == "update_packages"

    def test_list_returns_packages(self, mock_client: MagicMock) -> None:
        """Test listing packages."""
        mock_client._request.return_value = [
            {"$key": "yb-system", "name": "yb-system", "version": "26.0.1.2"},
            {"$key": "yb-cloud", "name": "yb-cloud", "version": "26.0.1.2"},
        ]

        manager = UpdatePackageManager(mock_client)
        packages = manager.list()

        assert len(packages) == 2
        assert isinstance(packages[0], UpdatePackage)

    def test_list_with_branch_filter(self, mock_client: MagicMock) -> None:
        """Test listing with branch filter."""
        mock_client._request.return_value = []

        manager = UpdatePackageManager(mock_client)
        manager.list(branch=1)

        call_args = mock_client._request.call_args
        assert "branch eq 1" in call_args[1]["params"]["filter"]

    def test_get_by_key(self, mock_client: MagicMock) -> None:
        """Test getting package by key (name)."""
        mock_client._request.return_value = {
            "$key": "yb-system",
            "name": "yb-system",
            "version": "26.0.1.2",
        }

        manager = UpdatePackageManager(mock_client)
        pkg = manager.get(key="yb-system")

        assert isinstance(pkg, UpdatePackage)
        assert pkg.key == "yb-system"

    def test_get_by_name(self, mock_client: MagicMock) -> None:
        """Test getting package by name (alias for key)."""
        mock_client._request.return_value = {
            "$key": "yb-cloud",
            "name": "yb-cloud",
            "version": "26.0.1.2",
        }

        manager = UpdatePackageManager(mock_client)
        pkg = manager.get(name="yb-cloud")

        assert pkg["name"] == "yb-cloud"

    def test_get_not_found(self, mock_client: MagicMock) -> None:
        """Test get raises NotFoundError when not found."""
        mock_client._request.return_value = None

        manager = UpdatePackageManager(mock_client)
        with pytest.raises(NotFoundError):
            manager.get(key="nonexistent")

    def test_get_requires_identifier(self, mock_client: MagicMock) -> None:
        """Test get raises ValueError without identifier."""
        manager = UpdatePackageManager(mock_client)
        with pytest.raises(ValueError, match="Either key or name"):
            manager.get()


class TestUpdatePackage:
    """Tests for UpdatePackage resource object."""

    def test_key_is_string(self, mock_client: MagicMock) -> None:
        """Test key property returns string."""
        manager = UpdatePackageManager(mock_client)
        pkg = UpdatePackage({"$key": "yb-system"}, manager)
        assert pkg.key == "yb-system"
        assert isinstance(pkg.key, str)

    def test_key_falls_back_to_name(self, mock_client: MagicMock) -> None:
        """Test key property falls back to name if $key not present."""
        manager = UpdatePackageManager(mock_client)
        pkg = UpdatePackage({"name": "yb-cloud"}, manager)
        assert pkg.key == "yb-cloud"

    def test_key_raises_without_value(self, mock_client: MagicMock) -> None:
        """Test key property raises ValueError if not set."""
        manager = UpdatePackageManager(mock_client)
        pkg = UpdatePackage({}, manager)
        with pytest.raises(ValueError):
            _ = pkg.key

    def test_branch_key(self, mock_client: MagicMock) -> None:
        """Test branch_key property."""
        manager = UpdatePackageManager(mock_client)
        pkg = UpdatePackage({"$key": "yb-system", "branch": 2}, manager)
        assert pkg.branch_key == 2

    def test_is_optional(self, mock_client: MagicMock) -> None:
        """Test is_optional property."""
        manager = UpdatePackageManager(mock_client)
        pkg = UpdatePackage({"$key": "yb-optional", "optional": True}, manager)
        assert pkg.is_optional is True


# =============================================================================
# UpdateSettingsManager Tests
# =============================================================================


class TestUpdateSettingsManager:
    """Tests for UpdateSettingsManager."""

    def test_init(self, mock_client: MagicMock) -> None:
        """Test manager initialization."""
        manager = UpdateSettingsManager(mock_client)
        assert manager._client == mock_client
        assert manager._endpoint == "update_settings"

    def test_get_returns_settings(self, mock_client: MagicMock) -> None:
        """Test getting update settings."""
        mock_client._request.return_value = {
            "$key": 1,
            "name": "Update Manager",
            "source": 1,
            "branch": 2,
            "auto_refresh": True,
        }

        manager = UpdateSettingsManager(mock_client)
        settings = manager.get()

        assert isinstance(settings, UpdateSettings)
        assert settings.key == 1
        assert settings["auto_refresh"] is True

    def test_get_always_fetches_key_1(self, mock_client: MagicMock) -> None:
        """Test get always fetches key=1 (singleton)."""
        mock_client._request.return_value = {"$key": 1}

        manager = UpdateSettingsManager(mock_client)
        manager.get(key=999)  # Key is ignored

        mock_client._request.assert_called()
        assert "update_settings/1" in mock_client._request.call_args[0][1]

    def test_update_settings(self, mock_client: MagicMock) -> None:
        """Test updating settings."""
        mock_client._request.side_effect = [
            None,  # PUT response
            {"$key": 1, "auto_refresh": True, "update_time": "02:00"},  # GET response
        ]

        manager = UpdateSettingsManager(mock_client)
        settings = manager.update(auto_refresh=True, update_time="02:00")

        assert settings["auto_refresh"] is True
        put_call = mock_client._request.call_args_list[0]
        assert put_call[0] == ("PUT", "update_settings/1")
        assert put_call[1]["json_data"]["auto_refresh"] is True
        assert put_call[1]["json_data"]["update_time"] == "02:00"

    def test_update_no_changes_returns_current(self, mock_client: MagicMock) -> None:
        """Test update with no changes returns current settings."""
        mock_client._request.return_value = {"$key": 1}

        manager = UpdateSettingsManager(mock_client)
        _ = manager.update()

        # Should only call GET, not PUT
        assert mock_client._request.call_count == 1

    def test_check_action(self, mock_client: MagicMock) -> None:
        """Test check action."""
        mock_client._request.return_value = {"task": 123}

        manager = UpdateSettingsManager(mock_client)
        result = manager.check()

        assert result == {"task": 123}
        mock_client._request.assert_called_with(
            "POST", "update_settings/1", json_data={"action": "check"}
        )

    def test_download_action(self, mock_client: MagicMock) -> None:
        """Test download action."""
        mock_client._request.return_value = {"task": 124}

        manager = UpdateSettingsManager(mock_client)
        result = manager.download()

        assert result == {"task": 124}
        mock_client._request.assert_called_with(
            "POST", "update_settings/1", json_data={"action": "download"}
        )

    def test_install_action(self, mock_client: MagicMock) -> None:
        """Test install action."""
        mock_client._request.return_value = {"task": 125}

        manager = UpdateSettingsManager(mock_client)
        result = manager.install()

        assert result == {"task": 125}
        mock_client._request.assert_called_with(
            "POST", "update_settings/1", json_data={"action": "install"}
        )

    def test_update_all_action(self, mock_client: MagicMock) -> None:
        """Test update_all action."""
        mock_client._request.return_value = {"task": 126}

        manager = UpdateSettingsManager(mock_client)
        result = manager.update_all()

        assert result == {"task": 126}
        mock_client._request.assert_called_with(
            "POST", "update_settings/1", json_data={"action": "all", "force": False}
        )

    def test_update_all_with_force(self, mock_client: MagicMock) -> None:
        """Test update_all action with force=True."""
        mock_client._request.return_value = {"task": 127}

        manager = UpdateSettingsManager(mock_client)
        result = manager.update_all(force=True)

        assert result == {"task": 127}
        mock_client._request.assert_called_with(
            "POST", "update_settings/1", json_data={"action": "all", "force": True}
        )


class TestUpdateSettings:
    """Tests for UpdateSettings resource object."""

    def test_source_key(self, mock_client: MagicMock) -> None:
        """Test source_key property."""
        manager = UpdateSettingsManager(mock_client)
        settings = UpdateSettings({"$key": 1, "source": 2}, manager)
        assert settings.source_key == 2

    def test_source_name_from_dict(self, mock_client: MagicMock) -> None:
        """Test source_name property from dict."""
        manager = UpdateSettingsManager(mock_client)
        settings = UpdateSettings({"$key": 1, "source": {"name": "Verge.io Updates"}}, manager)
        assert settings.source_name == "Verge.io Updates"

    def test_source_name_from_display(self, mock_client: MagicMock) -> None:
        """Test source_name property from display field."""
        manager = UpdateSettingsManager(mock_client)
        settings = UpdateSettings({"$key": 1, "source_display": "Verge.io Updates"}, manager)
        assert settings.source_name == "Verge.io Updates"

    def test_branch_key(self, mock_client: MagicMock) -> None:
        """Test branch_key property."""
        manager = UpdateSettingsManager(mock_client)
        settings = UpdateSettings({"$key": 1, "branch": 3}, manager)
        assert settings.branch_key == 3

    def test_branch_name_from_dict(self, mock_client: MagicMock) -> None:
        """Test branch_name property from dict."""
        manager = UpdateSettingsManager(mock_client)
        settings = UpdateSettings({"$key": 1, "branch": {"name": "stable-4.13"}}, manager)
        assert settings.branch_name == "stable-4.13"

    def test_is_auto_refresh(self, mock_client: MagicMock) -> None:
        """Test is_auto_refresh property."""
        manager = UpdateSettingsManager(mock_client)
        settings = UpdateSettings({"$key": 1, "auto_refresh": True}, manager)
        assert settings.is_auto_refresh is True

    def test_is_auto_update(self, mock_client: MagicMock) -> None:
        """Test is_auto_update property."""
        manager = UpdateSettingsManager(mock_client)
        settings = UpdateSettings({"$key": 1, "auto_update": True}, manager)
        assert settings.is_auto_update is True

    def test_is_installed(self, mock_client: MagicMock) -> None:
        """Test is_installed property."""
        manager = UpdateSettingsManager(mock_client)
        settings = UpdateSettings({"$key": 1, "installed": True}, manager)
        assert settings.is_installed is True

    def test_is_reboot_required(self, mock_client: MagicMock) -> None:
        """Test is_reboot_required property."""
        manager = UpdateSettingsManager(mock_client)
        settings = UpdateSettings({"$key": 1, "reboot_required": True}, manager)
        assert settings.is_reboot_required is True

    def test_is_applying_updates(self, mock_client: MagicMock) -> None:
        """Test is_applying_updates property."""
        manager = UpdateSettingsManager(mock_client)
        settings = UpdateSettings({"$key": 1, "applying_updates": True}, manager)
        assert settings.is_applying_updates is True

    def test_check_method(self, mock_client: MagicMock) -> None:
        """Test check method on settings object."""
        mock_client._request.return_value = {"task": 123}

        manager = UpdateSettingsManager(mock_client)
        settings = UpdateSettings({"$key": 1}, manager)
        result = settings.check()

        assert result == {"task": 123}

    def test_download_method(self, mock_client: MagicMock) -> None:
        """Test download method on settings object."""
        mock_client._request.return_value = {"task": 124}

        manager = UpdateSettingsManager(mock_client)
        settings = UpdateSettings({"$key": 1}, manager)
        result = settings.download()

        assert result == {"task": 124}

    def test_install_method(self, mock_client: MagicMock) -> None:
        """Test install method on settings object."""
        mock_client._request.return_value = {"task": 125}

        manager = UpdateSettingsManager(mock_client)
        settings = UpdateSettings({"$key": 1}, manager)
        result = settings.install()

        assert result == {"task": 125}

    def test_update_all_method(self, mock_client: MagicMock) -> None:
        """Test update_all method on settings object."""
        mock_client._request.return_value = {"task": 126}

        manager = UpdateSettingsManager(mock_client)
        settings = UpdateSettings({"$key": 1}, manager)
        result = settings.update_all(force=True)

        assert result == {"task": 126}


# =============================================================================
# UpdateDashboardManager Tests
# =============================================================================


class TestUpdateDashboardManager:
    """Tests for UpdateDashboardManager."""

    def test_init(self, mock_client: MagicMock) -> None:
        """Test manager initialization."""
        manager = UpdateDashboardManager(mock_client)
        assert manager._client == mock_client
        assert manager._endpoint == "update_dashboard"

    def test_get_returns_dashboard(self, mock_client: MagicMock) -> None:
        """Test getting update dashboard."""
        mock_client._request.return_value = {
            "logs": [{"level": "message", "text": "Update complete"}],
            "packages": [{"name": "yb-system", "version": "26.0.1.2"}],
            "branches": [{"name": "stable-4.13"}],
            "settings": {"auto_refresh": True},
            "node_count": {"$count": 2},
            "counts": {"event_count": 3, "task_count": 1},
        }

        manager = UpdateDashboardManager(mock_client)
        dashboard = manager.get()

        assert isinstance(dashboard, UpdateDashboard)

    def test_get_not_found(self, mock_client: MagicMock) -> None:
        """Test get raises NotFoundError when not found."""
        mock_client._request.return_value = None

        manager = UpdateDashboardManager(mock_client)
        with pytest.raises(NotFoundError):
            manager.get()


class TestUpdateDashboard:
    """Tests for UpdateDashboard resource object."""

    def test_node_count_from_dict(self, mock_client: MagicMock) -> None:
        """Test node_count property from dict."""
        manager = UpdateDashboardManager(mock_client)
        dashboard = UpdateDashboard({"node_count": {"$count": 3}}, manager)
        assert dashboard.node_count == 3

    def test_node_count_from_int(self, mock_client: MagicMock) -> None:
        """Test node_count property from int."""
        manager = UpdateDashboardManager(mock_client)
        dashboard = UpdateDashboard({"node_count": 4}, manager)
        assert dashboard.node_count == 4

    def test_event_count(self, mock_client: MagicMock) -> None:
        """Test event_count property."""
        manager = UpdateDashboardManager(mock_client)
        dashboard = UpdateDashboard({"counts": {"event_count": 5}}, manager)
        assert dashboard.event_count == 5

    def test_task_count(self, mock_client: MagicMock) -> None:
        """Test task_count property."""
        manager = UpdateDashboardManager(mock_client)
        dashboard = UpdateDashboard({"counts": {"task_count": 2}}, manager)
        assert dashboard.task_count == 2

    def test_get_settings(self, mock_client: MagicMock) -> None:
        """Test get_settings method."""
        manager = UpdateDashboardManager(mock_client)
        dashboard = UpdateDashboard({"settings": {"auto_refresh": True, "branch": 1}}, manager)
        settings = dashboard.get_settings()

        assert settings["auto_refresh"] is True
        assert settings["branch"] == 1

    def test_get_packages(self, mock_client: MagicMock) -> None:
        """Test get_packages method."""
        manager = UpdateDashboardManager(mock_client)
        dashboard = UpdateDashboard(
            {
                "packages": [
                    {"name": "yb-system", "version": "26.0.1.2"},
                    {"name": "yb-cloud", "version": "26.0.1.2"},
                ]
            },
            manager,
        )
        packages = dashboard.get_packages()

        assert len(packages) == 2
        assert packages[0]["name"] == "yb-system"

    def test_get_branches(self, mock_client: MagicMock) -> None:
        """Test get_branches method."""
        manager = UpdateDashboardManager(mock_client)
        dashboard = UpdateDashboard(
            {
                "branches": [
                    {"name": "stable-4.12"},
                    {"name": "stable-4.13"},
                ]
            },
            manager,
        )
        branches = dashboard.get_branches()

        assert len(branches) == 2
        assert branches[1]["name"] == "stable-4.13"

    def test_get_logs(self, mock_client: MagicMock) -> None:
        """Test get_logs method."""
        manager = UpdateDashboardManager(mock_client)
        dashboard = UpdateDashboard(
            {
                "logs": [
                    {"level": "message", "text": "Update started"},
                    {"level": "message", "text": "Update complete"},
                ]
            },
            manager,
        )
        logs = dashboard.get_logs()

        assert len(logs) == 2
        assert logs[0]["text"] == "Update started"

    def test_get_settings_empty(self, mock_client: MagicMock) -> None:
        """Test get_settings returns empty dict when not present."""
        manager = UpdateDashboardManager(mock_client)
        dashboard = UpdateDashboard({}, manager)
        assert dashboard.get_settings() == {}

    def test_get_packages_empty(self, mock_client: MagicMock) -> None:
        """Test get_packages returns empty list when not present."""
        manager = UpdateDashboardManager(mock_client)
        dashboard = UpdateDashboard({}, manager)
        assert dashboard.get_packages() == []

    def test_get_branches_empty(self, mock_client: MagicMock) -> None:
        """Test get_branches returns empty list when not present."""
        manager = UpdateDashboardManager(mock_client)
        dashboard = UpdateDashboard({}, manager)
        assert dashboard.get_branches() == []

    def test_get_logs_empty(self, mock_client: MagicMock) -> None:
        """Test get_logs returns empty list when not present."""
        manager = UpdateDashboardManager(mock_client)
        dashboard = UpdateDashboard({}, manager)
        assert dashboard.get_logs() == []
