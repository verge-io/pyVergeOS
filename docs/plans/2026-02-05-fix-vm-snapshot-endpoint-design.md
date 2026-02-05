# Fix: Remove broken vm.snapshot() method (Issue #23)

## Problem

`VM.snapshot()` in `pyvergeos/resources/vms.py` sends `POST /api/v4/vm_actions`
with `{"action": "snapshot"}`, but `"snapshot"` is not a valid action for the
`vm_actions` endpoint. This causes all snapshot creation via `vm.snapshot()` to
fail with: `value 'snapshot' is not in list for field 'action'`.

The correct endpoint is `POST /api/v4/machine_snapshots`, which is already used
by `vm.snapshots.create()`.

## Solution

Remove `VM.snapshot()` entirely. The working `vm.snapshots.create()` method is
the correct API and already exists.

## Changes

### 1. Remove `VM.snapshot()` method
**File:** `pyvergeos/resources/vms.py`
- Delete the `snapshot()` method (lines 229-254)

### 2. Remove broken unit test
**File:** `tests/unit/test_vms.py`
- Delete `test_snapshot` (lines 511-531) which asserts the broken behavior

### 3. Update example
**File:** `examples/vm_example.py`
- Change `vm.snapshot(name=..., retention=..., quiesce=...)` to
  `vm.snapshots.create(name=..., retention=..., quiesce=...)`

### 4. Update README
**File:** `README.md`
- Line 114: `vm.snapshot(retention=86400, quiesce=True)` ->
  `vm.snapshots.create(retention=86400, quiesce=True)`
- Lines 163-164: `result = vm.snapshot()` ->
  `result = vm.snapshots.create(name="backup")`

## Verification

- `uv run pytest tests/unit -k "test_vm or test_snapshot"` passes
- `uv run ruff check --fix . && uv run ruff format .` passes
- `uv run mypy pyvergeos` passes
- No remaining references to `vm.snapshot(` in codebase
