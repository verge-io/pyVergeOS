#!/usr/bin/env python3
"""Examples for network routing protocol configuration.

This script demonstrates routing protocol management tasks:
- BGP (Border Gateway Protocol) configuration
  - BGP routers and router commands
  - BGP interfaces and interface commands
  - BGP route maps and route map commands
  - BGP IP commands (prefix-lists, as-paths)
- OSPF (Open Shortest Path First) commands
- EIGRP (Enhanced Interior Gateway Routing Protocol) routers and commands

Prerequisites:
- Python 3.9 or later
- pyvergeos installed
- Environment variables set: VERGE_HOST, VERGE_USERNAME, VERGE_PASSWORD
- A network with routing capabilities (typically an external network)

Usage:
    # Set environment variables
    export VERGE_HOST=192.168.1.100
    export VERGE_USERNAME=admin
    export VERGE_PASSWORD=yourpassword
    export VERGE_VERIFY_SSL=false  # Optional, for self-signed certs

    # Run the examples
    python routing_example.py
"""

from __future__ import annotations

import os
import sys

from pyvergeos import VergeClient
from pyvergeos.exceptions import NotFoundError


def main() -> None:
    """Run routing protocol examples."""
    # Connect to VergeOS
    print("=" * 60)
    print("Connecting to VergeOS...")
    print("=" * 60)

    client = VergeClient.from_env()
    client.connect()
    print(f"Connected to VergeOS {client.version}")

    try:
        # Run examples
        bgp_router_examples(client)
        bgp_interface_examples(client)
        bgp_route_map_examples(client)
        bgp_ip_command_examples(client)
        ospf_command_examples(client)
        eigrp_router_examples(client)
        complete_workflow(client)
    finally:
        client.disconnect()
        print("\nDisconnected from VergeOS")


# =============================================================================
# BGP ROUTER EXAMPLES
# =============================================================================


def bgp_router_examples(client: VergeClient) -> None:
    """Demonstrate BGP router configuration."""
    print("\n" + "=" * 60)
    print("BGP ROUTER CONFIGURATION")
    print("=" * 60)

    # Get a network to work with (External network typically has routing)
    try:
        network = client.networks.get(name="External")
    except NotFoundError:
        print("External network not found, skipping BGP examples")
        return

    print(f"\nWorking with network: {network.name}")

    # Access routing protocols via the network
    routing = network.routing

    # List existing BGP routers
    print("\n--- List BGP routers ---")
    routers = routing.bgp_routers.list()
    print(f"Found {len(routers)} BGP routers:")
    for router in routers:
        print(f"  - Router key={router.key}, ASN={router.get('asn')}")

    # Clean up any existing test routers (ASN 64999)
    for existing in routers:
        if existing.get("asn") == 64999:
            print(f"Cleaning up existing test router ASN 64999...")
            # Delete any commands first
            for cmd in existing.commands.list():
                existing.commands.delete(cmd.key)
            routing.bgp_routers.delete(existing.key)

    # Create a BGP router (only requires ASN) - use private ASN 64999
    print("\n--- Create BGP router ---")
    router = routing.bgp_routers.create(asn=64999)
    print(f"Created BGP router: key={router.key}, ASN={router.get('asn')}")

    # Get router by key
    print("\n--- Get router by key ---")
    fetched = routing.bgp_routers.get(key=router.key)
    print(f"Found router: ASN={fetched.get('asn')}")

    # Add router commands (BGP configuration statements)
    # Note: Commands use separate 'command' (type) and 'params' (arguments) fields
    # Valid command types: aggregate-address, bgp, bmp, coalesce-time, distance,
    # maximum-paths, neighbor, network, read-quanta, redistribute, segment-routing,
    # table-map, timers, update-delay, vnc, vrf-policy, write-quanta
    print("\n--- Add BGP router commands ---")

    # Add router-id using 'bgp' command type
    router_id_cmd = router.commands.create(
        command="bgp",
        params="router-id 10.0.0.1",
    )
    print(f"Created command: {router_id_cmd.get('command')} {router_id_cmd.get('params')}")

    # Add neighbor command
    neighbor_cmd = router.commands.create(
        command="neighbor",
        params="10.0.0.2 remote-as 65002",
    )
    print(f"Created command: {neighbor_cmd.get('command')} {neighbor_cmd.get('params')}")

    # Add network advertisement
    network_cmd = router.commands.create(
        command="network",
        params="192.168.0.0/24",
    )
    print(f"Created command: {network_cmd.get('command')} {network_cmd.get('params')}")

    # List router commands
    print("\n--- List router commands ---")
    commands = router.commands.list()
    print(f"Found {len(commands)} commands:")
    for cmd in commands:
        print(f"  - {cmd.get('command')} {cmd.get('params')}")

    # Update a command
    print("\n--- Update command ---")
    updated_cmd = router.commands.update(
        router_id_cmd.key,
        params="router-id 10.0.0.100",
    )
    print(f"Updated command: {updated_cmd.get('command')} {updated_cmd.get('params')}")

    # Delete commands
    print("\n--- Cleanup commands ---")
    for cmd in commands:
        router.commands.delete(cmd.key)
    print("Deleted all router commands")

    # Delete the router
    print("\n--- Cleanup router ---")
    routing.bgp_routers.delete(router.key)
    print("Deleted BGP router")


