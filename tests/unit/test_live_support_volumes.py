"""Unit tests for NAS volume teardown helpers."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from pyvergeos.exceptions import APIError, NotFoundError
from tests.integration.live_support import (
    destroy_leftover_antivirus_volumes,
    destroy_volume,
    is_leftover_antivirus_volume,
)

_ONLINE = "Unable to delete machine drive: Unable to delete online drive"


def _client() -> MagicMock:
    return MagicMock()


def _volume(key: str, name: str, *, enabled: bool = True) -> MagicMock:
    volume = MagicMock()
    volume.key = key
    volume.get.side_effect = lambda field, default=None: {
        "name": name,
        "enabled": enabled,
    }.get(field, default)
    return volume


class TestIsLeftoverAntivirusVolume:
    """Name gate for sweeping volumes left by earlier antivirus runs."""

    @pytest.mark.parametrize(
        "name",
        ["pstest-antivirus", "pstest-av-f73b3826", "pstest-av-ce3a21d3", "pstest-av-ab"],
    )
    def test_suite_names_match(self, name: str) -> None:
        assert is_leftover_antivirus_volume(name) is True

    @pytest.mark.parametrize(
        "name",
        [
            "FileShare",
            "pstest-av-",
            "pstest-av-backup",
            "pstest-av-F73B3826",
            "pstest-antivirus-extra",
            "pytest-vol-crud",
            "",
        ],
    )
    def test_other_names_do_not_match(self, name: str) -> None:
        assert is_leftover_antivirus_volume(name) is False


class TestDestroyVolume:
    """Disable, then retry delete only while the drive is still online."""

    def test_disables_then_deletes(self) -> None:
        client = _client()
        client.nas_volumes.get.return_value = {"name": "pstest-av-abcd", "enabled": True}

        destroy_volume(client, "abc")

        client.nas_volumes.update.assert_called_once_with("abc", enabled=False)
        client.nas_volumes.delete.assert_called_once_with("abc")

    def test_disables_an_already_disabled_volume(self) -> None:
        client = _client()
        client.nas_volumes.get.return_value = {"name": "pstest-antivirus", "enabled": False}

        destroy_volume(client, "abc")

        client.nas_volumes.update.assert_called_once_with("abc", enabled=False)
        client.nas_volumes.delete.assert_called_once_with("abc")

    def test_returns_when_volume_is_already_gone(self) -> None:
        client = _client()
        client.nas_volumes.get.side_effect = NotFoundError("missing")

        destroy_volume(client, "abc")

        client.nas_volumes.update.assert_not_called()
        client.nas_volumes.delete.assert_not_called()

    def test_returns_when_disable_finds_volume_gone(self) -> None:
        client = _client()
        client.nas_volumes.get.return_value = {"name": "v", "enabled": True}
        client.nas_volumes.update.side_effect = NotFoundError("missing")

        destroy_volume(client, "abc")

        client.nas_volumes.delete.assert_not_called()

    def test_returns_when_delete_finds_volume_gone(self) -> None:
        client = _client()
        client.nas_volumes.get.return_value = {"name": "v", "enabled": True}
        client.nas_volumes.delete.side_effect = NotFoundError("missing")

        destroy_volume(client, "abc")

    def test_retries_while_drive_is_online(self) -> None:
        client = _client()
        client.nas_volumes.get.return_value = {"name": "pstest-av-abcd", "enabled": True}
        client.nas_volumes.delete.side_effect = [
            APIError(_ONLINE),
            APIError(_ONLINE),
            None,
        ]

        with (
            patch("tests.integration.live_support.time.monotonic", return_value=0.0),
            patch("tests.integration.live_support.time.sleep") as sleep,
        ):
            destroy_volume(client, "abc")

        assert client.nas_volumes.delete.call_count == 3
        assert sleep.call_count == 2
        sleep.assert_called_with(2.0)

    def test_raises_other_api_errors_immediately(self) -> None:
        client = _client()
        client.nas_volumes.get.return_value = {"name": "v", "enabled": True}
        client.nas_volumes.delete.side_effect = APIError("volume has shares")

        with (
            patch("tests.integration.live_support.time.monotonic", return_value=0.0),
            patch("tests.integration.live_support.time.sleep") as sleep,
            pytest.raises(APIError, match="volume has shares"),
        ):
            destroy_volume(client, "abc")

        sleep.assert_not_called()
        assert client.nas_volumes.delete.call_count == 1

    def test_raises_when_drive_stays_online(self) -> None:
        client = _client()
        client.nas_volumes.get.return_value = {"name": "pstest-av-abcd", "enabled": True}
        client.nas_volumes.delete.side_effect = APIError(_ONLINE)
        clock = iter((0.0, 100.0))

        with (
            patch(
                "tests.integration.live_support.time.monotonic",
                new=lambda: next(clock),
            ),
            patch("tests.integration.live_support.time.sleep") as sleep,
            pytest.raises(RuntimeError, match="pstest-av-abcd") as exc_info,
        ):
            destroy_volume(client, "abc", timeout=30)

        assert "abc" in str(exc_info.value)
        assert "online drive" in str(exc_info.value)
        sleep.assert_not_called()

    def test_accepts_a_volume_object(self) -> None:
        client = _client()
        client.nas_volumes.get.return_value = {"name": "v", "enabled": True}
        volume = _volume("vol-key", "v")

        destroy_volume(client, volume)

        client.nas_volumes.get.assert_called_once_with("vol-key")
        client.nas_volumes.delete.assert_called_once_with("vol-key")


class TestDestroyLeftoverAntivirusVolumes:
    """Sweep only the antivirus volumes this suite created."""

    def test_deletes_matching_volumes_only(self) -> None:
        client = _client()
        volumes = [
            _volume("legacy", "pstest-antivirus", enabled=False),
            _volume("disposable", "pstest-av-f73b3826"),
            _volume("keep", "FileShare"),
        ]
        client.nas_volumes.list.return_value = volumes

        def get(key: str) -> dict[str, object]:
            names = {
                "legacy": "pstest-antivirus",
                "disposable": "pstest-av-f73b3826",
                "keep": "FileShare",
            }
            return {"name": names[key], "enabled": True}

        client.nas_volumes.get.side_effect = get

        destroy_leftover_antivirus_volumes(client)

        deleted = [call.args[0] for call in client.nas_volumes.delete.call_args_list]
        assert deleted == ["legacy", "disposable"]
        updated = [call.args[0] for call in client.nas_volumes.update.call_args_list]
        assert updated == ["legacy", "disposable"]

    def test_keep_key_is_not_deleted(self) -> None:
        client = _client()
        client.nas_volumes.list.return_value = [
            _volume("current", "pstest-av-aaaaaaaa"),
            _volume("old", "pstest-av-bbbbbbbb"),
        ]
        client.nas_volumes.get.return_value = {"name": "pstest-av-bbbbbbbb", "enabled": True}

        destroy_leftover_antivirus_volumes(client, keep_key="current")

        client.nas_volumes.delete.assert_called_once_with("old")
        client.nas_volumes.get.assert_called_once_with("old")
