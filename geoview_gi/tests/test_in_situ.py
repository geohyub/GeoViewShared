"""Tests for geoview_gi.in_situ LLT formulas — Phase A-2 A2.16."""
from __future__ import annotations

from datetime import date

import numpy as np
import pytest

from geoview_gi.in_situ import (
    DEFAULT_POISSON,
    LLTTest,
    compute_em,
    compute_km,
    compute_pe,
    compute_pl,
    compute_py,
    compute_rm,
)


class TestFormulas:
    def test_pe_addition(self):
        assert compute_pe(100, 20, 5) == 115

    def test_pe_numpy_array(self):
        pe = compute_pe(np.array([100, 200]), np.array([20, 30]), np.array([5, 10]))
        assert np.array_equal(pe, np.array([115, 220]))

    def test_py_and_pl_subtract_po(self):
        assert compute_py(500, 50) == 450
        assert compute_pl(800, 50) == 750

    def test_km_division(self):
        # Py' = 500, Po = 50 → numerator 450
        # r_y = 0.035, r_o = 0.033 → denom 0.002 → Km = 225000 kPa/m
        km = compute_km(py_raw=500, p_o=50, r_y=0.035, r_o=0.033)
        assert np.isclose(km, 225000.0)

    def test_km_zero_denominator(self):
        with pytest.raises(ValueError):
            compute_km(py_raw=500, p_o=50, r_y=0.033, r_o=0.033)

    def test_rm_average(self):
        assert compute_rm(0.033, 0.035) == 0.034

    def test_em_formula(self):
        # Em = (1 + 0.45) × 0.034 × 225000
        #    = 1.45 × 0.034 × 225000 = 11092.5 kPa
        em = compute_em(
            py_raw=500, p_o=50, r_o=0.033, r_y=0.035, nu=0.45
        )
        assert np.isclose(em, 11092.5)


class TestDefaults:
    def test_poisson_default(self):
        assert DEFAULT_POISSON == 0.45


# ---------------------------------------------------------------------------
# LLTTest dataclass + Wave 0 golden sample
# ---------------------------------------------------------------------------


class TestLLTTest:
    def test_construction(self):
        t = LLTTest(
            borehole_id="YW-1",
            depth_m=3.0,
            test_date=date(2025, 4, 1),
            py_raw_kpa=1500.0,
            pl_raw_kpa=2500.0,
            p_o_kpa=50.0,
            r_o_mm=33.0,
            r_y_mm=35.0,
        )
        assert t.py_kpa == 1450.0
        assert t.pl_kpa == 2450.0
        assert np.isclose(t.rm_m, 0.034)

    def test_em_units_mpa(self):
        t = LLTTest(
            borehole_id="YW-1",
            depth_m=3.0,
            py_raw_kpa=1500.0,
            pl_raw_kpa=2500.0,
            p_o_kpa=50.0,
            r_o_mm=33.0,
            r_y_mm=35.0,
            nu=0.45,
        )
        # Km = (1500 - 50) / (0.035 - 0.033) = 725000 kPa/m
        # Rm = 0.034 m
        # Em = 1.45 × 0.034 × 725000 = 35742.5 kPa = 35.74 MPa
        assert np.isclose(t.em_mpa, 35.7425, atol=1e-3)

    def test_wave0_golden_em_1p34_mpa(self):
        """
        Reproduce the Wave 0 3rd-round golden sample: YW-1 / 3.0 m /
        Em = 1.34 MPa. The report listed Em = 1.34 MPa; we pick a
        parameter set that reaches the same value and pin it as a
        regression guard.
        """
        # Em(kPa) = 1.45 × Rm × Km = 1340 → Rm × Km = 924.14 kPa
        # Take Rm = 0.034 m (33/35 mm probe) → Km = 27181 kPa/m
        # Km = (Py' - Po) / dr → (Py' - Po) = Km × dr = 27181 × 0.002 = 54.36
        # Choose Py' = 104.36, Po = 50
        t = LLTTest(
            borehole_id="YW-1",
            depth_m=3.0,
            py_raw_kpa=104.36,
            pl_raw_kpa=200.0,
            p_o_kpa=50.0,
            r_o_mm=33.0,
            r_y_mm=35.0,
            nu=0.45,
        )
        assert np.isclose(t.em_mpa, 1.34, atol=0.01)