# =============================================================================
# BGP INTERFACE EXAMPLES
# =============================================================================


def bgp_interface_examples(client: VergeClient) -> None:
    """Demonstrate BGP interface configuration."""
    print("\n" + "=" * 60)
    print("BGP INTERFACE CONFIGURATION")
    print("=" * 60)

    try:
        network = client.networks.get(name="External")
    except NotFoundError:
        print("External network not found, skipping BGP interface examples")
        return

    print(f"\nWorking with network: {network.name}")
    routing = network.routing

    # List existing BGP interfaces
    print("\n--- List BGP interfaces ---")
    interfaces = routing.bgp_interfaces.list()
    print(f"Found {len(interfaces)} BGP interfaces:")
    for iface in interfaces:
        print(f"  - Interface key={iface.key}, name={iface.get('name')}")

    # Note: BGP interfaces require network configuration (interface_vnet, ipaddress, network)
    # Creating BGP interfaces involves creating virtual networks, so we show usage examples
    print("\n--- BGP interface creation (example code) ---")
    print("""
    # BGP interfaces require network configuration
    # Example (not executed - requires specific network setup):
    interface = routing.bgp_interfaces.create(
        name="peer-upstream",
        description="Interface for upstream BGP peering",
        ipaddress="10.0.0.1",
        network="10.0.0.0/30",
        interface_vnet=external_network_key,
    )

    # Add interface commands (command type + params)
    interface.commands.create(command="ip", params="ospf area 0")
    interface.commands.create(command="bandwidth", params="1000000")
    """)

    # If interfaces exist, show their commands
    if interfaces:
        iface = interfaces[0]
        print(f"\n--- Commands for interface '{iface.get('name')}' ---")
        commands = iface.commands.list()
        print(f"Found {len(commands)} commands:")
        for cmd in commands:
            print(f"  - {cmd.get('command')}")


# =============================================================================
# BGP ROUTE MAP EXAMPLES
# =============================================================================


def bgp_route_map_examples(client: VergeClient) -> None:
    """Demonstrate BGP route map configuration."""
    print("\n" + "=" * 60)
    print("BGP ROUTE MAP CONFIGURATION")
    print("=" * 60)

    try:
        network = client.networks.get(name="External")
    except NotFoundError:
        print("External network not found, skipping route map examples")
        return

    print(f"\nWorking with network: {network.name}")
    routing = network.routing

    # List existing route maps
    print("\n--- List BGP route maps ---")
    route_maps = routing.bgp_route_maps.list()
    print(f"Found {len(route_maps)} route maps:")
    for rm in route_maps:
        permit_str = "permit" if rm.get("permit") else "deny"
        print(f"  - {rm.get('tag')} seq {rm.get('sequence')} {permit_str} (key={rm.key})")

    # Clean up any existing test route maps
    for existing in route_maps:
        if existing.get("tag") == "EXAMPLE-FILTER":
            print(f"Cleaning up existing test route map...")
            for cmd in existing.commands.list():
                existing.commands.delete(cmd.key)
            routing.bgp_route_maps.delete(existing.key)

    # Create a route map entry (uses tag + sequence + permit)
    print("\n--- Create route map entry ---")
    route_map = routing.bgp_route_maps.create(
        tag="EXAMPLE-FILTER",
        sequence=10,
        permit=True,
    )
    print(f"Created route map: {route_map.get('tag')} seq {route_map.get('sequence')}")

    # Add route map commands (command type + params)
    print("\n--- Add route map commands ---")

    # Match prefix list
    match_cmd = route_map.commands.create(
        command="match",
        params="ip address prefix-list ALLOWED-PREFIXES",
    )
    print(f"Created: {match_cmd.get('command')} {match_cmd.get('params')}")

    # Set local preference
    set_cmd = route_map.commands.create(
        command="set",
        params="local-preference 200",
    )
    print(f"Created: {set_cmd.get('command')} {set_cmd.get('params')}")

    # List route map commands
    print("\n--- List route map commands ---")
    commands = route_map.commands.list()
    print(f"Found {len(commands)} commands:")
    for cmd in commands:
        print(f"  - {cmd.get('command')} {cmd.get('params')}")

    # Create a second route map entry (deny clause)
    print("\n--- Create deny clause ---")
    deny_map = routing.bgp_route_maps.create(
        tag="EXAMPLE-FILTER",
        sequence=100,
        permit=False,
    )
    print(f"Created: {deny_map.get('tag')} seq {deny_map.get('sequence')} deny")

    # Cleanup
    print("\n--- Cleanup ---")
    for cmd in commands:
        route_map.commands.delete(cmd.key)
    routing.bgp_route_maps.delete(route_map.key)
    routing.bgp_route_maps.delete(deny_map.key)
    print("Deleted route maps and commands")


