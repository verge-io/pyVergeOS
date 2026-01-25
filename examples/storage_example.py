#!/usr/bin/env python3
"""Example: Storage and File Operations

This example demonstrates:
- Listing and querying files in the media catalog
- Filtering files by type (ISO, QCOW2, etc.)
- Viewing storage tier information
- Getting vSAN cluster status
- Storage capacity analysis

Prerequisites:
- VergeOS system with files in the media catalog
- Valid credentials with read access to files and storage
"""

from pyvergeos import VergeClient


def main() -> None:
    # Connect to VergeOS using environment variables
    # Set: VERGE_HOST, VERGE_USERNAME, VERGE_PASSWORD, VERGE_VERIFY_SSL
    client = VergeClient.from_env()

    print("=" * 60)
    print("Storage and File Operations Example")
    print("=" * 60)

    # --- File Operations ---
    print("\n--- Media Catalog Files ---")
    files = client.files.list()
    print(f"Total files in catalog: {len(files)}")

    # Show file type summary
    type_counts: dict[str, int] = {}
    for f in files:
        type_counts[f.file_type] = type_counts.get(f.file_type, 0) + 1

    print("\nFile types:")
    for file_type, count in sorted(type_counts.items()):
        print(f"  {file_type}: {count} files")

    # --- ISO Files ---
    print("\n--- ISO Files ---")
    isos = client.files.list(file_type="iso")
    if isos:
        for iso in isos:
            print(f"  {iso.name}")
            print(f"    Size: {iso.size_gb:.2f} GB")
            print(f"    Tier: {iso.preferred_tier}")
            if iso.modified:
                print(f"    Modified: {iso.modified.strftime('%Y-%m-%d %H:%M')}")
    else:
        print("  No ISO files found")

    # --- Disk Images ---
    print("\n--- Disk Images ---")
    images = client.files.list(file_type=["qcow2", "vmdk", "vhdx", "raw"])
    if images:
        # Show first 5
        for img in images[:5]:
            print(f"  {img.name}: {img.size_gb:.1f} GB ({img.type_display})")
        if len(images) > 5:
            print(f"  ... and {len(images) - 5} more")
    else:
        print("  No disk images found")

    # --- Get a specific file ---
    if isos:
        print("\n--- Get Specific File ---")
        iso = client.files.get(name=isos[0].name)
        print(f"File: {iso.name}")
        print(f"  Type: {iso.type_display}")
        print(f"  Size: {iso.size_bytes:,} bytes ({iso.size_gb:.3f} GB)")
        print(f"  Allocated: {iso.allocated_gb:.3f} GB")
        print(f"  Used on disk: {iso.used_gb:.3f} GB")
        print(f"  Storage tier: {iso.preferred_tier}")
        print(f"  Created by: {iso.creator}")

    # --- Storage Tiers ---
    print("\n--- Storage Tiers ---")
    tiers = client.storage_tiers.list()
    for tier in sorted(tiers, key=lambda t: t.tier):
        print(f"\nTier {tier.tier}: {tier.description or 'No description'}")
        print(f"  Capacity: {tier.capacity_gb:,.1f} GB")
        print(f"  Used: {tier.used_gb:,.1f} GB ({tier.used_percent}%)")
        print(f"  Free: {tier.free_gb:,.1f} GB")
        print(f"  Allocated: {tier.allocated_gb:,.1f} GB")
        if tier.dedupe_ratio > 1.0:
            print(f"  Dedupe ratio: {tier.dedupe_ratio:.2f}x ({tier.dedupe_savings_percent:.1f}% savings)")
        if tier.read_ops or tier.write_ops:
            print(f"  IOPS: {tier.read_ops} read, {tier.write_ops} write")

    # --- Storage Summary ---
    print("\n--- Storage Summary ---")
    summary = client.storage_tiers.get_summary()
    print(f"Total tiers: {summary['tier_count']}")
    print(f"Total capacity: {summary['total_capacity_gb']:,.1f} GB")
    print(f"Total used: {summary['total_used_gb']:,.1f} GB")
    print(f"Total free: {summary['total_free_gb']:,.1f} GB")
    print(f"Overall usage: {summary['used_percent']:.1f}%")

    # --- vSAN Status ---
    print("\n--- vSAN Cluster Status ---")
    vsan_status = client.clusters.vsan_status(include_tiers=True)
    for status in vsan_status:
        print(f"\nCluster: {status.cluster_name}")
        print(f"  Health: {status.health_status}")
        print(f"  Status: {status.status}")
        print(f"  Nodes: {status.online_nodes}/{status.total_nodes} online")
        print(f"  Running VMs: {status.running_machines}")
        print(f"  RAM: {status.used_ram_gb:.1f}/{status.online_ram_gb:.1f} GB ({status.ram_used_percent}%)")
        print(f"  CPU Cores: {status.used_cores}/{status.online_cores} ({status.core_used_percent}%)")

        if status.tiers:
            print("  Tier Status:")
            for tier in status.tiers:
                print(f"    Tier {tier['tier']}: {tier['used_percent']:.1f}% used")

    # --- High Usage Tiers Alert ---
    print("\n--- Storage Alerts ---")
    high_usage_tiers = [t for t in tiers if t.used_percent > 80]
    if high_usage_tiers:
        print("WARNING: The following tiers are over 80% usage:")
        for tier in high_usage_tiers:
            print(f"  Tier {tier.tier}: {tier.used_percent}% used")
    else:
        print("All tiers are below 80% usage - storage is healthy")

    # Cleanup
    client.disconnect()
    print("\n" + "=" * 60)
    print("Example completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()
