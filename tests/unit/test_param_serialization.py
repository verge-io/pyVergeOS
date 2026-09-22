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

from pyvergeos import VergeClient
from pyvergeos.resources.base import normalize_fields, serialize_list
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
        mock_session.request.return_value.json.return_value = []

        mock_client.networks.list(fields="all")

        assert self._params(mock_session)["fields"] == "all"


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

    def test_no_direct_join_of_function_parameters(self) -> None:
        offenders: list[str] = []
        for path in sorted(PACKAGE_DIR.rglob("*.py")):
            tree = ast.parse(path.read_text())
            for node in ast.walk(tree):
                if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                if node.name in ("serialize_list", "normalize_fields"):
                    continue  # the sanctioned implementations (str-guarded)
                params = {a.arg for a in node.args.args + node.args.kwonlyargs} - {"self"}
                for sub in ast.walk(node):
                    if (
                        isinstance(sub, ast.Call)
                        and isinstance(sub.func, ast.Attribute)
                        and sub.func.attr == "join"
                        and sub.args
                        and isinstance(sub.args[0], ast.Name)
                        and sub.args[0].id in params
                    ):
                        offenders.append(
                            f"{path.relative_to(PACKAGE_DIR.parent)}:{sub.lineno} "
                            f"{node.name}() joins parameter {sub.args[0].id!r}"
                        )
        assert offenders == [], (
            "Direct join of caller-supplied parameters; a bare string would be "
            "joined character-by-character and silently corrupt the request "
            "(issue #101). Use serialize_list()/normalize_fields():\n" + "\n".join(offenders)
        )