# =============================================================================
# BGP IP COMMAND EXAMPLES
# =============================================================================


def bgp_ip_command_examples(client: VergeClient) -> None:
    """Demonstrate BGP IP command configuration (prefix-lists, as-paths)."""
    print("\n" + "=" * 60)
    print("BGP IP COMMANDS (Prefix Lists, AS Paths)")
    print("=" * 60)

    try:
        network = client.networks.get(name="External")
    except NotFoundError:
        print("External network not found, skipping IP command examples")
        return

    print(f"\nWorking with network: {network.name}")
    routing = network.routing

    # List existing IP commands
    print("\n--- List BGP IP commands ---")
    ip_commands = routing.bgp_ip_commands.list()
    print(f"Found {len(ip_commands)} IP commands:")
    for cmd in ip_commands:
        print(f"  - {cmd.get('command')}")

    # Create prefix-list entries (command type + params)
    print("\n--- Create prefix-list commands ---")

    # Allow specific prefixes
    prefix1 = routing.bgp_ip_commands.create(
        command="prefix-list",
        params="ALLOWED-PREFIXES seq 10 permit 10.0.0.0/8 le 24",
    )
    print(f"Created: {prefix1.get('command')} {prefix1.get('params')}")

    prefix2 = routing.bgp_ip_commands.create(
        command="prefix-list",
        params="ALLOWED-PREFIXES seq 20 permit 172.16.0.0/12 le 24",
    )
    print(f"Created: {prefix2.get('command')} {prefix2.get('params')}")

    prefix3 = routing.bgp_ip_commands.create(
        command="prefix-list",
        params="ALLOWED-PREFIXES seq 30 permit 192.168.0.0/16 le 24",
    )
    print(f"Created: {prefix3.get('command')} {prefix3.get('params')}")

    # Deny everything else (implicit in many implementations, but explicit is clearer)
    prefix_deny = routing.bgp_ip_commands.create(
        command="prefix-list",
        params="ALLOWED-PREFIXES seq 100 deny any",
    )
    print(f"Created: {prefix_deny.get('command')} {prefix_deny.get('params')}")

    # Create AS-path access list
    print("\n--- Create AS-path access list ---")
    aspath = routing.bgp_ip_commands.create(
        command="as-path",
        params="access-list 10 permit ^65002_",
    )
    print(f"Created: {aspath.get('command')} {aspath.get('params')}")

    # List all IP commands
    print("\n--- List all IP commands ---")
    all_commands = routing.bgp_ip_commands.list()
    print(f"Found {len(all_commands)} IP commands")

    # Cleanup
    print("\n--- Cleanup ---")
    for cmd in [prefix1, prefix2, prefix3, prefix_deny, aspath]:
        routing.bgp_ip_commands.delete(cmd.key)
    print("Deleted all test IP commands")


# =============================================================================
# OSPF COMMAND EXAMPLES
# =============================================================================


