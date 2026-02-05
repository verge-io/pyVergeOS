# Add DNS View Management Support (Issue #24)

## Problem

DNS Views are used internally by `DNSZoneManager._get_views()` but not exposed
as a public manager. Users cannot create, update, or delete DNS views. Zone
creation is also missing, so the full View -> Zone -> Records workflow is
incomplete.

## Solution

Add `DNSViewManager` with full CRUD, expose it on `Network.dns_views`, and add
zone create/delete to `DNSZoneManager`.

## New File: `pyvergeos/resources/dns_views.py`

### DNSView (ResourceObject)

Properties: `name`, `recursion`, `match_clients`, `match_destinations`,
`max_cache_size`, `query_source`.

`zones` property returns a `DNSZoneManager` scoped to this view, enabling
`view.zones.list()` and `view.zones.create()`.

### DNSViewManager (ResourceManager[DNSView])

Endpoint: `vnet_dns_views`. Accessed via `network.dns_views`.

Default fields: `$key`, `name`, `recursion`, `match_clients`,
`match_destinations`, `max_cache_size`, `query_source`, `vnet`.

Methods:
- `list(filter, fields)` — filtered by `vnet eq {network_key}`
- `get(key, name)` — by key or name
- `create(name, recursion=False, match_clients=None, match_destinations=None,
  max_cache_size=33554432, query_source=None)` — all API fields exposed
- `update(key, name, recursion, match_clients, match_destinations,
  max_cache_size, query_source)` — update any field
- `delete(key)` — delete a view

## Modified: `pyvergeos/resources/dns.py`

### DNSZoneManager Changes

Accept either a `Network` or `DNSView` as parent.

Add `create()`:
- Parameters: `domain`, `zone_type="master"`, `nameserver`, `email`,
  `default_ttl="1h"`, plus remaining zone fields via `**kwargs`
- Automatically sets view key when scoped to a DNSView
- Raises `ValueError` when constructed from Network (must go through a view)

Add `delete(key)`:
- `DELETE vnet_dns_zones/{key}`

## Modified: `pyvergeos/resources/networks.py`

Add `dns_views` property to `Network` class returning `DNSViewManager`.

## Tests

### New: `tests/unit/test_dns_views.py`

- DNSView property access for all fields
- DNSViewManager: list, get (by key/name), create, update, delete
- Verify network scoping (`vnet eq {key}`) in all requests
- `view.zones` returns scoped DNSZoneManager

### Modified: `tests/unit/test_dns.py`

- Zone create via view-scoped manager
- Zone delete
- Zone create without view raises ValueError

## Usage

```python
# List views
views = network.dns_views.list()

# Create a view with all options
view = network.dns_views.create(
    name="internal",
    recursion=True,
    match_clients="10/8;172.16/16;",
)

# Update a view
network.dns_views.update(view.key, recursion=False)

# Create a zone through a view
zone = view.zones.create(domain="example.com", zone_type="master")

# Records (existing)
zone.records.create(host="www", record_type="A", value="10.0.0.1")

# Delete
network.dns_views.delete(view.key)
```

## Verification

- `uv run pytest tests/unit -k "test_dns"` passes
- `uv run ruff check --fix . && uv run ruff format .` passes
- `uv run mypy pyvergeos` passes
