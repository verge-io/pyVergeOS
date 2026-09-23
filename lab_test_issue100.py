"""Lab verification for issue #100 - quote_value() must escape '{'.

The dangerous case is silent: a balanced {...} is consumed by the filter
grammar, so a lookup-by-name returns a DIFFERENT object and the caller can
then modify or delete something it never asked for.

Creates and destroys its own scratch VMs and networks. Never touches Core/DMZ.

Usage:  .venv/bin/python lab_test_issue100.py [round-label]
        SKIP_FIX_GUARD=1 ... to run deliberately against a pre-fix tree
"""

from __future__ import annotations

import os
import sys
import uuid

from pyvergeos import VergeClient
from pyvergeos.exceptions import APIError
from pyvergeos.filters import build_filter, quote_value, wildcard_condition

LABEL = sys.argv[1] if len(sys.argv) > 1 else "r1"
TAG = uuid.uuid4().hex[:6]
PREFIX = f"zzb{TAG}"

results: list[tuple[str, bool, str]] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    results.append((label, ok, detail))
    print(f"  [{'PASS' if ok else 'FAIL'}] {label}{': ' + detail if detail else ''}")


def _assert_fix_loaded() -> None:
    """Refuse to run against a tree that does not contain the fix.

    Lost time twice to this: sys.path[0] is the *script's* directory, so a
    PYTHONPATH override is silently ignored when the script sits next to the
    package, and a stray branch switch can swap the tree underneath a run.
    A suite that passes against the wrong code is worse than no suite.
    """
    import pyvergeos

    print(f"SDK under test: {pyvergeos.__file__}")
    got = quote_value("a{x}")
    if os.environ.get("SKIP_FIX_GUARD"):
        print(f"  (guard skipped; quote_value('a{{x}}') = {got!r})")
        return
    if got != r"'a\{x}'":
        raise SystemExit(
            f"REFUSING TO RUN: quote_value('a{{x}}') = {got!r}\n"
            "This tree does not contain the #100 fix. Set SKIP_FIX_GUARD=1 "
            "to run it anyway (e.g. as a deliberate pre-fix control)."
        )


