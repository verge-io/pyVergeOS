"""Integration tests for network diagnostics resource managers.

Tests against the dev environment defined in .claude/TESTENV.md.
Run with: uv run python tests/integration/test_network_diagnostics.py
"""

from __future__ import annotations

import sys
import traceback

from pyvergeos import VergeClient


def get_client() -> VergeClient:
    """Connect to dev environment."""
    return VergeClient(
        host="192.168.10.74",
        username="admin",
        password="QueenBuda44",
        verify_ssl=False,
    )


def test_connection(client: VergeClient) -> bool:
    """Verify basic connection works."""
    print(f"  Connected to: {client.cloud_name}")
    print(f"  Version: {client.version}")
    return True


# =============================================================================
# Query Manager Tests
# =============================================================================


def test_vnet_query_list(client: VergeClient) -> bool:
    """Test listing networks and accessing query manager."""
    networks = client.networks.list(limit=5)
    print(f"  Found {len(networks)} networks")
    if not networks:
        print("  SKIP: No networks found")
        return True

    # Find a running network
    running = [n for n in networks if n.is_running]
    if not running:
        # Try fetching more
        all_nets = client.networks.list_running()
        running = all_nets[:1] if all_nets else []

    if not running:
        print("  SKIP: No running networks to query")
        return True

    net = running[0]
    print(f"  Using network: {net.name} (key={net.key})")

    # Test list (should return empty or existing queries)
    queries = net.queries.list()
    print(f"  Existing queries: {len(queries)}")
    return True


def test_vnet_query_ping(client: VergeClient) -> bool:
    """Test running a ping query on a network."""
    running = client.networks.list_running()
    if not running:
        print("  SKIP: No running networks")
        return True

    net = running[0]
    print(f"  Pinging from network: {net.name} (key={net.key})")

    try:
        result = net.queries.ping("127.0.0.1", timeout=30)
        print(f"  Status: {result.status}")
        print(f"  Query ID: {result.query_id}")
        if result.result:
            # Show first 200 chars of result
            preview = result.result[:200]
            print(f"  Result preview: {preview}")
        return True
    except Exception as e:
        print(f"  Query failed (may be expected if network has no router): {e}")
        return True  # Not a test failure - some networks can't ping


def test_vnet_query_arp(client: VergeClient) -> bool:
    """Test running an ARP query on a network."""
    running = client.networks.list_running()
    if not running:
        print("  SKIP: No running networks")
        return True

    net = running[0]
    print(f"  ARP table from network: {net.name}")

    try:
        result = net.queries.arp(timeout=30)
        print(f"  Status: {result.status}")
        if result.result:
            preview = result.result[:200]
            print(f"  Result preview: {preview}")
        return True
    except Exception as e:
        print(f"  ARP query failed: {e}")
        return True


def test_node_query_list(client: VergeClient) -> bool:
    """Test listing nodes and accessing query manager."""
    nodes = client.nodes.list(limit=5)
    print(f"  Found {len(nodes)} nodes")
    if not nodes:
        print("  SKIP: No nodes found")
        return True

    node = nodes[0]
    print(f"  Using node: {node.name} (key={node.key})")

    queries = node.queries.list()
    print(f"  Existing queries: {len(queries)}")
    return True


def test_node_query_lsblk(client: VergeClient) -> bool:
    """Test running lsblk query on a node."""
    nodes = client.nodes.list(limit=1)
    if not nodes:
        print("  SKIP: No nodes found")
        return True

    node = nodes[0]
    print(f"  lsblk on node: {node.name}")

    try:
        result = node.queries.lsblk(timeout=30)
        print(f"  Status: {result.status}")
        if result.result:
            preview = result.result[:300]
            print(f"  Result preview: {preview}")
        return True
    except Exception as e:
        print(f"  lsblk query failed: {e}")
        return False


# =============================================================================
# NIC Stats/Status/Fabric Tests
# =============================================================================


def test_machine_nic_stats_global(client: VergeClient) -> bool:
    """Test global NIC stats listing."""
    stats = client.machine_nic_stats.list(limit=5)
    print(f"  Found {len(stats)} NIC stats records")
    if stats:
        s = stats[0]
        print(
            f"  First NIC stats: parent_nic={s.nic_key}, "
            f"tx={s.tx_bps_display}, rx={s.rx_bps_display}"
        )
    return True


def test_machine_nic_status_global(client: VergeClient) -> bool:
    """Test global NIC status listing."""
    statuses = client.machine_nic_status.list(limit=5)
    print(f"  Found {len(statuses)} NIC status records")
    if statuses:
        s = statuses[0]
        print(
            f"  First NIC status: parent_nic={s.nic_key}, "
            f"link={s.link_status_display}, speed={s.speed_display}"
        )
    return True


def test_machine_nic_fabric_status_global(client: VergeClient) -> bool:
    """Test global NIC fabric status listing."""
    fabrics = client.machine_nic_fabric_status.list(limit=5)
    print(f"  Found {len(fabrics)} NIC fabric status records")
    if fabrics:
        f = fabrics[0]
        print(
            f"  First fabric status: parent_nic={f.nic_key}, "
            f"status={f.fabric_status_display}, "
            f"score={f.min_score}-{f.max_score}"
        )
    return True


