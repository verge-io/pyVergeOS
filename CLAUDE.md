# pyvergeos

Python SDK for VergeOS REST API v4. Targets Python 3.9+, published to PyPI.

## Tech Stack

- **Language**: Python 3.9+
- **HTTP Client**: `requests` (sync), `httpx` (async, optional)
- **Validation**: `pydantic` (optional)
- **Testing**: `pytest`, `pytest-mock`, `pytest-cov`
- **Linting**: `ruff` (lint + format), `mypy`
- **Docs**: Sphinx with Google-style docstrings

## Project Structure

```
pyvergeos/
├── client.py           # Main VergeClient class
├── connection.py       # Authentication & session management
├── exceptions.py       # Custom exception hierarchy
├── filters.py          # OData filter builder
├── resources/          # Resource managers (vms.py, networks.py, etc.)
│   └── base.py         # Base ResourceManager with CRUD
├── models/             # Optional Pydantic models
└── utils/              # Validators, helpers

tests/
├── unit/               # Mock-based tests
├── integration/        # Requires live VergeOS (skipped in CI)
└── fixtures/           # JSON response fixtures
```

## Commands

```bash
# Setup environment (uses uv)
uv venv                              # Create venv
uv sync                              # Install all deps from pyproject.toml

# Run tests
uv run pytest                        # All tests
uv run pytest tests/unit             # Unit only
uv run pytest -k "test_vm"           # Pattern match
uv run pytest --cov=pyvergeos        # With coverage

# Linting & formatting
uv run ruff check .                  # Lint
uv run ruff check --fix .            # Auto-fix
uv run ruff format .                 # Format
uv run mypy pyvergeos                # Type check

# Build
uv build                             # Build wheel & sdist
```

## Code Conventions

### Naming
- `snake_case` for functions, variables, modules
- `PascalCase` for classes
- `SCREAMING_SNAKE_CASE` for constants
- Prefix booleans: `is_connected`, `has_error`, `can_retry`

### Type Hints
All public APIs must have type annotations:
```python
def get(self, key: int, *, fields: list[str] | None = None) -> ResourceObject:
```

### Docstrings
Google style with Args, Returns, Raises:
```python
def connect(self) -> "VergeClient":
    """Establish connection to VergeOS.

    Returns:
        Self for method chaining.

    Raises:
        ConnectionError: If connection fails.
        AuthenticationError: If credentials invalid.
    """
```

### Resource Manager Pattern
All resources follow the same CRUD interface:
```python
client.vms.list(**filters)      # GET /vms
client.vms.get(key)             # GET /vms/{key}
client.vms.get(name="...")      # GET /vms?filter=name eq '...'
client.vms.create(**kwargs)     # POST /vms
client.vms.update(key, **kw)    # PUT /vms/{key}
client.vms.delete(key)          # DELETE /vms/{key}
client.vms.action(key, "name")  # PUT /vms/{key}?action=name
```

### Error Handling
Use custom exceptions from `exceptions.py`. Names are prefixed with `Verge` to avoid shadowing Python builtins:
- `VergeError` - base class
- `VergeConnectionError`, `NotConnectedError` - connection issues
- `VergeTimeoutError` - request timeouts
- `APIError` (with `status_code`) → `AuthenticationError`, `NotFoundError`, `ValidationError`, `ConflictError`
- `TaskError`, `TaskTimeoutError` - async task issues

### Thread Safety
The `VergeClient` is NOT thread-safe. Each thread should use its own client instance, or external locking should be used.

### Reserved Networks
**IMPORTANT:** Never use "Core" or "DMZ" networks for workloads, services, VMs, or NAS. These networks are reserved for the VergeOS operating system. Always create a new network (e.g., "Internal") for test workloads and examples.

### Resources with Non-Integer Keys

Some VergeOS resources use string keys instead of integers (e.g., NAS volumes use 40-character hex strings). When implementing these:

1. **Override the `key` property** in the ResourceObject subclass:
```python
@property
def key(self) -> str:  # type: ignore[override]
    k = self.get("$key")
    if k is None:
        raise ValueError("Resource has no $key")
    return str(k)
```

2. **Override `refresh()`, `save()`, `delete()`** using `cast()`:
```python
def refresh(self) -> MyResource:
    from typing import cast
    manager = cast("MyResourceManager", self._manager)
    return manager.get(self.key)

def save(self, **kwargs: Any) -> MyResource:
    from typing import cast
    manager = cast("MyResourceManager", self._manager)
    return manager.update(self.key, **kwargs)

def delete(self) -> None:
    from typing import cast
    manager = cast("MyResourceManager", self._manager)
    manager.delete(self.key)
```

3. **Add `# type: ignore[override]`** to manager methods with different signatures:
```python
def get(self, key: str | None = None, ...) -> MyResource:  # type: ignore[override]
def update(self, key: str, ...) -> MyResource:  # type: ignore[override]
def delete(self, key: str) -> None:  # type: ignore[override]
```

4. **Use filter-based lookup** instead of direct endpoint paths for get-by-key:
```python
# Instead of: GET /volumes/{key}
# Use: GET /volumes?filter=id eq '{key}'
params = {"filter": f"id eq '{key}'"}
response = self._client._request("GET", self._endpoint, params=params)
```

### Configuration
Use `VergeClient.from_env()` to create a client from environment variables:
- `VERGE_HOST` (required)
- `VERGE_USERNAME`, `VERGE_PASSWORD` - for basic auth
- `VERGE_TOKEN` - for bearer auth
- `VERGE_VERIFY_SSL` - default "true"
- `VERGE_TIMEOUT` - default "30"

## API Reference

### VergeOS API v4
- Base URL: `https://<host>/api/v4/<endpoint>`
- Auth: Basic (`username:password` base64) or Bearer token
- Filters: OData style (`status eq 'running' and ram gt 2048`)
- Primary key: `$key` field on all resources

### Key Endpoints
| Resource | Endpoint | Manager |
|----------|----------|---------|
| VMs | `vms` | `client.vms` |
| Networks | `vnets` | `client.networks` |
| Tenants | `tenants` | `client.tenants` |
| Users | `users` | `client.users` |
| Tasks | `tasks` | `client.tasks` |

See `.claude/reference/api-schema/` for full endpoint schemas.

## Reference Docs

- `.claude/PRD.md` - Product requirements and milestones
- `.claude/reference/specs/` - Technical specifications
- `.claude/reference/api-schema/` - VergeOS API v4 schemas (336 endpoints)
