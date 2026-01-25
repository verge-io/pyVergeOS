#!/usr/bin/env python3
"""Example: Virtual Machine management with pyvergeos.

This example demonstrates VM operations including:
- Listing and filtering VMs
- Power management
- Getting VM details
- Console access
"""

import time

from pyvergeos import VergeClient
from pyvergeos.exceptions import NotFoundError


def basic_vm_operations() -> None:
    """Demonstrate basic VM operations."""
    print("=== Basic VM Operations ===")

    with VergeClient(
        host="192.168.1.100",
        username="admin",
        password="your-password",
        verify_ssl=False,
    ) as client:
        # List all VMs (excludes snapshots by default)
        vms = client.vms.list(limit=10)
        print(f"Found {len(vms)} VMs")

        for vm in vms[:5]:
            print(f"  - {vm.name}")
            print(f"    Key: {vm.key}")
            print(f"    Status: {vm.status}")
            print(f"    Running: {vm.is_running}")
            print(f"    Node: {vm.node_name}")
            print(f"    Cluster: {vm.cluster_name}")
            print(f"    RAM: {vm.get('ram')}MB")
            print(f"    CPU: {vm.get('cpu_cores')} cores")


def list_by_status() -> None:
    """List VMs by power state."""
    print("\n=== List by Status ===")

    with VergeClient(
        host="192.168.1.100",
        username="admin",
        password="your-password",
        verify_ssl=False,
    ) as client:
        # List running VMs
        running = client.vms.list_running()
        print(f"Running VMs ({len(running)}):")
        for vm in running[:5]:
            print(f"  - {vm.name} on {vm.node_name}")

        # List stopped VMs
        stopped = client.vms.list_stopped()
        print(f"Stopped VMs ({len(stopped)}):")
        for vm in stopped[:5]:
            print(f"  - {vm.name}")


def get_vm_by_name() -> None:
    """Get a specific VM by name."""
    print("\n=== Get VM by Name ===")

    with VergeClient(
        host="192.168.1.100",
        username="admin",
        password="your-password",
        verify_ssl=False,
    ) as client:
        try:
            vm = client.vms.get(name="WebServer01")
            print(f"Found VM: {vm.name}")
            print(f"  Key: {vm.key}")
            print(f"  Status: {vm.status}")
        except NotFoundError:
            print("VM 'WebServer01' not found")


def power_management() -> None:
    """Demonstrate VM power management."""
    print("\n=== Power Management ===")

    with VergeClient(
        host="192.168.1.100",
        username="admin",
        password="your-password",
        verify_ssl=False,
    ) as client:
        vm = client.vms.get(name="TestVM")

        if vm.is_running:
            print(f"VM {vm.name} is running, powering off...")
            vm.power_off()  # Graceful ACPI shutdown
            time.sleep(5)

            # Force power off if still running
            vm = client.vms.get(vm.key)
            if vm.is_running:
                print("VM still running, forcing power off...")
                vm.power_off(force=True)  # Immediate termination
        else:
            print(f"VM {vm.name} is stopped, powering on...")
            vm.power_on()  # Can optionally specify preferred_node

        # Wait and check status
        time.sleep(3)
        vm = client.vms.get(vm.key)
        print(f"VM is now: {vm.status}")


def console_access() -> None:
    """Get console access information for a VM."""
    print("\n=== Console Access ===")

    with VergeClient(
        host="192.168.1.100",
        username="admin",
        password="your-password",
        verify_ssl=False,
    ) as client:
        vm = client.vms.get(name="TestVM")

        if not vm.is_running:
            print("VM must be running to access console")
            return

        console = vm.get_console_info()
        print(f"Console type: {console['console_type']}")
        print(f"Host: {console['host']}")
        print(f"Port: {console['port']}")
        print(f"Direct URL: {console['url']}")
        print(f"Web Console: {console['web_url']}")


def guest_operations() -> None:
    """Demonstrate guest operations (requires guest agent)."""
    print("\n=== Guest Operations ===")

    with VergeClient(
        host="192.168.1.100",
        username="admin",
        password="your-password",
        verify_ssl=False,
    ) as client:
        vm = client.vms.get(name="TestVM")

        if not vm.is_running:
            print("VM must be running")
            return

        if not vm.get("guest_agent"):
            print("VM doesn't have guest agent enabled")
            return

        # These operations send signals through the guest agent
        # vm.guest_shutdown()  # Graceful shutdown via guest OS
        # vm.guest_reboot()    # Reboot via guest OS

        print("Guest agent available for this VM")


def snapshot_and_clone() -> None:
    """Demonstrate snapshot and clone operations."""
    print("\n=== Snapshot and Clone ===")

    with VergeClient(
        host="192.168.1.100",
        username="admin",
        password="your-password",
        verify_ssl=False,
    ) as client:
        vm = client.vms.get(name="TestVM")

        # Take a snapshot
        print(f"Taking snapshot of {vm.name}...")
        result = vm.snapshot(
            name="my-snapshot",
            retention=86400 * 7,  # 7 days
            quiesce=False,
        )
        print(f"Snapshot result: {result}")

        # Clone the VM
        print(f"Cloning {vm.name}...")
        result = vm.clone(
            name="TestVM-Clone",
            preserve_macs=False,
        )
        print(f"Clone result: {result}")


if __name__ == "__main__":
    print("pyvergeos VM Examples")
    print("=" * 40)
    print()
    print("NOTE: Update host/credentials in this file before running.")
    print()

    # Uncomment the examples you want to run:
    # basic_vm_operations()
    # list_by_status()
    # get_vm_by_name()
    # power_management()
    # console_access()
    # guest_operations()
    # snapshot_and_clone()

    print("\nSee the code for examples of:")
    print("  - Listing and filtering VMs")
    print("  - Getting VMs by name or key")
    print("  - Power management (on/off/reset)")
    print("  - Console access information")
    print("  - Guest agent operations")
    print("  - Snapshots and cloning")
