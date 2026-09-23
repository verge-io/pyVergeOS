"""Projection semantics: ``all`` is not a superset, and accessors must not
guess (issue #117).

The API resolves ``fields=all`` to the resource's *own columns*. Anything a
manager has the server compute is therefore absent from it: aliased
traversals (``machine#status#running as running``) and aggregates
(``count(members) as member_count``) alike. On ``nodes``, ``all`` does not
even carry ``$key``. Measured on VergeOS 26.1.8:

    /vnets?fields=all                                      -> 98 fields, no running
    /vnets?fields=all,machine#status#running as running     -> 99 fields, running=True
    /nodes?fields=all                                      -> 75 fields, no $key
    /nodes?fields=all,$key                                 -> 76 fields, $key=1

So a caller who asked for *more* data got *less*, with no error: a running
VM read back under ``all`` reported ``is_running is False``, and
``node.key`` raised "Resource has no $key" for a node that was plainly
persisted.

Neither ``most``, ``*`` nor ``basic`` includes the computed entries either,
and the foreign key under ``all`` is a bare int rather than an expanded
object, so asking for them by name is the only way to get them.
"""

from __future__ import annotations

import ast
import importlib
import inspect
import pathlib
import pkgutil
import re
import textwrap
from typing import Any
from unittest.mock import MagicMock

import pytest

from pyvergeos import VergeClient
from pyvergeos.exceptions import FieldNotProjectedError
from pyvergeos.resources.base import (
    ResourceManager,
    ResourceObject,
    expand_projection,
    is_computed_projection,
    projection_alias,
)
from pyvergeos.resources.networks import DEFAULT_NETWORK_FIELDS, Network, NetworkManager
from pyvergeos.resources.nodes import Node
from pyvergeos.resources.vms import VM, VM_DEFAULT_FIELDS

PACKAGE_DIR = pathlib.Path(__file__).resolve().parents[2] / "pyvergeos"
RESOURCES_DIR = PACKAGE_DIR / "resources"

# A projection entry the server has to compute, bound to a name: a traversal
# (machine#status#running as running) or an aggregate (count(members) as
# member_count). Neither is a column, so neither is ever part of ``all``.
COMPUTED_ALIAS = re.compile(r'["\']([^"\']*(?:#|\()[^"\']*)\s+as\s+(\w+)["\']')


def manager_classes() -> list[tuple[str, type, ast.Module]]:
    """Every ResourceManager subclass, discovered at runtime.

    Deliberately not an AST scan of base-class *names*: five managers
    subclass ResourceManager only indirectly (``VMCloudInitFileManager``,
    the four ``queries`` managers), and a name-matching tripwire skipped
    them -- which is how a projection bypass survived in
    ``VMCloudInitFileManager.get()`` (issue #117). ``issubclass`` cannot
    miss them.
    """
    import pyvergeos.resources as resources_pkg
    from pyvergeos.resources.base import ResourceManager as RM

    out: list[tuple[str, type, ast.Module]] = []
    for info in pkgutil.iter_modules(resources_pkg.__path__):
        module = importlib.import_module(f"pyvergeos.resources.{info.name}")
        for name, cls in vars(module).items():
            if not inspect.isclass(cls) or not issubclass(cls, RM):
                continue
            if cls is RM or cls.__module__ != module.__name__:
                continue
            try:
                source = textwrap.dedent(inspect.getsource(cls))
            except OSError:  # pragma: no cover
                continue
            out.append((f"{info.name}.{name}", cls, ast.parse(source)))
    return out


class TestProjectionAlias:
    def test_aliased_join_lands_under_its_alias(self) -> None:
        assert projection_alias("machine#status#running as running") == "running"

    def test_plain_column_lands_under_itself(self) -> None:
        assert projection_alias("name") == "name"
        assert projection_alias("$key") == "$key"

    def test_unaliased_join_is_not_mistaken_for_an_alias(self) -> None:
        assert projection_alias("machine#status") == "machine#status"

    def test_as_inside_a_field_name_is_not_an_alias(self) -> None:
        # 'aspect' must not be read as 'as pect'
        assert projection_alias("aspect") == "aspect"


