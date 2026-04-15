"""Structural tests for A2.7 chart builders — one class per chart."""
from __future__ import annotations

import pytest
from matplotlib.figure import Figure

from geoview_cpt.charts.borehole_log_kr import build_borehole_log_kr
from geoview_cpt.charts.cpet_it_compat import build_cpet_it_compat_plot
from geoview_cpt.charts.dr_profile import build_dr_profile
from geoview_cpt.charts.ic_profile import build_ic_profile
from geoview_cpt.charts.log_plot import build_log_plot
from geoview_cpt.charts.sbt_chart import build_sbt_chart
from geoview_cpt.charts.su_profile import build_su_profile


# ---------------------------------------------------------------------------
# A2.7a base charts
# ---------------------------------------------------------------------------


class TestLogPlot:
    def test_returns_figure(self, synthetic_sounding):
        fig = build_log_plot(synthetic_sounding)
        assert isinstance(fig, Figure)

    def test_has_five_tracks(self, synthetic_sounding):
        fig = build_log_plot(synthetic_sounding)
        assert len(fig.axes) == 5

    def test_title_contains_sounding_name(self, synthetic_sounding):
        fig = build_log_plot(synthetic_sounding)
        assert synthetic_sounding.name in fig._suptitle.get_text()

    def test_missing_rf_graceful(self, synthetic_sounding):
        synthetic_sounding.derived.pop("Rf")
        fig = build_log_plot(synthetic_sounding)
        # Still 5 axes — the Rf panel just carries a "not computed" note
        assert len(fig.axes) == 5


class TestSbtChart:
    def test_returns_figure(self, synthetic_sounding):
        fig = build_sbt_chart(synthetic_sounding)
        assert isinstance(fig, Figure)

    def test_log_log_axes(self, synthetic_sounding):
        fig = build_sbt_chart(synthetic_sounding)
        (ax,) = fig.axes
        assert ax.get_xscale() == "log"
        assert ax.get_yscale() == "log"

    def test_axis_limits(self, synthetic_sounding):
        fig = build_sbt_chart(synthetic_sounding)
        (ax,) = fig.axes
        assert ax.get_xlim() == (0.1, 10.0)
        assert ax.get_ylim() == (1.0, 1000.0)

    def test_nine_zone_patches_present(self, synthetic_sounding):
        from matplotlib.patches import Rectangle

        fig = build_sbt_chart(synthetic_sounding)
        (ax,) = fig.axes
        rects = [p for p in ax.patches if isinstance(p, Rectangle)]
        assert len(rects) == 9

    def test_sample_scatter_plotted(self, synthetic_sounding):
        fig = build_sbt_chart(synthetic_sounding)
        (ax,) = fig.axes
        # PathCollection for the scatter
        assert any(type(c).__name__ == "PathCollection" for c in ax.collections)


class TestIcProfile:
    def test_returns_figure(self, synthetic_sounding):
        fig = build_ic_profile(synthetic_sounding)
        assert isinstance(fig, Figure)

    def test_depth_axis_inverted_via_ylim(self, synthetic_sounding):
        fig = build_ic_profile(synthetic_sounding)
        ax = fig.axes[0]
        ylim = ax.get_ylim()
        assert ylim[0] > ylim[1]  # large at bottom (inverted)

    def test_zone_background_bands(self, synthetic_sounding):
        fig = build_ic_profile(synthetic_sounding)
        ax = fig.axes[0]
        # axvspan creates Polygon patches — should be 6 bands
        assert len(ax.patches) == 6


class TestSuProfile:
    def test_default_two_nkt_curves(self, synthetic_sounding):
        fig = build_su_profile(synthetic_sounding)
        ax = fig.axes[0]
        # Two line2d — one per Nkt
        lines = [ln for ln in ax.lines if not ln.get_label().startswith("_")]
        assert len(lines) == 2
        labels = [ln.get_label() for ln in lines]
        assert "Nkt = 15" in labels
        assert "Nkt = 30" in labels

    def test_single_nkt(self, synthetic_sounding):
        fig = build_su_profile(synthetic_sounding, nkt=20)
        ax = fig.axes[0]
        lines = [ln for ln in ax.lines if not ln.get_label().startswith("_")]
        assert len(lines) == 1


