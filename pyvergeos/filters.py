"""OData-style filter expression builder for VergeOS API queries."""

from enum import Enum
from typing import Any, Union


class FilterOperator(Enum):
    """Supported filter operators."""

    EQ = "eq"
    NE = "ne"
    LT = "lt"
    GT = "gt"
    LE = "le"
    GE = "ge"
    LIKE = "like"
    IN = "in"


class Filter:
    """OData-style filter expression builder.

    Example:
        >>> f = Filter()
        >>> f.eq("status", "running").and_().like("name", "web*")
        >>> str(f)
        "status eq 'running' and name like 'web%'"
    """

    def __init__(self) -> None:
        self._parts: list[str] = []

    def _add(self, field: str, op: FilterOperator, value: Any) -> "Filter":
        """Add a filter condition."""
        formatted_value = self._format_value(value, op)
        self._parts.append(f"{field} {op.value} {formatted_value}")
        return self

    def _format_value(self, value: Any, op: FilterOperator) -> str:
        """Format value for filter expression."""
        if op == FilterOperator.IN:
            if not isinstance(value, (list, tuple)):
                value = [value]
            formatted = ", ".join(self._format_single(v) for v in value)
            return f"({formatted})"

        if op == FilterOperator.LIKE and isinstance(value, str):
            # Convert wildcards: * -> %, ? -> _
            value = value.replace("*", "%").replace("?", "_")

        return self._format_single(value)

    def _format_single(self, value: Any) -> str:
        """Format a single value."""
        if value is None:
            return "null"
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, (int, float)):
            return str(value)
        # String - quote and escape
        value = str(value).replace("'", "''")
        return f"'{value}'"

    def _auto_and(self) -> None:
        """Auto-add AND if needed (implicit AND between conditions)."""
        if self._parts and self._parts[-1] not in ("and", "or"):
            self._parts.append("and")

    def eq(self, field: str, value: Any) -> "Filter":
        """Add equals condition."""
        self._auto_and()
        return self._add(field, FilterOperator.EQ, value)

    def ne(self, field: str, value: Any) -> "Filter":
        """Add not equals condition."""
        self._auto_and()
        return self._add(field, FilterOperator.NE, value)

    def lt(self, field: str, value: Any) -> "Filter":
        """Add less than condition."""
        self._auto_and()
        return self._add(field, FilterOperator.LT, value)

    def gt(self, field: str, value: Any) -> "Filter":
        """Add greater than condition."""
        self._auto_and()
        return self._add(field, FilterOperator.GT, value)

    def le(self, field: str, value: Any) -> "Filter":
        """Add less than or equal condition."""
        self._auto_and()
        return self._add(field, FilterOperator.LE, value)

    def ge(self, field: str, value: Any) -> "Filter":
        """Add greater than or equal condition."""
        self._auto_and()
        return self._add(field, FilterOperator.GE, value)

    def like(self, field: str, pattern: str) -> "Filter":
        """Add LIKE pattern condition. Use * for wildcard."""
        self._auto_and()
        return self._add(field, FilterOperator.LIKE, pattern)

    def in_(self, field: str, values: Union[list[Any], Any]) -> "Filter":
        """Add IN condition."""
        self._auto_and()
        return self._add(field, FilterOperator.IN, values)

    def and_(self) -> "Filter":
        """Add explicit AND connector (usually not needed, AND is implicit)."""
        self._parts.append("and")
        return self

    def or_(self) -> "Filter":
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
    value = str(value).replace("'", "''")
    return f"'{value}'"


def build_filter(**kwargs: Any) -> str:
    """Build a filter string from keyword arguments.

    Supports:
        - Simple equality: name="value"
        - Wildcards: name="prefix*" (converted to LIKE)
        - Lists: status=["running", "stopped"] (converted to IN)

    Args:
        **kwargs: Field-value pairs for filtering.

    Returns:
        OData filter string.

    Example:
        >>> build_filter(status="running", name="web*")
        "status eq 'running' and name like 'web%'"
    """
    parts = []

    for field, value in kwargs.items():
        if value is None:
            continue

        if isinstance(value, (list, tuple)):
            # IN query
            formatted = ", ".join(_format_value(v) for v in value)
            parts.append(f"{field} in ({formatted})")
        elif isinstance(value, str) and ("*" in value or "?" in value):
            # LIKE query
            pattern = value.replace("*", "%").replace("?", "_")
            parts.append(f"{field} like '{pattern}'")
        else:
            # Equality
            parts.append(f"{field} eq {_format_value(value)}")

    return " and ".join(parts)
