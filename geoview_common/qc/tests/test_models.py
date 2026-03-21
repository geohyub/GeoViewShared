"""Tests for geoview_common.qc.common.models"""
import pytest
from geoview_common.qc.common.models import (
    QCDomain, QCStatus, QCGrade,
    QCMetric, QCIssue, QCStageResult, QCResult, QCProjectSummary,
)


class TestQCStatus:
    def test_from_score_pass(self):
        assert QCStatus.from_score(85) == QCStatus.PASS

    def test_from_score_warn(self):
        assert QCStatus.from_score(65) == QCStatus.WARN

    def test_from_score_fail(self):
        assert QCStatus.from_score(30) == QCStatus.FAIL

    def test_from_score_boundary_80(self):
        assert QCStatus.from_score(80) == QCStatus.PASS

    def test_from_score_boundary_50(self):
        assert QCStatus.from_score(50) == QCStatus.WARN

    def test_from_score_zero(self):
        assert QCStatus.from_score(0) == QCStatus.FAIL


class TestQCMetric:
    def test_display_nT(self):
        m = QCMetric("Noise", 0.85, "nT")
        assert m.display == "0.85 nT"

    def test_display_pct(self):
        m = QCMetric("Rate", 92.34, "%")
        assert m.display == "92.3%"

    def test_display_dB(self):
        m = QCMetric("SNR", 18.5, "dB")
        assert m.display == "18.5 dB"

    def test_display_no_unit(self):
        m = QCMetric("Count", 42.0)
        assert m.display == "42.00"


class TestQCStageResult:
    def test_normalized_score(self):
        s = QCStageResult("Test", score=7.5, max_score=10)
        assert s.normalized_score == 75.0

    def test_normalized_score_zero_max(self):
        s = QCStageResult("Test", score=5, max_score=0)
        assert s.normalized_score == 0.0

    def test_normalized_score_cap_100(self):
        s = QCStageResult("Test", score=15, max_score=10)
        assert s.normalized_score == 100.0


class TestQCResult:
    def test_issue_counts_empty(self):
        r = QCResult(domain=QCDomain.MAG, file_name="test.mag")
        assert r.issue_counts == {"critical": 0, "warning": 0, "info": 0}

    def test_issue_counts(self):
        r = QCResult(
            domain=QCDomain.SONAR, file_name="test.jsf",
            issues=[
                QCIssue("critical", "noise", "High noise"),
                QCIssue("warning", "alt", "Low altitude"),
                QCIssue("warning", "track", "Deviation"),
            ],
        )
        assert r.issue_counts == {"critical": 1, "warning": 2, "info": 0}

    def test_all_metrics(self):
        r = QCResult(
            domain=QCDomain.SEISMIC, file_name="test.sgy",
            stages=[
                QCStageResult("A", metrics=[QCMetric("m1", 1.0), QCMetric("m2", 2.0)]),
                QCStageResult("B", metrics=[QCMetric("m3", 3.0)]),
            ],
        )
        assert len(r.all_metrics) == 3


class TestQCProjectSummary:
    def test_overall_status_fail(self):
        s = QCProjectSummary("P", fail_count=1, warn_count=2, pass_count=5)
        assert s.overall_status == QCStatus.FAIL

    def test_overall_status_warn(self):
        s = QCProjectSummary("P", fail_count=0, warn_count=1, pass_count=5)
        assert s.overall_status == QCStatus.WARN

    def test_overall_status_pass(self):
        s = QCProjectSummary("P", fail_count=0, warn_count=0, pass_count=5)
        assert s.overall_status == QCStatus.PASS

    def test_overall_status_na(self):
        s = QCProjectSummary("P")
        assert s.overall_status == QCStatus.NA

    def test_completion_pct(self):
        s = QCProjectSummary("P", total_files=10, analyzed_files=7)
        assert s.completion_pct == 70.0

    def test_completion_pct_zero(self):
        s = QCProjectSummary("P", total_files=0)
        assert s.completion_pct == 0.0
