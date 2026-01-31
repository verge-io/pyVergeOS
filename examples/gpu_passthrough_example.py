#!/usr/bin/env python3
"""Example: GPU Passthrough with pyvergeos.

This example demonstrates how to set up GPU passthrough for a VM:
1. Finding GPU/PCI devices on a node
2. Creating a resource group for host GPU passthrough
3. Creating a resource rule to include specific devices
4. Attaching the GPU device to a VM

Prerequisites:
    - VergeOS system with a GPU-equipped node
    - Environment variables configured
    - A VM to attach the GPU to (should be powered off)

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
    python gpu_passthrough_example.py
"""

from __future__ import annotations

import os
import sys

from pyvergeos import VergeClient
from pyvergeos.exceptions import NotFoundError


def check_environment() -> bool:
    """Check that required environment variables are set."""
    required = ["VERGE_HOST", "VERGE_USERNAME", "VERGE_PASSWORD"]
    missing = [var for var in required if not os.environ.get(var)]
    if missing:
        print("Error: Missing required environment variables:")
        for var in missing:
            print(f"  - {var}")
        print("\nSet them with:")
        print("  export VERGE_HOST=your-host")
        print("  export VERGE_USERNAME=admin")
        print("  export VERGE_PASSWORD=yourpassword")
        print("  export VERGE_VERIFY_SSL=false")
        return False
    return True


def list_node_gpus(client: VergeClient, node_name: str) -> None:
    """List all GPU-related devices on a node.

    Args:
        client: Connected VergeClient.
        node_name: Name of the node to inspect.
    """
    print(f"\n=== GPU Devices on {node_name} ===")

    try:
        node = client.nodes.get(name=node_name)
        print(f"Node: {node.name} (key={node.key})")
    except NotFoundError:
        print(f"Node '{node_name}' not found")
        return

    # List PCI devices that look like GPUs
    print("\nPCI Devices (potential GPUs):")
    pci_devices = node.pci_devices.list()
    gpu_devices = []
    for pci in pci_devices:
        desc = pci.get("name", "")
        vendor = pci.get("vendor", "")
        # Look for common GPU indicators
        if any(
            kw in desc.upper() or kw in vendor.upper()
            for kw in ["NVIDIA", "AMD", "VGA", "3D", "GPU", "RADEON", "GEFORCE"]
        ):
            gpu_devices.append(pci)
            print(f"  Key: {pci.key}")
            print(f"    Description: {desc}")
            print(f"    Vendor: {vendor}")
            print(f"    Slot: {pci.get('slot', 'N/A')}")
            print()

    if not gpu_devices:
        print("  No GPU devices found")

    # List host GPU devices (already configured for passthrough)
    print("\nHost GPU Devices (configured for passthrough):")
    host_gpus = node.host_gpu_devices.list()
    if host_gpus:
        for hgpu in host_gpus:
            print(f"  Key: {hgpu.key}")
            print(f"    Name: {hgpu.name}")
            print(f"    Status: {hgpu.status}")
            print(f"    Resource Group: {hgpu.resource_group_name}")
            print()
    else:
        print("  No host GPU devices configured")

    # List vGPU devices
    print("\nNVIDIA vGPU Devices:")
    vgpu_devices = node.vgpu_devices.list()
    if vgpu_devices:
        for vgpu in vgpu_devices:
            print(f"  Key: {vgpu.key}")
            print(f"    Name: {vgpu.name}")
            print(f"    Resource Group: {vgpu.resource_group_name}")
            print()
    else:
        print("  No vGPU devices configured")


