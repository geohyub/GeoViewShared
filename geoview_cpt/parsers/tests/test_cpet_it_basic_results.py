"""Tests for geoview_cpt.parsers.cpet_it_basic_results — A2.5 R2 fixture."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from geoview_cpt.parsers.cpet_it_basic_results import (
    BASIC_RESULTS_COLUMNS,
    BasicResultsParseError,
    BasicResultsTable,
    parse_basic_results,
)


# ---------------------------------------------------------------------------
# Real JAKO 분석결과_2nd sample (skipif H: drive missing)
# ---------------------------------------------------------------------------


_REAL_BASIC = Path(
    r"H:/자코/JAKO_Korea_area/분석결과_2nd/cpt01-Basic results.xls"
)
basic_required = pytest.mark.skipif(
    not _REAL_BASIC.exists(),
    reason="JAKO 분석결과_2nd Basic Results not mounted (H: drive)",
)


@pytest.fixture(scope="session")
def basic_results_cpt01():
    if not _REAL_BASIC.exists():
        pytest.skip("JAKO Basic Results not mounted")
    return parse_basic_results(_REAL_BASIC)


class TestColumnContract:
    def test_canonical_column_count(self):
        # Twenty-six columns documented in the master brief Wave 0 spec
        assert len(BASIC_RESULTS_COLUMNS) == 26


@basic_required
class TestRealJakoBasicResults:
    def test_returns_table(self, basic_results_cpt01):
        assert isinstance(basic_results_cpt01, BasicResultsTable)

    def test_sample_count(self, basic_results_cpt01):
        # JAKO CPT01 ground truth has 3943 processed samples
        assert basic_results_cpt01.n_samples > 1000

    def test_canonical_columns_present(self, basic_results_cpt01):
        for key in ("depth", "qc", "fs", "u", "qt", "rf", "ic", "bq", "gamma",
                    "sigma_v", "u0", "sigma_pvo"):
            assert key in basic_results_cpt01

    def test_depth_monotonic(self, basic_results_cpt01):
        z = basic_results_cpt01.get("depth")
        assert np.all(np.diff(z) >= -1e-6)

    def test_qt_close_to_qc(self, basic_results_cpt01):
        # JAKO data is pre-corrected (Gouda WISON cone_corrected=True),
        # so CPeT-IT's qt is essentially qc with a tiny residual. We just
        # check the magnitudes are within an order of magnitude.
        qc = basic_results_cpt01.get("qc")
        qt = basic_results_cpt01.get("qt")
        finite = np.isfinite(qc) & np.isfinite(qt)
        if not finite.any():
            pytest.skip("no finite qc/qt samples")
        assert np.median(np.abs(qt[finite] - qc[finite])) < 0.01  # well below 10 kPa

    def test_gamma_in_reasonable_range(self, basic_results_cpt01):
        g = basic_results_cpt01.get("gamma")
        # marine soft clay through stiff sand typically 13..20 kN/m³
        finite = g[np.isfinite(g)]
        assert finite.min() > 5
        assert finite.max() < 25


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class TestErrors:
    def test_missing_file(self, tmp_path):
        with pytest.raises(BasicResultsParseError, match="not found"):
            parse_basic_results(tmp_path / "nope.xls")
