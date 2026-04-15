"""
geoview_cpt.synthesis.layer_properties
==========================================
Priority-driven synthesis of per-layer properties from every data
source a CPT+Lab project can carry.

Scope (Wave 0 3rd-round redefinition):

    "A2.9 is not a single formula — it is multi-source aggregation and
    reconciliation. Each layer gets one SynthesizedValue per property;
    each SynthesizedValue carries the value, the source, a confidence
    tier, and a trace dict with the rejected alternatives."

Priority ladders (high → low, master plan §12):

    USCS        Lab USCS > CPT Ic classifier > narrative manual
    gamma       DensityLog > Lab bulk density > CPT R&C 2010
    Su          Lab UU/CIU/CID/CAU > CPT (qt-σv0)/Nkt (15, 30)
    Dr          Lab Id (if any) > CPT Jamiolkowski
    phi_prime   Lab direct shear / drained triaxial > CPT derived
    Vp, Vs      PSWaveLog direct > CPT Mayne/Andrus estimates
    N           neighbor SPT (< 50 m pairing) > null
    Em          LLTTest direct > PSWave Ed-derived > CPT derived

Missing-data handling: every synthesizer tries its ladder top-down;
the first available source wins, with the others recorded in the
``trace`` dict under keys matching the source tier. When *every* tier
is empty, :class:`SynthesizedValue` is emitted with
``value=None`` / ``source="missing"`` / ``confidence="unknown"`` so
downstream analysis modules can skip without branching.

The synthesizer is **pure / deterministic** — no randomness, no IO,
no LLM. Parameter-free invocations produce the same output for the
same inputs, which keeps the R2 harness + Phase A-4 AGS4 export
reproducible on the same fixtures.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Iterable, Literal

import numpy as np

from geoview_cpt.correction.units import to_kpa
from geoview_cpt.derivation.sbt import classify_ic_to_robertson_1990_zone
from geoview_cpt.model import CPTSounding

if TYPE_CHECKING:
    from geoview_gi.in_situ import LLTTest
    from geoview_gi.minimal_model import LabSample, SPTTest, StratumLayer
    from geoview_gi.physical_logging import DensityLog, PSWaveLog

__all__ = [
    "SynthesizedValue",
    "PropertySource",
    "PropertyConfidence",
    "LayerSynthesizer",
    "SYNTHESIZED_PROPERTIES",
]


PropertySource = Literal[
    "lab_direct",
    "cpt_derived",
    "pswave_direct",
    "density_direct",
    "llt_direct",
    "spt_neighbor",
    "narrative_manual",
    "missing",
]
PropertyConfidence = Literal["high", "medium", "low", "unknown"]


SYNTHESIZED_PROPERTIES: tuple[str, ...] = (
    "USCS",
    "gamma",
    "Su",
    "Dr",
    "phi_prime",
    "Vp",
    "Vs",
    "N",
    "Em",
)


@dataclass(frozen=True)
class SynthesizedValue:
    """
    One property's synthesis outcome for a single stratum.

    Attributes:
        value:      Scalar (float) or label (str) or ``None`` for missing.
        source:     Which ladder tier supplied the value.
        confidence: Qualitative tier — see :data:`PropertyConfidence`.
        trace:      Open dict keyed by tier label — stores rejected
                    alternatives, intermediate computations, and any
                    parameter hints the UI may want to surface.
    """

    value: Any = None
    source: PropertySource = "missing"
    confidence: PropertyConfidence = "unknown"
    trace: dict[str, Any] = field(default_factory=dict)

    @property
    def is_missing(self) -> bool:
        return self.source == "missing" or self.value is None


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


@dataclass
class LayerSynthesizer:
    """
    Pure function object that fills
    ``StratumLayer.synthesized_properties`` for every layer in
    :attr:`strata`.

    Call pattern::

        syn = LayerSynthesizer(
            sounding=sounding,
            strata=strata,
            lab_samples=lab,
            density_log=density,
            pswave_log=pswave,
            llt_tests=llt,
            neighbor_spt=spt,
        )
        enriched = syn.synthesize()

    The input :attr:`strata` list is mutated in-place (each layer's
    ``synthesized_properties`` dict is filled) and also returned for
    chaining convenience.
    """

    sounding: CPTSounding
    strata: "list[StratumLayer]" = field(default_factory=list)
    lab_samples: "list[LabSample]" = field(default_factory=list)
    density_log: "DensityLog | None" = None
    pswave_log: "PSWaveLog | None" = None
    llt_tests: "list[LLTTest]" = field(default_factory=list)
    neighbor_spt: "list[SPTTest]" = field(default_factory=list)

    # ------------------------------------------------------------------

    def synthesize(self) -> "list[StratumLayer]":
        for layer in self.strata:
            layer.synthesized_properties = self._synthesize_one(layer)
        return self.strata

    # ------------------------------------------------------------------
    # per-layer
    # ------------------------------------------------------------------

    def _synthesize_one(self, layer: "StratumLayer") -> dict[str, SynthesizedValue]:
        lab_hits = [
            s for s in self.lab_samples
            if layer.top_m <= s.top_m < layer.base_m
        ]
        return {
            "USCS":      self._synth_uscs(layer, lab_hits),
            "gamma":     self._synth_gamma(layer, lab_hits),
            "Su":        self._synth_su(layer, lab_hits),
            "Dr":        self._synth_dr(layer, lab_hits),
            "phi_prime": self._synth_phi_prime(layer, lab_hits),
            "Vp":        self._synth_pswave(layer, "Vp"),
            "Vs":        self._synth_pswave(layer, "Vs"),
            "N":         self._synth_spt(layer),
            "Em":        self._synth_em(layer),
        }

    # ------------------------------------------------------------------
    # USCS
    # ------------------------------------------------------------------

    def _synth_uscs(self, layer, lab_hits) -> SynthesizedValue:
        lab_codes = [s.sample_ref for s in lab_hits if s.sample_ref]
        if lab_codes:
            return SynthesizedValue(
                value=lab_codes[0],
                source="lab_direct",
                confidence="high",
                trace={"lab_codes": lab_codes},
            )

        ic_mean = self._mean_channel_in_layer(layer, "Ic")
        if ic_mean is not None:
            zone = classify_ic_to_robertson_1990_zone(ic_mean)
            label = _zone_to_uscs(zone)
            return SynthesizedValue(
                value=label,
                source="cpt_derived",
                confidence="medium",
                trace={"Ic_mean": ic_mean, "robertson_zone": zone},
            )

        if layer.legend_code:
            return SynthesizedValue(
                value=layer.legend_code,
                source="narrative_manual",
                confidence="low",
                trace={"from_field": "StratumLayer.legend_code"},
            )
        return SynthesizedValue(trace={"checked": ["lab", "cpt_ic", "narrative"]})

    # ------------------------------------------------------------------
    # γ (kN/m³)
    # ------------------------------------------------------------------

    def _synth_gamma(self, layer, lab_hits) -> SynthesizedValue:
        if self.density_log is not None:
            mean_rho = self._mean_density_in_layer(layer)
            if mean_rho is not None:
                gamma = mean_rho * 9.81  # g/cm³ → kN/m³
                return SynthesizedValue(
                    value=gamma,
                    source="density_direct",
                    confidence="high",
                    trace={"mean_rho_g_cm3": mean_rho},
                )

        lab_bulk = [
            s.bulk_density_t_m3 for s in lab_hits
            if s.bulk_density_t_m3 is not None
        ]
        if lab_bulk:
            bulk_mean = float(np.mean(lab_bulk))
            gamma = bulk_mean * 9.81  # t/m³ ≈ g/cm³ → kN/m³
            return SynthesizedValue(
                value=gamma,
                source="lab_direct",
                confidence="high",
                trace={"lab_bulk_t_m3": lab_bulk},
            )

        cpt_gamma = self._mean_channel_in_layer(layer, "gamma")
        if cpt_gamma is not None:
            return SynthesizedValue(
                value=cpt_gamma,
                source="cpt_derived",
                confidence="medium",
                trace={"source": "Robertson&Cabal 2010 estimate"},
            )
        return SynthesizedValue(
            trace={"checked": ["density_log", "lab_bulk", "cpt_gamma"]}
        )

    # ------------------------------------------------------------------
    # Su (kPa)
    # ------------------------------------------------------------------

    def _synth_su(self, layer, lab_hits) -> SynthesizedValue:
        lab_su = [
            s.undrained_shear_strength_kpa for s in lab_hits
            if s.undrained_shear_strength_kpa is not None
        ]
        if lab_su:
            return SynthesizedValue(
                value=float(np.mean(lab_su)),
                source="lab_direct",
                confidence="high",
                trace={"lab_su_values": lab_su, "n_samples": len(lab_su)},
            )

        # CPT (qt − σv0)/Nkt, compute both Nkt=15 and Nkt=30 bounds
        qt_mean = self._mean_channel_in_layer(layer, "qt")
        sv0_mean = self._mean_channel_in_layer(layer, "sigma_v0")
        if qt_mean is not None and sv0_mean is not None:
            qt_kpa = qt_mean * 1000.0  # MPa → kPa
            qnet = max(qt_kpa - sv0_mean, 0.0)
            su_15 = qnet / 15.0
            su_30 = qnet / 30.0
            return SynthesizedValue(
                value=su_15,
                source="cpt_derived",
                confidence="medium",
                trace={
                    "qt_mean_mpa": qt_mean,
                    "sigma_v0_mean_kpa": sv0_mean,
                    "Su_Nkt15_kpa": su_15,
                    "Su_Nkt30_kpa": su_30,
                    "bounds": [su_30, su_15],
                },
            )
        return SynthesizedValue(trace={"checked": ["lab_su", "cpt_qt_sv0"]})

    # ------------------------------------------------------------------
    # Dr (0..1 ratio)
    # ------------------------------------------------------------------

    def _synth_dr(self, layer, lab_hits) -> SynthesizedValue:
        # Lab doesn't carry Dr in the 17-field schema, so jump to CPT
        dr_mean = self._mean_channel_in_layer(layer, "Dr")
        if dr_mean is not None:
            return SynthesizedValue(
                value=dr_mean,
                source="cpt_derived",
                confidence="medium",
                trace={"source": "Jamiolkowski 2001"},
            )
        return SynthesizedValue(trace={"checked": ["cpt_dr"]})

    # ------------------------------------------------------------------
    # phi'
    # ------------------------------------------------------------------

    def _synth_phi_prime(self, layer, lab_hits) -> SynthesizedValue:
        lab_phi = [
            s.effective_friction_angle_deg for s in lab_hits
            if s.effective_friction_angle_deg is not None
        ]
        if lab_phi:
            return SynthesizedValue(
                value=float(np.mean(lab_phi)),
                source="lab_direct",
                confidence="high",
                trace={"lab_phi_deg": lab_phi},
            )
        return SynthesizedValue(trace={"checked": ["lab_phi"]})

    # ------------------------------------------------------------------
    # Vp / Vs
    # ------------------------------------------------------------------

    def _synth_pswave(self, layer, which: str) -> SynthesizedValue:
        if self.pswave_log is None:
            return SynthesizedValue(trace={"checked": ["pswave_log"]})
        depth = self.pswave_log.depth_gl_m
        if which == "Vp":
            series = self.pswave_log.vp_km_s
        else:
            series = self.pswave_log.vs_km_s
        mask = (depth >= layer.top_m) & (depth < layer.base_m)
        sel = series[mask & np.isfinite(series)]
        if sel.size == 0:
            return SynthesizedValue(trace={"checked": ["pswave_log"], "layer_empty": True})
        return SynthesizedValue(
            value=float(np.mean(sel)),
            source="pswave_direct",
            confidence="high",
            trace={"n_samples": int(sel.size), "unit": "km/s"},
        )

    # ------------------------------------------------------------------
    # N (SPT from neighbors)
    # ------------------------------------------------------------------

    def _synth_spt(self, layer) -> SynthesizedValue:
        hits = [
            t.n_value for t in self.neighbor_spt
            if layer.top_m <= t.top_m < layer.base_m and t.n_value is not None
        ]
        if hits:
            return SynthesizedValue(
                value=float(np.mean(hits)),
                source="spt_neighbor",
                confidence="medium",
                trace={"n_values": hits, "pair_count": len(hits)},
            )
        return SynthesizedValue(trace={"checked": ["neighbor_spt"]})

    # ------------------------------------------------------------------
    # Em
    # ------------------------------------------------------------------

    def _synth_em(self, layer) -> SynthesizedValue:
        llt_hits = [
            t for t in self.llt_tests
            if layer.top_m <= t.depth_m < layer.base_m
        ]
        if llt_hits:
            em_values = [t.em_mpa for t in llt_hits]
            return SynthesizedValue(
                value=float(np.mean(em_values)),
                source="llt_direct",
                confidence="high",
                trace={"em_values_mpa": em_values, "n_tests": len(llt_hits)},
            )

        # PSWave Ed — dynamic Young's modulus, rough proxy for static Em
        if self.pswave_log is not None:
            depth = self.pswave_log.depth_gl_m
            ed = self.pswave_log.ed_vendor_mpa
            mask = (depth >= layer.top_m) & (depth < layer.base_m)
            sel = ed[mask & np.isfinite(ed)]
            if sel.size > 0:
                return SynthesizedValue(
                    value=float(np.mean(sel)),
                    source="pswave_direct",
                    confidence="medium",
                    trace={
                        "source": "PSWave Ed (dynamic) — rough proxy for Em",
                        "n_samples": int(sel.size),
                    },
                )
        return SynthesizedValue(trace={"checked": ["llt", "pswave_ed"]})

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    def _mean_channel_in_layer(self, layer, name: str) -> float | None:
        ch = self.sounding.channels.get(name) or self.sounding.derived.get(name)
        if ch is None:
            return None
        depth_ch = self.sounding.channels.get("depth")
        if depth_ch is None:
            return None
        mask = (depth_ch.values >= layer.top_m) & (depth_ch.values < layer.base_m)
        vals = np.asarray(ch.values, dtype=np.float64)[mask & np.isfinite(ch.values)]
        if vals.size == 0:
            return None
        return float(np.mean(vals))

    def _mean_density_in_layer(self, layer) -> float | None:
        if self.density_log is None:
            return None
        depth = self.density_log.depth_m
        dens = self.density_log.density_g_cm3
        mask = (depth >= layer.top_m) & (depth < layer.base_m)
        sel = dens[mask & np.isfinite(dens)]
        if sel.size == 0:
            return None
        return float(np.mean(sel))


# ---------------------------------------------------------------------------
# Robertson zone → USCS label helper
# ---------------------------------------------------------------------------


_ZONE_TO_USCS: dict[int, str] = {
    1: "OL",   # Sensitive fine grained
    2: "OH",   # Organic clays
    3: "CL",   # Clays
    4: "ML",   # Silt mixtures
    5: "SM",   # Silty sand
    6: "SP",   # Clean sand
    7: "GW",   # Gravelly sand
    8: "SC",   # Very stiff sand to clayey sand
    9: "CH",   # Very stiff fine grained
}


def _zone_to_uscs(zone: int) -> str:
    return _ZONE_TO_USCS.get(zone, "OTHER")