def setup_gpu_passthrough(
    client: VergeClient,
    node_name: str,
    gpu_slot: str,
    resource_group_name: str,
) -> str | None:
    """Set up GPU passthrough by creating a resource group and rule.

    Uses PCI passthrough which is the appropriate method for VMs.
    For host GPU passthrough (physical nodes only), use create_host_gpu instead.

    Args:
        client: Connected VergeClient.
        node_name: Name of the node with the GPU.
        gpu_slot: PCI slot of the GPU (e.g., "01:00.0").
        resource_group_name: Name for the resource group.

    Returns:
        Resource group key (UUID) if successful, None otherwise.
    """
    print("\n=== Setting up GPU Passthrough ===")
    print(f"Node: {node_name}")
    print(f"GPU Slot: {gpu_slot}")
    print(f"Resource Group: {resource_group_name}")

    # Get the node
    try:
        node = client.nodes.get(name=node_name)
    except NotFoundError:
        print(f"Error: Node '{node_name}' not found")
        return None

    # Find the PCI device by slot
    pci_devices = node.pci_devices.list()
    target_gpu = None
    for pci in pci_devices:
        if pci.get("slot") == gpu_slot:
            target_gpu = pci
            break

    if not target_gpu:
        print(f"Error: No PCI device found at slot {gpu_slot}")
        return None

    print("\nFound GPU:")
    print(f"  Key: {target_gpu.key}")
    print(f"  Description: {target_gpu.get('name', 'N/A')}")
    print(f"  Vendor: {target_gpu.get('vendor', 'N/A')}")

    # Check if resource group already exists
    existing_groups = client.resource_groups.list(name=resource_group_name)
    if existing_groups:
        print(
            f"\nResource group '{resource_group_name}' already exists (key={existing_groups[0].key})"
        )
        return existing_groups[0].key

    # Create the resource group for PCI passthrough
    # Note: VMs use node_pci_devices for GPU passthrough
    # node_host_gpu_devices is only for physical node hosts
    print(f"\nCreating PCI resource group '{resource_group_name}'...")
    resource_group = client.resource_groups.create_pci(
        name=resource_group_name,
        description=f"PCI passthrough for {target_gpu.get('name', 'GPU')}",
        device_class="gpu",  # Classify as GPU for proper icon/categorization
        enabled=True,
    )
    print(f"Created resource group (key={resource_group.key})")

    # Create a resource rule to include the specific GPU
    print(f"\nCreating resource rule for slot {gpu_slot}...")
    rule = resource_group.rules.create(
        name=f"GPU at {gpu_slot}",
        filter_expression=f"slot eq '{gpu_slot}'",
        node=node.key,
        enabled=True,
    )
    print(f"Created resource rule (key={rule.key})")

    # Refresh the resource group to see updated device count
    resource_group = resource_group.refresh()
    print(f"\nResource group now has {resource_group.resource_count} device(s)")

    return resource_group.key


def attach_gpu_to_vm(
    client: VergeClient,
    vm_name: str,
    resource_group_key: str,
) -> bool:
    """Attach a GPU device to a VM via PCI passthrough.

    Args:
        client: Connected VergeClient.
        vm_name: Name of the VM.
        resource_group_key: Key (UUID) of the resource group with the GPU.

    Returns:
        True if successful, False otherwise.
    """
    print("\n=== Attaching GPU to VM ===")
    print(f"VM: {vm_name}")
    print(f"Resource Group Key: {resource_group_key}")

    # Get the VM
    try:
        vm = client.vms.get(name=vm_name)
    except NotFoundError:
        print(f"Error: VM '{vm_name}' not found")
        return False

    print(f"\nVM: {vm.name} (key={vm.key})")
    print(f"Status: {vm.status}")
    print(f"Running: {vm.is_running}")

    # Check if VM is stopped (recommended for adding GPU)
    if vm.is_running:
        print(
            "\nWarning: VM is running. It's recommended to stop the VM before adding GPU devices."
        )
        print("The device will be attached but may not be available until VM restart.")

    # Check existing devices
    print("\nCurrent devices on VM:")
    existing_devices = vm.devices.list()
    for dev in existing_devices:
        print(f"  {dev.name}: {dev.device_type} (key={dev.key})")
        rg_key = dev.get("resource_group")
        if rg_key and str(rg_key) == str(resource_group_key):
            print("    -> GPU already attached from this resource group!")
            return True

    if not existing_devices:
        print("  (no devices attached)")

    # Attach the GPU device via PCI passthrough
    # Note: VMs use create_pci, not create_host_gpu (which is for physical nodes only)
    print(f"\nAttaching PCI GPU from resource group {resource_group_key}...")
    device = vm.devices.create_pci(
        resource_group=resource_group_key,
        enabled=True,
        optional=False,  # VM requires this device to start
    )
    print(f"Created device: {device.name} (key={device.key})")
    print(f"Device type: {device.device_type}")
    print(f"Device status: {device.status}")

    return True


