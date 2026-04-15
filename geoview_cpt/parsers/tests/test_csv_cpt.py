"""Tests for geoview_cpt.parsers.csv_cpt — Phase A-2 A2.4."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from geoview_cpt.model import CPTSounding
from geoview_cpt.parsers.csv_cpt import (
    CptCsvParseError,
    detect_csv_cpt,
    parse_csv_cpt,
)


def _write(tmp_path: Path, name: str, body: str) -> Path:
    p = tmp_path / name
    p.write_text(body, encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


class TestParseCsvCpt:
    def test_basic_comma(self, tmp_path):
        csv = (
            "depth (m),qc (MPa),fs (kPa),u2 (kPa)\n"
            "0.02,0.05,1.2,0.5\n"
            "0.04,0.06,1.3,0.6\n"
            "0.06,0.08,1.5,0.7\n"
        )
        p = _write(tmp_path, "sample.csv", csv)
        s = parse_csv_cpt(p)
        assert isinstance(s, CPTSounding)
        assert set(s.channels.keys()) == {"depth", "qc", "fs", "u2"}
        assert s.channels["qc"].unit == "MPa"
        assert s.channels["fs"].unit == "kPa"
        assert len(s.channels["depth"]) == 3

    def test_tab_delimited(self, tmp_path):
        tsv = (
            "depth (m)\tqc (MPa)\tfs (kPa)\n"
            "0.02\t0.05\t1.2\n"
            "0.04\t0.06\t1.3\n"
            "0.06\t0.08\t1.5\n"
        )
        p = _write(tmp_path, "sample.tsv", tsv)
        s = parse_csv_cpt(p)
        assert len(s.channels["depth"]) == 3

    def test_fs_in_mpa_converted_to_kpa(self, tmp_path):
        csv = (
            "depth (m),qc (MPa),fs (MPa)\n"
            "0.02,0.05,0.001\n"
            "0.04,0.06,0.002\n"
            "0.06,0.08,0.003\n"
        )
        p = _write(tmp_path, "sample.csv", csv)
        s = parse_csv_cpt(p)
        # Canonical fs is kPa — 0.001 MPa → 1 kPa
        assert s.channels["fs"].unit == "kPa"
        assert s.channels["fs"].values[0] == pytest.approx(1.0)

    def test_unit_inference_defaults(self, tmp_path):
        csv = (
            "depth,qc,fs,u2\n"
            "0.02,0.05,1.2,0.5\n"
            "0.04,0.06,1.3,0.6\n"
        )
        p = _write(tmp_path, "sample.csv", csv)
        s = parse_csv_cpt(p)
        # No unit trailers → assume canonical
        assert s.channels["qc"].unit == "MPa"
        assert s.channels["fs"].unit == "kPa"

    def test_alternative_header_names(self, tmp_path):
        csv = (
            "test length (m),tip (MPa),sleeve (kPa),pore (kPa)\n"
            "0.02,0.05,1.2,0.5\n"
            "0.04,0.06,1.3,0.6\n"
        )
        p = _write(tmp_path, "alt.csv", csv)
        s = parse_csv_cpt(p)
        assert "depth" in s.channels
        assert "qc" in s.channels
        assert "fs" in s.channels
        assert "u2" in s.channels

    def test_depth_plus_qc_only(self, tmp_path):
        csv = "depth (m),qc (MPa)\n0.02,0.05\n0.04,0.06\n0.06,0.08\n"
        p = _write(tmp_path, "tip_only.csv", csv)
        s = parse_csv_cpt(p)
        assert set(s.channels.keys()) == {"depth", "qc"}
        assert "fs" not in s.channels
        assert "u2" not in s.channels

    def test_metadata(self, tmp_path):
        csv = "depth,qc\n0.02,0.05\n0.04,0.06\n"
        p = _write(tmp_path, "meta.csv", csv)
        s = parse_csv_cpt(p)
        meta = s.metadata
        assert meta["source_format"] == "csv_generic"
        assert meta["matched_columns"]["depth"] == 0
        assert meta["matched_columns"]["qc"] == 1


# ---------------------------------------------------------------------------
# detect_csv_cpt
# ---------------------------------------------------------------------------


class TestDetect:
    def test_positive(self, tmp_path):
        p = _write(tmp_path, "x.csv", "a,b\n1,2\n3,4\n")
        assert detect_csv_cpt(p) is True

    def test_unknown_extension(self, tmp_path):
        p = _write(tmp_path, "x.json", '{"a": 1}')
        assert detect_csv_cpt(p) is False

    def test_missing_file(self, tmp_path):
        assert detect_csv_cpt(tmp_path / "nope.csv") is False


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class TestErrors:
    def test_missing_file(self, tmp_path):
        with pytest.raises(CptCsvParseError):
            parse_csv_cpt(tmp_path / "nope.csv")

    def test_no_depth_column(self, tmp_path):
        csv = "time,value\n1,2\n3,4\n"
        p = _write(tmp_path, "no_depth.csv", csv)
        with pytest.raises(CptCsvParseError, match="depth"):
            parse_csv_cpt(p)
