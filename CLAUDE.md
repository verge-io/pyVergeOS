# pyvergeos

Python SDK for VergeOS REST API. Python 3.9+, published to PyPI.

## Commands

```bash
# Environment (uses uv, not pip)
uv sync                              # Install deps from pyproject.toml
uv run pytest tests/unit             # Run unit tests
uv run pytest -k "test_vm"           # Pattern match
uv run ruff check --fix . && uv run ruff format .  # Lint + format
uv run mypy pyvergeos                # Type check
uv build                             # Build wheel & sdist
```

## Critical Rules

**Line length: 100 characters max.**

**IMPORTANT: Reserved Networks**
Never use "Core" or "DMZ" networks for workloads, services, VMs, or NAS. These are reserved for VergeOS. Always create a new network (e.g., "Internal") for test workloads and examples.

**Build system:** Uses `hatchling` (not setuptools). Version in `pyvergeos/__version__.py`.

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

Use custom exceptions from `exceptions.py`. Names prefixed with `Verge` to avoid shadowing builtins:
- `VergeError` (base), `VergeConnectionError`, `VergeTimeoutError`
- `APIError` → `AuthenticationError`, `NotFoundError`, `ValidationError`, `ConflictError`
- `TaskError`, `TaskTimeoutError`

## Resource Patterns

Standard CRUD: `client.vms.list()`, `.get(key)`, `.create()`, `.update(key)`, `.delete(key)`, `.action(key, "name")`

For non-standard patterns (string keys, read-only resources, scoped managers, time-series stats), see `.claude/reference/specs/resources.md`.

## Reference Docs

- `.claude/PRD.md` - Product requirements
- `.claude/reference/specs/` - Technical specifications
- `.claude/reference/api-schema/` - API schema (336 endpoints)
- `.claude/TESTENV.md` - Integration test setup
- `examples/README.md` - Usage examples (25 scripts)
