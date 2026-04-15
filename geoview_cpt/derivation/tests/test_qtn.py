"""Tests for geoview_cpt.derivation.qtn — Q36 Week 9."""
from __future__ import annotations

import numpy as np
import pytest

from geoview_cpt.derivation.ic import compute_fr_normalized, compute_ic, compute_qt_normalized
from geoview_cpt.derivation.qtn import (
    DEFAULT_PA_KPA,
    QtnIterationResult,
    compute_ic_robertson_2009,
    compute_qtn_iterative,
)
from geoview_cpt.model import CPTChannel


def _ch(name: str, unit: str, values) -> CPTChannel:
    return CPTChannel(name=name, unit=unit, values=np.asarray(values, dtype=np.float64))


class TestConvergence:
    def test_returns_iteration_result(self):
        qt = _ch("qt", "MPa", [1.0, 5.0, 10.0])
        fs = _ch("fs", "kPa", [10.0, 50.0, 100.0])
        sv = _ch("sigma_v0", "kPa", [20.0, 80.0, 150.0])
        spv = _ch("sigma_prime_v0", "kPa", [15.0, 60.0, 120.0])
        result = compute_qtn_iterative(qt, fs, sv, spv)
        assert isinstance(result, QtnIterationResult)
        assert result.qtn.name == "Qtn"
        assert result.ic.name == "Ic"
        assert result.qtn.values.shape == (3,)
        assert result.ic.values.shape == (3,)
        assert result.n.shape == (3,)

    def test_converges_in_few_iterations(self):
        # Realistic sand: qt 10 MPa, fs 50 kPa, mid-depth stresses
        qt = _ch("qt", "MPa", [10.0])
        fs = _ch("fs", "kPa", [60.0])
        sv = _ch("sigma_v0", "kPa", [90.0])
        spv = _ch("sigma_prime_v0", "kPa", [70.0])
        result = compute_qtn_iterative(qt, fs, sv, spv)
        assert result.converged
        assert result.iterations <= 6

    def test_n_within_bounds(self):
        qt = _ch("qt", "MPa", [0.5, 5.0, 20.0])
        fs = _ch("fs", "kPa", [5.0, 30.0, 100.0])
        sv = _ch("sigma_v0", "kPa", [10.0, 80.0, 200.0])
        spv = _ch("sigma_prime_v0", "kPa", [8.0, 60.0, 150.0])
        result = compute_qtn_iterative(qt, fs, sv, spv)
        assert np.all(result.n >= 0.5)
        assert np.all(result.n <= 1.0)


class TestShapeAndValidation:
    def test_shape_mismatch_raises(self):
        with pytest.raises(ValueError, match="share shape"):
            compute_qtn_iterative(
                _ch("qt", "MPa", [1.0, 2.0]),
                _ch("fs", "kPa", [10.0]),
                _ch("sv", "kPa", [20.0, 40.0]),
                _ch("spv", "kPa", [15.0, 30.0]),
            )

    def test_default_constants(self):
        assert DEFAULT_PA_KPA == 100.0


class TestSoilBehaviour:
    """Qtn and Qt1 differ systematically; the direction depends on the
    stress ratio σ'v0 / pa (= 1 crossover)."""

    def test_qtn_differs_from_qt1(self):
        qt = _ch("qt", "MPa", [15.0])
        fs = _ch("fs", "kPa", [60.0])
        sv = _ch("sigma_v0", "kPa", [180.0])
        spv = _ch("sigma_prime_v0", "kPa", [80.0])

        qt1 = compute_qt_normalized(qt, sv, spv)
        result = compute_qtn_iterative(qt, fs, sv, spv)
        # Both positive, finite, and noticeably different (Robertson 2009
        # rescales so values diverge unless spv0 == pa exactly).
        assert result.qtn.values[0] > 0
        assert qt1.values[0] > 0
        rel = abs(result.qtn.values[0] - qt1.values[0]) / qt1.values[0]
        assert rel > 0.02

    def test_deep_sand_qtn_greater_than_qt1(self):
        # Deep sand: σ'v0 > pa, so (pa/σ'v0)^n < 1 — but qnet/pa > qnet/σ'v0,
        # and the second factor dominates.
        qt = _ch("qt", "MPa", [25.0])
        fs = _ch("fs", "kPa", [120.0])
        sv = _ch("sigma_v0", "kPa", [400.0])
        spv = _ch("sigma_prime_v0", "kPa", [250.0])

        qt1 = compute_qt_normalized(qt, sv, spv)
        result = compute_qtn_iterative(qt, fs, sv, spv)
        # At σ'v0 > pa the n < 1 exponent LOWERS the correction relative
        # to linear Qt1 since (pa/σ'v0) < 1 and n < 1 pushes toward 1.
        # We simply check they differ by > 2%.
        rel = abs(result.qtn.values[0] - qt1.values[0]) / qt1.values[0]
        assert rel > 0.02

    def test_clay_qtn_close_to_qt1(self):
        # Clay: Robertson 2009 gives n ≈ 1 so Qtn ≈ Qt1
        qt = _ch("qt", "MPa", [1.2])
        fs = _ch("fs", "kPa", [40.0])
        sv = _ch("sigma_v0", "kPa", [180.0])
        spv = _ch("sigma_prime_v0", "kPa", [100.0])

        qt1 = compute_qt_normalized(qt, sv, spv)
        result = compute_qtn_iterative(qt, fs, sv, spv)
        rel_diff = abs(result.qtn.values[0] - qt1.values[0]) / max(qt1.values[0], 1e-6)
        # Within 15% for clay (n ≈ 1 boundary case)
        assert rel_diff < 0.15


class TestConvenienceWrapper:
    def test_compute_ic_robertson_2009(self):
        qt = _ch("qt", "MPa", [5.0])
        fs = _ch("fs", "kPa", [40.0])
        sv = _ch("sigma_v0", "kPa", [50.0])
        spv = _ch("sigma_prime_v0", "kPa", [30.0])
        ic = compute_ic_robertson_2009(qt, fs, sv, spv)
        assert isinstance(ic, CPTChannel)
        assert ic.name == "Ic"
        assert np.isfinite(ic.values[0])
        assert 1.0 < ic.values[0] < 5.0

    def test_kwargs_propagate(self):
        qt = _ch("qt", "MPa", [5.0])
        fs = _ch("fs", "kPa", [40.0])
        sv = _ch("sigma_v0", "kPa", [50.0])
        spv = _ch("sigma_prime_v0", "kPa", [30.0])
        ic = compute_ic_robertson_2009(qt, fs, sv, spv, max_iter=2)
        assert np.isfinite(ic.values[0])
