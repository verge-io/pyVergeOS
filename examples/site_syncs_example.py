#!/usr/bin/env python3
"""Example demonstrating Site Sync operations for VergeOS backup/DR.

This example shows how to:
- List outgoing and incoming site syncs
- Enable/disable syncs
- Add cloud snapshots to the transfer queue
- Manage sync schedules
- Set throttle limits
"""

from datetime import timedelta  # noqa: F401 - used in commented examples

from pyvergeos import VergeClient


def main() -> None:
    """Demonstrate site sync operations."""
    # Create client from environment variables or specify credentials
    # Required: VERGE_HOST, and either VERGE_TOKEN or VERGE_USERNAME/VERGE_PASSWORD
    client = VergeClient.from_env()

    print(f"Connected to {client.host} (version: {client.version})")
    print()

    # =========================================================================
    # List Sites
    # =========================================================================
    print("=== Available Sites ===")
    sites = client.sites.list()
    for site in sites:
        print(f"  Site: {site.name} (key={site.key})")
        print(f"    URL: {site.url}")
        print(f"    Status: {site.status}")
        print(f"    Outgoing syncs enabled: {site.has_outgoing_syncs}")
        print(f"    Incoming syncs enabled: {site.has_incoming_syncs}")
    print()

    # =========================================================================
    # List Outgoing Syncs
    # =========================================================================
    print("=== Outgoing Site Syncs ===")
    outgoing_syncs = client.site_syncs.list()
    print(f"Found {len(outgoing_syncs)} outgoing syncs")

    for sync in outgoing_syncs:
        print(f"\n  Sync: {sync.name} (key={sync.key})")
        print(f"    Status: {sync.status} / State: {sync.state}")
        print(f"    Enabled: {sync.is_enabled}")
        print(f"    URL: {sync.url}")
        print(f"    Encryption: {sync.has_encryption}")
        print(f"    Compression: {sync.has_compression}")
        print(f"    Data threads: {sync.data_threads}")
        print(f"    Last run: {sync.last_run_at}")
    print()

    # =========================================================================
    # List Incoming Syncs
    # =========================================================================
    print("=== Incoming Site Syncs ===")
    incoming_syncs = client.site_syncs_incoming.list()
    print(f"Found {len(incoming_syncs)} incoming syncs")

    for sync in incoming_syncs:
        print(f"\n  Sync: {sync.name} (key={sync.key})")
        print(f"    Status: {sync.status} / State: {sync.state}")
        print(f"    Enabled: {sync.is_enabled}")
        print(f"    Registration code: {sync.registration_code[:20]}...")
        print(f"    Min snapshots: {sync.min_snapshots}")
        print(f"    Last sync: {sync.last_sync_at}")
    print()

    # =========================================================================
    # Enable/Disable Sync Operations
    # =========================================================================
    if outgoing_syncs:
        sync = outgoing_syncs[0]
        print(f"=== Enable/Disable Demo (Sync: {sync.name}) ===")
        print(f"Current enabled state: {sync.is_enabled}")

        # Disable the sync
        print("Disabling sync...")
        sync = sync.disable()  # Can also use: client.site_syncs.disable(sync.key)
        print(f"Enabled state after disable: {sync.is_enabled}")

        # Re-enable the sync
        print("Re-enabling sync...")
        sync = sync.enable()  # Can also use: client.site_syncs.enable(sync.key)
        print(f"Enabled state after enable: {sync.is_enabled}")

        # Alternative: use start/stop aliases
        # sync = sync.stop()   # Same as disable()
        # sync = sync.start()  # Same as enable()
        print()

    # =========================================================================
    # List Sync Schedules
    # =========================================================================
    print("=== Site Sync Schedules ===")
    schedules = client.site_sync_schedules.list()
    print(f"Found {len(schedules)} schedules")

    for schedule in schedules:
        print(f"\n  Schedule key={schedule.key}")
        print(f"    Sync key: {schedule.sync_key}")
        print(f"    Profile period key: {schedule.profile_period_key}")
        print(f"    Retention: {schedule.retention_timedelta}")
        print(f"    Priority: {schedule.priority}")
        print(f"    Do not expire: {schedule.do_not_expire}")
        print(f"    Destination prefix: {schedule.destination_prefix}")
    print()

    # =========================================================================
    # Create a Schedule (Example - commented out to avoid changes)
    # =========================================================================
    print("=== Create Schedule Example (Dry Run) ===")
    if outgoing_syncs:
        # Get available profile periods
        profiles = client.snapshot_profiles.list(include_periods=True)
        print("Available profile periods:")
        for profile in profiles:
            periods = profile.get_periods()
            for period in periods:
                print(f"  - {profile.name}/{period.name} (key={period.key})")

        # Example schedule creation (uncomment to actually create):
        # schedule = client.site_sync_schedules.create(
        #     sync_key=outgoing_syncs[0].key,
        #     profile_period_key=10,  # Use appropriate period key
        #     retention=timedelta(days=7),
        #     priority=0,
        #     do_not_expire=False,
        #     destination_prefix="remote",
        # )
        # print(f"Created schedule: {schedule}")
    print()

    # =========================================================================
    # Add Snapshot to Queue (Example - commented out to avoid changes)
    # =========================================================================
    print("=== Add to Queue Example (Dry Run) ===")
    if outgoing_syncs:
        # Get available cloud snapshots
        cloud_snaps = client.cloud_snapshots.list(limit=5)
        print(f"Found {len(cloud_snaps)} cloud snapshots:")
        for snap in cloud_snaps:
            print(f"  - {snap.name} (key={snap.key})")

        # Example queue addition (uncomment to actually queue):
        # if cloud_snaps:
        #     client.site_syncs.add_to_queue(
        #         sync_key=outgoing_syncs[0].key,
        #         snapshot_key=cloud_snaps[0].key,
        #         retention=timedelta(days=3),
        #         priority=0,
        #         do_not_expire=False,
        #         destination_prefix="manual",
        #     )
        #     print(f"Queued snapshot {cloud_snaps[0].name} for sync")

        # Alternative using object method:
        # sync = outgoing_syncs[0]
        # sync.add_to_queue(
        #     snapshot_key=cloud_snaps[0].key,
        #     retention=259200,  # 3 days in seconds
        # )
    print()

    # =========================================================================
    # Throttle Operations (Example - commented out to avoid changes)
    # =========================================================================
    print("=== Throttle Example (Dry Run) ===")
    if outgoing_syncs:
        sync = outgoing_syncs[0]
        print(f"Current throttle: {sync.send_throttle} bytes/sec")

        # Example throttle operations (uncomment to actually set):
        # # Set throttle to 1 MB/sec
        # sync = client.site_syncs.set_throttle(sync.key, 1000000)
        # print(f"Throttle after set: {sync.send_throttle}")
        #
        # # Disable throttle
        # sync = client.site_syncs.disable_throttle(sync.key)
        # print(f"Throttle after disable: {sync.send_throttle}")
    print()

    # =========================================================================
    # Filter Examples
    # =========================================================================
    print("=== Filter Examples ===")
    if sites:
        site = sites[0]
        print(f"Syncs for site '{site.name}':")

        # List syncs for specific site by key
        site_syncs = client.site_syncs.list_for_site(site_key=site.key)
        for sync in site_syncs:
            print(f"  - {sync.name}")

        # List only enabled syncs
        enabled_syncs = client.site_syncs.list_enabled()
        print(f"\nEnabled syncs: {len(enabled_syncs)}")

        # List only disabled syncs
        disabled_syncs = client.site_syncs.list_disabled()
        print(f"Disabled syncs: {len(disabled_syncs)}")

        # List schedules for specific sync
        if site_syncs:
            sync_schedules = client.site_sync_schedules.list_for_sync(sync_key=site_syncs[0].key)
            print(f"\nSchedules for '{site_syncs[0].name}': {len(sync_schedules)}")
    print()

    # =========================================================================
    # Get by Name
    # =========================================================================
    print("=== Get by Name ===")
    if outgoing_syncs:
        sync_name = outgoing_syncs[0].name
        try:
            sync = client.site_syncs.get(name=sync_name)
            print(f"Found sync by name '{sync_name}': key={sync.key}")
        except Exception as e:
            print(f"Error: {e}")
    print()

    client.disconnect()
    print("Done!")


if __name__ == "__main__":
    main()
