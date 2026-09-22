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
        r"(name eq 'O\'Brien' or name eq 'C:\\NAS' or name eq null"
        r" or name eq true or name eq false or name eq 42 or name eq 1.5)"
    )
    assert str(Filter().in_("name", values)) == expected
    assert build_filter(name=values) == expected


def test_builders_quote_wildcards() -> None:
    # '?' forces the rx path; the backslash and apostrophe must survive both
    # POSIX-ERE escaping and quote_value literal escaping.
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
    """Wildcards translate to supported operators; VergeOS has no LIKE (#103)."""

    def test_prefix_becomes_bw(self) -> None:
        assert build_filter(name="web*") == "name bw 'web'"

    def test_suffix_becomes_ew(self) -> None:
        assert build_filter(name="*web") == "name ew 'web'"

    def test_contains_becomes_cs(self) -> None:
        assert build_filter(name="*web*") == "name cs 'web'"

    def test_pure_star_matches_everything(self) -> None:
        assert build_filter(name="*") == "name bw ''"
        assert build_filter(name="**") == "name bw ''"

    def test_question_mark_becomes_anchored_rx(self) -> None:
        assert build_filter(name="web?") == "name rx '^web.$'"
        assert build_filter(name="?") == "name rx '^.$'"

    def test_interior_star_becomes_anchored_rx(self) -> None:
        assert build_filter(name="a*b") == "name rx '^a.*b$'"

    def test_mixed_pattern(self) -> None:
        assert build_filter(name="*a?b*") == "name rx '^.*a.b.*$'"

    def test_rx_pattern_is_never_empty(self) -> None:
        """An empty rx pattern matches every row on the platform (fail-open)."""
        for pattern in ["*", "?", "**", "*?", "a*b", "*a*"]:
            result = build_filter(name=pattern)
            assert "rx ''" not in result, f"{pattern!r} produced empty rx: {result}"

    def test_posix_metacharacters_escaped_in_rx(self) -> None:
        # '?' forces the rx path; every ERE metacharacter must be escaped.
        # The wire literal doubles each backslash (quote_value escaping);
        # the server unescapes it back to a single ERE escape.
        result = build_filter(name="a.b[c](d)+e{f}|g^h$i?")
        expected = r"name rx '^a\\.b\\[c\\]\\(d\\)\\+e\\{f\\}\\|g\\^h\\$i.$'"
        assert result == expected

    def test_backslash_in_pattern_survives_both_escapes(self) -> None:
        # literal backslash: ERE-escaped to \\ then wire-doubled to \\\\
        assert build_filter(name="back\\slash?") == r"name rx '^back\\\\slash.$'"

    def test_old_like_wildcards_are_literal(self) -> None:
        """'%' and '_' were LIKE wildcards; they must now be literal text."""
        assert build_filter(name="50%*") == "name bw '50%'"
        assert build_filter(name="under_*") == "name bw 'under_'"
        assert build_filter(name="a%b?") == "name rx '^a%b.$'"

    def test_translation_is_case_sensitive_cs_not_ct(self) -> None:
        assert " cs " in build_filter(name="*Web*")
        assert " ct " not in build_filter(name="*Web*")

    def test_no_like_token_ever_emitted(self) -> None:
        for pattern in ["web*", "*web", "*web*", "a*b", "a?b", "*", "?"]:
            assert " like " not in build_filter(name=pattern)
            assert " like " not in str(Filter().like("name", pattern))

    def test_filter_like_matches_build_filter(self) -> None:
        for pattern in ["web*", "*web", "*web*", "a*b", "web?"]:
            assert str(Filter().like("name", pattern)) == build_filter(name=pattern)

    def test_like_without_wildcards_is_exact(self) -> None:
        assert str(Filter().like("name", "exact")) == "name eq 'exact'"


class TestInTranslation:
    """Lists expand to parenthesized or-chains; VergeOS has no IN (#103)."""

    def test_or_chain_is_parenthesized(self) -> None:
        # Mandatory: and/or have no precedence on the platform (left-to-right)
        result = build_filter(status=["a", "b"], enabled=True)
        assert result == "(status eq 'a' or status eq 'b') and enabled eq true"

    def test_single_element_list(self) -> None:
        assert build_filter(name=["only"]) == "(name eq 'only')"

    def test_wildcards_translate_inside_lists(self) -> None:
        result = build_filter(name=["web*", "db1"])
        assert result == "(name bw 'web' or name eq 'db1')"

    def test_mixed_value_types(self) -> None:
        result = build_filter(x=[None, True, 42, "s"])
        assert result == "(x eq null or x eq true or x eq 42 or x eq 's')"

    def test_empty_list_raises(self) -> None:
        with pytest.raises(ValueError, match="empty sequence"):
            build_filter(name=[])
        with pytest.raises(ValueError, match="empty sequence"):
            Filter().in_("name", [])

    def test_no_in_token_ever_emitted(self) -> None:
        for values in [["a"], ["a", "b"], [1, 2], ["x*", "y"]]:
            assert " in (" not in build_filter(name=values)
            assert " in (" not in str(Filter().in_("name", values))

    def test_scalar_to_in_is_normalized(self) -> None:
        assert str(Filter().in_("name", "solo")) == "(name eq 'solo')"


class TestNewOperatorMethods:
    """Primitive builder methods for the platform's native operators."""

    def test_bw(self) -> None:
        assert str(Filter().bw("name", "web")) == "name bw 'web'"

    def test_ew(self) -> None:
        assert str(Filter().ew("name", "01")) == "name ew '01'"

    def test_cs(self) -> None:
        assert str(Filter().cs("name", "Web")) == "name cs 'Web'"

    def test_ct(self) -> None:
        assert str(Filter().ct("name", "WEB")) == "name ct 'WEB'"

    def test_rx(self) -> None:
        assert str(Filter().rx("name", "^web-[0-9]+$")) == "name rx '^web-[0-9]+$'"

    def test_chaining_with_implicit_and(self) -> None:
        f = Filter().bw("name", "zz").ct("description", "probe")
        assert str(f) == "name bw 'zz' and description ct 'probe'"

    def test_values_are_quoted(self) -> None:
        assert str(Filter().bw("name", "O'Brien")) == r"name bw 'O\'Brien'"
