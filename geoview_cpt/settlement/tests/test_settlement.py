"""Tests for geoview_cpt.settlement — Phase A-2 A2.12."""
from __future__ import annotations

import numpy as np
import pytest

from geoview_cpt.settlement import (
    FoundationLoad,
    SettlementResult,
    mayne_1d_settlement,
    schmertmann_settlement,
)


# ---------------------------------------------------------------------------
# FoundationLoad
# ---------------------------------------------------------------------------


class TestFoundationLoad:
    def test_basic(self):
        load = FoundationLoad(net_bearing_kpa=150, width_m=2.0)
        assert load.length_m == 2.0  # square default

    def test_length_auto(self):
        load = FoundationLoad(net_bearing_kpa=150, width_m=2.0, length_m=4.0)
        assert load.length_m == 4.0

    def test_negative_bearing_rejected(self):
        with pytest.raises(ValueError):
            FoundationLoad(net_bearing_kpa=-10, width_m=2.0)

    def test_negative_width_rejected(self):
        with pytest.raises(ValueError):
            FoundationLoad(net_bearing_kpa=150, width_m=-1.0)

    def test_length_below_width_rejected(self):
        with pytest.raises(ValueError):
            FoundationLoad(net_bearing_kpa=150, width_m=3.0, length_m=2.0)

    def test_frozen(self):
        load = FoundationLoad(net_bearing_kpa=150, width_m=2.0)
        with pytest.raises(Exception):
            load.net_bearing_kpa = 200  # type: ignore


# ---------------------------------------------------------------------------
# Mayne 1D
# ---------------------------------------------------------------------------


class TestMayne1D:
    def _profile(self, n: int = 20, e_kpa: float = 20_000):
        depth = np.linspace(0.5, 20.0, n)
        e = np.full(n, e_kpa)
        return depth, e

    def test_returns_result(self):
        load = FoundationLoad(net_bearing_kpa=150, width_m=2.0)
        depth, e = self._profile()
        result = mayne_1d_settlement(load, depth, e)
        assert isinstance(result, SettlementResult)
        assert result.method == "mayne_1d"
        assert result.total_mm > 0

    def test_stiffer_soil_less_settlement(self):
        load = FoundationLoad(net_bearing_kpa=150, width_m=2.0)
        depth, _ = self._profile()
        soft = mayne_1d_settlement(load, depth, np.full(20, 10_000.0))
        stiff = mayne_1d_settlement(load, depth, np.full(20, 50_000.0))
        assert soft.total_mm > stiff.total_mm

    def test_larger_load_more_settlement(self):
        depth, e = self._profile()
        s1 = mayne_1d_settlement(
            FoundationLoad(net_bearing_kpa=100, width_m=2.0), depth, e
        )
        s2 = mayne_1d_settlement(
            FoundationLoad(net_bearing_kpa=300, width_m=2.0), depth, e
        )
        assert s2.total_mm > s1.total_mm

    def test_per_layer_sum_matches_total(self):
        load = FoundationLoad(net_bearing_kpa=150, width_m=2.0)
        depth, e = self._profile()
        result = mayne_1d_settlement(load, depth, e)
        assert np.isclose(result.total_mm, np.sum(result.per_layer_mm))

    def test_shape_mismatch(self):
        load = FoundationLoad(net_bearing_kpa=150, width_m=2.0)
        with pytest.raises(ValueError):
            mayne_1d_settlement(load, np.array([1, 2]), np.array([10.0]))

    def test_extras_present(self):
        load = FoundationLoad(net_bearing_kpa=150, width_m=2.0)
        depth, e = self._profile()
        r = mayne_1d_settlement(load, depth, e)
        assert "influence_factor" in r.extras
        assert "delta_sigma_kpa" in r.extras


# ---------------------------------------------------------------------------
# Schmertmann
# ---------------------------------------------------------------------------


class TestSchmertmann:
    def _profile(self, n: int = 20, e_kpa: float = 20_000):
        depth = np.linspace(0.5, 20.0, n)
        e = np.full(n, e_kpa)
        return depth, e

    def test_returns_result(self):
        load = FoundationLoad(net_bearing_kpa=150, width_m=2.0)
        depth, e = self._profile()
        r = schmertmann_settlement(load, depth, e)
        assert r.method == "schmertmann"
        assert r.total_mm > 0

    def test_c1_embedment(self):
        load = FoundationLoad(net_bearing_kpa=200, width_m=2.0)
        depth, e = self._profile()
        r0 = schmertmann_settlement(load, depth, e, sigma_prime_v0_at_foundation_kpa=0)
        r1 = schmertmann_settlement(load, depth, e, sigma_prime_v0_at_foundation_kpa=100)
        # Embedment reduces settlement (C1 < 1)
        assert r1.total_mm < r0.total_mm

    def test_c2_creep(self):
        load = FoundationLoad(net_bearing_kpa=150, width_m=2.0)
        depth, e = self._profile()
        r_immediate = schmertmann_settlement(load, depth, e, time_years=0.1)
        r_long = schmertmann_settlement(load, depth, e, time_years=10.0)
        # Creep factor increases with time
        assert r_long.total_mm > r_immediate.total_mm

    def test_strip_vs_square(self):
        load = FoundationLoad(net_bearing_kpa=150, width_m=2.0)
        depth, e = self._profile()
        square = schmertmann_settlement(load, depth, e, strip=False)
        strip = schmertmann_settlement(load, depth, e, strip=True)
        # Strip footing has deeper influence → different settlement
        assert square.total_mm != strip.total_mm

    def test_Iz_in_extras(self):
        load = FoundationLoad(net_bearing_kpa=150, width_m=2.0)
        depth, e = self._profile()
        r = schmertmann_settlement(load, depth, e)
        assert "Iz" in r.extras
        assert "C1" in r.extras
        assert "C2" in r.extras

    def test_shape_mismatch(self):
        load = FoundationLoad(net_bearing_kpa=150, width_m=2.0)
        with pytest.raises(ValueError):
            schmertmann_settlement(load, np.array([1, 2]), np.array([10.0]))
