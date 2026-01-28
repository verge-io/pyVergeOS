#!/usr/bin/env python3
"""Comprehensive tenant management example.

This example demonstrates the proper tenant creation workflow:
1. Creating a tenant (shell)
2. Allocating compute nodes (CPU/RAM)
3. Allocating storage
4. Setting UI IP address
5. Sending files to the tenant (ISOs, disk images)
6. Sharing VMs with the tenant
7. Adding network blocks and external IPs for the tenant
8. Managing tenant isolation
9. Refreshing network rules
10. Cleanup (optional)

Prerequisites:
- VergeOS system with External and VLAN55 networks
- verge-io-install-26.0.1.2.iso file available
- VM named "123" exists

Usage:
    python tenant_management.py              # Create tenant, leave in place
    python tenant_management.py --cleanup    # Create tenant, then clean up
"""

import argparse
import os
import sys
import time

from pyvergeos import VergeClient
from pyvergeos.exceptions import APIError, ConflictError, NotFoundError


def refresh_network(client: VergeClient, network_name: str) -> None:
    """Refresh a network to apply pending rule changes.

    Args:
        client: VergeClient instance.
        network_name: Name of the network to refresh.
    """
    try:
        network = client.networks.get(name=network_name)
        client._request(
            "POST",
            "vnet_actions",
            json_data={"vnet": network.key, "action": "refresh"},
        )
        print(f"  Refreshed {network_name} network (key={network.key})")
    except NotFoundError:
        print(f"  Network '{network_name}' not found, skipping refresh")
    except APIError as e:
        print(f"  Failed to refresh {network_name}: {e}")


