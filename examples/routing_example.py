#!/usr/bin/env python3
"""Example: Network Routing Protocols with pyvergeos.

This example demonstrates configuring dynamic routing protocols:
- BGP (Border Gateway Protocol) configuration
- OSPF (Open Shortest Path First) configuration
- EIGRP (Enhanced Interior Gateway Routing Protocol) configuration
- Route maps and prefix lists
- Viewing routing status

Prerequisites:
    - Environment variables configured (or modify credentials below)
    - Network with routing enabled
    - Understanding of routing protocols for production use

Environment Variables:
    VERGE_HOST: VergeOS hostname or IP
    VERGE_USERNAME: Admin username
    VERGE_PASSWORD: Admin password
    VERGE_VERIFY_SSL: Set to 'false' for self-signed certs

WARNING:
    Routing configuration changes can affect network connectivity.
    Test in a lab environment before applying to production.

Usage:
    export VERGE_HOST=192.168.1.100
    export VERGE_USERNAME=admin
    export VERGE_PASSWORD=yourpassword
    export VERGE_VERIFY_SSL=false

    python routing_example.py
"""

from __future__ import annotations

from pyvergeos import VergeClient
from pyvergeos.exceptions import NotFoundError


def list_networks_with_routing() -> None:
    """List networks and their routing capabilities."""
    print("=== Networks with Routing ===")

    with VergeClient(
        host="192.168.1.100",
        username="admin",
        password="your-password",
        verify_ssl=False,
    ) as client:
        networks = client.networks.list()
        print(f"Found {len(networks)} networks")

        for net in networks:
            print(f"\n  Network: {net.name}")
            print(f"    Key: {net.key}")
            print(f"    Type: {net.network_type}")
            print(f"    Status: {net.status}")
            print(f"    IP: {net.ip_address}")
            print(f"    Network: {net.network_address}")


def view_bgp_configuration() -> None:
    """View existing BGP configuration on a network."""
    print("\n=== BGP Configuration ===")

    with VergeClient(
        host="192.168.1.100",
        username="admin",
        password="your-password",
        verify_ssl=False,
    ) as client:
        # Get the network
        try:
            network = client.networks.get(name="External")
        except NotFoundError:
            # Try to get any network
            networks = client.networks.list(limit=1)
            if not networks:
                print("No networks found")
                return
            network = networks[0]

        print(f"Network: {network.name}")

        # Access routing manager
        routing = network.routing

        # List BGP routers
        bgp_routers = routing.bgp_routers.list()
        print(f"\nBGP Routers ({len(bgp_routers)}):")

        for router in bgp_routers:
            print(f"  - ASN: {router.asn}")
            print(f"    Key: {router.key}")
            print(f"    Router ID: {router.router_id}")
            print(f"    Enabled: {router.is_enabled}")

            # List BGP commands (neighbor configuration, etc.)
            commands = router.commands.list()
            if commands:
                print(f"    Commands ({len(commands)}):")
                for cmd in commands[:5]:  # Show first 5
                    print(f"      {cmd.command} {cmd.params or ''}")

        # List BGP interfaces
        bgp_interfaces = routing.bgp_interfaces.list()
        print(f"\nBGP Interfaces ({len(bgp_interfaces)}):")

        for intf in bgp_interfaces:
            print(f"  - {intf.name}")
            print(f"    IP: {intf.ip_address}")
            print(f"    Network: {intf.network_address}")

        # List route maps
        route_maps = routing.bgp_route_maps.list()
        print(f"\nBGP Route Maps ({len(route_maps)}):")

        for rm in route_maps:
            print(f"  - {rm.name}")
            print(f"    Tag: {rm.tag}")
            print(f"    Sequence: {rm.sequence}")
            print(f"    Permit: {rm.is_permit}")

        # List IP commands (prefix-lists, as-paths)
        ip_commands = routing.bgp_ip_commands.list()
        print(f"\nBGP IP Commands ({len(ip_commands)}):")

        for ipc in ip_commands[:10]:  # Show first 10
            print(f"  - {ipc.command} {ipc.params or ''}")