class TestIsComputedProjection:
    def test_traversal_is_computed(self) -> None:
        assert is_computed_projection("machine#status#running as running")

    def test_aggregate_is_computed(self) -> None:
        assert is_computed_projection("count(members) as member_count")

    def test_plain_column_is_not_computed(self) -> None:
        assert not is_computed_projection("name")
        assert not is_computed_projection("$key")
        assert not is_computed_projection("description")


class TestExpandProjection:
    def test_all_gains_the_managers_joins_and_key(self) -> None:
        result = expand_projection(["all"], DEFAULT_NETWORK_FIELDS)
        assert result[0] == "all"
        assert "$key" in result
        assert "machine#status#running as running" in result
        assert "machine#status#status as status" in result

    def test_aggregate_is_appended_to_all(self) -> None:
        defaults = ["$key", "name", "count(members) as member_count"]
        result = expand_projection(["all"], defaults)
        assert "count(members) as member_count" in result
        assert "name" not in result

    def test_expansion_is_a_superset_of_the_default_projection(self) -> None:
        expanded = {projection_alias(f) for f in expand_projection(["all"], VM_DEFAULT_FIELDS)}
        for field in VM_DEFAULT_FIELDS:
            if is_computed_projection(field) or field == "$key":
                assert projection_alias(field) in expanded, field

    def test_plain_columns_are_not_appended(self) -> None:
        # 'all' already covers own columns; re-listing them only bloats the URL
        result = expand_projection(["all"], DEFAULT_NETWORK_FIELDS)
        assert "name" not in result
        assert "mtu" not in result

    def test_narrowed_projection_passes_through_untouched(self) -> None:
        assert expand_projection(["$key", "name"], DEFAULT_NETWORK_FIELDS) == ["$key", "name"]

    def test_caller_override_wins(self) -> None:
        explicit = ["all", "machine#status#running as running"]
        result = expand_projection(explicit, DEFAULT_NETWORK_FIELDS)
        assert result.count("machine#status#running as running") == 1

    def test_string_form_is_accepted(self) -> None:
        result = expand_projection("all", DEFAULT_NETWORK_FIELDS)
        assert "machine#status#running as running" in result

    def test_key_is_ensured_even_with_no_declared_defaults(self) -> None:
        """18 managers declare no default projection, and several endpoints
        leave ``$key`` out of ``all`` -- ``storage_tiers`` among them, where
        ``.key`` then raised for a plainly persisted row."""
        assert expand_projection(["all"], None) == ["all", "$key"]

    def test_key_is_not_duplicated(self) -> None:
        assert expand_projection(["all", "$key"], None) == ["all", "$key"]

    def test_sub_selection_is_computed(self) -> None:
        # 'all' answers a sub-selected column with the bare foreign key
        assert is_computed_projection("stats[reads,writes,rops]")

    def test_empty_projection_is_a_no_op(self) -> None:
        assert expand_projection(None, DEFAULT_NETWORK_FIELDS) is None

    def test_field_merely_containing_all_is_not_the_token(self) -> None:
        assert expand_projection(["allocated_bytes"], DEFAULT_NETWORK_FIELDS) == ["allocated_bytes"]

    def test_caller_named_alias_is_translated_to_the_managers_entry(self) -> None:
        """Naming an alias must mean the manager's field of that name.

        ``vms`` has a real ``running`` column that is null on every row, and
        ``vnets`` drops the name entirely; either way
        ``fields=["$key","name","running"]`` made ``is_running`` answer
        ``False`` for a running resource -- issue #117 reached through a
        narrowed projection rather than through ``all``.
        """
        result = expand_projection(["$key", "name", "running"], DEFAULT_NETWORK_FIELDS)
        assert "machine#status#running as running" in result
        assert "running" not in result

    def test_translation_does_not_widen_the_projection(self) -> None:
        result = expand_projection(["$key", "running"], DEFAULT_NETWORK_FIELDS)
        assert len(result) == 2

    def test_unknown_names_are_left_alone(self) -> None:
        assert expand_projection(["$key", "mtu"], DEFAULT_NETWORK_FIELDS) == ["$key", "mtu"]

    def test_a_fully_written_entry_is_not_double_translated(self) -> None:
        explicit = ["$key", "machine#status#running as running"]
        assert expand_projection(explicit, DEFAULT_NETWORK_FIELDS) == explicit

    def test_translation_applies_under_all_too(self) -> None:
        result = expand_projection(["all", "running"], DEFAULT_NETWORK_FIELDS)
        assert "machine#status#running as running" in result
        assert result.count("machine#status#running as running") == 1
        assert "running" not in result

    def test_expansion_is_idempotent(self) -> None:
        once = expand_projection(["all"], DEFAULT_NETWORK_FIELDS)
        assert expand_projection(once, DEFAULT_NETWORK_FIELDS) == once


