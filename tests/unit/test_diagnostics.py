"""Unit tests for system diagnostic resource managers."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from pyvergeos.exceptions import NotFoundError, VergeTimeoutError
from pyvergeos.resources.diagnostics import (
    SystemDiagnostic,
    SystemDiagnosticManager,
)


@pytest.fixture
def mock_client() -> MagicMock:
    """Create a mock VergeClient."""
    client = MagicMock()
    client._request = MagicMock()
    return client


@pytest.fixture
def sample_diag_data() -> dict[str, Any]:
    """Sample diagnostic data from API."""
    return {
        "$key": 1,
        "name": "issue-2024-01",
        "description": "Network connectivity issue",
        "status": "complete",
        "status_info": "Bundle ready",
        "file": 42,
        "send2support": False,
        "timestamp": 1704067200,
    }


@pytest.fixture
def sample_building_diag() -> dict[str, Any]:
    """Sample building diagnostic data."""
    return {
        "$key": 2,
        "name": "issue-2024-02",
        "description": "",
        "status": "building",
        "status_info": "Collecting logs...",
        "file": None,
        "send2support": False,
        "timestamp": 1704067200,
    }


@pytest.fixture
def sample_error_diag() -> dict[str, Any]:
    """Sample error diagnostic data."""
    return {
        "$key": 3,
        "name": "issue-2024-03",
        "description": "",
        "status": "error",
        "status_info": "Failed to collect data",
        "file": None,
        "send2support": False,
        "timestamp": 1704067200,
    }


# =============================================================================
# SystemDiagnostic Tests
# =============================================================================


class TestSystemDiagnostic:
    """Tests for SystemDiagnostic resource object."""

    def test_name(self, sample_diag_data: dict[str, Any]) -> None:
        diag = SystemDiagnostic(sample_diag_data, MagicMock())
        assert diag.name == "issue-2024-01"

    def test_description(self, sample_diag_data: dict[str, Any]) -> None:
        diag = SystemDiagnostic(sample_diag_data, MagicMock())
        assert diag.description == "Network connectivity issue"

    def test_status_complete(self, sample_diag_data: dict[str, Any]) -> None:
        diag = SystemDiagnostic(sample_diag_data, MagicMock())
        assert diag.status == "complete"
        assert diag.is_complete is True
        assert diag.is_error is False
        assert diag.is_building is False

    def test_status_building(self, sample_building_diag: dict[str, Any]) -> None:
        diag = SystemDiagnostic(sample_building_diag, MagicMock())
        assert diag.status == "building"
        assert diag.is_building is True
        assert diag.is_complete is False

    def test_status_error(self, sample_error_diag: dict[str, Any]) -> None:
        diag = SystemDiagnostic(sample_error_diag, MagicMock())
        assert diag.status == "error"
        assert diag.is_error is True

    def test_status_info(self, sample_diag_data: dict[str, Any]) -> None:
        diag = SystemDiagnostic(sample_diag_data, MagicMock())
        assert diag.status_info == "Bundle ready"

    def test_file_key(self, sample_diag_data: dict[str, Any]) -> None:
        diag = SystemDiagnostic(sample_diag_data, MagicMock())
        assert diag.file_key == 42

    def test_file_key_none(self, sample_building_diag: dict[str, Any]) -> None:
        diag = SystemDiagnostic(sample_building_diag, MagicMock())
        assert diag.file_key is None

    def test_timestamp(self, sample_diag_data: dict[str, Any]) -> None:
        diag = SystemDiagnostic(sample_diag_data, MagicMock())
        assert diag.timestamp == 1704067200

    def test_defaults_when_empty(self) -> None:
        diag = SystemDiagnostic({}, MagicMock())
        assert diag.name == ""
        assert diag.description == ""
        assert diag.status == "initializing"
        assert diag.status_info is None
        assert diag.file_key is None
        assert diag.timestamp is None


# =============================================================================
# SystemDiagnosticManager Tests
# =============================================================================


class TestSystemDiagnosticManager:
    """Tests for SystemDiagnosticManager."""

    def test_endpoint(self, mock_client: MagicMock) -> None:
        manager = SystemDiagnosticManager(mock_client)
        assert manager._endpoint == "system_diagnostics"

    def test_list(
        self,
        mock_client: MagicMock,
        sample_diag_data: dict[str, Any],
    ) -> None:
        mock_client._request.return_value = [sample_diag_data]
        manager = SystemDiagnosticManager(mock_client)
        results = manager.list()
        assert len(results) == 1
        assert isinstance(results[0], SystemDiagnostic)

    def test_list_empty(self, mock_client: MagicMock) -> None:
        mock_client._request.return_value = None
        manager = SystemDiagnosticManager(mock_client)
        assert manager.list() == []

    def test_get_by_key(
        self,
        mock_client: MagicMock,
        sample_diag_data: dict[str, Any],
    ) -> None:
        mock_client._request.return_value = sample_diag_data
        manager = SystemDiagnosticManager(mock_client)
        diag = manager.get(1)
        assert isinstance(diag, SystemDiagnostic)
        assert diag.name == "issue-2024-01"

    def test_get_by_name(
        self,
        mock_client: MagicMock,
        sample_diag_data: dict[str, Any],
    ) -> None:
        mock_client._request.return_value = [sample_diag_data]
        manager = SystemDiagnosticManager(mock_client)
        diag = manager.get(name="issue-2024-01")
        assert diag.name == "issue-2024-01"

    def test_get_not_found(self, mock_client: MagicMock) -> None:
        mock_client._request.return_value = None
        manager = SystemDiagnosticManager(mock_client)
        with pytest.raises(NotFoundError):
            manager.get(999)

    def test_get_by_name_not_found(self, mock_client: MagicMock) -> None:
        mock_client._request.return_value = []
        manager = SystemDiagnosticManager(mock_client)
        with pytest.raises(NotFoundError):
            manager.get(name="nonexistent")

    def test_get_no_args(self, mock_client: MagicMock) -> None:
        manager = SystemDiagnosticManager(mock_client)
        with pytest.raises(ValueError, match="Either key or name"):
            manager.get()

    def test_create(
        self,
        mock_client: MagicMock,
        sample_diag_data: dict[str, Any],
    ) -> None:
        mock_client._request.return_value = sample_diag_data
        manager = SystemDiagnosticManager(mock_client)
        manager.create(
            name="issue-2024-01",
            description="Network connectivity issue",
        )

        post_call = mock_client._request.call_args_list[0]
        assert post_call.args[0] == "POST"
        assert post_call.args[1] == "system_diagnostics"
        body = post_call.kwargs["json_data"]
        assert body["name"] == "issue-2024-01"
        assert body["description"] == "Network connectivity issue"

    def test_create_with_send2support(
        self,
        mock_client: MagicMock,
        sample_diag_data: dict[str, Any],
    ) -> None:
        mock_client._request.return_value = sample_diag_data
        manager = SystemDiagnosticManager(mock_client)
        manager.create(name="test", send2support=True)

        post_call = mock_client._request.call_args_list[0]
        body = post_call.kwargs["json_data"]
        assert body["send2support"] is True

    @patch("pyvergeos.resources.diagnostics.time.sleep")
    def test_wait_complete(
        self,
        mock_sleep: MagicMock,
        mock_client: MagicMock,
        sample_diag_data: dict[str, Any],
    ) -> None:
        mock_client._request.return_value = sample_diag_data
        manager = SystemDiagnosticManager(mock_client)
        diag = manager.wait(1, timeout=10)
        assert diag.is_complete

    @patch("pyvergeos.resources.diagnostics.time.sleep")
    @patch("pyvergeos.resources.diagnostics.time.monotonic")
    def test_wait_timeout(
        self,
        mock_monotonic: MagicMock,
        mock_sleep: MagicMock,
        mock_client: MagicMock,
        sample_building_diag: dict[str, Any],
    ) -> None:
        mock_client._request.return_value = sample_building_diag
        mock_monotonic.side_effect = [0.0, 0.0, 11.0]
        manager = SystemDiagnosticManager(mock_client)
        with pytest.raises(VergeTimeoutError, match="did not complete"):
            manager.wait(2, timeout=10)

    def test_send_to_support(self, mock_client: MagicMock) -> None:
        manager = SystemDiagnosticManager(mock_client)
        manager.send_to_support(1)

        call_args = mock_client._request.call_args
        assert call_args.args[0] == "POST"
        assert call_args.args[1] == "system_diagnostic_actions"
        body = call_args.kwargs["json_data"]
        assert body["system_diagnostic"] == 1
        assert body["action"] == "send2support"