def configure_bgp_basic() -> None:
    """Configure basic BGP routing.

    This example shows how to set up a simple BGP peering session.
    """
    print("\n=== Configure BGP ===")

    with VergeClient(
        host="192.168.1.100",
        username="admin",
        password="your-password",
        verify_ssl=False,
    ) as client:
        # Get the network
        try:
            network = client.networks.get(name="WAN")
        except NotFoundError:
            print("Network 'WAN' not found")
            print("Please create a WAN network or modify this example")
            return

        print(f"Network: {network.name}")
        routing = network.routing

        # Check if BGP is already configured
        existing_routers = routing.bgp_routers.list()
        if existing_routers:
            print("BGP already configured. Existing routers:")
            for r in existing_routers:
                print(f"  - ASN {r.asn}")
            return

        # Create BGP router
        # NOTE: Uncomment to actually configure
        print("\nConfiguring BGP router...")
        print("  ASN: 65001")
        print("  Router ID: 10.0.0.1")

        # bgp_router = routing.bgp_routers.create(
        #     asn=65001,
        #     router_id="10.0.0.1",
        #     enabled=True,
        # )
        # print(f"Created BGP router: ASN {bgp_router.asn}")

        # Add neighbor configuration
        print("\nAdding BGP neighbor...")
        print("  Neighbor: 10.0.0.2")
        print("  Remote AS: 65002")

        # bgp_router.commands.create(
        #     command="neighbor",
        #     params="10.0.0.2 remote-as 65002",
        # )

        # bgp_router.commands.create(
        #     command="neighbor",
        #     params="10.0.0.2 description ISP-Upstream",
        # )

        # bgp_router.commands.create(
        #     command="neighbor",
        #     params="10.0.0.2 timers 30 90",
        # )

        # Advertise networks
        print("\nAdvertising networks...")
        print("  Network: 192.168.0.0/16")

        # bgp_router.commands.create(
        #     command="network",
        #     params="192.168.0.0/16",
        # )

        # Apply changes
        print("\nApplying routing changes...")
        # network.apply_rules()

        print("\n(Configuration commented out - uncomment to run)")


def configure_bgp_route_maps() -> None:
    """Configure BGP route maps for filtering.

    Route maps allow fine-grained control over which routes
    are advertised or accepted.
    """
    print("\n=== Configure BGP Route Maps ===")

    with VergeClient(
        host="192.168.1.100",
        username="admin",
        password="your-password",
        verify_ssl=False,
    ) as client:
        try:
            network = client.networks.get(name="WAN")
        except NotFoundError:
            print("Network 'WAN' not found")
            return

        _ = network.routing  # noqa: F841 - used in commented code below

        # Create prefix list first
        # NOTE: Uncomment to actually configure
        print("Creating IP prefix list...")
        print("  Name: ALLOWED-NETS")
        print("  Permit: 10.0.0.0/8 le 24")

        # routing.bgp_ip_commands.create(
        #     command="ip",
        #     params="prefix-list ALLOWED-NETS seq 10 permit 10.0.0.0/8 le 24",
        # )

        # routing.bgp_ip_commands.create(
        #     command="ip",
        #     params="prefix-list ALLOWED-NETS seq 20 permit 192.168.0.0/16 le 24",
        # )

        # routing.bgp_ip_commands.create(
        #     command="ip",
        #     params="prefix-list ALLOWED-NETS seq 100 deny any",
        # )

        # Create route map
        print("\nCreating route map...")
        print("  Name: OUTBOUND-FILTER")
        print("  Match: prefix-list ALLOWED-NETS")

        # route_map = routing.bgp_route_maps.create(
        #     name="OUTBOUND-FILTER",
        #     tag="outbound",
        #     sequence=10,
        #     permit=True,
        # )

        # Add match condition
        # route_map.commands.create(
        #     command="match",
        #     params="ip address prefix-list ALLOWED-NETS",
        # )

        print("\n(Configuration commented out - uncomment to run)")


def view_ospf_configuration() -> None:
    """View existing OSPF configuration."""
    print("\n=== OSPF Configuration ===")

    with VergeClient(
        host="192.168.1.100",
        username="admin",
        password="your-password",
        verify_ssl=False,
    ) as client:
        try:
            network = client.networks.get(name="Internal")
        except NotFoundError:
            networks = client.networks.list(limit=1)
            if not networks:
                print("No networks found")
                return
            network = networks[0]

        print(f"Network: {network.name}")
        routing = network.routing

        # List OSPF commands
        ospf_commands = routing.ospf_commands.list()
        print(f"\nOSPF Commands ({len(ospf_commands)}):")

        for cmd in ospf_commands:
            neg = "no " if cmd.is_negated else ""
            print(f"  {neg}{cmd.command} {cmd.params or ''}")


def configure_ospf_basic() -> None:
    """Configure basic OSPF routing.

    OSPF is commonly used for internal routing within an organization.
    """
    print("\n=== Configure OSPF ===")

    with VergeClient(
        host="192.168.1.100",
        username="admin",
        password="your-password",
        verify_ssl=False,
    ) as client:
        try:
            network = client.networks.get(name="Internal")
        except NotFoundError:
            print("Network 'Internal' not found")
            return

        print(f"Network: {network.name}")
        _ = network.routing  # noqa: F841 - used in commented code below

        # Configure OSPF
        # NOTE: Uncomment to actually configure
        print("\nConfiguring OSPF...")

        # Enable OSPF process
        print("  Router OSPF 1")

        # routing.ospf_commands.create(
        #     command="router",
        #     params="ospf 1",
        # )

        # Set router ID
        print("  Router ID: 10.0.0.1")

        # routing.ospf_commands.create(
        #     command="router-id",
        #     params="10.0.0.1",
        # )

        # Add network to OSPF
        print("  Network: 10.0.0.0/24 area 0")

        # routing.ospf_commands.create(
        #     command="network",
        #     params="10.0.0.0/24 area 0",
        # )

        # Make interfaces passive by default
        print("  Passive interface default")

        # routing.ospf_commands.create(
        #     command="passive-interface",
        #     params="default",
        # )

        # Apply changes
        print("\nApplying routing changes...")
        # network.apply_rules()

        print("\n(Configuration commented out - uncomment to run)")


