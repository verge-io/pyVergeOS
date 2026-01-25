#!/usr/bin/env python3
"""Examples for network management and firewall configuration.

This script demonstrates network management tasks:
- Querying and managing networks
- Network power operations
- Configuring DHCP host overrides
- Creating and managing firewall rules
- Managing IP aliases for firewall rules

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
    python network_example.py
"""

from __future__ import annotations

import os
import sys

from pyvergeos import VergeClient
from pyvergeos.exceptions import NotFoundError


def main() -> None:
    """Run network management examples."""
    # Connect to VergeOS
    print("=" * 60)
    print("Connecting to VergeOS...")
    print("=" * 60)

    client = VergeClient.from_env()
    client.connect()
    print(f"Connected to VergeOS {client.version}")

    try:
        # Run examples
        query_networks(client)
        network_power_operations(client)
        dhcp_host_examples(client)
        firewall_rule_examples(client)
        ip_alias_examples(client)
        complete_workflow(client)
    finally:
        client.disconnect()
        print("\nDisconnected from VergeOS")


# =============================================================================
# QUERYING NETWORKS
# =============================================================================


def query_networks(client: VergeClient) -> None:
    """Demonstrate network querying operations."""
    print("\n" + "=" * 60)
    print("QUERYING NETWORKS")
    print("=" * 60)

    # List all networks
    print("\n--- List all networks ---")
    networks = client.networks.list()
    print(f"Found {len(networks)} networks:")
    for net in networks:
        status = "running" if net.is_running else "stopped"
        print(f"  - {net.name} ({net.get('type')}) [{status}]")

    # List only running networks
    print("\n--- Running networks ---")
    running = client.networks.list_running()
    print(f"Found {len(running)} running networks")

    # List by type
    print("\n--- Internal networks ---")
    internal = client.networks.list_internal()
    print(f"Found {len(internal)} internal networks")

    print("\n--- External networks ---")
    external = client.networks.list_external()
    print(f"Found {len(external)} external networks")

    # Find network by name
    print("\n--- Find network by name ---")
    try:
        net = client.networks.get(name="External")
        print(f"Found: {net.name}")
        print(f"  Type: {net.get('type')}")
        print(f"  Network: {net.get('network')}")
        print(f"  IP Address: {net.get('ipaddress')}")
        print(f"  DHCP Enabled: {net.get('dhcp_enabled')}")
        print(f"  Running: {net.is_running}")
        print(f"  Needs Rule Apply: {net.needs_rule_apply}")
        print(f"  Needs DNS Apply: {net.needs_dns_apply}")
    except NotFoundError:
        print("External network not found")

    # Networks with DHCP enabled (using filter)
    print("\n--- Networks with DHCP enabled ---")
    dhcp_networks = client.networks.list(filter="dhcp_enabled eq true")
    print(f"Found {len(dhcp_networks)} networks with DHCP enabled")


# =============================================================================
# NETWORK POWER OPERATIONS
# =============================================================================


def network_power_operations(client: VergeClient) -> None:
    """Demonstrate network power operations (display only, no changes)."""
    print("\n" + "=" * 60)
    print("NETWORK POWER OPERATIONS")
    print("=" * 60)

    print("\n--- Power operation examples (not executed) ---")
    print("""
    # Start a network
    network = client.networks.get(name="Dev-Network")
    network.power_on()

    # Start with apply rules
    network.power_on(apply_rules=True)

    # Stop a network gracefully
    network.power_off()

    # Force stop (killpower)
    network.power_off(force=True)

    # Restart a network
    network.restart()

    # Apply firewall rules without restart
    network.apply_rules()

    # Apply DNS configuration
    network.apply_dns()
    """)


# =============================================================================
# DHCP HOST OVERRIDES
# =============================================================================


