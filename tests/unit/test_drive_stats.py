"""Unit tests for the machine drive stats manager (issue #128)."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from pyvergeos.exceptions import NotFoundError
from pyvergeos.resources.drive_stats import (
    MachineDriveStats,
    MachineDriveStatsManager,
)


@pytest.fixture
def mock_client() -> MagicMock:
    client = MagicMock()
    client._request = MagicMock()
    return client


@pytest.fixture
def sample_stats() -> dict[str, Any]:
    # $key deliberately differs from parent_drive, the crux of issue #128
    return {
        "$key": 34,
        "parent_drive": 39,
        "reads": 100,
        "writes": 2048,
        "read_bytes": 400000,
        "write_bytes": 848000000,
        "rops": 0,
        "wops": 12,
        "rbps": 0,
        "wbps": 500000,
        "totalbps": 500000,
        "used_bytes": 1000000,
        "max_bytes": 8000000,
        "util": 0.15,
        "service_time": 1.2,
    }


class TestMachineDriveStatsModel:
    def test_drive_key_is_parent_drive_not_own_key(self, sample_stats: dict[str, Any]) -> None:
        """The whole point of #128: drive_key is parent_drive, not $key."""
        stats = MachineDriveStats(sample_stats, MagicMock())
        assert stats.drive_key == 39
        assert stats.get("$key") == 34
        assert stats.drive_key != stats.get("$key")

    def test_counters(self, sample_stats: dict[str, Any]) -> None:
        stats = MachineDriveStats(sample_stats, MagicMock())
        assert stats.writes == 2048
        assert stats.write_bytes == 848000000
        assert stats.reads == 100
        assert stats.write_ops_per_sec == 12
        assert stats.total_bps == 500000

    def test_has_booted_true_when_writes_present(self, sample_stats: dict[str, Any]) -> None:
        assert MachineDriveStats(sample_stats, MagicMock()).has_booted is True

    def test_has_booted_false_without_writes(self) -> None:
        """A VM at 'no bootable device' reports running but never writes."""
        stats = MachineDriveStats({"$key": 1, "parent_drive": 2, "writes": 0}, MagicMock())
        assert stats.has_booted is False

    def test_has_booted_ignores_reads(self) -> None:
        """Firmware reads the boot sector, so reads must not imply a boot."""
        stats = MachineDriveStats(
            {"$key": 1, "parent_drive": 2, "reads": 5000, "writes": 0}, MagicMock()
        )
        assert stats.has_booted is False

    def test_missing_counters_default_to_zero(self) -> None:
        stats = MachineDriveStats({"$key": 1, "parent_drive": 2}, MagicMock())
        assert stats.writes == 0
        assert stats.write_bytes == 0
        assert stats.utilization == 0.0


class TestMachineDriveStatsManager:
    def test_get_scoped_filters_by_parent_drive(
        self, mock_client: MagicMock, sample_stats: dict[str, Any]
    ) -> None:
        """Scoped access must filter on parent_drive, never path-key (issue #128)."""
        mock_client._request.return_value = [sample_stats]
        manager = MachineDriveStatsManager(mock_client, drive_key=39)
        stats = manager.get()
        call = mock_client._request.call_args
        assert call.args[0] == "GET"
        assert call.args[1] == "machine_drive_stats"
        assert "parent_drive eq 39" in call.kwargs["params"]["filter"]
        assert stats.drive_key == 39

    def test_get_by_key_uses_path(
        self, mock_client: MagicMock, sample_stats: dict[str, Any]
    ) -> None:
        mock_client._request.return_value = sample_stats
        manager = MachineDriveStatsManager(mock_client)
        stats = manager.get(key=34)
        call = mock_client._request.call_args
        assert call.args[1] == "machine_drive_stats/34"
        assert stats.drive_key == 39

    def test_get_scoped_not_found(self, mock_client: MagicMock) -> None:
        mock_client._request.return_value = []
        manager = MachineDriveStatsManager(mock_client, drive_key=999)
        with pytest.raises(NotFoundError):
            manager.get()

    def test_get_no_scope_no_key_raises(self, mock_client: MagicMock) -> None:
        manager = MachineDriveStatsManager(mock_client)
        with pytest.raises(ValueError, match="Either key or a scoped drive_key"):
            manager.get()

    def test_list_defaults_fields_so_rows_are_populated(
        self, mock_client: MagicMock, sample_stats: dict[str, Any]
    ) -> None:
        """Bare list() must request default fields; the endpoint else returns $key only."""
        mock_client._request.return_value = [sample_stats]
        manager = MachineDriveStatsManager(mock_client)
        rows = manager.list()
        call = mock_client._request.call_args
        assert "parent_drive" in call.kwargs["params"]["fields"]
        assert rows[0].drive_key == 39

    def test_list_filter_passthrough(
        self, mock_client: MagicMock, sample_stats: dict[str, Any]
    ) -> None:
        mock_client._request.return_value = [sample_stats]
        MachineDriveStatsManager(mock_client).list(filter="parent_drive eq 39")
        call = mock_client._request.call_args
        assert "parent_drive eq 39" in call.kwargs["params"]["filter"]


