"""VM-scoped managers must refuse another VM's row on by-key calls (#168)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from pyvergeos import VergeClient
from pyvergeos.exceptions import NotFoundError
from pyvergeos.resources.vms import VM

OWN_MACHINE = 200
OTHER_MACHINE = 60
FOREIGN_KEY = 2


def _operation_calls(mock_session: MagicMock) -> list[MagicMock]:
    """Requests other than the connection check against /system."""
    return [
        call
        for call in mock_session.request.call_args_list
        if not str(call.kwargs.get("url", "")).rstrip("/").endswith("/system")
    ]


def _assert_only_scope_read(mock_session: MagicMock, endpoint: str, key: int) -> None:
    """The call fetched the row and sent no write."""
    calls = _operation_calls(mock_session)
    assert len(calls) == 1
    assert calls[0].kwargs.get("method") == "GET"
    assert f"/{endpoint}/{key}" in calls[0].kwargs.get("url", "")
    fields = str(calls[0].kwargs.get("params", {}).get("fields", ""))
    assert "machine" in fields.split(",")
    writes = [
        call.kwargs.get("method")
        for call in mock_session.request.call_args_list
        if call.kwargs.get("method") in {"POST", "PUT", "DELETE", "PATCH"}
    ]
    assert writes == []


@pytest.fixture
def vm(mock_client: VergeClient) -> VM:
    """Stopped VM. In-place restore of another VM is the damaging case."""
    return VM(
        {"$key": 100, "name": "vm-a", "machine": OWN_MACHINE, "running": False},
        mock_client.vms,
    )


def _foreign_row(**extra: object) -> dict[str, object]:
    row: dict[str, object] = {
        "$key": FOREIGN_KEY,
        "name": "other-vm",
        "machine": OTHER_MACHINE,
    }
    row.update(extra)
    return row


class TestSnapshotMachineScope:
    """vm.snapshots must not touch a snapshot owned by another machine."""

    def test_get_refuses_other_machine(
        self, mock_client: VergeClient, mock_session: MagicMock, vm: VM
    ) -> None:
        mock_session.request.return_value.json.return_value = _foreign_row()

        with pytest.raises(NotFoundError, match="does not belong to machine 200"):
            vm.snapshots.get(FOREIGN_KEY)

        _assert_only_scope_read(mock_session, "machine_snapshots", FOREIGN_KEY)

    def test_get_narrowed_fields_still_requests_machine(
        self, mock_client: VergeClient, mock_session: MagicMock, vm: VM
    ) -> None:
        """Omitting machine from fields must not skip the scope check."""
        mock_session.request.return_value.json.return_value = _foreign_row()

        with pytest.raises(NotFoundError, match="does not belong"):
            vm.snapshots.get(FOREIGN_KEY, fields="$key,name")

        _assert_only_scope_read(mock_session, "machine_snapshots", FOREIGN_KEY)

    def test_get_accepts_string_machine(
        self, mock_client: VergeClient, mock_session: MagicMock, vm: VM
    ) -> None:
        mock_session.request.return_value.json.return_value = {
            "$key": 1,
            "name": "own",
            "machine": str(OWN_MACHINE),
        }

        snapshot = vm.snapshots.get(1)

        assert snapshot.key == 1

    def test_update_refuses_other_machine(
        self, mock_client: VergeClient, mock_session: MagicMock, vm: VM
    ) -> None:
        mock_session.request.return_value.json.return_value = _foreign_row()

        with pytest.raises(NotFoundError, match="does not belong"):
            vm.snapshots.update(FOREIGN_KEY, description="nope")

        _assert_only_scope_read(mock_session, "machine_snapshots", FOREIGN_KEY)

    def test_delete_refuses_other_machine(
        self, mock_client: VergeClient, mock_session: MagicMock, vm: VM
    ) -> None:
        mock_session.request.return_value.json.return_value = _foreign_row()

        with pytest.raises(NotFoundError, match="does not belong"):
            vm.snapshots.delete(FOREIGN_KEY)

        _assert_only_scope_read(mock_session, "machine_snapshots", FOREIGN_KEY)

    def test_restore_refuses_other_machine(
        self, mock_client: VergeClient, mock_session: MagicMock, vm: VM
    ) -> None:
        """In-place restore must not revert the VM that owns the snapshot."""
        mock_session.request.return_value.json.return_value = _foreign_row(snap_machine=999)

        with patch("time.sleep"), pytest.raises(NotFoundError, match="does not belong"):
            vm.snapshots.restore(FOREIGN_KEY, replace_original=True)

        _assert_only_scope_read(mock_session, "machine_snapshots", FOREIGN_KEY)


class TestDriveMachineScope:
    """vm.drives must not touch a drive owned by another machine."""

    def test_get_refuses_other_machine(
        self, mock_client: VergeClient, mock_session: MagicMock, vm: VM
    ) -> None:
        mock_session.request.return_value.json.return_value = _foreign_row()

        with pytest.raises(NotFoundError, match="does not belong to machine 200"):
            vm.drives.get(FOREIGN_KEY)

        _assert_only_scope_read(mock_session, "machine_drives", FOREIGN_KEY)

    def test_get_narrowed_fields_still_requests_machine(
        self, mock_client: VergeClient, mock_session: MagicMock, vm: VM
    ) -> None:
        mock_session.request.return_value.json.return_value = _foreign_row()

        with pytest.raises(NotFoundError, match="does not belong"):
            vm.drives.get(FOREIGN_KEY, fields=["$key", "name"])

        _assert_only_scope_read(mock_session, "machine_drives", FOREIGN_KEY)

    def test_update_refuses_other_machine(
        self, mock_client: VergeClient, mock_session: MagicMock, vm: VM
    ) -> None:
        mock_session.request.return_value.json.return_value = _foreign_row()

        with pytest.raises(NotFoundError, match="does not belong"):
            vm.drives.update(FOREIGN_KEY, description="written on the wrong drive")

        _assert_only_scope_read(mock_session, "machine_drives", FOREIGN_KEY)

    def test_delete_refuses_other_machine(
        self, mock_client: VergeClient, mock_session: MagicMock, vm: VM
    ) -> None:
        mock_session.request.return_value.json.return_value = _foreign_row()

        with pytest.raises(NotFoundError, match="does not belong"):
            vm.drives.delete(FOREIGN_KEY)

        _assert_only_scope_read(mock_session, "machine_drives", FOREIGN_KEY)


class TestNICMachineScope:
    """vm.nics must not touch a NIC owned by another machine."""

    def test_get_refuses_other_machine(
        self, mock_client: VergeClient, mock_session: MagicMock, vm: VM
    ) -> None:
        mock_session.request.return_value.json.return_value = _foreign_row()

        with pytest.raises(NotFoundError, match="does not belong to machine 200"):
            vm.nics.get(FOREIGN_KEY)

        _assert_only_scope_read(mock_session, "machine_nics", FOREIGN_KEY)

    def test_get_narrowed_fields_still_requests_machine(
        self, mock_client: VergeClient, mock_session: MagicMock, vm: VM
    ) -> None:
        mock_session.request.return_value.json.return_value = _foreign_row()

        with pytest.raises(NotFoundError, match="does not belong"):
            vm.nics.get(FOREIGN_KEY, fields="$key,name")

        _assert_only_scope_read(mock_session, "machine_nics", FOREIGN_KEY)

    def test_update_refuses_other_machine(
        self, mock_client: VergeClient, mock_session: MagicMock, vm: VM
    ) -> None:
        mock_session.request.return_value.json.return_value = _foreign_row()

        with pytest.raises(NotFoundError, match="does not belong"):
            vm.nics.update(FOREIGN_KEY, description="written on the wrong nic")

        _assert_only_scope_read(mock_session, "machine_nics", FOREIGN_KEY)

    def test_delete_refuses_other_machine(
        self, mock_client: VergeClient, mock_session: MagicMock, vm: VM
    ) -> None:
        mock_session.request.return_value.json.return_value = _foreign_row()

        with pytest.raises(NotFoundError, match="does not belong"):
            vm.nics.delete(FOREIGN_KEY)

        _assert_only_scope_read(mock_session, "machine_nics", FOREIGN_KEY)
