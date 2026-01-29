#!/usr/bin/env python3
"""Example: Advanced NAS setup with users, CIFS shares, and NFS shares.

This example demonstrates advanced NAS configuration:
- Deploy a NAS service with custom resources
- Create local NAS users
- Create three volumes
- Set up CIFS (SMB) shares with user restrictions
- Set up NFS shares with host restrictions
- Modify advanced NAS service settings

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

NAS_NAME = "pytest-nas-advanced"
NETWORK_NAME = "Internal"  # Will be created if it doesn't exist
NAS_CORES = 4
NAS_MEMORY_GB = 8

# Volume configuration
VOLUMES = [
    {"name": "UserData", "size_gb": 100, "description": "User home directories and data"},
    {"name": "Shared", "size_gb": 200, "description": "Department shared files"},
    {"name": "LinuxApps", "size_gb": 50, "description": "Linux application data via NFS"},
]

# User configuration (passwords must be 8+ chars and meet complexity requirements)
USERS = [
    {"name": "nasadmin", "password": "NasAdminPass123!@", "displayname": "NAS Administrator"},
    {"name": "jdoe", "password": "JohnDoePass456!@", "displayname": "John Doe"},
    {"name": "svcbackup", "password": "SvcBackupPass789!@", "displayname": "Backup Service Account"},
]

# Network for NFS access (CIDR notation)
NFS_ALLOWED_NETWORK = "192.168.10.0/24"


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
    """Run the advanced NAS setup example."""
    # Connect to VergeOS using environment variables
    # Set: VERGE_HOST, VERGE_USERNAME, VERGE_PASSWORD, VERGE_VERIFY_SSL
    with VergeClient.from_env() as client:
        # ============================================================================
        # STEP 0: ENSURE INTERNAL NETWORK EXISTS
        # ============================================================================

        print("\n=== Checking Network ===")
        ensure_internal_network(client)

        # ============================================================================
        # STEP 1: DEPLOY NAS SERVICE WITH CUSTOM RESOURCES
        # ============================================================================

        print("\n=== Deploying NAS Service ===")

        print(f"Deploying NAS: {NAS_NAME} ({NAS_CORES} cores, {NAS_MEMORY_GB}GB RAM)...")
        try:
            nas = client.nas_services.create(
                name=NAS_NAME,
                network=NETWORK_NAME,
                cores=NAS_CORES,
                memory_gb=NAS_MEMORY_GB,
            )
        except Exception as e:
            print(f"Failed to deploy NAS service: {e}")
            return

        vm = client.vms.get(nas.vm_key)
        print("NAS service deployed:")
        print(f"  Key:       {nas.key}")
        print(f"  VM Key:    {nas.vm_key}")
        print(f"  VM Cores:  {vm.get('cpu_cores')}")
        print(f"  VM RAM:    {vm.get('ram')} MB")

        # ============================================================================
        # STEP 2: START AND WAIT FOR NAS SERVICE
        # ============================================================================

        print("\n=== Starting NAS Service ===")

        print("Starting NAS VM...")
        client.nas_services.power_on(nas.key)

        # Wait for the NAS to come online
        max_wait_seconds = 180
        wait_interval = 10
        elapsed = 0

        while elapsed < max_wait_seconds:
            nas_status = client.nas_services.get(name=NAS_NAME)
            print(f"  Status: {nas_status.get('vm_status')}")

            if nas_status.is_running:
                print("NAS service is running!")
                break

            time.sleep(wait_interval)
            elapsed += wait_interval

        if not nas_status.is_running:
            print(f"WARNING: NAS service did not start within {max_wait_seconds} seconds.")
            print("Continuing anyway - configuration may still work...")

        # Additional initialization time
        print("Waiting for NAS service to fully initialize...")
        time.sleep(15)

        # ============================================================================
        # STEP 3: CONFIGURE ADVANCED NAS SETTINGS
        # ============================================================================

        print("\n=== Configuring Advanced Settings ===")

        print("Configuring NAS service settings...")
        client.nas_services.update(
            nas.key,
            max_imports=3,
            max_syncs=2,
            read_ahead_kb=1024,
            description="Advanced NAS for testing - production-style configuration",
        )
        print("  MaxImports: 3")
        print("  MaxSyncs: 2")
        print("  ReadAheadKB: 1024")

        # ============================================================================
        # STEP 4: CREATE LOCAL NAS USERS
        # ============================================================================

        print("\n=== Creating NAS Users ===")

        for user in USERS:
            print(f"Creating user: {user['name']}...")
            try:
                client.nas_users.create(
                    service=NAS_NAME,
                    name=user["name"],
                    password=user["password"],
                    displayname=user.get("displayname"),
                )
                print(f"  User '{user['name']}' created")
            except Exception as e:
                print(f"  Warning: Failed to create user '{user['name']}': {e}")

        # List created users
        print("\nNAS Users:")
        users = client.nas_users.list(service=NAS_NAME)
        for user in users:
            enabled_str = "Enabled" if user.is_enabled else "Disabled"
            print(f"  - {user.get('name')}: {user.displayname or 'N/A'} ({enabled_str})")

        # ============================================================================
        # STEP 5: CREATE VOLUMES
        # ============================================================================

        print("\n=== Creating Volumes ===")

        created_volumes = {}
        for vol in VOLUMES:
            print(f"Creating volume: {vol['name']} ({vol['size_gb']} GB)...")
            try:
                volume = client.nas_volumes.create(
                    name=vol["name"],
                    service=NAS_NAME,
                    size_gb=vol["size_gb"],
                    description=vol["description"],
                )
                created_volumes[vol["name"]] = volume
                print(f"  Volume '{vol['name']}' created (Key: {volume.key})")
            except Exception as e:
                print(f"  Warning: Failed to create volume '{vol['name']}': {e}")

        # List volumes
        print("\nVolumes:")
        volumes = client.nas_volumes.list(service=NAS_NAME)
        for vol in volumes:
            if vol.get("name") != "system-logs":
                print(f"  - {vol.get('name')}: {vol.max_size_gb} GB - {vol.get('description', '')}")

        # ============================================================================
        # STEP 6: CREATE CIFS (SMB) SHARES
        # ============================================================================

        print("\n=== Creating CIFS Shares ===")

        # Share 1: User data with restricted access
        print("Creating CIFS share: users (on UserData volume)...")
        try:
            client.cifs_shares.create(
                name="users",
                volume="UserData",
                comment="User home directories",
                valid_users=["nasadmin", "jdoe"],
                shadow_copy=True,
            )
            print("  Share 'users' created - access restricted to nasadmin, jdoe")
        except Exception as e:
            print(f"  Warning: Failed to create share: {e}")

        # Share 2: Department shared with broader access
        print("Creating CIFS share: shared (on Shared volume)...")
        try:
            client.cifs_shares.create(
                name="shared",
                volume="Shared",
                comment="Department shared files",
                description="Read-write access for all authenticated users",
            )
            print("  Share 'shared' created - all authenticated users")
        except Exception as e:
            print(f"  Warning: Failed to create share: {e}")

        # List CIFS shares
        print("\nCIFS Shares:")
        cifs_shares = client.cifs_shares.list()
        for share in cifs_shares:
            guest = "Yes" if share.allows_guests else "No"
            readonly = "Yes" if share.is_read_only else "No"
            print(
                f"  - {share.get('name')} on {share.volume_name}: "
                f"Guest={guest}, ReadOnly={readonly}"
            )

        # ============================================================================
        # STEP 7: CREATE NFS SHARE
        # ============================================================================

        print("\n=== Creating NFS Share ===")

        # NFS share for Linux clients
        print("Creating NFS share: linuxapps (on LinuxApps volume)...")
        try:
            client.nfs_shares.create(
                name="linuxapps",
                volume="LinuxApps",
                allowed_hosts=NFS_ALLOWED_NETWORK,
                data_access="rw",
                squash="root_squash",
                description="NFS share for Linux application data",
            )
            print("  Share 'linuxapps' created")
            print(f"  Allowed hosts: {NFS_ALLOWED_NETWORK}")
            print("  Data access: Read-Write")
            print("  Squash: root_squash")
        except Exception as e:
            print(f"  Warning: Failed to create NFS share: {e}")

        # List NFS shares
        print("\nNFS Shares:")
        nfs_shares = client.nfs_shares.list()
        for share in nfs_shares:
            print(
                f"  - {share.get('name')} on {share.volume_name}: "
                f"{share.data_access_display}, {share.squash_display}"
            )

        # ============================================================================
        # STEP 8: FINAL CONFIGURATION SUMMARY
        # ============================================================================

        print("\n" + "=" * 60)
        print("=== CONFIGURATION COMPLETE ===")
        print("=" * 60)

        # NAS Service
        final_nas = client.nas_services.get(name=NAS_NAME)
        final_vm = client.vms.get(final_nas.vm_key)

        print("\nNAS Service:")
        print(f"  Name:       {final_nas.get('name')}")
        print(f"  Status:     {final_nas.get('vm_status')}")
        print(f"  Running:    {final_nas.is_running}")
        print(f"  CPU Cores:  {final_vm.get('cpu_cores')}")
        print(f"  RAM:        {final_vm.get('ram')} MB")
        print(f"  MaxImports: {final_nas.get('max_imports')}")
        print(f"  MaxSyncs:   {final_nas.get('max_syncs')}")

        # Users
        print("\nUsers:")
        users = client.nas_users.list(service=NAS_NAME)
        for user in users:
            print(f"  - {user.get('name')} ({user.displayname or 'N/A'})")

        # Volumes
        print("\nVolumes:")
        volumes = client.nas_volumes.list(service=NAS_NAME)
        for vol in volumes:
            if vol.get("name") != "system-logs":
                print(f"  - {vol.get('name')}: {vol.max_size_gb} GB")

        # CIFS Shares
        print("\nCIFS Shares:")
        cifs_shares = client.cifs_shares.list()
        for share in cifs_shares:
            print(f"  - \\\\<nas-ip>\\{share.get('name')}")

        # NFS Shares
        print("\nNFS Shares (mount with: mount -t nfs server:/share /mnt):")
        nfs_shares = client.nfs_shares.list()
        for share in nfs_shares:
            print(f"  - <nas-ip>:/{share.get('name')}")

        # ============================================================================
        # CLEANUP INSTRUCTIONS
        # ============================================================================

        print("\n=== Cleanup Commands ===")
        print("To remove these test resources, run: python nas_advanced.py --cleanup")


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

        # Delete CIFS shares
        print("Deleting CIFS shares...")
        try:
            cifs_shares = client.cifs_shares.list()
            for share in cifs_shares:
                # Only delete shares on volumes belonging to our NAS
                vol_name = share.volume_name
                if vol_name in ["UserData", "Shared", "LinuxApps"]:
                    print(f"  Deleting CIFS share: {share.get('name')}...")
                    client.cifs_shares.delete(share.key)
        except Exception as e:
            print(f"  Warning: Error deleting CIFS shares: {e}")

        # Delete NFS shares
        print("Deleting NFS shares...")
        try:
            nfs_shares = client.nfs_shares.list()
            for share in nfs_shares:
                vol_name = share.volume_name
                if vol_name in ["UserData", "Shared", "LinuxApps"]:
                    print(f"  Deleting NFS share: {share.get('name')}...")
                    client.nfs_shares.delete(share.key)
        except Exception as e:
            print(f"  Warning: Error deleting NFS shares: {e}")

        # Delete users
        print("Deleting NAS users...")
        try:
            users = client.nas_users.list(service=NAS_NAME)
            for user in users:
                print(f"  Deleting user: {user.get('name')}...")
                client.nas_users.delete(user.key)
        except Exception as e:
            print(f"  Warning: Error deleting users: {e}")

        # Power off NAS
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

        time.sleep(2)

        # Delete volumes (skip system volumes)
        print("Deleting volumes...")
        volumes = client.nas_volumes.list(service=NAS_NAME)
        for vol in volumes:
            vol_name = vol.get("name")
            if vol_name == "system-logs":
                print(f"  Skipping system volume: {vol_name}")
                continue
            print(f"  Deleting volume: {vol_name}...")
            try:
                client.nas_volumes.delete(vol.key)
            except Exception as e:
                print(f"    Warning: Could not delete volume: {e}")

        # Delete NAS service
        print(f"Deleting NAS service: {NAS_NAME}...")
        client.nas_services.delete(nas.key, force=True)

        print("Cleanup complete!")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--cleanup":
        cleanup()
    else:
        main()