def dhcp_host_examples(client: VergeClient) -> None:
    """Demonstrate DHCP host override operations."""
    print("\n" + "=" * 60)
    print("DHCP HOST OVERRIDES")
    print("=" * 60)

    # Get a network to work with
    try:
        network = client.networks.get(name="External")
    except NotFoundError:
        print("External network not found, skipping host examples")
        return

    print(f"\nWorking with network: {network.name}")

    # List existing hosts
    print("\n--- List DHCP host overrides ---")
    hosts = network.hosts.list()
    print(f"Found {len(hosts)} host overrides:")
    for host in hosts:
        print(f"  - {host.hostname} -> {host.ip} (type={host.host_type})")

    # Create a test host
    print("\n--- Create host override ---")
    test_host = network.hosts.create(
        hostname="example-server01",
        ip="192.168.100.10",
        host_type="host",
    )
    print(f"Created: {test_host.hostname} -> {test_host.ip}")

    # Create a domain type override
    print("\n--- Create domain override ---")
    domain_host = network.hosts.create(
        hostname="mail.example.local",
        ip="192.168.100.25",
        host_type="domain",
    )
    print(f"Created: {domain_host.hostname} -> {domain_host.ip} (domain)")

    # Get host by hostname
    print("\n--- Get host by hostname ---")
    fetched = network.hosts.get(hostname="example-server01")
    print(f"Found: {fetched.hostname} -> {fetched.ip}")

    # Get host by IP
    print("\n--- Get host by IP ---")
    fetched_by_ip = network.hosts.get(ip="192.168.100.10")
    print(f"Found: {fetched_by_ip.hostname}")

    # Update host
    print("\n--- Update host IP ---")
    updated = network.hosts.update(test_host.key, ip="192.168.100.11")
    print(f"Updated: {updated.hostname} -> {updated.ip}")

    # Update host type
    print("\n--- Update host type ---")
    updated = network.hosts.update(test_host.key, host_type="domain")
    print(f"Updated type: is_domain={updated.is_domain}")

    # List by type
    print("\n--- List by type ---")
    domain_hosts = network.hosts.list(host_type="domain")
    print(f"Domain type hosts: {len(domain_hosts)}")

    # Cleanup
    print("\n--- Cleanup test hosts ---")
    network.hosts.delete(test_host.key)
    network.hosts.delete(domain_host.key)
    print("Deleted test hosts")

    # Note about applying changes
    print("\n--- Note ---")
    print("Host override changes require DNS apply to take effect:")
    print("  network.apply_dns()")


# =============================================================================
# FIREWALL RULES
# =============================================================================


def firewall_rule_examples(client: VergeClient) -> None:
    """Demonstrate firewall rule operations."""
    print("\n" + "=" * 60)
    print("FIREWALL RULES")
    print("=" * 60)

    # Get a network to work with
    try:
        network = client.networks.get(name="External")
    except NotFoundError:
        print("External network not found, skipping rule examples")
        return

    print(f"\nWorking with network: {network.name}")

    # List existing rules
    print("\n--- List firewall rules ---")
    rules = network.rules.list()
    print(f"Found {len(rules)} rules:")
    for rule in rules[:5]:  # Show first 5
        print(f"  [{rule.order}] {rule.name} - {rule.direction} {rule.action}")

    # List incoming rules only
    print("\n--- List incoming rules ---")
    incoming = network.rules.list(direction="incoming")
    print(f"Found {len(incoming)} incoming rules")

    # Create a rule to allow HTTPS
    print("\n--- Create Allow-HTTPS rule ---")
    https_rule = network.rules.create(
        name="Example-Allow-HTTPS",
        description="Allow HTTPS traffic (example)",
        direction="incoming",
        action="accept",
        protocol="tcp",
        destination_ports="443",
    )
    print(f"Created: {https_rule.name} (order={https_rule.order})")

    # Create a rule to allow SSH from specific IP
    print("\n--- Create Allow-SSH rule ---")
    ssh_rule = network.rules.create(
        name="Example-Allow-SSH",
        description="Allow SSH from admin workstation",
        direction="incoming",
        action="accept",
        protocol="tcp",
        source_ip="10.0.0.50",
        destination_ports="22",
    )
    print(f"Created: {ssh_rule.name}")

    # Create a rule for port range
    print("\n--- Create rule for port range ---")
    app_rule = network.rules.create(
        name="Example-App-Ports",
        description="Allow custom app ports",
        direction="incoming",
        action="accept",
        protocol="tcp",
        destination_ports="8000-8100",
    )
    print(f"Created: {app_rule.name}")

    # Create ICMP (ping) rule
    print("\n--- Create ICMP rule ---")
    icmp_rule = network.rules.create(
        name="Example-Allow-Ping",
        description="Allow ICMP ping",
        direction="incoming",
        action="accept",
        protocol="icmp",
    )
    print(f"Created: {icmp_rule.name}")

    # Create a reject rule
    print("\n--- Create reject rule ---")
    reject_rule = network.rules.create(
        name="Example-Block-Telnet",
        description="Block Telnet access",
        direction="incoming",
        action="reject",
        protocol="tcp",
        destination_ports="23",
    )
    print(f"Created: {reject_rule.name}")

    # Update a rule
    print("\n--- Update rule description ---")
    updated = network.rules.update(
        https_rule.key,
        description="Allow HTTPS traffic (updated)",
    )
    print(f"Updated: {updated.name} - {updated.description}")

    # Cleanup test rules
    print("\n--- Cleanup test rules ---")
    for rule in [https_rule, ssh_rule, app_rule, icmp_rule, reject_rule]:
        network.rules.delete(rule.key)
        print(f"Deleted: {rule.name}")

    # Note about applying rules
    print("\n--- Note ---")
    print("IMPORTANT: Apply rules after making changes:")
    print("  network.apply_rules()")


# =============================================================================
# IP ALIASES
# =============================================================================