def _client_returning(payload: Any) -> VergeClient:
    client = MagicMock(spec=VergeClient)
    client._request.return_value = payload
    return client


class TestManagerSendsExpandedProjection:
    def test_list_expands_all(self) -> None:
        client = _client_returning([])
        NetworkManager(client).list(fields=["all"])
        sent = client._request.call_args.kwargs["params"]["fields"]
        assert sent.startswith("all,")
        assert "machine#status#running as running" in sent
        assert "$key" in sent

    def test_get_by_key_expands_all(self) -> None:
        client = _client_returning({"$key": 1, "name": "n", "running": True})
        NetworkManager(client).get(1, fields=["all"])
        sent = client._request.call_args.kwargs["params"]["fields"]
        assert "machine#status#status as status" in sent

    def test_default_projection_is_left_alone(self) -> None:
        client = _client_returning([])
        NetworkManager(client).list()
        sent = client._request.call_args.kwargs["params"]["fields"]
        assert "all" not in sent.split(",")

    def test_narrowed_projection_is_left_alone(self) -> None:
        client = _client_returning([])
        NetworkManager(client).list(fields=["$key", "name"])
        assert client._request.call_args.kwargs["params"]["fields"] == "$key,name"


class TestEveryManagerDeclaresItsDefaultProjection:
    """AST tripwire: a manager whose defaults are unreachable cannot expand.

    ``expand_projection()`` needs the manager's default projection, and 34
    managers kept theirs in a module constant that only their own ``list()``
    could see.
    """

    def test_managers_with_computed_defaults_declare_them(self) -> None:
        undeclared: list[str] = []
        for path in sorted(RESOURCES_DIR.glob("*.py")):
            source = path.read_text()
            if not COMPUTED_ALIAS.search(source):
                continue
            tree = ast.parse(source)
            constants = {
                node.targets[0].id
                for node in tree.body
                if isinstance(node, ast.Assign)
                and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
                and isinstance(node.value, (ast.List, ast.Tuple))
            }
            for cls in (n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)):
                if any(
                    isinstance(stmt, ast.Assign)
                    and len(stmt.targets) == 1
                    and isinstance(stmt.targets[0], ast.Name)
                    and stmt.targets[0].id == "_default_fields"
                    for stmt in cls.body
                ):
                    continue
                for fn in cls.body:
                    if not isinstance(fn, ast.FunctionDef) or fn.name not in ("list", "get"):
                        continue
                    for node in ast.walk(fn):
                        if not (
                            isinstance(node, ast.If) and ast.unparse(node.test) == "fields is None"
                        ):
                            continue
                        for stmt in node.body:
                            if not (
                                isinstance(stmt, ast.Assign)
                                and ast.unparse(stmt.targets[0]) == "fields"
                            ):
                                continue
                            value = stmt.value
                            name = None
                            if isinstance(value, ast.Name):
                                name = value.id
                            elif (
                                isinstance(value, ast.Call)
                                and isinstance(value.func, ast.Attribute)
                                and value.func.attr == "copy"
                                and isinstance(value.func.value, ast.Name)
                            ):
                                name = value.func.value.id
                            if name in constants:
                                undeclared.append(f"{path.name}:{cls.name} -> {name}")
        assert not undeclared, (
            "managers whose default projection is not reachable from the base "
            "class, so a caller's fields=['all'] cannot be expanded into a "
            f"superset of it (issue #117): {sorted(set(undeclared))}"
        )


