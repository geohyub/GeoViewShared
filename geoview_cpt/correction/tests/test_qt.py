"""Tests for geoview_cpt.correction.qt — Phase A-2 A2.5a."""
from __future__ import annotations

import numpy as np
import pytest

from geoview_cpt.correction.qt import compute_qt
from geoview_cpt.correction.units import UnitError
from geoview_cpt.model import CPTChannel


def _qc(values, unit="MPa"):
    return CPTChannel(name="qc", unit=unit, values=values)


def _u2(values, unit="kPa"):
    return CPTChannel(name="u2", unit=unit, values=values)


class TestComputeQt:
    def test_basic_mpa_inputs(self):
        # qt = qc + u2 * (1 - a)
        qc = _qc([10.0], unit="MPa")
        u2 = _u2([0.5], unit="MPa")
        qt = compute_qt(qc, u2, a=0.7032)
        # 10 + 0.5 * (1 - 0.7032) = 10 + 0.1484 = 10.1484
        assert np.isclose(qt.values[0], 10.1484, atol=1e-4)
        assert qt.unit == "MPa"
        assert qt.name == "qt"

    def test_canonical_mixed_units(self):
        """Parser convention: qc in MPa, u2 in kPa."""
        qc = _qc([10.0], unit="MPa")
        u2 = _u2([500.0], unit="kPa")  # 0.5 MPa
        qt = compute_qt(qc, u2, a=0.7032)
        assert np.isclose(qt.values[0], 10.1484, atol=1e-4)

    def test_legacy_all_mpa(self):
        qc = _qc([10.0], unit="MPa")
        u2 = _u2([0.5], unit="MPa")  # explicit override
        qt = compute_qt(qc, u2, a=0.7032)
        assert np.isclose(qt.values[0], 10.1484, atol=1e-4)

    def test_a_071_helms(self):
        qc = _qc([20.0], unit="MPa")
        u2 = _u2([1000.0], unit="kPa")  # 1.0 MPa
        qt = compute_qt(qc, u2, a=0.71)
        # 20 + 1.0 * (1 - 0.71) = 20 + 0.29 = 20.29
        assert np.isclose(qt.values[0], 20.29, atol=1e-4)

    def test_array_input(self):
        qc = _qc([1, 2, 3, 4, 5], unit="MPa")
        u2 = _u2([100, 200, 300, 400, 500], unit="kPa")
        qt = compute_qt(qc, u2, a=0.7032)
        expected = np.array([1, 2, 3, 4, 5]) + np.array([0.1, 0.2, 0.3, 0.4, 0.5]) * 0.2968
        assert np.allclose(qt.values, expected)

    def test_a_out_of_range_low(self):
        with pytest.raises(ValueError, match="area ratio"):
            compute_qt(_qc([1.0]), _u2([1.0]), a=-0.1)

    def test_a_out_of_range_high(self):
        with pytest.raises(ValueError, match="area ratio"):
            compute_qt(_qc([1.0]), _u2([1.0]), a=1.1)

    def test_shape_mismatch(self):
        with pytest.raises(ValueError, match="shape"):
            compute_qt(_qc([1, 2, 3]), _u2([1, 2]), a=0.7)

    def test_unknown_unit_propagates(self):
        qc = CPTChannel(name="qc", unit="psi", values=[1.0])
        with pytest.raises(UnitError):
            compute_qt(qc, _u2([1.0]), a=0.7)