def view_eigrp_configuration() -> None:
    """View existing EIGRP configuration."""
    print("\n=== EIGRP Configuration ===")

    with VergeClient(
        host="192.168.1.100",
        username="admin",
        password="your-password",
        verify_ssl=False,
    ) as client:
        try:
            network = client.networks.get(name="Internal")
        except NotFoundError:
            networks = client.networks.list(limit=1)
            if not networks:
                print("No networks found")
                return
            network = networks[0]

        print(f"Network: {network.name}")
        routing = network.routing

        # List EIGRP routers
        eigrp_routers = routing.eigrp_routers.list()
        print(f"\nEIGRP Routers ({len(eigrp_routers)}):")

        for router in eigrp_routers:
            print(f"  - ASN: {router.asn}")
            print(f"    Key: {router.key}")
            print(f"    Router ID: {router.router_id}")

            # List EIGRP commands
            commands = router.commands.list()
            if commands:
                print(f"    Commands ({len(commands)}):")
                for cmd in commands[:5]:
                    print(f"      {cmd.command} {cmd.params or ''}")


def configure_eigrp_basic() -> None:
    """Configure basic EIGRP routing.

    EIGRP is a Cisco-developed protocol commonly used in enterprise networks.
    """
    print("\n=== Configure EIGRP ===")

    with VergeClient(
        host="192.168.1.100",
        username="admin",
        password="your-password",
        verify_ssl=False,
    ) as client:
        try:
            network = client.networks.get(name="Internal")
        except NotFoundError:
            print("Network 'Internal' not found")
            return

        print(f"Network: {network.name}")
        routing = network.routing

        # Check if EIGRP is already configured
        existing_routers = routing.eigrp_routers.list()
        if existing_routers:
            print("EIGRP already configured")
            return

        # Configure EIGRP
        # NOTE: Uncomment to actually configure
        print("\nConfiguring EIGRP...")
        print("  ASN: 100")
        print("  Router ID: 10.0.0.1")

        # eigrp_router = routing.eigrp_routers.create(
        #     asn=100,
        #     router_id="10.0.0.1",
        #     enabled=True,
        # )
        # print(f"Created EIGRP router: ASN {eigrp_router.asn}")

        # Add network
        print("\n  Network: 10.0.0.0/24")

        # eigrp_router.commands.create(
        #     command="network",
        #     params="10.0.0.0/24",
        # )

        # Apply changes
        print("\nApplying routing changes...")
        # network.apply_rules()

        print("\n(Configuration commented out - uncomment to run)")


def cleanup_routing() -> None:
    """Remove routing configuration.

    WARNING: This removes all routing configuration from a network.
    """
    print("\n=== Cleanup Routing Configuration ===")

    with VergeClient(
        host="192.168.1.100",
        username="admin",
        password="your-password",
        verify_ssl=False,
    ) as client:
        try:
            network = client.networks.get(name="Internal")
        except NotFoundError:
            print("Network not found")
            return

        routing = network.routing

        # NOTE: Uncomment to actually delete
        print("This would delete all routing configuration:")

        # Delete BGP routers
        bgp_routers = routing.bgp_routers.list()
        for router in bgp_routers:
            print(f"  - Delete BGP router ASN {router.asn}")
            # router.delete()

        # Delete EIGRP routers
        eigrp_routers = routing.eigrp_routers.list()
        for router in eigrp_routers:
            print(f"  - Delete EIGRP router ASN {router.asn}")
            # router.delete()

        # Delete OSPF commands
        ospf_commands = routing.ospf_commands.list()
        for cmd in ospf_commands:
            print(f"  - Delete OSPF: {cmd.command}")
            # cmd.delete()

        print("\n(Cleanup commented out - uncomment to run)")


if __name__ == "__main__":
    print("pyvergeos Network Routing Examples")
    print("=" * 50)
    print()
    print("NOTE: Update host/credentials in this file before running.")
    print()
    print("WARNING: Routing changes can affect network connectivity!")
    print("         Test in a lab environment first.")
    print()

    # Uncomment the examples you want to run:
    # list_networks_with_routing()
    # view_bgp_configuration()
    # configure_bgp_basic()
    # configure_bgp_route_maps()
    # view_ospf_configuration()
    # configure_ospf_basic()
    # view_eigrp_configuration()
    # configure_eigrp_basic()
    # cleanup_routing()

    print("See the code for examples of:")
    print("  - Viewing BGP configuration")
    print("  - Configuring BGP routers and neighbors")
    print("  - Creating BGP route maps and prefix lists")
    print("  - Viewing OSPF configuration")
    print("  - Configuring OSPF areas and networks")
    print("  - Viewing EIGRP configuration")
    print("  - Configuring EIGRP routing")