class TestEveryFieldsParameterComesFromTheProjectionHelper:
    """AST tripwire, over runtime-discovered managers.

    ``self._projection()`` is the one place a projection becomes a request
    parameter, so it is also the one place ``all`` gets expanded and the one
    place the requested alias set is recorded. Any other construction of the
    ``fields`` parameter is a hole in both.

    Hand-rolled shapes that slipped past earlier, narrower versions of this
    check: ``",".join(field_list)`` where ``field_list`` is a local built
    from the caller's ``fields`` (certificates, webhooks, cloud-init),
    ``",".join(request_fields)`` (auth sources, OIDC applications), and
    ``normalize_fields(fields)`` in managers reached only by indirect
    inheritance.
    """

    def test_fields_params_use_the_helper(self) -> None:
        offenders: list[str] = []
        for label, _cls, tree in manager_classes():
            for node in ast.walk(tree):
                values: list[ast.expr] = []
                # params["fields"] = ...  (the query-parameter dict; a
                # body["fields"] is a payload attribute, not a projection)
                if (
                    isinstance(node, ast.Assign)
                    and len(node.targets) == 1
                    and isinstance(node.targets[0], ast.Subscript)
                    and isinstance(node.targets[0].value, ast.Name)
                    and node.targets[0].value.id == "params"
                    and isinstance(node.targets[0].slice, ast.Constant)
                    and node.targets[0].slice.value == "fields"
                ):
                    values.append(node.value)
                # ... params={"fields": ...} passed straight to a request
                elif isinstance(node, ast.Call):
                    for kw in node.keywords:
                        if kw.arg != "params" or not isinstance(kw.value, ast.Dict):
                            continue
                        for k, v in zip(kw.value.keys, kw.value.values):
                            if isinstance(k, ast.Constant) and k.value == "fields":
                                values.append(v)
                # params: dict[str, Any] = {"fields": ...}
                elif (
                    isinstance(node, ast.AnnAssign)
                    and isinstance(node.target, ast.Name)
                    and node.target.id == "params"
                    and isinstance(node.value, ast.Dict)
                ):
                    for k, v in zip(node.value.keys, node.value.values):
                        if isinstance(k, ast.Constant) and k.value == "fields":
                            values.append(v)
                for value in values:
                    # A fixed literal projection is fine, unless it names
                    # 'all' - that is precisely what needs expanding, and
                    # SettingsManager.update() hid one here.
                    if (
                        isinstance(value, ast.Constant)
                        and isinstance(value.value, str)
                        and "all" not in [n.strip() for n in value.value.split(",")]
                    ):
                        continue
                    text = ast.unparse(value)
                    if text.startswith("self._projection("):
                        continue
                    offenders.append(f"{label}: fields = {text[:70]}")
        assert not offenders, (
            "fields parameters built without self._projection(), so 'all' is "
            "not expanded and the request is not recorded (issue #117): "
            f"{sorted(set(offenders))}"
        )

    def test_discovery_sees_indirect_subclasses(self) -> None:
        """Guard the guard: the blind spot that let the bypass through."""
        labels = {label for label, _cls, _tree in manager_classes()}
        assert "cloudinit_files.VMCloudInitFileManager" in labels
        assert "queries.VNetQueryManager" in labels


