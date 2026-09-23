"""``fields="all"`` is not a superset of a manager's default projection
(issue #117).

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

from pyvergeos import VergeClient
from pyvergeos.resources.base import (
    expand_projection,
    is_computed_projection,
    projection_alias,
)
from pyvergeos.resources.networks import DEFAULT_NETWORK_FIELDS, NetworkManager
from pyvergeos.resources.vms import VM_DEFAULT_FIELDS

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
