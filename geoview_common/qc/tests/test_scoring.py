"""Tests for geoview_common.qc.common.scoring"""
import pytest
from geoview_common.qc.common.scoring import (
    assign_grade, compute_score, ScoreComponent, ScoringProfile,
    MAG_SCORING_PROFILE, SONAR_SCORING_PROFILE, SEISMIC_SCORING_PROFILE,
    GRADE_BOUNDARIES,
)
from geoview_common.qc.common.models import QCGrade, QCStatus


class TestAssignGrade:
    def test_grade_A(self):
        assert assign_grade(95) == QCGrade.A

    def test_grade_B(self):
        assert assign_grade(85) == QCGrade.B

    def test_grade_C(self):
        assert assign_grade(75) == QCGrade.C

    def test_grade_D(self):
        assert assign_grade(65) == QCGrade.D

    def test_grade_F(self):
        assert assign_grade(55) == QCGrade.F

    def test_boundary_90(self):
        assert assign_grade(90) == QCGrade.A

    def test_boundary_89(self):
        assert assign_grade(89.9) == QCGrade.B

    def test_zero(self):
        assert assign_grade(0) == QCGrade.F


class TestScoreComponent:
    def test_higher_is_better_perfect(self):
        c = ScoreComponent("snr", 15, best=25, worst=5, higher_is_better=True)
        assert c.score(25) == 15.0

    def test_higher_is_better_worst(self):
        c = ScoreComponent("snr", 15, best=25, worst=5, higher_is_better=True)
        assert c.score(5) == 0.0

    def test_higher_is_better_mid(self):
        c = ScoreComponent("snr", 10, best=20, worst=0, higher_is_better=True)
        assert c.score(10) == pytest.approx(5.0)

    def test_lower_is_better_perfect(self):
        c = ScoreComponent("noise", 25, best=0.5, worst=5, higher_is_better=False)
        assert c.score(0.5) == 25.0

    def test_lower_is_better_worst(self):
        c = ScoreComponent("noise", 25, best=0.5, worst=5, higher_is_better=False)
        assert c.score(5) == 0.0

    def test_clamped_above(self):
        c = ScoreComponent("x", 10, best=100, worst=0, higher_is_better=True)
        assert c.score(200) == 10.0  # clamped to max

    def test_clamped_below(self):
        c = ScoreComponent("x", 10, best=100, worst=0, higher_is_better=True)
        assert c.score(-50) == 0.0  # clamped to 0

    def test_equal_best_worst(self):
        c = ScoreComponent("x", 10, best=5, worst=5)
        assert c.score(5) == 10.0  # avoid div by zero


class TestScoringProfile:
    def test_max_score(self):
        p = ScoringProfile("test", [
            ScoreComponent("a", 60, 0, 1),
            ScoreComponent("b", 40, 0, 1),
        ])
        assert p.max_score == 100

    def test_validate_sum_warning(self):
        p = ScoringProfile("test", [
            ScoreComponent("a", 60, 0, 1),
            ScoreComponent("b", 30, 0, 1),
        ])
        issues = p.validate()
        assert any("90" in i for i in issues)

    def test_validate_no_issues(self):
        p = ScoringProfile("test", [
            ScoreComponent("a", 50, 0, 1),
            ScoreComponent("b", 50, 0, 1),
        ])
        assert p.validate() == []

    def test_validate_duplicates(self):
        p = ScoringProfile("test", [
            ScoreComponent("x", 50, 0, 1),
            ScoreComponent("x", 50, 0, 1),
        ])
        issues = p.validate()
        assert any("Duplicate" in i for i in issues)


class TestComputeScore:
    def test_perfect_mag(self):
        m = {"noise_pp": 0.3, "fourth_diff_exceedance": 0, "spike_pct": 0,
             "integrity_pct": 100, "timestamp_regularity": 100}
        r = compute_score(MAG_SCORING_PROFILE, m)
        assert r["total_score"] >= 95
        assert r["grade"] == QCGrade.A

    def test_terrible_mag(self):
        m = {"noise_pp": 10, "fourth_diff_exceedance": 15, "spike_pct": 8,
             "integrity_pct": 70, "timestamp_regularity": 60}
        r = compute_score(MAG_SCORING_PROFILE, m)
        assert r["total_score"] < 30
        assert r["grade"] == QCGrade.F

    def test_missing_data_penalty(self):
        r = compute_score(MAG_SCORING_PROFILE, {}, missing_penalty=0.6)
        assert r["total_score"] == pytest.approx(60.0, abs=0.1)
        assert any(c.get("missing") for c in r["components"])

    def test_status_matches_score(self):
        m = {"noise_pp": 1.0, "fourth_diff_exceedance": 2, "spike_pct": 0.5,
             "integrity_pct": 98, "timestamp_regularity": 95}
        r = compute_score(MAG_SCORING_PROFILE, m)
        expected_status = QCStatus.from_score(r["total_score"])
        assert r["status"] == expected_status

    def test_components_count(self):
        r = compute_score(SONAR_SCORING_PROFILE, {"altitude_compliance": 95})
        assert len(r["components"]) == len(SONAR_SCORING_PROFILE.components)


class TestBuiltinProfiles:
    def test_mag_valid(self):
        assert MAG_SCORING_PROFILE.validate() == []

    def test_sonar_valid(self):
        assert SONAR_SCORING_PROFILE.validate() == []

    def test_seismic_valid(self):
        assert SEISMIC_SCORING_PROFILE.validate() == []

    def test_mag_100(self):
        assert MAG_SCORING_PROFILE.max_score == 100

    def test_sonar_100(self):
        assert SONAR_SCORING_PROFILE.max_score == 100

    def test_seismic_100(self):
        assert SEISMIC_SCORING_PROFILE.max_score == 100
