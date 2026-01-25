#!/usr/bin/env python3
"""VM Lifecycle Management Examples.

This script demonstrates common VM management tasks with pyvergeos:
- Listing and filtering VMs
- Starting, stopping, and restarting VMs
- Cloning VMs
- Working with snapshots
- Bulk operations
- Maintenance workflows
- Reporting

Usage:
    # Run all examples (dry-run mode - just shows what would happen)
    python vm_lifecycle.py

    # Run a specific section
    python vm_lifecycle.py --section listing
    python vm_lifecycle.py --section power
    python vm_lifecycle.py --section snapshots
    python vm_lifecycle.py --section cloning
    python vm_lifecycle.py --section reporting

Prerequisites:
    Set environment variables:
    - VERGE_HOST: VergeOS hostname or IP
    - VERGE_USERNAME: Username
    - VERGE_PASSWORD: Password
    - VERGE_VERIFY_SSL: "false" to skip SSL verification
"""

from __future__ import annotations

import argparse
import fnmatch
import sys
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

from pyvergeos import VergeClient
from pyvergeos.exceptions import NotFoundError, VergeError

if TYPE_CHECKING:
    from pyvergeos.resources.vms import VM


def filter_vms_by_pattern(vms: list[VM], pattern: str) -> list[VM]:
    """Filter VMs by name pattern (supports wildcards like * and ?).

    Args:
        vms: List of VMs to filter.
        pattern: Glob pattern (e.g., '*test*', 'web-*', 'app-??-prod').

    Returns:
        List of VMs matching the pattern.
    """
    return [vm for vm in vms if fnmatch.fnmatch(vm.name.lower(), pattern.lower())]


# =============================================================================
# QUERYING VMs WITH FILTERS
# =============================================================================


def demo_listing_vms(client: VergeClient) -> None:
    """Demonstrate various ways to list and filter VMs."""
    print("\n" + "=" * 60)
    print("QUERYING VMs WITH FILTERS")
    print("=" * 60)

    # List all VMs (excludes snapshots by default)
    print("\n--- All VMs ---")
    vms = client.vms.list()
    print(f"Total VMs: {len(vms)}")
    for vm in vms[:5]:  # Show first 5
        print(f"  {vm.name}: {vm.status} on {vm.node_name}")
    if len(vms) > 5:
        print(f"  ... and {len(vms) - 5} more")

    # List only running VMs
    print("\n--- Running VMs ---")
    running = client.vms.list_running()
    print(f"Running VMs: {len(running)}")
    for vm in running[:5]:
        print(f"  {vm.name} on {vm.node_name}")

    # List stopped VMs
    print("\n--- Stopped VMs ---")
    stopped = client.vms.list_stopped()
    print(f"Stopped VMs: {len(stopped)}")
    for vm in stopped[:5]:
        print(f"  {vm.name}")

    # Find VM by name (exact match)
    print("\n--- Find VM by Name ---")
    try:
        vm = client.vms.get(name="test")
        print(f"Found: {vm.name} (key={vm.key})")
    except NotFoundError:
        print("VM 'test' not found")

    # Find VMs by name pattern (client-side filtering with wildcards)
    print("\n--- Find VMs by Pattern ---")
    # VMs with names containing 'test' (case-insensitive with wildcards)
    filtered = filter_vms_by_pattern(vms, "*test*")
    print(f"VMs matching '*test*': {len(filtered)}")
    for vm in filtered[:5]:
        print(f"  {vm.name}")

    # More pattern examples
    print("\n--- Pattern matching examples ---")
    print("# Match VMs starting with 'web-'")
    print("filter_vms_by_pattern(vms, 'web-*')")
    print("")
    print("# Match VMs ending with '-prod'")
    print("filter_vms_by_pattern(vms, '*-prod')")
    print("")
    print("# Match VMs with pattern like 'app-01-xxx'")
    print("filter_vms_by_pattern(vms, 'app-??-*')")

    # Get a specific VM by key
    print("\n--- Get VM by Key ---")
    if vms:
        first_vm = client.vms.get(vms[0].key)
        print(f"VM key {first_vm.key}: {first_vm.name}")

    # Advanced filtering: VMs with more than 4GB RAM
    print("\n--- VMs with > 4GB RAM ---")
    large_vms = [vm for vm in client.vms.list() if (vm.get("ram") or 0) > 4096]
    print(f"VMs with > 4GB RAM: {len(large_vms)}")
    for vm in large_vms[:5]:
        ram_gb = (vm.get("ram") or 0) / 1024
        print(f"  {vm.name}: {ram_gb:.1f} GB")

    # VMs with specific CPU count
    print("\n--- VMs with 4+ CPU cores ---")
    multi_cpu = [vm for vm in client.vms.list() if (vm.get("cpu_cores") or 0) >= 4]
    print(f"VMs with 4+ cores: {len(multi_cpu)}")
    for vm in multi_cpu[:5]:
        print(f"  {vm.name}: {vm.get('cpu_cores')} cores")


