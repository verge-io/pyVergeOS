"""OData-style filter expression builder for VergeOS API queries.

VergeOS filtering is "similar to OData" but has its own grammar. The
supported comparison operators are ``eq``, ``ne``, ``gt``, ``ge``, ``lt``,
``le``, ``bw`` (begins-with), ``ew`` (ends-with), ``cs`` (contains,
case-sensitive), ``ct`` (contains, case-insensitive) and ``rx`` (POSIX ERE
regex). There is no ``like`` and no ``in`` -- the platform rejects both
tokens with HTTP 422 -- so the wildcard and list shorthands below are
translated to supported operators (issue #103).

``and``/``or`` have no precedence and are evaluated strictly left-to-right,
so every generated ``or`` chain is parenthesized.
"""

from __future__ import annotations

import re
from enum import Enum
from typing import Any

# The platform's ``rx`` dialect is POSIX ERE: PCRE shorthands such as ``\d``
# and inline flags such as ``(?i)`` do not error -- they silently match
# nothing -- so only backslash-escaping of metacharacters is safe.
_POSIX_ERE_SPECIALS = re.compile(r"[.\[\]()*+?{}|^$\\]")


# Characters the platform reserves inside a filter string literal. Measured by
# sweeping all 95 printable ASCII characters against a live system (issue #100):
# only these three carry meaning; the other 92 are inert, including ``}``.
#   ``\\``  the escape character itself
#   ``'``   terminates the literal
#   ``{``   opens a balanced, nesting-aware construct
# All three are escaped with a single backslash. ``\\`` MUST be replaced first,
# or the backslash it inserts for a later character gets doubled.
_RESERVED_IN_LITERAL = ("\\", "'", "{")


def quote_value(value: str) -> str:
    """Quote a string literal for a VergeOS filter expression.

    VergeOS uses backslash escaping, not SQL quote doubling. Three characters
    are reserved inside a literal and each is escaped with a backslash:
    ``\\`` (the escape character), ``'`` (terminates the literal) and ``{``
    (opens a balanced construct). ``}`` is not reserved.

    An unescaped ``{`` is the dangerous one: a *balanced* ``{...}`` is consumed
    silently and the query matches whatever the stripped string names, so a
    lookup-by-name can return - and the caller can then modify or delete - the
    wrong object (issue #100). An unbalanced ``{`` is merely rejected with
    HTTP 422.

    This only quotes the value; wildcard conversion belongs to the caller.
    """
    escaped = value
    for char in _RESERVED_IN_LITERAL:
        escaped = escaped.replace(char, "\\" + char)
    return f"'{escaped}'"


def _posix_escape(text: str) -> str:
    """Escape POSIX ERE metacharacters for the platform's ``rx`` operator.

    ``re.escape()`` is deliberately not used: it targets Python's PCRE-style
    dialect, while VergeOS evaluates POSIX ERE, where unsupported escapes
    silently match nothing instead of raising (issue #103).
    """
    return _POSIX_ERE_SPECIALS.sub(lambda m: "\\" + m.group(0), text)


def wildcard_condition(field: str, pattern: str) -> str:
    """Translate a ``*``/``?`` wildcard pattern into supported operators.

    Public so resource managers with a ``name`` search parameter share one
    translation instead of hand-rolling their own (issue #103, PR #104).

    VergeOS has no ``like`` operator (HTTP 422 "Invalid argument"), so
    wildcard patterns are translated (issue #103):

    - ``foo*``  -> ``field bw 'foo'``   (begins-with)
    - ``*foo``  -> ``field ew 'foo'``   (ends-with)
    - ``*foo*`` -> ``field cs 'foo'``   (contains)
    - ``*``     -> ``field bw ''``      (matches every row)
    - patterns with ``?`` or an interior ``*`` -> anchored POSIX-ERE ``rx``
      with metacharacters escaped, e.g. ``a*b`` -> ``field rx '^a.*b$'``

    Matching is case-sensitive throughout, consistent with ``eq``. For a
    case-insensitive contains, use a raw ``filter="field ct '...'"``.
    The anchored form guarantees the ``rx`` pattern is never empty (an
    empty ``rx`` pattern matches every row on the platform).
    """
    if "?" not in pattern:
        body = pattern.strip("*")
        if "*" not in body:
            leading = pattern.startswith("*")
            trailing = pattern.endswith("*")
            if not body:
                if leading or trailing:
                    # Only wildcards ('*', '**', ...): match everything,
                    # as LIKE '%' would have.
                    return f"{field} bw ''"
                return f"{field} eq {quote_value(pattern)}"
            if leading and trailing:
                return f"{field} cs {quote_value(body)}"
            if trailing:
                return f"{field} bw {quote_value(body)}"
            if leading:
                return f"{field} ew {quote_value(body)}"
            return f"{field} eq {quote_value(pattern)}"

    # Complex pattern ('?' anywhere, or '*' between literals): anchored regex.
    out = ["^"]
    for ch in pattern:
        if ch == "*":
            out.append(".*")
        elif ch == "?":
            out.append(".")
        else:
            out.append(_posix_escape(ch))
    out.append("$")
    return f"{field} rx {quote_value(''.join(out))}"


