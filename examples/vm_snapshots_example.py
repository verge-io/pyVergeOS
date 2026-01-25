#!/usr/bin/env python3
"""Example: VM Snapshot operations with pyvergeos.

This example demonstrates snapshot operations including:
- Creating a test VM
- Taking a snapshot of the VM
- Restoring a snapshot to a new VM (default)
- Restoring a snapshot over the existing VM (--overwrite)

Usage:
    # Restore snapshot to a new VM (default)
    python vm_snapshots_example.py

    # Restore snapshot over the existing VM
    python vm_snapshots_example.py --overwrite

    # Custom VM name
    python vm_snapshots_example.py --vm-name my-test-vm

    # Skip cleanup (keep VMs for inspection)
    python vm_snapshots_example.py --no-cleanup

Requirements:
    Set environment variables:
    - VERGE_HOST: VergeOS hostname or IP
    - VERGE_USERNAME: Username
    - VERGE_PASSWORD: Password
    - VERGE_VERIFY_SSL: "false" to skip SSL verification
"""

import argparse
import sys
import time

from pyvergeos import VergeClient
from pyvergeos.exceptions import NotFoundError, VergeError


def create_test_vm(client: VergeClient, vm_name: str) -> int:
    """Create a test VM for snapshot demonstration.

    Args:
        client: Connected VergeClient instance.
        vm_name: Name for the test VM.

    Returns:
        The created VM's $key.
    """
    print(f"\n{'=' * 50}")
    print("STEP 1: Create Test VM")
    print("=" * 50)

    # Check if VM already exists and clean it up
    try:
        existing = client.vms.get(name=vm_name)
        print(f"VM '{vm_name}' already exists (key={existing.key})")
        print("Cleaning up existing VM...")
        if existing.is_running:
            existing.power_off(force=True)
            time.sleep(2)
        client.vms.delete(existing.key)
        print("Existing VM deleted.")
        time.sleep(1)
    except NotFoundError:
        pass  # VM doesn't exist, proceed with creation

    # Create the VM
    print(f"\nCreating VM: {vm_name}")
    vm = client.vms.create(
        name=vm_name,
        cpu_cores=1,
        ram=1024,  # 1GB
        description="Test VM for snapshot example",
        os_family="linux",
    )
    print(f"  VM created: key={vm.key}, name={vm.name}")

    # Add a small drive
    print("\nAdding 10GB boot drive...")
    drive = vm.drives.create(
        name="boot_drive",
        size_gb=10,
        interface="virtio-scsi",
        media="disk",
        description="Boot drive for snapshot test",
    )
    print(f"  Drive created: key={drive.key}, size={drive.size_gb}GB")

    return vm.key


def create_snapshot(client: VergeClient, vm_key: int) -> int:
    """Create a snapshot of the VM.

    Args:
        client: Connected VergeClient instance.
        vm_key: The VM $key to snapshot.

    Returns:
        The created snapshot's $key.
    """
    print(f"\n{'=' * 50}")
    print("STEP 2: Create Snapshot")
    print("=" * 50)

    vm = client.vms.get(vm_key)
    print(f"\nCreating snapshot of VM: {vm.name}")

    # Create snapshot with 1-hour retention
    result = vm.snapshots.create(
        name=f"{vm.name}-snapshot",
        retention=3600,  # 1 hour
        quiesce=False,
        description="Snapshot created by pyvergeos example",
    )

    if result:
        print(f"  Snapshot task initiated: {result}")

    # Wait a moment for snapshot to be created
    print("  Waiting for snapshot to be available...")
    time.sleep(3)

    # Find the snapshot we just created
    snapshots = vm.snapshots.list()
    if not snapshots:
        raise VergeError("No snapshots found after creation")

    # Get the most recent snapshot
    snapshot = snapshots[0]  # Already sorted by created desc
    print("\n  Snapshot created:")
    print(f"    Key: {snapshot.key}")
    print(f"    Name: {snapshot.get('name')}")
    print(f"    Created: {snapshot.created_at}")
    print(f"    Expires: {snapshot.expires_at}")
    print(f"    Quiesced: {snapshot.is_quiesced}")

    return snapshot.key


