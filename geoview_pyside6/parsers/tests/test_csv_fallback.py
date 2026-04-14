"""Tests for samples.CSVFallbackParser reference implementation."""
from __future__ import annotations

from pathlib import Path

import pytest

from geoview_pyside6.parsers.base import BaseParser, ParseError
from geoview_pyside6.parsers.samples.csv_fallback import (
    CSVFallbackParser,
    CSVPayload,
)


@pytest.fixture
def csv_file(tmp_path: Path) -> Path:
    p = tmp_path / "sample.csv"
    p.write_text(
        "depth,qc,fs,u2\n"
        "0.0,0.5,0.01,0.1\n"
        "0.1,0.6,0.01,0.1\n"
        "0.2,0.7,0.02,0.1\n",
        encoding="utf-8",
    )
    return p


@pytest.fixture
def tsv_file(tmp_path: Path) -> Path:
    p = tmp_path / "sample.tsv"
    p.write_text(
        "depth\tqc\tfs\n"
        "0.0\t0.5\t0.01\n"
        "0.1\t0.6\t0.01\n"
        "0.2\t0.7\t0.02\n",
        encoding="utf-8",
    )
    return p


@pytest.fixture
def semicolon_file(tmp_path: Path) -> Path:
    p = tmp_path / "sample.csv"
    p.write_text(
        "a;b;c\n1;2;3\n4;5;6\n",
        encoding="utf-8",
    )
    return p


@pytest.fixture
def non_csv_file(tmp_path: Path) -> Path:
    p = tmp_path / "not_csv.csv"
    p.write_text(
        "just one word per line\nno delimiters anywhere here\n",
        encoding="utf-8",
    )
    return p


class TestProtocol:
    def test_conforms_to_base_parser(self):
        assert isinstance(CSVFallbackParser(), BaseParser)

    def test_has_code_and_display_name(self):
        parser = CSVFallbackParser()
        assert parser.CODE == "csv_fallback"
        assert parser.DISPLAY_NAME == "Generic CSV"


class TestDetect:
    def test_detect_comma_csv(self, csv_file: Path):
        result = CSVFallbackParser().detect(csv_file)
        assert result is not None
        assert result.code == "csv_fallback"
        assert "delim=','" in result.notes
        assert 0.6 <= result.confidence <= 0.95

    def test_detect_tsv(self, tsv_file: Path):
        result = CSVFallbackParser().detect(tsv_file)
        assert result is not None
        assert "delim=" in result.notes
        # tab character in notes (escaped)
        assert "\\t" in result.notes or "\t" in result.notes

    def test_detect_semicolon(self, semicolon_file: Path):
        result = CSVFallbackParser().detect(semicolon_file)
        assert result is not None
        assert "delim=';'" in result.notes

    def test_detect_non_csv(self, non_csv_file: Path):
        assert CSVFallbackParser().detect(non_csv_file) is None

    def test_detect_wrong_extension(self, tmp_path: Path):
        p = tmp_path / "foo.bin"
        p.write_text("a,b,c\n1,2,3\n", encoding="utf-8")
        assert CSVFallbackParser().detect(p) is None

    def test_detect_empty_file(self, tmp_path: Path):
        p = tmp_path / "empty.csv"
        p.write_text("", encoding="utf-8")
        assert CSVFallbackParser().detect(p) is None

    def test_detect_single_line(self, tmp_path: Path):
        p = tmp_path / "one.csv"
        p.write_text("just,a,header\n", encoding="utf-8")
        # only 1 non-empty line → below _MIN_LINES threshold
        assert CSVFallbackParser().detect(p) is None


class TestParse:
    def test_parse_comma_csv(self, csv_file: Path):
        result = CSVFallbackParser().parse(csv_file)
        assert isinstance(result.payload, CSVPayload)
        assert result.payload.header == ["depth", "qc", "fs", "u2"]
        assert len(result.payload.rows) == 3
        assert result.payload.rows[0] == ["0.0", "0.5", "0.01", "0.1"]
        assert result.payload.delimiter == ","
        assert result.metadata["row_count"] == 3
        assert result.metadata["column_count"] == 4
        assert result.ok is True
        assert result.warnings == []

    def test_parse_tsv(self, tsv_file: Path):
        result = CSVFallbackParser().parse(tsv_file)
        assert result.payload.delimiter == "\t"
        assert result.payload.header == ["depth", "qc", "fs"]

    def test_parse_non_csv_raises(self, non_csv_file: Path):
        with pytest.raises(ParseError, match="cannot parse"):
            CSVFallbackParser().parse(non_csv_file)

    def test_parse_inconsistent_rows_warns(self, tmp_path: Path):
        p = tmp_path / "ragged.csv"
        p.write_text(
            "a,b,c\n"
            "1,2,3\n"
            "4,5\n"  # short
            "6,7,8\n"
            "9,10,11\n",
            encoding="utf-8",
        )
        result = CSVFallbackParser().parse(p)
        assert any("line 3" in w for w in result.warnings)
        # still ok — warnings don't set errors
        assert result.ok is True
