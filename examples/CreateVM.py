#!/usr/bin/env python3
"""Example: Create a fully configured VM with pyvergeos.

This example demonstrates creating a VM with:
- 2 CPU cores and 8GB RAM
- 50GB boot drive on Tier 1 storage
- 100GB data drive on Tier 3 storage
- 1 NIC connected to the External network
- VergeOS installation ISO attached as CD-ROM

Requirements:
- A VergeOS system with:
  - An "External" network
  - Storage tiers 1 and 3 configured
  - The ISO file "verge-io-install-26.0.1.2.iso" uploaded to files
"""

import sys
import time

from pyvergeos import VergeClient
from pyvergeos.exceptions import NotFoundError, VergeError


def create_configured_vm(
    client: VergeClient,
    vm_name: str = "pstest-001",
) -> int:
    """Create a fully configured VM.

    Args:
        client: Connected VergeClient instance.
        vm_name: Name for the new VM.

    Returns:
        The created VM's $key.
    """
    print(f"Creating VM: {vm_name}")
    print("-" * 40)

    # Step 1: Create the VM
    print("1. Creating VM with 2 CPU cores, 8GB RAM...")
    vm = client.vms.create(
        name=vm_name,
        cpu_cores=2,
        ram=8192,  # 8GB in MB (will be normalized to 8192 which is 8 * 1024)
        description="Test VM created by pyvergeos example",
        os_family="linux",
        machine_type="pc-q35-10.0",
    )
    print(f"   VM created: key={vm.key}, name={vm.name}")

    # Step 2: Add 50GB boot drive on Tier 1
    print("2. Adding 50GB boot drive on Tier 1...")
    boot_drive = vm.drives.create(
        name="boot_drive",
        size_gb=50,
        interface="virtio-scsi",
        media="disk",
        tier=1,
        description="Boot drive - Tier 1",
    )
    print(f"   Boot drive created: key={boot_drive.key}, size={boot_drive.size_gb}GB")

    # Step 3: Add 100GB data drive on Tier 3
    print("3. Adding 100GB data drive on Tier 3...")
    data_drive = vm.drives.create(
        name="data_drive",
        size_gb=100,
        interface="virtio-scsi",
        media="disk",
        tier=3,
        description="Data drive - Tier 3",
    )
    print(f"   Data drive created: key={data_drive.key}, size={data_drive.size_gb}GB")

    # Step 4: Add CD-ROM with VergeOS ISO
    print("4. Adding CD-ROM with VergeOS installation ISO...")
    try:
        cdrom_drive = vm.drives.create(
            name="cdrom_0",
            interface="ide",
            media="cdrom",
            media_source="verge-io-install-26.0.1.2.iso",
            description="VergeOS installation media",
        )
        print(f"   CD-ROM created: key={cdrom_drive.key}, media={cdrom_drive.get('media_file')}")
    except ValueError as e:
        print(f"   Warning: Could not attach ISO - {e}")
        print("   Continuing without CD-ROM...")

    # Step 5: Add NIC on External network
    print("5. Adding NIC connected to External network...")
    try:
        nic = vm.nics.create(
            name="eth0",
            network="External",
            interface="virtio",
            description="Primary network interface",
        )
        print(f"   NIC created: key={nic.key}, network={nic.network_name}")
    except ValueError as e:
        print(f"   Warning: Could not create NIC on External network - {e}")
        print("   Trying to find available networks...")
        networks = client.networks.list(limit=5)
        if networks:
            net = networks[0]
            print(f"   Using network: {net.name}")
            nic = vm.nics.create(
                name="eth0",
                network=net.key,
                interface="virtio",
                description="Primary network interface",
            )
            print(f"   NIC created: key={nic.key}, network={nic.network_name}")
        else:
            print("   No networks available. VM created without NIC.")

    # Summary
    print()
    print("=" * 40)
    print("VM CREATION COMPLETE")
    print("=" * 40)
    print(f"VM Name:     {vm.name}")
    print(f"VM Key:      {vm.key}")
    print(f"CPU Cores:   {vm.get('cpu_cores')}")
    print(f"RAM:         {vm.get('ram')} MB")

    # List drives
    print("\nDrives:")
    for drive in vm.drives.list():
        print(f"  - {drive.name}: {drive.size_gb}GB ({drive.media_display})")

    # List NICs
    print("\nNICs:")
    for nic in vm.nics.list():
        print(f"  - {nic.name}: {nic.network_name} ({nic.interface_display})")

    print()
    print(f"Web Console: https://{client.host}/#/vm-console/{vm.key}")

    return vm.key


def cleanup_vm(client: VergeClient, vm_key: int) -> None:
    """Delete a VM and all its resources.

    Args:
        client: Connected VergeClient instance.
        vm_key: The VM $key to delete.
    """
    print()
    print("=" * 40)
    print("CLEANUP")
    print("=" * 40)

    try:
        vm = client.vms.get(vm_key)
        print(f"Deleting VM: {vm.name} (key={vm_key})")

        # Power off if running
        if vm.is_running:
            print("  Powering off VM...")
            vm.power_off(force=True)
            time.sleep(2)

        # Delete the VM
        client.vms.delete(vm_key)
        print("  VM deleted successfully.")

    except NotFoundError:
        print(f"  VM {vm_key} not found (already deleted?).")


def main() -> int:
    """Main entry point."""
    import os

    print("=" * 40)
    print("pyvergeos CreateVM Example")
    print("=" * 40)
    print()

    # Configuration from environment variables
    host = os.environ.get("VERGE_HOST", "")
    if not host:
        print("Error: VERGE_HOST environment variable not set")
        return 1

    vm_name = "pstest-001"

    # Connect to VergeOS
    print(f"Connecting to {host}...")
    try:
        with VergeClient.from_env() as client:
            print(f"Connected! VergeOS version: {client.version}")
            print()

            # Check if VM already exists
            try:
                existing = client.vms.get(name=vm_name)
                print(f"VM '{vm_name}' already exists (key={existing.key}).")
                print("Cleaning up existing VM first...")
                cleanup_vm(client, existing.key)
                print()
            except NotFoundError:
                pass  # VM doesn't exist, proceed with creation

            # Create the VM
            vm_key = create_configured_vm(client, vm_name)

            # Wait a moment
            print("\nWaiting 5 seconds before cleanup...")
            time.sleep(5)

            # Clean up
            cleanup_vm(client, vm_key)

            print()
            print("Example completed successfully!")
            return 0

    except VergeError as e:
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
