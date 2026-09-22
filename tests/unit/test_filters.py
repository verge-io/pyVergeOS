"""Tests for filter builder."""

from pathlib import PureWindowsPath
from typing import Any

import pytest

from pyvergeos.filters import Filter, build_filter, combine_filters, quote_value


class TestFilter:
    """Tests for Filter class."""

    def test_eq(self) -> None:
        f = Filter().eq("status", "running")
        assert str(f) == "status eq 'running'"

    def test_ne(self) -> None:
        f = Filter().ne("status", "stopped")
        assert str(f) == "status ne 'stopped'"

    def test_lt(self) -> None:
        f = Filter().lt("ram", 4096)
        assert str(f) == "ram lt 4096"

    def test_gt(self) -> None:
        f = Filter().gt("cpu_cores", 2)
        assert str(f) == "cpu_cores gt 2"

    def test_le(self) -> None:
        f = Filter().le("ram", 4096)
        assert str(f) == "ram le 4096"

    def test_ge(self) -> None:
        f = Filter().ge("cpu_cores", 2)
        assert str(f) == "cpu_cores ge 2"

    def test_like_with_asterisk(self) -> None:
        f = Filter().like("name", "web*")
        assert str(f) == "name bw 'web'"

    def test_like_with_question(self) -> None:
        f = Filter().like("name", "web?")
        assert str(f) == "name rx '^web.$'"

    def test_in_with_list(self) -> None:
        f = Filter().in_("status", ["running", "stopped"])
        assert str(f) == "(status eq 'running' or status eq 'stopped')"

    def test_and_connector(self) -> None:
        f = Filter().eq("status", "running").and_().gt("ram", 2048)
        assert str(f) == "status eq 'running' and ram gt 2048"

    def test_implicit_and(self) -> None:
        """AND is implicit between conditions - no need to call and_()."""
        f = Filter().eq("status", "running").gt("ram", 2048).like("name", "web*")
        assert str(f) == "status eq 'running' and ram gt 2048 and name bw 'web'"

    def test_or_connector(self) -> None:
        f = Filter().eq("os", "linux").or_().eq("os", "windows")
        assert str(f) == "os eq 'linux' or os eq 'windows'"

    def test_bool_value_true(self) -> None:
        f = Filter().eq("enabled", True)
        assert str(f) == "enabled eq true"

    def test_bool_value_false(self) -> None:
        f = Filter().eq("enabled", False)
        assert str(f) == "enabled eq false"

    def test_none_value(self) -> None:
        f = Filter().eq("owner", None)
        assert str(f) == "owner eq null"

    def test_escape_quotes(self) -> None:
        f = Filter().eq("name", "test's vm")
        assert str(f) == "name eq 'test\\'s vm'"

    def test_empty_filter_is_falsy(self) -> None:
        f = Filter()
        assert not f

    def test_non_empty_filter_is_truthy(self) -> None:
        f = Filter().eq("name", "test")
        assert f

    def test_repr(self) -> None:
        f = Filter().eq("name", "test")
        assert repr(f) == "Filter(\"name eq 'test'\")"


class TestBuildFilter:
    """Tests for build_filter function."""

    def test_simple_equality(self) -> None:
        result = build_filter(status="running")
        assert result == "status eq 'running'"

    def test_multiple_fields(self) -> None:
        result = build_filter(status="running", os_family="linux")
        assert "status eq 'running'" in result
        assert "os_family eq 'linux'" in result
        assert " and " in result

    def test_wildcard_pattern(self) -> None:
        result = build_filter(name="web*")
        assert result == "name bw 'web'"

    def test_list_values(self) -> None:
        result = build_filter(status=["running", "stopped"])
        assert result == "(status eq 'running' or status eq 'stopped')"

    def test_integer_value(self) -> None:
        result = build_filter(ram=4096)
        assert result == "ram eq 4096"

    def test_boolean_value(self) -> None:
        result = build_filter(enabled=True)
        assert result == "enabled eq true"

    def test_none_values_skipped(self) -> None:
        result = build_filter(status="running", name=None)
        assert result == "status eq 'running'"


