"""Polymorphic 'table/key' references, and the int() coercion they broke.

Issue #126. Several columns hold a reference naming both a table and a row --
``"vms/39"`` -- and a key is not always numeric, because recipes are keyed by
name. Four accessors declared ``-> int`` and coerced with ``int()``, so
reading them raised ValueError on ordinary rows: every alarm and every task
on the test system failed.

The raw values below were measured on VergeOS 26.1.8.
"""

from __future__ import annotations

import pytest

from pyvergeos import VergeClient
from pyvergeos.resources.alarms import Alarm
from pyvergeos.resources.base import reference_key, reference_table, split_reference
from pyvergeos.resources.task_events import TaskEvent
from pyvergeos.resources.task_schedules import TaskSchedule
from pyvergeos.resources.tasks import Task


class TestSplitReference:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("vms/39", ("vms", 39)),
            ("tenant_nodes/2", ("tenant_nodes", 2)),
            # recipes are keyed by name, so the key is not an int
            (
                "vm_recipes/yottabyte-services-nas-winbind-recipe-v1",
                ("vm_recipes", "yottabyte-services-nas-winbind-recipe-v1"),
            ),
            ("update_settings/1", ("update_settings", 1)),
            # not a reference at all, just a non-numeric scalar
            ("deprecated", (None, "deprecated")),
            ("39", (None, 39)),
            (39, (None, 39)),
            (None, (None, None)),
            ("", (None, None)),
            ("   ", (None, None)),
            # a table with no key, and a key containing a slash
            ("vms/", ("vms", None)),
            ("a/b/c", ("a", "b/c")),
        ],
    )
    def test_split(self, raw: object, expected: tuple[str | None, object]) -> None:
        assert split_reference(raw) == expected

    def test_key_and_table_are_the_two_halves(self) -> None:
        assert reference_table("vms/39") == "vms"
        assert reference_key("vms/39") == 39

    def test_a_plain_key_has_no_table(self) -> None:
        assert reference_table(39) is None
        assert reference_key(39) == 39

    def test_nothing_raises_on_any_shape(self) -> None:
        for raw in ["", "  ", "x", "x/", "/", "//", 0, -1, None, True, "1e5", "0x10"]:
            split_reference(raw)


class TestAccessorsReportTheKeyInsteadOfRaising:
    """Each of these raised ValueError on a real row before issue #126."""

    def test_alarm_owner_key(self, mock_client: VergeClient) -> None:
        alarm = Alarm({"$key": 1, "owner": "vms/39"}, mock_client.alarms)
        assert alarm.owner_key == 39

    def test_alarm_type_key_may_be_a_name(self, mock_client: VergeClient) -> None:
        alarm = Alarm({"$key": 1, "alarm_type": "deprecated"}, mock_client.alarms)
        assert alarm.alarm_type_key == "deprecated"

    def test_alarm_sub_owner_empty_is_none(self, mock_client: VergeClient) -> None:
        alarm = Alarm({"$key": 1, "sub_owner": ""}, mock_client.alarms)
        assert alarm.sub_owner is None

    def test_task_owner_key_may_be_a_recipe_name(self, mock_client: VergeClient) -> None:
        task = Task(
            {"$key": 1, "owner": "vm_recipes/yottabyte-services-nas-winbind-recipe-v1"},
            mock_client.tasks,
        )
        assert task.owner_key == "yottabyte-services-nas-winbind-recipe-v1"

    def test_task_owner_table_comes_from_its_own_column(self, mock_client: VergeClient) -> None:
        """Task already carries the table separately; owner only needs splitting."""
        task = Task({"$key": 1, "owner": "vms/39", "table": "vms"}, mock_client.tasks)
        assert task.owner_table == "vms"
        assert task.owner_key == 39

    def test_task_creator_key(self, mock_client: VergeClient) -> None:
        task = Task({"$key": 1, "creator": "users/3"}, mock_client.tasks)
        assert task.creator_key == 3

    def test_task_schedule_creator_key(self, mock_client: VergeClient) -> None:
        sched = TaskSchedule({"$key": 1, "creator": "users/3"}, mock_client.task_schedules)
        assert sched.creator_key == 3

    def test_task_event_owner_key_is_no_longer_discarded(self, mock_client: VergeClient) -> None:
        event = TaskEvent({"$key": 1, "owner": "update_settings/1"}, mock_client.task_events)
        assert event.owner_key == 1

    def test_iterating_alarms_does_not_raise(self, mock_client: VergeClient) -> None:
        """The reported symptom: a plain loop crashed on the first row."""
        rows = [
            {"$key": 1, "owner": "vms/39", "alarm_type": "deprecated", "sub_owner": ""},
            {"$key": 2, "owner": "vnets/7", "alarm_type": 4, "sub_owner": "3"},
        ]
        for raw in rows:
            alarm = Alarm(raw, mock_client.alarms)
            assert alarm.owner_key is not None
            assert alarm.alarm_type_key is not None
            _ = alarm.sub_owner


class TestOrdinaryReferencesAreUnaffected:
    def test_numeric_owner_still_reads_as_an_int(self, mock_client: VergeClient) -> None:
        assert Alarm({"$key": 1, "owner": 39}, mock_client.alarms).owner_key == 39

    def test_numeric_string_owner_still_reads_as_an_int(self, mock_client: VergeClient) -> None:
        assert Task({"$key": 1, "owner": "27"}, mock_client.tasks).owner_key == 27

    def test_absent_owner_is_still_none(self, mock_client: VergeClient) -> None:
        assert Alarm({"$key": 1}, mock_client.alarms).owner_key is None


class TestReferenceColumnsAreProjected:
    """The reference columns these accessors read must actually be fetched.

    Caught a real regression: while converting accessors for #125, the
    tooling pruned ``owner``, ``creator``, ``sub_owner`` and ``alarm_type``
    from four projections, because a declarative accessor briefly claimed
    them. The unit suite stayed green -- every test builds its row by hand --
    and only a comparison of the wire projections showed it. This pins them.
    """

    @pytest.mark.parametrize(
        ("manager_name", "column"),
        [
            ("AlarmManager", "owner"),
            ("AlarmManager", "sub_owner"),
            ("AlarmManager", "alarm_type"),
            ("TaskManager", "owner"),
            ("TaskManager", "creator"),
            ("TaskManager", "table"),
            ("TaskEventManager", "owner"),
            ("TaskEventManager", "table"),
            ("TaskScheduleManager", "creator"),
        ],
    )
    def test_column_is_in_the_default_projection(self, manager_name: str, column: str) -> None:
        from pyvergeos.resources.alarms import AlarmManager
        from pyvergeos.resources.task_events import TaskEventManager
        from pyvergeos.resources.task_schedules import TaskScheduleManager
        from pyvergeos.resources.tasks import TaskManager

        managers = {
            "AlarmManager": AlarmManager,
            "TaskManager": TaskManager,
            "TaskEventManager": TaskEventManager,
            "TaskScheduleManager": TaskScheduleManager,
        }
        defaults = managers[manager_name]._default_fields or []
        assert column in defaults, (
            f"{manager_name} no longer requests {column!r}, so the accessor "
            "reading it would silently report None for every row"
        )
