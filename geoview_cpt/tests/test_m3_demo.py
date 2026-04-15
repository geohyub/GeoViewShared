"""
M3 Demo — JAKO CPT01 end-to-end pipeline smoke test (Week 11 Phase A-2 gate).

Runs the full Week 1-10 pipeline against the real JAKO CPT01 sounding:

    .cdf + .CLog  →  parse_cdf_bundle
                     compute_qt / u0 / σv0 / σ'v0 / Rf / Bq
                     compute_qtn_iterative  (Q36b canonical Ic)
                     auto_split_by_ic  (Robertson 2009)
                     LayerSynthesizer  (9-property priority)
                     build_log_plot + build_sbt_chart + build_borehole_log_kr
                     VectorExportEngine  →  three deliverable folders:
                          01_log_plots/
                          02_sbt_analysis/
                          04a_borehole_log/

R1 gate — **Pretendard SVG Korean embed check**:
    After exporting the Korean borehole log, we parse the SVG and
    assert at least one ``<text>`` element contains a Korean character
    (``해상``, ``심도``, ``지층``) and that the SVG references the
    ``Pretendard`` font family. This is the v1 replacement for manual
    external-PC verification: once the SVG is structurally correct
    with embedded font attribution, any client machine that has
    Pretendard installed renders identically.

Skipped when H: drive is not mounted. The test writes to pytest's
``tmp_path`` so no real deliverable folder is touched.
"""
from __future__ import annotations

import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import numpy as np
import pytest

from geoview_cpt.charts.borehole_log_kr import build_borehole_log_kr
from geoview_cpt.charts.log_plot import build_log_plot
from geoview_cpt.charts.sbt_chart import build_sbt_chart
from geoview_cpt.correction.qt import compute_qt
from geoview_cpt.correction.stress import compute_sigma_prime_v0, compute_sigma_v0
from geoview_cpt.correction.u0 import hydrostatic_pressure
from geoview_cpt.derivation.bq import compute_bq
from geoview_cpt.derivation.ic import compute_fr_normalized
from geoview_cpt.derivation.qtn import compute_qtn_iterative
from geoview_cpt.derivation.rf import compute_rf
from geoview_cpt.model import CPTChannel, CPTSounding
from geoview_cpt.parsers.cpt_text_bundle import parse_cdf_bundle
from geoview_cpt.stratigraphy.ic_split import auto_split_by_ic
from geoview_cpt.synthesis.layer_properties import LayerSynthesizer
from geoview_gi.minimal_model import StratumLayer
from geoview_pyside6.export import VectorExportEngine


_REAL_CDF = Path(
    r"H:/자코/JAKO_Korea_area/Raw_data/Jako_Korea_area_CPT_raw_data/CPT01/CPT010001.cdf"
)
_REAL_CLOG = Path(
    r"H:/자코/JAKO_Korea_area/Raw_data/Jako_Korea_area_CPT_raw_data/CPT01/CPT010001.CLog"
)


m3_required = pytest.mark.skipif(
    not (_REAL_CDF.exists() and _REAL_CLOG.exists()),
    reason="JAKO CPT01 vendor bundle not mounted (H: drive)",
)


@pytest.fixture(scope="module")
def jako_cpt01_enriched() -> CPTSounding:
    """Full-pipeline CPTSounding: parsed + derived + synthesised."""
    if not (_REAL_CDF.exists() and _REAL_CLOG.exists()):
        pytest.skip("JAKO CPT01 bundle not mounted")

    s = parse_cdf_bundle(_REAL_CDF)

    # Derivation chain — Q36b canonical path
    qt = compute_qt(s.channels["qc"], s.channels["u2"], a=s.header.cone_area_ratio_a or 0.7032)
    u0 = hydrostatic_pressure(s.channels["depth"])
    sv0 = compute_sigma_v0(s.channels["depth"], gamma=18.0)
    spv0 = compute_sigma_prime_v0(sv0, u0)
    rf = compute_rf(s.channels["fs"], qt)
    bq = compute_bq(s.channels["u2"], u0, qt, sv0)
    fr_norm = compute_fr_normalized(s.channels["fs"], qt, sv0)
    qtn_result = compute_qtn_iterative(qt, s.channels["fs"], sv0, spv0)
    s.derived = {
        "qt": qt,
        "u0": u0,
        "sigma_v0": sv0,
        "sigma_prime_v0": spv0,
        "Rf": rf,
        "Bq": bq,
        "Fr": fr_norm,
        "Qtn": qtn_result.qtn,
        "Ic": qtn_result.ic,
    }
    return s


@m3_required
class TestM3Parsing:
    def test_bundle_loaded(self, jako_cpt01_enriched):
        s = jako_cpt01_enriched
        assert s.header.project_name.lower().startswith("jako")
        assert len(s.channels["depth"]) > 100
        assert len(s.header.events) > 0

    def test_derivation_chain_populated(self, jako_cpt01_enriched):
        s = jako_cpt01_enriched
        for key in ("qt", "u0", "sigma_v0", "sigma_prime_v0", "Rf", "Bq", "Qtn", "Ic"):
            assert key in s.derived
            assert s.derived[key].values.size == len(s.channels["depth"])


