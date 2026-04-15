"""Detailed NodeQueryManager integration test against node1.

Tests all 30+ query types from the API schema.

Run: uv run python tests/integration/test_node_queries_detailed.py
"""

from __future__ import annotations

import sys
import traceback

from pyvergeos import VergeClient
from pyvergeos.resources.queries import NodeQueryManager, QueryManager

NODE_NAME = "node1"


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
    """Verify NodeQueryManager class attributes."""
    print(f"  _endpoint: {NodeQueryManager._endpoint}")
    assert NodeQueryManager._endpoint == "node_queries"
    print(f"  _parent_field: {NodeQueryManager._parent_field}")
    assert NodeQueryManager._parent_field == "node"
    print(f"  Inherits QueryManager: {issubclass(NodeQueryManager, QueryManager)}")
    assert issubclass(NodeQueryManager, QueryManager)

    # Convenience methods
    for m in ["ping", "dns", "traceroute", "tcpdump", "arp", "smartctl", "lsblk", "dmidecode"]:
        assert hasattr(NodeQueryManager, m), f"Missing method: {m}"
        print(f"  Method {m}(): ✓")

    # Base methods
    for m in ["list", "get", "create", "wait", "run"]:
        assert hasattr(NodeQueryManager, m)
        print(f"  Base method {m}(): ✓")

    return True


def test_node_lookup(client: VergeClient) -> tuple[bool, int]:
    """Find node1 and return its key."""
    node = client.nodes.get(name=NODE_NAME)
    print(f"  Found: name={node.name}, key={node.key}")
    print(f"  Status: {node.status}")
    return True, node.key


def test_nested_manager(client: VergeClient, node_key: int) -> bool:
    """Verify node.queries returns NodeQueryManager."""
    node = client.nodes.get(node_key)
    qm = node.queries
    print(f"  Type: {type(qm).__name__}")
    assert isinstance(qm, NodeQueryManager)
    print(f"  _parent_key: {qm._parent_key}")
    assert qm._parent_key == node_key
    return True


def test_list(client: VergeClient, node_key: int) -> bool:
    """Test list()."""
    node = client.nodes.get(node_key)
    queries = node.queries.list()
    print(f"  Returned {len(queries)} existing queries")
    for q in queries[:3]:
        print(f"    key={q.query_key}, type={q.query_type}, status={q.status}")
    return True


def run_query(
    client: VergeClient,
    node_key: int,
    query_type: str,
    params: dict | None = None,
    timeout: float = 30,
) -> tuple[str, str, str]:
    """Run a single query type and return (status, result_preview, error)."""
    node = client.nodes.get(node_key)
    try:
        if params:
            result = node.queries.run(query_type, params, timeout=timeout)
        else:
            result = node.queries.run(query_type, timeout=timeout)

        preview = ""
        if result.result:
            preview = result.result[:200].replace("\n", " | ")
        return result.status, preview, ""
    except Exception as e:
        return "EXCEPTION", "", str(e)


def test_convenience_ping(client: VergeClient, node_key: int) -> bool:
    """Test ping() convenience method."""
    node = client.nodes.get(node_key)
    result = node.queries.ping("127.0.0.1", timeout=30)
    print(f"  Status: {result.status}, type: {result.query_type}")
    assert result.query_type == "ping"
    if result.result:
        print(f"  Result: {result.result[:200]}")
    return True


def test_convenience_dns(client: VergeClient, node_key: int) -> bool:
    """Test dns() convenience method."""
    node = client.nodes.get(node_key)
    result = node.queries.dns("verge.io", timeout=30)
    print(f"  Status: {result.status}, type: {result.query_type}")
    assert result.query_type == "dns"
    if result.result:
        print(f"  Result: {result.result[:200]}")
    return True