class TestRequireProjected:
    """The test is what the request asked for, not whether the key came back.

    Most computed fields come back null when there is nothing to report, so
    absence looks like a usable signal -- and a first cut of this fix used
    it. A fleet sweep of 421 rows then found 8 fields across 6 managers that
    go missing outright: a traversal through a *polymorphic* reference
    (``creator#$display`` on tasks, where ``creator`` holds a ``table/key``
    string) is omitted when that reference is null. Keying on absence alone
    raised ``FieldNotProjectedError`` for ``task.creator_display`` on a task
    fetched with the manager's own default projection.

    So the manager records the alias names it asked for, each object
    captures them at construction, and only a field that was never requested
    raises.
    """

    def _manager(self) -> ResourceManager[Any]:
        return MagicMock(spec=ResourceManager)

    def test_present_value_is_returned(self) -> None:
        obj = ResourceObject({"running": True}, self._manager())
        assert obj.require_projected("running") is True

    def test_a_genuine_false_still_reads_as_false(self) -> None:
        obj = ResourceObject({"running": False}, self._manager())
        assert obj.require_projected("running") is False

    def test_null_is_a_value_not_an_absence(self) -> None:
        obj = ResourceObject({"node_name": None}, self._manager())
        assert obj.require_projected("node_name") is None

    def test_absent_field_raises(self) -> None:
        obj = ResourceObject({"$key": 1, "name": "n"}, self._manager())
        with pytest.raises(FieldNotProjectedError) as excinfo:
            obj.require_projected("running")
        assert excinfo.value.field == "running"

    def test_error_names_the_field(self) -> None:
        obj = ResourceObject({}, self._manager())
        with pytest.raises(FieldNotProjectedError, match="running"):
            obj.require_projected("running")

    def test_error_is_not_swallowed_by_the_dict_attribute_fallback(self) -> None:
        """Regression guard on the fix itself.

        ``ResourceObject.__getattr__`` exists to expose row keys as
        attributes, and Python invokes it whenever normal lookup raises
        ``AttributeError``. An ``AttributeError`` subclass raised inside a
        property is therefore caught by that fallback and re-raised as a
        bare "'VM' has no attribute 'is_running'", destroying the
        diagnostic -- and ``hasattr()`` would quietly answer ``False`` for a
        field that exists but was not fetched.
        """
        assert not issubclass(FieldNotProjectedError, AttributeError)
        vm = VM({"$key": 1, "name": "vm"}, self._manager())
        with pytest.raises(FieldNotProjectedError, match="not included in the projection"):
            _ = vm.is_running


class TestAccessorsRefuseToGuess:
    """The reported symptom: a running resource reported as stopped."""

    def _manager(self) -> ResourceManager[Any]:
        return MagicMock(spec=ResourceManager)

    def test_vm_is_running_raises_instead_of_answering_false(self) -> None:
        vm = VM({"$key": 1, "name": "vm-a"}, self._manager())
        with pytest.raises(FieldNotProjectedError):
            _ = vm.is_running

    def test_vm_status_raises_instead_of_answering_unknown(self) -> None:
        vm = VM({"$key": 1, "name": "vm-a"}, self._manager())
        with pytest.raises(FieldNotProjectedError):
            _ = vm.status

    def test_network_is_running_raises(self) -> None:
        net = Network({"$key": 1, "name": "External"}, self._manager())
        with pytest.raises(FieldNotProjectedError):
            _ = net.is_running

    def test_node_is_online_raises(self) -> None:
        node = Node({"$key": 1, "name": "node1"}, self._manager())
        with pytest.raises(FieldNotProjectedError):
            _ = node.is_online

    def test_properly_projected_objects_are_unaffected(self) -> None:
        vm = VM({"$key": 1, "name": "vm-a", "running": True, "status": "running"}, self._manager())
        assert vm.is_running is True
        assert vm.status == "running"

    def test_a_stopped_vm_still_reads_as_stopped(self) -> None:
        vm = VM({"$key": 1, "name": "vm-b", "running": False, "status": "stopped"}, self._manager())
        assert vm.is_running is False
        assert vm.status == "stopped"