# =============================================================================
# STARTING, STOPPING, AND RESTARTING VMs
# =============================================================================


def demo_power_operations(client: VergeClient, dry_run: bool = True) -> None:
    """Demonstrate VM power operations."""
    print("\n" + "=" * 60)
    print("VM POWER OPERATIONS")
    print("=" * 60)

    if dry_run:
        print("\n[DRY RUN MODE - showing what would happen]")

    # Find a stopped VM for demonstration
    stopped_vms = client.vms.list_stopped()
    running_vms = client.vms.list_running()

    print("\n--- Start a VM ---")
    print("# Start a VM by name")
    print("vm = client.vms.get(name='WebServer01')")
    print("vm.power_on()")
    if stopped_vms and not dry_run:
        vm = stopped_vms[0]
        print(f"\nStarting {vm.name}...")
        vm.power_on()
        print(f"VM {vm.name} started")

    print("\n--- Start VM on preferred node ---")
    print("# Start a VM on a specific node")
    print("vm.power_on(preferred_node=2)")

    print("\n--- Stop a VM gracefully ---")
    print("# Graceful ACPI shutdown")
    print("vm = client.vms.get(name='WebServer01')")
    print("vm.power_off()")
    if running_vms and not dry_run:
        # Be careful not to stop important VMs
        print("\n[Skipping actual stop to avoid disruption]")

    print("\n--- Force stop a VM ---")
    print("# Hard power off (use with caution)")
    print("vm.power_off(force=True)")

    print("\n--- Reset a VM ---")
    print("# Hard reset")
    print("vm.reset()")

    print("\n--- Guest operations (requires guest agent) ---")
    print("# Graceful guest reboot")
    print("vm.guest_reboot()")
    print("")
    print("# Graceful guest shutdown")
    print("vm.guest_shutdown()")


# =============================================================================
# BULK OPERATIONS
# =============================================================================


def demo_bulk_operations(client: VergeClient, dry_run: bool = True) -> None:
    """Demonstrate bulk operations on VMs."""
    print("\n" + "=" * 60)
    print("BULK OPERATIONS")
    print("=" * 60)

    if dry_run:
        print("\n[DRY RUN MODE - showing what would happen]")

    print("\n--- Start all stopped VMs matching a pattern ---")
    print("# Start all stopped VMs with 'test' in the name")
    print("for vm in client.vms.list_stopped():")
    print("    if 'test' in vm.name.lower():")
    print("        vm.power_on()")

    test_vms = [vm for vm in client.vms.list_stopped() if "test" in vm.name.lower()]
    print(f"\nWould start {len(test_vms)} VMs:")
    for vm in test_vms[:5]:
        print(f"  - {vm.name}")

    print("\n--- Stop all VMs matching a pattern ---")
    print("# Stop all test VMs")
    print("for vm in client.vms.list_running():")
    print("    if '-test-' in vm.name.lower():")
    print("        vm.power_off()")

    print("\n--- Collect results from bulk operations ---")
    print("# Start VMs and track results")
    print("started_vms = []")
    print("for vm in client.vms.list_stopped():")
    print("    if vm.name.startswith('App'):")
    print("        vm.power_on()")
    print("        started_vms.append(vm)")


# =============================================================================
# WORKING WITH VM SNAPSHOTS
# =============================================================================


