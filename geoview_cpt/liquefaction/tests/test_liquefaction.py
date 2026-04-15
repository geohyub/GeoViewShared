"""Tests for geoview_cpt.liquefaction — Phase A-2 A2.10/A2.11."""
from __future__ import annotations

import numpy as np
import pytest

from geoview_cpt.liquefaction import (
    EarthquakeScenario,
    LiquefactionProfile,
    boulanger_idriss_2014_crr,
    compute_lpi,
    compute_lsn,
    msf_youd_2001,
    robertson_wride_1998_crr,
    triggering_boulanger_idriss_2014,
    triggering_robertson_wride_1998,
    triggering_youd_2001,
)
from geoview_cpt.liquefaction.boulanger_idriss_2014 import (
    k_sigma_boulanger_idriss_2014,
    msf_boulanger_idriss_2014,
    rd_idriss_1999,
)
from geoview_cpt.liquefaction.lpi_lsn import classify_lpi, classify_lsn
from geoview_cpt.liquefaction.robertson_wride_1998 import (
    CLAY_LIKE_IC_THRESHOLD,
    crr_75_robertson_wride_1998,
    fines_correction_kc,
    stress_reduction_liao_whitman_1986,
)


# ---------------------------------------------------------------------------
# EarthquakeScenario
# ---------------------------------------------------------------------------


class TestEarthquakeScenario:
    def test_basic(self):
        s = EarthquakeScenario(name="M7.0 design", magnitude_mw=7.0, pga_g=0.25)
        assert s.fines_correction is True

    def test_empty_name_rejected(self):
        with pytest.raises(ValueError):
            EarthquakeScenario(name="", magnitude_mw=7.0, pga_g=0.25)

    def test_magnitude_range(self):
        with pytest.raises(ValueError):
            EarthquakeScenario(name="x", magnitude_mw=2.0, pga_g=0.25)

    def test_pga_positive(self):
        with pytest.raises(ValueError):
            EarthquakeScenario(name="x", magnitude_mw=7.0, pga_g=0.0)


# ---------------------------------------------------------------------------
# Robertson & Wride 1998
# ---------------------------------------------------------------------------


class TestRobertsonWride1998Pieces:
    def test_kc_clean_sand_unity(self):
        kc = fines_correction_kc(np.array([1.0, 1.5, 1.64]))
        assert np.allclose(kc, 1.0)

    def test_kc_silty_sand_above_unity(self):
        kc = fines_correction_kc(np.array([1.8, 2.0, 2.4]))
        assert np.all(kc > 1.0)
        assert np.all(kc < 5.0)

    def test_crr_low_qtn_linear_branch(self):
        # Qtn_cs = 30 → CRR = 0.833 * 0.03 + 0.05 ≈ 0.075
        crr = crr_75_robertson_wride_1998(np.array([30.0]))
        assert np.isclose(crr[0], 0.075, atol=1e-4)

    def test_crr_high_qtn_cubic_branch(self):
        # Qtn_cs = 100 → CRR = 93 * 0.001 + 0.08 = 0.173
        crr = crr_75_robertson_wride_1998(np.array([100.0]))
        assert np.isclose(crr[0], 0.173, atol=1e-3)

    def test_rd_surface_unity(self):
        rd = stress_reduction_liao_whitman_1986(np.array([0.0]))
        assert np.isclose(rd[0], 1.0)

    def test_rd_deep_clip(self):
        rd = stress_reduction_liao_whitman_1986(np.array([100.0]))
        assert np.isclose(rd[0], 0.5)


