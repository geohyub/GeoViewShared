"""Tests for geoview_cpt.derivation.gamma — Phase A-2 A2.5b."""
from __future__ import annotations

import numpy as np
import pytest

from geoview_cpt.derivation.gamma import estimate_gamma_robertson_cabal_2010
from geoview_cpt.model import CPTChannel


def _ch(name, unit, values):
    return CPTChannel(name=name, unit=unit, values=values)


class TestEstimateGamma:
    def test_textbook_example(self):
        # Robertson & Cabal 2010 sample point:
        # qt = 5 MPa = 5000 kPa, Rf = 1% → check formula directly
        # γ/γw = 0.27×log10(1) + 0.36×log10(50) + 1.236
        #      = 0 + 0.36×1.69897 + 1.236 = 0.6116 + 1.236 = 1.8476
        # γ = 1.8476 × 9.81 ≈ 18.13 kN/m³
        qt = _ch("qt", "MPa", [5.0])
        rf = _ch("Rf", "%", [1.0])
        g = estimate_gamma_robertson_cabal_2010(qt, rf)
        assert np.isclose(g.values[0], 18.13, atol=0.05)
        assert g.unit == "kN/m^3"
        assert g.name == "gamma"

    def test_kpa_input(self):
        qt = _ch("qt", "kPa", [5000.0])
        rf = _ch("Rf", "%", [1.0])
        g = estimate_gamma_robertson_cabal_2010(qt, rf)
        assert np.isclose(g.values[0], 18.13, atol=0.05)

    def test_array(self):
        qt = _ch("qt", "MPa", [1.0, 5.0, 20.0])
        rf = _ch("Rf", "%", [2.0, 1.0, 0.5])
        g = estimate_gamma_robertson_cabal_2010(qt, rf)
        # Sanity: stiffer / cleaner → higher γ
        assert g.values[2] > g.values[1] > g.values[0]
        # Reasonable range 10..25 kN/m³
        for v in g.values:
            assert 10 < v < 25

    def test_low_rf_floor(self):
        qt = _ch("qt", "MPa", [5.0])
        rf = _ch("Rf", "%", [0.0])  # below floor
        g = estimate_gamma_robertson_cabal_2010(qt, rf)
        assert np.isfinite(g.values[0])

    def test_low_qt_floor(self):
        qt = _ch("qt", "MPa", [0.0])
        rf = _ch("Rf", "%", [1.0])
        g = estimate_gamma_robertson_cabal_2010(qt, rf)
        assert np.isfinite(g.values[0])

    def test_custom_gamma_w(self):
        qt = _ch("qt", "MPa", [5.0])
        rf = _ch("Rf", "%", [1.0])
        g_default = estimate_gamma_robertson_cabal_2010(qt, rf)
        g_custom = estimate_gamma_robertson_cabal_2010(qt, rf, gamma_w=10.0)
        # Different scaling
        ratio = g_custom.values[0] / g_default.values[0]
        assert np.isclose(ratio, 10.0 / 9.81, atol=1e-6)

    def test_negative_gamma_w_rejected(self):
        with pytest.raises(ValueError):
            estimate_gamma_robertson_cabal_2010(
                _ch("qt", "MPa", [1.0]),
                _ch("Rf", "%", [1.0]),
                gamma_w=-1.0,
            )

    def test_shape_mismatch(self):
        with pytest.raises(ValueError, match="shape"):
            estimate_gamma_robertson_cabal_2010(
                _ch("qt", "MPa", [1.0]),
                _ch("Rf", "%", [1.0, 2.0]),
            )
