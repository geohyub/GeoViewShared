"""Tests for geoview_cpt.derivation.rf — Phase A-2 A2.5b."""
from __future__ import annotations

import numpy as np
import pytest

from geoview_cpt.derivation.rf import compute_rf
from geoview_cpt.model import CPTChannel


def _ch(name, unit, values):
    return CPTChannel(name=name, unit=unit, values=values)


class TestComputeRf:
    def test_simple_ratio(self):
        # qt = 10 MPa, fs = 100 kPa = 0.1 MPa → Rf = 1.0%
        qt = _ch("qt", "MPa", [10.0])
        fs = _ch("fs", "kPa", [100.0])
        rf = compute_rf(fs, qt)
        assert np.isclose(rf.values[0], 1.0)
        assert rf.unit == "%"
        assert rf.name == "Rf"

    def test_canonical_mixed_units(self):
        qt = _ch("qt", "MPa", [5.0])
        fs = _ch("fs", "kPa", [25.0])  # 0.025 MPa
        rf = compute_rf(fs, qt)
        # Rf = 0.025 / 5 × 100 = 0.5
        assert np.isclose(rf.values[0], 0.5)

    def test_both_kpa(self):
        qt = _ch("qt", "kPa", [10000.0])
        fs = _ch("fs", "kPa", [100.0])
        rf = compute_rf(fs, qt)
        assert np.isclose(rf.values[0], 1.0)

    def test_zero_qt_yields_zero(self):
        qt = _ch("qt", "MPa", [0.0])
        fs = _ch("fs", "kPa", [10.0])
        rf = compute_rf(fs, qt)
        assert rf.values[0] == 0.0

    def test_array(self):
        qt = _ch("qt", "MPa", [10.0, 20.0, 5.0])
        fs = _ch("fs", "kPa", [100.0, 400.0, 25.0])
        rf = compute_rf(fs, qt)
        assert np.allclose(rf.values, [1.0, 2.0, 0.5])

    def test_shape_mismatch(self):
        with pytest.raises(ValueError, match="shape"):
            compute_rf(_ch("fs", "kPa", [1.0]), _ch("qt", "MPa", [1.0, 2.0]))
