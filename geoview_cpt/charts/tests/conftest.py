"""Test fixtures for geoview_cpt.charts — matplotlib Agg + synthetic sounding."""
from __future__ import annotations

import os

import matplotlib

matplotlib.use("Agg")

import numpy as np
import pytest

from geoview_cpt.correction.qt import compute_qt
from geoview_cpt.correction.stress import compute_sigma_prime_v0, compute_sigma_v0
from geoview_cpt.correction.u0 import hydrostatic_pressure
from geoview_cpt.derivation.bq import compute_bq
from geoview_cpt.derivation.ic import (
    compute_fr_normalized,
    compute_ic,
    compute_qt_normalized,
)
from geoview_cpt.derivation.rf import compute_rf
from geoview_cpt.model import CPTChannel, CPTHeader, CPTSounding


@pytest.fixture
def synthetic_sounding() -> CPTSounding:
    """Full-pipeline sounding with raw + derived channels populated."""
    depth = np.linspace(0.5, 25.0, 200)
    qc_vals = 0.5 + depth * 0.6 + np.sin(depth) * 0.2
    fs_vals = 5.0 + depth * 1.5
    u2_vals = 10.0 + depth * 9.0

    s = CPTSounding(
        handle=1, element_tag="1", name="CPT-SYNTH",
        max_depth_m=float(depth.max()),
    )
    s.header = CPTHeader(
        sounding_id="CPT-SYNTH",
        ground_elev_m=-88.0,
        cone_base_area_mm2=1000.0,
        cone_area_ratio_a=0.71,
    )
    s.channels = {
        "depth": CPTChannel(name="depth", unit="m",   values=depth),
        "qc":    CPTChannel(name="qc",    unit="MPa", values=qc_vals),
        "fs":    CPTChannel(name="fs",    unit="kPa", values=fs_vals),
        "u2":    CPTChannel(name="u2",    unit="kPa", values=u2_vals),
    }

    # Build full derivation chain so chart builders have what they need
    qt = compute_qt(s.channels["qc"], s.channels["u2"], a=0.71)
    u0 = hydrostatic_pressure(s.channels["depth"])
    sigma_v0 = compute_sigma_v0(s.channels["depth"], gamma=18.0)
    sigma_prime_v0 = compute_sigma_prime_v0(sigma_v0, u0)
    rf = compute_rf(s.channels["fs"], qt)
    bq = compute_bq(s.channels["u2"], u0, qt, sigma_v0)
    qt1 = compute_qt_normalized(qt, sigma_v0, sigma_prime_v0)
    fr_norm = compute_fr_normalized(s.channels["fs"], qt, sigma_v0)
    ic = compute_ic(qt1, fr_norm)

    s.derived = {
        "qt": qt, "u0": u0, "sigma_v0": sigma_v0, "sigma_prime_v0": sigma_prime_v0,
        "Rf": rf, "Bq": bq, "Qt1": qt1, "Fr": fr_norm, "Ic": ic,
    }
    return s


@pytest.fixture(autouse=True)
def close_figures_after_test():
    yield
    import matplotlib.pyplot as plt

    plt.close("all")
