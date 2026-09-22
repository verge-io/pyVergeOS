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

from pyvergeos.filters import _RESERVED_IN_LITERAL, quote_value

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


# ---------------------------------------------------------------------------
# Reserved characters inside a filter string literal (issue #100)
# ---------------------------------------------------------------------------
#
# Measured by sweeping all 95 printable ASCII characters through
# ``name eq '...<CHAR>...'`` against a live VergeOS 26.1.8 system, and by
# round-tripping real rows whose names contain each character:
#
#   '\'  the escape character itself
#   '''  terminates the literal
#   '{'  opens a balanced, nesting-aware construct
#
# The other 92 are inert, including '}'. An unescaped '{' is the dangerous
# one: a balanced {...} is consumed silently and the query matches whatever
# the stripped string names, so a lookup-by-name can resolve to - and the
# caller then modify or delete - the wrong object.

RESERVED_LITERAL_CHARS = ("\\", "'", "{")
INERT_SAMPLE = '}()[]*?%_.+|^$&#@!~`"<>=,;:/ -0aZ'


class TestLiteralReservedCharacters:
    """quote_value() must escape every reserved character and nothing else."""

    def test_each_reserved_char_is_escaped_exactly_once(self) -> None:
        for char in RESERVED_LITERAL_CHARS:
            assert quote_value(char) == f"'\\{char}'", (
                f"{char!r} is reserved inside a filter literal and must be "
                "backslash-escaped (issue #100)"
            )

    def test_inert_characters_are_not_escaped(self) -> None:
        # Over-escaping is a bug too: a backslash before an inert character
        # is consumed by the platform and silently removes it from the value.
        for char in INERT_SAMPLE:
            assert quote_value(char) == f"'{char}'", (
                f"{char!r} is not reserved and must be passed through unescaped"
            )

    def test_backslash_is_escaped_before_the_others(self) -> None:
        # If '{' were replaced before '\\', the backslash inserted for the
        # brace would itself be doubled and the brace would arrive unescaped.
        assert quote_value("\\{") == r"'\\\{'"
        assert quote_value("\\'") == r"'\\\''"

    @staticmethod
    def _unescaped_brace_positions(body: str) -> list[int]:
        """Indexes of '{' not preceded by an ODD number of backslashes.

        Counting matters: a single preceding backslash escapes the brace, but
        two form an escaped backslash and leave the brace bare. Checking only
        body[i - 1] would pass a value like '\\{' straight through.
        """
        out = []
        for i, ch in enumerate(body):
            if ch != "{":
                continue
            backslashes = 0
            j = i - 1
            while j >= 0 and body[j] == "\\":
                backslashes += 1
                j -= 1
            if backslashes % 2 == 0:
                out.append(i)
        return out

    def test_balanced_braces_cannot_reach_the_wire_unescaped(self) -> None:
        # The silent-wrong-row case: every '{' must carry an escape.
        for value in [
            "a{x}b",
            "{}",
            "a{b{c}d}e",
            "{{",
            "pre{mid}post",
            "\\{",
            "\\\\{",
            "a\\{b",
            "'{",
            "{'",
        ]:
            literal = quote_value(value)
            body = literal[1:-1]
            bare = self._unescaped_brace_positions(body)
            assert not bare, (
                f"quote_value({value!r}) = {literal!r} leaves an unescaped "
                f"'{{' at {bare} on the wire (issue #100)"
            )

    def test_the_brace_detector_itself_is_sound(self) -> None:
        # Guard the guard: the helper must call a bare brace bare.
        assert self._unescaped_brace_positions("{") == [0]
        assert self._unescaped_brace_positions(r"\\{") == [2]  # escaped backslash, bare brace
        assert self._unescaped_brace_positions(r"\{") == []  # escaped brace
        assert self._unescaped_brace_positions(r"\\\{") == []  # escaped backslash + escaped brace

    def test_reserved_set_matches_the_implementation(self) -> None:
        # Guards against the set being trimmed without re-measuring.
        assert set(_RESERVED_IN_LITERAL) == set(RESERVED_LITERAL_CHARS)
        assert _RESERVED_IN_LITERAL[0] == "\\", "backslash must be replaced first"
