#!/usr/bin/env python3
"""Examples for WireGuard VPN management.

This script demonstrates WireGuard VPN configuration:
- Creating and managing WireGuard interfaces
- Adding and configuring peers
- Site-to-site and remote user configurations
- Managing peer settings and allowed IPs

Prerequisites:
- Python 3.9 or later
- pyvergeos installed
- Environment variables set: VERGE_HOST, VERGE_USERNAME, VERGE_PASSWORD

Usage:
    # Set environment variables
    export VERGE_HOST=192.168.1.100
    export VERGE_USERNAME=admin
    export VERGE_PASSWORD=yourpassword
    export VERGE_VERIFY_SSL=false  # Optional, for self-signed certs

    # Run the examples
    python wireguard_example.py
"""

from __future__ import annotations

import base64
import os
import secrets
import sys

from pyvergeos import VergeClient
from pyvergeos.exceptions import NotFoundError


def generate_fake_pubkey() -> str:
    """Generate a fake WireGuard public key for demonstration."""
    return base64.b64encode(secrets.token_bytes(32)).decode("ascii")


def main() -> None:
    """Run WireGuard VPN management examples."""
    # Connect to VergeOS
    print("=" * 60)
    print("Connecting to VergeOS...")
    print("=" * 60)

    client = VergeClient.from_env()
    client.connect()
    print(f"Connected to VergeOS {client.version}")

    try:
        # Run examples
        query_interfaces(client)
        create_interface_example(client)
        peer_management_example(client)
        site_to_site_example(client)
        remote_user_example(client)
        complete_workflow(client)
    finally:
        client.disconnect()
        print("\nDisconnected from VergeOS")


# =============================================================================
# QUERYING WIREGUARD INTERFACES
# =============================================================================


def query_interfaces(client: VergeClient) -> None:
    """Demonstrate querying WireGuard interfaces."""
    print("\n" + "=" * 60)
    print("QUERYING WIREGUARD INTERFACES")
    print("=" * 60)

    # Get an external network (WireGuard is typically on external networks)
    try:
        network = client.networks.get(name="External")
    except NotFoundError:
        networks = client.networks.list_external()
        if not networks:
            print("No external networks found, skipping interface examples")
            return
        network = networks[0]

    print(f"\nWorking with network: {network.name}")

    # List all WireGuard interfaces
    print("\n--- List WireGuard interfaces ---")
    interfaces = network.wireguard.list()
    print(f"Found {len(interfaces)} WireGuard interfaces:")
    for iface in interfaces:
        status = "enabled" if iface.is_enabled else "disabled"
        print(f"  - {iface.name}")
        print(f"    IP: {iface.ip_address}")
        print(f"    Port: {iface.listen_port}")
        print(f"    MTU: {iface.mtu_display}")
        print(f"    Status: {status}")
        print(f"    Public Key: {iface.public_key[:32]}..." if iface.public_key else "")


# =============================================================================
# CREATING WIREGUARD INTERFACE
# =============================================================================


def create_interface_example(client: VergeClient) -> None:
    """Demonstrate creating a WireGuard interface."""
    print("\n" + "=" * 60)
    print("CREATING WIREGUARD INTERFACE")
    print("=" * 60)

    # Get network
    try:
        network = client.networks.get(name="External")
    except NotFoundError:
        networks = client.networks.list_external()
        if not networks:
            print("No external networks found, skipping examples")
            return
        network = networks[0]

    print(f"\nWorking with network: {network.name}")

    # Create a basic WireGuard interface
    print("\n--- Create WireGuard interface ---")
    wg = network.wireguard.create(
        name="example-wg0",
        ip_address="10.100.0.1/24",
        listen_port=51820,
        description="Example WireGuard VPN interface",
    )
    print(f"Created: {wg.name}")
    print(f"  Key: {wg.key}")
    print(f"  IP Address: {wg.ip_address}")
    print(f"  IP Only: {wg.ip_only}")
    print(f"  Subnet: /{wg.subnet_mask}")
    print(f"  Listen Port: {wg.listen_port}")
    print(f"  MTU: {wg.mtu_display}")
    print(f"  Public Key: {wg.public_key}")
    print(f"  Enabled: {wg.is_enabled}")

    # Update the interface
    print("\n--- Update interface settings ---")
    wg = network.wireguard.update(
        wg.key,
        mtu=1420,
        description="Updated WireGuard interface",
    )
    print(f"Updated MTU: {wg.mtu}")
    print(f"Updated Description: {wg.description}")

    # Get interface by name
    print("\n--- Get interface by name ---")
    fetched = network.wireguard.get(name="example-wg0")
    print(f"Fetched: {fetched.name} (key={fetched.key})")

    # Cleanup
    print("\n--- Cleanup ---")
    network.wireguard.delete(wg.key)
    print(f"Deleted interface: {wg.name}")


