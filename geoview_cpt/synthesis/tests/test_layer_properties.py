"""Tests for geoview_cpt.synthesis.layer_properties — Phase A-2 A2.9."""
from __future__ import annotations

import numpy as np
import pytest

from geoview_cpt.model import CPTChannel, CPTSounding
from geoview_cpt.synthesis.layer_properties import (
    SYNTHESIZED_PROPERTIES,
    LayerSynthesizer,
    SynthesizedValue,
)
from geoview_gi.in_situ import LLTTest
from geoview_gi.minimal_model import LabSample, SPTTest, StratumLayer
from geoview_gi.physical_logging import DensityLog, PSWaveLog


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _sounding_with_derived() -> CPTSounding:
    """Synthetic sounding with a fully-populated derivation chain."""
    depth = np.linspace(0.0, 10.0, 200)
    s = CPTSounding(handle=1, element_tag="1", name="CPT-SYNTH")
    s.channels = {"depth": CPTChannel(name="depth", unit="m", values=depth)}
    s.derived = {
        "qt":       CPTChannel(name="qt", unit="MPa", values=np.linspace(0.5, 5.0, 200)),
        "sigma_v0": CPTChannel(name="sigma_v0", unit="kPa", values=depth * 18.0),
        "Ic":       CPTChannel(name="Ic", unit="-",
                                values=np.where(depth < 5.0, 1.8, 3.2)),
        "gamma":    CPTChannel(name="gamma", unit="kN/m^3", values=np.full(200, 18.5)),
        "Dr":       CPTChannel(name="Dr", unit="-",
                                values=np.where(depth < 5.0, 0.6, 0.0)),
    }
    return s


def _layer_top(top_m: float = 0.0, base_m: float = 5.0) -> StratumLayer:
    return StratumLayer(
        top_m=top_m, base_m=base_m, description="sand", legend_code="SP"
    )


def _layer_bottom(top_m: float = 5.0, base_m: float = 10.0) -> StratumLayer:
    return StratumLayer(
        top_m=top_m, base_m=base_m, description="clay", legend_code="CL"
    )


# ---------------------------------------------------------------------------
# SynthesizedValue
# ---------------------------------------------------------------------------


class TestSynthesizedValue:
    def test_defaults_missing(self):
        sv = SynthesizedValue()
        assert sv.value is None
        assert sv.source == "missing"
        assert sv.confidence == "unknown"
        assert sv.is_missing is True

    def test_populated(self):
        sv = SynthesizedValue(
            value=42.0,
            source="lab_direct",
            confidence="high",
            trace={"n": 3},
        )
        assert sv.value == 42.0
        assert sv.is_missing is False

    def test_frozen(self):
        sv = SynthesizedValue(value=1.0, source="lab_direct")
        with pytest.raises(Exception):
            sv.value = 2.0  # type: ignore[misc]


# ---------------------------------------------------------------------------
# LayerSynthesizer
# ---------------------------------------------------------------------------


class TestLayerSynthesizerShape:
    def test_all_nine_properties_populated(self):
        syn = LayerSynthesizer(
            sounding=_sounding_with_derived(),
            strata=[_layer_top(), _layer_bottom()],
        )
        enriched = syn.synthesize()
        assert len(enriched) == 2
        for layer in enriched:
            assert set(layer.synthesized_properties.keys()) == set(SYNTHESIZED_PROPERTIES)

    def test_contract_nine_properties(self):
        assert len(SYNTHESIZED_PROPERTIES) == 9

    def test_missing_everything_yields_missing_source(self):
        bare = CPTSounding(handle=1, element_tag="1", name="bare")
        bare.channels = {
            "depth": CPTChannel(name="depth", unit="m", values=np.array([0, 1, 2]))
        }
        syn = LayerSynthesizer(
            sounding=bare,
            strata=[StratumLayer(top_m=0.0, base_m=2.0)],
        )
        enriched = syn.synthesize()
        props = enriched[0].synthesized_properties
        # gamma, Su, etc. all fall through to missing
        for key in ("gamma", "Su", "Dr", "phi_prime", "Vp", "Vs", "N", "Em"):
            assert props[key].is_missing


