"""Tests for geoview_gi.lab.sa_geolab — Phase A-2 A2.18."""
from __future__ import annotations

from pathlib import Path

import pytest

from geoview_gi.lab.sa_geolab import (
    FAILURE_CODES,
    STATE_CODES,
    TEST_TYPES,
    SAGeolabParseError,
    parse_sa_geolab_pdf,
)
from geoview_gi.minimal_model import LabSample


# ---------------------------------------------------------------------------
# Reference dictionaries
# ---------------------------------------------------------------------------


class TestReferenceDictionaries:
    def test_sixteen_test_types(self):
        assert len(TEST_TYPES) == 16

    def test_known_type_codes(self):
        for key in ("UU", "CIU", "CID", "CAU", "RC", "IL", "CRS",
                    "DS", "DSS", "RS", "DR", "F", "NES", "NP"):
            assert key in TEST_TYPES

    def test_failure_codes(self):
        assert FAILURE_CODES["A"] == "Bulge"
        assert len(FAILURE_CODES) == 4

    def test_state_codes_present(self):
        for code in ("R", "r", "M", "c", "cyc"):
            assert code in STATE_CODES


# ---------------------------------------------------------------------------
# Real JAKO PDF (optional)
# ---------------------------------------------------------------------------


_REAL_SIGNED = Path(r"H:/자코/JAKO_Korea_area/실내시험결과/JAKO - signed.pdf")
_REAL_PRELIM = Path(r"H:/자코/JAKO_Korea_area/실내시험결과/JAKO-PC Preliminary.pdf")

signed_required = pytest.mark.skipif(
    not _REAL_SIGNED.exists(),
    reason="SA Geolab signed PDF not mounted",
)
prelim_required = pytest.mark.skipif(
    not _REAL_PRELIM.exists(),
    reason="SA Geolab preliminary PDF not mounted",
)


@pytest.fixture(scope="session")
def signed_samples():
    if not _REAL_SIGNED.exists():
        pytest.skip("signed PDF not mounted")
    return parse_sa_geolab_pdf(_REAL_SIGNED)


@pytest.fixture(scope="session")
def prelim_samples():
    if not _REAL_PRELIM.exists():
        pytest.skip("preliminary PDF not mounted")
    return parse_sa_geolab_pdf(_REAL_PRELIM)


@signed_required
class TestRealSigned:
    def test_returns_lab_samples(self, signed_samples):
        assert len(signed_samples) > 5
        for s in signed_samples[:20]:
            assert isinstance(s, LabSample)

    def test_sample_ids_recognized(self, signed_samples):
        ids = {s.sample_id for s in signed_samples}
        # The JAKO signed PDF is known to contain B1/Q1/Q2 sample tags
        assert any(sid.startswith("B") for sid in ids)
        assert any(sid.startswith("Q") for sid in ids)

    def test_depths_reasonable(self, signed_samples):
        for s in signed_samples:
            assert 0.0 <= s.top_m <= 200.0


@prelim_required
class TestRealPreliminary:
    def test_parse_runs_without_error(self, prelim_samples):
        # The preliminary PDF uses a looser table layout than the signed
        # report; v1 regex may return zero matches on some pages. Just
        # ensure the call completes and returns a list (full 16-test-type
        # parsing is open question Q39).
        assert isinstance(prelim_samples, list)


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class TestErrors:
    def test_missing_file(self, tmp_path):
        with pytest.raises(SAGeolabParseError):
            parse_sa_geolab_pdf(tmp_path / "nope.pdf")