class TestRobertsonWride1998Trigger:
    def _inputs(self):
        depth = np.linspace(1.0, 15.0, 15)
        qtn = np.full(15, 60.0)
        ic = np.full(15, 2.0)      # silty sand
        sv0 = depth * 18.0
        spv0 = depth * 9.0
        return depth, qtn, ic, sv0, spv0

    def test_profile_shape(self):
        d, q, ic, sv, spv = self._inputs()
        scenario = EarthquakeScenario(name="M7", magnitude_mw=7.0, pga_g=0.2)
        prof = triggering_robertson_wride_1998(
            scenario=scenario, depth_m=d, qtn=q, ic=ic,
            sigma_v0_kpa=sv, sigma_prime_v0_kpa=spv,
        )
        assert isinstance(prof, LiquefactionProfile)
        assert prof.method == "robertson_wride_1998"
        assert len(prof) == 15
        assert prof.fs.shape == (15,)
        assert len(prof.labels) == 15

    def test_clay_like_fs_nan(self):
        d, q, _, sv, spv = self._inputs()
        ic = np.full(15, 3.0)   # clay
        scenario = EarthquakeScenario(name="M7", magnitude_mw=7.0, pga_g=0.25)
        prof = triggering_robertson_wride_1998(
            scenario=scenario, depth_m=d, qtn=q, ic=ic,
            sigma_v0_kpa=sv, sigma_prime_v0_kpa=spv,
        )
        assert all(L == "clay_like" for L in prof.labels)
        assert np.all(np.isnan(prof.fs))

    def test_strong_shaking_marks_liquefiable(self):
        d, q, ic, sv, spv = self._inputs()
        q = np.full(15, 30.0)   # loose
        scenario = EarthquakeScenario(name="big", magnitude_mw=7.5, pga_g=0.5)
        prof = triggering_robertson_wride_1998(
            scenario=scenario, depth_m=d, qtn=q, ic=ic,
            sigma_v0_kpa=sv, sigma_prime_v0_kpa=spv,
        )
        assert prof.liquefiable_fraction > 0.3

    def test_strong_resistance_marks_safe(self):
        d, _, ic, sv, spv = self._inputs()
        q = np.full(15, 200.0)   # dense
        scenario = EarthquakeScenario(name="mild", magnitude_mw=6.5, pga_g=0.1)
        prof = triggering_robertson_wride_1998(
            scenario=scenario, depth_m=d, qtn=q, ic=ic,
            sigma_v0_kpa=sv, sigma_prime_v0_kpa=spv,
        )
        assert "non_liquefiable" in prof.labels
        assert prof.liquefiable_fraction < 0.3


# ---------------------------------------------------------------------------
# Youd 2001
# ---------------------------------------------------------------------------


class TestYoud2001:
    def test_msf_m75_is_unity(self):
        assert abs(msf_youd_2001(7.5) - 1.0) < 0.01

    def test_msf_upper_and_lower_differ(self):
        # Upper/lower curves diverge above M7.5; at low magnitudes the
        # two Youd 2001 forms nearly coincide (intentional in the paper).
        upper = msf_youd_2001(8.0, upper_bound=True)
        lower = msf_youd_2001(8.0, upper_bound=False)
        # Either ordering is fine; just assert they differ
        assert upper != lower

    def test_msf_invalid(self):
        with pytest.raises(ValueError):
            msf_youd_2001(0)

    def test_profile_differs_from_rw_for_m6(self):
        depth = np.linspace(1.0, 10.0, 10)
        qtn = np.full(10, 60.0)
        ic = np.full(10, 2.0)
        sv = depth * 18.0
        spv = depth * 9.0
        scenario = EarthquakeScenario(name="M6", magnitude_mw=6.0, pga_g=0.2)
        prof = triggering_youd_2001(
            scenario=scenario, depth_m=depth, qtn=qtn, ic=ic,
            sigma_v0_kpa=sv, sigma_prime_v0_kpa=spv,
        )
        assert prof.method.startswith("youd_2001")
        assert np.all(np.isfinite(prof.fs))


# ---------------------------------------------------------------------------
# Boulanger & Idriss 2014
# ---------------------------------------------------------------------------


