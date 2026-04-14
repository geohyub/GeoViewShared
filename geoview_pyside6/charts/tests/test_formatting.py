"""Tests for geoview_pyside6.charts.formatting — Phase A-1 A1.4."""
from __future__ import annotations

import math

import pytest

from geoview_pyside6.charts.formatting import (
    NumberFormatError,
    format_axis_label,
    format_number,
)


class TestIntegers:
    def test_small_int(self):
        assert format_number(42) == "42"

    def test_thousands_separator(self):
        assert format_number(1234567) == "1,234,567"

    def test_negative(self):
        assert format_number(-12345) == "-12,345"

    def test_zero(self):
        assert format_number(0) == "0"

    def test_intlike_float_prints_as_int(self):
        assert format_number(1000.0) == "1,000"


class TestFloats:
    def test_default_two_decimals(self):
        assert format_number(1234.5) == "1,234.50"

    def test_custom_decimals(self):
        assert format_number(3.14159, decimals=4) == "3.1416"

    def test_zero_decimals(self):
        assert format_number(12.7, decimals=0) == "13"

    def test_negative_float(self):
        assert format_number(-0.5) == "-0.50"

    def test_very_small_truncates_by_default(self):
        assert format_number(0.000123) == "0.00"

    def test_very_small_high_precision(self):
        assert format_number(0.000123, decimals=6) == "0.000123"


class TestScientificOptIn:
    def test_scientific_refused_by_default(self):
        # tiny value keeps decimal form
        assert "e" not in format_number(1e-6, decimals=4).lower()

    def test_scientific_allowed_for_huge(self):
        s = format_number(5e15, allow_scientific=True, decimals=2)
        assert "e" in s.lower()

    def test_scientific_allowed_for_tiny(self):
        s = format_number(1e-6, allow_scientific=True, decimals=2)
        assert "e" in s.lower()

    def test_scientific_not_triggered_in_normal_range(self):
        s = format_number(1234.5, allow_scientific=True)
        assert s == "1,234.50"


class TestSpecialValues:
    def test_nan(self):
        assert format_number(float("nan")) == "NaN"

    def test_positive_inf(self):
        assert format_number(math.inf) == "∞"

    def test_negative_inf(self):
        assert format_number(-math.inf) == "-∞"

    def test_bool_rejected(self):
        with pytest.raises(NumberFormatError):
            format_number(True)  # type: ignore[arg-type]

    def test_string_rejected(self):
        with pytest.raises(NumberFormatError):
            format_number("12")  # type: ignore[arg-type]

    def test_negative_decimals_rejected(self):
        with pytest.raises(NumberFormatError):
            format_number(1.0, decimals=-1)


class TestUnit:
    def test_unit_appended(self):
        assert format_number(12.5, unit="m") == "12.50 m"

    def test_unit_with_integer(self):
        assert format_number(1000, unit="mV") == "1,000 mV"

    def test_unit_with_nan(self):
        assert format_number(float("nan"), unit="°") == "NaN °"


class TestFormatAxisLabel:
    def test_list_of_values(self):
        assert format_axis_label([1, 1000, 1_000_000]) == ["1", "1,000", "1,000,000"]

    def test_empty(self):
        assert format_axis_label([]) == []

    def test_decimals_propagated(self):
        assert format_axis_label([1.5, 2.5], decimals=1) == ["1.5", "2.5"]