def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Comprehensive tenant management example for pyvergeos"
    )
    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="Clean up all created resources after demonstration",
    )
    args = parser.parse_args()

    # Configuration - modify these values as needed
    TENANT_NAME = "example-tenant"
    UI_IP = "192.168.10.79"
    UI_NETWORK = "External"

    # External IPs for the tenant on VLAN55
    EXTERNAL_NETWORK = "VLAN55"
    EXTERNAL_IPS = [
        "192.168.50.100",
        "192.168.50.101",
        "192.168.50.102",
        "192.168.50.103",
        "192.168.50.104",
        "192.168.50.105",
    ]

    # Network block for tenant (covers the external IPs)
    NETWORK_BLOCK_CIDR = "192.168.50.100/29"  # Covers .100-.107

    # Files and VMs to share
    ISO_NAME = "verge-io-install-26.0.1.2.iso"
    VM_TO_SHARE = "123"

    # Connect to VergeOS
    # You can also use environment variables: VERGE_HOST, VERGE_USERNAME, VERGE_PASSWORD
    host = os.environ.get("VERGE_HOST", "192.168.10.75")
    username = os.environ.get("VERGE_USERNAME", "admin")
    password = os.environ.get("VERGE_PASSWORD")

    if not password:
        print("Error: VERGE_PASSWORD environment variable required")
        sys.exit(1)

    print(f"Connecting to VergeOS at {host}...")
    client = VergeClient(
        host=host,
        username=username,
        password=password,
        verify_ssl=False,
    )
    print(f"Connected to {client.cloud_name} at {client.host} (VergeOS {client.version})")

    tenant = None

    try:
        # Step 1: Create the tenant (shell)
        print(f"\n1. Creating tenant '{TENANT_NAME}'...")
        try:
            tenant = client.tenants.create(
                name=TENANT_NAME,
                description="Example tenant created by pyvergeos",
                password="TenantAdmin123!",
                expose_cloud_snapshots=True,
                allow_branding=False,
            )
            print(f"  Created tenant: {tenant.name} (key={tenant.key})")
        except ConflictError:
            print(f"  Tenant '{TENANT_NAME}' already exists, retrieving...")
            tenant = client.tenants.get(name=TENANT_NAME)
            print(f"  Found existing tenant: {tenant.name} (key={tenant.key})")

        # Step 2: Allocate compute node (CPU/RAM)
        print("\n2. Allocating compute node to tenant...")
        existing_nodes = tenant.nodes.list()
        if not existing_nodes:
            node = tenant.nodes.create(
                cpu_cores=4,
                ram_gb=16,
                cluster=1,
            )
            print(f"  Created node: {node.name} - {node.cpu_cores} cores, {node.ram_gb} GB RAM")
        else:
            node = existing_nodes[0]
            print(
                f"  Node already exists: {node.name} - {node.cpu_cores} cores, {node.ram_gb} GB RAM"
            )

        # Step 3: Allocate storage (Tier 1)
        print("\n3. Allocating storage to tenant...")
        existing_storage = tenant.storage.list()
        if not any(s.tier == 1 for s in existing_storage):
            storage = tenant.storage.create(tier=1, provisioned_gb=50)
            print(f"  Allocated {storage.provisioned_gb} GB on {storage.tier_name}")
        else:
            print("  Tier 1 storage already allocated")

        # Step 4: Set the UI address
        print(f"\n4. Setting UI address to {UI_IP} on {UI_NETWORK}...")
        try:
            tenant.set_ui_ip(UI_IP, UI_NETWORK)
            tenant = tenant.refresh()
            print(f"  UI address set: {tenant.ui_address_ip}")
        except (ConflictError, APIError) as e:
            print(f"  UI IP may already be assigned: {e}")
            tenant = tenant.refresh()
            if tenant.ui_address_ip:
                print(f"  Current UI address: {tenant.ui_address_ip}")

        # Step 5: Add network block on VLAN55
        print(f"\n5. Adding network block {NETWORK_BLOCK_CIDR} on {EXTERNAL_NETWORK}...")
        try:
            block = tenant.network_blocks.create(
                cidr=NETWORK_BLOCK_CIDR,
                network_name=EXTERNAL_NETWORK,
                description="External access block",
            )
            print(f"  Created network block: {block.cidr} on {block.network_name}")
        except (ConflictError, APIError) as e:
            print(f"  Network block may already exist or error: {e}")

        # Step 6: Add external IPs on VLAN55
        print(f"\n6. Adding external IPs on {EXTERNAL_NETWORK}...")
        vlan55 = client.networks.get(name=EXTERNAL_NETWORK)
        for ip in EXTERNAL_IPS:
            try:
                ext_ip = tenant.external_ips.create(
                    ip=ip,
                    network=vlan55.key,
                    hostname=f"tenant-ext-{ip.split('.')[-1]}",
                    description="External tenant IP",
                )
                print(f"  Added external IP: {ext_ip.ip_address}")
            except (ConflictError, APIError) as e:
                print(f"  Skipping {ip}: {e}")

        # Step 7: Send files to tenant
        print("\n7. Sending files to tenant...")
        try:
            iso_file = client.files.get(name=ISO_NAME)
            tenant.send_file(iso_file.key)
            print(f"  Sent file: {iso_file.name}")
        except NotFoundError:
            print(f"  File '{ISO_NAME}' not found, skipping")
        except ConflictError:
            print(f"  File '{ISO_NAME}' already shared with tenant")

        # Step 8: Share VM with tenant
        print(f"\n8. Sharing VM '{VM_TO_SHARE}' with tenant...")
        try:
            vm = client.vms.get(name=VM_TO_SHARE)
            shared_obj = client.shared_objects.create(
                tenant_key=tenant.key,
                vm_key=vm.key,
                name=f"Shared-{vm.name}",
                description=f"VM {vm.name} shared with {tenant.name}",
            )
            print(f"  Shared VM: {vm.name} as '{shared_obj.name}'")
        except NotFoundError:
            print(f"  VM '{VM_TO_SHARE}' not found, skipping")
        except (ConflictError, APIError) as e:
            print(f"  Could not share VM: {e}")

        # Step 9: Demonstrate isolation
        print("\n9. Demonstrating isolation controls...")
        print(f"  Current isolation status: {tenant.is_isolated}")

        # Enable isolation
        tenant.enable_isolation()
        tenant = tenant.refresh()
        print(f"  After enable_isolation(): {tenant.is_isolated}")

        # Disable isolation
        tenant.disable_isolation()
        tenant = tenant.refresh()
        print(f"  After disable_isolation(): {tenant.is_isolated}")

        # Step 10: Refresh networks to apply pending rules
        print("\n10. Refreshing networks to apply pending rules...")
        refresh_network(client, UI_NETWORK)
        refresh_network(client, EXTERNAL_NETWORK)

        # Step 11: Show tenant summary
        print("\n11. Tenant Summary:")
        tenant = tenant.refresh()
        print(f"  Name: {tenant.name}")
        print(f"  Status: {tenant.status}")
        print(f"  UI IP: {tenant.ui_address_ip}")
        print(f"  Isolated: {tenant.is_isolated}")

        nodes = tenant.nodes.list()
        if nodes:
            print("  Compute Nodes:")
            for n in nodes:
                print(f"    - {n.name}: {n.cpu_cores} cores, {n.ram_gb} GB RAM")

        storage_allocations = tenant.storage.list()
        if storage_allocations:
            print("  Storage:")
            for s in storage_allocations:
                print(f"    - {s.tier_name}: {s.provisioned_gb} GB")

        network_blocks = tenant.network_blocks.list()
        if network_blocks:
            print("  Network Blocks:")
            for b in network_blocks:
                print(f"    - {b.cidr} on {b.network_name}")

        ext_ips = tenant.external_ips.list()
        if ext_ips:
            print("  External IPs:")
            for ip in ext_ips:
                print(f"    - {ip.ip_address} on {ip.network_name}")

        shared_objs = client.shared_objects.list(tenant_key=tenant.key)
        if shared_objs:
            print("  Shared Objects:")
            for obj in shared_objs:
                print(f"    - {obj.name} ({obj.object_type})")

        print("\n" + "=" * 60)
        print("Tenant setup complete!")
        print(f"Access the tenant UI at: https://{tenant.ui_address_ip}")
        print("=" * 60)

        # Cleanup based on flag
        if args.cleanup:
            cleanup(client, tenant, UI_NETWORK, EXTERNAL_NETWORK)
        else:
            print("\nResources left in place. Run with --cleanup to remove them.")

    except Exception as e:
        print(f"\nError: {e}")
        raise

    finally:
        client.disconnect()
        print("\nDisconnected from VergeOS")


