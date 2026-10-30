"""Compare the VergeOS version reported by the system record.

Default field lists use this so a 26.1 server is not asked for columns that
arrived in a later release. A missing or unparseable version is treated as
older, which keeps the projection on the fields every supported release has.
"""

from __future__ import annotations


def version_at_least(os_version: str | None, major: int, minor: int) -> bool:
    """Return whether ``os_version`` is at least ``major.minor``.

    Only the first two numeric components are compared, so ``26.2.2.1``
    satisfies ``(26, 2)`` and ``26.1.8`` does not.
    """
    parts = (os_version or "").split(".")
    if len(parts) < 2:
        return False
    try:
        return (int(parts[0]), int(parts[1])) >= (major, minor)
    except ValueError:
        return False


def extend_fields(
    os_version: str | None,
    base: list[str],
    extras: list[str],
    *,
    major: int = 26,
    minor: int = 2,
) -> list[str]:
    """Return ``base`` plus ``extras`` when the server is new enough.

    The result is always a new list, so callers can store it on a manager
    without changing the shared default.
    """
    if version_at_least(os_version, major, minor):
        return [*base, *extras]
    return list(base)


def prepare_default_fields(manager: object, base: list[str], extras: list[str]) -> list[str]:
    """Store the version-specific default projection on ``manager``.

    Call this at the start of ``list`` and ``get``. The manager may have
    been built before ``connect()`` recorded the server version, and a
    cached manager has to follow the version that is current now.
    """
    client = getattr(manager, "_client", None)
    os_version = getattr(client, "os_version", None)
    fields = extend_fields(os_version, base, extras)
    manager._default_fields = fields  # type: ignore[attr-defined]
    return fields
