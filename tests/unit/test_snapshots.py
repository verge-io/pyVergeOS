"""Unit tests for VM Snapshot operations."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock

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

        vm.snapshots.create(name="my-snapshot", retention=172800, quiesce=True)

        call_args = mock_session.request.call_args
        body = call_args.kwargs.get("json", {})
        # Should POST directly to machine_snapshots
        assert body["machine"] == 200
        assert body["name"] == "my-snapshot"
        assert body["quiesce"] is True
        assert body["created_manually"] is True
        assert "expires" in body

    def test_create_snapshot_default_retention(
        self, mock_client: VergeClient, mock_session: MagicMock, vm: VM
    ) -> None:
        """Test creating snapshot with default retention."""
        mock_session.request.return_value.json.return_value = {"$key": 4}

        vm.snapshots.create()

        call_args = mock_session.request.call_args
        body = call_args.kwargs.get("json", {})
        # Should have generated name and expires timestamp
        assert "name" in body
        assert "expires" in body
        assert body["machine"] == 200

    def test_delete_snapshot(
        self, mock_client: VergeClient, mock_session: MagicMock, vm: VM
    ) -> None:
        """Test deleting a snapshot."""
        mock_session.request.return_value.status_code = 204
        mock_session.request.return_value.text = ""

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
            {"$key": 1, "name": "Daily", "snap_machine": 999},
            # Second call: find snapshot VM by machine key
            [{"$key": 888, "name": "snap_vm", "machine": 999, "is_snapshot": True}],
            {"$key": 102, "name": "CustomName"},
        ]

        vm.snapshots.restore(1, name="CustomName")

        call_args = mock_session.request.call_args
        body = call_args.kwargs.get("json", {})
        assert body["params"]["name"] == "CustomName"


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
        """Test restore method on snapshot object."""
        vm = VM(
            {"$key": 100, "name": "test-vm", "machine": 200},
            mock_client.vms,
        )
        manager = VMSnapshotManager(mock_client, vm)
        snapshot = VMSnapshot(snapshot_data, manager)

        mock_session.request.return_value.json.return_value = {
            "$key": 101,
            "name": "Daily_20240101 restored",
        }

        snapshot.restore(name="My Restored VM")

        call_args = mock_session.request.call_args
        body = call_args.kwargs.get("json", {})
        assert body["action"] == "clone"
        assert body["vm"] == 999
        assert body["params"]["name"] == "My Restored VM"