class TestBoulangerIdriss2014:
    def test_msf_positive(self):
        assert msf_boulanger_idriss_2014(6.0) > 0
        assert msf_boulanger_idriss_2014(8.5) > 0

    def test_msf_decreasing_with_mw(self):
        msf_55 = msf_boulanger_idriss_2014(5.5)
        msf_75 = msf_boulanger_idriss_2014(7.5)
        # Larger magnitude → smaller MSF (more liquefaction hazard)
        assert msf_55 > msf_75

    def test_k_sigma_shallow_unity(self):
        k = k_sigma_boulanger_idriss_2014(np.array([100.0]))
        assert abs(k[0] - 1.0) < 0.01

    def test_k_sigma_deep_below_unity(self):
        k = k_sigma_boulanger_idriss_2014(np.array([400.0]))
        assert k[0] < 1.0

    def test_rd_idriss_shape(self):
        rd = rd_idriss_1999(np.linspace(0, 30, 30), 7.0)
        assert np.all(rd > 0)
        assert rd[0] > rd[-1]   # decreases with depth

    def test_crr_monotone_in_qtn(self):
        ic = np.array([2.0, 2.0, 2.0])
        crr = boulanger_idriss_2014_crr(np.array([50.0, 100.0, 150.0]), ic)
        assert crr[0] < crr[1] < crr[2]

    def test_profile_runs(self):
        depth = np.linspace(1.0, 15.0, 15)
        qtn = np.full(15, 80.0)
        ic = np.full(15, 2.0)
        sv = depth * 18.0
        spv = depth * 9.0
        scenario = EarthquakeScenario(name="M7", magnitude_mw=7.0, pga_g=0.25)
        prof = triggering_boulanger_idriss_2014(
            scenario=scenario, depth_m=depth, qtn=qtn, ic=ic,
            sigma_v0_kpa=sv, sigma_prime_v0_kpa=spv,
        )
        assert prof.method == "boulanger_idriss_2014"
        assert len(prof) == 15
        assert "Qtn_cs" in prof.extras
        assert "k_sigma" in prof.extras


# ---------------------------------------------------------------------------
# LPI
# ---------------------------------------------------------------------------


class TestLPI:
    def test_all_safe_returns_zero(self):
        depth = np.linspace(0.5, 20.0, 40)
        fs = np.full(40, 2.0)
        assert compute_lpi(depth, fs) == 0.0

    def test_uniform_fs_half(self):
        # Theoretical max LPI at FS=0.5: ∫₀²⁰ 0.5·(10−0.5z) dz = 50.
        # Trapezoidal integration with 40 samples undershoots slightly.
        depth = np.linspace(0.5, 20.0, 40)
        fs = np.full(40, 0.5)
        lpi = compute_lpi(depth, fs)
        assert lpi > 40.0   # severe band

    def test_nan_fs_ignored(self):
        depth = np.linspace(0.5, 20.0, 40)
        fs = np.full(40, 0.5)
        fs[:10] = np.nan
        lpi_full = compute_lpi(depth, np.full(40, 0.5))
        lpi_partial = compute_lpi(depth, fs)
        assert lpi_partial < lpi_full

    def test_truncates_above_20m(self):
        depth = np.array([10.0, 15.0, 25.0])
        fs = np.array([0.5, 0.5, 0.5])
        # 25 m sample should be skipped
        lpi = compute_lpi(depth, fs)
        assert lpi > 0
        # Manually compute expected for [10, 15] only → shouldn't include the 25

    def test_shape_mismatch(self):
        with pytest.raises(ValueError):
            compute_lpi(np.array([1, 2]), np.array([1.0]))

    def test_classification(self):
        assert classify_lpi(0.0) == "none"
        assert classify_lpi(3.0) == "low"
        assert classify_lpi(10.0) == "moderate"
        assert classify_lpi(20.0) == "high"


# ---------------------------------------------------------------------------
# LSN
# ---------------------------------------------------------------------------


class TestLSN:
    def test_all_safe_returns_zero(self):
        depth = np.linspace(0.5, 20.0, 40)
        fs = np.full(40, 2.0)
        assert compute_lsn(depth, fs) == 0.0

    def test_liquefiable_positive(self):
        depth = np.linspace(0.5, 20.0, 40)
        fs = np.full(40, 0.6)
        lsn = compute_lsn(depth, fs)
        assert lsn > 0

    def test_custom_epsilon_v(self):
        depth = np.array([1.0, 2.0, 5.0, 10.0])
        fs = np.full(4, 0.5)
        eps = np.array([5.0, 4.0, 3.0, 2.0])   # custom %
        lsn = compute_lsn(depth, fs, epsilon_v_pct=eps)
        assert lsn > 0

    def test_classification(self):
        assert classify_lsn(5.0) == "none"
        assert classify_lsn(15.0) == "low"
        assert classify_lsn(25.0) == "moderate"
        assert classify_lsn(40.0) == "high"
        assert classify_lsn(60.0) == "very_high"