def ospf_command_examples(client: VergeClient) -> None:
    """Demonstrate OSPF command configuration."""
    print("\n" + "=" * 60)
    print("OSPF COMMAND CONFIGURATION")
    print("=" * 60)

    try:
        network = client.networks.get(name="External")
    except NotFoundError:
        print("External network not found, skipping OSPF examples")
        return

    print(f"\nWorking with network: {network.name}")
    routing = network.routing

    # List existing OSPF commands
    print("\n--- List OSPF commands ---")
    ospf_commands = routing.ospf_commands.list()
    print(f"Found {len(ospf_commands)} OSPF commands:")
    for cmd in ospf_commands:
        print(f"  - {cmd.get('command')}")

    # Create OSPF configuration commands (command type + params)
    print("\n--- Create OSPF commands ---")

    # Set router ID
    router_id = routing.ospf_commands.create(
        command="router-id",
        params="10.0.0.1",
    )
    print(f"Created: {router_id.get('command')} {router_id.get('params')}")

    # Configure area 0 (backbone)
    area_cmd = routing.ospf_commands.create(
        command="network",
        params="10.0.0.0/24 area 0",
    )
    print(f"Created: {area_cmd.get('command')} {area_cmd.get('params')}")

    # Configure additional network in area 1
    area1_cmd = routing.ospf_commands.create(
        command="network",
        params="192.168.1.0/24 area 1",
    )
    print(f"Created: {area1_cmd.get('command')} {area1_cmd.get('params')}")

    # Configure passive interface
    passive_cmd = routing.ospf_commands.create(
        command="passive-interface",
        params="eth0",
    )
    print(f"Created: {passive_cmd.get('command')} {passive_cmd.get('params')}")

    # Configure redistribution
    redistribute = routing.ospf_commands.create(
        command="redistribute",
        params="connected",
    )
    print(f"Created: {redistribute.get('command')} {redistribute.get('params')}")

    # List all OSPF commands
    print("\n--- List all OSPF commands ---")
    all_commands = routing.ospf_commands.list()
    print(f"Found {len(all_commands)} OSPF commands:")
    for cmd in all_commands:
        print(f"  - {cmd.get('command')} {cmd.get('params')}")

    # Update a command
    print("\n--- Update OSPF command ---")
    updated = routing.ospf_commands.update(
        router_id.key,
        params="10.0.0.100",
    )
    print(f"Updated: {updated.get('command')} {updated.get('params')}")

    # Cleanup
    print("\n--- Cleanup ---")
    for cmd in [router_id, area_cmd, area1_cmd, passive_cmd, redistribute]:
        routing.ospf_commands.delete(cmd.key)
    print("Deleted all test OSPF commands")


# =============================================================================
# EIGRP ROUTER EXAMPLES
# =============================================================================


def eigrp_router_examples(client: VergeClient) -> None:
    """Demonstrate EIGRP router configuration."""
    print("\n" + "=" * 60)
    print("EIGRP ROUTER CONFIGURATION")
    print("=" * 60)

    try:
        network = client.networks.get(name="External")
    except NotFoundError:
        print("External network not found, skipping EIGRP examples")
        return

    print(f"\nWorking with network: {network.name}")
    routing = network.routing

    # List existing EIGRP routers
    print("\n--- List EIGRP routers ---")
    routers = routing.eigrp_routers.list()
    print(f"Found {len(routers)} EIGRP routers:")
    for router in routers:
        print(f"  - Router key={router.key}, ASN={router.get('asn')}")

    # Clean up any existing test routers (ASN 999)
    for existing in routers:
        if existing.get("asn") == 999:
            print(f"Cleaning up existing test router ASN 999...")
            for cmd in existing.commands.list():
                existing.commands.delete(cmd.key)
            routing.eigrp_routers.delete(existing.key)

    # Create an EIGRP router (only requires ASN) - use private ASN 999
    print("\n--- Create EIGRP router ---")
    router = routing.eigrp_routers.create(asn=999)
    print(f"Created EIGRP router: key={router.key}, ASN={router.get('asn')}")

    # Add router commands (command type + params)
    print("\n--- Add EIGRP router commands ---")

    # Set router ID
    router_id = router.commands.create(
        command="eigrp",
        params="router-id 10.0.0.1",
    )
    print(f"Created: {router_id.get('command')} {router_id.get('params')}")

    # Configure network
    network_cmd = router.commands.create(
        command="network",
        params="10.0.0.0/24",
    )
    print(f"Created: {network_cmd.get('command')} {network_cmd.get('params')}")

    # Configure additional network
    network2_cmd = router.commands.create(
        command="network",
        params="192.168.0.0/16",
    )
    print(f"Created: {network2_cmd.get('command')} {network2_cmd.get('params')}")

    # Configure redistribution
    redistribute = router.commands.create(
        command="redistribute",
        params="connected",
    )
    print(f"Created: {redistribute.get('command')} {redistribute.get('params')}")

    # List router commands
    print("\n--- List EIGRP router commands ---")
    commands = router.commands.list()
    print(f"Found {len(commands)} commands:")
    for cmd in commands:
        print(f"  - {cmd.get('command')} {cmd.get('params')}")

    # Cleanup
    print("\n--- Cleanup ---")
    for cmd in commands:
        router.commands.delete(cmd.key)
    routing.eigrp_routers.delete(router.key)
    print("Deleted EIGRP router and commands")


