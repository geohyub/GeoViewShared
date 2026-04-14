"""Tests for geoview_pyside6.reports.builder — Phase A-1 A1.6."""
from __future__ import annotations

import hashlib
from io import BytesIO
from pathlib import Path

import pytest

from geoview_pyside6.reports import (
    ReportBuilder,
    ReportBuildError,
    ReportFormat,
    ReportManifest,
)
from geoview_pyside6.reports.builder import ReportArtifact


# ---------------------------------------------------------------------------
# Fake generators — let us unit-test the builder without booting openpyxl/
# docx/reportlab. Real generator integration is exercised via a single
# smoke test at the end.
# ---------------------------------------------------------------------------


def _fake_excel(summary, output_path=None):
    return BytesIO(b"PK\x03\x04fake-xlsx-bytes")  # ZIP magic


def _fake_word(summary, output_path=None):
    return BytesIO(b"PK\x03\x04fake-docx-bytes")


def _fake_pdf(summary, output_path=None):
    return BytesIO(b"%PDF-1.4 fake")


def _failing(summary, output_path=None):
    raise RuntimeError("boom")


def _empty(summary, output_path=None):
    return BytesIO(b"")


def _returns_wrong_type(summary, output_path=None):
    return 42


def _fake_generators() -> dict:
    return {
        ReportFormat.EXCEL: _fake_excel,
        ReportFormat.WORD: _fake_word,
        ReportFormat.PDF: _fake_pdf,
    }


@pytest.fixture
def summary():
    # The builder never inspects the summary, so a sentinel is fine.
    return object()


@pytest.fixture
def builder():
    return ReportBuilder(generators=_fake_generators())


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


class TestConstruction:
    def test_defaults_load_real_generators(self):
        b = ReportBuilder()
        # Should have all three keys populated from geoview_common.
        assert set(b.generators.keys()) == set(ReportFormat)
        for fn in b.generators.values():
            assert callable(fn)

    def test_inject_fake_generators(self):
        b = ReportBuilder(generators=_fake_generators())
        assert b.generators[ReportFormat.EXCEL] is _fake_excel


# ---------------------------------------------------------------------------
# Single-format build
# ---------------------------------------------------------------------------


class TestBuildSingle:
    def test_excel_writes_and_returns_artifact(self, builder, summary, tmp_path):
        out = tmp_path / "report.xlsx"
        art = builder.build_excel(summary, out)

        assert isinstance(art, ReportArtifact)
        assert art.path == out.resolve()
        assert art.format is ReportFormat.EXCEL
        assert out.exists()
        data = out.read_bytes()
        assert data.startswith(b"PK")
        assert art.size_bytes == len(data)
        assert art.sha256 == hashlib.sha256(data).hexdigest()

    def test_word(self, builder, summary, tmp_path):
        out = tmp_path / "report.docx"
        art = builder.build_word(summary, out)
        assert art.format is ReportFormat.WORD
        assert out.read_bytes().startswith(b"PK")

    def test_pdf(self, builder, summary, tmp_path):
        out = tmp_path / "report.pdf"
        art = builder.build_pdf(summary, out)
        assert art.format is ReportFormat.PDF
        assert out.read_bytes().startswith(b"%PDF-")

    def test_suffix_mismatch_rejected(self, builder, summary, tmp_path):
        with pytest.raises(ReportBuildError, match="suffix"):
            builder.build(summary, tmp_path / "x.docx", fmt=ReportFormat.EXCEL)

    def test_parent_dir_created(self, builder, summary, tmp_path):
        out = tmp_path / "nested" / "a" / "report.xlsx"
        builder.build_excel(summary, out)
        assert out.exists()

    def test_generator_failure_wrapped(self, summary, tmp_path):
        b = ReportBuilder(
            generators={**_fake_generators(), ReportFormat.EXCEL: _failing}
        )
        with pytest.raises(ReportBuildError, match="xlsx"):
            b.build_excel(summary, tmp_path / "x.xlsx")

    def test_empty_output_rejected(self, summary, tmp_path):
        b = ReportBuilder(
            generators={**_fake_generators(), ReportFormat.EXCEL: _empty}
        )
        with pytest.raises(ReportBuildError, match="empty"):
            b.build_excel(summary, tmp_path / "x.xlsx")

    def test_wrong_return_type_rejected(self, summary, tmp_path):
        b = ReportBuilder(
            generators={
                **_fake_generators(),
                ReportFormat.EXCEL: _returns_wrong_type,
            }
        )
        with pytest.raises(ReportBuildError, match="unsupported type"):
            b.build_excel(summary, tmp_path / "x.xlsx")

    def test_accepts_raw_bytes(self, summary, tmp_path):
        def gen(summary, output_path=None):
            return b"PK-raw-bytes"

        b = ReportBuilder(generators={**_fake_generators(), ReportFormat.EXCEL: gen})
        art = b.build_excel(summary, tmp_path / "x.xlsx")
        assert art.size_bytes == len(b"PK-raw-bytes")

    def test_accepts_path_return(self, summary, tmp_path):
        pre = tmp_path / "pre.xlsx"
        pre.write_bytes(b"from-file-path")

        def gen(summary, output_path=None):
            return pre

        b = ReportBuilder(generators={**_fake_generators(), ReportFormat.EXCEL: gen})
        art = b.build_excel(summary, tmp_path / "x.xlsx")
        assert (tmp_path / "x.xlsx").read_bytes() == b"from-file-path"
        assert art.size_bytes == len(b"from-file-path")


