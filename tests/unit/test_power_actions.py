"""Tripwire for the power-action vocabulary used across resource modules.

Issue #42 fixed ``VM.power_off(force=True)`` sending an action string the
platform rejects.  The same bug survived untouched in ``networks.py`` until
issue #112, because nothing tied the two call sites together and the unit
test asserted the broken value.  These tests scan every resource module so a
third occurrence cannot ship.
"""

from __future__ import annotations

import ast
import pathlib

import pytest

PACKAGE_DIR = pathlib.Path(__file__).resolve().parents[2] / "pyvergeos"
RESOURCES_DIR = PACKAGE_DIR / "resources"

# The action vocabulary the platform accepts for VM-style power endpoints
# (vm_actions, vnet_actions).  Confirmed against VergeOS docs for vm_actions
# and probed on a live system for vnet_actions (issue #112).
VALID_FORCE_ACTION = "kill"
VALID_GRACEFUL_ACTION = "poweroff"

# Values that look plausible but are rejected by the platform.
REJECTED_ACTIONS = frozenset({"killpower", "forceoff", "force_off", "poweroff_force"})


def _resource_sources() -> list[pathlib.Path]:
    return sorted(RESOURCES_DIR.rglob("*.py"))


class TestNoRejectedActionLiterals:
    """No module may contain a known-invalid action string."""

    def test_rejected_action_strings_absent(self) -> None:
        offenders: list[str] = []
        for path in _resource_sources():
            tree = ast.parse(path.read_text())
            for node in ast.walk(tree):
                if isinstance(node, ast.Constant) and node.value in REJECTED_ACTIONS:
                    offenders.append(
                        f"{path.relative_to(PACKAGE_DIR.parent)}:{node.lineno} {node.value!r}"
                    )
        assert offenders == [], (
            'Action string the platform rejects with "value ... is not in list for '
            "field 'action'\" (issues #42, #112). The force value is "
            f"{VALID_FORCE_ACTION!r}:\n" + "\n".join(offenders)
        )


class TestForcePowerOffVocabulary:
    """Every ``power_off(force=...)`` must pick kill/poweroff, not a variant."""

    @staticmethod
    def _force_conditionals(path: pathlib.Path) -> list[tuple[int, ast.IfExp]]:
        """Find ``X if force else Y`` expressions inside power_off methods."""
        found: list[tuple[int, ast.IfExp]] = []
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if node.name != "power_off":
                continue
            for sub in ast.walk(node):
                if (
                    isinstance(sub, ast.IfExp)
                    and isinstance(sub.test, ast.Name)
                    and sub.test.id == "force"
                ):
                    found.append((sub.lineno, sub))
        return found

    def test_force_selects_kill_and_poweroff(self) -> None:
        checked = 0
        problems: list[str] = []
        for path in _resource_sources():
            for lineno, expr in self._force_conditionals(path):
                checked += 1
                where = f"{path.relative_to(PACKAGE_DIR.parent)}:{lineno}"
                body, orelse = expr.body, expr.orelse
                if not (isinstance(body, ast.Constant) and isinstance(orelse, ast.Constant)):
                    problems.append(f"{where}: force branch is not a pair of literals")
                    continue
                if body.value != VALID_FORCE_ACTION:
                    problems.append(
                        f"{where}: force=True sends {body.value!r}, expected {VALID_FORCE_ACTION!r}"
                    )
                if orelse.value != VALID_GRACEFUL_ACTION:
                    problems.append(
                        f"{where}: force=False sends {orelse.value!r}, "
                        f"expected {VALID_GRACEFUL_ACTION!r}"
                    )
        assert problems == [], "\n".join(problems)
        # Guard the guard: if the shape of these methods changes so the scan
        # matches nothing, the test would pass vacuously.
        assert checked >= 3, (
            f"expected to check at least 3 force power_off sites, found {checked}; "
            "the scan pattern has drifted and is no longer protecting anything"
        )


class TestPowerActionDocstrings:
    """Docstrings must not advertise an action the platform rejects."""

    @pytest.mark.parametrize("path", _resource_sources(), ids=lambda p: p.name)
    def test_docstrings_free_of_rejected_actions(self, path: pathlib.Path) -> None:
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if not isinstance(
                node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Module)
            ):
                continue
            doc = ast.get_docstring(node)
            if not doc:
                continue
            for bad in REJECTED_ACTIONS:
                assert bad not in doc, (
                    f"{path.relative_to(PACKAGE_DIR.parent)}: docstring advertises "
                    f"invalid action {bad!r} (issue #112)"
                )
