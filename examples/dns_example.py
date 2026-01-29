#!/usr/bin/env python3
"""DNS Zone and Record Management Example.

This example demonstrates how to:
- List DNS zones on a network
- Get a specific DNS zone
- Create various DNS record types
- List and filter DNS records
- Delete DNS records
- Apply DNS configuration

Prerequisites:
- A network with DNS mode set to "bind"
- At least one DNS zone configured on the network

Environment variables:
    VERGE_HOST: VergeOS hostname/IP
    VERGE_USERNAME: Username
    VERGE_PASSWORD: Password
"""

from __future__ import annotations

import os

# Disable SSL warnings for self-signed certificates
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from pyvergeos import VergeClient  # noqa: E402
from pyvergeos.exceptions import NotFoundError  # noqa: E402


def main() -> None:
    # Connect to VergeOS
    print("Connecting to VergeOS...")
    client = VergeClient(
        host=os.environ.get("VERGE_HOST", "192.168.1.100"),
        username=os.environ.get("VERGE_USERNAME", "admin"),
        password=os.environ.get("VERGE_PASSWORD", ""),
        verify_ssl=False,
    )
    print(f"Connected to VergeOS {client.version}")

    try:
        # Find a network with bind DNS enabled
        print("\n=== Finding network with DNS zones ===")
        networks = client.networks.list()
        dns_network = None

        for net in networks:
            if net.get("dns") == "bind":
                zones = net.dns_zones.list()
                if zones:
                    dns_network = net
                    break

        if not dns_network:
            print("No network with bind DNS and zones found.")
            print("DNS zones are typically created through the VergeOS UI.")
            print("\nTo use this example:")
            print("1. Go to a network's settings in VergeOS")
            print("2. Set DNS mode to 'bind'")
            print("3. Create a DNS view and zone")
            return

        print(f"Using network: {dns_network.name}")

        # List all DNS zones
        print("\n=== DNS Zones ===")
        zones = dns_network.dns_zones.list()
        print(f"Found {len(zones)} zone(s):")
        for zone in zones:
            print(f"  - {zone.domain}")
            print(f"    Type: {zone.zone_type_display}")
            print(f"    Nameserver: {zone.nameserver}")
            print(f"    View: {zone.view_name}")

        # Get the first zone for record operations
        zone = zones[0]
        print(f"\n=== Working with zone: {zone.domain} ===")

        # List existing records
        print("\n--- Existing Records ---")
        records = zone.records.list()
        print(f"Found {len(records)} record(s):")
        for rec in records:
            host = rec.host if rec.host else "@"
            extra = ""
            if rec.record_type == "MX":
                extra = f" (priority: {rec.mx_preference})"
            elif rec.record_type == "SRV":
                extra = f" (weight: {rec.weight}, port: {rec.port})"
            print(f"  {host:20} {rec.record_type:6} -> {rec.value}{extra}")

        # Create example DNS records
        print("\n--- Creating Example Records ---")
        created_records = []

        # A record
        print("Creating A record: www -> 10.0.0.100")
        a_record = zone.records.create(
            host="www",
            record_type="A",
            value="10.0.0.100",
            ttl="1h",
        )
        created_records.append(a_record)
        print(f"  Created: {a_record.host} (key={a_record.key})")

        # CNAME record
        print("Creating CNAME record: webserver -> www.{domain}")
        cname = zone.records.create(
            host="webserver",
            record_type="CNAME",
            value=f"www.{zone.domain}",
        )
        created_records.append(cname)
        print(f"  Created: {cname.host} (key={cname.key})")

        # MX record
        print("Creating MX record: @ MX 10 -> mail.{domain}")
        mx = zone.records.create(
            host="",  # root domain
            record_type="MX",
            value=f"mail.{zone.domain}",
            mx_preference=10,
        )
        created_records.append(mx)
        print(f"  Created: MX record (key={mx.key})")

        # TXT record (SPF)
        print("Creating TXT record: SPF")
        txt = zone.records.create(
            host="",
            record_type="TXT",
            value="v=spf1 mx -all",
            description="SPF record",
        )
        created_records.append(txt)
        print(f"  Created: TXT record (key={txt.key})")

        # List all records now
        print("\n--- All Records After Creation ---")
        all_records = zone.records.list()
        for rec in all_records:
            host = rec.host if rec.host else "@"
            print(f"  {host:20} {rec.record_type:6} -> {rec.value}")

        # Filter by type
        print("\n--- Filter: A Records Only ---")
        a_records = zone.records.list(record_type="A")
        for rec in a_records:
            print(f"  {rec.host} -> {rec.value}")

        # Get a specific record
        print("\n--- Get Record by Host ---")
        try:
            www_record = zone.records.get(host="www")
            print(f"  Found: {www_record.host} {www_record.record_type} -> {www_record.value}")
        except NotFoundError:
            print("  Record not found")

        # Apply DNS changes
        print("\n--- Applying DNS Configuration ---")
        dns_network.apply_dns()
        print("  DNS configuration applied!")

        # Clean up created records
        print("\n--- Cleaning Up ---")
        for rec in created_records:
            print(f"  Deleting: {rec.host or '@'} {rec.record_type} -> {rec.value}")
            zone.records.delete(rec.key)

        # Apply DNS again after cleanup
        dns_network.apply_dns()
        print("  Cleanup complete!")

        # Verify cleanup
        print("\n--- Verification ---")
        remaining = zone.records.list()
        print(f"  Remaining records: {len(remaining)}")

    finally:
        client.disconnect()
        print("\nDisconnected from VergeOS")


if __name__ == "__main__":
    main()