def restore_to_new_vm(
    client: VergeClient,
    vm_key: int,
    snapshot_key: int,
) -> int | None:
    """Restore snapshot to a new VM.

    Args:
        client: Connected VergeClient instance.
        vm_key: The original VM $key.
        snapshot_key: The snapshot $key to restore.

    Returns:
        The new VM's $key, or None if restore failed.
    """
    print(f"\n{'=' * 50}")
    print("STEP 3: Restore Snapshot to New VM")
    print("=" * 50)

    vm = client.vms.get(vm_key)
    restored_name = f"{vm.name}-restored"

    # Check if a VM with the target name already exists and clean it up
    try:
        existing = client.vms.get(name=restored_name)
        print(f"\nVM '{restored_name}' already exists (key={existing.key})")
        print("Cleaning up existing VM first...")
        if existing.is_running:
            existing.power_off(force=True)
            time.sleep(2)
        client.vms.delete(existing.key)
        print("Existing VM deleted.")
        time.sleep(1)
    except NotFoundError:
        pass  # No existing VM with that name

    print(f"\nRestoring snapshot to new VM: {restored_name}")

    result = vm.snapshots.restore(
        key=snapshot_key,
        name=restored_name,
        replace_original=False,  # Clone to new VM
        power_on=False,
    )

    if result:
        print(f"  Restore task result: {result}")

    # Get the new VM key from the response
    new_vm_key = None
    if result and isinstance(result, dict):
        response = result.get("response", {})
        if isinstance(response, dict):
            new_vm_key = response.get("vmkey")

    # Wait for the new VM to be created
    print("  Waiting for restored VM to be available...")
    time.sleep(5)

    # Get the restored VM - prefer using the key from the response
    try:
        if new_vm_key:
            restored_vm = client.vms.get(int(new_vm_key))
        else:
            restored_vm = client.vms.get(name=restored_name)

        print("\n  Restored VM created:")
        print(f"    Key: {restored_vm.key}")
        print(f"    Name: {restored_vm.name}")
        print(f"    Status: {restored_vm.status}")
        print(f"    RAM: {restored_vm.get('ram')} MB")
        print(f"    CPU: {restored_vm.get('cpu_cores')} cores")

        # Show drives
        drives = restored_vm.drives.list()
        print(f"    Drives: {len(drives)}")
        for drive in drives:
            print(f"      - {drive.name}: {drive.size_gb}GB")

        return restored_vm.key
    except NotFoundError:
        print("  Warning: Could not find restored VM")
        return None


def restore_overwrite(
    client: VergeClient,
    vm_key: int,
    snapshot_key: int,
) -> None:
    """Restore snapshot over the existing VM.

    Args:
        client: Connected VergeClient instance.
        vm_key: The VM $key to overwrite.
        snapshot_key: The snapshot $key to restore.
    """
    print(f"\n{'=' * 50}")
    print("STEP 3: Restore Snapshot (Overwrite Existing)")
    print("=" * 50)

    vm = client.vms.get(vm_key)
    print(f"\nRestoring snapshot over existing VM: {vm.name}")

    # VM must be powered off for in-place restore
    if vm.is_running:
        print("  Powering off VM for in-place restore...")
        vm.power_off(force=True)
        time.sleep(3)
        vm = client.vms.get(vm_key)  # Refresh status

    print("  Performing in-place restore...")
    print("  WARNING: All changes since snapshot will be lost!")

    result = vm.snapshots.restore(
        key=snapshot_key,
        replace_original=True,  # Overwrite existing
        power_on=False,
    )

    if result:
        print(f"  Restore task result: {result}")

    # Wait for restore to complete
    print("  Waiting for restore to complete...")
    time.sleep(5)

    # Verify the VM still exists
    vm = client.vms.get(vm_key)
    print("\n  VM restored in-place:")
    print(f"    Key: {vm.key}")
    print(f"    Name: {vm.name}")
    print(f"    Status: {vm.status}")