#: Accessors that read a computed alias but can still answer from another
#: *projected* field when it is absent -- ``device_type_display`` falls back
#: to the ``device_type`` column, ``size_gb`` to ``disksize``, ``used_percent``
#: to capacity/used. Refusing there would discard a correct answer.
ALIAS_READ_EXEMPTIONS: dict[str, tuple[str, ...]] = {
    "ResourceGroup": ("type_display", "class_display"),
    "ResourceRule": ("type_display",),
    "Drive": ("allocated_bytes",),
    "NASUser": ("status_value",),
    "UpdateSettings": ("source_display", "branch_display"),
    "User": ("auth_source_name",),
    "ClusterTier": ("used_pct",),
    "ClusterTierStatus": ("used_pct",),
}


class TestNoAccessorInventsAComputedValue:
    """AST tripwire: an accessor backed by a computed field must not default.

    ``self.get("running", False)`` cannot distinguish a stopped VM from a VM
    whose ``running`` field was never fetched. Any field the manager obtains
    through a traversal or an aggregate is absent whenever the caller
    narrows ``fields``, so reading one with a fallback re-introduces #117.

    An earlier version matched only the two-argument form. ``self.get(alias)``
    is just as dangerous once the accessor coerces: ``bool(None)`` is
    ``False`` and ``int(None or 0)`` is ``0``. That hole left ``ClusterTier``
    reporting a live 2 TB tier as ``"Offline"`` with zero capacity, and a
    64-core cluster as having 0 cores.
    """

    def test_no_computed_accessor_uses_a_silent_default(self) -> None:
        offenders: list[str] = []
        for path in sorted(RESOURCES_DIR.glob("*.py")):
            source = path.read_text()
            aliases = {m.group(2) for m in COMPUTED_ALIAS.finditer(source)}
            if not aliases:
                continue
            tree = ast.parse(source)
            for cls in (n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)):
                if not any("ResourceObject" in ast.unparse(b) for b in cls.bases):
                    continue
                for node in ast.walk(cls):
                    if (
                        isinstance(node, ast.Call)
                        and isinstance(node.func, ast.Attribute)
                        and node.func.attr == "get"
                        and ast.unparse(node.func.value) == "self"
                        # any arity: self.get(alias) yields None, which
                        # bool()/int()/str() turn into False/0/"" just as
                        # confidently as an explicit default did
                        and node.args
                        and isinstance(node.args[0], ast.Constant)
                        and node.args[0].value in aliases
                        and node.args[0].value not in ALIAS_READ_EXEMPTIONS.get(cls.name, ())
                    ):
                        offenders.append(
                            f"{path.name}:{node.lineno} {cls.name}."
                            f"get({node.args[0].value!r}, ...) — use require_projected()"
                        )
        assert not offenders, (
            f"accessors that would answer for a field they never fetched (issue #117): {offenders}"
        )


