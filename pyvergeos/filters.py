"""OData-style filter expression builder for VergeOS API queries."""

from __future__ import annotations

from enum import Enum
from typing import Any


def quote_value(value: str) -> str:
    """Quote a string literal for a VergeOS filter expression.

    VergeOS uses backslash escaping, not SQL quote doubling. Escape existing
    backslashes first so they cannot consume an apostrophe's escape character.
    This only quotes the value; wildcard conversion belongs to the caller.
    """
    escaped = value.replace("\\", "\\\\").replace("'", "\\'")
    return f"'{escaped}'"


class FilterOperator(Enum):
    """Filter operators supported by the VergeOS filter grammar.

    VergeOS filtering is *similar to* OData but is not OData: the grammar is
    ``eq, ne, gt, ge, lt, le, bw, ew, cs, ct, rx`` joined by ``and``/``or``.
    ``like`` and ``in`` are **not** part of it - the platform rejects them with
    HTTP 422 ``Invalid argument`` - so they are not represented here (issue
    #103). Wildcard and list shorthands are translated to these operators by
    :func:`wildcard_condition` and :func:`in_condition`.
    """

    EQ = "eq"
    NE = "ne"
    LT = "lt"
    GT = "gt"
    LE = "le"
    GE = "ge"
    BW = "bw"
    """Begins with (case-sensitive)."""
    EW = "ew"
    """Ends with (case-sensitive)."""
    CS = "cs"
    """Contains, case-sensitive."""
    CT = "ct"
    """Contains, case-insensitive."""
    RX = "rx"
    """Regular expression, unanchored and case-sensitive."""


_WILDCARD_CHARS = ("*", "?")

# Metacharacters of the platform's regex engine, escaped when embedding a
# literal in an ``rx`` pattern. Verified against VergeOS 26.1.8: the filter
# parser unescapes ``\\`` to ``\`` before the regex engine sees the pattern,
# so quote_value()'s backslash doubling round-trips correctly.
_REGEX_METACHARS = frozenset("\\.^$*+?()[]{}|")


def _has_wildcard(value: str) -> bool:
    """Return True if the value uses the SDK's wildcard shorthand."""
    return any(char in value for char in _WILDCARD_CHARS)


def _escape_regex_literal(text: str) -> str:
    """Escape a literal for embedding in a VergeOS ``rx`` pattern.

    Only true metacharacters are escaped. Python's :func:`re.escape` also
    escapes ``' '``, ``#``, ``&``, ``-`` and ``~``, which produces noisy
    patterns and relies on escape sequences this engine does not define.

    A literal ``{`` cannot be expressed at all: VergeOS 26.1.8 rejects it with
    HTTP 422 in bare, escaped and character-class form, for *every* operator
    including ``eq``. It is escaped here as the metacharacter it is; the
    request fails either way, exactly as an equality filter on the same value
    already does.
    """
    return "".join(f"\\{char}" if char in _REGEX_METACHARS else char for char in text)


def _glob_to_regex(pattern: str) -> str:
    """Convert a wildcard pattern to an anchored VergeOS regex.

    ``rx`` is unanchored, so ``^``/``$`` are added to preserve whole-value
    wildcard semantics: ``web*`` must not match ``my-web-1``.
    """
    parts = ["^"]
    for char in pattern:
        if char == "*":
            parts.append(".*")
        elif char == "?":
            parts.append(".")
        else:
            parts.append(_escape_regex_literal(char))
    parts.append("$")
    return "".join(parts)


def wildcard_condition(field: str, pattern: str) -> str:
    """Build a condition for a wildcard pattern using supported operators.

    ``*`` matches any sequence, ``?`` matches a single character. The simple
    shapes map to the platform's dedicated operators, which are cheaper than a
    regex; anything else becomes an anchored ``rx``. Every operator used here
    is case-sensitive, so matching does not change with wildcard position.

    ==================  ==========================
    Pattern             Condition
    ==================  ==========================
    ``foo``             ``field eq 'foo'``
    ``foo*``            ``field bw 'foo'``
    ``*foo``            ``field ew 'foo'``
    ``*foo*``           ``field cs 'foo'``
    ``*``               ``field bw ''`` (matches all)
    ``a*b``, ``a?b``    ``field rx '^a.*b$'``
    ==================  ==========================

    Args:
        field: Field name to match against.
        pattern: Wildcard pattern.

    Returns:
        A single filter condition using the VergeOS grammar.
    """
    if not _has_wildcard(pattern):
        return f"{field} eq {quote_value(pattern)}"

    core = pattern.strip("*")
    if not core:
        # All wildcards: every value begins with the empty string. ``cs ''``
        # would match nothing, so ``bw ''`` is used deliberately.
        return f"{field} bw ''"

    if "?" not in pattern and "*" not in core:
        leading = pattern.startswith("*")
        trailing = pattern.endswith("*")
        if leading and trailing:
            return f"{field} cs {quote_value(core)}"
        if trailing:
            return f"{field} bw {quote_value(core)}"
        if leading:
            return f"{field} ew {quote_value(core)}"

    return f"{field} rx {quote_value(_glob_to_regex(pattern))}"


