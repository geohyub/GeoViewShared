"""Tests for geoview_cpt.correction.units — Phase A-2 A2.5a."""
from __future__ import annotations

import numpy as np
import pytest

from geoview_cpt.correction.units import UnitError, to_kpa, to_mpa
from geoview_cpt.model import CPTChannel


class TestToMpa:
    def test_passthrough_when_mpa(self):
        ch = CPTChannel(name="qc", unit="MPa", values=[1.0, 2.0])
        out = to_mpa(ch)
        assert np.array_equal(out, [1.0, 2.0])

    def test_kpa_to_mpa_division(self):
        ch = CPTChannel(name="fs", unit="kPa", values=[1000.0, 500.0])
        out = to_mpa(ch)
        assert np.allclose(out, [1.0, 0.5])

    def test_unknown_unit_raises(self):
        ch = CPTChannel(name="q", unit="psi", values=[1.0])
        with pytest.raises(UnitError):
            to_mpa(ch)

    def test_empty_unit_rejected(self):
        ch = CPTChannel(name="q", unit="", values=[1.0])
        with pytest.raises(UnitError):
            to_mpa(ch)


class TestToKpa:
    def test_passthrough_when_kpa(self):
        ch = CPTChannel(name="fs", unit="kPa", values=[10.0, 20.0])
        out = to_kpa(ch)
        assert np.array_equal(out, [10.0, 20.0])

    def test_mpa_to_kpa_multiplication(self):
        ch = CPTChannel(name="qc", unit="MPa", values=[1.0, 2.5])
        out = to_kpa(ch)
        assert np.allclose(out, [1000.0, 2500.0])

    def test_unknown_unit_raises(self):
        ch = CPTChannel(name="x", unit="bar", values=[1.0])
        with pytest.raises(UnitError):
            to_kpa(ch)


class TestErrorMessage:
    def test_error_carries_channel_name(self):
        ch = CPTChannel(name="weird", unit="bar", values=[1.0])
        with pytest.raises(UnitError) as exc:
            to_mpa(ch)
        assert "weird" in str(exc.value)
        assert "bar" in str(exc.value)
