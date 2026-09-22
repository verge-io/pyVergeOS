"""Grammar tripwire: the SDK may only emit operators VergeOS supports.

Root-cause guard for issue #103. The filter layer originally emitted
``like`` and ``in`` -- operators assumed from SQL/OData that were never in
the VergeOS grammar -- and unit tests asserted that broken output, so the
defect shipped. This test scans every string literal and f-string in the
package for filter-condition shapes (``field OP value``) and fails if any
uses an operator outside the wire-verified set, so an invented operator can
never ship silently again.

Verified grammar (official API Guide + measured on VergeOS 26.1.8, #103):
eq ne gt ge lt le bw ew cs ct rx, connectors and/or. Known-rejected or
known-broken tokens: like, in, sw, re (parses but never matches), matches,
regex, contains.
"""

from __future__ import annotations

import ast
import pathlib
import re

PACKAGE_DIR = pathlib.Path(__file__).resolve().parents[2] / "pyvergeos"

VERIFIED_OPERATORS = {"eq", "ne", "gt", "ge", "lt", "le", "bw", "ew", "cs", "ct", "rx", "and", "or"}

# Operators VergeOS rejects with 422 (like, in, sw, matches, regex) or
# accepts but never matches (re) -- measured in issue #103. English prose
# makes a fully general unknown-operator scan too noisy, so the tripwire
# targets the known-dangerous tokens in filter-condition shape.
DENIED_OPERATORS = {"like", "in", "sw", "re", "matches", "regex"}

# field (identifier, $-prefixed, or f-string placeholder), operator token,
# then a value: quoted literal, placeholder, parenthesized group, keyword,
# or number. Docstrings are excluded separately.
CONDITION = re.compile(
    r"(?:^|[ (])"
    r"([A-Za-z_$][\w$]*|\{[^}]*\})"
    r"\s+([a-z]{2,10})\s+"
    r"(?:'|\"|\{|\(|null\b|true\b|false\b|[0-9])"
)


def _docstring_nodes(tree: ast.AST) -> set[int]:
    """Line numbers of docstring constants (module/class/function bodies)."""
    lines: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            body = getattr(node, "body", [])
            if (
                body
                and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
                and isinstance(body[0].value.value, str)
            ):
                lines.add(body[0].value.lineno)
    return lines


def _string_payloads(tree: ast.AST, skip_lines: set[int]):
    for node in ast.walk(tree):
        if isinstance(node, ast.JoinedStr):
            text = "".join(
                v.value if isinstance(v, ast.Constant) and isinstance(v.value, str) else "{x}"
                for v in node.values
            )
            yield node.lineno, text
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            if node.lineno in skip_lines:
                continue
            yield node.lineno, node.value


def test_only_verified_filter_operators_are_emitted() -> None:
    offenders: list[str] = []
    for path in sorted(PACKAGE_DIR.rglob("*.py")):
        tree = ast.parse(path.read_text())
        skip = _docstring_nodes(tree)
        for lineno, text in _string_payloads(tree, skip):
            for match in CONDITION.finditer(text):
                op = match.group(2)
                if op in DENIED_OPERATORS:
                    offenders.append(
                        f"{path.relative_to(PACKAGE_DIR.parent)}:{lineno} "
                        f"operator {op!r} in {text[:70]!r}"
                    )
    assert offenders == [], (
        "Filter-condition strings using operators outside the verified VergeOS "
        f"grammar ({' '.join(sorted(VERIFIED_OPERATORS))}). The platform "
        "rejects unknown operators with HTTP 422, or worse, accepts and "
        "silently never matches (see issue #103):\n" + "\n".join(offenders)
    )
