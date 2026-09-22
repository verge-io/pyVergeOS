"""Regression tests: iter_all()/__iter__ pass limit/offset to list().

Any list() override that consumes **kwargs as filter arguments but does not
declare limit/offset parameters will receive them in **kwargs and merge them
into the OData filter (e.g. ``limit eq 100``), which matches nothing and
breaks iteration. Follow-up to issue #96 / PR #99.
"""

from __future__ import annotations

import ast
import pathlib
from typing import Any
from unittest.mock import MagicMock

from pyvergeos import VergeClient
from pyvergeos.resources.vms import VM

RESOURCES_DIR = pathlib.Path(__file__).resolve().parents[2] / "pyvergeos" / "resources"


class TestListSignatureGuard:
    """Static guard: every kwargs-consuming list() must declare limit/offset."""

    def test_no_list_override_leaks_limit_offset_into_kwargs(self) -> None:
        offenders: list[str] = []
        for path in sorted(RESOURCES_DIR.glob("*.py")):
            tree = ast.parse(path.read_text())
            for node in ast.walk(tree):
                if not isinstance(node, ast.ClassDef):
                    continue
                for fn in node.body:
                    if not (isinstance(fn, ast.FunctionDef) and fn.name == "list"):
                        continue
                    kwarg = fn.args.kwarg.arg if fn.args.kwarg else None
                    if kwarg is None:
                        continue
                    consumed = any(
                        isinstance(sub, ast.Name)
                        and sub.id == kwarg
                        and isinstance(sub.ctx, ast.Load)
                        for sub in ast.walk(fn)
                    )
                    argnames = {a.arg for a in fn.args.args + fn.args.kwonlyargs}
                    if consumed and not {"limit", "offset"} <= argnames:
                        offenders.append(f"{path.name}:{node.name}.list")
        assert offenders == [], (
            "list() overrides consume **kwargs but lack limit/offset params; "
            f"iter_all()/__iter__ would leak them into the filter: {offenders}"
        )


class TestScopedManagerPagination:
    """Behavioural checks that limit/offset go to params, not the filter."""

    def _vm(self, mock_client: VergeClient) -> VM:
        return VM({"$key": 100, "name": "test-vm", "machine": 200}, mock_client.vms)

    def _last_params(self, mock_session: MagicMock) -> dict[str, Any]:
        return mock_session.request.call_args.kwargs.get("params", {})

    def test_drives_list_limit_offset_are_params(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        mock_session.request.return_value.json.return_value = []
        vm = self._vm(mock_client)

        vm.drives.list(limit=50, offset=10)

        params = self._last_params(mock_session)
        assert params.get("limit") == 50
        assert params.get("offset") == 10
        assert "limit eq" not in params.get("filter", "")
        assert "offset eq" not in params.get("filter", "")

    def test_drives_iteration_does_not_leak_into_filter(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        mock_session.request.return_value.json.return_value = []
        vm = self._vm(mock_client)

        list(vm.drives)  # __iter__ -> iter_all -> list(limit=100, offset=0)

        params = self._last_params(mock_session)
        assert params.get("limit") == 100
        assert "limit eq" not in params.get("filter", "")
        assert "offset eq" not in params.get("filter", "")

    def test_nics_iteration_does_not_leak_into_filter(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        mock_session.request.return_value.json.return_value = []
        vm = self._vm(mock_client)

        list(vm.nics)

        params = self._last_params(mock_session)
        assert params.get("limit") == 100
        assert "limit eq" not in params.get("filter", "")

    def test_machine_nics_iteration_does_not_leak_into_filter(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """MachineNICManager leaked limit/offset even before PR #99."""
        mock_session.request.return_value.json.return_value = []

        list(mock_client.machine_nics)

        params = self._last_params(mock_session)
        assert params.get("limit") == 100
        assert "limit eq" not in params.get("filter", "")

    def test_storage_tiers_iteration_does_not_leak_into_filter(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        """Delegating manager: limit/offset must forward to super().list()."""
        mock_session.request.return_value.json.return_value = []

        list(mock_client.storage_tiers)

        params = self._last_params(mock_session)
        assert params.get("limit") == 100
        assert "limit eq" not in params.get("filter", "")

    def test_snapshots_iteration_does_not_leak_into_filter(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        mock_session.request.return_value.json.return_value = []
        vm = self._vm(mock_client)

        list(vm.snapshots)

        params = self._last_params(mock_session)
        assert params.get("limit") == 100
        assert "limit eq" not in params.get("filter", "")

    def test_filter_kwargs_still_merge_alongside_pagination(
        self, mock_client: VergeClient, mock_session: MagicMock
    ) -> None:
        mock_session.request.return_value.json.return_value = []
        vm = self._vm(mock_client)

        vm.drives.list(name="data", limit=25)

        params = self._last_params(mock_session)
        assert params.get("limit") == 25
        assert "machine eq 200" in params.get("filter", "")
        assert "name eq 'data'" in params.get("filter", "")