# Expected wire literals are explicit: these must not share the implementation's
# escaping logic, or the SQL-doubling regression could go unnoticed again.
STRING_LITERALS = [
    ("", "''"),
    ("plain", "'plain'"),
    ("O'Brien", r"'O\'Brien'"),
    (r"C:\NAS\share", r"'C:\\NAS\\share'"),
    ("trailing\\", r"'trailing\\'"),
    (r"back\'quote", r"'back\\\'quote'"),
    ('a"b', "'a\"b'"),
    ("équipe's", r"'équipe\'s'"),
    ("x' or name ne 'x", r"'x\' or name ne \'x'"),
]


@pytest.mark.parametrize(("value", "literal"), STRING_LITERALS)
def test_quote_value(value: str, literal: str) -> None:
    assert quote_value(value) == literal


@pytest.mark.parametrize(("value", "literal"), STRING_LITERALS)
def test_builders_quote_equality(value: str, literal: str) -> None:
    assert str(Filter().eq("name", value)) == f"name eq {literal}"
    assert build_filter(name=value) == f"name eq {literal}"


@pytest.mark.parametrize("container", [list, tuple])
def test_builders_quote_in_values(container: Any) -> None:
    values = container(["O'Brien", r"C:\NAS", None, True, False, 42, 1.5])
    expected = (
        r"(name eq 'O\'Brien' or name eq 'C:\\NAS' or name eq null or name eq true "
        r"or name eq false or name eq 42 or name eq 1.5)"
    )
    assert str(Filter().in_("name", values)) == expected
    assert build_filter(name=values) == expected


def test_builders_quote_wildcards() -> None:
    # '?' forces the rx path; the literal backslash is regex-escaped and then
    # quote_value-escaped, so four backslashes reach the wire for one literal.
    value = r"O'Brien\share*?"
    expected = r"name rx '^O\'Brien\\\\share.*.$'"
    assert str(Filter().like("name", value)) == expected
    assert build_filter(name=value) == expected


def test_exact_filter_preserves_literal_wildcards() -> None:
    assert str(Filter().eq("name", "a*?%_")) == "name eq 'a*?%_'"
    assert quote_value("a*?%_") == "'a*?%_'"


def test_builders_stringify_objects() -> None:
    value = PureWindowsPath(r"C:\O'Brien\share")
    expected = r"name eq 'C:\\O\'Brien\\share'"
    assert str(Filter().eq("name", value)) == expected
    assert build_filter(name=value) == expected


class TestCombineFilters:
    """Tests for combine_filters (issue #96)."""

    def test_both_supplied_are_merged(self) -> None:
        result = combine_filters("is_snapshot eq false", {"name": "web1"})
        assert result == "(is_snapshot eq false) and (name eq 'web1')"

    def test_filter_only(self) -> None:
        assert combine_filters("name eq 'a'", {}) == "name eq 'a'"

    def test_kwargs_only(self) -> None:
        assert combine_filters(None, {"name": "a"}) == "name eq 'a'"

    def test_neither_returns_none(self) -> None:
        assert combine_filters(None, {}) is None
        assert combine_filters("", {}) is None

    def test_all_none_kwargs_raise(self) -> None:
        with pytest.raises(ValueError, match="empty filter"):
            combine_filters(None, {"name": None})
        with pytest.raises(ValueError, match="empty filter"):
            combine_filters("vnet eq 1", {"name": None, "enabled": None})

    def test_partial_none_kwargs_are_kept(self) -> None:
        result = combine_filters(None, {"name": "DMZ", "enabled": None})
        assert result == "name eq 'DMZ'"

    def test_multiple_kwargs(self) -> None:
        result = combine_filters("vnet eq 1", {"name": "a", "enabled": True})
        assert result == "(vnet eq 1) and (name eq 'a' and enabled eq true)"