# ---------------------------------------------------------------------------
# Triple-format build_all
# ---------------------------------------------------------------------------


class TestBuildAll:
    def test_three_files(self, builder, summary, tmp_path):
        m = builder.build_all(summary, tmp_path, "qc_2026")
        assert isinstance(m, ReportManifest)
        assert m.base_name == "qc_2026"
        assert m.out_dir == tmp_path.resolve()
        assert set(m.artifacts.keys()) == set(ReportFormat)
        for fmt in ReportFormat:
            assert m.get(fmt).path.name == f"qc_2026.{fmt.value}"
            assert m.get(fmt).path.exists()
        assert m.duration_ms >= 0.0

    def test_subset_of_formats(self, builder, summary, tmp_path):
        m = builder.build_all(
            summary, tmp_path, "subset", formats=(ReportFormat.EXCEL,)
        )
        assert list(m.artifacts.keys()) == [ReportFormat.EXCEL]
        assert not (tmp_path / "subset.pdf").exists()

    def test_manifest_get_missing_raises(self, builder, summary, tmp_path):
        m = builder.build_all(
            summary, tmp_path, "x", formats=(ReportFormat.EXCEL,)
        )
        with pytest.raises(KeyError, match="pdf"):
            m.get(ReportFormat.PDF)

    def test_paths_property(self, builder, summary, tmp_path):
        m = builder.build_all(summary, tmp_path, "paths")
        d = m.paths
        assert set(d.keys()) == set(ReportFormat)

    def test_empty_base_name_rejected(self, builder, summary, tmp_path):
        with pytest.raises(ReportBuildError, match="base_name"):
            builder.build_all(summary, tmp_path, "")

    def test_slash_base_name_rejected(self, builder, summary, tmp_path):
        with pytest.raises(ReportBuildError, match="base_name"):
            builder.build_all(summary, tmp_path, "sub/name")

    def test_reserved_char_rejected(self, builder, summary, tmp_path):
        with pytest.raises(ReportBuildError, match="reserved"):
            builder.build_all(summary, tmp_path, "bad?name")

    def test_atomic_no_tmp_leftovers(self, builder, summary, tmp_path):
        builder.build_all(summary, tmp_path, "clean")
        leftovers = [p for p in tmp_path.iterdir() if p.suffix == ".tmp"]
        assert leftovers == []

    def test_non_atomic_mode(self, summary, tmp_path):
        b = ReportBuilder(atomic=False, generators=_fake_generators())
        m = b.build_all(summary, tmp_path, "nonatomic")
        assert len(m.artifacts) == 3


# ---------------------------------------------------------------------------
# Real-generator smoke test — builds a minimal QCProjectSummary and runs the
# whole triple. Guards the "diff ≤1%" contract by ensuring the underlying
# code path is still reachable through the façade.
# ---------------------------------------------------------------------------


class TestRealGeneratorsSmoke:
    def _summary(self):
        from geoview_common.qc.common.models import (
            QCDomain,
            QCGrade,
            QCProjectSummary,
            QCResult,
            QCStatus,
        )

        res = QCResult(
            domain=QCDomain.MAG,
            file_name="line_001.mag",
            line_name="L001",
            total_score=92.3,
            grade=QCGrade.A,
            status=QCStatus.PASS,
            record_count=1500,
        )
        return QCProjectSummary(
            project_name="A1.6 Smoke",
            client="GeoView",
            vessel="RV-Test",
            domain=QCDomain.MAG,
            total_files=1,
            analyzed_files=1,
            avg_score=92.3,
            pass_count=1,
            results=[res],
        )

    def test_real_excel_writes(self, tmp_path):
        b = ReportBuilder()
        art = b.build_excel(self._summary(), tmp_path / "real.xlsx")
        # XLSX is a ZIP — starts with PK
        assert art.path.read_bytes()[:2] == b"PK"
        assert art.size_bytes > 1000

    def test_real_word_writes(self, tmp_path):
        b = ReportBuilder()
        art = b.build_word(self._summary(), tmp_path / "real.docx")
        assert art.path.read_bytes()[:2] == b"PK"
        assert art.size_bytes > 1000

    def test_real_pdf_writes(self, tmp_path):
        b = ReportBuilder()
        art = b.build_pdf(self._summary(), tmp_path / "real.pdf")
        assert art.path.read_bytes()[:5] == b"%PDF-"
        assert art.size_bytes > 500

    def test_real_build_all(self, tmp_path):
        b = ReportBuilder()
        m = b.build_all(self._summary(), tmp_path, "smoke_all")
        for fmt in ReportFormat:
            art = m.get(fmt)
            assert art.path.exists()
            assert art.size_bytes > 400