def ip_alias_examples(client: VergeClient) -> None:
    """Demonstrate IP alias operations for firewall rules."""
    print("\n" + "=" * 60)
    print("IP ALIASES (for firewall rules)")
    print("=" * 60)

    # Get a network to work with
    try:
        network = client.networks.get(name="External")
    except NotFoundError:
        print("External network not found, skipping alias examples")
        return

    print(f"\nWorking with network: {network.name}")

    # List existing aliases
    print("\n--- List IP aliases ---")
    aliases = network.aliases.list()
    print(f"Found {len(aliases)} aliases:")
    for alias in aliases:
        print(f"  - {alias.hostname}: {alias.ip}")

    # Create an alias for admin workstation
    print("\n--- Create IP alias ---")
    admin_alias = network.aliases.create(
        ip="10.0.0.50",
        name="admin-workstation",
        description="Admin workstation for SSH access",
    )
    print(f"Created: {admin_alias.hostname} -> {admin_alias.ip}")

    # Create an alias for a subnet
    print("\n--- Create subnet alias ---")
    subnet_alias = network.aliases.create(
        ip="10.10.0.0/24",
        name="dev-subnet",
        description="Development network subnet",
    )
    print(f"Created: {subnet_alias.hostname} -> {subnet_alias.ip}")

    # Get alias by name
    print("\n--- Get alias by name ---")
    fetched = network.aliases.get(name="admin-workstation")
    print(f"Found: {fetched.hostname}")

    # Get alias by IP
    print("\n--- Get alias by IP ---")
    fetched_by_ip = network.aliases.get(ip="10.0.0.50")
    print(f"Found: {fetched_by_ip.hostname}")

    # Show how to use alias in firewall rule
    print("\n--- Using aliases in firewall rules ---")
    print("""
    # Create a rule using the alias
    rule = network.rules.create(
        name="Allow-SSH-Admins",
        description="Allow SSH from admin workstations",
        direction="incoming",
        action="accept",
        protocol="tcp",
        source_ip="alias:admin-workstation",  # Reference by alias name
        destination_ports="22",
    )
    """)

    # Cleanup
    print("\n--- Cleanup test aliases ---")
    network.aliases.delete(admin_alias.key)
    network.aliases.delete(subnet_alias.key)
    print("Deleted test aliases")


# =============================================================================
# COMPLETE WORKFLOW
# =============================================================================


def complete_workflow(client: VergeClient) -> None:
    """Demonstrate a complete network setup workflow."""
    print("\n" + "=" * 60)
    print("COMPLETE WORKFLOW: Web Server Network Setup")
    print("=" * 60)

    print("\n--- Workflow steps (not executed) ---")
    print("""
    # 1. Create the network
    web_net = client.networks.create(
        name="Web-Tier",
        network_type="internal",
        network_address="10.30.0.0/24",
        ip_address="10.30.0.1",
        gateway="10.30.0.1",
        dhcp_enabled=True,
        dhcp_start="10.30.0.100",
        dhcp_stop="10.30.0.200",
        domain="web.local",
    )

    # 2. Add firewall rules for HTTP/HTTPS
    web_net.rules.create(
        name="Allow-HTTP",
        description="Allow HTTP traffic",
        direction="incoming",
        action="accept",
        protocol="tcp",
        destination_ports="80",
    )

    web_net.rules.create(
        name="Allow-HTTPS",
        description="Allow HTTPS traffic",
        direction="incoming",
        action="accept",
        protocol="tcp",
        destination_ports="443",
    )

    # 3. Add DHCP host overrides for static IPs
    web_net.hosts.create(
        hostname="web01",
        ip="10.30.0.10",
    )

    web_net.hosts.create(
        hostname="web02",
        ip="10.30.0.11",
    )

    # 4. Apply rules and start the network
    web_net.apply_rules()
    web_net.apply_dns()
    web_net.power_on()

    print(f"Web tier network '{web_net.name}' is ready!")
    """)

    # Export network configuration example
    print("\n--- Export network configuration ---")
    try:
        network = client.networks.get(name="External")
        rules = network.rules.list()
        hosts = network.hosts.list()
        aliases = network.aliases.list()

        print(f"Network: {network.name}")
        print(f"  Type: {network.get('type')}")
        print(f"  Address: {network.get('network')}")
        print(f"  Gateway: {network.get('gateway')}")
        dhcp = network.get("dhcp_enabled")
        if dhcp:
            print(f"  DHCP: {network.get('dhcp_start')} - {network.get('dhcp_stop')}")
        else:
            print("  DHCP: Disabled")
        print(f"  Firewall Rules: {len(rules)}")
        print(f"  Host Overrides: {len(hosts)}")
        print(f"  IP Aliases: {len(aliases)}")
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
        print("  python network_example.py")
        sys.exit(1)

    main()