# =============================================================================
# PEER MANAGEMENT
# =============================================================================


def peer_management_example(client: VergeClient) -> None:
    """Demonstrate WireGuard peer management."""
    print("\n" + "=" * 60)
    print("PEER MANAGEMENT")
    print("=" * 60)

    # Get network
    try:
        network = client.networks.get(name="External")
    except NotFoundError:
        networks = client.networks.list_external()
        if not networks:
            print("No external networks found, skipping examples")
            return
        network = networks[0]

    print(f"\nWorking with network: {network.name}")

    # Create interface for peer testing
    print("\n--- Create interface for peer testing ---")
    wg = network.wireguard.create(
        name="example-wg-peers",
        ip_address="10.101.0.1/24",
        listen_port=51821,
    )
    print(f"Created interface: {wg.name}")

    # List peers (should be empty)
    print("\n--- List peers ---")
    peers = wg.peers.list()
    print(f"Found {len(peers)} peers")

    # Create a peer
    print("\n--- Create peer ---")
    peer = wg.peers.create(
        name="example-peer-1",
        peer_ip="10.101.0.2",
        public_key=generate_fake_pubkey(),
        allowed_ips="10.101.0.2/32",
        description="Example peer",
    )
    print(f"Created: {peer.name}")
    print(f"  Key: {peer.key}")
    print(f"  Peer IP: {peer.peer_ip}")
    print(f"  Public Key: {peer.public_key[:32]}...")
    print(f"  Allowed IPs: {peer.allowed_ips}")
    print(f"  Firewall Config: {peer.firewall_config_display}")
    print(f"  Enabled: {peer.is_enabled}")

    # Update peer
    print("\n--- Update peer ---")
    peer = wg.peers.update(
        peer.key,
        keepalive=25,
        description="Updated example peer",
    )
    print(f"Updated keepalive: {peer.keepalive}")
    print(f"Updated description: {peer.description}")

    # Get peer by name
    print("\n--- Get peer by name ---")
    fetched = wg.peers.get(name="example-peer-1")
    print(f"Fetched: {fetched.name}")

    # List peers again
    print("\n--- List peers after creation ---")
    peers = wg.peers.list()
    print(f"Found {len(peers)} peers:")
    for p in peers:
        print(f"  - {p.name}: {p.peer_ip}")

    # Delete peer
    print("\n--- Delete peer ---")
    wg.peers.delete(peer.key)
    print(f"Deleted peer: {peer.name}")

    # Cleanup interface
    print("\n--- Cleanup ---")
    network.wireguard.delete(wg.key)
    print(f"Deleted interface: {wg.name}")


# =============================================================================
# SITE-TO-SITE VPN EXAMPLE
# =============================================================================


