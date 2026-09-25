# pyvergeos

Python SDK for the VergeOS REST API.

[![PyPI version](https://img.shields.io/pypi/v/pyvergeos)](https://pypi.org/project/pyvergeos/)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Documentation](https://img.shields.io/badge/docs-GitHub%20Pages-blue)](https://verge-io.github.io/pyVergeOS/)

pyvergeos gives you a Pythonic way to drive VergeOS. It wraps the REST API in a typed, discoverable SDK so you can write automation and tooling without hand rolling HTTP calls and JSON payloads.

**[Read the full documentation](https://verge-io.github.io/pyVergeOS/)**

## Installation

```bash
pip install pyvergeos

# Or with uv
uv add pyvergeos
```

## Quick start

```python
from pyvergeos import VergeClient

client = VergeClient(
    host="192.168.1.100",
    username="admin",
    password="secret",
    verify_ssl=False,  # For self signed certificates
)

# List VMs
for vm in client.vms.list():
    print(f"{vm.name}: {vm.ram}MB RAM, {vm.cpu_cores} cores")

# Fetch one, then act on it
vm = client.vms.get(name="web-server")
vm.power_on()

# Create a VM
new_vm = client.vms.create(
    name="test-vm",
    ram=2048,
    cpu_cores=2,
    os_family="linux",
)

client.disconnect()
```

## Connecting

### Username and password

```python
client = VergeClient(
    host="192.168.1.100",
    username="admin",
    password="secret",
)
```

### API token

```python
client = VergeClient(
    host="192.168.1.100",
    token="your-api-token",
)
```

### Context manager

Preferred, since it always closes the session for you.

```python
with VergeClient(host="192.168.1.100", token="api-token") as client:
    running = client.vms.list_running()
```

### Environment variables

```bash
export VERGE_HOST=192.168.1.100
export VERGE_USERNAME=admin
export VERGE_PASSWORD=secret

# Or authenticate with a token instead of a username and password
export VERGE_TOKEN=your-api-token

# Optional
export VERGE_VERIFY_SSL=true
export VERGE_TIMEOUT=30
export VERGE_RETRY_TOTAL=3
export VERGE_RETRY_BACKOFF=1
```

```python
client = VergeClient.from_env()
```

### Bring your own session

Hand the client an existing `requests.Session` when you need to share connection pooling, proxy settings, or custom TLS material with the rest of your application. pyvergeos will not mount its own adapter or change the session's TLS verification, and it leaves the session open on disconnect.

```python
import requests

session = requests.Session()
session.proxies = {"https": "http://proxy.internal:3128"}

with VergeClient(host="192.168.1.100", token="api-token", session=session) as client:
    vms = client.vms.list()
```

Do not share one session across several active clients. Pass `close_session=True` if you want pyvergeos to close it for you anyway.

## Finding things

Every manager exposes the same three ways to narrow a query.

```python
# Keyword shorthand, including wildcards
vms = client.vms.list(os_family="linux", name="web-*")

# A filter string
vms = client.vms.list(filter="os_family eq 'linux' and ram gt 2048")

# The filter builder, when you are assembling a query programmatically
from pyvergeos import Filter

query = Filter().eq("os_family", "linux").and_().gt("ram", 2048)
vms = client.vms.list(filter=str(query))
```

A few helpers cover state the API cannot filter on directly, so reach for those instead of writing the filter yourself.

```python
client.vms.list_running()
client.vms.list_stopped()
client.networks.list_external()
```

Large tables page automatically with `iter_all()`, which yields objects instead of building one giant list.

```python
for vm in client.vms.iter_all(page_size=100):
    print(vm.name)
```

### A note on get(name=...)

Names are not unique in every VergeOS table. When you look something up by name and more than one row matches, `get()` returns the first match rather than raising. If a name might be ambiguous in your environment, use `list()` and decide for yourself, or look the object up by `$key`.

## Field projections

Managers request a curated set of fields by default, which keeps responses small. Narrow that set with `fields` when you want less, or ask for `"all"` when you want everything.

```python
names = client.vms.list(fields=["$key", "name"])
everything = client.vms.get(name="web-server", fields="all")
```

One behavior is worth knowing about. If you narrow the projection and then read an accessor whose backing field you left out, the SDK raises instead of making up an answer.

```python
from pyvergeos import FieldNotProjectedError

vm = client.vms.get(name="web-server", fields=["$key", "name"])

vm.name    # "web-server"
vm.status  # raises FieldNotProjectedError
```

That is deliberate. Guessing here once reported a running VM as stopped, and that is exactly the check people put in front of a destructive operation. To fix it, re-fetch with the manager's default fields or add the field you need to the `fields` argument.

## Virtual machines

```python
vm = client.vms.get(name="web-server")

# Power
vm.power_on()
vm.power_off()
vm.reset()
vm.guest_reboot()
vm.guest_shutdown()

# Placement
vm.migrate()
vm.hibernate()

# Clone
clone = vm.clone(name="web-server-clone")

# Drives and NICs
vm.drives.create(name="data", size_gb=50)
vm.nics.create(network=network.key)

# Hot plug into a running VM, which needs allow_hotplug enabled
vm.hotplug_drive(name="scratch", size=100 * 1024**3)
vm.hotplug_nic(name="nic2", network=network.key)
```

Watch the units. `drives.create()` takes `size_gb` in gigabytes, while `hotplug_drive()` takes `size` in bytes and that value must be a positive whole number of GiB. Hot plug creates the drive or NIC, then attaches the existing device by key. `hotplug_drive()` accepts only a `disk` on `virtio` or `virtio-scsi`. If the hotplug action is rejected, the drive or NIC created for that call is deleted and the error is re-raised.

You can hand a VM its cloud-init config at create time.

```python
vm = client.vms.create(
    name="web-server",
    ram=4096,
    cpu_cores=2,
    cloud_init="#cloud-config\npackages:\n  - nginx",
)
```

## Networks

```python
network = client.networks.create(
    name="app-network",
    network_address="10.10.1.0/24",
    ip_address="10.10.1.1",
    dhcp_enabled=True,
)

network.power_on()

# Firewall rules. Ports are strings, so "22", "80,443" and "1024-65535" all work.
network.rules.create(
    name="Allow SSH",
    direction="incoming",
    action="accept",
    protocol="tcp",
    destination_ports="22",
)

# Rule and DNS changes need to be applied before they take effect
network.apply_rules()
network.apply_dns()
```

Networks also carry DNS zones, static hosts, aliases, routing, IPSec, WireGuard, and a proxy, each on its own manager under the network object.

> **Heads up:** the Core and DMZ networks are reserved for VergeOS. Create your own network for workloads.

## Storage and NAS

```python
# vSAN tiers, which are numbered rather than named
for tier in client.storage_tiers.list():
    print(f"Tier {tier.tier}: {tier.used_percent:.1f}% of {tier.capacity_gb:.0f}GB used")

# NAS volumes and shares
volume = client.nas_volumes.create(name="share-data", service="nas1", size_gb=500)

client.cifs_shares.create(name="data", volume=volume.key, browseable=True)
client.nfs_shares.create(name="data", volume=volume.key)
```

## Snapshots

VM snapshots are scoped to the VM.

```python
vm.snapshots.create(name="before-upgrade", retention=86400, quiesce=True)

for snap in vm.snapshots.list():
    print(snap.name, snap.expires_at)
```

System wide cloud snapshots live on the client. Snapshot creation is not backed by a task, so pass `wait=True` when you need the call to block until the snapshot settles.

```python
snapshot = client.cloud_snapshots.create(
    name="nightly",
    wait=True,
    wait_timeout=600,
)
print(snapshot.status)
```

You can also scope a cloud snapshot to a set of tags, which captures only the VMs carrying them.

```python
client.cloud_snapshots.create(name="db-only", include_tags="database", wait=True)
```

## Tenants

```python
tenant = client.tenants.create(name="customer-a", password="initial-password")
tenant.power_on()

# Give the tenant a UI address on the external network
tenant.set_ui_ip("192.168.1.150")

# Resources
tenant.nodes.list()
tenant.network_blocks.list()
tenant.snapshots.list()
```

## Scheduled tasks

`client.tasks` is the VergeOS task scheduler. Use it to run and wait on scheduled work.

```python
task = client.tasks.get(name="Nightly backup")

task.execute()
task.wait(timeout=300)
```

Most VergeOS operations complete on the API call itself and do not create a task row, so reach for a manager's own `wait` argument, such as `cloud_snapshots.create(wait=True)`, rather than expecting a task to poll.

## What else is in here

The client exposes more than eighty managers. The ones above are the common starting points. Beyond them you will find:

- **Compute and infrastructure:** `nodes`, `clusters`, `cluster_status`, `physical_drives`, `machine_drive_stats`, `vgpu_profiles`
- **Sites and replication:** `sites`, `site_syncs`, `site_syncs_incoming`, `site_sync_schedules`, `volume_syncs`
- **Provisioning:** `catalogs`, `catalog_repositories`, `vm_recipes`, `tenant_recipes`, `vm_imports`, `volume_vm_exports`, `cloudinit_files`, `files`
- **Identity and access:** `users`, `groups`, `permissions`, `api_keys`, `auth_sources`, `oidc_applications`
- **Operations:** `update_settings`, `update_sources`, `update_packages`, `task_schedules`, `alarms`, `logs`, `billing`, `system_diagnostics`, `vsan_queries`, `certificates`, `tags`, `snapshot_profiles`

Full reference for all of them is in the [API documentation](https://verge-io.github.io/pyVergeOS/).

## Error handling

```python
from pyvergeos import (
    AuthenticationError,
    FieldNotProjectedError,
    NotFoundError,
    TaskTimeoutError,
    ValidationError,
    VergeTimeoutError,
)

try:
    vm = client.vms.get(name="nonexistent")
except NotFoundError:
    print("VM not found")

try:
    task.wait(timeout=60)
except TaskTimeoutError as e:
    print(f"Task {e.task_id} timed out")
```

Everything the SDK raises inherits from `VergeError`, so catch that if you just want one handler. `APIError` covers the HTTP failures underneath `AuthenticationError`, `NotFoundError`, `ValidationError`, and `ConflictError`.

## Retries and timeouts

The client retries transient failures automatically, which by default means 429, 500, 502, 503, and 504, three times, with exponential backoff.

```python
from http import HTTPStatus

client = VergeClient(
    host="192.168.1.100",
    username="admin",
    password="secret",
    timeout=30,                 # Per request timeout in seconds (default: 30)
    retry_total=5,              # Retry attempts (default: 3)
    retry_backoff_factor=2.0,   # Backoff factor (default: 1)
    retry_status_codes=frozenset({
        HTTPStatus.TOO_MANY_REQUESTS,
        HTTPStatus.SERVICE_UNAVAILABLE,
    }),
)
```

Set `retry_total=0` to turn retries off entirely.

## Requirements

- Python 3.9 or newer
- VergeOS 26.0 or newer

## Contributing

Contributions are welcome. Start with the [contributing guide](docs/contributing.rst) for the development setup, test commands, and coding standards.

All contributors must agree to the [Contributor License Agreement](CLA.md). Submitting a pull request counts as accepting it.

## License

Apache License 2.0. See [LICENSE](LICENSE) for details.

## Resources

- [pyvergeos documentation](https://verge-io.github.io/pyVergeOS/) for the full SDK reference
- [VergeOS documentation](https://docs.verge.io/) for the platform itself
- [VergeOS website](https://www.verge.io/)

## Related projects

- [PSVergeOS](https://github.com/verge-io/PSVergeOS), the PowerShell module for VergeOS
- [govergeos](https://github.com/verge-io/govergeos), the Go SDK for VergeOS