def main() -> int:
    _assert_fix_loaded()
    client = VergeClient.from_env()
    vms: list = []
    nets: list = []

    def mkvm(suffix: str):
        vm = client.vms.create(name=f"{PREFIX}{suffix}", cpu_cores=1, ram=512,
                               os_family="linux")
        vms.append(vm)
        return vm

    try:
        # ===========================================================
        print("\n=== A. the silent wrong-row case (the core of #100) ===")
        braced = mkvm("-br{x}ace")
        decoy = mkvm("-brace")
        stored = dict(client.vms.get(braced.key))["name"]
        check("A0 name stored verbatim (not a write-path issue)",
              stored == f"{PREFIX}-br{{x}}ace", stored)

        found = client.vms.get(name=f"{PREFIX}-br{{x}}ace")
        check("A1 lookup by braced name returns the RIGHT row",
              str(found.key) == str(braced.key),
              f"got key={found.key} name={dict(found)['name']!r}, want key={braced.key}")
        check("A2 lookup did NOT return the decoy",
              str(found.key) != str(decoy.key), f"decoy key={decoy.key}")

        found_decoy = client.vms.get(name=f"{PREFIX}-brace")
        check("A3 decoy still resolves to itself",
              str(found_decoy.key) == str(decoy.key), f"got {found_decoy.key}")

        # ===========================================================
        print("\n=== B. unbalanced brace (previously HTTP 422) ===")
        lead = mkvm("-{lead")
        try:
            got = client.vms.get(name=f"{PREFIX}-{{lead")
            check("B1 unbalanced '{' lookup succeeds",
                  str(got.key) == str(lead.key), f"got {got.key} want {lead.key}")
        except APIError as exc:
            check("B1 unbalanced '{' lookup succeeds", False, str(exc)[:110])

        # ===========================================================
        print("\n=== C. '}' is not reserved; regression on ' and \\ ===")
        cases = [
            ("-trail}", "closing brace"),
            ("-o'brien", "apostrophe (#72)"),
            ("-back\\slash", "backslash (#72)"),
            ("-mix'{a}b", "apostrophe + brace together"),
            ("-dbl{{x}}", "doubled braces"),
            ("-{}", "empty braces"),
            ("-a{b{c}d}e", "nested braces"),
            ("-q{2,3}z", "brace that looks like an ERE quantifier"),
        ]
        for suffix, desc in cases:
            vm = mkvm(suffix)
            want = f"{PREFIX}{suffix}"
            try:
                got = client.vms.get(name=want)
                ok = str(got.key) == str(vm.key)
                detail = "" if ok else f"got {dict(got)['name']!r}"
            except APIError as exc:
                ok, detail = False, str(exc)[:90]
            check(f"C {desc}: {want!r}", ok, detail)

        # ===========================================================
        print("\n=== D. every operator, not just eq ===")
        target = mkvm("-ops{z}end")
        name = f"{PREFIX}-ops{{z}}end"
        op_cases = [
            ("eq", quote_value(name), name),
            ("bw", quote_value(f"{PREFIX}-ops{{z}}"), "prefix"),
            ("ew", quote_value("ops{z}end"), "suffix"),
            ("cs", quote_value("ops{z}en"), "contains cs"),
            ("ct", quote_value("OPS{Z}EN"), "contains ct (case-insensitive)"),
        ]
        for op, lit, desc in op_cases:
            try:
                rows = client._request("GET", "vms",
                                       params={"filter": f"name {op} {lit}",
                                               "fields": "$key,name", "limit": "10"})
                rows = rows if isinstance(rows, list) else ([rows] if rows else [])
                keys = [str(r.get("$key")) for r in rows]
                ok = str(target.key) in keys
                detail = "" if ok else f"{len(rows)} rows, keys={keys}"
            except APIError as exc:
                ok, detail = False, str(exc)[:90]
            check(f"D {op} matches a braced value ({desc})", ok, detail)

        # ===========================================================
        print("\n=== E. rx path: wildcard patterns containing braces ===")
        rx_target = mkvm("-rx{q}tail")
        rx_cases = [
            (f"{PREFIX}-rx{{q}}*l", "interior * -> rx"),
            (f"{PREFIX}-rx{{q}}tai?", "? -> rx"),
            (f"{PREFIX}-rx{{q}}*", "trailing * -> bw"),
            ("*rx{q}tail", "leading * -> ew"),
            ("*rx{q}*", "both -> cs"),
        ]
        for pattern, desc in rx_cases:
            cond = wildcard_condition("name", pattern)
            try:
                rows = client._request("GET", "vms",
                                       params={"filter": cond, "fields": "$key,name",
                                               "limit": "10"})
                rows = rows if isinstance(rows, list) else ([rows] if rows else [])
                keys = [str(r.get("$key")) for r in rows]
                ok = str(rx_target.key) in keys
                detail = "" if ok else f"cond={cond} keys={keys}"
            except APIError as exc:
                ok, detail = False, f"cond={cond} {str(exc)[:70]}"
            check(f"E {desc}", ok, detail)

        # ===========================================================
        print("\n=== F. build_filter kwargs shorthand ===")
        f_target = mkvm("-kw{k}arg")
        f_name = f"{PREFIX}-kw{{k}}arg"
        flt = build_filter(name=f_name)
        try:
            rows = client._request("GET", "vms",
                                   params={"filter": flt, "fields": "$key,name", "limit": "10"})
            rows = rows if isinstance(rows, list) else ([rows] if rows else [])
            ok = [str(r.get("$key")) for r in rows] == [str(f_target.key)]
            detail = "" if ok else f"filter={flt} rows={rows}"
        except APIError as exc:
            ok, detail = False, f"filter={flt} {str(exc)[:70]}"
        check("F1 build_filter(name=...) with braces", ok, detail)

        vm_list = client.vms.list(name=f_name)
        check("F2 manager list(name=...) with braces",
              [str(v.key) for v in vm_list] == [str(f_target.key)],
              f"{[dict(v).get('name') for v in vm_list]}")

        # ===========================================================
        print("\n=== G. a second table (networks) ===")
        nb = client.networks.create(name=f"{PREFIX}-n{{x}}et", network_type="internal",
                                    network_address="10.242.10.0/24",
                                    ip_address="10.242.10.1")
        nets.append(nb)
        nd = client.networks.create(name=f"{PREFIX}-net", network_type="internal",
                                    network_address="10.242.11.0/24",
                                    ip_address="10.242.11.1")
        nets.append(nd)
        try:
            gotn = client.networks.get(name=f"{PREFIX}-n{{x}}et")
            ok = str(gotn.key) == str(nb.key)
            detail = "" if ok else f"got {dict(gotn)['name']!r} (decoy={nd.key})"
        except APIError as exc:
            ok, detail = False, str(exc)[:90]
        check("G1 networks lookup by braced name", ok, detail)

        # ===========================================================
        print("\n=== H. the destructive scenario from the issue ===")
        victim = mkvm("-del{x}me")
        bystander = mkvm("-delme")
        target_vm = client.vms.get(name=f"{PREFIX}-del{{x}}me")
        check("H1 resolved the intended victim",
              str(target_vm.key) == str(victim.key),
              f"resolved {dict(target_vm)['name']!r}")
        target_vm.delete()
        vms.remove(victim)
        still = client.vms.list(name=f"{PREFIX}-delme")
        check("H2 the bystander still exists after the delete",
              len(still) == 1 and str(still[0].key) == str(bystander.key),
              f"found {[dict(v).get('name') for v in still]}")
        gone = client.vms.list(name=f"{PREFIX}-del{{x}}me")
        check("H3 the intended victim is gone", gone == [], f"{len(gone)} rows")

        # ===========================================================
        print("\n=== I. user-supplied ERE quantifier still works ===")
        # Filter.rx() passes a raw regex through quote_value. Escaping '{' must
        # PRESERVE a quantifier: the literal grammar unescapes \{ back to '{'
        # before the regex engine sees it.
        from pyvergeos.filters import Filter

        for suffix in ["-qa b", "-qaab", "-qaaab", "-qaaaab"]:
            mkvm(suffix.replace(" ", ""))
        qflt = str(Filter().rx("name", f"^{PREFIX}-qa{{2,3}}b$"))
        try:
            rows = client._request("GET", "vms", params={"filter": qflt,
                                                         "fields": "$key,name", "limit": "20"})
            rows = rows if isinstance(rows, list) else []
            got_names = sorted(str(r.get("name")) for r in rows)
        except APIError as exc:
            got_names = f"APIError: {str(exc)[:70]}"
        want_names = sorted([f"{PREFIX}-qaab", f"{PREFIX}-qaaab"])
        check("I1 ERE quantifier {2,3} still behaves as a quantifier",
              got_names == want_names, f"filter={qflt} got={got_names} want={want_names}")

    finally:
        print("\n=== Cleanup ===")
        for vm in vms:
            try:
                vm.delete()
            except Exception as exc:  # noqa: BLE001
                print(f"  vm {vm.key} cleanup failed: {str(exc)[:80]}")
        for net in nets:
            try:
                net.delete()
            except Exception as exc:  # noqa: BLE001
                print(f"  net {net.key} cleanup failed: {str(exc)[:80]}")
        leftovers = [v for v in client.vms.list()
                     if str(dict(v).get("name", "")).startswith(PREFIX)]
        leftovers += [n for n in client.networks.list()
                      if str(dict(n).get("name", "")).startswith(PREFIX)]
        print(f"  leftover scratch objects: {[dict(o).get('name') for o in leftovers] or 'none'}")

    failed = [r for r in results if not r[1]]
    print(f"\n{'=' * 60}\n{len(results) - len(failed)}/{len(results)} checks passed ({LABEL})")
    for label, _, detail in failed:
        print(f"  FAIL {label}: {detail}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