class TestDriveScopedAccessor:
    def test_drive_exposes_scoped_drive_stats(self, mock_client: MagicMock) -> None:
        from pyvergeos.resources.drives import Drive

        mgr = MagicMock()
        mgr._client = mock_client
        drive = Drive({"$key": 16}, mgr)
        scoped = drive.drive_stats
        assert isinstance(scoped, MachineDriveStatsManager)
        assert scoped._drive_key == 16


class TestMachineDriveStatsCoverage:
    """Exercise the remaining accessors and get() branches."""

    def test_all_accessors_on_populated_row(self, sample_stats: dict[str, Any]) -> None:
        s = MachineDriveStats(sample_stats, MagicMock())
        assert s.read_bytes == 400000
        assert s.read_ops_per_sec == 0
        assert s.read_bps == 0
        assert s.write_bps == 500000
        assert s.used_bytes == 1000000
        assert s.max_bytes == 8000000
        assert s.service_time == pytest.approx(1.2)
        assert s.utilization == pytest.approx(0.15)

    def test_get_by_key_none_response_raises(self, mock_client: MagicMock) -> None:
        mock_client._request.return_value = None
        with pytest.raises(NotFoundError, match="not found"):
            MachineDriveStatsManager(mock_client).get(key=1)

    def test_get_by_key_non_dict_response_raises(self, mock_client: MagicMock) -> None:
        mock_client._request.return_value = ["unexpected"]
        with pytest.raises(NotFoundError, match="invalid response"):
            MachineDriveStatsManager(mock_client).get(key=1)

    def test_scoped_none_response_raises(self, mock_client: MagicMock) -> None:
        mock_client._request.return_value = None
        with pytest.raises(NotFoundError):
            MachineDriveStatsManager(mock_client, drive_key=1).get()

    def test_scoped_single_dict_response_is_accepted(
        self, mock_client: MagicMock, sample_stats: dict[str, Any]
    ) -> None:
        mock_client._request.return_value = sample_stats
        s = MachineDriveStatsManager(mock_client, drive_key=39).get()
        assert s.drive_key == 39

    def test_list_with_explicit_fields_is_passed_through(
        self, mock_client: MagicMock, sample_stats: dict[str, Any]
    ) -> None:
        mock_client._request.return_value = [sample_stats]
        MachineDriveStatsManager(mock_client).list(fields=["$key", "parent_drive"])
        assert "parent_drive" in mock_client._request.call_args.kwargs["params"]["fields"]


def test_drive_stats_get_by_key_with_explicit_fields(
    mock_client: MagicMock, sample_stats: dict[str, Any]
) -> None:
    mock_client._request.return_value = sample_stats
    MachineDriveStatsManager(mock_client).get(key=1, fields=["$key", "parent_drive"])
    assert "parent_drive" in mock_client._request.call_args.kwargs["params"]["fields"]
