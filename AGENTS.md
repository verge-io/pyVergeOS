# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

Python SDK for the VergeOS REST API. Python 3.9+, published to PyPI as `pyvergeos`.

## Commands

```bash
# Environment (uses uv, not pip)
uv sync                              # Install deps from pyproject.toml
uv run pytest tests/unit             # Run unit tests
uv run pytest tests/unit -k "test_vm"  # Pattern match
uv run pytest tests/unit -v --cov --cov-fail-under=80  # With coverage
uv run ruff check --fix . && uv run ruff format .      # Lint + format
uv run ruff format --check .         # Format check (CI mode)
uv run mypy pyvergeos                # Type check
uv build                             # Build wheel & sdist
uv lock --check                      # Verify lockfile is current
```

## Critical Rules

**Line length: 100 characters max.**

**IMPORTANT: Reserved Networks**
Never use "Core" or "DMZ" networks for workloads, services, VMs, or NAS. These are reserved for VergeOS. Always create a new network (e.g., "Internal") for test workloads and examples.

**Build system:** Uses `hatchling` (not setuptools). Version must be updated in **both** `pyproject.toml` AND `pyvergeos/__version__.py` — they must stay in sync. Also run `uv lock` after bumping to update `uv.lock`.

## Architecture

### Connection Flow

```
VergeClient(host, username, password)
  → connect() → VergeConnection (requests.Session + retry adapter)
    → authenticate → GET /api/v4/system to validate
  → client.vms.list() → ResourceManager._request("GET", ...)
    → session.request() → _handle_response() → [VM(...), ...]
```

### Core Classes

- **`VergeClient`** (`client.py`) — Main facade. Owns the connection and lazily exposes ~80 resource manager properties (`client.vms`, `client.tasks`, etc.). Not thread-safe. Supports context manager and `from_env()` factory.
- **`VergeConnection`** (`connection.py`) — Manages HTTP session, auth (basic or token), retry with exponential backoff.
- **`ResourceManager[T]`** (`resources/base.py`) — Generic base for CRUD operations. Subclasses override `_endpoint` and `_to_model()`. Supports OData filtering, pagination (`iter_all()`), field selection, and `action()` for custom operations.
- **`ResourceObject`** (`resources/base.py`) — Dict subclass with attribute access, `refresh()`, `save()`, `delete()`. Holds a back-reference to its manager.

### Key Patterns

**Lazy manager loading:** Client properties check `if self._manager is None:` before importing/instantiating. Reduces startup cost.

**Nested scoped managers:** Resources like VMs expose child managers: `vm.drives`, `vm.nics`, `vm.snapshots`. These are scoped to the parent — `vm.drives.list()` auto-filters by `machine_key`.

**OData filtering:** `list(filter="name eq 'test'")` or kwargs shorthand `list(name="test")` which gets converted via `build_filter()`.

**Default field selection:** Managers define `_DEFAULT_LIST_FIELDS` to limit response size. Detail views (`get()`) return all fields.

**Task polling:** `task.wait(timeout=300)` uses blocking `time.sleep` loop. Raises `TaskTimeoutError` on timeout, `TaskError` on failure.

## Linting Gotchas

When shadowing builtins for API consistency (common in this codebase), use noqa:
```python
def list(self, filter: str | None = None):  # noqa: A002
```

When variables are intentionally unused:
```python
_ = manager.update(key=1, name="test")
```

## Error Handling

Custom exceptions from `exceptions.py`, prefixed with `Verge` to avoid shadowing builtins:
- `VergeError` (base), `VergeConnectionError`, `VergeTimeoutError`
- `APIError` → `AuthenticationError`, `NotFoundError`, `ValidationError`, `ConflictError`
- `TaskError`, `TaskTimeoutError`

## Testing

Unit tests use `mock_client` fixture from `tests/conftest.py` (mocked HTTP session). Integration tests use `live_client` fixture (requires `VERGE_HOST`, `VERGE_USERNAME`, `VERGE_PASSWORD` env vars).

## Reference Docs

- `.claude/TESTENV.md` — Integration test environment setup
- `examples/README.md` — Usage examples
