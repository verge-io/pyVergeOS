"""Lab verification for issue #117 - fields="all" must be a superset, and
accessors must not invent a value for a field they never fetched.

Read-only. Never touches Core/DMZ; it only reads existing resources.

Usage:  .venv/bin/python lab_test_issue117.py [round-label]
        SKIP_FIX_GUARD=1 ... to run deliberately against a pre-fix tree
"""

from __future__ import annotations

import os
import re
import sys

from pyvergeos import VergeClient
from pyvergeos.exceptions import FieldNotProjectedError

LABEL = sys.argv[1] if len(sys.argv) > 1 else "r1"

results: list[tuple[str, bool, str]] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    results.append((label, ok, detail))
    print(f"  [{'PASS' if ok else 'FAIL'}] {label}{': ' + detail if detail else ''}")


def _assert_fix_loaded() -> None:
    if os.environ.get("SKIP_FIX_GUARD"):
        return
    from pyvergeos.resources import base

    if not hasattr(base, "expand_projection"):
        raise SystemExit("expand_projection() missing - the #117 fix is not loaded")
    from pyvergeos.resources.base import ResourceObject

    if not hasattr(ResourceObject, "require_projected"):
        raise SystemExit("require_projected() missing - the #117 fix is not loaded")


def alias_names(defaults: list[str]) -> list[str]:
    out = []
    for field in defaults or []:
        m = re.search(r"\s+as\s+(\S+)\s*$", field)
        if m:
            out.append(m.group(1))
    return out


def main() -> int:
    _assert_fix_loaded()
    client = VergeClient(
        host=os.environ["VERGE_HOST"],
        username=os.environ["VERGE_USERNAME"],
        password=os.environ["VERGE_PASSWORD"],
        verify_ssl=False,
    )

    managers = [
        ("networks", client.networks),
        ("vms", client.vms),
        ("nodes", client.nodes),
        ("clusters", client.clusters),
        ("tenants", client.tenants),
    ]

    print(f"\n== round {LABEL}: 'all' is a superset of the default projection ==")
    for label, mgr in managers:
        truth = {r["$key"]: dict(r) for r in mgr.list()}
        under_all = {r["$key"]: dict(r) for r in mgr.list(fields=["all"])}
        if not truth:
            check(f"{label}: has rows", False, "no rows to compare")
            continue
        k = next(iter(truth))
        t = truth[k]
        a = under_all.get(k)
        if a is None:
            check(f"{label}: same rows under all", False, f"key {k} missing")
            continue
        missing = sorted(set(t) - set(a))
        check(f"{label}: all is a superset", not missing, f"lost {missing}" if missing else "")
        mismatched = {f: (t[f], a[f]) for f in t if f in a and t[f] != a[f]}
        check(f"{label}: values agree with default projection", not mismatched, str(mismatched))
        check(f"{label}: all still widens", len(a) > len(t), f"default={len(t)} all={len(a)}")

    print("\n== the reported symptom: a running resource read back under 'all' ==")
    truth = {n["name"]: n.is_running for n in client.networks.list()}
    running = [name for name, r in truth.items() if r]
    check("lab has a running network to test with", bool(running), f"{len(running)} running")
    wrong = []
    for name in running:
        net = client.networks.get(name=name, fields=["all"])
        if net.is_running is not True or net.status != "running":
            wrong.append((name, net.is_running, net.get("status", "<ABSENT>")))
    check("every running network reports running under all", not wrong, str(wrong))

    vm_truth = {v["name"]: v.is_running for v in client.vms.list()}
    vm_running = [n for n, r in vm_truth.items() if r]
    wrong_vms = []
    for name in vm_running:
        vm = client.vms.get(name=name, fields=["all"])
        if vm.is_running is not True:
            wrong_vms.append((name, vm.is_running))
    check(
        f"every running VM reports running under all ({len(vm_running)} running)",
        not wrong_vms,
        str(wrong_vms),
    )

    print("\n== nodes keep $key under 'all' ==")
    for node in client.nodes.list(fields=["all"]):
        try:
            check(f"node {node.get('name')}: .key works under all", node.key > 0, f"key={node.key}")
        except Exception as exc:  # noqa: BLE001
            check(f"node {node.get('name')}: .key works under all", False, repr(exc))

    print("\n== a narrowed projection is reported, not guessed ==")
    net_name = next(iter(truth))
    narrow = client.networks.get(name=net_name, fields=["$key", "name"])
    try:
        _ = narrow.is_running
        check("narrow projection raises rather than answering False", False, "returned a value")
    except FieldNotProjectedError as exc:
        check("narrow projection raises rather than answering False", True, f"{exc.field}")
    check(
        "narrowing is still honoured (not silently widened)",
        set(dict(narrow)) == {"$key", "name"},
        str(sorted(dict(narrow))),
    )

    print("\n== absence means unprojected, never 'no value' ==")
    # The whole design rests on this: the API returns a key for every field it
    # was asked for, using null when there is nothing to report.
    for label, mgr in managers:
        defaults = getattr(mgr, "_default_fields", None)
        aliases = alias_names(list(defaults or []))
        if not aliases:
            continue
        rows = [dict(r) for r in mgr.list()]
        absent = {a: sum(1 for r in rows if a not in r) for a in aliases}
        bad = {a: n for a, n in absent.items() if n}
        nulls = sum(1 for r in rows for a in aliases if r.get(a) is None)
        check(
            f"{label}: every requested alias comes back ({len(aliases)} aliases, {nulls} null)",
            not bad,
            str(bad),
        )

    print("\n== issue #117 reproducer, verbatim ==")
    name = running[0]
    try:
        assert client.networks.get(name=name).is_running is True
        assert client.networks.get(name=name, fields=["all"]).is_running is True
        check("reproducer: is_running under all", True)
    except AssertionError:
        check("reproducer: is_running under all", False)
    d_def = dict(list(client.nodes.list())[0])
    d_all = dict(list(client.nodes.list(fields=["all"]))[0])
    check(
        "reproducer: set(default) <= set(all)",
        set(d_def) <= set(d_all),
        str(sorted(set(d_def) - set(d_all))),
    )

    failed = [r for r in results if not r[1]]
    print(f"\n{len(results) - len(failed)}/{len(results)} passed")
    if failed:
        print("FAILURES:")
        for label, _ok, detail in failed:
            print(f"  - {label}: {detail}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
