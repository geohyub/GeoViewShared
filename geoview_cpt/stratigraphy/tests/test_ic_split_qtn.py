"""Q36b regression — ic_split Qt1 → Qtn production path."""
from __future__ import annotations

import numpy as np
import pytest

from geoview_cpt.correction.qt import compute_qt
from geoview_cpt.correction.stress import compute_sigma_prime_v0, compute_sigma_v0
from geoview_cpt.correction.u0 import hydrostatic_pressure
from geoview_cpt.derivation.ic import compute_fr_normalized, compute_ic, compute_qt_normalized
from geoview_cpt.derivation.qtn import compute_ic_robertson_2009
from geoview_cpt.model import CPTChannel, CPTSounding
from geoview_cpt.stratigraphy.ic_split import auto_split_by_ic


def _full_sounding() -> CPTSounding:
    """Synthetic sounding with every input required for Robertson 2009 Ic."""
    depth = np.linspace(0.5, 20.0, 400)
    qc_vals = np.where(depth < 10.0, 2.0 + 0.3 * depth, 8.0 + 0.1 * depth)
    fs_vals = np.where(depth < 10.0, 20.0 + depth * 3.0, 80.0 + depth * 2.0)
    u2_vals = 10.0 + depth * 10.0
    s = CPTSounding(handle=1, element_tag="1", name="CPT-Q36b")
    s.channels = {
        "depth": CPTChannel(name="depth", unit="m", values=depth),
        "qc":    CPTChannel(name="qc",    unit="MPa", values=qc_vals),
        "fs":    CPTChannel(name="fs",    unit="kPa", values=fs_vals),
        "u2":    CPTChannel(name="u2",    unit="kPa", values=u2_vals),
    }
    qt = compute_qt(s.channels["qc"], s.channels["u2"], a=0.7032)
    u0 = hydrostatic_pressure(s.channels["depth"])
    sv0 = compute_sigma_v0(s.channels["depth"], gamma=18.0)
    spv0 = compute_sigma_prime_v0(sv0, u0)
    s.derived = {
        "qt": qt,
        "u0": u0,
        "sigma_v0": sv0,
        "sigma_prime_v0": spv0,
    }
    return s


class TestQ36bAutoMode:
    def test_auto_uses_robertson_2009_when_inputs_available(self):
        s = _full_sounding()
        # Auto should detect qt/fs/sv0/spv0 and recompute with Qtn
        layers = auto_split_by_ic(s)
        assert len(layers) >= 1
        # No pre-populated Ic; the deriver ran internally
        assert "Ic" not in s.derived

    def test_auto_falls_back_to_existing_ic(self):
        """When raw inputs are missing we read the pre-populated Ic channel."""
        s = CPTSounding(handle=1, element_tag="1", name="CPT-legacy")
        depth = np.linspace(0.0, 10.0, 100)
        ic_vals = np.where(depth < 5.0, 1.8, 3.2)
        s.channels = {"depth": CPTChannel(name="depth", unit="m", values=depth)}
        s.derived = {"Ic": CPTChannel(name="Ic", unit="-", values=ic_vals)}
        layers = auto_split_by_ic(s)
        # Two zones
        assert len(layers) == 2

    def test_legacy_qt1_produces_lower_ic_than_qtn(self):
        """
        Pin the Week 4 observation: feeding Qt1 to compute_ic gives a
        smaller Ic than Qtn. Q36b motivation lives here.
        """
        s = _full_sounding()
        fr = compute_fr_normalized(
            s.channels["fs"], s.derived["qt"], s.derived["sigma_v0"]
        )
        qt1 = compute_qt_normalized(
            s.derived["qt"], s.derived["sigma_v0"], s.derived["sigma_prime_v0"]
        )
        ic_qt1 = compute_ic(qt1, fr)
        ic_qtn = compute_ic_robertson_2009(
            s.derived["qt"],
            s.channels["fs"],
            s.derived["sigma_v0"],
            s.derived["sigma_prime_v0"],
        )
        # In the clay band (depth > 10) Qtn Ic must be >= Qt1 Ic on average
        deep_mask = s.channels["depth"].values > 10
        assert float(np.nanmean(ic_qtn.values[deep_mask])) >= float(
            np.nanmean(ic_qt1.values[deep_mask])
        ) - 0.05


class TestExplicitModes:
    def test_robertson_2009_raises_when_missing_inputs(self):
        s = CPTSounding(handle=1, element_tag="1", name="x")
        s.channels = {
            "depth": CPTChannel(name="depth", unit="m", values=np.array([0.0, 1.0]))
        }
        with pytest.raises(KeyError, match="robertson_2009"):
            auto_split_by_ic(s, ic_mode="robertson_2009")

    def test_robertson_2009_succeeds_with_raw_inputs(self):
        layers = auto_split_by_ic(_full_sounding(), ic_mode="robertson_2009")
        assert len(layers) >= 1

    def test_existing_mode_ignores_raw_inputs(self):
        s = _full_sounding()
        # No pre-populated Ic — "existing" mode yields the undifferentiated
        # fallback layer
        layers = auto_split_by_ic(s, ic_mode="existing")
        assert len(layers) == 1
        assert layers[0].legend_code == "NA"

    def test_off_mode_always_single_layer(self):
        layers = auto_split_by_ic(_full_sounding(), ic_mode="off")
        assert len(layers) == 1
        assert layers[0].legend_code == "NA"
