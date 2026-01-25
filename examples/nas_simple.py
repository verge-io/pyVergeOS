#!/usr/bin/env python3
"""Example: Simple NAS setup - single NAS with two volumes.

This example demonstrates the basic NAS setup workflow:
- Deploy a NAS service on an internal network
- Create two volumes with default settings
- Verify the configuration

Prerequisites:
- Python 3.9 or later
- pyvergeos installed
- Connected to a VergeOS system
- An internal network available
"""

import time

from pyvergeos import VergeClient
from pyvergeos.exceptions import NotFoundError

# ============================================================================
# CONFIGURATION - Modify these values as needed
# ============================================================================

NAS_NAME = "pytest-nas-simple"
NETWORK_NAME = "Internal"  # Will be created if it doesn't exist
VOLUME_1_NAME = "Data"
VOLUME_2_NAME = "Archive"
VOLUME_SIZE_GB = 50  # Size in GB for each volume


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
    """Run the simple NAS setup example."""
    # Connect to VergeOS using environment variables
    # Set: VERGE_HOST, VERGE_USERNAME, VERGE_PASSWORD, VERGE_VERIFY_SSL
    with VergeClient.from_env() as client:
        # ============================================================================
        # STEP 0: ENSURE INTERNAL NETWORK EXISTS
        # ============================================================================

        print("\n=== Checking Network ===")
        ensure_internal_network(client)

        # ============================================================================
        # STEP 1: DEPLOY NAS SERVICE
        # ============================================================================

        print("\n=== Deploying NAS Service ===")

        # Deploy a new NAS service with default settings (4 cores, 8GB RAM)
        try:
            nas = client.nas_services.create(
                name=NAS_NAME,
                network=NETWORK_NAME,
            )
        except Exception as e:
            print(f"Failed to deploy NAS service: {e}")
            return

        # Get VM details for display
        vm = client.vms.get(nas.vm_key)

        print("NAS Service deployed successfully:")
        print(f"  Name:      {nas.get('name')}")
        print(f"  VM Key:    {nas.vm_key}")
        print(f"  VM Cores:  {vm.get('cpu_cores')}")
        print(f"  VM RAM:    {vm.get('ram')} MB")

        # ============================================================================
        # STEP 2: START AND WAIT FOR NAS SERVICE
        # ============================================================================

        print("\n=== Starting NAS Service ===")

        # Start the NAS VM (NAS services are backed by VMs)
        print("Starting NAS VM...")
        client.nas_services.power_on(nas.key)

        # Wait for the NAS to come online
        max_wait_seconds = 120
        wait_interval = 10
        elapsed = 0

        while elapsed < max_wait_seconds:
            nas_status = client.nas_services.get(name=NAS_NAME)
            if nas_status.is_running:
                print("NAS service is now running!")
                break
            print(f"  Status: {nas_status.get('vm_status')} - waiting...")
            time.sleep(wait_interval)
            elapsed += wait_interval

        if not nas_status.is_running:
            print(f"WARNING: NAS service did not start within {max_wait_seconds} seconds.")
            print("It may still be initializing. Continuing anyway...")

        # Give the NAS a moment to fully initialize
        print("Waiting for NAS service to fully initialize...")
        time.sleep(10)

        # ============================================================================
        # STEP 3: CREATE VOLUMES
        # ============================================================================

        print("\n=== Creating Volumes ===")

        # Create first volume - Data
        print(f"Creating volume: {VOLUME_1_NAME} ({VOLUME_SIZE_GB} GB)...")
        vol1 = client.nas_volumes.create(
            name=VOLUME_1_NAME,
            service=NAS_NAME,
            size_gb=VOLUME_SIZE_GB,
            description="General data storage",
        )
        print(f"  Volume '{VOLUME_1_NAME}' created successfully (Key: {vol1.key})")

        # Create second volume - Archive
        print(f"Creating volume: {VOLUME_2_NAME} ({VOLUME_SIZE_GB} GB)...")
        vol2 = client.nas_volumes.create(
            name=VOLUME_2_NAME,
            service=NAS_NAME,
            size_gb=VOLUME_SIZE_GB,
            description="Archive storage",
        )
        print(f"  Volume '{VOLUME_2_NAME}' created successfully (Key: {vol2.key})")

        # ============================================================================
        # STEP 4: VERIFY CONFIGURATION
        # ============================================================================

        print("\n=== Configuration Summary ===")

        # Get final NAS status
        final_nas = client.nas_services.get(name=NAS_NAME)

        # Get VM details for display
        final_vm = client.vms.get(final_nas.vm_key)

        print("\nNAS Service Details:")
        print(f"  Name:       {final_nas.get('name')}")
        print(f"  Status:     {final_nas.get('vm_status')}")
        print(f"  Running:    {final_nas.is_running}")
        print(f"  VM Cores:   {final_vm.get('cpu_cores')}")
        print(f"  VM RAM:     {final_vm.get('ram')} MB")

        # List the volumes we created
        print("\nVolumes on this NAS:")
        volumes = client.nas_volumes.list(service=NAS_NAME)
        for vol in volumes:
            print(f"  - {vol.get('name')}: {vol.max_size_gb} GB - {vol.get('description', '')}")

        # ============================================================================
        # CLEANUP INSTRUCTIONS
        # ============================================================================

        print("\n=== Cleanup Commands ===")
        print("To remove these test resources, run the following Python code:")
        print()
        print("# Remove volumes first")
        print(f"client.nas_volumes.delete('{vol1.key}')")
        print(f"client.nas_volumes.delete('{vol2.key}')")
        print()
        print("# Then remove the NAS service (power off first)")
        print(f"client.nas_services.power_off({final_nas.key})")
        print("# Wait for it to stop, then:")
        print(f"client.nas_services.delete({final_nas.key})")


def cleanup() -> None:
    """Clean up resources created by this example."""
    # Connect to VergeOS using environment variables
    with VergeClient.from_env() as client:
        print("\n=== Cleaning Up ===")

        # Get the NAS service
        try:
            nas = client.nas_services.get(name=NAS_NAME)
        except NotFoundError:
            print(f"NAS service '{NAS_NAME}' not found, nothing to clean up")
            return

        # Delete any volume syncs first (they block volume deletion)
        print("Checking for volume syncs...")
        syncs = client.volume_syncs.list(service=NAS_NAME)
        for sync in syncs:
            print(f"Deleting volume sync: {sync.get('name')}...")
            client.volume_syncs.delete(sync.key)

        # Power off the NAS first (required before deleting volumes)
        if nas.is_running:
            print("Powering off NAS service...")
            client.nas_services.power_off(nas.key)

            # Wait for it to stop
            max_wait = 60
            elapsed = 0
            while elapsed < max_wait:
                time.sleep(5)
                elapsed += 5
                nas = client.nas_services.get(name=NAS_NAME)
                print(f"  Status: {nas.get('vm_status')}")
                if not nas.is_running:
                    print("NAS service stopped.")
                    break

        # Give the system a moment to finalize
        time.sleep(2)

        # Delete volumes (must be done after NAS is stopped)
        volumes = client.nas_volumes.list(service=NAS_NAME)
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

        # Delete the NAS service
        print(f"Deleting NAS service: {NAS_NAME}...")
        client.nas_services.delete(nas.key, force=True)

        print("Cleanup complete!")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--cleanup":
        cleanup()
    else:
        main()
