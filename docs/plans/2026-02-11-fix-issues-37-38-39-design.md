# Fix Issues #37, #38, #39 — API Parameter Bugs

## Summary

Three bug fixes for incorrect API request construction in the SDK.

## Issue #37: tasks.create() and task_events.create() parameter format

**Root cause:** `tasks.create()` sends `owner` as a bare integer and `table` as a separate
field. The VergeOS API expects `owner` in `"table/key"` combined format (e.g., `"vms/39"`).
For `task_events.create()`, the `owner` field should not be sent at all — it is auto-populated
from the parent task.

**Evidence:** Captured from VergeOS UI:
- Tasks POST: `{"owner": "smtp_settings/1", "action": "send", ...}` (combined format, no
  separate `table`)
- Task events POST: `{"task": "5", "table": "alarms", "event": "lowered", ...}` (no `owner`)

### tasks.create() changes

- Make `table` a required keyword argument (was optional)
- Format `owner` as `f"{table}/{owner}"` in the request body
- Remove `table` as a separate body field
- Update docstring and examples

### task_events.create() changes

- Remove `owner` parameter entirely (auto-populated from parent task)
- Make `table` a required keyword argument (event source table, e.g., `"alarms"`)
- Update docstring to clarify `table` = event source table and document task-first workflow

**Files:** `pyvergeos/resources/tasks.py`, `pyvergeos/resources/task_events.py`

## Issue #38: oidc_applications.create() omits required fields

**Root cause:** `force_auth_source` and `map_user` are only included in the request body when
not `None`. API schema marks both as `required: true` with `show_none: true` — they must
always be present, with `0` meaning "not set."

### Changes

- Always include `force_auth_source` in body (default `0` when `None`)
- Always include `map_user` in body (default `0` when `None`)

**Files:** `pyvergeos/resources/oidc_applications.py`

## Issue #39: api_keys.list() silently ignores unresolved user

**Root cause:** `_resolve_user_key()` returns `None` on lookup failure. `list()` silently
drops the user filter when `None`, returning ALL API keys instead of raising an error.

### Changes

- `_resolve_user_key()`: Remove try/except, let `NotFoundError` propagate naturally
- Return type changes from `int | None` to `int`
- Simplify `list()` caller — no more `None` check needed

**Files:** `pyvergeos/resources/api_keys.py`

## Testing

Unit tests for each fix following existing test patterns in `tests/unit/`.