class TestWildcardTranslation:
    """Wildcards map to the VergeOS grammar, never to `like` (issue #103).

    Expected strings are written out literally rather than derived from the
    implementation, and every mapping below was verified on the wire against
    VergeOS 26.1.8.
    """

    @pytest.mark.parametrize(
        ("pattern", "expected"),
        [
            # No wildcard: plain equality.
            ("web", "name eq 'web'"),
            # Simple shapes use the dedicated (and cheaper) operators.
            ("web*", "name bw 'web'"),
            ("*web", "name ew 'web'"),
            ("*web*", "name cs 'web'"),
            ("**web**", "name cs 'web'"),
            # All-wildcard matches everything; `cs ''` would match nothing.
            ("*", "name bw ''"),
            ("***", "name bw ''"),
            # Anything else becomes an anchored regex.
            ("a*b", "name rx '^a.*b$'"),
            ("web?", "name rx '^web.$'"),
            ("?web", "name rx '^.web$'"),
            ("?", "name rx '^.$'"),
            ("*a*b*", "name rx '^.*a.*b.*$'"),
            # Regex metacharacters in the literal parts are escaped.
            ("a.b?", r"name rx '^a\\.b.$'"),
            ("a+b?", r"name rx '^a\\+b.$'"),
            ("a(b)?", r"name rx '^a\\(b\\).$'"),
            ("a[b]?", r"name rx '^a\\[b\\].$'"),
            ("a^b?", r"name rx '^a\\^b.$'"),
            ("a$b?", r"name rx '^a\\$b.$'"),
            ("a|b?", r"name rx '^a\\|b.$'"),
            # '%' and '_' were the old LIKE wildcards; now plain literals.
            ("50%*", "name bw '50%'"),
            ("under_*", "name bw 'under_'"),
            ("%_?", "name rx '^%_.$'"),
        ],
    )
    def test_pattern_maps_to_supported_operator(self, pattern: str, expected: str) -> None:
        assert build_filter(name=pattern) == expected
        assert str(Filter().like("name", pattern)) == expected

    def test_simple_shapes_are_case_sensitive_operators(self) -> None:
        """bw/ew/cs are all case-sensitive; ct (insensitive) is never chosen.

        Mixing ct in would make matching depend on wildcard position.
        """
        for pattern in ("web*", "*web", "*web*"):
            assert " ct " not in build_filter(name=pattern)

    def test_anchors_prevent_substring_matches(self) -> None:
        """rx is unanchored on the platform, so ^ and $ must be emitted."""
        result = build_filter(name="a*b")
        assert result.startswith("name rx '^")
        assert result.endswith("$'")

    def test_backslash_is_regex_escaped_then_quote_escaped(self) -> None:
        r"""One literal backslash becomes four: \ -> \\ (regex) -> \\\\ (quote)."""
        assert build_filter(name="a\\b?") == r"name rx '^a\\\\b.$'"

    def test_apostrophe_survives_the_regex_path(self) -> None:
        assert build_filter(name="O'B?") == r"name rx '^O\'B.$'"

    def test_escaping_is_not_python_re_escape(self) -> None:
        r"""Python's re.escape() escapes far more than this engine accepts.

        re.escape() escapes ' ', '#', '&', '-' and '~' among others. Escaping
        only true metacharacters keeps patterns readable and avoids relying on
        escapes the platform's engine may not define.
        """
        assert build_filter(name="a b?") == "name rx '^a b.$'"
        assert build_filter(name="a-b?") == "name rx '^a-b.$'"
        assert build_filter(name="a#b?") == "name rx '^a#b.$'"
        assert build_filter(name="a~b?") == "name rx '^a~b.$'"

    def test_brace_is_escaped_as_a_metacharacter(self) -> None:
        r"""'{' is a regex metacharacter and is escaped as one.

        '{' is additionally reserved by the filter-string grammar and must be
        escaped by quote_value(), which is issue #100 and not fixed here.
        Until it is, a braced value fails for every operator including plain
        ``eq``, so the wildcard path is no worse off than the equality path.
        The two escapes compose: once quote_value() escapes '{', the '\\{'
        emitted here survives to the regex engine as a literal brace.
        """
        assert build_filter(name="a{b?") == r"name rx '^a\\{b.$'"
        # The closing brace, by contrast, is accepted by the platform.
        assert build_filter(name="a}b?") == r"name rx '^a\\}b.$'"


