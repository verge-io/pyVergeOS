#!/usr/bin/env python3
"""Example: Multi-Tenant Monitoring with pyvergeos.

This example demonstrates tenant monitoring capabilities:
- Tenant dashboard overview
- Per-tenant resource utilization
- Historical metrics for capacity planning
- Tenant logs and activity tracking
- Billing and chargeback data

Prerequisites:
    - Environment variables configured (or modify credentials below)
    - One or more tenants created
    - Tenants running to generate metrics

Environment Variables:
    VERGE_HOST: VergeOS hostname or IP
    VERGE_USERNAME: Admin username
    VERGE_PASSWORD: Admin password
    VERGE_VERIFY_SSL: Set to 'false' for self-signed certs

Usage:
    export VERGE_HOST=192.168.1.100
    export VERGE_USERNAME=admin
    export VERGE_PASSWORD=yourpassword
    export VERGE_VERIFY_SSL=false

    python tenant_monitoring_example.py
"""

from __future__ import annotations

from datetime import datetime, timedelta

from pyvergeos import VergeClient
from pyvergeos.exceptions import NotFoundError


def tenant_dashboard_overview() -> None:
    """Get an overview of all tenants from the dashboard."""
    print("=== Tenant Dashboard Overview ===")

    with VergeClient(
        host="192.168.1.100",
        username="admin",
        password="your-password",
        verify_ssl=False,
    ) as client:
        # Get the tenant dashboard
        dashboard = client.tenant_dashboard.get()

        print(f"Total Tenants: {dashboard.tenants_count}")
        print(f"Online: {dashboard.tenants_online}")
        print(f"Offline: {dashboard.tenants_count - dashboard.tenants_online}")
        print()

        # Resource totals
        print("Resource Totals:")
        print(f"  RAM Allocated: {dashboard.total_ram_allocated} MB")
        print(f"  RAM Used: {dashboard.total_ram_used} MB")
        print(f"  CPU Cores: {dashboard.total_cpu_cores}")
        print(f"  Storage Allocated: {dashboard.total_storage_allocated} GB")
        print(f"  Storage Used: {dashboard.total_storage_used} GB")
        print()

        # Top consumers
        if dashboard.top_ram_consumers:
            print("Top RAM Consumers:")
            for tenant in dashboard.top_ram_consumers[:5]:
                name = tenant.get("name", "Unknown")
                ram = tenant.get("ram_used", 0)
                print(f"  - {name}: {ram} MB")
            print()

        if dashboard.top_storage_consumers:
            print("Top Storage Consumers:")
            for tenant in dashboard.top_storage_consumers[:5]:
                name = tenant.get("name", "Unknown")
                storage = tenant.get("storage_used", 0)
                print(f"  - {name}: {storage} GB")


def list_tenants_with_stats() -> None:
    """List all tenants with their current resource usage."""
    print("\n=== Tenants with Stats ===")

    with VergeClient(
        host="192.168.1.100",
        username="admin",
        password="your-password",
        verify_ssl=False,
    ) as client:
        tenants = client.tenants.list()
        print(f"Found {len(tenants)} tenants")

        for tenant in tenants:
            print(f"\n  Tenant: {tenant.name}")
            print(f"    Key: {tenant.key}")
            print(f"    Status: {tenant.status}")
            print(f"    Running: {tenant.is_running}")

            # Get current stats
            try:
                stats = tenant.stats.get()
                print(f"    RAM Used: {stats.ram_used_mb} MB")
                print(f"    Last Update: {stats.last_update}")
            except NotFoundError:
                print("    Stats: Not available")


def tenant_detailed_stats() -> None:
    """Get detailed statistics for a specific tenant."""
    print("\n=== Detailed Tenant Stats ===")

    with VergeClient(
        host="192.168.1.100",
        username="admin",
        password="your-password",
        verify_ssl=False,
    ) as client:
        # Get first available tenant
        tenants = client.tenants.list(limit=1)
        if not tenants:
            print("No tenants found")
            return

        tenant = tenants[0]
        print(f"Tenant: {tenant.name}")

        # Get current stats
        stats = tenant.stats.get()
        print("\nCurrent Stats:")
        print(f"  RAM Used: {stats.ram_used_mb} MB")
        print(f"  Last Update: {stats.last_update}")

        # Get recent history (high resolution, last few hours)
        print("\nRecent History (short-term):")
        history = tenant.stats.history_short(limit=10)
        for point in history:
            timestamp = point.timestamp or "Unknown"
            ram = point.ram_used_mb
            cpu = point.total_cpu_percent
            print(f"  {timestamp}: CPU {cpu:.1f}%, RAM {ram} MB")

        # Get long-term history (for capacity planning)
        print("\nLong-term History:")
        history_long = tenant.stats.history_long(limit=7)
        for point in history_long:
            timestamp = point.timestamp or "Unknown"
            ram = point.ram_used_mb
            tier0 = point.tier0_used_gb
            print(f"  {timestamp}: RAM {ram} MB, Tier0 {tier0} GB")


