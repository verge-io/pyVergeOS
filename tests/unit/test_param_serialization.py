"""Serialization of user-supplied sequence parameters (issue #101).

``",".join(value)`` on a caller-supplied value is the classic Python
footgun: a ``str`` is iterable, so ``",".join("$key,name")`` silently
produces ``'$,k,e,y,,,n,a,m,e'`` — which the API accepts and answers with
rows containing no usable fields. The same shape corrupted write-path
parameters (``dns_servers``, ``ssh_keys``, ``valid_users``, ...).

All such parameters must go through ``serialize_list()`` /
``normalize_fields()``; an AST tripwire enforces it.
"""

from __future__ import annotations

import ast
import pathlib
from typing import Any
from unittest.mock import MagicMock

import pytest

from pyvergeos import VergeClient
from pyvergeos.resources.base import normalize_fields, serialize_list, split_fields
from pyvergeos.resources.vms import VM

PACKAGE_DIR = pathlib.Path(__file__).resolve().parents[2] / "pyvergeos"


class TestSerializeHelpers:
    def test_list_is_joined(self) -> None:
        assert serialize_list(["a", "b"]) == "a,b"
        assert serialize_list(["a", "b"], "\n") == "a\nb"

    def test_string_passes_through(self) -> None:
        assert serialize_list("a,b") == "a,b"
        assert serialize_list("one two", "\n") == "one two"

    def test_none_and_empty(self) -> None:
        assert serialize_list(None) is None
        assert serialize_list([]) == ""
        assert serialize_list("") == ""

    def test_mapping_is_rejected(self) -> None:
        """Iterating a mapping yields its keys, which look like real values.

        ``ssh_keys={"a": 1}`` previously serialised to ``'a'`` and was sent.
        """
        with pytest.raises(TypeError, match="iterating a mapping yields its keys"):
            serialize_list({"a": 1, "b": 2})

    def test_unordered_collection_is_rejected(self) -> None:
        """Order is part of the value for several of these parameters.

        The first entry of ``dnslist`` is the primary DNS server, so joining
        a set would send a different value run to run.
        """
        for unordered in ({"b", "a"}, frozenset({"b", "a"})):
            with pytest.raises(TypeError, match="ordered sequence"):
                serialize_list(unordered)

    def test_non_string_values_are_rejected_clearly(self) -> None:
        for bad in ([1, 2], ["ok", None], [["nested"]]):
            with pytest.raises(TypeError, match="values must be strings"):
                serialize_list(bad)

    def test_generator_is_accepted(self) -> None:
        assert serialize_list(x for x in ["a", "b"]) == "a,b"

    def test_tuple_works(self) -> None:
        assert serialize_list(("a", "b")) == "a,b"

    def test_normalize_fields_string(self) -> None:
        assert normalize_fields("$key,name") == "$key,name"
        assert normalize_fields("all") == "all"

    def test_normalize_fields_list(self) -> None:
        assert normalize_fields(["$key", "name"]) == "$key,name"

    def test_normalize_fields_empty_means_no_projection(self) -> None:
        assert normalize_fields(None) is None
        assert normalize_fields([]) is None
        assert normalize_fields("") is None

    def test_normalize_fields_rejects_degenerate_strings(self) -> None:
        """A projection with no field names must mean "no projection".

        Passing "," or "   " through asks the API for a projection with no
        columns; it answers with a single {"$count": N} row instead of the
        requested resources -- measured on VergeOS 26.1.8, a 5-VM list
        collapsed to one meaningless row. That is the silent-empty result
        #101 was filed for, so it must not reach the wire.
        """
        for degenerate in (",", ",,,", "   ", " , "):
            assert normalize_fields(degenerate) is None, degenerate

    def test_normalize_fields_cleans_like_split_fields(self) -> None:
        """String and sequence forms must stay interchangeable."""
        for value in (" $key , name ", "$key,,name", "$key,name,"):
            assert normalize_fields(value) == "$key,name", value
        assert normalize_fields("$key,name") == ",".join(split_fields("$key,name"))

    def test_normalize_fields_preserves_alias_syntax(self) -> None:
        """'name as vm_name' contains a space but is one field expression."""
        assert normalize_fields("$key,name as vm_name") == "$key,name as vm_name"
        assert split_fields("$key,name as vm_name") == ["$key", "name as vm_name"]

    def test_non_string_field_names_are_rejected(self) -> None:
        """Coercing with str() would silently produce a wrong projection.

        ``normalize_fields([1, 2])`` raised TypeError before this change (the
        join refused the ints). Coercing them to "1,2" would send a
        plausible-looking but wrong projection instead of failing, which is
        the corruption this issue exists to prevent.
        """
        for bad in ([1, 2], ["ok", 3], (None,)):
            with pytest.raises(TypeError, match="field names must be strings"):
                normalize_fields(bad)  # type: ignore[arg-type]
            with pytest.raises(TypeError, match="field names must be strings"):
                split_fields(bad)  # type: ignore[arg-type]

    @pytest.mark.parametrize(
        ("string_form", "sequence_form"),
        [
            ("$key,", ["$key", ""]),
            (" $key , name ", [" $key ", "name"]),
            ("$key,,name", ["$key", "", "name"]),
        ],
    )
    def test_string_and_sequence_forms_agree(
        self, string_form: str, sequence_form: list[str]
    ) -> None:
        """The two forms must clean identically, as the docstring promises."""
        assert normalize_fields(string_form) == normalize_fields(sequence_form)

    def test_fields_mapping_is_rejected(self) -> None:
        """Iterating a dict yields its keys, which would look plausible."""
        with pytest.raises(TypeError, match="sequence of field names"):
            normalize_fields({"name": 1})  # type: ignore[arg-type]
        with pytest.raises(TypeError, match="sequence of field names"):
            split_fields({"name": 1})  # type: ignore[arg-type]


