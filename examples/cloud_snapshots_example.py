#!/usr/bin/env python3
"""Example: Cloud snapshot management with pyvergeos.

This example demonstrates cloud (system) snapshot operations:
1. List existing cloud snapshots
2. Create a new cloud snapshot
3. Get snapshot details with VMs and tenants
4. Query VMs and tenants in a snapshot
5. Clean up resources

Cloud snapshots capture the entire system state including all VMs and
tenants at a point in time. They are used for disaster recovery and
point-in-time restoration.

Environment Variables:
    VERGE_HOST: VergeOS hostname or IP
    VERGE_USERNAME: Admin username
    VERGE_PASSWORD: Admin password
    VERGE_VERIFY_SSL: Set to 'false' for self-signed certs

Usage:
    # Set environment variables
    export VERGE_HOST=192.168.1.100
    export VERGE_USERNAME=admin
    export VERGE_PASSWORD=yourpassword
    export VERGE_VERIFY_SSL=false

    # Run the example
    python cloud_snapshots_example.py
"""

import sys
import time
from datetime import timedelta

from pyvergeos import VergeClient


def format_datetime(dt) -> str:
    """Format a datetime for display."""
    if dt is None:
        return "Never"
    return dt.strftime("%Y-%m-%d %H:%M:%S UTC")


def format_size(mb: int) -> str:
    """Format memory size for display."""
    if mb >= 1024:
        return f"{mb / 1024:.1f} GB"
    return f"{mb} MB"