def tenant_storage_by_tier() -> None:
    """Analyze storage usage by tier for tenants."""
    print("\n=== Tenant Storage by Tier ===")

    with VergeClient(
        host="192.168.1.100",
        username="admin",
        password="your-password",
        verify_ssl=False,
    ) as client:
        tenants = client.tenants.list()

        for tenant in tenants[:5]:  # Show first 5 tenants
            print(f"\n  Tenant: {tenant.name}")

            # Get latest stats with tier breakdown
            history = tenant.stats.history_short(limit=1)
            if history:
                point = history[0]
                print(f"    Tier 0: {point.tier0_used_gb:.2f} GB")
                print(f"    Tier 1: {point.tier1_used_gb:.2f} GB")
                print(f"    Tier 2: {point.tier2_used_gb:.2f} GB")
                print(f"    Tier 3: {point.tier3_used_gb:.2f} GB")
                print(f"    Tier 4: {point.tier4_used_gb:.2f} GB")
                print(f"    Tier 5: {point.tier5_used_gb:.2f} GB")
                print(f"    Total: {point.total_storage_gb:.2f} GB")
            else:
                print("    No storage data available")


def tenant_logs() -> None:
    """View tenant activity logs."""
    print("\n=== Tenant Logs ===")

    with VergeClient(
        host="192.168.1.100",
        username="admin",
        password="your-password",
        verify_ssl=False,
    ) as client:
        tenants = client.tenants.list(limit=1)
        if not tenants:
            print("No tenants found")
            return

        tenant = tenants[0]
        print(f"Tenant: {tenant.name}")

        # Get recent logs
        print("\nRecent Logs:")
        logs = tenant.logs.list(limit=15)
        for log in logs:
            level = log.level or "info"
            text = log.text or ""
            timestamp = log.timestamp or ""
            # Truncate long messages
            text_display = text[:60] + "..." if len(text) > 60 else text
            print(f"  [{level.upper():8s}] {timestamp} - {text_display}")

        # Get warning and error logs
        print("\nWarnings and Errors:")
        warnings = tenant.logs.list(level="warning", limit=5)
        for log in warnings:
            print(f"  [WARNING] {log.text[:60]}")

        errors = tenant.logs.list_errors(limit=5)
        for log in errors:
            print(f"  [ERROR] {log.text[:60]}")


def tenant_gpu_usage() -> None:
    """Monitor GPU/vGPU usage by tenants."""
    print("\n=== Tenant GPU Usage ===")

    with VergeClient(
        host="192.168.1.100",
        username="admin",
        password="your-password",
        verify_ssl=False,
    ) as client:
        tenants = client.tenants.list()

        for tenant in tenants[:5]:
            print(f"\n  Tenant: {tenant.name}")

            # Get stats with GPU metrics
            history = tenant.stats.history_short(limit=1)
            if history:
                point = history[0]
                gpus = point.gpus_used
                vgpus = point.vgpus_used

                if gpus > 0 or vgpus > 0:
                    print(f"    GPUs: {gpus}")
                    print(f"    vGPUs: {vgpus}")
                else:
                    print("    No GPU allocation")
            else:
                print("    No data available")


def billing_report() -> None:
    """Generate billing data from tenant stats."""
    print("\n=== Billing Report ===")

    with VergeClient(
        host="192.168.1.100",
        username="admin",
        password="your-password",
        verify_ssl=False,
    ) as client:
        # Get billing records from the system
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)

        print(f"Billing Period: {start_date.date()} to {end_date.date()}")
        print()

        # System-wide billing records
        records = client.billing.list(
            start_time=start_date,
            end_time=end_date,
            limit=10,
        )

        if records:
            print("System Billing Records:")
            for record in records[:5]:
                print(f"  Date: {record.timestamp}")
                print(f"    CPU: {record.cpu_used}")
                print(f"    RAM: {record.ram_used} MB")
                print(f"    Tier0: {record.tier0_used} GB")
                print()
        else:
            print("No billing records found")

        # Per-tenant billing data
        print("\nPer-Tenant Usage:")
        tenants = client.tenants.list()

        for tenant in tenants[:3]:
            print(f"\n  {tenant.name}:")

            # Get historical stats for billing period
            history = tenant.stats.history_long(limit=7)

            if history:
                # Calculate averages
                total_ram = sum(h.ram_used_mb for h in history)
                avg_ram = total_ram / len(history) if history else 0

                total_tier0 = sum(h.tier0_used_gb for h in history)
                avg_storage = total_tier0 / len(history) if history else 0

                print(f"    Avg RAM: {avg_ram:.0f} MB")
                print(f"    Avg Tier0 Storage: {avg_storage:.2f} GB")
                print(f"    Data Points: {len(history)}")
            else:
                print("    No usage data")