class TestInTranslation:
    """Lists expand to an `or` chain, never to `in` (issue #103)."""

    def test_multiple_values_are_parenthesised(self) -> None:
        assert build_filter(status=["running", "stopped"]) == (
            "(status eq 'running' or status eq 'stopped')"
        )

    def test_parentheses_keep_and_merge_correct(self) -> None:
        result = combine_filters("is_snapshot eq false", {"name": ["a", "b"]})
        assert result == "(is_snapshot eq false) and ((name eq 'a' or name eq 'b'))"

    def test_single_value_needs_no_parentheses(self) -> None:
        assert build_filter(status=["running"]) == "status eq 'running'"

    def test_tuple_behaves_like_list(self) -> None:
        assert build_filter(status=("a", "b")) == "(status eq 'a' or status eq 'b')"

    def test_numeric_values(self) -> None:
        assert build_filter(key=[1, 33]) == "(key eq 1 or key eq 33)"

    def test_wildcards_inside_a_list_are_translated(self) -> None:
        assert build_filter(name=["web*", "db*"]) == "(name bw 'web' or name bw 'db')"

    def test_mixed_wildcard_and_exact(self) -> None:
        assert build_filter(name=["web*", "db1"]) == "(name bw 'web' or name eq 'db1')"

    @pytest.mark.parametrize("empty", [[], ()])
    def test_empty_sequence_raises(self, empty: Any) -> None:
        with pytest.raises(ValueError, match="empty sequence"):
            build_filter(name=empty)
        with pytest.raises(ValueError, match="empty sequence"):
            Filter().in_("name", empty)


class TestGrammarSafety:
    """No generated filter may contain an operator the platform rejects."""

    @pytest.mark.parametrize(
        "kwargs",
        [
            {"name": "web*"},
            {"name": "*web"},
            {"name": "*web*"},
            {"name": "a*b"},
            {"name": "web?"},
            {"name": "*"},
            {"name": ["a", "b"]},
            {"name": ["a*", "b?"]},
            {"name": "a.b*"},
            {"name": "50%*"},
        ],
    )
    def test_no_unsupported_operator_token(self, kwargs: Any) -> None:
        result = build_filter(**kwargs)
        assert " like " not in result
        assert " in (" not in result
        # 're' is accepted by the platform but silently matches nothing.
        assert " re " not in result

    def test_filter_operator_enum_has_no_unsupported_members(self) -> None:
        from pyvergeos.filters import FilterOperator

        values = {op.value for op in FilterOperator}
        assert "like" not in values
        assert "in" not in values
        # The documented VergeOS grammar.
        assert values == {"eq", "ne", "gt", "ge", "lt", "le", "bw", "ew", "cs", "ct", "rx"}


class TestNewOperatorMethods:
    """The platform's string operators are reachable from Filter."""

    def test_bw(self) -> None:
        assert str(Filter().bw("name", "web")) == "name bw 'web'"

    def test_ew(self) -> None:
        assert str(Filter().ew("name", "web")) == "name ew 'web'"

    def test_cs(self) -> None:
        assert str(Filter().cs("name", "web")) == "name cs 'web'"

    def test_ct(self) -> None:
        assert str(Filter().ct("name", "web")) == "name ct 'web'"

    def test_rx_is_sent_verbatim(self) -> None:
        assert str(Filter().rx("name", "^web.*$")) == "name rx '^web.*$'"

    def test_operators_quote_values(self) -> None:
        assert str(Filter().cs("name", "O'Brien")) == r"name cs 'O\'Brien'"

    def test_chaining_with_implicit_and(self) -> None:
        f = Filter().bw("name", "web").ct("description", "prod")
        assert str(f) == "name bw 'web' and description ct 'prod'"