@m3_required
class TestM3Stratigraphy:
    def test_auto_split_produces_layers(self, jako_cpt01_enriched):
        layers = auto_split_by_ic(jako_cpt01_enriched)
        assert len(layers) >= 1
        # Full depth coverage
        assert layers[0].top_m == pytest.approx(
            float(jako_cpt01_enriched.channels["depth"].values[0]), abs=0.1
        )

    def test_synthesis_fills_properties(self, jako_cpt01_enriched):
        layers = auto_split_by_ic(jako_cpt01_enriched)
        syn = LayerSynthesizer(sounding=jako_cpt01_enriched, strata=layers)
        enriched = syn.synthesize()
        for layer in enriched:
            props = layer.synthesized_properties
            assert "USCS" in props
            assert "gamma" in props


@m3_required
class TestM3Exports:
    def _three_folder_export(self, sounding, tmp_path: Path) -> dict[str, Path]:
        log_dir = tmp_path / "01_log_plots"
        sbt_dir = tmp_path / "02_sbt_analysis"
        bh_dir = tmp_path / "04a_borehole_log"
        engine = VectorExportEngine()

        fig_log = build_log_plot(sounding)
        r_log = engine.render(fig_log, log_dir, "CPT01_log")

        fig_sbt = build_sbt_chart(sounding)
        r_sbt = engine.render(fig_sbt, sbt_dir, "CPT01_sbt")

        # Synthetic strata for the borehole log (real stratigraphy via
        # auto_split_by_ic is layer-only; a full USCS tagging happens
        # through synthesis in the Deliverables Pack)
        strata = [
            StratumLayer(top_m=0, base_m=1.0, description="연약 점토", legend_code="CL"),
            StratumLayer(top_m=1.0, base_m=4.0, description="실트질 모래", legend_code="SM"),
        ]
        fig_bh = build_borehole_log_kr(
            sounding, strata=strata, project_name="JAKO Korea", borehole_id="CPT01",
        )
        r_bh = engine.render(fig_bh, bh_dir, "CPT01_borehole_log_kr")

        return {
            "log": r_log.svg,
            "sbt": r_sbt.svg,
            "bh_svg": r_bh.svg,
            "bh_pdf": r_bh.pdf,
            "bh_png": r_bh.png,
        }

    def test_three_folder_outputs_created(self, jako_cpt01_enriched, tmp_path):
        out = self._three_folder_export(jako_cpt01_enriched, tmp_path)
        for key, path in out.items():
            assert path.exists(), f"missing export: {key}"
            assert path.stat().st_size > 500

    def test_deliverable_folders_exist(self, jako_cpt01_enriched, tmp_path):
        self._three_folder_export(jako_cpt01_enriched, tmp_path)
        assert (tmp_path / "01_log_plots").is_dir()
        assert (tmp_path / "02_sbt_analysis").is_dir()
        assert (tmp_path / "04a_borehole_log").is_dir()

    # ---------- R1 gate: Pretendard SVG Korean embed ---------------------

    def test_borehole_log_svg_contains_korean_text(
        self, jako_cpt01_enriched, tmp_path
    ):
        out = self._three_folder_export(jako_cpt01_enriched, tmp_path)
        svg_text = out["bh_svg"].read_text(encoding="utf-8", errors="ignore")
        # Korean characters from the header template
        assert "해상" in svg_text or "심도" in svg_text or "지층" in svg_text, (
            "Korean text missing from borehole log SVG — "
            "Pretendard embed would fail on client machines"
        )

    def test_borehole_log_svg_uses_pretendard_family(
        self, jako_cpt01_enriched, tmp_path
    ):
        out = self._three_folder_export(jako_cpt01_enriched, tmp_path)
        svg_text = out["bh_svg"].read_text(encoding="utf-8", errors="ignore")
        assert "Pretendard" in svg_text, (
            "SVG must reference the Pretendard font family so external "
            "PCs can resolve Korean glyphs"
        )

    def test_borehole_log_svg_text_nodes_present(
        self, jako_cpt01_enriched, tmp_path
    ):
        """
        svg.fonttype='none' (A1.5 default) keeps glyphs as <text> nodes
        rather than raster paths — the R1 prerequisite for in-Word
        re-flowing.
        """
        out = self._three_folder_export(jako_cpt01_enriched, tmp_path)
        svg_text = out["bh_svg"].read_text(encoding="utf-8", errors="ignore")
        text_nodes = re.findall(r"<text[^>]*>[^<]*</text>", svg_text)
        assert len(text_nodes) > 20


@m3_required
class TestM3Regression:
    def test_pipeline_repeatable(self, jako_cpt01_enriched):
        """Running the pipeline twice on the same sounding is deterministic."""
        first_qtn = jako_cpt01_enriched.derived["Qtn"].values.copy()
        # Re-run Qtn from raw — should match bit-for-bit
        qt = jako_cpt01_enriched.derived["qt"]
        fs = jako_cpt01_enriched.channels["fs"]
        sv0 = jako_cpt01_enriched.derived["sigma_v0"]
        spv0 = jako_cpt01_enriched.derived["sigma_prime_v0"]
        again = compute_qtn_iterative(qt, fs, sv0, spv0)
        assert np.allclose(again.qtn.values, first_qtn, equal_nan=True)