def list_vm_devices(client: VergeClient, vm_name: str) -> None:
    """List all devices attached to a VM.

    Args:
        client: Connected VergeClient.
        vm_name: Name of the VM.
    """
    print(f"\n=== Devices on VM '{vm_name}' ===")

    try:
        vm = client.vms.get(name=vm_name)
    except NotFoundError:
        print(f"VM '{vm_name}' not found")
        return

    devices = vm.devices.list()
    if not devices:
        print("No devices attached")
        return

    for device in devices:
        print(f"\nDevice: {device.name} (key={device.key})")
        print(f"  Type: {device.device_type}")
        print(f"  Enabled: {device.is_enabled}")
        print(f"  Optional: {device.is_optional}")
        print(f"  Status: {device.status}")
        print(f"  Resource Group: {device.resource_group_name}")

        # Show device type flags
        flags = []
        if device.is_gpu:
            flags.append("GPU")
        if device.is_vgpu:
            flags.append("vGPU")
        if device.is_host_gpu:
            flags.append("Host GPU")
        if device.is_tpm:
            flags.append("TPM")
        if device.is_usb:
            flags.append("USB")
        if device.is_pci:
            flags.append("PCI")
        if device.is_sriov:
            flags.append("SR-IOV")
        if flags:
            print(f"  Flags: {', '.join(flags)}")


def remove_gpu_from_vm(client: VergeClient, vm_name: str, device_name: str) -> bool:
    """Remove a GPU device from a VM.

    Args:
        client: Connected VergeClient.
        vm_name: Name of the VM.
        device_name: Name of the device to remove.

    Returns:
        True if successful, False otherwise.
    """
    print("\n=== Removing Device from VM ===")
    print(f"VM: {vm_name}")
    print(f"Device: {device_name}")

    try:
        vm = client.vms.get(name=vm_name)
    except NotFoundError:
        print(f"Error: VM '{vm_name}' not found")
        return False

    if vm.is_running:
        print("Warning: VM is running. Device removal may fail or require restart.")

    try:
        device = vm.devices.get(name=device_name)
    except NotFoundError:
        print(f"Error: Device '{device_name}' not found on VM")
        return False

    print(f"Removing device (key={device.key})...")
    device.delete()
    print("Device removed successfully")

    return True


def cleanup_resource_group(client: VergeClient, resource_group_name: str) -> bool:
    """Delete a resource group and its rules.

    Args:
        client: Connected VergeClient.
        resource_group_name: Name of the resource group to delete.

    Returns:
        True if successful, False otherwise.
    """
    print("\n=== Cleaning up Resource Group ===")
    print(f"Resource Group: {resource_group_name}")

    try:
        rg = client.resource_groups.get(name=resource_group_name)
    except NotFoundError:
        print(f"Resource group '{resource_group_name}' not found")
        return False

    # Delete rules first
    rules = rg.rules.list()
    for rule in rules:
        print(f"Deleting rule: {rule.name} (key={rule.key})")
        rule.delete()

    # Delete the resource group
    print(f"Deleting resource group (key={rg.key})...")
    rg.delete()
    print("Resource group deleted successfully")

    return True


def main() -> int:
    """Run the GPU passthrough example."""
    if not check_environment():
        return 1

    # Configuration - modify these for your environment
    NODE_NAME = "node2"  # Node with the GPU
    GPU_SLOT = "01:00.0"  # PCI slot of the GPU
    VM_NAME = "123"  # VM to attach the GPU to
    RESOURCE_GROUP_NAME = "RTX-A4500-Passthrough"

    try:
        with VergeClient.from_env() as client:
            print("Connected to VergeOS")
            print(f"Host: {os.environ.get('VERGE_HOST')}")

            # Step 1: List available GPUs on the node
            list_node_gpus(client, NODE_NAME)

            # Step 2: Set up GPU passthrough
            rg_key = setup_gpu_passthrough(
                client,
                node_name=NODE_NAME,
                gpu_slot=GPU_SLOT,
                resource_group_name=RESOURCE_GROUP_NAME,
            )

            if rg_key is None:
                print("\nFailed to set up GPU passthrough")
                return 1

            # Step 3: Attach the GPU to the VM
            success = attach_gpu_to_vm(client, VM_NAME, rg_key)
            if not success:
                print("\nFailed to attach GPU to VM")
                return 1

            # Step 4: Show final device list
            list_vm_devices(client, VM_NAME)

            print("\n" + "=" * 50)
            print("GPU passthrough setup complete!")
            print(f"VM '{VM_NAME}' now has access to the GPU in slot {GPU_SLOT}")
            print("Start the VM to use the GPU.")
            print("=" * 50)

            # Uncomment to clean up:
            # remove_gpu_from_vm(client, VM_NAME, "Host GPU")
            # cleanup_resource_group(client, RESOURCE_GROUP_NAME)

    except Exception as e:
        print(f"\nError: {e}")
        import traceback

        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
