"""Tests for geoview_cpt.correction.u0 — Phase A-2 A2.5a."""
from __future__ import annotations

import numpy as np
import pytest

from geoview_cpt.correction.u0 import DEFAULT_GAMMA_W_KN_M3, hydrostatic_pressure
from geoview_cpt.model import CPTChannel


def _depth(values):
    return CPTChannel(name="depth", unit="m", values=values)


class TestHydrostatic:
    def test_default_gwt_at_surface(self):
        d = _depth([0.0, 1.0, 5.0, 10.0])
        u0 = hydrostatic_pressure(d)
        # 9.81 kN/m³ × depth → 0, 9.81, 49.05, 98.1 kPa
        assert np.allclose(u0.values, [0.0, 9.81, 49.05, 98.1])
        assert u0.unit == "kPa"
        assert u0.name == "u0"

    def test_unit_weight_default(self):
        assert DEFAULT_GAMMA_W_KN_M3 == 9.81

    def test_gwt_below_surface(self):
        d = _depth([0.0, 1.0, 2.0, 5.0])
        u0 = hydrostatic_pressure(d, gwt_m=2.0)
        # Above GWT (z < 2): u0 = 0; below: γ × (z - 2)
        assert np.allclose(u0.values, [0.0, 0.0, 0.0, 3 * 9.81])

    def test_custom_gamma_w(self):
        d = _depth([0.0, 10.0])
        u0 = hydrostatic_pressure(d, gamma_w=10.0)
        assert np.allclose(u0.values, [0.0, 100.0])

    def test_negative_gamma_rejected(self):
        with pytest.raises(ValueError):
            hydrostatic_pressure(_depth([0.0]), gamma_w=-1.0)

    def test_zero_gamma_rejected(self):
        with pytest.raises(ValueError):
            hydrostatic_pressure(_depth([0.0]), gamma_w=0.0)