# =============================================================================
# COMPLETE WORKFLOW
# =============================================================================


def complete_workflow(client: VergeClient) -> None:
    """Demonstrate a complete BGP peering setup workflow."""
    print("\n" + "=" * 60)
    print("COMPLETE WORKFLOW: BGP Peering Setup")
    print("=" * 60)

    print("\n--- Workflow steps (not executed) ---")
    print("""
    # 1. Get the external network
    network = client.networks.get(name="External")
    routing = network.routing

    # 2. Create prefix lists for route filtering (command + params)
    routing.bgp_ip_commands.create(
        command="prefix-list",
        params="CUSTOMER-PREFIXES seq 10 permit 203.0.113.0/24"
    )
    routing.bgp_ip_commands.create(
        command="prefix-list",
        params="CUSTOMER-PREFIXES seq 100 deny any"
    )

    # 3. Create route map entries (tag + sequence + permit/deny)
    permit_entry = routing.bgp_route_maps.create(
        tag="PEER-INBOUND",
        sequence=10,
        permit=True
    )
    permit_entry.commands.create(
        command="match",
        params="ip address prefix-list CUSTOMER-PREFIXES"
    )
    permit_entry.commands.create(command="set", params="local-preference 150")

    # Add default deny
    routing.bgp_route_maps.create(tag="PEER-INBOUND", sequence=100, permit=False)

    # 4. Create BGP router (ASN only)
    bgp_router = routing.bgp_routers.create(asn=65001)

    # 5. Configure the router with commands (command type + params)
    bgp_router.commands.create(command="bgp", params="router-id 192.0.2.1")
    bgp_router.commands.create(command="neighbor", params="192.0.2.2 remote-as 65002")
    bgp_router.commands.create(command="neighbor", params="192.0.2.2 route-map PEER-INBOUND in")
    bgp_router.commands.create(command="network", params="203.0.113.0/24")

    # 6. Create BGP interface (requires network configuration)
    interface = routing.bgp_interfaces.create(
        name="upstream-peer",
        description="Interface for upstream BGP peering",
        ipaddress="192.0.2.1",
        network="192.0.2.0/30",
        interface_vnet=external_network_key,  # Reference to parent network
    )
    interface.commands.create(command="ip", params="ospf area 0")

    print("BGP peering configuration complete!")
    """)

    # Show current routing configuration
    print("\n--- Current Routing Configuration ---")
    try:
        network = client.networks.get(name="External")
        routing = network.routing

        bgp_routers = routing.bgp_routers.list()
        bgp_interfaces = routing.bgp_interfaces.list()
        bgp_route_maps = routing.bgp_route_maps.list()
        bgp_ip_commands = routing.bgp_ip_commands.list()
        ospf_commands = routing.ospf_commands.list()
        eigrp_routers = routing.eigrp_routers.list()

        print(f"Network: {network.name}")
        print(f"  BGP Routers: {len(bgp_routers)}")
        print(f"  BGP Interfaces: {len(bgp_interfaces)}")
        print(f"  BGP Route Maps: {len(bgp_route_maps)}")
        print(f"  BGP IP Commands: {len(bgp_ip_commands)}")
        print(f"  OSPF Commands: {len(ospf_commands)}")
        print(f"  EIGRP Routers: {len(eigrp_routers)}")
    except NotFoundError:
        print("External network not found")


if __name__ == "__main__":
    # Check for required environment variables
    if not os.environ.get("VERGE_HOST"):
        print("Error: VERGE_HOST environment variable not set")
        print("\nUsage:")
        print("  export VERGE_HOST=192.168.1.100")
        print("  export VERGE_USERNAME=admin")
        print("  export VERGE_PASSWORD=yourpassword")
        print("  python routing_example.py")
        sys.exit(1)

    main()