def _scalar_condition(field: str, value: Any) -> str:
    """Equality condition, with wildcard translation for string values."""
    if isinstance(value, str) and ("*" in value or "?" in value):
        return wildcard_condition(field, value)
    return f"{field} eq {_format_value(value)}"


def _in_condition(field: str, values: Any) -> str:
    """Expand a sequence into a parenthesized ``or`` chain of conditions.

    VergeOS has no ``in`` operator (HTTP 422 "Invalid argument"). The chain
    must be parenthesized: the platform evaluates ``and``/``or`` strictly
    left-to-right with no precedence, so an unparenthesized chain silently
    regroups when combined with ``and`` (issue #103). String elements get
    the same wildcard translation as scalar values.

    Raises:
        ValueError: If the sequence is empty. An empty ``in`` would match
            no rows, which is almost certainly a caller bug and must not
            fail silently.
    """
    items = list(values)
    if not items:
        raise ValueError(
            f"Cannot build a filter for {field!r} from an empty sequence; it would match no rows"
        )
    terms = " or ".join(_scalar_condition(field, v) for v in items)
    return f"({terms})"


class FilterOperator(Enum):
    """Filter operators.

    ``LIKE`` and ``IN`` are accepted for backwards compatibility but are
    never sent to the API: VergeOS rejects both tokens, so they are
    translated to supported operators (issue #103).
    """

    EQ = "eq"
    NE = "ne"
    LT = "lt"
    GT = "gt"
    LE = "le"
    GE = "ge"
    BW = "bw"
    EW = "ew"
    CS = "cs"
    CT = "ct"
    RX = "rx"
    LIKE = "like"
    IN = "in"


class Filter:
    """OData-style filter expression builder.

    Example:
        >>> f = Filter()
        >>> f.eq("status", "running").and_().like("name", "web*")
        >>> str(f)
        "status eq 'running' and name bw 'web'"
    """

    def __init__(self) -> None:
        self._parts: list[str] = []

    def _add(self, field: str, op: FilterOperator, value: Any) -> Filter:
        """Add a filter condition, translating unsupported operators."""
        if op is FilterOperator.LIKE:
            # VergeOS has no 'like' operator (issue #103).
            self._parts.append(wildcard_condition(field, str(value)))
            return self
        if op is FilterOperator.IN:
            # VergeOS has no 'in' operator (issue #103).
            seq = value if isinstance(value, (list, tuple)) else [value]
            self._parts.append(_in_condition(field, seq))
            return self
        self._parts.append(f"{field} {op.value} {_format_value(value)}")
        return self

    def _auto_and(self) -> None:
        """Auto-add AND if needed (implicit AND between conditions)."""
        if self._parts and self._parts[-1] not in ("and", "or"):
            self._parts.append("and")

    def eq(self, field: str, value: Any) -> Filter:
        """Add equals condition."""
        self._auto_and()
        return self._add(field, FilterOperator.EQ, value)

    def ne(self, field: str, value: Any) -> Filter:
        """Add not equals condition."""
        self._auto_and()
        return self._add(field, FilterOperator.NE, value)

    def lt(self, field: str, value: Any) -> Filter:
        """Add less than condition."""
        self._auto_and()
        return self._add(field, FilterOperator.LT, value)

    def gt(self, field: str, value: Any) -> Filter:
        """Add greater than condition."""
        self._auto_and()
        return self._add(field, FilterOperator.GT, value)

    def le(self, field: str, value: Any) -> Filter:
        """Add less than or equal condition."""
        self._auto_and()
        return self._add(field, FilterOperator.LE, value)

    def ge(self, field: str, value: Any) -> Filter:
        """Add greater than or equal condition."""
        self._auto_and()
        return self._add(field, FilterOperator.GE, value)

    def like(self, field: str, pattern: str) -> Filter:
        """Add a wildcard pattern condition. ``*`` = any run, ``?`` = one char.

        VergeOS has no ``like`` operator, so the pattern is translated to
        supported operators: ``foo*`` -> ``bw``, ``*foo`` -> ``ew``,
        ``*foo*`` -> ``cs``, complex patterns -> anchored POSIX-ERE ``rx``.
        Matching is case-sensitive, consistent with ``eq`` (issue #103).
        """
        self._auto_and()
        return self._add(field, FilterOperator.LIKE, pattern)

    def in_(self, field: str, values: list[Any] | Any) -> Filter:
        """Add a membership condition as a parenthesized ``or`` chain.

        VergeOS has no ``in`` operator, so the list expands to
        ``(field eq v1 or field eq v2 ...)``. String values follow the same
        wildcard translation as :meth:`like` (issue #103).

        Raises:
            ValueError: If ``values`` is an empty sequence.
        """
        self._auto_and()
        return self._add(field, FilterOperator.IN, values)

    def bw(self, field: str, value: str) -> Filter:
        """Add begins-with condition (case-sensitive)."""
        self._auto_and()
        return self._add(field, FilterOperator.BW, value)

    def ew(self, field: str, value: str) -> Filter:
        """Add ends-with condition (case-sensitive)."""
        self._auto_and()
        return self._add(field, FilterOperator.EW, value)

    def cs(self, field: str, value: str) -> Filter:
        """Add contains condition (case-sensitive)."""
        self._auto_and()
        return self._add(field, FilterOperator.CS, value)

    def ct(self, field: str, value: str) -> Filter:
        """Add contains condition (case-insensitive)."""
        self._auto_and()
        return self._add(field, FilterOperator.CT, value)

    def rx(self, field: str, pattern: str) -> Filter:
        """Add a POSIX-ERE regex condition (partial match, case-sensitive).

        The platform dialect is POSIX ERE: bracket classes like ``[0-9]``
        and ``[[:digit:]]`` work, but PCRE shorthands (``\\d``) and inline
        flags (``(?i)``) silently match nothing, and an **empty pattern
        matches every row**. Escape literal metacharacters with a backslash.
        """
        self._auto_and()
        return self._add(field, FilterOperator.RX, pattern)

    def and_(self) -> Filter:
        """Add explicit AND connector (usually not needed, AND is implicit)."""
        self._parts.append("and")
        return self

    def or_(self) -> Filter:
        """Add OR connector (must be explicit, unlike AND)."""
        self._parts.append("or")
        return self

    def __str__(self) -> str:
        return " ".join(self._parts)

    def __bool__(self) -> bool:
        return bool(self._parts)

    def __repr__(self) -> str:
        return f"Filter({str(self)!r})"