def export_tenant_metrics() -> None:
    """Export tenant metrics to CSV format."""
    print("\n=== Export Tenant Metrics ===")

    with VergeClient(
        host="192.168.1.100",
        username="admin",
        password="your-password",
        verify_ssl=False,
    ) as client:
        tenants = client.tenants.list()

        # CSV header
        print("tenant_name,timestamp,ram_used_mb,tier0_gb,tier1_gb,total_storage_gb")

        for tenant in tenants[:3]:  # Limit for example
            history = tenant.stats.history_short(limit=5)

            for point in history:
                timestamp = point.timestamp.isoformat() if point.timestamp else ""
                print(
                    f"{tenant.name},"
                    f"{timestamp},"
                    f"{point.ram_used_mb},"
                    f"{point.tier0_used_gb:.2f},"
                    f"{point.tier1_used_gb:.2f},"
                    f"{point.total_storage_gb:.2f}"
                )


def monitor_tenant_health() -> None:
    """Monitor tenant health and generate alerts."""
    print("\n=== Tenant Health Monitoring ===")

    # Thresholds for alerting
    RAM_WARNING_PERCENT = 80
    STORAGE_WARNING_PERCENT = 85

    with VergeClient(
        host="192.168.1.100",
        username="admin",
        password="your-password",
        verify_ssl=False,
    ) as client:
        tenants = client.tenants.list()

        alerts = []

        for tenant in tenants:
            # Check if tenant is running
            if not tenant.is_running:
                continue

            # Get tenant storage allocation
            storage_allocated = tenant.get("storage_allocated", 0)
            ram_allocated = tenant.get("ram_allocated", 0)

            # Get current usage
            history = tenant.stats.history_short(limit=1)
            if not history:
                continue

            point = history[0]

            # Check RAM usage
            if ram_allocated > 0:
                ram_percent = (point.ram_used_mb / ram_allocated) * 100
                if ram_percent > RAM_WARNING_PERCENT:
                    alerts.append(
                        f"WARNING: {tenant.name} RAM at {ram_percent:.0f}% "
                        f"({point.ram_used_mb}/{ram_allocated} MB)"
                    )

            # Check storage usage
            if storage_allocated > 0:
                storage_percent = (point.total_storage_gb / storage_allocated) * 100
                if storage_percent > STORAGE_WARNING_PERCENT:
                    alerts.append(
                        f"WARNING: {tenant.name} Storage at {storage_percent:.0f}% "
                        f"({point.total_storage_gb:.1f}/{storage_allocated} GB)"
                    )

            # Check for recent errors
            errors = tenant.logs.list_errors(limit=5)
            if errors:
                alerts.append(f"ALERT: {tenant.name} has {len(errors)} recent errors")

        # Display alerts
        if alerts:
            print(f"Found {len(alerts)} alerts:")
            for alert in alerts:
                print(f"  - {alert}")
        else:
            print("All tenants healthy - no alerts")


if __name__ == "__main__":
    print("pyvergeos Multi-Tenant Monitoring Examples")
    print("=" * 50)
    print()
    print("NOTE: Update host/credentials in this file before running.")
    print()

    # Uncomment the examples you want to run:
    # tenant_dashboard_overview()
    # list_tenants_with_stats()
    # tenant_detailed_stats()
    # tenant_storage_by_tier()
    # tenant_logs()
    # tenant_gpu_usage()
    # billing_report()
    # export_tenant_metrics()
    # monitor_tenant_health()

    print("See the code for examples of:")
    print("  - Tenant dashboard overview")
    print("  - Listing tenants with stats")
    print("  - Detailed tenant statistics")
    print("  - Storage breakdown by tier")
    print("  - Tenant activity logs")
    print("  - GPU/vGPU usage monitoring")
    print("  - Billing report generation")
    print("  - Exporting metrics to CSV")
    print("  - Health monitoring with alerts")