def site_to_site_example(client: VergeClient) -> None:
    """Demonstrate site-to-site VPN configuration."""
    print("\n" + "=" * 60)
    print("SITE-TO-SITE VPN CONFIGURATION")
    print("=" * 60)

    # Get network
    try:
        network = client.networks.get(name="External")
    except NotFoundError:
        networks = client.networks.list_external()
        if not networks:
            print("No external networks found, skipping examples")
            return
        network = networks[0]

    print(f"\nWorking with network: {network.name}")

    # Create interface
    print("\n--- Create site-to-site interface ---")
    wg = network.wireguard.create(
        name="example-s2s-vpn",
        ip_address="10.200.0.1/24",
        listen_port=51822,
        endpoint_ip="203.0.113.50",  # Public IP for remote peers
        description="Site-to-Site VPN endpoint",
    )
    print(f"Created: {wg.name}")
    print(f"  Endpoint IP (for peers): {wg.endpoint_ip}")

    # Create site-to-site peer
    print("\n--- Create site-to-site peer ---")
    remote_site = wg.peers.create(
        name="remote-office",
        peer_ip="10.200.0.2",
        public_key=generate_fake_pubkey(),
        allowed_ips="192.168.100.0/24,192.168.101.0/24",  # Remote networks
        endpoint="vpn.remote-office.example.com",
        port=51820,
        firewall_config="site_to_site",
        description="Remote office VPN connection",
    )
    print(f"Created: {remote_site.name}")
    print(f"  Peer IP: {remote_site.peer_ip}")
    print(f"  Endpoint: {remote_site.endpoint}:{remote_site.port}")
    print(f"  Allowed IPs (remote networks): {remote_site.allowed_ips}")
    print(f"  Firewall: {remote_site.firewall_config_display}")

    # Note about firewall rules
    print("\n--- Site-to-Site Firewall Notes ---")
    print("""
    With firewall_config="site_to_site", VergeOS automatically:
    - Creates routes for allowed_ips through the WireGuard interface
    - Adds accept rules for traffic from the remote networks

    This allows full bi-directional traffic between sites.
    """)

    # Cleanup
    print("--- Cleanup ---")
    network.wireguard.delete(wg.key)
    print(f"Deleted interface: {wg.name}")


# =============================================================================
# REMOTE USER VPN EXAMPLE
# =============================================================================


def remote_user_example(client: VergeClient) -> None:
    """Demonstrate remote user (road warrior) VPN configuration."""
    print("\n" + "=" * 60)
    print("REMOTE USER VPN CONFIGURATION")
    print("=" * 60)

    # Get network
    try:
        network = client.networks.get(name="External")
    except NotFoundError:
        networks = client.networks.list_external()
        if not networks:
            print("No external networks found, skipping examples")
            return
        network = networks[0]

    print(f"\nWorking with network: {network.name}")

    # Create interface for remote users
    print("\n--- Create remote access interface ---")
    wg = network.wireguard.create(
        name="example-remote-vpn",
        ip_address="10.50.0.1/24",
        listen_port=51823,
        endpoint_ip="vpn.example.com",  # DNS name works too
        description="Remote User VPN Server",
    )
    print(f"Created: {wg.name}")

    # Create remote user peers (roaming clients)
    print("\n--- Create remote user peers ---")

    # Laptop user
    laptop = wg.peers.create(
        name="john-laptop",
        peer_ip="10.50.0.10",
        public_key=generate_fake_pubkey(),
        allowed_ips="10.50.0.10/32",  # Only the peer's tunnel IP
        keepalive=25,  # Keep NAT mappings alive
        firewall_config="remote_user",
        description="John's work laptop",
    )
    print(f"Created: {laptop.name}")
    print(f"  Peer IP: {laptop.peer_ip}")
    print(f"  Keepalive: {laptop.keepalive}s")
    print(f"  Firewall: {laptop.firewall_config_display}")

    # Phone user
    phone = wg.peers.create(
        name="john-phone",
        peer_ip="10.50.0.11",
        public_key=generate_fake_pubkey(),
        allowed_ips="10.50.0.11/32",
        keepalive=25,
        firewall_config="remote_user",
        description="John's mobile phone",
    )
    print(f"Created: {phone.name}")

    # Note about remote user config
    print("\n--- Remote User Firewall Notes ---")
    print("""
    With firewall_config="remote_user", VergeOS automatically:
    - Creates routes for the peer's tunnel IP
    - Adds SNAT rules so outbound traffic from the peer appears
      to come from the VPN server
    - This is ideal for remote users who need to access internal
      resources but shouldn't expose their device to the network

    Note: No endpoint is specified for remote users (they can roam).
    The keepalive setting helps maintain connections through NAT.
    """)

    # Try to get peer configuration (won't work for non-auto-generated peers)
    print("\n--- Peer Configuration ---")
    print("""
    For auto-generated peers (created in VergeOS UI with auto-generate enabled),
    you can retrieve the WireGuard configuration file:

        config = peer.get_config()
        with open("wg0.conf", "w") as f:
            f.write(config)

    Note: Peers created via API don't have auto-generated private keys,
    so get_config() will raise an error. Generate keys on the client device
    and provide the public key when creating the peer.
    """)

    # List all remote user peers
    print("--- List remote user peers ---")
    peers = wg.peers.list()
    print(f"Remote users ({len(peers)}):")
    for p in peers:
        status = "enabled" if p.is_enabled else "disabled"
        print(f"  - {p.name}: {p.peer_ip} [{status}]")

    # Cleanup
    print("\n--- Cleanup ---")
    network.wireguard.delete(wg.key)
    print(f"Deleted interface: {wg.name}")