def _format_value(value: Any) -> str:
    """Format a value for a filter expression."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    return quote_value(str(value))


def combine_filters(filter: str | None, filter_kwargs: dict[str, Any]) -> str | None:  # noqa: A002
    """Merge an explicit filter string with shorthand filter kwargs.

    Both filter forms are honoured: when both are supplied the result is
    ``(filter) and (built)``. Previously shorthand kwargs were silently
    dropped whenever an explicit filter was present (issue #96).

    Args:
        filter: OData filter string, or None.
        filter_kwargs: Shorthand field-value filter arguments.

    Returns:
        Combined filter string, or None when no filtering was requested.

    Raises:
        ValueError: If filter kwargs were supplied but every value was None.
            An empty filter would silently match every row, so it is rejected
            instead of widening the result set (issue #96).
    """
    built = ""
    if filter_kwargs:
        built = build_filter(**filter_kwargs)
        if not built:
            names = ", ".join(sorted(filter_kwargs))
            raise ValueError(
                f"Filter argument(s) {names} are all None and would produce an "
                "empty filter matching every row; omit them to list all resources"
            )
    if filter and built:
        return f"({filter}) and ({built})"
    return filter or built or None


def build_filter(**kwargs: Any) -> str:
    """Build a filter string from keyword arguments.

    Supports:
        - Simple equality: name="value"
        - Wildcards: name="prefix*" (translated to bw/ew/cs/rx; VergeOS has
          no LIKE operator -- see issue #103). Case-sensitive.
        - Lists: status=["running", "stopped"] (expanded to a parenthesized
          or-chain of equality/wildcard conditions; VergeOS has no IN
          operator). Raises ValueError for an empty sequence.

    Args:
        **kwargs: Field-value pairs for filtering.

    Returns:
        OData-style filter string.

    Example:
        >>> build_filter(status="running", name="web*")
        "status eq 'running' and name bw 'web'"
        >>> build_filter(status=["running", "stopped"])
        "(status eq 'running' or status eq 'stopped')"
    """
    parts = []

    for field, value in kwargs.items():
        if value is None:
            continue

        if isinstance(value, (list, tuple)):
            parts.append(_in_condition(field, value))
        else:
            parts.append(_scalar_condition(field, value))

    return " and ".join(parts)