class TestUSCSPriority:
    def test_lab_wins(self):
        lab = LabSample(
            loca_id="BH", sample_id="U1", sample_type="U",
            sample_ref="CL", top_m=2.0,
        )
        syn = LayerSynthesizer(
            sounding=_sounding_with_derived(),
            strata=[_layer_top()],
            lab_samples=[lab],
        )
        enriched = syn.synthesize()
        uscs = enriched[0].synthesized_properties["USCS"]
        assert uscs.source == "lab_direct"
        assert uscs.value == "CL"
        assert uscs.confidence == "high"

    def test_cpt_fallback(self):
        syn = LayerSynthesizer(
            sounding=_sounding_with_derived(),
            strata=[_layer_top()],
        )
        enriched = syn.synthesize()
        uscs = enriched[0].synthesized_properties["USCS"]
        assert uscs.source == "cpt_derived"
        # Ic ≈ 1.8 → Robertson zone 6 → "SP"
        assert uscs.value == "SP"

    def test_narrative_fallback_when_no_cpt_ic(self):
        bare = CPTSounding(handle=1, element_tag="1", name="bare")
        bare.channels = {
            "depth": CPTChannel(name="depth", unit="m", values=np.linspace(0, 5, 50))
        }
        syn = LayerSynthesizer(
            sounding=bare,
            strata=[StratumLayer(top_m=0, base_m=5, legend_code="CH")],
        )
        enriched = syn.synthesize()
        uscs = enriched[0].synthesized_properties["USCS"]
        assert uscs.source == "narrative_manual"
        assert uscs.value == "CH"


class TestGammaPriority:
    def test_density_log_wins(self):
        density = DensityLog(
            borehole_id="YW",
            sheet_name="YW",
            depth_m=np.linspace(0, 5, 50),
            lsd_cps=np.full(50, 1000.0),
            density_g_cm3=np.full(50, 1.9),   # → γ = 18.63 kN/m³
        )
        syn = LayerSynthesizer(
            sounding=_sounding_with_derived(),
            strata=[_layer_top()],
            density_log=density,
        )
        enriched = syn.synthesize()
        gamma = enriched[0].synthesized_properties["gamma"]
        assert gamma.source == "density_direct"
        assert abs(gamma.value - 1.9 * 9.81) < 1e-6

    def test_lab_bulk_wins_over_cpt(self):
        lab = LabSample(
            loca_id="BH", sample_id="U1",
            top_m=2.0, bulk_density_t_m3=1.85,
        )
        syn = LayerSynthesizer(
            sounding=_sounding_with_derived(),
            strata=[_layer_top()],
            lab_samples=[lab],
        )
        gamma = syn.synthesize()[0].synthesized_properties["gamma"]
        assert gamma.source == "lab_direct"
        assert abs(gamma.value - 1.85 * 9.81) < 1e-6

    def test_cpt_fallback(self):
        syn = LayerSynthesizer(
            sounding=_sounding_with_derived(),
            strata=[_layer_top()],
        )
        gamma = syn.synthesize()[0].synthesized_properties["gamma"]
        assert gamma.source == "cpt_derived"
        assert abs(gamma.value - 18.5) < 1e-6


class TestSuPriority:
    def test_lab_wins(self):
        lab = LabSample(
            loca_id="BH", sample_id="U1",
            top_m=3.0,
            undrained_shear_strength_kpa=45.0,
        )
        syn = LayerSynthesizer(
            sounding=_sounding_with_derived(),
            strata=[_layer_top()],
            lab_samples=[lab],
        )
        su = syn.synthesize()[0].synthesized_properties["Su"]
        assert su.source == "lab_direct"
        assert su.value == 45.0

    def test_cpt_fallback_gives_both_nkt_bounds(self):
        syn = LayerSynthesizer(
            sounding=_sounding_with_derived(),
            strata=[_layer_top()],
        )
        su = syn.synthesize()[0].synthesized_properties["Su"]
        assert su.source == "cpt_derived"
        assert "Su_Nkt15_kpa" in su.trace
        assert "Su_Nkt30_kpa" in su.trace
        # Value is the Nkt=15 bound
        assert su.value == pytest.approx(su.trace["Su_Nkt15_kpa"])


class TestPhiPrime:
    def test_lab_direct(self):
        lab = LabSample(
            loca_id="BH", sample_id="U1",
            top_m=2.0, effective_friction_angle_deg=32.0,
        )
        syn = LayerSynthesizer(
            sounding=_sounding_with_derived(),
            strata=[_layer_top()],
            lab_samples=[lab],
        )
        phi = syn.synthesize()[0].synthesized_properties["phi_prime"]
        assert phi.source == "lab_direct"
        assert phi.value == 32.0

    def test_missing_when_no_lab(self):
        syn = LayerSynthesizer(
            sounding=_sounding_with_derived(),
            strata=[_layer_top()],
        )
        phi = syn.synthesize()[0].synthesized_properties["phi_prime"]
        assert phi.is_missing


