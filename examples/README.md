# pyvergeos Examples

This directory contains example scripts demonstrating how to use pyvergeos to interact with VergeOS systems. Each example is self-contained and includes detailed comments explaining the operations.

## Prerequisites

Before running any example:

1. Install pyvergeos:
   ```bash
   pip install pyvergeos
   ```

2. Set environment variables (or modify credentials in the script):
   ```bash
   export VERGE_HOST="your-vergeos-host"
   export VERGE_USERNAME="admin"
   export VERGE_PASSWORD="your-password"
   export VERGE_VERIFY_SSL="false"  # Optional, for self-signed certs
   ```

## Examples by Category

### Getting Started

| Example | Description |
|---------|-------------|
| [connection_example.py](connection_example.py) | Various ways to connect to VergeOS (basic auth, environment variables, context managers) |

### Virtual Machines

| Example | Description |
|---------|-------------|
| [vm_example.py](vm_example.py) | Basic VM operations: listing, filtering, power management, console access |
| [vm_lifecycle.py](vm_lifecycle.py) | Complete VM lifecycle: create, clone, snapshot, bulk operations, maintenance workflows |
| [vm_snapshots_example.py](vm_snapshots_example.py) | VM snapshot operations: create, restore to new VM, restore over existing VM |
| [CreateVM.py](CreateVM.py) | Create a fully configured VM with drives, NICs, ISO, and optional cloud-init |

### Networking

| Example | Description |
|---------|-------------|
| [network_example.py](network_example.py) | Network management, DHCP, firewall rules, IP aliases, DNS, diagnostics |
| [dns_example.py](dns_example.py) | DNS zone and record management for networks with BIND DNS |
| [wireguard_example.py](wireguard_example.py) | WireGuard VPN: interfaces, peers, site-to-site and remote user configs |

### Storage & NAS

| Example | Description |
|---------|-------------|
| [storage_example.py](storage_example.py) | Storage operations: media catalog, file listing, tier info, vSAN status |
| [nas_simple.py](nas_simple.py) | Simple NAS setup: deploy service, create volumes |
| [nas_advanced.py](nas_advanced.py) | Advanced NAS: users, CIFS/SMB shares, NFS shares with restrictions |
| [nas_volume_sync.py](nas_volume_sync.py) | NAS volume synchronization between two NAS services |

### Backup & DR

| Example | Description |
|---------|-------------|
| [cloud_snapshots_example.py](cloud_snapshots_example.py) | Cloud (system) snapshots: create, list, query VMs/tenants, restore |
| [snapshot_profiles_example.py](snapshot_profiles_example.py) | Snapshot profiles: schedules, retention policies, periods |
| [site_syncs_example.py](site_syncs_example.py) | Site sync operations: outgoing/incoming syncs, queues, throttling |

### Multi-Tenancy

| Example | Description |
|---------|-------------|
| [tenant_management.py](tenant_management.py) | Complete tenant workflow: create, allocate resources, networking, file sharing |
| [tenant_monitoring_example.py](tenant_monitoring_example.py) | Multi-tenant monitoring: dashboards, stats, billing, health checks |
| [recipe_example.py](recipe_example.py) | VM recipe provisioning from Marketplace catalogs |

### Automation & Tasks

| Example | Description |
|---------|-------------|
| [task_automation_example.py](task_automation_example.py) | Task Engine: schedules, events, triggers for automated operations |

### Enterprise Networking

| Example | Description |
|---------|-------------|
| [routing_example.py](routing_example.py) | Dynamic routing: BGP, OSPF, EIGRP configuration and management |

### VM Import/Export

| Example | Description |
|---------|-------------|
| [vm_import_export_example.py](vm_import_export_example.py) | VM import/export: file imports, NAS volume exports for backup |

### System Administration

| Example | Description |
|---------|-------------|
| [system_example.py](system_example.py) | System settings, license info, dashboard stats, inventory reports |
| [user_management_example.py](user_management_example.py) | User onboarding: create users, groups, API keys, permissions |
| [tag_management_example.py](tag_management_example.py) | Tag workflow: categories, tags, resource tagging, queries |
| [certificate_example.py](certificate_example.py) | SSL/TLS certificates: self-signed, manual upload, renewal, monitoring |
| [catalog_example.py](catalog_example.py) | Recipe catalogs: repositories, marketplace integration, downloads |
| [billing_csv_example.py](billing_csv_example.py) | Billing reports: CSV export, time-range queries, tenant usage |

### GPU & Hardware

| Example | Description |
|---------|-------------|
| [gpu_passthrough_example.py](gpu_passthrough_example.py) | GPU passthrough: PCI devices, resource groups, VM attachment |

## Running Examples

Most examples are designed to be read and modified before running. They contain placeholder credentials and resource names that should be updated for your environment.

```bash
# View an example
cat vm_example.py

# Run an example (after updating credentials)
python vm_example.py
```

## Example Structure

Each example follows a consistent structure:

```python
#!/usr/bin/env python3
"""Example: Brief description.

Detailed explanation of what this example demonstrates.
"""

from pyvergeos import VergeClient

def example_function() -> None:
    """Demonstrate a specific operation."""
    with VergeClient(
        host="192.168.1.100",
        username="admin",
        password="your-password",
        verify_ssl=False,
    ) as client:
        # Example operations here
        pass

if __name__ == "__main__":
    # Uncomment to run:
    # example_function()
    pass
```

## Safety Notes

- Examples that modify resources (create, delete, power operations) are commented out by default
- Always review and understand an example before running it
- Test in a non-production environment first
- Some examples include cleanup functions to remove created resources

## Contributing

When adding new examples:

1. Follow the existing naming convention: `feature_example.py`
2. Include a comprehensive docstring at the top
3. Use type hints for function signatures
4. Keep credentials as placeholders (not real values)
5. Comment out destructive operations by default
6. Include cleanup functions where appropriate
7. Update this README with the new example

## Related Documentation

- [pyvergeos Documentation](https://github.com/verge-io/pyvergeos)
- [VergeOS Documentation](https://docs.verge.io)
- [VergeOS API Reference](https://docs.verge.io/api)
