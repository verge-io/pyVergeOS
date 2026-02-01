#!/usr/bin/env python3
"""Example: VM Import/Export with pyvergeos.

This example demonstrates VM import and export operations:
- Importing VMs from files (VMDK, QCOW2, OVA, OVF)
- Importing VMs from NAS volumes
- Exporting VMs to NAS volumes for backup
- Monitoring import/export progress

Prerequisites:
    - Environment variables configured (or modify credentials below)
    - NAS service with volumes set up
    - VMs with "Allow Export" enabled for export operations

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

    python vm_import_export_example.py
"""

from __future__ import annotations

from pyvergeos import VergeClient
from pyvergeos.exceptions import NotFoundError


def list_imports() -> None:
    """List existing VM import jobs."""
    print("=== List VM Import Jobs ===")

    with VergeClient(
        host="192.168.1.100",
        username="admin",
        password="your-password",
        verify_ssl=False,
    ) as client:
        imports = client.vm_imports.list()
        print(f"Found {len(imports)} import jobs")

        for imp in imports:
            print(f"\n  Import: {imp.name}")
            print(f"    Key: {imp.key[:16]}...")
            print(f"    Status: {imp.status}")
            print(f"    Status Info: {imp.status_info or 'N/A'}")
            print(f"    Complete: {imp.is_complete}")
            print(f"    Importing: {imp.is_importing}")
            if imp.vm_key:
                print(f"    Created VM: {imp.vm_key}")


def import_from_volume() -> None:
    """Import VMs from a NAS volume.

    This demonstrates importing VMs from a remote NFS/CIFS share
    that has been set up as a remote volume in the NAS.
    """
    print("\n=== Import VMs from Volume ===")

    with VergeClient(
        host="192.168.1.100",
        username="admin",
        password="your-password",
        verify_ssl=False,
    ) as client:
        # First, find the source volume (should be a remote NFS/CIFS volume)
        try:
            # Get NAS service
            nas_services = client.nas_services.list(limit=1)
            if not nas_services:
                print("No NAS service found")
                return

            nas = nas_services[0]

            # Find remote volume with VMware exports
            volumes = nas.volumes.list()
            remote_volumes = [v for v in volumes if v.volume_type == "remote"]

            if not remote_volumes:
                print("No remote volumes found. Set up a remote volume first.")
                print("Remote volumes connect to external NFS/CIFS shares.")
                return

            print("Available remote volumes:")
            for vol in remote_volumes:
                print(f"  - {vol.name} (key={vol.key})")

            # Use first remote volume for demo
            source_volume = remote_volumes[0]
            print(f"\nUsing volume: {source_volume.name}")

        except NotFoundError as e:
            print(f"Volume not found: {e}")
            return

        # Create an import job
        # NOTE: Uncomment to actually create an import
        print("\nCreating import job...")
        print("  Volume: {source_volume.name}")
        print("  Preserve MAC: True")
        print("  Preferred Tier: default")

        # import_job = client.vm_imports.create(
        #     name=f"Import from {source_volume.name}",
        #     volume=source_volume.key,
        #     preserve_macs=True,  # Keep original MAC addresses
        #     preferred_tier=0,    # Use default tier
        # )
        # print(f"Created import job: {import_job.key}")

        print("\n(Import creation commented out - uncomment to run)")


def monitor_import_progress() -> None:
    """Monitor the progress of an import job."""
    print("\n=== Monitor Import Progress ===")

    with VergeClient(
        host="192.168.1.100",
        username="admin",
        password="your-password",
        verify_ssl=False,
    ) as client:
        # Get recent import jobs
        imports = client.vm_imports.list(limit=5)

        if not imports:
            print("No import jobs found")
            return

        for imp in imports:
            print(f"\nImport: {imp.name}")
            print(f"  Status: {imp.status}")
            print(f"  Status Info: {imp.status_info or 'N/A'}")

            # Get import logs
            logs = imp.logs.list(limit=10)
            if logs:
                print(f"  Recent logs ({len(logs)}):")
                for log in logs:
                    level = log.get("level", "info")
                    text = log.get("text", "")[:60]
                    print(f"    [{level}] {text}")

            # Check for errors
            errors = imp.logs.list_errors(limit=3)
            if errors:
                print(f"  Errors ({len(errors)}):")
                for err in errors:
                    print(f"    - {err.get('text', '')[:60]}")


def list_exports() -> None:
    """List VM export configurations."""
    print("\n=== List VM Export Configurations ===")

    with VergeClient(
        host="192.168.1.100",
        username="admin",
        password="your-password",
        verify_ssl=False,
    ) as client:
        exports = client.volume_vm_exports.list()
        print(f"Found {len(exports)} export configurations")

        for export in exports:
            print(f"\n  Export: {export.name}")
            print(f"    Key: {export.key}")
            print(f"    Volume: {export.volume_key}")
            print(f"    Status: {export.status}")
            print(f"    Quiesced: {export.quiesced}")
            print(f"    Max Exports: {export.max_exports}")


