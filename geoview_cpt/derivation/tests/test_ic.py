"""Tests for geoview_cpt.derivation.ic — Phase A-2 A2.5b."""
from __future__ import annotations

import numpy as np
import pytest

from geoview_cpt.derivation.ic import (
    compute_fr_normalized,
    compute_ic,
    compute_qt_normalized,
)
from geoview_cpt.model import CPTChannel


def _ch(name, unit, values):
    return CPTChannel(name=name, unit=unit, values=values)


class TestQtNormalized:
    def test_simple(self):
        # Qt1 = (qt - sv0) / spv0
        qt = _ch("qt", "MPa", [1.0])      # 1000 kPa
        sv0 = _ch("sigma_v0", "kPa", [50.0])
        spv0 = _ch("sigma_prime_v0", "kPa", [40.0])
        qt1 = compute_qt_normalized(qt, sv0, spv0)
        assert np.isclose(qt1.values[0], (1000 - 50) / 40)
        assert qt1.name == "Qt1"
        assert qt1.unit == "-"

    def test_zero_spv0_yields_zero(self):
        qt = _ch("qt", "MPa", [1.0])
        sv0 = _ch("sigma_v0", "kPa", [0.0])
        spv0 = _ch("sigma_prime_v0", "kPa", [0.0])
        qt1 = compute_qt_normalized(qt, sv0, spv0)
        assert qt1.values[0] == 0.0


class TestFrNormalized:
    def test_simple(self):
        fs = _ch("fs", "kPa", [10.0])
        qt = _ch("qt", "MPa", [1.0])
        sv0 = _ch("sigma_v0", "kPa", [50.0])
        fr = compute_fr_normalized(fs, qt, sv0)
        # Fr = 10 / (1000 - 50) × 100 ≈ 1.0526
        assert np.isclose(fr.values[0], 10.0 / 950.0 * 100.0)
        assert fr.name == "Fr"
        assert fr.unit == "%"

    def test_low_qnet_yields_zero(self):
        fs = _ch("fs", "kPa", [10.0])
        qt = _ch("qt", "kPa", [10.0])
        sv0 = _ch("sigma_v0", "kPa", [9.5])
        fr = compute_fr_normalized(fs, qt, sv0)
        assert fr.values[0] == 0.0


class TestComputeIc:
    def test_known_value(self):
        # Robertson textbook example: Qt1=20, Fr=2 → Ic ≈ 2.27
        qt1 = _ch("Qt1", "-", [20.0])
        fr = _ch("Fr", "%", [2.0])
        ic = compute_ic(qt1, fr)
        a = 3.47 - np.log10(20)
        b = np.log10(2) + 1.22
        expected = np.sqrt(a * a + b * b)
        assert np.isclose(ic.values[0], expected)
        assert ic.name == "Ic"

    def test_high_resistance_low_ic(self):
        # Sand: high Qt1, low Fr → low Ic
        qt1 = _ch("Qt1", "-", [200.0])
        fr = _ch("Fr", "%", [0.3])
        ic = compute_ic(qt1, fr)
        assert ic.values[0] < 2.0  # sand range

    def test_clay_high_ic(self):
        qt1 = _ch("Qt1", "-", [3.0])
        fr = _ch("Fr", "%", [5.0])
        ic = compute_ic(qt1, fr)
        assert ic.values[0] > 3.0  # clay range

    def test_log_floor_no_crash(self):
        qt1 = _ch("Qt1", "-", [0.0, 1e-10])
        fr = _ch("Fr", "%", [0.0, 1e-10])
        ic = compute_ic(qt1, fr)
        assert np.all(np.isfinite(ic.values))

    def test_shape_mismatch(self):
        with pytest.raises(ValueError, match="shape"):
            compute_ic(_ch("Qt1", "-", [1.0]), _ch("Fr", "%", [1.0, 2.0]))
