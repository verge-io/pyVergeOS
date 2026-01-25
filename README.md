# pyvergeos

Python SDK for the VergeOS REST API.

[![PyPI version](https://badge.fury.io/py/pyvergeos.svg)](https://badge.fury.io/py/pyvergeos)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Overview

pyvergeos provides a Pythonic interface for managing VergeOS infrastructure. It abstracts the VergeOS REST API behind a clean, type-annotated SDK suitable for automation, tooling, and integration development.

## Installation

```bash
pip install pyvergeos

# Or with uv
uv add pyvergeos
```

## Quick Start

```python
from pyvergeos import VergeClient

# Connect to VergeOS
client = VergeClient(
    host="192.168.1.100",
    username="admin",
    password="secret",
    verify_ssl=False  # For self-signed certificates
)

# List all VMs
for vm in client.vms.list():
    print(f"{vm.name}: {vm.ram}MB RAM, {vm.cpu_cores} cores")

# Get a specific VM
vm = client.vms.get(name="web-server")

# Power operations
vm.power_on()
vm.power_off()

# Create a VM
new_vm = client.vms.create(
    name="test-vm",
    ram=2048,
    cpu_cores=2,
    os_family="linux"
)

# Cleanup
client.disconnect()
```

## Context Manager

```python
with VergeClient(host="192.168.1.100", token="api-token") as client:
    vms = client.vms.list_running()
```

## Authentication

### Username/Password
```python
client = VergeClient(
    host="192.168.1.100",
    username="admin",
    password="secret"
)
```

### API Token
```python
client = VergeClient(
    host="192.168.1.100",
    token="your-api-token"
)
```

### Environment Variables
```bash
export VERGE_HOST=192.168.1.100
export VERGE_USERNAME=admin
export VERGE_PASSWORD=secret
```

```python
client = VergeClient.from_env()
```

## Features

### Virtual Machines
```python
# List, filter, create, update, delete
vms = client.vms.list(os_family="linux", name="web-*")
vm = client.vms.create(name="test", ram=2048, cpu_cores=2)

# Power operations
vm.power_on()
vm.power_off()
vm.reset()

# Snapshots
vm.snapshot(retention=86400, quiesce=True)

# Clone
clone = vm.clone(name="test-clone")

# Drives and NICs
vm.drives.add(name="data", size=50*1024*1024*1024)
vm.nics.add(network=network.key)
```

### Networks
```python
# Create and manage virtual networks
network = client.networks.create(
    name="app-network",
    network_address="10.10.1.0/24",
    ip_address="10.10.1.1",
    dhcp_enabled=True
)

network.power_on()
network.apply_rules()

# Firewall rules
network.rules.create(name="Allow SSH", action="accept", protocol="tcp", dest_port=22)
```

### Tenants
```python
tenant = client.tenants.create(name="customer-a")
tenant.power_on()
```

### Filtering
```python
# Keyword arguments
vms = client.vms.list(status="running", name="prod-*")

# OData filter string
vms = client.vms.list(filter="os_family eq 'linux' and ram gt 2048")

# Filter builder
from pyvergeos.filters import Filter
f = Filter().eq("os_family", "linux").and_().gt("ram", 2048)
vms = client.vms.list(filter=str(f))
```

### Task Waiting
```python
result = vm.snapshot()
task = client.tasks.wait(result["task"], timeout=300)
```

## Error Handling

```python
from pyvergeos.exceptions import NotFoundError, AuthenticationError, TaskTimeoutError

try:
    vm = client.vms.get(name="nonexistent")
except NotFoundError:
    print("VM not found")

try:
    task = client.tasks.wait(task_id, timeout=60)
except TaskTimeoutError as e:
    print(f"Task {e.task_id} timed out")
```

## Requirements

- Python 3.9+
- VergeOS 26.0+

## License

MIT License - see [LICENSE](LICENSE) for details.

## Contributing

Contributions welcome! Please read the contributing guidelines before submitting PRs.

## Related Projects

- [PSVergeOS](https://github.com/verge-io/PSVergeOS) - PowerShell module for VergeOS
