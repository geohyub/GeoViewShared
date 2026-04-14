"""Tests for geoview_cpt.derivation.water_content — Phase A-2 A2.5c."""
from __future__ import annotations

import numpy as np
import pytest

from geoview_cpt.derivation.water_content import compute_water_content


class TestScalar:
    def test_basic(self):
        # 110 g wet, 100 g dry → 10%
        assert compute_water_content(110.0, 100.0) == pytest.approx(10.0)

    def test_zero_water(self):
        assert compute_water_content(100.0, 100.0) == 0.0

    def test_int_inputs(self):
        assert compute_water_content(150, 100) == 50.0

    def test_returns_float_scalar(self):
        result = compute_water_content(110.0, 100.0)
        assert isinstance(result, float)


class TestArray:
    def test_shape_preserved(self):
        w = np.array([110.0, 120.0, 130.0])
        d = np.array([100.0, 100.0, 100.0])
        omega = compute_water_content(w, d)
        assert omega.shape == (3,)
        assert np.allclose(omega, [10.0, 20.0, 30.0])

    def test_2d(self):
        w = np.array([[110.0, 120.0], [130.0, 140.0]])
        d = np.array([[100.0, 100.0], [100.0, 100.0]])
        omega = compute_water_content(w, d)
        assert omega.shape == (2, 2)
        assert np.allclose(omega, [[10.0, 20.0], [30.0, 40.0]])


class TestErrors:
    def test_zero_dry_mass_rejected(self):
        with pytest.raises(ValueError, match="strictly positive"):
            compute_water_content(110.0, 0.0)

    def test_negative_dry_mass_rejected(self):
        with pytest.raises(ValueError, match="strictly positive"):
            compute_water_content(110.0, -10.0)

    def test_shape_mismatch(self):
        with pytest.raises(ValueError, match="shape"):
            compute_water_content(np.array([1.0, 2.0]), np.array([1.0]))

    def test_array_contains_zero_dry(self):
        w = np.array([110.0, 110.0])
        d = np.array([100.0, 0.0])
        with pytest.raises(ValueError):
            compute_water_content(w, d)