class TestDrProfile:
    def test_returns_figure(self, synthetic_sounding):
        fig = build_dr_profile(synthetic_sounding)
        assert isinstance(fig, Figure)

    def test_five_density_bands(self, synthetic_sounding):
        fig = build_dr_profile(synthetic_sounding)
        ax = fig.axes[0]
        # axvspan → 5 Polygon patches for the density bands
        assert len(ax.patches) == 5

    def test_x_axis_0_to_100(self, synthetic_sounding):
        fig = build_dr_profile(synthetic_sounding)
        ax = fig.axes[0]
        assert ax.get_xlim() == (0.0, 100.0)


# ---------------------------------------------------------------------------
# A2.7b ★ cpet_it_compat
# ---------------------------------------------------------------------------


class TestCpetItCompat:
    def test_returns_figure(self, synthetic_sounding):
        fig = build_cpet_it_compat_plot(synthetic_sounding)
        assert isinstance(fig, Figure)

    def test_has_main_layout(self, synthetic_sounding):
        """3 tracks + 1 cross-correlation + header + footer = 6 axes."""
        fig = build_cpet_it_compat_plot(synthetic_sounding)
        # header, qc, fs, u2, cross_corr, footer
        assert len(fig.axes) == 6

    def test_qc_axis_range(self, synthetic_sounding):
        fig = build_cpet_it_compat_plot(synthetic_sounding)
        qc_ax = fig.axes[1]
        assert qc_ax.get_xlim() == (0.0, 80.0)

    def test_fs_axis_range(self, synthetic_sounding):
        fig = build_cpet_it_compat_plot(synthetic_sounding)
        fs_ax = fig.axes[2]
        assert fs_ax.get_xlim() == (0.0, 200.0)

    def test_u2_axis_range(self, synthetic_sounding):
        fig = build_cpet_it_compat_plot(synthetic_sounding)
        u2_ax = fig.axes[3]
        assert u2_ax.get_xlim() == (-2000.0, 2000.0)

    def test_cross_correlation_log_log(self, synthetic_sounding):
        fig = build_cpet_it_compat_plot(synthetic_sounding)
        corr_ax = fig.axes[4]
        assert corr_ax.get_xscale() == "log"
        assert corr_ax.get_yscale() == "log"

    def test_branding_fallbacks_without_project(self, synthetic_sounding):
        fig = build_cpet_it_compat_plot(synthetic_sounding)
        header_ax = fig.axes[0]
        texts = " ".join(t.get_text() for t in header_ax.texts)
        assert "GEOVIEW" in texts
        assert "Busan" in texts

    def test_uses_project_branding_when_provided(self, synthetic_sounding):
        from types import SimpleNamespace

        proj = SimpleNamespace(
            partner_brand="HELMS",
            partner_description="Geomarine",
            partner_address="Seoul, Korea",
            partner_url="http://helms.example",
            name="Test Project",
        )
        fig = build_cpet_it_compat_plot(synthetic_sounding, project=proj)
        header_ax = fig.axes[0]
        texts = " ".join(t.get_text() for t in header_ax.texts)
        assert "HELMS" in texts
        assert "Seoul" in texts


# ---------------------------------------------------------------------------
# A2.7c ★ borehole_log_kr
# ---------------------------------------------------------------------------


