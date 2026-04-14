"""Tests for geoview_cpt.correction.stress — Phase A-2 A2.5a."""
from __future__ import annotations

import numpy as np
import pytest

from geoview_cpt.correction.stress import compute_sigma_prime_v0, compute_sigma_v0
from geoview_cpt.model import CPTChannel


def _depth(values):
    return CPTChannel(name="depth", unit="m", values=values)


class TestSigmaV0Scalar:
    def test_uniform_gamma(self):
        # Uniform γ = 18 kN/m³, depth 0..5 m at 1 m steps
        # σ_v0(z) = 18 × z
        d = _depth([0.0, 1.0, 2.0, 3.0, 4.0, 5.0])
        sigma = compute_sigma_v0(d, gamma=18.0)
        assert np.allclose(sigma.values, [0.0, 18.0, 36.0, 54.0, 72.0, 90.0])
        assert sigma.unit == "kPa"
        assert sigma.name == "sigma_v0"

    def test_non_zero_first_depth(self):
        # γ = 18, first depth = 0.5 m → sigma[0] = 18 × 0.5 = 9
        d = _depth([0.5, 1.0, 1.5])
        sigma = compute_sigma_v0(d, gamma=18.0)
        assert np.isclose(sigma.values[0], 9.0)
        assert np.isclose(sigma.values[1], 9.0 + 18.0 * 0.5)

    def test_negative_gamma_rejected(self):
        with pytest.raises(ValueError):
            compute_sigma_v0(_depth([0.0]), gamma=-1.0)

    def test_empty_depth(self):
        sigma = compute_sigma_v0(_depth([]), gamma=18.0)
        assert sigma.values.size == 0
        assert sigma.unit == "kPa"


class TestSigmaV0Channel:
    def test_variable_gamma(self):
        d = _depth([0.0, 1.0, 2.0, 3.0])
        # γ varies: 16, 17, 18, 19
        gamma_ch = CPTChannel(
            name="gamma", unit="kN/m^3", values=[16.0, 17.0, 18.0, 19.0]
        )
        sigma = compute_sigma_v0(d, gamma=gamma_ch)
        # Trapezoidal between adjacent samples; first slab uses γ[0] for both ends
        # slab1 = (16+16)/2 × (1-0) = 16
        # slab2 = (16+17)/2 × 1 = 16.5  → cum 32.5 (wait, slab1 starts with prev=z[0]=0)
        # Reconstruct expected with same algorithm:
        expected = np.array([0.0, (16 + 17) / 2 * 1, (17 + 18) / 2 * 1, (18 + 19) / 2 * 1]).cumsum()
        # cumsum gives [0, 16.5, 34, 52.5]
        assert np.allclose(sigma.values, expected)

    def test_gamma_shape_mismatch(self):
        d = _depth([0.0, 1.0])
        gamma_ch = CPTChannel(name="gamma", unit="kN/m^3", values=[18.0])
        with pytest.raises(ValueError, match="gamma channel shape"):
            compute_sigma_v0(d, gamma=gamma_ch)


class TestSigmaPrimeV0:
    def test_subtraction(self):
        sv0 = CPTChannel(name="sigma_v0", unit="kPa", values=[10.0, 20.0, 30.0])
        u0 = CPTChannel(name="u0", unit="kPa", values=[2.0, 5.0, 12.0])
        spv0 = compute_sigma_prime_v0(sv0, u0)
        assert np.allclose(spv0.values, [8.0, 15.0, 18.0])
        assert spv0.name == "sigma_prime_v0"
        assert spv0.unit == "kPa"

    def test_shape_mismatch(self):
        sv0 = CPTChannel(name="sigma_v0", unit="kPa", values=[10.0, 20.0])
        u0 = CPTChannel(name="u0", unit="kPa", values=[2.0])
        with pytest.raises(ValueError, match="shape"):
            compute_sigma_prime_v0(sv0, u0)
