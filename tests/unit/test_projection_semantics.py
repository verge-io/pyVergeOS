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
import pathlib
import re
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

    def test_no_defaults_is_a_no_op(self) -> None:
        assert expand_projection(["all"], None) == ["all"]

    def test_empty_projection_is_a_no_op(self) -> None:
        assert expand_projection(None, DEFAULT_NETWORK_FIELDS) is None

    def test_field_merely_containing_all_is_not_the_token(self) -> None:
        assert expand_projection(["allocated_bytes"], DEFAULT_NETWORK_FIELDS) == ["allocated_bytes"]

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


class TestNoManagerBypassesProjectionExpansion:
    """AST tripwire: managers must not serialize ``fields`` themselves.

    Many managers assemble ``params`` and call ``_request`` directly instead
    of delegating to ``ResourceManager.list()``. Each such site that called
    ``normalize_fields(fields)`` was a hole in the expansion: ``nodes`` was
    one, which is why ``fields=["all"]`` kept losing ``$key`` there long
    after the base class had been fixed. ``self._projection(fields)`` is the
    single serialization point.
    """

    def test_manager_methods_use_the_projection_helper(self) -> None:
        offenders: list[str] = []
        for path in sorted(RESOURCES_DIR.glob("*.py")):
            if path.name == "base.py":
                continue
            tree = ast.parse(path.read_text())
            for cls in (n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)):
                if not any("ResourceManager" in ast.unparse(b) for b in cls.bases):
                    continue
                for fn in ast.walk(cls):
                    if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        continue
                    names = {a.arg for a in fn.args.args} | {a.arg for a in fn.args.kwonlyargs}
                    if "fields" not in names:
                        continue
                    for node in ast.walk(fn):
                        if (
                            isinstance(node, ast.Call)
                            and isinstance(node.func, ast.Name)
                            and node.func.id == "normalize_fields"
                            and len(node.args) == 1
                            and isinstance(node.args[0], ast.Name)
                            and node.args[0].id == "fields"
                        ):
                            offenders.append(
                                f"{path.name}:{node.lineno} {cls.name}.{fn.name}() — "
                                "use self._projection(fields)"
                            )
        assert not offenders, (
            "caller-supplied projections serialized without expanding 'all' "
            f"(issue #117): {offenders}"
        )
