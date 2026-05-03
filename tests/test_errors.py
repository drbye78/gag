"""Tests for core/errors.py Result class."""

import pytest

from core.errors import Result


class TestResultOk:
    def test_ok_creates_success_result(self):
        r = Result.ok(42)
        assert r.is_ok is True
        assert r.is_err is False

    def test_ok_value(self):
        r = Result.ok("hello")
        assert r.value == "hello"

    def test_ok_error_is_none(self):
        r = Result.ok(42)
        assert r.error == "Unknown"


class TestResultErr:
    def test_err_creates_error_result(self):
        r = Result.err("something went wrong")
        assert r.is_ok is False
        assert r.is_err is True

    def test_err_error_message(self):
        r = Result.err("bad input")
        assert r.error == "bad input"

    def test_err_value_raises(self):
        r = Result.err("oops")
        with pytest.raises(ValueError, match="Result is error: oops"):
            _ = r.value


class TestResultEquality:
    def test_equal_ok_results(self):
        assert Result.ok(42) == Result.ok(42)

    def test_equal_err_results(self):
        assert Result.err("x") == Result.err("x")

    def test_not_equal_ok_vs_err(self):
        assert Result.ok(42) != Result.err("42")

    def test_not_equal_different_values(self):
        assert Result.ok(1) != Result.ok(2)

    def test_not_equal_to_non_result(self):
        assert Result.ok(42).__eq__("not a result") is NotImplemented


class TestResultUnwrapOr:
    def test_unwrap_or_on_ok(self):
        r = Result.ok(99)
        assert r.unwrap_or(0) == 99

    def test_unwrap_or_on_err(self):
        r = Result.err("fail")
        assert r.unwrap_or(0) == 0

    def test_unwrap_or_none_default(self):
        r = Result.err("fail")
        assert r.unwrap_or(None) is None


class TestResultRepr:
    def test_repr_ok(self):
        r = Result.ok(42)
        assert repr(r) == "Ok(42)"

    def test_repr_err(self):
        r = Result.err("oops")
        assert repr(r) == "Err('oops')"


class TestResultSlots:
    def test_slots_allows_v_and_e(self):
        r = Result.ok(1)
        assert hasattr(r, "_v")
        assert hasattr(r, "_e")
        assert r._v == 1
        assert r._e is None

    def test_slots_disallows_arbitrary_attrs(self):
        r = Result.ok(1)
        with pytest.raises(AttributeError):
            r.random_attr = "nope"