def create_export_volume() -> None:
    """Create a VM export volume.

    VM export volumes are special NAS volumes designed for storing
    VM snapshots that can be accessed by external backup systems.
    """
    print("\n=== Create VM Export Volume ===")

    with VergeClient(
        host="192.168.1.100",
        username="admin",
        password="your-password",
        verify_ssl=False,
    ) as client:
        # Get NAS service
        nas_services = client.nas_services.list(limit=1)
        if not nas_services:
            print("No NAS service found. Create a NAS service first.")
            return

        nas = nas_services[0]
        print(f"Using NAS service: {nas.name}")

        # Check if export volume already exists
        existing = nas.volumes.list(name="vm-exports")
        if existing:
            print(f"Export volume 'vm-exports' already exists (key={existing[0].key})")
            return

        # Create the export volume
        # NOTE: Uncomment to actually create
        print("\nCreating VM export volume...")
        print("  Name: vm-exports")
        print("  Type: vmexport")
        print("  Description: VM snapshots for backup")

        # export_volume = nas.volumes.create(
        #     name="vm-exports",
        #     volume_type="vmexport",
        #     description="VM snapshots for external backup",
        # )
        # print(f"Created export volume: {export_volume.key}")

        print("\n(Volume creation commented out - uncomment to run)")


def run_export() -> None:
    """Run a VM export operation.

    Exports all VMs with 'Allow Export' enabled to the export volume.
    """
    print("\n=== Run VM Export ===")

    with VergeClient(
        host="192.168.1.100",
        username="admin",
        password="your-password",
        verify_ssl=False,
    ) as client:
        # Get export configurations
        exports = client.volume_vm_exports.list(limit=1)

        if not exports:
            print("No export configurations found.")
            print("Create a VM export volume first using create_export_volume()")
            return

        export = exports[0]
        print(f"Export: {export.name}")
        print(f"Current status: {export.status}")

        if export.is_building:
            print("Export is already in progress")
            return

        # Start the export
        # NOTE: Uncomment to actually run
        print("\nStarting export...")

        # result = export.start(
        #     name="backup-2026-02-01",  # Optional: custom folder name
        #     # vms=[123, 456],          # Optional: specific VMs only
        # )
        # print(f"Export started: {result}")

        print("(Export start commented out - uncomment to run)")


def monitor_export_progress() -> None:
    """Monitor export progress via stats."""
    print("\n=== Monitor Export Progress ===")

    with VergeClient(
        host="192.168.1.100",
        username="admin",
        password="your-password",
        verify_ssl=False,
    ) as client:
        exports = client.volume_vm_exports.list(limit=1)

        if not exports:
            print("No exports found")
            return

        export = exports[0]
        print(f"Export: {export.name}")
        print(f"Status: {export.status}")

        # Get export statistics
        stats = export.stats.list()
        print(f"\nExport Stats ({len(stats)} snapshots):")

        for stat in stats:
            print(f"  - {stat.file_name}")
            print(f"    VMs: {stat.virtual_machines}")
            print(f"    Size: {stat.file_size} bytes")
            print(f"    Created: {stat.timestamp}")


def enable_vm_export() -> None:
    """Enable export on VMs.

    VMs must have 'Allow Export' enabled to be included in exports.
    """
    print("\n=== Enable VM Export ===")

    with VergeClient(
        host="192.168.1.100",
        username="admin",
        password="your-password",
        verify_ssl=False,
    ) as client:
        # Get VMs that don't have export enabled
        vms = client.vms.list(allow_export=False, limit=10)

        if not vms:
            print("All VMs already have export enabled (or no VMs exist)")
            return

        print(f"VMs without export enabled: {len(vms)}")
        for vm in vms:
            print(f"  - {vm.name} (key={vm.key})")

        # Enable export on first VM
        # NOTE: Uncomment to actually enable
        vm = vms[0]
        print(f"\nEnabling export on: {vm.name}")

        # vm.update(allow_export=True)
        # print(f"Export enabled for {vm.name}")

        print("(Update commented out - uncomment to run)")


if __name__ == "__main__":
    print("pyvergeos VM Import/Export Examples")
    print("=" * 50)
    print()
    print("NOTE: Update host/credentials in this file before running.")
    print()

    # Uncomment the examples you want to run:
    # list_imports()
    # import_from_volume()
    # monitor_import_progress()
    # list_exports()
    # create_export_volume()
    # run_export()
    # monitor_export_progress()
    # enable_vm_export()

    print("See the code for examples of:")
    print("  - Listing VM import jobs")
    print("  - Importing VMs from NAS volumes")
    print("  - Monitoring import progress")
    print("  - Creating VM export volumes")
    print("  - Running VM exports")
    print("  - Monitoring export progress")
    print("  - Enabling export on VMs")
