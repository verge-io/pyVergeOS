#!/usr/bin/env python3
"""Example demonstrating Site Sync operations for VergeOS backup/DR.

This example shows how to:
- List outgoing and incoming site syncs
- Enable/disable syncs
- Add cloud snapshots to the transfer queue
- Manage sync schedules
- Set throttle limits
- View sync queue items and manage queue
- View remote snapshots at destination site
- Monitor sync statistics and performance metrics
- Access sync transfer logs
- Manage verified incoming syncs
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

    # =========================================================================
    # Queue Management (NEW in v1.0)
    # =========================================================================
    print("=== Sync Queue Management ===")
    if outgoing_syncs:
        sync = outgoing_syncs[0]
        print(f"Queue for sync '{sync.name}':")

        # Access queue via the sync object's scoped manager
        queue_items = sync.queue.list()
        print(f"  Found {len(queue_items)} items in queue")

        for item in queue_items:
            print(f"\n  Queue Item key={item.key}")
            print(f"    Cloud Snapshot: {item.cloud_snapshot_key}")
            print(f"    Priority: {item.priority}")
            print(f"    Status: {item.status}")
            print(f"    Retention: {item.retention_timedelta}")
            print(f"    Do not expire: {item.do_not_expire}")
            if item.stats:
                print(f"    Progress: {item.stats}")

        # Filter queue by status
        pending_items = sync.queue.list_by_status("pending")
        print(f"\n  Pending items: {len(pending_items)}")

        # Example queue item operations (uncomment to actually modify):
        # if queue_items:
        #     item = queue_items[0]
        #     # Change priority
        #     item = item.set_priority(5)
        #     # Update retention
        #     item = item.set_retention(timedelta(days=14))
        #     # Remove from queue
        #     item.remove()
    print()

    # =========================================================================
    # Remote Snapshots (NEW in v1.0)
    # =========================================================================
    print("=== Remote Snapshots ===")
    if outgoing_syncs:
        sync = outgoing_syncs[0]
        print(f"Remote snapshots for sync '{sync.name}':")

        # Access remote snapshots via the sync object's scoped manager
        remote_snaps = sync.remote_snapshots.list()
        print(f"  Found {len(remote_snaps)} remote snapshots")

        for snap in remote_snaps:
            print(f"\n  Remote Snapshot key={snap.key}")
            print(f"    Name: {snap.name}")
            print(f"    Status: {snap.status}")
            print(f"    Remote Key: {snap.remote_key}")
            print(f"    Expires: {snap.expires_at}")
            print(f"    Retention: {snap.retention_timedelta}")
            print(f"    Do not expire: {snap.do_not_expire}")

        # Example remote snapshot operations (uncomment to actually modify):
        # if remote_snaps:
        #     snap = remote_snaps[0]
        #     # Request immediate sync of this snapshot
        #     snap.request()
        #     # Update retention to 30 days
        #     snap = snap.set_retention(timedelta(days=30))
        #     # Set to never expire
        #     snap = snap.set_retention(do_not_expire=True)
    print()

    # =========================================================================
    # Sync Statistics (NEW in v1.0)
    # =========================================================================
    print("=== Sync Statistics ===")
    if outgoing_syncs:
        sync = outgoing_syncs[0]
        print(f"Statistics for sync '{sync.name}':")

        # Access current stats via the sync object's scoped manager
        current_stats = sync.stats.get_current()
        if current_stats:
            print("\n  Current Statistics:")
            print(f"    Checked bytes: {current_stats.checked_bytes:,}")
            print(f"    Scanned bytes: {current_stats.scanned_bytes:,}")
            print(f"    Sent bytes: {current_stats.sent_bytes:,}")
            print(f"    Received bytes: {current_stats.received_bytes:,}")
            print(f"    Check rate: {current_stats.check_rate:,} bytes/sec")
            print(f"    Scan rate: {current_stats.scan_rate:,} bytes/sec")
            print(f"    Send rate: {current_stats.send_rate:,} bytes/sec")
            print(f"    Active transfers: {current_stats.active_transfers}")
            print(f"    Queued transfers: {current_stats.queued_transfers}")
            print(f"    Total blocks: {current_stats.total_blocks:,}")
            print(f"    Completed blocks: {current_stats.completed_blocks:,}")

        # Get historical stats
        history = sync.stats.list(limit=5)
        print(f"\n  Recent history entries: {len(history)}")
        for entry in history:
            print(f"    - {entry.timestamp_at}: sent={entry.sent_bytes:,} bytes")

        # Long-term history (hourly aggregates)
        long_history = sync.stats.list_long_history(limit=3)
        print(f"\n  Long-term history entries: {len(long_history)}")
        for entry in long_history:
            print(f"    - {entry.timestamp_at}: sent={entry.sent_bytes:,} bytes")
    print()

    # =========================================================================
    # Sync Logs (NEW in v1.0)
    # =========================================================================
    print("=== Sync Logs ===")
    if outgoing_syncs:
        sync = outgoing_syncs[0]
        print(f"Logs for outgoing sync '{sync.name}':")

        # Access logs via the sync object's scoped manager
        logs = sync.logs.list(limit=5)
        print(f"  Found {len(logs)} recent log entries")

        for log in logs:
            print(f"\n  Log key={log.key}")
            print(f"    Timestamp: {log.timestamp_at}")
            print(f"    Message: {log.message}")
            if log.snapshot_name:
                print(f"    Snapshot: {log.snapshot_name}")

        # Filter logs by type
        error_logs = sync.logs.list_errors(limit=3)
        print(f"\n  Error logs: {len(error_logs)}")

    if incoming_syncs:
        sync = incoming_syncs[0]
        print(f"\nLogs for incoming sync '{sync.name}':")

        # Access logs via the incoming sync object's scoped manager
        logs = sync.logs.list(limit=5)
        print(f"  Found {len(logs)} recent log entries")

        for log in logs:
            print(f"\n  Log key={log.key}")
            print(f"    Timestamp: {log.timestamp_at}")
            print(f"    Message: {log.message}")
    print()

    # =========================================================================
    # Verified Incoming Syncs (NEW in v1.0)
    # =========================================================================
    print("=== Verified Incoming Syncs ===")
    if incoming_syncs:
        sync = incoming_syncs[0]
        print(f"Verified snapshots for incoming sync '{sync.name}':")

        # Access verified snapshots via the incoming sync object's scoped manager
        verified = sync.verified.list()
        print(f"  Found {len(verified)} verified snapshots")

        for v in verified:
            print(f"\n  Verified Snapshot key={v.key}")
            print(f"    Name: {v.name}")
            print(f"    Status: {v.status}")
            print(f"    Local Key: {v.local_key}")
            print(f"    Registered: {v.is_registered}")
            if v.is_registered:
                print(f"    Registered on: {v.registered_on_at}")
            print(f"    Retention: {v.retention_timedelta}")
            print(f"    Do not expire: {v.do_not_expire}")

        # Filter by registration status
        registered = sync.verified.list_registered()
        unregistered = sync.verified.list_unregistered()
        print(f"\n  Registered: {len(registered)}, Unregistered: {len(unregistered)}")

        # Example verified snapshot operations (uncomment to actually modify):
        # if verified:
        #     v = verified[0]
        #     # List available snapshots at source
        #     snaps = v.list_snaps()
        #     print(f"Available snapshots: {snaps}")
        #     # Request a specific snapshot
        #     v.request(snap_name="snap-2024-01-15")
        #     # Update retention
        #     v = v.set_retention(timedelta(days=60))
    print()

    client.disconnect()
    print("Done!")


if __name__ == "__main__":
    main()
