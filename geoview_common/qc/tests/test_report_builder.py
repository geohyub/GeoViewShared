"""Tests for geoview_common.qc.common.report_builder"""
import pytest
from geoview_common.qc.common.models import (
    QCDomain, QCResult, QCProjectSummary, QCGrade, QCStatus,
)
from geoview_common.qc.common.report_builder import (
    generate_excel_report, generate_word_report, generate_pdf_report,
)


@pytest.fixture
def sample_summary():
    return QCProjectSummary(
        project_name="Test Project",
        client="TestCo",
        vessel="MV Test",
        total_files=3,
        analyzed_files=3,
        avg_score=82.5,
        pass_count=2,
        warn_count=1,
        fail_count=0,
        results=[
            QCResult(domain=QCDomain.MAG, file_name="mag.882", total_score=90, grade=QCGrade.A, status=QCStatus.PASS),
            QCResult(domain=QCDomain.SONAR, file_name="sonar.jsf", total_score=68, grade=QCGrade.D, status=QCStatus.WARN),
            QCResult(domain=QCDomain.SEISMIC, file_name="seis.sgy", total_score=89, grade=QCGrade.B, status=QCStatus.PASS),
        ],
    )


@pytest.fixture
def empty_summary():
    return QCProjectSummary(project_name="Empty", total_files=0)


class TestExcelReport:
    def test_generates_bytes(self, sample_summary):
        buf = generate_excel_report(sample_summary)
        assert len(buf.getvalue()) > 1000

    def test_xlsx_magic_bytes(self, sample_summary):
        buf = generate_excel_report(sample_summary)
        assert buf.getvalue()[:4] == b"PK\x03\x04"  # ZIP (xlsx)

    def test_empty_project(self, empty_summary):
        buf = generate_excel_report(empty_summary)
        assert len(buf.getvalue()) > 500


class TestWordReport:
    def test_generates_bytes(self, sample_summary):
        buf = generate_word_report(sample_summary)
        assert len(buf.getvalue()) > 5000

    def test_docx_magic_bytes(self, sample_summary):
        buf = generate_word_report(sample_summary)
        assert buf.getvalue()[:4] == b"PK\x03\x04"  # ZIP (docx)

    def test_empty_project(self, empty_summary):
        buf = generate_word_report(empty_summary)
        assert len(buf.getvalue()) > 5000


class TestPdfReport:
    def test_generates_bytes(self, sample_summary):
        buf = generate_pdf_report(sample_summary)
        assert len(buf.getvalue()) > 500

    def test_pdf_magic_bytes(self, sample_summary):
        buf = generate_pdf_report(sample_summary)
        assert buf.getvalue()[:5] == b"%PDF-"

    def test_empty_project(self, empty_summary):
        buf = generate_pdf_report(empty_summary)
        assert buf.getvalue()[:5] == b"%PDF-"
