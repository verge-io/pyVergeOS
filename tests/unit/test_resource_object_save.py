"""Regression tests for issue #80: setattr + bare save() must persist updates.

Previously, ``ResourceObject.save()`` only forwarded keyword arguments, so
attributes set via ``setattr()`` (or item assignment) were silently dropped
and an empty PUT body was sent. These tests verify dirty-field tracking for
the five affected resource types: VM, Network, NIC, Drive, and User.
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock

from pyvergeos import VergeClient
from pyvergeos.resources.base import ResourceManager, ResourceObject


def _put_calls(mock_session: MagicMock) -> list[Any]:
    return [
        call for call in mock_session.request.call_args_list if call.kwargs.get("method") == "PUT"
    ]


def _put_body(call: Any) -> dict[str, Any]:
    data = call.kwargs.get("data")
    if data is None:
        return call.kwargs.get("json") or {}
    return dict(json.loads(data))


class TestResourceObjectDirtyTracking:
    """Base ResourceObject dirty-field tracking."""

    def test_setattr_marks_field_dirty_and_save_sends_it(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        manager: ResourceManager[ResourceObject] = ResourceManager(mock_client)
        manager._endpoint = "things"
        obj = ResourceObject({"$key": 5, "name": "orig"}, manager)

        mock_session.request.return_value.json.return_value = {"$key": 5, "name": "new"}
        obj.name = "new"
        obj.save()

        puts = _put_calls(mock_session)
        assert len(puts) == 1
        assert "things/5" in puts[0].kwargs["url"]
        assert _put_body(puts[0]) == {"name": "new"}

    def test_setitem_marks_field_dirty(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        manager: ResourceManager[ResourceObject] = ResourceManager(mock_client)
        manager._endpoint = "things"
        obj = ResourceObject({"$key": 5}, manager)

        obj["description"] = "via item"
        obj.save()

        puts = _put_calls(mock_session)
        assert len(puts) == 1
        assert _put_body(puts[0]) == {"description": "via item"}

    def test_dict_update_marks_fields_dirty(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        manager: ResourceManager[ResourceObject] = ResourceManager(mock_client)
        manager._endpoint = "things"
        obj = ResourceObject({"$key": 5}, manager)

        obj.update({"a": 1}, b=2)
        obj.save()

        puts = _put_calls(mock_session)
        assert len(puts) == 1
        assert _put_body(puts[0]) == {"a": 1, "b": 2}

    def test_explicit_kwargs_take_precedence_over_dirty_fields(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        manager: ResourceManager[ResourceObject] = ResourceManager(mock_client)
        manager._endpoint = "things"
        obj = ResourceObject({"$key": 5}, manager)

        obj.name = "from-attr"
        obj.save(name="from-kwarg")

        puts = _put_calls(mock_session)
        assert _put_body(puts[0]) == {"name": "from-kwarg"}

    def test_save_without_changes_does_not_put(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        manager: ResourceManager[ResourceObject] = ResourceManager(mock_client)
        manager._endpoint = "things"
        obj = ResourceObject({"$key": 5, "name": "orig"}, manager)

        mock_session.request.return_value.json.return_value = {"$key": 5, "name": "orig"}
        obj.save()

        assert _put_calls(mock_session) == []

    def test_initial_data_is_not_dirty(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        manager: ResourceManager[ResourceObject] = ResourceManager(mock_client)
        manager._endpoint = "things"
        obj = ResourceObject({"$key": 5, "name": "orig", "ram": 1024}, manager)

        assert obj._dirty == set()

    def test_dollar_fields_are_never_sent(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        manager: ResourceManager[ResourceObject] = ResourceManager(mock_client)
        manager._endpoint = "things"
        obj = ResourceObject({"$key": 5}, manager)

        obj["$row"] = 9
        obj.name = "x"
        obj.save()

        puts = _put_calls(mock_session)
        assert _put_body(puts[0]) == {"name": "x"}

    def test_dirty_fields_cleared_after_save(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        manager: ResourceManager[ResourceObject] = ResourceManager(mock_client)
        manager._endpoint = "things"
        obj = ResourceObject({"$key": 5}, manager)

        obj.name = "x"
        obj.save()
        assert obj._dirty == set()


class TestIssue80AffectedResources:
    """The five resource types named in issue #80."""

    def test_vm_setattr_save_persists(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        mock_session.request.return_value.json.return_value = {"$key": 1, "name": "vm1"}
        vm = mock_client.vms.get(1)
        mock_session.request.reset_mock()

        vm.description = "updated"
        vm.save()

        puts = _put_calls(mock_session)
        assert len(puts) == 1
        assert "vms/1" in puts[0].kwargs["url"]
        assert _put_body(puts[0]) == {"description": "updated"}

    def test_network_setattr_save_persists(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        mock_session.request.return_value.json.return_value = {"$key": 2, "name": "net1"}
        net = mock_client.networks.get(2)
        mock_session.request.reset_mock()

        net.description = "updated"
        net.save()

        puts = _put_calls(mock_session)
        assert len(puts) == 1
        assert _put_body(puts[0]) == {"description": "updated"}

    def test_nic_setattr_save_persists(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        mock_session.request.return_value.json.return_value = {
            "$key": 1,
            "name": "vm1",
            "machine": 10,
        }
        vm = mock_client.vms.get(1)
        mock_session.request.return_value.json.return_value = {"$key": 3, "name": "nic1"}
        nic = vm.nics.get(3)
        mock_session.request.reset_mock()

        nic.description = "updated"
        nic.save()

        puts = _put_calls(mock_session)
        assert len(puts) == 1
        assert _put_body(puts[0]) == {"description": "updated"}

    def test_drive_setattr_save_persists(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        mock_session.request.return_value.json.return_value = {
            "$key": 1,
            "name": "vm1",
            "machine": 10,
        }
        vm = mock_client.vms.get(1)
        mock_session.request.return_value.json.return_value = {"$key": 4, "name": "drive1"}
        drive = vm.drives.get(4)
        mock_session.request.reset_mock()

        drive.description = "updated"
        drive.save()

        puts = _put_calls(mock_session)
        assert len(puts) == 1
        assert _put_body(puts[0]) == {"description": "updated"}

    def test_user_setattr_save_issues_put(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        mock_session.request.return_value.json.return_value = {"$key": 6, "name": "user1"}
        user = mock_client.users.get(6)
        mock_session.request.reset_mock()

        user.displayname = "Updated Name"
        user.save()

        puts = _put_calls(mock_session)
        assert len(puts) == 1
        assert "users/6" in puts[0].kwargs["url"]
        assert _put_body(puts[0]) == {"displayname": "Updated Name"}

    def test_user_manager_update_accepts_extra_fields(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        mock_session.request.return_value.json.return_value = {"$key": 6, "name": "user1"}
        mock_client.users.update(6, displayname="D", ssh_allow_password="x")

        puts = _put_calls(mock_session)
        assert len(puts) == 1
        body = _put_body(puts[0])
        assert body["displayname"] == "D"
        assert body["ssh_allow_password"] == "x"

    def test_user_save_without_changes_does_not_put(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        mock_session.request.return_value.json.return_value = {"$key": 6, "name": "user1"}
        user = mock_client.users.get(6)
        mock_session.request.reset_mock()

        user.save()

        assert _put_calls(mock_session) == []