def demo_snapshots(client: VergeClient, dry_run: bool = True) -> None:
    """Demonstrate snapshot operations."""
    print("\n" + "=" * 60)
    print("WORKING WITH VM SNAPSHOTS")
    print("=" * 60)

    if dry_run:
        print("\n[DRY RUN MODE - showing what would happen]")

    # Find a VM to work with
    vms = client.vms.list()
    if not vms:
        print("\nNo VMs available for snapshot demo")
        return

    demo_vm = vms[0]
    print(f"\nUsing VM: {demo_vm.name} (key={demo_vm.key})")

    print("\n--- List snapshots for a VM ---")
    print("vm = client.vms.get(name='WebServer01')")
    print("snapshots = vm.snapshots.list()")
    snapshots = demo_vm.snapshots.list()
    print(f"\nSnapshots for {demo_vm.name}: {len(snapshots)}")
    for snap in snapshots[:5]:
        print(f"  - {snap.get('name')}: created {snap.created_at}")

    print("\n--- Create a snapshot ---")
    print("# Basic snapshot")
    print("vm.snapshots.create(name='Before-Update')")
    print("")
    print("# Snapshot with retention (seconds)")
    print("vm.snapshots.create(")
    print("    name='Pre-Patch',")
    print("    retention=86400 * 7,  # 7 days")
    print("    description='Before applying security patches'")
    print(")")

    print("\n--- Restore a snapshot to new VM ---")
    print("# Clone snapshot to a new VM (default)")
    print("snapshots = vm.snapshots.list()")
    print("if snapshots:")
    print("    vm.snapshots.restore(snapshots[0].key, name='Restored-VM')")

    print("\n--- Restore snapshot over existing VM ---")
    print("# WARNING: Overwrites current VM state!")
    print("vm.snapshots.restore(snapshot_key, replace_original=True)")

    print("\n--- Delete a snapshot ---")
    print("vm.snapshots.delete(snapshot_key)")

    print("\n--- Delete old snapshots ---")
    print("# Remove snapshots older than 7 days")
    print("cutoff = datetime.now(timezone.utc) - timedelta(days=7)")
    print("for snap in vm.snapshots.list():")
    print("    if snap.created_at and snap.created_at < cutoff:")
    print("        vm.snapshots.delete(snap.key)")

    # Show example of what would be deleted
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    old_snaps = [s for s in snapshots if s.created_at and s.created_at < cutoff]
    print(f"\nWould delete {len(old_snaps)} old snapshots")


# =============================================================================
# CLONING VMs
# =============================================================================


def demo_cloning(client: VergeClient, dry_run: bool = True) -> None:
    """Demonstrate VM cloning operations."""
    print("\n" + "=" * 60)
    print("CLONING VMs")
    print("=" * 60)

    if dry_run:
        print("\n[DRY RUN MODE - showing what would happen]")

    print("\n--- Clone a VM ---")
    print("# Clone a VM with a new name")
    print("vm = client.vms.get(name='Template-Ubuntu22')")
    print("result = vm.clone(name='NewWebServer')")

    print("\n--- Clone with options ---")
    print("# Clone and preserve MAC addresses")
    print("vm.clone(name='ClonedServer', preserve_macs=True)")

    print("\n--- Clone and get result ---")
    print("# The clone operation returns task info")
    print("result = vm.clone(name='DevServer01')")
    print("print(f'Clone task: {result}')")

    # Show available VMs that could be cloned
    vms = client.vms.list()
    print(f"\n{len(vms)} VMs available for cloning")


# =============================================================================
# MAINTENANCE WORKFLOWS
# =============================================================================


def demo_maintenance_workflows(client: VergeClient, dry_run: bool = True) -> None:
    """Demonstrate common maintenance workflows."""
    print("\n" + "=" * 60)
    print("MAINTENANCE WORKFLOWS")
    print("=" * 60)

    if dry_run:
        print("\n[DRY RUN MODE - showing what would happen]")

    print("\n--- Pre-maintenance snapshot workflow ---")
    print("""
# 1. Create pre-maintenance snapshot
vm = client.vms.get(name='WebServer01')
snapshot_name = f"Pre-Maintenance-{datetime.now().strftime('%Y%m%d')}"
result = vm.snapshots.create(name=snapshot_name, retention=86400)
print(f"Snapshot created: {snapshot_name}")

# 2. Perform maintenance
# ... your changes here ...

# 3. If something goes wrong, restore the snapshot
# vm.snapshots.restore(snapshot_key, replace_original=True)
""")

    print("\n--- Maintenance window workflow ---")
    print("""
# Record running VMs before shutdown
running_vms = client.vms.list_running()

# Save to file for later restart
with open('running-vms-backup.csv', 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['name', 'key'])
    for vm in running_vms:
        writer.writerow([vm.name, vm.key])

# Stop all running VMs
for vm in running_vms:
    print(f"Stopping {vm.name}...")
    vm.power_off()

# ... perform maintenance ...

# After maintenance, restart them
with open('running-vms-backup.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        vm = client.vms.get(int(row['key']))
        print(f"Starting {vm.name}...")
        vm.power_on()
""")

    # Show what would be affected
    running = client.vms.list_running()
    print(f"\nCurrently {len(running)} VMs running that would be affected")


# =============================================================================
# GENERATING VM REPORTS
# =============================================================================