def in_condition(field: str, values: Any) -> str:
    """Build a membership condition as a parenthesised ``or`` chain.

    VergeOS has no ``in`` operator, so ``status=["running", "stopped"]``
    becomes ``(status eq 'running' or status eq 'stopped')``. The parentheses
    keep the chain correct when merged into a larger ``and`` expression.
    Wildcard patterns are honoured per element.

    Args:
        field: Field name to match against.
        values: Values to match; a non-sequence is treated as a single value.

    Returns:
        A single filter condition using the VergeOS grammar.

    Raises:
        ValueError: If an empty sequence is supplied. An empty membership test
            matches nothing, which would silently return zero rows.
    """
    if not isinstance(values, (list, tuple)):
        values = [values]
    if not values:
        raise ValueError(
            f"Filter argument {field!r} is an empty sequence, which would match no rows; "
            "omit it to list all resources"
        )

    conditions = [
        wildcard_condition(field, value)
        if isinstance(value, str) and _has_wildcard(value)
        else f"{field} eq {_format_value(value)}"
        for value in values
    ]
    if len(conditions) == 1:
        return conditions[0]
    return "(" + " or ".join(conditions) + ")"


class Filter:
    """VergeOS filter expression builder.

    Example:
        >>> f = Filter()
        >>> f.eq("status", "running").and_().like("name", "web*")
        >>> str(f)
        "status eq 'running' and name bw 'web'"
    """

    def __init__(self) -> None:
        self._parts: list[str] = []

    def _add(self, field: str, op: FilterOperator, value: Any) -> Filter:
        """Add a filter condition."""
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
        """Add regular-expression condition.

        The pattern is sent verbatim. VergeOS regexes are unanchored and
        case-sensitive, so anchor with ``^``/``$`` for whole-value matches.
        """
        self._auto_and()
        return self._add(field, FilterOperator.RX, pattern)

    def like(self, field: str, pattern: str) -> Filter:
        """Add a wildcard condition. Use ``*`` for any run, ``?`` for one char.

        VergeOS has no ``like`` operator, so the pattern is translated to the
        supported operators (``eq``/``bw``/``ew``/``cs``/``rx``) by
        :func:`wildcard_condition` (issue #103).
        """
        self._auto_and()
        self._parts.append(wildcard_condition(field, str(pattern)))
        return self

    def in_(self, field: str, values: list[Any] | Any) -> Filter:
        """Add a membership condition.

        VergeOS has no ``in`` operator, so this expands to a parenthesised
        ``or`` chain of equality tests (issue #103).

        Raises:
            ValueError: If ``values`` is an empty sequence.
        """
        self._auto_and()
        self._parts.append(in_condition(field, values))
        return self

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
        - Wildcards: name="prefix*" (translated by :func:`wildcard_condition`)
        - Lists: status=["running", "stopped"] (expanded to an ``or`` chain)

    ``None`` values are skipped so optional filters can be passed through.

    Args:
        **kwargs: Field-value pairs for filtering.

    Returns:
        VergeOS filter string.

    Raises:
        ValueError: If a value is an empty sequence, which would match no rows.

    Example:
        >>> build_filter(status="running", name="web*")
        "status eq 'running' and name bw 'web'"
    """
    parts = []

    for field, value in kwargs.items():
        if value is None:
            continue

        if isinstance(value, (list, tuple)):
            parts.append(in_condition(field, value))
        elif isinstance(value, str) and _has_wildcard(value):
            parts.append(wildcard_condition(field, value))
        else:
            parts.append(f"{field} eq {_format_value(value)}")

    return " and ".join(parts)