def main() -> int:
    """Run the cloud snapshot management example."""
    # Create client from environment variables
    try:
        client = VergeClient.from_env()
    except ValueError as e:
        print(f"Error: {e}")
        print("Please set VERGE_HOST, VERGE_USERNAME, and VERGE_PASSWORD")
        return 1

    print(f"Connected to {client.cloud_name} (VergeOS {client.version})")
    print()

    # Use timestamp suffix for unique names
    ts = int(time.time()) % 100000
    snapshot_name = f"pyvergeos_snapshot_{ts}"

    try:
        # =====================================================================
        # Step 1: List existing cloud snapshots
        # =====================================================================
        print("=== Step 1: List Existing Cloud Snapshots ===")
        snapshots = client.cloud_snapshots.list()
        print(f"Found {len(snapshots)} active cloud snapshot(s):")
        for snap in snapshots[:5]:  # Show first 5
            print(f"  - {snap.name}")
            print(f"      Key: {snap.key}")
            print(f"      Created: {format_datetime(snap.created_at)}")
            if snap.never_expires:
                print("      Expires: Never")
            else:
                print(f"      Expires: {format_datetime(snap.expires_at)}")
            if snap.is_immutable:
                print(f"      Immutable: Yes ({snap.immutable_status})")
        if len(snapshots) > 5:
            print(f"  ... and {len(snapshots) - 5} more")
        print()

        # Also show expired count
        all_snapshots = client.cloud_snapshots.list(include_expired=True)
        expired_count = len(all_snapshots) - len(snapshots)
        if expired_count > 0:
            print(f"(Plus {expired_count} expired snapshot(s))")
            print()

        # =====================================================================
        # Step 2: Create a new cloud snapshot
        # =====================================================================
        print("=== Step 2: Create Cloud Snapshot ===")
        print(f"Creating snapshot: {snapshot_name}")
        print("This may take a moment...")
        print()

        snapshot = client.cloud_snapshots.create(
            name=snapshot_name,
            retention=timedelta(hours=1),  # 1 hour retention for demo
            min_snapshots=1,
            wait=True,  # Wait for completion
            wait_timeout=180,  # 3 minute timeout
        )

        print("Snapshot created successfully!")
        print(f"  Name: {snapshot.name}")
        print(f"  Key: {snapshot.key}")
        print(f"  Created: {format_datetime(snapshot.created_at)}")
        print(f"  Expires: {format_datetime(snapshot.expires_at)}")
        print(f"  Status: {snapshot.status}")
        print()

        # =====================================================================
        # Step 3: Get snapshot with VMs and tenants
        # =====================================================================
        print("=== Step 3: Get Snapshot Details ===")
        detailed_snap = client.cloud_snapshots.get(
            snapshot.key,
            include_vms=True,
            include_tenants=True,
        )

        print(f"Snapshot: {detailed_snap.name}")
        print(f"  Description: {detailed_snap.description or '(none)'}")
        print(f"  Immutable: {detailed_snap.is_immutable}")
        print(f"  Private: {detailed_snap.is_private}")

        if detailed_snap.vms:
            print(f"\n  VMs ({len(detailed_snap.vms)}):")
            for vm in detailed_snap.vms[:5]:
                print(f"    - {vm.name}")
                print(f"        Cores: {vm.cpu_cores}, RAM: {format_size(vm.ram_mb)}")
                print(f"        OS: {vm.os_family or 'Unknown'}")
            if len(detailed_snap.vms) > 5:
                print(f"    ... and {len(detailed_snap.vms) - 5} more")
        else:
            print("\n  VMs: None captured in this snapshot")

        if detailed_snap.tenants:
            print(f"\n  Tenants ({len(detailed_snap.tenants)}):")
            for tenant in detailed_snap.tenants[:5]:
                print(f"    - {tenant.name}")
                print(f"        Nodes: {tenant.nodes}")
                print(f"        Cores: {tenant.cpu_cores}, RAM: {format_size(tenant.ram_mb)}")
            if len(detailed_snap.tenants) > 5:
                print(f"    ... and {len(detailed_snap.tenants) - 5} more")
        else:
            print("\n  Tenants: None captured in this snapshot")
        print()

        # =====================================================================
        # Step 4: Query VMs and tenants via sub-managers
        # =====================================================================
        print("=== Step 4: Query VMs and Tenants via Sub-managers ===")

        # Query VMs
        vm_manager = client.cloud_snapshots.vms(snapshot.key)
        vms = vm_manager.list()
        print(f"VMs in snapshot (via sub-manager): {len(vms)}")

        # Query tenants
        tenant_manager = client.cloud_snapshots.tenants(snapshot.key)
        tenants = tenant_manager.list()
        print(f"Tenants in snapshot (via sub-manager): {len(tenants)}")

        # Can also use object methods
        vms_from_obj = snapshot.get_vms()
        tenants_from_obj = snapshot.get_tenants()
        print(f"VMs (via object method): {len(vms_from_obj)}")
        print(f"Tenants (via object method): {len(tenants_from_obj)}")
        print()

        # =====================================================================
        # Step 5: Demonstrate restore APIs (without actually restoring)
        # =====================================================================
        print("=== Step 5: Restore API Overview ===")
        print("Cloud snapshots support restoring VMs and tenants:")
        print()
        print("  # Restore a VM from snapshot")
        print("  result = client.cloud_snapshots.restore_vm(")
        print("      snapshot_key=snapshot.key,")
        print("      vm_name='MyVM',")
        print("      new_name='MyVM-Restored',")
        print("  )")
        print()
        print("  # Restore a tenant from snapshot")
        print("  result = client.cloud_snapshots.restore_tenant(")
        print("      snapshot_key=snapshot.key,")
        print("      tenant_name='MyTenant',")
        print("      new_name='MyTenant-DR',")
        print("  )")
        print()

        # =====================================================================
        # Cleanup
        # =====================================================================
        print("=== Cleanup ===")
        print("What would you like to do with the created snapshot?")
        print("  1. Keep the snapshot (default)")
        print("  2. Delete the snapshot")
        print()

        choice = input("Enter choice [1]: ").strip() or "1"

        if choice == "2":
            print()
            print(f"Deleting snapshot: {snapshot.name}...")

            # Can use either manager method or object method
            snapshot.delete()

            print("Snapshot deleted.")
        else:
            print()
            print(f"Keeping snapshot: {snapshot.name}")
            print(f"It will expire at: {format_datetime(snapshot.expires_at)}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()
        return 1

    finally:
        client.disconnect()

    print()
    print("Cloud snapshot example completed!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
