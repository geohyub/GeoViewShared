"""Tests for geoview_pyside6.export.engine — Phase A-1 A1.5."""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pytest
from matplotlib.figure import Figure

from geoview_pyside6.export import (
    ExportError,
    ExportResult,
    VectorExportEngine,
)


def _make_figure(*, title: str = "샘플 Figure 1,234.50 MPa") -> Figure:
    fig, ax = plt.subplots(figsize=(4, 3))
    ax.plot([0, 1, 2, 3, 4], [0, 1, 4, 9, 16], label="시추공 1")
    ax.set_xlabel("Depth (m)")
    ax.set_ylabel("q_c (MPa)")
    ax.set_title(title)
    ax.legend()
    return fig


@pytest.fixture
def engine():
    return VectorExportEngine()


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


class TestConstruction:
    def test_defaults(self):
        eng = VectorExportEngine()
        assert eng.dpi == 150
        assert eng.png_scale == 2.0
        assert eng.atomic is True

    def test_custom_png_scale(self):
        eng = VectorExportEngine(dpi=200, png_scale=1.5)
        assert eng.dpi == 200

    def test_invalid_dpi_rejected(self):
        with pytest.raises(ValueError):
            VectorExportEngine(dpi=0)

    def test_invalid_scale_rejected(self):
        with pytest.raises(ValueError):
            VectorExportEngine(png_scale=-1.0)


# ---------------------------------------------------------------------------
# Render happy path
# ---------------------------------------------------------------------------


class TestRenderHappy:
    def test_produces_three_formats(self, engine, tmp_path):
        fig = _make_figure()
        try:
            result = engine.render(fig, tmp_path, "plot_01")
        finally:
            plt.close(fig)

        assert isinstance(result, ExportResult)
        assert result.svg.exists()
        assert result.pdf.exists()
        assert result.png.exists()

    def test_file_signatures(self, engine, tmp_path):
        fig = _make_figure()
        try:
            result = engine.render(fig, tmp_path, "sig_test")
        finally:
            plt.close(fig)

        # SVG
        svg_body = result.svg.read_text(encoding="utf-8")
        assert "<svg" in svg_body.lower()
        # PDF
        assert result.pdf.read_bytes()[:5] == b"%PDF-"
        # PNG
        assert result.png.read_bytes()[:4] == b"\x89PNG"

    def test_svg_keeps_text_editable(self, engine, tmp_path):
        """svg.fonttype=none means glyphs remain as <text>, not <path>."""
        fig = _make_figure()
        try:
            result = engine.render(fig, tmp_path, "text_test")
        finally:
            plt.close(fig)
        body = result.svg.read_text(encoding="utf-8")
        assert "<text" in body

    def test_png_has_icc_profile(self, engine, tmp_path):
        from PIL import Image

        fig = _make_figure()
        try:
            result = engine.render(fig, tmp_path, "icc")
        finally:
            plt.close(fig)

        with Image.open(result.png) as img:
            assert img.info.get("icc_profile"), "PNG missing sRGB ICC profile"

    def test_png_scale_affects_resolution(self, tmp_path):
        from PIL import Image

        fig = _make_figure()
        try:
            small = VectorExportEngine(dpi=100, png_scale=1.0).render(
                fig, tmp_path, "small"
            )
            big = VectorExportEngine(dpi=100, png_scale=2.0).render(
                fig, tmp_path, "big"
            )
        finally:
            plt.close(fig)

        with Image.open(small.png) as s, Image.open(big.png) as b:
            assert b.size[0] >= s.size[0] * 1.8
            assert b.size[1] >= s.size[1] * 1.8

    def test_out_dir_created(self, engine, tmp_path):
        fig = _make_figure()
        try:
            nested = tmp_path / "nested" / "a" / "b"
            result = engine.render(fig, nested, "x")
        finally:
            plt.close(fig)
        assert result.svg.parent == nested.resolve()

    def test_result_paths_dict(self, engine, tmp_path):
        fig = _make_figure()
        try:
            result = engine.render(fig, tmp_path, "paths_dict")
        finally:
            plt.close(fig)
        d = result.paths
        assert set(d.keys()) == {"svg", "pdf", "png"}
        assert d["svg"] == result.svg


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------


class TestInputValidation:
    def test_rejects_non_figure(self, engine, tmp_path):
        with pytest.raises(TypeError, match="Figure"):
            engine.render("not a figure", tmp_path, "x")

    def test_empty_base_name(self, engine, tmp_path):
        fig = _make_figure()
        try:
            with pytest.raises(ValueError, match="base_name"):
                engine.render(fig, tmp_path, "")
        finally:
            plt.close(fig)

    def test_path_separator_rejected(self, engine, tmp_path):
        fig = _make_figure()
        try:
            with pytest.raises(ValueError, match="base_name"):
                engine.render(fig, tmp_path, "sub/plot")
        finally:
            plt.close(fig)

    def test_parent_escape_rejected(self, engine, tmp_path):
        fig = _make_figure()
        try:
            with pytest.raises(ValueError, match="base_name"):
                engine.render(fig, tmp_path, "..")
        finally:
            plt.close(fig)

    def test_reserved_char_rejected(self, engine, tmp_path):
        fig = _make_figure()
        try:
            with pytest.raises(ValueError, match="reserved"):
                engine.render(fig, tmp_path, "plot?1")
        finally:
            plt.close(fig)


# ---------------------------------------------------------------------------
# Atomic rollback
# ---------------------------------------------------------------------------


class TestAtomic:
    def test_non_atomic_mode(self, tmp_path):
        eng = VectorExportEngine(atomic=False)
        fig = _make_figure()
        try:
            result = eng.render(fig, tmp_path, "nonatomic")
        finally:
            plt.close(fig)
        assert result.png.exists()

    def test_atomic_leaves_no_tmp_siblings(self, engine, tmp_path):
        fig = _make_figure()
        try:
            engine.render(fig, tmp_path, "clean")
        finally:
            plt.close(fig)
        leftovers = [p for p in tmp_path.iterdir() if p.suffix == ".tmp"]
        assert leftovers == []