class TestPSWavePriority:
    def _pswave(self) -> PSWaveLog:
        return PSWaveLog(
            borehole_id="YW",
            sheet_name="YW",
            depth_el_m=np.linspace(-10, -5, 6),
            depth_gl_m=np.linspace(0.0, 5.0, 6),
            rock_type=["rock"] * 6,
            vp_km_s=np.full(6, 1.6),
            vs_km_s=np.full(6, 0.3),
            gamma_kn_m3=np.full(6, 18.0),
            gd_vendor_mpa=np.full(6, 165.0),
            ed_vendor_mpa=np.full(6, 490.0),
            kd_vendor_mpa=np.full(6, 4400.0),
            poisson_vendor=np.full(6, 0.48),
        )

    def test_vp_direct(self):
        syn = LayerSynthesizer(
            sounding=_sounding_with_derived(),
            strata=[_layer_top()],
            pswave_log=self._pswave(),
        )
        props = syn.synthesize()[0].synthesized_properties
        assert props["Vp"].source == "pswave_direct"
        assert abs(props["Vp"].value - 1.6) < 1e-6
        assert props["Vs"].source == "pswave_direct"
        assert abs(props["Vs"].value - 0.3) < 1e-6

    def test_missing_without_log(self):
        syn = LayerSynthesizer(
            sounding=_sounding_with_derived(),
            strata=[_layer_top()],
        )
        props = syn.synthesize()[0].synthesized_properties
        assert props["Vp"].is_missing
        assert props["Vs"].is_missing


class TestSPT:
    def test_neighbor_spt_mean(self):
        spts = [
            SPTTest(top_m=1.0, main_blows=10),
            SPTTest(top_m=2.5, main_blows=20),
            SPTTest(top_m=6.0, main_blows=35),   # outside top layer
        ]
        syn = LayerSynthesizer(
            sounding=_sounding_with_derived(),
            strata=[_layer_top()],
            neighbor_spt=spts,
        )
        n = syn.synthesize()[0].synthesized_properties["N"]
        assert n.source == "spt_neighbor"
        assert n.value == 15.0
        assert n.trace["pair_count"] == 2


class TestEmPriority:
    def test_llt_direct(self):
        llt = LLTTest(
            borehole_id="YW", depth_m=2.0,
            py_raw_kpa=104.36, pl_raw_kpa=200.0, p_o_kpa=50.0,
            r_o_mm=33.0, r_y_mm=35.0,
        )
        syn = LayerSynthesizer(
            sounding=_sounding_with_derived(),
            strata=[_layer_top()],
            llt_tests=[llt],
        )
        em = syn.synthesize()[0].synthesized_properties["Em"]
        assert em.source == "llt_direct"
        assert em.value == pytest.approx(1.34, abs=0.01)

    def test_pswave_ed_fallback(self):
        pswave = PSWaveLog(
            borehole_id="YW",
            sheet_name="YW",
            depth_el_m=np.linspace(-10, -5, 6),
            depth_gl_m=np.linspace(0, 5, 6),
            rock_type=["rock"] * 6,
            vp_km_s=np.full(6, 1.6),
            vs_km_s=np.full(6, 0.3),
            gamma_kn_m3=np.full(6, 18.0),
            gd_vendor_mpa=np.full(6, 165.0),
            ed_vendor_mpa=np.full(6, 490.0),
            kd_vendor_mpa=np.full(6, 4400.0),
            poisson_vendor=np.full(6, 0.48),
        )
        syn = LayerSynthesizer(
            sounding=_sounding_with_derived(),
            strata=[_layer_top()],
            pswave_log=pswave,
        )
        em = syn.synthesize()[0].synthesized_properties["Em"]
        assert em.source == "pswave_direct"
        assert em.value == pytest.approx(490.0)

    def test_missing_when_no_source(self):
        syn = LayerSynthesizer(
            sounding=_sounding_with_derived(),
            strata=[_layer_top()],
        )
        em = syn.synthesize()[0].synthesized_properties["Em"]
        assert em.is_missing


# ---------------------------------------------------------------------------
# StratumLayer extension smoke
# ---------------------------------------------------------------------------


class TestStratumLayerField:
    def test_default_empty_dict(self):
        layer = StratumLayer(top_m=0, base_m=1)
        assert layer.synthesized_properties == {}

    def test_accepts_synthesized_values(self):
        layer = StratumLayer(
            top_m=0, base_m=1,
            synthesized_properties={
                "USCS": SynthesizedValue(value="SP", source="lab_direct"),
            },
        )
        assert "USCS" in layer.synthesized_properties
