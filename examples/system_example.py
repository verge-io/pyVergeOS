#!/usr/bin/env python3
"""Example demonstrating system operations in VergeOS.

This example shows how to:
- Get system settings
- View license information
- Retrieve system statistics (dashboard)
- Generate a system inventory (like RVtools for VMware)

Requirements:
    - A running VergeOS system
    - Environment variables set (VERGE_HOST, VERGE_USERNAME, VERGE_PASSWORD)
      OR modify the connection parameters below
"""

from __future__ import annotations

import os

from pyvergeos import VergeClient
from pyvergeos.exceptions import NotFoundError


def main() -> None:
    # Connect using environment variables or direct credentials
    host = os.environ.get("VERGE_HOST")
    username = os.environ.get("VERGE_USERNAME")
    password = os.environ.get("VERGE_PASSWORD")

    if not all([host, username, password]):
        print("Please set VERGE_HOST, VERGE_USERNAME, VERGE_PASSWORD environment variables")
        print("Or modify this script with your credentials")
        return

    with VergeClient(
        host=host,  # type: ignore[arg-type]
        username=username,
        password=password,
        verify_ssl=False,
    ) as client:
        print(f"Connected to {client.cloud_name} (VergeOS {client.version})")
        print("=" * 60)

        # =========================================================
        # System Settings
        # =========================================================
        print("\n--- System Settings ---\n")

        # List all settings
        settings = client.system.settings.list()
        print(f"Total settings: {len(settings)}")

        # Show first few settings
        print("\nSample settings:")
        for setting in settings[:5]:
            modified = "(modified)" if setting.is_modified else ""
            print(f"  {setting.key}: {setting.value!r} {modified}")

        # Get a specific setting
        try:
            cloud_name = client.system.settings.get("cloud_name")
            print(f"\nCloud name setting: {cloud_name.value}")
        except NotFoundError:
            print("Could not find cloud_name setting")

        # Filter settings by key pattern
        net_settings = client.system.settings.list(key_contains="net_")
        print(f"\nNetwork-related settings: {len(net_settings)}")
        for s in net_settings[:3]:
            print(f"  {s.key}: {s.value}")

        # =========================================================
        # Licenses
        # =========================================================
        print("\n--- Licenses ---\n")

        licenses = client.system.licenses.list()
        print(f"Total licenses: {len(licenses)}")

        for lic in licenses:
            status = "VALID" if lic.is_valid else "EXPIRED/INVALID"
            print(f"\n  {lic.name}:")
            print(f"    Status: {status}")
            if lic.valid_from:
                print(f"    Valid from: {lic.valid_from}")
            if lic.valid_until:
                print(f"    Valid until: {lic.valid_until}")
            print(f"    Auto-renewal: {lic.auto_renewal}")
            print(f"    Allow branding: {lic.allow_branding}")
            if lic.features:
                print(f"    Features: {lic.features}")

        # =========================================================
        # System Statistics (Dashboard)
        # =========================================================
        print("\n--- System Statistics ---\n")

        stats = client.system.statistics()

        print("Resource Summary:")
        print(f"  VMs: {stats.vms_online}/{stats.vms_total} online")
        if stats.vms_warning:
            print(f"    - {stats.vms_warning} with warnings")
        if stats.vms_error:
            print(f"    - {stats.vms_error} with errors")

        print(f"  Tenants: {stats.tenants_online}/{stats.tenants_total} online")
        print(f"  Networks: {stats.networks_online}/{stats.networks_total} online")
        print(f"  Nodes: {stats.nodes_online}/{stats.nodes_total} online")
        print(f"  Clusters: {stats.clusters_online}/{stats.clusters_total} online")
        print(f"  Storage Tiers: {stats.storage_tiers_total}")
        print(f"  Users: {stats.users_enabled}/{stats.users_total} enabled")
        print(f"  Groups: {stats.groups_enabled}/{stats.groups_total} enabled")

        print("\nAlarms:")
        print(f"  Total active: {stats.alarms_total}")
        print(f"  Warnings: {stats.alarms_warning}")
        print(f"  Errors/Critical: {stats.alarms_error}")

        # Get statistics as dictionary
        stats_dict = stats.to_dict()
        print(f"\nStatistics as dict has {len(stats_dict)} categories")

        # =========================================================
        # System Inventory (like RVtools)
        # =========================================================
        print("\n--- System Inventory ---\n")

        inventory = client.system.inventory()
        print(f"Generated at: {inventory.generated_at}")

        # VM Inventory
        print(f"\nVirtual Machines ({len(inventory.vms)}):")
        print(f"  {'Name':<30} {'State':<10} {'CPU':<5} {'RAM':<10} {'OS':<15}")
        print("  " + "-" * 75)
        for vm in inventory.vms[:10]:  # Show first 10
            print(
                f"  {vm.name:<30} {vm.power_state:<10} {vm.cpu_cores:<5} "
                f"{vm.ram_gb:.1f} GB     {vm.os_family:<15}"
            )
        if len(inventory.vms) > 10:
            print(f"  ... and {len(inventory.vms) - 10} more VMs")

        # Network Inventory
        print(f"\nNetworks ({len(inventory.networks)}):")
        print(f"  {'Name':<25} {'Type':<15} {'State':<10} {'Address':<20}")
        print("  " + "-" * 75)
        for net in inventory.networks[:10]:
            print(
                f"  {net.name:<25} {net.network_type:<15} "
                f"{net.power_state:<10} {net.network_address:<20}"
            )
        if len(inventory.networks) > 10:
            print(f"  ... and {len(inventory.networks) - 10} more networks")

        # Storage Inventory
        print(f"\nStorage Tiers ({len(inventory.storage)}):")
        print(f"  {'Tier':<10} {'Used':<15} {'Capacity':<15} {'% Used':<10}")
        print("  " + "-" * 55)
        for tier in inventory.storage:
            print(
                f"  Tier {tier.tier:<4} {tier.used_gb:>10.1f} GB   "
                f"{tier.capacity_gb:>10.1f} GB   {tier.used_percent:>6.1f}%"
            )

        # Node Inventory
        print(f"\nNodes ({len(inventory.nodes)}):")
        print(f"  {'Name':<20} {'Status':<15} {'Cores':<10} {'RAM':<15} {'Cluster':<20}")
        print("  " + "-" * 85)
        for node in inventory.nodes:
            print(
                f"  {node.name:<20} {node.status:<15} {node.cores:<10} "
                f"{node.ram_gb:.1f} GB        {node.cluster:<20}"
            )

        # Cluster Inventory
        print(f"\nClusters ({len(inventory.clusters)}):")
        for cluster in inventory.clusters:
            print(f"  {cluster.name}: {cluster.online_nodes}/{cluster.total_nodes} nodes online")

        # Tenant Inventory
        print(f"\nTenants ({len(inventory.tenants)}):")
        for tenant in inventory.tenants:
            status = "running" if tenant.is_running else "stopped"
            print(f"  {tenant.name}: {status}")

        # Inventory Summary
        print("\n--- Inventory Summary ---\n")
        summary = inventory.summary
        print(f"  VMs: {summary['vms_running']}/{summary['vms_total']} running")
        print(f"  Total CPU cores: {summary['total_cpu_cores']}")
        print(f"  Total RAM: {summary['total_ram_gb']:.1f} GB")
        print(f"  Networks: {summary['networks_running']}/{summary['networks_total']} running")
        print(f"  Storage capacity: {summary['storage_capacity_gb']:.1f} GB")
        print(f"  Storage used: {summary['storage_used_gb']:.1f} GB")
        print(f"  Nodes: {summary['nodes_total']}")
        print(f"  Clusters: {summary['clusters_total']}")
        print(f"  Tenants: {summary['tenants_running']}/{summary['tenants_total']} running")

        # =========================================================
        # Partial Inventory (for performance)
        # =========================================================
        print("\n--- Partial Inventory Example ---\n")

        # Get only VMs and storage (faster for large environments)
        partial_inv = client.system.inventory(
            include_vms=True,
            include_networks=False,
            include_storage=True,
            include_nodes=False,
            include_clusters=False,
            include_tenants=False,
        )
        print(f"Partial inventory: {len(partial_inv.vms)} VMs, {len(partial_inv.storage)} storage tiers")
        print(f"Excluded: networks={len(partial_inv.networks)}, nodes={len(partial_inv.nodes)}")

        print("\n" + "=" * 60)
        print("System example complete!")


if __name__ == "__main__":
    main()