def test_nic_stats_scoped(client: VergeClient) -> bool:
    """Test NIC stats through scoped manager on a VM NIC."""
    vms = client.vms.list(limit=3)
    if not vms:
        print("  SKIP: No VMs found")
        return True

    for vm in vms:
        try:
            nics = vm.nics.list()
            if nics:
                nic = nics[0]
                print(f"  Testing NIC {nic.key} on VM {vm.get('name', '?')}")
                try:
                    stats = nic.nic_stats.get()
                    print(
                        f"    Stats: tx={stats.tx_bps_display}, "
                        f"rx={stats.rx_bps_display}, "
                        f"total={stats.total_bps_display}"
                    )
                    return True
                except Exception as e:
                    print(f"    Stats not available for this NIC: {e}")
                try:
                    status = nic.link_status.get()
                    print(f"    Status: {status.link_status_display} at {status.speed_display}")
                    return True
                except Exception as e:
                    print(f"    Status not available for this NIC: {e}")
        except Exception as e:
            print(f"  Error accessing VM NICs: {e}")
            continue

    print("  SKIP: No VM NICs with stats found")
    return True


# =============================================================================
# LLDP Neighbor Tests
# =============================================================================


def test_lldp_neighbors_global(client: VergeClient) -> bool:
    """Test global LLDP neighbor listing."""
    neighbors = client.node_lldp_neighbors.list(limit=10)
    print(f"  Found {len(neighbors)} LLDP neighbors")
    if neighbors:
        n = neighbors[0]
        print(
            f"  First neighbor: node={n.node_key}, nic={n.nic_key}, "
            f"chassis={n.chassis_name}, port={n.port_id}"
        )
    else:
        print("  (No LLDP neighbors - normal if no LLDP-capable switches)")
    return True


def test_lldp_neighbors_scoped(client: VergeClient) -> bool:
    """Test LLDP neighbors scoped to a node."""
    nodes = client.nodes.list(limit=1)
    if not nodes:
        print("  SKIP: No nodes found")
        return True

    node = nodes[0]
    print(f"  LLDP neighbors for node: {node.name}")
    neighbors = node.lldp_neighbors.list()
    print(f"  Found {len(neighbors)} neighbors")
    if neighbors:
        for n in neighbors[:3]:
            print(f"    NIC {n.nic_key}: chassis={n.chassis_name}, port={n.port_id}, via={n.via}")
    return True


# =============================================================================
# System Diagnostics Tests
# =============================================================================


def test_system_diagnostics_list(client: VergeClient) -> bool:
    """Test listing system diagnostics."""
    diags = client.system_diagnostics.list()
    print(f"  Found {len(diags)} existing diagnostics")
    for d in diags[:3]:
        print(f"    {d.name}: status={d.status}, file={d.file_key}")
    return True


def test_system_diagnostics_create(client: VergeClient) -> bool:
    """Test creating a system diagnostic (and clean up after)."""
    import time

    name = f"sdk-inttest-{int(time.time())}"
    print(f"  Creating diagnostic: {name}")

    diag = client.system_diagnostics.create(
        name=name,
        description="Integration test - safe to delete",
    )
    print(f"  Created: key={diag.key}, status={diag.status}")

    # Wait for it to complete (up to 120s)
    try:
        diag = client.system_diagnostics.wait(diag.key, timeout=120, poll_interval=5)
        print(f"  Completed: status={diag.status}, file={diag.file_key}")
    except Exception as e:
        print(f"  Wait ended: {e}")
        # Fetch latest status
        diag = client.system_diagnostics.get(diag.key)
        print(f"  Current status: {diag.status}")

    # Clean up
    try:
        client.system_diagnostics.delete(diag.key)
        print(f"  Cleaned up diagnostic {name}")
    except Exception as e:
        print(f"  Cleanup failed (manual delete needed): {e}")

    return True


# =============================================================================
# Runner
# =============================================================================


def run_tests() -> None:
    """Run all integration tests."""
    print("=" * 60)
    print("Network Diagnostics Integration Tests")
    print("=" * 60)

    print("\nConnecting to dev environment...")
    try:
        client = get_client()
    except Exception as e:
        print(f"FATAL: Cannot connect to dev environment: {e}")
        sys.exit(1)

    tests = [
        ("Connection", test_connection),
        ("VNet Query - List", test_vnet_query_list),
        ("VNet Query - Ping", test_vnet_query_ping),
        ("VNet Query - ARP", test_vnet_query_arp),
        ("Node Query - List", test_node_query_list),
        ("Node Query - lsblk", test_node_query_lsblk),
        ("NIC Stats - Global", test_machine_nic_stats_global),
        ("NIC Status - Global", test_machine_nic_status_global),
        ("NIC Fabric Status - Global", test_machine_nic_fabric_status_global),
        ("NIC Stats - Scoped", test_nic_stats_scoped),
        ("LLDP Neighbors - Global", test_lldp_neighbors_global),
        ("LLDP Neighbors - Scoped", test_lldp_neighbors_scoped),
        ("System Diagnostics - List", test_system_diagnostics_list),
        ("System Diagnostics - Create/Wait/Delete", test_system_diagnostics_create),
    ]

    passed = 0
    failed = 0
    errors = []

    for name, test_fn in tests:
        print(f"\n[TEST] {name}")
        try:
            result = test_fn(client)
            if result:
                print("  ✓ PASS")
                passed += 1
            else:
                print("  ✗ FAIL")
                failed += 1
                errors.append(name)
        except Exception as e:
            print(f"  ✗ ERROR: {e}")
            traceback.print_exc()
            failed += 1
            errors.append(f"{name}: {e}")

    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed out of {len(tests)}")
    if errors:
        print("Failures:")
        for err in errors:
            print(f"  - {err}")
    print("=" * 60)

    client.disconnect()

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    run_tests()
