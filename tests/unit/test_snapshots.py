"""Unit tests for VM Snapshot operations."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from pyvergeos import VergeClient
from pyvergeos.exceptions import NotFoundError
from pyvergeos.resources.snapshots import VMSnapshot, VMSnapshotManager
from pyvergeos.resources.vms import VM


class TestVMSnapshotManager:
    """Unit tests for VMSnapshotManager."""

    @pytest.fixture
    def vm(self, mock_client: VergeClient) -> VM:
        """Create a mock VM."""
        return VM(
            {"$key": 100, "name": "test-vm", "machine": 200, "running": False},
            mock_client.vms,
        )

    def test_list_snapshots(
        self, mock_client: VergeClient, mock_session: MagicMock, vm: VM
    ) -> None:
        """Test listing snapshots."""
        mock_session.request.return_value.json.return_value = [
            {
                "$key": 1,
                "name": "Daily_20240101",
                "created": 1704067200,
                "expires": 1704153600,
            },
            {
                "$key": 2,
                "name": "Manual_Backup",
                "created": 1704153600,
                "expires": 0,
            },
        ]

        snapshots = vm.snapshots.list()

        assert len(snapshots) == 2
        assert snapshots[0].name == "Daily_20240101"
        assert snapshots[1].name == "Manual_Backup"

    def test_list_snapshots_filters_by_machine(
        self, mock_client: VergeClient, mock_session: MagicMock, vm: VM
    ) -> None:
        """Test that list() filters by machine key."""
        mock_session.request.return_value.json.return_value = []

        vm.snapshots.list()

        call_args = mock_session.request.call_args
        params = call_args.kwargs.get("params", {})
        assert "machine eq 200" in params.get("filter", "")

    def test_list_snapshots_sorted_by_created_desc(
        self, mock_client: VergeClient, mock_session: MagicMock, vm: VM
    ) -> None:
        """Test that snapshots are sorted newest first."""
        mock_session.request.return_value.json.return_value = []

        vm.snapshots.list()

        call_args = mock_session.request.call_args
        params = call_args.kwargs.get("params", {})
        assert params.get("sort") == "-created"

    def test_get_snapshot_by_key(
        self, mock_client: VergeClient, mock_session: MagicMock, vm: VM
    ) -> None:
        """Test getting a snapshot by key."""
        mock_session.request.return_value.json.return_value = {
            "$key": 1,
            "name": "Daily_20240101",
            "created": 1704067200,
            "machine": 200,
        }

        snapshot = vm.snapshots.get(1)

        assert snapshot.key == 1
        assert snapshot.name == "Daily_20240101"

    def test_get_snapshot_by_name(
        self, mock_client: VergeClient, mock_session: MagicMock, vm: VM
    ) -> None:
        """Test getting a snapshot by name."""
        mock_session.request.return_value.json.return_value = [
            {
                "$key": 1,
                "name": "Daily_20240101",
                "created": 1704067200,
            }
        ]

        snapshot = vm.snapshots.get(name="Daily_20240101")

        assert snapshot.name == "Daily_20240101"

    def test_get_snapshot_not_found(
        self, mock_client: VergeClient, mock_session: MagicMock, vm: VM
    ) -> None:
        """Test NotFoundError when snapshot not found."""
        mock_session.request.return_value.json.return_value = []

        with pytest.raises(NotFoundError):
            vm.snapshots.get(name="nonexistent")

    def test_create_snapshot(
        self, mock_client: VergeClient, mock_session: MagicMock, vm: VM
    ) -> None:
        """Test creating a snapshot."""
        mock_session.request.return_value.json.return_value = {
            "$key": 3,
            "name": "my-snapshot",
        }

        with patch("time.time", return_value=1_700_000_000):
            vm.snapshots.create(name="my-snapshot", retention=172800, quiesce=True)

        call_args = mock_session.request.call_args
        body = call_args.kwargs.get("json", {})
        # Should POST directly to machine_snapshots
        assert body["machine"] == 200
        assert body["name"] == "my-snapshot"
        assert body["quiesce"] is True
        assert body["created_manually"] is True
        assert body["expires"] == 1_700_000_000 + 172800

    def test_create_snapshot_default_retention(
        self, mock_client: VergeClient, mock_session: MagicMock, vm: VM
    ) -> None:
        """Test creating snapshot with default retention."""
        mock_session.request.return_value.json.return_value = {"$key": 4}

        with patch("time.time", return_value=1_700_000_000):
            vm.snapshots.create()

        call_args = mock_session.request.call_args
        body = call_args.kwargs.get("json", {})
        # Omitted retention is 24h, not expires:0 and not the platform +72h default.
        assert "name" in body
        assert body["expires"] == 1_700_000_000 + 86400
        assert body["machine"] == 200

    def test_create_snapshot_retention_zero_sends_expires_zero(
        self, mock_client: VergeClient, mock_session: MagicMock, vm: VM
    ) -> None:
        """retention=0 must send expires:0 (never), not omit the field (#146)."""
        mock_session.request.return_value.json.return_value = {"$key": 5}

        vm.snapshots.create(name="never-expires", retention=0)

        call_args = mock_session.request.call_args
        body = call_args.kwargs.get("json", {})
        assert body["name"] == "never-expires"
        assert "expires" in body
        assert body["expires"] == 0

    def test_create_snapshot_negative_retention_rejected(
        self, mock_client: VergeClient, mock_session: MagicMock, vm: VM
    ) -> None:
        """A negative retention must not be stored as never-expires (#146)."""
        with pytest.raises(ValueError, match="non-negative"):
            vm.snapshots.create(name="bad", retention=-1)

        assert mock_session.request.call_count == 1  # connect only; no POST

    def test_create_snapshot_none_retention_rejected(
        self, mock_client: VergeClient, mock_session: MagicMock, vm: VM
    ) -> None:
        """Explicit None is not 'never' and not the 24h default."""
        with pytest.raises(TypeError, match="retention"):
            vm.snapshots.create(name="bad", retention=None)  # type: ignore[arg-type]

        assert mock_session.request.call_count == 1  # connect only; no POST

    def test_delete_snapshot(
        self, mock_client: VergeClient, mock_session: MagicMock, vm: VM
    ) -> None:
        """Test deleting a snapshot that belongs to this VM."""
        mock_session.request.return_value.json.return_value = {
            "$key": 1,
            "machine": 200,
        }

        vm.snapshots.delete(1)

        call_args = mock_session.request.call_args
        assert call_args.kwargs["method"] == "DELETE"
        assert "machine_snapshots/1" in call_args.kwargs["url"]

    def test_restore_snapshot_clone_mode(
        self, mock_client: VergeClient, mock_session: MagicMock, vm: VM
    ) -> None:
        """Test restoring snapshot (clone mode - default)."""
        mock_session.request.return_value.json.side_effect = [
            # First call: get snapshot
            {
                "$key": 1,
                "name": "Daily_20240101",
                "snap_machine": 999,
                "machine": 200,
            },
            # Second call: find snapshot VM by machine key
            [{"$key": 888, "name": "snap_vm", "machine": 999, "is_snapshot": True}],
            # Third call: clone action
            {"$key": 101, "name": "Daily_20240101 restored"},
        ]

        vm.snapshots.restore(1)

        # Check the clone action was called
        call_args = mock_session.request.call_args
        body = call_args.kwargs.get("json", {})
        assert body["action"] == "clone"
        assert body["vm"] == 888  # Should use snapshot VM key, not machine key

    def test_restore_snapshot_with_custom_name(
        self, mock_client: VergeClient, mock_session: MagicMock, vm: VM
    ) -> None:
        """Test restoring snapshot with custom name."""
        mock_session.request.return_value.json.side_effect = [
            {"$key": 1, "name": "Daily", "snap_machine": 999, "machine": 200},
            # Second call: find snapshot VM by machine key
            [{"$key": 888, "name": "snap_vm", "machine": 999, "is_snapshot": True}],
            {"$key": 102, "name": "CustomName"},
        ]

        vm.snapshots.restore(1, name="CustomName")

        call_args = mock_session.request.call_args
        body = call_args.kwargs.get("json", {})
        assert body["params"]["name"] == "CustomName"

    def test_restore_skips_key_collision_and_wrong_machine(
        self, mock_client: VergeClient, mock_session: MagicMock, vm: VM
    ) -> None:
        """Clone the snapshot VM, not a VM whose $key equals snap_machine (#147)."""
        mock_session.request.return_value.json.side_effect = [
            {"$key": 1, "name": "Daily", "snap_machine": 999, "machine": 200},
            [
                # Snapshot of a different machine must not win just by order.
                {"$key": 777, "name": "other-snap", "machine": 1, "is_snapshot": True},
                # VM key collision: $key == snap_machine, but it is not a snapshot.
                {"$key": 999, "name": "unrelated", "machine": 999, "is_snapshot": False},
                {"$key": 888, "name": "snap_vm", "machine": 999, "is_snapshot": True},
            ],
            {"$key": 101, "name": "Daily restored"},
        ]

        vm.snapshots.restore(1)

        lookups = [
            call
            for call in mock_session.request.call_args_list
            if call.kwargs.get("method") == "GET"
            and str(call.kwargs.get("url", "")).rstrip("/").endswith("/vms")
        ]
        assert lookups
        assert lookups[-1].kwargs["params"]["filter"] == "machine eq 999"

        body = mock_session.request.call_args.kwargs.get("json", {})
        assert body["action"] == "clone"
        assert body["vm"] == 888

    def test_restore_missing_snapshot_vm_does_not_clone(
        self, mock_client: VergeClient, mock_session: MagicMock, vm: VM
    ) -> None:
        """Do not fall back to posting snap_machine as a VM key (#147)."""
        mock_session.request.return_value.json.side_effect = [
            {"$key": 1, "name": "Daily", "snap_machine": 999, "machine": 200},
            [],
        ]

        with pytest.raises(ValueError, match="Could not find snapshot VM"):
            vm.snapshots.restore(1)

        actions = [
            call.kwargs.get("json", {})
            for call in mock_session.request.call_args_list
            if isinstance(call.kwargs.get("json"), dict) and call.kwargs["json"].get("action")
        ]
        assert actions == []


class TestVMSnapshot:
    """Unit tests for VMSnapshot object."""

    @pytest.fixture
    def snapshot_data(self) -> dict[str, Any]:
        """Sample snapshot data."""
        return {
            "$key": 1,
            "name": "Daily_20240101",
            "description": "Daily backup",
            "created": 1704067200,  # 2024-01-01 00:00:00 UTC
            "expires": 1704153600,  # 2024-01-02 00:00:00 UTC
            "expires_type": "time",
            "quiesced": True,
            "created_manually": False,
            "machine": 200,
            "snap_machine": 999,
            "snapshot_period": None,
        }

    @pytest.fixture
    def mock_snapshot_manager(self, mock_client: VergeClient) -> VMSnapshotManager:
        """Create a mock snapshot manager."""
        vm = VM(
            {"$key": 100, "name": "test-vm", "machine": 200},
            mock_client.vms,
        )
        return VMSnapshotManager(mock_client, vm)

    def test_created_at(
        self, snapshot_data: dict[str, Any], mock_snapshot_manager: VMSnapshotManager
    ) -> None:
        """Test created_at property."""
        snapshot = VMSnapshot(snapshot_data, mock_snapshot_manager)
        assert snapshot.created_at == datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

    def test_expires_at(
        self, snapshot_data: dict[str, Any], mock_snapshot_manager: VMSnapshotManager
    ) -> None:
        """Test expires_at property."""
        snapshot = VMSnapshot(snapshot_data, mock_snapshot_manager)
        assert snapshot.expires_at == datetime(2024, 1, 2, 0, 0, 0, tzinfo=timezone.utc)

    def test_expires_at_none(
        self, snapshot_data: dict[str, Any], mock_snapshot_manager: VMSnapshotManager
    ) -> None:
        """Test expires_at when no expiration."""
        snapshot_data["expires"] = 0
        snapshot = VMSnapshot(snapshot_data, mock_snapshot_manager)
        assert snapshot.expires_at is None

    def test_never_expires_false(
        self, snapshot_data: dict[str, Any], mock_snapshot_manager: VMSnapshotManager
    ) -> None:
        """Test never_expires when snapshot has expiration."""
        snapshot = VMSnapshot(snapshot_data, mock_snapshot_manager)
        assert snapshot.never_expires is False

    def test_never_expires_true_by_type(
        self, snapshot_data: dict[str, Any], mock_snapshot_manager: VMSnapshotManager
    ) -> None:
        """Test never_expires when expires_type is 'never'."""
        snapshot_data["expires_type"] = "never"
        snapshot = VMSnapshot(snapshot_data, mock_snapshot_manager)
        assert snapshot.never_expires is True

    def test_never_expires_true_by_value(
        self, snapshot_data: dict[str, Any], mock_snapshot_manager: VMSnapshotManager
    ) -> None:
        """Test never_expires when expires is 0."""
        snapshot_data["expires"] = 0
        snapshot = VMSnapshot(snapshot_data, mock_snapshot_manager)
        assert snapshot.never_expires is True

    def test_is_quiesced(
        self, snapshot_data: dict[str, Any], mock_snapshot_manager: VMSnapshotManager
    ) -> None:
        """Test is_quiesced property."""
        snapshot = VMSnapshot(snapshot_data, mock_snapshot_manager)
        assert snapshot.is_quiesced is True

        snapshot_data["quiesced"] = False
        snapshot = VMSnapshot(snapshot_data, mock_snapshot_manager)
        assert snapshot.is_quiesced is False

    def test_is_manual(
        self, snapshot_data: dict[str, Any], mock_snapshot_manager: VMSnapshotManager
    ) -> None:
        """Test is_manual property."""
        snapshot = VMSnapshot(snapshot_data, mock_snapshot_manager)
        assert snapshot.is_manual is False

        snapshot_data["created_manually"] = True
        snapshot = VMSnapshot(snapshot_data, mock_snapshot_manager)
        assert snapshot.is_manual is True

    def test_snap_machine_key(
        self, snapshot_data: dict[str, Any], mock_snapshot_manager: VMSnapshotManager
    ) -> None:
        """Test snap_machine_key property."""
        snapshot = VMSnapshot(snapshot_data, mock_snapshot_manager)
        assert snapshot.snap_machine_key == 999

    def test_is_cloud_snapshot_false(
        self, snapshot_data: dict[str, Any], mock_snapshot_manager: VMSnapshotManager
    ) -> None:
        """Test is_cloud_snapshot when not a cloud snapshot."""
        snapshot = VMSnapshot(snapshot_data, mock_snapshot_manager)
        assert snapshot.is_cloud_snapshot is False

    def test_is_cloud_snapshot_true(
        self, snapshot_data: dict[str, Any], mock_snapshot_manager: VMSnapshotManager
    ) -> None:
        """Test is_cloud_snapshot when snapshot_period is set."""
        snapshot_data["snapshot_period"] = 123
        snapshot = VMSnapshot(snapshot_data, mock_snapshot_manager)
        assert snapshot.is_cloud_snapshot is True

    def test_restore_method(
        self,
        mock_client: VergeClient,
        mock_session: MagicMock,
        snapshot_data: dict[str, Any],
    ) -> None:
        """Object restore must post the snapshot VM key, not snap_machine (#147)."""
        vm = VM(
            {"$key": 100, "name": "test-vm", "machine": 200},
            mock_client.vms,
        )
        manager = VMSnapshotManager(mock_client, vm)
        snapshot = VMSnapshot(snapshot_data, manager)

        mock_session.request.return_value.json.side_effect = [
            # manager.restore: get snapshot by key
            snapshot_data,
            # resolve snap_machine (999) → snapshot VM, skipping a key collision
            [
                {"$key": 999, "name": "unrelated", "machine": 50, "is_snapshot": False},
                {"$key": 888, "name": "snap_vm", "machine": 999, "is_snapshot": True},
            ],
            # clone action
            {"$key": 101, "name": "My Restored VM"},
            # power on the clone
            {"$key": 101},
        ]

        with patch("time.sleep"):
            snapshot.restore(name="My Restored VM", power_on=True)

        posts = [
            call.kwargs.get("json", {})
            for call in mock_session.request.call_args_list
            if isinstance(call.kwargs.get("json"), dict) and call.kwargs["json"].get("action")
        ]
        assert posts[0]["action"] == "clone"
        assert posts[0]["vm"] == 888  # snapshot VM key, not machine key 999
        assert posts[0]["params"]["name"] == "My Restored VM"
        assert posts[1] == {"vm": 101, "action": "poweron"}
