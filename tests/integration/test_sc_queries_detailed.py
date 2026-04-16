"""ServiceContainerQueryManager integration test.

Tests all 12 query types against running service containers on dev env.

Run: uv run python tests/integration/test_sc_queries_detailed.py
"""

from __future__ import annotations

import sys
import traceback

from pyvergeos import VergeClient
from pyvergeos.resources.queries import (
    QueryManager,
    ServiceContainerQueryManager,
)

HOST = "192.168.10.74"


def get_client() -> VergeClient:
    return VergeClient(host=HOST, username="admin", password="QueenBuda44", verify_ssl=False)


def find_service_containers(client: VergeClient) -> list[dict]:
    """Find running service containers."""
    response = client._request(
        "GET",
        "service_containers",
        params={
            "fields": "$key,name",
            "limit": 20,
        },
    )
    if response is None:
        return []
    if isinstance(response, dict):
        return [response]
    return response


def run() -> None:
    print("=" * 60)
    print("ServiceContainerQueryManager Integration Test")
    print(f"Host: {HOST}")
    print("=" * 60)

    client = get_client()
    print(f"Connected to {client.cloud_name} v{client.version}")

    tests = []

    # 1. Class structure
    print("\n=== 1. Class Structure ===")
    assert ServiceContainerQueryManager._endpoint == "service_container_queries"
    print(f"  _endpoint: {ServiceContainerQueryManager._endpoint}")
    assert ServiceContainerQueryManager._parent_field == "service_container"
    print(f"  _parent_field: {ServiceContainerQueryManager._parent_field}")
    assert issubclass(ServiceContainerQueryManager, QueryManager)
    print("  Inherits QueryManager: True")
    for m in ["ping", "dns", "traceroute"]:
        assert hasattr(ServiceContainerQueryManager, m)
        print(f"  Convenience {m}(): ✓")
    for m in ["list", "get", "create", "wait", "run"]:
        assert hasattr(ServiceContainerQueryManager, m)
        print(f"  Base {m}(): ✓")
    tests.append(("Class structure", "PASS"))

    # 2. Find service containers
    print("\n=== 2. Service Containers ===")
    scs = find_service_containers(client)
    if not scs:
        print("  ERROR: No running service containers found")
        tests.append(("Service container lookup", "FAIL"))
        sys.exit(1)

    for sc in scs:
        print(f"  key={sc.get('$key')} name={sc.get('name', '?')}")
    test_scs = [(int(sc["$key"]), sc["name"]) for sc in scs]
    print(f"  Found {len(test_scs)} running service containers")
    tests.append(("Service container lookup", "PASS"))

    # 3. Manager instantiation
    print("\n=== 3. Manager Instantiation ===")
    for sc_key, sc_name in test_scs:
        mgr = ServiceContainerQueryManager(client, parent_key=sc_key)
        assert isinstance(mgr, ServiceContainerQueryManager)
        assert mgr._parent_key == sc_key
        print(f'  SC "{sc_name}" (key={sc_key}): ✓')
    tests.append(("Manager instantiation", "PASS"))

    # 4. list()
    print("\n=== 4. list() ===")
    for sc_key, sc_name in test_scs:
        mgr = ServiceContainerQueryManager(client, parent_key=sc_key)
        queries = mgr.list()
        assert isinstance(queries, list)
        print(f'  SC "{sc_name}": {len(queries)} existing queries')
    tests.append(("list()", "PASS"))

    # 5. query_key handling
    print("\n=== 5. query_key / query_id ===")
    sc_key, sc_name = test_scs[0]
    mgr = ServiceContainerQueryManager(client, parent_key=sc_key)
    try:
        r = mgr.run("whatsmyip", timeout=30)
        print(f'  SC "{sc_name}": whatsmyip → status={r.status}')
        print(f"  query_key: {r.query_key} (len={len(r.query_key)})")
        assert isinstance(r.query_key, str) and len(r.query_key) == 40
        rf = mgr.get(r.query_key)
        print(f"  Re-fetched by key: status={rf.status}")
        rf2 = mgr.get(query_id=r.query_id)
        print(f"  Re-fetched by query_id: status={rf2.status}")
        if r.result:
            print(f"  Result: {r.result.strip()}")
        tests.append(("query_key handling", "PASS"))
    except Exception as e:
        print(f"  ERROR: {e}")
        traceback.print_exc()
        tests.append(("query_key handling", f"ERROR: {e}"))

    # 6. Convenience methods
    print("\n=== 6. Convenience Methods ===")
    sc_key, sc_name = test_scs[0]
    mgr = ServiceContainerQueryManager(client, parent_key=sc_key)
    conv_ok = True
    for name, fn in [
        ("ping", lambda: mgr.ping("127.0.0.1", timeout=30)),
        ("dns", lambda: mgr.dns("verge.io", timeout=30)),
        ("traceroute", lambda: mgr.traceroute("8.8.8.8", timeout=60)),
    ]:
        try:
            r = fn()
            preview = (r.result or "")[:120].replace("\n", " | ")
            print(f"  {name}: status={r.status}, type={r.query_type} | {preview}")
            assert r.query_type == name
        except Exception as e:
            print(f"  {name}: ERROR: {e}")
            conv_ok = False
    tests.append(("Convenience methods", "PASS" if conv_ok else "FAIL"))

    # 7. All 12 query types against BOTH service containers
    print("\n=== 7. All Query Types (per service container) ===")

    all_types = [
        ("logs", None),
        ("top", None),
        ("top_if", None),
        ("tcpdump", {"count": "3"}),
        ("ping", {"host": "127.0.0.1"}),
        ("dns", {"name": "verge.io"}),
        ("traceroute", {"host": "8.8.8.8"}),
        ("ip", None),
        ("arp", None),
        ("arp-scan", None),
        ("whatsmyip", None),
        # dhcp_release_renew skipped — would disrupt networking
        ("tcp_connect", {"host": "127.0.0.1", "port": "22"}),
    ]

    all_ok = True
    for sc_key, sc_name in test_scs:
        print(f'\n  --- SC: "{sc_name}" (key={sc_key}) ---')
        mgr = ServiceContainerQueryManager(client, parent_key=sc_key)
        sc_passed = 0
        sc_total = len(all_types)
        for qtype, params in all_types:
            try:
                r = mgr.run(qtype, params, timeout=45) if params else mgr.run(qtype, timeout=45)
                preview = (r.result or "")[:80].replace("\n", " | ")
                print(f"  ✓ {qtype:20s} {r.status:10s} {preview}")
                sc_passed += 1
            except Exception as e:
                print(f"  ✗ {qtype:20s} EXCEPTION  {str(e)[:80]}")
                all_ok = False
        print(f"  {sc_passed}/{sc_total} types executed")

    print("\n  (skipped dhcp_release_renew — would disrupt active networking)")
    tests.append(("All query types", "PASS" if all_ok else "FAIL"))

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    passed = sum(1 for _, s in tests if s == "PASS")
    failed = sum(1 for _, s in tests if s != "PASS")
    for name, status in tests:
        marker = "✓" if status == "PASS" else "✗"
        print(f"  {marker} {name}: {status}")
    print(f"\n  {passed} passed, {failed} failed out of {len(tests)}")
    print("=" * 60)

    client.disconnect()
    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    run()