# =============================================================================
# COMPLETE WORKFLOW
# =============================================================================


def complete_workflow(client: VergeClient) -> None:
    """Demonstrate a complete WireGuard VPN setup workflow."""
    print("\n" + "=" * 60)
    print("COMPLETE WORKFLOW: Branch Office VPN")
    print("=" * 60)

    print("\n--- Workflow steps (documentation only) ---")
    print("""
    # Scenario: Connect a branch office to headquarters

    # 1. Get the external network
    network = client.networks.get(name="External")

    # 2. Create WireGuard interface on HQ side
    hq_wg = network.wireguard.create(
        name="hq-to-branch",
        ip_address="10.99.0.1/30",  # Small tunnel subnet
        listen_port=51820,
        endpoint_ip="203.0.113.10",  # HQ public IP
        description="HQ to Branch Office VPN",
    )

    # 3. Create peer for branch office
    # Note: Get the branch's public key from their WireGuard config
    branch_peer = hq_wg.peers.create(
        name="branch-office-nyc",
        peer_ip="10.99.0.2",
        public_key="<branch_public_key_here>",
        allowed_ips="192.168.200.0/24",  # Branch office LAN
        endpoint="branch.example.com",    # Branch public IP/DNS
        port=51820,
        firewall_config="site_to_site",
        description="NYC Branch Office",
    )

    # 4. The branch office configures their side similarly:
    # - Their WireGuard interface: 10.99.0.2/30
    # - Their peer (HQ): 10.99.0.1, allowed_ips="192.168.100.0/24"
    # - endpoint="203.0.113.10:51820"

    # 5. Apply firewall rules
    network.apply_rules()

    # 6. Traffic between 192.168.100.0/24 (HQ) and
    #    192.168.200.0/24 (Branch) now flows through the tunnel!

    print("Branch office VPN configured!")
    print(f"HQ Public Key: {hq_wg.public_key}")
    print("Share this key with the branch office for their peer config.")
    """)

    # Show example of listing all VPN connections
    print("\n--- Show VPN Summary (example output) ---")
    print("""
    WireGuard VPN Summary:
    =====================

    Interface: hq-to-branch
      Local IP: 10.99.0.1/30
      Listen Port: 51820
      Endpoint: 203.0.113.10

      Peers:
        - branch-office-nyc
          Tunnel IP: 10.99.0.2
          Allowed IPs: 192.168.200.0/24
          Endpoint: branch.example.com:51820
          Last Handshake: 2 minutes ago
    """)


if __name__ == "__main__":
    # Check for required environment variables
    if not os.environ.get("VERGE_HOST"):
        print("Error: VERGE_HOST environment variable not set")
        print("\nUsage:")
        print("  export VERGE_HOST=192.168.1.100")
        print("  export VERGE_USERNAME=admin")
        print("  export VERGE_PASSWORD=yourpassword")
        print("  python wireguard_example.py")
        sys.exit(1)

    main()