class TestPolymorphicAbsenceIsNotMisreported:
    """Regression guard for the false positive found in the lab.

    ``tasks`` asks for ``creator#$display as creator_display``. When a task
    has no creator, the API omits the key rather than returning null. That
    row was correctly projected and must not raise.
    """

    def _manager(self, requested: frozenset[str] | None) -> ResourceManager[Any]:
        mgr = MagicMock(spec=ResourceManager)
        mgr._requested_aliases = requested
        return mgr

    def test_requested_but_omitted_returns_the_default(self) -> None:
        mgr = self._manager(frozenset({"$key", "name", "creator_display"}))
        obj = ResourceObject({"$key": 1, "name": "t"}, mgr)
        assert obj.require_projected("creator_display", "") == ""

    def test_requested_but_omitted_defaults_to_none_when_unspecified(self) -> None:
        mgr = self._manager(frozenset({"$key", "creator_display"}))
        obj = ResourceObject({"$key": 1}, mgr)
        assert obj.require_projected("creator_display") is None

    def test_never_requested_still_raises(self) -> None:
        mgr = self._manager(frozenset({"$key", "name"}))
        obj = ResourceObject({"$key": 1, "name": "t"}, mgr)
        with pytest.raises(FieldNotProjectedError):
            obj.require_projected("creator_display", "")

    def test_unknown_projection_stays_strict(self) -> None:
        obj = ResourceObject({"$key": 1}, self._manager(None))
        with pytest.raises(FieldNotProjectedError):
            obj.require_projected("running", False)

    def test_a_non_frozenset_is_treated_as_unknown(self) -> None:
        """A mocked or hand-built manager must not read as a real projection."""
        mgr = MagicMock(spec=ResourceManager)  # _requested_aliases is a Mock
        obj = ResourceObject({"$key": 1}, mgr)
        assert obj._requested is None
        with pytest.raises(FieldNotProjectedError):
            obj.require_projected("running", False)

    def test_present_value_wins_over_everything(self) -> None:
        mgr = self._manager(frozenset({"running"}))
        obj = ResourceObject({"running": False}, mgr)
        assert obj.require_projected("running", True) is False

    def test_manager_records_what_it_asked_for(self) -> None:
        client = _client_returning([])
        mgr = NetworkManager(client)
        mgr.list(fields=["$key", "name"])
        assert mgr._requested_aliases == frozenset({"$key", "name"})
        mgr.list(fields=["all"])
        assert mgr._requested_aliases is not None
        assert {"all", "running", "status", "$key"} <= mgr._requested_aliases

    def test_default_projection_is_recorded_too(self) -> None:
        client = _client_returning([])
        mgr = NetworkManager(client)
        mgr.list()
        assert mgr._requested_aliases is not None
        assert "running" in mgr._requested_aliases


class TestWriteResponsesDoNotInheritAProjection:
    """A write response is not a query result (issue #117).

    ``POST`` answers with a receipt -- measured on VergeOS 26.1.8, the keys
    are ``$key``, ``$row``, ``dbpath``, ``location``, ``response`` -- and
    ``PUT`` answers with ``{}``. Nothing there was asked for by a
    projection.

    Before this, the object built from such a response inherited whatever
    alias set the manager last fetched with, so
    ``networks.list(); networks.update(...)`` produced an object that
    answered ``is_running`` as ``False`` from a row that never contained
    ``running`` -- the original defect arriving by a side door, and worse,
    an answer that depended on unrelated earlier calls.
    """

    def test_unprojected_build_clears_the_record(self) -> None:
        client = _client_returning([])
        mgr = NetworkManager(client)
        mgr.list()  # records the default projection
        assert mgr._requested_aliases is not None
        obj = mgr._to_model_unprojected({"$key": 1, "name": "n"})
        assert mgr._requested_aliases is None
        assert obj._requested is None

    def test_write_object_reports_unfetched_rather_than_false(self) -> None:
        client = _client_returning([])
        mgr = NetworkManager(client)
        mgr.list()
        obj = mgr._to_model_unprojected({"$key": 1, "name": "n"})
        with pytest.raises(FieldNotProjectedError):
            _ = obj.is_running

    def test_answer_does_not_depend_on_unrelated_history(self) -> None:
        payload = {"$key": 1, "name": "n"}
        outcomes = set()
        for prime in (
            None,
            lambda m: m.list(),
            lambda m: m.list(fields=["$key", "name"]),
            lambda m: m.list(fields=["all"]),
        ):
            mgr = NetworkManager(_client_returning([]))
            if prime:
                prime(mgr)
            obj = mgr._to_model_unprojected(dict(payload))
            try:
                outcomes.add(repr(obj.is_running))
            except FieldNotProjectedError:
                outcomes.add("raised")
        assert outcomes == {"raised"}, outcomes

    def test_a_field_the_write_response_did_return_is_still_readable(self) -> None:
        mgr = NetworkManager(_client_returning([]))
        obj = mgr._to_model_unprojected({"$key": 1, "running": True, "status": "running"})
        assert obj.is_running is True
        assert obj.status == "running"