def demo_reporting(client: VergeClient) -> None:
    """Demonstrate VM reporting capabilities."""
    print("\n" + "=" * 60)
    print("GENERATING VM REPORTS")
    print("=" * 60)

    vms = client.vms.list()

    print("\n--- VM Inventory Summary ---")
    running = [vm for vm in vms if vm.is_running]
    stopped = [vm for vm in vms if not vm.is_running]
    total_cpu = sum(vm.get("cpu_cores") or 0 for vm in vms)
    total_ram_gb = sum((vm.get("ram") or 0) for vm in vms) / 1024

    print(f"Total VMs:     {len(vms)}")
    print(f"Running:       {len(running)}")
    print(f"Stopped:       {len(stopped)}")
    print(f"Total CPU:     {total_cpu} cores")
    print(f"Total RAM:     {total_ram_gb:.1f} GB")

    print("\n--- Export VM inventory to CSV ---")
    print("# Code to export inventory:")
    print("""
with open('vm-inventory.csv', 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['Name', 'Status', 'CPUs', 'RAM_GB', 'Node', 'Cluster'])
    for vm in client.vms.list():
        writer.writerow([
            vm.name,
            vm.status,
            vm.get('cpu_cores'),
            (vm.get('ram') or 0) / 1024,
            vm.node_name,
            vm.cluster_name
        ])
""")

    print("\n--- Large VMs (4+ cores or 8GB+ RAM) ---")
    large_vms = [
        vm
        for vm in vms
        if (vm.get("cpu_cores") or 0) >= 4 or (vm.get("ram") or 0) >= 8192
    ]
    print(f"Found {len(large_vms)} large VMs:")
    print(f"{'Name':<30} {'CPUs':>5} {'RAM(GB)':>8} {'Status':<10}")
    print("-" * 60)
    for vm in large_vms[:10]:
        ram_gb = (vm.get("ram") or 0) / 1024
        print(f"{vm.name:<30} {vm.get('cpu_cores') or 0:>5} {ram_gb:>8.1f} {vm.status:<10}")

    print("\n--- VMs by Node ---")
    nodes: dict[str, list[VM]] = {}
    for vm in vms:
        node = vm.node_name or "Unknown"
        if node not in nodes:
            nodes[node] = []
        nodes[node].append(vm)

    for node, node_vms in sorted(nodes.items()):
        running_count = sum(1 for vm in node_vms if vm.is_running)
        print(f"  {node}: {len(node_vms)} VMs ({running_count} running)")

    print("\n--- VMs without snapshots ---")
    vms_without_snaps = []
    for vm in vms[:10]:  # Check first 10 to avoid too many API calls
        if not vm.snapshots.list():
            vms_without_snaps.append(vm)
    print(f"VMs without snapshots (checked {min(10, len(vms))}): {len(vms_without_snaps)}")
    for vm in vms_without_snaps[:5]:
        print(f"  - {vm.name}")


# =============================================================================
# MAIN
# =============================================================================


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="VM Lifecycle Management Examples",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Sections:
  listing     - Querying and filtering VMs
  power       - Power operations (start/stop/restart)
  bulk        - Bulk operations on multiple VMs
  snapshots   - Working with VM snapshots
  cloning     - Cloning VMs
  maintenance - Maintenance workflows
  reporting   - Generating reports

Examples:
  %(prog)s                          # Run all sections (dry-run)
  %(prog)s --section listing        # Run only listing examples
  %(prog)s --section reporting      # Run only reporting examples
  %(prog)s --no-dry-run             # Actually execute operations (use with caution!)
""",
    )
    parser.add_argument(
        "--section",
        choices=["listing", "power", "bulk", "snapshots", "cloning", "maintenance", "reporting"],
        help="Run only a specific section",
    )
    parser.add_argument(
        "--no-dry-run",
        action="store_true",
        help="Actually execute operations (default is dry-run mode)",
    )

    args = parser.parse_args()
    dry_run = not args.no_dry_run

    print("=" * 60)
    print("pyvergeos VM Lifecycle Examples")
    print("=" * 60)

    if dry_run:
        print("\n[DRY RUN MODE - operations will NOT be executed]")
        print("[Use --no-dry-run to actually execute operations]")

    try:
        print("\nConnecting to VergeOS...")
        with VergeClient.from_env() as client:
            print(f"Connected! VergeOS version: {client.version}")

            sections = {
                "listing": lambda: demo_listing_vms(client),
                "power": lambda: demo_power_operations(client, dry_run),
                "bulk": lambda: demo_bulk_operations(client, dry_run),
                "snapshots": lambda: demo_snapshots(client, dry_run),
                "cloning": lambda: demo_cloning(client, dry_run),
                "maintenance": lambda: demo_maintenance_workflows(client, dry_run),
                "reporting": lambda: demo_reporting(client),
            }

            if args.section:
                # Run specific section
                sections[args.section]()
            else:
                # Run all sections
                for section_func in sections.values():
                    section_func()

            print("\n" + "=" * 60)
            print("Examples completed!")
            print("=" * 60)
            return 0

    except VergeError as e:
        print(f"\nError: {e}")
        return 1
    except KeyboardInterrupt:
        print("\n\nInterrupted by user.")
        return 130


if __name__ == "__main__":
    sys.exit(main())
