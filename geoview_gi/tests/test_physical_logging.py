"""Tests for geoview_gi.physical_logging — Phase A-2 A2.15."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from geoview_gi.physical_logging import (
    DensityLog,
    DensityStratum,
    PhysicalLoggingParseError,
    PSWaveLog,
    dynamic_poisson_ratio,
    dynamic_shear_modulus,
    dynamic_young_modulus,
    parse_density_datasheet_xlsx,
    parse_ps_wave_datasheet_xlsx,
)


# ---------------------------------------------------------------------------
# Formulas — pure, no fixture needed
# ---------------------------------------------------------------------------


class TestDynamicModuli:
    def test_shear_modulus_simple(self):
        # γ = 18 kN/m³ → ρ = 18000 / 9.81 = 1834.86 kg/m³
        # Vs = 0.2 km/s = 200 m/s → Vs² = 40000
        # G = 1834.86 × 40000 = 7.34e7 Pa = 73.4 MPa
        g = dynamic_shear_modulus(
            np.array([1.5]),
            np.array([0.2]),
            np.array([18.0]),
        )
        assert g.shape == (1,)
        assert np.isclose(g[0], 73.4, atol=0.2)

    def test_poisson_ratio_sanity(self):
        # Real rock: Vp 2.0, Vs 1.0 → ν ≈ 0.333
        nu = dynamic_poisson_ratio(np.array([2.0]), np.array([1.0]))
        assert 0.25 < nu[0] < 0.40

    def test_poisson_ratio_denominator_guard(self):
        nu = dynamic_poisson_ratio(np.array([1.0]), np.array([1.0]))
        assert np.isfinite(nu[0])

    def test_young_modulus_relation(self):
        # E = 2G(1 + ν) — check consistency
        vp = np.array([1.6])
        vs = np.array([0.3])
        g = np.array([18.0])
        e_calc = dynamic_young_modulus(vp, vs, g)
        g_calc = dynamic_shear_modulus(vp, vs, g)
        nu_calc = dynamic_poisson_ratio(vp, vs)
        assert np.isclose(e_calc[0], 2 * g_calc[0] * (1 + nu_calc[0]), rtol=1e-6)


# ---------------------------------------------------------------------------
# DensityLog / PSWaveLog dataclasses
# ---------------------------------------------------------------------------


class TestDataclassConstruction:
    def test_density_log_mean(self):
        log = DensityLog(
            borehole_id="YW-1",
            sheet_name="raw",
            depth_m=np.array([0.0, 1.0, 2.0]),
            lsd_cps=np.array([1000.0, 1010.0, 1020.0]),
            density_g_cm3=np.array([1.7, 1.75, 1.8]),
        )
        assert len(log) == 3
        assert np.isclose(log.mean_density_g_cm3, 1.75)

    def test_density_stratum(self):
        s = DensityStratum(top_m=0.0, base_m=5.0, stratum_label="sand", mean_density_g_cm3=1.7)
        assert s.stratum_label == "sand"

    def test_ps_wave_log_cross_check(self):
        log = PSWaveLog(
            borehole_id="YW-1",
            sheet_name="raw",
            depth_el_m=np.array([-10.0]),
            depth_gl_m=np.array([5.0]),
            rock_type=["rock"],
            vp_km_s=np.array([1.6]),
            vs_km_s=np.array([0.3]),
            gamma_kn_m3=np.array([18.0]),
            gd_vendor_mpa=np.array([165.0]),
            ed_vendor_mpa=np.array([490.0]),
            kd_vendor_mpa=np.array([4400.0]),
            poisson_vendor=np.array([0.48]),
        )
        # Cross-check G should be roughly vendor G
        g_calc = log.shear_modulus_cross_check_mpa
        assert abs(g_calc[0] - 165.0) / 165.0 < 0.03    # within 3 %


# ---------------------------------------------------------------------------
# Real GeoPlus xlsx files (optional)
# ---------------------------------------------------------------------------


_REAL_DENSITY = Path(
    r"H:/야월해상풍력단지 지반조사 용역 결과보고서_rev7/CPT 데이터 분석/야월해상풍력 타사_물리검층보고서_지오플러스이엔지/(지오플러스이엔지)야월 해상풍력 프로젝트 지반조사 밀도검층DATASHEET(2025.05.07).xlsx"
)
_REAL_PSWAVE = Path(
    r"H:/야월해상풍력단지 지반조사 용역 결과보고서_rev7/CPT 데이터 분석/야월해상풍력 타사_물리검층보고서_지오플러스이엔지/(지오플러스이엔지)야월 해상풍력 프로젝트 지반조사 음파검층DATASHEET(2025.05.07).xlsx"
)

density_required = pytest.mark.skipif(
    not _REAL_DENSITY.exists(),
    reason="GeoPlus density DATASHEET not mounted",
)
pswave_required = pytest.mark.skipif(
    not _REAL_PSWAVE.exists(),
    reason="GeoPlus PS-wave DATASHEET not mounted",
)


@pytest.fixture(scope="session")
def real_density_logs():
    if not _REAL_DENSITY.exists():
        pytest.skip("density datasheet not mounted")
    return parse_density_datasheet_xlsx(_REAL_DENSITY)


@pytest.fixture(scope="session")
def real_pswave_logs():
    if not _REAL_PSWAVE.exists():
        pytest.skip("ps-wave datasheet not mounted")
    return parse_ps_wave_datasheet_xlsx(_REAL_PSWAVE)


@density_required
class TestRealDensity:
    def test_three_boreholes(self, real_density_logs):
        assert len(real_density_logs) == 3

    def test_borehole_ids(self, real_density_logs):
        ids = [log.borehole_id for log in real_density_logs]
        assert any("YW-1" in i for i in ids)
        assert any("YW-4" in i for i in ids)
        assert any("YW-12" in i for i in ids)

    def test_density_range(self, real_density_logs):
        for log in real_density_logs:
            assert log.depth_m.size > 1000
            finite = log.density_g_cm3[np.isfinite(log.density_g_cm3)]
            assert finite.size > 0
            assert 1.3 < finite.mean() < 2.6

    def test_strata_side_table(self, real_density_logs):
        # Every borehole should have at least one stratum from the side table
        for log in real_density_logs:
            assert len(log.strata) >= 1
            for s in log.strata:
                assert s.base_m > s.top_m


@pswave_required
class TestRealPsWave:
    def test_three_boreholes(self, real_pswave_logs):
        assert len(real_pswave_logs) == 3

    def test_vp_vs_ranges(self, real_pswave_logs):
        for log in real_pswave_logs:
            assert log.vp_km_s.size >= 20
            vp = log.vp_km_s[np.isfinite(log.vp_km_s)]
            vs = log.vs_km_s[np.isfinite(log.vs_km_s)]
            assert 1.2 < vp.mean() < 3.5
            assert 0.1 < vs.mean() < 1.5

    def test_cross_check_poisson_matches_vendor(self, real_pswave_logs):
        log = real_pswave_logs[0]
        calc = log.poisson_cross_check
        vendor = log.poisson_vendor
        mask = np.isfinite(calc) & np.isfinite(vendor)
        diff = np.abs(calc[mask] - vendor[mask])
        assert diff.mean() < 0.02

    def test_cross_check_gd_matches_vendor(self, real_pswave_logs):
        log = real_pswave_logs[0]
        calc = log.shear_modulus_cross_check_mpa
        vendor = log.gd_vendor_mpa
        mask = np.isfinite(calc) & np.isfinite(vendor) & (vendor > 0)
        rel = np.abs(calc[mask] - vendor[mask]) / vendor[mask]
        assert rel.mean() < 0.03


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class TestErrors:
    def test_density_missing_file(self, tmp_path):
        with pytest.raises(PhysicalLoggingParseError):
            parse_density_datasheet_xlsx(tmp_path / "nope.xlsx")

    def test_pswave_missing_file(self, tmp_path):
        with pytest.raises(PhysicalLoggingParseError):
            parse_ps_wave_datasheet_xlsx(tmp_path / "nope.xlsx")