def test_convenience_traceroute(client: VergeClient, node_key: int) -> bool:
    """Test traceroute() convenience method."""
    node = client.nodes.get(node_key)
    result = node.queries.traceroute("8.8.8.8", timeout=60)
    print(f"  Status: {result.status}, type: {result.query_type}")
    assert result.query_type == "traceroute"
    if result.result:
        print(f"  Result: {result.result[:300]}")
    return True


def test_convenience_arp(client: VergeClient, node_key: int) -> bool:
    """Test arp() convenience method."""
    node = client.nodes.get(node_key)
    result = node.queries.arp(timeout=30)
    print(f"  Status: {result.status}, type: {result.query_type}")
    assert result.query_type == "arp"
    if result.result:
        print(f"  Result: {result.result[:300]}")
    return True


def test_convenience_smartctl(client: VergeClient, node_key: int) -> bool:
    """Test smartctl() convenience method."""
    node = client.nodes.get(node_key)
    # Use first nvme device which should exist on the dev env
    result = node.queries.smartctl("/dev/nvme0", timeout=30)
    print(f"  Status: {result.status}, type: {result.query_type}")
    assert result.query_type == "smartctl"
    if result.result:
        print(f"  Result: {result.result[:300]}")
    return True


def test_convenience_lsblk(client: VergeClient, node_key: int) -> bool:
    """Test lsblk() convenience method."""
    node = client.nodes.get(node_key)
    result = node.queries.lsblk(timeout=30)
    print(f"  Status: {result.status}, type: {result.query_type}")
    assert result.query_type == "lsblk"
    if result.result:
        print(f"  Result: {result.result[:300]}")
    return True


def test_convenience_dmidecode(client: VergeClient, node_key: int) -> bool:
    """Test dmidecode() convenience method."""
    node = client.nodes.get(node_key)
    result = node.queries.dmidecode(timeout=30)
    print(f"  Status: {result.status}, type: {result.query_type}")
    assert result.query_type == "dmidecode"
    if result.result:
        print(f"  Result: {result.result[:300]}")
    return True


def test_all_query_types(client: VergeClient, node_key: int) -> bool:
    """Test all 30+ query types via raw run()."""
    # All query types from the API schema
    all_types = [
        ("logs", None),
        ("top", None),
        ("top_if", None),
        ("tcpdump", {"count": "3"}),
        ("ping", {"host": "127.0.0.1"}),
        ("dns", {"name": "verge.io"}),
        ("traceroute", {"host": "8.8.8.8"}),
        ("ip", None),
        ("bridge", None),
        ("whatsmyip", None),
        ("ipmi-sel", None),
        ("ipmi-sensor", None),
        ("ipmi-fru", None),
        ("ipmi-lan", None),
        ("ipmi-chassis", None),
        ("ipmi-bmc", None),
        ("ipmi-sdr", None),
        # ("ipmi-reset", None),  # Skip — destructive action
        ("dmidecode", None),
        ("lsblk", None),
        ("arp", None),
        ("arp-scan", None),
        ("smartctl", {"device": "/dev/nvme0"}),
        # ("smartctl-test", ...),  # Skip — long-running test
        # ("ledctl", None),  # Skip — hardware-dependent
        ("openssl-speed", None),
        ("tcp_connect", {"host": "127.0.0.1", "port": "22"}),
        ("eth-tool", None),
        ("fabric", None),
        # ("clear-pstore", None),  # Skip — destructive
        ("ras-mc-ctl", None),
        ("bonding", None),
    ]

    passed = 0
    failed = 0
    results_table = []

    for qtype, params in all_types:
        status, preview, error = run_query(client, node_key, qtype, params, timeout=45)
        marker = "✓" if status in ("complete", "error") else "✗"
        if status == "EXCEPTION":
            marker = "✗"
            results_table.append((qtype, "EXCEPTION", error[:80]))
            failed += 1
        else:
            results_table.append((qtype, status, preview[:80] if preview else "(empty)"))
            passed += 1

        print(
            f"  {marker} {qtype:20s} status={status:10s} {preview[:60] if preview else error[:60] if error else ''}"
        )

    print(f"\n  Summary: {passed} completed, {failed} exceptions out of {len(all_types)}")
    return failed == 0