class TestFieldsParameter:
    """String and list forms of ``fields`` must be equivalent on the wire."""

    def _params(self, mock_session: MagicMock) -> dict[str, Any]:
        return mock_session.request.call_args.kwargs.get("params", {})

    def test_base_list_fields_string(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        mock_session.request.return_value.json.return_value = []

        mock_client.networks.list(fields="$key,name")

        assert self._params(mock_session)["fields"] == "$key,name"

    def test_base_list_fields_list(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        mock_session.request.return_value.json.return_value = []

        mock_client.networks.list(fields=["$key", "name"])

        assert self._params(mock_session)["fields"] == "$key,name"

    def test_vms_list_fields_string_not_exploded(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """The reported reproduction: fields='$key,name' must not become
        '$,k,e,y,,,n,a,m,e'."""
        mock_session.request.return_value.json.return_value = []

        mock_client.vms.list(fields="$key,name")

        sent = self._params(mock_session)["fields"]
        assert sent == "$key,name"
        assert ",k,e,y" not in sent

    def test_get_fields_string(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        mock_session.request.return_value.json.return_value = {"$key": 1, "name": "x"}

        mock_client.networks.get(1, fields="$key,name")

        assert self._params(mock_session)["fields"] == "$key,name"

    def test_scoped_manager_fields_string(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        mock_session.request.return_value.json.return_value = []
        vm = VM({"$key": 100, "name": "test-vm", "machine": 200}, mock_client.vms)

        vm.drives.list(fields="$key,name")

        assert self._params(mock_session)["fields"] == "$key,name"

    def test_fields_all_string(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        """``all`` survives as a token and is not split character by character.

        It no longer travels alone: the manager's computed entries are
        appended so that ``all`` is a true superset of the default
        projection, because the API resolves ``all`` to own columns only
        (issue #117). The point this test guards is the #101 one — that the
        string form is not exploded into ``a,l,l``.
        """
        mock_session.request.return_value.json.return_value = []

        mock_client.networks.list(fields="all")

        sent = self._params(mock_session)["fields"].split(",")
        assert sent[0] == "all"
        assert "machine#status#running as running" in sent


class TestWritePathSerialization:
    """Write-path sequence params accept both string and list forms."""

    def _body(self, mock_session: MagicMock) -> dict[str, Any]:
        for call in mock_session.request.call_args_list:
            if call.kwargs.get("method") in ("POST", "PUT") and call.kwargs.get("json"):
                return call.kwargs["json"]
        raise AssertionError("no write request captured")

    def test_users_ssh_keys_string(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        mock_session.request.return_value.json.return_value = {"$key": 1, "name": "u"}

        mock_client.users.update(1, ssh_keys="ssh-rsa AAAA key1")

        assert self._body(mock_session)["ssh_keys"] == "ssh-rsa AAAA key1"

    def test_users_ssh_keys_list(self, mock_client: VergeClient, mock_session: MagicMock) -> None:
        mock_session.request.return_value.json.return_value = {"$key": 1, "name": "u"}

        mock_client.users.update(1, ssh_keys=["k1", "k2"])

        assert self._body(mock_session)["ssh_keys"] == "k1\nk2"

    def test_api_key_ip_allow_list_string_not_exploded(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        mock_session.request.return_value.json.return_value = {"$key": 1, "name": "k"}

        mock_client.api_keys.create(name="k", user=1, ip_allow_list="10.0.0.0/8,192.168.1.0/24")

        sent = self._body(mock_session)["ip_allow_list"]
        assert sent == "10.0.0.0/8,192.168.1.0/24"
        assert "1,0" not in sent

    def test_api_key_ip_allow_list_list(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        mock_session.request.return_value.json.return_value = {"$key": 1, "name": "k"}

        mock_client.api_keys.create(name="k", user=1, ip_allow_list=["10.0.0.0/8"])

        assert self._body(mock_session)["ip_allow_list"] == "10.0.0.0/8"


class TestParamJoinTripwire:
    """No function may join a caller-supplied parameter directly.

    Root-cause guard for #101: ``sep.join(param)`` succeeds on a bare
    string and silently corrupts the request. All serialization of
    user-supplied sequences must go through ``serialize_list()`` /
    ``normalize_fields()``, which pass strings through.
    """

    #: Helpers that launder a caller value into a safe form.
    SANCTIONED = frozenset({"serialize_list", "normalize_fields", "split_fields"})

    @classmethod
    def _tainted_names(cls, node: ast.FunctionDef | ast.AsyncFunctionDef) -> set[str]:
        """Parameters, plus locals that alias one.

        The original tripwire only matched ``join(param)`` with the parameter
        named directly. Six sites escaped it by aliasing first::

            field_list = list(fields)          # or: field_list = fields
            params["fields"] = ",".join(field_list)

        ``list("$key,name")`` splits a string into characters just as
        ``join`` does, so the alias is every bit as corrupting. Assignments
        through a sanctioned helper are laundered and clear the taint.
        """
        tainted = {a.arg for a in node.args.args + node.args.kwonlyargs} - {"self"}
        for _ in range(3):  # fixed point; alias chains here are 1-2 deep
            grown = False
            for sub in ast.walk(node):
                if not isinstance(sub, ast.Assign):
                    continue
                targets = {t.id for t in sub.targets if isinstance(t, ast.Name)}
                if not targets or targets <= tainted:
                    continue
                if cls._expr_is_tainted(sub.value, tainted):
                    tainted |= targets
                    grown = True
            if not grown:
                break
        return tainted

    @classmethod
    def _expr_is_tainted(cls, expr: ast.expr, tainted: set[str]) -> bool:
        """True if the expression carries a caller value through unlaundered."""
        if isinstance(expr, ast.Name):
            return expr.id in tainted
        if isinstance(expr, ast.Call):
            func = expr.func
            name = getattr(func, "id", None) or getattr(func, "attr", None)
            if name in cls.SANCTIONED:
                return False  # laundered
            if name in ("list", "tuple", "sorted"):
                return any(cls._expr_is_tainted(a, tainted) for a in expr.args)
            return False
        if isinstance(expr, ast.BoolOp):  # fields or DEFAULTS
            return any(cls._expr_is_tainted(v, tainted) for v in expr.values)
        if isinstance(expr, ast.IfExp):  # list(fields) if fields else DEFAULTS
            return cls._expr_is_tainted(expr.body, tainted) or cls._expr_is_tainted(
                expr.orelse, tainted
            )
        return False

    def test_no_direct_join_of_function_parameters(self) -> None:
        offenders = self._scan(PACKAGE_DIR)
        assert offenders == [], (
            "Join of a caller-supplied parameter (or a local aliasing one); a bare "
            "string would be joined character-by-character and silently corrupt the "
            "request (issue #101). Use serialize_list()/normalize_fields()/"
            "split_fields():\n" + "\n".join(offenders)
        )

    @classmethod
    def _scan(cls, root: pathlib.Path) -> list[str]:
        offenders: list[str] = []
        for path in sorted(root.rglob("*.py")):
            tree = ast.parse(path.read_text())
            for node in ast.walk(tree):
                if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                if node.name in cls.SANCTIONED:
                    continue  # the sanctioned implementations (str-guarded)
                tainted = cls._tainted_names(node)
                for sub in ast.walk(node):
                    if (
                        isinstance(sub, ast.Call)
                        and isinstance(sub.func, ast.Attribute)
                        and sub.func.attr == "join"
                        and sub.args
                        and isinstance(sub.args[0], ast.Name)
                        and sub.args[0].id in tainted
                    ):
                        offenders.append(
                            f"{path.relative_to(root.parent)}:{sub.lineno} "
                            f"{node.name}() joins {sub.args[0].id!r}"
                        )
        return offenders

    def test_tripwire_detects_the_aliased_form(self, tmp_path: pathlib.Path) -> None:
        """The extended tripwire must catch what the original missed.

        Modelled on the real ``certificates.get`` / ``auth_sources.get``
        shape that shipped past the first version of this guard.
        """
        pkg = tmp_path / "pkg"
        pkg.mkdir()
        (pkg / "mod.py").write_text(
            "def get(key, fields=None, include_settings=False):\n"
            "    request_fields = list(fields) if fields else list(DEFAULTS)\n"
            "    if include_settings:\n"
            "        request_fields.append('settings')\n"
            "    return {'fields': ','.join(request_fields)}\n"
            "\n"
            "def get_alias(key, fields=None):\n"
            "    field_list = fields\n"
            "    return {'fields': ','.join(field_list)}\n"
            "\n"
            "def get_or(key, fields=None):\n"
            "    field_list = fields or DEFAULTS\n"
            "    return {'fields': ','.join(field_list)}\n"
            "\n"
            "def safe(key, fields=None):\n"
            "    field_list = split_fields(fields) or list(DEFAULTS)\n"
            "    return {'fields': ','.join(field_list)}\n"
        )
        offenders = self._scan(pkg)
        caught = {o.split("py:")[1].split("(")[0].split()[1] for o in offenders}
        assert caught == {"get", "get_alias", "get_or"}, offenders
        assert not any("safe" in o for o in offenders), offenders


class TestCertificateIncludeKeys:
    """include_keys must augment whatever projection was requested (#101).

    It previously applied only to the default projection, so supplying
    ``fields`` silently dropped the key material the caller asked for --
    matching neither AuthSourceManager.get(include_settings=...) nor
    OidcApplicationManager.get(include_secret=...), which both append.
    """

    def _fields(self, mock_session: MagicMock) -> str:
        return str(mock_session.request.call_args.kwargs["params"]["fields"])

    def test_get_appends_key_fields_to_explicit_projection(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        mock_session.request.return_value.json.return_value = {"$key": 1, "domain": "d"}

        mock_client.certificates.get(1, fields="$key,domain", include_keys=True)

        sent = self._fields(mock_session)
        assert sent == "$key,domain,public,private,chain"

    def test_list_appends_key_fields_to_explicit_projection(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        mock_session.request.return_value.json.return_value = []

        mock_client.certificates.list(fields="$key,domain", include_keys=True)

        assert self._fields(mock_session) == "$key,domain,public,private,chain"

    def test_without_include_keys_no_key_material_is_requested(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        mock_session.request.return_value.json.return_value = {"$key": 1}

        mock_client.certificates.get(1, fields="$key,domain")

        assert self._fields(mock_session) == "$key,domain"

    def test_key_fields_are_not_duplicated(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        mock_session.request.return_value.json.return_value = {"$key": 1}

        mock_client.certificates.get(1, fields="$key,public", include_keys=True)

        assert self._fields(mock_session) == "$key,public,private,chain"

    def test_degenerate_projection_falls_back_to_defaults(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """A projection with no field names must not send an empty fields=."""
        mock_session.request.return_value.json.return_value = {"$key": 1}

        mock_client.certificates.get(1, fields=",")

        sent = self._fields(mock_session)
        assert sent != ""
        assert "domain" in sent