class TestBoreholeLogKr:
    def _strata(self):
        from geoview_gi.minimal_model import StratumLayer

        return [
            StratumLayer(top_m=0, base_m=3, description="연약 점토", legend_code="CL"),
            StratumLayer(top_m=3, base_m=8, description="실트질 모래", legend_code="SM"),
            StratumLayer(top_m=8, base_m=15, description="치밀한 모래", legend_code="SP"),
            StratumLayer(top_m=15, base_m=25, description="풍화암", legend_code="ROCK"),
        ]

    def test_returns_figure(self, synthetic_sounding):
        fig = build_borehole_log_kr(
            synthetic_sounding,
            strata=self._strata(),
            project_name="Test",
            borehole_id="01",
        )
        assert isinstance(fig, Figure)

    def test_six_track_layout_plus_header_footer(self, synthetic_sounding):
        fig = build_borehole_log_kr(
            synthetic_sounding, strata=self._strata(),
            project_name="Test", borehole_id="01",
        )
        # header + 6 tracks + footer = 8 axes
        assert len(fig.axes) == 8

    def test_paging_advances_depth_window(self, synthetic_sounding):
        fig1 = build_borehole_log_kr(
            synthetic_sounding, strata=self._strata(),
            project_name="Test", borehole_id="01",
            page=1, max_depth_per_page=10.0,
        )
        fig2 = build_borehole_log_kr(
            synthetic_sounding, strata=self._strata(),
            project_name="Test", borehole_id="01",
            page=2, max_depth_per_page=10.0,
        )
        # Header text should carry different depth window strings
        h1 = " ".join(t.get_text() for t in fig1.axes[0].texts)
        h2 = " ".join(t.get_text() for t in fig2.axes[0].texts)
        assert "0.0 m" in h1
        assert "10.0 m" in h2

    def test_header_contains_korean_title(self, synthetic_sounding):
        fig = build_borehole_log_kr(
            synthetic_sounding, strata=self._strata(),
            project_name="야월풍력", borehole_id="YW-01",
        )
        texts = " ".join(t.get_text() for t in fig.axes[0].texts)
        assert "해상 시추주상도" in texts
        assert "야월풍력" in texts
        assert "YW-01" in texts

    def test_missing_strata_fallback_qc(self, synthetic_sounding):
        # Empty strata triggers qc-shaded fallback column — should still render
        fig = build_borehole_log_kr(
            synthetic_sounding, strata=[], project_name="Test", borehole_id="01",
        )
        assert len(fig.axes) == 8

    def test_spt_scatter_when_present(self, synthetic_sounding):
        from geoview_gi.minimal_model import SPTTest

        spts = [
            SPTTest(top_m=2.0, main_blows=5),
            SPTTest(top_m=5.0, main_blows=15),
            SPTTest(top_m=10.0, main_blows=40),
        ]
        fig = build_borehole_log_kr(
            synthetic_sounding, strata=self._strata(),
            spt_tests=spts, project_name="Test", borehole_id="01",
        )
        spt_ax = fig.axes[7 - 1]  # 6th track = SPT (header at 0, then 6 tracks 1..6, footer 7)
        assert any(type(c).__name__ == "PathCollection" for c in spt_ax.collections)


# ---------------------------------------------------------------------------
# VectorExportEngine smoke — each chart should survive SVG/PDF/PNG export
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "builder, extra_kwargs",
    [
        (build_log_plot, {}),
        (build_sbt_chart, {}),
        (build_ic_profile, {}),
        (build_su_profile, {}),
        (build_dr_profile, {}),
        (build_cpet_it_compat_plot, {}),
    ],
)
def test_export_triple(tmp_path, synthetic_sounding, builder, extra_kwargs):
    from geoview_pyside6.export import VectorExportEngine

    fig = builder(synthetic_sounding, **extra_kwargs)
    engine = VectorExportEngine()
    result = engine.render(fig, tmp_path, builder.__name__)
    assert result.svg.exists()
    assert result.pdf.exists()
    assert result.png.exists()
    assert result.png.read_bytes()[:4] == b"\x89PNG"


def test_borehole_log_kr_export_triple(tmp_path, synthetic_sounding):
    from geoview_gi.minimal_model import StratumLayer
    from geoview_pyside6.export import VectorExportEngine

    strata = [StratumLayer(top_m=0, base_m=25, description="혼성층", legend_code="SM")]
    fig = build_borehole_log_kr(
        synthetic_sounding, strata=strata, project_name="Test", borehole_id="01",
    )
    engine = VectorExportEngine()
    result = engine.render(fig, tmp_path, "borehole_log_kr")
    assert result.svg.exists()
    assert result.pdf.exists()
    assert result.png.exists()