def test_query_key_handling(client: VergeClient, node_key: int) -> bool:
    """Verify SHA1 string key handling."""
    node = client.nodes.get(node_key)
    result = node.queries.run("whatsmyip", timeout=30)

    qk = result.query_key
    qi = result.query_id
    print(f"  query_key: {qk} (type: {type(qk).__name__}, len: {len(qk)})")
    print(f"  query_id:  {qi}")
    print(f"  Match: {qk == qi}")
    assert isinstance(qk, str)
    assert len(qk) == 40  # SHA1 hex

    # Re-fetch by key
    refetched = node.queries.get(qk)
    print(f"  Re-fetched: status={refetched.status}")
    assert refetched.query_type == "whatsmyip"

    # Re-fetch by query_id
    refetched2 = node.queries.get(query_id=qi)
    print(f"  Re-fetched by query_id: status={refetched2.status}")
    return True


def run() -> None:
    print("=" * 60)
    print("NodeQueryManager Detailed Integration Test")
    print(f"Node: {NODE_NAME}")
    print("=" * 60)

    client = get_client()
    print(f"Connected to {client.cloud_name} v{client.version}")

    tests = []
    node_key = 0

    # 1. Class structure
    section("1. Class Structure")
    try:
        ok = test_class_structure()
        tests.append(("Class structure", "PASS" if ok else "FAIL"))
    except Exception as e:
        tests.append(("Class structure", f"ERROR: {e}"))
        traceback.print_exc()

    # 2. Node lookup
    section("2. Node Lookup")
    try:
        ok, node_key = test_node_lookup(client)
        tests.append(("Node lookup", "PASS" if ok else "FAIL"))
    except Exception as e:
        tests.append(("Node lookup", f"ERROR: {e}"))
        traceback.print_exc()
        print("\nCANNOT CONTINUE. Aborting.")
        client.disconnect()
        sys.exit(1)

    # 3. Nested manager
    section("3. Nested Manager (node.queries)")
    try:
        ok = test_nested_manager(client, node_key)
        tests.append(("Nested manager", "PASS" if ok else "FAIL"))
    except Exception as e:
        tests.append(("Nested manager", f"ERROR: {e}"))
        traceback.print_exc()

    # 4. list()
    section("4. list()")
    try:
        ok = test_list(client, node_key)
        tests.append(("list()", "PASS" if ok else "FAIL"))
    except Exception as e:
        tests.append(("list()", f"ERROR: {e}"))
        traceback.print_exc()

    # 5. SHA1 key handling
    section("5. query_key / query_id Handling")
    try:
        ok = test_query_key_handling(client, node_key)
        tests.append(("query_key handling", "PASS" if ok else "FAIL"))
    except Exception as e:
        tests.append(("query_key handling", f"ERROR: {e}"))
        traceback.print_exc()

    # 6. Convenience methods
    convenience = [
        ("6a. ping()", test_convenience_ping),
        ("6b. dns()", test_convenience_dns),
        ("6c. traceroute()", test_convenience_traceroute),
        ("6d. arp()", test_convenience_arp),
        ("6e. smartctl()", test_convenience_smartctl),
        ("6f. lsblk()", test_convenience_lsblk),
        ("6g. dmidecode()", test_convenience_dmidecode),
    ]

    for name, fn in convenience:
        section(name)
        try:
            ok = fn(client, node_key)
            tests.append((name, "PASS" if ok else "FAIL"))
        except Exception as e:
            tests.append((name, f"ERROR: {e}"))
            traceback.print_exc()

    # 7. All 30+ query types
    section("7. All Query Types (30+)")
    try:
        ok = test_all_query_types(client, node_key)
        tests.append(("All query types", "PASS" if ok else "FAIL"))
    except Exception as e:
        tests.append(("All query types", f"ERROR: {e}"))
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