def cleanup(
    client: VergeClient,
    tenant,
    ui_network: str,
    external_network: str,
) -> None:
    """Clean up all created resources.

    Args:
        client: VergeClient instance.
        tenant: Tenant object to clean up.
        ui_network: Name of the UI network (for refresh after cleanup).
        external_network: Name of the external network (for refresh after cleanup).
    """
    print("\nCleaning up resources...")

    if tenant:
        # Remove shared objects
        print("  Removing shared objects...")
        for obj in client.shared_objects.list(tenant_key=tenant.key):
            try:
                client.shared_objects.delete(obj.key)
                print(f"    Removed: {obj.name}")
            except Exception as e:
                print(f"    Failed to remove {obj.name}: {e}")

        # Remove external IPs
        print("  Removing external IPs...")
        for ip in tenant.external_ips.list():
            try:
                tenant.external_ips.delete(ip.key)
                print(f"    Removed: {ip.ip_address}")
            except Exception as e:
                print(f"    Failed to remove {ip.ip_address}: {e}")

        # Remove network blocks
        print("  Removing network blocks...")
        for block in tenant.network_blocks.list():
            try:
                tenant.network_blocks.delete(block.key)
                print(f"    Removed: {block.cidr}")
            except Exception as e:
                print(f"    Failed to remove {block.cidr}: {e}")

        # Remove storage
        print("  Removing storage allocations...")
        for storage in tenant.storage.list():
            try:
                tenant.storage.delete(storage.key)
                print(f"    Removed: {storage.tier_name}")
            except Exception as e:
                print(f"    Failed to remove {storage.tier_name}: {e}")

        # Remove nodes
        print("  Removing compute nodes...")
        for node in tenant.nodes.list():
            try:
                tenant.nodes.delete(node.key)
                print(f"    Removed: {node.name}")
            except Exception as e:
                print(f"    Failed to remove {node.name}: {e}")

        # Power off tenant network if running
        vnet_key = tenant.get("vnet")
        if vnet_key:
            print("  Powering off tenant network...")
            try:
                client._request(
                    "POST",
                    "vnet_actions",
                    json_data={"vnet": vnet_key, "action": "poweroff"},
                )
                time.sleep(2)
            except Exception:
                pass

        # Delete tenant
        print(f"  Deleting tenant '{tenant.name}'...")
        try:
            client.tenants.delete(tenant.key)
            print("    Tenant deleted")
        except Exception as e:
            print(f"    Failed to delete tenant: {e}")

    # Refresh networks after cleanup to apply rule changes
    print("  Refreshing networks after cleanup...")
    refresh_network(client, ui_network)
    refresh_network(client, external_network)

    print("Cleanup complete!")


if __name__ == "__main__":
    main()
