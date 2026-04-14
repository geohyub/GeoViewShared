"""Tests for geoview_cpt.derivation.strength — Phase A-2 A2.5c."""
from __future__ import annotations

import numpy as np
import pytest

from geoview_cpt.derivation.strength import (
    DEFAULT_NKT,
    compute_dr_jamiolkowski,
    compute_su,
)
from geoview_cpt.model import CPTChannel


def _ch(name, unit, values):
    return CPTChannel(name=name, unit=unit, values=values)


# ---------------------------------------------------------------------------
# Su — Nkt list
# ---------------------------------------------------------------------------


class TestComputeSuDefaultNkt:
    def test_returns_dict_of_two_channels(self):
        qt = _ch("qt", "MPa", [1.0, 2.0, 3.0])
        sv0 = _ch("sigma_v0", "kPa", [10.0, 20.0, 30.0])
        out = compute_su(qt, sv0)
        assert set(out.keys()) == {15.0, 30.0}
        for ch in out.values():
            assert ch.unit == "kPa"
            assert ch.values.shape == (3,)

    def test_su_values(self):
        # qt = 1 MPa = 1000 kPa, sv0 = 50 kPa → qnet = 950 kPa
        # Nkt = 15 → Su = 63.33
        # Nkt = 30 → Su = 31.67
        qt = _ch("qt", "MPa", [1.0])
        sv0 = _ch("sigma_v0", "kPa", [50.0])
        out = compute_su(qt, sv0)
        assert np.isclose(out[15.0].values[0], 950.0 / 15.0)
        assert np.isclose(out[30.0].values[0], 950.0 / 30.0)

    def test_channel_names(self):
        out = compute_su(_ch("qt", "MPa", [1.0]), _ch("sigma_v0", "kPa", [10.0]))
        assert out[15.0].name == "Su_Nkt15"
        assert out[30.0].name == "Su_Nkt30"


class TestComputeSuCustomNkt:
    def test_single_nkt_scalar(self):
        out = compute_su(
            _ch("qt", "MPa", [1.0]), _ch("sigma_v0", "kPa", [10.0]), nkt=20
        )
        assert list(out.keys()) == [20.0]

    def test_list_of_nkt(self):
        out = compute_su(
            _ch("qt", "MPa", [1.0]), _ch("sigma_v0", "kPa", [10.0]),
            nkt=[10, 15, 20, 25],
        )
        assert set(out.keys()) == {10.0, 15.0, 20.0, 25.0}

    def test_float_nkt_name(self):
        out = compute_su(
            _ch("qt", "MPa", [1.0]), _ch("sigma_v0", "kPa", [10.0]), nkt=14.5
        )
        assert out[14.5].name == "Su_Nkt14.5"

    def test_negative_nkt_rejected(self):
        with pytest.raises(ValueError, match="Nkt must be positive"):
            compute_su(_ch("qt", "MPa", [1.0]), _ch("sigma_v0", "kPa", [1.0]), nkt=-1)

    def test_empty_nkt_rejected(self):
        with pytest.raises(ValueError, match="non-empty"):
            compute_su(_ch("qt", "MPa", [1.0]), _ch("sigma_v0", "kPa", [1.0]), nkt=[])


class TestSuUnitAware:
    def test_qt_kpa_input(self):
        qt = _ch("qt", "kPa", [1000.0])
        sv0 = _ch("sigma_v0", "kPa", [50.0])
        out = compute_su(qt, sv0)
        assert np.isclose(out[15.0].values[0], 950.0 / 15.0)

    def test_mixed_units_ok(self):
        # qt in MPa, sv0 in kPa — canonical parser output
        qt = _ch("qt", "MPa", [2.0])
        sv0 = _ch("sigma_v0", "kPa", [100.0])
        out = compute_su(qt, sv0, nkt=15)
        # qnet = 2000 - 100 = 1900
        assert np.isclose(out[15.0].values[0], 1900.0 / 15.0)

    def test_shape_mismatch(self):
        with pytest.raises(ValueError, match="shape"):
            compute_su(
                _ch("qt", "MPa", [1.0, 2.0]), _ch("sigma_v0", "kPa", [10.0])
            )


class TestDefaultNkt:
    def test_constant_pair(self):
        assert DEFAULT_NKT == (15.0, 30.0)


# ---------------------------------------------------------------------------
# Dr — Jamiolkowski (HARDCODED UNITS)
# ---------------------------------------------------------------------------


class TestComputeDrJamiolkowski:
    def test_accepts_mpa_and_kpa(self):
        qc = _ch("qc", "MPa", [10.0])
        spv0 = _ch("sigma_prime_v0", "kPa", [50.0])
        dr = compute_dr_jamiolkowski(qc, spv0)
        assert dr.name == "Dr"
        assert dr.unit == "-"
        assert dr.values.shape == (1,)

    def test_value_matches_formula(self):
        # Dr = (1/2.9) × ln(10 / (141 × 50^0.55))
        qc = _ch("qc", "MPa", [10.0])
        spv0 = _ch("sigma_prime_v0", "kPa", [50.0])
        dr = compute_dr_jamiolkowski(qc, spv0)
        expected = (1.0 / 2.9) * np.log(10.0 / (141.0 * 50.0 ** 0.55))
        assert np.isclose(dr.values[0], expected)

    def test_rejects_qc_in_kpa(self):
        qc = _ch("qc", "kPa", [10000.0])
        spv0 = _ch("sigma_prime_v0", "kPa", [50.0])
        with pytest.raises(ValueError, match="qc.unit == 'MPa'"):
            compute_dr_jamiolkowski(qc, spv0)

    def test_rejects_spv0_in_mpa(self):
        qc = _ch("qc", "MPa", [10.0])
        spv0 = _ch("sigma_prime_v0", "MPa", [0.05])
        with pytest.raises(ValueError, match="sigma_prime_v0.unit == 'kPa'"):
            compute_dr_jamiolkowski(qc, spv0)

    def test_spv0_floor_avoids_log_crash(self):
        # σ'v0 = 0 at first sample
        qc = _ch("qc", "MPa", [0.0, 5.0])
        spv0 = _ch("sigma_prime_v0", "kPa", [0.0, 20.0])
        dr = compute_dr_jamiolkowski(qc, spv0)
        assert np.all(np.isfinite(dr.values))

    def test_zero_qc_yields_finite(self):
        qc = _ch("qc", "MPa", [0.0])
        spv0 = _ch("sigma_prime_v0", "kPa", [50.0])
        dr = compute_dr_jamiolkowski(qc, spv0)
        assert np.isfinite(dr.values[0])

    def test_array(self):
        qc = _ch("qc", "MPa", [1.0, 5.0, 10.0, 20.0])
        spv0 = _ch("sigma_prime_v0", "kPa", [10.0, 30.0, 50.0, 100.0])
        dr = compute_dr_jamiolkowski(qc, spv0)
        assert dr.values.shape == (4,)
        # Dr should increase with qc at constant σ'v0 — check monotone on
        # a synthetic pair
        qc2 = _ch("qc", "MPa", [1.0, 2.0, 5.0, 10.0])
        spv02 = _ch("sigma_prime_v0", "kPa", [50.0, 50.0, 50.0, 50.0])
        dr2 = compute_dr_jamiolkowski(qc2, spv02)
        assert np.all(np.diff(dr2.values) > 0)

    def test_shape_mismatch(self):
        with pytest.raises(ValueError, match="shape"):
            compute_dr_jamiolkowski(
                _ch("qc", "MPa", [1.0, 2.0]),
                _ch("sigma_prime_v0", "kPa", [10.0]),
            )
