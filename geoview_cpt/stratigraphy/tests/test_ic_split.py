"""Tests for geoview_cpt.stratigraphy.ic_split — Phase A-2 A2.8."""
from __future__ import annotations

import numpy as np
import pytest

from geoview_cpt.model import CPTChannel, CPTSounding
from geoview_cpt.stratigraphy.ic_split import (
    DEFAULT_IC_THRESHOLDS,
    StratumEditor,
    auto_split_by_ic,
)
from geoview_gi.minimal_model import StratumLayer


def _sounding_with_ic(depth: np.ndarray, ic: np.ndarray) -> CPTSounding:
    s = CPTSounding(handle=1, element_tag="1", name="CPT-SYNTH")
    s.channels = {
        "depth": CPTChannel(name="depth", unit="m", values=depth),
    }
    s.derived = {
        "Ic": CPTChannel(name="Ic", unit="-", values=ic),
    }
    return s


# ---------------------------------------------------------------------------
# auto_split_by_ic
# ---------------------------------------------------------------------------


class TestAutoSplit:
    def test_uniform_clay_single_layer(self):
        depth = np.linspace(0.0, 10.0, 100)
        ic = np.full(100, 3.2)  # zone 3 (clay)
        layers = auto_split_by_ic(_sounding_with_ic(depth, ic))
        assert len(layers) == 1
        assert layers[0].legend_code == "CL"
        assert layers[0].top_m == 0.0
        assert layers[0].base_m > 9.9

    def test_two_clear_zones(self):
        depth = np.linspace(0.0, 10.0, 100)
        ic = np.where(depth < 5.0, 1.8, 3.2)  # top = sand (6), bottom = clay (3)
        layers = auto_split_by_ic(_sounding_with_ic(depth, ic))
        assert len(layers) == 2
        assert layers[0].legend_code == "SP"  # clean sand
        assert layers[1].legend_code == "CL"
        assert abs(layers[0].base_m - 5.0) < 0.15

    def test_thin_layer_merged_up(self):
        depth = np.linspace(0.0, 10.0, 200)
        ic = np.where(depth < 5.0, 1.8, 3.2)
        # Insert a 5 cm silt sliver at depth 2m
        sliver_mask = (depth > 2.0) & (depth < 2.05)
        ic[sliver_mask] = 2.3
        layers = auto_split_by_ic(
            _sounding_with_ic(depth, ic), min_thickness_m=0.1
        )
        # Sliver should be merged into the overlying sand layer
        assert all(layer.thickness_m >= 0.1 for layer in layers)

    def test_top_sliver_merged_down(self):
        depth = np.linspace(0.0, 10.0, 100)
        ic = np.full(100, 3.2)
        ic[0:2] = 1.8   # 2-sample sand sliver at the surface (~0.1 m)
        layers = auto_split_by_ic(
            _sounding_with_ic(depth, ic), min_thickness_m=0.5
        )
        # Sliver (<0.5 m) should be merged into the underlying clay layer
        assert len(layers) == 1
        assert layers[0].legend_code == "CL"

    def test_missing_ic_falls_back(self):
        depth = np.array([0.0, 1.0, 2.0])
        s = CPTSounding(handle=1, element_tag="1", name="x")
        s.channels = {"depth": CPTChannel(name="depth", unit="m", values=depth)}
        layers = auto_split_by_ic(s)
        assert len(layers) == 1
        assert layers[0].legend_code == "NA"

    def test_empty_sounding_returns_empty_list(self):
        s = CPTSounding(handle=1, element_tag="1", name="x")
        assert auto_split_by_ic(s) == []

    def test_default_thresholds(self):
        assert DEFAULT_IC_THRESHOLDS == (1.31, 2.05, 2.60, 2.95, 3.60)


# ---------------------------------------------------------------------------
# StratumEditor
# ---------------------------------------------------------------------------


class TestStratumEditor:
    def _three_layers(self) -> list[StratumLayer]:
        return [
            StratumLayer(top_m=0.0, base_m=3.0, description="sand", legend_code="SP"),
            StratumLayer(top_m=3.0, base_m=7.0, description="silt", legend_code="ML"),
            StratumLayer(top_m=7.0, base_m=12.0, description="clay", legend_code="CL"),
        ]

    def test_move_boundary_valid(self):
        editor = StratumEditor(layers=self._three_layers())
        editor.move_boundary(1, 8.0)
        assert editor.layers[1].base_m == 8.0
        assert editor.layers[2].top_m == 8.0
        assert editor.layers[2].base_m == 12.0

    def test_move_boundary_out_of_range(self):
        editor = StratumEditor(layers=self._three_layers())
        with pytest.raises(ValueError):
            editor.move_boundary(1, 2.5)  # below upper's top
        with pytest.raises(ValueError):
            editor.move_boundary(1, 15.0)  # beyond lower's base

    def test_move_boundary_no_layer_below(self):
        editor = StratumEditor(layers=self._three_layers())
        with pytest.raises(IndexError):
            editor.move_boundary(2, 10.0)

    def test_merge_with_next(self):
        editor = StratumEditor(layers=self._three_layers())
        editor.merge_with_next(0)
        assert len(editor) == 2
        assert editor.layers[0].top_m == 0.0
        assert editor.layers[0].base_m == 7.0

    def test_split_valid(self):
        editor = StratumEditor(layers=self._three_layers())
        editor.split(1, 5.0)
        assert len(editor) == 4
        assert editor.layers[1].base_m == 5.0
        assert editor.layers[2].top_m == 5.0

    def test_split_at_boundary_rejected(self):
        editor = StratumEditor(layers=self._three_layers())
        with pytest.raises(ValueError):
            editor.split(1, 3.0)

    def test_copy_is_deep(self):
        editor = StratumEditor(layers=self._three_layers())
        clone = editor.copy()
        clone.merge_with_next(0)
        assert len(editor) == 3
        assert len(clone) == 2