def cleanup(
    client: VergeClient,
    vm_keys: list[int],
) -> None:
    """Clean up created VMs.

    Args:
        client: Connected VergeClient instance.
        vm_keys: List of VM $keys to delete.
    """
    print(f"\n{'=' * 50}")
    print("CLEANUP")
    print("=" * 50)

    for vm_key in vm_keys:
        try:
            vm = client.vms.get(vm_key)
            print(f"\nDeleting VM: {vm.name} (key={vm_key})")

            # Delete snapshots first
            snapshots = vm.snapshots.list()
            for snapshot in snapshots:
                print(f"  Deleting snapshot: {snapshot.get('name')}")
                vm.snapshots.delete(snapshot.key)

            # Power off if running
            if vm.is_running:
                print("  Powering off VM...")
                vm.power_off(force=True)
                time.sleep(2)

            # Delete the VM
            client.vms.delete(vm_key)
            print("  VM deleted successfully.")

        except NotFoundError:
            print(f"\nVM {vm_key} not found (already deleted?).")
        except Exception as e:
            print(f"\nError cleaning up VM {vm_key}: {e}")


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="VM Snapshot example for pyvergeos",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                      # Restore snapshot to new VM (default)
  %(prog)s --overwrite          # Restore snapshot over existing VM
  %(prog)s --vm-name my-vm      # Use custom VM name
  %(prog)s --no-cleanup         # Keep VMs after example completes
        """,
    )
    parser.add_argument(
        "--vm-name",
        default="snapshot-test-vm",
        help="Name for the test VM (default: snapshot-test-vm)",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Restore snapshot over existing VM instead of creating new",
    )
    parser.add_argument(
        "--no-cleanup",
        action="store_true",
        help="Skip cleanup (keep VMs for inspection)",
    )

    args = parser.parse_args()

    print("=" * 50)
    print("pyvergeos VM Snapshot Example")
    print("=" * 50)
    print()
    print(f"VM Name: {args.vm_name}")
    print(f"Mode: {'Overwrite existing' if args.overwrite else 'Restore to new VM'}")
    print(f"Cleanup: {'No' if args.no_cleanup else 'Yes'}")

    # Track VMs for cleanup
    vm_keys_to_cleanup: list[int] = []

    try:
        # Connect to VergeOS using environment variables
        print("\nConnecting to VergeOS...")
        with VergeClient.from_env() as client:
            print(f"Connected! VergeOS version: {client.version}")

            # Step 1: Create test VM
            vm_key = create_test_vm(client, args.vm_name)
            vm_keys_to_cleanup.append(vm_key)

            # Step 2: Create snapshot
            snapshot_key = create_snapshot(client, vm_key)

            # Step 3: Restore snapshot
            if args.overwrite:
                # Restore over existing VM
                restore_overwrite(client, vm_key, snapshot_key)
            else:
                # Restore to new VM
                restored_key = restore_to_new_vm(client, vm_key, snapshot_key)
                if restored_key:
                    vm_keys_to_cleanup.append(restored_key)

            # Cleanup
            if not args.no_cleanup:
                cleanup(client, vm_keys_to_cleanup)
            else:
                print(f"\n{'=' * 50}")
                print("SKIPPING CLEANUP")
                print("=" * 50)
                print("\nVMs left for inspection:")
                for key in vm_keys_to_cleanup:
                    try:
                        vm = client.vms.get(key)
                        print(f"  - {vm.name} (key={key})")
                    except NotFoundError:
                        print(f"  - key={key} (not found)")

            print(f"\n{'=' * 50}")
            print("Example completed successfully!")
            print("=" * 50)
            return 0

    except VergeError as e:
        print(f"\nError: {e}")
        return 1
    except KeyboardInterrupt:
        print("\n\nInterrupted by user.")
        return 130


if __name__ == "__main__":
    sys.exit(main())
