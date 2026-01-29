#!/usr/bin/env python3
"""Example: NAS Volume Sync - two NAS services with volume synchronization.

This example demonstrates NAS volume synchronization:
- Deploy two NAS services on an internal network
- Create one volume on each NAS
- Set up a volume sync job between them
- Run the sync and verify

Prerequisites:
- Python 3.9 or later
- pyvergeos installed
- Connected to a VergeOS system (set VERGE_HOST, VERGE_USERNAME, VERGE_PASSWORD, VERGE_VERIFY_SSL)
- An internal network available
"""

import time

from pyvergeos import VergeClient
from pyvergeos.exceptions import NotFoundError

# ============================================================================
# CONFIGURATION - Modify these values as needed
# ============================================================================

NAS1_NAME = "pytest-nas-primary"
NAS2_NAME = "pytest-nas-replica"
NETWORK_NAME = "Internal"  # Will be created if it doesn't exist
SOURCE_VOLUME_NAME = "Production"
DEST_VOLUME_NAME = "Backup"
SYNC_JOB_NAME = "Prod-to-Backup-Sync"
VOLUME_SIZE_GB = 50


def ensure_internal_network(client: VergeClient) -> None:
    """Create the Internal network if it doesn't exist."""
    try:
        network = client.networks.get(name=NETWORK_NAME)
        print(f"Network '{NETWORK_NAME}' already exists")
    except NotFoundError:
        print(f"Creating network '{NETWORK_NAME}'...")
        network = client.networks.create(
            name=NETWORK_NAME,
            description="Internal network for NAS example",
            network_type="internal",
            network_address="10.100.100.0/24",
            ip_address="10.100.100.1",
            dhcp_enabled=True,
            dhcp_start="10.100.100.100",
            dhcp_stop="10.100.100.200",
        )
        # Power on the network
        network.power_on()
        print(f"Network '{NETWORK_NAME}' created and powered on")


def main() -> None:
    """Run the NAS volume sync example."""
    # Connect to VergeOS using environment variables
    # Set: VERGE_HOST, VERGE_USERNAME, VERGE_PASSWORD, VERGE_VERIFY_SSL
    with VergeClient.from_env() as client:
        # ============================================================================
        # STEP 0: ENSURE INTERNAL NETWORK EXISTS
        # ============================================================================

        print("\n=== Checking Network ===")
        ensure_internal_network(client)

        # ============================================================================
        # STEP 1: DEPLOY TWO NAS SERVICES
        # ============================================================================

        print("\n=== Deploying NAS Services ===")

        # Deploy primary NAS
        print(f"Deploying primary NAS: {NAS1_NAME}...")
        try:
            nas1 = client.nas_services.create(name=NAS1_NAME, network=NETWORK_NAME)
        except Exception as e:
            print(f"Failed to deploy primary NAS: {e}")
            return

        client.vms.get(nas1.vm_key)
        print(f"  Primary NAS deployed (Key: {nas1.key}, VM: {nas1.vm_key})")

        # Deploy replica NAS
        print(f"Deploying replica NAS: {NAS2_NAME}...")
        try:
            nas2 = client.nas_services.create(name=NAS2_NAME, network=NETWORK_NAME)
        except Exception as e:
            print(f"Failed to deploy replica NAS: {e}")
            return

        client.vms.get(nas2.vm_key)
        print(f"  Replica NAS deployed (Key: {nas2.key}, VM: {nas2.vm_key})")

        # ============================================================================
        # STEP 2: START AND WAIT FOR BOTH NAS SERVICES
        # ============================================================================

        print("\n=== Starting NAS Services ===")

        # Start both NAS VMs
        print("Starting primary NAS VM...")
        client.nas_services.power_on(nas1.key)

        print("Starting replica NAS VM...")
        client.nas_services.power_on(nas2.key)

        print("\nWaiting for NAS services to come online...")

        max_wait_seconds = 180
        wait_interval = 10
        elapsed = 0

        while elapsed < max_wait_seconds:
            nas1_status = client.nas_services.get(name=NAS1_NAME)
            nas2_status = client.nas_services.get(name=NAS2_NAME)

            nas1_running = nas1_status.is_running
            nas2_running = nas2_status.is_running

            print(
                f"  {NAS1_NAME}: {nas1_status.get('vm_status')} | "
                f"{NAS2_NAME}: {nas2_status.get('vm_status')}"
            )

            if nas1_running and nas2_running:
                print("Both NAS services are running!")
                break

            time.sleep(wait_interval)
            elapsed += wait_interval

        if not (nas1_status.is_running and nas2_status.is_running):
            print(f"WARNING: NAS services did not start within {max_wait_seconds} seconds.")
            print("Continuing anyway - volumes may still be created if NAS is initializing...")

        # Additional initialization time
        print("Waiting for NAS services to fully initialize...")
        time.sleep(15)

        # ============================================================================
        # STEP 3: CREATE VOLUMES ON EACH NAS
        # ============================================================================

        print("\n=== Creating Volumes ===")

        # Create source volume on primary NAS
        print(f"Creating source volume: {SOURCE_VOLUME_NAME} on {NAS1_NAME}...")
        source_vol = client.nas_volumes.create(
            name=SOURCE_VOLUME_NAME,
            service=NAS1_NAME,
            size_gb=VOLUME_SIZE_GB,
            description="Production data volume",
        )
        print(f"  Source volume created (Key: {source_vol.key})")

        # Create destination volume on replica NAS
        print(f"Creating destination volume: {DEST_VOLUME_NAME} on {NAS2_NAME}...")
        dest_vol = client.nas_volumes.create(
            name=DEST_VOLUME_NAME,
            service=NAS2_NAME,
            size_gb=VOLUME_SIZE_GB,
            description="Backup replica volume",
        )
        print(f"  Destination volume created (Key: {dest_vol.key})")

        # ============================================================================
        # STEP 4: CREATE VOLUME SYNC JOB
        # ============================================================================

        print("\n=== Creating Volume Sync Job ===")

        # Create the sync job on the primary NAS
        print(f"Creating volume sync job: {SYNC_JOB_NAME}...")
        sync_job = client.volume_syncs.create(
            name=SYNC_JOB_NAME,
            service=NAS1_NAME,
            source_volume=source_vol.key,
            destination_volume=dest_vol.key,
            sync_method="ysync",
            destination_delete="never",
            workers=4,
            description="Sync production data to backup",
        )

        print(f"  Volume sync job created (Key: {sync_job.key})")
        print(f"  Source:      {sync_job.get('source_volume_name')}")
        print(f"  Destination: {sync_job.get('destination_volume_name')}")
        print(f"  Method:      {sync_job.sync_method_display}")

        # ============================================================================
        # STEP 5: RUN INITIAL SYNC
        # ============================================================================

        print("\n=== Running Initial Sync ===")

        print("Starting sync job...")
        client.volume_syncs.start(sync_job.key)

        # Wait a moment and check status
        time.sleep(3)

        sync_status = client.volume_syncs.get(name=SYNC_JOB_NAME, service=NAS1_NAME)
        print(f"  Sync Status: {sync_status.status_display}")

        if sync_status.is_syncing:
            print("  Sync job started successfully")

        # ============================================================================
        # STEP 6: VERIFY CONFIGURATION
        # ============================================================================

        print("\n=== Configuration Summary ===")

        # Show both NAS services
        print("\nNAS Services:")
        for name in [NAS1_NAME, NAS2_NAME]:
            nas = client.nas_services.get(name=name)
            print(f"  - {nas.get('name')}: {nas.get('vm_status')} (Running: {nas.is_running})")

        # Show volumes
        print("\nVolumes:")
        for name in [SOURCE_VOLUME_NAME, DEST_VOLUME_NAME]:
            vol = client.nas_volumes.get(name=name)
            print(
                f"  - {vol.get('name')} on {vol.get('service_display')}: "
                f"{vol.max_size_gb} GB - {vol.get('description', '')}"
            )

        # Show sync job
        print("\nVolume Sync Jobs:")
        sync = client.volume_syncs.get(name=SYNC_JOB_NAME, service=NAS1_NAME)
        print(
            f"  - {sync.get('name')}: {sync.status_display} "
            f"({sync.get('source_volume_name')} -> {sync.get('destination_volume_name')})"
        )

        # ============================================================================
        # CLEANUP INSTRUCTIONS
        # ============================================================================

        print("\n=== Cleanup Commands ===")
        print("To remove these test resources, run: python nas_volume_sync.py --cleanup")