class TestNoWritePathInheritsAProjection:
    """AST tripwire: write paths must build models with the unprojected helper.

    ``base.create()``/``update()`` were the obvious cases, but 34 managers
    hand-roll a write and fall back to ``self._to_model(response)`` when they
    cannot re-fetch. Each of those inherited the manager's last projection.
    """

    def test_write_methods_use_to_model_unprojected(self) -> None:
        offenders: list[str] = []
        for path in sorted(RESOURCES_DIR.glob("*.py")):
            if path.name == "base.py":
                continue
            tree = ast.parse(path.read_text())
            for cls in (n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)):
                if not any("ResourceManager" in ast.unparse(b) for b in cls.bases):
                    continue
                for fn in cls.body:
                    if not isinstance(fn, ast.FunctionDef):
                        continue
                    calls = [
                        ast.unparse(n.func)
                        for n in ast.walk(fn)
                        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                    ]
                    if "self._to_model" not in calls or "self._projection" in calls:
                        continue
                    writes = any(
                        isinstance(n, ast.Call)
                        and isinstance(n.func, ast.Attribute)
                        and n.func.attr == "_request"
                        and n.args
                        and isinstance(n.args[0], ast.Constant)
                        and n.args[0].value in ("POST", "PUT", "PATCH")
                        for n in ast.walk(fn)
                    )
                    if writes:
                        offenders.append(
                            f"{path.name}:{cls.name}.{fn.name}() — use self._to_model_unprojected()"
                        )
        assert not offenders, (
            "models built from a write response while inheriting the manager's "
            f"last projection (issue #117): {offenders}"
        )


class TestRefreshAdoptsTheRefetchProjection:
    """``refresh()`` replaces the row, so it must replace the record too.

    A task fetched with ``fields=["$key","name"]`` and then refreshed holds
    the full default row, yet kept the narrow record -- so it still raised
    for ``creator_display``, which the server omits, while an identically
    fetched task returned ``""``. Same data, two answers.
    """

    def test_refresh_replaces_the_requested_set(self) -> None:
        client = MagicMock(spec=VergeClient)
        client._request.return_value = [{"$key": 1, "name": "n"}]
        mgr = NetworkManager(client)

        narrow = mgr.list(fields=["$key", "name"])[0]
        assert narrow._requested == frozenset({"$key", "name"})

        client._request.return_value = {
            "$key": 1,
            "name": "n",
            "running": True,
            "status": "running",
        }
        narrow.refresh()

        assert narrow._requested is not None
        assert "running" in narrow._requested
        assert narrow.is_running is True

    def test_refreshed_object_agrees_with_a_fresh_one(self) -> None:
        """The row the server omits must read the same either way."""
        client = MagicMock(spec=VergeClient)
        full = {"$key": 1, "name": "n"}  # 'running' requested but omitted

        client._request.return_value = [full]
        fresh = NetworkManager(client).list()[0]

        mgr = NetworkManager(client)
        client._request.return_value = [{"$key": 1, "name": "n"}]
        narrow = mgr.list(fields=["$key", "name"])[0]
        client._request.return_value = dict(full)
        narrow.refresh()

        def read(obj: Any) -> Any:
            try:
                return obj.is_running
            except FieldNotProjectedError:
                return "raised"

        assert read(narrow) == read(fresh)
