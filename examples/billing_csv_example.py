#!/usr/bin/env python3
"""Generate a billing CSV report from VergeOS usage data.

This example demonstrates how to:
1. Fetch billing records from VergeOS
2. Apply pricing to resource usage
3. Export the data to a CSV file

The script calculates costs based on configurable hourly rates for:
- CPU cores
- RAM (per GB)
- Storage tiers 0-5 (per GB)

Usage:
    # Set credentials via environment variables
    export VERGE_HOST="192.168.10.75"
    export VERGE_USERNAME="admin"
    export VERGE_PASSWORD="your-password"

    # Generate billing CSV for last 30 days (default)
    python billing_csv_example.py

    # Specify custom date range
    python billing_csv_example.py --days 7

    # Custom output file
    python billing_csv_example.py --output my_billing.csv
"""

import argparse
import csv
import os
import sys
from datetime import datetime, timedelta, timezone

from pyvergeos import VergeClient

# Pricing configuration (hourly rates in USD)
PRICING = {
    "cpu_per_core": 0.02,  # $0.02/core/hour
    "ram_per_gb": 0.01,  # $0.01/GB/hour
    "storage_tier_0": 0.0001,  # $0.0001/GB/hour (NVMe/fastest)
    "storage_tier_1": 0.00008,  # $0.00008/GB/hour (SSD)
    "storage_tier_2": 0.00005,  # $0.00005/GB/hour (HDD)
    "storage_tier_3": 0.00003,  # $0.00003/GB/hour (Archive)
    "storage_tier_4": 0.00002,  # $0.00002/GB/hour (Cold)
    "storage_tier_5": 0.00001,  # $0.00001/GB/hour (Glacier)
    "gpu": 0.50,  # $0.50/GPU/hour
    "vgpu": 0.25,  # $0.25/vGPU/hour
}


def calculate_record_cost(record, hours: float = 1.0) -> dict:
    """Calculate costs for a single billing record.

    Args:
        record: BillingRecord object.
        hours: Number of hours this record represents.

    Returns:
        Dictionary with itemized costs and total.
    """
    # CPU cost (based on used cores)
    cpu_cost = record.used_cores * PRICING["cpu_per_core"] * hours

    # RAM cost (based on used RAM in GB)
    ram_cost = record.used_ram_gb * PRICING["ram_per_gb"] * hours

    # Storage costs per tier
    storage_costs = {}
    total_storage_cost = 0.0
    for tier in range(6):
        stats = record.get_tier_stats(tier)
        if stats:
            tier_gb = stats.get("used", 0) / (1024**3)  # Convert bytes to GB
            tier_cost = tier_gb * PRICING[f"storage_tier_{tier}"] * hours
            storage_costs[f"tier_{tier}"] = tier_cost
            total_storage_cost += tier_cost

    # GPU costs
    gpu_cost = record.gpus * PRICING["gpu"] * hours
    vgpu_cost = record.vgpus * PRICING["vgpu"] * hours

    total = cpu_cost + ram_cost + total_storage_cost + gpu_cost + vgpu_cost

    return {
        "cpu_cost": cpu_cost,
        "ram_cost": ram_cost,
        "storage_costs": storage_costs,
        "total_storage_cost": total_storage_cost,
        "gpu_cost": gpu_cost,
        "vgpu_cost": vgpu_cost,
        "total": total,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Generate a billing CSV report from VergeOS usage data"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="Number of days to include in report (default: 30)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="billing_report.csv",
        help="Output CSV file path (default: billing_report.csv)",
    )
    args = parser.parse_args()

    # Get credentials from environment
    host = os.environ.get("VERGE_HOST")
    username = os.environ.get("VERGE_USERNAME")
    password = os.environ.get("VERGE_PASSWORD")

    if not all([host, username, password]):
        print("Error: Missing required environment variables")
        print("Please set: VERGE_HOST, VERGE_USERNAME, VERGE_PASSWORD")
        sys.exit(1)

    # Calculate date range
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(days=args.days)

    print(f"Connecting to VergeOS at {host}...")
    client = VergeClient(
        host=host,
        username=username,
        password=password,
        verify_ssl=False,
    )
    print(f"Connected to {client.cloud_name} (VergeOS {client.version})")

    try:
        # Fetch billing records
        print(f"\nFetching billing records from {start_time.date()} to {end_time.date()}...")
        records = client.billing.list(from_time=start_time, to_time=end_time)
        print(f"Found {len(records)} billing records")

        if not records:
            print("No billing records found for the specified period.")
            return

        # Prepare CSV data
        csv_rows = []
        total_cost = 0.0

        for record in records:
            # Calculate hours between from_time and to_time
            if record.from_time and record.to_time:
                duration = record.to_time - record.from_time
                hours = duration.total_seconds() / 3600
            else:
                hours = 1.0  # Default to 1 hour if times not available

            costs = calculate_record_cost(record, hours)
            total_cost += costs["total"]

            row = {
                "record_key": record.key,
                "from_time": record.from_time.isoformat() if record.from_time else "",
                "to_time": record.to_time.isoformat() if record.to_time else "",
                "hours": round(hours, 2),
                "cpu_cores_used": record.used_cores,
                "cpu_cost": round(costs["cpu_cost"], 4),
                "ram_gb_used": round(record.used_ram_gb, 2),
                "ram_cost": round(costs["ram_cost"], 4),
                "storage_tier_0_cost": round(costs["storage_costs"].get("tier_0", 0), 4),
                "storage_tier_1_cost": round(costs["storage_costs"].get("tier_1", 0), 4),
                "storage_tier_2_cost": round(costs["storage_costs"].get("tier_2", 0), 4),
                "storage_total_cost": round(costs["total_storage_cost"], 4),
                "gpus": record.gpus,
                "gpu_cost": round(costs["gpu_cost"], 4),
                "vgpus": record.vgpus,
                "vgpu_cost": round(costs["vgpu_cost"], 4),
                "total_cost": round(costs["total"], 4),
            }
            csv_rows.append(row)

        # Write CSV file
        if csv_rows:
            fieldnames = list(csv_rows[0].keys())
            with open(args.output, "w", newline="") as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(csv_rows)

            print(f"\nBilling report written to: {args.output}")
            print(f"Total records: {len(csv_rows)}")
            print(f"Total cost: ${total_cost:.2f}")

            # Print pricing summary
            print("\n" + "=" * 50)
            print("Pricing used (hourly rates):")
            print(f"  CPU: ${PRICING['cpu_per_core']}/core")
            print(f"  RAM: ${PRICING['ram_per_gb']}/GB")
            print(f"  Storage Tier 0 (NVMe): ${PRICING['storage_tier_0']}/GB")
            print(f"  Storage Tier 1 (SSD): ${PRICING['storage_tier_1']}/GB")
            print(f"  Storage Tier 2 (HDD): ${PRICING['storage_tier_2']}/GB")
            print(f"  GPU: ${PRICING['gpu']}/GPU")
            print(f"  vGPU: ${PRICING['vgpu']}/vGPU")
            print("=" * 50)

    finally:
        client.disconnect()
        print("\nDisconnected from VergeOS")


if __name__ == "__main__":
    main()
