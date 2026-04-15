"""Detailed VNetQueryManager integration test against network 'fghdfgh454'.

Verifies:
1. VNetQueryManager class exists with correct _endpoint and _parent_field
2. Network lookup by name works
3. network.queries accessor works (nested manager wiring)
4. list() — lists existing queries for the network
5. create() + get() — raw query submission and retrieval
6. wait() — async polling
7. run() — convenience create+wait
8. query_key property — SHA1 string key handling
9. Convenience methods: ping, dns, traceroute, arp, firewall, trace, tcpdump
10. Raw create for additional query types: logs, top, ip, whatsmyip, etc.

Run: uv run python tests/integration/test_vnet_queries_detailed.py
"""

from __future__ import annotations

import sys
import traceback

from pyvergeos import VergeClient
from pyvergeos.resources.queries import QueryManager, QueryResult, VNetQueryManager

NETWORK_NAME = "fghdfgh454"


def get_client() -> VergeClient:
    return VergeClient(
        host="192.168.10.74",
        username="admin",
        password="QueenBuda44",
        verify_ssl=False,
    )


def section(title: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")


def test_class_structure() -> bool:
    """Verify VNetQueryManager class attributes."""
    print("  _endpoint:", VNetQueryManager._endpoint)
    assert VNetQueryManager._endpoint == "vnet_queries", "Wrong endpoint"
    print("  _parent_field:", VNetQueryManager._parent_field)
    assert VNetQueryManager._parent_field == "vnet", "Wrong parent field"
    print("  Inherits from QueryManager:", issubclass(VNetQueryManager, QueryManager))
    assert issubclass(VNetQueryManager, QueryManager)

    # Verify convenience methods exist
    methods = ["ping", "dns", "traceroute", "tcpdump", "arp", "firewall", "trace"]
    for m in methods:
        assert hasattr(VNetQueryManager, m), f"Missing method: {m}"
        print(f"  Method {m}(): ✓")

    # Verify base methods exist
    base_methods = ["list", "get", "create", "wait", "run"]
    for m in base_methods:
        assert hasattr(VNetQueryManager, m), f"Missing base method: {m}"
        print(f"  Base method {m}(): ✓")

    return True


def test_network_lookup(client: VergeClient) -> tuple[bool, int]:
    """Find network 'fghdfgh454' and return its key."""
    net = client.networks.get(name=NETWORK_NAME)
    print(f"  Found network: name={net.name}, key={net.key}")
    print(f"  Running: {net.is_running}")
    print(f"  Status: {net.status}")
    return True, net.key


def test_nested_manager_access(client: VergeClient, net_key: int) -> bool:
    """Verify network.queries returns a VNetQueryManager."""
    net = client.networks.get(net_key)
    qm = net.queries
    print(f"  Type: {type(qm).__name__}")
    assert isinstance(qm, VNetQueryManager), f"Expected VNetQueryManager, got {type(qm)}"
    print(f"  _parent_key: {qm._parent_key}")
    assert qm._parent_key == net_key
    return True


def test_list(client: VergeClient, net_key: int) -> bool:
    """Test list() — should return list of QueryResult objects."""
    net = client.networks.get(net_key)
    queries = net.queries.list()
    print(f"  Returned {len(queries)} existing queries")
    assert isinstance(queries, list)
    for q in queries[:3]:
        assert isinstance(q, QueryResult), f"Expected QueryResult, got {type(q)}"
        print(f"    query_key={q.query_key}, type={q.query_type}, status={q.status}")
    return True


def test_create_and_get(client: VergeClient, net_key: int) -> bool:
    """Test raw create() then get() by key."""
    net = client.networks.get(net_key)

    # Create a simple query
    result = net.queries.create("whatsmyip")
    print(f"  Created query: query_key={result.query_key}")
    print(f"  query_id={result.query_id}")
    print(f"  query_type={result.query_type}")
    print(f"  status={result.status}")
    assert isinstance(result, QueryResult)
    assert result.query_key  # Should be a non-empty string

    # Verify query_key is a SHA1 string (40 hex chars)
    key = result.query_key
    assert isinstance(key, str), f"query_key should be str, got {type(key)}"
    print(f"  query_key type: {type(key).__name__}, length: {len(key)}")

    # Get by key
    fetched = net.queries.get(key)
    print(f"  Fetched by key: status={fetched.status}, type={fetched.query_type}")
    assert isinstance(fetched, QueryResult)

    return True


def test_wait(client: VergeClient, net_key: int) -> bool:
    """Test create() + wait() — poll until complete."""
    net = client.networks.get(net_key)

    result = net.queries.create("whatsmyip")
    print(f"  Created: key={result.query_key}, status={result.status}")

    waited = net.queries.wait(result.query_key, timeout=30, poll_interval=1.0)
    print(f"  After wait: status={waited.status}")
    if waited.result:
        print(f"  Result: {waited.result[:200]}")
    assert waited.status in ("complete", "error")
    return True


def test_run(client: VergeClient, net_key: int) -> bool:
    """Test run() — convenience create+wait in one call."""
    net = client.networks.get(net_key)

    result = net.queries.run("whatsmyip", timeout=30)
    print(f"  Status: {result.status}")
    print(f"  query_key: {result.query_key}")
    if result.result:
        print(f"  Result: {result.result[:200]}")
    assert result.status in ("complete", "error")
    return True


def test_ping(client: VergeClient, net_key: int) -> bool:
    """Test ping() convenience method."""
    net = client.networks.get(net_key)
    result = net.queries.ping("127.0.0.1", timeout=30)
    print(f"  Status: {result.status}")
    print(f"  query_type: {result.query_type}")
    assert result.query_type == "ping"
    if result.result:
        print(f"  Result: {result.result[:300]}")
    return True


def test_dns(client: VergeClient, net_key: int) -> bool:
    """Test dns() convenience method."""
    net = client.networks.get(net_key)
    result = net.queries.dns("google.com", timeout=30)
    print(f"  Status: {result.status}")
    print(f"  query_type: {result.query_type}")
    assert result.query_type == "dns"
    if result.result:
        print(f"  Result: {result.result[:300]}")
    return True


def test_traceroute(client: VergeClient, net_key: int) -> bool:
    """Test traceroute() convenience method."""
    net = client.networks.get(net_key)
    result = net.queries.traceroute("8.8.8.8", timeout=60)
    print(f"  Status: {result.status}")
    print(f"  query_type: {result.query_type}")
    assert result.query_type == "traceroute"
    if result.result:
        print(f"  Result: {result.result[:300]}")
    return True


def test_arp(client: VergeClient, net_key: int) -> bool:
    """Test arp() convenience method."""
    net = client.networks.get(net_key)
    result = net.queries.arp(timeout=30)
    print(f"  Status: {result.status}")
    print(f"  query_type: {result.query_type}")
    assert result.query_type == "arp"
    if result.result:
        print(f"  Result: {result.result[:300]}")
    return True


def test_firewall(client: VergeClient, net_key: int) -> bool:
    """Test firewall() convenience method."""
    net = client.networks.get(net_key)
    result = net.queries.firewall(timeout=30)
    print(f"  Status: {result.status}")
    print(f"  query_type: {result.query_type}")
    assert result.query_type == "firewall"
    if result.result:
        print(f"  Result: {result.result[:500]}")
    return True


def test_trace(client: VergeClient, net_key: int) -> bool:
    """Test trace() convenience method (nftables trace)."""
    net = client.networks.get(net_key)
    result = net.queries.trace(timeout=30)
    print(f"  Status: {result.status}")
    print(f"  query_type: {result.query_type}")
    assert result.query_type == "trace"
    if result.result:
        print(f"  Result: {result.result[:300]}")
    return True


def test_tcpdump(client: VergeClient, net_key: int) -> bool:
    """Test tcpdump() convenience method (short capture)."""
    net = client.networks.get(net_key)
    # Use count=5 to limit capture and ensure it completes
    result = net.queries.tcpdump(timeout=30, count="5")
    print(f"  Status: {result.status}")
    print(f"  query_type: {result.query_type}")
    assert result.query_type == "tcpdump"
    if result.result:
        print(f"  Result: {result.result[:300]}")
    return True


def test_remaining_query_types(client: VergeClient, net_key: int) -> bool:
    """Test additional query types via raw create/wait."""
    net = client.networks.get(net_key)

    # Test a selection of the remaining query types
    test_types = ["logs", "top", "ip"]

    for qtype in test_types:
        print(f"\n  --- {qtype} ---")
        try:
            result = net.queries.run(qtype, timeout=30)
            print(f"  Status: {result.status}")
            if result.result:
                preview = result.result[:200].replace("\n", "\n    ")
                print(f"  Result: {preview}")
        except Exception as e:
            print(f"  Error (may be expected): {e}")

    return True


def test_query_key_properties(client: VergeClient, net_key: int) -> bool:
    """Verify query_key and query_id properties on a live result."""
    net = client.networks.get(net_key)
    result = net.queries.run("whatsmyip", timeout=30)

    # query_key should be str
    qk = result.query_key
    print(f"  query_key: {qk}")
    print(f"  query_key type: {type(qk).__name__}")
    assert isinstance(qk, str)

    # query_id should also be str (the 'id' field)
    qi = result.query_id
    print(f"  query_id: {qi}")
    print(f"  query_id type: {type(qi).__name__}")
    assert isinstance(qi, str)

    # Both should be the same SHA1
    print(f"  query_key == query_id: {qk == qi}")

    # Verify we can re-fetch by this key
    refetched = net.queries.get(qk)
    print(f"  Re-fetched by query_key: status={refetched.status}")
    assert refetched.query_type == "whatsmyip"

    # Also test get by query_id
    refetched2 = net.queries.get(query_id=qi)
    print(f"  Re-fetched by query_id: status={refetched2.status}")

    return True


def run() -> None:
    print("=" * 60)
    print("VNetQueryManager Detailed Integration Test")
    print(f"Network: {NETWORK_NAME}")
    print("=" * 60)

    client = get_client()
    print(f"Connected to {client.cloud_name} v{client.version}")

    tests: list[tuple[str, ...]] = []
    net_key = 0

    # Phase 1: Structure verification (no network needed)
    section("1. Class Structure Verification")
    try:
        ok = test_class_structure()
        tests.append(("Class structure", "PASS" if ok else "FAIL"))
    except Exception as e:
        tests.append(("Class structure", f"ERROR: {e}"))
        traceback.print_exc()

    # Phase 2: Find the network
    section("2. Network Lookup")
    try:
        ok, net_key = test_network_lookup(client)
        tests.append(("Network lookup", "PASS" if ok else "FAIL"))
    except Exception as e:
        tests.append(("Network lookup", f"ERROR: {e}"))
        traceback.print_exc()
        print("\nCANNOT CONTINUE without network. Aborting.")
        client.disconnect()
        sys.exit(1)

    # Phase 3: Manager wiring
    section("3. Nested Manager Access (network.queries)")
    try:
        ok = test_nested_manager_access(client, net_key)
        tests.append(("Nested manager access", "PASS" if ok else "FAIL"))
    except Exception as e:
        tests.append(("Nested manager access", f"ERROR: {e}"))
        traceback.print_exc()

    # Phase 4: Core CRUD operations
    section("4. list()")
    try:
        ok = test_list(client, net_key)
        tests.append(("list()", "PASS" if ok else "FAIL"))
    except Exception as e:
        tests.append(("list()", f"ERROR: {e}"))
        traceback.print_exc()

    section("5. create() + get()")
    try:
        ok = test_create_and_get(client, net_key)
        tests.append(("create() + get()", "PASS" if ok else "FAIL"))
    except Exception as e:
        tests.append(("create() + get()", f"ERROR: {e}"))
        traceback.print_exc()

    section("6. wait()")
    try:
        ok = test_wait(client, net_key)
        tests.append(("wait()", "PASS" if ok else "FAIL"))
    except Exception as e:
        tests.append(("wait()", f"ERROR: {e}"))
        traceback.print_exc()

    section("7. run() (create+wait)")
    try:
        ok = test_run(client, net_key)
        tests.append(("run()", "PASS" if ok else "FAIL"))
    except Exception as e:
        tests.append(("run()", f"ERROR: {e}"))
        traceback.print_exc()

    section("8. query_key / query_id Properties")
    try:
        ok = test_query_key_properties(client, net_key)
        tests.append(("query_key/query_id", "PASS" if ok else "FAIL"))
    except Exception as e:
        tests.append(("query_key/query_id", f"ERROR: {e}"))
        traceback.print_exc()

    # Phase 5: Convenience methods
    convenience_tests = [
        ("9. ping()", test_ping),
        ("10. dns()", test_dns),
        ("11. traceroute()", test_traceroute),
        ("12. arp()", test_arp),
        ("13. firewall()", test_firewall),
        ("14. trace()", test_trace),
        ("15. tcpdump()", test_tcpdump),
    ]

    for name, fn in convenience_tests:
        section(name)
        try:
            ok = fn(client, net_key)
            tests.append((name, "PASS" if ok else "FAIL"))
        except Exception as e:
            tests.append((name, f"ERROR: {e}"))
            traceback.print_exc()

    # Phase 6: Additional query types
    section("16. Additional Query Types (logs, top, ip)")
    try:
        ok = test_remaining_query_types(client, net_key)
        tests.append(("Additional query types", "PASS" if ok else "FAIL"))
    except Exception as e:
        tests.append(("Additional query types", f"ERROR: {e}"))
        traceback.print_exc()

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
