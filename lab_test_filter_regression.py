"""Broad read-only regression for the #100 escaping change.

quote_value() is on the lookup path of every manager, so the regression
surface is "does lookup-by-name still resolve normal names everywhere".
Data-driven: for each top-level manager, read a real row, then look that
row back up by its own name and require the same key.

Read-only. Creates and deletes nothing.
"""

from __future__ import annotations

import sys

from pyvergeos import VergeClient
from pyvergeos.exceptions import APIError, NotFoundError
from pyvergeos.filters import quote_value

SKIP = {"connect", "disconnect", "from_env"}


def main() -> int:
    import pyvergeos

    print(f"SDK under test: {pyvergeos.__file__}")
    print(f"quote_value('a{{x}}') = {quote_value('a{x}')!r}\n")

    client = VergeClient.from_env()
    managers = []
    for prop in sorted(dir(type(client))):
        if prop.startswith("_") or prop in SKIP:
            continue
        try:
            obj = getattr(client, prop)
        except Exception:  # noqa: BLE001
            continue
        if hasattr(obj, "list") and hasattr(obj, "get"):
            managers.append((prop, obj))

    print(f"discovered {len(managers)} top-level managers\n")

    checked = ok = skipped = 0
    failures: list[str] = []
    empty: list[str] = []

    for prop, mgr in managers:
        try:
            rows = mgr.list(limit=3)
        except (APIError, TypeError, ValueError) as exc:
            skipped += 1
            print(f"  ~ {prop:<28} list() unavailable ({type(exc).__name__})")
            continue
        except Exception as exc:  # noqa: BLE001
            skipped += 1
            print(f"  ~ {prop:<28} list() raised {type(exc).__name__}")
            continue

        named = [r for r in rows if isinstance(dict(r).get("name"), str) and dict(r)["name"]]
        if not named:
            empty.append(prop)
            continue

        row = named[0]
        name = dict(row)["name"]
        key = str(row.key)
        checked += 1
        try:
            got = mgr.get(name=name)
            if str(got.key) == key:
                ok += 1
                print(f"  ok {prop:<28} {name!r} -> {key}")
            else:
                failures.append(f"{prop}: get(name={name!r}) -> key {got.key}, expected {key}")
                print(f"  XX {prop:<28} {name!r} -> WRONG key {got.key} (want {key})")
        except NotFoundError:
            failures.append(f"{prop}: get(name={name!r}) raised NotFoundError for an existing row")
            print(f"  XX {prop:<28} {name!r} -> NotFoundError")
        except (APIError, TypeError, ValueError) as exc:
            skipped += 1
            checked -= 1
            print(f"  ~ {prop:<28} get(name=) unsupported ({type(exc).__name__})")

    print(f"\n{'=' * 62}")
    print(f"managers with rows checked : {checked}")
    print(f"  resolved to the same row : {ok}")
    print(f"  wrong row / not found    : {len(failures)}")
    print(f"managers with no rows      : {len(empty)}")
    print(f"managers skipped           : {skipped}")
    if failures:
        print("\nFAILURES:")
        for f in failures:
            print(f"  - {f}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
