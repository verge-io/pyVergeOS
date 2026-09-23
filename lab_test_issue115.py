"""Lab verification for issue #115 - filter values must go through quote_value.

Before the fix, a caller-supplied value was parsed as filter grammar: a
crafted value returned the entire table instead of zero rows, and the #100
brace effect reached these sites too.

Mostly read-only. Creates a couple of scratch VMs for the round-trip checks
and deletes them. Never touches Core/DMZ.

Usage:  .venv/bin/python lab_test_issue115.py [round-label]
        SKIP_FIX_GUARD=1 ... to run deliberately against a pre-fix tree
"""

from __future__ import annotations

import os
import sys
import uuid

from pyvergeos import VergeClient
from pyvergeos.exceptions import APIError, NotFoundError
from pyvergeos.filters import quote_value
from pyvergeos.resources.system import RootCertificateManager, SettingsManager
from pyvergeos.resources.task_events import TaskEventManager

LABEL = sys.argv[1] if len(sys.argv) > 1 else "r1"
TAG = uuid.uuid4().hex[:6]
PREFIX = f"zzq{TAG}"

results: list[tuple[str, bool, str]] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    results.append((label, ok, detail))
    print(f"  [{'PASS' if ok else 'FAIL'}] {label}{': ' + detail if detail else ''}")


def _assert_fix_loaded() -> None:
    import pyvergeos
    from pyvergeos.resources import system as system_mod
    import inspect

    print(f"SDK under test: {pyvergeos.__file__}")
    src = inspect.getsource(system_mod.SettingsManager.list)
    quoted = "quote_value(key_contains)" in src
    if os.environ.get("SKIP_FIX_GUARD"):
        print(f"  (guard skipped; key_contains quoted = {quoted})")
        return
    if not quoted:
        raise SystemExit(
            "REFUSING TO RUN: SettingsManager.list() still interpolates "
            "key_contains directly. This tree does not contain the #115 fix. "
            "Set SKIP_FIX_GUARD=1 to run it anyway as a pre-fix control."
        )


def rowcount(result) -> int:
    if result is None:
        return 0
    return len(result) if isinstance(result, list) else 1


def safe_count(fn, *args, **kwargs):
    """Call fn and return a row count, or the exception if it raised.

    A pre-fix tree can make the platform reject the malformed filter
    outright, so the control run must survive that and keep reporting.
    """
    try:
        return rowcount(fn(*args, **kwargs))
    except APIError as exc:
        return exc


def main() -> int:
    _assert_fix_loaded()
    client = VergeClient.from_env()
    settings = SettingsManager(client)
    events = TaskEventManager(client)
    certs = RootCertificateManager(client)
    vms: list = []

    try:
        total_settings = rowcount(
            client._request("GET", "settings", params={"fields": "key", "limit": "500"})
        )
        total_tasks = rowcount(
            client._request("GET", "tasks", params={"fields": "$key", "limit": "500"})
        )
        print(f"baseline: {total_settings} settings rows, {total_tasks} task rows")

        # pick a real prefix that matches something, to prove we did not
        # simply break matching altogether
        keys = client._request("GET", "settings", params={"fields": "key", "limit": "10"})
        stem = next((k["key"][:4] for k in keys if len(k.get("key", "")) > 4), "clou")
        baseline = rowcount(settings.list(key_contains=stem, limit=500))
        check("0 baseline: a real prefix still matches", baseline > 0,
              f"{stem!r} -> {baseline} rows")

        # ===========================================================
        print("\n=== A. injection is closed (settings, ct operator) ===")
        inj_or = f"zzzz' or key ne 'zzzz"
        n = safe_count(settings.list, key_contains=inj_or, limit=500)
        check("A1 crafted OR returns 0 rows, not the whole table", n == 0,
              f"{n} rows (table has {total_settings})")

        inj_and = f"zzzz' and key ne 'zzzz"
        n = safe_count(settings.list, key_contains=inj_and, limit=500)
        check("A2 crafted AND returns 0 rows", n == 0, f"{n} rows")

        # ===========================================================
        print("\n=== B. the #100 symptom no longer reaches these sites ===")
        n = safe_count(settings.list, key_contains=f"{stem}{{x}}", limit=500)
        check("B1 braced value matches nothing (was: matched the stem)", n == 0,
              f"{stem}{{x}} -> {n} rows")
        n = safe_count(settings.list, key_contains=f"{stem}'", limit=500)
        check("B2 apostrophe is not truncated", n == 0, f"{stem}' -> {n} rows")
        n = safe_count(settings.list, key_contains=f"{stem}\\", limit=500)
        check("B3 trailing backslash does not break the literal", n == 0,
              f"{stem}\\ -> {n} rows")

        # ===========================================================
        print("\n=== C. a second module: tasks.list_by_action ===")
        n = safe_count(client.tasks.list_by_action, inj_or, limit=500)
        check("C1 crafted OR returns 0 rows", n == 0,
              f"{n} rows (table has {total_tasks})")
        n = safe_count(client.tasks.list_by_action, "zzzz-nope", limit=500)
        check("C2 benign non-match still 0", n == 0, f"{n} rows")

        # ===========================================================
        print("\n=== D. a third module: task_events.list(table=...) ===")
        n = safe_count(events.list, table=inj_or, limit=500)
        check("D1 crafted OR returns 0 rows", n == 0, f"{n} rows")

        # ===========================================================
        print("\n=== E. a fourth module: root certificates (ct) ===")
        for probe in [inj_or, f"{stem}{{x}}"]:
            try:
                certs.get_by_subject(probe)
                check(f"E {probe[:20]!r} did not resolve a row", False, "returned a row")
            except NotFoundError:
                check(f"E {probe[:20]!r} correctly finds nothing", True, "")
            except APIError as exc:
                check(f"E {probe[:20]!r} errored rather than mismatching", True,
                      str(exc)[:60])

        # ===========================================================
        print("\n=== F. round-trip: hostile names still resolve to themselves ===")
        hostile_names = [
            f"{PREFIX}-o'brien",
            f"{PREFIX}-br{{x}}ace",
            f"{PREFIX}-back\\slash",
            f"{PREFIX}-mix'{{a}}b",
        ]
        for nm in hostile_names:
            vm = client.vms.create(name=nm, cpu_cores=1, ram=512, os_family="linux")
            vms.append(vm)
        for vm, nm in zip(vms, hostile_names):
            try:
                got = client.vms.get(name=nm)
                ok = str(got.key) == str(vm.key)
                detail = "" if ok else f"resolved {dict(got)['name']!r}"
            except APIError as exc:
                ok, detail = False, str(exc)[:80]
            check(f"F {nm!r}", ok, detail)

        # ===========================================================
        print("\n=== G. quoting is applied, not just matching by luck ===")
        lit = quote_value(inj_or)
        check("G1 quote_value escapes both apostrophes",
              lit.count("\\'") == 2, lit)

    finally:
        print("\n=== Cleanup ===")
        for vm in vms:
            try:
                vm.delete()
            except Exception as exc:  # noqa: BLE001
                print(f"  vm {vm.key} cleanup failed: {str(exc)[:70]}")
        left = [v for v in client.vms.list()
                if str(dict(v).get("name", "")).startswith(PREFIX)]
        print(f"  leftover scratch objects: {[dict(o).get('name') for o in left] or 'none'}")

    failed = [r for r in results if not r[1]]
    print(f"\n{'=' * 60}\n{len(results) - len(failed)}/{len(results)} checks passed ({LABEL})")
    for label, _, detail in failed:
        print(f"  FAIL {label}: {detail}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
