"""Tests for geoview_cpt.derivation.bq — Phase A-2 A2.5b."""
from __future__ import annotations

import numpy as np
import pytest

from geoview_cpt.derivation.bq import compute_bq
from geoview_cpt.model import CPTChannel


def _ch(name, unit, values):
    return CPTChannel(name=name, unit=unit, values=values)


class TestComputeBq:
    def test_simple(self):
        # u2=200, u0=100, qt=1MPa=1000kPa, sv0=20 → Bq = (200-100)/(1000-20) ≈ 0.102
        u2 = _ch("u2", "kPa", [200.0])
        u0 = _ch("u0", "kPa", [100.0])
        qt = _ch("qt", "MPa", [1.0])
        sv0 = _ch("sigma_v0", "kPa", [20.0])
        bq = compute_bq(u2, u0, qt, sv0)
        assert np.isclose(bq.values[0], 100.0 / 980.0, atol=1e-6)
        assert bq.unit == "-"
        assert bq.name == "Bq"

    def test_negative_excess_pore_pressure(self):
        # Sand dilation: u2 < u0 → negative Bq
        u2 = _ch("u2", "kPa", [50.0])
        u0 = _ch("u0", "kPa", [100.0])
        qt = _ch("qt", "MPa", [5.0])
        sv0 = _ch("sigma_v0", "kPa", [50.0])
        bq = compute_bq(u2, u0, qt, sv0)
        assert bq.values[0] < 0

    def test_qnet_below_floor_yields_zero(self):
        # qt - sv0 < 1 kPa → Bq = 0
        u2 = _ch("u2", "kPa", [10.0])
        u0 = _ch("u0", "kPa", [5.0])
        qt = _ch("qt", "kPa", [10.0])
        sv0 = _ch("sigma_v0", "kPa", [9.5])
        bq = compute_bq(u2, u0, qt, sv0)
        assert bq.values[0] == 0.0

    def test_array(self):
        u2 = _ch("u2", "kPa", [100, 200, 300])
        u0 = _ch("u0", "kPa", [50, 100, 150])
        qt = _ch("qt", "MPa", [1, 2, 3])
        sv0 = _ch("sigma_v0", "kPa", [10, 20, 30])
        bq = compute_bq(u2, u0, qt, sv0)
        expected = np.array([50, 100, 150]) / np.array([990, 1980, 2970])
        assert np.allclose(bq.values, expected)

    def test_shape_mismatch(self):
        u2 = _ch("u2", "kPa", [1.0])
        u0 = _ch("u0", "kPa", [1.0, 2.0])
        qt = _ch("qt", "MPa", [1.0])
        sv0 = _ch("sigma_v0", "kPa", [1.0])
        with pytest.raises(ValueError, match="shape"):
            compute_bq(u2, u0, qt, sv0)
