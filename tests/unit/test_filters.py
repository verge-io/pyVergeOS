"""Tests for filter builder."""

from pyvergeos.filters import Filter, build_filter


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
        assert str(f) == "name like 'web%'"

    def test_like_with_question(self) -> None:
        f = Filter().like("name", "web?")
        assert str(f) == "name like 'web_'"

    def test_in_with_list(self) -> None:
        f = Filter().in_("status", ["running", "stopped"])
        assert str(f) == "status in ('running', 'stopped')"

    def test_and_connector(self) -> None:
        f = Filter().eq("status", "running").and_().gt("ram", 2048)
        assert str(f) == "status eq 'running' and ram gt 2048"

    def test_implicit_and(self) -> None:
        """AND is implicit between conditions - no need to call and_()."""
        f = Filter().eq("status", "running").gt("ram", 2048).like("name", "web*")
        assert str(f) == "status eq 'running' and ram gt 2048 and name like 'web%'"

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
        assert str(f) == "name eq 'test''s vm'"

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
        assert result == "name like 'web%'"

    def test_list_values(self) -> None:
        result = build_filter(status=["running", "stopped"])
        assert result == "status in ('running', 'stopped')"

    def test_integer_value(self) -> None:
        result = build_filter(ram=4096)
        assert result == "ram eq 4096"

    def test_boolean_value(self) -> None:
        result = build_filter(enabled=True)
        assert result == "enabled eq true"

    def test_none_values_skipped(self) -> None:
        result = build_filter(status="running", name=None)
        assert result == "status eq 'running'"
