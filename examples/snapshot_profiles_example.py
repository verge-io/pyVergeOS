#!/usr/bin/env python3
"""Example: Snapshot profile management with pyvergeos.

This example demonstrates snapshot profile operations:
1. List existing snapshot profiles
2. Create a new snapshot profile
3. Add schedule periods (hourly, daily, weekly)
4. Update profile and period settings
5. Clean up resources

Snapshot profiles define automated snapshot schedules that can be applied
to VMs, NAS volumes, and cloud/system snapshots. Each profile can have
multiple periods with different frequencies and retention policies.

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
    python snapshot_profiles_example.py
"""

import sys
import time

from pyvergeos import VergeClient


def format_retention(seconds: int) -> str:
    """Format retention seconds as a human-readable string."""
    if seconds <= 0:
        return "None"
    days = seconds // 86400
    hours = (seconds % 86400) // 3600
    if days > 0:
        if hours > 0:
            return f"{days} days {hours} hours"
        return f"{days} days"
    return f"{hours} hours"


def main() -> int:
    """Run the snapshot profile management example."""
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
    profile_name = f"pyvergeos_profile_{ts}"

    try:
        # =====================================================================
        # Step 1: List existing snapshot profiles
        # =====================================================================
        print("=== Step 1: List Existing Snapshot Profiles ===")
        profiles = client.snapshot_profiles.list(include_periods=True)
        print(f"Found {len(profiles)} existing profile(s):")
        for profile in profiles:
            period_count = len(profile.periods) if profile.periods else 0
            print(f"  - {profile.name} ({period_count} period(s))")
            if profile.periods:
                for period in profile.periods:
                    retention = format_retention(period.retention_seconds)
                    print(f"      {period.name}: {period.frequency_display}, {retention}")
        print()

        # =====================================================================
        # Step 2: Create a new snapshot profile
        # =====================================================================
        print("=== Step 2: Create Snapshot Profile ===")
        profile = client.snapshot_profiles.create(
            name=profile_name,
            description="Example profile created by pyvergeos SDK",
        )
        print(f"Created profile: {profile.name}")
        print(f"  Key: {profile.key}")
        print(f"  Description: {profile.description}")
        print()

        # =====================================================================
        # Step 3: Add schedule periods
        # =====================================================================
        print("=== Step 3: Add Schedule Periods ===")

        # Hourly period - keep for 1 day
        print("Adding hourly period...")
        hourly = profile.add_period(
            name="Hourly",
            frequency="hourly",
            retention_seconds=86400,  # 1 day
            min_snapshots=2,  # Keep at least 2 snapshots
        )
        print(f"  Created: {hourly.name}")
        print(f"    Frequency: {hourly.frequency_display}")
        print(f"    Retention: {hourly.retention_display}")
        print(f"    Min Snapshots: {hourly.min_snapshots}")

        # Daily period - keep for 7 days, run at 2 AM
        print("Adding daily period...")
        daily = profile.add_period(
            name="Daily",
            frequency="daily",
            retention_seconds=604800,  # 7 days
            hour=2,
            minute=0,
            quiesce=True,  # Quiesce disks during snapshot
        )
        print(f"  Created: {daily.name}")
        print(f"    Frequency: {daily.frequency_display}")
        print(f"    Retention: {daily.retention_display}")
        print(f"    Time: {daily.hour:02d}:{daily.minute:02d}")
        print(f"    Quiesce: {daily.quiesce}")

        # Weekly period - keep for 30 days, run Sunday at 3 AM
        print("Adding weekly period...")
        weekly = profile.add_period(
            name="Weekly",
            frequency="weekly",
            retention_seconds=2592000,  # 30 days
            day_of_week="sun",
            hour=3,
            minute=0,
            max_tier=2,  # Store on tier 2 or lower
        )
        print(f"  Created: {weekly.name}")
        print(f"    Frequency: {weekly.frequency_display}")
        print(f"    Day: {weekly.day_of_week_display}")
        print(f"    Retention: {weekly.retention_display}")
        print(f"    Max Tier: {weekly.max_tier}")
        print()

        # =====================================================================
        # Step 4: View profile with periods
        # =====================================================================
        print("=== Step 4: View Profile Summary ===")
        profile_with_periods = client.snapshot_profiles.get(
            profile.key, include_periods=True
        )
        print(f"Profile: {profile_with_periods.name}")
        print(f"  Description: {profile_with_periods.description}")
        if profile_with_periods.periods:
            print(f"  Schedule ({len(profile_with_periods.periods)} period(s)):")
            for period in profile_with_periods.periods:
                retention = format_retention(period.retention_seconds)
                print(f"    - {period.name}:")
                print(f"        Frequency: {period.frequency_display}")
                print(f"        Retention: {retention}")
                if period.estimated_snapshot_count:
                    print(f"        Est. Snapshots: {period.estimated_snapshot_count}")
        print()

        # =====================================================================
        # Step 5: Update profile and period
        # =====================================================================
        print("=== Step 5: Update Profile and Period ===")

        # Update profile description
        print("Updating profile description...")
        updated_profile = client.snapshot_profiles.update(
            profile.key,
            description="Updated example profile",
        )
        print(f"  New description: {updated_profile.description}")

        # Update the daily period to skip missed snapshots
        print("Updating daily period...")
        updated_daily = client.snapshot_profiles.periods(profile.key).update(
            daily.key,
            skip_missed=True,
            min_snapshots=3,
        )
        print(f"  Skip Missed: {updated_daily.skip_missed}")
        print(f"  Min Snapshots: {updated_daily.min_snapshots}")
        print()

        # =====================================================================
        # Step 6: Demonstrate getting period by name
        # =====================================================================
        print("=== Step 6: Get Period by Name ===")
        fetched_weekly = client.snapshot_profiles.periods(profile.key).get(
            name="Weekly"
        )
        print(f"Found period: {fetched_weekly.name}")
        print(f"  Key: {fetched_weekly.key}")
        print(f"  Day: {fetched_weekly.day_of_week_display}")
        print()

        # =====================================================================
        # Cleanup
        # =====================================================================
        print("=== Cleanup ===")
        print("What would you like to do with the created profile?")
        print("  1. Keep the profile (default)")
        print("  2. Delete the profile and all periods")
        print()

        choice = input("Enter choice [1]: ").strip() or "1"

        if choice == "2":
            print()
            print("Deleting profile and periods...")

            # Delete all periods first
            for period in client.snapshot_profiles.periods(profile.key).list():
                print(f"  Deleting period: {period.name}")
                period.delete()

            # Delete the profile
            print(f"  Deleting profile: {profile.name}")
            client.snapshot_profiles.delete(profile.key)

            print()
            print("All resources deleted.")
        else:
            print()
            print(f"Keeping profile: {profile.name}")
            print("You can apply this profile to VMs, NAS volumes, or cloud snapshots")
            print("through the VergeOS UI or by setting the 'snapshot_profile' field.")

    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()
        return 1

    finally:
        client.disconnect()

    print()
    print("Snapshot profile example completed!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