def cleanup() -> None:
    """Clean up resources created by this example."""
    # Connect to VergeOS using environment variables
    with VergeClient.from_env() as client:
        print("\n=== Cleaning Up ===")

        # Delete sync jobs first
        print("Checking for volume syncs...")
        for nas_name in [NAS1_NAME, NAS2_NAME]:
            try:
                syncs = client.volume_syncs.list(service=nas_name)
                for sync in syncs:
                    print(f"Deleting volume sync: {sync.get('name')}...")
                    client.volume_syncs.delete(sync.key)
            except NotFoundError:
                pass

        # Power off both NAS services
        for nas_name in [NAS1_NAME, NAS2_NAME]:
            try:
                nas = client.nas_services.get(name=nas_name)
                if nas.is_running:
                    print(f"Powering off NAS service: {nas_name}...")
                    client.nas_services.power_off(nas.key)
            except NotFoundError:
                print(f"NAS service '{nas_name}' not found")

        # Wait for NAS services to stop
        print("Waiting for NAS services to stop...")
        max_wait = 60
        elapsed = 0
        while elapsed < max_wait:
            time.sleep(5)
            elapsed += 5
            all_stopped = True
            for nas_name in [NAS1_NAME, NAS2_NAME]:
                try:
                    nas = client.nas_services.get(name=nas_name)
                    if nas.is_running:
                        all_stopped = False
                        print(f"  {nas_name}: {nas.get('vm_status')}")
                except NotFoundError:
                    pass
            if all_stopped:
                print("All NAS services stopped.")
                break

        time.sleep(2)

        # Delete volumes (skip system volumes)
        for nas_name in [NAS1_NAME, NAS2_NAME]:
            try:
                volumes = client.nas_volumes.list(service=nas_name)
                for vol in volumes:
                    vol_name = vol.get("name")
                    if vol_name == "system-logs":
                        print(f"Skipping system volume: {vol_name}")
                        continue
                    print(f"Deleting volume: {vol_name}...")
                    try:
                        client.nas_volumes.delete(vol.key)
                    except Exception as e:
                        print(f"  Warning: Could not delete volume: {e}")
            except NotFoundError:
                pass

        # Delete NAS services
        for nas_name in [NAS1_NAME, NAS2_NAME]:
            try:
                nas = client.nas_services.get(name=nas_name)
                print(f"Deleting NAS service: {nas_name}...")
                client.nas_services.delete(nas.key, force=True)
            except NotFoundError:
                pass

        print("Cleanup complete!")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--cleanup":
        cleanup()
    else:
        main()
